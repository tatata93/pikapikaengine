# sphere boxの全Resultを保存する次段

2026-11-06。Audit／PartitionLeaf後の計画。Native実結果は[全Result取得](REPORT_COVERAGE_SPHERE_RESULT_WIRE.md)と正式受入JSONを参照。GNU・公開は別受入。元headerのResult全12項目を宣言順に取得する。

| 宣言順 | 元の項目と保持内容 |
| --- | --- |
| 1–4 | status、reason、snapshotまたは欠損、snapshot_validated |
| 5–6 | failed_inputの元位置または欠損、partition_complete |
| 7–9 | audits、partition、frontierの全要素と元順序 |
| 10–12 | currentまたは欠損、work、messageの全byte |

failed_inputは0=first sphere、1=second sphere、2=first B、3=second B、4=marginという元の診断位置を保存する。currentはfrontierの先頭へ移動せず、前線と独立したoptionalとして保存する。messageの空文字と任意byte列を保持し、規範的な判定へ格上げしない。

全要素・全tail・重複・元の順序とoptionalの存在／欠損を保持する。再query、番号修正、本文の短縮、確定flagや計数の再推定を行わない。人工fixtureと実数値queryを区別し、公開constructorだけで構築する。

独立の全byte仕様、全fieldと配列、全optional mask、callback停止／例外／再入／丸めmode、異なる有効文法変更と同値交換の分離、17header gate、旧全fixture／実行出力／20profile／保護原本を確認する。Native・GNU・公開を別受入とする。全World Report／C API pump／WASM・ゲーム接続はこのResultだけで完了としない。
