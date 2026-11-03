# 有限偏光 POWER packet の指定経路センサー集計

`pikapika::polarized_packet::evaluate` は再利用可能な純粋 C++ API である。同じ指定面列に有限個の packet を送り、既存 `polarized_route` の偏光を保持した POWER 輸送と、幾何 sensor 円盤を接続する。既存 kernel / World / 呼出側の配列を変更しない。

## POWER measure の入力契約

各 `Packet` の点 Stokes `power={I,Q,U,V}` は **watts**。`I` は caller が明示した、その packet の ray-tube POWER である。Q/U/V も同じ単位で、規約は `POLARIZED_ROUTE.md` の右手初期基底と `C12=(U+iV)/2` を引き継ぐ。範囲も同じで `I∈[0,1e12]`, `|Q/U/V|<=1e12`、有限値、物理円錐の確定が必要。負の光量や円錐外を epsilon で通さない。円錐を確定できない入力は power unknown のまま残す。

packet は互いに非干渉と仮定する有限の離散 POWER measure である。1 packet 内の偏光は世界 Hermitian coherency C として全段保持するが、packet 同士の複素電場を足さない。例えば同じ幾何 ray の1Wを独立な0.5W packet二つへ分割すれば、この線形モデルの検出合計は同じになる。caller は同じ放射を二重登録しない責任を持つ。ここでは一つの指定 route だけを集計するため、複数 route の排他性を証明したり、同じ源から派生する coherent 経路を加算したりしない。

瞳の幾何サンプル weight、個数、分布、面積を自動的に W へ変換する処理はない。source の radiance/強度/開口から packet W を生成する放射モデルは後続機能である。`vacuum_wavelength_m` は全 packet に共通の点波長パラメータであり、入力 POWER を W/nm と解釈したり波長 bin 幅を自動的に掛けたりしない。

`BoundedRay` は packet の幾何状態の包含である。箱の各 member にそれぞれ追加の I watts があるという意味ではない。複数の代替状態を保持し、一つの真の packet 状態に対する結果を囲む。有限幅ビーム内部の面積分布や、sensor rim での部分遮蔽率もこの箱から推定しない。

## 指定光路と理想センサー

各 packet を `polarized_route::trace_route` へそのまま渡す。全 ray / index / normal / coherency の箱を残し、中央値を使わず、面ごとの無偏光 reset もしない。相関喪失を含む真の PSD/transverse 族の包含であり、出力箱の独立 member がすべて物理状態だという主張ではない。

route が全段成功した場合だけ、最終 ray を指定閉 t domain で `optical_bounds::intersect` により sensor `PlaneDisk` へ投影する。sensor は追加の光学 interface ではなく、両面の理想吸収 POWER counter である。法線の長さや入射角により、到着済み ray-tube POWER に追加の cosine / 屈折率二乗 / inverse-square を掛けない。これらを flux と radiance/irradiance の変換と混同すると二重計上になる。角度による部分 aperture 通過は幾何判定で扱う。

sensor の family hit を確定した record だけ `accepted` とし、`sensor_power` は **route completion の `state.power` と同じ区間**になる。sensor miss はこの指定経路での0到達。aperture 境界や t 境界をまたぐ族は `sensor_unresolved` で、黒/0W/通過割合へ置き換えない。自動最近傍、他面遮蔽、housing 吸収、媒質の幾何整合、全 ghost 列挙、sensor の量子効率/応答曲線、画像画素/PSF/干渉/回折は扱わない。

## 集計、prefix、失敗

各 `Record` は元 ordinal、元 caller Stokes watts、status、元 `polarized_route::Result` 全体、sensor 診断、accepted 時だけの `sensor_power` を保持する。geometry/power の失敗 prefix を捨てない。途中までの C を最終到着 POWER として使うこともない。

全 record が accepted、証明された route miss / branch unavailable / sensor miss のいずれかになったときだけ `final_stats` が存在する。

```
total_source_power    = sum(all point packet I)
accepted_source_power = sum(accepted point packet I)
detected_power        = sum(accepted bounded sensor_power)
```

和は C++ interval 演算で外向きに作る。真の passivity に基づいて `detected <= accepted_source <= total_source` と交差する。全負や空交差の不整合を0Wに潰さない。source 合計は未モデル吸収量ではなく入力 finite measure の合計である。空集合は valid な completed zero tally。I=0 packet は route/frame/sensor を省略せず、未知の0W packetがあれば最終 tally もない。

power 未確定が geometry miss の診断と同時にある場合、未確定を優先する保守方針である。geometry だけを見て初期状態の未確定を隠さない。全 packet の ray/Stokes/reference、全 route surface / index / branch / domain、sensor / settings を演算前に監査する。明白に不正な後続入力を、先行 packet の accepted/miss で隠せない。count 上限を超える集合は未受理の budget failure として bounded に拒否する。

unknown は次 packet の診断を妨げない。route/sensor/batch 予算または numerical failure では停止し、残り record は `not_examined`。そのとき `final_stats` はない。失敗後も同じ入力を適切な予算で再試行でき、保持する外部状態はない。allocation failure は診断の割当自体が失敗すると外へ伝播し得る。

## 数値域と仕事予算

ray / shape / t / index / source reference / Stokes の域は `OPTICAL_BOUNDS.md`, `POLARIZED_ROUTE.md` と同じ。`max_packets`, `max_evaluations` は1..1024、既定1024。route settings は元 kernel の全制限を保持する。route ごとの総 sqrt 予算と batch 総 sqrt 予算は独立に指定でき、どちらも1..4000000、既定1000000。max steps は1..64、各新 sqrt の endpoint 更新上限は1..256。

`geometry_sqrt_refinements`, `power_sqrt_refinements`, `sensor_sqrt_refinements` と3種 query counter を別々に報告する。batch 総更新数は packet の有限 route+sensor の後に監査するため、失敗時 overshoot は最大一 packet の仕事まで。completed は総予算を超えない。元 route の局所予算を超えた record も最終 tally に加えない。primitive 例外が隠す途中 counter は numerical failure であり、完了の仕事保証には使わない。

`refinement_limited` な広い包含でも、必要な hit/frame/amplitude を確定できていれば valid な completed 結果になり得る。幅を勝手に縮めず、limited を unknown と同一視もしない。メモリ必要量は保持する全 prefix に依存する。個数の許容は割当成功や性能の保証ではない。

strict FP / round-to-nearest / subnormal 保持 / fast-math と縮約なしは `INTERVAL.md` の契約を引き継ぐ。点入力 double を厳密な二進有理数として解釈し、微小な POWER も通常の double 演算による内向き clamp で消さない。

## 独立受入

`tests/polarized_packet_tests.cpp` は通常試験、完全入力の `--fixtures` JSON、128固有の POWER / identity・plate・ghost 入力の `--oracle` hexadecimal binary64 CSV を出力する。checker は次で実行する。

```
python scripts/verify-polarized-packet.py native-fixtures.json wasm-fixtures.json --oracle native-oracle.csv --wasm-oracle wasm-oracle.csv
```

Native fixture path 必須、WASM と corpus は任意。Python `-O` は拒否する。32/64bit integer や十進表示の違いを入力実数の違いと混同せず、JSON はまず binary64、その値から `Fraction` を作る。case 名/順序/個数、固定入力の binary64 fingerprint、スキーマ、重複 key、有限値、record/count/prefix/sensor の整合、予算、最終 tally の有無を fail closed に監査する。有限 corpus での一致は連続 source / pupil 積分の誤差証明ではない。

独立有理数参照では `r=(1-3/2)/(1+3/2)` から `R=1/25`, `T=24/25` を導く。5W の正常平板二透過は `5*(24/25)^2 = 4.608 W`、内面二反射を指定した ghost は `5*(24/25)^2*(1/25)^2 = 0.0073728 W`。ghost は単独の明示 itinerary であり、これらを他の coherent route と合算していない。

以前の独立非共面 Jones 行列 oracle の出力 power `42544/17294403` と純Uの `322768/259416045` も packet 経由で確認する。面ごと無偏光 reset の誤値を除外し、入射 cosine=4/5 の斜め非単位方向 ray でも detector が既に輸送した1Wを0.8Wへ減らさないことを確認する。2 TIR、全3 primitive、known omission、sensor境界、partial prefix、円錐/基底未確定、後続不正、個数/評価/sqrt予算、再利用、最小 subnormal の真の POWER、明示 W partition、空集合を含む。

最終 standalone Native42群 / 実 WASM42群が成功した。36固定 fixtures と128固有 oracle 行は全 binary64 bit一致、独立 Fraction 包含は片側501項目、両側計1002項目。入力/出力/型/個数/順序/有限値/予算/prefix の破損、subnormal の内向き0 clamp、余分な cosine/index 係数、誤 reset、`-O` 等の負例107件を全拒否した。これは有限受入集合での実測であり、連続光源/撮像全体の完成ではない。

実行手順・raw input/output・checker 負例・compiler/SDK/source/artifact SHA は `build/polarized-packet-proof/provenance.json` と `proof-commands.json` に保存する。公開証拠へのコピーと共通 ABI/JS/CI 統合は親担当である。

## 閲覧資料と実装の区別

- [PBRT 4ed, Radiometry §4.1.1](https://pbr-book.org/4ed/Radiometry,_Spectra,_and_Color/Radiometry): flux の W、面積密度である irradiance、角度/面積の区別を実閲覧して確認した。本 packet API の有限 measure と理想 detector はここで明示したモデル定義であり、PBRT の無偏光 radiance 輸送コードを使用していない。
- [PBRT 4ed, Specular Reflection and Transmission](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission): Fresnel と幾何輸送の前提を確認。追加の radiance 変換係数を POWER に流用しない。
- 偏光 / 全反射 / coherency の閲覧一次資料と導出は [POLARIZED_ROUTE.md](POLARIZED_ROUTE.md)。この batch はその厳密核を実呼出しし、旧 ordinary-double polarization を厳密性の根拠にしない。外部コード/図/測定データの転載、新依存、ライセンス変更はない。
