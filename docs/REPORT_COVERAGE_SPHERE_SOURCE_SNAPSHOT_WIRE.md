# 球同士の元入力とSnapshotを保存する

2026-11-06。`accelerated_sphere_box_coverage::Input`全5項目と`Snapshot`全3項目を宣言順に取得する。合計78record型447項目＋別Input variant1型。coverage依存内は23record型101項目に対応し、残る6record型41項目を依存順に進める。Native・GNU・公開の受入はそれぞれ実記録で確認する。

| 型 | 保存する項目 |
| --- | --- |
| Input | first、second、first_position_error、second_position_error、contact_margin |
| Snapshot | input、horizon、settings |

二つの球はそれぞれ元の位置・速度・加速度・半径を保持する。各軸位置誤差B1とB2は呼出側の宣言した元のスカラーであり、別々に保存する。明示的なcontact_marginとも区別し、誤差の推定・合算・Vec3化や元半径への加算を行わない。Snapshotのhorizonは元の秒、settingsはsqrt_refinementsを含む全5項目である。

元入力の負零、subnormal、非有限、NaN payloadや不正値を修復しない。この保存試験は、実モデルが人工不整合入力を受理したことや、宣言誤差が実軌道を囲むことの認証ではない。getterは距離、区間、平方根、判定を再計算しない。

人工Input8件とSnapshot8件で、16種類のbinary64 bitを循環させる。各Inputは二つの球の20値と独立誤差2値・marginの計23F64を含む。全12,095byte、416typed leaf（F64 384／負零25、U64 16、U32 16）を独立仕様へ比較する。64bit計数には0、UINT64_MAX、2^53+1、2^63、depth／sqrt_refinementsには0、32、2^31、UINT32_MAXを含む。

全scalar／key byte6,304件（typed payload3,264byte）、root順序・個数3件、全field値交換744件、全objectのfield順序160件の計7,211変更を検査する。同じbyteとなる交換は0件。球同士の交換、B1／B2／margin、Snapshotのinput／horizon／settingsも全field対検査へ含む。

Writerと元データを生存・不変に保ち、Writerは排他的に使用する。返却値とWriter状態、finish、complete、transportの全成否を確認する。1,860callback境界すべての停止／例外3,720件は送信済みprefixを保持し、再入3,720件を拒否する。4丸めmodeで全byteが変わらないことも調べる。

製品は2data TU、新harnessは1TU。Interval構築TUや数値model libraryを新対象へ結合しない。旧回帰試験のInterval TUとは別の閉包として実compile／linkを監査する。GNUの通常・真Debug・新3TUすべてへのO1 ASan／UBSanはpush後の別受入である。

正式なNative記録は`reports/diagnostic-wire-coverage-sphere-source-snapshot-verification.json`。初回の単体成功を全回帰・GNU・公開成功へ読み替えない。最上位World Report、C API pump、今回取得のWASM／ゲーム接続は後続。[次はEvaluation全9項目](REPORT_COVERAGE_SPHERE_EVALUATION_WIRE_PLAN.md)。
