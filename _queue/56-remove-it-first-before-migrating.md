---
title: "Vitestの「vite-tsconfig-pathsは不要」警告に従う前に、プラグインを外して落としてみた"
emoji: "🔁"
type: "tech"
topics: ["vitest", "vite", "typescript", "testing"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

Vitest を起動するたびに、警告が1つ出ていました。

```text
The plugin "vite-tsconfig-paths" is detected. Vite now supports tsconfig paths
resolution natively via the resolve.tsconfigPaths option. You can remove the
plugin and set resolve.tsconfigPaths: true in your Vite config instead.
```

「A（プラグイン）の代わりに B（`resolve.tsconfigPaths`）を使え」と言っています。素直に B に切り替えれば済む話です。

その前に、**A を外すだけ**を試しました。

## なぜ先に外したか

前日に、`vi.mock` を外したらテストが通ってしまう、という経験をしていました。

https://zenn.dev/matsutake_prgrm/articles/vi-mock-is-for-isolation-not-for-survival

「無いと落ちる」と書いてあったものが、外しても落ちなかった。**理由が実物と違っていた**わけです。

今回の警告も、「A の代わりに B」とは言っていますが、**「そもそも A が要るのか」は言っていません**。いきなり B に切り替えると、B が効いたのか、そもそも要らなかったのかが区別できない。同じ構造だと思ったので、対照を取ることにしました。

## 結果

| 実験 | config | 結果 |
|---|---|---|
| **A を外すだけ** | プラグインなし・`resolve` なし | **3ファイルとも落ちた**（`Failed to resolve import "@/lib/schemas/item"`） |
| **B に切り替え** | `resolve.tsconfigPaths: true` | **18本緑・警告も消えた** |
| 元 | `vite-tsconfig-paths` プラグイン | 18本緑・**警告あり** |

A を外したら落ちました。**A は本当に要るものでした。** 古かったのは手段だけです。

config はこうなりました。

```ts:vitest.config.mts
export default defineConfig({
  plugins: [react()],
  resolve: {
    // これが無いと `@/` を解決できない。Vitest は tsconfig の paths を自動では
    // 読まない（外して実測したら3ファイルとも Failed to resolve import で落ちた）。
    // 以前は vite-tsconfig-paths プラグインで教えていたが、Vite が同じことを
    // 自分でできるようになったので依存を1つ減らした
    tsconfigPaths: true,
  },
  ...
```

依存は `globrex` / `tsconfck` / `vite-tsconfig-paths` の3つ減。`package-lock.json` の差分は削除のみで追加ゼロでした。

## 前日と同じ確認で、結論が逆になった

| | 外してみた結果 | 分かったこと |
|---|---|---|
| `vi.mock`（前日） | **落ちなかった** | **理由が間違っていた**（落ちるのを防ぐためではなかった） |
| `vite-tsconfig-paths`（今回） | **落ちた** | **理由は正しく、手段だけが古かった** |

同じ「外して確かめる」で、片方は理由が崩れ、片方は理由が裏付けられました。

どちらも「コメントを信じたまま触ると間違える」点は同じなので、対照の取り方は変えなくてよさそうです。結論が逆でも、確かめ方は同じでした。

だから config のコメントも、**手段の一文だけ**書き換えています。「Vitest は tsconfig の paths を自動では読まない」という理由の文は、A が落ちたことで裏付けられたので、そのまま残しました。

## 一次情報が古くなることもある

Next.js 16.3.0 に同梱されている公式の Vitest ガイド（`node_modules/next/dist/docs/` 配下）は、まだプラグイン版の config を載せています。

```ts
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
```

これは公式ガイドが悪いという話ではなくて、バージョンを固定した一次情報は、依存側が進むと古くなることがある、というだけです。警告のほうが新しかった。

「ガイドが古い」と分かったのは、A を外して落ちたのを見てからでした。その実験が保険になっていた形です。

環境: Vitest 4.1.10 / Vite 8.2.1 / Next.js 16.3.0。`lint` → `format:check` → `test:run`（18本）→ `build` をローカルと CI の両方で通しています。
