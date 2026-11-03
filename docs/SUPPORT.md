# W2基盤: 法線支持反力のread-only照会

`support::solve(const dynamics::World&, Settings)` は、現在の球proxyと静的平面から、**時刻を進めずに**法線支持反力を求める自作の最初の核である。Worldの位置、姿勢、速度、角運動量、荷重、ID、storageを書き換えない。force/torqueを消費せず、衝撃impulseや投影も加えない。W1へ接続しておらず、支持を保った時間積分や摩擦支持の完成ではない。

```cpp
#include "pikapika/support.hpp"
const auto result = pikapika::support::solve(world);
if (!result.success) {
    // failure/message/pair IDs と残差を確認する。
    // 失敗した候補forceをWorldに適用しない。
}
```

単位はSI、右手系、+Y up。反力lambdaはN、gapはm、法線速度はm/s、法線加速度はm/s²。返すbody forceは法線反力だけで、重力や保持forceそのものを含まない。返すbody accelerationは重力・保持force・求めた法線反力を含む並進加速度。静的bodyの加速度は0だが、反作用forceは報告する。

## 支持と衝撃を混同しない入力契約

既存Worldのbody validationに加え、自由加速度成分は `1e12 m/s²` 以下。body IDsは挿入時の昇順・一意性を維持し、plane IDsとも重複しない。Worldの同時書込みは未対応。

幾何は明示的な**guarded-contactモデル**を使う。gapの外向き包含全体が `[-gap_tolerance,+gap_tolerance]` に入る候補を、今回の支持照会の境界として扱う。既定bandは `1e-8 m`、全半径の0.001倍以下でなければならない。

- gap下端がbandより大きければ分離したpairとして除外する。
- gap上端が負のbandより小さければ、深い貫通で失敗する。
- 包含がband境界を跨ぐ場合は、幾何判定不能で失敗する。
- band内の僅かな正gapや負gapも、**近似境界として選ばれ得る**。全constraintの `guarded_geometry=true`、gap両端、`maximum_geometry_offset` を必ず返す。位置は変更しない。

従って、正gapで力0という厳密な位置レベルの相補条件を証明する核ではない。例えば正gap `1e-9 m` の静止球も既定band内では10Nの反力を返し、その正gapをJSONで公開する。この近似を、実物の接触の存在証明や、今後のW1連結の受入へ読み替えてはいけない。

速度にはこのような「小さければ支持」のbandを使わない。法線速度の包含が厳密に負なら、`-1e-20 m/s` でも `impact_required` とする。厳密に正なら離反phaseとしてlambda=0とし、rest LCPへ入れない。厳密なzeroは、各座標の積が0になる構造から確認する。球対では各軸で中心座標が等しいか速度が等しいこと、平面では各軸で法線成分か速度成分が0であることを使う。

非自明な積の相殺でzeroになる接線速度を一般に厳密判定する機能はない。包含が0を跨ぎ、上の構造的zeroを確認できなければ `velocity_uncertain`。例えば `.6*.8 + .8*(-.6)` の厳密な相殺もこの版は保守的に拒否する。既定 `velocity_interval_tolerance=1e-9 m/s` は**包含の幅**の上限であり、小さい接近速度をzeroへ丸める閾値ではない。

離反phaseは、正の法線速度を持った瞬間のlambda0を返す。内向きの法線加速度と共存し得るため、離反phaseへ `a_n>=0` を要求しない。以後の再接触はこのread-only照会では解かない。`resting_constraints` と `separating_constraints` を分けて報告し、相補性残差はrest phaseだけに集計する。

## 球proxyの式と回転の扱い

平面法線の実数としての長さをL、向きをNとすると、

```
L = |n|, N = n/L
gap = (n·x - offset)/L - r
v_n = N·v
b_n = N·(gravity + heldForce/mass)
```

Worldのplane normalは概ね単位長だが、そのbinary64入力の実数ノルムを正確な1とは仮定しない。

球対は `dvec=xB-xA, d=|dvec|, N=dvec/d, u=vB-vA` とし、

```
gap = d - rA - rB
v_n = N·u
curvature = (|u|² - v_n²)/d = |u_tangent|²/d
b_n = N·(aB_free-aA_free) + curvature
```

を使う。静的bodyの自由加速度は0。動的2体で共通の重力は相対加速度から消える。曲率は中心間距離の二階微分から生じ、接線速度が大きければ支持反力を減らし、十分なら離脱を許す。

球の形状はorientationに依存せず、法線反力は中心線方向なので中心回りtorqueは0。法線constraintにangular inertiaや `r*omega²` を加えない。回転球のある特定の物質点の加速度と、球面の幾何gapの二階微分は別である。平面上を速度3m/s、半径0.5mで転がる球のomega=6rad/sに対しても、質量1kg・重力10m/s²なら支持は10Nであり、`mg-m*r*omega²=-8 N` ではない。保持torqueや異方慣性は入力検証されるが、このnormal-only方程式に回転の誤った向心項を作らない。

## 法線LCPとbounded解法

各rest constraintのJacobian行Jは、first bodyへ−N、second bodyへ+N。平面firstには動的自由度がない。Mは並進質量で、静的bodyの逆質量は0。

```
A = J M^-1 J^T
a_n = A lambda + b
lambda >= 0, a_n >= 0, lambda_i*a_ni = 0
```

Aはこの摩擦なし球proxyモデルのGram行列である。法線方向ごとに共有bodyの逆質量と符号付きdotを足す。静的同士の境界は反力が不定なので `static_constraint`。特異な重複contactや悪条件行列は、反復が見かけ上収束してもそのまま成功にしない。

各対角で規格化した行列へCholesky前検査を行い、scaled pivotが既定 `1e-10` 未満なら `ill_conditioned`。これはbinary64のconditioning gateであり、厳密な条件数や全interval行列のSPD証明ではない。重複constraintが物理的に矛盾するとは限らないが、反力が非一意なPSD系もこの版は保守的に拒否する。対角regularization、人工compliance、ばね、減衰を足して通す処理はない。

候補lambdaは自作のprojected Gauss-Seidelで更新する。

```
lambda_i <- max(0, lambda_i - (b_i + sum_j A_ij*lambda_j)/A_ii)
```

毎sweepの数値残差が要求値の1/8以下に入った後、下記のinterval監査を行う。規定回数を超えれば失敗。有限反復の終了だけで成功にはしない。失敗時も最終候補のlambdaと包含残差を診断に返すが、失敗候補を反力解として使わない。

## 丸めと残差の契約

`interval.hpp` と同じstrict binary64/round-to-nearest/gradual underflow/非fast-math契約を使う。新sourceは `/fp:strict` または `-fno-fast-math -ffp-contract=off`。入力binary64を実数と解釈し、中心差・速度差・F/m+g・norm・normal・曲率・行列を各演算から外向きに包含する。球対では絶対位置を別々に伝播せず、最初に入力差を取る。

normは `hypot` を初期推定にだけ使い、隣接候補のinterval二乗が元の平方和の上下を挟むことを確認する。256隣接値で確認できなければ失敗。曲率の非負性は幾何の恒等式から既知なので、包含の負側を0と交差させる。交差自体が存在しなければ数値失敗。代表値には `std::midpoint` を用い、subnormalの同一点包含を半分ずつ足して0へ消す実装にはしない。

数値行列で得た**表現済みlambda**を、元入力からのinterval行列と自由加速度へ戻し、実数の法線加速度を囲む。成功にはすべてのrest constraintで次が必要。

| 検査 | 既定上限 | 単位 |
|---|---:|---|
| 負のlambda | 0（投影で常に非負） | N |
| `max(0,-lower(a_n))` | `1e-8` | m/s² |
| `max(abs(bounds(lambda*a_n)))` | `1e-7` | N m/s² |
| 数値行列のprojected fixed-point残差 | `1e-8` | N |

最後のprojected residualは数値行列の補助検査であり、単独で厳密相補性を証明しない。最初の3条件をintervalで監査する。nominalに収束しても丸め包含が許容値を満たせなければ `numerical_uncertainty`。絶対単位の許容値なので、極端な質量・荷重では適切な要求値の選択が必要だが、APIが無断で緩めることはない。

`Constraint.acceleration_bounds` とbodyのreaction/acceleration上下界を返す。代表値のdoubleベクトルが、厳密な反力方向や厳密なa_n=0だとは主張しない。近接モデルのgeometry誤差と、入力幾何における反力方程式の丸め誤差を混同しない。

restの法線反力の瞬間仕事率は `lambda*v_n=0`（構造的zeroの範囲）。これは時間積分後のエネルギー保存を証明しない。`lambda*a_n` は相補性残差で、仕事率の単位ではない。重力や保持荷重・torqueの仕事、摩擦の散逸、姿勢積分誤差はこのread-only APIの外側で扱う。

## 予算とAPI制約

既定は128 contacts、100000 geometry pair queries、20000 sweeps。設定上限は256 contacts、1000000 pair queries、100000 sweeps、force `1e24 N`。各body-planeと球対を調べ、静的同士も近接すれば明示失敗。Broadphaseはまだない。行列はdense O(C²)、Cholesky前検査はO(C³)、各sweepはO(C²)。この最初の核にリアルタイム性能の保証はない。

APIは `success/failure/message`、問題pairのstable IDs、予算カウンタ、geometry/velocity幅、scaled pivot、残差、全constraint、body別反作用を返す。予算超過でcontactを落とさず、失敗後の同じWorldへ再照会できる。すべてのfailureで原Worldはread-onlyのまま。通常例外はResultへ捕捉するが、メモリ枯渇時の診断文字列確保まで保証するnoexcept APIではない。

## 独立核の初回検証・証拠

コード原点 `0c9d26fd6b17aef30e382abfbac474afa70d7df1`。新規4ファイルのみ。既存World/W1/C ABI/CMake/主WASM/assets/manifestを変更していない。

`tests/support_tests.cpp` は**Native21試験群、standalone実WASM21試験群**。支持mg、転がり/任意spin、荷重とmassの異なる3球stack、自由落下する接触2体、斜面、独立な2拘束wedge、上向き力による離脱、曲率による反力減少/離脱、動く異mass球対、離反phase、微小接近の衝撃拒否、速度相殺の未解決、明示band、静的/重複/悪条件/予算/厳しすぎる残差、平行移動/ID入替、失敗後再利用を解析値と照合する。質量 `1e-3..1e3 kg`、半径 `.005..5 m`、subnormalの代表値保持も別に検査する。

3球stackは質量1,2,3kg、gravityY=−10、保持forceY=5,−4,7N。下からの支持反力は独立な荷重和から52,47,23N。球対距離1m、静的相手、gravity10m/s²では、接線速度2m/sで曲率4m/s²・lambda6N、速度4m/sでは曲率16m/s²・lambda0・a_n=6m/s²となる。

最終stack実行は169 sweepsで、負の加速度上界 `2.167865886804066e-10 m/s²`、相補性上界 `1.1272902611029045e-8 N m/s²`。1 sweepへ制限した同一入力は、負の加速度上界約8m/s²、相補性約40N m/s²を残して失敗する。これは同じ入力に必要な残差検査を通さず、単に反復終了を成功にしないことの証拠である。

完全なbody/plane/重力/設定入力と全結果・残差・カウンタを `--fixtures` でJSON出力する。12fixture・1566数値のNative/standalone WASM比較を行う。分類/ID/カウンタは一致を要求し、数値比較の許容値は絶対1e-10+相対1e-12。現在の実測値は最大絶対差0でJSON値が完全一致した。将来のtoolchainや異なる有限反復順でもbit一致するという約束ではない。

証拠はignored `build/support-proof/` の `build.cmd`、`build-wasm.mjs`、`run-wasm.mjs`、`compare.mjs`、`native-tests.txt`、`wasm-tests.txt`、`native-fixtures.json`、`wasm-fixtures.json`、`parity.json`、`provenance.json`。MSVC19.51.36247 x64、C++20 `/O2 /MD /fp:strict` と、既存固定Emscripten6.0.13のstandalone出力を使う。主エンジンWASMへ公開した証拠やブラウザ支持実験とは別である。compiler生成ファイルのACLを直すための再作成はbyte一致で行い、物理コード/データの差替えではない。

## 調査した一次資料と後続

- [Baraff, SIGGRAPH 1997, Rigid Body Simulation II §6](https://www.cs.cmu.edu/~baraff/sigcourse/notesd2.pdf): 衝撃による速度不連続と、resting contactを保つ支持力の区別。
- [Baraff, 1994, Fast Contact Force Computation for Nonpenetrating Rigid Bodies §3](https://www.cs.cmu.edu/~baraff/papers/sig94.pdf): 法線加速度と反力の相補条件、質量/幾何からの線形関係。資料のDantzig実装やfriction algorithmを転載したものではなく、今回は自作bounded PGSと包含監査を使う。

資料を2026-11-03に実閲覧。新SDK/数値solver/外部physics libraryの追加なし。後続は、支持manifold/速度の一般判定、摩擦と接線constraint、状態を保つ積分、W1衝撃との整合、接触中の新規衝撃、長時間・刻み収束試験である。この核だけで初期支持、stackや転がりの時間発展が完成したとは扱わない。


## 共通APIと追加の独立解析例

現在は主C ABIの`pp_sim_world_support`と2つのrecord取得関数、JS Worldの`querySupport`へ統合した。
有効な照会の失敗候補もsnapshotへ更新するが、ABI入力数や整数域の不正は前record/出力を維持する。
Worldの物理状態・荷重・clockは変えず、reset/destroyでrecordを消す。

追加2群は非直交2面の正coupling（A12=.8、lambda=(2,10)）と一方の支持解除
（lambda=(0,4.4)、a=(-3.36,2.52)）、質量2/3kg・相対接線速度3m/s・保持荷重−54Nの
球対（曲率9m/s²、lambda10.8N）。全21群をNative/standalone実WASMで実行した。
主ABIは完全input12fixtureを再現し、公開した689数値と全物理状態の不変を比較する。
初回のignored provenanceは当時の原本を示し、統合後の最終hash/生証拠は
`reports/route-support-verification.json`へ保持する。

[支持ラボ](../tools/support-lab.html)は各設定で同じ原入力からread-only queryする。
図の反力は実C++の成功値だけを描き、候補の失敗やguarded positive gapを明示する。
この接続も、Worldの持続接触の時間発展を完了するものではない。
