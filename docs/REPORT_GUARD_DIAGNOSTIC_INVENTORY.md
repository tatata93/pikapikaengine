# World guardの診断recordと依存台帳

2026-11-06。実宣言を読んだ後続段の台帳。**全体の取得対応は未完**。
根拠は`core/include/pikapika/world_static_mesh_flight_guard.hpp`、SHA256
`6f3b09292d2ea5503d315c1115d4180fb103e389049594dc53b848a4dd65f659`。既存16header gate内。

| 型 | 項目数 | 全member |
|---|---:|---|
| Limits（取得済み） | 20 | body_records, pair_records, held_audits, held_certified_leaves, held_partition, held_frontier, primitive_audits, primitive_partition, primitive_frontier, last_mesh_rows, primitive_candidates, retained_faces, mesh_queries, primitive_queries, candidates_examined, sqrt_refinements, plane_metric_values, box_values, propagations, logical_payload_bytes |
| GuardSettings（取得済み） | 7 | preparation, mesh, plane_metric, plane_box, sphere_box, contact_margin, limits |
| BindingInfo（Native取得済み） | 5 | mode, state, checked, profile, build_id |
| Failure（Native取得済み） | 3 | preparation, body_ordinal, pair_ordinal |
| Counter（取得済み） | 3 | known, upper, exact |
| HeldLedger（取得済み） | 9 | mesh_queries, primitive_queries, candidates_examined, primitive_sqrt_refinements, enclosure_sqrt_refinements, sqrt_refinements, mesh_sqrt_limited_rows, enclosure_sqrt_calls, enclosure_sqrt_limited_calls |
| Work（取得済み） | 22 | child_calls_attempted, child_calls_returned, mesh_calls_attempted, mesh_calls_returned, plane_metric_calls_attempted, plane_metric_calls_returned, plane_box_calls_attempted, plane_box_calls_returned, sphere_box_calls_attempted, sphere_box_calls_returned, held, propagation_attempts, plane_metric_values, box_values, bridge_calls_upper, plane_norm_calls_upper, plane_norm_loop_iterations_upper, sphere_root_results_returned, sphere_root_limited_returns, sphere_sqrt_refinements, sqrt_refinements, exact |
| Retained（取得済み） | 13 | body_records, pair_records, held_audits, held_certified_leaves, held_partition, held_frontier, primitive_audits, primitive_partition, primitive_frontier, last_mesh_rows, primitive_candidates, retained_faces, logical_payload_bytes |
| WorkGrant（取得済み） | 9 | mesh_queries, primitive_queries, candidates_examined, sqrt_refinements, propagations, plane_metric_values, box_values, plane_norm_loop_iterations_upper, bridge_calls_upper |
| Reservation（取得済み） | 3 | retained, granted, charged |
| Grant（取得済み） | 2 | retained, work |
| MessageOmission（取得済み） | 4 | fields, nonempty_fields, bytes, omitted |
| MeshCall（Native取得済み） | 8 | state, attempt_ordinal, requested_settings, used_settings, granted, grant, result, messages |
| PlaneMetricCall | 8 | state, attempt_ordinal, requested_settings, used_settings, granted, grant, result, messages |
| PlaneBoxCall | 8 | state, attempt_ordinal, requested_settings, used_settings, granted, grant, result, messages |
| SphereCall | 8 | state, attempt_ordinal, requested_settings, used_settings, granted, grant, result, messages |
| PlaneCalls | 2 | metric, box |
| PairRecord | 5 | pair_ordinal, state, reason, execution_ordinal, child |
| BodyRecord（Native取得済み） | 4 | body_ordinal, is_static, state, seed_pair_ordinal |
| GuardResult | 14 | status, reason, binding, original_settings, failure, preparation, preparation_messages, bodies, pairs, work, reservation, initial_request, candidate_bodies, message |

4つのCall実型を別々に数え、20record型157項目。現manifestでは14型112項目が取得済み、未対応6型45項目。
Childは上記recordとは別のvariant境界で、実ordinalはMeshCall=0、PlaneCalls=1、SphereCall=2。
PairRecordの元順とpair_ordinal、execution_ordinal、Call.attempt_ordinalは別々の意味で保存する。
保存順から実行順を推測せず、unexamined/nonreturnedのresult不在を再queryで埋めない。

BindingInfo.build_idは所有65char配列。文字列表示と取得するraw配列の範囲を別途契約し、隠れた末尾を暗黙に捨てない。
これは設定identityであり、実object/executableを実行時に測定したhashではない。
Failure.preparationのFailureLocationはNative取得対応済み。GuardResult.preparationの全Result/inventoryは別headerの未対応依存。
MeshCallは自由飛行Result全12項目、他3Callは各accelerated coverage Resultと全下位型の取得を必要とする。
現台帳だけでそれらの依存が取得済みとは言わない。

GuardResult.candidate_bodiesはoptional<vector<RigidBody>>。absent、presentの空列、元順の全候補を分ける。
全pairsは停止後の未照会tailも取得し、候補がある場合だけの選別や、成功childだけの抽出をしない。
省略済みmessageを復元せず、各MessageOmissionと実message byteを保存する。
上限・grant・charged・実Workを混同しない。人工保存fixtureと実guardの数値認証・実消費量は別受入。

自由飛行の全5型34項目は[全Result取得](REPORT_FLIGHT_RESULT_WIRE.md)でNative有限受入済み。
[BindingInfo/BodyRecord](REPORT_GUARD_IDENTITY_BODY_WIRE.md)の2型9項目と固定65byteの設定identityをNative有限受入。
[FailureLocation/Failure](REPORT_GUARD_FAILURE_WIRE.md)の2型6項目をNative有限受入。次は[coverageの元点係数](REPORT_COVERAGE_SOURCE_WIRE_PLAN.md)から依存順に固定し、全Call/Child/Pair/GuardResultへ進む。
最上位Report、C API pump、JS/WASM/game接続は後続。
