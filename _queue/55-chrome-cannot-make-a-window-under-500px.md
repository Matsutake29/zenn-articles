---
title: "Chromeの--window-sizeは500px未満に縮まない。390pxのスクショはviewportのエミュレーションで撮る"
emoji: "📐"
type: "tech"
topics: ["chrome", "css", "responsive", "テスト"]
published: false
---

ダッシュボードをスマホ幅（390px）でスクリーンショットに撮ろうとしました。

ウィンドウサイズの指定は**通ります**。エラーも警告も出ません。ただ、撮れた画像の中身はスマホ幅ではありませんでした。

## 指定は通るが効かない

ヘッドレスの Chrome に `--window-size=390,844` を渡して、念のため測りました。

```js
document.documentElement.clientWidth   // → 500
```

**500px でした。** 指定した 390 ではありません。

要素を1つずつ変えて確かめると、境目がはっきり出ます。

```text
--window-size=390,844  → innerWidth=500
--window-size=500,844  → innerWidth=500
--window-size=600,844  → innerWidth=600
```

500 未満を指定すると 500 に丸められ、500 以上ならそのまま通る。自分の環境（macOS・Chrome 152）では、新旧どちらの headless モードでも同じでした。

## 何がまずいか

画像を 390px に切り出しても、**中身は 500px 幅でレイアウトされたページの左端**です。

- `sm:` などのブレークポイントは **500px で判定される**
- つまりモバイルレイアウトを撮ったつもりで、実際には撮れていない
- 見た目が「それっぽい」ので、測るまで気づけない

カードが1列に並んでいれば、それが「390px だから1列」なのか「500px でも1列」なのかは、画像からは分かりません。

## 制約はウィンドウにあって、viewport には無い

ここが自分の理解の浅かったところでした。最初は「Chrome は 500px 未満のウィンドウを作れない」と覚えて、だから小さい viewport は作れないのだと思い込んでいました。

違いました。**ウィンドウの下限と、viewport の下限は別**です。

DevTools Protocol の `Emulation.setDeviceMetricsOverride` で viewport を 390 に指定すると、ウィンドウは 500 のまま、中身は 390 でレイアウトされます。

```text
--window-size=390 のみ                       → clientWidth=500
setDeviceMetricsOverride({ width: 390 })    → clientWidth=390
```

`<meta name="viewport">` の有無、`mobile: true` / `false` のどちらでも 390 になりました。

これが Playwright の `viewport` オプションや Puppeteer の `setViewport`、DevTools の Device Mode が中でやっていることです。**ウィンドウはそのままで、描画領域だけを偽装する**。だから 500px の壁に当たりません。

```ts
// Playwright なら
const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
```

モバイル幅のスクショは、こちらが標準の道でした。

## ウィンドウしか触れないときの回避策: iframe

とはいえ、ツールによってはウィンドウサイズしか指定できないことがあります。`--screenshot` を CLI から直接叩く場合や、ブラウザ自動化ツールが `resize_window` しか公開していない場合です。

そのときは、**ウィンドウの中に小さい viewport を作ります**。

```html
<iframe
  src="（撮りたいURL）"
  style="position: fixed; left: 0; top: 0; width: 390px; height: 844px; border: 0"
></iframe>
```

iframe は独立した viewport を持つので、中のページは 390px でレイアウトされます。撮影後に左端 390px を crop すれば、スマホ幅の画像になります。

確認はこれです。

```js
iframe.contentDocument.documentElement.clientWidth   // → 390
```

**これを実測してから撮ります。** 測らないと、同じ罠にもう一度落ちます。

### iframe 方式の注意点

- **同一オリジンでないと `contentDocument` を読めません**。別ドメインのページを iframe に入れると、中の幅を確認する手段がなくなります
- **`X-Frame-Options: DENY` を返すページは iframe に入りません**。自分のサイトにこれを付けていたので、iframe 方式が使えなくなった場面がありました。しかもエラーは返らず、灰色の空ページが「成功」として保存されます

2つ目は、セキュリティのために自分で付けた設定が、自分の撮影手順を壊した形でした。こういう制約が出てきた時点で、エミュレーションのほうに切り替えるのが筋だったと思います。

## 同じ罠を2回踏んでいた

| | 経路 | 症状 |
|---|---|---|
| 1回目 | ヘッドレスの `--window-size=390` | 画像は 390px・viewport は **500px** |
| 2回目 | ブラウザ自動化ツールの `resize_window(390)` | 画像は 390px・viewport は **606px** |

2回目の 606 は Chrome の制約と別物で、そのツールが持つペインの最小幅でした。数字が違うのに「同じ 500px の壁」だと思い込んでいたのが、今回書き直すきっかけになっています。**2つの観測で数字が違うなら、原因も2つある**。

## 指定が通ることと、指定どおりになることは別

撮影は「見た目が正しければ正しい」と思いやすい作業です。だからこそ、**画像ではなく数値を確認する**手順が要る、というのが自分の持ち帰りでした。

500px という下限は自分の環境での実測なので、別の環境やバージョンでは違うかもしれません。ただ「指定したから 390 になっている」とは、どの環境でも言えない。`clientWidth` を1回読むだけで済むので、撮る前に読むようにしています。
