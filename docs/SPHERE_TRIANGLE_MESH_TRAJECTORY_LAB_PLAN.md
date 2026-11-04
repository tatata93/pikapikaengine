# 定義線分guardの手動ラボ: 次の有限受入案

2026-11-04 JST。**実装前の受入設計。現在は[実装ガイド](SPHERE_TRIANGLE_MESH_TRAJECTORY_LAB.md)のローカル受入を完了し、公開を確認する段階**。後続の所有JavaScript API公開受入後に、線分経路全体の証明・点witness・未認証と、全所有診断を操作して保存する最小UIを作る。新しいURL案は `tools/sphere-triangle-mesh-trajectory-lab.html` だが、現在動くリンクとして案内しない。既存の瞬間meshラボは保存し、このUI段階でC++核・共有SDK artifact/ABI・ゲーム原本を変更しない。

## 実計算への入力

原本入力は `{start:[3],end:[3],radius,triangles:[{id,vertices:[[3]x3]}],settings:{mesh:{maxSurfaces,primitive:{6設定}},maxEvaluations,maxLeaves,maxDepth,enclosureSqrtRefinements,maxTotalSqrtRefinements}}` とする。既存strict JSONでduplicate key・非有限・不正Unicodeを拒否し、signed zeroを保存する。sourceの予算案は64KiB/depth12/12000nodes。省略設定は既存API既定値を明示して補うが、低予算・品質条件を成功しやすい値へ自動変更しない。

実 `runtime.querySphereTriangleMeshTrajectory` を一回呼んで完全DTOを得る。UI側で距離・Lipschitz境界・R/E・平方根・KKT・接触分類を再計算せず、瞬間mesh照会や標本点だけの成功で代替しない。65面例はhost拒否を見せる入力として許しても、64面へ切り詰めない。finiteな域外座標/半径・整数設定0などのモデル入力を、UI独自の物理判定でhost拒否へ変えない。

入力形式拒否、SDK/loader失敗、host交換拒否、実モデルの失敗/未認証を別表示する。未照会にstatusや成功結果を捏造しない。単位はm、parameter sは無次元で、時刻・速度・移動後の真の力学状態を入力したUIにはしない。

## 全体結果と全partitionを読めること

先頭に実status/reason、入力検査位置、snapshotの有無、`safePrefix`、witness、最大depth/partitionLeaves、全Workを表示する。`separated` だけを全経路のstrict非接触とし、点witnessをTOI/最初の衝突・全経路貫通・応答許可とは呼ばない。`not_certified` をmissや安全へ変更しない。prefix:nullを0と表示してs=0の安全を装わず、prefixがあっても残区間を捨てない。

| 所有診断 | 表示と容量の受入 |
|---|---|
| originalInput / snapshot | 原入力はsnapshot:nullでも保持。endpoint/全設定/全source/echoと、Nativeの完全snapshotの所属を区別する |
| certifiedLeaves | 最大128件、closed bounds・strict lower-gap certificate・auditIndex。末尾127を閲覧可能にする |
| audits | 最大255件、元の評価順・cell/depth/midpoint/outcome、optional path/point/anchor、実mesh照会の有無/status/reason、距離・R/E・二certificate、delta Work。末尾254を閲覧可能にする |
| current / frontier | 評価済み/予算停止の現在cellと、まだqueryしていない最大33cellを別欄に置く |
| witness | parameter・厳密なpath点のbounds・任意anchor・E上界・strict負のupper式・auditIndexを省かない |
| lastMesh | 最後に返った実mesh結果とlastMeshAuditIndexを示す。全64source/実row/候補prefixと最後の最大7候補を閲覧可能にする |

auditやsourceの選択は閲覧であり、新しい照会/nearestの確定ではない。選択した未照会cellに、以前のlastMeshを結び付けない。lastMeshが選択auditのものではなければ所属先を明示し、null query・失敗行・後続行・nearest:nullを保持する。実source一覧は常に元順で、実rowの有無は区別する。

`work.workExact=false` の場合は返却既知workとsqrt保守上限を別に表示し、予約を実使用件数や完全実測へ変換しない。人工DTOでこの表示を試す場合はdecoder/UIの試験と明記し、Native例外やallocation faultの実注入とは報告しない。各auditのdeltaと全体総計を混同しない。

## 2D投影とparameter帯

XY/XZ/YZ投影で入力の静的三角形・定義線分と、選択auditのpath box/point box・任意anchorを説明表示する。厳密なp(m)はpointBoundsであり、丸めanchorを厳密なpath点へ昇格しない。二つのcertificateは下界式/上界式の包含で、真のgap全体のpairとして描かない。離れた複数面の最近接点・法線・barycentricを一つに平均しない。

parameter帯は[0,1]、certified leaves、safePrefix、current、未照会frontier、点witnessを区別する。closedな共有境界と区間の未被覆を隠さない。表示上の丸め/線幅が証明を変えないよう、数値boundsを並記する。密な128葉はスクロール/選択で全件確認でき、見切れた末尾を欠落させない。

描画座標の有限性を別に検査する。巨大/域外入力や極小幅を有限の表示へ変換できなければ「説明図を表示できない」とし、モデル結果statusを変更しない。inkを最小pxへ拡大する場合は表示用と明記し、元DTO・数値bounds・保存dataを変えない。図の見た目をInterval包含やGPU/render精度の証明にしない。

## 編集、読込み世代、保存

入力/preset変更・reset・retry開始時には、旧証明葉・witness・lastMesh/候補・図・表示JSONと保存可能状態を即座に消す。旧結果のまま新入力の安全表示を続けない。projection/閲覧audit/source変更は同じowned結果の表示変更で、query件数を増やさない。

loaderの同時呼出しをcoalesceし、同期throw/rejected promise後に再試行できるようにする。世代をまたぐ遅延成功/失敗・dispose後の復活を拒否する。retry中は旧runtimeでqueryせず、旧74-export SDKや欠損6exportsでは明示失敗し、JS幾何fallbackを足さない。

保存案はschema1/kind `sphere-triangle-mesh-trajectory-lab`、完全な正規化input・実full result（originalInputとoptional snapshotを含む）・SDK diagnostics、projection/閲覧audit index/source ID。未照会・loader/host拒否をモデルpacketとして保存しない。実モデルのinvalid/not_certified/witnessもそのまま保存する。strict serializerの予算案8MiB/depth32/1000000nodesを監査し、表示の短縮が保存DTOを切り詰めないようにする。

実Blob downloadを発生させ、表示JSON・所有packet・保存bytesをstrict parseした全数値bits/−0が一致することを確認する。projection/選択はview fieldだけを変え、model DTOのbitsを変えない。

## 有限の受入手順

1. 既受入fixtureから、静止/parallel near miss・共有辺/頂点・順逆path/面順、途中strict貫通、exact contact、terminal-contact prefix、Eが偽witnessを防ぐlost-low-term、遠い/途中退化面と後続row、各予算停止、preflight、signed zeroをpreset候補にする。実採用数とブラウザでの結果は実行後に確定する。
2. 実64sourceの末尾と全ID、255audit/128leafの各末尾、127葉予算失敗の連続prefixと未処理区間をブラウザで検査する。これらは既受入Native入力のUI再生候補であり、ラボ受入を既に済ませたとはしない。
3. edit直後の全旧表示/保存状態消去、host拒否→修正→retry、モデル失敗後の成功/逆順、全input/source/settings/resultの別所有、projection/閲覧変更でquery不増加、実Blob保存を試す。loader coalescing/遅延世代/同期throw/rejection/disposeは専用Node/DOM試験も用いる。
4. 実UIから得たfull DTOを同じ80-export SDKの直接呼出しと全数値bits比較する。独立Fraction checkerのpin62を緩めず、新操作入力の受入が必要なら別の明示corpus契約を設計する。59 ownedモデル＋pure補足3という先行mixed参照の出自を保持し、UI追加例やhost拒否まで全て実WASM数値結果と呼ばない。
5. 専用UI試験、全Node/構文/Web build、既存SDK/native回帰、実ローカル/公開ブラウザ、公開CI/Pagesと配信byte照合をそろえる。SDK artifact・C++/ABI・ゲーム原本のbyte不変を確認し、操作画像だけで数値/保存/例外受入の成功を代用しない。

原著図/教材25記事・研究/法務台帳を更新するが、新依存・外部素材・有料service・本体ライセンス選定は不要。World/一般CCD/TOI/接触応答・ゲーム適用、流体/損傷・専門モデル/IK/制御/高精度撮像の未完scopeを維持する。
