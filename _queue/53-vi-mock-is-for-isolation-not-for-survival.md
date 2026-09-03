---
title: "vi.mock を外してもテストは落ちなかった。「無いと落ちるから」ではなく「切り離すため」だった"
emoji: "🔌"
type: "tech"
topics: ["vitest", "nextjs", "react", "testing"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

自分で書いた手順書に、こう書いてありました。

> `actions.ts` が `next/headers` まで届くので、`vi.mock` が無いとテストが Supabase まで引きずり込まれて落ちる

もっともらしい理由です。そのまま信じて `vi.mock` を書くつもりでいたのですが、AI から「モックが効いていないのに緑になる形が無いか。たとえばパスがずれていても `vi.mock` は黙って何もしない」と聞かれて、確かめたくなりました。

**`vi.mock` を書かずに描画したら、通りました。**

```text
Test Files  1 passed (1)
     Tests  1 passed (1)      ← 通ってしまった
```

## 落ちなかった理由は2つ

Server Action を持つ `actions.ts` を、一覧コンポーネント `ItemList` が import しています。`actions.ts` は Supabase のクライアントを作る `server.ts` に届き、そこに `next/headers` があります。

```ts:src/utils/supabase/server.ts
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()
  ...
```

1つ目。import では落ちません。落ちるのは `await cookies()` を呼んだときです。リクエストの外で呼ぶとエラーになりますが、import しただけでは何も起きない。

2つ目。`.bind()` は呼びません。

```tsx:src/app/dashboard/item-list.tsx
<form action={moveItem.bind(null, item.id, 'up')}>
```

`.bind()` は「その引数で呼ぶ準備をした新しい関数」を作るだけで、関数本体は実行しません。フォームを送信しない限り、`cookies()` には到達しない。

つまり手順書の理由は、**もっともらしいが、確かめていない理由**でした。

## では `vi.mock` は何のために書くのか

落ちないなら要らないのか、というとそうではありませんでした。

`actions.ts` には Zod のバリデーション、Supabase への書き込み、`redirect`、`revalidatePath` が入っています。これらをどう変えても、UI のテストが影響を受けない。これが `vi.mock` を書く理由です。

「落ちるのを防ぐ」ではなく「**切り離す**」。テストは通っていたので、書く行為そのものは変わりません。変わったのは理由のほうだけです。

## 理由が変わると、副作用の見え方が変わった

「無いと落ちる」が理由なら、`vi.mock` が効いていなければテストが落ちるので、効いていないことに気づけます。

「切り離すため」が理由だと、話が逆になります。`vi.mock` に書いたパスが実際の import と食い違っていた場合、本物の `actions.ts` が読み込まれますが、上に書いたとおりそれでも落ちません。**切り離せていないのに、テストは緑のまま**になりえます（パスずれのときに Vitest が警告を出すかどうかは確かめていません。出さない前提で備えました）。

これは最初の AI の問いそのものでした。

そこで、差し替えが効いていること自体を1本にしました。

```ts:__tests__/item-list.test.tsx
test('Server Action がモックに差し替わっている', async () => {
  const { moveItem } = await import('@/app/dashboard/actions')
  expect(vi.isMockFunction(moveItem)).toBe(true)
})
```

これは「アプリの挙動」ではなく「**テスト環境**」を見るテストです。パスを直し忘れたら、ここが落ちる。

## 手順書は「確かめられる粒度」で書いてあった

手順書が間違っていた、で終わらせたくない話でした。

「`next/headers` まで届くので、無いと落ちる」という理由は、間違ってはいたのですが、**外してみれば確かめられる粒度**で書いてありました。だから実験で外せた。「なんとなく必要」と書いてあったら、外す発想にもならなかったと思います。

理由を書くときは、後から実験で反証できる形にしておくと、間違っていても直せる。今回はそれに救われました。

環境: Vitest 4.1.10 / Next.js 16.3.0 / React 19.2.8 / @testing-library/react 16.3.2。`.bind()` の話は React 19 の Server Action が前提です。
