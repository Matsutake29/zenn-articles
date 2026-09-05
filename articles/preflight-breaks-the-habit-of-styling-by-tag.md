---
title: "h1が大きくならないのはバグではなく、タグで見た目を決める癖を折る設計だった"
emoji: "🔤"
type: "tech"
topics: ["tailwindcss", "css", "html", "アクセシビリティ", "初心者"]
published: true
published_at: 2026-09-05 18:00
---
:::message
Tailwind CSS を初めて本格的に使ったときに手が止まった話です。バージョンは v4。
WordPress のテーマを書いてきた側から見ると、最初は「壊れている」ように見えました。
:::

## `h1` を書いたのに大きくならない

見出しを置いたのに、本文と同じ大きさで出ました。
`ul` に黒丸も付きません。

CSS が読み込まれていないのかと思って確認しましたが、読み込まれています。
Tailwind のクラスは効いている。効いていないのは**タグそのものの見た目**でした。

原因は Preflight です。Tailwind が最初に読み込むリセットCSSで、
**ブラウザ既定のスタイルを意図的に消しています。**

## 何をどこまで消しているか

公式ドキュメントを読むと、消しているものが明示されていました。

```css
/* 見出し */
h1, h2, h3, h4, h5, h6 {
  font-size: inherit;
  font-weight: inherit;
}

/* リスト */
ol, ul, menu {
  list-style: none;
}

/* 余白 */
*, ::after, ::before, ::backdrop, ::file-selector-button {
  margin: 0;
  padding: 0;
}
```

ベースは modern-normalize で、その上に Tailwind の判断が乗っている形です。

## 「壊れている」ではなく「決めさせている」

驚いたのは、**理由がドキュメントに書いてある**ことでした。

見出しについては2つ挙げられています。

> - **It helps you avoid accidentally deviating from your type scale**.
> - **In UI development, headings should often be visually de-emphasized**.
>   Making headings unstyled by default means any styling you apply to headings happens
>   consciously and deliberately.

1つめは、ブラウザが割り当てるサイズが**自分のタイプスケールに存在しない**という話です。
`h1` の 2em は、自分が決めたサイズの一覧のどこにも無い。
気づかずに使うと、その1箇所だけスケールの外に出ます。

2つめのほうが面白いと思いました。
**UI では見出しをむしろ目立たなくしたい場面が多い**、という指摘です。
記事の見出しは大きくていいですが、サイドバーの「設定」や、カードの中の小見出しは、
大きいと邪魔になります。

そして最後の一文が設計意図そのものでした。
既定を無スタイルにしておけば、**見出しに当てるスタイルは必ず意識的なものになる。**

余白のリセットにも同じ形の説明があります。

> This makes it harder to accidentally rely on margin values applied by the user-agent
> stylesheet that are not part of your spacing scale.

「うっかり依存しにくくする」。禁止ではなく、**素通りできなくする**という書き方です。

## 何を防いでいるのか

自分なりに読むと、**「大きくしたいから `h1`」を書けなくする**のが狙いだと理解しました。

タグに見た目が付いていると、見た目のためにタグを選ぶ動機が生まれます。
`h1` が自動で大きいから、大きくしたい場所に `h1` を置く。
そのとき文書構造は壊れますが、**見た目は正しいので気づけません。**

Preflight は、その動機を先に断っている。
大きくしたければクラスを書くことになるので、タグを選ぶ理由が見た目から切り離されます。

リセットCSSを「ブラウザ差を吸収する道具」だと思っていたのですが、
Tailwind のそれは**書き手の癖に介入する道具**でもありました。

## ただし、意味まで無傷ではなかった

「タグは意味・クラスは見た目」で整理できた、と思って読み進めたら、
公式がその整理に釘を刺していました。

> Unstyled lists are not announced as lists by VoiceOver. If your content is truly a list but
> you would like to keep it unstyled, add a "list" role to the element

**`list-style: none` にすると、VoiceOver がリストとして読み上げません。**
見た目を消したつもりが、支援技術から見た扱いまで変わっています。

対策も併記されていて、明示的にロールを付ければ戻ります。

```html
<ul role="list">
  <li>One</li>
  <li>Two</li>
  <li>Three</li>
</ul>
```

`<ul>` と書いてあるのに `role="list"` を足す、という見た目には冗長なコードになります。
それでも必要なのは、**見た目の指定が意味の伝わり方に影響してしまう**からです。

見出しのほうは `font-size` と `font-weight` を消しているだけなので、
`<h2>` が見出しであることは変わりません。
**同じ「見た目を消す」でも、リストのほうは意味に届いてしまう**ところが、
きれいに分けられない部分だと思いました。

## 持ち帰り

- **`h1` が大きくならないのは設定ミスではない。** Preflight が意図して消している
- 理由は公式に書かれている。**タイプスケールから外れないため**と、**UI では見出しを弱めたい場面が多いため**
- 既定を無スタイルにすると、スタイルを当てる行為が意識的になる。禁止ではなく素通りさせない設計
- 🚨 **`list-style: none` は VoiceOver でのリスト扱いを外す。** 意味を保ちたいなら `role="list"` を足す。
  「タグは意味・クラスは見た目」という整理は便利ですが、ここだけは重なっていました
