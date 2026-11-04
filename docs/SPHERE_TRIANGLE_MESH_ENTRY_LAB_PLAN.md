# Entry-windowの手動ラボ: 次の有限受入案

2026-11-04 JST。**UI実装・公開受入済み（263d531）**。以下は実装前に定めた設計で、現在地と実測は[ラボ契約](SPHERE_TRIANGLE_MESH_ENTRY_LAB.md)と[検証記録](../reports/2026-11-04-sphere-triangle-mesh-entry-lab.md)を優先する。所有JS APIはコード578895dで公開受入済み。次はこの手動UIを実装する。[所有API案](SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md)と[正式raw ABI](SPHERE_TRIANGLE_MESH_ENTRY_ABI.md)を使い、既存trajectory guardラボと別の手動入口を作る。URL案は `tools/sphere-triangle-mesh-entry-lab.html`。現時点で動く起動リンクとは案内しない。C++核・86-export SDK/61原本・artifact・既存ゲームはこのUI段階で変更しない。

## 入力と一回の実計算

原入力は `{start:[3],end:[3],radius,triangles:[{id,vertices:[[3]x3]}],settings:{mesh:{maxSurfaces,primitive:{6設定}},parameterTolerance,maxEvaluations,maxLeaves,maxDepth,enclosureSqrtRefinements,maxTotalSqrtRefinements}}`。strict JSONでduplicate key・unknown key・非有限/overflow・不正Unicodeを拒否し、signed zeroを保存する。入力予算案は64KiB/depth12/12000nodes。省略設定は実API既定へ補完するが、低予算や品質条件を自動変更しない。tol既定1e-6、評価256/全partition128/depth24、enclosure128/全sqrt1000000を明示する。

実 `runtime.querySphereTriangleMeshEntry({start,end,radius},triangles,settings)` を一回呼んで完全なowned DTOを受け取る。UIに距離・sqrt・KKT・Lipschitz境界・Interval・接触solverを実装しない。瞬間mesh query、標本点の安全、旧guardやJS計算へのfallbackを使わない。座標/半径/距離はm、global parameter sと窓幅は無次元。時刻・速度・力学の真の軌道ではない。

初回load・preset選択・reset・明示retry後は、現在の入力がその世代で未編集の場合だけ自動一回queryする案とする。通常のinput編集後は旧結果を消し、実行操作で照会する。閲覧・projection変更ではqueryを増やさない。実行回数を試験で監査し、連続再生で未認証を隠さない。

空集合・重複ID・有限域外・半径0・uint32設定0等はモデル結果へ渡す。65面/ID0/unsafe ID/非整数設定などのhost拒否例はそのまま表示し、切詰めない。JSON形式拒否、loader/能力拒否、host交換拒否、モデルstatusを別段階として表示する。旧80/欠損6exportsでは入力書込前に明示拒否する。

## 結果の意味と完全な所属

| status | 表示契約 |
|---|---|
| entry_window | 初期strict正・closed安全prefix・E補正strict負witness・外向き窓幅・exact Workを揃えた開始窓。単一根/正確なTOI/接触面ではない |
| separated | 全closed [0,1]のstrict非接触被覆。端点や有限標本だけの安全ではない |
| initial_penetration | s=0のstrict負。新規entry窓はない |
| not_certified | 境界/接線/品質/予算等で証拠不足。missや安全に変えない |
| invalid_input | モデル入力拒否。host交換拒否と区別する |
| unsupported_environment / numerical_failure | 環境拒否/計算失敗。部分診断を成功結果として表示しない |

結果の先頭には実status/reason、failedIndex、snapshot有無、initialSeparationProven、safePrefix、windowのL/Uとwidth、tol、bestWitness、最大depth/partitionLeaves、Work全11項目を表示する。`safePrefix:null` と `[0,0]` は異なる。後者は初期点のstrict正のみでも成立し、正の長さのcellを証明したとは限らない。windowの候補IDは全sourceの昇順保守集合で、lastMeshのnearest IDsへ縮めない。

| 所有物 | 閲覧・保存の受入 |
|---|---|
| originalInput / snapshot | snapshot:nullでも原echo24・全設定・全sourceを保持。整数設定の原−0とsnapshotの正規化+0を分ける |
| initial / audit0 | initial_pointのcell[0,0]/parameter0・両certificateを独立表示。初期query失敗のinitial:null/current[0,0]を落とさない |
| audits | 初期点込み最大256、元BFS順、kind/cell/depth/parameter/outcome、全optional bounds/anchor・mesh状態・距離・R/E・certificate・delta Work。末尾255を閲覧可能にする |
| certifiedLeaves | 最大128の全証明島、cell/certificate/auditIndex。prefixの後方も残す |
| partition | 最大128の全closed被覆、state/auditIndex/blockedReason。未照会tailを含む |
| frontier / current | 全unqueried最大128と停止cellを別表示。旧DFSの33件上限を流用しない |
| bestWitness / window | witnessのexactPathBounds・任意anchor・E・strict負式・audit所属、windowの両端/外向き幅を省略しない |
| lastMesh | lastMeshAuditIndexと全64source/実row/null query/全候補最大448を保持。選択auditとは別の所属であることを示す |

audit・面の選択は閲覧である。選択auditがlastMeshAuditIndexと一致するときだけその幾何を重ね、一致しなければ「最後の返却meshは別audit」と示す。未照会面/未返却queryへ古いgeometryやstatusを代入しない。row_failure ancestorを表示しながら子cellの別証拠でwindowが成立する例を確認する。source順、全候補prefix、保守ID集合、未知と欠落の区別を保存する。

Workの既知refinement数、保守upper、workExactを別欄に置く。unknown blockの予約を実使用回数や0へ変換しない。各auditはdelta、全体は総計。人工Workfalse/初期allocation DTOのUI試験は表示試験と明記し、実Native例外注入とは呼ばない。

## 説明図とparameter帯

XY/XZ/YZに入力三角形・元線分と、選択auditのpath/point box・任意anchorを説明表示する。丸めanchorを厳密p(s)へ昇格しない。certificateは下界式/上界式の包含であり、二つを真のgap範囲として描かない。面ごとの法線/barycentric/closestを平均しない。

帯には全[0,1]、全partition state/blocked reason、全証明島、連続prefix、initial点、bestWitness点、entry window、currentと未照会tailを分ける。負witnessがあるだけの未認証と、窓が受理された場合を混同しない。幅広許容の窓も実L/U/width/tolのまま示す。数値boundsを常時併記し、最小1pxなどのink拡張は表示専用と説明する。

巨大座標・縮尺・極小帯を有限な描画値へ変換できなければ「説明図を表示できない」とし、数値packet/status/保存を変更しない。図はInterval包含・世界座標/GPU精度・性能の証明ではない。

## 編集・loader世代・保存

入力変更/preset/reset/retry開始は旧summary・initial/window・帯/葉/audit・lastMesh/候補・JSON・保存可能状態を即クリアする。projection/閲覧変更は所有packetのviewだけを変更する。loaderをcoalesceし、同期throw/rejected promiseから再試行でき、retry開始時には旧runtimeを無効にする。入力編集・二重retry・disposeをまたいだ遅延callbackで旧結果を復活させない。dispose後のhandler/保存を無効化する。

module API案は `entryLabPresets`、`entryLabPreset`、`parseEntryLabInput`、`evaluateEntryLab`、`serializeEntryLab`、`entryProjection`、`initializeSphereTriangleMeshEntryLab`。DOM案はprefix `entry-`、既存trajectoryラボ相当のstatus/error/retry/controls/preset/source/query/reset/save/runtime/note/projection/view/summary/audit/inspect/audits/leaves/partition/timeline/rows/geometry/candidates/json。初期証拠とwindowには専用pre欄を追加できる。正式ID/exportは実装開始時にUI/test担当間で固定する。

保存はschema1/kind `sphere-triangle-mesh-entry-lab`、補完済みinput・実full result/originalInput・SDK diagnostics、viewのprojection/inspectedAudit/inspectedOrdinal。空一覧の選択はnullとし、存在しないordinal0を実診断にしない。未照会やloader/host拒否をモデルpacketへ偽装せず、実モデルの失敗packetは保存する。strict serializerの8MiB/depth32/1000000nodes案は最終LFを含め監査し、超過時は明示拒否・切詰め禁止。実Blob保存と表示JSONをstrict再読込し、全数値bits/−0/optionalがowned packetと一致することを確認する。

## 最小の有限受入

1. frozen65のinputをbit単位で再現する約25代表presetを原著moduleへ定義し、fixtureNameで出自を記録する。静止/near miss、解析quarter/reverse、対称中点法線失敗から回復、複数entry/面順逆、幅広tol/厳しいtol、初期負/境界/離反、接線/terminal contact、退化後続面、sqrt予約、signed zero/lost-lowを候補とする。実採用件数は実装時に固定する。
2. actual-256-audits-128-leaves、breadth-frontier-budget、actual-64-entry-all-conservative-ids、127leaf/255評価予算、host65は必須候補。最大末尾255/127/63、全IDと全未照会tail、prefix後方の証明島、lastMesh別所属を実操作で確認する。全例成功を要求せずstatus内訳を実測する。
3. 実86-WASMの同入力直接APIと全DTO型/keys/bits/負零を照合し、UIの出力/実Blob再読込と一致させる。固定65/独立Fraction/90負例は既存pinを緩めず維持する。host補足を含むmixed corpusは各行出自を記録し、UIの全入力を実モデル計算と呼ばない。
4. Node実SDK/DOMで編集即消去、input/result/callerの別所有、query件数、投影・閲覧query0、loader coalescing/同期throw/rejection/遅延世代/dispose、失敗後復帰、全capacity・厳密保存予算を試す。人工packet表示のscopeを分ける。
5. 全Node/構文/Web、既存SDK/数学回帰、C++/SDK/assets/game原本の不変、実ローカル/公開ブラウザ、公開CI/Pages/配信byteを別の証拠として揃える。初回失敗rawも保持する。実装前の本計画や操作画像だけを公開成功としない。

新依存・外部素材・課金は追加せず、本体license未選定を維持する。手動entry参照UIはWorld・一般CCD/TOI応答・manifold/反力やゲーム衝突への接続ではない。一般物理、流体/損傷、専門車両・航空・鉄道、IK/制御、高精度撮像と未実行fault注入の残件を維持する。
