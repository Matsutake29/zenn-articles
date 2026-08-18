---
title: "OS設定を触らずに、ライト/ダーク両方の画像切り替えを検証する"
emoji: "🌓"
type: "tech"
topics: ["css", "javascript", "darkmode", "devtools", "html"]
published: false
---

## `<picture>` でテーマ追従させると、確認が2倍になる

図やスクリーンショットをテーマに追従させるとき、`<picture>` を使うと CSS なしで書けます。

```html
<picture>
  <source srcset="/img/diagram-dark.png" media="(prefers-color-scheme: dark)">
  <img src="/img/diagram-light.png" alt="構成図">
</picture>
```

ダークなら1枚目、そうでなければ `<img>` の `src`。素直な仕組みです。

面倒なのは確認のほうでした。
**両方の見え方を見るには、両方の状態を作らないといけません。**
画像が5枚あれば10通りです。

## いちばん近い手は DevTools のエミュレーション

Chrome の DevTools には Rendering パネルがあって、
`prefers-color-scheme` を light / dark に固定できます。
普段はこれで足ります。

ただ、これはブラウザの表示側を切り替える機能なので、
**確認したいのが「切り替わったかどうか」だけのときは少し遠回り**でもあります。
パネルを開いて、値を変えて、画面を見て、戻す。

もう1つ、DevTools を開けない相手には使えません。
GitHub の README のように、**サイト側の設定でしかテーマが変わらない場所**もあります。

## DOM 側の `media` を反転させる

コンソールから1行で反転できます。

```js
document.querySelectorAll('picture source').forEach(s => {
  s.media = '(prefers-color-scheme: light)'   // ← 逆側の条件を入れる
})
```

`media` の条件を逆にすると、いま満たされている側が入れ替わります。
ライトで見ているなら、ダーク用の `<source>` が選ばれる状態になります。

環境の設定は何も変えていません。**ページを離れれば元に戻ります。**

## なぜ属性を書き換えるだけで切り替わるのか

`media` は静的な指定に見えるのですが、仕様上は**変更が監視されています。**

HTML Standard には `img` 要素の「relevant mutations」の一覧があり、そこにこう書かれています。

> The element's parent is a `picture` element and a `source` element that is a previous sibling
> has its `srcset`, `sizes`, `media`, `type`, `width` or `height` attributes set, changed, or removed.

**先行する `<source>` の `media` が設定・変更・削除されたとき**も、
対応する `img` に対する関連する変更として扱われます。
つまりブラウザは画像の再選択をやり直します。

書き換えたあとに何も操作しなくても切り替わるのは、そのためでした。
MDN の `<source>` のページを見ても書かれていなくて、仕様まで降りて初めて根拠が取れた部分です。

## ついでに404も分かる

切り替えの確認と同時に、**ファイルが生きているか**も見られます。

```js
document.querySelectorAll('picture img').forEach(img => {
  console.log(img.currentSrc, img.naturalWidth)
})
```

- `currentSrc` … ブラウザが**実際にどれを選んだか**
- `naturalWidth` … **0 なら読み込めていない**（パス違い・404）

この2つを並べて見ると、「切り替わったか」と「ファイルがあるか」が1回で確認できます。

テーマ追従の実装でありがちなのは、**片方のパスだけ間違っている**ケースです。
普段使っているテーマのほうは正しく、逆側だけ 404 になっている。
自分の環境では気づけないので、切り替えて `naturalWidth` を見るまで残り続けます。

## 使い分け

| やりたいこと | 手段 |
|---|---|
| 実際の見た目を確認する・スクリーンショットを撮る | OS または DevTools でテーマを切り替える |
| 切り替わるか・ファイルが生きているかを確認する | **コンソールから `media` を反転** |

見た目そのものを評価したいときは、エミュレーションでも OS 設定でも、
とにかく**その状態でレンダリングされたもの**を見るのが確実です。

一方、確認したいのが「配線が合っているか」だけなら、
`media` の反転と `naturalWidth` のほうが速いし、環境を触りません。
`<picture>` の数が増えるほど差が出ます。

## 持ち帰り

- `<source>` の `media` は**動的に書き換えるとブラウザが再選択する**（HTML Standard の relevant mutations）
- コンソールから1行で両方の状態を作れる。**環境の設定は変わらない**
- `currentSrc` と `naturalWidth` を並べると、切り替えと404を同時に確認できる
- 見た目の評価はエミュレーション、配線の確認は DOM 反転、と分けると楽でした
