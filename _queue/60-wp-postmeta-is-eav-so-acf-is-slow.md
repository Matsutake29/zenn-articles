---
title: "wp_postmeta は EAV だった。ACF を盛ると重い理由が、自作アプリの1カラムで繋がった"
emoji: "🗄"
type: "tech"
topics: ["wordpress", "database", "acf", "sql"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

カードの並び順を保存するために、テーブルに1行足しました。

```sql
sort_order int not null default 0
```

これを書いた手が止まりました。
WordPress を7年触ってきて「ACF でカスタムフィールドを増やすと重くなる」という体感がありましたが、理由を考えたことがありませんでした。
**足したこの1行が、その理由のちょうど反対側**でした。

## wp_postmeta は縦に持つ

WordPress のカスタムフィールドは、投稿テーブルにカラムが増えるわけではありません。
`wp_postmeta` という別のテーブルに、1フィールドが1行として積まれます。

```text
meta_id | post_id | meta_key       | meta_value
--------+---------+----------------+------------
    101 |      12 | price          | 3000
    102 |      12 | release_date   | 2026-09-11
    103 |      12 | is_featured    | 1
```

カラムは4つだけです。
「どの投稿の」「なんという名前の」「値」を、行を増やすことで表現しています。
この形は EAV（Entity-Attribute-Value）と呼ばれていて、WordPress の文脈でも一般的に使われている呼び方でした。

強みは分かりやすいです。
**プラグインがカラムを追加せずに何でも保存できる**。
テーブル定義を変えずに済むので、他人のサイトに入るプラグインの仕組みとして理にかなっています。
ACF が自由にフィールドを増やせるのも、置き場所がこの形だからです。

## 縦に持つと、絞り込みと並べ替えが重くなる

代わりに失うものがあります。

まず、条件を足すほど JOIN が増えます。
「価格が3000円以上」「かつ特集フラグが立っている」を探すとき、`wp_postmeta` は1行に1フィールドしか持っていないので、**条件の数だけ同じテーブルを結合し直す**ことになります。
カラムなら `WHERE price >= 3000 AND is_featured = 1` で済むところです。

次に、`meta_value` の型が `longtext` です。
`3000` も `2026-09-11` も文字列として入っています。
数値として比較するには `CAST` が要りますが、**変換をかけた時点でインデックスが効かなくなります**。

`meta_key` 側にも制約がありました。
索引は張られているものの、utf8mb4 環境では先頭191文字までの部分索引です。
`varchar(255)` を丸ごと索引にできない事情があって、そうなっています（[WordPress Trac #53958](https://core.trac.wordpress.org/ticket/53958)）。

ACF で繰り返しフィールドやグループを作ると、この行がさらに増えます。
フィールド1つにつき、値の行と、フィールド定義を指す `_` 始まりの行がペアで入るためです。
**フィールドを盛るほど行が増え、絞り込みは JOIN が増える。
** 重くなる体感には、構造の側に理由がありました。

## 自分のテーブルでは、横に持てた

同じものを自作アプリ側で書くと、こうなります。

```sql
create table public.items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  type text not null check (type in ('link', 'note', 'feed')),
  title text not null,
  sort_order int not null default 0,
  visible boolean not null default true,
  ...
);

create index items_user_id_sort_order_idx on public.items (user_id, sort_order);
```

`sort_order` は `int` です。
文字列ではないので `CAST` が要らず、`(user_id, sort_order)` の複合インデックスがそのまま効きます。
「このユーザーのカードを並び順に取り出す」が、インデックスを辿るだけの操作になりました。

WordPress で同じことをするなら、並び順は `wp_postmeta` の1行になります。
取り出すには JOIN して、文字列を数値に直して、並べ替える。
**やりたいことは同じなのに、通る道の長さが違います。
**

## 「外部キー」と書こうとして、止まった

この記事を書くとき、WordPress 側の関係を「`wp_posts.post_author` が `wp_users.ID` への外部キー」と書きかけました。
念のため調べてもらったら、違いました。

**WordPress は FOREIGN KEY 制約を張っていません。**
MyISAM が長く使われていた経緯があり、InnoDB が既定になった今も制約は入っていません。
`post_author` は設計上の参照ではありますが、**データベースが守ってくれる関係ではない**ということです。
だからユーザーを消しても、その投稿はエラーにならずに残ります。

7年使っていて、ここを勘違いしていました。
毎日触っていることと、構造を知っていることは別でした。

## 遅いのではなく、交換していた

書き終えて思ったのは、「WordPress は遅い」という話ではないということです。

EAV は、**スキーマを固定しない代わりに、絞り込みと並べ替えのコストを払う**形です。
誰がどんなプラグインを入れるか分からない CMS が、この形を選ぶのは筋が通っています。
逆に、自分で作るアプリは**何を持つか自分で決められる**ので、カラムにできます。

同じデータを置く場所が2つあって、置き方が違う。
どちらが正しいかではなく、何を固定できるかの差でした。

## 実務の体感に、名前がついた

「ACF を盛ると重い」は、7年ぶんの体感として持っていました。
そこに `CREATE TABLE` を1回書いたら、体感の下にあった構造が見えました。

WordPress しかやってこなかったことを弱みのように感じていた時期がありますが、この繋がり方をするなら、**読み替えの材料としてはむしろ多いほう**だと思っています。
触ってきた量そのものは変わらないので、あとは反対側を1回書いてみるかどうかでした。
