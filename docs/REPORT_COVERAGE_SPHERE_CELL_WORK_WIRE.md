# sphere boxの時間区間と平方根計算量を保存する

2026-11-06。`accelerated_sphere_box_coverage::Cell`全3項目と`Work`全7項目のconst取得をNative有限受入。取得範囲は81record型466項目＋別variant1型、coverage内26record120項目／残り3record22項目。Native実結果は`reports/diagnostic-wire-coverage-sphere-cell-work-verification.json`を参照。GNU・公開は別受入であり、Native成功から推定しない。

| 元の項目 | 保持する内容 |
| --- | --- |
| Cell.time_bounds、depth、parent_audit | 元の秒2端点、UInt32深さ、元の64bit親位置または欠損 |
| Work.value_calls_attempted、value_calls_returned | 常に元のwrapper試行・返却回数 |
| sqrt_results_returned、sqrt_refinements_returned、sqrt_limited_returns | 完全に返却されたEvaluationから観測した元のroot計数 |
| sqrt_refinements_upper、exact | 未観測blockを含む元のroot計算量上限と、その計数の確定状態 |

exactはroot計算量に関するflagであり、falseでもwrapperの試行・返却回数を捨てない。未返却rootを実観測へ加算したり、上限値を実消費量と同一視したりしない。取得時に計数の再推定、親番号の振り直し、秒区間の修正、flag再判定を行わない。

人工Cell8件は元の16種類のbinary64 bit（負零、subnormal、非有限、NaN payloadを含む）と、親位置の欠損4／存在4を保持する。人工Work8件は6種類の64bit計数を、0／UINT64_MAX／2^53+1／2^63を循環した4パターンとexactの両値で比較する。これらはモデルが人工不整合値を生成・受理したことの認証ではない。

初回単体では全2,759byte SHA256 `dd2c8420c62bc46aa72a082929d2bcae41c5682d3e1654a5b2151652cce793f5`、84typed leaf（F64 16／負零1、U64 52、U32 8、bool8）がRelease／Debugで一致した。308callback境界の停止／例外616件、再入拒否616件、4丸めmodeの保持も新対象の単体で確認した。

全scalar／key byte1,880件（typed payload584byte）、root順序・個数3件、欠損→null4件、存在→欠損／null8件、端点交換8件、秒配列の個数16件、field値交換176件、objectのfield順序16件の計2,111変更を検出。同値となるfield交換16件は拒否件数へ含めない。

新対象の閉包は製品2data TU＋harness1TUで、Interval構築TUと数値model libraryを加えない。旧回帰harnessのInterval TUとは区別する。GNUの通常・真Debug・新3TUすべてへのO1 ASan／UBSanは別受入。

初回単体は`reports/diagnostic-wire-recipes/run-20261106-coverage-sphere-cell-work-early-001/verification.json`、変更検査は同`coverage-sphere-cell-work-controls-001/`。全Nativeは別fresh `build/wfdcscw2`と`coverage-sphere-cell-work-native-001/`で実行する。最上位World Report、C API pump、今回取得のWASM／ゲーム接続は後続。[次はAudit／PartitionLeaf全10項目](REPORT_COVERAGE_SPHERE_AUDIT_PARTITION_WIRE_PLAN.md)。
