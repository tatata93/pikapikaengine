# 派生meshのまとめ読出し

2026-11-04 JST。Native C ABIとJS decoderを実装し、共通SDKをローカル・Linux CI/Pagesで受け入れた。公開操作は既存singleの互換動作を確認し、ブラウザ両transport比較は次段である。新SDKは66 exports、API version1、F64 output容量64、入力上限2048頂点/32768面を維持する。Native744群/CTest30・Node452skip0、両transportの独立数値照合と有限Node比較を[統合報告](../reports/2026-11-04-derived-readback.md)へ保存した。

[当初の計画](DERIVED_MESH_BATCH_READ_PLAN.md)に基づき、既存の所有snapshotを複数recordずつ読むC ABIを1つ追加した。query核・Float32監査条件・原本・renderer・sampleは変更しない。呼出し回数の削減は実測した速度改善を意味せず、通常の既定経路はsingleのままである。

## C ABI

```c
int32_t pp_sim_derived_mesh_records(
    uint32_t kind, uint32_t first, uint32_t record_count);
```

既存の `pp_sim_derived_mesh`、summary20、`pp_sim_derived_mesh_record(kind,index)` はそのまま使用できる。新関数は同じ直近snapshotの読出しだけを行い、prepareや時計を進めない。新たなC++ object layout、借用buffer、input領域は公開しない。

成功packetはheader4 `[kind,first,recordCount,stride]` の後に、既存recordのpayloadをordinal順に連結する。output countは厳密に `4 + recordCount * stride` で、未使用tailをpaddingとして公開しない。

| kind | payload | stride | countの範囲 | 最大output count |
|---|---|---:|---:|---:|
| 0 | Float32局所頂点 xyzをdoubleへ拡幅 | 3 | 1..20 | 64 |
| 1 | triangle indices3 | 3 | 1..20 | 64 |
| 2 | faceのinterleaved position3/normal3 ×3 | 18 | 1..3 | 58 |
| 3 | 既存audit26 | 26 | 1..2 | 56 |

audit26は `face,crossBounds6,squaredCross2,hasNormalized,normalizedBounds6Or0,hasNormal,normal3Or0,hasError,error3Or0,sqrtCount,limited`。optional flagsとlower/upper順はsingle版と同じである。Float32値は正確にdoubleへ拡幅し、存在する数値のsigned zeroを維持する。absent payloadのゼロはゼロ法線や誤差ゼロの証明ではない。

count0、不正kind、上限を超えるcount、snapshot外の要求、無snapshotは `PP_SIM_INVALID_ARGUMENT`。末尾を自動縮小しない。callerが `min(maxCount,available-first)` を計算し、空の集合なら呼出しを省略する。実装は `first < available` の後で `count <= available-first` を検査し、未監査のfirst+count加算を使わない。

全packetを局所array64へ作り、有限値を監査してから一度だけpublishする。失敗時は直前のoutput countと有効prefixの全bits、現在のderived snapshotを保持する。last_status/error textは通常のC ABI失敗規約に従う。成功時の `PP_SIM_OK` は読出し成功であり、元モデルのcompletedを意味しない。モデルstatus/reasonはsummary20のまま。

acceptedモデル失敗は、以前のgeometryをgeometry-nullの新snapshotへ置換する。kind0..2はこの場合拒否されるが、kind3は実在するaudit prefixだけを取得できる。失敗面を含む診断prefixをまとめて読んでも、部分的なrender geometryにはならない。auditCount0ならkind3も要求できない。

atomicityは各C ABI呼出しの境界である。prepare commit後のgetter拒否は、その新snapshotと直前outputを保持する。prepare前のsnapshotへ戻す意味ではない。global resetは新旧derived getterのsnapshotを消す。World resetと他種queryはderived snapshotを消さず、この読出しもWorld時計・保持荷重やskin/motion/optical snapshotを変更しない。共有scratchは引き続き同期・非再入で使う。

## JSの選択と所有

```js
runtime.prepareDerivedMesh({positions, triangles}); // 既定single
runtime.prepareDerivedMesh({positions, triangles}, {readback: 'single'});
runtime.prepareDerivedMesh({positions, triangles}, {readback: 'batch'});
```

他のoptionsは従来どおり `maxVertices=2048,maxTriangles=32768,sqrtRefinements=128`。readbackはsingle/batchの2値だけで、autoは実装していない。不正指定、新exportのない旧SDKへのbatch指定は、入力交換/queryより前にhost errorとなる。旧65-export SDKでも従来のsingleは使える。batchが不正packetや実行errorを返した場合はsingleへfallbackして隠さない。

decoderはkind別に最大1packetの所有Array cacheを持つ。header4・件数・stride・厳密な長さ・全有限値を先に監査し、record単位の従来検査へpayloadを渡す。triangleと展開faceの取得が交互でも、それぞれのcacheを保持する。ordinal、optional flags、Float32表現、input triangle順序、展開position/normalの `Object.is` 整合、面積/誤差条件、sqrt合計を省略しない。全decodeが終わる前に部分DTOを返さない。

返るDTOはsingle版と同じ型・順序・nullの意味で、geometryは所有Float32Array/Uint32Array、bounds/error等は所有Arrayとなる。`runtime.output()` は現在のHEAP/pointer/countから通常Arrayをcopyする従来実装を使う。HEAP viewをcacheや公開DTOへ借用しない。後続getter/queryやHEAP view交換は以前のDTOを変えず、callerによる自身のDTO改変はNative snapshotや別の返却DTOへ及ばない。

JSが不正packetを検出してthrowしても、Nativeが既にcommitしたprepareを巻き戻すわけではない。以前callerへ返したDTOの所有は維持する。C++で証明した局所量を、batch decodeや描画によってworld/GPUの保証へ広げない。

## 計測のcallsとrecords

計測helperの5 stagesは維持し、新旧getterをともに `cppGetter` として観測する。

- `getterKinds[4]` はkind別の実際のABI呼出し数。
- `getterRecords[4]` はkind別の要求record数。singleは1件、batchは引数countを加える。いずれも成功件数ではなく、Nativeへ届いた失敗呼出しも含み得る。
- `cppGetter.calls = sum(getterKinds)`、通常の完了経路では `outputCopy.calls = 1 + cppGetter.calls`。1はsummary20。
- completedの要求record数は `[N,T,T,T]`、失敗prefixは `[0,0,0,A]`。入力前host拒否は各stage0。

completed時、single getterは `N+3T` 回、batchは `ceil(N/20)+ceil(T/20)+ceil(T/3)+ceil(T/2)` 回。実Source4面は18→6、64面/192頂点は384→68、512面/512頂点は2048→479回となる計算である。header4の分だけ転送量は増える。512面ではpayload25,600 doublesへ1,916 doublesを追加する。query核を軽くする変更ではない。

減ったcalls、増えたpayload、cache/slice/所有copy、計器の負荷を含む全体を別々に評価する。未分類残差を純JS費用と呼ばず、中央値同士を足して一trialの会計にしない。先行copy pilotはprepareで一貫した効果を確認できず採用していない。このbatchも速度保証や通常既定変更をまだ受け入れていない。

## 検証した範囲と次の受入

Nativeには全kindの最大packet/tail、single payloadとのbits照合、独立な有理cross/法線、符号零、不正count/range/overflowのatomic拒否、mixed失敗audit prefix、scratch所有、独立snapshot/resetの試験を追加した。JSにはhost能力検査、kind別cache、hostile packet拒否、既存固定モデル/実Sourceの両transport照合を追加した。ローカルの最終実行結果とSDK hashes、公開CI/Pagesと既存singleの互換確認を統合報告へ保存した。

次の小さい受入は、同一SDKでsingle/batchを明示したブラウザの比較である。first/warmup/全反復、全DTOの型/bits/typed bytes、原本/入力とSDK hashを保持し、prepare全体とgetter/output/残差を区別する。実3caseの全byte upload/末尾/cache0B/旧buffer退役も維持する。この両transport比較UIと性能受入は本段では未実装。効果未確認なら通常経路への採用を保留し、single既定を維持する。

Native/GPU単独時間、最大容量での実時間描画、robot連続animation、一般物理/流体/損傷/IK/光学撮像の完成を、このsnapshot読出しから主張しない。
