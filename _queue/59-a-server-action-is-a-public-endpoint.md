---
title: "Next.jsのServer Actionは関数に見えるが、実体はIDつきの公開エンドポイントだった"
emoji: "🚪"
type: "tech"
topics: ["nextjs", "react", "security", "serveractions"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

ヘルパー関数を1つ書きました。`export` を付けるか迷って、付けませんでした。

理由を調べる過程で、Server Action が自分の思っていたものと違うことが分かりました。関数呼び出しの見た目をしていますが、**実体は ID つきの HTTP エンドポイントへの POST** です。ここから2つの帰結が出ます。

## 1つの事実

`'use server'` を書いたファイルで `export` した関数は、Next.js がビルド時に ID を振り、**POST で叩ける状態になります**。認証は、関数の中に書いたものがすべてです。

普通の関数なら、呼ぶ側が認証を通っていれば安全です。Server Action は違いました。

## 帰結A: export した瞬間に穴が開く

書いたのは、公開ページのキャッシュを捨てるヘルパーです。

- 引数は `userId` だけ。**認証を持たない**（呼び出し元で `auth.getUser()` を通している前提）
- export すると、**誰でも任意の `userId` を送れる**

対策は単純で、**export しない**。同じファイル内の Server Action から呼ぶだけにしました。

```ts:src/app/dashboard/actions.ts
// export しない。'use server' ファイルで export した関数は
// すべて公開エンドポイントになる
async function revalidatePublicPage(supabase: SupabaseClient, userId: string) {
  ...
}

export async function toggleVisible(id: string, visible: boolean) {
  // 認証はここで通す
  ...
  await revalidatePublicPage(supabase, auth.claims.sub)
}
```

`'use client'` を間違えると「重くなる」。`'use server'` を間違えると「穴が開く」。どちらもファイル単位で効くのに、間違えたときの結果だけが違う。

## 帰結B: ID はビルドごとに変わる

`npm run dev` で開いていたタブをそのままにして `npm start`（本番ビルド）へ切り替え、画面のボタンを押したら出ました。

```text
Server Action "6022524a…" was not found on the server.
This request might be from an older or newer deployment.
```

ブラウザが持っている HTML は **dev が返したもの**で、サーバーは**本番ビルド**。ID が噛み合いません。スタックトレースが `.next/dev/static/chunks/...` を指していたのが決定的でした。リロードで直ります。

これは開発中だけの話ではなくて、**実運用でも起きます**。デプロイの瞬間、古いタブを開いたままのユーザーが押すと同じエラーになる。Next.js が公式に `failed-to-find-server-action` のエラーページを用意しているくらい典型的なものでした。

## どちらも「実体がエンドポイント」から出ている

| 帰結 | 理由 |
|---|---|
| export の有無が公開範囲を決める | ID を振られて POST で叩けるから |
| ビルドが変わると古いタブから叩けなくなる | ID がビルドごとに変わるから |

普通の関数呼び出しでは、どちらも絶対に起きません。**同じ見た目のコードが、まったく違うものになっている**。片方だけ知っていると理由が浅くなるので、2つ並べて覚えることにしました。

## 自分のプロジェクトのどの関数が公開されているか

最後に、これは自分向けの確認手順です。

```bash
grep -rn "^export async function" src --include="*.ts" -l | xargs grep -l "'use server'"
```

`'use server'` ファイルの `export` を数えると、それがそのまま公開エンドポイントの一覧になります。「知らずに書いていた」というより、書きながら気づけたのが今回は幸運でした。次のプロジェクトでは、最初にこれを数えるところから入ると思います。

環境: Next.js 16.3.0 / React 19.2.8。エラーメッセージ中の ID は自分のビルドのもので、値そのものに意味はありません。
