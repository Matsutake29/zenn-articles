---
title: "Server ActionでDBは変わったのに画面が変わらない —— Next.jsは「DBを触ったこと」を知らない"
emoji: "🔄"
type: "tech"
topics: ["nextjs", "react", "supabase", "serveractions"]
published: false
---

:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

カードの表示／非表示を切り替えるボタンを Server Action で作りました。押しても画面が変わりません。

でもリロードすると切り替わっています。**DB は正しく更新されている。**

## ターミナルを見たら GET が無かった

```text
POST /dashboard 200 in 312ms
```

POST は 200 で返っています。そして **GET が1本も出ていない**。画面を作り直す通信が走っていませんでした。

## Next.js は「DB を触ったこと」を知らない

ここが自分の理解の抜けていたところでした。

Server Action は、Next.js から見れば**ただの関数**です。中で Supabase を呼んだのか、ログを1行吐いただけなのかを区別できません。区別できないので、**何を捨てればいいかも分からない**。

だから、こちらから宣言する道具が用意されています。

```ts:src/app/dashboard/actions.ts
export async function toggleVisible(id: string, visible: boolean) {
  ...
  await supabase.from('items').update({ visible: !visible }).eq('id', id)
  revalidatePath('/dashboard')   // ← 「このパスの結果はもう古い」
}
```

`revalidatePath` は「このパスのキャッシュを捨てろ」ではなく、「**このパスの結果は変わった、と自分が知っている**」と伝えるもの、と理解しました。知っているのは書いた側だけなので。

## 予想が外れた: GET は増えなかった

`revalidatePath('/dashboard')` を入れたら、「POST のあとに GET が続けて出るはず」と AI から説明されて、自分もそう思っていました。

実際は **POST 1本のままで、画面が新しくなりました**。

```text
POST /dashboard 200 in 341ms
（GET は出ない）
```

理由は、`revalidatePath` を呼ぶと **POST のレスポンスに更新後の画面（RSC ペイロード）が同梱される**ためでした。

つまり revalidate していないときに GET が出なかったのは「取りに行かなかった」のではなく、**そもそも同梱するものが無かった**。1往復のまま画面が新しくなるのが Server Action の設計で、`revalidatePath` はそのスイッチでした。

## 「動かない」ではなく「描き直していない」だった

DB は変わっていて、POST も 200 で返っている。壊れているものは1つもありません。足りなかったのは「変えた」と伝える1行だけでした。

関数呼び出しに見えるものが、実際にはサーバーとの1往復で、**その往復に何を載せて返すかをこちらが決めていた**、という話です。

自分は「GET が増える」という予想が外れたことで、この設計の形が見えました。正解だけ知っていたら、なぜ1往復で済むのかは考えなかったと思います。

環境: Next.js 16.3.0 / React 19.2.8。キャッシュまわりの挙動はバージョンで変わるので、他の版では違うかもしれません。
