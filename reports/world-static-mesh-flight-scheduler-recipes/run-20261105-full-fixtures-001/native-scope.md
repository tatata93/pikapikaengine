# Full scheduler Native保存の有限記録

2026-11-05。`check-full-fixtures.py` 初回は **FINITE_FULL_FIXTURE_NATIVE_PASS**。新短build/wfsf1だけで作業した。旧native／wfa2／wfat1／wfa3／wfs1／wfs2は再構成・再buildしていない。

7command全exit0、986 source／artifact path前後hash不変。新main／scheduler TU／shared advance writerと、macroなしのshared writer（計4実compile）は `/W4 /WX /permissive- /fp:strict /GL-`、非LTO。compiler/configure/raw/tlog・新profile照合・全stdout/stderr/exit/timeは同runに保存した。actual instructionや全clock／commitの形式証明とは呼ばない。

新実出力は11scenario／28pump、23 elapsed受理、43 actual advance attempt／37commit／41実owned guard。outer statusはwaiting12／step_budget5／tick_rejected6／invalid_input5。数値は保存済JSONの集計であり独立数学検証の件数ではない。新dumpは857310B、SHA256 `2d9b594c5b35d14d4d590c6d6308eef76d75e1c779f3db2de7337f0cdd34e236`。全8nullable slots、upperBudgetのsettled charged hard上界、全実PumpReport／AdvanceReport／guardMessage／nested numerical diagnosticsを保持する。Reportの不在guardは生成しない。

実外部World／Progress／source／pointerは**各pumpの前後のみ**。各tick間のWorldAfterをcandidateから生成して実観測欄へ入れない。元body ordinal／ID／find_body対応、各mesh face storageもouterで保存する。内部origin snapshot／candidate chainを独立checkerが照合することは、外部中間観測の追加を意味しない。

新writerはprivate bufferを64MiBで制限し、既存writerから共有したtest-only UTF8／JSON構文／finite-number gateを通してからstdoutへ出す。新enumはrange確認、非finite elapsedはraw64 bits文字列のみ。actual出力ではNaN payloadや−0もbits／既存数値形式の区別を保持する。size budgetは出力bytesの上限であり、allocator／プロセスheap／RSSのhard上限ではない。gate故障注入やallocation例外の動的注入は未実施。

旧advance writerはmainをlibrary-only macroで囲み、test-only UTF8／string／document関数を共有しただけ。macroなしfresh buildの旧51は**2979456Bの全raw完全一致**し、旧独立51／14自己群／85拒否・実Python-O拒否／label順序独立が成功。旧原本は書き換えていない。型・入力・数値閾値・旧51期待を変えていない。scheduler2sourceと7sourceの数値実装も不変。

新scheduler IDは `32d91ef19f1eef9206d930f6ed0dd4bdbb0e1e8aad74bdb20ae076e26a1381fb`、旧7source IDは `4dc5fea0a751f469137271421800e282b3a257ddf56d6ac6498182bd0bff061f` のまま。元identity材料のsource2／imported lib hash／実compiler facts／flagsとの一致を確認して同IDを用いた。caller bool unlockや旧IDの新TUへの付替えはない。

新full schedulerの独立checker／負例は別担当・別scopeで、**このNative recipeはそれらの成功を主張しない**。GNU／sanitizer／本体CMake／CI／SDK／ゲーム統合も未実施。初回に新build・数値・serializerの失敗はなかった。過去prototype001のcollector失敗は別の凍結証拠であり、このrunの失敗として再分類しない。

frozen files:

- tests/world_static_mesh_flight_advance_fixtures.cpp：26769B、SHA256 `778f41a9fa6620809ecc305c850d502d21aafa9f9c6bb012ef5dd7a19e61bacb`
- tests/world_static_mesh_flight_advance_fixture_support.hpp：1314B、`700931c4c918e01b60c5faaaff391a79071d013b8e87a27a8d2d0d429cc78d83`
- tests/world_static_mesh_flight_scheduler_fixtures.cpp：18459B、`d3a5cba196bfaf7a4e2a2a5c9e011018528c567699a629544515845b4306f32d`
- tests/world_static_mesh_flight_scheduler_fixture_support.hpp：580B、`ee31136cee623f8049e00f084ac3464f259617d9556123cfb594d41c34f7879f`
- check-full-fixtures.py：14286B、`7dc8a42a641ffe1f9a9dacfac068535c7f3f4778abec8aa682507a71413e5ef6`
