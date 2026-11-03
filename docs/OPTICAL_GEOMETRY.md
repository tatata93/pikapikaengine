# レンズ面へ向けた光線交差の参照核

2026-11-03。独自C++の `optical_geometry.hpp/.cpp` と `optical_geometry_tests.cpp`。円形開口の平面、球全体、頂点を指定する球面キャップに対し、指定した光線parameter域で最初の有効交差を調べる。交点・parameter・実距離・法線の区間と、表示等に使うdouble近似を分ける。多面レンズの光路追跡、ゴースト、フレア、画像生成はこの核だけでは完成しない。

## 光線のparameterと単位

名前空間は `pikapika::optical_geometry`。

```cpp
Ray ray{{0,0,-6}, {0,0,2}, 0, 10};
PlaneDisk disk{{0,0,0}, {0,0,1}, 1};
auto result = intersect(ray, disk);
// tは約3、交点は(0,0,0)、原点からの実距離は約6m。
```

`P(t)=origin+t×direction`。origin・交点・形状寸法はm、directionは無次元、tもm単位だが **parameter** であり、実距離は `t×|direction|`。directionを単位化しなければtと実距離は一致しない。計算前にdirectionを通常doubleで単位化して別の光線へ変えてしまうことはしない。

`minimum_parameter` と `maximum_parameter` の閉区間だけを調べる。missは「この面の、このparameter域に有効交差がない」という意味で、域より手前の交差や別の物体まで否定しない。

## 3種類の面を区別する

| 型 | 数学的な面 |
|---|---|
| `PlaneDisk` | centerを通り、normalに垂直な平面のうち、centerからの距離がaperture_radius以下の円盤 |
| `FullSphere` | centerとradiusで指定する球面全体。レンズの一つの面とは区別する |
| `SphericalCap` | vertex、axis、符号付き曲率半径signed_radius、円形開口で指定する、頂点側の球面部分 |

capのaxisを実数で単位化したA、符号付き半径Rとすると、球中心は `C=vertex+R×A`、球半径は `|R|`。元のaxisからの長さの計算・正規化・中心構成を区間で囲む。通常doubleで丸めた中心を正確な原入力として扱うことはしない。

capでは、球面の点Pに加えて次の両方を要求する。

```text
(P−C)·(R A) <= 0                    頂点側の半球
|(P−vertex)×A|² <= aperture_radius²  軸に垂直な平面へ投影した円形開口
```

Rの符号は曲率中心が頂点からaxisのどちら側にあるかを示す。開口半径は `|R|` 以下。球の反対側までレンズ面として採用しない。開口の縁の壁・筒・レンズの体積・媒質判別はモデルに含まれない。

## 最初の有効根と、不確定の保持

`Result.status` は `hit / miss / unresolved`。`nearest` はhitの場合だけ存在する。球の真の2根は数学的に近い順であり、包含区間が重なっても根の順序自体と区間の大小比較を混同しない。

根ごとに、parameter域、cap半球、円形開口、要求精度、法線の向きを検査する。手前の根が開口外や反対半球と証明できれば、その次の根を調べる。手前の根が未解決なら、それを飛ばして後ろの根を「最初」として返さない。

`candidates` は最大2件の根区間。`root_count` は構成した根数、`considered_count` は実際にフィルタを調べた数。`CandidateState` はnot_examined、accepted、rejected_parameter、rejected_aperture、rejected_cap、unresolved。最初のacceptedで停止するため、それより後の根のフィルタ結果まで調べたAPIではない。

主な未解決理由:

- `parallel_or_coplanar`: 平面との内積が零付近。厳密に平行かつ非共面と証明できる場合だけparallelのmiss。
- `tangent_or_discriminant`: 球の判別式が0を含む。真の接線・近接した2根・無交差を推測で選ばない。
- `parameter_boundary`: 根区間が指定域の境界をまたぐ。
- `aperture_boundary / cap_boundary`: 開口端・半球境界の内外を証明できない。
- `orientation`: 交差した法線の表裏が確定しない。grazingの曖昧な向きを確定入力として光学界面へ渡さない。
- `precision_limit / refinement_budget`: 根の幅または平方根包含の予算で必要な判定を成立させられない。

開口と半球は数学的には境界を含むが、包含が境界の両側に広がるならunresolvedになる。missへ丸めることも、少し大きい開口として通すこともしない。

## 区間構成と平方根

入力doubleを厳密な二進有理数として解釈し、演算を最初から自作intervalで囲む。平面のtは

```text
t = (center−origin)·normal / (direction·normal)
```

球ではo=origin−C、d=directionとして `A t²+2H t+Cq=0`、`A=|d|², H=o·d, Cq=|o|²−r²`。判別式 `Δ=H²−A Cq` の上限が負なら無交差、下限が正なら2根を構成し、0を含むと未解決。Hの符号が確定する場合は打消しを減らすqの形で一方を求め、もう一方を `Cq/q` で囲む。Hが零付近の場合は±平方根の式を区間演算で使う。最終値だけを1ulp膨張する方式ではない。

証明用のsqrtはlibmの丸めを仮定しない。有限非負区間Xに対し、最初は `0 <= sqrt(X) <= max(1,X.upper)`。二分点mの二乗をintervalで囲み、Xとの厳密な大小で上下境界を狭める。重なるときは

```text
|sqrt(x)−m| = |x−m²| / (sqrt(x)+m)
sqrt(x)+m >= lo+m
```

から、すべてのxを囲む誤差半径をinterval除算で作る。正常な方向・axisの一軸だけが非零の場合は、その長さと単位軸を解析的に確定できる。通常doubleのhypot・正規化は最後の概算値にのみ使用する。

`Hit.position` は真の交点を含む3成分の直方体区間。`physical_distance` は真のt×|direction|を含む。区間内の任意の組合せが球面上にある、という意味ではない。`parameter_estimate` や `position_estimate`、`*_normal_estimate` は近似値で、証明用の区間に置き換えられない。

## 法線と後続の輸送

平面の幾何法線は入力normalの実数単位方向。球/capの幾何法線は球中心から外向き。`geometric_normal` は真の交点におけるこの単位法線の包含、`front_face` は `direction·geometric_normal<0` と証明された場合にtrue。back側の交差も許可する。

`incident_normal` はback側で反転して、入射媒質へ向けた法線を囲む。表裏の符号が確定しない場合はhitにしない。ただしgeometryは屈折率や媒質IDを割り当てない。どちらの媒質から来たかは後続の光路データが持つ必要がある。

現時点の単一界面 `optics::dielectric_interface` は点double入力を受ける。そのAPIへ概算の交点・法線だけを渡す場合は、ここで得た区間を保持した厳密な多面輸送の証明にはならない。後続光線には交点/方向の不確かさを引き継ぐ設計が別途必要。

## self-hitに隠れたepsilonを入れない

光線原点を勝手に動かさず、t=0付近を自動で捨てない。たとえば円盤中心を原点にして垂直に出る光線は、t=0のhitを保持できる。一方、球上の原点から出る根の区間が0をまたぐ場合は、unresolvedのまま保持する。

呼出側が正のtMinを明示すれば、その域より手前と証明できた根だけを除外できる。これはself-hitを自動で正しく識別する機能ではなく、実際の近接面や近い交差を指定域の外へ除外することもある。試験ではt=`2^−20`の実在する近根を既定域で拾い、明示cutoffの外へ置いた場合だけ次の根へ進むことを確認する。

計算交点からの安全な光線生成・境界の履歴による同じ面の再訪識別・光路の閉路や予算は未実装。PBRTの誤差境界に基づくorigin offset等は参照したが、固定epsilonで置換して完成扱いにはしない。

## 有効域・予算・FP契約

位置/中心/頂点の各成分は有限かつ絶対値1e6m以下。direction/axis/normalの絶対値最大成分は `[1e−6,1e6]`、半径と開口は `[1e−6,1e6]` m。capの符号付き半径は絶対値がこの域に入ること。`0<=tMin<=tMax<=1e9` parameter m、parameter_toleranceは有限で `(0,1e6]`。不正入力はinvalid_argumentで拒否する。

`parameter_tolerance` は受理する根区間幅の上限。物理距離の許容誤差と自動換算されない。方向が大きければ同じt幅でも位置区間は広がり得る。`max_sqrt_refinements` は各平方根の1..256回、既定128。`sqrt_refinements` は合計回数、`refinement_limited` は予算終了を示す。粗い境界でも交差/除外を証明できる場合は結果を返せるため、このflagとhit/missが共存し得る。区間幅やflagを捨てて一律の精度保証とはしない。

`docs/INTERVAL.md` のbinary64・nearest-even・gradual underflow・例外masked・有効CPU条件を継承。区間の比較中も有効環境を維持する。ビルドはMSVC `/fp:strict`、GCC/Clang Native `-fno-fast-math -ffp-contract=off -frounding-math`、WASM `-fno-fast-math -ffp-contract=off`。既知のfast-math/contract設定はcompile error。コンパイラの再結合、x87拡張中間精度、LTO、relaxed SIMDへ保証を広げない。

## 独立検証と成果物

Native MSVC19.51.36247.0 / Windows SDK10.0.26100 / Releaseと、既存公式Emscripten6.0.13 O2 / Node24.14.1での **standalone実WASM** は双方16群成功。

平面のtと実距離の差、表裏、平行/共面、原点・方向scale変更、3-4-5傾斜軸、円形開口境界、球の順序付き2根と内部退出、接線±近傍、cap反対半球、負曲率、self-hit、明示cutoff、精度/平方根予算、不正入力を試験した。

特にcap `vertex=(0,0,0), axis=(0,0,1), R=5, aperture=3` と `O=(−8,0,4), d=(4,0,−2)` では、球の根はt=1と2。最初の点(−4,0,2)は開口外、2番目の頂点(0,0,0)が最初の有効hit。球の最初の根だけで終了しないことを整数の既知解で確認した。

`--oracle` は入力bit・両根区間・候補状態・真の交点/距離の包含をCSVへ出す。ignoredの `build/optical-geometry-proof/verify-geometry.py` はPython標準Fractionで正確な有理数を復号する。平面の根は正確な有理式、球の根は二次式の符号と頂点との位置関係で検査するため、sqrtの通常double計算を参照解として使わない。capの3-4-5軸では数学的な単位軸も有理数で再構成する。開口・半球・表裏・近根の除外理由、交点区間・実距離区間も独立に照合する。

| 試験 | 最終結果 |
|---|---|
| Native / standalone WASM | 各16群成功 |
| Fraction oracle | 各200例、330根包含成功。hit197 / miss2 / unresolved1 |
| Native/WASM | 200行の分類・包含packet bit一致。概算法線等のbit一致は要求しない |
| standalone WASM | 194,614 bytes、SHA256 `766a12f21a15b5c0852da97492bd048ee39462eec1e2e98f92fe94836e5313f2` |
| CSV双方 | SHA256 `07f35ebfb8754d0e134265c97cb6e248baf12b60f2ddc39e7d43a27ca9bf8763`（PowerShell出力CRLF） |

有限個のoracleが全入力の証明になるとはしない。包含構成とFP契約を根拠とし、oracleはその実装・ビルドを独立に検査する。

```powershell
# 個別Native build: interval.cpp + optical_geometry.cpp + testの3ソース。
cmake -S build/optical-geometry-proof -B build/optical-geometry-proof/native
cmake --build build/optical-geometry-proof/native --config Release
build/optical-geometry-proof/native/Release/optical-geometry-tests.exe
build/optical-geometry-proof/native/Release/optical-geometry-tests.exe --oracle > build/optical-geometry-proof/native.csv

build/toolchains/emsdk/upstream/emscripten/em++.exe core/src/interval.cpp core/src/optical_geometry.cpp tests/optical_geometry_tests.cpp -Icore/include -std=c++20 -O2 -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -fwasm-exceptions -sENVIRONMENT=node -sWASM_ASYNC_COMPILATION=0 -o build/optical-geometry-proof/optical-geometry-tests.cjs
node build/optical-geometry-proof/optical-geometry-tests.cjs
node build/optical-geometry-proof/optical-geometry-tests.cjs --oracle > build/optical-geometry-proof/wasm.csv
python build/optical-geometry-proof/verify-geometry.py build/optical-geometry-proof/native.csv build/optical-geometry-proof/wasm.csv
```

ここに記録したのは個別核の証拠。担当作業では既存CMake、主ABI、主WASM、教材、配布manifestを編集していない。共有統合・公開版の証拠とは分ける。

## 一次資料と未対応

- [PBRT第4版 §6.2 Spheres](https://pbr-book.org/4ed/Shapes/Spheres) 本文を閲覧。球の二次式、近い根と遠い根、部分球のフィルタを確認。既成コードを移植せず、このAPIの明示parameter域とunresolved規約で独自実装。
- [PBRT第4版 §6.8 Managing Rounding Error](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error) 本文を閲覧。丸めによる誤交差と固定epsilonの見落とし、誤差境界を後続へ保つ必要性を確認。
- [PBRT第3版 §6.4 Realistic Cameras](https://pbr-book.org/3ed-2018/Camera_Models/Realistic_Cameras) 本文を閲覧。頂点からの曲率・開口を持つレンズ面と球全体の違いを確認。数表・レンズ処方・図・コードは取り込まない。

自作intervalと標準C++のみ。外部の幾何/レンズライブラリ・資産・材質表は追加していない。試験SDKの依存/配布条件は既存記録に従い、エンジンのライセンスは未選定のまま。

未対応: 非球面・自由曲面・楕円/非円形開口、面配置の加減算そのものに不確かさを持つ外部入力、動く形状、媒質/屈折率割当、多面屈折/反射枝、偏光と光路の統合、開口壁、ゴースト/フレア、回折、画像生成、一般のself-intersection回避。概算交点からの光路を無条件に厳密とする保証もない。

共有CMake/主WASMへ後続統合し、C ABI入力19/出力52とJS`queryOpticalSurface`を追加。
原本200例を主ABIへ通して分類/候補と2400区間端点bit一致を確認した。
公開checkerはscripts/verify-optical-geometry.py（型・件数の検査を統合時に追加）、
主ABIの比較はscripts/verify-optical-geometry-wasm.mjs。
[面交差ラボ](../tools/lens-surface-lab.html)は実WASMを使用し、9つの操作/照会試験が成功。
独立proofの原本hashと、後続で追記した本書のhashは区別する。
