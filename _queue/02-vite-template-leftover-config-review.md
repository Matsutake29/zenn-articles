---
title: "環境構築が終わった\"つもり\"の後に、棚卸しレビューを挟んでみた"
emoji: "🔍"
type: "tech"
topics: ["vite", "react", "githubactions", "個人開発", "typescript"]
published: false
---

## 環境構築、一気に終わらせた後の話

パワーリフティングのプレート計算アプリを個人開発中。
目標の重量に対して、バーの片側に何kgのプレートを何枚つければいいかを計算するWebアプリだ。

:::message
公式大会では装着する構成が自動で表示される。これが普段の練習でもスマホで見られたら便利だと思って作りはじめた。

- リポジトリ: https://github.com/Matsutake29/plate-calculator
- Vite + React + TypeScript + Tailwind CSS
:::

Vite + React + TS の雛形からTailwind v4・ESLint/Prettier・Vitest・huskyまで、工程2「環境構築」として一気に構築した。

「動いた、終わった」で止めてもよかったが、リポジトリ全体をもう一度読み解く工程を挟んでみた。
git status・git log・全履歴grep・CI実行履歴・GitHub Contributors APIを実際に叩いて確認する棚卸しレビュー。

結果、雛形が"やりかけ"のまま残していた設定が2つ見つかった。

## 発見1: .gitignoreにあるのに、ファイルが存在しない

`.gitignore`を読んでいたら、こんな2行があった。

```gitignore
.vscode/*
!.vscode/extensions.json
```

1行目で`.vscode`配下を丸ごと除外し、2行目の`!`で`extensions.json`だけ除外解除している。
つまり「`.vscode`は基本無視するが、`extensions.json`だけはgit管理する」という意味。
ところが肝心の`.vscode/extensions.json`自体がリポジトリのどこにも存在しなかった。

Vite雛形は「ここにチーム推奨の拡張機能リストを置く想定」を`.gitignore`の一行だけ残していて、ファイル自体は生成しない作りになっていた。
意図はあるが、手を動かさないと完成しない。

対応として、ESLint・Prettier・Tailwind CSS・GitHub Actionsの拡張機能IDを`.vscode/extensions.json`に明示した。
これでcloneした人がVS Codeを開くと、自動で導入が提案されるようになる。

## 発見2: CIは固定、ローカルは野放し

`.github/workflows`を見ると、CIは`node-version: 24`と明示的に固定されていた。
ところが、ローカル環境のNodeバージョンを揃える手段（`.nvmrc`や`package.json`の`engines`フィールド）が何もなかった。

| | Nodeバージョン指定 |
|---|---|
| CI（GitHub Actions） | `node-version: 24` で固定 |
| ローカル環境 | 指定なし |

「CI側だけ環境を固定して、ローカルは野放し」という状態。
違うNodeバージョンでcloneして動かすと、CIは通るのにローカルでは挙動が違う、というズレが起きうる。

対応として`.nvmrc`と`engines`フィールドを追加し、Node 24系に揃えた。
調べてみると、`engines`は単体だと「このバージョンで動きます」という宣言止まりで、違うバージョンでも`npm install`自体は通ってしまうらしい。
実際にバージョンを揃えたいなら、`.nvmrc`を置いてnvmやfnmに読ませる方が効くという理解に落ち着いた。

実物は [.nvmrc](https://github.com/Matsutake29/plate-calculator/blob/main/.nvmrc) と [.github/workflows/ci.yml](https://github.com/Matsutake29/plate-calculator/blob/main/.github/workflows/ci.yml) にある。

## 保留にした論点: LICENSE

もう一つ、あえて保留にした論点がある。LICENSEファイルの未設定。

調べて知ったのは、「何も設定しない」ことにも既定の意味があるという点。
LICENSEファイルがないリポジトリは、法的には「all rights reserved（無断利用不可）」がデフォルトになる。
何もしないことが「制限なし」ではなく「最も制限が強い状態」というのは、知らないと見落としやすい。

これは単なる設定漏れというより、「ポートフォリオを自由にcloneされたい状態にするか、見せるだけにするか」という価値観の選択の話だと気づいた。
今回は結論を急がず保留にしている。

mainブランチ保護の設定も同様に保留。

## 棚卸しレビューをやってみて

環境構築を「動いた」で終わらせず、もう一段レビューを挟んだことで、雛形が置き土産にしていた"やりかけ"の設定に気づけた。

個人開発だと見過ごしがちだが、チーム開発に途中からジョインする場面を想定すると、こういう抜けは初日のつまずきポイントになりそうだと感じている。

同じような棚卸しをする機会があれば、次はこのあたりから見ていくと思う。

- [ ] `.gitignore`の除外解除（`!`で始まる行）に、対応するファイルが実在するか
- [ ] CIとローカルのNodeバージョンが揃っているか（`.nvmrc` + CI設定）
- [ ] `.vscode/extensions.json`が共有されているか（チーム開発を想定するなら）
- [ ] LICENSEを明示的に選んだか（「選ばない」という選択も含めて）
- [ ] READMEに環境構築手順と前提バージョンが書いてあるか
