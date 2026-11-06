# plane boxのCellとWorkを保存する次段

2026-11-06。Evaluation後の計画。Native受入の実結果は[Cell／Work取得](REPORT_COVERAGE_PLANE_CELL_WORK_WIRE.md)とformal receiptを参照。GNUと公開は別受入。`accelerated_plane_box_coverage::Cell`全3項目と`Work`全2項目を取得する。

| 型 | 宣言順と取得form |
| --- | --- |
| Cell | time_bounds(array)、depth(field)、parent_audit(optional_count) |
| Work | value_calls_attempted(count)、value_calls_returned(count) |

Cellは元の秒の両端をraw binary64 bitで保存し、depthから時間を復元しない。parent_auditの欠損と0、UINT64_MAX、2^53+1、2^63を区別する。元端点には負零・subnormal・非有限・NaN payloadを人工値として含め、正当なInterval構築時の零正規化とは区別する。

Workは保存済みのwrapper呼出試行数と返却数を独立に取得する。plane用の2計数へ、pair用のprivate norm上限や推定反復数を足さない。人工的な返却数と試行数の逆転も修復せず保存し、その組合せを実モデルが生成したとは報告しない。

この新harnessにはInterval構築TUや数値model libraryは不要の設計とし、実compile／link閉包で確認する。全scalar／key byte、時間両端の順序と個数、元親位置、全計数対交換、停止・例外・再入、4丸めmode、17header gateと旧全fixture／全出力／20profile・原本保持を検査する。実測前のfixture長やcallback数を成功値として記載しない。Nativeと実GNUは別受入。その後Audit／PartitionLeaf、全Resultへ進む。
