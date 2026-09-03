---
title: "ER図のために置いたuniqueが、Supabaseの入れ子selectの返り値を配列からオブジェクトに変えていた"
emoji: "🧬"
type: "tech"
topics: ["supabase", "postgrest", "typescript", "postgresql"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。外部フィードの記事をカードに表示する機能の話です。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

入れ子の select を書いたら、`feed_sources` が**配列ではなくオブジェクト**で返ってきました。

配列を予想して型を書こうとしていたので、手が止まりました。

## テーブル定義と select

```sql
create table public.feed_sources (
  id uuid primary key default gen_random_uuid(),
  item_id uuid not null unique references public.items(id) on delete cascade,
  ...
);
```

```ts
.select(`
  id, type, title, description, url, sort_order,
  feed_sources ( max_entries, last_fetched_at,
    feed_entries ( title, url, published_at, thumbnail_url ) )
`)
```

返ってきたもの:

```json
"feed_sources": { "max_entries": 3, "feed_entries": [ ... ], "last_fetched_at": null }
```

`feed_entries` は配列なのに、`feed_sources` はオブジェクトです。

## PostgREST は外部キーの unique を見て、1対1と判定していた

PostgREST の Resource Embedding のドキュメントに、1対1の検出条件が書かれています。

> When the foreign key is also a primary key. Or when the foreign key has a unique constraint.

この条件に当てはまると、埋め込んだリソースは配列ではなく単一の JSON オブジェクトで返ります（PostgREST v10 から）。

`feed_sources.item_id` に付けた `unique` が、まさにこれでした。

| `unique` | レスポンスの形 | 表示側の書き方 |
|---|---|---|
| **あり** | `feed_sources: { ... } \| null` | `item.feed_sources?.feed_entries` |
| なし | `feed_sources: [ { ... } ]` | `item.feed_sources[0].feed_entries` |

紐づく `feed_sources` が無いカード（外部フィードではないカード）は `null` で返ります。型に `| null` が要る。

## その unique は、ER図のために置いたものだった

`item_id` に `unique` を付けた理由として、自分が手順書に書いていたのは「**ER図の1対1が守られない**」だけでした。2枚目が刺さらないようにする制約、という理解です。

実際には、**フロントエンド側のコードの書き方まで決めていました**。この制約を忘れていたら、表示側は `item.feed_sources[0]` と書くことになっていた。DB の制約が、DB の中だけの話で終わっていない。

制約を1つ書くとき、それが何を決めるかを1つしか見ていなかった、というのが自分の反省でした。

## 観測したのは「unique あり」の側だけ

正直に書いておくと、自分の環境で観測したのは「`unique` ありで `{ ... }` が返った」ことだけです。`unique` を外せば `[ { ... } ]` になる、というのは本番テーブルなので消して確かめていません。

因果のほうは、上に引用した PostgREST のドキュメントが根拠です。最初は「PostgREST は外部キーの制約を見て決めている」という説明を AI から受けて、観測1件がそれを裏付けたように見えていたのですが、**観測されたのは同時発生だけで因果ではない**、と途中で指摘を受けました。ドキュメントで裏を取ってから書いています。

## 対になる話

同じ日に、同じ入れ子 select で、逆向きのことも踏みました。`feed_entries` に `order` を書いていないのに期待どおりの順で返ってきて、それは保証ではなかった、という話です。

こちらは**書いたもの**（`unique`）が効いた話で、あちらは**書かなかったもの**（`order`）が保証を作らなかった話でした。

環境: Supabase（PostgREST v10 以降）/ @supabase/supabase-js 2.112.1 / Next.js 16.3.0。観測は 2026-08-25。
