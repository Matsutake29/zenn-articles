---
title: "SupabaseのRLSは正しいのに誰でも書き換えられた —— UIの無い機能にGRANTだけ残っていた"
emoji: "🔓"
type: "tech"
topics: ["supabase", "postgresql", "rls", "security", "nextjs"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

デモログイン付きのアプリを公開した直後、レビューで**実害1件**が出ました。

プロフィール編集の UI は1つも作っていません。なのに、`update` 権限だけが開いていました。

```sql
-- マイグレーションの1行
grant select, update on public.profiles to authenticated;
```

## RLS は正しく効いていた

ここがこの記事の核心です。**RLS を疑っても見つかりません。**

```sql
-- これは正しい。何も間違っていない
using (auth.uid() = id)
```

デモアカウントは、誰でもボタン1つで**正規のセッション**を手に入れられます。だから `auth.uid() = id` は**成立します**。本人の行なので。

RLS は「本人かどうか」しか見ていませんでした。「その操作をしてよいか」は GRANT の担当です。

| レイヤー | 役割 | 今回の状態 |
|---|---|---|
| **GRANT** | **どの操作ができるか** | `update` が開いていた |
| **RLS** | **どの行に対してできるか** | 正しい |

2枚のうち1枚だけを設計していました。

## 成立経路（UI を経由しない）

1. ログイン画面のデモログインは**誰でも押せる**
2. DevTools からアクセストークンを取り出す
3. Supabase の REST API に直接 `PATCH`

**REST API は UI の有無を知りません。** テーブルと権限があれば呼べます。

### 何が起きるか

| できること | 影響 |
|---|---|
| `username` を変更 | デモページの URL が**恒久的に 404** |
| `display_name` に落書き | 公開ページにそのまま出る |

さらに悪いのは、デモアカウントのリセット処理が `items` しか初期化していなかったことでした。カードの落書きはログインのたびに消えますが、**プロフィールの落書きは誰も消さない**。

## 直し方

```sql
revoke update on public.profiles from authenticated;
```

これだけです。将来プロフィール編集を作るときは、列を絞った形で戻します。

```sql
grant update (display_name, display_name_en, title, avatar_url)
  on public.profiles to authenticated;
```

**PostgreSQL の GRANT は列単位で書けます。** `username` を外しておけば、編集機能を作った後も URL は壊せません。列単位の GRANT はあまり知られていない気がするので、ここは書いておきたかったところです。

## 「機能を作らなかったから安全」ではなかった

最小権限の原則の教科書どおりの穴なのですが、**向きが逆**でした。

権限を広げすぎたのではなく、使う予定だった機能が来なかった。最初に「プロフィール編集を作る」つもりで `update` を配り、機能のほうを後回しにして、権限だけが残った。

**UI が無い＝攻撃面が無い、ではない。** 自分がこの穴を見つけられたのは、外部からの観測とコード内部の監査を別々に回して、両方が独立に同じ1点を指したからでした。片方だけなら「実害は無さそう」で終わっていたと思います。

環境: Supabase（PostgreSQL）/ Next.js 16.3.0。修正は本番に適用済みで、この記事の穴は塞がっています。
