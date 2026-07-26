#!/usr/bin/env python3
"""_queue/ に待機させた記事を、1日1本だけ articles/ へ昇格させる。

Zennのレートリミットは「直近24時間の投稿数（投稿予約中を含む）」で判定される。
→ https://zenn.dev/faq/rate-limit

そのため published_at で公開日を散らしても回避できない。pushした時点で
カウントされ、上限を超えた分は無言で捨てられる（2026-07-26に4本pushして
1本しか受理されなかった）。

Zennが記事として読むのは articles/ 直下だけなので、_queue/ に置いた
ファイルはカウントされない。ここから毎日1本ずつ流す。

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


def promote(today, publish_time, dry_run):
    # すでに同じ日に公開予定の記事があれば見送る（1日1本を守る）
    for path in sorted(ARTICLES.glob("*.md")):
        if scheduled_date(path) == today:
            log(f"[skip] {today} は {path.stem} が公開予定です。今日は昇格させません。")
            return True

    picked = pick_next()
    if not picked:
        log("[skip] _queue/ が空です。")
        return True

    order, slug_name, src = picked
    dst = ARTICLES / slug_name
    if dst.exists():
        log(f"[error] articles/{slug_name} が既にあります。slug重複の可能性があるため中止します。")
        return False

    text = src.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        log(f"[error] {src.name} にfrontmatterがありません。")
        return False

    at = f"{today.isoformat()} {publish_time}"
    fm = set_field(fm, "published", "true")
    fm = set_field(fm, "published_at", at)
    title = get_field(fm, "title") or slug_name

    log(f"[promote] _queue/{src.name} → articles/{slug_name}")
    log(f"          {title}")
    log(f"          published_at: {at}")

    if dry_run:
        log("[dry-run] ファイルは変更していません。")
        return True

    dst.write_text("---\n" + fm + "---\n" + body, encoding="utf-8")
    src.unlink()

    remaining = len([p for p in QUEUE.glob("*.md") if QUEUE_NAME.match(p.name)])
    log(f"[promote] 完了。_queue/ の残り: {remaining}本")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="ファイルを変更せず動作だけ表示する")
    parser.add_argument("--publish-time", default="18:00", help="公開時刻（JST・既定 18:00）")
    parser.add_argument("--skip-verify", action="store_true", help="前回分の公開照合を省く")
    parser.add_argument("--today", help="基準日をYYYY-MM-DDで上書きする（動作確認・手動リカバリ用）")
    args = parser.parse_args()

    if not re.match(r"^\d{2}:\d{2}$", args.publish_time):
        log(f"[error] --publish-time は HH:MM 形式で指定してください: {args.publish_time}")
        return 2

    QUEUE.mkdir(exist_ok=True)
    if args.today:
        try:
            today = datetime.date.fromisoformat(args.today)
        except ValueError:
            log(f"[error] --today は YYYY-MM-DD 形式で指定してください: {args.today}")
            return 2
    else:
        today = datetime.datetime.now(JST).date()
    log(f"=== zenn drip / {today} (JST) ===")

    ok = True
    if not args.skip_verify:
        ok = verify_previous(today)

    if not promote(today, args.publish_time, args.dry_run):
        return 1

    # 昇格自体は済ませたうえで、取りこぼしがあれば失敗として通知する
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
