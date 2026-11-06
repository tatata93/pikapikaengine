# World guardのプリミティブ呼出記録を保存する次段

2026-11-06。MeshCall後の未実装計画。最初の最小段はPlaneMetricCall全8項目。続いてPlaneBoxCall、SphereCallの各8項目へ進む。どの実型もstate、attempt_ordinal、requested_settings、used_settings、granted、grant、result、messagesを宣言順に保持する。

要求設定と実使用設定、許可と計算済みGrant、返却結果と欠損、元のMessageOmissionは別の値である。元の全child通算試行位置を保存し、保存順へ振り直さない。拒否時のgrantを消さず、未知の結果や除去済み本文を復元しない。各結果の全監査・区画・前線・current・計数・本文を保存する。

各実型の依存serializerを再利用し、独立子仕様へ全値を比較する。人工状態・optional・bool、未知ordinal、整数境界、停止／例外／再入／丸めmode、全field／配列／本文の異なる有効文法変更と同値交換、17header gate、旧全fixture／実行出力／20profile／保護原本を確認する。Native・GNU・公開は別受入。

その後のPlaneCalls2項目、Childの別variant境界、PairRecord全5項目、準備の全依存とGuardResultも別段とする。呼出記録の取得だけで最上位World Report／C API pump／今回取得のWASM・ゲーム接続を完了扱いしない。
