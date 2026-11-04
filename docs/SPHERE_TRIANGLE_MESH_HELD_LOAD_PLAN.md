# 保持荷重と秒時間による球×静的mesh entry: 次のNative受入案

2026-11-04 JST。**Native実装の公開受入済み（7844b46）**。[実装ガイド](SPHERE_TRIANGLE_MESH_HELD_LOAD.md)と[実行記録](../reports/2026-11-04-sphere-triangle-mesh-held-load.md)を参照する。[手動entryラボ](SPHERE_TRIANGLE_MESH_ENTRY_LAB_PLAN.md)に続き、Worldの実SI入力を使う数値核へ進む。既存の線分guard/entry・加速球対/平面・World・SDK/86 exports・ゲームの原本は変更しない。新段はNative-onlyのread-only照会で、時間進行・力の消費・衝撃応答を実装したものではない。外部solver/素材/依存を追加せず、本体license未選定を維持する。

## 既存能力と新しい境界

[dynamics.cpp](../core/src/dynamics.cpp)の`detail::propagate_free`は既に保持外力による二次の並進、世界Lと姿勢中点積分を実装する。`World::step`は候補を進めて既存球/平面接触を解き、成功時に荷重を消費する。[continuous_world.cpp](../core/src/continuous_world.cpp)のW1は、丸めた加速度と厳密なF/m+gの差、伝播のoperation-graph丸め、時間/空間guardを別に監査する。[accelerated.cpp](../core/src/accelerated.cpp)には一定加速度の球対/無限平面の式と探索がある。これらを再実装しない。

今回の新機能は、一定の**世界座標**force/gravityから決まる曲がった球中心経路を、有限で薄い両面三角形の面/辺/頂点まで照会すること。Worldにtriangle storageはまだなく、`planes()`は単位normalの静的半空間である。外部から渡す世界座標の三角形集合を、既存planeや描画meshへ無断で置き換えない。

## 入力とconst World adapter

名前案は`pikapika::sphere_triangle_mesh_held_load`。初段の公開案は次の二入口とし、正式型/enum番号は実装前ヘッダで固定する。

```cpp
Result query(const HeldSphere& input, span<const StaticTriangle> triangles,
             double horizon_seconds, const Settings& settings = {});
Result query_body(const dynamics::World& world, uint64_t body_id,
                  span<const StaticTriangle> triangles,
                  double horizon_seconds, const Settings& settings = {});
```

`HeldSphere`はID、position P0[m]、velocity V0[m/s]、mass m[kg]、force F[N]、gravity g[m/s²]、radius r[m]の点binary64を原値として所有する。動的球proxyの自由飛行だけを定義する。m/F/gは区間中一定、mass loss・時間依存荷重・空力/流体/支持反力をこの式へ暗黙に含めない。

実際のWorld const APIは`find_body(id) const -> const RigidBody*`、`bodies()/planes()`のconst参照、公開`gravity`である。adapterは選択bodyを一回copyし、その`validate()`とgravity/profileを検査して上記raw入力へ渡す。存在しない/unsafe IDは明示invalid、初段の`is_static` bodyは**unsupported bodyとして未認証**にする。静止colliderの力をmで割って動かす実装にはしない。

`RigidBody`にはposition/velocity/radiusのほかorientation、世界angular_momentum、慣性、torque、materialがある。adapterのowned診断には選択body全fieldsとgravityを保持するが、今回の中心運動へtorque/回転を再積分しない。球はpositionを中心とする既存のCoM球proxyで、姿勢による形状変化がない。local collider offset、偏心球、非球形/回転体や動く三角形を受け付けるAPIにしない。将来そのような指定を増やすときは明示unsupportedとし、入力を無視して成功扱いにしない。既存Worldにoffset形状fieldがあるかのような説明もしない。

他のWorld body/planeとの衝突を調べたとは主張しない。面IDは渡したsource集合の安定IDとして保持し、body IDと型付きで区別する。Worldへのcollider登録・ID再採番はしない。全body/plane/gravity・荷重・pointer・外部clockを変更せず、mutable getter、apply_force/step/const_castを使わない。

## 厳密な保持荷重pathと秒時間

入力doubleを厳密な実数とし、各成分で次を構成する。

```text
A_i = I::point(g_i) + I::point(F_i) / I::point(m)
p_i(t) = I::point(P0_i) + I::point(V0_i)*T
         + I::point(0.5)*A_i*square(T)
```

Aは丸めた`g+F*(1/m)`のpointでも、区間の中央値でもない。真の定数加速度g+F/mを包含する内部Intervalのまま使う。返却snapshotは元m/F/g、診断はacceleration boundsを別に保持する。係数の打消しで幅が残った場合も、不足する証拠をpoint化して補わない。

初段は **globalな秒t∈[0,H]をそのまま分割**する。Cellはclosed time_bounds[seconds]とdepthを持ち、midpointは区間内の表現可能なbinary64時刻を選ぶ。この時刻自体を厳密な選択点としてp(t)を囲む。丸めた子のposition/velocityを初期値にして再伝播しない。privateに二分木のindexを使っても、`H*i/2^depth`の丸め値を別の厳密時刻とすり替えない。旧線分のdyadic s∈[0,1] packet/decoderは流用・変更しない。

返すcell/prefix/witness/windowは秒、window幅は`I(U)-I(L)`の外向き包含とする。Hのsubnormal等で内部midpointを表現できなければtime_resolutionで停止する。normalized τ=t/Hは解析説明用であり、出力の時間単位ではない。

窓幅の許容値は時間精度だけを制限する。窓のpath boxと、そのcoordinate幅の外向き和によるL1 diameter上界[m]も診断として返す案を採用する。これは空間の保守的広がりで、最大貫通・伝播誤差・接触点精度ではない。速度1000m/sで1µsが約1mmに相当することを、1µsの位置精度保証と言い換えない。

## 有限domainと探索・証拠

実装前のhard bounds案を次で固定する。入力条件と派生計算が域内と証明できない場合を分け、設定を黙って縮めない。

| 項目 | 初段の契約 |
|---|---|
| H | 有限0<H<=0.1 s。真の1/120ではなくcallerが渡すbinary64秒を使用 |
| body原入力 | ID1..2^53−1、mass[1e−12,1e18]、radius(0,1e9]、P0/triangle座標±1e12、V0±1e9、F±1e24、g±1e9。adapterの他body fieldsは既存validateに従う |
| 派生域 | acceleration bounds±1e12、全path/velocity boundsは既存Worldの±1e12m/±1e9m/s域。過大包含で確証できない場合もderived-domain未認証とし、入力の物理的不正と混同しない |
| source | 1..64、一意な安定ID。全事前検査・全所有copy後に照会。mesh/primitive設定6項は既存域を維持 |
| 時間/探索 | time_tolerance既定1e−7s、有限0<tol<=0.1s。max_evaluations1..256、全partition max_leaves1..128、max_depth0..32、既定256/128/24 |
| sqrt | enclosure1..256既定128、全sqrt既定1000000/上限16777216。R/E各block予約512 |

FP環境を最初に検査し、環境拒否前にIntervalをdefault構築しないResult構造にする。profile/source/adapter不正で原入力/Worldを変更しない。snapshotと全診断の所有・allocation失敗のprefix/null・未照会を区別する。

初期点t=0を一評価として監査し、その後は未照会の最小depth、同率左のBFS。最小負witnessより後の未照会tailもpartitionに保持し、深さ/葉でblockedになったcellだけを除いて他の候補を調べる。初期strict正なしではentryを受理しない。全島のうち0から連続するstrict正だけをprefixへ連結する。

任意binary64 anchor cについて、J全体のp(J)からR>=sup||p(t)−c||、選択点p(t*)からE>=||p(t*)−c||を囲む。既存mesh queryの全row成功によるdistance boundsを[dlo,dhi]とし、`dlo−Rup−r>0`だけをcellのstrict非接触、`dhi+Eup−r<0`だけを厳密点貫通証拠とする。平方和の外向き下端が微小負でも上端からR/Eを囲めることと、平方根自体の非負域を混同しない。

entry_windowは初期strict正、closed[0,L]の証明、UでのE補正strict負、外向き秒幅上端<=tol、exact Workの全条件を要求する。全[0,H]証明だけseparated、初期負はinitial_penetration、境界/接線/品質/予算不足は未認証。全source IDを保守候補に残し、witnessのnearest IDsへ縮めない。

返却済exact-workの回復可能row_failureはunknown cellとして子/別点へ進めるが、そのancestorから証明を作らない。初期失敗、環境、numeric/null-query/unknown-workはglobal停止。全source/profile/body原本、acceleration bounds、initial、全audit/partition/島/blocked/frontier/current、prefix、witness/windowと秒幅・空間diameter、全ID、lastMeshと所属を所有する。

## Workの上限と独立参照

初期1＋最大255の二分木cellで評価/audit最大256。全partition/frontierは128以下。各mesh呼出前にN×512を予約し、各R/E root前に512を予約する。原本のsqrt_enclosureは各endpoint最大256更新なので1row<=512、mesh64<=32768。全体のprimitive更新<=8388608、R/E<=262144、既知合計<=8650752。acceleration/二次式/秒幅/L1 diameterはsqrtを追加しない。

Workは各audit deltaと総和、実mesh/primitive/candidate/root calls、limited、既知更新と保守upper、exactを別に持つ。未返却mesh blockのupper=N×512、未返却R/E blockはそのaudit既知値＋512を保持し、unknownを0へ変えず停止する。実例未注入のallocation/内部例外を、人工packetや構造検査だけで実行済みと報告しない。

独立Python stdlib/Fraction参照は、C++のKKT候補mask/選択結果を正解に使わない。一般quartic/Sturm実装をこの段の必須依存にせず、発行された証拠を次で直接監査する。

1. 原binary64から厳密A=g+F/mを有理数化。各二次coordinateの両端と区間内の停留点−V/Aを調べ、真のcell rangeを求め、p(J) boundsを検査する。
2. anchor cで面内feasible解＋全3clamped辺（endpoint含む）から独立なpoint-triangle最小距離²を求める。全sourceを最小化し、distance boundsを有理数の二乗比較で監査する。
3. coordinate rangeとanchorのbox最大差の平方和がRup²以下、厳密p(t*)との差の平方和がEup²以下であることを確認する。root上端のsoundnessに通常sqrtやDecimal精度を使わない。
4. certificate式は返却doubleの厳密有理値で照合し、全prefix/partition被覆、初期/witness/windowの所属・秒幅・Work・IDを検査する。

これは有限標本の確認ではなく、二次coordinate全区間の極値とLipschitz証拠の独立監査である。一方、原本の全四次最近接問題を一般に解いたoracleとは呼ばない。解析例による非自明な成功/未認証を別途必須にする。

## 必須の解析反例・非vacuous受入

以下はτ=t/H、H=1/16s、triangle A(0,0,0),B(4,0,0),C(0,0,4)。正規化coordinate `C0+C1τ+C2τ²` はP0=C0、V=C1/H、A=2C2/H²へ正確に換算する。mass/force/gravityから同じAを作る入力も含める。H=1の正規化式を実1秒のWorld tickと報告しない。

| 例 | 正規化経路と独立基準 |
|---|---|
| 1 chord偽安全 | p=(1,(1−2τ)²,1),r=1/4。endpoint chordは静止安全だが真のentry=H/4、exit=3H/4。中点d=0の失敗保持と子証拠を確認 |
| 2 chord偽衝突 | p=(−2+8τ,1/8+4τ−4τ²,1),r=1/4。chordは面内で侵入。真pathはτ∈[0,1/8]でx<=−1、[1/8,7/8]でy>=9/16、[7/8,1]でx>=5なので全域strict安全 |
| 3 edge四次 | p=(1,3(τ−1/2)²,−1/4),r=5/16。独立closestはedge AB、d²=9(τ−1/2)^4+1/16。最初のentry=H/4 |
| 4 vertex四次 | p=(−3/16,12(τ−1/2)²,−1/4),r=13/16。closest=A、d²=144(τ−1/2)^4+25/256、entry=H/4 |
| 5 接線 | p=(1,1/4+(τ−1/2)²,1),r=1/4。τ=1/2で接するだけ。負witnessを作らず、entry/全域strict安全へ昇格しない |
| 6 非有理最小 | p=(τ−1,τ²−1/2,−1)。closest=A、d²=τ^4−2τ+9/4、最小はα³=1/2。r=1ではα<5/6からdmin²>1。r=17/16では両端外、τ=3/4で273/256<289/256となり途中侵入。0..3/4の単調性と有理bisectionも独立の根照合に使える |

さらにF/m打消し例: mass3、F=(0,−1,0)、g=(0,fl(1/3),0)、P0=(0,2^-64,0)、r=2^-65、H=1/16、初速0。厳密A_y=−1/(3·2^54)、開始はsqrt(3)/32sだが`g+F*(1/m)`のpoint加速度は0になる。真の係数を含むboundsを検査し、偽separatedを拒否する。Interval幅やgeometry品質で未認証となる結果は許すが、成功のために点化/閾値緩和はしない。

巨大共通offset、正負零、単位時間の2冪rescale、複数侵入/面順逆、64面全ID、実256audit/128partitionと予算不足、初期負/境界、遠い退化/後続row、失敗後再利用も含める。成功を全未認証に置き換えて通過するoracleにせず、例1/3/4と例6(r=17/16)の窓、例2と例6(r=1)の全域安全を実行して非vacuityを確認する。未達なら原結果と原因を保持し、暗黙に入力/品質/予算を変えない。

負例はA=0への置換、chord化、内部極値を外すpath box、E/予約削除、負witness単独の偽window、先行未知域の飛越し、時刻をparameter扱い、time widthを位置誤差扱い、tail/ID削除を拒否する。元body/全World storage・loads/gravity/pointerとsource/settingsのbit不変、Native strict FP/GNU warnings・ASan/UBSan、独立参照・全旧回帰を別に記録する。

## 次段の実装境界

新規追加は`core/include/pikapika/sphere_triangle_mesh_held_load.hpp`、`core/src/sphere_triangle_mesh_held_load.cpp`、専用Native tests/fixtures、独立Fraction checker/reference tests、実装guide。既存核のhelper抽出やABI再生成が必要になれば別の承認済み受入として扱い、原本hashを黙って変えない。今回のNative実装からSDK/JS/UIが使えるとは案内しない。

数学的な保持荷重pathの証明は、ordinary-double `propagate_free`の丸めた位置pathを含む証明ではない。Worldへの実際のadvanceには既存W1相当のoperation-graph propagation tubeと係数差、時間丸め・残時間、空間guardを接続する別受入が必要。W2の拘束候補放物線もg+F/mだけの自由経路とは異なる。

全body/plane/meshのevent順序と同時接触、triangle material/登録、接触点・normal cone/feature競合、manifold、反発/摩擦・支持、全tick rollbackを解く前に応答してはならない。Interval中点をpoint impulseへ渡さず、既存`solve_selected_impacts`は妥当な接触構成とguardができた後に再利用する。一般CCD/World応答・流体/損傷・専門車両航空鉄道・IK/制御・高精度撮像の要求は未完として維持する。本案の数式は現原本と原著の数学的導出に基づき、新外部資料を閲覧したという主張はしない。

次段は[丸め自由伝播guardの計画](SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD_PLAN.md)。この計画追加では新guardは未実装。
