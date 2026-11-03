# 一定加速度の球・平面の区間照会

2026-11-03 JST。`core/include/pikapika/accelerated.hpp` と `core/src/accelerated.cpp` の独自C++実装。
既存の [interval基盤](INTERVAL.md) を使い、入力doubleを厳密なbinary64の実数値として解釈する。
浮動小数点で作った係数を最後に膨らませる方法ではなく、相対量と係数の構成から包含する。
これは [World CCD計画](CONTINUOUS_WORLD_PLAN.md) の独立照会部分である。Worldの状態更新、
衝撃応答、持続接触、位置依存荷重、回転する形状、ゲームへの接続は行わない。

## APIと単位

名前空間は `pikapika::accelerated`。

| 型/API | 意味 |
|---|---|
| `Sphere` | 初期中心m、速度m/s、一定加速度m/s²、正の半径m |
| `StaticPlane` | 静的な式 `normal·x=offset`、負側を固体とする。任意の非零normal |
| `sphere_sphere(a,b,horizon,settings)` | 相対加速度を持つ二球の最初の入口を囲む照会 |
| `sphere_plane(sphere,plane,horizon,settings)` | 球と静的半空間の照会。加速する/回転する平面は対象外 |
| `sphere_sphere_value(a,b,time_interval)` | `|r+v*t+a*t²/2|²-(ra+rb)²` の区間包含、m² |
| `sphere_plane_value(s,plane,time_interval)` | `n·p(t)-d-radius*|n|` の区間包含、normal尺度を含むm |

normalを丸めた単位ベクトルへ置換しない。正の係数でnormalとoffsetを同時に拡大しても、
数学上の平面と半空間は同じになる。両方の符号を反転すると固体側が反転する。
球の加速度は呼出し側が与える。重力だけならg、held forceならg+F/mを用意するが、この照会は
forceやmassを受け取らず、Worldの荷重消費にも関与しない。

入力の各中心/速度/加速度/normal成分、半径、offsetの絶対値は有限で `1e12` 以下。
半径は正、normalは非零、horizonとvalue照会の時間区間は `[0,1e6]` 秒内。
この境界なら軌道や四次式の中間量はbinary64のoverflow域に達しない。位置の原点や半径に
対する一様な精度を保証する境界ではない。微小な量や悪条件では正直に未解決になる。
領域外入力/不正設定は `invalid_argument`、不正な浮動小数環境はinterval基盤の例外とする。

`Settings` は `time_tolerance in (0,1e6] s`、`max_evaluations=1..1,000,000`、
`max_frontier=1..65,536`、`max_depth=0..128`。既定値はそれぞれ `1e-8,32768,4096,64`。
evaluationは初期/時点/時間区間のvalue評価をすべて数える。係数構成とnormal長さの準備は
固定量で、normal内部の二分は最大64回。時間frontierは2本、記憶量は `O(max_frontier)`。
これは60fpsを測定した実時間設定ではない。

## 結果と証拠の境界

| `Kind` | 保証する範囲 |
|---|---|
| `none` | 初期が分離し、閉区間 `[0,horizon]` 全体で間隔式が厳密に正と包含で除外できた |
| `entry_bracket` | 正の連続safe prefixの端から、負と証明したwitnessまでが指定時間幅内。連続性により入口が存在し、最初の零と少なくとも一つの入口をbracketに含む |
| `unresolved` | 必要な存在/除外/幅の証拠が得られない。成功接触やnoneとして扱わない |

`initial_separation_proven=true` の場合、**閉じた連続prefix** `[0,safe_until]` が厳密に正。
`value_at_safe` はその端の実数値を含む正の区間である。時間区間の包含を端の証拠へ使う場合も
あるので、最狭の点評価とは限らない。falseなら `safe_until=0` を安全な初期状態と解釈しない。
`initial_value` は初期の評価区間を保持する。

`negative_witness` / `negative_value` は負の時点とその証拠を保持する。未解決でも見つかる
場合がある。**負のwitnessだけで、手前の未解決区間を飛ばして成功しない。** 成功時は
`bracket=[safe_until,negative_witness]`、左値は正、右値は負、差の区間上限がtime_tolerance以下。
丸めた通常doubleの差だけで幅を過小評価しない。

初期重複、初期の零/符号不確定はそれぞれ `initial_overlap` / `initial_boundary` を理由に
unresolvedとする。接線、偶数重根、horizon端だけの接触には区間内の負witnessがないため、
この実装は入口成功を捏造しない。根を含むだけの区間も同じである。予算/深さ/時間分解能/
数値判定の不足は別のreasonを返す。bracketは根の一意性や一つの衝撃法線を認証しない。
非常に近い複数の零やgrazingが同じ幅に入る場合もある。normalや反発impulseを返すAPIではない。

## 二次・四次式と包含の構成

球対の `r=pB-pA, v=vB-vA, a=aB-aA, R=ra+rb` をすべてpoint区間から演算し、
`h=a/2` とすると

```
F(t) = |r+v*t+h*t²|²-R²
     = (h·h)t⁴ + (2v·h)t³ + (v·v+2r·h)t² + (2r·v)t + (r·r-R²)
```

となる。球と平面では

```
phi(t) = (n·a/2)t² + (n·v)t + (n·p-d-radius*|n|)
```

を使う。点入力の差、半分、dot、半径和と平方、全係数の各演算を包含する。
幾何式の `t²` と各座標の二乗にはintervalの `square` を使い、係数/Horner評価とは独立に
もう一つの囲みを作る。両方が同じ実数式を含むので交差も包含になる。交差が空なら
実装/環境の不整合として例外にし、都合のよい片方を選ばない。

たとえば `r=(t-2)²-2, R=1` は4交差を持ち、始点・終点・中点のFはすべて正である。
端点の符号だけでは、途中の接触も偶数重根も除外できない。
[Wang et al. 2021 §5](https://cims.nyu.edu/gcl/papers/2021-CCD.pdf)で包含による除外と
root-findingの考え方を確認した。ただしその専用線形primitiveのpredicateや証明を今回の
加速球へ流用したとは称さず、この式から独自に実装した。論文コードは転載していない。

### normalの実数長さ

`max|n_i| <= |n| <= sum|n_i|` を初期boundsとし、二分の中点mの平方区間と
`N=n·n` の区間を比較して上下を証明する。`std::sqrt/hypot` の丸め精度を仮定しない。
normalの非零成分が一つなら長さはその絶対値そのものである。

平方の区間が重なった場合も、それだけでmを正解としない。真の長さxについて
`|x-m|=|N-m²|/(x+m)`、`x+m>=lo+m>0` を使い、差/分母/商から誤差半幅を包含する。
元のboundsと交差する。分母や極小量のため狭められなければ、証明済みの古いboundsを保持する。
二分停止や微小なn²のunderflowで長さが広くしか分からなければ、その不確かさを係数と最終結果へ
伝える。normalを通常doubleで正規化して、その後をexact unitとみなす経路はない。

## 時間順探索とsafe prefix

未除外区間のfrontierを時間順に保持し、各段階で左から走査する。正と証明した区間だけを
除去し、残りを左右へ二分して同じ順番で次段へ残す。手前で最初の未除外区間を見つけたら、
その後の除外をsafe_untilへ足さない。以前除外した隙間も正と証明済みなので、前側の区間が
新たに除外できたときだけ連続prefixを伸ばせる。

未除外区間の中点/右端や、全体が負と証明した区間の端をwitness候補にする。負の時刻が
見つかれば、それ以後は最初の零を探すために不要なので探索対象をその時刻までに絞る。
それより前の未解決区間は残す。最初の未除外区間の左端の正値も確認して、prefixと負witnessが
指定幅へ近づいた場合だけ成功する。

段階ごとの時間順frontierを使うのは、根がちょうど二分境界にある場合にも、手前の安全性を
保ったまま隣の区間から負witnessを得るためである。左の区間が零端点に近づくたびに、その中だけを
無限に掘る方法は採らない。一方、前側の接線/重根を飛ばして遠い後続衝突を採ることもしない。
予算内に決着しなければunresolvedとする。

初期の負/境界では探索を始めない。horizon=0でも正を証明できた点だけnoneとする。
`std::midpoint` が端点と同じになれば時間の表現分解能不足。評価回数/frontier/深さの上限も
判定結果に保持する。時間や区間を捨てたり、根のない側へepsilon移動して成功にはしない。

包含の前提は [INTERVAL.md](INTERVAL.md) のbinary64・nearest-even・gradual underflowとstrict flags。
Nativeは `/fp:strict`、GCC/Clangは `-fno-fast-math -ffp-contract=off` 等を維持する。
入力検査の前に環境を検査し、FTZ/DAZで極小入力が零に変わる環境を受理しない。
有限個の試験で全入力を証明したのではなく、連続時間の包含の根拠は各演算の構成に置く。

## Native試験と独立oracle

MSVC 19.51.36247 x64、C++20、Release相当 `/O2 /Ob2 /DNDEBUG /MD /W4 /permissive- /fp:strict`。
新しいaccelerated.cppと既存interval.cpp、accelerated_tests.cppだけを直接リンクした。
19群・22個の独立な解析入口比較がPASS。試験許容幅は1e-7秒、最大bracket幅は
`8.9406967163085938e-8 s`、入口比較の最大評価回数180回。精度は測定したこの集合の値で、
一様誤差保証やWorldの受入結果ではない。

重力落下、初期離反からの戻り、異なるa/静的球、既知時刻へ構成した3D接触、4crossing、
高速通過、二分境界、normal尺度 `1e-150..1e11` とhalfspace反転、無根、初期境界/重根、
近接miss、horizonだけの根、共通加速度/Galilean/入替/尺度、不足予算と微小数を確認した。
normal平方がunderflowする例は長さの広いboundsを保ち、未解決となることを試験した。
`r=2^39-2^-20, R=2^39` の初期式 `-2^20+2^-40` など、通常doubleで先に差を作ると消える
低位項の係数構成も検査する。

`--oracle` は入力/出力のIEEE754 bitsを485行のCSVへ出す。独立Pythonスクリプトはbitsを
整数と `Fraction` へ復号し、参照側のdouble演算やsqrtを使わず比較する。

| 検査 | 結果と適用範囲 |
|---|---|
| 点時刻240行 | 厳密な有理数の軌道値で包含を確認。一般normalの長さは平方不等式で比較 |
| 非零時間幅245行 | 各区間の9有理時刻を確認。点時刻を合わせ2,445時刻の包含PASS |
| 平面202区間の全範囲 | 二次式の端点と有理数の頂点で正確な極値を求め、sqrtを二乗不等式で比較して全体包含を独立確認 |
| 1軸球対2区間の全範囲 | 相対座標の二次式の極値と0の通過から距離二乗の正確な全範囲を導出して確認 |
| 一般3D球対41区間 | 有理時刻の有限サンプルの検査。四次式の連続全体の独立証明とはしない |

区間の値に0が入ることを根の存在と認める試験にはしていない。`phi=(t-1)²` の全範囲
`[0,1]`、4crossingのFの全範囲 `[-1,3]`（一部の極値時刻は無理数）も確認する。
CSVのSHA256は `e2e8757f6a73ade541b8f57a34dccbc38b4a056558cf237e64caeb2165d3ecda`。
oracleスクリプトと出力、source hash、実行設定はignored build内に保持する。

```powershell
cmd /d /c build\native\accelerated-proof\build.cmd
build/native/accelerated-proof/pikapika-accelerated-tests.exe
build/native/accelerated-proof/pikapika-accelerated-tests.exe --oracle > build/native/accelerated-proof/oracle.csv
python build/native/accelerated-proof/verify_oracle.py build/native/accelerated-proof/oracle.csv
```

証拠は `build/native/accelerated-proof/` の `test-output.txt`、`oracle.csv`、
`oracle-result.json`、`verify_oracle.py`、`verification.json`。
この担当作業では既存World/public API/C ABI/CMake/linear TOI/WASMを変更していない。
Native/WASMの共通化、ABI公開、表示、加速Worldへの接続は統合側/後続の受入である。
次段でWorldに使うには、時間幅を相対速度/加速度から空間誤差へ換算し、状態伝播・残時間・
同時接触・持続支持・原状保持と接続する必要がある。任意normalのvalueや球対m²の値を
そのまま共通のメートル誤差として使わない。

## 共通WASMへの統合

同じ原本を主simulation WASMに組み込み、C ABIの25値/19値入力・21値出力と
`queryAcceleratedSpheres` / `queryAcceleratedPlane` から呼べるようにした。
[パケットと予算](SIMULATION_ABI.md#constant-acceleration-enclosure-queries-additive-v1-exports)。
演算・照会のソースはNativeでstrict FP、WASMでfast-math/contractを禁じた別objectにする。
既存dynamics.cppのコンパイル方針は変更していない。
独立oracleは`scripts/verify-accelerated.py`へ収録し、統合Native試験の出力にも実行する。
加速軌道ラボでは実APIの証明prefix・bracket・未解決を可視化する。
上記の照会API自体はWorldを進めない。後続の[W1 World](CONTINUOUS_WORLD.md)はこの核と
実数荷重のwitness再検査・伝播丸めguardを組み合わせ、限定した衝撃応答と残時間へ接続する。
初期支持・接線・未確定は成功へ変換せず、一般の持続接触は別の受入である。
