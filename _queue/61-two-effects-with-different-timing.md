---
title: "同じ useEffect の中に、即座に効くものと1回遅れるものが同居していた（react-hook-form）"
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
でもエラー文だけが遅れてくる。
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

つまり、検証も state 更新も1回目から動いていて、**表示だけが遅れていました**。
サーバー側を疑っていたので、ここで探す場所が変わりました。

## 原因は同じ useEffect の中にあった

`errors` オプションが何をしているのか、node_modules を開きました。

```js
// react-hook-form@7.85.0 / dist/index.esm.mjs:3578
React.useEffect(() => {
    if (props.errors) {
        control._setErrors(props.errors);
        control._focusError();
    }
}, [control, props.errors]);
```

2つが並んでいます。
症状で見えていた「フォーカスは移るのにエラーは出ない」の、両方がここにありました。

同じ関数の中で連続して呼ばれているのに、効くタイミングが違います。

## 片方は DOM を触り、もう片方は state を経由する

それぞれの実装を見ると、違いがはっきりしました。

```js
// 3103行: フォーカス側
const _focusError = () => _options.shouldFocusError &&
    !_options.shouldUseNativeValidation &&
    iterateFieldsByAction(_fields, _focusInput, _names.mount);
```

こちらはフィールドを走査して、DOM 要素に直接フォーカスを当てています。
React を経由しないので、**呼んだその場で効きます**。

```js
// 2217行: エラー側
const _setErrors = (errors) => {
    _formState.errors = errors;
    _subjects.state.next({
        errors: _formState.errors,
        isValid: false,
    });
};
```

こちらは内部の `_formState` を書き換えたあと、購読者に通知しています。
通知を受けたコンポーネント側が React の state を更新するので、**画面に出るのは次のレンダリング**です。

`useEffect` 自体がレンダリングの後に走るので、そこから state を更新すれば、表示はもう1回描画を待つことになります。
React 18 で入った自動バッチングは React 19 でも同じで、`useEffect` の中の更新もまとめられます。
バッチングされること自体は問題ではなく、**このレンダリングにはもう間に合わない**という順序の話でした。

DOM 操作は即座、state 更新は次の描画。
**同じ `useEffect` の中に、効き方の違う2つが同居していた**ことになります。

## errors オプションは外さなかった

最初は「遅れるなら `errors` オプションを使うのをやめて、自前で表示しよう」と考えました。
やめました。

**フォーカスを飛ばしているのも、この同じ `useEffect` だからです。**
オプションを外すと `_setErrors()` と一緒に `_focusError()` も失われます。
エラーのある最初の欄へ飛ぶ挙動は、入力欄が10個ある画面では効きます。
遅れる表示を直すために、効いている挙動を捨てることになります。

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
// state 側は Server Action が返した検証結果を、1レンダリング待たずに拾う。
const fieldError = (name: keyof ItemInput) =>
  formState.errors[name]?.message ?? state?.errors?.[name]?.message
```

`??` で先に出たほうを表示します。
1回目は `state` 側から出て、2回目以降は `formState` にも入っているのでそちらが使われます。
どちらも同じメッセージなので、表示は切り替わりません。

差分は2ファイルで20行足して6行消す程度でした。
原因を掴むまでのほうが長くて、切り分けに20分、修正に14分かかっています。

## 表示が出ないことと、処理が動いていないことは別

この症状で危なかったのは、**サーバー側を疑い始めていた**ことでした。
「エラーが出ない＝検証が動いていない」と読むのが自然ですが、実際には検証も state 更新も1回目から動いていて、描画のタイミングだけがずれていました。

ログを1行出して `prevState` の中身を見た時点で、探す場所が「サーバー」から「表示」に変わっています。
**症状の見た目より、どこまでは正しいかを先に確かめるほうが早い**、という進み方でした。

同じライブラリを使っていても、`errors` オプションで外部からエラーを注入する構成に踏み込まないと出てこない挙動だと思います。
GitHub の issue を探しても、この形での報告は見つけられませんでした。
近いものは `setError()` を呼んだ直後の話で、条件が少し違います。
node_modules を開けば10行で分かる話だったので、**ライブラリの中を読むのは思ったより近道**でした。
