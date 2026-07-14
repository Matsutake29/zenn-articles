---
title: "React入門、動画教材をローカルVite環境に置き換えて学び直した記録"
emoji: "🌱"
type: "tech"
topics: ["react", "vite", "vscode", "javascript", "frontend"]
published: true
---

## はじめに

Web制作を本業にしながら、フロントエンドエンジニア転向を目指してReactを学習しています。

教材はUdemyの「モダンJavaScriptの基礎から始める挫折しないためのReact入門」。講師の解説はブラウザ上のCodeSandboxで進みます。動画としては分かりやすいのですが、実務のことを考えるとやっぱりVS Codeで手を動かしたい。そう思って、Reactの章に入ったところで環境構築が止まっていました。

今回、ローカルにVite + React環境を作って動画を追いかける形に切り替えたので、そこで詰まったところと、JSXを学びながら気づいたことをまとめておきます。

## 動画教材とローカル環境のギャップ

CodeSandboxとローカルのVS Codeでは、ファイル構成が少し違います。

- 動画（CodeSandbox）: `src/index.js`
- Vite: `src/main.jsx`

拡張子も`.js`ではなく`.jsx`が基本です。中身のimport文自体はほぼ同じなので、動画を見ながらでもファイル名の対応さえ頭に入れておけば、そのまま写経できました。

環境構築自体は`npm create vite@latest`一発で、思っていたより簡単でした。以前Web制作でGulpを使っていましたが、プラグインが更新されなくなったり情報が古くてエラーが出たりで、環境整備に時間を取られて結局使わなくなった経験があります。Viteは「とりあえず動く」状態まで数分で行けるのが素直にありがたかったです。

## VS CodeでJSXの補完が効かない

ローカル環境に切り替えて最初にぶつかったのが、コード補完でした。

WordPress制作のときは当たり前に使っていたEmmet（`div.container` + Tabで展開するアレ）が、`.jsx`ファイルではまったく反応しません。

原因は「VS CodeのEmmetが対象言語としてJSXを含んでいない」ことでした。`settings.json`に以下を追加すると解決します。

```json
"emmet.includeLanguages": {
  "javascript": "javascriptreact"
}
```

あわせて、Reactを書く人の多くが入れている拡張機能「ES7+ React/Redux/React-Native snippets」も導入しました。`rafce`と打つとアロー関数コンポーネントの雛形が一発で出るので、ボイラープレートを書く手間がかなり減ります。

## importの自動補完は結局スッキリ解決しなかった

`useState`と打ったときに、importが自動で追加されない場面がありました。

候補一覧が出た状態でEnterを押さずに次に進んでしまい、`uses`のような未確定の文字列だけが残って`ReferenceError`になる、というのが典型パターンです。

VS Codeには標準で「TypeScript and JavaScript Language Features」というオートインポート機能が入っていて、CodeSandbox特有の機能というわけではありません。ただ、入力中に自動でポップアップが出るタイミングは環境によって多少ブレます。確実に効くのは、行の左に出る電球マーク（`Cmd + .`のQuick Fix）からの「Add import from "react"」でした。

正直、as-you-typeの挙動は完全には解消しないまま、今回は手動でimportを書いて先に進めました。デバッグに時間を使いすぎるより、学習のペースを優先した形です。

## JSXのインラインスタイル、CSSの知識があるほど混同する

JSXではCSSをインラインで書けます。実務でこの書き方をすることはなさそうですが、書き方の違いに驚きました。

- 実務のCSS: `font-size: 16px;`
- JSX: `fontSize: "16px"`

プロパティ名はcamelCase、値は文字列なので`""`で囲む必要があります。数値だけはクォート不要で、`margin`や`padding`など多くのプロパティでは自動的に`100px`扱いになることを確認しました（`opacity`や`z-index`など単位を付けないプロパティは例外です）。

理由はシンプルで、JSXのstyle属性は本物のCSSではなく、ただのJavaScriptオブジェクトだからです。CSSを長く書いてきた人ほど「あれ、書き方が違う」と引っかかるポイントだと思います。知識があるから楽になるというより、知識があるからこそ一瞬混同する、という感覚に近いです。

## Props と State、実装しながらやっと言葉が繋がった

概念の説明を読むだけでは正直ピンときていなかった`Props`と`State`ですが、実際に色付きメッセージを表示する小さなコンポーネントを作ったことで理解が進みました。

```jsx
const ColorfulMessage = ({ color, children }) => {
  const contentStyle = {
    color,
    fontSize: "18px",
  };
  return <p style={contentStyle}>{children}</p>;
};
```

```jsx
<ColorfulMessage color="blue">お元気ですか？</ColorfulMessage>
```

`color`や`children`が親から渡ってくる`Props`で、これは子コンポーネント側からは書き換えられません。対して`useState`で持つ値は、コンポーネント自身が管理して書き換えられる`State`です。「渡されるだけのデータ」と「自分で持って変えられるデータ」という区別が、コードを書いて初めて腹落ちしました。

## おわりに

セクション6を終えた時点でまだ両方とも完全には頭に馴染んでいません。それでも、環境構築からエラーの読み方まで一通り自分の手でつまずいた分、次のセクション（TODOアプリの実装）で同じ概念を繰り返したときに、少しずつ繋がっていく感覚があります。

引き続き、作りながら覚えていくスタイルで進めます。
