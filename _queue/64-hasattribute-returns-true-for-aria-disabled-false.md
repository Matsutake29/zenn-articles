---
title: "hasAttribute は aria-disabled=\"false\" でも true を返す。属性名だけ置換したらテストが空洞になった"
emoji: "🟢"
type: "tech"
topics: ["テスト", "aria", "vitest", "アクセシビリティ"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

並び替えボタンの `disabled` 属性を `aria-disabled` に変えました。
フォーカスが消える不具合を直すためです。

テストも同じように、属性名を置換しました。

```js
// 変更前
expect(btn.hasAttribute('disabled')).toBe(true)

// 変更後
expect(btn.hasAttribute('aria-disabled')).toBe(true)
```

**テストは全部、緑のまま通りました。**
そして、何も検証しなくなっていました。

## 真偽の表し方が違う

`disabled` は真偽値属性です。
**属性が付いていれば true、付いていなければ属性ごと無い。**
だから `hasAttribute` で正しく判定できます。

`aria-disabled` は違います。
**文字列の値で真偽を表します。**

```html
<button aria-disabled="true">上へ移動</button>   <!-- 無効 -->
<button aria-disabled="false">上へ移動</button>  <!-- 有効 -->
```

無効でないほうにも `aria-disabled="false"` という属性が付きます。
React で `aria-disabled={index === 0}` と書けば、2番目以降のボタンにも `aria-disabled="false"` が出力されます。

つまり `hasAttribute('aria-disabled')` は、**全部のボタンで true** を返します。
無効なボタンでも、有効なボタンでも。

アサーションは残っていますが、何も切り分けていません。
`toBe(true)` が常に通るので、実装が壊れても落ちないテストになっていました。

## 値を見る形に変えた

```js
expect(ups[0].getAttribute('aria-disabled')).toBe('true')
expect(ups[1].getAttribute('aria-disabled')).toBe('false')
expect(ups[2].getAttribute('aria-disabled')).toBe('false')
```

`getAttribute` で値そのものを見ます。
返るのは文字列なので、比較するのは真偽値の `true` ではなく `'true'` です。

有効な側も `'false'` で明示的に書いています。
**「無効でないこと」を確かめないと、全部無効になる実装が通ってしまう**からです。

テストファイルには理由もコメントで残しました。

```js
// 🚨 hasAttribute は使わない。aria-disabled は false のときも属性自体は出るので、
//    hasAttribute だと「無効かどうか」ではなく「属性があるか」しか見ていないことになり、
//    全件 true で通る（＝アサーションが空洞になる）
```

同じ罠にもう一度落ちないように、というより、**次に読む人が `hasAttribute` に戻さないように**という意図です。

## `hasAttribute` が正しい場所も、同じファイルにある

ここが自分にとって整理になった点でした。

`hasAttribute` が悪いわけではありません。
**属性によって真偽の表し方が違うので、見る道具も変わる**というだけです。

同じテストファイルに、`hasAttribute` を使っているテストを1本足しています。

```js
expect(up.getAttribute('aria-disabled')).toBe('true')
expect(up.hasAttribute('disabled')).toBe(false)
expect(down.hasAttribute('disabled')).toBe(false)
```

これは「**無効な側に `disabled` が付いていないこと**」を固定するテストです。
`disabled` を書き戻すと、フォーカスが消える不具合が再発します。
だから、戻したら落ちるようにしました。

ここでは `disabled` の有無を見ているので、`hasAttribute` が正しい道具です。
1つのファイルの中で、`getAttribute` と `hasAttribute` が並んでいます。
**属性の性質に合わせて使い分けるほうが、片方を禁止するより正確**でした。

テストは20本から21本になりました。

## 名前を置換したときは、意味も置換されたか見る

振り返ると、やったのは検索と置換でした。
`disabled` を `aria-disabled` に。
実装側はそれで正しく、テスト側だけが意味を失っていました。

危ないのは、**置換した結果が緑になる**ことです。
赤くなれば手が止まりますが、緑のままなら通り過ぎます。
テストが通ったことを、テストが働いている証拠として読んでしまいます。

`aria-*` 属性は全般に値で状態を表します。
`aria-expanded` も `aria-checked` も `aria-hidden` も、false のときに属性が消えるわけではありません。
だから、この置換をする人は同じ形で踏むと思います。

一括置換をしたら、そのアサーションが**まだ偽になり得るか**を1回考える。
今回はそこが抜けていました。
