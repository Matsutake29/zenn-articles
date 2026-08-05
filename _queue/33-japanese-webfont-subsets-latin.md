---
title: 'next/fontで日本語フォントを使うとき、subsetsに"japanese"は書けない'
emoji: "🔤"
type: "tech"
topics: ["nextjs", "googlefonts", "webフォント", "typescript"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

Next.jsで日本語のサイトを作っていて、Noto Sans JPをWebフォントで読み込もうとしたら詰まりました。

先に結論を書きます。**`subsets: ["latin"]` と書くと日本語が表示されます。**

日本語フォントなのに `latin` を指定する。矛盾しているように見えるのですが、
理由が分かると納得できたので、詰まった順に書いていきます。

## 1. `subsets: ["japanese"]` は書けない

`next/font/google` で読み込むとき、素直に考えるとこう書きたくなります。

```tsx
const notoSansJP = Noto_Sans_JP({
  subsets: ["japanese"],   // ← これは書けない
});
```

型エラーになります。型定義を見に行ったら、こうなっていました。

```ts
export declare function Noto_Sans_JP<...>(options?: {
    weight?: '100' | ... | '900' | 'variable' | Array<...>;
    style?: 'normal' | Array<'normal'>;
    ...
    subsets?: Array<'cyrillic' | 'latin' | 'latin-ext' | 'vietnamese'>;
}): ...
```

指定できるのは **`cyrillic` / `latin` / `latin-ext` / `vietnamese`** の4つだけです。

日本語フォントの `Noto_Sans_JP` に、日本語がありません。
キリル文字とベトナム語は選べるのに。ここで一度手が止まりました。

## 2. かといって省略するとビルドが落ちる

指定できないなら書かなければいい、と思って省略したらビルドが落ちました。

```
Preload is enabled but no subsets were specified for font Noto Sans JP
```

**指定できないのに、省略もできない。** ここが一番わけが分からなかったところです。

## 3. 解は2つある

調べたら、抜け道は2つありました。

**(a) `subsets: ["latin"]` を指定する**

```tsx
const notoSansJP = Noto_Sans_JP({
  variable: "--f-jp",
  subsets: ["latin"],
  display: "swap",
});
```

これでビルドが通り、**日本語も普通に表示されます**。自分はこちらを選びました。

**(b) `preload: false` にする**

実は、Next.jsの公式エラーページが案内しているのはこちらです。
[Missing specified subset for a `next/font/google` font](https://nextjs.org/docs/messages/google-fonts-missing-subsets) に、
**日本語フォントを例にしたコードがそのまま載っています**。

```js
const notoSansJapanese = Noto_Sans_JP({
  weight: '400',
  preload: false,
})
```

「意図したサブセットをpreloadできない場合は、preloadを無効にできます」という案内です。

自分は(a)を選びましたが、これは英数字（ラテン文字）の表示を早くしたかったからで、
「(b)が間違い」ではありません。preloadを切ると `font-display` の既定が `swap` になります。

どちらにせよ、矛盾しているように見えたのは
`subsets` が何を制御しているかを取り違えていたからでした。

## 4. `subsets` が決めているのは「preloadするもの」

`subsets` は「このフォントで使う文字の範囲」を宣言するものだと思っていました。
実際には**どのサブセットを preload するか**を決めるオプションでした。

エラーメッセージが `Preload is enabled but no subsets were specified` と言っていたのは、
そのままの意味だったわけです。preloadを有効にしているのに、何をpreloadするか指定されていない、と。

では日本語のグリフはどこから来るのか。**ブラウザが必要になった時点で取りに行っています。**

Google Fontsが返すCSSを実際に見てみました。Noto Sans JP（weight 400）を取得したら、
`@font-face` が **124個**入っていて、それぞれに別々の `unicode-range` が付いていました。
1つのフォントが、文字の範囲ごとに124分割されて配信されています。

`unicode-range` の挙動は仕様にこう書かれています。

> If the page doesn't use any character in this range, the font is not downloaded; if it uses at least one, the whole font is downloaded.
> （[MDN - unicode-range](https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face/unicode-range)）

範囲内の文字が1つも使われていなければダウンロードされない。1つでも使われていれば、
**そのファイルが丸ごと**ダウンロードされる。

つまり日本語のダウンロードは preload ではなく**遅延で取得される**設計になっていて、
`subsets` の指定対象に日本語が出てこないのはそのためでした。

「日本語Webフォントはファイルが数MBある」という話を聞いていたので、
そのまま全部落ちてくるものだと思っていました。実際には全グリフを1ファイルに抱えた場合の数字で、
配信されるのは**使った文字が含まれるサブセットだけ**です。

「使った文字のぶんだけ」ではない、というのが自分の理解の甘かったところでした。
サブセット単位なので、1文字使えばそのファイル1つぶんは丸ごと落ちてきます。
実測したところ1ファイルは16〜42KBでした。

## 5. なぜ `japanese` が無いのか、経緯が残っていた

ここまで分かっても、「じゃあ最初から `japanese` を指定できるようにしておけばいいのでは」
という疑問が残りました。

調べたら、**一度は指定できたようです。** 除外したPRが見つかりました。

> Currently there's a bug when selecting Chinese, Japanese or Korean (CJK) as subsets.
> It actually doesn't work, nothing preloads.
> （[vercel/next.js #44594](https://github.com/vercel/next.js/pull/44594)）

指定はできるのに、preloadは実際には動いていなかった。そのうえで、こう書かれていました。

> they contain so many glyphs that each font-family is split up in 100+ font files.
> It doesn't make sense to preload all of them.

グリフが多すぎて100個以上のファイルに分割されるので、全部preloadする意味がない。
だからCJKのサブセットを型定義から外した、という経緯でした。

自分が数えた124個と、この「100+ font files」が同じものを指しています。
**選べないのは実装漏れではなく、選んでも意味が無いから外された**ということでした。

なお `japanese` を指定できるようにしてほしい、という要望自体は
[Discussion #86336](https://github.com/vercel/next.js/discussions/86336) に今も残っています。

## 6. `weight` は省略から試すのが早い

`weight` も最初は指定していたのですが、省略できました。

可変フォント（variable font）の場合、ウェイトが連続的に変えられるので、
ファイルは1つのままで済みます。型定義でも `weight` は optional で、`'variable'` という値を持っています。

Noto Sans JP も Inter も可変フォントだったので、省略してビルドが通りました。

落ちたら `["400", "700"]` のように使うぶんだけ指定する。この順で試すのが手数が少ないと思います。
先に細かく指定して「なぜファイルが増えるのか」を調べるより早いです。

## 7. もう一つの罠: `font-family` の順序

フォントを読み込んだあと、CSS変数で当てています。

```css
@theme inline {
  --font-sans: var(--f-en), var(--f-jp), sans-serif;
}
```

**欧文を先に書きます。**

日本語フォントは、日本語だけでなく**ラテン文字のグリフも持っています**。
順序を逆にすると、英数字まで日本語フォントの字形でレンダリングされます。

数字やアルファベットが少し間延びして見える、という形で出てきます。
気づきにくいので、書く順序で先に潰しておくのが楽でした。

## まとめ

- `subsets` に `"japanese"` は指定できない（型に無い）
- 省略するとビルドが落ちる
- 解は2つ。`["latin"]` を指定するか、公式が案内している `preload: false` にするか
- `subsets` が決めているのは preload するサブセット。日本語グリフは `unicode-range` により、
  使った文字を含むサブセット単位でダウンロードされる
- CJKが型定義から外されたのは、100個以上に分割されていて全部preloadする意味が無いから
- `weight` は可変フォントなら省略できる
- `font-family` は欧文を先に書く

自分が詰まったのは、`subsets` を「使う文字の範囲の宣言」だと思い込んでいたからでした。
実際には preload の対象を決めるオプションで、エラーメッセージにも `Preload is enabled` と
書いてあった。オプションの名前から意味を推測して、メッセージのほうを読んでいませんでした。

そして「なぜ選べないのか」は、公式リポジトリのPRに理由が残っていました。
仕様がおかしいと思ったときに経緯を探すと、だいたい誰かが同じことを考えたあとが見つかる、
というのも今回の収穫です。
