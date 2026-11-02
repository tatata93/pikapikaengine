# 次の受入: 共通C++の剛体・浮力をWebで動かす

2026-11-03。Nativeの無接触浮遊体と静的Webラボの公開後に着手する次項目。ここでは新たなWASMを生成・実行済みとはしない。

## 現状と調査

現在の650B freestanding WASMは4個の小さなC ABIだけを共有する。剛体/閉メッシュ核はvector・optional・例外等のC++標準機能を使うため、既存の `-nostdlib -fno-exceptions` コマンドをそのまま拡大して全機能が動くとはしない。WindowsのPATHにはemcc/em++/clang++/wasm-ldが見つからなかった。

2026-11-03にEmscripten公式の[C++ Exceptions Support](https://emscripten.org/docs/porting/exceptions.html)、[Interacting with code](https://emscripten.org/docs/porting/connecting_cpp_and_javascript/Interacting-with-code.html)、[Open Source License](https://emscripten.org/docs/introducing_emscripten/emscripten_license.html)を本文確認。閲覧文書は `6.0.14-git (dev)` 表記で、採用済みSDK版ではない。例外catchの既定、JS方式とWASM方式の違い、C exports/線形メモリへの接続、MIT/NCSAの説明を確認した。実SDK版・全同梱ランタイムの条件は導入対象ごとに確認する。ツールチェーン候補の調査であり、新依存のインストール・製品への同梱はまだない。

候補はEmscriptenで標準C++経路をコンパイルする方式と、従来freestanding境界へ必要な機能だけを切り出す方式。後者は標準コンテナ/例外の置換や二重実装を生みやすい。まずEmscriptenで最小コンパイルと出力内容を測り、サイズ・初期化・例外・メモリ・配布条件が明確な状態で採用判断する。完成済み物理ライブラリへの置換は目的ではない。

## 最初の実装・検証順

1. 一定のSDK版/取得元/ハッシュを固定し、生成ランタイムとC/C++標準ライブラリを含む配布範囲・ライセンス・帰属文を記録する。既存650Bの来歴を上書きしない。
2. C++共通の `dynamics` / `hydrostatics` へ薄いC ABIを追加。例外を境界内で捕捉し、失敗コードと診断を返す。状態を壊さず、巨大入力/メモリ不足を無言で成功にしない。C++の内部レイアウトをJSから直接推測しない。
3. Hull/Worldの寿命と解放、物体/頂点/面/メモリの予算、単位/Quaternion/ID/Float64配列の規約を定義。メモリ成長後の古いTypedArray参照を再利用しない。
4. 既存12静水圧fixtureと釣合い/上下振動/偏心復原をNative・Node WASM・ブラウザで実行。独立解析値、刻み収束、状態比較、例外後の再利用、反復作成/破棄を検証。各処理系での許容誤差を測定し、無条件のビット一致を主張しない。
5. 同じ固定tickの浮遊体をWebGPUで表示し、停止/再開/コマ送り/初期条件リセットを本当の共通C++状態へ接続する。再生済み軌跡を表示するだけで実時間シミュレーターと称さない。現在の静的浮力ラボは維持する。
6. コアのCPU・メモリ・初期化サイズに加え、描画/音/入力込みのフレーム生ログを測定。遅い刻みや失敗を除去しない。性能未達を品質変更や刻みの取りこぼしで合格にしない。

無接触浮遊体の共通化と、箱の接触形状・一般関節・非定常流・材料損傷は別の受入。高精度レンズ計算は `OPTICS_SCOPE.md` の任意選択要求を維持する。
