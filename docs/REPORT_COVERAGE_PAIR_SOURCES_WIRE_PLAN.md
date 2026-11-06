# pair coverageの二つの元入力recordを取得する次段

2026-11-06。元のSphere/StaticPlaneの次の未実装計画。先行段が終わった場合に予定62型369項目。
accelerated_pair_coverage::SpherePairのfirst/secondとSpherePlaneのsphere/plane、2record型4項目を取得する。
既存17header gate内の実宣言を使い、新しいsource headerや数値bindingを追加しない。

first/secondの順序を保存し、対称な物理問題だからという理由でソートしない。
sphere/planeを取り違えず、raw normal/offsetと元radiusを保持する。正規化・半径膨張・F/m計算を行わない。
製品は既存field経路と原係数getterを用い、今回の2recordでInput variantを実装済みとは呼ばない。

全初期化済みSpherePair2件/SpherePlane2件の4rootを作る。
先行の元Sphere A/Bと元Plane A/Bを用い、Pairは(A,B)/(B,A)、Planeは(A,Plane A)/(B,Plane B)。
計68F64 leafと負零6か所を独立比較する。各名前の入れ子・原順と全NaN payloadを保持し、浮動小数点演算で期待値を作らない。
全scalar byte/キー、rootの交換/除去/重複、全callback停止/例外/再入、4丸めmodeと原値再取得を確認する。
人工の非有限入力を実coverageが受理したとは主張しない。

製品2TU+harness1TUでInterval TU/数値model libraryを新harnessへ結合しない。
旧20fixtureと全run出力/旧20profile/数値核/owner/SDK/sampleをfresh Release/真Debugで維持する。
17header+manifestの1受理20拒否、全getter/descriptor、GNU3TU O1 ASan-UBSanを別々に受入する。

Inputは次の別variant境界。SpherePair=0/SpherePlane=1と実active alternativeを保存する設計を先に固定する。
variant_npos/valueless状態を勝手に代替値へ修復せず、正当なC++操作による到達性と失敗時の実returned Status/Writer状態を調査する。
private byteの破壊で作った状態を実variant操作と呼ばない。再入の実Statusを失わず、全getter Statusを確認してから公開する契約を維持する。
その後Snapshot、Cell/Work、Evaluation、Audit/Partition、全Resultへ進み、guard Call/最上位Report/C API pumpへ接続する。
