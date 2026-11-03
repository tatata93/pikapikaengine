# 実数結果を囲う区間演算の基盤

2026-11-03。`core/include/pikapika/interval.hpp` と `core/src/interval.cpp` の独自C++実装。有限doubleとして与えられた数を厳密な二進有理数と解釈し、加減乗除・平方・多項式評価の実数結果を囲む。各基本演算の直後に包含を行う。加速度付き接触時刻探索に必要な前提の一つであり、根の分離、衝突応答、WorldのCCDはこの変更に含まれない。IEEE 1788への適合実装とは称さない。

## 集合とAPI

名前空間は `pikapika::interval`。`Interval(lo,hi)` は空でない有限実数の集合を囲む。NaN、逆順、`[+∞,+∞]`、`[−∞,−∞]` を `invalid_argument` で拒否する。`Interval::point(x)` は有限doubleのみ、`whole()` は全有限実数。端点の∞は非有界を示す境界であり集合の要素ではない。したがって `whole().contains(+∞)` も `contains(NaN)` もfalseになる。空の交差は `std::nullopt`、未定義値を格納するNaIや空区間型は設けない。

| API | 規約 |
|---|---|
| `lower()/upper()` | 境界を取得。両端の実数0は下限−0、上限+0へ正規化 |
| `contains(double/Interval)`, `contains_zero()` | 有限実数の所属・区間の包含・0の所属 |
| `strictly_positive()/strictly_negative()` | `lower()>0` / `upper()<0`。0に接する片側区間と区別 |
| `sign()` | negative / nonpositive / zero / nonnegative / positive / mixed。mixedは負と正の両方を含む |
| `intersection(a,b)`, `hull(a,b)` | 交差 / 両方を囲む最小の単一区間 |
| `add/sub/mul/divide`, `+ − * /`, `negate` | 演算結果の包含。除数が0を含むと `domain_error` |
| `square(x)` | 0をまたぐ場合も下限0を利用。一般の `x*x` より相関を利用できる |
| `polynomial(coefficients,x)` | Horner評価。係数順は **最高次数→定数**、空列は拒否 |
| `environment_issue()/require_environment()` | 前提を検査。問題の説明文字列 / `runtime_error` |

例えば `polynomial({1,−3,2},x)` に相当する係数区間列は `x²−3x+2` を表す。区間が0を含む場合は「未解決」であり、根の存在や接触の証明にはならない。区間下限が厳密に正なら、その区間全体で多項式が正という除外に利用できる。繰り返し現れるxの相関を失うため、細分化が必要になる場合がある。

## 各演算の包含

有限端点の加減乗除をそれぞれ分離した関数で一度binary64へ格納し、直後に `nextafter(result,−∞)` / `nextafter(result,+∞)` を取る。nearest-evenで丸めた値の前後の隣接値は、正しく丸められた基本演算の正確な実数結果を囲む。厳密に表せる結果でも広がる場合がある。最小幅や正しく方向丸めされた最適端点を保証する実装ではない。

加減算は単調性で下限・上限を選ぶ。乗算は4つの端点積の下限の最小・上限の最大。`square` は非負性と0の極小を使う。除算は0を含まない除数の逆数を外向きに囲み、その区間との乗算を再度外向きに囲む。逆数と乗算の **2段階** の包含であり、直接商の最狭区間より広がることがある。

たとえば実数として `((2^53+1)−2^53)=1`。通常doubleで最後まで計算すると0になり、最後の0だけを1ulp膨張しても1を囲めない。本実装と試験では加算時点から囲み、合成した減算の結果が1を含むことを確認する。外向き包含は式を構成する各段階で必要になる。

呼出側も、係数や入力を計算する段階から包含演算を使う必要がある。通常doubleで計算済みの値を後から `point()` に入れても、その以前の丸め誤差は回復できない。`point(0.1)` は渡されたdoubleの正確な二進値の点であり、十進実数1/10を厳密に表す点ではない。

## overflow・微小数・非有界境界

- 有限演算が+∞へoverflowすると下限は最大有限double、上限は+∞。負のoverflowは−∞と負の最大有限値で囲む。∞の点区間にはしない。
- 最小subnormal未満の正確な結果も0の両隣の値で囲む。例えば `2^−1074 × 1/2 = 2^−1075` は正の実数であり、0だけとはしない。平方の下限は非負性で0に制限する。
- 非有界の加減算は先に境界を処理する。数学的に無限な下限を `nextafter(−∞,+∞)` で有限化しない。有限演算のoverflowと非有界の入力は区別する。
- 端点積の `0×∞` は有限実数集合の極値を求めるための0境界として処理し、IEEEスカラー演算でNaNを生成しない。特に `[0,0] × whole() = [0,0]`。この規約は∞を実数の要素として乗算する意味ではない。
- `1/±∞` の境界は±0。0を含む除数（片側の0端点も含む）は、分子が0でも明示拒否する。分裂区間や∞を根として扱う機能はない。
- 想定外のNaNが基本演算から出た場合は例外にする。NaNを区間端点として伝播させない。

## 実行・コンパイル前提

対象はx64のSSE2 binary64とWebAssembly。`is_iec559`、基数2、53bit精度、指数域、subnormalの存在、`FLT_EVAL_METHOD==0` をコンパイル時に検査する。未対応のCPUは実行時に拒否する。

Nativeは `FE_TONEAREST`、段階的underflow、例外maskedが必要。区間生成・演算・交差・hullの各入口で検査する。x64ではMXCSRのrounding、FTZ、DAZ、例外maskを先に読み、不適合なら微小数の演算や比較をする前に拒否する。次に最近接偶数丸め、微小な入出力、0/1/∞付近の `nextafter` を実演算で確認する。環境検査はコンパイラ全体や標準ライブラリ全入力の形式検証ではなく、下記のビルド契約も保証の前提になる。取得済み区間に対する `contains/sign/strictly_positive` などの比較だけの問い合わせでも、この環境を維持すること。演算の途中でsignal等により同じthreadの浮動小数環境を変更する使用法は対象外。

WebAssemblyの通常のf64基本演算はnearest-even固定、例外は非停止。今回のEmscriptenでは `fesetround(FE_UPWARD)` が0を返してもf64の丸め方向は変わらなかった。試験は返値だけで「丸めを変更できた」と判断せず、実際のmode・演算probeとWASMの仕様を用いる。

必要なビルド方針:

```text
MSVC x64: /std:c++20 /fp:strict
GCC/Clang Native: -std=c++20 -fno-fast-math -ffp-contract=off -frounding-math
Emscripten: -std=c++20 -fno-fast-math -ffp-contract=off
```

fast-math、finite-math-only、FMAへの式縮約・再結合、x87の拡張中間精度、relaxed SIMDは使用しない。実装は既知のfast-math/contractマクロをビルドエラーにし、MSVCの厳密制御pragma、Clangのcontract-off、単一基本演算だけを含むnoinline関数とvolatile binary64格納を使う。これらは不適切な未知のコンパイラ設定を完全に検出する仕組みではない。検証したstrict flagsを外して同じ保証があるとはしない。LTOや別CPUへ変更した場合も再検証する。

実装はrounding modeを変更しないが、probe・演算・`nextafter` は浮動小数例外flagやerrnoを変え得る。これらの保存や、結果に対応するflagだけの報告は保証しない。検査には実行費用があり、性能計測前の参照基盤として扱う。

## 試験と再現

`tests/interval_tests.cpp` は解析的に既知の二進境界・1/3・106bit相当の積・中間で消える低位項・overflow・subnormal・非有界集合・符号・交差・二次/四次式・不正環境を検査する。`--oracle` は入力と包含端点のIEEE754 bitをCSVとして出力する。独立の `scripts/verify-interval.py` はmantissaと指数をPython標準 `Fraction` へ整数で復号し、正確な有理数の四隅の演算・平方の極値と両端を比較する。参照側で同じdouble演算を繰り返して一致を確認する方式ではない。

2026-11-03の独立実行結果:

| 対象 | 結果 |
|---|---|
| Windows x64 / MSVC 19.51.36247.0 / SDK10.0.26100 / Release `/fp:strict` | 18群成功 |
| 既存公式Emscripten6.0.13 / O2 / Node24.14.1で実WASM実行 | 17群成功。Native固有MXCSRの1群は対象外 |
| Native正確有理数比較 | 6,829区間で包含成功 |
| 実WASM正確有理数比較 | 同じ6,829区間で包含成功 |
| Native / WASM比較 | 6,829行・13,658端点のbit一致 |
| 禁止設定の検査 | Emscripten `-ffast-math` を指定した別compileが、実装の明示的 `#error` で拒否された |

corpusは25個の符号・0・指数境界・最大有限・最小subnormal等の組合せと、固定seedの512組の全指数域有限bitパターンから成る。有限個の試験だけで全入力の証明とはしない。包含の根拠は前節の浮動小数契約と演算ごとの構成で、oracleは実装・ビルドがそれに反しないかを独立に検査する。

独立検証で使った一時ディレクトリは `build/interval-proof/`（配布物ではない）。最終standalone WASMは177,151 bytes、SHA256 `7c605486eff4fd6f6977c8aaf474627c26f71beab6c305c96f2baf84e0689a61`。Native/WASMのCSVは双方SHA256 `04e0dc89354f40c5b1107f29e7c89e0bc3f1506c15a5f95e119c6696afb85a51`（PowerShell出力のCRLFを含む）。主simulation ABIの公開29関数に区間演算は追加していない。既存SDKのみを使い、外部区間ライブラリは導入していない。

```powershell
# 親プロジェクトのNative test executable（統合後）でCSVを出す場合:
build/native/Release/pikapika_interval_tests.exe --oracle > build/interval-native.csv
python scripts/verify-interval.py build/interval-native.csv

# 今回のstandalone実WASM検証で使ったコマンド:
build/toolchains/emsdk/upstream/emscripten/em++.exe core/src/interval.cpp tests/interval_tests.cpp -Icore/include -std=c++20 -O2 -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -fwasm-exceptions -sENVIRONMENT=node -sWASM_ASYNC_COMPILATION=0 -o build/interval-proof/interval-tests.cjs
node build/interval-proof/interval-tests.cjs
node build/interval-proof/interval-tests.cjs --oracle > build/interval-proof/wasm.csv
python scripts/verify-interval.py build/interval-proof/native.csv build/interval-proof/wasm.csv
```

## 次に必要なもの

加速度一定の相対軌道 `r(t)=r₀+v₀t+(a/2)t²` から球間隔の式 `r(t)·r(t)−R²` を作ると四次式になる。今回の演算は係数生成・時間区間での符号除外に使えるが、時間区間の安全な細分化、最初の根の分離、接線/重根、精度や計算予算で未解決となる場合の結果型は別途必要。普通のdoubleで作った四次係数を後から点区間にするだけでは、係数生成の丸めを囲めない。

未知の運動、変化する外力、回転形状、接触後の残り時間と持続接触、Worldへの応答統合、一般形状CCDは未完。超越関数、sqrt、三角関数、十進の方向付き読込、IEEE1788のdecorationや準拠試験も追加していない。

後続統合では、この同じinterval.cppをstrict flagsで別objectとして主simulation WASMへ
リンクした。加速軌道の照会と単一光学界面の分類が実使用する。区間型そのものを
C ABIとして公開するものではない。[共通ABI](SIMULATION_ABI.md)は32関数となった。
過去のstandalone計測と、今回の公開モジュールへの接続を区別する。

## 実閲覧した一次資料と来歴

以下は仕様・考え方の参照。コード・試験・説明は独自作成。規格本文の購入や外部ソースコードの取り込みは行っていない。エンジンのライセンスは引き続き未選定。

- [GNU C Manual: Rounding](https://www.gnu.org/software/c-intro-and-ref/manual/html_node/Rounding.html) — 基本演算の丸めと、演算ごとに上下の境界を作る必要性を確認。取得時は本文の検索キャッシュを閲覧（直接取得はtimeout）。本実装のnearest+隣接値による包含はこの前提から構成したもの。
- [WG14 N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) §7.12.11.3 / F.10.8.3 — nextafterの隣接表現値、丸め方向からの独立、微小/overflow時の例外flagを本文確認。C++側の宣言は [C++ draft `<cmath>`](https://eel.is/c++draft/c.math) も確認。
- [Microsoft `/fp`](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170) と [predefined macros](https://learn.microsoft.com/en-us/cpp/preprocessor/predefined-macros?view=msvc-170) — strict/fast/contractの違い、環境変更、縮約、検出マクロを本文確認。
- [WebAssembly numerics](https://webassembly.github.io/spec/core/exec/numerics.html#floating-point-operations) — 通常f64演算のnearest-even固定、非停止、二進値の丸め規約を本文確認。
- [IEEE 1788公式概要](https://standards.ieee.org/ieee/1788/4431/) — 標準の対象範囲を概要で確認。規格全文は取得しておらず、適合認証の根拠にはしない。
