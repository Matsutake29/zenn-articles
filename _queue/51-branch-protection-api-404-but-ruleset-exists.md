---
title: "branch protectionのAPIが404でも、保護が無いとは限らなかった（GitHubの保護は2系統ある）"
emoji: "🛡️"
type: "tech"
topics: ["github", "githubactions", "ci", "git"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

「CI が赤でも Merge できてしまう」という状態を開発の初期に見つけて、ブランチ保護を入れる作業を持ち越しにしていました。

数週間後に確認したら、**API は 404 を返し、それでも保護は効いていました**。

## 「保護されていない」という報告が誤りだった

確認は AI に任せました。返ってきたのはこうです。

```text
GET /repos/{owner}/{repo}/branches/main/protection   → 404
```

「`main` は保護されていません」という報告でした。404 なので、自分もそのまま受け取りかけました。

でも数週間前に、自分でリポジトリの設定画面から何か入れた記憶があります。そこで別のエンドポイントを叩いてもらいました。

```text
GET /repos/{owner}/{repo}/rulesets

[main protection] enforcement=active target=branch     ← 2026-08-06 作成
  rule: deletion / non_fast_forward
  rule: required_status_checks → build
  rule: pull_request
```

**ありました。** 最初の API が見ていたのとは別の場所です。

## GitHub の保護は2系統ある

| | エンドポイント | 設定画面 |
|---|---|---|
| クラシックの branch protection | `/branches/{branch}/protection` | Settings → Branches |
| **ルールセット** | `/rulesets` | Settings → **Rules** → Rulesets |

自分が設定していたのは後者のルールセットでした。クラシックのほうには何も無いので、そちらの API は 404 を返します。

404 は「このリソースは存在しない」という意味で、それ自体は正確です。ただ、**保護そのものが無い**という意味にはなりません。ルールセットという別の入り口が、同じ役目を持っているからです。

## 実地で確かめた

API の応答だけでは、どちらの系統が「実際に Merge を止めるか」までは分かりません。使い捨ての draft PR を1本立てて、わざとテストを落としました。

```text
4. Run npm ci               — success
5. Run npm run lint         — success
6. Run npm run format:check — success
7. Run npm run test:run     — failure   ← ここで止まった
8. Run npm run build        — skipped   ← 走らずに飛ばされた
```

draft を外しても **`Merge pull request` は灰色のまま**でした。`All checks have failed`、そして `CI / build (pull_request)` に **`Required`** のバッジ。ルールセットの `required_status_checks → build` が効いています。

確認後に PR は close して、ブランチも削除しました。

### ついでに見えたこと

`build` が **skipped** になっているのが、自分には収穫でした。

CI の順序は「速く落ちるものを先に」と考えて lint → format → test → build の順に置いていたのですが、**本当にそう動くのを見たのはこれが初めて**です。テストが落ちた時点で、いちばん重い build には進んでいません。順序の理由を書いたときは、まだ動きを見ていませんでした。

## 確認手段が1つだと外す

今回の流れを並べるとこうなります。

1. クラシックの API → 404
2. 「保護されていない」と判断（**誤報**）
3. 別系統の API → ルールセットが存在
4. 使い捨て PR で実地確認 → Merge が止まる

2 で止まっていたら、既に入っている保護を二重に入れようとして、設定画面で「あれ、もうある」となっていたはずです。それなら害はありません。ただ、逆のケースだと困ります。**あると思っていたものが、確認した系統には無かった**、というほうです。

GitHub が分かりにくい、という話にはしたくありません。2系統あるのは移行期の設計として自然だと思います。自分が持ち帰ったのは、**「無い」という応答は確認した範囲でしか成立しない**、というほうでした。1つの API が 404 でも、他の入り口を見るまでは「無い」とは言えない。

保護が効いているかは、結局 PR を1本立てて押してみるのが確実でした。
