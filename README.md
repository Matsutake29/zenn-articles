# zenn-articles

Zenn articles by matsutake_prgrm

## 構成

```
articles/   Zennが記事として読む場所。ここに入った瞬間に投稿としてカウントされる
_queue/     昇格待ちの記事。Zennからは見えないのでカウントされない
books/      本
images/     記事内の画像（images/{slug}/ に置く）
scripts/    drip.py（_queue/ → articles/ の昇格）
```

## なぜ _queue/ があるのか

Zennには投稿数の上限（レートリミット）がある。判定は
**直近24時間以内の投稿数で、投稿予約中のものも含む**（[公式FAQ](https://zenn.dev/faq/rate-limit)）。

つまり `published_at` で公開日を散らしても回避できない。**pushした時点でカウントされ、
上限を超えた分は無言で捨てられる**。2026-07-26に4本まとめてpushしたところ、受理されたのは
1本だけだった。GitHub側のpushは成功するため、[デプロイ履歴](https://zenn.dev/dashboard/deploys)を
見ないと弾かれたことに気づけない。

Zennが読むのは `articles/` 直下だけなので、`_queue/` に置いておけばカウントされない。
ここから1日1本ずつ流す。**まとめて書いて、出すのは毎日1本**が成立する。

## 使い方

### 1. 記事をキューに入れる

`_queue/NN-{slug}.md` の形式で置く。`NN` は2桁の昇格順。

```
_queue/01-wp-rest-api-bulk-without-ssh.md   →  articles/wp-rest-api-bulk-without-ssh.md
```

frontmatter は `published: false` のままでよい。公開日時は昇格時に自動で入る。

```yaml
---
title: "記事タイトル"
emoji: "🔧"
type: "tech"
topics: ["wordpress", "php"]
published: false
---
```

### 2. あとは自動

GitHub Actions（`.github/workflows/drip.yml`）が **毎日 09:00 JST** に1本昇格させ、
その日の **18:00 JST 公開** で予約する。9時間の猶予があるので、弾かれても当日中に手を打てる。

次の場合はスキップする（何もせず正常終了）。

- `_queue/` が空
- その日に公開予定の記事が `articles/` に既にある（1日1本を守る）

### 3. 取りこぼしの検知

レートリミットで弾かれるとGitHub側は成功したまま何も起きないため、実行のたびに
**公開予定日を過ぎた記事がZennのフィードに載っているか**を照合する。載っていなければ
ワークフローを失敗させる（GitHubから通知が飛ぶ）。

弾かれていた場合の復旧は、`published_at` を先送りして再push。差分がないとデプロイが
再実行されないので、日時の書き換えがそのままトリガーになる。

## 手元で動かす

```bash
python3 scripts/drip.py --dry-run              # 何が起きるか確認するだけ
python3 scripts/drip.py --today 2026-07-30     # 基準日を変えて挙動を見る
python3 scripts/drip.py --publish-time 12:00   # 公開時刻を変える
python3 scripts/drip.py                        # 実際に1本昇格させる（pushは手動）
```

## 覚えておくこと

- **削除は両側で必要**。GitHubから消すだけではZenn側に残り、次のデプロイで復活する
- **slug（ファイル名）が記事の識別子**。既存と同じ名前にすると上書きになる
- 既存記事の更新はレートリミットの対象外（制限されるのは新規投稿）
- 上限緩和の申請窓口はあるが、用途は他ブログからの移行
