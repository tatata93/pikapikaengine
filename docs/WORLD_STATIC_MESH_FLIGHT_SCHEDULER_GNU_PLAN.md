# scheduler正式target／GNU13受入の最小統合計画

2026-11-05作成時の計画。**後に正式CMakeをWindowsで局所受入した。現在の[main receipt](../reports/world-static-mesh-flight-scheduler-main-verification.json)を参照。GNU／全依存sanitizerは未実行で、以下は統合前の固定契約である。** 既存の隔離MSVC試作、full fixture、独立数学検証をGNUやmain CMakeの受入へ読み替えない。本作業ではこの新文書以外を変更しない。[scheduler契約](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_PLAN.md)、[full fixture境界](WORLD_STATIC_MESH_FLIGHT_SCHEDULER_FIXTURE_PLAN.md)を引き継ぐ。

## 読取原本と既存の有限baseline

実読した統合箇所は `CMakeLists.txt` の既存advance tests／fixtures target、`cmake/WorldFlightBinding.cmake`、`reports/world-static-mesh-flight-advance-recipes/verify-gnu.py`、そのread-only依存のguard GNU helper、現scheduler hpp／cpp／tests／fixturesと独立reference freezeである。外部資料や新依存は使っていない。

現在のMSVC baselineは、隔離13群／1382 selected pump、full **28pump・11scenario・planned45／actual43／commit37／owned guard41**。full857310BのSHA256は `2d9b594c5b35d14d4d590c6d6308eef76d75e1c779f3db2de7337f0cdd34e236`。新独立checkerは16自己群／146拒否、実Python-O拒否、label／scenario名／document順序独立を成功させた。数学childはflight8／metric8／planeBox8／sphereBox0であり、最後の0をsphere数学検証成功件数へ足さない。root正本は各既存receipt／reference freezeを参照する。

共有advance writerのmacroなし51出力はfresh MSVCで2979456B完全一致し、旧14自己／85拒否を成功させた。これも新GNUでの実再実行を代用しない。

## 正式CMakeの変更案

旧 `pikapika_core` にscheduler cppを混ぜず、独立STATIC target `pikapika_world_static_mesh_flight_scheduler` を追加する。sourceは新hpp／cppの2つ、public includeはcore/include、`pikapika_core` にlinkする。旧7sourceの集合・ID式・source flags・SDK source listは変更しない。

新 `cmake/WorldFlightSchedulerBinding.cmake` を、旧WorldFlightBindingの構成後にincludeする案とする。次を別namespace変数で設定する。

- sourceSet `world-static-mesh-flight-scheduler-v1`、厳密なsource2一覧とsha、configure-depends。
- Release／genuine MSVC19.51 x64またはGNU13 x86-64 SSE2のみprofile1、それ以外0。現在cppのNDEBUG／target guardも維持し、caller boolを足さない。
- source2、compiler ID／version／path／arch、strict options、configuration、global＋Release flags、上流7source buildIdから別SHA256を作る。`PIKAPIKA_FLIGHT_SCHEDULER_PROFILE`／`PIKAPIKA_FLIGHT_SCHEDULER_BUILD_ID` はscheduler libraryのprivate定義にだけ適用する。旧7source macro／IDへ付け替えない。
- `scheduler-binding-$<CONFIG>.json` に上記原本とidentity／scopeを保存する。形式は実装時に固定し、unknown sourceSet／missing source／flag違い／profile不一致を拒否する。

正式profileは隔離試作のidentity材料と構成方法が異なるため、既存 `32d91ef1…1381fb` を無条件にコピーしない。**2sourceを独立に保持することと、異なる正式構成でも同じIDを名乗ることは別。** 新形式のversionと旧試作IDとの関係を記録する。core libraryの最終artifact hashはbuild後のprovenanceに保存し、configure時のIDへ同じlibrary自身の最終hashを入れる循環を作らない。上流依存は旧7source IDで明示し、actual lib／object／link hashを別gateで照合する。

新targetは次の2つ。

| target案 | sources／link／CLI |
|---|---|
| `pikapika_world_static_mesh_flight_scheduler_tests` | 現test main＋新scheduler library。Releaseは `--run` 13群、Debug／profile0は `--unsupported-profile`。 |
| `pikapika_world_static_mesh_flight_scheduler_fixtures` | 新full main＋shared advance writer＋既存guard7serializer TU、新scheduler libraryへlink。CLI `--fixtures`。このtargetだけ `PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY=1` をprivate定義。 |

既存advance51 targetにはlibrary-only macroを定義しない。shared writerのSOURCE単位global COMPILE_DEFINITIONSでmainを消すと旧targetも壊すため採用しない。7serializerは当面既存targetと同じ独立compileを維持し、共通OBJECT化で旧recipeのsource／object inventoryを無断変更しない。

新scheduler cpp／test／full mainはMSVC `/W4 /WX /permissive- /fp:strict /GL-`、GNUは既存full strict SSE2 flags＋`-Wall -Wextra -Wpedantic -Werror`。既存writerへのWerrorは現policyを維持し、他の旧serializerへ新たなwarning抑制／緩和をしない。IPO false、非LTO link、専用mapを設定する。新full targetのmapは `world-flight-scheduler-fixtures.map`、testは `world-flight-scheduler.map` 案。旧guard／advance mapは変更しない。

新exeで既存leaf／callerのlink監査を行う場合、MSVCは既存advance target同様にharnessの `/OPT:NOREF /OPT:NOICF` も付けて対象関数を保持する。sourceの演算を監査しやすい命令へ変更しない。これは検査用link方針であり、全scheduler命令を証明したという意味ではない。

CTestは実13群／profile0拒否のtestを一件だけ追加する案（既存47に対し新規構成では実数を確認する）。JSONを出して終わるだけの薄いserializer CTestは追加しない。独立full28／旧51／負例は専用recipeが実行する。

## GNU normal：既存buildを入力にする

新GNU recipeは、既にRelease／Unix Makefiles／g++-13／export compile databaseでbuildしたnormal directoryを受け取る。recipe自身はそのdirectoryを再構成・再buildせず、fresh output、別Debug、別sanitizer directoryだけを書く。rootの既存advance job／portable jobの実行・原本を変更しない。

必要なnormal targetsは旧guard／advance9／advance51と新scheduler13／full28。新jobを独立させるか既存専用advance jobを拡張するかは測定後にrootが決定する。最小案は新scheduler専用jobでこの5targetをparallel2 buildし、20分等の上限を明記する。現advance専用jobの約243秒から新所要時間を算定して成功保証しない。

1. actual GNU `--version`／dumpversion／dumpmachine、両profileのsource・sha・flags・Release状態を確認する。GNU13以外、Clang偽装、旧／unknown sourceSet、未構成schedulerをnormal成功へ補填しない。
2. normalのlib／新scheduler lib／全object／exe／maps／compile_commands／link.txt／profileをhash保存する。終了後も同じ対象を比較する。compiler自体と全source／SDK原本も前後捕捉する。
3. 旧actual Vec3 leaf／caller＋7source compiler-command監査を実行する。新scheduler.cppのactual compile行・別macro／ID／strict／非LTOは別に監査する。既存auditorの旧7source gateを「新scheduler全命令証明」へ拡張解釈しない。
4. 新3TU（scheduler cpp／test／full fixture main）を独立Werror compileでも検査する。shared advance writerも現policyどおり検査する。normalのactual objectをこのwarning用objectへ差し替えない。
5. 新test `--run` を実行し13群／1382観測の既存有限期待を確認。必要なら `--observations` も保存し、元credit integer checkerと14拒否を独立実行する。144Hzだけ119tickというrepresented-credit方針を旧epsilonへ合わせない。
6. 新full `--fixtures` をfresh保存し、独立 `scripts/verify-world-static-mesh-flight-scheduler.py` と `tests/world_static_mesh_flight_scheduler_reference_tests.py FIXTURE --output FRESH` を実行。28／11／43／37／41、16自己／146拒否／-O／label-order独立と、全8nullable slotsを確認する。ラベルで物理期待を選ばない。
7. macroなし旧advance51も実保存し、旧独立51／14自己／85拒否を実行する。現advance9／clock18整数参照／guard51の既存受入を維持し、新helperの都合で旧CLI／corpusを差し替えない。

再利用できる既存advance GNU関数は `checked_profile`、`advance_run`、`transaction_run` とguard helperのCommands／load／exact_tree等。再利用はread-only importし、既存recipeのmainを呼んで別Debug／sanitizer buildを二重作成しない。現在のharness inventoryは旧3target専用なので、新source／target集合を新recipeで明示する。source順／object所有／flagsを新target分もactual compile databaseから確認する。

## Debug profile0

fresh Debugを同じGNU13で構成し、新scheduler testsと旧advance／guard testsをbuildする。新profile／旧profileとも0、actual scheduler TUにRelease macro1やNDEBUGがないことをcompile行で確認する。各 `--unsupported-profile` は実拒否・入力受理0・World／Progress／backlog無変更で成功しなければならない。

new full writerをDebugで試す場合は「configured corpusを生成できない」ことを非zero exit・空stdoutで確認し、28のモデル失敗データとして補填しない。Debugのno-data拒否とReleaseの実guard拒否は別scopeである。

## 全依存O1 ASan／UBSan

別fresh Release sanitizer構成を作る。現advance recipeどおりglobal flagsに `-O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer`、Release flagsを `-O1 -DNDEBUG`、linkにもsanitizerを指定する。source strict／SSE2／非LTOを残す。旧7source IDと新2source IDはどちらもsanitizer構成の別値になり、normal値を再使用しない。

新scheduler libraryだけを計装して旧coreを通常libへlinkする試験では不足。**全core dependency TU、新scheduler TU、各main、shared writerと全7serializer**を同構成でcompileし、actual compile databaseの全対象へO1／ASan／UBSan／strict／非LTOがあることを確認する。通常MSVC輸入objectやnormal GNU objectを混ぜない。TU数は実compile集合で測定し、旧40core／17harnessへ新codeを足した推測値を実測として書かない。

normalと同じ新13／1382、full28＋独立16／146、旧9／18時計＋整数参照、旧51＋14／85、必要なguard51を実行する。ASAN_OPTIONS／UBSAN_OPTIONSは現recipeのhalt_on_error／leak等を引き継ぐ。sanitizerのinstrumented machine graphへ通常artifactの命令監査PASSを流用せず、これは数値／memory開発データと明記する。

## 完全比較：2identity familyと3path

**同じGNU13／stdlib／ABIのnormal対sanitizer**では、full28の全treeを型／key順／array順／binary64 bits・負零まで比較する。置換を許すのは次のID pathだけである。

| path pattern | identity family | 現corpusの実箇所数 |
|---|---|---:|
| `fixtures[i].report.binding.buildId` | scheduler2source | 28 |
| `fixtures[i].report.tickReports[j].report.binding.buildId`（実slotのみ） | advance7source | 43 |
| 同 `.report.guard.binding.buildId`（guard presentのみ） | advance7source | 41 |

したがって「binding2fieldだけ」とは**2種類の構成ID**の意味であり、実JSONの二箇所だけではない。現fullには3path pattern／計112leafある。各pathがその側の実profile IDと一致すること、normal／san IDが異なることを先に検証し、deep copy上でだけ固定markerへ置換する。文字列全体のreplace、任意buildId keyの再帰置換、unknown pathを無視する比較は禁止する。null／未実行slotをそのまま比較する。

その上で既存 `exact_tree` 相当の全比較を行う。必要なら同じmarkerでJSONをcanonical化してraw bytes比較も保存できるが、原rawを書き換えない。**layoutSizes／advanceLayoutSizes／schedulerLayoutSizes、nested storage／reservation.logicalPayloadBytes、padding影響のあるsizeof観測もこの同ABI比較では一切正規化しない。** 差が出たらrawを保って失敗原因を調べる。旧51は現 `compare_transactions` の旧2path（7source familyのみ）をそのまま維持し、時計18は現gateどおり正規化なしで比較する。

一方、**Windows MSVC対GNUは別ABI**である。sizeof／vector／optional等に由来するlayout・storage・logical reservationの差があり得るため、857310Bや2979456BというWin raw長・全byte同値をGNUの既定条件にしない。それらを大量に削って「full比較PASS」とすることもしない。各側を独立checker＋actual layout provenanceで検証し、元input/type/bits/fingerprint・queue／clock等の明示projectionを別gateで比較する。必要な可搬projectionの全pathは実行前に固定し、cross-ABI差をnormal↔ASanの許容差へ持ち込まない。

## 終了条件と未実行境界

各commandはfresh argv／cwd／exit／time／stdout／stderr／source前後を保存し、子失敗時にstderr/stdoutの中身をCIへ出す。hashだけを表示して原因不明にしない。timeout／parser不対応／warning／ASan failureを失敗のまま残し、次は別fresh出力で実行する。現old buildを再構成したり、古い成功を新source hashへ流用しない。

この文書で確定した変更候補はCMakeの独立scheduler library＋2target、新binding CMake、新scheduler GNU recipe／strict比較、専用workflow接続である。既存7source／SDK／旧receipt／根本契約docsは変更していない。正式実装の前にはrootがbaselineと所有範囲を固定する。GNU／sanitizer／Debug／main CMakeのscheduler受入、全機械clock／commit／例外経路証明、実時間性能、SDK／ゲーム／FixedClock置換／一般接触応答は今回未実施のままである。
