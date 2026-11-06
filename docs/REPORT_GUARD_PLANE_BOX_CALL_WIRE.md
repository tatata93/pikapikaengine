# World guardの平面包絡呼出記録を保存する

2026-11-06。`world_static_mesh_flight_guard::PlaneBoxCall`全8項目のconst取得をNative有限受入。合計87record型512項目＋別Input variant1型。正式記録は`reports/diagnostic-wire-guard-plane-box-call-verification.json`。GNU・公開は別受入。

| 元の項目 | 保存する内容 |
| --- | --- |
| state、attempt_ordinal | 元の状態ordinalと、全child呼出にまたがる元の64bit試行位置または欠損 |
| requested_settings、used_settings | 元の要求設定と実使用設定を別々に保持 |
| granted、grant | 元の許可boolと、拒否時も保持された計算済みGrant |
| result、messages | 元のplane box coverage Result全12項目または欠損、元のMessageOmission全4項目 |

返却結果のSnapshotは球の点係数、未正規化の平面係数、呼出元が宣言した位置誤差B・接触margin、元の秒・設定を持つ。Inputはstructであり、PlaneMetricCallの球対／球平面Input variantとは異なる。全監査20件・区画12件・前線・current・計数・本文と、返却済みEvaluationの全3軸Intervalを保存する。欠損を架空のゼロ区間で埋めず、再query・法線正規化・順序修正・grantのchargedへの置換・本文復元を行わない。

これは人工診断値の保存試験である。B・marginの妥当性、実Worldからの誤差Bの導出、数値モデルの認証を証明するものではない。

fresh `build/wfdgpb1` Release／真Debugの全44,917byte SHA256 `65ad735fc6135ebf110380ae743e5bc299225f4a531fee0a47e12d1c5cb6e7f2`が独立したplane coverage・Ledger仕様に一致した。人工16Call／1,348typed leaf（F64 483／負零35、U64 546、U32 98、bool79、enum134、bytes8）、存在111／欠損89、外側の全16optional・bool組合せと4試行位置境界を確認した。全件で要求設定と実使用設定が異なる。

6,125callback、停止／例外12,250件、再入12,250件、4丸めmodeの保持も新対象のみで成功した。単体原記録は`reports/diagnostic-wire-recipes/run-20261106-guard-plane-box-call-early-001/verification.json`。

全Nativeは別fresh `build/wfdgpb2`で受入。旧40＋新1の41CTestを分割して各240秒、全32,234変更を16分割して各180秒の上限を維持して全件受入。同値交換74件（field68、array6）を変更拒否へ数えない。製品2data TU＋harness1＋元Interval試験用1TU、数値model library非結合。主参照／wire／plane Result／plane Source-Snapshot／plane Audit-Partition／plane Cell-Work／Ledgerの実7scriptを固定する。人工sourceは既存plane Resultのconst値定義から構成し、新たな共有headerやモデル照会は使わない。

SphereCall、PlaneCalls、別Child variant、Pair／GuardResult、最上位World Report、C API pump、今回取得のWASM・ゲーム接続は後続。
