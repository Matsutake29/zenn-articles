---
title: "height: 100% は親の高さを見る。その親の高さは自分で決まっていた"
emoji: "📐"
type: "tech"
topics: ["css", "tailwindcss", "html", "個人開発", "flexbox"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

## カードを開いたら、隣の行に重なった

グリッドに並べたカードを、押すと説明文が開く形にしていました。

開いた瞬間、展開パネルが `<li>` からはみ出して**次の行のカードと重なります。**
パネルの中の文字は、隣のカードに隠れて左端が読めない状態でした。

書いていたのはこれだけです。

```tsx
<li>
  <button className="pin-card h-full">…</button>
  <div>…展開パネル…</div>
</li>
```

## 原因は `h-full` の1語だった

`h-full` は `height: 100%` です。
親の高さの100%になれ、という指定になります。

問題は**その親の高さが何で決まっているか**でした。順を追うとこうなります。

1. `<li>` は grid item なので、**行の高さまで伸ばされる**
2. その行の高さは `<li>` の中身から決まる
   （ボタン 112px ＋ `mt-3` の 12px ＋ パネル 68px ＝ **約192px**）
3. **`<li>` が192pxに確定したあとで**、ボタンの `height: 100%` が「192px」に解決される
4. 中身が 192 ＋ 12 ＋ 68 ＝ **272px** になり、**80pxぶん `<li>` からはみ出す**

`height: 100%` は親の高さを見ますが、**その親の高さは自分を含めて決まっています。**
ボタンが大きくなる → 親が大きくなる → ボタンがもっと大きくなる、という循環にはならず、
**一度確定した高さを、あとから中身が押し広げる**形で破綻していました。

閉じているときは展開パネルの高さがゼロなので、この計算が起きません。
だから**開いた瞬間にだけ壊れます。**

## なぜ今まで壊れなかったのか

同じ書き方は別のページにもありました。そちらは今も `h-full` のままで、正常に動いています。

```tsx
// src/app/page.tsx — こちらは壊れていない
<Link className="pin-card h-full" href={link.href}>
```

違いは**カードの中身が1つしかない**ことでした。
`<li>` の中に子要素が1つだけなら、`height: 100%` に解決されても押し広げる相手がいません。

**兄弟要素が増えた瞬間に初めて表面化した**わけです。
「今まで動いていた」は「正しかった」ではなかった、という話でもあります。

直したあともこちらは `h-full` のまま残してあります。
壊れていないものを揃えるために触ると、別の壊し方をしそうだったので。

## 直し方は「余りを埋める」に変えること

```diff
- <li>
-   <button className="pin-card h-full">
+ <li className="flex flex-col">
+   <button className="pin-card grow">
```

`grow` は `flex-grow: 1` です。
`flex-basis` が `auto` のままなので、**中身の高さを基準にして、行に余りがあるときだけ伸びます。**

`height: 100%` が「親の高さをよこせ」なのに対して、
`flex-grow` は「余っていたら埋める」という指定です。
カードの高さを揃えたいという目的は同じまま、はみ出しだけが消えました。

`w-full` も要らなくなりました。flex column の子は交差軸へ自動で伸びるためです。

実際のコードにはこの経緯をコメントで残してあります。

```tsx
// li を縦の flex にしてカードは grow で余りを埋める。h-full だと「行の高さ」が
// 親に解決されてしまい、展開部のぶんだけ次の行へはみ出す
<li key={item.id} className={`flex flex-col ${isOpen ? "col-span-full" : ""}`}>
```

## 「指定していないのに伸びる」の正体

引っかかったのは、`<li>` を伸ばす指定を自分では書いていないことでした。

調べると `align-items` の初期値は `stretch` ではなく **`normal`** です。
そのうえで、MDN にこう書かれています。

> For grid items, this keyword leads to a behavior similar to the one of `stretch`,
> except for boxes with an aspect ratio or an intrinsic size where it behaves like `start`.

**grid item では `stretch` に似た振る舞いになる**（アスペクト比や固有サイズを持つ場合は `start`）。
だから何も書かなくても、`<li>` は行の高さまで伸びます。

「既定は `stretch`」と覚えていたのですが、正確には `normal` で、
**レイアウトモードによって意味が変わるキーワード**でした。
grid と flex では結果が似ていても、同じ理屈で動いているわけではないようです。

## 持ち帰り

- **`height: 100%` は親の高さを見る。その親の高さが中身から決まっていると、あとから押し広げられる**
- 高さを揃えたいだけなら `flex-grow`。「余りを埋める」なので、中身より小さくなりません
- **子要素が1つのうちは壊れない。** 動いていたコードが正しかったとは限らない
- `align-items` の初期値は `normal`。**grid item で `stretch` のように振る舞う**が、同じ値ではない
