# tickごとに別の荷重を渡すNative試作

2026-11-05。**有限MSVCの隔離単体群と全owned transcript／独立参照をローカル受入した試作。**
正式CMake、実GNU／全依存sanitizer、SDK／ゲーム接続は未受入。現在の正本は
[full受入記録](../reports/world-static-mesh-flight-controlled-scheduler-full-verification.json)。
[次段計画](WORLD_STATIC_MESH_FLIGHT_CONTROLLED_SCHEDULER_PLAN.md)と
[原著概念図](learn/diagrams/world-static-mesh-flight-controlled-scheduler.svg)を参照する。

入口は新しい`world_static_mesh_flight_controlled_scheduler::Scheduler::pump`。
World、静的mesh、guard設定、Progress、elapsed秒、最大8個のTickLoadPacketを渡す。
旧Scheduler、単一controlled tick、advance、SDK、sampleのソースや識別子を変えない。
新bindingは、自身の構成IDと実controlled／旧scheduler／上流7源の対応を確認する。
構成ラベルを実artifact自己認証や全clock／commitの命令証明とは呼ばない。

elapsedは一度受理する。dueの各tickへその順のpacketを一個ずつ渡し、実controlled
APIの外部commitが成功した分だけcreditとpacketを消費する。途中の拒否で止まり、
成功済みWorldとProgress、未消費creditとpacket suffixを保持する。再試行はelapsed0。
力0のpacketの生成、最後の力の再利用、callback、旧advanceへのfallbackは行わない。
入力不足のawaiting_input、step budget、実child拒否、due0のwaitingを区別する。

一度のpumpの入力は所有copyする。未使用未来tailはその場で意味検査せず、実tickで
既存controlled APIがmode／ID／荷重／expected_tickを検査する。ただしcaptureの
有界性のため、packet9個、任意packetのload9行はadmission前に拒否する。
新wrapperはWorldを永続所有せず、pump間のpacket enqueueや世代handleも作らない。
一つの論理World／Progressと排他的な同期callはcallerの前提である。

親Reportは各実ControlledReportと、最大9個の実World／Progress境界を保持する。
境界は最大8body／16planeの固定arrayの有効prefixだけを読む。全bodyfield／raw plane／
gravityと順序、負零をコピーし、元body格納先との一致観測も保存する。
投げ得る外側capture／copyと時間計画は最初の外部commit前に終える。
commit後はnothrow条件を固定したchild移動、固定境界copy、scalar保存だけにする。
親のcatchが成功prefixを隠すことはない。実allocation／post-child faultは未注入。

`UpperBudget`は時間上のplanned slots×旧guardのsettled upper limitsを予約する。
packet不足の未呼出slotも含む予約で、実workではない。全Reportのheap、allocator
overhead、RSS、stack高水位やdeadlineまで16MiBの旧論理payloadへ含めない。
新Storageのsizeofは名前を付けた固定bufferだけの観測である。

## 今回確認した有限範囲

fresh build/wfcq3で7command／21群を確認した。二tickのFx=4→−4、guard拒否後の
retry0、入力不足後のretry0、stale入力、未来の未使用tail、step budget、packetなし、
最大8tick／9境界、hard count、invalid elapsed、backlog上限、FE_UPWARD拒否、
非finite raw packet、設定6拒否を含む。m=2、g=0、H=1/16の解析数値は、最終
x=1/128、vx=0でC++ assertionsを確認した。これは独立参照checkerの受入ではない。
最大8body／16planeの全組をこの21群で検証した意味でもない。

configured/defaultのReleaseとDebugを別にcompileし、実8tlogのstrict／WX／非LTO、
profileとIDを確認した。Debugは`/MD`と`_ITERATOR_DEBUG_LEVEL=0`でRelease importへ
合わせた新TUのprofile0拒否だけであり、実Debug coreの受入ではない。
先行単一tickの5df636aは実Debug coreとGNU全依存sanitizerまで受入済みだが、
それを新scheduler全体の受入へ転用しない。

初回はGuardSettingsの非default構築を見落としてcompile失敗、明示copy constructorへ
修正した。次のrun002は実7commandと21群が成功した後、collectorがCMake自身の
CompilerId用commandを混ぜて停止した。新4targetだけに限定してfresh003を完走した。
失敗run／実recipe／全前後stampを保持し、物理入力や期待値を緩めていない。

正本と再開方法は[recipe README](../reports/world-static-mesh-flight-controlled-scheduler-recipes/README.md)。
外部資料・実装・ライブラリ・モデル・画像の追加はない。

## 全記録と独立参照の後続受入

新しいfull producerはfresh build/wfcqt3で4commandが成功し、70scenario／84pump、
実controlled call83／成功44tick、実private advance79／guard79を保存した。
全記録4,688,084Bは原本の型・原順・負零と全nullable slotを保持する。固定境界は
actual active prefixの値copyで、World::add_bodyで再構築したりcandidateから作った
実測Worldへ差し替えたりしない。全guardを再照会する処理もない。
body9／plane17／mesh5／face65の4assertionは、capture／admission前の拒否を確認した。
旧controlled全88のrawは既存main受入物とbyte一致し、実producer／legacy mainの2tlogも
strict／WX／非LTOを確認した。source／既存artifact1536pathは全commandで前後一致。

最初の77pump producerを保持し、hard境界4件を加えた81、120Hz既定stepの丸め会計3件を
加えた84を別runへ保存した。既存guardのstatic scene/body/settingsを明示scheduler stepで
再利用しており、元guardのH入力まで全件不変で再実行したという意味ではない。
全recordは有限。prototypeの非finite unit assertionsや実fault注入へ範囲を広げない。

新しい独立checkerは整数／Fraction ties-evenで時間受理と全減算を導き、成功prefixの
packet／credit消費を照合する。83実ControlledReportと79実guardの279数学child
（flight126／metric66／planeBox65／sphereBox22）、285個の実固定境界body観測を検査した。
実actual childだけを既存の純粋advance_reportへ渡し、架空のWorldAfter／find_body／
pointer行を旧full-row checkerへ作らない。per-pumpの外側pointer観測と、中間固定境界の
元ordinal-address一致だけの観測は別である。

80コピー改変拒否、名称／scenario改名と文書逆順、実2つのdyadic閉形式、実120Hz記録の
非零queue丸め誤差、実Python -O拒否を確認した。独立coreの旧actual88回帰は、既存の
全row検査の数学・counterと一致した。初回72拒否の後、整数metadataを同値floatへ
替える8型controlを追加し、型検査を強化した最終80拒否を確認した。物理入力／計算核は不変。

これは有限cohortの独立検証で、全入力の正しさ、全例外／alias／clock／commit命令証明、
allocator／nonreturn／post-child自然fault注入、実時間性能の保証ではない。旧21群のDebugは
Release import ABIの新TU拒否のままで、実Debug coreと新GNUは正式統合後の別gateである。
