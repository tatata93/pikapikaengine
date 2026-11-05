# Controlled schedulerの隔離Native試作

`check-prototype.py`は同一workspaceの既存受入物を読取importするMSVC専用recipe。
正本は[run003 result](run-20261105-prototype-003/result.json)。実7command／21群と
configured/default、Release/Debugの新TU拒否、8tlogのstrict／WX／非LTOとIDを確認した。
全owned JSON／独立参照／負例／GNU／正式CMake／SDKの受入ではない。

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
