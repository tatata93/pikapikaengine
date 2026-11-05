# Controlled schedulerの隔離Native試作

`check-prototype.py`は同一workspaceの既存受入物を読取importするMSVC専用recipe。
正本は[run003 result](run-20261105-prototype-003/result.json)。実7command／21群と
configured/default、Release/Debugの新TU拒否、8tlogのstrict／WX／非LTOとIDを確認した。
このprototype段階のreceiptは全owned JSON／独立参照／負例／GNU／正式CMake／SDKの受入ではない。
後続のlocal full受入は下記の別run／正本へ保存する。

## 必要な実import物

- `build/wfcm1/Release/pikapika_core.lib`
- `build/wfcm1/Release/pikapika_world_static_mesh_flight_controlled_tick.lib`
- `build/wfcm1/Release/pikapika_world_static_mesh_flight_scheduler.lib`
- 同buildの`pikapika_world_static_mesh_flight_controlled_tick_tests.dir/Release/`にある
  serializer9個のobj。旧controlled tick testsのmain objはimportしない。
- 同buildのworld-flight binding、controlled tick binding、scheduler bindingのRelease JSON。

これらは5df636aの通常CMakeで作ったMSVC19.51 x64の実Release受入物。
古いbuild／原本を再構成・上書きせず、現在sourceとの不一致を隠さない。
他workspaceやfresh cloneへhashやprofileを付替えない。通常CMakeで先行targetを
新規buildしてから、そのcompiler／ABIに対応する新受入を準備する必要がある。
このprototype自体はfresh clone一commandの入口ではない。

## 再実行

未使用の短いbuild名とrun名を両方選ぶ。次は例であり、実行済み成功を意味しない。

```powershell
python -B reports/world-static-mesh-flight-controlled-scheduler-recipes/check-prototype.py --build build/wfcq4 --name run-20261105-prototype-004
```

recipeは新build内にだけCMake projectを作る。新library2variantとtest driverを
`/W4 /WX /permissive- /fp:strict /GL-`でcompile、非LTOでlinkする。
configured Releaseの`--run`、default Releaseの`--unsupported-profile`、Debugの
両variantの`--unsupported-profile`を実行する。入力/source/既存artifactの全前後stamp、
実argv／cwd／exit／stdout／stderr、source原本、CMake project、構成materialを保存する。
Debugは`/MD`＋iterator0でRelease importに合わせる拒否試験だけ。

## 失敗を保持する

run001はGuardSettingsがdefault構築不可なのを見落とし、新cppがcompile失敗した。
Originalへ明示copy constructorを設けた。既存設定型や物理条件は変更しない。
run002は全7実command／21群が成功した後、collectorがCompilerIdのCMake確認用
compileをstrict新TUと誤認して停止した。そのFAIL／全rawを残した。
run003では新4targetの実tlogだけを選び、全7commandからやり直して成功した。
run002以後の新Native3sourceは同一で、source/期待値を弱めた再試験ではない。

## 次の受入

全original／packet列／実境界／実child Reportを有限full writerへ保存し、整数RNの
時間会計とpacket消費、actual childのみの純粋数学参照、コピー改変拒否を結ぶ。
最大8body／16plane／source順と負零を含む記録を追加する。pointerやWorldAfterを
candidateから補填しない。allocator／post-child faultを実注入していなければ未実施とする。
正式CMake／GNU全依存sanitizerはその後で、旧source2/7とSDK/sampleを保持する。
詳細は[計画](../../docs/WORLD_STATIC_MESH_FLIGHT_CONTROLLED_SCHEDULER_PLAN.md)を参照。

## 後続：complete finite writerと独立参照

`check-full-fixtures.py`は、上のwfcq3 Releaseのpacket_configured.lib、wfcm1の既存3libraryと
9serializer objを読取importする。新C++ full writer／旧controlled mainだけを別buildへcompileする。
現在の受入runはrun-20261105-full-003／build/wfcqt3。4commandで84pump／70scenario、
83実controlled call／44commit、79実private child／guardを保存した。最初の77／追加hard4の81は
各run001／002へ保存し、finalは既定120Hzの3rowも加えた84である。古いrunを上書きしない。

同じworkspaceで、未使用の名前を使う例（この例の実行済み成功は主張しない）:

```powershell
python -B reports/world-static-mesh-flight-controlled-scheduler-recipes/check-full-fixtures.py --build build/wfcqt4 --name run-20261105-full-004
```

compiler実path/version/native x64、実2tlogのstrict/WX/非LTO、全1536保護前後一致と旧88raw一致を確認した。
full JSONは有限入力だけ、64MiBの私有buffer完了／UTF8 JSON検査の後に一括outputする。
原World／lookup観測は実callerから、各中間Worldは実fixed境界のactive prefixから保存する。
実ControlledReport／GuardResultを保持し、数値queryや候補からの観測値生成はしない。

独立checkerはscripts/verify-world-static-mesh-flight-controlled-scheduler.py、負例は
 tests/world_static_mesh_flight_controlled_scheduler_reference_tests.py。
final84のinput fingerprintは26e21e83eadab0b998100dc1ee9e7ef45f03adfee93c49f0ce920d04fad46a7c。
実83Report／79guard／279数学child、285固定境界body観測、80コピー拒否、旧actual88回帰、
名称順序独立／2dyadic閉形式／非零120Hz queue丸め／実-O拒否が成功した。
正本は[full受入記録](../world-static-mesh-flight-controlled-scheduler-full-verification.json)。

実行はfull JSONをcheckerへ渡し、reference testsには新しいworkspace内outputを指定する。
過去のcontrols-001／002やfreezeは上書きしない。初回unpinned照合の後に84cohortをpinし、
72拒否へ整数→float型8controlsを加えて最終80拒否へ強化した。入力／Native計算核は不変。
この受入は正式main CMake／実Debug core／GNU全依存sanitizer／SDK／ゲーム接続を含めない。


## Formal main MSVC / GNU preparation

`check-main-integration.py --build build/wfcqm2 --name run-20261105-main-integration-002`
passed13 commands: Release21 groups/full84/reference80, old88/51/28 whole raw regression,
50CTest, genuine Debug core and5 refusals. Three old Release/Debug profiles are byte exact.
Prototype differs only at84 explicit outer IDs. Five new tlogs contain32 actual TU entries;
1488 protected paths stayed unchanged. Never reuse wfcqm1/2: choose fresh wfcqmN/report names.
Run001 preserves CMake negative-substring-index refusal; corrected helper passed fresh002.

`verify-gnu.py` / `GNU_PLAN.md` define the pending bounded public job: core40+three actual
library TUs and20 harness TUs, fresh Debug/O1 ASan-UBSan, normal artifacts never rebuilt.
Comparison controls reject17 copied changes at4 named ID families/8 paths/660 leaves and
an actual Windows process refuses GNU execution. This is not GNU acceptance. Failed001
wrote the same already-negative-zero value; corrected002 flips that actual sign bit.

Main receipt: `../world-static-mesh-flight-controlled-scheduler-main-verification.json`.
0060ec8 publication: `../world-static-mesh-flight-controlled-scheduler-full-public-verification.json`.


## Actual GNU13 acceptance

06b55f4 job127142176118 passed in296s: all21 actual commands, GNU13.3.0/x86_64,
43library/20harness TUs,5Werror replays, genuine Debug refusal and normal/all-dependency
O1 ASan-UBSan each21 groups/full84/279 mathematical children/80 copied rejects/-O refusal.
Four ID families at8 explicit paths/660 leaves are the only same-GNU-ABI typed-tree and
raw-byte differences. Normal artifacts/compiler/source stayed unchanged. This is actual
GNU acceptance; prior copied controls are still separate. The whole Engine workflow's
portable-core remained in progress at this observation. Canonical receipt:
`../world-static-mesh-flight-controlled-scheduler-gnu-verification.json`.
Owner-session design: `../../docs/WORLD_STATIC_MESH_SESSION_PLAN.md` (unimplemented).
