# 保持荷重の全監査行と区画レコードの取得条件

2026-11-06。未実装の次段。小型証明4型の次に、実held headerのCellAudit18項目とPartitionLeaf4項目を取得する。
予定の合計は49型287項目。全held Resultはその後の別段。

| 型 | 全member |
|---|---|
| CellAudit | kind, cell, time, outcome, path_bounds, point_bounds, anchor, mesh_queried, mesh_status, mesh_reason, distance, displacement_squared_bound, error_squared_bound, displacement_root, error_root, clearance_certificate, penetration_certificate, work |
| PartitionLeaf | cell, state, audit_index, blocked_reason |

まず専用Recordへoptional配列とoptional enumの明示経路を追加する。
optional Bounds3はabsentかpresentに全3区間のarrayを1個だけ入れる。
optional enumはabsentかpresentに実ordinalのenum tagを1個だけ入れる。U32 scalarへ暗黙変換しない。
どちらもpresentのendとarrayのendを区別し、callbackが返したStatusを保持する。
非存在を零/null/空配列で補わず、全到達値の寿命と不変性を呼出側の契約にする。
既存optional_countは監査indexの全U64を保存する。
schemaと全getter照合の検査器は新しいformを明示的に認識する。

CellAuditのkind/outcome、PartitionLeafのstate/blocked_reasonは別のenumとして保存する。
Bounds3の全軸、anchor、全距離/平方量/平方根/証明区間を原値のまま保持する。
workはこの監査行の差分。取得時に他行のWorkやResult.workへ合算しない。
未照会や未返却と実status/reasonの有無を、mesh_queriedと別々に保持する。
PartitionLeafの所属audit_indexなしと0を区別し、未解決理由を消さない。

初fixtureは構築済み人工診断。CellAuditの12optionalについて全なし/全ありと各1項目だけありの14recordを用意する。
独立した有無maskは0、4095、1<<k（k=0..11）。全12memberの両分岐に加え、任意2memberの全4有無組合せを含む。
参照側で66組×4=264のpair組合せの被覆を確認する。全4096組合せを実行したとは主張しない。
各memberのpresent/absentを独立比較し、これらをモデルが返した有効な組合せとは紹介しない。
PartitionLeafはindexなし/0/53bit超/U64最大と、異なるstate/reasonを含む複数record。
公開doubleとenum ordinalのraw域、実Intervalの構築域を区別し、全値を初期化する。
optional配列の全軸入替・削除・重複、present/absentとnull、enum tagとU32 tagの区別を実byte改変で拒否する。
全scalar byteとkey、record順と個数も検査する。

全callback停止/例外/再入と4丸めmode取得、全byte再取得を確認する。
Interval構築は丸めmode変更前、getterはconst端点取得のみ。製品は2TU、試験専用旧interval.cppを明示linkする。
fresh Release/真Debugで旧12fixtureの3112/4587/3706/3937/1037/3241/12924/5414/20256/2507/4907/2487byteと全run出力を保持する。
16header+manifest gate、全descriptor順、旧20profile、数値核/owner/SDK/sampleを維持する。
GNU通常/真Debug/全TU O1 ASan-UBSanとNative全byte一致は別受入。

完了後held全13型98項目の12型73項目が対応する見込みで、残るResult25項目は別段。
全証明島・全partitionとtail・全frontier・全auditsのコンテナはResultで取得する。
この計画は最上位Report、C API pump、JS/WASM/game接続の実装ではない。


Native実装の有限検証を行った履歴計画。実結果はREPORT_HELD_AUDITS_WIRE.mdと正式verification JSONを参照。新GNUと全held Resultは別受入。
