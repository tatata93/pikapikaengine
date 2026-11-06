# sphere boxの結果全体を保存する

2026-11-06。`accelerated_sphere_box_coverage::Result`全12項目のconst取得をNative有限受入。合計84record型488項目＋別Input variant1型、coverage依存内全29record142項目。正式記録は`reports/diagnostic-wire-coverage-sphere-result-verification.json`。GNU・公開は別受入。

| 元の項目 | 保持する内容 |
| --- | --- |
| status、reason | 元のenum ordinal |
| snapshot、snapshot_validated | 元のInput／秒／全設定または欠損と、独立した元のflag |
| failed_input、partition_complete | 元の失敗位置または欠損と、独立した元のflag |
| audits、partition、frontier | 全要素・原順・重複・全末尾・空配列 |
| current、work、message | 停止中のCellまたは欠損、元の7項目の計数、本文の全byte |

failed_inputは元の0～4の入力位置と64bit境界値を保持する。currentをfrontierへ移動せず、返却されなかった評価を再queryで埋めない。snapshotの存在を検証成功と同一視せず、wrapper計数・rootの実観測・上限とexactを個別に保存する。本文の埋込NULや非UTF8を変換・短縮しない。借用した元データの寿命・不変性とWriterの排他所有が必要で、sink失敗時は送信済みprefixを保持する。

新対象のみのfresh `build/wfdcsrl1` Release／真Debugでは、人工32Resultの全57,252byte SHA256 `96e49d871fbd6d0713112787c1d199310eba11086a60c087368fa51011fd9d2e`が独立した子仕様と一致した。1,740typed leaf（F64 1,008／負零74、U64 282、U32 119、bool139、enum160、bytes32）、存在119／欠損125、外側optional全8maskとboolを合わせた全32mask、全437本文byteを確認した。最終Resultは全20監査・全12区画と重複を含む末尾を保持する。失敗位置は既知0～4と3つの大整数境界の全8値を含む。

8,447callback、停止／例外16,894件、再入16,894件、4丸めmodeの保持も単体で成功した。Debugの実行時間はその実機・実負荷で166.719秒であり、性能保証ではない。人工不整合値の保存を、数値モデルがその値を生成・認証したことの証拠としない。

全Nativeは別fresh `build/wfdcsrl2`で受入。変更検出も全16担当shardの合計38,958件を受入し、同値250交換を別集計した。初8分割のshard0は180秒timeoutで未受入とし、元scanner／recipeと失敗観測を`coverage-sphere-result-shards-001/`へ保持。fresh `shards-002/`で同じ全件を16分割し、各180秒上限を維持する。製品2data TU＋harness1＋元Interval試験用1TUで、数値model libraryを結合しない。最上位World Report、C API pump、今回取得のWASM／ゲーム接続は後続。実結果は`reports/diagnostic-wire-recipes/run-20261106-coverage-sphere-result-early-001/verification.json`を参照し、単体・全Native・GNU・公開の各記録を区別する。
