---
title: "React Hook Formの値が送信後に消えるのは、React 19がform.reset()を呼ぶから"
emoji: "🫗"
type: "tech"
topics: ["react", "nextjs", "reacthookform", "typescript", "form"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

編集ページで保存を押すと、全項目が空になりました。その状態でもう一度押すと「タイトルを入力してください」「URLを入力してください」が出ます。

**空の値がサーバーへ届いている。** 1回目の送信で何が起きているのかを追いました。

## 最初の見立ては外れた

「タイトルを消す操作が他の項目まで消している」と考えましたが、違いました。

切り分けを1回やったら範囲が半分になりました。**何も触らずに保存**を押しても空が飛ぶ。入力操作は無関係で、フォームの値が送信されていない（ように見える）。

## 手がかりは「URL を要求された」こと

`type: note` のカードなのに「URLを入力してください」が出ました。

検証は `type === 'link'` のときしか URL を要求しません。つまり、サーバーには `link` として届いている。**`<select>` の値までリセットされている**、と読めました。テキスト入力だけの問題ではない。

## ブラウザで直接観測して確定させた

`submit` イベントと `HTMLFormElement.prototype.reset` にフックを仕掛けました。

```js
const origReset = HTMLFormElement.prototype.reset
HTMLFormElement.prototype.reset = function () {
  console.log('RESET CALLED', new Error().stack)   // ← ここに recursivelyResetForms が出る
  return origReset.call(this)
}
form.addEventListener('submit', () => console.log(Object.fromEntries(new FormData(form))), true)
```

分かったことは4つです。

1. **`submit` の時点で FormData は正しい**（capture / bubble の両方で確認）
2. そのあと React DOM の **`recursivelyResetForms` が `form.reset()` を呼んでいる**（スタックトレースで確認）
3. `reset()` は各要素を **`defaultValue`** に戻す
4. **react-hook-form は `ref.value` を書き換えているだけで、`defaultValue` は空のまま**（`defaultValue: ""` を実測）

サーバーには正しい値が届いていました。壊れていたのは送信ではなく、**送信の「あと」**です。

## `value` と `defaultValue` は別物

表示しているのは `value`、リセットが戻すのは `defaultValue`。

react-hook-form は `register` で `ref` を取り、`ref.value` に値を書き込みます。`defaultValue` 属性は触りません。だから React 19 が `form.reset()` を呼ぶと、DOM は「初期値」＝空に戻る。

React 19 が `<form action>` の完了後にフォームをリセットするのは、新規作成のフォームで次の入力をすぐ始められるようにするためで、その場面では正しい挙動です。**同じコードが、編集では欠陥になる。** 新規作成では「送信後に空になる」が正しいので、そこでは欠陥として見えませんでした。

## 対策の選択肢3つ

| 案 | 評価 |
|---|---|
| 各 input に `defaultValue={item.title}` を付ける | 根本的だが、react-hook-form の `values` と二重管理になる |
| 成功時もサーバーから値を返す | 「保存しました」表示と組むなら筋は通る。state の形が増える |
| **成功したら `redirect()` で画面を離れる** | ✅ 採用。空のフォームを見せる場面自体が消える |

```ts:src/app/dashboard/actions.ts
export async function updateItem(...) {
  ...
  revalidatePath('/dashboard')
  redirect('/dashboard')
}
```

問題を直すというより、起きない設計にした形です。編集を終えて編集画面に留まる理由がありませんでした。

1つ注意があって、`redirect()` は例外を投げて処理を打ち切る仕組みなので、`try/catch` で囲むと `NEXT_REDIRECT` を握り潰して動かなくなります。

## 「表示できているのに保存できない」の中身

画面には値が見えている。押すと消える。もう一度押すと空が飛ぶ。この現象の中身が、`value` と `defaultValue` の差でした。

`recursivelyResetForms` は React DOM の内部実装なので、今後変わりうるものです。スタックトレースで観測した、という以上のことは言えません。ただ「React 19 は form action の完了後に reset する」という挙動自体は公式に書かれているので、内部の名前が変わっても同じ形は残ると思っています。

環境: React 19.2.8 / react-hook-form 7.85.0 / Next.js 16.3.0。
