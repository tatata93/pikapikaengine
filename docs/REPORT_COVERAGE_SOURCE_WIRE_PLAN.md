# coverage入力の元点係数を取得する次段

2026-11-06。FailureLocation/Failure段の次の未実装計画。先行段が完了した場合に予定60型365項目。
[依存台帳](REPORT_COVERAGE_DIAGNOSTIC_INVENTORY.md)のaccelerated::SphereとStaticPlane2型6項目を対応する。

Sphere: center, velocity, acceleration, radius。
StaticPlane: normal, offset。
点係数をそのまま取得し、F/mの再計算、normal正規化、半径のB/marginによる膨張を行わない。
各Vec3の原順と全binary64 bitsを保存し、負零・subnormal・Inf・NaNを数値判定で修復しない。
完全初期化済み人工Sphere2件/StaticPlane2件の4root、28F64 leafを独立比較する。
全scalar byte/キー、rootの交換/除去/重複、callback全境界の停止/例外/再入、4丸めmodeと原値再取得を確認する。
人工の非有限値を実数値モデルが受理したとは主張しない。

accelerated.hpp SHA256 ccc36df04a2a7fb6f617b723d9af586c84a25ee1015a035ba7f1048dd81094c1を17番目の取得source gateに追加する。
schema manifest SHAも更新し、17header+manifestの1受理20拒否を実行する。既存16headerと数値binding profileは変更しない。
製品2TU+harness1TUで新harnessにInterval TU/数値model libraryを結合しない。
旧19fixtureと全run出力/旧20profile/数値核/owner/SDK/sampleをfresh Release/真Debugで維持する。
GNU3TU O1 ASan-UBSanは別受入。登録CTest全件を実行したとは呼ばない。

その後pairのSpherePair/SpherePlaneとInput variantを宣言順に固定し、各Snapshot、Cell/Work、Evaluation、Audit/Partition、各全Resultへ進む。
先に3種類の全Resultやguard Callが完成したと主張しない。
最上位Report、C API pump、JS/WASM/game接続は別段。
