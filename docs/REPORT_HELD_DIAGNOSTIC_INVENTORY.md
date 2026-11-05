# 保持荷重診断の下位型と全memberの確認台帳

2026-11-06。実宣言を読んだ対応順の台帳。**表全体の取得対応は未完**。
根拠は`core/include/pikapika/sphere_triangle_mesh_held_load.hpp`、SHA256
`d01f2e623767bb125379ac3269003c6efa98e14cdbf2815c7f1909c036573d5d`。
既存16header gateで固定している。同名のguard::Work/Settingsとは別型。

| 型 | 項目数 | 全member |
|---|---:|---|
| HeldSphere | 7 | id, position, velocity, mass, force, gravity, radius |
| Settings（取得対応済み） | 7 | mesh, time_tolerance, max_evaluations, max_leaves, max_depth, enclosure_sqrt_refinements, max_total_sqrt_refinements |
| Cell | 2 | time_bounds, depth |
| Snapshot | 4 | input, horizon, triangles, settings |
| WorldBodySnapshot | 2 | body, gravity |
| Work | 11 | mesh_queries, primitive_queries, candidates_examined, primitive_sqrt_refinements, enclosure_sqrt_refinements, sqrt_refinements, sqrt_refinements_upper, mesh_sqrt_limited_rows, enclosure_sqrt_calls, enclosure_sqrt_limited_calls, exact |
| CellAudit | 18 | kind, cell, time, outcome, path_bounds, point_bounds, anchor, mesh_queried, mesh_status, mesh_reason, distance, displacement_squared_bound, error_squared_bound, displacement_root, error_root, clearance_certificate, penetration_certificate, work |
| InitialProof | 3 | lower_gap_certificate, upper_gap_certificate, audit_index |
| CertifiedLeaf | 3 | cell, lower_gap_certificate, audit_index |
| Witness | 7 | cell, time, exact_path_bounds, anchor, error_upper, upper_gap_certificate, audit_index |
| EntryWindow | 5 | time_bounds, time_width, path_bounds, l1_diameter_bound, witness_audit_index |
| PartitionLeaf | 4 | cell, state, audit_index, blocked_reason |
| Result | 25 | status, reason, failed_index, snapshot, world_body, acceleration, whole_path_bounds, whole_velocity_bounds, initial, initial_separation_proven, certified_leaves, safe_prefix, best_witness, window, candidate_surface_ids, partition, frontier, current, audits, last_mesh, last_mesh_audit_index, work, partition_leaves, maximum_depth, message |

宣言上は13型98項目。Settingsの1型7項目だけが現在の取得対応済みで、残る12型91項目を依存順に対応する。
最小段は[HeldSphere/Cell/WorldBodySnapshotの3型11項目](REPORT_HELD_SOURCE_VALUES_WIRE_PLAN.md)。
その後Snapshot/Work、証明の小型record、CellAudit/PartitionLeaf、Resultへ進む。

次の型を扱う前に必要な取得経路を決める。

- optional Bounds3とoptional array<double,2>は、presentの中に原順arrayを1個だけ置く。中点や再構築値にしない。
- optional mesh Status/Reasonは実ordinalのenum tag。U32 scalarへ暗黙変換して区別を失わない。
- optional audit_index/failed_index/last_mesh_audit_indexは既存optional_countのU64経路を使う。
- Work.exactとsqrt_refinements_upperは実返却情報。既知実回数に置換しない。auditのWorkは差分、ResultのWorkは集計。
- certified_leavesは全証明島、partitionは全[0,H]とtail、frontierは証拠時刻より後の未照会も保持する。
- safe_prefixなしと[0,0]は別。last_meshなしを再queryで補わず、実所属audit_indexと一緒に保持する。
- EntryWindow.l1_diameter_boundの下端は物理的変位/侵入/誤差の下限ではない。ラベルを変更しない。

getterの契約は構築済みで全到達値が初期化されたconst診断。人工fixtureでも配列や証明recordの全memberを明示的に初期化する。
この表は値の観測範囲を定めるもので、数値モデルの新認証、最上位Reportの全対応、C API pump/JS/WASM/game接続ではない。
