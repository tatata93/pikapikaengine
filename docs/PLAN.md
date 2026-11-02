# 現在地と再開位置

更新: 2026-11-03。製品仕様は `PROJECT_SPEC.md`。この記録は実装した範囲と未完を区別する。ユーザーは節目でのGitHubプッシュ・起動リンク・継続開発を明示的に指示している。

## 実行できる入口

- 公開ブラウザ: https://tatata93.github.io/pikapikaengine/ （Pages設定済み。公開応答・起動の最新結果はreports参照）
- ローカル: `npm start` → http://localhost:8080
- 教材: `docs/learn/index.html` / `flame.html`
- Windows: `./scripts/build-native.ps1` → `build/native/Release/pikapika-viewer.exe`
- CLI: `build/native/Release/pikapika.exe help`

## 最初の受入項目

| 段階/仕様 | 現在の実体 | 検証と残り |
|---|---|---|
| M0 ビルド・方針・資料 | CMake/Node入口、原仕様、ADR、依存/素材/出典台帳 | ローカルビルド実行済み。OSSライセンス未選定、配布バイナリのランタイム同梱監査が残る |
| M1 数学・時間 | C++ Vec3/Quaternion/Transform/FixedClock、JS math/time | CTest13検証群。JS描画30/60/120/144周期比較、リプレイ一致 |
| M1 シーン | C++版付きテキスト、Web原本JSON、camera/source/listener、共通形式アダプタ、編集API | 生成→変更→保存→再読込、Web原本→native CLI変更→Web再読込。ID/位置/色保持を実行確認。Webの回転はYのみ |
| M1 描画・入力 | Windows DirectX12 + 自作WebGPU/WGSL、手続き床・箱・ロボット | DX12実GPU120フレームとGPU読戻し画像。IABでWebGPU起動・移動・射撃・停止を確認。視覚/操作の網羅試験は未完 |
| M1 固定運動 | 120Hz、補間、軸別箱接触、球/箱の連続衝突 | 高速すり抜け、周期差テスト。ブーストはゲーム用制御。汎用剛体ではない |
| M1 音響 | 自作PCMインパルスWAV、d/c遅延と1/r振幅、Web操作後の発音 | 遅延・分数サンプル・倍距離-6.0206dB・WAVテスト。聴感未確認、移動経路の継続更新未実装 |
| M1 CLI | init/inspect/move/roundtrip/audio/audio-scene/simulate | 実行済み。GUIとCLIが全く同じ内部コードである段階には未到達 |
| M1 Native/WASM | C++共通C ABIをnative/Webから実使用、650B WASM、CI | 現地clang/wasm-ldなし。Ubuntu clang18.1.3で実コンパイル、CI/Windows Node/ブラウザで実行。来歴・source/binary SHA256を固定。ゲーム全ロジックのC++共通化はM2残件 |
| M1 性能 | Web生ログJSON、Native生CSV・p50/p95/p99/最大/超過 | Native loop p95 17.9802ms、p99 18.8144ms、max29.1888ms、63/120超過。60fps目標未達。GPU/実提示未測定 |
| M1 教材 | 図解4項目と検索、炎4モード・波形・パラメーター・停止/コマ送り | 教材9テスト成功。IABで入口・図・炎の再生・コマ送り・振幅・リセットを確認、画像保存 |
| サンプル初版 | オリジナルIRON FIELD、移動/ブースト/上昇/ロック射撃/敵/3波/勝敗/再出撃 | 純粋シミュレーションとブラウザ実操作を確認。Native版の戦闘未実装 |
| 制作A 初段 | 箱の生成・位置/寸法・Undo/Redo・JSON/共通形式 | 編集/保存再読込あり。頂点・面/押出し/UV/地形/原本メッシュは未実装 |

## 次の最小マイルストーン

1. M1縦断の実装・試験は成立。公開PagesでC++ WASM起動・出撃・移動・射撃・撃破を確認済み。次の実装対象は下記M2制作A。製品全体の完成、全作品60fps達成、音の聴感確認と混同しない。
2. 初回Web30秒試験を reports/webgpu-benchmark.json に保存。1800フレーム、p95=16.755ms、p99=16.785ms、max=17.465ms、厳密予算超過1193件。GPU/実提示未計測で合格にしない。初回の負の開始間隔を含む試験も別ログに保持。今後はGPUタイムスタンプと実提示・音声負荷を含め、Native超過の原因を分解する。
3. M2制作A: 任意メッシュの原本と箱頂点編集→保存→再読込→Web/Windows表示の最小縦断を作る。変更に追従する衝突/音響派生データを明示する。
4. M2制作B: 少数ボーン/キーの原本・時間サンプリング・保存を作り、30/60/120描画で同じ姿勢/イベントを検証する。
5. サンプルは上記エンジン機能を使って更新。別チャット由来の変更があれば先に確認・統合する。

## 残っている製品目標

M2: 同一ゲームロジックをWindows/Webへ出力、共通アセット・入力・音声、モデリングとモーション、許諾済みglTF導入。M3: 基礎光学の参照比較、影、反射・残響、視認性、性能。M4: 権威サーバー・PC/Web通信、予測と補正、精密シミュレーション拡張。M5: 高度光学・音響・気象・大世界。M6: 同じ編集APIを使う人間向けGUI。各分野の詳細要件は原仕様に保持し、この短い記録で削除したことにしない。

## 継続時の注意

30分heartbeatがこのチャットに設定済み。これは実行環境が利用可能なときの再開であり、無停止の無期限稼働を保証しない。能動goalも継続中。進捗がない同じ通知を繰り返さない。課金・有料契約・フォーラム投稿・メール操作は禁止。公開repoの標準GitHubホストrunnerのみ利用し、追加artifact/cache保存や課金設定は作らない。

初回push: `358870e`。それ以降のコード版はgit logで確認。実績に先行して完了チェックを付けない。

現在の動作確認済み公開版: https://tatata93.github.io/pikapikaengine/?v=9064a2f 。HTML自体もPagesにキャッシュされるため、節目の起動リンクには版のクエリーを付ける。9064a2fの公開CI・Pages deployment成功を確認済み。画像 reports/public-iron-field.png。Nativeでも同じassets/iron-field.sceneを読込・52形状描画し、120提出成功。ただし重いフレームはp95 26.9045ms、p99 53.9267ms、max75.2425ms、60/120超過。全ログはreports/native-arena*へ保存し、未判定の原因は今後調査する。
