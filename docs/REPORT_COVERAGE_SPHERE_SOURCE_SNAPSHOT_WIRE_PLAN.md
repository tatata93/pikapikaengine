# sphere boxの元入力とSnapshotを保存する次段

2026-11-06。plane全Result後の未実装計画。実headerの`accelerated_sphere_box_coverage::Input`全5項目と`Snapshot`全3項目を宣言順に取得する。

| 型 | 保存する項目 |
| --- | --- |
| Input | first、second、first_position_error、second_position_error、contact_margin |
| Snapshot | input、horizon、settings |

二つの元Sphereと各軸スカラー位置誤差B1／B2、明示marginを独立に保存する。BをVec3化したり、二つの誤差をまとめたり、半径へ加算して置き換えない。Snapshotの元の秒と、sqrt_refinementsを含む全Settingsも保持する。取得時にtube・root・distanceを再計算せず、元値の不整合や不正入力を修復しない。

人工値の全binary64 bit・負零・subnormal・非有限・NaN payload、全64bit計数とUInt32を独立仕様へ照合する。scalar／key byte、全field値・順序、停止・例外・再入、4丸めmode、17header gate、旧全fixture／全run出力／20profileと保護原本を検査する。

新harnessにInterval構築TUや数値model libraryは不要の設計とし、実compile／link閉包で確認する。Native・GNU・公開を別受入とし、実行前にfixture長やcallback数を成功値にしない。その後Evaluation、Cell／Work、Audit／PartitionLeaf、全Resultへ進む。
