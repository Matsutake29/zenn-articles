---
title: "matcherに「保護したいパス」を書いたら、1時間後にログアウトされた"
emoji: "🚪"
type: "tech"
topics: ["nextjs", "supabase", "認証", "個人開発", "approuter"]
published: true
published_at: 2026-09-01 18:00
---
:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS

Next.js 16 で `middleware` は `proxy` に改名されたので、以下は `src/proxy.ts` の話になります。
:::

## 保護したいのは `/dashboard` だけ。だからこう書いた

編集画面は `/dashboard`、それ以外は誰でも見られる公開ページ、という構成です。
保護したいのは `/dashboard` だけなので、こう書きました。

```ts
export const config = {
  matcher: ['/dashboard/:path*'],
}
```

素直な発想だと思います。**保護したいパスを書く。**

動作確認も通りました。
未ログインで `/dashboard` を開くと `/login` に飛ぶ。公開ページは普通に見られる。
**保護は効いています。**

## 1時間後にログアウトされる

しばらく触っていると、ログインしていたはずのセッションが切れます。

Supabase のセッションはトークンとして Cookie に入っていて、期限があります。
そして**アクセスのたびに `proxy` がそれを更新している**。

`matcher` を `/dashboard` だけに絞ると、**それ以外のページでは `proxy` 自体が動きません。**
公開ページを見て回っている間、トークンは1秒も更新されない。
期限が来たら、そのまま切れます。

## `matcher` と保護は、別の役割だった

整理するとこうです。

| | 何を決めるか |
|---|---|
| `matcher` | **`proxy` を動かす範囲**（実行するかどうか） |
| 関数の中の `if` | **通すか弾くか**（保護そのもの） |

名前が「マッチャー」なので保護の範囲に見えるのですが、決めているのは実行の範囲でした。

いま動いているのはこの形です。

```ts
// src/proxy.ts — matcher は原則全パス
export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
```

```ts
// src/utils/supabase/proxy.ts — 保護は if 文のほう
const { data } = await supabase.auth.getClaims()
const user = data?.claims

if (!user && request.nextUrl.pathname.startsWith('/dashboard')) {
  const url = request.nextUrl.clone()
  url.pathname = '/login'
  return NextResponse.redirect(url)
}
```

`matcher` から除外しているのは、`api` と静的アセットだけです。
**セッションと関係のないものしか外していません。**

## 気づけない形で壊れるのが厄介だった

これがやっかいだと思ったのは、**保護は効いているから**です。

未ログインで `/dashboard` を開けば `/login` に飛ぶ。
動作確認のチェックリストは全部通ります。

症状が出るのは1時間後で、しかも見えるのは「なんかログアウトされた」だけ。
その場でリロードすればログインし直せてしまうので、
**再現手順を書こうとした時点でもう分からなくなっています。**

## 実装中にもう1つ引っかかった

`config` を書き換えても反映されません。

`matcher` の値は**ビルド時に静的解析される**ためで、同梱ドキュメントにこう書かれています。

> The `matcher` values need to be constants so they can be statically analyzed at build-time.
> Dynamic values such as variables will be ignored.

dev サーバーを再起動するまで、古い `matcher` のまま動きます。
「直したのに直らない」で、ここでも一度止まりました。

変数を入れても無視される、というのも同じ理由です。
環境ごとに `matcher` を出し分ける、といった書き方はできません。

## `proxy` だけに保護を任せてはいけない

同梱ドキュメントを読んでいて、もう1つ大事な注意を見つけました。

> Server Functions are not separate routes in this chain. They are handled as POST requests to
> the route where they are used, so a Proxy matcher that excludes a path will also skip Server
> Function calls on that path.

Server Function（Server Action）は**独立したルートではなく、それが置かれているルートへの POST**
として扱われます。
つまり `matcher` がそのパスを除外していると、**Server Function の呼び出しも `proxy` を通りません。**

続けてこう書かれています。

> A matcher change or a refactor that moves a Server Function to a different route can silently
> remove Proxy coverage. Always verify authentication and authorization inside each Server
> Function rather than relying on Proxy alone.

**`matcher` を変えたり、Server Function を別のルートへ移しただけで、保護が黙って外れる。**
だから `proxy` だけに頼らず、Server Function の中でも認証と認可を確かめろ、と書いてあります。

自分の場合、最初に書いた `matcher: ['/dashboard/:path*']` のままだったら、
`/login` に置いた Server Action は最初から `proxy` の外にいたことになります。

## 手順書に書いてあったのに踏んだ

いちばん引っかかっているのはここです。

このプロジェクトでは実装の前に手順書を書く運用にしていて、そこには
**「matcher は保護したいパスではない」と名指しで書いてありました。**
自分で書いた文です。

それでも実装の瞬間に「保護したいパスを書く」以外の発想が出てきませんでした。
`matcher` という名前を見て、素直に保護対象を書いています。

読んで理解することと、手を動かす瞬間に思い出すことは別物なんだな、と思いました。
手順書があっても、**その行を読み返すタイミングが来なければ効かない**わけです。

## 持ち帰り

- **`matcher` は実行範囲、`if` 文が保護。** 名前から受ける印象と役割が違う
- `matcher` から外していいのは、**セッションと無関係なもの**（静的アセットなど）だけ
- **`config` はビルド時に静的解析される。** 変えたら dev サーバーを再起動する
- **Server Function は `matcher` の除外に巻き込まれる。** `proxy` だけに保護を任せない
- 動作確認で見つかるのは「その場で出る症状」だけでした。
  1時間後に出るものは、チェックリストを何周しても引っかかりません
