# 派生mesh snapshotの有界まとめ読出し案

2026-11-04 JST。設計のみ・未実装。既存65 exports / ABI v1 / F64 output容量64を基準とする。C++ prepare、局所Float32の監査条件、原本、公開DTOの型と所有は変えない。今回追加したファイルは本計画だけであり、SDK再生成・本番最適化・性能受入は行っていない。

## 選ぶ最小変更

新しいC ABIを1つだけ追加する案とする。

```c
int32_t pp_sim_derived_mesh_records(
    uint32_t kind, uint32_t first, uint32_t record_count);
```

既存 `pp_sim_derived_mesh`、single getter `pp_sim_derived_mesh_record(kind,index)`、summary20、全既存関数のsignatureと意味は維持する。output/input容量も変えず、ABI versionを1のまま、新exportの有無を能力判定に使う。採用時の配布は66 exportsとなる。派生結果を再計算する関数ではなく、直近の同じ所有snapshotを読む関数である。

成功packetの先頭4要素を `[kind, first, record_count, stride]` とし、その後へ、同じkindの既存record payloadを順に連結する。各recordの中身・順序・optional flags・数値を変えない。`pp_sim_output_count()` は厳密に `4 + record_count * stride`。64まで埋めるためのpaddingを公開しない。

| kind | 既存payload | stride | 1回のrecord_count | 最大output_count |
|---|---|---:|---:|---:|
| 0 | 局所Float32頂点 xyzをdoubleへ正確に拡幅 | 3 | 1..20 | 64 |
| 1 | triangle indices xyz、元順序 | 3 | 1..20 | 64 |
| 2 | face-order interleaved pos3/normal3 ×3頂点 | 18 | 1..3 | 58 |
| 3 | 既存audit26全体 | 26 | 1..2 | 56 |

audit26は `[face,cross6,Q2,hasNormalized,normalized6Or0,hasNormal,normal3Or0,hasError,error3Or0,sqrtCount,limited]` のまま。例えばkind3/first4/count2はheader4と、`face=4` / `face=5` の26要素ずつを返す。headerのkind/ordinal/count/strideはこの容量ではdoubleへ正確に表せる整数である。

headerなしなら3要素recordを21件入れられるが、今回は自己記述と短いtail/stride監査を優先して20件とする。特殊なindex packing、Float32のbitを整数へ詰める方式、複数kind混在、借用pointerを追加しない。

## 範囲・status・失敗atomicity

呼出しは既存と同様、同期かつ再入/並行利用非対応。引数の型はuint32だが、kindは0..3、countは上表の正範囲でなければならない。count0も拒否する。空集合はcallerが呼出しを省略する。要求countを勝手に縮小せず、末尾countはcallerが `min(maxCount, available-first)` と明示計算する。

全条件をpublish前に検査する。

1. derived snapshotが存在すること、kind/countが有効であること。
2. kind0..2は `geometry.has_value()` が必要。kind3はモデルが失敗していても実在する `audits.size()` をavailableとする。
3. `first < available` と `record_count <= available-first` を確認する。未検査の `first+record_count` でuint32 overflowを起こさない。
4. 局所 `std::array<double,64>` に全packetを構築し、既存と同じ有限値監査後、一度だけnoexcept publishする。

成功時はC戻り値 `PP_SIM_OK`。これは「snapshotの読出し成功」であり、元のprepareモデルがcompletedであるとの再判定ではない。モデルstatus/reasonは既存summary20にだけあり、packet headerへ別のstatusを重複させない。

無snapshot、不正kind/count/range、render getterへのgeometry-null要求は `PP_SIM_INVALID_ARGUMENT`。packetの数値出力に内部矛盾があれば既存と同じ `PP_SIM_CORE_REJECTED` とする。例外捕捉・bounded error text・last_statusは既存guarded規約を使う。失敗時は直前のoutput_countとその有効prefixの全bits、現在のderived snapshotを保持する。途中までの成功packetを返さない。未使用のoutput tailにゼロ初期化や永続性を約束しない。

accepted prepareモデル失敗は既存どおり新しいgeometry-null snapshotへ更新される。そのauditは失敗面を含み得る診断prefixであり、まとめ読みしてもrender geometryへ昇格させない。auditCount0ならkind3も呼ばない。global reset後は新旧getterとも無snapshotとして拒否、World resetや他種queryはderived snapshotを消さない。

atomicityは各ABI呼出しの境界である。prepareが既にcommitした後のbatch getter拒否は、その新しいsnapshotと直前chunkを保持するのであって、prepare前の古いsnapshotへ戻すわけではない。JSがpacket検査でthrowしてもNativeのprepare commitは巻き戻さない。前回callerへ返した所有DTOは引き続き不変である。

## JS decodeと旧SDKとの比較可能性

最初の受入では `prepareDerivedMesh(input,{...,readback:'single'|'batch'})` の明示比較経路を提案する。省略は現行single。batch指定時に新exportがなければ、input交換/queryより前に明示的なhost errorとする。自動fallbackで比較対象を変えない。不正readback指定も呼出し前に拒否する。既存引数と旧SDKでのsingle経路を維持する。

batchを通常既定へ変更するか、後でauto判定を追加するかは、同一SDKでの独立計測後に決める。将来autoを採用する場合の旧SDK capability fallbackは、処理開始前の新export有無だけでsingleを選び、実際に選んだtransportを計測条件へ保存する。batchが存在するのに不正packet/実行errorを返した場合はsingleへfallbackしない。本計画は一貫した性能改善や既定変更を先に採用しない。

既存decoderのrecord単位検査を再利用し、private get helperのtransportだけ差し替える。kindごとに最大1packetの所有Array cacheを持ち、header4とstrict length、有限値、kind/first/count/strideを先に検査してから各recordをdecodeする。既存decoderは各kind内でordinalが昇順なので、kind1/2が交互に呼ばれてもkind別cacheで再取得を避けられる。summary20は最初に一度だけ読む。

既存 `runtime.output()` の `Array.from(current HEAPF64.subarray(...))` を使う。各ABI後に現在のHEAP view/pointer/countを取り直し、公開DTO/cacheに借用HEAP viewを漏らさない。new Float32Array / Uint32Array、normalErrorの通常Array、boundsの通常Array、object key順序とnullの意味を維持する。batchからのslice/decodeに新たなArray割当があり、call数減少だけでcopy/全体コストが減るとは扱わない。

header監査後も、audit ordinal/flags/absent payload、Q/normal error、Float32 exact representation、sqrt合計、triangleの入力順、expanded position/normalの `Object.is` 比較を省略しない。Float32からdoubleへの拡幅とArray copyはsigned zeroを保持する。absent payloadの0規約も既存どおりで、存在する数値の-0を一括+0 canonicalへ変換しない。非有限や不正packetをsingleへ再試行して隠さずprotocol errorにする。全decode終了まで部分DTOを返さない。

## 呼出し回数と増える転送量

completedの頂点N、面T、audit A=Tについて、既存getter数は `N + 3T`、提案は `ceil(N/20)+ceil(T/20)+ceil(T/3)+ceil(T/2)`。output copyはそれぞれgetter数+summary1。失敗prefixは `ceil(A/2)` getterとsummary1だけで、geometry getterを呼ばない。A0ならgetter0。

| 入力 | N/T | single getter | batch getter | single/batch output copy |
|---|---|---:|---:|---:|
| 実Source帯 | 6/4 | 18 | 6 | 19 / 7 |
| 斜め法線 | 192/64 | 384 | 68 | 385 / 69 |
| sheared grid | 512/512 | 2048 | 479 | 2049 / 480 |
| SDK同時上限 | 2048/32768 | 100352 | 29049 | 100353 / 29050 |

有効payload自体は `3N+47T` doublesで変わらず、新方式はgetterごとのheader4を余分に運ぶ。512頂点/512面では25,600に1,916 doublesが加わり約7.48%増える。上限例はsummaryを除き1,546,240→1,662,436 doublesとなる。prepareのC++query核の計算量・費用自体を減らす変更ではない。少ないABI往復と長い所有copyが有利か、header・cache・sliceが不利かは実測事項であり、call削減率を速度向上率へ読み替えない。30回探索pilotではindex copy単体が短くてもprepareの一貫改善はなく、production output置換を採用しなかった。同じ推論の飛躍をbatchにも持ち込まない。

## 計測helperと互換性

`tools/derived-profile.mjs` は現在single getter名だけをcppGetterとして捕捉する。新方式を測る前に新exportも同stageへ登録する。`getterKinds[4]` は引き続き「kind別ABI呼出し数」とし、record数へ意味を変えない。必要なら別の `getterRecords[4]` を追加して処理record数を明示する。singleの場合は両者が一致する。stages名とCPU観測時間の解釈は維持する。

`cppGetter.calls=sum(getterKinds)`、`outputCopy.calls=1+cppGetter.calls` は維持できる。record件数はcompletedで `[N,T,T,T]`、失敗時 `[0,0,0,A]`。batch call件数は上のceil式で別監査する。host検査拒否は交換/query/getter/outputとも0回。現在のCLI/UI/testsのsingle前提の固定期待値は、batch比較経路について明示的に更新し、旧single回帰を消さない。capture漏れを未分類残差へ押し込まない。

同一SDK、同一case、孤立runtime、交互paired順でfirst/warmup/全measureを保存する。全DTOの型/ordered keys/bits/typed bytes、入力/原本、SDK source/notice/artifact hashを照合する。nativequery、getter、output copy、未分類残差と全体を別に扱い、中央値同士の和やmicro差引きから因果を断定しない。実ブラウザ4/64/512面の通常checked描画で全upload bytes/末尾/cache0Bも維持する。Native/GPU単独時間・一般fps・robot更新頻度の受入には広げない。

## 実装時の独立受入

1. **Native packetの全kind。** 上限件数とtailを含むN41/T23等を一度prepareし、batchを連結してsingle全recordとbinary64 bitsで比較する。header64満杯のkind0/1、face58、audit56、count1、最終record、sourceに特徴のある末尾を明示。独立の既知頂点/triangle/有理法線参照と照合し、共通serializer同士の一致だけを正解にしない。
2. **raw不正とatomicity。** kind4/UINT32_MAX、count0/上限+1/UINT32_MAX、first=available/UINT32_MAX、tail不足/加算overflow相当、reset後、geometry-nullのkind0..2を拒否。前回有効count/prefix bitsと新旧getterで読むsnapshotを保持。失敗後に正常batch/prepareが再利用可能なこと。
3. **失敗prefix。** 先行正常面+退化面の2auditを1packetにし、成功normalと失敗optional-null/flags、失敗面ordinal、global countersを保持。A1/A3のtail、A0の空モデル、quality_unresolved、invalid settings、予算例も通常成功geometryへ変えない。
4. **主SDK parity。** 既存40固定モデルとSource11をsingle/batch両方で再生し、全model/host分類、DTO型/全bits/bytes/key順序を比較。独立Fraction checker/36負例を両transport出力へ適用。acceptedモデル失敗と交換不正の違いを残す。
5. **JS hostile packet。** header不正/不足/余分、count0/過大/ordinal逆転、stride異常、payload欠損/非有限、audit境界のoptional flag破損/absent非zero/normal改変、triangle末尾改変を偽nativeで注入。成功/部分DTOを返さず、fallbackしない。旧SDKのsingle正常とbatch指定の事前拒否も試験する。
6. **所有と独立record。** -0を含むvertex/normal/intervalのbits、後続getter/queryと返却Array改変に対する所有分離、現在HEAP view再取得を確認。view交換は実memory.growと区別したstub回帰でも明示する。World clock、skin/motion/optics snapshot、元export/prototypeを変えない。
7. **容量と処理完結。** 既存同時2048/32768 prepareを繰り返し増やさず、1snapshotからbatch最終頂点/triangle/face/audit、全件数/全buffer末尾を確認。容量を増やしたり未読tailを捨てて合格にしない。旧single getterも残す。
8. **profile/renderer回帰。** 両modeのceil call数、output回数、clock失敗/復帰/host0を試験。実SDK3caseを既存rendererへ通し全bytes/末尾/draw count/cache0B/退役/clearを確認。GPUやtimestamp処理を追加せず、rendererの既存資源契約を維持する。

最初に新ABIのNative packet試験を完成し、その後SDK再生成・JS transport比較・全既存回帰・独立数値検査を行う。数値/所有/互換性の全検査に合格し、同条件のNodeと小規模ブラウザで一貫した効果を確認するまで通常経路への採用を保留する。測定未達や改善未確認なら既定はsingleのままとし、不採用のrawも保持する。性能測定を数値品質の代用にしない。実装分担時はC ABI/header/tests/build/provenance、JS decoder/profile/tests、UI/証拠の所有を先に分け、元数値核・sampleは変更しない。

## 読取根拠

以下は本設計時の行番号。後の実装で移動し得る。

- `core/include/pikapika/simulation_api.h:22` output64、`:84` 共有領域/HEAP refresh/同期非再入、`:258` 既存derived入力/summary/record/error契約。
- `core/src/simulation_api.cpp:55` scratchと独立record、`:80` guarded例外/status、`:118` noexcept publish、`:230` finite output監査。
- `core/src/simulation_api.cpp:237` audit26 serializer、`:245` 全candidate/ordinal/counters検査、`:577` prepareのモデルcommit、`:600` single getterの範囲/geometry/有限値/publish。
- `engine/simulation.mjs:31` Array.from所有copy、`:119` host検査とprepare、`:555` summaryとrecord decode、`:568` 失敗prefix含むaudit、`:578` typed geometryと展開整合。
- `tools/derived-profile.mjs:41` query/single getter計測、`:42` getterKindsの実call count、`:51` JS output wrapper。
- `tests/simulation_api_tests.cpp:556` bits/record/入力scratch所有、`:567` malformed exchange/getter保持、`:586` model失敗prefix、`:595` 同時SDK上限、`:605` record独立/reset。
- `tests/derived-mesh-sdk.test.mjs:21` hostile summary/record、`:36` 実所有/符号零、`:45` model失敗、`:52` 容量、`:59` host保持、`:76` 実Source通し。
- `tests/derived-profile.test.mjs:25` getter/output call会計、`:36` failureのaudit数、`:42` host0と以前output、`:48` 後続query不変、`:54` 他recordとWorld clock。
- `tests/derived-gpu-profile.test.mjs` 実3caseの全upload/cache/退役受入。計測・コピー探索の原rawは `reports/derived-copy-archive.json` と `reports/derived-copy-pilot/`。計画の前提は `docs/DERIVED_MESH_READBACK_PLAN.md`。
