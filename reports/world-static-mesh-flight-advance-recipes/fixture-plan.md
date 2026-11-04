# Native advance全transaction fixtureの追加harness

2026-11-05。**実装ソースを配置した段階。今回の所有範囲ではcompile・実行・独立checkerを実施していない。** 既存のadvance 9内部assert群／18時計JSONとは別の証拠入口であり、それらの置換や正式advance全受入の宣言ではない。本体・header・既存test・CMake・GNU driver・auditor・既存receiptは変更しない。

## 入口とsource

新しい独立mainを持つ `tests/world_static_mesh_flight_advance_fixtures.cpp` のCLIは `--fixtures` 一つだけ。引数不正はexit2、capture／serialize／出力失敗はexit1、完成documentの出力完了でexit0。rootレビュー後に専用targetを構成する。まだそのtargetを追加したり実行したりしていない。

`world_guard_fixture::cases()` の既存51入力を名前・順序・設定・mesh原値を変えずに使用する。caseごとにfreshなCase（World／mesh／settings）をcopyし、`Progress{.125,17}` から**実 `advance` を一回だけ**呼ぶ。独立guard query、伝播の再計算、旧結果のimport、期待statusによる補填は行わない。guardの既存 `Case.expected/reason` はadvance結果を作るために参照しない。

元の最小2dynamic×2mesh＋plane等、非空Worldの全body field／held force／torqueを保存できる。既存51にはempty／static-onlyも含まれるため、それらも除かず保存する。全51がguardへ到達するという期待は置かない。例えば非常に短いHでは、同じ有効Progressでも時計の非進行で先に拒否し得る。`report.work.guardQueriesAttempted/Returned` は実返却値そのままであり、外側advance一回と区別する。

各実Reportの `advanceProfileChecked && advanceProfileMatches` を要求する。未構成／不一致profileの51拒否を通常のconfigured transaction corpusへ代入しない。runtime環境拒否等によってこの条件を満たさなければdocument全体を出さず失敗する。これはconfigurationラベルの確認であり、新artifactの機械監査成功の主張ではない。無効clock等の既存18時計入力は変更せず、今回の51へ混ぜない。

## JSON envelopeと各row

envelopeは `schema:1`、`kind:"world-static-mesh-flight-advance-transaction-fixtures"`、scope文、`initialProgress`、既存guardの `layoutSizes`、新5型の `advanceLayoutSizes`、`fixtures`。sizeofはこの実行構成の観測値のみで、使用heap／stack／RSSの上限ではない。

各rowは次を持つ。

- `name`、`input`、`inputAfter`：既存 `input_json` が保存する全body／raw plane／gravity／全mesh ID・revision・face ID・頂点／H／全settings。`input` は呼出し前、`inputAfter` は実呼出し後の値。
- `worldBefore`／`worldAfter`：既存 `world_json` による全World。body全field、向き、角運動量、force／torque、material、ID、順序、raw planeを省略しない。
- `progressBefore`／`progressAfter`：実time／uint64 ticks。ticksをdoubleへcastせず十進整数として保存し、宣言域 `0..9007199254740991` を越えた診断は拒否する。
- `report`：下記の実AdvanceReport全fieldと、既存guard writerの省略を補う `guardMessage`。
- `observations`：実原本との比較。`captureComplete` はharness自身の全入力記録の完了であり、nested preparationのcapture状態を上書きしない。`advanceCalls:1`、mesh原値bit比較の `sourceUnchanged`、settingsのmax_digits10／負零保持JSON比較、H／plane／gravityのbit比較、全World JSON一致、Progressのbit／整数一致を別々に記録する。

`failureAtomicObserved` は未commit時のWorld＋Progress一致の実観測boolean。commit時は適用対象外としてnull。これだけでsource／pointerの不変を代用せず、それらは別の観測fieldを読む。booleanがfalseでもtrueへ補正しないため、異常traceは保存可能である。下流checkerがその適否を判定する。低位のcaptureやJSON構文に失敗した場合はrowを途中まで出して「観測完了」としない。

`pointerStability` はbody／plane／meshのdata pointer比較、各元body ordinalのaddress比較、元IDによるfind_bodyの呼出し前後結果、mesh別face vectorのdata pointer比較を保存する。生address値は出さない。重複body ID等の不正入力ではfind_bodyが最初のordinalを返す場合があるため、`lookupBeforeMatchesOrdinal` と `lookupAfterMatchesOrdinal` をそのまま保存し、最初から全trueとは仮定しない。これは同一プロセス内の安定性観測であってthread atomicityの証拠ではない。

## Reportと省略scope

新writerは `status/reason/committed/requestedDt/advancedDt/originalProgress/proposedProgress/clock/binding/advanceProfileChecked/advanceProfileMatches/failure/guard/work/storage/message` を保存する。optionalは不在時に明示null。clockは `timeSum/representedDifference/sumRoundingError/representedDt`。failureはstageと、あればtyped object kind／index／faceIndex。workはCommitWorkの全15 counter、storageはCommitStorageの全4 fieldである。

`guard` は**そのadvanceが返したoptional GuardResultだけ**を既存 `world_guard_fixture::result_json` へ渡す。全source snapshot／inventory／全pair／全child call・grant／nested audit・partition・frontier・候補／work／retained予約を既存形式のまま保存する。`world_guard_fixture::binding_json` と `layout_sizes_json` も再利用する。

既存guard writerは `GuardResult.message` を省略する。このfieldは新Report JSONの **`guardMessage`** に実文字列をescapeして補足する。guard不在ならnull、存在して空文字なら空文字。`AdvanceReport.message` 自体も保存する。guardは設計上、child／preparationの非規範messageを既にstripし `MessageOmission{fields,nonemptyFields,bytes,omitted}` を保存する。今回それらの失われたtextを再構築せず、旧nested writerのこの明示省略scopeを継承する。数値fieldを省略したり、nullを別の計算結果で埋めたりしない。

新status／reason／stage／object kindを未知enumなら拒否する。既存writerのenum配列参照前にもguard／preparation／call／child／held／mesh／singleの該当enum範囲を検査し、未知値で配列外参照を起こさない。これは形式・保存時の検査であり、物理条件の再計算ではない。

## 厳密な保存と失敗

classic locale、binary64 `max_digits10`、負零 `-0` を使用する。新messageはJSON control／quote／backslashをescapeし、UTF-8の不正sequenceを拒否する。既存数値writerと新数値writerは非finiteを拒否する。全documentを一旦bufferし、最後にJSON grammar／全数値tokenのfinite変換／末尾余剰なしを検査してからstdoutへ出す。これはJSON構文gateであり独立物理検証ではない。旧nested writer用のstd::cout format／localeを保存・復元する。一部nested writerのstreambuf redirectも既存実装のまま使用する。

stdoutの最終writeが失敗すればexit1であり、consumerはexit0と完全JSONの両方を必要とする。OS出力先の切断までhardware atomicにする主張はしない。allocator／nonreturn fault注入、敵対enum／JSON writer故障注入、実strict-Werror compile、JSON再読込、全51実結果の分類、独立checker、GNU／sanitizer／公開検証はこのauthoring段階で未実施である。

## rootレビュー後の依存TUと受入

新main TUとcore libraryに加え、既存serializer／input factory依存は以下の7TU。旧testのmain TUはlinkしない。entryの低位JSON writerは既存inline header経由であり、entry test mainを追加しない。

1. `tests/world_static_mesh_flight_guard_fixtures.cpp`
2. `tests/world_static_mesh_flight_preparation_fixtures.cpp`
3. `tests/sphere_triangle_mesh_free_flight_guard_fixtures.cpp`
4. `tests/sphere_triangle_mesh_held_load_fixtures.cpp`
5. `tests/accelerated_pair_coverage_fixtures.cpp`
6. `tests/accelerated_plane_box_coverage_fixtures.cpp`
7. `tests/accelerated_sphere_box_coverage_fixtures.cpp`

今後の専用targetでは新mainをstrict FP＋MSVC `/W4 /WX /permissive-`／GNUの既知warning拒否でcompileし、実7-source profileのlibraryへlinkする。CMake／監査／旧SDKの変更はroot所有。原guard51のinput全key/type/floatbitsとの一致、完全JSONの再読込、全Progress／World commit対応と失敗不変、所有guardの数学・metadata再検証、負例、sizeof観測scope、全受入のprovenanceを別checkerで確定する。このメモはそれらの成功を代用しない。
