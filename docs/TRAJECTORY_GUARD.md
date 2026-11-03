# W2候補放物線の全区間幾何監査

2026-11-03。`trajectory_guard::audit` は、始状態・終状態・初速度で**定義した数値軌道**が、指定した貫通許容帯から外れないかを調べる独自C++核である。支持反力や衝撃を求めず、Worldを進めず、入力を変更しない。RATTLE等の計算結果を後から監査する用途を想定するが、この核単独は支持時間積分ではない。

## 軌道と入力の意味

```cpp
#include "pikapika/trajectory_guard.hpp"
using namespace pikapika;
trajectory_guard::Settings settings;
settings.spatial_tolerance = 1e-6; // m
const auto report = trajectory_guard::audit(initial, final, planes, dt, settings);
if (!report.success) {
    // 証明済み貫通と、予算不足による未解決を区別する。
    // 失敗した候補をWorldの成功tickとしてcommitしない。
}
```

bodyごとの中心軌道を、binary64で渡された値を厳密な実数として

```text
s ∈ [0,1], t = dt*s
q(s) = q0 + dt*v0*s + (q1-q0-dt*v0)*s²
```

と定義する。sは無次元、dtは秒、qはm、v0はm/s。これは一般の始終速度を補間するHermite曲線ではない。終速度を位置軌道へ使わず、この放物線の終端微分と最終RigidBody.velocityの一致も要求しない。従って、成功だけで運動方程式・終速度・エネルギー収支が正しいとは言えない。

配列は `std::span<const dynamics::RigidBody>` と `std::span<const dynamics::Plane>`。始終bodyの配列長・順番・ID・radius・staticフラグは一致する必要がある。静的bodyの中心は不変、始終linear velocityは0とする。body/plane IDは全体で一意な非zero値。位置・始終速度・半径・plane法線/offsetは有限で各成分の絶対値が`1e12`以下、半径は正、`dt∈(0,0.1]`。bodyとplaneはそれぞれ4096個以下。回転・慣性・質量・荷重・材質はこの幾何照会の対象外で、検証も変更もしない。

planeは固定した半空間で、`n·x <= offset`がsolid、許容側は外側。raw nを数学上の単位法線と仮定せず、距離条件へ実数ノルムを含める。移動・回転planeの時間関数は入力できない。球対の相対位置に伴う法線変化は、中心間距離を全区間で評価することによって扱う。

## 安全条件と平方による証明

`epsilon=spatial_tolerance` はm単位で、`0 <= epsilon <= 1e6`かつ**すべてのbodyのradiusより小さい**必要がある。球対では正の閾値 `R=rA+rB-epsilon` を使い、

```text
fSphere(s) = |qB(s)-qA(s)|² - R² >= 0
```

を全区間で確認する。これは球surface間gapが`−epsilon`以上であることと同値で、epsilonを球ごとに二重加算しない。

planeでは `L(s)=n·q(s)-offset`、`R=r-epsilon>0` として、

```text
L(s) >= 0
fPlane(s) = L(s)² - R²*(n·n) >= 0
```

をともに確認する。この二条件は `L(s)/|n| >= r-epsilon` と同値。負側の遠い点を、平方した距離だけで誤って合格にしない。`n·n`の正値を包含で確認できない極小法線は `numerical_uncertainty`。sqrt・hypot・正規化後の丸めた法線・libm精度仮定は証明に使わない。

## 区間演算と被覆

`interval.hpp`の点区間を原入力doubleから作り、差・積・係数構成・Horner評価・平方・閾値の構成まで各演算を外向きに囲む。通常doubleで係数を完成させてから膨張する方法ではない。球対は**元の始位置差・終位置差・初速度差を先に**作る。共通translationや速度が大きくても、各絶対軌道を別々に伝播してから差し引くことで生じる不要な拡幅を避ける。相対差そのものに必要な包含は残す。

球対の相対放物線を`a+b*s+c*s²`とすると、同じ実数predicateを次の四次多項式でも評価する。

```text
|c|²*s⁴ + 2(b·c)*s³ + (|b|²+2a·c)*s² + 2(a·b)*s + |a|²-R²
```

この係数も原入力からのInterval演算だけで作り、Horner包含と、各座標を囲んで平方した包含を交差させる。曲率支持では各座標boxがO(h²)の幅を生じる一方、実際のgapはO(h⁴)に留まる場合があり、この相殺を四次係数で保持する。planeのLも`(n·c)*s²+(n·b)*s+n·a-offset`として別に囲み、座標評価と交差する。交差が空なら数値失敗であり、一方だけを恣意的に選ばない。

各cell `S=[sLo,sHi]` で、条件の包含下端がすべて非負ならcell全体をcertifyする。できなければ中点を調べ、cellを二分割して続ける。全cellがcertifyされ、全pairが完了した場合だけsuccessとなる。始点・終点・中点の点評価は貫通証拠の探索にだけ使い、有限個の標本が安全という理由で区間を合格にしない。`s=0,1`の評価には、元の始終位置へ戻る厳密な恒等式を使う。

`spatial_tolerance=0`も入力できるが、厳密な接触・許容帯境界では丸めの包含幅が残り、未解決になることがある。0を含む評価は、接触の存在証明でも貫通証拠でもない。Hornerで同じsを繰り返す依存性と、係数間の相関喪失も、未解決や細分化増加の原因になる。

## 結果・予算・静的pair

`Result.success`と`failure`を最初に見る。

| failure | 意味 |
|---|---|
| `none` | 対象全pairとs全体を許容帯内と証明 |
| `invalid_input` | 始終不一致、領域外、無効設定等。候補を監査できない |
| `penetration_witness` | 表現可能な特定sで、禁止領域内であることを包含で証明 |
| `pair_budget` | 次のpairを検査する予算がない |
| `evaluation_budget` | 次の区間/点評価を実行する予算がない |
| `depth_budget` | 未解決cellが最大分割深さへ到達 |
| `numerical_uncertainty` | 正の法線ノルム等を証明できない、または分割不能 |
| `numerical_failure` | strict-FP環境不適合や区間演算等の例外 |

貫通証拠は `has_point_witness=true`、`witness_parameter`と`predicate_bounds.upper<0`を伴う。これは特定sでの証拠であり、最初の衝突時刻ではない。`Predicate`は球の平方clearance、plane符号付きoffset、plane平方clearanceを区別する。後二者も含めて返値を一律のgap[m]と読んではいけない。二乗predicateは法線が無次元ならm²、符号付きoffsetはm。丸めでLの符号を決められなくても、平方clearanceの上端が負なら、どちら側でも許容距離未満であることを証明できる。

失敗pairのIDと未解決cellの`parameter_bounds`は診断値。pairはplane→body、球対は入力配列順。success時のID/predicate/parameter診断は0へ戻す。`evaluations`は点と区間の評価の合計で、初期/終端点の証拠探索も含む。`certified_intervals`は合格したcell数。`maximum_depth`は実際に訪れた最大深さである。

既定予算は100000 pair、1000000評価、深さ48。設定上限は10000000 pair、100000000評価、深さ52。深さ0も有効で、全区間1cellの証明と点証拠探索だけを行う。予算を超えて接触を捨てたり、未解決を成功へ変えたりしない。

既定 `include_static_pairs=true` は静的同士も含める。`false`を**明示**すると、静的body/planeと静的球同士だけを除外し、`skipped_static_pairs`へ数える。静的colliderが地面内部を占有する通常のWorld配置を許すための選択であり、動的bodyを含むpairは常に監査する。

## 保証の境界とW2への接続

包含するのは上で定義した離散放物線の幾何条件。真の拘束運動の解・反力変化・離脱時刻・連続系の打切り誤差は囲まない。外向き丸めによる監査を、RATTLEの連続解に対する検証済み時間積分と呼ばない。

球面上の両端が正しくても、その間の放物線や弦が僅かに球内へ入ることがある。活動支持pairも監査するので、許容帯を超えれば失敗する。driverはdtを小さくするか、別の明示的なdense path監査を実装する必要がある。活動pairを黙って除外する処理はない。角度の大きい一歩で球の反対側へ通過しても、端点だけの安全を根拠に合格しない。

この核は貫通の最小値や最大深さを精密に返す最適化器ではなく、時刻順TOI探索でもない。貫通していても深さ/評価予算が先に尽きれば未解決となり得る。全対象pairを許容帯内と証明したsuccessと、十分な証拠を得られなかった失敗だけを明確に分ける。

## FP契約・検証・来歴

[区間演算契約](INTERVAL.md)と同じx64 SSE2またはWebAssembly binary64、nearest-even、gradual underflow、非fast-math、非FMA再結合が前提。Native `/fp:strict`、Clang/GCC `-fno-fast-math -ffp-contract=off -frounding-math`、WASMでは固定nearest-evenと非contract flagsで個別buildする。`interval::require_environment()`で入力判定前から環境を検査する。signal等で呼出し途中の環境を変更する使用法は対象外。環境probeはコンパイラ全体の形式検証ではない。

独立試験は、高速1000m/s通過、plane側の符号、途中だけ沈む放物線、非単位/非軸法線、曲面支持の許容帯、非中点の狭障害、細分化が必要な安全経路、各予算、巨大共通translation、始終不一致、static除外とdynamic必須、微小法線、空集合、時間scale、Nativeの丸めmode変更を含む。Native24群、公式Emscripten6.0.13でNode実WASM23群（mode変更試験はNativeのみ）の検証を行う。曲面の回帰例`q0=(0,1), v0=(1,0), dt=.01, q1=(.01,sqrt(1-.0001))`では、丸めたq1を原入力として、tol`1e-8m`で分割なし3評価の全区間合格、tol`1e-14m`で途中の貫通証拠を確認する。sqrtはこの試験の終点生成に使うだけで、kernelの証明には使わない。

ignored `build/trajectory-guard-proof/` に個別CMake、Native/WASM実行物、`--oracle`の640例の元入力bits/結果と独立`verify-trajectory.py`を保持する。Fractionで原入力binary64を厳密有理数へ復元し、plane/軸方向放物線の最小値と、一定横距離で反対符号の始終xを結ぶ球対の最小距離を独立に解析する。さらに曲面160例は二次元の距離四次式をz=s²の二次式へ変換し、その最小値を厳密に求める。safe320例、貫通証拠320例を分類し、後者の実数predicateも返却包含内かつ負であることを確認する。162例は丸めた1/120秒を使い、係数を通常doubleで丸めたものとは異なる実数式を照合する。Native/WASM一致だけを包含の根拠とはしない。

式・実装・試験・文書は本projectの原著。既存の自作interval核とC++標準機能を使用し、外部の完成solverや新しい依存を導入していない。数値経路監査という位置付けは [支持モデル](SUPPORT.md)と、Moreau–Jeanの位置違反に関する[Acary RR8602 §4.1](https://arxiv.org/pdf/1410.2499)の読取調査から区別した。論文のcode/図/solverの移植ではなく、上の定義式を直接監査する別の原著核である。engineのlicense選定は本変更では行わない。
