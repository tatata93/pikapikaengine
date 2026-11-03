# 一定並進速度の接触時刻核

実装・Native確認: 2026-11-03 JST。追加依存なし。実装は
`core/include/pikapika/continuous.hpp` と `core/src/continuous.cpp`、試験は
`tests/continuous_tests.cpp`。公開 `fe3a9f3` の後続で、単体確認時のGit原点は
`e06cd50fa6a151af68e119ee1712cc9a73b25af9`、working treeに本変更と並行する統合作業がある。

二つの球、または球と平面が、**指定した一定の並進速度**で動く場合の最初の接触時刻を
3Dで求める。加速度、回転、接触応答、物体の状態更新は扱わない。重力や状態依存浮力を
持つ既存 `dynamics::World` の一般的な連続衝突検出を完成させたものではない。

## APIと規約

名前空間は `pikapika::continuous`。長さm、速度m/s、時刻s、右手系を使う。

| 入出力 | 規約 |
|---|---|
| `MovingSphere` | 初期中心 `center`、一定速度 `velocity`、正の半径 `radius` |
| `MovingPlane` | 初期の式 `normal·x=offset`、一定速度 `velocity`。回転しない |
| `sphere_sphere(a,b,horizon)` | 両球が動く。イベント法線は**Aの中心からBの中心へ** |
| `sphere_plane(sphere,plane,horizon)` | 平面の負側 `normal·(x-velocity*t)<=offset` を固体とする。法線は平面から球へ |
| `time` | `[0,horizon]` 内の秒。無接触は空。初期重複/接触は0。`uncertain`では診断用候補時刻 |
| `initial_gap` | 初期表面間隔m。負は重複。平面では符号付き中心距離−半径 |
| `initial_motion` | stationary / approaching / separating / tangential。相対速度で判定 |
| `initial_normal_speed` / `normal_speed` | 初期/イベント法線速度m/s。負は接近。無接触時は両方とも初期値 |
| `normal_valid` | 初期の球中心が一致すればfalse。法線を勝手な軸で代用しない |
| `at_horizon` | 返したdouble時刻が入力horizonと厳密に同値ならtrue |
| `roundoff_sensitive` | 後述する丸め境界の診断。誤差の厳密な上限証明ではない |

`ContactKind` は `none=0, initial_overlap=1, initial_touch=2, impact=3, grazing=4,
uncertain=5`。`Motion` は `stationary=0, approaching=1, separating=2, tangential=3`。
初期に重なっていれば離反中でも `initial_overlap` を返す。これは重複を解消する退出時刻
ではない。中心一致で相対速度が非零なら距離の右微分は正なので `separating` とし、
法線は無効、`initial_normal_speed` は相対速度の大きさとする。そのとき法線に対する速度を
定義できないため `normal_speed=0` とする。

無接触時の法線は初期法線。`uncertain` の法線も診断用で、確定接触として応答へ流さない。
半径0の点、負の半径、両側が固体となる薄板平面はこのAPIの対象外。

既存 `core.hpp::sweep_sphere(start,end,radius,Sphere)` は、静的な球に対する線分の
掃引と区間比率を返す。今回のAPIは二物体の速度、秒単位のhorizon、動く平面、
初期状態/接近・離反の分類、無効法線、丸め診断を明示する独立の照会である。
既存の掃引、剛体原本、simulation ABIをこの実装作業では変更していない。
ABI/WASMへの公開や表示は別の統合層である。

## 幾何と安定した根

球Aと球Bの相対位置を `r=B.center-A.center`、相対速度を `v=B.velocity-A.velocity`、
半径和を `R` とすると、接触条件は `|r+v*t|²=R²`。
光線と球の交差を二次式にする導出は [PBRT 4 §6.2](https://pbr-book.org/4ed/Shapes/Spheres)
で確認した。実装は本リポジトリで作成し、外部のコードやライブラリを転載していない。

相対速度の大きさを `speed`、単位方向を `u`、空間尺度を
`S=max(|r.x|,|r.y|,|r.z|,R)` として、`p=r/S, q=R/S, s=speed*t/S` を使う。
これにより式は `s²+2*b*s+c=0` となる。計算では

```
b = p·u
c = (initial_gap/S) * (|r|/S + q)
h = |p×u|
D = (q-h) * (q+h)
s_entry = c / (-b + sqrt(D))
```

を使う。`c` は二つの大きな二乗の差を避けた因数分解で、`D` は最近接距離から求め、
`b²-c` の大きな項同士の打消しを避ける。接近している分離球では `b<0,c>0` なので
分母は加算になる。小さい根を根の積から求める方法と、ほぼ重根の場合の不良条件は
[Kahanの一次資料 §1](https://people.eecs.berkeley.edu/~wkahan/Qdrtcs.pdf)で確認した。
近接した二根を浮動小数点で無条件に正確に区別できると仮定していない。

初期に分離し、相対法線速度が非負なら、一定速度下で距離の最小点は過去または現在なので
将来の侵入はない。静止時も二次式を割らない。`D=0` は計算上の接線 `grazing`。
正の根では、最近接点の垂線成分から `u*sqrt(D)` を引いて接触法線を得る。
別々に大きな世界座標を時刻tまで移動して、その差で法線を作らない。

平面は単位法線 `n` に対して `gap(t)=gap(0)+n·(v_sphere-v_plane)*t`。
分離し接近している場合だけ `gap/(-normal_speed)` を使う。先にhorizon内の移動距離と
比較するため、ほぼ零の速度を無条件に割って巨大な時刻を作らない。

## 数値境界と不確かな境界

入力はすべて有限とし、各座標・速度成分・半径・平面offsetの絶対値は `1e12` 以下、
半径は正、horizonは `[0,1e6]` 秒とする。平面法線の長さは1との差 `1e-12` 以内とし、
受理後は法線とoffsetを同じ長さで割って平面を保存する。違反は `invalid_argument`。
正規化した半径の二乗がunderflowする場合、分離係数が正に表現できない場合、入口距離や
正の接触時刻が正の有限値に表現できない場合は `domain_error`。成功時にNaN/Infを返す設計にはしない。

`hypot` と成分ごとの除算を使い、法線/速度方向は最大成分で一度尺度を合わせる。
`1/1e-320` の逆数overflowや、subnormal長さを直接割ることで非単位法線を作ることを避ける。
subnormalの距離・速度・半径を検出した照会は `roundoff_sensitive` にする。
ただしsubnormalでは物理量自体の相対表現誤差が大きい。すべての指数範囲で同じ精度を
保証しない。原点移動や単位系の適切な選択を行い、情報を失って丸めた座標を入力してから
精度が回復することを期待しない。

初期間隔が計算の丸め尺度に近い場合、判別式が零に近い場合、または根がhorizon端に
近い場合に診断フラグを立てる。判別式の負値が診断尺度内なら、最近接時刻を持つ
`uncertain` を返す。horizonよりわずかに外側の根も、診断尺度内なら端時刻を持つ
`uncertain` とする。明確な負の判別式や区間外の根は `none`。

判別式の診断尺度はdouble epsilonに基づく
`64ε(q²+h²+h|p|)+128ε²|p|²`、horizon比較は移動距離の大きさの `32ε`。
初期間隔には関連する長さの和の `16ε` を使う。固定のメートルepsilonで小物を消さない。
これらは外向き丸めを行う区間演算ではなく、全演算を覆う厳密な誤差証明でもない。
`grazing` は計算した判別式が零という分類で、数学的な厳密接線を認証したものではない。
`roundoff_sensitive=false` でも実数解に対する形式保証ではない。
[PBRT 4 §6.8](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error)の説明にあるとおり、
浮動小数点の交差判定は端点や接線で符号を誤り得る。厳密な保守CCDが必要な呼出し側には
区間算術や再評価方針が別途必要になる。

## Native検証

MSVC 19.51.36247 x64、C++20、`/W4 /fp:precise`、最適化指定なしで、
新しい2ソースだけを直接コンパイルし実行した。追加依存・既存物理の変更はない。
実コマンドは `build/native/continuous-proof/build.cmd`、生ログは同ディレクトリの
`test-output.txt`。親側のCMake/CTest統合は別途行う。

```
cl /nologo /std:c++20 /EHsc /W4 /fp:precise /Icore/include \
  core/src/continuous.cpp tests/continuous_tests.cpp \
  /Fe:build/native/continuous-proof/pikapika-continuous-tests.exe \
  /Fo:build/native/continuous-proof/ /link /INCREMENTAL:NO
```

17群、132個の解析解比較がPASS。最大時刻絶対誤差 `5.4569682106375694e-12 s`、
最大単位法線誤差 `1.5700924586837752e-16`、接触表面の最大相対残差
`3.219646771412954e-15`。時刻絶対誤差の集計には長い飛行時間のケースも含む。
これはこの試験集合の測定値であり、入力全域の誤差上限ではない。

試験には、動く平面、斜めの3D接触、始終点で分離した高速通過、接線と僅かな外れ、
初期重複/離反/中心一致、零・閉horizon、空間尺度 `1e-9..1e9`、速度/時間尺度、
Galilean変換・平行移動・球の入替対称性、小さい入口根、遠距離正面衝突を含む。
円の弦から独立に計算した108ケースでは入口の分枝と表面残差を確認する。
`1e-320` と最小subnormalの初期接触、相対速度の打消し、成功時の有限値/単位法線、
NaN/Inf/overflowを招く領域外入力、数値的に表現できない派生幾何の拒否も確認した。

今後Worldへ接続する場合、加速度下での有効区間・軌道近似誤差、複数接触の時刻順序、
衝突後の再照会、静止接触、反復回数と残り時間、形状の追加を別に設計・検証する。
球と平面の一定速度照会だけで自動車・航空機・鉄道・ロボットの接触全般が正しくなる
とは扱わない。

## 共通WASMと操作ラボへの統合

上記の核を既存共通ライブラリへ追加し、ReleaseのCTest5/5に統合した。C ABIには
2個のstateless照会を追加し、既存handleやWorld状態は変更しない。例外・不正countで
直前の出力を保ち、診断を返す。入力15値/出力13値の規約は[SIMULATION_ABI.md](SIMULATION_ABI.md)。

公式Emscripten6.0.13でWASM184090B/glue38078Bを実生成。Native/WASMの比較は既存の
剛体/静水圧軌跡とTOI12例、計30336値を対象にし、kind/flagsは完全一致を要求する。

後続の内部分離では同じABIのWASMを184044Bへ再生成した（glue38078B）。
最新のhash/原本依存は同名build.json、検証は
[区間演算・内部分離の記録](../reports/2026-11-03-interval-foundation.md)。
独立した区間演算を追加したが、この一定速度TOI核の診断を形式的な保守判定へ変更したものではない。
共通原本の処理系比較と、上記の独立解析例による検証を区別する。
[操作ラボ](../tools/contact-lab.html)は区間と終点の両方を実WASMへ再照会する。
XY断面の図示は指定した線形軌道で、衝突後の運動や時間積分ではない。
測定・実ブラウザの証拠は[今回の記録](../reports/2026-11-03-continuous.md)。
