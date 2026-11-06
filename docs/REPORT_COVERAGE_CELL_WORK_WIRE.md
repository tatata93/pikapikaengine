# pair coverageの時間区間・所属・計算記録を保存する

2026-11-06。`accelerated_pair_coverage::Cell` の3項目と`Work`の4項目を宣言順に取得する。診断全体は65record型379項目と別Input variant1型。coverage依存内では10record型33項目を取得し、19record型109項目が残る。

| 型 | 保存する原値 | 意味 |
| --- | --- | --- |
| Cell | time_boundsの全2端点 | 閉じたglobal秒。horizonやdepthから復元しない |
| Cell | depth、parent_audit | U32深さ、U64監査位置のなし・0を区別 |
| Work | value_calls_attempted、value_calls_returned | wrapperの実試行数と返却数 |
| Work | plane_norm_calls_upper、plane_norm_loop_iterations_upper | 計装されていないprivate normの上限 |

getterは時間端点を並べ替えず、負零・非有限値も元bitで残す。parent位置の欠損を0にしない。Workの各値を独立に保存し、上限を64倍計算で作り直さない。上限は内部helperの実測回数ではなく、保存試験も実モデルの計算消費量の測定ではない。

人工Cell8件は16種類のbinary64端点、4深さ、親位置なし4件と全64bitの親位置あり4件を含む。Work4件は4種類の境界U64を4項目へ巡回配置する。独立仕様は1,395byte、44typed leaf（F64 16/U64 20/U32 8）、負零1を比較する。全scalarとkey byteの924改変、root3・absent→null4・present除去/null8・端点交換8・4件数の対交換24も検査する。

Sourceは生存・不変、Writerは排他的に使用する。停止・例外・再入と4丸めmode、全旧fixtureと実行出力、20profile、保護原本を検査する。新harnessは2data TU＋1harness TUでInterval TUと数値model libraryを結合しない。Nativeと実GNUの受入記録を分ける。

最上位Report、物理進行C API、今回取得のWASM／ゲーム接続は後続。次は[監査と区画](REPORT_COVERAGE_AUDIT_PARTITION_WIRE_PLAN.md)。原検証結果は`reports/diagnostic-wire-coverage-cell-work-verification.json`へ集約する。
