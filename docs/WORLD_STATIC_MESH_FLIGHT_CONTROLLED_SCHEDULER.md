# tickごとに別の荷重を渡すNative試作

2026-11-05。**有限MSVCの隔離assertionsだけを受入した試作。**
全owned transcript、独立数学・負例、正式CMake、GNU／sanitizer、SDK／ゲーム接続は未受入。
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
