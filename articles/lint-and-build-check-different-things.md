---
title: "CIをわざと壊したら、lintが緑のままbuildだけ赤くなった"
emoji: "🔴"
type: "tech"
topics: ["githubactions", "typescript", "eslint", "nextjs", "ci"]
published: true
published_at: 2026-08-28 18:00
---
:::message
2作目のポートフォリオとして「Hubpin」（分散した発信を1か所に集めるハブサイト）を作りながら書いています。

- リポジトリ: https://github.com/Matsutake29/hubpin
- Next.js（App Router） + Supabase + Tailwind CSS
:::

個人開発のリポジトリにGitHub ActionsでCIを入れました。PRを出すとlintとbuildが走る、19行の設定です。

入れた直後にPRを出したら緑になりました。動いている、と思いました。

ただ、そのときの緑には**何も意味がありません**。
CIが正しく動いて緑になったのか、そもそも何も検査していないから緑なのか、この時点では区別が付かないからです。

なので工程に「わざと壊して赤くする」という手順を入れました。実際にやってみたら、
**lintは緑のまま、buildだけが赤くなりました。**

## 入れたCI

```yaml
- run: npm ci
- run: npm run lint
- run: npm run build
```

`npm ci` で依存を入れて、lintを通して、ビルドする。それだけです。

## わざと壊した内容

動的ルートのページから `await` を1つ消しました。

```tsx
const { username } = await params   // ← この await を消した
```

Next.jsのApp Routerでは `params` がPromiseで渡ってくるので、`await` を外すと
Promiseのまま分割代入することになります。

コミットメッセージは `test: break build to verify CI fails` にしました。
意図的に壊していることが履歴に残るようにしています。あとから見て事故と区別が付かないと困るので。

## 結果

![CIのステップ一覧。npm ci と npm run lint は緑、npm run build だけが赤](/images/lint-and-build-check-different-things/ci-log-lint-green-build-red.png)

```
✓ npm ci        10s
✓ npm run lint   3s   ← 通っている
✗ npm run build  7s   ← ここで落ちた
```

lintが通っています。壊したコードを見逃しました。

buildのログはこうでした。

```
✓ Compiled successfully in 4.3s      ← 変換は成功している
  Running TypeScript ...
Error: src/app/[username]/page.tsx(17,11): error TS2339:
  Property 'username' does not exist on type 'Promise<{ username: string; }>'
Failed to type check.
Error: Process completed with exit code 1
```

`Property 'username' does not exist on type 'Promise<...>'`。
Promiseには `username` なんてプロパティは無い、と言われています。そのとおりです。

## 分かったこと1: lintとbuildは別のものを見ていた

lintが素通りしたのは、**自分の設定では型情報を使っていなかった**からでした。

`create-next-app` が生成した `eslint.config.mjs` は、`eslint-config-next` の
`core-web-vitals` と `typescript` を読み込んでいるだけです。
未使用の変数や危険な書き方といった、書き方の作法を見ています。

型の矛盾はここを素通りします。文法としては正しいコードなので。

なお「ESLintは型を見ない」と言い切ると正確ではありません。
typescript-eslint には型情報を使うルール群があって、設定を足せば有効になります。
自分がそれを入れていなかった、というだけの話でした。

いずれにせよ、**片方だけ回していたらこの壊れ方は検出できませんでした。**
lintとbuildの両方を回す構成にしていたのが、結果的に効いています。

## 分かったこと2: コンパイルは通って、型チェックで落ちた

ログの順番が示唆的でした。

```
✓ Compiled successfully in 4.3s
  Running TypeScript ...
```

**変換は成功しています。** そのあとの型チェックで落ちている。

JavaScriptとして見れば、`await` の無い `params` から `username` を取り出すのは
エラーではありません。Promiseオブジェクトに `username` というプロパティが無いだけなので、
`undefined` が返って、そのまま動きます。

つまり本番では「なぜか名前が表示されない」という形で出てくるバグでした。
エラーにならず、静かに空になる。原因を探すのに時間がかかるタイプです。

それを型が止めてくれた、という順序が見えたのが収穫でした。
型を書く理由を説明できるようになったのは、通ったときではなく落としたときでした。

## 分かったこと3: CIの成否は終了コードで決まる

最後の行です。

```
Error: Process completed with exit code 1
```

「エラーメッセージが出たから赤くなった」のではなく、
**プロセスが0以外を返したから赤くなっています。**

言われてみれば当たり前なのですが、自分は「CIがログを読んで判定している」くらいの
ぼんやりした理解でいました。実際にはコマンドの終了コードを見ているだけです。

これが分かると、自作のスクリプトをCIに足すときに何をすればいいかも分かります。
失敗したら0以外で終わればいい。

## おまけ: 赤なのにマージできた

赤くなったPRの画面で、`Merge pull request` ボタンが普通に押せました。

![All checks have failed と表示されているPR画面。Merge pull request ボタンは押せる状態](/images/lint-and-build-check-different-things/ci-red-pr.png)

`All checks have failed` と出ているのに、マージを止めてはくれない。

**CIは教えてくれるだけで、止めてはくれませんでした。**
止めるには Settings → Branches でブランチ保護を設定して、
`Require status checks to pass before merging` を有効にする必要があります。

一人で開発しているので実害はまだ出ていないのですが、
「CIを入れた＝壊れたコードが入らなくなった」と思っていたのは間違いでした。設定はこれから入れます。

ちなみに赤くなったPRには `Fix with Copilot` のボタンも出ていました。押していません。
意図的に壊しているので、直されると困るという状況でした。

## 緑に意味が出たのは、一度赤くしてからだった

CIを入れた直後の緑は、「検査してOKだった」と「そもそも検査していない」を区別できません。
区別できるようにするには、赤くなるはずのものを入れて、実際に赤くなるのを見るしかない。

そして赤くしたことで、**lintとbuildが別のものを見ている**という、
設定した時点では分かっていなかったことが実データで出てきました。

わざと壊す手順は、CIが動くことの確認だと思って工程に入れていました。
実際には、自分がCIを何だと思っていたかの確認になっていました。
