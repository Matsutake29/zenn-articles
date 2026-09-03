---
title: "WordPressの「予約投稿の失敗」、原因はcronではなくpost_date_gmtのズレだった"
emoji: "🗓️"
type: "tech"
topics: ["wordpress", "wpcli", "mysql", "個人開発", "運用"]
published: false
---

WordPress の管理画面に、赤字で「**予約投稿の失敗**」が出ていました。

この表示で検索すると、出てくる対策はほぼ cron 側です。WP-Cron はアクセスが無いと発火しないので、`DISABLE_WP_CRON` にして外部 cron を使う、あるいはプラグインで補う。自分もそれを疑いました。

違いました。cron は正常に動いていて、それでも絶対に公開されない状態になっていました。

## 症状

```text
ID   post_status  post_date              post_date_gmt
959  future       2026-08-13 20:00:00    2026-08-14 11:00:00   ← 15時間先
960  future       2026-08-13 21:00:00    2026-08-15 11:00:00   ← 38時間先
```

サイトのタイムゾーンは `Asia/Tokyo`（`gmt_offset` は 9）。正しい GMT は「ローカル時刻 − 9時間」なので、959 なら `2026-08-13 11:00:00` のはずです。

ところが GMT のほうが未来を指していました。ひどいものは1週間以上ずれています。

## WordPress は `post_date_gmt` で公開判定する

ここが自分の知らなかったところでした。

`post_date` が過去になっていても、**`post_date_gmt` が未来なら `future` のまま**動きません。cron が発火しても、WordPress 側で「まだ時刻になっていない」と判断されます。

実際、事後に確認したら cron イベントは正常に登録されていました。

```text
publish_future_post   2026-08-14 19:00:00
publish_future_post   2026-08-14 20:00:00
publish_future_post   2026-08-14 21:00:00
```

`DISABLE_WP_CRON` も未定義。つまり、**発火はしていた。発火先で拒まれていた**わけです。「予約投稿の失敗」の表示につられて cron を直しにいくと、永久に直らない形でした。

## `--post_status=publish` が `Success` を返す

原因が分かる前に、手で公開しようとしました。

```bash
wp post update 959 --post_status=publish
# Success: Updated post 959.
```

`Success` が返ってきます。そして `post_status` は `future` のままでした。

GMT が未来なので、WordPress が publish を受け付けません。成功メッセージは嘘ではないのですが、意図した結果は起きていない。ここで「直った」と思って次に進んでいたら、翌日また同じ画面を見ていたはずです。

## 原因は自分の過去の操作だった

予約記事の公開日を前倒しするために、`post_date` を一括で変更したことがありました。

```bash
wp post update {ID} --post_date='2026-08-14 19:00:00'
```

これは `post_date_gmt` を再計算しません。 ローカル時刻だけが動いて、GMT には前倒しする前の日程が残り続けていました。

壊れていたのは、その一括変更をかけた15本だけでした。同じ日に新規で投入した28本は、両方の値が最初から揃っていたので無事です。**43件中15件**が該当という形でした。

## 検出

JST なら、2つの差が 9 以外のものが壊れています。

```sql
SELECT ID, post_status, post_date, post_date_gmt,
       TIMESTAMPDIFF(HOUR, post_date_gmt, post_date) AS diff
FROM wp_posts
WHERE post_type='post' AND post_status IN ('publish','future')
  AND TIMESTAMPDIFF(HOUR, post_date_gmt, post_date) != 9;
```

`publish` も含めているのは、公開済みの記事にもズレが残っていることがあるからです（自分は1時間ずれたものが1本ありました）。

## 修正

両方渡します。

```bash
wp post update {ID} \
  --post_date='2026-08-14 20:00:00' \
  --post_date_gmt='2026-08-14 11:00:00'
```

GMT を正しくした瞬間、**公開時刻を過ぎているものは自動で `publish` になりました**。手動で `--post_status=publish` を打つ必要はありませんでした。最初に打った `Success` のコマンドは、そもそも要らなかったことになります。

上の SQL が0件になれば完了です。

### 修正すると一覧の並びが変わる

1つ注意があって、`wp post update` を打つと `post_modified` が動くので、**公開予約の一覧で修正した記事が後ろのページへ移動します**。

一覧の先頭が5日先の記事になって、一瞬「明日からの予約が消えた」ように見えました。実際は件数もそのままで、どれも無事でした。一覧の見た目ではなく、件数と上の SQL で確認したほうが確実です。

## 「予約投稿の失敗」は原因を1つに絞ってくれない

自分の場合はこうでしたが、**cron が原因のケースは実在します**。同じ表示が出て、対策が正反対になる。

見分け方は簡単で、**`post_date` と `post_date_gmt` の差を見るだけ**です。差が UTC オフセットと一致していれば cron 側を疑う。一致していなければ、cron をどう直しても公開されません。

もう1つ持ち帰ったのは、`Success` の扱いでした。コマンドが成功したことと、意図した状態になったことは別で、後者は自分で見に行かないと分からない。今回は見に行ったから気づけましたが、見に行かない日のほうが多かったと思います。
