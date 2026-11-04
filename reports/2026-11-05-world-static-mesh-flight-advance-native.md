# Native World自由伝播の有限ローカル統合

状態は **LOCAL_FINITE_INTEGRATION_PASS**。新 `world_static_mesh_flight_advance::advance` は、内部で現在のowned guardを一度照会し、全候補・元World・宛先・時計を検査した後だけ全bodyと明示Progressを反映する。失敗では位置・保持荷重・時計・格納先を保持する。thread／hardware atomicな複数storeではなく、callerは同期呼出し中の並行・再入を排除する。接触応答は追加していない。

[契約と実入口](../docs/WORLD_STATIC_MESH_FLIGHT_ADVANCE_NATIVE.md)、[正式ローカル集約](world-static-mesh-flight-advance-native-integration-verification.json)にscopeを分けた。実MSVC19.51 x64の短 `build/wfa2` で全target、専用9群、独立整数参照付き18時計例（7commit／11拒否）、47CTest、Debugの新旧2拒否と7-source実4TU command／既存3leaf機械gateが成功した。初回の長path MSB3491失敗を保存し、短pathの別runで成功した。既存 `build/native` とSDKは不変。Web互換のNode684／構文／build、旧新6組の全出力byte一致、guard51入力のbinding ID以外の一致と独立参照も別に成功した。

新しい別probeで51実transactionの全入力・World／Progress前後・Reportを2979456Bとして保存した。1入力1advanceで、実owned guard50件を再queryせず保存した。独立checkerで14commit／37failure、成功32bodyの全fieldと荷重消費、時計RN、失敗不変、実数学child180件を検査した。14自己試験・85改変拒否・label／順序独立と実 `-O` 拒否も成功。入力51とowned guard50は先行同構成原本と全bit／型／順序一致である。新mainの実strict／WX compileと非LTO linkを保存したが、新probe全命令の機械認証とは呼ばない。

[原著図](../docs/learn/diagrams/world-static-mesh-flight-advance-native.svg)と[HTML教材](../docs/learn/index.html#world-flight-advance)を追加し、実ローカルブラウザー表示を保存した。図は概念図で、実測traceや全体形式証明ではない。原型の149証拠・旧plan／図は当時の状態として不変に保持する。

GNU13向けrecipeは準備・Windows driver拒否試験までで、実GNU advance／sanitizerと公開受入は未実施。新transaction targetのmain CMake登録、GNU workflowへの独立clock／transaction接続、全clock／commitの機械形式証明、SDK・FixedClock・衝突応答は次段である。先行する5-source guardの公開受入d302を新7-sourceの受入へ読み替えない。任意CFD・材料損傷・専門機体／車両モデル・IK／制御・撮像の完成も含めない。
