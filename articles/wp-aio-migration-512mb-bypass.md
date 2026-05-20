---
title: "WordPressサブドメイン移行で All-in-One WP Migration 512MB制限を突破した手順"
emoji: "📦"
type: "tech"
topics: ["wordpress", "migration", "conoha", "wpcli", "htaccess"]
published: true
---

## はじめに

個人ブログ Life Builder を `mt-tk.com/life_builder` から `blog.mt-tk.com` サブドメインへ完全移行しました。当初は All-in-One WP Migration（以下AIO）でサクッと終わらせるつもりが、**全体1.3GB** で無料版の **512MB制限**（2026年5月時点・有料Unlimited Extensionは$69で解除）にひっかかり、削減手順から練り直すことになった話です。

最終的には 376MB に絞ってインポート → URL置換 → 301リダイレクトまで完了したので、同じ場面で詰まった人向けに手順を残します。

## 状況整理

| 項目 | 値 |
|---|---|
| 旧サイト | `mt-tk.com/life_builder` |
| 新サイト | `blog.mt-tk.com`（サブドメイン化） |
| サーバー | ConoHa WING（同一） |
| WP全体サイズ | 1.3GB |
| AIO Migration 無料版上限 | 512MB |

## ステップ1: エクスポート前の容量削減

エクスポート前に、移行に必要ないキャッシュ・バックアップ系を削除しました。

| 削除フォルダ | 役割 |
|---|---|
| `wp-content/ewww/` | EWWW Image Optimizer のキャッシュ |
| `wp-content/wflogs/` | Wordfence ログ |
| `wp-content/updraft/` | UpdraftPlus バックアップ |
| `wp-content/ai1wm-backups/` | AIO Migration が export 時に自動除外 |

特に **EWWW Image Optimizer のキャッシュが約373MB** あって、想像以上に肥大化していました。これだけで大幅に削減できた印象です。Wordfence ログと UpdraftPlus バックアップも合わせて整理した結果、エクスポート時のサイズは以下のように圧縮できました。

**1.3GB → 436MB → 376MB**（エクスポート時点）

## ステップ2: 同サーバー内なら SSH cp で転送

エクスポートした `.wpress` ファイルは通常「ローカルにダウンロード→新サーバーでアップロード」しますが、**同サーバー内移行なら SSH cp で数秒で済みます**。

```bash
cp /home/cXXXXXX/public_html/mt-tk.com/life_builder/wp-content/ai1wm-backups/{ファイル名}.wpress \
   /home/cXXXXXX/public_html/blog.mt-tk.com/wp-content/ai1wm-backups/
```

ConoHa WING の場合、SSH ログインして cp 一発。ローカル経由のダウンロード/アップロードを回避できるので大幅に時短になります。

## ステップ3: インポートとパーマリンク再生成

AIO Migration の管理画面で `.wpress` を選択してインポート。
完了後、必ず **設定 → パーマリンク設定 → 「変更を保存」** を押します（`.htaccess` 再生成のため）。

詳細は別記事 [WordPress移行後にパーマリンク404が出る罠と、「変更を保存」だけで直る理由](https://zenn.dev/matsutake_prgrm/articles/wp-permalink-404-after-migration) に書いています。

## ステップ4: URL置換（大文字小文字パターン両方）

旧URL（`mt-tk.com/life_builder`）から新URL（`blog.mt-tk.com`）への置換が必要です。

```bash
wp search-replace 'mt-tk.com/life_builder' 'blog.mt-tk.com' --skip-columns=guid
```

**罠**：`wp search-replace` は case-sensitive（大文字小文字を区別）です。

私の環境では、Privacy Policy の本文に `mt-tk.com/Life_Builder`（**Lが大文字**）が4箇所残っていました。小文字パターン置換だけで「0件残存」と表示されても、大文字パターンが残っている可能性があります。

```bash
# 大文字パターンも明示的に流す
wp search-replace 'mt-tk.com/Life_Builder' 'blog.mt-tk.com' --skip-columns=guid
```

念のため `grep -i` での本文確認も併用すると安全です。

## ステップ5: 301リダイレクト（実装順序が重要）

旧URL（`mt-tk.com/life_builder/*`）から新URL（`blog.mt-tk.com/*`）への301リダイレクトを設定します。

**順序を間違えると302・404を経由してSEO評価を落とすので注意**。

1. **子.htaccess**（`life_builder/.htaccess`）を 301リダイレクト専用に書き換え
   - 既存の WordPress RewriteRule + RewriteBase は捨てる
2. **動作確認**: `curl -I` で旧URLが 301 を返すか確認
3. **旧ディレクトリを物理削除**
4. **親.htaccess**（`mt-tk.com/.htaccess`）の RewriteRule に処理が引き継がれる

子.htaccess の記述例：

```apache
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteBase /life_builder/
  RewriteRule ^(.*)$ https://blog.mt-tk.com/$1 [R=301,L]
</IfModule>
```

子→親 の順で `.htaccess` が評価される Apache の仕様を理解した上で組むのがポイント。

## まとめ

- AIO Migration 無料版の512MB制限は、不要キャッシュフォルダ削除で十分突破可能
- 同サーバー内移行なら SSH cp で `.wpress` を直接転送して時短
- インポート後はパーマリンク再生成必須
- `wp search-replace` は case-sensitive。大文字パターン残存を `grep -i` で再確認
- 301リダイレクトは子.htaccess → 物理削除 → 親.htaccess の順序

中規模WPの移行で同じ罠にハマる人に届けば。
