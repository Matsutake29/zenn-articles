---
title: "デモログインのID/PWをREADMEに書くか、ボタンにするか"
emoji: "🔑"
type: "tech"
topics: ["supabase", "nextjs", "個人開発", "ポートフォリオ", "認証"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

## 登録なしで編集画面を触ってほしかった

ポートフォリオを複数の会社に送るとき、
**見る人に登録なしで編集画面まで触ってもらいたい**と考えていました。

公開ページを見せるだけなら URL を渡せば済みますが、
このアプリの作りこみは編集画面のほうに入っています。
そこを見てもらえないと、スクリーンショットを並べたのと変わりません。

そこでデモ用のアカウント（`guest`）を実ユーザーとして作りました。
入口の置き方は2つ思いつきます。

- **A: `/login` に「デモとしてログイン」ボタンを置く**（クリック1回）
- **B: README にデモのメールとパスワードを書く**（コピペ2回・手間はかかる）

最初は **B のほうが慎重なのでは**と思っていました。
ワンクリックで誰でも入れる A より、一手間あるぶん安全そうに見えたからです。

## 秘匿性では選べなかった

並べてみると、その基準では差がつきませんでした。

- ボタンを置く → 誰でも押せる
- README に書く → 誰でも読める

**どちらも公開情報**です。
入力の手間を増やしても、その見返りに秘匿性は1ミリも上がりません。

「面倒にすること」を安全と勘違いしていました。
手間はハードルに見えますが、越えられるハードルの高さを変えていないので、
実際には何も守っていません。

## 差が出たのは1点だけだった

| | ボタン | README に ID/PW |
|---|---|---|
| 資格情報の在処 | サーバーのみ | 完全に公開 |
| **認証APIを直接叩けるか** | **できない** | **できる** |
| 相手の手間 | クリック1回 | コピペ2回 |

デモの資格情報は `.env.local` に `DEMO_EMAIL` / `DEMO_PASSWORD` として置いて、
**`NEXT_PUBLIC_` を付けていません。**

Next.js では `NEXT_PUBLIC_` の付いた環境変数だけがブラウザ向けのJSに埋め込まれます。
付けなければサーバー側でしか読めないので、デモログインは Server Action の中でしか書けません。

```ts
// src/app/login/actions.ts
'use server';

export async function demoLogin(_prevState: LoginState) {
  const supabase  = await createClient();
  const { error } = await supabase.auth.signInWithPassword({
      email: process.env.DEMO_EMAIL!,
      password: process.env.DEMO_PASSWORD!,
  });
  if (error) {
    console.error('Demo login failed:', error.message)
    return { message: 'デモログインに失敗しました' }
  }
  await resetDemoData(supabase);
  redirect('/dashboard');
}
```

**ボタンにすると、パスワードを知っているのはサーバーだけ**になります。
README に書けば、サイトを経由せず Supabase の認証APIを直接叩けるようになります。

手間が増えるほうが安全そうに見えて、実際は逆でした。
安全を決めているのは面倒さではなく、**攻撃できる経路がいくつあるか**のほうです。

GitHub から来た人には、README に `→ デモを触る: https://.../login` を1本置けば足ります。
**流入経路は2つでも、入口は1つで足りました。**

## 荒らしより先に来たのは、もっと地味な問題だった

「誰でも入れるなら荒らされるのでは」と考えていました。
ただ、実際に先に来るのはこちらです。

**複数の会社に同時に応募するので、悪意がなくても A 社の方が編集した状態を B 社の方が見ます。**

カードを1枚消して試した人がいれば、次に来た人が見るのは3枚です。
荒らされたわけではありません。
**デモを触ってくれた人が普通に操作した結果**で、むしろ触ってもらえた証拠です。
止めたい動作ではありません。

面接の前に手動でリセットする案も考えましたが、**いつ誰が来るか分からない**ので守れません。
そもそも、応募先が見る時刻を自分が知っている前提のほうが無理があります。

## ログインのたびに初期化することにした

デモログインを押した瞬間に、`guest` のデータを初期状態へ戻します。

```ts
// src/lib/demo-seed.ts
export async function resetDemoData(supabase: SupabaseClient) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return

  await supabase.from('items').delete().eq('user_id', user.id)
  await supabase.from('items').insert(
    DEMO_ITEMS.map((item) => ({ ...item, user_id: user.id }))
  )
}
```

全員が同じ4枚から始められます。
前の人が何をしていても関係ありません。

## 追加の権限は要らなかった

ここは書く前に構えていたのですが、実際には何も足さずに済みました。

`guest` が消して入れ直しているのは**自分自身のデータ**なので、RLS のポリシーをそのまま通ります。

```sql
create policy "users can insert own items"
  on public.items for insert with check (auth.uid() = user_id);

create policy "users can delete own items"
  on public.items for delete using (auth.uid() = user_id);
```

テーブル権限のほうも、ログイン済みユーザーには最初から付けてあります。

```sql
grant select, insert, update, delete on public.items to authenticated;
grant select on public.items to anon;   -- 未認証は読むだけ
```

**管理者用のキー（service role）を持ち出す必要がない**のは、あとから気づいた利点でした。
初期化のために強い権限をサーバーに置くと、そのキーが漏れたときの被害範囲が変わります。
本人の権限でできる操作に収まっているうちは、その心配が発生しません。

## 却下した案

- **`guest` を読み取り専用にする** — 確実に荒らされませんが、
  「編集画面を触ってもらう」という目的を半分壊します。**見るだけならスクリーンショットで足ります**
- **面接前に手動でリセットする** — コストはほぼゼロですが、タイミングを守れません
- **デモログインを出さない** — リスクはゼロで、登録なしで触れる導線も消えます

## 持ち帰り

- **手間を増やしても秘匿性は上がらない。** 公開されているものは、面倒でも公開されている
- 差がついたのは「**資格情報がどこにあるか**」と「**サイトを経由せず叩けるか**」の2点でした
- 荒らしより先に来るのは、**善意の利用者どうしの衝突**でした。時間で守る対策は当てになりません
- 自分のデータを操作するだけなら、**RLS も GRANT も既存のままで足りました**
