# plane boxの監査と区画を保存する次段

2026-11-06。Cell／Workの後に、`accelerated_plane_box_coverage::Audit`全6項目と`PartitionLeaf`全4項目を取得する未実装計画。

| 型 | 宣言順と取得form |
| --- | --- |
| Audit | cell(field)、call_attempted(field)、evaluation(optional)、outcome(enumeration)、blocked_reason(enumeration)、split_time(optional) |
| PartitionLeaf | cell(field)、state(enumeration)、audit_index(optional_count)、blocked_reason(enumeration) |

`evaluation`は返却された全Evaluationまたは欠損を保持する。値がないときに再query・全区間・零区間で埋めない。call_attempted、outcome、blocked_reason、split_timeは独立した保存値であり、取得時に整合性修復をしない。人工的な不整合値を実数値モデルの生成物と呼ばない。

元のCell、親監査位置、区画の監査位置、分割時刻と欠損をそのまま保存する。raw enumの未定義値やUINT32_MAX、全binary64 bit、full64親位置、全optional maskと原順を検査する。Intervalは既存の正当なpublic constructorだけで人工構築し、その実装TUを新harnessの試験専用依存として明示する。製品取得層には数値演算やmodel libraryを加えない。

各scalar／key byte、全field値と順序、optionalの欠損／存在、停止・例外・再入、4丸めmode、17header schema gateを独立に比較する。旧全fixture／全run出力／20profile／保護原本を保持し、製品2data TUと試験用Interval TUを実compile／linkで区別する。fixture長やcallback数を実行前に成功値として固定しない。

NativeとGNU、公開の受入は別々に記録する。その後plane全Result、sphere box依存、World guardの呼出recordと最上位Reportへ進む。
