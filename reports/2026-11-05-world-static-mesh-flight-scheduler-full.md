# Native scheduler全transactionの局所有限受入

2026-11-05。正式値は [full-verification](world-static-mesh-flight-scheduler-full-verification.json)。既存1382pumpのselected credit cohortと別に、全Reportを持つ11scenario／28pumpを保存した。43attempt／37commit、41実owned guardと2clock先行拒否、45予定slotのうち2未実行slotを保持した。

fresh MSVC19.51 x64の `build/wfsf1`、7command全成功、986対象前後不変。新writerと共有writerはstrict／WX／非LTO。旧writerのmacroなし51出力2979456Bは全byte一致し、旧独立14自己群／85改変拒否も成功した。旧buildは再構成していない。実保存の[全原本](world-static-mesh-flight-scheduler-recipes/run-20261105-full-fixtures-001/scheduler-full.json)と [Native scope](world-static-mesh-flight-scheduler-recipes/run-20261105-full-fixtures-001/native-scope.md)を分けて残す。

独立checkerは全queueとcredit、別Progress時計を整数RN／Fractionで計算し、全Reportと実guardを検査した。実captured-originと期待candidate chain、実外部pump前後の全World／source／pointerを照合する。中間WorldAfterや欠けたguardを実測として作らない。flight／plane metric／plane-box各8、計24数学childを確認し、sphere childは0。16自己群／146改変拒否、名称・順序独立、実Python -O拒否が成功した。[凍結記録](world-static-mesh-flight-scheduler-reference-development/freeze.json)は開発3試行と全command／原本hashを保持する。最終checkerのroot再実行も成功した。

教材12試験とWeb build `25509ed4cc1d87e4`／54moduleが成功し、[原著図](../docs/learn/diagrams/world-static-mesh-flight-scheduler-transaction.svg)を実ブラウザー表示した。図のplanned3／attempts2／commit1は説明用の例で、測定traceではない。

GNU／全依存sanitizer／本体CMake／新SDK／ゲーム接続は次段。原著scheduler2source、既存7source、SDK、sampleは不変。構成IDやleaf機械監査を全scheduler／clock／commit経路の機械形式証明へ昇格しない。JSON改変拒否はNative allocator／例外の故意fault注入ではない。

同時に、先行source301efa3のEngine41899848629両job成功とPages41899847012失敗を実確認した。deployはupdating_pages中に600000msでtimeout。Git全blob1008325176Bのうちreports999932458Bだが、size errorはなく原因は断定しない。[失敗原本](pages-deployment/run-20261105-legacy-timeout-001/measurement.json)を保持し、[選択Pages配信](../docs/PAGES_DEPLOYMENT.md)へ修正する。検証原本はGitに残す。新workflowの公開成功・manifest／HTTP byte照合・ゲーム起動は、実行後の別receiptで確定する。
