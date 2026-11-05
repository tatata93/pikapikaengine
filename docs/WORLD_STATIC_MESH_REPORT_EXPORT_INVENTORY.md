# 全Report取得の対応台帳 — 未実装

2026-11-06。primitive v1受入後、実headerと旧fixture writerを読んだ再開用の台帳。
以下は最上位recordの実member一覧。serializerの実装・全依存型のinventory完成を意味しない。
最上位Reportの取得対応と独立比較は未完。
12葉型（Vec3／Quaternion／Material／RigidBody／Plane／StaticTriangle／StaticMeshSource／
BodyLoad／TickLoadPacket／Progress／scheduler Settings／Snapshot）の44memberは
[値取得層](REPORT_VALUES_WIRE.md)で実Native有限受入。下位guard全型やReport本体の完成とは別。

| 実型 | 保持するmember |
|---|---|
| session::Pump | status, token, scheduler_calls, report |
| controlled_scheduler::PumpReport | status, reason, binding, before, after, requested_elapsed, elapsed_accepted, admitted_credit, admission_rounding_error, progress_before, progress_after, capture, original, boundaries, queue_plan, tick_reports, boundary_count, planned_attempts, attempts, committed_ticks, packets_consumed, upper_budget, work, storage, dropped_seconds, has_whole_tick_backlog |
| controlled_tick::ControlledReport | status, reason, committed, requested_dt, advanced_dt, original_progress, requested_mode, requested_tick, binding, failure, capture, staged_capture, private_after_capture, original_bodies_validated, original, mappings, staged_before, private_after, private_progress_after, child, work, storage, message |
| advance::AdvanceReport | status, reason, committed, requested_dt, advanced_dt, original_progress, proposed_progress, clock, binding, advance_profile_checked, advance_profile_matches, failure, guard, work, storage, message |
| guard::GuardResult | status, reason, binding, original_settings, failure, preparation, preparation_messages, bodies, pairs, work, reservation, initial_request, candidate_bodies, message |

根拠は `core/include/pikapika/world_static_mesh_session.hpp`、
`world_static_mesh_flight_controlled_scheduler.hpp`、`world_static_mesh_flight_controlled_tick.hpp`、
`world_static_mesh_flight_advance.hpp`、`world_static_mesh_flight_guard.hpp`。
guard下位の全typeと全memberは、次の対応作業で別に列挙してから固定する。

## 次の実装で落としてはいけないもの

- schedulerの配列全slot。boundariesは9、queue_plan/tick_reportsは各8。
  未実行tailのabsentと実拒否Reportを区別し、countだけから架空の値を埋めない。
- BoundaryのWorldStateはfixed arrayのactive prefixだけが観測値。body_count/plane_countを残し、
  未初期化の未使用RigidBody/Planeを読み出さない。元body address一致のboolは対応するactive body分。
- originalのsettings、全mesh/face、全packet/load。Report.originalのpartialと、提出envelopeの完全原本は別。
- guard::PairRecord.childのvariant ordinalと実member。MeshCall、PlaneCalls(metric/box)、SphereCallを区別。
  Callのstate/attempt_ordinal/requested_settings/used_settings/granted/grant/result/messagesを残す。
- preparation_messagesおよび全Call.messagesのfields/nonempty_fields/bytes/omitted。
  除去されたmessageを復元したり、空文字しか無かったと断定しない。
- Counterのknown/upper/exact、Reservationのretained/granted/charged。workとcapacityと実memory peakを混同しない。
- 各childの全原本、partition、frontier、audit、候補、sqrt診断。成功したchildだけを選別しない。
- F64のNaN/Infinity/負零と、full64 tick/ID。入出力診断の保存とモデルによる有効性判断は別。

旧finite writerとの比較では、JSONのcamelCaseやenum文字列とNative member名/ordinalの対応も明示する。
旧writerに無い不正elapsedのnonfinite値は別の実ケースを作り、全field対応と混同しない。
旧writerのnumber有限要求、境界の一時vector構築、CoutToのglobal std::cout差替えを製品へ移植しない。

次は全依存型のfield対応を固定して直接const値を辿る専用serializerを作る。
source header変更時の無効化、独立decoderの全値比較、所有cacheの寿命を通してからC API pumpへ進む。
この台帳自体は新しい公開API、Report export、数値モデルの完成ではない。

## 次の最小実装: 設定10型・62member（Native受入済み）

実headerを確認し、以下を同じRecord経路へ対応させた。詳細は[設定取得](REPORT_SETTINGS_WIRE.md)。
unsignedの設定値はU32、size_tはU64、doubleはF64 bitで区別する。

| 型 | 対応member |
|---|---|
| sphere_triangle::Settings | max_candidates, sqrt_refinements, max_total_sqrt_refinements, maximum_local_width, maximum_normal_width, minimum_sine_squared |
| sphere_triangle_mesh::Settings | max_surfaces, primitive |
| sphere_triangle_mesh_held_load::Settings | mesh, time_tolerance, max_evaluations, max_leaves, max_depth, enclosure_sqrt_refinements, max_total_sqrt_refinements |
| sphere_triangle_mesh_free_flight_guard::Settings | held_load, max_angular_increment |
| accelerated_pair_coverage::Settings | time_tolerance, max_evaluations, max_leaves, max_depth |
| accelerated_plane_box_coverage::Settings | time_tolerance, max_evaluations, max_leaves, max_depth |
| accelerated_sphere_box_coverage::Settings | time_tolerance, max_evaluations, max_leaves, max_depth, sqrt_refinements |
| world_static_mesh_flight::Settings | max_bodies, max_planes, max_meshes, max_total_faces, max_pairs |
| guard::Limits | body_records, pair_records, held_audits, held_certified_leaves, held_partition, held_frontier, primitive_audits, primitive_partition, primitive_frontier, last_mesh_rows, primitive_candidates, retained_faces, mesh_queries, primitive_queries, candidates_examined, sqrt_refinements, plane_metric_values, box_values, propagations, logical_payload_bytes |
| guard::GuardSettings | preparation, mesh, plane_metric, plane_box, sphere_box, contact_margin, limits |

15headerとmanifestを固定し、既存12型の3112 byte比較を保持した。
設定10型の実Release/Debug・独立参照・18schema拒否をfresh buildで確認した。
新設定の実GNUと、interval端点／Counter／WorkGrant／Retained／MessageOmission、全audit・partition・frontierは次。
この設定取得だけでinterval/audit/全Reportが取得可能になったとは報告しない。

## 次の最小実装: 計算量・保持量・省略情報7型43member（Native受入済み）

全て`world_static_mesh_flight_guard.hpp`の実宣言を確認した。設定値と、実行後の記録は別の値。
known／upper／exact、累積grantとcharged、requested capacityと実使用量を混同せずそのまま保持する。

| 型 | 対応member |
|---|---|
| guard::Counter | known, upper, exact |
| guard::HeldLedger | mesh_queries, primitive_queries, candidates_examined, primitive_sqrt_refinements, enclosure_sqrt_refinements, sqrt_refinements, mesh_sqrt_limited_rows, enclosure_sqrt_calls, enclosure_sqrt_limited_calls |
| guard::Retained | body_records, pair_records, held_audits, held_certified_leaves, held_partition, held_frontier, primitive_audits, primitive_partition, primitive_frontier, last_mesh_rows, primitive_candidates, retained_faces, logical_payload_bytes |
| guard::WorkGrant | mesh_queries, primitive_queries, candidates_examined, sqrt_refinements, propagations, plane_metric_values, box_values, plane_norm_loop_iterations_upper, bridge_calls_upper |
| guard::Reservation | retained, granted, charged |
| guard::Grant | retained, work |
| guard::MessageOmission | fields, nonempty_fields, bytes, omitted |

Counter.exactは計数が既知というflagで、物理的な分離・成功の保証ではない。
Reservation.grantedは正確な返金後に累積でlimitsを超え得る。勝手にchargedへ置換しない。
MessageOmission.fieldsは空文字も含め全visited message fieldを数える。失われたtextを復元しない。
各size_tはU64、boolはbooleanで取得し、既存3112／4587 byteの回帰を保持する。
この7型の後も、interval・全audit／partition／frontier・最上位Reportは未完。

実装と有限Native検証は[ledger取得](REPORT_LEDGERS_WIRE.md)。合計29型149member。新ledgerのGNUは別受入待ち。
次はguard::Workの22member（outer call attempts/returns、held、各Counter、bridge/root上限、exact）、
interval端点と全audit／partition／frontier、最上位Reportへ進む。全型の対応完了前にC API pumpへ接続しない。

## 次の最小実装: guard::Workの22member（Native受入済み）

実宣言は同じguard headerの78〜91行。HeldLedgerとCounterの対応完了により、
追加の数値照会や演算をせず既存Record経路から直接辿れる。

| 型 | 未対応member |
|---|---|
| guard::Work | child_calls_attempted, child_calls_returned, mesh_calls_attempted, mesh_calls_returned, plane_metric_calls_attempted, plane_metric_calls_returned, plane_box_calls_attempted, plane_box_calls_returned, sphere_box_calls_attempted, sphere_box_calls_returned, held, propagation_attempts, plane_metric_values, box_values, bridge_calls_upper, plane_norm_calls_upper, plane_norm_loop_iterations_upper, sphere_root_results_returned, sphere_root_limited_returns, sphere_sqrt_refinements, sqrt_refinements, exact |

10個のouter attempts／returnsは実wrapper記録。bridge_calls_upperとplane_norm系上限を
実計測回数へ読み替えない。全体exactと5個のCounter.exactは独立に取得し、合成・再計算しない。
実受入は新1型・異なる2recordの全typed値、全callback停止／例外／再入、
既存3112／4587／3706 byteと実行結果の全保持、15header＋manifest gate。
この22memberを追加してもReport全体のwork／storage対応が終わったことにはならない。

interval::Intervalは公開memberを持たず、lower()／upper()のconst noexcept accessorで実端点を返す。
後続段ではinterval.hppもschema review gateへ追加し、実Intervalの構築を検査用に行う経路と、
取得時に再構築・演算・環境変更をしない経路を分ける。NaNを禁止するIntervalの不変条件を
byte書換えで破って「実入力の保存試験」と呼ばない。interval対応はこのWork段には混ぜない。


Work22memberの実装・有限検証は[Work取得](REPORT_WORK_WIRE.md)。合計30型171member。

## 次の最小実装: interval端点とSqrtResult（Native受入済み）

| 実型 | 次の取得対象 |
|---|---|
| interval::Interval | lower()／upper()の実端点をF64 bitとして取得（private memberへ直接アクセスしない） |
| interval::SqrtResult | value, refinements, refinement_limited |

interval.hppをreview gateへ追加する。Interval取得は実accessorだけを呼び、再構築・計算・環境probeを行わない。
試験harnessは既存interval.cppで実値を構築してから取得する。製品serializer自体に数値coreの依存を足さない。
正規化済みの負零／正零、subnormal、最大有限値、片側／両側の無限境界と、不正構築拒否を区別する。
構築は既存の環境条件で行い、getterだけの4丸めmode保持を構築の受理へ読み替えない。
SqrtResultは真のsqrt計算による実例と、公開memberを組み合わせた診断取得例を区別し、数学証明を新規主張しない。
旧3112／4587／3706／3937 byteを保持し、独立参照と全callback失敗を確認してから全audit群へ進む。


次段のbuild方針: 取得libraryは専用2TUを維持し、実Interval/SqrtResultを構築する試験targetだけに既存interval.cppを追加する。
既存のinterval.cpp source property（strict FP/rounding）と旧20profileを変更せず、追加TUの実flags/Debug/sanitizerを記録する。
旧4種類のfixtureを同じfresh構成で再実行して比較する。新しい数値runtime bindingやWASM能力を解禁しない。


実受入は[区間取得](REPORT_INTERVALS_WIRE.md)。合計32型176項目。

## 次の最小実装: sphere_triangleの候補監査と幾何結果2型17member（Native受入済み）

| 実型 | 未対応member |
|---|---|
| sphere_triangle::CandidateAudit | feature, disposition, barycentric, kkt, kkt_count |
| sphere_triangle::Geometry | surface_id, surviving_features, barycentric, closest_local, closest, delta, normal, sphere_point, squared_distance, distance, gap, relation |

宣言は既にgateへ固定したsphere_triangle.hpp。Bounds3はarray<Interval,3>のaliasで、新しい別数値型ではない。
全3成分とkkt全2slotを原順で残し、kkt_countだけから配列を切り詰めない。maskを一意featureへ変換しない。
enum ordinalはU32 enum tag、surviving_features/kkt_countはU32、surface_idはfull64。
区間は既存accessor取得へ渡し、closestの中点や代替normalを計算しない。
最初の取得fixtureは公開値を構築した人工診断と明記し、実queryの受入やモデル正解を主張しない。
旧5fixtureの全byte/実行結果、16header+manifest gate、実Interval TUを試験だけに限定する構造を保持する。

次段の具体的な比較: CandidateAuditは異なるfeature/dispositionとkkt_countを持つ複数recordを使い、
count=0の場合も全2slotの値を残す。Geometryはfull64 ID・全U32 mask・全6組のBounds3と3区間を区別し、
maskとRelationを互いに推測しない。raw enum ordinalを含む人工診断と明記し、物理モデルの受理と区別する。
製品getterはRecord::arrayと既存Interval取得を使い、追加の数値TUや新しい演算・確保を要求しない。


実受入は[幾何取得](REPORT_GEOMETRY_WIRE.md)。合計34型193項目。

## sphere_triangle::Resultの全10member（Native受入済み）

status, reason, geometry, squared_cross, sine_squared, candidates, candidates_examined, sqrt_refinements, sqrt_refinement_limited, message。

geometryと2区間のoptionalはabsentとpresentを保持し、absentをnullや零の既定値にしない。
全candidate vectorを原順で取得し、失敗prefixを成功geometryから再構成しない。messageは空文字/NUL/任意byteを保つ。
Recordへ専用optionalとbytes経路を追加し、返却Statusの一時reentrantをWriter::status()で上書きしない。
実queryを再実行せず構築済みconst Resultを直接辿る。最初は人工診断と明示し、実数値照会の受入と分ける。
旧6fixtureと16header+manifest gateを保持し、全optional組合せ・異なるvector長・実Intervalの無限境界を独立参照で検証する。
NaN端点を内部byte書換えで捏造しない。


Result次段の具体的受入: 3optionalの全8組合せ、空/複数/重複candidateの原順、
空messageとNUL/非UTF8 byte・255/256/257byte境界を保持する。presentは実child1件とend、absentはleafだけ。
既存のsink停止/例外/再入と全値比較を通し、未完documentを完成Resultとして公開しない。


実受入は[Result取得](REPORT_RESULT_WIRE.md)。合計35型203項目。

## sphere_triangle_mesh::RowとNearestの2型6member（Native受入済み）

Row: triangle, query。元のtriangleとoptionalの実Resultを直接取得する。absent queryは未照会でありmissではない。
Nearest: squared_distance, distance, gap, possible_surface_ids。全U64 IDを原順で取得し一意winnerへ変換しない。
最初は人工診断で、query不在/存在、full64/重複/空ID集合を比較する。物理的に受理したnearestという主張をしない。
追加数値TU/照会/再構築なし、旧7fixtureを保持する。sphere_triangle_mesh.hppは既に16header gate内。
その後mesh::Resultの全12member（status/reason、failed_index/first_failed_row、rows/nearest、queries/candidates_examined/sqrt_refinements/sqrt_limited_rows/failed_rows/message）ではsize_t optionalをU64へ明示して扱う。
空row、失敗prefix、未照会optionalとnearest不在を別々に保持し、構造失敗位置から実row結果を推測しない。


次のRow/Nearestの入力例・独立比較・旧7fixture保持は[次段受入条件](REPORT_MESH_VALUES_WIRE_PLAN.md)に固定した。計画は未実装。


実受入は[mesh値取得](REPORT_MESH_VALUES_WIRE.md)。合計37型209項目。

## sphere_triangle_mesh::Resultの全12member（Native受入済み）

status, reason, failed_index, first_failed_row, rows, nearest, queries, candidates_examined, sqrt_refinements, sqrt_limited_rows, failed_rows, message。

2つのoptional size_t位置はU64として明示し、なしと0を区別する。5つの実計数もU64。
rowsは元順と未照会query/失敗prefixを保持し、nearestなしから候補を推測しない。全message byteを取得する。
人工診断で全optional組合せ・空/複数row・異なる順/重複・full64位置/計数を比較し、旧8fixtureを同じfresh構成で保持する。
全Report/新数値照会/追加TUやWASM接続を混ぜない。


mesh全Resultの具体的入力例/optional size_tのU64取得/旧8fixture保持は[次段受入条件](REPORT_MESH_RESULT_WIRE_PLAN.md)に固定した。計画は未実装。


実受入は[mesh全Result取得](REPORT_MESH_RESULT_WIRE.md)。合計38型221項目。

## 次の最小実装: heldの原入力/セル/選択body3型11member（未実装）

HeldSphere: id, position, velocity, mass, force, gravity, radius。
Cell: time_bounds, depth。WorldBodySnapshot: body, gravity。
元F/m+gを取得時に計算せず、力と重力を別々に保持する。Cellは閉じた秒の全2要素で、depthから再構成しない。
選択bodyの全RigidBody項目を保持し、回転や材料も捨てない。新しい数値照会をせず人工診断で全型/bitを比較する。
既存16header gate内のheld headerを使い、旧9fixtureをfresh Release/Debugで保持する。
その後held Snapshot/Work、全audit/partition/frontierと最上位Reportへ進む。


保持荷重の全下位13型98項目を[確認台帳](REPORT_HELD_DIAGNOSTIC_INVENTORY.md)へ列挙した。Settings取得済み以外12型91項目は未実装。最小段は[原入力/Cell/選択body](REPORT_HELD_SOURCE_VALUES_WIRE_PLAN.md)。
