# 進行処理の作業量と固定バッファの記録を保存する

2026-11-07。`world_static_mesh_flight_advance::CommitWork`の15項目と`CommitStorage`の4項目をconst取得する実装。作業treeは101record型600項目＋別Input／Child variant2型。Release／真Debug各67実CTest、全10,547変更とWebをNative有限受入した。正式記録は`reports/diagnostic-wire-advance-commit-ledgers-verification.json`。新GNU・公開は別受入。

| 型 | 宣言順の全項目 |
| --- | --- |
| CommitWork | guard_queries_attempted, guard_queries_returned, pair_records_checked, call_records_checked, origin_bodies_checked, origin_planes_checked, origin_meshes_checked, origin_faces_checked, candidates_copied, candidate_validations_attempted, candidates_validated, destination_lookups, destinations_resolved, body_assignments, progress_assignments |
| CommitStorage | body_buffer_slots, destination_slots, body_buffer_sizeof_bytes, destination_buffer_sizeof_bytes |

元のsize_t計数をU64として取得する。0、1、2⁵³を超える値、最大値などを丸めず保存する。getterはadvance・衝突query・メモリ計測を実行せず、計数の加算や上限への切り詰めも行わない。

origin系の計数は、候補検査前と検査後の両照合、および途中失敗までに実際に照合したprefixを含む。異なるbodyの個数とは限らない。body_assignments／progress_assignmentsは実advanceでは全失敗時に0だが、人工fixtureの保存値をgetterが0へ補正することはない。

Storageは名前付き2固定local bufferのslotとsizeof byteだけを示す。全call frame、stack／heap使用量、RSS、物理メモリのピークを保証しない。guard.reservationとも別の記録である。

人工16 CommitWork＋16 CommitStorageの全11,967byte、SHA256 `4f1cd4715d68b0e77dda108b8b35d988535392916ca4c7fcdadab792e47cbf38`を両構成で比較した。独立304 U64 leaf、980 callback境界、停止／例外1,960件、再入1,960件、4丸めmodeと元sourceの再取得が一致した。新harnessは製品2data TU＋harness1の3TUで、Intervalと数値model libraryを結合しない。

全10,547の異なる有効文法変更を全文decodeして拒否した。scalar／key byte8,848、root順序・個数3、field値交換1,664、object field順序32。同値field交換112は拒否数に加算しない。初scannerは前段のoptional／enum個数を残したため、改変検査前の境界preconditionで失敗した。初原本・実stderr・exit1を保持し、個数を0へ修正したfresh controls002で全件を確認した。Cpp earlyの再実行は行っていない。

全Nativeは旧66＋新1の各67実CTest、51 executable target、登録124／122を要求する。旧16停止shardの実引数・240秒上限、全50種類の旧raw fixture、20profile、元sourceと保護原本を保持する。実親31569のexit0を確認し、全134 actual assertionと全raw fixtureをCppの再実行なしで独立照合した。87 source／386保護／306 baselineの全byte、前段386保護ファイルのcoverage、3TUのsource毎strict CL条件と真Debug、Windows＋2data LIBだけのlinkを維持した。最終source reviewと必須Webbuildを通して受入する。新GNUの実閉包2oracle／28 unique source／3TU全SANは準備段階であり、Linux実行成功ではない。

続いてAdvanceReport全16項目を取得する。全World Report／C API pump／今回取得のWASM・ゲーム接続、一般接触・摩擦・流体・塑性損傷・精密光学は後続である。

公開前の静的確認で、GNU log receiverに前段の変更件数2,896が1か所残っていることを発見した。実controls002とGNU driverの10,547件へ修正し、元receiverと訂正理由を保存した。fresh source-closure-002で実2oracle／28 sourceと訂正後receiverを確認した。これは実GNU失敗やGNU実行成功の記録ではなく、全Nativeのcaptured sourceも変更していない。次段の条件は`REPORT_ADVANCE_RESULT_WIRE_PLAN.md`を参照する。
