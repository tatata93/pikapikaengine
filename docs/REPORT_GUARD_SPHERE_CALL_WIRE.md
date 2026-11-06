# World guardの球包絡呼出記録を保存する

2026-11-06。`world_static_mesh_flight_guard::SphereCall`全8項目のconst取得をNative有限受入。合計88record型520項目＋別Input variant1型。正式記録は`reports/diagnostic-wire-guard-sphere-box-call-verification.json`。GNU・公開は別受入。

| 元の項目 | 保存する内容 |
| --- | --- |
| state、attempt_ordinal | 元の状態ordinalと、全child呼出通算の64bit試行位置または欠損 |
| requested_settings、used_settings | 元の要求設定と実使用設定を別々に保持 |
| granted、grant | 元の許可boolと、拒否時も保持された計算済みGrant |
| result、messages | 元のsphere box coverage Result全20項目または欠損、元のMessageOmission全4項目 |

返却結果のSnapshotには二つの球の点係数、それぞれの宣言誤差B1／B2、明示margin、元の秒と設定がある。半径への合算や拡張、再query、区間・sqrt結果の再計算をしない。元の全3軸配列、SqrtResultの値・計数・limited、全監査20件・区画12件・前線・current・未処理tailと省略計数を保持する。欠損をゼロ値で埋めず、grantをchargedへ置換せず、省略済み本文を復元しない。

これは人工診断値の保存試験である。実Worldからの誤差B1／B2の導出、その妥当性や数値モデルの認証は別である。実API型は`SphereCall`であり、保存試験artifactの`guard-sphere-box-call`という名前と区別する。

fresh `build/wfdgsc1` Release／真Debugの全60,749byte SHA256 `254c6e5196306fd87f155ad68f13217ced5e580303b9ba87987ba4495bb5a21a`が独立したsphere coverage・Ledger仕様へ一致した。人工16Call／1,852typed leaf（F64 871／負零63、U64 578、U32 154、bool107、enum134、bytes8）、存在111／欠損89、外側の全16optional・bool組合せと4試行位置境界を確認した。全件の要求設定と実使用設定は異なる。

8,389callback、停止／例外16,778件、再入16,778件、4丸めmodeも新対象だけで成功した。early原記録は`reports/diagnostic-wire-recipes/run-20261106-guard-sphere-box-call-early-001/verification.json`。全Nativeは別fresh `build/wfdgsc2`で受入。旧41＋新1の42CTestを分割して各240秒、全42,907変更を16分割して各180秒で全件受入。同値交換117件（field111、array6）は変更拒否へ数えない。

製品2data TU＋harness1＋元Interval試験用1TU、数値model library非結合。主参照／wire／sphere Result／sphere Source-Snapshot／sphere Audit-Partition／sphere Cell-Work／Ledgerの実7scriptを34source内へ固定する。人工sourceは既存sphere Resultのconst値定義から構成し、新たな共有headerを増やさない。

PlaneCalls、別Child variant、Pair／GuardResult、最上位World Report、C API pump、今回取得のWASM・ゲーム接続は後続。
