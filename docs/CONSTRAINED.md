# 法線のみのRATTLE候補区間

`pikapika::constrained::advance` は、明示されたactive球–平面/球–球接触を
連成して解く、read-onlyの数値RATTLE区間である。固定法線だけに制限せず、
球の中心線が動く場合も位置段・速度段で別々の法線を評価する。

**World CCDや片側接触driverの完成ではない。** inactive pairの衝突、区間途中の
安全性、離脱の時刻決定、再接触、衝撃、残時間、tickのcommitは呼出側の責務である。
この関数は離脱が必要な候補を返せるが、active行を自動削除して成功させない。
連続解の包含や、Newton解の大域的一意性を証明するAPIでもない。

## APIと状態の所有

`core/include/pikapika/constrained.hpp`:

```cpp
constrained::Pair active[] = {{100,1}}; // plane ID -> sphere ID
auto r = constrained::advance(world.bodies(), world.planes(), world.gravity,
                              0.01, active, settings);
if (r.success) {
    // r.candidate_bodies is a candidate only; the surrounding driver audits
    // inactive geometry and the segment before committing a complete tick.
}
```

Worldを受け取る薄いoverloadも同じ純粋入口へ渡す。球対はlower ID→higher ID、
平面はplane ID→body ID。重複、逆順球対、不明ID、static-staticのactive行を拒否する。
body/plane配列はWorldと同じID昇順・一意性を要求する。

原body、plane、gravity、storage、force/torqueを変更しない。成功時だけ
`candidate_bodies`を設定する。成功候補も元のforce/torqueを保持し、消費しない。
失敗時は候補配列が空で、stage impulseや残差・release IDsなどの診断だけが
残ることがある。途中まで計算した状態を公開Worldへ適用してはならない。
通常の検査/数値例外はResultにするが、診断文字列の確保自体が失敗するメモリ枯渇まで
noexceptを保証するものではない。

摩擦・反発はこの候補区間で適用しない。Material metadataは保持されるが、この関数の
モデルはnormal-onlyと明示する。Coulomb支持やimpactの代替として黙って使わない。
法線支持は球中心線方向なのでspin torqueは0。候補の姿勢/世界Lは既存
`detail::propagate_free`の保持torque・中点姿勢式を呼び、自由q/vだけをRATTLEの
q/vへ置き換える。gyro挙動を消すためにomegaを一定化しない。

## 方程式とimpulseの単位

位置q [m]、速度v [m/s]、mass M [kg]、保持外力と重力をまとめた自由加速度a
[m/s²]を用いる。平面gapは

```
g = (rawNormal·q-offset)/|rawNormal| - radius
```

球対gapは `|qB-qA|-rA-rB`。Jはその位置微分で、球対行はAに−n、Bに+n。
staticの逆質量は0。active全行の共有body応答を連成する。

```
vHalf = v0 + h/2*a + M^-1 * J0^T * P0
q1    = q0 + h*vHalf
gActive(q1) = 0

vStar = vHalf + h/2*a
v1    = vStar + M^-1 * J1^T * P1
J1*v1 = 0
```

`P0=impulse_position`、`P1=impulse_velocity`は各段の**符号付きimpulse係数 [N s]**。
force [N]ではない。一定平面の真の支持力がλなら、整合した初期状態では各段が
およそ `h λ/2`。球法線が動く場合は `J0 != J1` であり、総body impulseは
`J0^T P0+J1^T P1`。各係数を同じ法線方向のscalarとして単純加算してはいけない。

位置段はP0のNewton反復で解く。微分は

```
d g(q1) / d P0 = h * J1 * M^-1 * J0^T
```

なので、実装は `C*deltaP0=-g/h` を解く。Cは一般に**非対称**であり、
Choleskyや対称行列への置換を使わない。初期Gram対角の平方根による行/列平衡化後、
partial-pivot LUで符号付き解を得る。速度段は `J1 M^-1 J1^T` の符号付きsolve。
後者も同じLUを使い、非負clampや対角regularisationを加えない。

Newtonは全q/half-vを元snapshotと現在のP0から再構築し、監査した最大gapを減らす
bounded backtrackingを行う。位置段は少なくとも1回factorisationし、初期残差0でも
特異な重複行を見逃さない。試行の法線回転/domain違反は保守的に失敗し、driverが
刻みを縮めて最初から再試行できる。任意のNewton経路で成功する保証はない。

## 初期誤差・離脱・残差

初期active gapとnormal velocityの外向き包含全体が、各初期tolerance内にあることを
監査する。既定は各 `1e-8 m`、`1e-8 m/s`。これは**明示された有限誤差初期モデル**で、
`support::solve`の構造的zero/微小接近拒否規約を変更しない。

初期gapやvnが非零なら、RATTLE段がそれを拘束へ戻す操作も含む。これは厳密な
無誤差初期条件からの物理運動と同じではなく、位置/速度の補修に仕事・エネルギー変化が
あり得る。初期gap/vnの包含と最大値を必ず返す。これらを0に隠して保存則を合格にしない。

最終P0/P1のどちらかが負なら、そのpairを`release_pairs`へ加え、
`release_required`として**候補を成功扱いしない**。微小な負値も0へclampしない。
この符号は数値的なstage解の符号であり、連続反力の厳密な符号包含や離脱時刻の
証明ではない。driverはactive setを変えた場合、元区間開始状態から再計算する必要がある。
正のstage impulseだけでもinactive geometryや途中の接触安全性を保証しない。

位置/速度だけでなく、元の二つの離散式も監査する。

```
positionEquation = max | q1 - (q0+h*(v0+h/2*a+M^-1 J0^T P0)) |
velocityEquation = max | v1 - (v0+h*a+M^-1*(J0^T P0+J1^T P1)) |
```

この監査は既存interval核を使い、入力の真の実数 `F/m+gravity` と幾何法線の
包含を構成する。sqrt/hypotの値を証明として信頼せず、隣接値の二乗でnormの
上下を検査する（各norm最大256回）。成功時は最終gap、最終vn、上記の式の残差が
設定内であり、stage係数が非負である。Newton flagだけでは成功しない。

この包含は**出力endpointの離散残差**に関するもの。連続解との位置誤差、
Newtonの真の解の存在・一意性、全時間の軌道包含や無侵入を導くものではない。
特に球面上の二端点を結ぶ直線chordは、途中で球の内部を通る。
候補の自由放物線やchordを、実際の拘束軌道と称してCCDに使わない。
step-doublingによる差も、それ単独では誤差包含の証明にならない。

`minimum_scaled_pivot`は平衡化LUで観測した最小pivotと1の小さい方。
これはcondition numberの証明ではない。`maximum_normal_rotation`もnominal法線の
endpoint/trial角度の制限で、区間途中の総回転を囲む値ではない。

## 有限範囲・失敗

- `dt`は `[1e-12,0.1] s`、1024 bodies、64 planes、既定128/上限256 active contacts。
- 原RigidBodyの状態領域・ID・慣性・姿勢・Materialの検査を使う。planeもID、unit-normal
  近似規約、offset、Materialを検査する。自由加速度は各成分 `1e12 m/s²` 以下。
- 初期gap bandは全body radiusの0.001倍以下。各初期/最終/式残差toleranceは
  正有限かつ上限 `1e-3`、各単位はヘッダーに明記。
- 既定Newton32回（上限64）、LU64回（上限256）、line search16回（上限32）。
  Contact超過は`contact_budget`、反復/solve超過も対応するfailureを返し、行を落とさない。
- 既定pivot下限 `1e-10`（許可下限 `1e-14`）、法線回転0.5rad（上限1rad）、
  絶対stage impulse上限 `1e24 N s`。特異・悪条件をregularisationで隠さない。
- 残差、回転、Newton、line-search、数値領域に問題があれば全候補を拒否する。
  失敗後、同じ原snapshotへ別刻み/予算で再試行できる。

行列はdenseで、1 solveがO(C³)、記憶O(C²)。全ての上限は有限処理のためで、
大規模リアルタイム性能の保証ではない。各counterをResultへ返す。
intervalの[環境契約](INTERVAL.md)とstrict FP/no contractionでコンパイルする。
既存dynamics/coreのコンパイル挙動はこの追加によって変更しない。

## 独立受入と実測

`tests/constrained_tests.cpp`はNative・standalone実WASMとも17群PASS。
主要な独立参照は次の通り。

- 床：質量1、gravityY−10、forceX2、torqueZ2、h=.05。
  最終x=.0025、vx=.1、支持P0=P1=.25Ns、Lz=.1。
  一様球のI=.1から姿勢角.025rad。保持荷重を残し原Worldを変更しない。
- 3球stack：質量1,2,3、鉛直保持力5,−4,7N、gravityY−10。
  独立な荷重和52,47,23Nから、各段impulseはh/2倍。
  全bodyへ共通水平加速度も加え、共有body連成を検査する。
- 非直交2面：法線(0,1,0),(.6,.8,0)、force(−6,0,0)、gravityY−10。
  反力2,10Nを比較。一方を引離す変更では負のstage解と正しいrelease IDを返す。
- 曲面：静的球との中心距離1、動的質量1、q0=(0,1,0)、v0=(1,0,0)、gravityY−4。
  一区間は `x1=h`, `y1=sqrt(1-h²)` と
  `P0=h*(2-1/(1+y1))`, `P1=h*(4*y1-1)-y1*P0` の独立幾何解を比較する。
- 異質量の両動球：mass1,2、中心距離1、相対接線速度1、等大反対向きの保持力と
  重力を与え、COMの解析放物線と全momentumを比較する。
- 別々に法線が変わる2球接触を共有bodyへ接続し、実際に非対称なcross-endpoint
  Jacobianとなる例で、両gap/速度/元式を監査する。

さらにsingular/near-parallel、各予算、過大回転、strict残差、初期誤差、
無効入力、negative multiplier、失敗後再利用、empty active、static荷重保持を検査する。

曲面をT=.4まで進め、独立な縮約ODE `theta''=4 sin(theta)` のRK4参照（40000刻み）と
比較した。これは独立の数値参照であり、連続解の厳密包含ではない。

| h [s] | 位置誤差 [m] | 速度誤差 [m/s] | 最大エネルギー誤差 [J] |
|---:|---:|---:|---:|
| .04 | 3.26825664e-4 | 4.57208336e-4 | 3.74858792e-4 |
| .02 | 8.17069119e-5 | 1.14321070e-4 | 9.36878588e-5 |
| .01 | 2.04267340e-5 | 2.85814172e-5 | 2.34202155e-5 |

観測した半刻み比は約4。エネルギーは `v²/2+4y`（初期4.5J）で測り、係数抵抗や
結果に合わせた減衰を加えていない。normal workが連続系で0でも離散エネルギー誤差は
非零であり、表にそのまま残す。

球中心回りの離散軌道角運動量は、各kick位置の外力torqueの台形和
`h/2*(q0×F+q1×F)` と比較し、最大残差3.9e−16 kg m²/s以下だった。
これは当該離散式の監査で、真の連続torque積分と同じだという主張ではない。
最終gap/vnと丸めを含む式残差は別に記録する。

`--fixtures`は14例の全body/plane/force/torque/Material、active IDs、gravity、dt、
全Settings、候補状態、signed impulses、残差、失敗理由、counter、収束値をJSON出力する。
`--curve-trace`は40区間の軌跡/仕事診断をCSV出力する。
Native/WASMで1744数値を比較し、最大絶対差4.45e−15、ID/enum/counter145値は一致。
1694値はbinary64 bitも一致。残りは浮動小数点/数学関数差を含み、全bit一致とは呼ばない。
独立の有限参照39チェックもPASS。standalone WASMは273311 bytes。

証拠とコマンドはignored `build/constrained-proof/`。
`native-tests.txt`, `wasm-tests.txt`, `native-fixtures.json`, `wasm-fixtures.json`,
`native-curve.csv`, `wasm-curve.csv`, `comparison.json`, `compare.py`, `provenance.json`
へ原データを保存する。NativeはMSVC19.51.36247 x64、固定Emscripten6.0.13を使い、
新しいconstrained/interval/testソースだけstrict FPとし、既存core/dynamicsは元の条件を保つ。
Nativeの基底libraryはproof内へbyteコピーして固定し、SHA-256を記録する。
共通CMake/ABI/配布へ接続済みだという証拠とは別である。

## 原典と実装範囲

- [Cotter/Reich, Time Stepping Algorithms for Classical Molecular Dynamics §2.2](https://www.ma.ic.ac.uk/~sreich/03_6.pdf)：位置段・速度段を分けるRATTLEとNewton構成を参照。ここでは外向きnormalとNs単位の二つの係数で独自実装した。
- [Console/Hairer/Lubich, Symmetric multistep methods for constrained Hamiltonian systems §1](https://www.unige.ch/~hairer/preprints/sym-constr.pdf)：位置/速度整合条件と拘束系の背景。有限toleranceやunilateral driverの正当性をこの文献の保存性から自動的に結論しない。
- [Baraff, Rigid Body Simulation II](https://www.cs.cmu.edu/~baraff/sigcourse/notesd2.pdf)：支持力と衝撃の分離。

ライブラリsolverや文献コードは導入・転載していない。固定Jacobian例だけをW2の代用とせず、
実際の曲率・動く法線を扱う候補区間まで検証した。次の課題はdriverのactive切替、
非活動CCD/軌道誤差監査、残時間、接触island衝撃、全tick rollbackの結合である。
