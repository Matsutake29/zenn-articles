---
title: "Web制作のコーダーがReactを学んで気づいた、思考回路の転換"
emoji: "🎓"
type: "tech"
topics: ["react", "javascript", "frontend", "webdesign", "learning"]
published: true
---

## はじめに

Udemyの「モダンJavaScriptの基礎から始める挫折しないためのReact入門」を修了しました。合計7時間・65レクチャー、修了証明書も出ました。

Web制作を本業にしながら、フロントエンドエンジニア転向を目指して学習しています。
Reactの章に入ってから環境構築で詰まった話は[前回の記事](https://zenn.dev/matsutake_prgrm/articles/react-vite-local-env-jsx-hamari)に書いた通りで、今回はコースを最後まで走り切ったところで感じたことをまとめます。

VanillaJSとReactの書き方の違いというより、普段WordPressでHTML/CSSを書いているコーダーとして、頭の使い方がどう変わったかを中心に書いていきます。

このコースの設計思想が、修了してみるとよく効いていたと感じます。

> 「JavaScriptへの理解なくしてReactの習得はなし得ない」という考えのもと、1) モダンJSの周辺知識（SPA・仮想DOM等の概念）→2) React開発で使うモダンJS機能→3) プレーンなJavaScriptのみでアプリを開発（Reactの恩恵を知るため）→4) Reactの基本・ルール→5) 同じアプリをReactで作り直す（近代JavaScriptへの転換を体感）

要は「先にVanillaJSで書く苦労をしてから、同じものをReactで作り直させる」という構成です。
実際に体を通してみると、3)と5)の落差がそのままReactを学ぶ意味になっていました。

## 同じTODOアプリを、二通りの書き方で作った

作ったのはTODOの追加・完了・削除・差し戻しができるだけのシンプルなアプリです。これをまずVanillaJSで、そのあとReactで、同じ機能のまま作り直します。

作り終えて一番実感したのは、この2つが単に「書き方が違う」のではなく、そもそもの考え方が逆を向いているということでした。

VanillaJSは「画面がこう変わってほしいなら、こう命令する」という書き方です。
Reactは「今の状態がこうなら、画面はこう見えるべき」という宣言の書き方です。

命令的・宣言的、と言葉で片づけるのは簡単ですが、書きながら気づいたのはもっと具体的な違いでした。

VanillaJS側で書く命令——`closest("li")`で自分の親を探す、`nextElementSibling.remove()`で隣の要素を消す——は、どれも「今、画面はこういうDOM構造になっているはずだ」という仮定の上に成り立っています。
次に何を書くかは、その仮定が今も合っているかどうかで決まるので、仮定を自分の中で更新し続けない限り、次の一手が書けません。
しかも、新しく生成した要素(後述する「戻す」ボタン)には、また一からイベントを結び直す必要があります。
DOM構造とイベントの結びつきを、変化が起きるたびに自分の手でメンテナンスし続ける。それがVanillaJSでの書き方でした。

Reactでは、この「今のDOMがどうなっているか」を一度も考えませんでした。
見ているのは「今のデータ(state)がこうだ」という事実だけです。
書く側がやることは「こうなったら、こう見えるべき」という対応関係を宣言するところまでで、古い画面から新しい画面への変化を計算して反映する仕事——差分の検出、DOM更新、イベントの再設定——はReact側が肩代わりしてくれます。

つまりこの2つの違いは、「今の状態をどこで管理するか」「変化の手順を誰が背負うか」が丸ごと入れ替わっている、ということだったのだと思います。

## VanillaJS版：完了ボタンひとつに何行必要か

VanillaJS版の「完了」ボタンを押したときの処理は、こんな流れでした。

```js
completeButton.addEventListener("click", () => {
  const movetarget = completeButton.closest("li");
  completeButton.nextElementSibling.remove();
  completeButton.remove();

  const backButton = document.createElement("button");
  backButton.innerText = "戻す";
  backButton.addEventListener("click", () => {
    const todoText = backButton.previousElementSibling.innerText;
    createIncompleteTodo(todoText);
    backButton.closest("li").remove();
  });

  movetarget.firstElementChild.appendChild(backButton);
  document.getElementById("complete-list").appendChild(movetarget);
});
```

完了ボタン1つ押すだけで、やることが5つあります。自分が今いる`li`要素を探す、いらなくなった要素を消す、代わりの「戻す」ボタンを作る、そのボタンにもイベントを貼る、最後に別のリストへ移動する。

全部、手順として自分で書く必要があります。DOM操作は「今どこに何があるか」を自分で把握し続ける仕事だと、書きながら実感しました。

## React版：stateを書き換えるだけでUIが追従する

同じ機能をReactで書き直すと、こうなります。

```jsx
const [incompleteTodos, setIncompleteTodos] = useState(["TODOです1", "TODOです2"]);
const [completeTodos, setCompleteTodos] = useState(["TODOでした1", "TODOでした2"]);

const onClickComplete = (index) => {
  const newIncompleteTodos = [...incompleteTodos];
  newIncompleteTodos.splice(index, 1);
  const newCompleteTodos = [...completeTodos, incompleteTodos[index]];
  setIncompleteTodos(newIncompleteTodos);
  setCompleteTodos(newCompleteTodos);
};
```

`createElement`も`appendChild`も一度も出てきません。配列をコピーして中身を書き換え、`setIncompleteTodos`と`setCompleteTodos`を呼んでいるだけです。ボタンの生成もリストへの移動も、Reactの側が勝手にやってくれます。

`incompleteTodos`はただのJS変数なのに、これがそのまま画面の状態そのものになっている感覚があります。試しに「今リストに何件あるか」を出そうとしたとき、VanillaJS版ならDOMを数えるコードが要りますが、Reactは`incompleteTodos.length`と書くだけで済みました。配列の中身自体が状態の本体だから、数えるまでもなく答えが手元にあるわけです。

DOMは「今の状態が反映された結果」でしかなく、状態そのものではない。この線引きが、2つを両方書いてみて初めて体に入った気がします。

## 「コーディング」という言葉の広さに気づいた

この比較を通して、自分がやってきた仕事の輪郭も見えてきました。

普段のWordPress制作は、デザインカンプという「完成した答え」をHTML/CSSに変換する仕事です。
答えは最初から決まっていて、それを正確に再現する力が問われます。

一方、Reactでこのアプリを作るときは、まず「incompleteTodosという配列で未完了リストを持つ」「completeTodosという別の配列で完了リストを持つ」という、データの持ち方そのものを自分で決める必要がありました。
答えが最初から決まっていないので、要件からロジックやデータ構造を組み立てる工程が先に来ます。

どちらが上ということではなく、使う思考回路がそもそも違う、というのが今回の一番大きな気づきです。
今まで「コーディング」とひとくくりにしていた言葉の中に、実はかなり性質の違う仕事が並んでいたのだと分かりました。

## これから

次はTypeScriptを先に基礎から学んでから、Next.jsに進む予定です。
5月に実務のフロントエンドエンジニアの方から「JS基礎の次はTypeScriptを」と勧められていたのを思い出しつつ、今回VanillaJSとReactの両方を書いてみたことで、その順番の意味がようやく腹落ちしました。

土台が一つ整った実感があるので、次の学習に進んでいきます。
