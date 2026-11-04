# 静的三角形集合と定義線分軌道のstrict非接触guard案

2026-11-04 JST。**Native実装・ローカル受入済み、公開受入は確認待ち**。既存の有限集合照会を、球中心の定義された線形経路の全区間証明へ使う次の最小Native段である。新規Native header/cppと69群/独立参照を実装した。実測はSPHERE_TRIANGLE_MESH_TRAJECTORY.mdと対応検証記録を参照する。共有SDK/手動ラボ/ゲームには追加していない。以下の契約をsphere_triangle_mesh_trajectory.hppへ反映し、既存APIの意味を変更しない。

## 何を証明するか

入力binary64を、丸める前の理想十進数ではなく、それぞれが表す厳密な実数として解釈する。

```text
p(s) = q0 + s (q1 − q0),  0 <= s <= 1
S = 指定した1..64枚の静的な両面三角形の和集合
g(s) = distance(p(s), S) − radius
```

q0/q1/頂点/radiusの単位はm、sは無次元である。時刻・速度・加速度・姿勢・荷重は入力しない。完了条件は **すべてのsでg(s)>0**。接触を許すepsilonやpenetration bandは設けず、`>=0`へ緩めない。面順・ID・signed zeroを原本のまま保持し、表裏とも有限三角形との距離を扱う。隣接面、閉固体の内部、厚み、片面材質は推測しない。

`trajectory_guard::audit` は球/平面・球対の定義放物線と許容帯を監査する既存核である。本案は静的な有限三角形集合に対する別の線分経路証明であり、その実装の置換ではない。両者とも連続した運動方程式の真解を囲むAPIではない。本案の成功でWorld/CCD・最初の衝突時刻・接触法線・manifold・衝撃/摩擦/支持反力が完成したとはしない。

## 距離のLipschitz性を使う導出

三角不等式から、任意の点x,cと任意のt∈Sについて

```text
|x−t| >= |c−t| − |x−c|
```

なので、S上の最小値を取れば `d(x,S) >= d(c,S)−|x−c|`。xとcを交換して `d(x,S) <= d(c,S)+|x−c|` も得る。有限三角形の和集合は空でないcompact集合であり、ここでの最小値は存在する。この数学的導出を本段の原著記述とし、新たな外部論文の実読・第三者実装利用を主張しない。

cell `J=[a,b]` の全経路を外向きInterval演算で

```text
D = point(q1) − point(q0)             // 成分ごと、差の丸めも包含
P(J) = point(q0) + interval(a,b) * D
Pm = point(q0) + point(m) * D         // mは表現可能なdyadic parameter
```

と囲む。端点用にq0/q1へ戻す厳密恒等式を使うことは可能だが、他のsに対して通常doubleで作ったp(s)を点区間へ昇格しない。既存Intervalのstrict-FP・runtime environment契約を全過程へ適用し、呼出し側のFP modeは変更しない。

anchor `c` は有限binary64の**任意点**でよい。候補はPmの各上下端を半分ずつ加えた有限のbox centerであり、通常doubleの丸めを含んでもcはそのbinary64点自身として扱う。「cが厳密なp(m)である」としない。派生anchorは既存単一面核の座標域にも入ることを検査し、非有限/域外なら明示失敗する。

```text
R2 = sum_k square(P(J)[k] − point(c[k]))
E2 = sum_k square(Pm[k]   − point(c[k]))
R >= sqrt(R2.upper), E >= sqrt(E2.upper)
```

差・平方・加算・sqrtの上下端を既存Intervalと `sqrt_enclosure` だけで作る。R/Eにはその実sqrt包含の上端を使用する。未校正のlibm sqrt・ordinary norm・後付けepsilonは証明に使わない。Rはcell全体の `|p(s)−c|` の上界、Eは厳密な `|p(m)−c|` の上界である。boxが広すぎても包含は維持されるが、成功しやすいとは限らない。

R/Eの初段はそれぞれ `sqrt_enclosure(point(R2.upper))` / `sqrt_enclosure(point(E2.upper))` の上端を使う。真のノルムの下端を必要としないためである。有限かつ非負のupperを確認してから呼び、区間加算の外向き丸めで現れた負のlowerをそのままsqrtへ渡さない。このpointは「真のノルムがこの値」とする点化ではなく、包含済みの二乗上界そのものの平方根を囲む操作である。

既存の `sphere_triangle_mesh::query({c,radius}, triangles, meshSettings)` を**そのまま一回**使う。全row completedかつnearestを持つ場合だけ、そのdistance bounds `[L,U]` を使う。次の二つを各演算から外向きに構成する。

```text
clearanceCertificate = point(L) − point(R) − point(radius)
penetrationCertificate = point(U) + point(E) − point(radius)
```

- clearanceCertificate.lower > 0 なら、J全体をstrict separatedとしてcertifyする。
- penetrationCertificate.upper < 0 なら、**厳密なp(m)** にstrict penetrationが存在するpoint witnessを返せる。
- それ以外は未解決。0を含む/下端0/上端0を接触・非接触・貫通と決めない。分割可能なら次のcellへ細分化する。

`L−R−radius` 等を通常doubleで計算してから比較せず、丸めで微小な正値を捏造しない。有限だがwide/limitedなsqrtでも、真の包含と厳密不等式が成立すれば使用できる。limited flagと実更新数は診断へ残す。

この二certificateはそれぞれ**下界式/上界式そのもの**の数値包含で、g(s)全体の上下端pairではない。clearanceCertificate.upperを経路gapの上界と解釈したり、penetrationCertificate.lowerをpoint gapの下界と解釈しない。既存meshのnearest.gap（anchor cに対する距離gap区間）とも区別して命名/保存する。

mesh::queryが1行でも失敗した場合は、そのcellをcertifyせず `not_certified / mesh_query_failed` とする。遠方の退化面を無視しない。例えばcが三角形上にあると既存核はd=0で単位法線を作れず失敗するため、本案も貫通を推測せず未認証で止める。これは距離専用核ではない既存APIを再利用する初段の実質的な不完全性である。

## 入力と有界処理の候補

Native純粋入口は概念上 `audit(q0,q1,radius,span<const StaticTriangle>,Settings)->Result`。resource builder・mutable Worldは導入しない。初段の領域は次とする。

| 対象 | 候補範囲 |
|---|---|
| q0/q1/全頂点 | finite、各成分abs<=1e12 m |
| radius | finite、0<radius<=1e12 m、subnormalも黙って0にしない |
| surfaces | 1..64、元順、ID1..2^53−1のunique safe整数 |
| mesh profile | 既存mesh/singleの公開範囲と同じ。小さいmaxSurfacesを呼出し予算として尊重 |
| maxEvaluations | default256、1..1024。実mesh::queryを一回呼ぶごとに1 |
| maxLeaves | default/hard128、1..128。certified+pendingを合わせた現在partitionの総cell数 |
| maxDepth | default16、0..32。depth0でも[0,1]を一回評価 |
| enclosureSqrtRefinements | default128、1..256/endpoint |
| maxTotalSqrtRefinements | default1,000,000、1..16,777,216。primitiveとR/Eの実更新数の合計 |

入力/全source/profileを先に検査し、無効な最後の面があるのに先頭だけを証明しない。environmentチェックはInterval構築より前で、既存核同様に優先する。構造検査後に全原本を所有copyし、その失敗も原入力を変更しない。入力domainの1e12は既存単一核の1e150より狭い初段の明示契約であり、既存核のdomainを縮める変更ではない。

各sqrt blockを実行する前に、残り総予算が当該blockの最悪更新数以上あることを要求する。mesh query blockは `N*512`、R/Eの各sqrt blockは最大512更新（上下端各256）を予約する。**予約量を実使用として報告しない**。終了後は返却された実更新数のみ加算して未使用予約を解放する。既存primitiveのpost-call予算auditやlimited結果は変えず、guard側は新しい総予算を越すblockを開始しない。小予算では、実際に必要な更新が少ないケースでも予約不足により未認証となり得ることを明示する。

予約根拠は原本で確認した呼出し数に置く。`core/src/sphere_triangle.cpp:124` のsqrt_enclosureはdistanceの一箇所だけで、設定refinementsは同file:62の1..256。`core/src/interval.cpp:212` のendpointループは指定回数以内、同関数末尾の上下端各一回（同値なら一回）なので、単一queryの実更新数は `2*sqrt_refinements<=512`。single同file:125のmaxTotal判定は**実call後**であり、これだけをglobal予算へ代入してhard上限としない。meshは最大N枚の全列挙で、`core/src/sphere_triangle_mesh.cpp:60` も各row<=512を監査している。新guardのR/Eはそれぞれ一回のsqrt呼出しだけとするため、その二blockに各`2*enclosureSqrtRefinements<=512`を保守予約できる。既存profileの幅/条件/精度設定を黙って下げない。正式実装時にこのcall数と原本byteを再監査し、増えていれば予約式/上限を先に変更する。

例外中の未返却workは別に扱う。sqrtが内部更新後にthrowすると、そのSqrtResultのcounterは返らず、既存single/meshのfailureにはその未返却更新数が現れない可能性がある。従って失敗全般のcounterを無条件に「完全な実work」と呼ばない。成功blockでは実返却countを集計し、未返却の可能性がある失敗blockでは予約を解放せず、そのblockを含むwork下限/保守上限と`workExact=false`を保持して処理を止める。上限は`knownBefore+reservedBlockWorst`で、返却countへ予約全量を二重加算しない。全体separatedには全blockが正常に返りworkExactであることも要求する。この追加のcertainty/上下界DTOの正式名称はNative着手時に固定する。

maxLeaves128の完全二分木は最大255評価nodeであり、maxEvaluationsを1024に設定してもこのpartition上限を越えない。この冗長性を隠さず、実処理のhard上限は255 mesh queries/16,320 primitive rows/114,240 KKT candidatesとなる。primitive sqrtは最大8,355,840更新、R/Eは最大261,120更新、計8,616,960更新（実際は設定総予算以下）。これは処理量・メモリの上限で、時間/速度保証ではない。hard128を変更したい場合はこの計算と受入を着手前に更新する。

## 全被覆と予算失敗

最初のpartitionは閉区間[0,1]一つ。未解決cellを `[a,m]` と `[m,b]` に分け、**左側を先に**深さ優先で処理する。mはdyadicで、同じbinary64値を左右の境界へ使う。両区間はmで重なり、穴を作らない。split前に `partitionCellCount+1<=maxLeaves` とdepthを監査する。最大depth32の現在契約では[0,1]由来のdyadic midpointは厳密に表現できるが、なお `a<m<b` を確認し、満たせなければparameter_resolutionで拒否する。未到達の防御分岐を、実public入力で発火確認済みとはしない。

処理済みのcertified leafと未処理frontier/現在cellを区別する。成功を返す直前に、certified leavesの元順が0から1まで境界一致して覆い、全leafのstrict certificateが揃うことを再監査する。端点/中点の有限個の安全観測でsuccessにしない。

左優先で確定した**連続prefixだけ**を `safePrefix` に記録する。何もcertifyしていない状態ではoptionalをnullとし、`safeUntil=0`だけで[0,0]の安全が証明されたように見せない。未処理右側の点witness/局所certificateで先行cellを飛び越えてprefixを進めない。証明済みprefixがあっても、残時間/残区間を捨てて全体successへ昇格しない。

evaluation/leaf/depth/sqrt予算不足・mesh失敗・丸め幅・分割不能では `not_certified` と対応reasonを返し、remaining partitionを区別して保持する。penetration witnessは存在証拠であり、最初の接触時刻/entry bracket/応答の許可ではない。witness発見時も未照会範囲を「貫通なし」と扱わない。

## owned結果・診断の最小案

正式enumの名前/順序はNative実装開始時に固定する。候補statusは `separated / penetration_witness / not_certified / invalid_input / unsupported_environment / numerical_failure`。reasonは入力/profile・surface budget・mesh_query_failed・evaluation/leaf/depth/sqrt budget・parameter_resolution・数値/割当/environmentを区別する。

Resultには以下を持たせる。

- 全事前検査/copyが完了した場合だけのowned input snapshot。無効入力やcopy未完に架空の完全snapshotを付けない。
- 全体status/reason、返却済みmesh/primitive queries・KKT・primitive/enclosure/合計sqrt更新・limited件数、最大depth。未返却workの可能性がある時はcertainty flagと保守上限も付け、既知の返却countを完全実workとしない。
- certified leafの閉parameter boundsとstrict lower-gap certificate、optionalな連続safePrefix。
- optional witness `{parameter, exactPathBounds, anchor, errorUpper, upperGapCertificate}`。negative upperを証明した時だけ存在。
- 未certifiedな現在cellと、まだqueryしていないfrontier。null queryをmiss/成功にしない。
- 最大maxEvaluations個のcompact CellAudit（parameter/depth、p(J)/p(m)のbounds、c、R/E、実mesh status/counts/distance、certificate、処理結果）。全cellへ完全な64行Resultを蓄積しない。
- 最後の実mesh::Resultをoptionalで完全所有し、全row/候補prefix・失敗理由を失わない。call未実行ならnull。前の成功queryを後の未実行cellの結果へ転用しない。

DFS frontierはdepth32で最大33 cells、partition全体はmaxLeaves以下、CellAuditは1024以下という別の上限を持つ。例外/割当失敗時は実際に保存できた診断だけを返し、完全snapshotや全被覆を捏造しない。既存queryと同様にstatus設定とmessageの割当を分離し、エラー文の再割当でResult方針を破らない。故意のallocation fault injectionを未実施のまま成功と報告しない。どの失敗も入力・World・時計・他snapshotに副作用を持たない。

## 独立受入案

最初はNative/strictと範囲を明示したsanitizerを揃える。fixtureは全入力・settings・全leaf/audit・最後の実mesh結果と数値bitを持つstrict JSONとし、非有限・不正schema・切り詰めをrejectする独立checkerを別所有で作る。

1. 静止球、面上をparallelに移動するnear miss、逆向き経路、共有辺/共有頂点、離れた複数closest。既知の正marginで全leafを証明し、原本/ID/−0を保つ。順序反転が物理predicateを変えず、探索順/counterの一致は別に評価する。
2. 両端が外側でも途中を通る例：triangle A(0,0,0),B(4,0,0),C(0,0,4)、q0=(1,2,1),q1=(1,−4,1),r=1.5。両端はstrict separated、s=.5ではd=1<r。中点anchorが面上でないこの例はE込みのstrict witnessを解析確認する。世界での移動速度は入力しないため「高速度の力学CCD試験」とは呼ばない。
3. 接線・初期/終端接触・gap=0境界、非常に薄い正margin、巨大共通offsetとlost-low-term。非接触証明に届かないものを未認証とし、anchorをexact pathへ昇格しない。q0/q1を1秒未満へ再解釈する等の時間操作で受入を変えない。
4. 遠方/途中の退化面、conditioning/normal-width/candidate budget失敗、anchorのd=0失敗、64/65面、重複ID・NaN/Inf/域外。全source事前検査と実row failureを区別し、valid retry/過去結果所有/無変更を確認する。
5. evaluation=1、leaf=1、depth=0、sqrt予約不足、limited sqrt、最大partitionと末尾。[0,1]のgapless cover、certificate数と実query/candidate/sqrt和、未処理frontier、偽safePrefixを検査する。FP mode/FTZ/DAZ拒否後の復帰も含む。

独立な全区間Fraction参照は、時間標本の増量では代替しない。入力doubleをexact rationalへ戻し、各三角形について**feasible face projectionと3本のclamped edge（endpoint含む）**から、線分parameterごとの距離²の候補を作る。face barycentric/edge parameterのfeasible範囲はsの一次不等式で正確に切り分けられる。各有効rangeで距離²は有理二次式なので、両端と範囲内のstationary pointを調べ、全候補/全三角形の厳密最小を取れる。Native KKTのretained mask選択を再利用せず、各certified leafの最小distance²>r²と、各point witnessのdistance²<r²を独立に確認する。R/Eのsqrt上界は有理数の二乗比較でも監査する。

negative controlsは端点のみ/中点のみ安全から全成功を偽造、未被覆leaf削除/境界を1ulpずらす、右側certificateでprefixを飛ばす、R/Eを小さく改ざん、R/Eを0へ置換、witness parameter/upper-gapの改ざん、far failed rowの削除、source/ID/−0/個数/予算/未照会flagの変更を含む。原本と独立oracleの双方に照らし、0を含む境界を勝手に合格させない。

## 批判的レビューと残る限界

- **soundnessとcompletenessを分ける。** Lipschitz証明自体は任意anchorで有効だが、既存mesh::queryが要求する法線/条件/幅によって、真に離れた経路も未認証となり得る。すべての非接触経路で終了成功する保証はない。
- **Eを省くのは誤り。** 丸めanchorと厳密p(m)が異なる場合、d(c)<rだけではpathの貫通証拠にならない。Rも実path boxとの差から作り、単なる半線分長へ丸め誤差無しで置換しない。
- **三角形集合への全件照会は高価。** 最初は毎node全surfaceへ実queryし、退化した遠方の面も無視しない。broadphaseや距離専用核による改善は別のsoundness受入が必要で、現段では速度達成を主張しない。
- **予算は保守的。** 事前sqrt予約は上限遵守と引き換えにfalse unresolvedを増やす。後からpost-call overshoot方式へ変えるならbudgetの意味/上限・raw diagnosticsを別途変更し検証する。
- **failure counterの完全性は自動で得られない。** 既存sqrt内部のthrowは返却countを持たない。成功queryの正確な実countと、例外blockの予約によるwork上界を分ける。未返却分を0扱いして追加callへ予算を再利用しない。
- **点witnessはTOIではない。** 区間のentry/exit根・同時接触・残時間・荷重・衝撃は求めない。既存Worldへ付けただけで一般mesh CCDが完成するとはしない。
- **有限corpusと証明構成は別。** Fractionの解析受入は有限入力の独立比較で、任意入力の安全性の根拠は各Interval演算・三角不等式・全被覆条件に置く。新しい外部研究/実装/素材やSDK ABI変更はこの設計段階で追加しない。

正式header/enumと所有snapshot・fixture schemaに基づき、Native純粋核と独立参照を実装・検証する。SDK・手動trajectory UI・World結合・ゲーム接触はその後の別受入とする。
