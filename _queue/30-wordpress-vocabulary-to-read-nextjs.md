---
title: "WordPress の語彙で Next.js（App Router）を読む"
emoji: "🗺️"
type: "tech"
topics: ["nextjs", "wordpress", "react", "approuter"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

WordPressの受託でコーディングを2年やってきました。テーマを触って、テンプレート階層に沿ってファイルを置いて、
ループを回して記事を出す。そういう作り方が手に馴染んでいます。

その状態でNext.jsのApp Routerを触り始めたとき、用語の多さで身構えました。
ルートレイアウト、props、動的ルート、メタデータ。全部が初めて聞く言葉に見えました。

実際に書き始めたら、**名前が違うだけで手が既に覚えていたもの**がかなりありました。
自分用に作った対応表を置いておきます。

## 対応表

| Next.js | WordPress | 気づいたこと |
|---|---|---|
| ルートレイアウト `app/layout.tsx` | `header.php` + `footer.php` | 共有UIが無くても必須。`<html>` と `<body>` を出す唯一の場所だから |
| `{children}` | `the_content()` | 「中身がここに入る」という穴 |
| props | ショートコードの属性 `[button color="red"]` | `properties` の略。PHPの `$atts` に近い |
| `children`（props） | ショートコードで囲んだ中身 `$content` | 自分では渡さないprops |
| 動的ルート `app/[username]/page.tsx` | `single.php` | 1枚のテンプレートで受けて出し分ける |
| `cards.map((card) => ...)` | `foreach ($cards as $card)` | `as $card` が `(card) =>` に当たる |
| `metadata` | `wp_head()` ＋ 個別記事のSEO上書き | layoutに書けば全体、pageに書けば個別（pageが勝つ） |
| ファイル配置＝URL構造 | テンプレート階層 | どちらも規約でルーティングする |

一番効いたのは一番下の行でした。
**どちらも「ファイルをどこに置くか」でURLが決まる**という思想が同じです。

`single.php` を置けば個別記事のURLがそれを使う。`app/[username]/page.tsx` を置けば `/matsutake` がそれを使う。
どちらもルーティングの設定ファイルを書きません。ここの発想が近いです。

## `map` で最初に詰まったところ

対応表の中で、自分が実際に手を止めたのは `map` の行でした。

書いていたのはこういうコードです。

```tsx
<ul>
  {cards.map((card) => (
    <li key={card.url}>
      <a href={card.url}>{card.title}</a>
    </li>
  ))}
</ul>
```

ここで引っかかったのが、`{card.url}` の部分です。
配列の名前は `cards` なのに、なぜ中では `card` になるのか。

PHPで書くとこうです。

```php
<ul>
  <?php foreach ( $cards as $card ) : ?>
    <li><a href="<?php echo $card['url']; ?>"><?php echo $card['title']; ?></a></li>
  <?php endforeach; ?>
</ul>
```

`as $card` です。**1個ずつ受け取るときの名前を、その場で決めている。**
`(card) =>` が同じことをしていました。2年間書いてきたものと同じでした。

配列と、その中の1個を区別する。文字にすると当たり前なのですが、
`map` という見慣れない名前が付いているせいで、別の概念だと思い込んでいました。

## ただし `foreach` と `map` は同じではない

対応表は「近い」であって「同じ」ではないので、ズレるところを書いておきます。

`foreach` は**出力する**構文で、`map` は**配列を返す**関数です。
PHPで正確に対応するのは `array_map()` のほうになります。

```php
$items = array_map( fn( $card ) => "<li>{$card['title']}</li>", $cards );
echo implode( '', $items );
```

JSXの場合、この `echo implode()` に当たる部分が要りません。
**JSXは配列を渡されると、中の要素を順に並べて描画してくれる**からです。
だから `map` の返り値をそのまま `{}` の中に置ける。

この違いは、慣れてくると使い勝手として出てきます。
`map` は返り値があるので、こう繋げられます。

```tsx
{cards
  .filter((card) => card.published)
  .sort((a, b) => a.order - b.order)
  .map((card) => (
    <li key={card.url}>{card.title}</li>
  ))}
```

`foreach` ではこう書けません。出力してしまうので、繋ぐ先がない。
PHPで同じことをするなら `array_filter` → `usort` → `array_map` と関数を並べることになります。

ちなみに `for` はJSXの `{}` の中に書けません。
`{}` の中に置けるのは**式**で、`for` は**文**だからです。
`map` を使うのはおしゃれな書き方だからではなく、構文上そうなっているだけでした。

## 他にもズレるところ

雑に対応させると事故りそうなところを、いくつか。

**`{children}` と `the_content()`**

`{children}` は**値**です。ReactNodeという型の値が変数に入っていて、それを置いている。
`the_content()` は**出力する関数**で、呼んだ時点でechoされます。
値として受け取りたい場合はWordPress側にも `get_the_content()` があるので、
そちらのほうが対応としては近いです。

「中身がここに入る穴」という感覚は同じですが、値か関数かは違います。

**動的ルートと `single.php`**

どちらも「1枚のテンプレートで複数のページを出す」点は同じです。
ただし解決のタイミングが違います。

`single.php` はリクエストが来てからクエリを見て決まります。
Next.jsの動的ルートは、設定によってビルド時に決まることもリクエスト時に決まることもあります。
ここは同じつもりで扱うと、キャッシュの挙動で戸惑うことになりそうです。

## 身構えていたのは、名前のほうだった

App Routerを触る前に感じていた「全部が新しい概念だ」という抵抗感は、
実際に書いてみたら**名前に対する抵抗**でした。

やっていることは、テンプレートを置いて、共通部分を切り出して、配列を回して出す。
WordPressのテーマ制作でやってきたことと、かなり重なっていました。

もちろん違うところもあります。ただ、違いを確認するのは対応が付いてからでも遅くない。
最初に「全部わからない」と思って止まっていた時間のほうが、実際には長かったです。

同じようにWeb制作からフロントエンドに寄ろうとしている人には、
**まず自分の語彙に翻訳してみる**のが入口として楽かもしれません。想定読者は少し前の自分ひとりです。
