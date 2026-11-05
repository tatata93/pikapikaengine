# 自由飛行の終点監査を取得する次段

2026-11-06。未実装の次段。free_flight_guard::EndpointAuditの全9項目を取得する。
予定の合計は53型332項目。既存16header gateで固定された宣言を使用する。

nominal_position、nominal_allowed、exact_position、exact_allowed、exact_differenceはそれぞれ全3区間。
l1_error_boundの両端、nominal_contained/exact_contained/l1_within_tubeの各flagを別々に保存する。
候補の位置から区間やL1上界を再構築せず、flagsを位置の比較で作り直さない。
人工値の保存と実propagation/包含証明を区別する。

各3軸・各端点を識別できる複数の全初期化済み人工値と、3flagの全8有無組合せを独立比較する。
全scalar各byte/キーと全区間配列の原順・個数を改変して拒否し、全callback停止/例外/再入と4丸めmode取得を確認する。
区間はRN環境で先に構築し、getter中はprobe/再計算しない。製品2TU、新harness1TU+試験専用旧interval.cppだけ。
fresh Release/真Debugで旧15fixtureと全run出力、全getter/descriptor、16header gate、旧20profileと数値核/owner/SDK/sampleを保持する。
GNU全4TU O1 ASan-UBSanは別受入。

その後CcdFailureの符号付き基底を含むResultへ進む。現unsigned専用optional enum helperをそのまま適用しない。
全guardのcall/pair/variant、最上位Report、C API pump、JS/WASM/gameは後続。
