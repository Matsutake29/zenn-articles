---
title: ".htaccessではRewriteRuleがRedirectMatchより先に動く —— 通説と逆だった"
emoji: "🔀"
type: "tech"
topics: ["apache", "htaccess", "modrewrite", "wordpress"]
published: false
---

既存の `.htaccess` に**リダイレクトを1行足す**だけの作業をしました。足す前に「どっちが先に評価されるのか」を確かめたら、広く言われている順序と逆でした。

```apache
# 既にあった2つ
RedirectMatch 404 /\.git                                                # mod_alias
RewriteEngine On
RewriteRule ^life_builder/?(.*)$ https://blog.example.com/$1 [R=301,L]  # mod_rewrite

# ここに1行足したい
RewriteRule ^$ https://sub.example.com/ [R=302,L]
```

## 通説「mod_alias が先」は間違いではない。適用範囲が違う

「`Redirect`（mod_alias）は `RewriteRule`（mod_rewrite）より先に処理される」という説明はよく見ます。これ自体は正しいのですが、**サーバー設定（`httpd.conf` / VirtualHost）に書いた `Redirect` の話**です。

`.htaccess` に書いた `RedirectMatch` には当てはまりませんでした。

## ソースで確定した順序

Apache httpd 2.4.x のソース（GitHub の `apache/httpd`、`2.4.x` ブランチ）を読みました。

まず mod_alias（`modules/mappers/mod_alias.c`）のフック登録です。

```c
static void register_hooks(apr_pool_t *p)
{
    ...
    ap_hook_translate_name(translate_alias_redir,NULL,aszSucc,APR_HOOK_MIDDLE);
    ap_hook_fixups(fixup_redir,NULL,NULL,APR_HOOK_MIDDLE);
}
```

2つのフックがあって、それぞれ見ている設定が違います。

| 関数 | フェーズ | 参照する Redirect |
|---|---|---|
| `translate_alias_redir` | translate_name（早い） | `serverconf->redirects`＝**サーバー設定** |
| `fixup_redir` | fixups（遅い） | `dirconf->redirects`＝**`.htaccess` / `<Directory>`** |

通説が正しいのは上の行です。`.htaccess` の `RedirectMatch` は下の行、**fixups フェーズ**で処理されます。

次に mod_rewrite（`modules/mappers/mod_rewrite.c`）です。

```c
    /* allow to change the uri before mod_proxy takes over it */
    ap_hook_translate_name(hook_uri2file, NULL, aszModProxy, APR_HOOK_FIRST);
    /* fixup before mod_proxy so that a [P] URL gets fixed up there */
    ap_hook_fixups(hook_fixup, NULL, aszModProxy, APR_HOOK_FIRST);
```

`.htaccess` の `RewriteRule` は `hook_fixup` が処理し、**同じ fixups フェーズで `APR_HOOK_FIRST`** です。

| fixups 内の順序 | モジュール | 関数 |
|---|---|---|
| `APR_HOOK_FIRST` | **mod_rewrite** | `hook_fixup` |
| `APR_HOOK_MIDDLE` | mod_alias | `fixup_redir` |

### そして途中で打ち切られる

fixups フックは、`OK` / `DECLINED` 以外の値が返ると**そこで後続の呼び出しが止まります**。mod_rewrite の `hook_fixup` は、外部リダイレクトを起こすルールに当たるとステータスコードをそのまま返します。

```c
        if (ACTION_STATUS == rulestatus) {
            int n = r->status;

            r->status = HTTP_OK;
            return n;
        }
```

`n` は 301 や 302 です。ここで返るので、**`RewriteRule` がリダイレクトしたリクエストでは、同じファイルの `RedirectMatch` は一度も評価されません**。

## 何が怖いか

`.git` を 404 で守っている `.htaccess` は多いと思います。WordPress 案件でもよく書きます。

```apache
RedirectMatch 404 /\.git
```

これを**ファイルの一番上に書いても、順序の保証にはなりません**。上に書いたから先に効く、という前提が `.htaccess` の中では成立していないためです。

同じファイルに `.git` を含むパスに当たる `RewriteRule` が1つでもあると、そちらが先に走ってリダイレクトし、404 のほうは評価されないまま終わります。

運用ルールとしてはこうなりました。

> 新しく足す `RewriteRule` が「`.git` を含むパスに当たりうるか」で判断する。上下の順番では守れない。

Apache の公式ドキュメントにも「mod_alias と mod_rewrite を混ぜないほうがよい」という趣旨の記述がありますが、理由のほうを自分で読むまで、なぜ混ぜると困るのかは分かっていませんでした。

## 今回は交差しなかった

足したのは `^$`（トップだけ）。既存は `^life_builder`。どちらも `/\.git` と交差しないので、実害はゼロでした。`.git` 系のパスが全部 404 のままなのは実測しています。

交差しないと分かったのは、順序を調べたからです。「下に書いたから安全」で済ませていたら、次に `.htaccess` を触るときも同じ判断を繰り返していたはずでした。
