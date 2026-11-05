# Controlled tick：隔離Native prototypeの再開方法

このdirectoryの `check-prototype.py` は、既存buildを変更せず、新しい単一tick絶対荷重packet APIを試す**同一workspace向けMSVC隔離recipe**である。main CMake targetへは未統合で、GUI・ゲーム・SDK／WASMにも未接続。fresh cloneから一commandで全依存をbuildする入口ではない。GNUのscheduler受入も、この新controlled tickのGNU成功とは別である。

## 読取importする前提

現行sourceと実際の先行受入が揃う同じworkspaceを使う。

- `build/wfsm1/Release/pikapika_core.lib`：先行main scheduler統合で作ったRelease core。recipeは先行runの全core source stampと現在の旧core sourceを比較する。新controlled tickのhpp／cppだけは別源として新規compileする。
- `build/wfa3/pikapika_world_static_mesh_flight_advance_fixtures.dir/Release/` の旧7 writer objects：`world_static_mesh_flight_guard_fixtures.obj`、`world_static_mesh_flight_preparation_fixtures.obj`、`sphere_triangle_mesh_free_flight_guard_fixtures.obj`、`sphere_triangle_mesh_held_load_fixtures.obj`、`accelerated_pair_coverage_fixtures.obj`、`accelerated_plane_box_coverage_fixtures.obj`、`accelerated_sphere_box_coverage_fixtures.obj`。
- 先行source hash／raw originals／profile：`world-static-mesh-flight-scheduler-recipes/run-20261105-main-integration-001/`、旧advance／full schedulerの固定原本もrecipeが読取／保護する。
- genuine MSVC 19.51、native x64、CMakeと既存Windows toolchain。新TUはC++20、`/fp:strict /GL- /W4 /WX /permissive-`、非LTO、Releaseの `/MD` でcompileする。compiler／実flags／新2source／既存7-source IDから新しい独立構成IDを作る。callerのboolでは有効化できない。

依存由来は、先行 [advance正式target recipe](../world-static-mesh-flight-advance-recipes/check-formal-target.py)、[scheduler main統合recipe](../world-static-mesh-flight-scheduler-recipes/check-main-integration.py)、[旧writer import定義](../world-static-mesh-flight-scheduler-recipes/check-full-fixtures.py)を参照する。これらの歴史recipeを既存run／build上へ再実行してはいけない。import物がないfresh clone、source／compilerが違う環境では、その構成に対応した新しい先行受入とprovenanceの準備が必要である。古いIDやartifact stampを付替えたり、欠損をゼロ値で埋めて実行したりしない。

## 実行するCLI

repo rootから、**両方とも未使用**の短いbuild名とrun名を明示する。既存 `wfc1`／`wfc2` は再利用しない。例えば次のcommandはfresh `wfc3`／run003を作る形であり、この例そのものの実行済み成功を意味しない。

```powershell
python -B reports/world-static-mesh-flight-controlled-tick-recipes/check-prototype.py --build build/wfc3 --name run-20261105-prototype-003
```

outputは `reports/world-static-mesh-flight-controlled-tick-recipes/<name>/`。recipeはCMakeListsを新build内にだけ作り、次の9commandを実行する。各commandのargv／cwd／exit／time／stdout／stderr／前後hashを保存し、失敗内容も表示する。

| command | 内容 |
|---|---|
| 01 | fresh CMake `-A x64` configure、実compiler facts／独立identity保存 |
| 02 | 新configured／default libraryとtest executableのRelease build |
| 03 | configured `--run`：94群のNative assertions |
| 04 | configured `--fixtures`：完全finite JSON `controlled-full.json` |
| 05 | configured `--unit-observations`：非finite単体入力4件のraw bits |
| 06 | Release default `--unsupported-profile`：capture／child前拒否 |
| 07 | 新TU／harnessのDebug build（Release coreはimportのまま） |
| 08–09 | Debug configured／default各 `--unsupported-profile` |

`--fixtures`／`--run` 等は `build/<wfcN>/configured/Release/controlled_configured_tests.exe` の入口である。default executableは `controlled_default_tests.exe`。Debugは対応する `Debug/` directoryに置く。new targetの実tlogを調べ、profile／ID／strict／WX／非LTOの実commandを確認する。通常の再実行は上のfresh recipe全体とし、部分commandの成功を新source全受入へ昇格させない。

## 保存済みNative scope

正本は [run002 result](run-20261105-prototype-002/result.json) と [freeze](run-20261105-prototype-002/freeze.json)。Native9command／94群、88 finite fixtures（外部commit22／not_certified29／invalid_input37）、actual private child64件を確認した。全fixtureは3,992,656B、SHA256 `1320a1306f30d64cfd275dec582a8eefb1275ddc7a93654975ac5428b7822db0`。旧guard由来51入力＋directed32入力＋連続5frameであり、GUIやWASMの実行件数ではない。

source2と旧7-sourceの構成IDは分け、元のscheduler／advance／guard／SDK／sampleを変えていない。旧buildを再configure／再buildせず、全commandで保護pathの前後一致を保存した。private childのsuccessは外部commitとは別で、完全Report内にactual private origin／before／after／childを保持する。外部Worldを途中のcandidateから生成した観測値で置換していない。

Debugは `/MD`＋`_ITERATOR_DEBUG_LEVEL=0` を明示してRelease importとABIを合わせ、NDEBUG無しの新TUが拒否することだけを測った。**実Debug coreやDebugでの数値transactionの受入ではない。** 全依存sanitizer、GNU、main統合、全clock／commit機械形式証明、allocator／nonreturn／post-child allocation failureの自然注入もこのreceiptでは未実施。

## 非finiteと独立checker

full JSON cohortの入力はすべてfiniteと明示している。旧 `world_advance_fixture::report_json` はrequestedDt／Progressを含め数値有限を要求する。NaN H／NaN Progressから得たactual childを、有限値へ直してそのwriterへ渡してはいけない。

4件のNative単体観測は元force NaN、packet force NaN、NaN H、NaN Progress。`unit-observations.json` にoriginal World前後の全wordとraw入力bits、child存在、旧finite child writerの実拒否を別scopeで保存した。これは非finiteを含む全owned Reportのlossless JSON codecではない。NaN payloadを保持するNative assertionsと、full finite serializerの境界を分ける。

独立数学・負例の正本はこのNative recipeのstatusへ足し込まない。専用 [checker](../../scripts/verify-world-static-mesh-flight-controlled-tick.py)、[reference tests](../../tests/world_static_mesh_flight_controlled_tick_reference_tests.py) と [参照freeze](../world-static-mesh-flight-controlled-tick-reference-development/freeze.json)を親が後段の正式受入記録へ結ぶ。ここに記載した成功数はNative scopeだけである。

## 初回collector FAILと正確な再開

[run001](run-20261105-prototype-001/result.json) はconfigure／strict Release compile自体はexit0だったが、旧helperの `world*` globが**別担当が編集中の新Python reference test**を保護集合へ入れたため、source-stability gateが実runtime開始前に停止した。数値assertion失敗や製品source変更ではない。raw／最初のrecipe／全before-afterを保持している。

修正は新recipe内で、そのexactな未凍結Python path一件を「これらNative commandの入力ではない並行著作物」として明示除外しただけである。旧sourceやchecksumを緩めず、新Native5fileは初回compileから同一hashのまま。fresh `wfc2`／run002で最初から再実行し全9commandを確認した。run001のFAILをPASSへ書換えていない。

再開時はまずrun002のfreezeと新source／import物を確認する。違いがあれば原因と新構成を記録し、未使用 `wfcN`／run名へ進む。失敗run／旧binaryを削除・上書きせず、新しい数学期待やthresholdへ黙って差替えない。main CMake／GUI／WASMへの正式統合は、この隔離準備とは別の次段受入である。
