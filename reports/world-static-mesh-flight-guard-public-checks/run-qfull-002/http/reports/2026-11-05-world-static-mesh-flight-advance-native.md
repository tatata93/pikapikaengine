# Native World自由伝播の有限ローカル統合

状態はローカル **LOCAL_FINITE_INTEGRATION_PASS**、続く専用Linux検査は **GNU_FINITE_ADVANCE_PASS**。新 `world_static_mesh_flight_advance::advance` は、内部で現在のowned guardを一度照会し、全候補・元World・宛先・時計を検査した後だけ全bodyと明示Progressを反映する。失敗では位置・保持荷重・時計・格納先を保持する。thread／hardware atomicな複数storeではなく、callerは同期呼出し中の並行・再入を排除する。接触応答は追加していない。

[契約と実入口](../docs/WORLD_STATIC_MESH_FLIGHT_ADVANCE_NATIVE.md)、[正式ローカル集約](world-static-mesh-flight-advance-native-integration-verification.json)にscopeを分けた。実MSVC19.51 x64の短 `build/wfa2` で全target、専用9群、独立整数参照付き18時計例（7commit／11拒否）、47CTest、Debugの新旧2拒否と7-source実4TU command／既存3leaf機械gateが成功した。初回の長path MSB3491失敗を保存し、短pathの別runで成功した。既存 `build/native` とSDKは不変。Web互換のNode684／構文／build、旧新6組の全出力byte一致、guard51入力のbinding ID以外の一致と独立参照も別に成功した。

新しい別probeで51実transactionの全入力・World／Progress前後・Reportを2979456Bとして保存した。1入力1advanceで、実owned guard50件を再queryせず保存した。独立checkerで14commit／37failure、成功32bodyの全fieldと荷重消費、時計RN、失敗不変、実数学child180件を検査した。14自己試験・85改変拒否・label／順序独立と実 `-O` 拒否も成功。入力51とowned guard50は先行同構成原本と全bit／型／順序一致である。新mainの実strict／WX compileと非LTO linkを保存したが、新probe全命令の機械認証とは呼ばない。

[原著図](../docs/learn/diagrams/world-static-mesh-flight-advance-native.svg)と[HTML教材](../docs/learn/index.html#world-flight-advance)を追加し、実ローカルブラウザー表示を保存した。図は概念図で、実測traceや全体形式証明ではない。原型の149証拠・旧plan／図は当時の状態として不変に保持する。

続く正式target登録では、新しいbuild/wfa3で3targetを実buildし、9群／18時計／51transaction・独立14自己85改変拒否が成功した。2979456Bの全transaction原本は先行probeとbyte一致、保護194件とsource identityは不変。新実行物の既存3leaf／caller／4core TUと新main strict-WX／非LTO commandも確認した。全clock／commit命令証明とは区別する。[正式target集約](world-static-mesh-flight-advance-formal-target-verification.json)に実9commandと原本hashを保存した。先行47CTestを今回の再実行へ数え直していない。

source30894e3の公開Linux portable-coreは実47CTest／684Node skip0／既存guard通常・計装検査を含む全工程成功。ただしadvance18時計／51transactionの実GNU検査は旧jobの対象外だった。今回、main CMake登録に加え、別native-world-advance jobへ通常3target、Werror新3TU、Debug新旧拒否、全依存O1 ASan-UBSanと独立clock／transaction照合を接続した。Windows driver smoke002の11拒否／正比較1・改変拒否12が成功。smoke001のstdout／stderr確認先を誤った収集失敗はrawを保持し、GNU実行成功へ混ぜない。実GNU新job、20分枠の実測、公開配信受入は未完。

続くsource bb58cf2の専用GNU job126802750687が実243秒で成功した。実31command、通常版の既存3leaf／callerと4core TU command gate、新3TU Werror、別Debugの新旧拒否、全40coreと17harness commandのO1 ASan／UBSanを確認した。両側9群／18時計／51transaction・独立14自己85改変拒否が成功し、時計全JSONは正規化なし、transaction全JSONは宣言した2箇所のbinding IDだけを除いて一致した。実両側14commit／37failure・成功32body・実child180。source／normal artifacts／compilerは不変。原runner fixtureは各2979455Bのhashと実checker要約をログに保持し、ローカルへrawを別downloadしたとは主張しない。[GNU集約](world-static-mesh-flight-advance-gnu-verification.json)は実ログとREST job／sourceを結ぶ。

同版のPages全3jobが成功し、216Pages＋GitHub workflow1の217原本5087597Bが固定Git blob一致、公開READYと新原著図／説明の実表示を確認した。ゲーム挙動は不変で、この版では出撃を再実行していない。その後portable-coreも全工程成功を確認し、正式公開集約を world-static-mesh-flight-advance-public-verification.json へ保存した。

全clock／commitの機械形式証明、SDK・FixedClock・衝突応答は次段である。先行する5-source guardの公開受入d302を新7-sourceの受入へ読み替えない。任意CFD・材料損傷・専門機体／車両モデル・IK／制御・撮像の完成も含めない。
