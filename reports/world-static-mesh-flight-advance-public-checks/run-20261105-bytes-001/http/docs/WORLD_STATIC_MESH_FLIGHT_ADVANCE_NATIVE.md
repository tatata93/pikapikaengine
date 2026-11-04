# 全Worldの認証候補を自由伝播へ反映するNative API

2026-11-05。**LOCAL_FINITE_INTEGRATION_PASS**。MSVC19.51 x64の実CMake Releaseで全target、新advance9群、時計18例、全47CTest、7-sourceのVec3／caller／実compile監査、Debugの新旧拒否を確認した。[正式Native実行原本](../reports/world-static-mesh-flight-advance-checks/run-20261105-native-integration-002/result.json)の有限範囲の結果であり、clock／commit全経路の形式的機械証明、GNU／公開CI・Browser SDK接続の成功ではない。先行する隔離試作の9群・18時計例とは別の実行として記録する。

離隔を確認した [read-only World guard](WORLD_STATIC_MESH_FLIGHT_GUARD.md) の完全候補を、実Worldと明示時計へ反映する入口である。[計画](WORLD_STATIC_MESH_FLIGHT_ADVANCE_PLAN.md) と [原著概念図](learn/diagrams/world-static-mesh-flight-advance-native.svg) は処理順を説明する。図は測定traceや実行証明ではなく、新図の実ブラウザー表示も別に確認する。

## 実入口と時計

[world_static_mesh_flight_advance.hpp](../core/include/pikapika/world_static_mesh_flight_advance.hpp) の `pikapika::world_static_mesh_flight_advance` が宣言する。

```cpp
AdvanceReport advance(dynamics::World& world,
                      std::span<const StaticMeshSource> meshes,
                      double horizon_seconds, const GuardSettings& settings,
                      Progress& progress) noexcept;
```

`GuardSettings(margin)` のmarginは必須。Hはglobal秒の有限 `(0,.1]`。World本体に時計はないため、`Progress{double time; uint64_t ticks;}` を別の更新対象とする。timeは有限 `[0,1e9]`、ticksは `[0,2^53−1]`。成功には `ticks+1` が域内で、binary64の `RN(time+H)` が上限内かつ元timeより大きいことが必要となる。Hが丸めに吸収される場合は `not_certified/time_resolution` として進めない。上限判定は表現された提案timeに対する判定であり、厳密実数和の上限判定へ読み替えない。

`advanced_dt=H` は認証した伝播区間を表す。一方、`ClockAudit.represented_dt=RN(proposed_time−original_time)` は表現時計差であり、Hとのbit一致を要求しない。`time_sum`／`represented_difference`／`sum_rounding_error` は各厳密実数式を囲む診断で、時計を補正する値ではない。累積時計が実数時間と厳密一致する保証にしない。元time／要求Hの負零は診断へ保持する。

## commitまで元Worldを変えない

[実装](../core/src/world_static_mesh_flight_advance.cpp) の順序は次のとおり。

1. interval環境、既存guard binding、新advance TU自身のprofile／build identityを検査する。環境受入前にIntervalを構築しない。
2. 時計を事前検査して提案Progressと時計区間を所有する。時計失敗ではguardを呼ばない。
3. 現在のWorld／sourceからguardを一回呼び、完全owned結果を保存する。全pair・全seed・全候補・実child linkとexact work会計を再検査する。外部の古い証拠をcommitする入口はない。
4. 元Progress、body全field／順序、gravity、raw plane、mesh ID／revision／全faceがowned原本に対応することを検査する。全候補を固定bufferへcopyし、全destinationを解決する。
5. private bufferだけの全bodyのforce／torqueを `+0` にし、全bodyをvalidateする。staticも成功tickで荷重を消費する。証拠の元荷重・候補荷重は消さない。全originをもう一度検査し、返却metadataを確定する。
6. catch領域の外にあるnoexcept commitで既存body格納先へ全候補を代入し、Progressを代入する。型のnothrow copy／move／destruction条件をstatic assertionで要求する。最初の実書込以後に検索・検証・割当・診断生成を置かない。

すべての返却失敗で `committed=false`、`advanced_dt=+0`、body／Progress store数0とする。元Worldの荷重を含む全field・時計・source・body address／順序は保持する。guardが失敗しても、時計提案や途中のowned証拠が残る場合がある。**提案があることはcommitの意味ではない。** 成功prefixの反映、Hの自動縮小、旧step／W1／W2へのfallbackは行わない。

この原子性は**単一の同期呼出しが失敗したら外部を変更しないこと**であり、thread／hardware atomicな複数storeではない。callerは呼出し全体でWorld／mesh／設定／Progressへの並行・reentrantな観測と変更を排除し、別々の生存する有効objectを渡す。前後の原本照合は並行アクセスを合法化する仕組みではない。

## 実body・費用・所有の記録

`AdvanceReport` はstatus／reason／failure stage、元と提案Progress、optional ClockAudit、binding、`advance_profile_checked`／`advance_profile_matches`、optionalな完全GuardResult、`CommitWork`／`CommitStorage` を所有する。messageは非規範的であり、割当失敗時は空の最小診断となり得る。返却値へ入力pointer／spanを残さない。

guardの数値child費用とcommitのcopy／検査は別である。`CommitWork` はguard attempts／returns、pair／call record検査、origin body／plane／mesh／face検査、候補copy、validate attempts／returns、destination lookup／解決、最終storeを分ける。origin数は候補validateの前後2回の照合と、失敗時の実検査prefixを含む。guard内の未知実費をcommit側の0へ置換しない。

body／destinationの固定buffer上限は8。`CommitStorage` のslotsとsizeof bytesはこの2bufferの論理的な型payload観測だけであり、Report・全call frame・allocator overhead・使用stack／heap・RSS・物理peakの上限ではない。成功後は証拠内候補と実bodyを全field比較し、意図した差分をforce／torqueの消費だけに限定する。

## 7-source設定と機械監査の範囲

[WorldFlightBinding.cmake](../cmake/WorldFlightBinding.cmake) のsource setは `world-static-mesh-flight-advance-v1`。限定identity対象は `core.cpp`／`core.hpp`／`dynamics.cpp`／guardのhpp・cpp／advanceのhpp・cppの7件である。7件は全依存TU一覧でも、7機械関数の証明でもない。新advance cppにはstrict浮動小数点とwarnings-as-errors、MSVCでは `/GL-`、GNU候補ではSSE2／excess-precision／no-LTO条件等を設定する。Release以外はprofile0とし、未構成・不一致は拒否する。MSVC19.51 x64／GNU13 x86-64 SSE2の設定候補であることと、そのartifactを実際に受入済みであることは別である。

generated identityはsource／設定の識別子であり、実行中binaryの自己測定hashではない。受入には現在の7-source原本、実compile command、object／linked artifact、実call先を対応付ける。古い5-source guard監査だけで新clock TUを受入しない。

現auditorの機械dataflow範囲は既存Vec3の位置差・dot・lengthの3 leafと、実caller target／FMA・x87不使用の検査である。7-source対応は新TUを含む実4CPPのsource／commandをそのprovenanceへ加えるが、**clock全命令・commit全経路のsymbolic機械証明には拡張していない**。隔離試作の逆アセンブル収集も探索的観測として分ける。固定sourceとstrict設定による契約、有限実行の観測、leafの機械dataflow証拠、未実施の全体形式証明を混同しない。

実統合artifactの[別機械review](../reports/world-static-mesh-flight-advance-machine-review/run-integrated-001/review.md)は、選択6関数のCOFF／linked byte／map対応、時計のscalar加減算とinline storeの命令観測を保存し、289入力hashの前後一致を確認した。relocation bytesは比較から明示除外する。単独 `commit` symbolの存在だけで実advance経路を証明せず、実advance内のinline loopも調べた。これはfield／alias同定、全分岐・EH dominance、全依存先、commitの形式証明が完成したことを意味しない。

## 有限統合の実行結果と未完

**LOCAL_FINITE_INTEGRATION_PASS**：短い `build/wfa2` の実Release全targetと9専用群、18時計例（7commit／11拒否）＋整数RN／Fraction参照11自己、47/47CTestが成功。7-sourceのactual Vec3／caller／4CPP command監査、profile0の実Debugで新advanceと旧guardの2拒否commandを確認し、監視99件のsource／既存artifactは不変だった。初回run001は指定build pathが物理的に長くMSB3491で停止した履歴であり、無改修の短path run002成功と分けて保存する。初回を数値核や物理入力の不合格へ読み替えない。

[別Web互換receipt](../reports/world-static-mesh-flight-advance-checks/run-20261105-web-integration-001/result.json)では、既存Node684件・構文・Web buildが成功し、監視506件が不変だった。これは新Browser数値APIの検証ではない。隔離試作・整数RNの選択42149点の[別レビュー](../reports/world-static-mesh-flight-advance-clock-review/run-001/result.json)・synthetic parser拒否も、それぞれ別scopeである。有限例とnothrow型／source監査だけでallocator／child非返却を自然に注入した証拠へ昇格しない。

[旧新の別回帰](../reports/world-static-mesh-flight-advance-checks/run-20261105-legacy-integration-001/result.json)では、保存した旧5-source実行物と新7-source実行物を同じ入力で実行した。W1・simulation・supported・held-load・free-flight・supplementalの6組の全出力は、正規化なしでraw byte一致した。guard51入力は `fixtures[*].result.binding.buildId` だけを除き、key／array順・scalar型・binary64の負零を含め一致した。比較helperの引数名 `normal`／`sanitized` はここでは旧／新を指し、どちらも計装版ではない。両側51入力の独立参照と、新側の12自己試験・138改変拒否・順序／label独立が成功し、source・新旧artifact等の保護224件は不変だった。これはMSVCの同環境での有限回帰であり、別compiler間の全出力一致や一般入力の証明ではない。

未完・別scopeはclock／commit全経路の機械形式証明、GNU／sanitizerと公開CI・Pages、実Browser数値API等である。本書の状態を全target／全入力への形式的受入完了と解釈しない。

9群の内部assertionと18時計例とは別に、[transaction capture001](../reports/world-static-mesh-flight-advance-checks/run-20261105-transaction-capture-001/result.json)で全51入力のWorld／Progress前後・全AdvanceReport・実owned guardを2979456BのJSONへ保存した。新mainのみをstrict／warnings-as-errorsでcompileし、変更していない7-source core libraryと既存7serializer objectへリンクした別開発probeである。元build/nativeとbuild/wfa2は再構成・再buildせず、194保護対象は不変だった。実結果は14commit／26未認証／11不正で、1件のclock拒否を除く50件で実guardを保存した。GuardResultの非規範messageも別fieldへ補い、既存のchild message stripping会計は再構築しない。

[保存データの別provenance照合](../reports/world-static-mesh-flight-advance-checks/run-20261105-transaction-provenance-001/result.json)では、先行する同7-sourceのguard51原本に対し、元入力51件と実owned guard50件が正規化なしで全key／array順・scalar型・binary64負零まで一致した。再queryや代替結果は使っていない。

[独立transaction checkerの実行記録](../reports/world-static-mesh-flight-advance-reference-development/run-001/freeze.json)では全51入力、成功32bodyの全field、失敗37件の全World／Progress／荷重保持、整数／Fraction RN時計、全work／buffer会計が成功した。実guard50件の数学childは180（flight92／metric34／planeBox33／sphere21）。旧184との差4件はclockの先行拒否で実行されていないため、成功したchildへ補わない。14自己試験・85改変拒否、label／順序独立、実Python `-O` での拒否も成功。113body pointerとsizeofはNative観測であり、外部JSONから生addressを独立再観測した証明ではない。

[別の実compile／link command観測](../reports/world-static-mesh-flight-advance-checks/run-20261105-probe-command-001/result.json)で、新mainの `/fp:strict /W4 /WX /GL-`、実非LTO linkと既存library＋7objectの対応を保存した。この新probeの全機械artifact監査は実施していない。全51保存・独立有限受入と、全clock／commit形式証明を分ける。

### 正式transaction targetと別GNUジョブ

main CMakeへ `pikapika_world_static_mesh_flight_advance_fixtures` を登録した。[正式targetの有限集約](../reports/world-static-mesh-flight-advance-formal-target-verification.json)は **LOCAL_FORMAL_TARGET_FINITE_PASS_GNU_PENDING**。新しい短path `build/wfa3` で3targetを実buildし、9群・18時計・全51transaction・独立14自己／85改変拒否が成功した。全transaction原本2979456Bは先行する別probeとbyte一致した。保護194件と7-source build identityは不変。新実行物の既存3leaf／callerと実4core TU・新main strict／WX／非LTO commandも別gateで確認した。全47CTestは先行する同source統合の履歴であり、今回再実行した数へ加えない。

source公開30894e3の[実Linux CI記録](../reports/world-static-mesh-flight-advance-checks/run-20261105-feature-ci-001/result.json)は47CTest／684Node skip0と既存guard監査を通過した。ただし、この旧workflowはadvanceの18時計／51transactionの通常・計装照合を実行していない。これを新APIのGNU全面受入へ読み替えない。

別の `native-world-advance` jobをubuntu24.04／GNU13へ追加した。通常3target、実artifactの既存leaf gate、新3TU Werror、別Debug profile0拒否、全core依存と3harnessのO1 ASan／UBSan、両側9群／18時計／51transactionと独立checkerを実行する。時計比較は正規化なし、transaction比較は実normal／sanitizedの2箇所のbinding.buildIdだけを除外し、全key／型／順序／binary64負零を照合する。Windowsではdriver拒否境界・比較正負試験まで確認したが、新jobの実GNU結果と実行時間は公開実行待ちである。初期20分枠を性能合格として扱わない。

既存FixedClockのvoid callbackは、内部のadvanceが失敗してもcallbackが正常復帰するとtickを消費する。今回は独立Progressまでで、FixedClock scheduler／accumulator／dropped-timeの統合は未実装。新Browser SDK、ゲーム接触適用、mesh TOI応答、一般接触応答・支持・摩擦・流体損傷等の完成を含まない。
