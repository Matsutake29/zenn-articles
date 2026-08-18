---
title: "一次情報がnode_modulesに入っていた——読んだら自分のやり方が古かった"
emoji: "📦"
type: "tech"
topics: ["nextjs", "ai", "ドキュメント", "個人開発", "agentsmd"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

## 検索して出てくる記事が、手元のバージョンと噛み合わない

Next.js 16 を使っていて、何度か同じ形で詰まりました。

検索して出てきた記事のコードを写しても動かない。
よく見ると v15 以前の前提で書かれています。
**書かれた時点では正しかった**ので、記事のどこにも「これは古い」とは書いてありません。

AIに聞いても似たことが起きます。
学習データに入っているのは、ある時点までの Next.js です。
自分が入れたものより古いことがあり、しかも古いという申告は出てきません。

実際、`middleware` が `proxy` に改名されていたことに気づかず、
古い名前のまま実装しかけて時間を使いました。

## インストール済みのバージョンと一致するドキュメントが手元にあった

調べていて知ったのですが、Next.js はドキュメントをパッケージに同梱しています。

```bash
$ ls node_modules/next/dist/docs/
01-app  02-pages  03-architecture  04-community  index.md
```

公式サイトと同じ構造がそのまま入っています。
`01-app/02-guides/` の下だけで50本以上ありました。

大事なのは網羅性より、**インストールしたバージョンと完全に一致している**ことです。
「この記事はどのバージョンの話か」を確認する手間が、まるごと消えます。
ネットワークも要りません。

自分のプロジェクトは Next.js 16.3.0 / React 19.2.8 です。

## エージェント向けの入口があった

同梱されているのはドキュメント本体だけではありませんでした。

`AGENTS.md` という索引ファイルをプロジェクトのルートに置いて、
AIエージェントに「まずここを読め」と伝える仕組みがあります。
自分のリポジトリにも作りました。8832バイトの1ファイルです。

冒頭がこうなっています。

```
[Next.js Docs Index]|root: ./node_modules/next/dist/docs|
STOP. What you remember about Next.js is WRONG for this project.
Always search docs and read before any task.
```

「お前が覚えている Next.js は、このプロジェクトでは間違っている」。
その日に自分が踏んだ事故の対策が、そのまま書かれていました。

## そのドキュメントを読んだら、自分のやり方が古かった

ここからが本題です。

同梱ドキュメントに `01-app/02-guides/ai-agents.md` というページがあります。
せっかく手元にあるので読んでみたら、**自分が使ったコマンドが「legacy」と書かれていました。**

原文はこうです。

> On version 16.1 and earlier, the docs are not bundled either.
> Use the legacy `agents-md` command, which downloads a version-matched copy to `.next-docs/`

自分が実行した `npx @next/codemod@canary agents-md` は、
**16.1 以前のための後方互換のコマンド**でした。

現行の仕組みはバージョンごとに分かれています。

| バージョン | ドキュメントの同梱 | `AGENTS.md` |
|---|---|---|
| **16.3 以降** | ✅ | **`next dev` が自動生成**（`CLAUDE.md` も） |
| 16.2 | ✅ | 自動生成されない。自分で書く |
| 16.1 以前 | ❌ | `agents-md` で `.next-docs/` にダウンロードして索引 |

自分は 16.3.0 なので、**何もしなくても `next dev` を動かした時点で生成される**側にいました。
コマンドを探して実行した手間は、丸ごと要らなかったことになります。

16.3 が生成するブロックは、内容も自分のものとは違います。

```md
<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure
may all differ from your training data.
Read the relevant guide in `node_modules/next/dist/docs/` before writing any code.

<!-- END:nextjs-agent-rules -->
```

## 手元の実物と、公式の説明が一部合わなかった

ここで1つ引っかかったので書いておきます。

公式は「legacy コマンドは `.next-docs/` にダウンロードする」と説明しています。
ところが自分のプロジェクトに `.next-docs/` はありません。
生成された `AGENTS.md` も、`root: ./node_modules/next/dist/docs` と**同梱ドキュメントを指しています。**

ダウンロードは起きていませんでした。

`@canary` を付けて実行したので、公式の説明より新しい挙動になっていたのだと思いますが、
**確かめたわけではないので断定はできません。**
どちらが正しいかを判定できる材料が手元にないので、「自分の環境ではこうなっていた」という記録として置いておきます。

もう1つ。自分のファイルには 16.3 の管理ブロック（`BEGIN:nextjs-agent-rules`）が入っておらず、
`CLAUDE.md` も生成されていません。
先に別形式の `AGENTS.md` を置いてしまったことが影響していそうですが、これも未確認です。

## ハマりどころ: `next dev` が書き戻す

16.3 の管理ブロックについて、ドキュメントにこう書かれています。

> This block is written and re-added by `next dev`.
> Removing it from a diff only re-creates the uncommitted change;
> committing it with your work keeps the tree clean.

**消しても `next dev` のたびに戻ってきます。**
コミットしないと、git の差分に出続けることになります。
「生成物だからコミットしない」と判断すると、毎回同じ差分を見ることになる作りです。

生成元まで書いてあり、`node_modules/next/dist/server/lib/generate-agent-files.js` を見ろとあります。
挙動を疑ったときに読む場所が明示されているのは、ドキュメントとしてありがたい形でした。

## ネットワーク越しにも読める

`node_modules` を読めない環境向けの経路も用意されていました。

- `nextjs.org/docs` の任意のURLに `.md` を付けると Markdown が返る
- `Accept: text/markdown` を送っても Markdown になる
- `/docs/llms.txt`（索引）と `/docs/llms-full.txt`（全文）が [llms.txt の規約](https://llmstxt.org/) に沿って置かれている

エラーページ（`/docs/messages` 以下）は同梱されていないので、そちらはネットワーク経由になります。

## 持ち帰り

- **バージョンが一致したドキュメントが `node_modules/next/dist/docs/` にある**（16.2 以降）。
  検索やAIを否定する話ではなく、「バージョンが一致している」という一点で確実性が違う
- **16.3 以降は `next dev` が `AGENTS.md` を自動生成する。** 自分が使った `agents-md` コマンドは 16.1 以前向け
- ⭐ 一次情報を読みに行ったら、**古い情報で踏まない方法より先に、
  自分がいましている手順が古いことのほうが見つかりました。**
  読まなければ、要らない手順をこの先も続けていたと思います
- 手元の実物と公式の説明が食い違う箇所もありました。**そこは断定せず、実測として書いておく**のが今のところの落としどころです
