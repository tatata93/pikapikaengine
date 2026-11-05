# guard::Workの22項目を取得する

2026-11-06。診断の値取得へguard::Workを追加し、合計30型171memberになった。
実宣言は`world_static_mesh_flight_guard.hpp`。全Report／C API pump／WASM・ゲーム接続は未完。

| member群 | 取得の意味 |
|---|---|
| child／mesh／plane_metric／plane_box／sphere_boxのattempted／returned | 外側wrapperの試行数と返却数をそれぞれU64で保持 |
| held | 9個のCounterを既存HeldLedger取得へ渡す |
| propagation_attempts／plane_metric_values／box_values | known／upper／exactを別々に保持 |
| bridge_calls_upper／plane_norm_calls_upper／plane_norm_loop_iterations_upper | 上限値をU64で保持。実計測回数とは呼ばない |
| sphere_root_results_returned／sphere_root_limited_returns | 返却されたroot結果の記録を保持 |
| sphere_sqrt_refinements／sqrt_refinements | 各Counterのknown／upper／exactを保持 |
| exact | Work全体のflagを保持。下位flagから再計算しない |

入力の会計を再計算・正規化せず、実const memberから専用sinkへ直接取得する。
全体exactと各Counter.exactが異なる値でも、出力時に修復しない。
取得層は物理的成功や会計の有効性を判定せず、元Worldの再照会や数値モデルの再実行もしない。
Writerの生存・排他操作・返却Status・finish／完了の条件は[値取得](REPORT_VALUES_WIRE.md)と同じ。

fresh `build/wfdwk1` のMSVC19.51 x64 Release／真Debugで全3937 byteが一致した。
同じ型の異なる2recordを出し、独立参照が116scalar（U64 86、bool 30）を照合した。
0／最大整数／2^53超／2^63と、全体・下位exactの異なる組を使用した。
これらは取得用に作った診断値であり、物理計算が実際に消費したworkの測定ではない。

全476 callback境界の952停止／例外と476再入拒否、実4丸めmode保持が成功。
独立参照は文法を保つ262単byte改変とrecord入替／削除／重複3件を拒否した。
既存12葉型・10設定型・7ledger型も実再実行し、旧3112／4587／3706 byteと全実行結果が一致した。
登録CTestはRelease62／Debug60、実行は新Workと旧3種の各4件のみ。
数値coreをbuild／linkせず、schema gateは既存15header＋manifestを維持した。

原本は`reports/diagnostic-wire-recipes/run-20261106-work-native-001/`。
integration、旧20profile、Node回帰、実GNUは、それぞれ実結果の記録を参照する。
次はinterval端点とSqrtResultの実値、全audit／partition／frontier、最上位Reportへ進む。
Intervalの実構築と取得時のaccessorを分け、NaN等を内部byte書換えで捏造しない。


integrationの実source gateは1受理／18拒否、旧20profileの全byte一致、Node693 skip0・構文・Web build25509ed4cc1d87e4／54modules成功。正式要約はreports/diagnostic-wire-work-verification.json。新Workの実GNUは公開CIで別受入する。
