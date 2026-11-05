# scheduler全transaction保存と独立検査の境界

2026-11-05。**LOCAL_FINITE_FULL_TRANSACTION_PASS**。retain-only Native schedulerの全PumpReport・実AdvanceReport・実owned guardを保存し、独立検査した。fresh MSVCで11scenario／28pump、43attempt／37commit、41owned guardと2clock先行拒否を記録。独立整数RN／Fraction参照、16自己群／146改変拒否／名称・順序独立／実Python -O拒否が成功した。[正式receipt](../reports/world-static-mesh-flight-scheduler-full-verification.json)で原本と範囲を対応付ける。既存の[隔離scheduler試作](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_NATIVE.md)1382pumpとは別cohortで、全経路やGNU受入の意味ではない。

[fixture計画](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_FIXTURE_PLAN.md)、[実header](../core/include/pikapika/world_static_mesh_flight_scheduler.hpp)、[実cpp](../core/src/world_static_mesh_flight_scheduler.cpp)を読んで記す。[原著概念図](learn/diagrams/world-static-mesh-flight-scheduler-transaction.svg)は1成功後に次tickが拒否される場合を説明する例であり、実fixtureの測定traceではない。図の生成と実ブラウザー表示確認も区別する。

## 一pump全体をrollbackするAPIではない

`Scheduler::pump(world, meshes, settings, progress, elapsed)` は二つの決定を分ける。事前にcreditの全演算・queue slot・費用積を作った後、elapsedを一度受理する。その後、現在Worldからadvanceを一tickずつ呼び、返った `committed` を見てcreditを減らす。最初の拒否で止める。

`elapsed_accepted=false` の拒否ならscheduler・World・Progressを保持する。受理後の拒否なら、受理creditと既に成功したtickを保持する。一tickのadvanceは失敗原子的でも、複数tickのpump全体が入口へrollbackするわけではない。`tick_rejected` と `committed_ticks>0` は両立する。再試行はelapsed0とし、受理済みelapsedを再供給しない。未受理の入力は再提出できるが、API自体は重複配送を検出しない。

成功advanceが全bodyの保持force／torqueを一度消費するため、次の成功tickは消去済み荷重から始まる。gravityを消したり、同じ力を勝手に再投入したりしない。静的bodyも荷重消費の規則に含む。外部のper-tick入力callback／荷重供給transactionは本APIにない。

## 外部観測と内部原本chainを分ける

現在のAPIにper-tick観測hookはない。fixtureが外から保存できる実World全field・Progress・body addressは**pump前とpump後**である。候補から中間Worldを構成できても、その値を「実測中間WorldAfter」「実測per-tick pointer」と名付けない。

一方、実際に内部advanceが返したguardの `preparation.snapshot` は、その照会が捕捉したNative内部のowned原本である。この原本を、単なる推測値や新queryの結果と混ぜず、次のchainで検査する。

| 境界 | 使用する証拠 |
|---|---|
| pump入口→最初のguardありattempt | 外部WorldBefore／source／Progressと、最初の実captured-originの全field・順序・負零を対応付ける。 |
| 成功attempt→次のguardありattempt | 実candidateの全bodyを基に、commit規則でforce／torqueだけを消去した期待値と、次の実captured-originを照合する。これは内部原本chainであり、外部中間観測ではない。 |
| 拒否attempt | 直前までの成功状態を保持する。clock／環境／binding先行拒否等でguardが無い場合は、原本や数学childを捏造しない。 |
| 最後の成功prefix→pump出口 | 期待する全bodyと外部の実WorldAfterを照合し、実ProgressAfter、gravity、raw plane、mesh、元pointer／順序の保持も確認する。 |

chainの計算用に構成した期待Worldを、旧advance checkerの「実前後World」欄へ入れない。全fixed51入力・元Progressを要求するdocument入口へ新pump列を偽装することもしない。既存guard数学checkerへ渡すのは**実返却されたowned guardそのもの**と、そのcaptured-originから独立に復元した入力である。実Reportのsource・全counter・optional・全pair／audit／leaf／frontier／未照会tailまで検査する。

連続pumpの間にcallerが荷重やsourceを変更するfixtureでは、その操作と次pumpの実入力を明示する。中間chain不一致を「caller編集かもしれない」と無条件に免除しない。一つのschedulerを同じ論理World／Progressに用い、同期呼出し中の並行・再入観測／変更をcallerが排除する。busy flagはthread lockでもsignal安全な機構でもない。

## 二つのRN ledgerと未実行queue

固定stepは毎attempt同じbinary64のHである。represented creditでは `C=RN(B+elapsed)`、成功tickだけ `Cnext=RN(C−H)` をstoreする。due判定は `credit>=H` そのもので、旧FixedClockのepsilonを使わない。各加減算の厳密式との差はInterval診断に保存する。

`Progress.time` の `RN(time+H)` と、creditの加算／減算は別ledgerである。要求H、表現時計差、credit減少量がすべてbit一致すると仮定しない。整数／Fraction RN参照は入力bitsからそれぞれを再構成し、exact実数の累積時間が一致したという保証へ昇格しない。非有限elapsedはhex bitsで保存し、有限JSON数値へ置換しない。

`queue_plan` は実行前に全planned slotを作るため、拒否tickとその後のproposalも存在する。これらの減算を最終creditへ適用するのは誤りである。返却例を次のように区別する。

| 記録 | 意味 |
|---|---|
| `planned_attempts`／`queue_plan[0..planned)` | 上限まで事前に作ったproposal。実queryや成功の数ではない。 |
| `attempts`／`tick_reports[0..attempts)` | 実際に呼んだadvanceの返却。`queue_index` は連続し、最初の非commitで停止する。 |
| `committed_ticks`／`credit_consumed` | 実成功prefixだけ。拒否Reportは存在しても、そのproposal減算を消費しない。 |
| `tick_reports[attempts..8)` | 未実行ならnull。成功Report・0実費のReport・新guardで埋めない。 |
| `admitted_credit`等のoptional | 事前計算の提案が残ることもある。存在だけで受理とせず、`elapsed_accepted`を検査する。 |

sequenceはelapsed受理時に一増加し、成功tick数ではない。retain-onlyなので `dropped_seconds` は常に `+0`。step上限後のwhole backlogも保持し、`has_whole_tick_backlog` に出す。未処理backlogを0..1の描画alphaに見せたり、fmodで黙って捨てたりしない。

## planned上界・実費・保持枠

実cppは全planned slotの `UpperBudget` をchecked整数積で事前計算する。これは既存guardの**settled charged** hard上界×planned数と、guard logical payload上界の積である。拒否後の未実行slotも計画上界に残る。

各実GuardResultのknown／upper／exact、`reservation.charged`、retainedをそのまま保存し、実workと予定上界を分ける。`reservation.granted` はexact返却後のrefundを挟んだ累積要求であり、settled charged限度を超えることがある。これを同じ上界と比較したり、unknown／nonreturned blockを0実費へ置き換えたりしない。予定上界を実際の消費量とも呼ばない。

fixed optional8slotでも、各Reportのowned guardは多数のvectorを所有する。`guard_logical_payload_bytes` はReport全体・allocator overhead・使用stack／heap・RSSのhard上限ではない。実返却容量、型sizeofの論理payload、処理時間は別観測とする。実要素数が少ないことを理由にslotを返し、9回目を呼ぶことはない。

## 出自と独立検査のgate

既存advance／guardの7-source source-enforced IDと、新scheduler hpp／cppの2-source構成IDは別の識別子である。全PumpReportのscheduler binding、実AdvanceReportとnested guardのbindingをそれぞれ原値で保存する。異なるIDを同じplaceholderへ置き換えてchain成功を作らない。構成labelとactual commandを結び、7-source leaf監査がschedulerのcredit全命令を証明したとはしない。

保存時は実Reportを既存原著writerへ渡し、stdout用の再query／事前candidate適用をしない。共有writerのmain切替はtest-only境界とし、旧advance51原本のbyte回帰と独立参照を別に行う。全JSONをprivate bufferへ完成し、enum域・有限数値・UTF8・構文・stream状態を検査してから出力する。途中の壊れたstdout、失敗run、修正前の元入力を保持し、成功データへ上書きしない。

実保存契約はschema1／kind `world-static-mesh-flight-scheduler-fixtures`、flat `fixtures` 配列である。各rowは `name`／`scenario`／`frameOrdinal`／`externalEdit`、実 `input`／`inputAfter`、`worldBefore`／`worldAfter`、`progressBefore`／`progressAfter`、`schedulerBefore`／`schedulerAfter`、`elapsedBits`、完全 `report`、外部実pointerを含む `observations` を持つ。report内のqueue／attemptは8個のnullable slotを保持する。共有writerの実AdvanceReportに不足する非規範的guard messageは補足として保存し、数値証拠を別queryで補わない。`layoutSizes`（guard24型）／`advanceLayoutSizes`（5型）／`schedulerLayoutSizes` は同runのsizeof観測であり、入力fingerprintや物理heap保証と混ぜない。実保存857310Bを確認した。

独立受入は、(1) 入力bits・全credit／queue／時刻、(2) 実全Reportの型・optional・全会計、(3) 実captured-origin chainと候補、(4) 実外部pump前後World／source／Progress／pointer、(5) 実nested guardの数学、(6) writer／library／compiler／source provenanceへ分ける。実装・checkerの都合で同じ元fixtureを変更して通さない。label／順序独立、改変拒否、最適化でassertを消したcheckerの拒否も別に検査する。

今回の41実guard内ではflight／plane metric／plane-box各8、計24数学childを検査した。sphere childは0で、このcohortがsphere分岐を新たに網羅したとはしない。旧advance writerはmacroなしの51出力2979456Bが完全一致し、旧14自己／85改変拒否も成功した。選択1382観測・14改変拒否は従来credit検査の範囲で、新しい全transaction件数に転用しない。GNU／全依存sanitizer／本体CMake統合、全scheduler clock／commit機械形式証明、SDK／ゲームfixed update、TOI／接触支持応答の完了は含まない。外部依存・有料機能・既存World/FixedClock/SDKの変更も本ガイド作成には不要である。
