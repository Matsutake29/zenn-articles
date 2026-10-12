---
title: "react-hook-form の errors で渡したエラーが、1回目の送信だけ消えていた —— values の入れ直しが reset していた"
emoji: "⏱"
type: "tech"
topics: ["react", "reacthookform", "nextjs", "typescript"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

カードを登録するフォームで、こういう症状が出ました。

**保存を1回目に押すと、入力欄にフォーカスは移るのに、エラー文が出ない。2回目で出る。**

フォーカスは移るので、何かは効いています。
でもエラー文だけが出てこない。
この「片方だけ効く」が気持ち悪くて、原因を追いました。

環境は react-hook-form 7.85.0 / React 19.2.8 / Next.js 16.3.0 です。
Server Action の検証結果を `useActionState` で受けて、`useForm` の `errors` オプションに渡す構成でした。

## サーバーは最初から正しかった

まず、どこまで正しく動いているかを見ました。
Server Action に入ってくる値をログに出します。

```text
1回目: createItem(undefined, {})
2回目: createItem({"errors":{"title":…,"url":…},"values":{…}}, {})
```

2回目の第1引数に、1回目の結果が入っています。
`useActionState` の `prevState` なので、**1回目の時点で state は更新されていた**ということです。

つまり、検証も state 更新も1回目から動いていて、**表示だけが追いついていませんでした**。
サーバー側を疑っていたので、ここで探す場所が変わりました。

## エラーを入れる effect のすぐあとに、値を入れ直す effect が走っていた

`errors` オプションが何をしているのか、node_modules の中を読んでもらいました。

```js
// react-hook-form@7.85.0 / dist/index.esm.mjs:3578
React.useEffect(() => {
    if (props.errors) {
        control._setErrors(props.errors);
        control._focusError();
    }
}, [control, props.errors]);
```

エラーを入れて、エラーのある欄へフォーカスを当てています。ここまでは期待どおりです。

同じ描画のあと、少し下にある `values` オプションの effect も走ります。

```js
// 同 3601行
React.useEffect(() => {
    if (props.values && !deepEqual(props.values, _values.current)) {
        control._reset(props.values, {
            keepFieldsRef: true,
            ...control._options.resetOptions,
        });
        // …
    }
}, [control, props.values]);
```

`values` が前回と違えば `_reset()` が呼ばれます。そして `_reset()` は、`keepErrors` を指定していなければ `_formState.errors = {}` でエラーを空にします。

1回目の送信では、Server Action が入力値を `values` として返すので、初期値とは中身が変わります。つまり順番はこうでした。

1. エラーを入れる（`_setErrors`）
2. エラーの欄へフォーカスを当てる（`_focusError`。DOM を直接触るので、その場で効く）
3. `values` が変わったので reset され、**入れたばかりのエラーが消える**

フォーカスは DOM の操作なので reset のあとも残り、エラーだけが消えます。「フォーカスは移るのにエラー文が出ない」の正体はこれでした。

2回目の送信では、返ってくる `values` が前回と同じなので reset されません。エラーが残って、表示されます。

## 最初は「1回遅れて出る」と考えていた

最初に立てた説明は、別のものでした。フォーカスは DOM を直接触るので即座に効き、エラーは state を経由するので次の描画まで遅れる、という見方です。

ただ、それなら次の描画で自然に出るはずで、**もう1回押さないと出ない**ことの説明になっていません。記事にする前に、jsdom で同じ構成を作って動かしてみました。

| 条件 | 1回目の送信 | 2回目の送信 |
|---|---|---|
| そのまま | **出ない**（再描画は起きている） | 出る |
| `resetOptions: { keepErrors: true }` | **出る** | 出る |

再描画は起きているのにエラーが出ていないので、遅れではなく、消えていました。`keepErrors` を付けると1回目から出るので、reset が原因だと確かめられました。

## errors オプションは外さなかった

最初は「1回目に出ないなら `errors` オプションを使うのをやめて、自前で表示しよう」と考えました。
やめました。

**フォーカスを飛ばしているのも、この同じ `useEffect` だからです。**
オプションを外すと `_setErrors()` と一緒に `_focusError()` も失われます。
エラーのある最初の欄へ飛ぶ挙動は、入力欄が10個ある画面では効きます。
出ない表示を直すために、効いている挙動を捨てることになります。

そこで、**表示側で両方を見る**形にしました。

```ts
const [state, formAction, isPending] = useActionState(action, undefined)
const { register, formState } = useForm<ItemInput>({
  errors: state?.errors,
  values: (state?.values as ItemInput | undefined) ?? defaultItem,
  mode: 'onBlur',
  resolver: zodResolver(itemSchema),
})

// formState 側は onBlur のクライアント検証を拾う。
// state 側は Server Action が返した検証結果を拾う（values の入れ直しで消えても残る）。
const fieldError = (name: keyof ItemInput) =>
  formState.errors[name]?.message ?? state?.errors?.[name]?.message
```

`??` で先に出たほうを表示します。
1回目は `state` 側から出て、2回目以降は `formState` にも入っているのでそちらが使われます。
どちらも同じメッセージなので、表示は切り替わりません。

差分は2ファイルで20行足して6行消す程度でした。
原因を掴むまでのほうが長くて、切り分けに20分、修正に14分かかっています。

いま振り返ると、`resetOptions: { keepErrors: true }` を付けるのがいちばん直接的な直し方でした。ただし reset のたびにエラーを残す設定なので、値を入れ直したときに古いエラーまで残らないかは、別に確かめる必要があります。

## 表示が出ないことと、処理が動いていないことは別

この症状で危なかったのは、**サーバー側を疑い始めていた**ことでした。
「エラーが出ない＝検証が動いていない」と読むのが自然ですが、実際には検証も state 更新も1回目から動いていて、表示の手前で消えていました。

ログを1行出して `prevState` の中身を見た時点で、探す場所が「サーバー」から「表示」に変わっています。
**症状の見た目より、どこまでは正しいかを先に確かめるほうが早い**、という進み方でした。

`errors` と `values` の両方を外から渡す構成に踏み込まないと、出てこない挙動だと思います。

ライブラリの中を読むのは近道でした。ただ、読んで立てた最初の説明は外れていました。**読んだら、動かして確かめるところまでやる**。今回はそれで、記事の中身が入れ替わりました。
