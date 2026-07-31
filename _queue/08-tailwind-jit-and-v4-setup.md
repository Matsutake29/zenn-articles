---
title: "gap-[3px] はどこから来るのか——Tailwindを「CSSを作る機械」として理解する"
emoji: "⚙️"
type: "tech"
topics: ["tailwindcss", "css", "vite", "wordpress", "個人開発"]
published: false
---

<!-- 【公開前チェック】

     ■ 公開順の制約
     冒頭で前編 tailwind-from-flocss-perspective へリンクしている。
     未公開だと404になるので **前編の公開後に出すこと。**

     ■ 数値の出所
     CSSサイズ 12.76kB / gzip 3.54kB は plate-calculator の実測値（2026-07-26時点）
-->

前編（[FLOCSS実務者が初めてTailwindを使って、誤解していたこと3つ](https://zenn.dev/matsutake_prgrm/articles/tailwind-from-flocss-perspective)）で、Tailwindの任意値記法について書きました。
`gap-[3px]` と書けば3pxのgapが当たる、というやつです。

書いておいて何ですが、当時は**なぜそれが動くのか分かっていませんでした。**

Tailwindのクラスは「あらかじめ用意されているもの」だと思っていました。
それだと `gap-[3px]` のような自由な値が動く理由が説明できない。
用意されているならキリの良い値だけのはずだし、全パターン用意してあるならCSSが天文学的な量になります。

答えは「そもそもCSSファイルではなかった」でした。

## 生成されたCSSを見るのが一番速かった

ドキュメントを読むより、自分のプロジェクトのビルド結果を見るほうが速かったです。

`dist/assets/index-*.css` から抜き出すと、こうなっていました。

```css
.gap-\[3px\]{gap:3px}
.border-\(--plate-edge\){border-color:var(--plate-edge)}
.p-4{padding:calc(var(--spacing) * 4)}
```

`gap-[3px]` に対応するCSSが、ちゃんと存在しています。

ただしこれは**事前に用意されていたものではなく、自分が書いた瞬間に生まれたもの**でした。

## Tailwindは「CSSの塊」ではなく「CSSを作る機械」

仕組みは4ステップです。

1. ビルド時に `.tsx` を**ただのテキストとして**スキャンする
2. クラス名っぽい文字列を拾う
3. 解釈してCSSをその場で生成する
4. 使われた分だけ書き出す

これがJIT（Just-In-Time）と呼ばれているものでした。

`gap-[3px]` と書けば、スキャナがその文字列を見つけて `.gap-\[3px\]{gap:3px}` を作る。
書かなければ作られない。だから未使用CSSが積もらないし、任意の値が書けます。

「Tailwindを入れる＝CSSファイルを読み込む」というイメージを持っていたのが、そもそもの間違いでした。
読み込んでいるのは**出力先の指定**で、本体はビルド時に動くプログラムのほうです。

### `p-4` の生成結果が面白い

さっきの生成CSSをもう一度見ます。

```css
.p-4{padding:calc(var(--spacing) * 4)}
```

`padding: 1rem` ではなく `calc(var(--spacing) * 4)` になっています。

つまり「数字 × 基準値」の計算がCSS変数として外に出ている。`--spacing` を変えれば、全ユーティリティが一斉に変わります。

前編に書いた「カンプの規則をTailwindに教える」（`@theme { --spacing: 5px }`）。
これが実際に効く仕組みが、ここにありました。
設定を変えると全部のクラスが追従するのは、値がハードコードされていないからです。

ちなみにデフォルトが4pxなのは、**8pxグリッドを偶数で表現できる**からだと理解しています。
（`p-2` = 8px、`p-4` = 16px）
`--spacing: 8px` にすると4pxが `p-0.5` になって扱いづらくなる。
小数も使えるので `gap-0.75` = 3px も書けます。
自分が `gap-[3px]` と書いたとき、エディタの拡張が `gap-0.75` を提案してきた正体がこれでした。

## 実務でハマる罠——文字列連結は動かない

ここが一番実用的な学びでした。

**クラス名を文字列連結で組み立てると動きません。**

```jsx
// 動かない
<div className={`gap-[${n}px]`}>
```

理由はJITの仕組みそのものです。
スキャナは単なるテキスト検索なので、`gap-[${n}px]` という文字列を見ても、実行後に何になるかは分かりません。
だからCSSが生成されない。

自分のコードでは、プレートの高さと背景色を動的に変えたい箇所がありました。そこは `style={{}}` で書いています。

```jsx
<span style={{ height: `${h}px`, background: color }} />
```

書いたときは「Tailwindなのにインラインstyleを使っていいのか」と少し引っかかっていました。
読み解いた後の答えは明確で、**動的な値はインラインstyleが正解**です。
ビルド時に値が確定しないものは、そもそもJITの守備範囲外なので。

「Tailwindを使うならクラスで全部書くべき」ではありませんでした。
「ビルド時に決まるものはクラス、実行時に決まるものはstyle」という線引きです。

## v4の導入は「1行」ではなかった

もうひとつ勘違いしていたことがあります。

導入は `@import 'tailwindcss';` の一文でいい、と思っていました。実際は3点セットが必要です。

```bash
npm i -D tailwindcss @tailwindcss/vite
```

```ts
// vite.config.ts
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

```css
/* index.css */
@import 'tailwindcss';
```

役割を分けて理解すると腑に落ちました。

- **プラグインが本体**。`.tsx` を読んで `gap-[3px]` を見つけ、CSSを書く機械
- **CSSの1行は出力先の指定**。「ここに書き出してください」という宣言

JITの仕組みが分かっていれば、「スキャンする主体が必要」と自然につながります。
CSSファイルの中に1行書いただけでは、誰も `.tsx` を読みに行きません。

### v4で消えた設定ファイル

v3の記事を読んでいると出てくるファイルが、v4では要らなくなっています。

| | v3 | v4 |
|---|---|---|
| `tailwind.config.js` | 必要 | **不要**（設定はCSSの `@theme` へ） |
| `postcss.config.js` | 必要 | **不要** |
| CSSの記述 | `@tailwind base/components/utilities` の3行 | `@import 'tailwindcss';` の1行 |

自分のプロジェクトに `tailwind.config.js` が存在しないこと自体が、v4を使っている証拠でした。

これが分かってから、**ネット記事の読み方が変わりました。** 検索して出てくる記事の大半はv3前提です。
`tailwind.config.js` の話が出てきたらv3の記事だと判断して、設定まわりは読み飛ばす。
クラス名自体はほぼ変わっていないので、それ以外は参考になります。

## Viteは必須ではない——WordPressにも持ち込める

これは自分にとって一番の収穫かもしれません。

必要なのはNode環境だけで、バンドラは要りません。CLIで直接動きます。

```bash
npx @tailwindcss/cli -i input.css -o output.css --watch
```

そして**スキャン対象は拡張子を問いません。** テキストとして読んでクラス名っぽい文字列を拾うだけなので、`.php` でも動きます。

つまりWordPressのテーマ制作にそのまま持ち込めます。
`header.php` に `class="flex items-center gap-4"` と書く。
あとはCLIをwatchで回しておけばCSSが生成される。

正直、Tailwind＝モダンフロントエンドの道具、という枠で見ていました。
仕組みが「テキストをスキャンしてCSSを吐く」だけだと分かると、枠のほうが自分の思い込みでした。

（なお Play CDN はブラウザ上でJITを走らせる方式で、本番利用は非推奨とされています。試すぶんには手軽です）

## まとめ

- Tailwindは「CSSの塊」ではなく「**CSSを作る機械**」。書いた瞬間にCSSが生まれる
- `p-4` は `calc(var(--spacing) * 4)` として出力される。だから基準値を変えると全部追従する
- **クラス名の文字列連結は動かない**。動的な値はインラインstyleが正解
- v4の導入は3点セット。プラグインが本体で、CSSの1行は出力先の指定
- `tailwind.config.js` が出てくる記事はv3。設定の話は読み飛ばしてよい
- バンドラなしでも動き、`.php` もスキャンできる。**WordPressテーマにも持ち込める**

前編: [FLOCSS実務者が初めてTailwindを使って、誤解していたこと3つ](https://zenn.dev/matsutake_prgrm/articles/tailwind-from-flocss-perspective)
