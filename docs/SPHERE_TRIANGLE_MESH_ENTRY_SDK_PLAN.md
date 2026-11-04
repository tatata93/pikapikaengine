# Entry windowの共有SDK接続案

2026-11-04 JST。事前設計の履歴。raw C ABI/実WASM交換をローカル受入済み（専用24群・38CTest/586Node、62model3host・全wire bits一致）。コード4b03f0cの公開GNU/Pagesも全工程成功。[正式ABIガイド](SPHERE_TRIANGLE_MESH_ENTRY_ABI.md)参照。以下のJS所有decoder/UI段は未実装で、[次段計画](SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md)へ分離した。数学契約は既受入Native核を継承し、World/TOI/応答やゲーム接触は未接続。

## 現物と独立した所有

現manifestを読み、80 exports、29翻訳単位、hash対象59 source/header、7通知、linked runtime member91、2 artifactを確認した。ABI1、F64入力49,152/U32入力98,304/出力64、初期memory64MiB/最大256MiB/stack1MiBを維持する。現WASM674,978B/SHA256 `5f3c633b0f4a209ad07dc8fb3f847d496e0264ecf0ca1eb7667dd38deac0b0e7`、glue56,289B/SHA256 `25dad6ad39c0734d172dd2fee7937a5b33af235a26868dfd2af1954929c72855`。この読取り確認は新能力の実行検証ではない。

新entry専用stageとcommitted recordを各1つ持つ。既存single/mesh/trajectory/光学/motion/skin/derived/Worldのrecord、stage、時計へ一時代入しない。resetは新2所有物も消去する。module共有scratchを使う同期・非再入APIとし、公開ポインタは解放せずmemory growth後にviewを再取得する。

追加6 exports案は `pp_sim_sphere_triangle_mesh_entry_begin(n)`、`_append(count)`、`pp_sim_sphere_triangle_mesh_entry(count)`、`_record(kind,index)`、`_last_mesh(part,index)`、`_candidate(row,index)`。予定86 exportsであり、実装時に正式header/probeへ固定して実測する。

beginは0..64、appendはID+ABC9の10..60 F64（1..6面）。全chunk検査・候補copy後にstageを交換する。未begin/不足/超過/非有限/ID0/unsafe ID/不正chunkはhost拒否、旧stage/record/output/countを保持する。valid begin/appendも旧record/outputを変更しない。重複ID・有限domain外・設定0は実Nativeへ渡し、JSの幾何分類で代替しない。

## 入力24と候補record

query24の配置案は旧trajectoryの先頭19値を保ち、parameterToleranceを追加する。

```text
0..2 start, 3..5 end, 6 radius, 7 mesh.maxSurfaces,
8 maxCandidates, 9 primitive.sqrtRefinements, 10 primitive.maxTotalSqrtRefinements,
11 maximumLocalWidth, 12 maximumNormalWidth, 13 minimumSineSquared,
14 maxEvaluations, 15 maxLeaves, 16 maxDepth,
17 enclosureSqrtRefinements, 18 maxTotalSqrtRefinements,
19 parameterTolerance, 20..23 reserved +0
```

整数設定はuint32全域を交換でき、モデル無効値も渡す。NaN/Inf・非整数・unsigned域外・reserved−0は交換前に拒否。Nativeの座標/radius域±1e12m、正radius、tol∈(0,1]、最大256評価/128葉/深さ32等は核の判定である。

original echo24と全sourceを必ず所有する。Native snapshot:nullでも取得可能。有りならendpoint/radius/全source bits・全settingsを照合する。整数設定のNative正規化+0とechoの−0を区別する。queryは全packet/flags/range/finite/リンクを候補内で監査し、nothrow move後に一回publishする。正常交換のモデル失敗は新失敗recordへ置換し、交換・割当・packet監査拒否は旧record/outputを保持。割当fault injection未実施を構造監査の成功で置き換えない。

## 64 F64内の全packet案

以下は実装前の明示map。全countとpaddingを正式probeで固定する。不在getterは拒否し、別recordや別auditへfallbackしない。

header40:

```text
0 status,1 reason,2 sourceCount,3 hasSnapshot,4 hasFailedIndex,5 failedIndex,
6 hasInitial,7 initialSeparationProven,8 certifiedLeafCount,9 partitionCount,
10 frontierCount,11 auditCount,12 hasSafePrefix,13 safeLo,14 safeHi,
15 hasBestWitness,16 hasWindow,17 candidateIdCount,18 hasCurrent,
19 hasLastMesh,20 hasLastMeshAuditIndex,21 lastMeshAuditIndex,
22 partitionLeaves,23 maximumDepth,24..34 Work11,35..39 +0
```

| record kind | 長さ / 上限 | 全payload |
|---|---|---|
| 0 | 24 / 1 | 元query echo、index0 |
| 1 | 14 / 64 | ordinal,ID,ABC9,hasLastMeshRow,hasLastMeshQuery,isLastMeshPossible |
| 2 | 64 / 256 | 下記audit。初期点も1件として算入 |
| 3 | 6 / 128 | certified Cell3,lowerGapCertificate2,auditIndex。prefix後方の成功islandも全て |
| 4 | 8 / 128 | ordinal,Cell3,LeafState,hasAuditIndex,auditIndex,blockedReason。全partition |
| 5 | 4 / 128 | ordinal,Cell3。全unqueried frontier、bestU以後のtailも保持 |
| 6 | 4 / 1 | ordinal0,Cell3。optional current |
| 7 | 6 / 1 | ordinal0,initial lowerCertificate2,upperCertificate2,auditIndex |
| 8 | 18 / 1 | ordinal0,Cell3,parameter,exactPathBounds6,anchor3,errorUpper,upperCertificate2,auditIndex |
| 9 | 6 / 1 | ordinal0,L,U,widthBounds2,witnessAuditIndex |
| 10 | 2 / 64 | ordinal,ID。window時の全source ID昇順、未filterの保守候補 |

Cell3はclosed parameter両端とdepth。audit64は次の62意味値＋padding2で収まる。

```text
0 ordinal,1 kind,2 cellLo,3 cellHi,4 depth,5 parameter,6 outcome,
7 hasPath/8..13 Bounds6,14 hasPoint/15..20 Bounds6,
21 hasAnchor/22..24 XYZ,25 meshQueried,
26 hasMeshStatus/27 status,28 hasMeshReason/29 reason,
30 hasDistance/31..32 I,33 hasDisplacementSquared/34..35 I,
36 hasErrorSquared/37..38 I,39 hasDisplacementRoot/40..41 I,
42 hasErrorRoot/43..44 I,45 hasClearance/46..47 I,
48 hasPenetration/49..50 I,51..61 Work11,62..63 +0
```

Work11はmeshQueries,primitiveQueries,candidatesExamined,primitiveSqrtRefinements,enclosureSqrtRefinements,sqrtRefinements,sqrtRefinementsUpper,meshSqrtLimitedRows,enclosureSqrtCalls,enclosureSqrtLimitedCalls,workExactの順。各auditはdelta、headerは合計。0反復のroot呼出しも実callsから省略しない。

last_meshはpart0/index0でsummary24、part1で実row58、candidateは当該rowの13値を返す。全64行/448候補を所有し、null queryはsource flagsで区別する。source14末尾とlastMesh.nearestは最後のmeshだけの所属であり、entry面の同定ではない。lastMeshAuditIndexへ正しく結ぶ。旧pure packet helperはconst参照で再利用可、旧globalへの仮代入は禁止。

独立上限を全て足しても29,370 F64相当だが、一括packetや同時最大達成を意味しない。毎回最大64だけをpublish/所有copyする。Native fixture DTOが除外する可変人間向けmessage原文はこのwire案に含めず、status/reasonを診断本体とする。messageを空文字で復元したふりはしない。

## JS所有decoderの受理

将来method案は `querySphereTriangleMeshEntry({start,end,radius},triangles,settings)`。settingsはNativeと同形のmesh/primitive、parameterToleranceとguard5項目。全6能力を最初のinput書込み前に検出し、旧80-export SDK・欠損・loader拒否を明示する。fallbackは禁止。面数/ID/配列参照/数値を一度captureして全入力を検査・copyし、それからbeginする。

返却は新Native fixtureの全数学/所有診断keys、enum文字列化、追加`originalInput:{start,end,radius,triangles,settings,echo}`案。snapshotとoriginalInputも別所有。全packetの正確な長さ・dense finite・整数・flag0/1・enum・+0 padding・optionalを先に確認する。実interval/原本/unused KKT[-0,+0]のbitsは保存する。

初期kindはaudit0のinitial_point/[0,0]/depth0/parameter0だけ。通常partition cellは正の幅を持つglobal dyadic領域。初期停止時current=[0,0]はpartition内へ強制しない。initialProofの両certificate/所属、initialSeparationProven、安全prefix[0,0]の根拠を照合する。

全partitionは[0,1]を穴なく覆い、certified islands・unresolved/current・全unqueried tailを保持する。frontier上限を旧DFSの33へ下げない。幅優先/左順・eligible条件、LeafState/auditIndex/blockedReason、全work delta、lastMesh/linkを検査する。exact row_failure祖先はunknownのまま、子の実証拠だけで認証できる。初期失敗や未知workを0/successへ変えない。

windowは初期strict正、closed [0,L]strict被覆、E込みg(U)<0、Native幅包含upper<=tol、exact work、全ID候補との整合が必須。未知cellの幅や負witnessだけでは受理しない。初期負はwindowなし。separatedは全区間strict被覆のみ。JSは幾何・sqrt・Intervalを再計算しない。正常Native publish後のdecoder拒否はJS DTOを返さないが、Native recordのrollbackを約束しない。

## 段階的な未受入作業

1. Native C ABI/strict probeで新65原本を再構築し、host拒否とモデル実行を実測分類する。初期/全256audit・128partition/frontier・64source・islands/tail・bestWitness/window・全末尾/候補、exactfalse保守上限を欠落なく照合する。人工例外DTOと実fault injectionは分ける。
2. Native/WASM全wire bits、−0、echoとsettings、旧output/count/record保持、invalid getter/reset/他snapshot独立、caller/scratch/旧DTO分離を検査する。WASMから復元したDTOを独立Fraction参照へ渡し、pure補足があれば出自を明記する。既存guard62と新65を混同しない。sanitizer・警告・改ざん負例・旧全回帰を別記録にする。
3. build時に新hpp/cppを追加するためhash対象61 source/headerを予想するが、実数・WASM/glue bytes/SHA・memory高水位・全license通知・runtime member差分は再生成後に監査する。Emscripten固定版/既存依存も実member増加を測る。本体licenseは未選定、新素材/課金は追加しない。
4. JS所有API受入後に別UI段を作る。初期proof/正prefix/後方witness/全partition/blockedReason/全tail/lastMesh所属を閲覧・完全保存し、編集消去・loader世代・公開配信を検査する。UI/World/TOI/response・ゲーム接触や、流体/損傷/専門モデル/IK/高精度撮像の未完をSDK段の成功で埋めない。
