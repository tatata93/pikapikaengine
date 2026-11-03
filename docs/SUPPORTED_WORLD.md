# W2: 法線支持・離脱・衝撃を伴うWorld

`supported::step(World,dt,Settings)` と共通JS `World.stepSupported` は、球proxyと静的平面を
持つWorldを進める。法線が変わる球対、共有bodyの非直交接触、保持荷重、既存支持を含む
同時衝撃を扱う。全参加materialに `friction=0` を明示する初期profileであり、摩擦を
黙って省略しない。旧 `World::step` とW1の契約は変更しない。

## 一つのtickの流れ

1. 原Worldを候補へコピーする。SI単位・ID・状態・設定・profileを検査する。
2. 現候補の近接接触を集め、接近速度へのNewton反発則を法線impulseで連成solveする。
   既存rest行の反発目標は0。運動エネルギーの増加と閉じ速度残差を監査する。
3. 曲率を含む瞬間の片側支持LCPからactive集合を選ぶ。
   W2のprivate入口だけは、全vn区間が明示した±速度残差内ならrest候補とする。
   公開read-only `support::solve` の構造的zero/微小接近の厳密分類は維持する。
4. [RATTLE候補](CONSTRAINED.md)で位置と速度の拘束を連成solveする。
   負の段階乗数は一行ずつ外して区間開始から再計算し、必要なinactive行を再追加する。
   負だった全行を一度に永久削除する方法は採らない。集合の循環はboundedな再試行にする。
5. 一回の幅と二回の半幅を比較する。位置・速度・quaternion chordの差が設定以内なら、
   [定義した数値軌道の全区間](TRAJECTORY_GUARD.md)を、動的bodyに関わる**全pair**で監査する。
   接触数や分割数が予算を超えた場合に、pairを捨てて進めることはない。
6. 受理できなければ幅を半分にして同じ候補開始状態からやり直す。
   受理した区間だけ候補時刻を進め、tick末尾まで繰り返す。
7. tick全体が成功した場合だけ原bodyへcommitし、保持force/torqueを一度消費する。
   失敗では全body、元bodyのアドレス、荷重、gravityを保持する。ABIのclock/tickも保持する。

static collider同士の重なりは運動対象外として明示的に除外する。
動的bodyとstatic colliderの組合せは全て監査する。
tick末尾の近接衝撃もcommit前に解き、反発後の速度を返す右連続のsnapshotとする。
衝撃を次tickの冒頭まで延期しない。

## 数値モデルと保証の境界

これは有限幅の接触モデルであり、連続の剛体接触解を囲むinterval integratorではない。
RATTLEの端点残差、全区間の数値軌道の幾何、粗細幅差の三つを区別する。
半幅差の小ささだけから、連続解の厳密な誤差上限や衝撃時刻の包含を宣言しない。

採用した区間のdense pathは、入力doubleを実数として

```text
q(s) = q0 + h*v0*s + (q1-q0-h*v0)*s²,  0 <= s <= 1
```

と定義する。guardが証明するのはこの曲線全体が `gap >= -spatial_tolerance` を満たすこと。
実際の拘束軌道との違いは刻み収束で別に評価する。描画の直線補間をこの証明へ置き換えない。
端点が離れていても途中で通過する球対を、端点だけで合格にしない。

既定の空間許容値は1e−7m、近接帯は5e−8m、速度残差は1e−9m/s。
各半径の0.001以下でなければ入力を拒否する。近接帯内で反発を扱うので、
ごく小さい正gapで早期応答したり、小さい負gapを許容する場合がある。
これを正確な衝撃時刻・完全な幾何接触と呼ばない。
W1のentry bracketの意味をW2イベント時刻へ流用しない。
近接帯への採用はgap区間のlower endpointで判定し、その区間全体が空間許容帯内かも確認する。
近接帯の端を跨ぐ区間も採用され得る。

Cold inputの負速度へは小ささだけで反発係数を0にしない。
全ての許容速度guard内の小さい接近処理は `velocity_repair` イベントに分け、
Cold inputならNewton反発則を維持、同tick内の伝播後なら反発0とする。
このタグは小さい速度の処理を表し、丸め起因を証明する名前ではない。これはW2の有限残差契約であり、
read-only支持の厳密zero policyを緩めたという意味ではない。
小さい物理的な新接触と丸め起因を証明で分離したものではなく、その両方を含み得る
有限速度guardモデルである。`velocity_repair` という名前だけから丸め誤差と断定しない。

`support_impulse_sum` は二段の法線係数の和（Ns）で、反力Nやベクトル合力ではない。
`held_force_work` は保持並進力の `ΣF·(q1-q0)`。トルクの仕事推定を含まない。
mechanical energyは並進/回転kineticと `-m gravity·position` の和であり、
トルク・反発・数値散逸のあるケースで一定を要求するものではない。

## 予算とdiagnostics

最大substep、最小substep、粗細差の許容値、Newton/LU/line search、contact、
全pair/区間評価、attempt/segment/eventを明示的に制限する。
候補の進行時間やイベントは失敗時にも診断として残るが、`advanced_dt` は必ず0。
最後のconstraint/trajectory failureも残す。全tickのcommitと診断prefixを混同しない。
共通ABIは一度に1tickで、戻ったsnapshotは次の照会や編集で書き換えない。

## 解析受入と研究

Native試験は、床上の水平等加速度とtorque、質量1/2/3のstack、非直交2面、
片方の面からの離脱、同tick内の再接触、支持中の弾性衝突、高速通過、曲面離脱、
全tick rollbackと同じWorldでの復帰を比較する。新しい反例は
`A=[[1,-.8],[-.8,1]], b=(-7,9.2)`。全拘束のbilateral係数は(-1,-10)でも、
片側接触の正しい解は(7,0)であり、必要な支持を落として偽の衝撃を発生させてはならない。

球面上の質量1、初速1、重力4、中心距離1では、
`u²=1+8(1-cosθ)`、`λ=12cosθ−9` より離脱は `cosθ=3/4`。
この独立式と刻み半減で、法線が変わる運動とエネルギーを検査する。
最終実行数と生証拠は公開マイルストーンのreportsへ記録する。

- [McLachlanほか, Geometric Generalisations of SHAKE and RATTLE §4・§5.1.3](https://arxiv.org/pdf/1207.3367): 位置/速度拘束と滑らかな正則系の収束を確認。片側衝撃・離脱driver全体の二次精度や保存性の証明へ拡張しない。
- [Stewart–Trinkle, An Implicit Time-Stepping Scheme for Rigid Body Dynamics with Coulomb Friction §3](https://www.cse.lehigh.edu/~trink/Papers/STicra00.pdf): 位置・速度・impulseの整合と曲面幾何更新の必要性を比較。本実装はこの論文の完成solverやfriction法の移植ではない。

本文・図・コードの転載、追加solver、校正済み材質データの導入はない。
一般mesh/box contact、摩擦支持、関節、動く平面、流体連成、弾塑性破壊は後続とする。
