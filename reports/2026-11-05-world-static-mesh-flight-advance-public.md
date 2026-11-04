# Native World advanceの有限公開受入

source **bb58cf2aff81a00c55f7034dccf153c268824df4** を **PUBLIC_FINITE_ACCEPTED** とした。[正式集約](world-static-mesh-flight-advance-public-verification.json)は、原RESTとdecoded job log、配信raw、実ブラウザー観測を分けて結ぶ。

Engine run41895203663の2jobが成功した。portable-core job126802751106は必須25工程（Completeを含む実26行）、実47CTest／684Node skip0、全既存監査とWASM工程を通過し、可視48GNU診断のmultisetは従来と同一だった。所要時間はREST timestampで1117秒。専用native-world-advance job126802750687は243秒・31commandで成功した。通常artifactの既存3leaf／callerと実4core TU command gate、新3TU Werror、別Debugの新旧拒否、全40coreと17harness compile commandのO1 ASan／UBSanを含む。

専用jobの通常／計装の両側で9群・18時計・51transactionと独立参照が成功した。両側とも14commit／37failure・成功32body・実数学child180、14自己試験／85改変拒否。時計の全JSONは正規化なし、transactionの全key／型／順序／binary64負零は宣言した2箇所のbinding IDだけを除いて一致した。source・normal artifact・compilerは前後不変。runner-localな各2979455Bのtransaction原本はhashと実checker要約をログで保存しており、別途ローカルへraw artifactをdownloadした証拠とは区別する。

Pages run41895200177のbuild／deploy／reportの3jobも成功した。216Pagesと完全commitのGitHub workflow1、計217ファイル5087597Bを固定Git blobと全byte照合した。公開ゲームのC++ WASM／WEBGPU READY、新原著World advance図と説明の実表示を確認した。この版では出撃を再実行しておらず、ゲームのruntime原本も変更していない。背景rAF約1秒の観測を実時間性能保証に使わない。

この受入は有界入力・固定source／構成のNative自由伝播であり、全clock／commit経路の機械形式証明、全CPU・全入力、Browser advance API、FixedClock scheduler、TOI／接触応答・摩擦、CFD・材料損傷・専門シミュレーターの完成を含まない。先行ローカル・準備段階のreceiptは当時の状態として保持し、新しい結果で書き換えていない。

次は[retain-only scheduler計画](../docs/WORLD_STATIC_MESH_FLIGHT_SCHEDULER_PLAN.md)の隔離Native試作へ進む。成功tickだけcreditを消費し、拒否tickと未実行backlogを残す。全frameのrollbackとは区別し、先行advanceの公開受入をscheduler受入へ流用しない。
