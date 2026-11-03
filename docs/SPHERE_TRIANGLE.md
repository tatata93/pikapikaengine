# 球と静的な両面三角形の距離を囲む

2026-11-04 JST。**Native-onlyの純粋照会をローカル受入**。Native/ASan各126群、32CTest/Node496skip0、113入力中の成功88例の独立有理数参照と23改ざん負例を確認した。公開Linux CI/Pagesは統合報告で別に確定する。[受入案](SPHERE_TRIANGLE_PLAN.md)のNative段階を実装し、主SDK、ゲームのmesh衝突、Worldの接触生成へはまだ接続していない。

## 1枚の有限面を調べる

world-spaceの球中心xと半径r、元頂点順を持つ静的三角形A/B/Cを受ける。三角形上の最近接点qは、三角形の内部と境界を含めて `|x-q|²` を最小にする点である。無限平面への投影が三角形外なら、辺や頂点を調べなければならない。

```text
d = |x − q|             距離 [m]
gap = d − r            球と薄い三角形の符号付きclearance [m]
n = (x − q) / d        三角形から球中心への単位方向
sphere_point = x − r*n 法線方向に定義する球表面の参照点 [m]
```

gap<0は球の領域と薄い三角形の重なりを表す尺度であり、集合間の非負距離や、閉固体の内部までの侵入深さと同じではない。重なっているときのsphere_pointを実際の三角形との交点と呼ばない。面は両面で、三角形のcross法線を固定接触法線として使わず、裏側でもqから中心へ向ける。元の頂点順とstable surface IDを保存する。

例として三角形 `(0,0,0),(4,0,0),(0,0,4)` と中心 `(2,3,-4)` では、qは `(2,0,0)`、d=5m、n=`(0,3/5,-4/5)`。r=4mならgap=1mで分離する。同じ中心から無限平面y=0までの距離3mだけで判定すると誤って重なりにできる。中心 `(-3,4,0)` の頂点側もq=`(0,0,0)`、d=5mである。これらの解析例を有限の試験と独立参照へ照合した。全入力の精度や専門シミュレータの完成を示すものではない。

## 原入力から、否定できない候補をすべて残す

有限binary64入力を指定された正確な点値として扱い、既存の外向きInterval演算で差・係数・barycentric・最小条件を囲む。面1、辺3、頂点3の全7候補を調べる。各候補について三角形の範囲や必要な最小条件（KKT）の違反を証明できた場合だけ除き、否定できない候補を全部保持する。

残る候補のbarycentricと局所qをhullし、実際の最近接点を落とさない包含から距離・gap・法線を求める。保持候補のすべてが真の接触点だと断定したり、最も都合のよい候補だけを選んだりしない。候補監査は診断であり、多点contact manifoldの生成ではない。区間の中点や点近似を保証済みのq/nへ置き換えない。

面と辺などのfeature名が同率でも、共有する最近接点の法線まで不定になるとは限らない。一方、d=0なら `(x-q)/d` は定義できず、任意の三角形法線をfallbackしない。距離の正性や局所/法線の幅の証拠が不足する場合も、成功geometryを返さない。

## Native API

確定headerは [sphere_triangle.hpp](../core/include/pikapika/sphere_triangle.hpp)。名前空間は `pikapika::sphere_triangle`。

```cpp
Result query_sphere_triangle(
    Sphere sphere,
    const StaticTriangle& triangle,
    const Settings& settings = {});
```

`Sphere` は既存のcenter/radius、`StaticTriangle` はstable `id` と元順序の3頂点。座標と半径は有限で絶対値<=1e150、radius>0、surface IDは1..2^53−1。入力域に入るだけで計算の表現可能性や品質が保証されるわけではなく、途中の非有限・悪条件・証拠不足を失敗として分ける。strict FPと環境条件は既存 [Interval契約](INTERVAL.md)に従い、callerの丸め方向やFTZ/DAZ等の制御modeを変更しない。probe/演算による例外flagやerrnoの保存は保証しない。

| Settings | 既定 | 許容範囲・意味 |
|---|---:|---|
| max_candidates | 7 | 1..7。成功には全7候補の検査が必要で、未検査候補を捨てない |
| sqrt_refinements | 128 | 1..256、平方根endpointごとの更新予算 |
| max_total_sqrt_refinements | 1024 | 1..1024。平方根の1呼出し後に実更新数を監査する総予算 |
| maximum_local_width | 1e-7 m | 正かつ<=1e6 m。closest_localとdeltaの成分幅の上限 |
| maximum_normal_width | 1e-8 | 無次元、正かつ<=2。normalの成分幅の上限 |
| minimum_sine_squared | 1e-12 | 正かつ<=1。辺AB/ACの角度のsin²による条件検査 |

これらは品質/予算の条件で、gapを接触扱いにする有限contact bandではない。小さいgapを都合よくzeroへ丸める仕様でもない。sqrt予算は呼出しを途中で強制停止するタイマーではなく、最大2*sqrt_refinementsの更新を行い得る1呼出し後の監査である。

巨大な共通平行移動の影響を局所差で抑えるため、`closest_local=q-A` と `delta=x-q` を局所で作る。world qを戻す加算では区間が広がり得る。**maximum_local_widthはworld qの幅を制限しない**。sphere_pointのworld座標にも局所幅の保証を無断で広げない。

## 結果と失敗の読み方

`Result` はstatus/reason、optional geometry、候補監査、cross²/sin²のoptional区間、検査/平方根の件数、refinement limitedとmessageを持つ。geometryはcompleted時だけで、失敗の診断prefixから部分的な成功geometryを作らない。

- `Status`: completed / invalid_input / degenerate / ill_conditioned / quality_unresolved / budget_exceeded / numerical_failure / unsupported_environment。
- `Geometry`: surface_id、surviving_featuresのbit mask、barycentric、closest_local、world closest、delta、normal、sphere_point、squared_distance、distance、gapとrelation。位置[m]、距離²[m²]、normal/barycentricは無次元。
- `CandidateAudit`: feature、retained/outside_simplex/kkt_violated、clip前のbarycentric包含、必要なKKT residual（面0/辺1/頂点2）。保持候補のaccepted hullでは各barycentricを[0,1]と交差する。
- surviving_featuresは保持したfeatureの候補集合であり、一意なfeature確定や複数の物理接触点を示すbitではない。

relationはgapの下限>0ならseparated、上限<0ならpenetrating。計算したgapの両端が0（±0は同値）の場合だけtouchingとし、それ以外の0を含む区間はboundary_unresolvedとする。有限bandや不明な接触をtouchingへ昇格しない。completedは最近接幾何/法線の包含と幅品質が成立したことを示し、relationがboundary_unresolvedでもgeometryを返し得る。逆に距離²の下限が厳密に正と確認できない場合は、geometryを出さない。失敗reasonは入力/設定、crossや条件検査、候補予算、局所幅、zero distance/距離未確定、sqrt予算、法線幅、非有限/割当/環境を分ける。

## ローカル検証と境界

Native/ASan各126群には解析例、winding/裏面/全頂点順・剛体変換、巨大共通offset、feature/gap境界、退化/近退化、予算・失敗後再利用がある。113入力の88成功・25明示失敗を記録し、成功88例の1848参照成分を独立Fractionへ照合した。参照はfeasibleな面内解と3本のclamped edgeから厳密な最小を選び、距離・法線・球表面点を有理数の平方不等式で検査する。libm/Decimalのsqrt精度に依存せず、候補の除外証拠と全保持bitも確認した。記録の23改ざんを拒否し、case名と順序を変えても同じ集計になる。

既存point impulse solverとの接続10群は、既知q/nの解析例のコピー候補だけで反発速度・energy・角impulse、摩擦、異方慣性の既存平面とのbit一致を比較した。一般の区間結果をmidpoint化して点solverへ無条件に渡す受入ではない。全Native 32CTestとNode496skip0が成功し、主SDKと原本assetはbyte不変。[生出力と統合報告](../reports/2026-11-04-sphere-triangle.md)で公開受入を別に確定する。

幅の閾値判定も通常doubleの減算ではなく、外向きの減算上限を使う。丸めた幅を閾値にすると真の幅が約1e-323だけ超過する境界例を拒否する回帰を含めた。これは全位置/法線が正確な点値という主張ではなく、返す包含と明示品質の契約を守るための検査である。

これは瞬間のread-only照会で、入力・World・時刻・荷重・姿勢を進めない。主SDK/ゲームの制作mesh衝突は未接続。時間方向のCCD、動く三角形、閉固体の内部/外部、隣接三角形の内部辺・manifold、摩擦支持、流体・材料損傷はこの段階で完成していない。既存の球/平面のCCDやW2軌道監査も、自動で三角形へ対応したものにはならない。

## 読取した一次資料

David Eberly, [Distance Between Point and Triangle in 3D](https://www.geometrictools.com/Documentation/DistancePoint3Triangle3.pdf)、2020-09-11改訂、Geometric Tools。2026-11-04 JSTに§1–2の最小化定式化と境界上の扱いを実読した。著者PDFのCC BY 4.0表示を確認したが、文献本文・図・実装codeは転載しない。全否定不能KKT候補を区間で保持する方式はこのプロジェクトの独自実装で、文献の点値分岐codeやdeterminantを絶対値化する処理を移植しない。ライセンス表記を、未選定のエンジン本体ライセンスへ置き換えない。
