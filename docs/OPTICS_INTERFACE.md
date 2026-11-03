# 単一の平面界面を通る光の参照核

2026-11-03。`core/include/pikapika/optics.hpp` / `core/src/optics.cpp` の独自C++実装。任意選択の精密光学へ向けた最初の参照計算で、与えられた入射方向から反射・屈折方向とFresnelのs/pパワー比を求める。レンズ処方の追跡や画面効果への接続はまだ行っていない。

## 物理モデルと入力

単一の滑らかで無限に広い平面、線形・等方・非吸収、正の実屈折率、両側の磁気透磁率が等しい媒質を仮定する。一般に屈折率だけでは異なる磁性媒質のインピーダンスまで決まらないため、等透磁率の仮定を明示する。幾何光学の光線方向と、平面波の境界条件から得られるFresnelパワー配分を使う。面の位置・光線の交点は入力に含まず、「この境界へ入射した」光線の方向と配分を照会するAPIである。

```cpp
using namespace pikapika::optics;
InterfaceInput input;
input.incident = {0,-1,0};       // 光が境界へ進む伝播方向
input.normal = {0,1,0};          // 入射媒質の中を向く法線
input.index_incident = 1.0;
input.index_transmitted = 1.5;
input.vacuum_wavelength_m = 550e-9;
auto result = dielectric_interface(input);
```

方向・法線は単位長でなくてもよい。各ベクトルの全成分が有限で、絶対値最大成分が `[1e−6,1e6]` に入ることが必要。屈折率も `[1e−6,1e6]`、真空波長は有限かつ正、単位m。入力の範囲は数値実装の有効域であり、その屈折率が現実の特定材質の測定値であることを保証しない。

`index_incident` と `index_transmitted` は **指定した真空波長における既知の値**。波長は出力にも記録するが、材質表・分散式を自動評価しない。同じ屈折率のまま波長だけを変更して色収差を作る実装ではない。

法線は入射媒質側を向き、入射伝播方向との内積は負になる。逆側から入れるには、逆方向の光線・反転した法線・入れ替えた二つの屈折率を渡す。向きが逆であると区間計算で証明できれば `invalid_argument`。ゼロベクトル・NaN・∞・範囲外も拒否する。

## 結果と不確定

| `InterfaceKind` | 有効な結果 |
|---|---|
| `transmission` | `transmitted`, `cosine_transmitted`, `power` が存在。反射方向も返す |
| `total_internal_reflection` | `power` はs/pともR=1、T=0。実数の伝播屈折方向は存在せずoptionalは空 |
| `uncertain` | `power`, `transmitted`, `cosine_transmitted` はすべて空。成功値の0/1を代入しない |

不確定理由は `incident_side`（入射側の符号を証明できない）、`critical_angle`（臨界付近の符号が未解決）、`numerical_output`（分類が分かっても通常doubleの方向・パワー計算を成立させられない）。未解決を全反射や透過へ勝手に振り分けない。反射方向・正規化方向・入射cosineは近似的な診断値で、未解決の屈折やパワーの代わりにはならない。

判定順序:

1. 原入力の内積を区間で計算。厳密に正なら向き逆として拒否。厳密に負なら入射側が確定。
2. 内積区間が **ちょうど `[0,0]`** の場合だけ `exact_grazing` として接線入射の片側極限を許可する。単に0を含む区間では零の証明にならず、`incident_side` を返す。たとえば二つの非零項が相殺する内積は、本実装の包含では零の点に縮まらず未解決になる場合がある。
3. 向きの処理が終わった後、入力屈折率のdouble値が厳密に等しければ、界面のない解析的極限R=0、T=1、屈折方向=入射方向。角度判定をこの特例で迂回しない。等屈折率・厳密接線の場合もこの透明な極限とする。
4. その他は次節のDの符号で全反射・透過・不確定を決める。

接線入射では正味の入射法線fluxが0であり、その場の0/0を通常のパワー比と定義するのではなく、指定した側から近づけた極限を返す。異なる屈折率のgrazingではR=1/T=0の極限、等屈折率では界面がないR=0/T=1の極限になる。

## 何を包含で保証するか

原入力doubleは正確な二進有理数として解釈する。数学的な入射・法線の単位方向は、それぞれこの原ベクトルを **実数の長さで正規化した方向** と定義する。実装が通常doubleで作った単位方向とは区別する。

原ベクトルをi,n、屈折率をnᵢ,nₜとし、

```text
D = nₜ² |i|² |n|² − nᵢ² |i×n|²
D / (nₜ² |i|² |n|²) = 1 − (nᵢ/nₜ)² sin²θᵢ = cos²θₜ
```

を用いる。分母は有効入力で正。Dが正なら実数の透過方向が存在し、負なら全反射、0は臨界。`i×n`、ノルム二乗、屈折率二乗、積、差の **全構成段階** を既存の独自interval演算で外向き包含する。通常doubleで計算した係数を最後だけ膨張する方法ではない。

`discriminant.lower()>0` だけを透過の確定、`upper()<0` だけを全反射の確定とする。0を含む場合は、上の等屈折率解析分岐を除き不確定。内積の包含も原入力から同様に構成する。sqrt・正規化・逆三角関数の数値誤差は、この符号判定には入らない。

方向とR/Tは通常doubleの近似値であり、値そのものを区間で囲む保証や一律の最大誤差はまだ提供しない。正規化にはhypot、通常の屈折にはsqrtを使い、最後の方向も正規化する。近似cosineは微小な丸め域のみ `[0,1]` へ制限する。パワー値は32eps以内の丸めによる範囲外だけを `[0,1]` へ制限し、それを超えれば `numerical_output`。この制限はDの符号判定に使わない。臨界付近でDが正でも、通常doubleの屈折計算が負や0の根号を作った場合は成功扱いしない。

入力ベクトルや屈折率をこのAPIへ渡す **前** に通常doubleで計算した誤差、測定誤差、十進の意図まで包含するものではない。`point(0.1)` が十進1/10の厳密値を意味しないのと同じ境界である。

## 振幅・パワー・放射輝度

sは電場が入射面に垂直、pは平行。ci=cosθᵢ、ct=cosθₜに対してパワー反射率は

```text
Rs = ((nᵢ ci − nₜ ct)/(nᵢ ci + nₜ ct))²
Rp = ((nₜ ci − nᵢ ct)/(nₜ ci + nᵢ ct))²
Ts = 4 nᵢ nₜ ci ct / (nᵢ ci + nₜ ct)²
Tp = 4 nᵢ nₜ ci ct / (nₜ ci + nᵢ ct)²
```

電場の振幅係数tの二乗だけを透過パワーとしてはならない。実数で非吸収のこのモデルでは、透過側/入射側の法線Poynting fluxの比は `(nₜ ct)/(nᵢ ci) × |t|²`（非接線入射）。実装のTはこの法線fluxから得る上式を安定な積の形で評価し、`1−R` を代入して収支を自明にする方式ではない。

無偏光は、s/pに等しく分配される非干渉なパワーの平均として `(Rs+Rp)/2`, `(Ts+Tp)/2`。垂直入射では入射面の基底は任意だが、両偏光の係数は一致する。全反射時の位相差や楕円偏光、Jones/Mueller伝搬は出力しない。

返すTは界面の法線 **パワー比**。電場振幅、放射輝度の倍率、BSDFの重みとは別である。屈折で変わる立体角・放射輝度の輸送規約やエタンデュ、面交差の幾何係数を含むレンダラーへの接続は、別の設計と検証が必要。

## FP契約と実行

包含分類は `docs/INTERVAL.md` の前提に従う。x64 SSE2またはWASMのbinary64、nearest-even、gradual underflow、例外masked。FTZ/DAZや異なるrounding modeは拒否する。演算中にFP環境を変えない。optics.cppにもfast-math/contract禁止の既知マクロ検査と制御pragmaを置く。

```text
MSVC x64: /std:c++20 /fp:strict
GCC/Clang Native: -std=c++20 -fno-fast-math -ffp-contract=off -frounding-math
Emscripten: -std=c++20 -fno-fast-math -ffp-contract=off
```

光学の明示的 `std::fma` は近似量の評価だけに用い、包含用の演算はinterval関数を通す。コンパイラが勝手に式を縮約することとは区別する。LTO、別CPU、別のFP設定へ移した場合は再検証が必要。

## 独立な検証

`tests/optics_tests.cpp` の通常実行で以下を確認する。

- nᵢ=1、nₜ=1.5の垂直入射: R=1/25=4%、T=24/25。逆向きも同じパワー。
- 同じ屈折率: 任意の確定入射でR=0/T=1、方向不変。
- 入射(3,−4,0): 屈折(2/5,−√21/5,0)。軸回転と入力scale変更も比較。
- Brewster条件の入射(1.5,−1,0): Rp=0、Rs=25/169、反射と屈折の方向が直交。
- 低屈折率側への過臨界入射でTIR、逆屈折経路で方向とs/pパワーが相反。
- 1..89度の角度・4組の屈折率と既知例を含む314透過例で、別の電場透過振幅式と法線flux比に照合。R+Tの収支も独立に確認。
- 既知の臨界例: nᵢ=5/4、nₜ=3/4、i=(x,−4,0)、n=(0,1,0)では厳密に `D=9−x²`。x=3と両隣のdoubleは未解決、十分離れた両側は透過/TIRと判定。
- ゼロ・非有限・範囲外、向き逆、曖昧な相殺接線、subnormal付近の符号、入力域端点を検証。

`--oracle` は原入力、Dと内積の包含端点のIEEE bit、分類を出す。ignoredの `build/optics-proof/verify-optics.py` はPython標準Fractionでbitを正確な有理数へ復号し、D・内積を独立に再構成して包含と分類の誤確定がないことを検査する。参照側は通常doubleの計算を繰り返さない。固定1029例（臨界5例+固定seedの3D形状1024例）を使う。

2026-11-03の最終ソースでの実行結果:

| 実行 | 結果 |
|---|---|
| MSVC19.51.36247.0 / Windows SDK10.0.26100 / x64 Release `/fp:strict` | 16群成功、314透過例を独立flux式と照合 |
| 既存公式Emscripten6.0.13 / O2 / Node24.14.1で実WASM実行 | 同じ16群と314透過例が成功 |
| Native最大誤差 | R+T: `4.4408920985006262e−16`、独立T式: `5.5511151231257827e−16`、Snell関係: `2.6239427297625184e−14` |
| WASM最大誤差 | R+T: `4.4408920985006262e−16`、独立T式: `4.4408920985006262e−16`、Snell関係: `2.0834028946481453e−14` |
| Fractionの独立比較 | 双方1029例のD・内積包含が成功。透過969/TIR57/未解決3で誤確定なし |
| Native/WASM | 1029分類と4116包含端点のbit一致。近似方向/R/Tのbit一致は要求していない |

ここでの最大誤差は試験集合内の観測値で、全入力の誤差保証ではない。包含の根拠は演算ごとの構成とFP契約であり、有限の試験集合だけを全入力の数学的証明としない。

独立buildは `build/optics-proof/`。最終standalone WASMは193,048 bytes、SHA256 `5ff45fe74ed23c9825a3cb5b8f2ccfc957104b8b0761e3c9b4375d081c6e7606`。Native/WASMのCSVは双方SHA256 `0efb1c1b1e8753f700e874d53a249aa7a565c31b7918e059181ef61f901b37f1`（PowerShell出力CRLF）。主ABI、主simulation WASM、レンダラーへの接続は今回の担当範囲では行っていない。

```powershell
# Nativeの独立build（build/optics-proof/CMakeLists.txtに3ソースを列挙）:
cmake -S build/optics-proof -B build/optics-proof/native
cmake --build build/optics-proof/native --config Release
build/optics-proof/native/Release/optics-tests.exe
build/optics-proof/native/Release/optics-tests.exe --oracle > build/optics-proof/native.csv

# 既存公式SDKでstandalone試験物を生成。主WASM配布物を上書きしない:
build/toolchains/emsdk/upstream/emscripten/em++.exe core/src/interval.cpp core/src/optics.cpp tests/optics_tests.cpp -Icore/include -std=c++20 -O2 -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -fwasm-exceptions -sENVIRONMENT=node -sWASM_ASYNC_COMPILATION=0 -o build/optics-proof/optics-tests.cjs
node build/optics-proof/optics-tests.cjs
node build/optics-proof/optics-tests.cjs --oracle > build/optics-proof/wasm.csv
python build/optics-proof/verify-optics.py build/optics-proof/native.csv build/optics-proof/wasm.csv
```

## 一次資料・来歴・残り

- [PBRT 第4版 §9.3](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission) 本文を閲覧。Snell則、Fresnel、s/p平均、全反射の物理的前提を確認。書籍の方向規約や既成コードは移植せず、上記の入射伝播方向と媒質順序で独自実装。
- [MIT OCW 6.007 Lecture33: Fresnel Equations and EM Power Flow](https://ocw.mit.edu/courses/6-007-electromagnetic-energy-from-motors-to-lasers-spring-2011/082040cbe101109ac9f87e94a75ea5b5_MIT6_007S11_lec33.pdf) 本文を閲覧。境界条件、等透磁率の光学式、Brewster、法線エネルギーfluxを確認。図・写真・コードは取り込まない。
- [PBRT 第4版 §9.5 Dielectric BSDF](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF) は放射輝度の輸送に界面パワー以外の因子が必要なことを確認する比較資料。BSDF自体は今回未実装。
- [PBRT 第3版 §6.4 Realistic Cameras](https://pbr-book.org/3ed-2018/Camera_Models/Realistic_Cameras) は既存 `OPTICS_SCOPE.md` の多面系調査を再確認。レンズ処方・図表・資産は取り込まない。

外部の光学ライブラリや材質表を追加していない。C++標準機能と既存の自作intervalのみを使う。試験用の公式Emscriptenランタイムの扱いは既存の依存記録に従い、このstandalone試験物を新たな配布runtimeとはしない。エンジンのライセンスは未選定のまま。

未対応: 複素屈折率/吸収、磁性・異方性、コーティング/薄膜/干渉、波長依存材質、多面レンズ、開口・口径食・収差、ゴースト/フレア、回折/PSF、波動伝搬、画像生成、方向/R/T自体の区間保証。単一界面の今回の結果を、レンズや厳密光学全体の完成とは扱わない。

## 共通WASMと操作ラボへの統合

同じ原本を主simulation WASMへリンクし、`pp_sim_dielectric_interface(9)` と
`runtime.queryDielectricInterface`へ接続した。[31値の出力と規約](SIMULATION_ABI.md#lossless-dielectric-interface-additive-v1-export)。
独立Fraction checkerは`scripts/verify-optics.py`へ収録した。
主モジュールにもNative oracleの1029入力を通し、分類と4116包含端点のbitが一致した。
検証用の`scripts/verify-optics-wasm.mjs`は近似方向/R/Tのbit一致を要求しない。

[単一界面ラボ](../tools/optics-lab.html)は実APIへ入射角・屈折率・波長を渡し、返された
方向とパワーを表示する。臨界プリセットは元の`(3,-4,0)`を維持し、角度編集で丸めた入力へ
切り替える。波長変更で屈折率が自動変化する機能や、多面レンズを描画するものではない。
