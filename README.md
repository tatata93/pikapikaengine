# pikapikaengine

自作C++20 / WebGPU汎用ゲームエンジンの開発初期版です。WindowsはDirectX 12、ブラウザはWebGPUへ直接接続します。数学・物理・音響の核は独自実装です。共通物理のWebAssembly出力にはEmscriptenとC/C++標準ランタイムを使用します。[依存と配布条件](docs/legal/DEPENDENCIES.md)を記録しています。

**[ブラウザで起動](https://tatata93.github.io/pikapikaengine/) · [図解付き学習ラボ](https://tatata93.github.io/pikapikaengine/docs/learn/) · [開発状況と次の作業](docs/PLAN.md)**

`IRON FIELD`は高速ロボット戦闘のオリジナル試作。移動、上昇、ブースト、ロック射撃、敵AI、ダメージ、3波、勝敗・再出撃を実装しています。既存作品の素材や固有設定は含みません。

## ローカル起動

Node.js 22以上（検証環境24.14.1）とWebGPU対応ブラウザが必要です。外部npmパッケージのインストールは不要です。

```powershell
npm start
```

[http://localhost:8080](http://localhost:8080) を開き「出撃する」。WASDで移動、Shiftでブースト、Spaceで上昇、Fまたは左クリック長押しで射撃、Tabでロック切替、左右矢印または右ドラッグでカメラ旋回、Pで一時停止します。音声は起動操作後に開始します。

localhost以外ではHTTPSのセキュアコンテキストが必要です。WebGPU非対応・初期化失敗時には理由を表示します。教材は [docs/learn/index.html](docs/learn/index.html) を直接開いても利用できます。

「シーン編集」で箱・原本メッシュを作成し、位置・寸法・頂点を変更、Undo/Redo、JSON/共通テキスト形式の保存・読込ができます。「選択物を表示」で形状を確認できます。ゲームの進行状態ではなく編集原本を保存します。頂点編集は手動の形状変更で、材料の塑性変形ではありません。ゲームのメッシュ接触は外接AABB近似です。

公開前は `npm run build` でHTML内のimport mapと配信URLの識別子を更新します。ES module・CSS・WASMを同じビルド識別子で読み、Pagesのキャッシュに古いモジュールが残る問題を防ぎます。`npm start` はこの処理を先に実行します。

## Windows C++ビルド

Visual Studio C++20ビルドツール、Windows SDK、CMake 3.24以上を用意します。この環境ではMSVC19.51、SDK10.0.26100、CMake4.3.3で実行済みです。

```powershell
./scripts/build-native.ps1
./build/native/Release/pikapika-viewer.exe
./scripts/smoke-native.ps1
./build/native/Release/pikapika.exe init build/demo.scene
./build/native/Release/pikapika.exe move build/demo.scene 2 5 2 -20 build/edited.scene
./build/native/Release/pikapika-viewer.exe --scene build/edited.scene
./build/native/Release/pikapika.exe audio 34.3 build/direct-34m.wav
./build/native/Release/pikapika.exe audio-scene build/demo.scene build/scene-direct.wav
./build/native/Release/pikapika.exe simulate 10
./build/native/Release/pikapika.exe mesh-init build/mesh.scene
./build/native/Release/pikapika.exe mesh-vertex build/mesh.scene 1 6 2 7 2 build/mesh-edited.scene
./build/native/Release/pikapika-dynamics.exe --steps 1200 --csv build/dynamics-steps.csv
./build/native/Release/pikapika-buoyancy.exe --csv build/buoyancy-trajectory.csv
node scripts/verify-buoyancy.mjs
node scripts/verify-simulation.mjs
```

Windowsビューアは床・物体・カメラ操作の描画試作です。ブラウザの戦闘ゲームと同じ機能を備えた.exeではありません。WASD、Q/E、上下キー、Shift、Escで操作します。共通シーンの交換範囲は [設計判断](docs/adr/001-foundation.md) を参照してください。

## 検証

```powershell
npm run check
npm test
./scripts/build-native.ps1
```

固定刻みの描画30/60/120/144fps比較、連続衝突、保存・再読込、リプレイ、音の遅延/1/r振幅、教材操作を自動検証します。30fps試験は時間の正しさを調べるためで、性能目標を下げるものではありません。

ブラウザの「性能ログを書き出す」でフレーム間隔の生データ、p95/p99、最大値、予算超過をJSONに保存します。rAF間隔とCPU提出時間であり、GPU処理時間や実ディスプレイ提示回数は未計測です。**通常プレイで常に60fps以上という目標は未達・未検証であり、保証しません。** Windowsの現時点の試験は [reports/native-smoke.json](reports/native-smoke.json) と [全区間CSV](reports/native-frames.csv) を参照。

衝突と直接音のC++共通サブセットを650バイトのWebAssemblyとしてブラウザでも実使用します。Ubuntu clang18.1.3でビルドし、CI・Windows Node・実ブラウザで検証しました。ゲームロジック全体の共通化は未完です。来歴とハッシュは `assets/pikapika-core.build.json`。現地で再ビルドする場合はclang/wasm-ldと `scripts/build-wasm.ps1` を使います。

[固定条件の描画試験](https://tatata93.github.io/pikapikaengine/tools/benchmark.html) で30秒の通常移動・旋回・戦闘・多数弾の全フレームを保存できます。初回結果は [Web生ログ](reports/webgpu-benchmark.json) を参照。

## 実装範囲

- 自作ベクトル/変換、固定120Hz、球・箱の連続衝突、原本シーンと編集API。
- 原本の任意三角形メッシュ、頂点編集、WebGPU/DX12表示、v2シーンのWeb/Windows往復。[モデリング教材](docs/learn/modeling.html)。
- Nativeの6自由度剛体、球/平面の接触・摩擦・回転応答。[計算範囲と数値誤差](docs/DYNAMICS.md)。ブラウザ戦闘への接続は未完。
- 閉じたメッシュに対する静水圧・浮力・復原トルクのJS計算核。[流体モデルの仮定](docs/FLUID_MODELS.md)。動的流体/CFDではありません。
- [浮力ラボ](docs/learn/buoyancy.html)では寸法・質量・沈み位置・傾きを変更し、浮力/重力/トルクを操作で比較できます。指定姿勢の静的計算です。
- Nativeでは同じ静水圧モデルを6自由度剛体へ接続し、無接触1体の浮遊/偏心復原をCLIで検証できます。[結合モデルと誤差](docs/BUOYANCY.md)。動的な流体場や箱形状の厳密接触は未対応です。
- [動的な浮遊体実験](tools/float-lab.html)は同じC++核を実際にWebAssemblyで実行し、WebGPUへ姿勢を補間表示します。再生・停止・コマ送り・上下動/復原の切替と計測JSONを備えます。[C ABIと資源上限](docs/SIMULATION_ABI.md)。剛体の球/平面接触も汎用Web APIから呼べますが、この実験は接触なしです。
- WebGPUインスタンス描画、GGX直接光と環境光近似、露出、表示変換、霧。
- 自前発音の距離遅延・減衰、オフラインWAV。反射/残響/HRTFは未実装。
- 図解付き教材、sin/ノイズの炎操作デモ、依存・参考資料・素材台帳。

航空/車両専門モデル、オンライン対戦、外部モデル取込、リグ・モーション編集、高度な光学/音響、大規模GUIは未実装です。公開ソースですが、エンジンのOSSライセンスは未選定です。再配布条件を選定済みとは扱わないでください。詳しくは [権利台帳](docs/legal/ASSETS.md)。
