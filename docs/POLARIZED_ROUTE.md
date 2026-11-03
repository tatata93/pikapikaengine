# 指定光路の区間偏光 POWER 輸送

`pikapika::polarized_route::trace_route` は、既存 `optical_route` の指定面列を一度だけ計算し、その全 ray / 法線 / 屈折率区間を使って偏光状態を輸送する純粋 C++ API である。入力や既存 World を変更しない。旧 ordinary-double `polarization.cpp` の許容誤差・結果を包含の根拠には使用しない。

この `I` と出力 `power` は同じ ray tube の POWER 正規化である。電場強度、radiance、irradiance、有限瞳の面積積分、センサー画像の輝度とは異なる。指定 route の透過/反射を追う機能であり、自動最近傍、媒質の幾何学的整合、他面の遮蔽、全 ghost 列挙を証明しない。別経路間の相互 coherence、光路長による干渉位相、回折、吸収、複屈折、薄膜も含まない。

## 状態と規約

時間依存は `exp(-i omega t)`。初期の右手基底 `e1 × e2 = d` で `C12=(U+iV)/2` と定義し、左右円偏光という名前には依存しない。点 Stokes の `I∈[0,1e12]`, `|Q|,|U|,|V|<=1e12`、全値 finite を要求する。入力 double は厳密な二進有理数として解釈する。

物理条件は `I>=0`, `I²-Q²-U²-V²>=0`。円錐外を epsilon で許容しない。区間算術で円錐内/外を確定し、判定区間が零をまたぐ場合は `initial_state_uncertain` とする。零状態と軸方向の canonical pure `±Q/±U/±V` は恒等式で受理する。例えば点 `(5,3,4,0)` は物理的でも、この有限手順では未確定になり得る。最小正 subnormal の canonical pure V も受理し、表現可能な端点で真の半値 `2^-1075` を囲む。

初期基底は `d=unit(D)`, `e2=unit(d×reference)`, `e1=e2×d`。正規化の sqrt を共有 `interval::sqrt_enclosure` で囲む。reference の有限成分域は `±1e6`。横成分を確定できない族は未確定で、別軸への fallback をしない。

世界 XYZ の Hermitian `C=<a a*>` を保存する。`diagonal` は xx,yy,zz、複素 `upper` は xy,xz,yz、下三角は共役である。この独立区間箱は真の PSD/transverse 族を包含する。箱の任意の独立成分の組合せがすべて PSD/transverse であるという主張ではない。

## 面での輸送

入射側を向く単位法線 n、単位方向 d から

```
s = unit(n × d)
p_in = d × s
p_out = d_out × s
J = a_s s s^T + a_p p_out p_in^T
C_out = J C_in J†
```

を区間演算で構成する。旧 route の unpolarized power envelope を重みとして使わず、各面で Stokes を無偏光へ戻さない。反射は符号付き Fresnel 振幅

```
rs = (ni ci - nt ct)/(ni ci + nt ct)
rp = (nt ci - ni ct)/(nt ci + ni ct)
```

を使う。透過振幅は `sqrt(Ts),sqrt(Tp)` とし、電場透過係数に必要な斜入射/媒質の flux 因子を含む POWER 正規化である。

全反射では既存 interface が確定した discriminant の負符号から `kappa²=(ni/nt)² sin²(theta_i)-1` を囲み、

```
rs = (ni ci - i nt kappa)/(ni ci + i nt kappa)
rp = (nt ci - i ni kappa)/(nt ci + i ni kappa)
```

を複素区間として輸送する。各偏光の相対位相は次面へ保持される。`|rs|=|rp|=1` の物理恒等式により trace power を前段 power と交差できる。これは ray 間のグローバル位相保存ではない。

全族の `D×normal=0` を証明できる正入射では `R=((ni-nt)/(ni+nt))²`, `T=4ni nt/(ni+nt)²` を直接世界 C に掛ける。反射時 `p_out=-p_in`, `rp=-rs` なので世界の U/V 成分を独自に反転しない。非軸方向の相関喪失により正入射を証明できない場合もある。近正入射で s の正規化を証明できなければ未確定。ni と nt が同じ singleton のときだけ同一媒質の透過 identity / 反射 zero を使う。同じ非点区間どうしを相関した等値とみなさない。

真の passivity/PSD から各対角と power を `[0,sourceI]`、非対角の実虚成分を `[-sourceI/2,sourceI/2]` と安全に交差する。半値上限自体も区間除算で外向きに作る。空の交差、全負などの不整合を zero に潰さず `numerical_failure` にする。相関喪失で箱が広くなることは残る。

## 成功・失敗・予算

全 ray/shape/index/branch/閉 t domain と設定を geometry 開始前に検査する。shape と ray の数値域は `OPTICAL_BOUNDS.md` と同じ。step 上限は 1..64、新 sqrt 上限は endpoint ごと 1..256、総 reported sqrt 更新上限は 1..4000000（既定1000000）。元 route は最大64面で有限処理する。

`geometry` は元 route の完全な診断で、`segments` は power 側の試行と完了 prefix である。geometry が全成功していても power の基底/振幅/初期状態が未確定なら最終 `completion` はない。geometry miss、未確定、branch unavailable、予算失敗も最終 zero 光量にしない。power が進んだ prefix は失敗時の診断だけに使う。`completion` が存在するのは両者が全段成功した場合だけである。

sqrt は元 route が返った直後と新 sqrt 呼出し直後に実更新 counter を監査する。失敗時の overshoot は一回の有限 route または一回の sqrt 呼出し（最大2 endpoint ×256更新）まで。予算を超えたまま成功しない。`refinement_limited` は幅のある包含が残ったことを示し、それだけでは不正/無根を意味しない。既存 primitive が例外で途中更新数を返せない場合は `numerical_failure` とし、完了計算の予算保証へ利用しない。

区間の前提は `INTERVAL.md` の strict FP、round-to-nearest、subnormal 保持、fast-math/縮約なし。共有 sqrt は libm の正確丸めを仮定しない。Native/WASM の一致は観測された試験範囲の証拠で、コンパイラの形式検証ではない。

## 独立受入と再実行

`tests/polarized_route_tests.cpp` の通常実行、`--fixtures`（32固定入力）、`--oracle`（128固有の dyadic Stokes / 2基底の hexadecimal binary64 CSV）を使う。後者は任意の連続入力族を標本だけで証明したという意味ではない。一般包含の根拠は演算の構成にある。

```
python scripts/verify-polarized-route.py native-fixtures.json wasm-fixtures.json --oracle native-oracle.csv --wasm-oracle wasm-oracle.csv
```

checker は Python `-O` を拒否し、名前/個数/順序/スキーマ/有限値/重複 JSON key/状態を監査する。固定受入 corpus の入力 binary64 全体も fingerprint で確認し、面/屈折率/reference を変えたまま旧 oracle を使えないようにする。有理数は JSON を binary64 として読んだ後に `Fraction` へ変換する。JSON 十進字面を別の厳密実数と解釈しない。

独立 oracle は ordinary kernel を呼ばず、別の Python `Fraction` 行列積と二次体 `Q(sqrt(11))` で C 全体を構成する。sqrt11 の隣接 binary64 enclosure は有理数二乗比較で証明する。正常入射、identity、mixed/circular、subnormal、非共面反射、TIR、source 基底変更、R+T energy、有限予算、失敗後再利用、全3形状、geometry/power prefix を含む。

非共面二反射の ni=25,nt=39、両入射 `ci=4/5,ct=12/13` では `rs=-2/7,rp=22/147`。無偏光の正しい最終 power は `42544/17294403`、各面 reset の誤値 `1263376/466948881` は出力区間から除外される。純 U=1 は `322768/259416045`。非共面二 TIR の独立出射局所 Stokes は `(1,424/625,-10007/15625,1696 sqrt(11)/15625)` となる。これらは独立導出した原著の合成入力で、実レンズ測定値ではない。

最終 standalone Native 37群 / 実 WASM 37群が成功した。32 fixtures と128 oracle 行は全 binary64 bit一致、独立包含は片側1539項目、両側計3078項目。入力/出力破損、truncation、schema、非有限、誤位相、subnormal 内向き clamp、`-O` 等の負例88件を全拒否した。これらは当該有限入力での実測である。

build/proof の実コマンド・compiler/SDK・source/artifact SHA・raw output は `build/polarized-route-proof/provenance.json` と `proof-commands.json` に保存する。Native/WASM 証拠の公開コピーは親の統合時に扱う。

## 閲覧した一次資料

- [Peatross / Ware, Physics of Light and Optics](https://optics.byu.edu/docs/OpticsBook.pdf), 2025-01-31 revision、§3.2–3.5（印刷77–82頁、PDF85–90頁）: Fresnel 振幅、法線 flux 比、全反射の複素係数を確認。p 基底の向きによる符号を本 API の規約へ変換した。式の採用と POWER 正規化は本実装で導出し、本文/コード/図は転載しない。
- [Anche et al., Polarization aberrations in next-generation giant segmented mirror telescopes](https://arxiv.org/html/2304.02079v1), §3 式1–3: 世界座標と局所 Jones の合成方法を確認。論文の電場 PRT をそのまま ray-tube POWER と同一視していない。
- [Gil, Interpretation of the coherency matrix for three-dimensional polarization states](https://arxiv.org/pdf/1408.0312), §2 式1–3: Hermitian coherency、PSD、trace の意味を確認。輸送の区間証明は本実装の演算構成による。
- [NIST SCATMECH conventions](https://pages.nist.gov/SCATMECH/docs/convent.htm): 時間依存と基底方向の記載を確認。V の符号/円偏光の名称は資料間で一律と仮定せず、本 API の `C12` 定義を優先する。
