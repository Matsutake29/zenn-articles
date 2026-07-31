---
title: "FLOCSSでSCSSを30件書いてきた構成と、なぜそのルールにしたか"
emoji: "🗂️"
type: "tech"
topics: ["sass", "css", "flocss", "wordpress", "設計"]
published: false
---

<!-- 【公開前チェック】

     ■ 現行テンプレート（wp-theme-flocss-base）と突き合わせ済み（2026-07-29）
     - コンパイルは npm run css（Live Sass Compiler は使用しない運用に変更済み）
     - url() はルート相対パスを基本とする方針に変更済み
     - mixin ファイル名は _mixins.scss（複数形）

     ■ 案件が特定できる情報は書かない
-->

WordPressの受託でコーディングをしていて、SCSSの構成はFLOCSSベースで固定しています。
案件ごとに考え直すのをやめて、テンプレートとして持っている形です。

構成そのものは珍しくないと思うので、**なぜそのルールにしたか**のほうを中心に書きます。
ルールの理由が説明できるかどうかが、テンプレートを育てるうえで効いてくるので。

## ディレクトリ構成

```
assets/scss/
├── style.scss              ← エントリーポイント
├── foundation/
│   ├── _variables.scss
│   ├── _mixins.scss
│   ├── _reset.scss
│   └── _base.scss
├── layout/
│   ├── _header.scss
│   └── _footer.scss
└── object/
    ├── component/          ← 使い回す最小単位（ボタン・パンくず等）
    ├── project/            ← ページ固有のかたまり
    └── utility/
```

FLOCSSそのままです。接頭辞も `.c-` `.p-` `.u-` で揃えています。

## エントリーポイントは1ファイルに集約する

`style.scss` で全部を `@use` します。

```scss
@charset "UTF-8";

// Foundation
@use "foundation/variables";
@use "foundation/mixins";
@use "foundation/reset";
@use "foundation/base";

// Layout
@use "layout/header";
@use "layout/footer";

// Object / Component
@use "object/component/btn";
@use "object/component/breadcrumb";
@use "object/component/pagination";

// Object / Project
@use "object/project/top";
@use "object/project/contact";

// Object / Utility
@use "object/utility/utility";
```

読み込み順がそのまま詳細度の前提になるので、**1ファイルを見れば全体の構造が分かる**状態を保っています。

## ページ別フォルダと `_index.scss`

`object/project/` は、ページが増えると平たく増えていきます。
`_top.scss` `_about.scss` `_contact.scss` という具合に。
1ページのCSSが長くなると、その1ファイルが数百行になる。

なので**ページごとにフォルダを切って**、中で分割しています。

```
object/project/
└── top/
    ├── _index.scss     ← @forward でまとめる
    ├── _hero.scss
    ├── _feature.scss
    └── _news.scss
```

```scss
// _index.scss
@forward "hero";
@forward "feature";
@forward "news";
```

こうすると `style.scss` 側は1行のままです。

```scss
@use "object/project/top";
```

新しいセクションを足すときは `_index.scss` に `@forward` を1行足すだけ。
**エントリーポイントを触らずに済む**のが利点です。

`@use` と `@forward` の使い分けは、

- `@use` … 使う側（名前空間が付く）
- `@forward` … まとめて再公開する側（`_index.scss` 専用）

と割り切っています。`@import` は非推奨になって久しいので使っていません。

## 名前空間を短く付ける

変数とmixinは名前空間付きで参照します。

```scss
@use "../../foundation/variables" as v;
@use "../../foundation/mixins" as m;

.c-btn {
  background-color: v.$color-accent;
  color: v.$color-white;

  @include m.hover {
    opacity: 0.8;
  }
}
```

`as v` `as m` と1文字に潰しているのは、毎行に出てくるからです。
`variables.$color-accent` と書くと長すぎて、値のほうが読みにくくなります。

名前空間を消す（`as *`）ことも考えましたが、**どこから来た変数か分からなくなる**のでやめました。
案件を引き継ぐ立場で読むと、`$color-accent` がどのファイル由来かを探すことになるので。

## ネストのルール——`&__` の省略は禁止

これがいちばん語れるルールです。

SCSSでは、こう書けます。

```scss
// 禁止している書き方
.p-hero {
  &__title { ... }
  &__body { ... }
}
```

書くのは速いです。でも**禁止しています。**

理由は単純で、**grepで検索できなくなる**から。

`.p-hero__title` の実装を探したいとき、この書き方だと困ります。
ファイル内に `p-hero__title` という文字列が存在しないからです。
`&__title` を探すには、まず親の `.p-hero` を見つけて、そこから読み下す必要があります。

自分で書いて自分で保守するなら困りません。**引き継ぎや修正依頼で、他人（数ヶ月後の自分を含む）が該当箇所を探す場面**で効いてきます。

なので、こう書きます。

```scss
.p-hero { ... }
.p-hero__title { ... }
.p-hero__body { ... }
```

書く速度と、探す速度のトレードオフです。**書くのは1回、探すのは何回もある**ので、探す側に寄せました。

### メディアクエリのネストはOK

一方で、メディアクエリはネストします。

```scss
.p-hero__title {
  font-size: 40px;

  @include m.mq-sm {
    font-size: 28px;
  }
}
```

こちらは「同じセレクタの値違い」なので、離すと**片方だけ直す事故**が起きます。近くにあったほうが安全です。

同じ「ネスト」でも、**セレクタを組み立てるネストは禁止、条件を入れ子にするネストは推奨**という線引きにしています。

## mixin はメディアクエリとホバーだけ

mixinを増やしすぎると、それ自体が覚えるコストになります。実質2つだけ持っています。

```scss
// デスクトップファースト（max-width）
@mixin mq-lg {
  @media screen and (max-width: #{v.$bp-lg}) { @content; }
}

@mixin mq-sm {
  @media screen and (max-width: #{v.$bp-sm}) { @content; }
}

// ホバーはPCのみ
@mixin hover {
  @media (hover: hover) and (pointer: fine) {
    &:hover { @content; }
  }
}
```

`hover` mixin は、**タッチデバイスでホバーが残る問題**への対処です。スマホでタップした後に色が変わったままになるやつ。
`@media (hover: hover)` で囲んでおけば起きません。

余談ですが、最近Tailwindを触ったら `hover:` が自動で `@media (hover: hover)` に包まれていました。
**同じ問題に対して同じ対処をしていた**と分かって、少し嬉しかったです。

デスクトップファースト（`max-width`）なのは、受託でカンプがPCから来るからです。
モバイルファーストが原則として正しいのは理解しています。
ただ**カンプがPC基準で来る以上、PCの値を基準に書いたほうが実装とカンプが一致します。**

## url() はルート相対パスにする

画像パスの書き方は、以前は「コンパイル後のCSSの位置を基準にした相対パス」で書いていました。

いまはルート相対（`/` 始まり）を基本にしています。

```scss
background-image: url("/wp-content/themes/{theme}/assets/img/bg.jpg");
```

相対パスだと、**SCSSファイルの位置とCSSの出力先の関係を毎回考える**ことになります。パーシャルを別階層に移動すると壊れる。
ルート相対なら、ファイルがどこにあっても同じ文字列で通ります。

WordPressのテーマだとパスが長くなるのが難点ですが、壊れないほうを取りました。

## コンパイルは npm script に寄せた

以前はエディタの拡張（Live Sass Compiler）で、`.css` と `.min.css` を両方生成していました。

いまは `npm run css` に統一しています。理由は**エディタに依存しない**ことです。

- 拡張の設定は `.vscode/settings.json` に入るので、環境が変わると再現しない
- AIにコード修正を任せるとき、**コンパイルまで含めて実行させられる**

2つ目が大きくて、SCSSを直したあと自動でコンパイルまで通せるようになりました。
拡張の保存トリガーだと、AIが書いたファイルでは発火しないので。

## 構成そのものより、理由を持っているかどうか

FLOCSS自体は10年近く前からある考え方で、構成を真似るだけなら記事はいくらでもあります。

自分がテンプレートとして固定してよかったと思うのは、
**案件ごとに構成を考え直す時間がゼロになった**ことより、
**「なぜこの構成か」を毎回説明できるようになった**ことのほうでした。

制作会社経由の案件だと、引き継ぎ時に構成の説明を求められることがあります。
「FLOCSSです」だけだと会話が終わります。
「`&__` を禁止しているのはgrepのためです」まで言えると、相手も自分たちのルールを話してくれる。
設計の話ができる相手だと認識されると、その後の進め方が変わります。

## まとめ

- エントリーポイント1ファイルに `@use` を集約し、構造を1画面で見せる
- ページ別フォルダ + `_index.scss` の `@forward` で、エントリーポイントを触らずに済ませる
- 名前空間は `as v` `as m` と短く。ただし**消さない**（出自が分からなくなる）
- **`&__` の省略は禁止**。書く速度より探す速度を取る
- **メディアクエリのネストはOK**。離すと片方だけ直す事故が起きる
- mixinは増やさない。実質「メディアクエリ2つ + ホバー1つ」で足りている
- `url()` はルート相対。ファイルの移動で壊れない
