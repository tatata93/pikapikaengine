# World進行結果の取得依存台帳

2026-11-07。実`world_static_mesh_flight_advance.hpp`と取得schemaを照合した台帳。Failure／ClockAuditの99型581項目は各66実CTest／3,196変更／Web、実GNU、全18CIとPages公開READYまで受入済み（source `84b743dfdd248ce610798b75872bd3d6cf485137`）。CommitWork／CommitStorageの状態は下表と最新PLAN／formalを優先する。この文書は数値モデルの認証ではない。

| 実型 | 項目数 | 宣言順の全member | 状態 |
| --- | --- | --- | --- |
| Progress | 2 | time, ticks | 既存取得済み |
| Failure | 2 | stage, object | Native／GNU／公開受入 |
| ClockAudit | 4 | time_sum, represented_difference, sum_rounding_error, represented_dt | Native／GNU／公開受入 |
| CommitWork | 15 | guard_queries_attempted, guard_queries_returned, pair_records_checked, call_records_checked, origin_bodies_checked, origin_planes_checked, origin_meshes_checked, origin_faces_checked, candidates_copied, candidate_validations_attempted, candidates_validated, destination_lookups, destinations_resolved, body_assignments, progress_assignments | Native有限受入、GNU別受入 |
| CommitStorage | 4 | body_buffer_slots, destination_slots, body_buffer_sizeof_bytes, destination_buffer_sizeof_bytes | Native有限受入、GNU別受入 |
| AdvanceReport | 16 | status, reason, committed, requested_dt, advanced_dt, original_progress, proposed_progress, clock, binding, advance_profile_checked, advance_profile_matches, failure, guard, work, storage, message | 未実装 |

最初の小段はFailure2／ClockAudit4の2型6項目。Stage全6ordinalと未知値、objectの欠損／存在を保存し、guard::Failureと型を混同しない。ClockAuditの3Intervalは既存の端点getterを使い、元のrepresented_dt bit列を保存する。取得時にIntervalを再構築したり、時刻の和・差・丸め誤差を計算し直したりしない。

time_sumは元時刻＋要求H、represented_differenceは提案時刻−元時刻、sum_rounding_errorは提案時刻−（元時刻＋H）を囲む診断である。represented_dtはRN差でHと異なる場合があり、累積物理時間の厳密値や誤差の補正値と見なさない。人工値の取得では、これらの数値関係をgetterが補正しない。

次にCommitWork15／CommitStorage4を保存する。origin系の計数は候補検査前後の両照合と実際に照合したprefixを含み、異なるbodyの個数ではない。実advanceでは失敗時のbody_assignments／progress_assignmentsは0だが、人工保存値をgetterが0へ変換しない。Storageのsizeof byte値は名前を持つ2固定local bufferだけを示し、全call frame・stack／heap・RSS・物理peak memoryの保証ではない。

最後にAdvanceReport全16項目を保存する。committed、advanced_dt、提案Progress、clock、failure、guardを独立に保存し、statusから欠損や値を作らない。guardのbindingだけでadvance固有の構成gateが合格したことにせず、advance_profile_checked／matchesを保持する。messageは元の長さ付きbyte列とする。取得はWorldを進めず、body／Progressを書き換えない。

GuardResult97型575項目の受入を前提に、Failure／ClockAuditの2型6項目で99型581項目を受入済み。CommitWork／CommitStorage2型19項目も101型600項目としてNative有限受入した。全Report16項目では102型616項目を予定する。Input／Childの別variant2型はrecord数に混ぜない。段階ごとの実状態は表とformalに従い、予定数を受入済みの数と混同しない。全Reportの次段条件は`REPORT_ADVANCE_RESULT_WIRE_PLAN.md`を参照する。

今後の親NativeにはRootのcontracts＋16stopが同じexecutableを共有する。旧65実CTestと49targetの違いを保持し、全argumentが--run／一target一CTestと仮定しない。実canonical JSONText、全raw fixture、20profile、全callback停止／例外と再入・4丸めmode、保護原本とsourceを依存順に維持する。実測した件数・byte・shardだけを受入へ固定する。
