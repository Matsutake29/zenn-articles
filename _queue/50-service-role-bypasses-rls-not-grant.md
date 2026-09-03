---
title: "Supabaseのservice roleはRLSをバイパスするが、GRANTは効く —— 実測したら読み書きの権限が1つも無かった"
emoji: "🔑"
type: "tech"
topics: ["supabase", "postgresql", "rls", "nextjs"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

Cron から外部フィードを取り込む処理を作っていて、書き込みは service role でやる前提でした。

「service role は RLS をバイパスするから、何でも書ける」と思っていました。実測したら、**読み書きの権限が1つも無かった**。

## 訂正が3代目でようやく当たった

最初、AI から「service role は GRANT も RLS も通らない」と説明を受けました。これは不正確でした。

次に「RLS はバイパスするが GRANT は効く。ただし Supabase が既定で service_role に配っているので、結果として書ける」と理解し直しました。自分も AI もそう思っていました。

3代目は実測です。**既定では配られていませんでした。**

## 実測

テーブルの権限は `pg_class` の `relacl` に入っています。

```sql
select unnest(relacl)::text from pg_class where relname = 'feed_entries';
```

| テーブル | postgres | anon | authenticated | **service_role** |
|---|---|---|---|---|
| `feed_entries` | `arwdDxtm` | `rDxtm` | `rDxtm` | **`Dxtm`** |
| `feed_sources` | `arwdDxtm` | `rDxtm` | `arwdDxtm` | **`Dxtm`** |
| `fetch_logs` | `arwdDxtm` | `Dxtm` | `rDxtm` | **`Dxtm`** |

権限の文字はこう読みます。

| 文字 | 権限 |
|---|---|
| `a` | INSERT（append） |
| `r` | SELECT（read） |
| `w` | UPDATE（write） |
| `d` | DELETE |
| `D` | TRUNCATE |
| `x` | REFERENCES |
| `t` | TRIGGER |
| `m` | MAINTAIN |

service_role にあるのは `Dxtm` だけ。**`a` `r` `w` `d` が1つも入っていません。** TRUNCATE はできるのに SELECT ができない、という状態でした。

そして `arwd` が付いている箇所は、**自分で GRANT のマイグレーションに書いたぶんと完全に一致**していました。既定が配るのは `Dxtm` だけで、読み書きは書いたものだけが権限になる。

なお Supabase の公式ドキュメントには、新規テーブルへの既定の権限付与（default privileges）についての記述があり、プロジェクトの作成時期や設定で挙動が違うようです。自分のプロジェクトで実測した結果が上の表で、**他のプロジェクトでも同じとは限りません**。`relacl` を1行引けば分かるので、自分の環境で確かめるのが確実です。

## 「バイパスする」は RLS だけの話だった

RLS のバイパスは**ロール属性**（`BYPASSRLS`）で、GRANT は**権限**です。別の関門でした。

| | 何を見るか | service_role |
|---|---|---|
| RLS | 行ごとのポリシー | バイパスする（ロール属性） |
| GRANT | テーブルごとの操作権限 | **効く**（書いたものだけ） |

RLS を素通りできても、そもそもテーブルに SELECT する権限が無ければ読めません。

対応は明示的に足すだけでした。

```sql
grant select, insert, delete on public.feed_entries to service_role;
grant select, update on public.feed_sources to service_role;
```

## 関数の権限も同じ穴があった

`revoke execute ... from public` で関数を絞ろうとして、service_role の実行権限まで巻き込む可能性に気づきました。確かめるために既存の関数を見ました。

```sql
select proname, proacl from pg_proc where proname = 'swap_item_order';   → NULL
```

**`proacl` が `NULL` は「権限が無い」ではありません。** 「明示的な GRANT / REVOKE が一度も無い＝デフォルトのまま」です。関数のデフォルトは所有者と PUBLIC に EXECUTE なので、この関数は PUBLIC の暗黙の権限だけで動いていました。

つまり `revoke ... from public` すると、service_role も PUBLIC の一員なので巻き込まれます。`grant execute ... to service_role` と対で書く必要がありました。

## 確かめなければ、発覚は Cron を動かしたときだった

開発中は service role キーを使う経路を一度も通りません。機能側の完了条件を全部通しても、この穴は出ない。**発覚するのは本番で Cron が初めて走ったとき**でした。

Supabase の既定が控えめなのは、設計として正しいと思います。読み書きを既定で配らないほうが安全側です。自分の側の問題は、**既定に頼っていた部分を1回も見ていなかった**こと。`relacl` を1行引くだけで分かることでした。

環境: Supabase（PostgreSQL）/ @supabase/supabase-js 2.112.1。`relacl` の値は 2026-08-31 時点の自分のプロジェクトの実測です。
