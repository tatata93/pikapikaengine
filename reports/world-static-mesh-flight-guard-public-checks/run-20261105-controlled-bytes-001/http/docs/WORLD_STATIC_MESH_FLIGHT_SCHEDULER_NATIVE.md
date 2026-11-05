# 拒否tickの時間を残すNative scheduler

2026-11-05。**FINITE_NATIVE_MSVC_GNU_ACCEPTED**。正式独立libraryをMSVC mainで局所受入し、修正source c29a3c4の[GNU実検証](../reports/world-static-mesh-flight-scheduler-gnu-verification.json)も成功した。GNU13.3 x86-64の38command／225秒、通常版と全40core＋独立scheduler1＋全harnessのO1 ASan／UBSanで、両側13群1382観測・全28／16自己146拒否・旧51／85拒否、actual full Debug拒否、source／compiler／通常artifact保持を確認した。same-ABI通常／計装版の全記録比較は明示2identity familyの112leafだけを除外し、selected1382は除外なしで一致した。公開237件5327795Bと実READYも確認。全portable-coreも906秒で48CTest／693Node skip0・旧48warning全診断multiset不変が成功し、Engine全3job／全stepとPages全jobの成功を確認した。新SDK／WASM／ゲーム接続、完全clock／commit機械証明や一般応答は含まない。

以下は各段の履歴である。2026-11-05。**LOCAL_FINITE_MAIN_SCHEDULER_PASS**。正式CMakeへ独立 `pikapika_world_static_mesh_flight_scheduler` libraryとtest／full serializerを登録した。fresh main build/wfsm1の17command、実ReleaseとDebug core、新CTest1、全28記録／16自己146拒否、旧51全byte／85拒否が成功した。[正式main receipt](../reports/world-static-mesh-flight-scheduler-main-verification.json)を参照。全48CTestは登録数で、旧47件をこのrunで再実行したとはしない。GNU／全依存sanitizer／SDK／ゲーム接続は後続である。

正式統合source8a69932はPages配信237件と実READY起動を確認した。新GNU通常4target build／旧7source実artifact監査も通過したが、後続Werror再compileの引数輸送で失敗した。実ログと修正は[GNU実行計画](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_GNU_PLAN.md)と[原失敗](../reports/world-static-mesh-flight-scheduler-recipes/run-20261105-gnu-failure-001/receipt.json)、[局所8検査](../reports/world-static-mesh-flight-scheduler-recipes/run-20261105-gnu-replay-fix-003/freeze.json)へ分ける。この先行失敗時点ではGNU受入は未完だった。後続c29a3c4の成功は冒頭の別receiptで確定し、Pages成功とも分ける。

以下は隔離試作からの契約と有限検証の履歴。**FINITE_ISOLATED_PROTOTYPE_PASS**。既存の[advance](WORLD_STATIC_MESH_FLIGHT_ADVANCE_NATIVE.md)を一回ずつ呼び、成功したtick分だけ時間creditを減らす小さいNative APIを実装した。[計画](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_PLAN.md)は作成時の契約、[試作実行記録](../reports/world-static-mesh-flight-scheduler-recipes/README.md)は今回の結果である。隔離段時点では本体CMake／GNU／sanitizer／SDK／ゲームへの統合は未完だった。現在のmain局所受入と分ける。

`world_static_mesh_flight_scheduler::Scheduler` の `pump` は、World・mesh原本・GuardSettings・Progressとelapsed秒を受け取る。固定stepは既定binary64の1/120秒、許容 `[2^-20,.1]`、attempt上限は既定4／hard8。全queue算術と返却slotを入力受理前に準備し、入力受理・成功tick・最初の拒否を別に報告する。

elapsedを受理した後のguard拒否ではcreditを保持する。再試行はelapsed0で行う。cap等で入力受理前に失敗した場合は全状態不変で、元elapsedを再提出できる。複数tickの途中で拒否された場合も、実成功prefixは残る。frame全体を入口へrollbackしたとは呼ばない。未実行時間の自動drop・H縮小・旧stepへのfallbackは行わない。

力とtorqueは最初の成功tickで既存advanceが消費する。後続tickへ同じ力を自動で入れ直さない。World／Progress／sourceへの並行・再入観測をcallerが除外し、一つのschedulerを一つの論理Worldに用いる。schedulerは借用参照を返却値へ残さず、実AdvanceReportを固定8slotで所有する。guard予算のchecked積はsettled chargedの上界で、refund前の累積grantedや全heap／stackの保証ではない。

時間creditはbinary64のRN ledgerで、各加減算の誤差を外向区間へ保存する。厳密実数時間の累積一致や全描画周期で同じtick数になる保証ではない。今回の1秒分の表現入力では144Hzだけ119tickと未処理creditを残し、次frameの入力で継続できる。旧FixedClockのepsilon判定で早期tickを作る仕様へ合わせていない。全clock命令の形式証明とも区別する。

MSVC19.51 x64の新しい短build/wfs2で、13群・1382実pump、strict／WX／非LTOのconfigured・default両targetと未構成profileの実拒否を確認した。既存919対象はhash不変で、旧buildを再構成していない。新schedulerの別構成IDを旧7-source IDへ混ぜていない。初回run001はCMakeのCompilerId probeまでstrict対象へ含めたcollector失敗であり、rawを保持して対象source commandを限定したfresh run002で成功した。

さらに[独立credit検査](../reports/world-static-mesh-flight-scheduler-credit-checks/run-002/result.json)で、実1382観測のcredit／全queue／Progressを整数・Fraction RNで確認した。1376入力受理、642attempt／637成功、外部環境拒否の観測1件。14改変拒否、label／順序独立と実Python -O拒否も成功した。このselected JSONは全nested AdvanceReportを保存していないため、数学childと成功World全fieldの独立照合が完了したとはしない。Native内の解析例・全candidate／実body照合と別gateである。

続いて[全transaction保存と独立検査](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_TRANSACTION.md)の別28pumpをローカル受入。43attempt／37commit／41実guardと24数学child、16自己群／146改変拒否が成功した。旧51writerは全byte一致した。次はGNUと全依存sanitizer、正式CMakeとSDK接続へ進む。接触応答・支持摩擦・流体・材料損傷や専門シミュレーターの完成を含めない。

## Nativeアプリからのlink

既存coreとは別のtargetへlinkする。`target_link_libraries(my_app PRIVATE pikapika_world_static_mesh_flight_scheduler)` とし、header `pikapika/world_static_mesh_flight_scheduler.hpp` を使う。対応するstrict Release／compiler環境を満たさなければAPIはunsupportedを返す。Debugは実coreを含めprofile0拒否を確認した。構成profileのJSONはactual object／全命令を自ら測った証明ではない。旧7source identityを変更せず、新2sourceはhelper／compiler／flags／上流IDを含む別構成として記録する。

次のNative入力段は[単一tickの絶対荷重packet計画](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_NEXT_PLAN.md)。調査・設計のみで、新APIは未実装。GNU有限受入後に進め、既存schedulerやWASMへ接続済みとはしない。
