# pair coverage Snapshotの元入力3項目を取得する次段

2026-11-06。Input variant有限受入後に行う未実装計画。
`accelerated_pair_coverage::Snapshot` のinput/horizon/settingsを、この宣言順の3項目で取得する。
既存62record型369項目＋Input variant1型に、record1型3項目を追加する。

inputは既存のconst variant getterへ渡し、horizonの全binary64 bitsとsettingsの原値を保持する。正の秒への修復、設定defaultへの差替え、validated判定、入力の再queryをしない。snapshot_validatedは後続Resultの独立flagであり、Snapshot自体に架空fieldを足さない。

双方のactive alternative、正負零・非有限horizon・NaN payload、境界U64件数・unsigned max_depthを人工sourceで独立比較する。名前順、元入力/設定の各byteと欠損を勝手に作らないことを検査する。

正当な操作でinputが値なしになった実targetでは、そのchildの実Statusを伝播する。Snapshot getterはobject/keyのprefixを既に送信し得るため、Snapshot全体を出力0byteのtransactionとは呼ばない。Input getter自身の追加byteなし拒否、既存prefixの保持、finish/status/complete/transportの公開条件を分ける。

17header gate、旧primitive/controlと全21record＋Input variant fixture、全run出力、20profile、数値核/owner/SDK/sampleを維持する。新harnessは製品2data TU+harness1TUでInterval TU/model library非link。GNUの通常/真Debug/全TU O1 ASan-UBSanは別受入。

公開manifestは現在8MiB読取上限に近づいているため、各push後に実byte数を確認し、上限へ達する前に有限上限・配布選択・原検証記録の保持を別の小段でレビューする。黙って無制限読取へ変更しない。
その後Cell/Work、Audit/Partition、全Resultへ進む。
