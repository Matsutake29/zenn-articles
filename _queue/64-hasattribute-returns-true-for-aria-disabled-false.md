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

並び替えボタンで、フォーカスが消える不具合がありました。
キーボードで切り分けると、消えるのは「移動先が1番目のとき」だけで、原因は `disabled={index === 0}` でした。`disabled` な要素は、フォーカスを保持できません。

そこで `disabled` を `aria-disabled` に変えると決めました。属性の書き換えとテストの修正はAIの作業にして、自分は判断と、差分の確認を受け持つ分担です。

差分を見ると、テストは属性名の置換ではなく、`getAttribute` を使う形に変わっていました。名前だけを置換すると、こうなるからです。

```js
// 変更前
expect(btn.hasAttribute('disabled')).toBe(true)

// 名前だけ置換すると
expect(btn.hasAttribute('aria-disabled')).toBe(true)
```

**これは全部、緑のまま通ります。**
そして、何も検証しなくなります。

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

テストファイルには、理由のコメントも残してあります。

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

同じテストファイルに、`hasAttribute` を使っているテストが1本足してあります。

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

属性の変更は、検索と置換で済む作業に見えます。
`disabled` を `aria-disabled` に。
実装側はそれで正しく、テスト側だけが意味を失います。

危ないのは、**置換した結果が緑になる**ことです。
赤くなれば手が止まりますが、緑のままなら通り過ぎます。
テストが通ったことを、テストが働いている証拠として読んでしまいます。

`aria-*` 属性は全般に値で状態を表します。
`aria-expanded` も `aria-checked` も `aria-hidden` も、false のときに属性が消えるわけではありません。
だから、この置換をする人は同じ形で踏むと思います。

一括置換をしたら、そのアサーションが**まだ偽になり得るか**を1回考える。
置換の差分を読むときの見方が、1つ増えました。
