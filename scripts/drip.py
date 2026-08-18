#!/usr/bin/env python3
"""_queue/ に待機させた記事を、1日1本だけ articles/ へ昇格させる。

Zennのレートリミットは「直近24時間の投稿数（投稿予約中を含む）」で判定される。
→ https://zenn.dev/faq/rate-limit

そのため published_at で公開日を散らしても回避できない。pushした時点で
カウントされ、上限を超えた分は無言で捨てられる（2026-07-26に4本pushして
1本しか受理されなかった）。

Zennが記事として読むのは articles/ 直下だけなので、_queue/ に置いた
ファイルはカウントされない。ここから毎日1本ずつ流す。

24時間の起点は「前回Zennに登録された時刻」であって暦日ではない。毎日同じ
cron時刻に昇格させると、Actionsのスケジュール遅延がブレるだけで境界を割る
（2026-07-28に前回受理から23時間56分で昇格し、4分足りずに弾かれた）。
そのため昇格間隔を実時刻で見張り、MIN_INTERVAL に満たなければ見送る。
cronを日に何度も回し、条件を満たした最初のtickで昇格させる前提の設計。

昇格時刻は毎日15分以上うしろへずれる。これは仕様であって不具合ではない。
2026-08-03にウィンドウ（当時09:00-12:00の3tick）の末尾を越えて1日飛び、
X告知だけが先に出て404を晒したため、cronを24時間ぶんに広げた。
条件を満たした最初のtickで必ず昇格するので、もう飛ばない。

公開日時（published_at）は昇格時刻から切り離し、articles/ にある
最後の公開予定日の翌日に置く。昇格が何時になっても読者から見える公開は
毎日18:00のまま動かない（→ next_publish_at）。

使い方:
    python3 scripts/drip.py              # 1本昇格させる
    python3 scripts/drip.py --dry-run    # 何が起きるかだけ表示する
"""

import argparse
import datetime
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "_queue"
ARTICLES = ROOT / "articles"

JST = datetime.timezone(datetime.timedelta(hours=9))
ZENN_USER = os.environ.get("ZENN_USER", "matsutake_prgrm")

# _queue/ のファイル名は昇格順を先頭2桁で持つ（例: 01-my-article.md）
QUEUE_NAME = re.compile(r"^(\d{2})-(.+\.md)$")

# 本文の先頭に残った下書きメモ（→ strip_leading_comments）
# 終端は「行頭に単独で置かれた -->」を優先して探す。非貪欲の .*? だけだと、
# メモが本文中に <!--FOO--> のようなマーカーを引用しているとき、その行末の
# --> をブロックの終端と読んで途中で切ってしまう（2026-08-18 に1本踏んだ）。
LEADING_COMMENT_BLOCK = re.compile(r"\A\s*<!--.*?^-->[ \t]*\n", re.S | re.M)
LEADING_COMMENT = re.compile(r"\A\s*<!--.*?-->[ \t]*\n", re.S)

# 前回の昇格時刻。articles/ の published_at は「表示上の公開時刻」であって
# Zennに登録された時刻ではないため、実時刻を別に持つ必要がある
STATE = QUEUE / ".last-promoted"

# 昇格の最低間隔。24時間ちょうどだとcronの実行揺れで境界を割るので余裕を持たせる。
# 実測: 18h37m=受理 / 23h56m=拒否 / 24h15m以上=受理(3/3)。24時間付近は
# 残枠が直近の投稿ペースで変動するため通るか通らないか予測できない
MIN_INTERVAL = datetime.timedelta(hours=24, minutes=15)

# 昇格が止まったと判断してジョブを失敗させるまでの時間。MIN_INTERVAL を
# 大きく超えて見送りが続くのは、キューの詰まりか設定ミスが疑わしい
STALL_AFTER = datetime.timedelta(hours=48)


def log(msg):
    print(msg, flush=True)


def parse_frontmatter(text):
    """frontmatter部分と本文に割る。frontmatterが無ければ (None, text)。"""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return None, text
    return text[4 : end + 1], text[end + 5 :]


def strip_leading_comments(body):
    """本文冒頭のHTMLコメントを落とす。

    下書き側（/zenn-ready）は検証メモを `<!-- 【公開前チェック】 ... -->` として
    frontmatterの直後に置く。ZennのMarkdownはHTMLを許可しないため、これが
    残ったまま公開されると本文の先頭に生テキストで出る（2026-08-04に実際に出た）。
    コピー時に消し忘れても事故らないよう、昇格の直前でも落とす。
    """
    while True:
        m = LEADING_COMMENT_BLOCK.match(body) or LEADING_COMMENT.match(body)
        if not m:
            return body.lstrip("\n")
        body = body[m.end():]


def get_field(fm, key):
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", fm, re.M)
    return m.group(1) if m else None


def set_field(fm, key, value):
    """frontmatterのキーを更新する。無ければ末尾に足す。"""
    pattern = rf"^{re.escape(key)}:.*$"
    if re.search(pattern, fm, re.M):
        return re.sub(pattern, f"{key}: {value}", fm, count=1, flags=re.M)
    return fm.rstrip("\n") + f"\n{key}: {value}\n"


def scheduled_date(path):
    """記事の公開予定日（date）。published_at が無ければ None。"""
    fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    if not fm:
        return None
    raw = get_field(fm, "published_at")
    if not raw:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw.strip().strip('"').strip("'"))
    if not m:
        return None
    return datetime.date(*(int(g) for g in m.groups()))


def next_publish_at(now, publish_time):
    """公開予定日時を決める。基準は「articles/ の最後の公開予定日の翌日」。

    昇格時刻は MIN_INTERVAL のぶん毎日うしろへずれるが、公開日をそこに紐づけると
    ずれがそのまま読者側に出てしまう。articles/ の最後の1本から数えることで、
    昇格が何時になっても公開は1日1本・毎日 publish_time のまま動かない。

    昇格が publish_time を回った時刻に起きると当日枠には入れられないので翌日へ送る。
    このとき公開日は飛ばない（翌日ぶんの枠がそのまま1日先へずれるだけ）。
    """
    hh, mm = (int(x) for x in publish_time.split(":"))
    dates = [d for d in (scheduled_date(p) for p in ARTICLES.glob("*.md")) if d]
    base = max(dates) + datetime.timedelta(days=1) if dates else now.date()
    at = datetime.datetime.combine(base, datetime.time(hh, mm), tzinfo=JST)
    while at <= now:
        at += datetime.timedelta(days=1)
    return at


def fetch_published_slugs():
    """公開済み記事のslugをZennのフィードから取る。取れなければ None。"""
    url = f"https://zenn.dev/{ZENN_USER}/feed"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "zenn-drip/1.0"})
        with urllib.request.urlopen(req, timeout=20) as res:
            body = res.read().decode("utf-8", errors="replace")
    except Exception as e:  # ネットワーク断でジョブを落とさない
        log(f"[warn] フィードを取得できませんでした: {e}")
        return None
    return set(re.findall(r"/articles/([A-Za-z0-9_-]+)", body))


def verify_previous(today):
    """公開予定日を過ぎた記事が実際に公開されているかを照合する。

    レートリミットで弾かれるとGitHub側は成功したまま何も起きないため、
    ここで気づけないと数日分が静かに止まる（実際に起きた）。
    """
    # 当日公開分はまだ時刻前のことがあるので、前日〜4日前を見る
    window = [today - datetime.timedelta(days=n) for n in range(1, 5)]
    targets = []
    for path in sorted(ARTICLES.glob("*.md")):
        d = scheduled_date(path)
        if d in window:
            targets.append((path.stem, d))

    if not targets:
        log("[verify] 照合対象なし")
        return True

    published = fetch_published_slugs()
    if published is None:
        return True

    missing = [(slug, d) for slug, d in targets if slug not in published]
    for slug, d in targets:
        mark = "NG" if slug in [m[0] for m in missing] else "ok"
        log(f"[verify] {mark}  {slug}（{d} 公開予定)")

    if missing:
        log("")
        log("[verify] 公開予定日を過ぎたのに公開されていない記事があります。")
        log("         レートリミットで弾かれた可能性が高いです。")
        log("         → https://zenn.dev/dashboard/deploys でデプロイ履歴を確認し、")
        log("           published_at を先送りして再pushしてください。")
        return False
    return True


def last_promoted_at():
    """前回の昇格時刻。記録が無いか壊れていれば None（＝ガードを適用しない）。"""
    if not STATE.exists():
        return None
    raw = STATE.read_text(encoding="utf-8").strip()
    try:
        return datetime.datetime.fromisoformat(raw)
    except ValueError:
        log(f"[warn] {STATE.name} を読めないので間隔ガードを飛ばします: {raw!r}")
        return None


def interval_ok(now, force):
    """前回の昇格から MIN_INTERVAL 以上空いているか。"""
    prev = last_promoted_at()
    if prev is None:
        return True

    elapsed = now - prev
    if force:
        log(f"[force] 前回の昇格から {format_delta(elapsed)}。ガードを無視して昇格します。")
        return True
    if elapsed >= MIN_INTERVAL:
        return True

    wait = prev + MIN_INTERVAL
    log(f"[skip] 前回の昇格から {format_delta(elapsed)} しか経っていません。")
    log(f"       Zennの24時間判定を割るため見送ります（{wait:%m-%d %H:%M} 以降のtickで昇格）。")
    return False


def format_delta(delta):
    total = int(delta.total_seconds())
    return f"{total // 3600}時間{total % 3600 // 60}分"


def pick_next():
    """_queue/ から次に出す1本を返す。無ければ None。"""
    candidates = []
    for path in QUEUE.glob("*.md"):
        m = QUEUE_NAME.match(path.name)
        if not m:
            log(f"[warn] 命名規則に合わないのでスキップ: {path.name}（NN-slug.md 形式）")
            continue
        candidates.append((m.group(1), m.group(2), path))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return candidates[0]


def promote(now, publish_time, dry_run, force):
    """1本昇格させる。返り値は (エラーでないか, 昇格したか)。

    「同じ日に公開予定の記事があれば見送る」判定はここに置かない。
    公開日は next_publish_at が最後の1本の翌日に振るので重複しようがなく、
    昇格ペースは MIN_INTERVAL が抑えている。判定を残すと、昇格が publish_time を
    回って公開が翌日へ送られた日に、その翌日ぶんの昇格まで見送って1日おきになる。
    """
    if not interval_ok(now, force):
        return True, False

    picked = pick_next()
    if not picked:
        log("[skip] _queue/ が空です。")
        return True, False

    order, slug_name, src = picked
    dst = ARTICLES / slug_name
    if dst.exists():
        log(f"[error] articles/{slug_name} が既にあります。slug重複の可能性があるため中止します。")
        return False, False

    text = src.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        log(f"[error] {src.name} にfrontmatterがありません。")
        return False, False

    body = strip_leading_comments(body)

    at = f"{next_publish_at(now, publish_time):%Y-%m-%d %H:%M}"
    fm = set_field(fm, "published", "true")
    fm = set_field(fm, "published_at", at)
    title = get_field(fm, "title") or slug_name

    log(f"[promote] _queue/{src.name} → articles/{slug_name}")
    log(f"          {title}")
    log(f"          published_at: {at}")

    if dry_run:
        log("[dry-run] ファイルは変更していません。")
        return True, True

    dst.write_text("---\n" + fm + "---\n" + body, encoding="utf-8")
    src.unlink()
    STATE.write_text(now.isoformat(timespec="seconds") + "\n", encoding="utf-8")

    remaining = len([p for p in QUEUE.glob("*.md") if QUEUE_NAME.match(p.name)])
    log(f"[promote] 完了。_queue/ の残り: {remaining}本")
    log(f"          次に昇格できるのは {now + MIN_INTERVAL:%m-%d %H:%M} 以降です。")
    return True, True


def stalled(now):
    """昇格が長期間止まっていないか。在庫があるのに動いていなければ True。"""
    prev = last_promoted_at()
    if prev is None or now - prev < STALL_AFTER:
        return False
    return any(QUEUE_NAME.match(p.name) for p in QUEUE.glob("*.md"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="ファイルを変更せず動作だけ表示する")
    parser.add_argument("--publish-time", default="18:00", help="公開時刻（JST・既定 18:00）")
    parser.add_argument("--skip-verify", action="store_true", help="前回分の公開照合を省く")
    parser.add_argument("--today", help="公開照合の基準日をYYYY-MM-DDで上書きする（動作確認用）")
    parser.add_argument(
        "--force", action="store_true", help="昇格間隔のガードを無視する（手動リカバリ用）"
    )
    args = parser.parse_args()

    if not re.match(r"^\d{2}:\d{2}$", args.publish_time):
        log(f"[error] --publish-time は HH:MM 形式で指定してください: {args.publish_time}")
        return 2

    QUEUE.mkdir(exist_ok=True)
    now = datetime.datetime.now(JST)
    if args.today:
        try:
            today = datetime.date.fromisoformat(args.today)
        except ValueError:
            log(f"[error] --today は YYYY-MM-DD 形式で指定してください: {args.today}")
            return 2
    else:
        today = now.date()
    log(f"=== zenn drip / {now:%Y-%m-%d %H:%M} (JST) ===")

    ok = True
    if not args.skip_verify:
        ok = verify_previous(today)

    promote_ok, promoted = promote(now, args.publish_time, args.dry_run, args.force)
    if not promote_ok:
        return 1

    if not promoted and stalled(now):
        log("")
        log(f"[stall] 前回の昇格から {format_delta(now - last_promoted_at())} 経っているのに")
        log("        _queue/ に在庫が残ったまま昇格していません。設定かキューを確認してください。")
        ok = False

    # 昇格自体は済ませたうえで、取りこぼしがあれば失敗として通知する
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
