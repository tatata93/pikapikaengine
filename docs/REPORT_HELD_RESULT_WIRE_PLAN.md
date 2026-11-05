# 保持荷重Result全25項目の取得条件

2026-11-06。未実装の次段。全下位型の対応後に実held::Resultを取得する。
予定の合計は50型312項目。held headerの13型98項目が対応する見込みで、最上位Reportはまだ後続。

| member | 取得経路 |
|---|---|
| status, reason | enumeration |
| failed_index | optional_count |
| snapshot, world_body | optional |
| acceleration, whole_path_bounds, whole_velocity_bounds | optional_array（全3区間） |
| initial | optional |
| initial_separation_proven | field |
| certified_leaves | array |
| safe_prefix | optional_array（秒の全2要素） |
| best_witness, window | optional |
| candidate_surface_ids, partition, frontier | array |
| current | optional |
| audits | array |
| last_mesh | optional |
| last_mesh_audit_index | optional_count |
| work | field |
| partition_leaves | count |
| maximum_depth | field |
| message | bytes |

元snapshot/world_bodyと計算結果を別々に保持する。元の力/質量/重力から値を作り直さない。
acceleration/path/velocityの全3軸、全証明島、全区画とtail、証拠時刻より後の未照会frontierも取得する。
candidate_surface_idsは全U64の元列を保持し、人工診断の並べ替えや重複除去を行わない。
safe_prefixなしと[0,0]、currentなし、last_meshなしと未返却の所属indexを別々に残す。
取得時にlast_meshを再照会せず、auditsのWork差分をResult.workへ合算しない。
実計数・上限・exact・最大深さ・本文を保持し、enumや診断失敗を成功へ修復しない。

初fixtureは全到達値を初期化した人工Result。外側13optionalの全なし/全あり/各1項目だけありを含む15recordを独立比較する。
maskは0、8191、1<<k（k=0..12）。任意2optionalの78組×4=312有無組合せを参照側で確認する。
全8192組合せの実行とは呼ばない。実モデルが返した有効な組合せとも区別する。
各コンテナは空/複数/異なる原順/重複を含み、欠けたtail・島・候補・監査行を全値比較と順序/個数改変で拒否する。
失敗位置/所属indexなし・0・53bit超・U64最大、空/NUL/非UTF8本文と256byte出力境界を含む。
本文の各byte、全scalar各byteとkey、root record、present/absent/null、配列軸、全コンテナ構造を検査する。
人工取得fixtureと実queryの数値認証・最大保持量/性能の測定を分ける。

製品2TUのconst取得だけを使い、試験専用旧interval.cppを明示linkする。
全callback停止/例外/再入と4丸めmode取得を確認する。Intervalはmode変更前に構築する。
fresh Release/真Debugで旧13fixtureの3112/4587/3706/3937/1037/3241/12924/5414/20256/2507/4907/2487/14275byteと全run出力を保持する。
16header+manifest gate、全descriptor順、旧20profile、数値核/owner/SDK/sampleを維持する。
GNU通常/真Debug/全TU O1 ASan-UBSanとNative全byte一致は別受入。

その後free_flight_guardのSnapshot/Tube/EndpointAudit/ResultとCcdFailureの取得範囲を実宣言から別に固定する。
元bodyの半径とtube.guard_radius、inflated内の別snapshotを混ぜない。candidateとendpointの有無も別々に保持する。
続いてguardの全下位call/audit/pair/variant、最上位Reportの全境界・未実行tailと会計へ進む。
全Report取得の受入前にC API pumpを接続せず、失敗取得を物理状態のrollbackと呼ばない。
この計画はC API pump、JS/WASM/game接続の実装ではない。


Native実装の有限検証を行った履歴計画。実結果はREPORT_HELD_RESULT_WIRE.mdと正式verification JSONを参照。保持荷重13型98項目の保存範囲を確認し、新GNU/最上位Report/C API pumpは別受入。
