---
title: "React Hook Formで型エラーが正しい入り口を教えてくれて、型が通った側にバグが3箇所残った"
emoji: "🧭"
type: "tech"
topics: ["react", "typescript", "reacthookform", "nextjs"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

フォーム全体のエラー（「ログインが必要です」「保存に失敗しました」のような、特定の入力欄に紐づかないもの）を表示しようとしたら、型で止まりました。

止まった理由は「その名前は自分で決めたものだった」から。そして直したあと、**型が通るほうで**同じ問題が起きました。

## 前半 — 型が通らなかった側

フォーム全体のエラーを `_form` というキーで持っていました。表示しようとしたらこう止まります。

```text
プロパティ '_form' は型 'FieldErrors<{ title; type; visible; url?; description? }>' に存在していません
```

react-hook-form の `FieldErrors<T>` は、**T のキーしか持てません**。そして、どのフィールドにも紐づかないエラーの置き場所として **`root` が最初から用意されています**。

```ts
type FieldErrors<T> = Partial<…T のキー…> & { root?: … }
```

`_form` は、react-hook-form を入れる**前**に自分で決めた名前でした。ライブラリを足した時点で `root` に寄せるべきだった名前が、共通化のタイミングで型エラーとして表に出た形です。

ここで `as any` を書いて黙らせていたら、`root` の存在に気づけませんでした。**型が通らないときは、たいてい別に正しい入り口がある。**

```tsx:src/app/dashboard/item-form.tsx
const rootError = formState.errors.root?.message ?? state?.errors?.root?.message
```

## 後半 — 型が通ってしまった側（本当の問題）

Server Action 側を `root` に直したとき、**別の関数の3箇所に `_form` が残りました**。

| チェック | 結果 |
|---|---|
| `tsc` | ✅ 通る |
| lint | ✅ 通る |
| `return` している | ✅ している |
| **画面に出る** | ❌ **出ない** |

なぜ `tsc` が通るのか。Server Action の戻り値の型を `Record<string, …>` にしていたので、**どんなキーでも通る**からです。フォームは `errors.root` しか見ていないので、`_form` で返した3箇所は画面に何も出さない。

**見つけたのは grep でした。** 型でもテストでもなく、文字列の一致を人が確かめるしかなかった。

```bash
grep -n "_form" src/app/dashboard/actions.ts
# → 3箇所
```

## 同じリファクタで、型が守ってくれた側と守れなかった側が両方出た

- 守ってくれたほう（`FieldErrors<T>`）は、間違いを止めただけでなく**正しい入り口を教えてくれた**
- 守れなかったほう（`Record<string, …>`）は、**型を書いてあるぶん安心していた**。キーの綴りが違うだけで、コードは全部正しく見える

`Record<string, string[]>` にしていたのは自分の設計で、ライブラリの落ち度ではありません。緩い型は「何でも入る」ので、書いた瞬間は楽で、後で何も止めてくれない。

**型で守れる範囲の外側は、型を書いてあるほど見えなくなる**、というのが自分の持ち帰りでした。型があると「型が通っている＝合っている」と読んでしまう。型が何を検査していないかは、型定義を見ても書いていない。

環境: react-hook-form 7.85.0 / React 19.2.8 / Next.js 16.3.0。`FieldErrors<T>` に `root` があることは手元の型定義で確認しました。
