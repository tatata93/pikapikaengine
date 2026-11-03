# 次の受入: 参照計算と転送費用の測定

2026-11-04 JST。Node段階計測を実装・ローカル受入。全体の性能受入は未完。手動3D表示の後、robotや実時間animationへ適用する前に測定条件と正しさの条件を固定する。既存のNative最大容量prepareは秒単位の観測で、毎frame計算可能という意味ではない。

1. 実配布WASMと原著JSを使用し、runtime起動・原本FK/LBS・派生C++照会・全snapshot読出し/検査・tokenコピー・GPU upload/描画完了を区別する。測っていない内訳を差分から断定しない。ブラウザとNode、Nativeの結果を混同しない。
2. 決定的な正常入力と明示した面数/頂点数/予算を保存する。小さい帯4面からSDK上限まで、最初の実行とwarm後を分け、全反復時間・中央値・p95・最大・環境/バイナリhashを残す。例外・quality/budget失敗は成功時間へ混ぜない。制限付き/超過入力の拒否も別に記録する。
3. bufferの全bytesと入力/原本不変・statusを確認した上で測る。UI負荷やGPU frameとの同期待ちを含む数値とCPU queryだけの数値を分ける。GPUのhardware/software種別が不明なら不明とし、未測定fpsや一般性能は報告しない。
4. 最初は測定のみで、結果に基づいて最小の改善を選ぶ。高速化は独立40fixtureと36負例、実Source11の2841bit、既存skin/motion/物理/光学の回帰、全byte uploadと資源寿命を保つ。許容誤差/面積floor/不確定拒否を弱めたり、JS法線・古い成功bufferへfallbackさせたりしない。
5. robot適用は別の受入。更新時刻/頻度と予算失敗時の表示、原本編集/保存と他チャットのgame改変の統合を先に定義する。手動表示や一つの小入力での時間だけを、一般animation/物理モデルの完成へ広げない。

外部profiler/runtime/packageの導入を前提とせず、まず既存Node/browser/C++の単調時計と検証器を使う。GPU/CPUの局所性と数値精度の保証範囲は既存契約を維持する。

[Node段階計測](DERIVED_MESH_PROFILE.md)を追加した。標準100queryは全8,123,305数値をbaselineと比較し、40固定例+実Source8照会の2318Native数値bitと独立Fraction/36負例も通した。多様な小入力とdyadic shear gridを使い、SDK上限ではgrid面を繰り返す負荷であることを明示する。初回/warmupも保持したが、cold CPU/OSを制御した試験ではない。C ABI照会・getter・JS output copy・未分類残差と別token生成を保存する。実GPU upload/完了、Nativeの同条件内訳、更新頻度・robot適用は未受入。次は実ブラウザの小規模入力でCPU呼出しと全byte upload/queue完了を区別し、adapter情報を記録して計測する。実測を見てからsnapshot読出しの改善案を選ぶ。

初回の探索pilotを実行した（正式な性能受入は未完）。Node24.14.1 / i5-6500 / Windows、同一XY面を4/64/512/4096/32768面に繰り返した限定入力。各2warmup後5計測で、SDK全体の中央値は0.535/3.499/15.300/115.214/873.147ms、別のtoken検査・所有copyは0.035/0.369/2.154/14.492/95.116ms。rawと全反復・hash・recipeはreports/derived-render-performance-pilot*.json。この値をC++核単独の時間や実キャラクター/実GPU/一般fpsへ読み替えない。warmupの個別時刻は残していないため、初回cold費用・多様な形・Native/GPUと内訳測定は次段で補う。
