# 保持荷重の小型証明recordの取得条件

2026-11-06。未実装の次段。Snapshot/Workの次に実held headerの4型18項目を取得する。

| 型 | 全member |
|---|---|
| InitialProof | lower_gap_certificate, upper_gap_certificate, audit_index |
| CertifiedLeaf | cell, lower_gap_certificate, audit_index |
| Witness | cell, time, exact_path_bounds, anchor, error_upper, upper_gap_certificate, audit_index |
| EntryWindow | time_bounds, time_width, path_bounds, l1_diameter_bound, witness_audit_index |

Intervalは実lower()/upper()から端点を読む既存取得を使用し、再構築や中点計算をしない。
Bounds3は全3区間の原順array。秒の2端点も全array、時刻とerror_upperは元F64 bit。
anchorは実Vec3、indexは明示的U64 count。depthは実Cellを通す。
getterでp(t)を再計算せず、axisの並べ替え、窓幅計算、normalや欠けた証拠の補完をしない。
EntryWindow.l1_diameter_boundの下端を物理的変位や侵入の下限と呼ばない。
time_width[秒]とpath_bounds/diameter[メートル]を区別する。

全到達値を明示初期化した複数の人工recordを最初のfixtureとする。
intervalの許可された構築域と、公開doubleのraw bit取得域を分ける。
異なる全axis・両端、Cell、全64bit index、原順を独立参照で比較する。
モデルが返した証拠という認証はこの取得試験から主張しない。
新fixtureで実Intervalを作る場合は旧interval.cppを試験専用で明示linkする。
製品は既存2TUのまま。実model queryや数値model libraryは不要。

全callback停止/例外/4型再入と4丸めmode取得、全byte再取得を確認する。
丸めmodeを変更する前にIntervalを構築する。構築とconst取得の契約を混ぜない。
全scalar byteとkeyの改変、root record入替/削除/重複、固定配列の要素順と個数の改変を独立に拒否する。
fresh Release/真Debugで旧11fixtureの3112/4587/3706/3937/1037/3241/12924/5414/20256/2507/4907byteと全run出力を保持する。
予定schemaは47型265項目。16header+manifest gate、全getter順descriptor、旧20profileを維持する。
GNU通常/真Debug/製品と試験用旧Intervalを含む全TU O1 ASan-UBSan、Native全byte一致は別受入。

held全13型98項目中、この段の完了後は10型51項目に対応する見込み。
残るCellAudit18、PartitionLeaf4、Result25の3型47項目は別段。
optional arrayとoptional enumの明示経路を用意し、全audit/partition/frontierと最上位Reportへ進む。
この計画は全Report、C API pump、JS/WASM/game接続の実装ではない。
