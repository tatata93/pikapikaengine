# 有限ray集合の幾何spot参照

`optical_spot::evaluate` は、各入力rayを同じ**指定面列・指定branch**へ通し、sensor
PlaneDiskへ幾何投影して、有限個の点の重み付き統計を返すread-only APIである。
レンズ形状に固定されず、空のroute、平板、曲面などに既存の
[optical_route](OPTICAL_ROUTE.md) / [optical_bounds](OPTICAL_BOUNDS.md) を再利用する。
sensorでは誘電体interfaceを作らない。反射/透過powerはrouteの診断であり、spotの重みへ混ぜない。

これは幾何spotであり、放射画像、校正された明るさ、回折PSF、連続pupil全体の積分誤差包含、
自動nearest-world光路、全ghost探索、連続最適焦点の保証ではない。任意桁数計算ではなく、
[INTERVAL.md](INTERVAL.md) のstrict binary64包含モデルを使用する。

## 入力とsource helper

`Input` はsamplesのspan、route stepsのspan、initial phase-index interval、1点のvacuum wavelength、
sensor PlaneDiskとその明示閉parameter domainである。`Sample` は全BoundedRayと正のweightを持つ。
位置/距離はm、mean squared radiusはm²、波長はm。directionは無次元で、unit化を要求しない。
ray parameter tはm単位でP(t)=O+tD、物理距離はt|D|である。

weightは呼出側が定義する幾何quadratureの測度で、有限binary64 `[1e-12,1e6]` に限る。
面積重みでも規格化した面積重みでもよく、一様なweight倍率はcentroid/varianceを変えない。
totalWeightをW単位の放射束と呼ばない。円盤を等半径で標本化して等票とすることは、一様面積
標本化を意味しない。pupil generator・面積測度・標本数収束の記録は呼出側の責務である。

`make_launch_ray(Source, launch_point, tMin, tMax)` は物点/平行beamの構成をC++側で行う。

- finite_point: origin=point(O)、direction=point(P)-point(O)をinterval subtractionで構成する。
- parallel_beam: origin=point(P)、direction=point(K)。Kをunit化せず全値を保持する。

例えばO.x=2^19、P.x=2^-40では、通常doubleの差がP成分を落としても、このhelperは真の
binary64入力同士の実数差を包含する。JSで差を丸めてからpoint intervalへ戻さない。
平行光は有限launch平面上の複数起点と共通方向で表し、巨大な有限物体距離で無限遠を代用しない。
source/launch点と生成rayのvector/domain限界を検査する。不正kindや範囲はthrow invalid_argument。
ゼロ方向は既存BoundedRay同様に表現できるが、その後のsensor/route hitをcertifyできず未確定になる。

## batchの保証と状態

設定、sensor、全stepの形状/index/branch/domain、全sampleのray/weightをevaluation前に検査する。
sample数/step数のquota超過は巨大な配列を走査せずbudgetで停止し、それ以外のpreflight不正は
invalid_input、evaluation=0、recordsなし。全sampleを受理した後はrecordsを入力順に全て確保し、
未実行のものもnot_examinedとして元weightとordinalを保持する。入力は変更しない。

1 sampleのevaluationはrouteを実行し、completed時だけcompletion rayをsensorへ幾何照会する。
sensorには明示domainを設定し、ray全箱を保持する。sensorのzero-distanceや開口端を隠さない。

| SampleStatus | 意味 |
|---|---|
| not_examined | sample評価予算などでまだ実行していない |
| accepted | 指定routeとsensorの全ray族hitが確定 |
| route_miss | 指定された面に全族員がmiss |
| branch_unavailable | TIR中の透過など、指定branchが存在しない |
| sensor_miss | 完了routeの全族員がsensor domain/apertureをmiss |
| route_unresolved / sensor_unresolved | 境界・向き・精度・箱の相関喪失等で不確定 |
| budget_exceeded | 必要なprimitive精錬または総処理数の予算不足 |
| invalid_input / numerical_failure | preflight後の下位routeの失敗または計算例外 |

route_miss / branch_unavailable / sensor_missは、この指定撮像経路の既知の欠落である。
未実装の筐体による吸収、scene内の全光路でpowerがゼロという意味ではない。
unresolved/budget/not_examinedをmissへ変換したり、黒やweight=0として消したりしない。
preflight済みの下位計算がinput/numerical failureを返した場合、batchはnumerical_failureとなる。
FP環境が未対応の場合もinvalid_inputと区別する。部分診断は残すがfinalStatsを設定しない。

Resultのstatus順はcompleted/unresolved/invalid_input/budget_exceeded/numerical_failure。
全sampleがacceptedまたは上記の既知欠落だけならcompletedでfinalStatsが存在する。
unknownが1つでもあればfinalStats全体がない。既知点を図示することは可能だが、
その部分集合の図を全体の統計や保証付きの画像として提示しない。
全missや空sample集合もcompletedになり、total/accepted weightは定義されるがmomentsは存在しない。
受理weightが0なのにcentroidを0と捏造したり、0で除算したりしない。

## 統計と包含

全既知のとき、total weightは入力全sampleの和、accepted weightはacceptedだけの和である。
正のweightを持つaccepted集合について

```text
W = sum wi
centroid = sum wi * Xi / W
mean_squared_radius = sum wi * |Xi-centroid|² / W
hull[k] = [min Xi[k].lower, max Xi[k].upper]
```

をC++ intervalで計算する。Xiはsensor hitの**全position箱**であり、中央値を使用しない。
同一平面上の真の点に対する3D距離なので、傾いたsensorでも座標系によらない面内距離である。
相関喪失でcentroidの箱が平面外へ広がることは保守的な誤差である。
varianceの下端は、数学的な非負性を使って0以上に制限する。sqrtを追加せずm²のまま出力する。
RMSの見積値を描画側で表示する場合、保証付きの平方根包含と区別する。

各ray/phase index箱への包含と、有限点集合の統計への包含を合成している。
異なるrayのindex相関や同一ray内の相関を失うことで広くなり得る。
これはpupilの未標本領域やquadrature誤差まで含むという意味ではない。
標本数を増やしたときの数値変化と、各有限集合のinterval幅は別の情報として記録する。

## 光量・媒質・self-rootの限界

現route throughputは任意偏光normal-power比の包絡である。その中央値を光量とせず、
各面で無偏光を作り直して平均Fresnelの積を取らない。radianceやsensor irradianceを得るには、
光源の放射量、面積/立体角の測度、方向cos、屈折のradiance変換、sensor応答などが別途必要である。
最初の本APIはこの物理量を合成しておらず、純粋に指定weightの幾何spotを返す。

routeは面と他側indexを明示指定する。保持中のindex intervalをそのまま次段へ渡し、
独立箱を中央値へ置き換えない。sensorは幾何だけなので架空の第三interfaceはない。
指定されていない面による遮蔽や媒質の空間的整合は証明しない。
[optical_selection](OPTICAL_SELECTION.md) をspawn後に自動接続すると、source面t=0や元面上の
相関喪失で止まり得る。このAPIでsource ID skipやepsilon offsetを追加して回避していない。

また、off-axis平行光をz一定のlaunch平面から出す場合、各始点は同位相面ではない。
routeのOPL差だけからwavefront aberrationや干渉PSFを作らない。
有限sensorによるcutや波長色分けも、物理的な露光・分光RGB・diffraction imageと混同しない。

## 予算

Settingsはrouteの既存設定とmax_samples/max_evaluations/総max_sqrt_refinementsを持つ。
既定は1024/1024/1000000、範囲は1..1024 / 1..1024 / 1..4000000。
1 evaluationは1sampleのroute+必要ならsensor。geometry/interfaceのglobal counterも返す。
route最大64stepのためgeometry照会は最大66560、interfaceは最大65536である。

sqrtは既存結果に報告された全counterを加え、sample終了後に総予算を監査する。
超過sampleはbudget_exceededとし、成功sensor診断があっても受理統計へcommitしない。
超過は1sampleの有限処理に限られる。最大設定で1sampleを263680 scalar refinement以内と
保守的に上界づけられる。厳密なinstruction中断型の総予算ではない。
既存primitive内で例外が起きるとその途中のWork counterは返らないため、数値失敗時に
真の全処理数が計測済みとは主張しない。この場合もstatusは失敗、finalStatsはない。
allocation failureは診断自体が確保できなければ外へ伝播し得る。

## 独立受入と再現

Native試験は通常の幾何・予算・失敗復帰に加え、rounding環境の拒否と復旧を確認する。
standalone実WASMは同じC++ソースをstrict flagsで実行する。

- 点(-1,0),(1,0),(0,-1),(0,1)、weight1,2,3,4ではcentroid=(1/10,1/10)、M²=49/50。
- 傾いたsensor normal=(3,0,4)ではcentroid.z=37/40、3D M²=1829/1600。
- 点光源O=(0,0,-1)からz=0の同じ4点を通りsensor z=1へ投影すると、M²=98/25。
- 平行平板、全miss、成功+miss、開口端unknown、TIR欠落、全quota、非unit方向を確認する。
- source差で消える2^-40の項をFractionで独立に照合する。

合成両凸profileはR1=.05、R2=-.05、厚さ=.005、開口=.015、n=3/2である。
reduced-angleの近軸行列から、EFL=3/59 m、back focal length=29/590 m、sensor絶対z=639/11800 m。
これらはdecimal値を厳密な分数とした場合の簡潔な近軸参照であり、全開口の共通焦点ではない。
実入力の.05/.005はexact binary64値なので、Python checkerではそのFractionから行列と焦点を
改めて導出し、小さな表現差も落とさない。開口内の表面非交差 a²<R*t−t²/4 も同じ入力で確認する。
半径h=.002/.001/.0005のray群が、この焦点へO(h²)で近づくことと、h=.014の周辺rayに
球面収差が残ることを検証する。spot API自体はこのレンズへ固定されていない。

`--fixtures` は25の完全入力・全record診断、2つのsource helper入力/出力、3段の近軸収束をJSON出力。
`--oracle` は128のdyadic点配置・正の整数weightによる既知のcentroid/variance/hullをhex出力する。
[verify-optical-spot.py](../scripts/verify-optical-spot.py) はschema/ケースidentity/有限値/分類/
原weight/全counter/unknown抑止を検査し、exact Fractionの解析値と照合する。
有限accepted箱のcentroidとhullの極値、および各座標のweighted varianceの最小/最大も独立に計算する。
凸二次式の最大値は箱頂点、最小値は共通cへclampした点のweighted-mean固定点を区間ごとに解いて求める。
これは少数標本boxへの統計集約の検査であり、未標本pupilを囲むものではない。
Python -Oは拒否し、任意の第二入力がある場合は独立検証後にbinary64 bit比較する。

最終standaloneではNative19群/実WASM18群が成功した。差の1群はNative専用のFP丸め環境
拒否・復旧試験である。25fixture/source helper2件/近軸3段の4767数値が全bit一致し、
166の有理数包含を通過した。128個の相異なるdyadic配置の1408包含も成功し、oracleの
全hex入力/出力が一致した。checkerは正常4通りと破損入力72通りを期待どおり処理した。
公開用rawは [Native fixtures](../reports/optical-spot-native-fixtures.json)、
[fixture comparison](../reports/optical-spot-fixture-comparison.json)、
[oracle](../reports/optical-spot-oracle.csv)、
[negative controls](../reports/optical-spot-negative-controls.json) に保存する。

```text
cmd /c build\optical-spot-proof\build.cmd
node build/optical-spot-proof/build-wasm.mjs
build\optical-spot-proof\spot-tests.exe --fixtures
build\optical-spot-proof\spot-tests.exe --oracle
node build/optical-spot-proof/run-wasm.mjs --fixtures
node build/optical-spot-proof/run-wasm.mjs --oracle
python scripts/verify-optical-spot.py native-fixtures.json [wasm-fixtures.json]
python scripts/verify-optical-spot.py native-oracle.csv [wasm-oracle.csv]
```

原本SHA、固定toolchain、strict flags、raw結果、負例、比較ログはignored
`build/optical-spot-proof/` に保存する。共有ABI/renderer/UIの統合証拠は親の節目で記録する。
新しい第三者コード、処方データ、solver依存は導入していない。

参考として閲覧した一次資料:
[PBRT Radiometry](https://pbr-book.org/4ed/Radiometry,_Spectra,_and_Color/Radiometry)、
[Working with Radiometric Integrals](https://pbr-book.org/4ed/Radiometry,_Spectra,_and_Color/Working_with_Radiometric_Integrals)、
[Realistic Cameras](https://pbr-book.org/3ed-2018/Camera_Models/Realistic_Cameras)、
[Dielectric BSDF](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF)。
それらの画像形成法を実装完了したという主張ではなく、幾何spotから放射画像への境界を整理する根拠である。
