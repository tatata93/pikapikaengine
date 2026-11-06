# plane boxの元入力とSnapshotを保存する次段

2026-11-06。pair Result後の未実装計画。`accelerated_plane_box_coverage::Input`4項目と`Snapshot`3項目を追加する。既存の元Sphere、raw StaticPlane、plane Settingsの取得を再利用する。

| 型 | 宣言順と取得form |
| --- | --- |
| Input | sphere(field)、plane(field)、position_error(field)、contact_margin(field) |
| Snapshot | input(field)、horizon(field)、settings(field) |

position_errorは呼出側が宣言した各軸位置誤差Bのスカラー、contact_marginは明示的な元値である。Vector3化、推測、半径への加算や法線の正規化を行わない。Snapshotは不正入力も含む原値の保存であり、認証済みtubeという意味を足さない。

元binary64 bitの独立仕様に負零・subnormal・非有限・NaN payloadを含め、horizonを正規化時刻へ変換しない。Settingsの時間許容差／全件数を含む全7項目の順序と全byteを比較する。位置誤差とmarginの値を交換する変更、名前付きchild交換、停止・例外・再入、4丸めmode、17header gateと旧fixture／20profileを確認する。

この新harnessはIntervalを構築する必要がないため、製品2data TUとharness1TUを基本とする。実include／link閉包で確認し、数値queryや完成済みmodel libraryを追加しない。Nativeと実GNUは別受入とし、実測前のfixture長・callback数・改変件数を成功値として記載しない。以後Evaluation、Cell／Work、Audit／PartitionLeaf、全Resultへ依存順に進む。
