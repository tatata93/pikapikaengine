# World guardの3種類のcoverage Resultに必要な取得依存

2026-11-06。後続依存台帳。BindingInfo/BodyRecordの有限受入後に実宣言を確認した。
元係数・3Settings・pair元入力2record・pair Snapshot/Cell/Work/Audit/PartitionLeafをNative取得対応済み。Input variantもNative取得対応。残るrecordは依存順に対応する。
この台帳だけで取得対応済み・数値モデル検証済みとは主張しない。

根拠headerとSHA256:

| header（core/include/pikapika/） | SHA256 | 現在の取得gate |
|---|---|---|
| accelerated.hpp | ccc36df04a2a7fb6f617b723d9af586c84a25ee1015a035ba7f1048dd81094c1 | 17番目として固定、元係数取得をNative有限受入 |
| accelerated_pair_coverage.hpp | e5de3e36093b8287abab924c5f2cbcd50906e8c046f81ab31ae73b17a78a3e9b | 既存16header内 |
| accelerated_plane_box_coverage.hpp | 977e0085d30947e46abdd8e5ca3ee1b0328b310689e86efe10d84b697f15b544 | 既存16header内 |
| accelerated_sphere_box_coverage.hpp | b1095fca311ac2eb4a1b6d464e85945d11ae82d2ae86ab59c5547cef5fbd7ada | 既存16header内 |

| namespace | record型 | 項目数 | 全member |
|---|---|---:|---|
| accelerated | Sphere（Native取得済み） | 4 | center, velocity, acceleration, radius |
| accelerated | StaticPlane（Native取得済み） | 2 | normal, offset |
| accelerated_pair_coverage | Settings（取得済み） | 4 | time_tolerance, max_evaluations, max_leaves, max_depth |
| accelerated_pair_coverage | SpherePair（Native取得済み） | 2 | first, second |
| accelerated_pair_coverage | SpherePlane（Native取得済み） | 2 | sphere, plane |
| accelerated_pair_coverage | Snapshot（Native取得済み） | 3 | input, horizon, settings |
| accelerated_pair_coverage | Cell（Native取得済み） | 3 | time_bounds, depth, parent_audit |
| accelerated_pair_coverage | Audit（Native取得済み） | 6 | cell, call_attempted, value, outcome, blocked_reason, split_time |
| accelerated_pair_coverage | PartitionLeaf（Native取得済み） | 4 | cell, state, audit_index, blocked_reason |
| accelerated_pair_coverage | Work（Native取得済み） | 4 | value_calls_attempted, value_calls_returned, plane_norm_calls_upper, plane_norm_loop_iterations_upper |
| accelerated_pair_coverage | Result | 12 | status, reason, snapshot, snapshot_validated, failed_input, partition_complete, audits, partition, frontier, current, work, message |
| accelerated_plane_box_coverage | Settings（取得済み） | 4 | time_tolerance, max_evaluations, max_leaves, max_depth |
| accelerated_plane_box_coverage | Input | 4 | sphere, plane, position_error, contact_margin |
| accelerated_plane_box_coverage | Snapshot | 3 | input, horizon, settings |
| accelerated_plane_box_coverage | Evaluation | 4 | tube_coordinates, distance, threshold, gap |
| accelerated_plane_box_coverage | Cell | 3 | time_bounds, depth, parent_audit |
| accelerated_plane_box_coverage | Audit | 6 | cell, call_attempted, evaluation, outcome, blocked_reason, split_time |
| accelerated_plane_box_coverage | PartitionLeaf | 4 | cell, state, audit_index, blocked_reason |
| accelerated_plane_box_coverage | Work | 2 | value_calls_attempted, value_calls_returned |
| accelerated_plane_box_coverage | Result | 12 | status, reason, snapshot, snapshot_validated, failed_input, partition_complete, audits, partition, frontier, current, work, message |
| accelerated_sphere_box_coverage | Settings（取得済み） | 5 | time_tolerance, max_evaluations, max_leaves, max_depth, sqrt_refinements |
| accelerated_sphere_box_coverage | Input | 5 | first, second, first_position_error, second_position_error, contact_margin |
| accelerated_sphere_box_coverage | Snapshot | 3 | input, horizon, settings |
| accelerated_sphere_box_coverage | Evaluation | 9 | first_coordinates, second_coordinates, delta, raw_squared_distance, nonnegative_squared_distance, root, distance, threshold, gap |
| accelerated_sphere_box_coverage | Cell | 3 | time_bounds, depth, parent_audit |
| accelerated_sphere_box_coverage | Audit | 6 | cell, call_attempted, evaluation, outcome, blocked_reason, split_time |
| accelerated_sphere_box_coverage | PartitionLeaf | 4 | cell, state, audit_index, blocked_reason |
| accelerated_sphere_box_coverage | Work | 7 | value_calls_attempted, value_calls_returned, sqrt_results_returned, sqrt_refinements_returned, sqrt_limited_returns, sqrt_refinements_upper, exact |
| accelerated_sphere_box_coverage | Result | 12 | status, reason, snapshot, snapshot_validated, failed_input, partition_complete, audits, partition, frontier, current, work, message |

29record型142項目のうち、既存取得は3Settings＋元係数2型＋pair入力2型＋pair Snapshot/Cell/Work/Audit/PartitionLeafの12record型43項目。残る17record型99項目。
pair::InputはNative取得済みの別variant境界で、SpherePair=0、SpherePlane=1を固定する。
空/原順/全tailとabsentを保持し、未返却のvalue/evaluationを再計算で埋めない。
snapshot_validatedはResult側の独立flagであり、保存された不正入力を有効な軌道へ修復しない。

元係数Sphereのaccelerationは呼出者の点係数であり、getterでF/mを計算しない。
StaticPlaneのnormal/offsetを正規化しない。normalの計量値とplane boxの固定ASTによるgapを混同しない。
二つの宣言Bと明示margin、元半径、rootの全SqrtResultとdistanceの保存コピーを別々に取得する。
不一致な人工コピーもそのまま保存し、実数値モデルがその組合せを生成したとは呼ばない。

Workのwrapper実呼出数、private normの上限、返却したrootの観測数、未知blockを含むsqrt上限とexactを区別する。
getterが未観測rootを推測したり、実消費量を上限と同一視したりしない。
Cellの閉じたglobal秒、parent_audit、Audit原順、Partition全leaf、frontier、currentを保持する。
配列の両端や一部の成功leafだけで全coverageを復元しない。

実装は元係数、各source/snapshot、小型cell/work、評価record、監査/区画、各全Resultの順で小分けにする。
元係数2型6項目をNative有限受入し合計60型365項目。[SpherePair/SpherePlane](REPORT_COVERAGE_PAIR_SOURCES_WIRE.md)も2型4項目をNative有限受入。[明示拒否](DIAGNOSTIC_WIRE_REJECTION.md)と[Input variant](REPORT_COVERAGE_INPUT_VARIANT_WIRE.md)もNative有限受入。[Snapshot](REPORT_COVERAGE_SNAPSHOT_WIRE.md)の3項目も取得対応。[Cell/Work](REPORT_COVERAGE_CELL_WORK_WIRE.md)2型7項目も取得対応。[Audit/PartitionLeaf](REPORT_COVERAGE_AUDIT_PARTITION_WIRE.md)2型10項目も取得対応。次は[全pair Result](REPORT_COVERAGE_PAIR_RESULT_WIRE_PLAN.md)12項目。
getterと新harnessに数値model libraryを追加しない。Interval値の人工構築に旧TUが必要な段だけ試験側へ明示して分ける。
全依存を保存できてからguardのPlaneMetricCall/PlaneBoxCall/SphereCallへ接続し、その後Child/Pair/GuardResult/最上位Reportへ進む。
