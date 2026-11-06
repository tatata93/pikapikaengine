# World guardの平面計量呼出記録を保存する

2026-11-06。`world_static_mesh_flight_guard::PlaneMetricCall`全8項目のconst取得をNative有限受入。合計86record型504項目＋別Input variant1型。正式記録は`reports/diagnostic-wire-guard-plane-metric-call-verification.json`。GNU・公開は別受入。

| 元の項目 | 保存する内容 |
| --- | --- |
| state、attempt_ordinal | 元の状態ordinalと、全child呼出にまたがる元の64bit試行位置または欠損 |
| requested_settings、used_settings | 元の要求設定と実使用設定を別々に保持 |
| granted、grant | 元の許可boolと、拒否時も保持された計算済みGrant |
| result、messages | 元のpair coverage Result全12項目または欠損、元のMessageOmission全4項目 |

返却結果のSnapshotには、球同士または球と平面の元入力が入る。各入力の全係数・設定、全監査20件・区画12件・前線・current・計数・本文を保存する。再query、正規化、順序の修正、grantのchargedへの置換、省略済み本文の復元を行わない。人工不整合値の保存は数値モデルの認証を意味しない。

fresh `build/wfdgpm2` Release／真Debugの全38,466byte SHA256 `5c788270b133869a0cae0702966e720fa4a8859f11a21304e9823020aa999cc2`が独立したpair coverage・Ledger仕様に一致した。人工16Call／1,134typed leaf（F64 284／負零22、U64 550、U32 93、bool75、enum124、bytes8）、存在86／欠損99、入れ子variant5、外側の全16optional・bool組合せと4試行位置境界、全件異なる要求／実使用設定を確認した。

5,032callback、停止／例外10,064件、再入10,064件、4丸めmodeを確認した。正当な公開`emplace`の変換例外4件によって、MSVCではInputが値なしになる4経路を実測。24状態、出力途中の正確なprefix16件、既存失敗20件、値なし値による再入20,128件を確認した。`invalid_state`の伝播後も既にsinkへ渡したbyteを取り消さない。GNUで同じ経路が値なしになるとは推定せず、保持された場合の結果を別に測定する。private byteの改変は使わない。

初回early001では独立参照が「球と平面の入力を含まない」fixtureを拒否した。失敗時source・全出力を保存し、実SnapshotのInput ordinalを確認してResult5を選んだ。修正後のfresh early002で両入力形式を受入。元の失敗を成功へ置換しない。

全Nativeは別fresh `build/wfdgpm3`で受入。旧39件と新1件のCTestを分割し各240秒、全28,362変更を16分割し各180秒の上限を維持して全件受入。同値交換49件（field44、array1、variant4）は変更拒否へ数えない。製品2data TU＋harness1＋元Interval試験用1TU、数値model library非結合。独立仕様は主参照／wire／pair Result／Snapshot／Audit-Partition／Cell-Work／Ledgerの全7scriptと人工source headerを固定する。

PlaneBoxCall／SphereCall、別Child variant、PlaneCalls／Pair／GuardResult、最上位World Report、C API pump、今回取得のWASM・ゲーム接続は後続。


公開追記: source8e13691fは実GNU13.3通常／真Debug／全4TU O1 ASan-UBSan、実oracle全7path／35source、Engine全9jobとPages成功を受入。GNUの公開emplaceは値なし0／保持4、MSVC値なし4と区別。公開READY／出撃有効と原著図解を確認。正式記録は`reports/diagnostic-wire-guard-plane-metric-call-gnu-verification.json`と`reports/diagnostic-wire-guard-plane-metric-call-public-verification.json`。今回取得のgame接続を完了扱いしない。
