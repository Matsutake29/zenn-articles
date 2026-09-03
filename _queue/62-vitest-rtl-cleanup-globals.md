---
title: "Next.js 公式ガイドどおりに Vitest を設定したら、2本目のテストで Found multiple elements が出た"
emoji: "🧹"
type: "tech"
topics: ["vitest", "testinglibrary", "react", "nextjs"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

Next.js 16 に同梱されている公式の Vitest ガイドどおりに設定して、1本目のテストは通りました。

2本目を書いた瞬間に落ちました。

```text
TestingLibraryElementError: Found multiple elements with the text: 削除
```

## 文言が重複したのではなかった

最初は「削除」というテキストを持つ要素が2つあるのだと思いました。似た文言のボタンが別にあるのかと。

違いました。列挙された2要素は、**どちらも同じボタン**です。1本目のテストで `render` した DOM と、2本目で `render` した DOM。1本目の分が片付いていませんでした。

なお `getByText` は既定で完全一致なので、「削除する」のような似た文言には当たりません（`@testing-library/dom` の `queries/text.js` で `exact = true` が既定値）。ここは脇道ですが、最初に疑った場所だったので書いておきます。

## 自動 cleanup は、`afterEach` がグローバルにあるときしか登録されない

Testing Library は、テストごとに DOM を掃除する `cleanup` を自動で登録してくれます。自分もそう理解していました。

実物を読んだら、条件付きでした。

```js:node_modules/@testing-library/react/dist/index.js
// if we're running in a test runner that supports afterEach
// or teardown then we'll automatically run cleanup afterEach test
// this ensures that tests run in isolation from each other
// if you don't like this then either import the `pure` module
// or set the RTL_SKIP_AUTO_CLEANUP env variable to 'true'.
if (typeof process === 'undefined' || !process.env?.RTL_SKIP_AUTO_CLEANUP) {
  if (typeof afterEach === 'function') {
    afterEach(() => {
      (0, _pure.cleanup)();
    });
```

**`typeof afterEach === 'function'` が条件です。** グローバルに `afterEach` が居なければ、この `if` は丸ごと素通りします。

Vitest がグローバルに `afterEach` を置くのは `globals: true` のときだけ。そして公式ガイドの config には `globals` がありません。

```ts:vitest.config.mts（公式ガイドのまま）
export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
  },
})
```

`describe` / `test` / `expect` を明示的に import する書き方を選んでいたので、掃除役が誰も登録されていない状態でした。

## 直し方は2つある

(a) `globals: true` にする。1行で済みます。

(b) `setupFiles` で自分で登録する。

```ts:vitest-setup.ts
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => {
  cleanup()
})
```

```ts:vitest.config.mts
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest-setup.ts'],
  },
```

自分は (b) を選びました。

| | |
|---|---|
| `globals: true` | config を読んでも「なぜ true か」が分からない。`describe` / `test` の import も要らなくなるので、**書き方が2通りになる** |
| `setupFiles` | **「毎回 `cleanup()` する」とコードそのものが説明になる**。明示 import の書き方を保てる |

(a) が間違いというわけではありません。`globals: true` を前提にしているプロジェクトなら、そもそもこの問題は起きません。自分の場合は明示 import で揃えていたので、そこを崩さない側を取りました。

## 1本目では顕在化しない

自分にとっていちばん引っかかったのはここでした。

設定漏れなのに、最初のテストは通ります。掃除されていなくても、1本だけなら残骸が無いからです。2本目を書いて初めて、1本目の DOM が残っていることが見える。

「公式ガイドどおりにやって1本通った」は、設定が揃った証拠にはなりませんでした。ガイドは1本目まで面倒を見ていて、`globals` を使うかどうかは利用側の選択、という切り分けになっています。選択の結果として cleanup が落ちる、という組み合わせの問題でした。

環境: Next.js 16.3.0（同梱の公式ガイドを一次情報にしています）/ Vitest 4.1.10 / @testing-library/react 16.3.2 / @testing-library/dom 10.4.1。
