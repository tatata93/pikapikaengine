# sphere boxの監査と区画を保存する次段

2026-11-06。sphere Cell／Work後の未実装計画。実headerのAudit全6項目（cell、call_attempted、evaluation、outcome、blocked_reason、split_time）とPartitionLeaf全4項目（cell、state、audit_index、blocked_reason）を宣言順に取得する。

元のCell、返却されたEvaluation全9項目または欠損、試行flag、元のraw enum、分割秒または欠損を保持する。区画の元の監査位置は64bitのまま保存し、番号の振り直し・再query・零埋め・理由やflagの再判定を行わない。未返却Evaluationの代わりに計算を再実行しない。

人工値ではpresence／boolの全組合せ、元の親位置と監査位置、全3軸とrootの全戻り値・元のdistanceコピー、不正なenum ordinalや元のsplit_time F64 bitを独立仕様へ比較する。Intervalは正当なpublic constructorだけを使い、NaN／反転区間を偽造しない。sourceの人工不整合は数値モデルの生成・認証を意味しない。

全scalar／key byte、optionalのnull混同、全field値と順序、各軸配列の順序・個数、停止／例外／再入／4丸めmode、17header gateと旧全fixture・assertion・20profileを確認する。Native・GNU・公開を別受入とし、その後は全Result12項目へ進む。
