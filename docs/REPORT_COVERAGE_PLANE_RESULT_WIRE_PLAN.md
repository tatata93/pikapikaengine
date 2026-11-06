# plane boxの全Resultを保存する次段

2026-11-06。Audit／PartitionLeaf後の計画。Native受入の実結果は[全Result取得](REPORT_COVERAGE_PLANE_RESULT_WIRE.md)とformal receiptを参照。GNUと公開は別受入。`accelerated_plane_box_coverage::Result`全12項目を宣言順に取得する。

| 保存項目 | 取得form |
| --- | --- |
| status、reason | enumeration |
| snapshot | optional |
| snapshot_validated | field |
| failed_input | optional_count |
| partition_complete | field |
| audits、partition、frontier | array |
| current | optional |
| work | field |
| message | bytes |

全監査・区画・未照会frontier・停止中currentを原順・重複・全tailまで保存する。snapshot_validatedとpartition_complete、失敗元位置、status／reasonを独立に取得し、取得時に再判定や修復をしない。未照会のEvaluationや元入力のB、marginを再queryや推定で埋めない。メッセージは埋込NULや非UTF8を含む元の全byteとして扱う。

snapshot／failed_input／currentの全8optional maskと二つのbool、全既知・未定義enum、空配列・複数要素・原順・重複・部分失敗tailを人工値で検査する。Snapshotは元Input・秒・設定、Workは元のwrapper試行数／返却数を保持する。plane ResultにはInput variantの値なし境界を新設しない。

全fieldと型・原順・個数・全byteを独立仕様へ比較する。scalar／key byte、optional境界、全recordと全vector、fieldの値交換と順序、停止・例外・再入、4丸めmode、17header gateを検査する。正当なpublic Interval構築は試験側へ1TUとして分離し、製品2data TUに数値model libraryを加えない。旧全fixture／全run出力／20profile／保護原本を保持する。

Native・GNU・公開を別受入とし、実行前にfixture長やcallback数を成功値として記載しない。その後sphere boxの原入力・Snapshot・Evaluation・Cell／Work・Audit／PartitionLeaf・全Resultへ進み、全coverage依存が揃ってからWorld guardの呼出recordへ接続する。
