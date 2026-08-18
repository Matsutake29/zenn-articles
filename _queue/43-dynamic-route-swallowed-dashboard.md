---
title: "動的ルートが /dashboard を飲み込んで、@dashboard と表示された"
emoji: "🕳️"
type: "tech"
topics: ["nextjs", "approuter", "設計", "個人開発", "postgresql"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS

`/[username]` が公開ページ、`/dashboard` が編集画面、という構成です。
:::

## 404 を期待して開いたら、ページが出た

`/dashboard` はまだ作っていませんでした。
存在しないパスなので 404 が出るはずです。

実際に出たのは **`@dashboard`** という文字列でした。
公開ページのレイアウトで、ユーザー名を表示する部分にそう入っています。

## `[username]` は何にでもマッチする

理由は単純でした。`src/app/[username]/page.tsx` があるからです。

```
src/app/
├── [username]/page.tsx   ← ここが /dashboard を拾う
└── dashboard/            ← まだ無い
```

`/dashboard` は **「username が `dashboard` のユーザーのページ」** として解決されます。
`[username]` は文字列なら何でも受け取るので、404 になるほうがおかしい。

**ルーティングとしては正しく動いていました。**

## 直し方は1ファイル作るだけだった

`src/app/dashboard/page.tsx` を置いた瞬間に解決します。

同梱ドキュメントに解決順が書かれていて、`proxy` の実行順のところで一覧になっています。

```
5. Filesystem routes (public/, _next/static/, pages/, app/, etc.)
   ...
7. Dynamic Routes (/blog/[slug])
```

**ファイルとして存在するルートのほうが、動的ルートより先に解決される。**
だから `dashboard/page.tsx` を作れば、`/dashboard` はそちらへ吸われます。

ここまでは10分もかかっていません。

## 本題はそこではなかった

直したあとで、別のことが気になりました。

**ユーザー名に `dashboard` や `login` を使えていいのか。**

使えてしまうと、その名前を取ったユーザーの公開ページは**永久に見られなくなります。**
ファイルシステムのルートが常に勝つので、`/login` は必ずログイン画面です。
`/[username]` には二度と到達しません。

登録はできる。ページも作れる。**でも誰も見られない。**
エラーも出ないので、本人は自分のページが表示されない理由が分かりません。

## DB の制約として閉じた

アプリ側のバリデーションで弾く手もありますが、書き忘れると素通りします。
登録の経路が増えたときにも付け忘れます。

**DB の CHECK 制約なら、どの経路から入れても必ず通ります。**

```sql
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique not null,
  ...
  constraint username_format check (username ~ '^[a-z0-9_-]{3,30}$'),
  constraint username_not_reserved check (
    username not in ('about', 'dashboard', 'login', 'api', 'auth', '_next', 'favicon')
  )
);
```

`_next` と `favicon` が入っているのは、フレームワークが使うパスだからです。
`api` も同じ理由で、自分でルートを作らなくても予約しておく必要があります。

書式のほうの制約（`^[a-z0-9_-]{3,30}$`）も同時に入れました。
大文字や記号を許すと、URL の見え方と DB の値がずれる余地が生まれます。

## 動作確認から設計の穴が出てきた

この論点は、机の上で設計していたときには出ていませんでした。

設計の段階で考えていたのは「公開ページと編集画面をどう分けるか」で、
**その2つが同じ名前空間を取り合うことには気づいていません。**

出てきたのは、実際に `/dashboard` を開いて `@dashboard` という表示を見た瞬間です。
バグとして見つけたものが、設計の穴を教えてきました。

手を動かさないと出てこない論点がある、というのは知識としては知っていたのですが、
**「404が出ないぞ」という小さな驚きが入口になる**とは思っていませんでした。
驚くべきだったのは 404 が出ないことではなく、誰でも `/login` を名乗れることのほうです。

## 持ち帰り

- **ファイルシステム上のルートは動的ルートより先に解決される。** だから静的なファイルを置けば勝つ
- `/[username]` のような形を作るなら、**予約語を先に決めておく**。
  自分のアプリのパスだけでなく、`_next` のようなフレームワーク側のパスも含める
- 予約語は**DB の CHECK 制約に置くと経路によらず効く**。アプリ側のバリデーションは書き忘れる
- 設計の穴は、動かしてみたときの小さな違和感から出てきました
