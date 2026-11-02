# Native剛体と静水圧の結合参照

更新・実行確認: 2026-11-03 JST。実装は
`core/include/pikapika/hydrostatics.hpp` と `core/src/hydrostatics.cpp`、試験は
`tests/hydrostatics_tests.cpp`、CLIは `tools/buoyancy_bench.cpp`。
追加依存なし。既存の剛体積分器・WASM ABIは変更していない。

閉じた排水形状に作用する静水圧と、既存の6自由度剛体の運動を接続した。
最初の動的参照は**動的剛体1体・接触なし**に限定する。描画、実測水槽、CFD、
船舶・潜水艦・航空機の精密な実機応答、製品全体の60fpsを検証したものではない。

## 再利用するAPIと入力条件

名前空間は `pikapika::hydrostatics`。

| API | 役割 |
|---|---|
| `Hull(Mesh)` | 番号付き三角形原本を検査し、閉shell・原本体積・shell数を準備する。不変の原本を保持 |
| `Fluid` | 密度kg/m³、正の重力加速度の大きさm/s²、水平水面の世界Y座標m |
| `Pose` | 正のscale、位置、body→world単位quaternion、任意の世界CoM |
| `pressure(depth,fluid)` | ゲージ圧力Pa。水面以上で0、下でρg depth |
| `forces(hull,fluid,pose)` | 流体の合力N、指定CoM回りのトルクN m、濡れ面積、排水体積、浮心、全体積、shell数 |
| `apply_buoyancy(world,id,...)` | その時点の剛体姿勢で荷重を評価し、既存force/torqueへ加算。時間は進めない |
| `step_isolated_buoyant_body(world,id,hull,dt,...)` | 荷重を中点で再評価して無接触1体を進める結合参照 |

流体は一定密度・静止・非圧縮、外部水面は水平、重力は−Yとする。
各辺は逆向きの2面に接続し、各連結shellは正の符号付き体積を持つことを要求する。
開境界・向き不整合・非多様体辺・裏返ったshellは拒否する。別shellは互いに重ならない
閉じた物体を仮定する。自己交差、shellの重なり、入れ子の空洞を検出・Boolean統合する
機能はない。辺と体積の検査だけで任意の入力を物理的な固体と認定しない。

`Hull`は既存メッシュの頂点・面数、索引、退化面、Float32表現の検査も利用する。
変換後の頂点、水面、CoM、位置は有限な±1,000,000m内、scaleは正で各成分1,000,000以下、
quaternion長さの許容差は1e-10。これらは入力の数値境界であり、全域で精度を保証する
条件ではない。出力が非有限、排水体積が負、浮心積分が不良条件になったら失敗する。

圧力積分は[既存JSモデル](FLUID_MODELS.md)と同じ次数の式を使う。
三角形を水面で切り、線形圧力と二次モーメントを面積分する。和には補償加算を用い、
原本体積はshellごとの近い基準点から求める。人工的な水面の蓋はゲージ圧力0なので
力へ寄与しない。浮心は圧力トルクとは別の体積一次モーメントから求める。

## CoM・浮心・衝突形状を分ける

剛体の `position` は質量中心CoMである。`hull_origin_body` はCoMから排水メッシュ原点
への**body座標のメートル**オフセット。排水原点は
`body.position + R(body.orientation) * hull_origin_body` とする。
面積分は常に剛体CoM回りのトルクを返し、浮力だけをメッシュ原点へ置いて代用しない。
scaleは排水形状だけを変更する。質量・慣性・CoMの再計算や密度推定は呼出し側の責任である。

今回の動的参照は4×2×4mの箱を排水形状に使い、既存剛体には半径0.25mの球衝突proxyを
保持する。**箱の浮力形状と球の接触形状は一致しない**。球proxyで箱の接触が正しくなる
とは扱わない。参照は平面も他物体も置かず、全tickで接触数0を確認する。

## 状態依存荷重を中点で再評価する

`apply_buoyancy`の開始荷重だけを既存`World::step`へ渡す方法は、荷重をtick内で一定と
仮定する。浮力のような位置依存荷重では、単純にその方法を反復しても全体の二次精度は
得られず、調和的heaveで非物理的なエネルギー増加も起こり得る。
参照の `step_isolated_buoyant_body` は次を行う。

1. 元worldを複製し、開始姿勢での浮力・CoMトルクを加えて半tickを予測する。
2. 予測した姿勢とCoMで浮力・トルクを再評価する。
3. 元状態の別の複製へ、その中点荷重と元からのheld荷重を加え、全tick進める。
4. 成功した剛体状態だけを元worldへ戻す。失敗なら元状態と蓄積荷重を保持する。

中点で求めたトルクは、その時刻のCoM回りの一般化荷重として直接角運動量へ作用させる。
中点CoMから開始CoMへトルクを移し替えて、余分な `r × F` を加えることはしない。
元の剛体積分器は変更しない。結合APIは動的剛体1体、平面0枚、流体と一致する−Y重力を
要求し、他の接触を含むworldを拒否する。dtの範囲・回転増分制約は既存剛体と同じ。
抵抗・減衰・速度のclampを付けて誤差を隠していない。

## 独立した数値基準

釣合い・heave参照の箱は4×2×4m、ρ=1000kg/m³、g=10m/s²、水面Y=0、
質量16000kg、原点=CoM、慣性は一様な箱の主慣性
`[16000*20/12, 16000*32/12, 16000*20/12]` kg m²である。
半没体積16m³で自重と浮力が一致する。回転せず、常に部分没であるheaveなら、
水線面積16m²から独立に次を導ける。

```text
F_net,y = -160000 y [N]
y'' = -10 y
y(0)=0.1m, v(0)=0 → y(t)=0.1 cos(sqrt(10)t)
E_heave = K_body + (160000/2)y² [J], 初期値800J
```

復原参照は同じ排水箱を完全に沈め、CoMをY=−4m、排水原点をbodyの`[0,0.5,0]`m、
質量32000kg、主慣性`[24000,48000,40000]`kg m²とする。この慣性・CoMは与えた仮定値であり、
均一材質の箱のCoMを移動したと偽らない。中性浮力でCoMの並進は釣り合う。
純粋なZroll角θについて、浮心は `CoM + Rz(θ)[0,0.5,0]` なので、独立な基準は
`torque_z = -160000 sin(θ)` N m、`θ''=-4 sin(θ)` となる。
符号は傾きを戻す。比較用のscalar RK4はこの式だけを積分し、メッシュの切断・面積分や
既存Worldを呼び出さない。微小角近似だけを非線形の正解として使わない。

## 初回釣合い試験の失敗と安定性の区別

最初の4×2×2m・CoM中心・半没の箱は、Zrollの復原があっても狭い奥行方向のpitchは
不安定だった。半没断面の幾何ではその方向のGMは `2²/12 - 0.5 = -1/6`mとなり、
微小な丸めによる傾きが増幅し得る。10秒釣合い試験は状態誤差の許容値を超えた。
許容誤差を広げず、釣合い参照を両方向に復原する4×2×4mへ変更した。
元の箱の±0.01rad pitchに対して「トルクが傾きを増す」符号、新しい箱では「戻す」符号を
別の回帰試験に残した。安定な船体だけを選んで任意の形状の安定を主張しない。

## 実行結果と保存量・仕事の境界

Windows Release、MSVC 19.51.36247.0でCTest 3/3成功。新規Native静水圧・結合は20試験群。
圧力、乾燥/半没/全没箱、水面切断、移動/scale/任意回転、CoM偏心、斜面四面体、面の細分割、
複数shell、失敗入力、釣合い、安定/不安定符号、時間刻み収束、長時間誤差を確認した。

| 参照 | 実測値 |
|---|---|
| 10秒釣合い、120Hz | 最終Y誤差1.9534e−16m、最大並進速さ8.1802e−16m/s、接触0 |
| heave 2秒、dt=1/30,1/60,1/120 | 状態誤差1.44615e−4、3.59505e−5、8.97489e−6m相当。最初の比4.02261 |
| heave 100秒、120Hz | 最大相対機械エネルギー誤差3.59258e−4、最終−2.94761e−4 |
| heave 100秒、240Hz | 最大相対誤差4.49146e−5、最終−2.84941e−5 |
| 非線形復原roll 2秒、dt=1/30,1/60,1/120 | scalar RK4との状態誤差3.99715e−5、1.02310e−5、2.58899e−6rad相当 |
| 全没復原roll 10秒、120Hz | 最大相対機械エネルギー誤差3.42096e−5 |
| 離散仕事との残差 | heave約1e−11J以下、復原roll約5e−12J |

heave誤差は`hypot(y−y_exact, (v−v_exact)/sqrt(10))`、roll誤差は
`hypot(θ−θ_reference, (ω−ω_reference)/2)`で定義する。これらの試験範囲で二次収束に
整合する。エネルギー誤差は0ではなく、100秒の全履歴を保存している。抵抗は無効のまま。
この方法が厳密なエネルギー保存積分器、任意刻みや任意時間で安定、という結論ではない。
初期エネルギー0のequilibriumでは、JSONの`max_relative_energy_error`と
`final_relative_energy_error`は実装上1Jで正規化した欄であり、初期エネルギーに対する
真の相対比ではない。釣合いの評価には位置・速度と接触0を使う。
初期エネルギーが正のheave/rollでは、同欄はその初期値に対する相対誤差である。

仕事は中点荷重と前後速度の平均を用いて、
`(F_buoyancy + m gravity) dot v_average dt + torque dot omega_average dt` を累積する。
heaveの機械エネルギーは上の解析的な合成potential、全没純Zrollでは
`K_body + 160000(1−cosθ)` を使う。これらは指定した準静的外部場の基準である。
流体の反作用、運動エネルギー、水面の変形、付加質量を計算していないので、
**流体と剛体を合わせた全系の運動量・角運動量・エネルギー保存を実証したとはしない**。
外部場からトルクを受ける剛体の角運動量が単独で一定になるとも扱わない。
単一軸・指定potentialでの仕事一致を、任意の3D運動へ無条件に一般化しない。

## 起動・共通フィクスチャ・記録

```powershell
./scripts/build-native.ps1
New-Item -ItemType Directory -Force ./build/native/buoyancy-proof
./build/native/Release/pikapika_hydrostatics_tests.exe
./build/native/Release/pikapika-buoyancy.exe --csv ./build/native/buoyancy-proof/trajectory.csv
./build/native/Release/pikapika-buoyancy.exe --fixtures
node ./scripts/verify-buoyancy.mjs
```

`--fixtures`は`{fixtures:[{name,mesh,options,result},...]}`をJSONで出力する。
12ケースに箱/四面体/任意回転/変形/CoM偏心/平行移動/複数shellを含み、meshの全頂点・三角形と
`density,gravity,waterLevel,position,scale,orientation,centerOfMass`を明示する。
結果キーはJSと同じ`force,torque,wetArea,submergedVolume,centerOfBuoyancy,totalVolume,shells`。
JS/Native parityは実装のずれの検出用であり、別途の解析試験の代わりにはしない。
実際の比較は12ケース153数値で成功し、最大絶対差は5.820766091346741e−11だった。

raw記録は`build/native/buoyancy-proof/benchmark.json`、`trajectory.csv`、`fixtures.json`、
`test-output.txt`。CSVは38,400tickを除外せず保持する（釣合い1200、heave12000/24000、roll1200）。
各行に状態、荷重、体積、機械エネルギー、累積離散仕事、CPU時間を含む。
レポートはUTC `2026-11-02T23:46:13Z`（11月3日08:46:13 JST）、revision基点
`3d463d74cb8f68c50c2625c2287bb526b5505cb7`、dirty状態、Native実装/ヘッダー/CLI/剛体ソースの
SHA256を記録する。基点commitだけを未コミット差分込みの正確なソースだと扱わない。

公開証拠は[Native参照結果](../reports/buoyancy-native.json)、
[共通フィクスチャ](../reports/buoyancy-fixtures.json)、
[20試験群の出力](../reports/buoyancy-native-tests.txt)、
[全tickの圧縮CSV](../reports/buoyancy-trajectory.csv.gz)。圧縮CSVは元ファイルと解凍後の
バイト一致を検証して保存し、値の変更や不都合なtickの除去は行っていない。
元の非圧縮CSVはbuild内に残す。

この参照はCPUの数値計算だけであり、描画・GPU・音声・実提示を含まない。
初回記録の最大CPU結合stepはheave120Hzで5.1058ms、240Hzで4.8205msだった。
並行開発中の単一実行で、ここから全作品60fpsや厳密なtick締切の達成を宣言しない。
デバイスや非定常の外因まで分類した製品性能試験は別に必要である。

## 一次資料と未実装

既存[静水圧モデルの資料台帳](FLUID_MODELS.md#一次資料と確認範囲)の範囲を引き継ぎ、
2026-11-03にOpenStaxの[圧力・密度](https://openstax.org/books/university-physics-volume-1/pages/14-1-fluids-density-and-pressure)と
[アルキメデスの原理](https://openstax.org/books/university-physics-volume-1/pages/14-4-archimedes-principle-and-buoyancy)を
再閲覧した。深さによる圧力、表面法線方向の力、排水重量と浮力の関係を参照する。
図・本文・外部コードの転載なし。面積分、結合手順、復原/仕事の参照式・fixtureは自作である。

波、流体の速度場・反作用、空気の圧縮性、造波、付加質量、粘性、抗力、回転抗力、
推進、自由表面更新、浸水、船殻の応力/座屈/圧壊、自己交差の修復、箱と球の接触形状統一は
未実装。JSの係数抗力も今回のNative静水圧結合へ移植・追加したとは扱わない。
これは次の精密モデル・接触・流体相互作用の検証へ進むための小さな共通実行経路である。
