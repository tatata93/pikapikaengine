# Native固定tick scheduler隔離試作

2026-11-05。**FINITE_ISOLATED_PROTOTYPE_PASS**。これは新scheduler TUのMSVC19.51 x64 Release有限試作であり、本体CMake／CI統合、GNU、全依存sanitizer、全nested数学checker、全clock／commit機械形式証明、SDK／ゲームの受入ではない。既存の契約文書 `docs/WORLD_STATIC_MESH_FLIGHT_SCHEDULER_PLAN.md` は設計作成時の未実装状態を記録するもので、今回その原文を変更していない。

## 今回の実装と実測

新header／cppは `world_static_mesh_flight_scheduler::Scheduler` を提供する。設定はconstructorで検証・保持し、World／source／Progressを借用するのはpumpの同期呼出し中のみ。callback・古いcertificate・frame全体rollback・自動dropはない。全queue算術と固定8slotを入力受理前に準備し、成功advanceの後はReportのnothrow moveとscalar storeだけ。拒否したtickのcreditを消費せず、実成功prefixは残る。成功済みelapsedを再提出せずretry0を用いる。

上限はstep `[2^-20,.1]`、elapsed／represented backlog `[0,1]`、attempt既定4／最大8。UpperBudgetはplanned slot数と**settled charged**の既存hard上限のchecked積。累積grantedはrefundにより限度を越え得るため、その上界という意味ではない。拒否で未実行のqueue tailも予約から取り除かない。logical payloadだけを全Report／heap／stackの上限としない。各actual AdvanceReportの全owned guard／work／unknown upperは返却値内に保持する。

### 正式な隔離試作run002

`python reports/world-static-mesh-flight-scheduler-recipes/check-prototype.py --name run-20261105-prototype-002 --build build/wfs2`

- compiler probe、configure、build、`--run`、`--observations`、別default-profile `--unsupported-profile` の6commandが全exit0。
- 新cpp／testのconfigured・unconfigured両targetをstrict `/W4 /WX /permissive- /fp:strict /GL-`、link `/LTCG:OFF` で実compile。build8.906秒、warning0。実4source commandをMSBuild tlogへ保存した。compiler flags捕捉は機械命令監査の代用ではない。
- **13群、1,382 actual pump**。`--run` 0.140秒、observations出力0.437秒。時間はこの有限runの観測で、継続性能やdeadlineの保証ではない。
- **919 pathの前後hashが不変**。新sourceも測定中不変。旧core source、main CMake／binding CMake、SDK artifact、既存Native／wfa2／wfat1／wfa3の対象lib／exe／core.obj／map／profile／project／command tlogを保護した。旧buildの再構成・再ビルドは行わない。
- new scheduler source2／compiler／flags／imported dependencyから作った別IDは `32d91ef19f1eef9206d930f6ed0dd4bdbb0e1e8aad74bdb20ae076e26a1381fb`。importした旧7-sourceのIDは `4dc5fea0a751f469137271421800e282b3a257ddf56d6ac6498182bd0bff061f` のまま。新IDはconfiguration identityであって実object自己計測やartifact認証ではない。caller boolでunlockしない。default未構成schedulerは入力受理前に実拒否した。

rawの正本は `run-20261105-prototype-002/result.json`（3343906 B、SHA256 `9ee4e31b1a1ff9b008f9c40864e0e20416e8179b3c1c85603de8c769aabf7361`）。各commandのargv／stdout／stderr／exit／時間／前後source hash、compiler facts／identity材料、tlogコピー、artifact hashesも同runへ保存している。Native exe／objはignored build内のみで、reportsへコピーしない。

### 13群の内容

1. 空Worldで閾値直前／0 retry／正確dyadic境界／複数tick。
2. cap4／hard8まで成功しbacklog保持、retry0でdrain。
3. backlog capでelapsed未受理、drain後に元elapsedを再提出。
4. 最初guard拒否、retry0でも拒否、入力を直してretry0成功。旧owned失敗snapshotを維持。
5. 非空sphereがplaneへ向かい一tickだけ成功、次tick拒否。実y=.3125／Progress tick+1／backlog=.125を保持。
6. 非零力／torqueで二tick。力8N／mass2kgは最初tickだけ、二tick後の解析x=1.1484375／vx=1.25と全candidate field／+0荷重を照合。
7. 不正elapsed（非finiteはbits保存）、-0原本。
8. 六つの不正immutable設定のconstructor拒否。
9. 実Progress tick／time上限でadvanceが拒否し、credit保持。
10. 実FE_DOWNWARD時の受理前拒否と環境復元。
11. 既定binary64 120Hz stepを同じbitsで渡す二tick。
12. minimum step、subnormal elapsed、RNによる吸収を明示したcredit会計。
13. 30／60／120／144／1000Hzのrepresented ledger。最初の四つのうち144だけは119tick、backlog `3f811111111110f9`。他は120tick。旧FixedClockのepsilon仕様へ一致させていない。144の期待値はrootの別整数参照候補と照合した有限assertで、全独立参照の完了とはしない。

各pumpでWorld全body field／plane／gravity、全source／settingsのbit snapshot、元／後Progress、格納先pointer安定性、入力受理前失敗の全無変更、成功0時のWorld／Progress無変更、actual AdvanceReportとconsumed flagの対応を検査する。成功最終bodyは実candidateの全fieldからforce／torqueだけ+0へしたものとbit比較する。hidden requery／fallbackはない。

## 初回履歴と保存scope

run001（build/wfs1）のcompiler/configure/build／13群／observations／default拒否は全exit0だったが、最後のcollectorがCMake自身のCompilerIdCXX.tlogをnew TUのstrict監査へ混ぜたため全体exit1。原recipe／全raw／失敗resultをそのまま保存した。製品数学やtest期待の修正はない。collectorを新2targetの実cpp／testだけに限定し、各実commandの正確なstrict／WX／GL- tokenとsource集合を検査してfresh002を実行した。hpp／cpp／testのbytesは初回から不変。

`observations.json` は `05-observations.stdout.txt` と同一bytes、4989985 B、SHA256 `d8765a42ff498fa087ebc54d47f04c544f797a8a8529789346da0052bde9c757`。JSONはfull World／source bit snapshotとselected credit／queue／Progress／attempt metadataで、**完全nested AdvanceReport serializerではない**。返却C++値の全Report所有とJSON保存scopeを混同しない。独立credit checkerはroot所有で、このrecipeはその実行／成功を主張しない。

未実施はGNU、sanitizer、busy／sequence限度の人工注入、自然allocation／nonreturn fault注入、新TU全命令監査、main統合、全nested childの独立数学再検証。1,382 frameの実行でこれらを証明したとはしない。独立checker・全fixture serializer・CI・SDK・制御入力packet・一般接触応答は後続。

## frozen source

| path | bytes | SHA256 |
|---|---:|---|
| core/include/pikapika/world_static_mesh_flight_scheduler.hpp | 4008 | 6ed6a2c9221e09aae4fdd3f4ad52cf7390494c9b14c415eb8989ebb9d0085b27 |
| core/src/world_static_mesh_flight_scheduler.cpp | 7597 | 432af4ad99b669f895bafb010a1ba7a4b99fddabb75e7c80ec0abb69c557f721 |
| tests/world_static_mesh_flight_scheduler_tests.cpp | 22678 | e690503352496e494670f98033970390404c5c95f8e0fa2ce0b6a0a441e97e27 |
| reports/world-static-mesh-flight-scheduler-recipes/check-prototype.py | 13037 | dbfe63bf0c81d634eb7e60b52ca66237e9fe4ce363152f50dbf0a5932b8a20fb |
