# 定義線分guardの共有SDK接続案

2026-11-04 JST。**C ABIと実WASM raw wireをローカル受入、JS所有decoderは未実装**。有界交換はSPHERE_TRIANGLE_MESH_TRAJECTORY_ABI.mdと正式headerに固定した。現80-export SDKはraw C ABIに対応し、使いやすいJS APIへの接続を次段にする。以下は全段の設計と受入条件である。数学・work上限は `SPHERE_TRIANGLE_MESH_TRAJECTORY_PLAN.md` と正式headerを継承する。

## 所有と入力

既存mesh stagingと別にmodule内に専用stageを一つ持つ。begin(0..64)→append(1..6面、ID+ABC9の10..60値)→query。65枚以上・不正chunk/ID/非有限・未begin/不足/超過はhost拒否。全chunk検査・候補copy後に交換し、部分追加しない。重複ID・有限domain違反・0設定等は実Nativeが判定する。

query入力は24 F64案。意味値19は次の通りで、残り5はreserved +0。

```text
start3, end3, radius,
mesh.maxSurfaces,
primitive[maxCandidates,sqrtRefinements,maxTotalSqrtRefinements,
          maximumLocalWidth,maximumNormalWidth,minimumSineSquared],
guard[maxEvaluations,maxLeaves,maxDepth,enclosureSqrtRefinements,
      maxTotalSqrtRefinements], reserved0*5
```

個数/整数設定はuint32交換域全体を検査し、Native-invalid値も渡す。NaN/Inf/非整数/整数域外/予約違反は呼出し前後でhost拒否。座標abs<=1e12、r>0等をJSだけで代替分類しない。JSは全入力を一度所有copyし、それだけをchunk化する。

stage、committed record、Native.snapshotを区別する。valid begin/appendは旧record/outputを、全拒否は旧stage/record/output/countを保持。queryはecho/source/全packetの有限性・整合を検査し、nothrow move/swap後に一回publishする。正常交換のモデル失敗は新failure recordへ置換。割当失敗保証はcommit順を監査し、未実施fault injectionを主張しない。

recordはoriginal echo/sourceを所有。snapshot:nullでもechoは読め、有りなら全settings/endpoint/source bits一致を検査する。後のstage/caller編集で旧recordを変えず、single/mesh/光学/motion/skin/derived/World/timeとも独立。global resetで専用stage/recordを消去する。

## 64 F64内のpacket群

6exports/名前/offsetはNative probeで固定済み（正式headerとABIガイド参照）。begin/append/query、record(kind,index)、last_mesh(part,index)、candidate(row,index)でABI1/出力64/既存signatureを保つ。以下の表はJS decoderへ保持すべき情報の契約であり、正式wire長/offsetはheaderを正とする。

| packet | 上限/必要な情報 |
|---|---|
| query header <=64 | status/reason、original数、snapshot/current/witness/prefix/lastMeshの有無、failedIndexのflag/value、leaf/frontier/audit数、lastMeshAuditIndexのflag/value、Work11、partitionLeaves/maximumDepth、safePrefix2 |
| original echo24 | query24の全値。Native snapshot settingsの有無と別所属 |
| original source14 | ordinal/ID/ABC9=11値＋3flags。全64面を元順・全bitsで取得 |
| audit64案 | ordinal1+Cell3+midpoint1+outcome1、optional pathBounds7/pointBounds7/anchor4、meshQueried1、meshStatus/Reason各flag+value4、7個のoptional interval各3=21、Work11。計61、残り3padding |
| certified leaf6 | Cell3、lowerGapCertificate2、auditIndex1。最大128件 |
| frontier4 | ordinal1+Cell3。未照会を最大33件。currentとは別 |
| current4案 | 専用ordinal0+Cell3。有無はheader、存在しないgetterは拒否 |
| witness18以下 | Cell3/parameter1/exactPathBounds6/anchor3/errorUpper1/upperGapCertificate2/auditIndex1、有無を示す枠1以内 |
| lastMesh summary24 | 既存mesh headerの配置/enum/count/optional nearest/workを別recordから返す |
| lastMesh row58 | 当該行の全geometry/診断prefix情報。最大64行 |
| lastMesh candidate13 | 当該実行行の最大7候補、unused KKT符号零を保持 |

auditの7 intervalはdistance、displacementSquaredBound、errorSquaredBound、displacementRoot、errorRoot、clearanceCertificate、penetrationCertificate。Rcellを球radiusと呼び替えない。Work11はmeshQueries/primitiveQueries/candidatesExamined/primitiveSqrtRefinements/enclosureSqrtRefinements/sqrtRefinements/sqrtRefinementsUpper/meshSqrtLimitedRows/enclosureSqrtCalls/enclosureSqrtLimitedCalls/workExact。

source14の末尾flagsは既存mesh source helperの形を利用可能だが、**lastMesh**のhasRow/hasQuery/isPossibleNearestであると明記する。経路全体のnearestを捏造しない。lastMesh:nullなら全0。原本source自体は常にoriginal echoの所属で、Native.snapshotの存在はheaderで別に検査する。全lastMesh row.triangleはoriginal sourceとbit一致するため再利用できるが、省略/別行/再計算で代用しない。

lastMesh helperは専用recordを参照する純粋packet生成だけを共通化し、既存mesh/single snapshotへ一時代入してgetterを呼ばない。null queryはflagsで確認して行getterを呼ばず、miss扱いしない。lastMeshAuditIndexで最後の返却callへリンクし、後の未照会currentへ取り付けない。

## decoderの成功条件

能力検出は全新exportsに対してinput書込前に行う。旧74-export SDK、欠損exports・loader失敗は明示拒否し、単一mesh照会やJSの幾何計算へfallbackしない。getter不正kind/index/末尾/不在optionalは旧record/outputを保持する。packetは毎回正確な長さ・finite・整数count・0/1flag・enum/予約・optional整合を監査後に所有copyする。不在payloadは+0、原本と実intervalの−0は別で、unused KKT[-0,+0]を消さない。

設定maxEvaluationsは1024まででも、128葉の二分木で実audit/mesh callは最大255。source64、leaf128、frontier33、current/witness/safePrefix各optional、最後のmesh全64行/全候補を切り詰めない。件数、audit delta/global Work、lastMesh workを照合する。

separatedはclosed leafが[0,1]を穴なく覆い、全lower certificate>0かつworkExact=trueの場合だけ。safePrefix:nullをs=0の安全へ変えない。current/frontierは未認証/未照会であり、partial葉を全成功にしない。strict witnessはE込みupper certificate<0、parameterとauditの一致を要求する。各certificateは下界式/上界式の包含であり、真のgapの両端pairではない。

workExact=falseでは返却済み既知workと保守上限を別に保持する。既知workが時系列prefixとは限らない。未返却sqrt blockを0とせず、予約上界を次callへ再利用しない。例外時の実保持診断を超えるquery/geometryを捏造せず、全DTOを取得・整合監査してからJSへ返す。

## 実装順と受入

Native staging/C ABI/strict probeと固定SDK build/raw Native-WASM交換を先に受入済み。次はJS owned decoderと全DTO照合へ進む。固定62入力は65面/ID0/unsafe IDの3件がhost拒否、残59モデルとして実行確認した。入力/Source/settings/全wire numeric bits・DTO型/所有を照合し、WASM由来fixtureも独立Fraction全経路最小・R/E・被覆・負例へ通す。Native guard69群・62入力・数学self14/負例71と、未来の交換検証件数を混同しない。

最大128葉/255auditと末尾、64source/lastMesh最終行7候補、127葉失敗prefix、Eが偽witnessを防ぐ例、source/preflight/primitive/各予算失敗、nullsを再生する。全chunkと不正末尾・再試行、旧record/output/count保持、invalid getter/reset・他snapshot/clock独立、caller/scratch/旧DTO編集分離を試す。workExact=falseの例外枝は実注入しない限り未検証と記録する。strict環境とsanitizerはinstrument対象/未完を区別する。

C ABI/raw段でSDK80exports/59source-headerを実測し、manifest/新WASM bytes/hash・runtime linked member・全license notice/source差分をbuild後に監査した（ABIガイド/検証記録）。今後の変更でも同じ実測監査を継続する。既設依存のmember増加も「依存不変」で隠さない。公開CI/Pages/配信byte/ブラウザ受入は後段で、この計画の保存をその成功としない。

定義線分のread-only guardまでで、UI/World/TOI/response/ゲーム接触は未接続。他physics支流・IK/制御・高精度撮像の未完scopeを維持し、新素材/package/ライセンス選定は追加しない。
