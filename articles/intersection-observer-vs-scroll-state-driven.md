---
title: "スクロール連動UIの取りこぼし問題: IntersectionObserverから状態駆動への切り替え"
emoji: "🧭"
type: "tech"
topics: ["javascript", "css", "frontend", "performance", "ux"]
published: true
---

## はじめに

LPや採用ページなどでよく見かける、スクロール連動UIの実装で不具合が出ました。
「ビューポート中央に来たカードを active 化、別の要素（写真・画像・テキスト等）と連動切替」というありがちな仕掛けで、最初は IntersectionObserver で実装していました。

しかし高速スクロール時に：
- 「2を飛ばして4にジャンプ」する
- 一番上に戻しても「1まで戻りきらず2のまま」になる

という症状が出ました。本記事では原因と、scroll 直接観測への切り替えで解決した話を書いていきます。

## 旧実装（IntersectionObserver）

```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      const key = entry.target.dataset.key;
      // active 切替
    }
  });
}, { rootMargin: "-40% 0px -40% 0px", threshold: 0 });
```

ビューポート中央20%の帯に「入った瞬間」だけ検知して切り替えるシンプルな実装です。
一見動きそうに見えますが、ここに罠がありました。

## 飛ぶ問題の原因

高速スクロール時、ブラウザは IntersectionObserver のコールバックを **複数まとめて発火** することがあります。
「Bが入った」「Cが出た」「Dが入った」が同じ `entries` 配列に含まれるケースです。

`forEach` で順番に処理しているものの、`isIntersecting=true` のものを処理 → 最後に処理されたものが勝って active に残ります。
順序が保証されないため、間が飛んで見える挙動になっていました。

## 戻り切らない問題の原因

「帯を出た」イベントを処理していませんでした（`isIntersecting=true` のときしか動かない実装）。

一番上まで戻しても、最後に「入った」と判定された2が残ったまま。
1番目の要素がそもそも帯に入る前にスクロールが止まると永遠に切り替わりません。

つまり「変化の瞬間」だけを見張る実装では、変化が高速だと取りこぼし、戻し方によっては前の状態を引きずってしまうわけです。

## 新実装（scroll 直接観測）

```js
function initScrollSync() {
  const items = document.querySelectorAll("...");

  let currentKey = null;
  let ticking = false;

  const update = () => {
    ticking = false;
    const viewportCenter = window.innerHeight / 2;
    let nearestKey = null;
    let minDistance = Infinity;

    items.forEach((item) => {
      const rect = item.getBoundingClientRect();
      const itemCenter = rect.top + rect.height / 2;
      const distance = Math.abs(itemCenter - viewportCenter);
      if (distance < minDistance) {
        minDistance = distance;
        nearestKey = item.dataset.key;
      }
    });

    if (nearestKey && nearestKey !== currentKey) {
      currentKey = nearestKey;
      // active 切替
    }
  };

  const onScroll = () => {
    if (!ticking) {
      requestAnimationFrame(update);
      ticking = true;
    }
  };

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  update();
}
```

スクロールするたびに全要素の位置を測り、**ビューポート中央に最も近い1つ** を active にする実装です。

## なぜこれで解決するか

旧: 「変化点を見張る」イベント駆動
新: 「現在地を見続ける」状態駆動

状態駆動だと：
- イベントの取りこぼし／重複に依存しない
- 一番上まで戻れば必ず1番目の要素が「中央に最も近い」状態になる
- 中間要素も中央通過の瞬間に必ず最近接になる → 飛ばない

## パフォーマンスの工夫

scroll イベントは秒間数十〜数百回発火することがありますが、画面描画は60fpsが上限です。
`requestAnimationFrame` で1フレームに1回に間引き、`ticking` フラグでさらに重複排除しています。

`currentKey` 比較で「同じ要素を再度 active にする」DOM操作もスキップしています。

## 設計上の気づき

> 「変化の瞬間」を捕まえる実装は、変化が高速だと取りこぼしやすい。
> 「常に現在地を答える」実装にすると、観測タイミングに依存しにくくなる。

スクロール連動の目次ハイライト、セクションナビ、サイドバーのアクティブ表示など、似たUIで同じ罠にハマるケースがありそうです。

IntersectionObserver が悪いわけではありません。「要素が画面に入ったか」を1回検知したい用途（フェードイン、遅延読み込み）には最適です。
ただし「常に最新の状態を反映したい」UIには、状態駆動の方が向いていそうだ、というのが今回の結論でした。

## まとめ

- イベント駆動と状態駆動を意識して使い分ける
- スクロール連動UIで「飛ぶ」「戻らない」が起きたら状態駆動を疑う
- パフォーマンスは requestAnimationFrame で十分担保できる
