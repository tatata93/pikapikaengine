# 保持荷重と丸め自由伝播guardの共有SDK接続計画

2026-11-04 JST。**raw C ABI/WASM交換は4e422ddで公開受入済み**。[ガイド](SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md)を参照。以下は元の設計と未実装のJS/計測項目を含む。現在のNative保持荷重/自由伝播guard受入を、新しいC ABI・WASM・JSの実行済み証拠とはしない。本稿では旧C++/SDK/manifest/ゲームを変更しない。物理契約は[保持荷重](SPHERE_TRIANGLE_MESH_HELD_LOAD_PLAN.md)と[自由伝播guard](SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD_PLAN.md)をそのまま運ぶ。

## 現物と段階の選択

現headerの86 exports、ABI1、F64入力49,152/U32入力98,304/出力64を維持した上で追加する。現manifestは62 source/header hashes、30翻訳単位、Emscripten6.0.13、runtime member91、7通知、2artifact、memory初期64MiB/最大256MiB、stack1MiB。読取り時の正式strict artifactはWASM719,396B、glue58,933B。この数値は新能力の予測値ではない。

**両入口をまとめるNative C ABI→raw WASM受入を推奨する**。heldだけを先に配布すると、同じ256audit/128partition交換・decoder・再buildをguard段で繰り返す。共通のbounded packetをconst helperで再使用し、同一probeで原半径と膨張半径の所属を比較する方が境界を直接検証できる。JS所有decoderとUIはraw wire受入後の別段にしてよい。一般応答を同時実装する案ではない。

## 独立したmode/stage/record

新family名案は`pp_sim_sphere_triangle_mesh_flight_*`、modeは0=held_load、1=free_flight_guard。6exports案:

```text
begin(mode,triangleCount)
append(mode,valueCount)
query(mode,valueCount)
record(mode,kind,index)
last_mesh(mode,part,index)
candidate(mode,row,ordinal)
```

正式名/定数/packet長はheader/probe実装時に固定する。追加6・予定92 exportsであり、実buildで確定する。mode別にstageとcommitted recordを各1つ、計2組持つ。一方のbegin/append/queryは他方、旧entry/trajectory/single/mesh、World/時計、その他機能のsnapshotへ書かない。last_mesh/candidateは同modeに所属するheld結果だけを参照し、旧globalへ一時代入しない。resetは両stage/recordも消去する。

beginは0..64、appendは1..6面のID+ABC9（10..60 F64）。全chunk有限/ID/長さを検査し候補sourceを所有してからstageを交換する。valid begin/appendも旧record/output/countを保持する。未begin・不足/超過・不正mode/chunk/非有限/unsafe IDは原子的host拒否。空集合、重複ID、有限のモデル域外、設定0等は構造として交換でき、既存核が実際にモデル判定する。未照会を成功/空結果へ読み替えない。

## 入力とWorldとの境界

held input32:

```text
0 ID,1..3 P,4..6 V,7 mass,8..10 F,11..13 g,14 radius,15 H,
16 meshMax,17 maxCandidates,18 primitiveSqrt,19 primitiveTotalSqrt,
20 localWidth,21 normalWidth,22 minSineSquared,
23 timeTolerance,24 maxEvaluations,25 maxLeaves,26 maxDepth,
27 enclosureSqrt,28 totalSqrt,29..31 reserved +0
```

guard input48:

```text
0..27 body28（既存World入力と同じ全fields/順序）,
28..30 gravity,31 H,
32..44 上記13settings（meshMaxからtotalSqrtまで）,
45 maxAngularIncrement,46..47 reserved +0
```

body28はID/static/mass/radius/I3/P3/q4/V3/L3/F3/torque3/restitution/friction。全body原本を保存し、orientationやtorqueを「球だから不要」と落とさない。元source/settingsもquery echoと別に所有する。

全数値有限、ID正safe integer、static flag0/1、整数設定uint32全域、予約は**正零**、正確なcountを変更前に検査する。static入力の−0は既存と同じfalseとして受理し、original echoだけ−0を保持、型変換後snapshot/worldBody/candidateのflagは+0に正準化する。有限の不適切mass/inertia/q/radius等は実Native`body_invalid`へ渡す。既存`body_input()`は直ちに`body.validate()`するため、そのまま再使用してNativeモデル失敗をhost拒否に変えてはならない。整数設定echoの−0と、Native型変換後snapshotの+0を区別する。原本の位置/力/weightでない全実数・intervalの−0を保存する。

初段はraw SI値を入力する。guardは既存純粋`query(body,gravity,...)`を呼び、World handleへ一時bodyを追加しない。JSが実Worldからbodyを読み取る場合も読取snapshotであり、同Worldの他pairやtickを検査したことにはならない。const World adapter自体はNative専用試験で全storage/pointer/loads不変を確認する。新handle/time/tick出力を捏造しない。

## 候補検査と原子的publish

queryは入力echoとsourceの全所有copy→核実呼出し→返却全optional/flags/enum/range/count/finite/リンク監査→全packetを構築できることの監査→nothrow move→summary一回publishの順とする。候補監査・host側の所有copy/packet構築allocation・host交換拒否なら旧stage/record/output/countを保持する。正常交換のモデル失敗は新しい失敗recordへ置換し、geometry/候補成功と混同しない。Native核が捕捉して返した`numerical_failure/allocation_failure`も、有限で整合する診断ならこのモデル結果である。reason名だけでrollbackせず、返ったpartial/unknown Workとoptionalを保持する。実allocation fault injection未実施は構造監査で代用しない。

guardのoriginal snapshot/body radiusは**元半径**。nested inflatedのHeldSphere.radiusはTube.guardRadius。TubeのexactAとnominalA、B/roundoff、Endpointの各boundsを区別する。candidateは`certified_separated`のときだけ存在し、Hで実`propagate_free`＋validateを通った全bodyコピーで、force/torqueを消費していない。膨張entry/initial penetrationは元球のentryではなく外側not_certifiedの診断。原半径の別query結果をnestedへ補填しない。

## 64 F64以内のpacket案

全packet固定長・未使用payload/+0 padding・metadata正零。interval、unused KKT[-0,+0]、echoの実数bitsは別扱いでそのまま保存する。不在getter/不正kind/indexは旧output/count/recordを保持し、fallbackしない。可変message原文はwireへ含めずstatus/reasonを診断本体とする。Native fixtureとの比較ではmessage除外を明示し、復元したふりをしない。

family summary24案:

```text
mode,status,reason,sourceCount,hasSnapshot,hasFailedIndex,failedIndex,
hasWorldBody,hasTube,hasFlightFailure,flightFailure,candidateEvaluated,
hasEndpoint,hasInflated,hasCandidate,hasHeldResult,+0x8
```

mode0のstatus/reasonはHeld enumでhasHeldResult=1、mode1はGuard enum。hasHeldResultはmode1ではhasInflatedに等しい。別headerの有無をここで明示し、初期snapshot:nullでもecho/sourceは得られる。

| record kind案 | 固定長・上限 | 内容 |
|---|---|---|
| original echo | 32/48、1 | 正常交換の全原input（snapshot:nullでもあり） |
| source | 14、64 | ordinal/ID/ABC9/hasLastMeshRow/hasLastMeshQuery/isLastPossible。後3flagはnested lastMeshだけの所属 |
| native snapshot echo | 32/48、1 | snapshotが所有した型変換済全入力。echoと独立照合 |
| held header | 48、1 | 下記。mode0は本体、mode1はinflatedだけ |
| held snapshot input | 32、1 | 実HeldSphere/settings/H。mode1のradiusは膨張値 |
| world body | 32、1 | body28/gravity3/+0。実optionalだけ。mode0 rawでは通常なし |
| tube | 24、1 | nominalA3/exactA6/difference6/B/roundoff/guardRadius/+0x6 |
| endpoint | 40、1 | nominalPosition6/nominalAllowed6/exactPosition6/exactAllowed6/exactDifference6/L1I2/3flags/+0x5 |
| candidate body | 32、1 | body28/+0x4。成功only。派生omega/energy/timeを新計算しない |
| acceleration/wholePath/wholeVelocity | 各8、各1 | ordinal0/Bounds6/+0。Held側の実optional |
| audit | 64、256 | 既存entryのaudit64と同配置、parameter欄をglobal **seconds time**として扱う |
| certified leaf | 6、128 | closed TimeCell3/lowerCertificate2/auditIndex。全後方island |
| partition | 8、128 | ordinal/TimeCell3/state/hasAudit/index/blockedReason |
| frontier/current | 4、128/1 | ordinal/TimeCell3。全未照会tail、initial current[0,0]も保存 |
| initial | 6、1 | ordinal0/lowerCertificate2/upperCertificate2/auditIndex |
| witness | 18、1 | ordinal0/TimeCell3/time/pointBounds6/anchor3/E/upperCertificate2/auditIndex |
| window | 14、1 | ordinal0/L/U/timeWidth2/pathBounds6/L1Diameter2/witnessAuditIndex |
| conservative surface ID | 2、64 | ordinal/ID。window時の全source昇順、縮小しない |

Held header48案:

```text
0 status,1 reason,2 sourceCount,3 hasSnapshot,4 hasFailedIndex,5 failedIndex,
6 hasWorldBody,7 hasAcceleration,8 hasWholePath,9 hasWholeVelocity,
10 hasInitial,11 initialSeparationProven,12 leafCount,13 partitionCount,
14 frontierCount,15 auditCount,16 hasSafePrefix,17 safeLo,18 safeHi,
19 hasBestWitness,20 hasWindow,21 conservativeIdCount,22 hasCurrent,
23 hasLastMesh,24 hasLastMeshAuditIndex,25 lastMeshAuditIndex,
26 partitionLeaves,27 maximumDepth,28..38 Work11,39..47 +0
```

Work11は既存entryと同順、各auditはdelta/headerは合計。exact=falseのknown/upper・未返却block reservationを落とさない。Audit64のkind/initial/time・Bounds/roots/certificates/mesh flagsも既存配置をそのまま使う。squared normやL1区間の微小負lowerを、非負rootの検査と混同しない。

last_meshはpart0 summary24/part1 row58、candidateはprimitive13。全64row/448候補、null query/未照会、最後のmeshとauditIndexリンク、source−0/unused KKTを保存する。world body getterはmode1の外側Result専用とし、mode0 rawとmode1 nested inflatedのheldHeader.hasWorldBodyは常に0を検査する。captured不正bodyも有限なら失敗診断としてpublishし、worldBodyへ成功candidate用の物理validateを掛けない。const helper再使用は可だが、旧globalへの仮代入、lastMeshをentry面/衝撃点とする処理は禁止。packet長/定数/enum/mapは正式headerとNative probeで固定し、上表だけで実装済みとしない。

## JS所有・能力検出

将来のmethod案は`querySphereTriangleMeshHeldLoad(input,triangles,settings)`と`querySphereTriangleMeshFreeFlightGuard(body,gravity,triangles,H,settings)`。同family6能力を最初の書込前に全検出し、旧86/一部欠損/loader拒否を明示、無fallback。Proxy/getterを含む入力field/length/成分を一度captureして全検査・copyし、それからstageを触る。

新guardのJS body原本はNative fixtureと同じ`inertiaDiagonal`・`velocity`・`material:{restitution,friction}`の全28field形に固定する。既存World DTOの`inertia`・`linearVelocity`・flat restitution/frictionとは別で、既存`bodyInput()`を直接流用しない。World DTOから使う場合は明示した全fieldの所有変換helperを介し、不在fieldを既定速度0や推定慣性へ補填しない。candidate/worldBodyも新28field専用codecで読む。旧`bodyResult()`の34値（omega/energy/time/ticks付き）を32packetへ適用し、paddingを新しい派生値として解釈してはならない。新raw C ABI受入とJS所有段それぞれで非零velocity・異方慣性・非零torqueの変換を照合する。

返却はNative全数学診断に`originalInput`を加え、caller/snapshot/original/oldDTO/nested inflated/lastMeshを別所有する。memory growth後のHEAP view再取得と即owned copy、dense長さ/finite/enum/+0 flags/optional/count/link/全partition閉被覆/BFS/prefix/islands/tail/seconds幅/全保守ID/Work予約を検査する。JSは幾何、sqrt、F/mやBを再計算するsolverではない。Native正常publish後のdecoder拒否はJS DTOを返さないがNative record rollbackを保証しない。同期・非再入で、共有scratchへの並列アクセスは不可。

## メモリ・stack・正式再build

1つのheld結果は最大256audit、128partition/leaf/frontier、64source、lastMesh64row×7候補であり、過去auditに全meshを複製しない。両mode各committed1＋更新候補1、stage2までを同時に保持する。最大同時件数を単純に全て実達成したと主張せず、各独立上限でallocation計算をchecked arithmeticする。大配列をstackへ置かず、packet用localは64 F64以下、全DTO/sourceはheapのowned vectorでmoveする。stageを新recordにaliasしない。

新guard.hpp/cppとheld.hpp/cppをbuilderへ加え、private bridge/headerと**dynamics.cppもstrict/no-fast-math/no-contraction**のsource flagsを監査する。現62 hash対象からの増分、runtime91/通知7からのmember差、WASM/glue bytes/SHA、初期memory/成長/stack高水位・最大raw/owned読出しの実使用量は正式再build後に測定する。64/256MiB・1MiBを事前に増やさず、OOM/stack不成立なら予算を黙って下げず明示して再設計する。SDK6.0.13固定、全source/artifact/通知/license（本体未選定）を監査し、新素材/課金は追加しない。

## 次段の独立受入

- Native probeで純79 held/100 guardと補足4の**完全入力**を再構築し、hostと実modelを実測分類。ID0/unsafe/65面等をhost出自として保持し、pure入力をNative/WASM実行へ補填したとはしない。
- 旧86の全回帰、旧W1 full20例・SDK4520bitsの前後比較を再実行。新92予定の全wire/header/source/body/candidate/audit末尾/negativezero、Native/WASM全bitを照合。formal packet整数正規化だけは元echoとの相違を明示する。
- WASM由来DTOを独立Fraction参照へ渡し、exact F/mとquadratic extrema/距離/certificates/全prefix/closed partition、独立RN/ties-even operation graph/ULP recurrence、実candidate endpointを照合。実取得model行だけを独立verify_fixtureへ渡し、受理された完全入力のfingerprintと件数を別固定する。host拒否行をNative結果で埋めて全WASM数学監査と呼ばない。通常safe成功を必須にし、膨張entryを元球contactへ昇格する負例を拒否。
- 全kind末尾/256audit/128leaf・frontier/64source/候補、static/不良body/派生radius域/回転失敗/unknown work・prefix、candidate成功only、旧record/output/count保持、同/別mode独立、reset/不正getter、input/scratch/旧DTO所有を検査。
- strict Native/GNU warnings・API/test sanitizerとpure各核別sanitizer、改ざんcontrols、実fixture byte比較・原本保護を別証拠にする。自然未到達のallocation/未知workは人工wire試験と実fault注入を区別する。

本受入はSI照会と診断の配布であり、World advance/全pair順序/同時manifold/反発摩擦支持/残時間と累積丸め/tick commit/一回の荷重消費を増やさない。手動UIやゲーム適用は別の依存段として設計し、一般物理・流体/損傷・専門モデルの未完範囲を維持する。
