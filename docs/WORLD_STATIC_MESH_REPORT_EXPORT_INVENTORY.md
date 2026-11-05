# 全Report取得の対応台帳 — 未実装

2026-11-06。primitive v1受入後、実headerと旧fixture writerを読んだ再開用の台帳。
以下は最上位recordの実member一覧。serializerの実装・全依存型のinventory完成を意味しない。
各memberの取得対応と独立比較は全て未完。

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
