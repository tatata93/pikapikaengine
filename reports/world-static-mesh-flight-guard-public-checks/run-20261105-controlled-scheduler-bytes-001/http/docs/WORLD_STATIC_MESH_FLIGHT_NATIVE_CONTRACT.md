# World静的mesh flight guardのNative契約案

追記（2026-11-05）：以下は実装前に固定した契約案の履歴。現在は新Native核・型・source固有strict設定・実機監査ツール・有限試験を実装して検証中で、公開受入前である。下記の「未実装」は契約策定時の状態を記録する。現在の説明は [実装ガイド](WORLD_STATIC_MESH_FLIGHT_GUARD.md)、実行原本は reports/world-static-mesh-flight-guard-checks/ と binding-development/ を参照。

2026-11-04。**次段の提案。source_enforced Native x64を選択したが、World guardの新header/cpp/API・binding検査・受入は未実装**。現在の公開機能や検証結果へ含めない。[World計画](WORLD_STATIC_MESH_FLIGHT_PLAN.md)、[seed監査](WORLD_STATIC_MESH_FLIGHT_SEED_AUDIT.md)、[metric coverage](ACCELERATED_PAIR_COVERAGE.md)、[plane-box契約](ACCELERATED_PLANE_BOX_COVERAGE_PLAN.md)、[sphere-box契約](ACCELERATED_SPHERE_BOX_COVERAGE_PLAN.md)から最小接続を選ぶ。本案は現在のplane-box/sphere-box機能公開・証拠receiptから除外する。既存数値核・World・92-export SDK・ゲームの変更は本案の前提にしない。

## 入力と所有

概念上の入口を次とする。既存prepareの `Settings` と衝突させず、新設定名は `GuardSettings` とする。

```cpp
GuardResult query(const dynamics::World& world,
                  std::span<const StaticMeshSource> meshes,
                  double horizon_seconds, const GuardSettings& settings) noexcept;
```

入力viewは同期capture中だけ借用する。返却値へreference/span/pointerを残さない。Hは原global秒 `(0,.1]`。`GuardSettings` は `preparation`（既存count設定）、`mesh`（既存free-flight Settings）、`plane_metric` / `plane_box` / `sphere_box`（各個別coverage Settingsを使用する提案）、`contact_margin`、`limits` を持つ。**marginはconstructorで必須、queryの設定引数にも既定値を作らない**。Worldからmarginを推測せず、有限 `[0,.1]` を要求する。

環境確認→下記source_enforced build binding確認→GuardSettings原値の固定copy→既存 `prepare` →prepare失敗ならその全結果を返す→残る全局所設定・margin・global limitsの検証→全記録容量の予約、の順とする。prepareのinvalid/environment/numericalを同種の外側statusへ、budget_exceededをnot_certifiedへ写し、reason=preparation_failedと元typed failureを保持する。未監査bindingではpreparation/数値childとも未照会、binding stateだけを返しcandidate無しとする。数値childは全preflight後だけ。`preparation` の全owned snapshot/inventoryを一度move所有し、以後callerのWorld/gravity/sourceを再読しない。valid inputでも準備/数値状態を別に保持する。

既存hard上限body8（static込み）・plane16・mesh1..4・全face64を維持する。全28colliderの378組＝必要188＋静的除外190を準備し、全必要pair keyを最初に保持する。face IDはmesh内、collider IDは全種類共通。mesh revisionをgeometry identityの代用にしない。

## 返却型の最小形

| 型/field | 所有内容・不変条件 |
|---|---|
| GuardResult | status/reason、optional typed failure、originalSettings、optional preparation、全BodyRecord、全PairRecord、Work、Reservation、optional candidateBodies |
| BodyRecord | 元body ordinal、dynamic/static、SeedState、optional seedPairOrdinal。巨大seed Resultやtubeの重複copyを置かない |
| PairRecord | preparation.inventory.pairsへのordinal、PairState、reason、実execution ordinal、型別child。元typed refs/ID/revisionは同じ所有inventoryから取得 |
| MeshCall | call state/grants/attempt ordinal、optional **全free-flight Result** |
| SphereCall | 同上＋optional **全sphere-box Result**（元の両radius・両B・明示marginを一度だけ使う。sphere metricは追加しない） |
| PlaneCalls | **同じowned typed pair**にplane metric Callとplane-box Callを別所有。片方未照会でも両slotを残し、両方全域成功が必要 |
| Call record | requestedSettings、usedSettings、work/storage予約、attempt/return、返却Result有無、message省略情報 |

提案enum:

```text
Status = certified_separated / not_certified / invalid_input /
         unsupported_environment / numerical_failure
SeedState = static_copy / pending / ready / failed / unexamined
PairState = unexamined / certified / not_certified / dependency_failed
CallState = unexamined / returned / nonreturned
Reason = none / preparation_failed / settings / storage_budget / work_budget /
         seed_failed / dependency_failed / mesh_not_separated /
         metric_not_separated / box_not_separated / binding_unsupported / child_environment /
         unknown_work / child_exception / metadata_inconsistent / allocation_failure
```

Childの全normative fields（snapshot、全audit/leaf/partition/frontier/current、全row/candidate、元bits、sphere-boxの全15区間/root診断/Work）を保持する。plane metric/plane-box/sphere-boxの異なるleafを同じcellと偽装しない。optional Result無しは未照会かnonreturnedのstateで区別する。nested held/lastMesh/primitive Resultを含む**non-normative message本文だけは保持対象外**とし、callごとの原message総byte数・field数・省略flagを記録して各文字列を空へswapする案を選ぶ。byte合算もcheckedとしoverflowを明示する。数値/診断の切詰めはしない。top messageも固定短文のみとする。このtext方針は既存APIを変更せず、外側の新契約としてレビューする。

## 実行順と渡す値

1. 必要pair一覧の保存順は既存stable key順のまま。dynamic ID順に、そのbody×最小mesh IDのpairをseedとして一度実行する。seed済みpairを再実行しない。BodyRecordはそのPairRecordだけをlinkする。
2. 成功seedは `certified_separated`、tube/endpoint/candidate有り、endpoint監査成功、inflated held separated＋exact Workを要求する。tubeがあるだけ、candidate_evaluatedだけの失敗結果をready seedにしない。失敗seedの依存primitive pairはdependency_failed、child未照会で残す。他の独立body/meshは通常失敗後も予算内で続ける。
3. 未実行mesh pairは旧free-flight `query` を完全callする。同じ所有body/gravity/Hと局所設定を渡し、成功child間では**geometryに依存しない不変数値fieldだけ**を照合する。対象はtubeのnominal/exact加速度・加速度差・B/roundoff/rGuard、endpointの全bounds/L1誤差、全candidate body fields。binary64は−0を含むbits、整数/booleanは型付き値で比較する。endpoint成功flagは別に全trueを要求する。mesh/source配列、audit/Work/row/reason等のmesh別診断や、意図的に省略したmessageは共通flight比較へ混ぜない。各child snapshotの元body/gravity/H/設定と当該mesh所属は別に原本照合する。**各meshで実flight/propagationが繰り返され、全attemptを数える**。tube-only APIへの置換や、再利用したような費用0の報告は行わない。
4. seedが揃ったprimitive pairをstable key順で実行する。body-planeは同pairのplane metric→plane-boxを各一度、body-bodyはsphere-boxを一度だけ実行する。sphere metricを重複照会せず、旧accelerated searchも追加しない。通常のモデル失敗後も独立pairを続け、環境拒否/未知費用/nonreturned/allocation等では停止して残りを未照会で保持する。

dynamicの**plane metric** Sphereは元P/V、seed.tube.nominal_acceleration、seed.tube.guard_radius。plane-boxとsphere-boxの各Sphereは同じ元P/V/aNomだが**元body.radius**を使い、各seed.tube.position_errorを各Bとして明示する。`roundoff` をBの代わりにせず、`g+F/m`、r+B、正規化normalを通常doubleで再構成しない。sphere-boxは `Input(first,second,firstB,secondB,contact_margin)` へ元radiusと各Bを一度だけ渡し、guard radius+Bの二重膨張を禁止する。static geometryはP固定・V=A=B=0・元radius。原static bodyの微小V/Lや荷重bitsはsnapshot/候補copyに保持する。

planeは**同じowned body/plane/元ordinal/同H/margin**に由来するmetricとboxの両全 `[0,H]` がcertifiedの場合だけ成功。metricは幾何半空間、boxはraw中心predicateの証拠であり、片方をもう片方の代わりにしない。body-bodyは両Bのsphere-boxだけで、実Worldの位置差→左dot→sqrtと左結合radius/margin閾値の固定graphを囲む。新shared norm/sqrt helperは増やさず、既存の各全owned transcriptを保存する。

## 選択済みsource_enforced Native x64 gate（実装・監査は未実施）

採用は **source_enforced**。conditional_fixed_graphだけを根拠にactual-World成功へ昇格しない。最初の対応候補は**監査対象のMSVC x64 / GNU x86-64、binary64 SSE2**に限定する。callerが渡すboolや任意のruntime assertionでgateを解除できる入口は設けない。compiler名やx64 macroだけではbinding済みとせず、実行するartifactに結び付く後述のbuild/instruction監査が完了した組だけ許す。ARM/x87/WASM/別compiler・未監査最適化は本Native成功範囲へ自動追加しない。現core.cppはtarget Precise / GNU警告指定で、source固有strict指定・実sqrt監査を済ませたとは扱わない。

現Worldの対象call graphは `dynamics.cpp:225–226` のraw `plane.normal.dot(position)-offset <= radius+margin` と、`:233–234` の `other.position-body.position`→`Vec3::length()`→`Vec3::dot()`→`std::sqrt`、および `(rA+rB)+margin`。呼出先は `core.cpp:23,25,27`。実Worldの全solver/応答・内部接触生成後の計算を認証する案ではなく、この**非接触predicateを各representable durationの自由伝播候補が満たす**範囲である。旧World step/W1/W2を実行/commitするAPIにしない。

実装時の有限gateを次とする。

1. actual `core.cpp`、predicateの `dynamics.cpp`、W1 tube/伝播、guard TUをsource固有のbinary64/order契約へ固定する。MSVCは `/fp:strict` と収縮無し、GNUは `-fno-fast-math -ffp-contract=off -frounding-math` を明示し、actual x64 SSE2 codeでexcess precision・再結合・hypot/近似rsqrt置換がないことを確認する。LTO/別pragmaで未監査graphへ変わらないようbuild構成もpinする。従来sourceを同等flagで再compileしたテスト用コピーだけでactual TUを代用しない。
2. **実linked artifact**の該当symbol/inline call pathをMSVC dumpbin・GNU objdump等で捕捉する。dotのbinary64積/左加算、位置差/閾値順序と、非負有限Qからの `SQRTSD`（監査済み同義encodingなら明記）を検証する。実symbolから監査済み命令へ到達すること、別libm dispatch・未知のcall・x87/近似root・未検査rounding overrideがないことを確認する。単純な別TUの `sqrt(2)` 標本や命令文字列の存在確認だけをbindingとしない。libm経由しか得られない構成は最初の対応から外し、別の無限なhelper開発へ広げない。
3. 当該命令のIEEE binary64 sqrt/RN仕様と実CPUの対応機能を確認し、既存interval環境確認でRN-even、gradual underflow、FTZ/DAZ無しをquery中維持する。compiler/target/flags、対象source・object/linked code・監査結果hashをproof receiptへ保存し、Resultにはbinding mode/stateと対応build identityを保持する。runtimeが自分でobjectを読み直したと偽装せず、build時の固定済みidentityと実行環境を照合する。未証明ならbinding=unsupportedかunverifiedのまま `unsupported_environment / binding_unsupported` とし、数値childを呼ばず外側candidate無しにする。
4. flags/source/provenanceを変える前の旧World/W1全report・全state bitsとSDKの原本を保存し、変更後に全field回帰、source-specific flags/provenance、実artifactを再検証する。SDKを再生成する場合もNative gateをWASM bindingへ自動継承せず、bytes/export/build-ID変化を実測する。descriptor/source hashだけでmachine-code監査や全旧回帰を代用しない。

これは新しい数値helperを要求せず、既存external実体を限定したbuildへ接続する検査である。**現段では命令・object/linked artifact監査を一度も実行していない**。`unverified` をactual-World保証として返せない設計だけを先に確定する。

一次資料の範囲（2026-11-04確認）：[MSVC /fp](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170) はstrictの順序・環境/収縮条件、[GNU optimize options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) はcontract等の個別flagを説明する。いずれも現artifactの命令証拠ではない。[MSVC sqrt API](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/sqrt-sqrtf-sqrtl?view=msvc-170) の戻り値/domain説明だけから全stdlibの正しいRNを導かない。将来照合するinstruction仕様は [Intel SDM Vol.2 SQRTSD](https://cdrdv2-public.intel.com/774492/325383-sdm-vol-2abcd.pdf)。今回は公式検索抽出で該当instruction/rounding-controlの所在を確認しただけで、PDF全体取得はサイズ制限、実machine bindingも未実施である。

## Global制限と呼出し前予約

以下は初期profile案。設定は正整数でhard以下、元値と各grantを保存する。

| 予約対象 | 初期hard/default |
|---|---:|
| PairRecord / BodyRecord | 256 / 8 |
| held audit / certified leaf / partition / frontier要求slot | 各1024 |
| primitive全3種合算 audit / partition / frontier要求slot | 各1024（heldとは別枠。plane metric/plane-box/sphere-boxで共通） |
| lastMesh row / primitive candidate / retained face copies（原本T含む） | 512 / 3584 / 1600 |
| held mesh queries / primitive queries / candidate examinations | 1024 / 65536 / 458752 |
| sqrt refinements upper | 16,777,216 |
| plane metric value attempts / box value attempts | 各1,048,576（boxはplane-box＋sphere-box合算） |
| full body propagation attempts upper | 32 |
| logical requested-capacity payload | 16MiB |

N面、局所held評価上限Eのmesh childについて、call前に全保持worst（E audit、L leaf/partition/frontier、N row、7N candidates、3N source等）を予約する。sqrt work枠は `min(localTotalSqrtLimit, E*(512N+1024))`。512Nはmesh、1024はR/E各512。mesh/primitive/candidate/propagationの各枠もworstで先予約する。**旧mesh設定は残予算都合で下げない**。不足ならcallせず当該pairを未照会budgetとして停止する。

plane metric/plane-box/sphere-boxはEだけを明示的にgrantできる。`usedE=min(requestedE,残valueAttempt枠,残retainedAudit要求slot)`、0なら未照会停止。timeTolerance/depth/maxLeavesは変えず、leaf/frontier枠が足りなければcallしない。requested/used両設定とgrantを保存し、child.snapshotにも実usedEが入る。**primitive5call×既定255=1275が共通1024audit要求slotを超える**ため、この可視grantが必要である。たとえば4callで1020slotを保持後、最後はE4となる。root一件で正を証明できる最小例は通せるが、複雑な安全例の成功は保証しない。

sphere-boxはgrant前にsqrt残枠も加味して `usedE <= floor(残sqrt上界/(2*sqrtRefinements))` とする。refinement設定自体は変えず、call直前に **2*usedE*sqrtRefinements** を全unknown blockとして予約する。0なら未照会停止。返却ResultのWorkがexactなら観測 `sqrt_refinements_returned` へ精算し、非exactは返却upperを保持して全体停止、child非返却は予約全量を保持する。小さいactual反復数を先に推測してgrantしない。rootのlimitedは失敗ではなく、全域gapとexact会計が揃えば成功可能とする。

返却後、unused **work** 予約は正常exact返却から精算できる。保持済みvectorの**要求capacity/storage**予約は、actual sizeが小さい理由で戻さない。全childのsizeof/要求slotからchecked arithmeticでlogical payloadを計算し、16MiB案へ収まるか正式型確定後に確認する。実capacityは別観測。allocator overhead、一時buffer、message構築中、stack/RSS/heap peakの上限とは呼ばない。既存meshは返却3N source、一時旧/新lastMesh併存では4Nとなる点も別に記録する。

## Work・失敗・候補公開

Call attempts/returnsは外側実counter。返却meshではnested heldの全known/upper/exactを加算する。unknown child Workならそのupperを残して全体停止。known returned量は時系列prefixとは限らない。返却不能ならcallをnonreturnedとし、既知返却counter0＋call前full reservation upper、exact=falseとする。これは実使用0ではない。診断prefixを成功結果で補填しない。

実body propagation attemptは返却child.candidate_evaluatedから数える。非返却時は予約1のupperを残す。bridge実call数の専用counterは旧型に無いため推測せず、必要ならmesh child attemptごと上界1として別に記録する。plane metricのprivate normal_magnitudeは既存value attempts/returnsに対する64-loop **upper** のみ（sqrt_enclosureの実反復でも観測rootでもない）。plane-boxはrootを使わずvalue attempts/returnsだけ。sphere-boxはwrapper attempts/returnsに加え、返却された全Evaluationからのroot results/refinements/limitedとunknown upper/exactを別fieldで合算する。value非返却時の観測root0は実内部実行0を意味しない。異種counterを実sqrt回数/反復へ混ぜず、全体sqrt上界には既存heldのroot上界＋sphere-box root上界を加え、private plane norm loop上界は別ledgerで保持する。plane metric call前に `64*usedE` のprivate-loop上界を予約し、全体の既存metric attempt制限から導く `64*1,048,576` の上限でchecked集計する。返却型にprivate反復実測が無い以上、小さかったと推測して精算しない。

全必要pair certified、全dynamic ready、全子正常返却/exact、global会計整合の後だけ `candidateBodies` を元body順で構成する。dynamicはseedの全validated H候補、staticは元copy。失敗・未照会・依存失敗・未知費用では外側候補はnull。最後の候補配列allocation失敗でも全証拠を残してnumerical_failureとし、候補prefixを公開しない。force/torqueは保持し、World/時計をadvanceせず荷重をclearしない。

## 次の最小受入

2dynamic×2mesh＋plane1で必要pairは**7**（body-mesh4、body-plane2、body-body1）。seed2＋残mesh2の実4guard call、同じplane各pairのmetric2＋plane-box2、sphere-box1の**実9call（mesh4＋coverage5）**を確認する。sphere metricや旧searchを重複照会しない。全候補/元World/全原本bits、B/margin/typed所属、実grant/予約/counter、両plane証拠・sphere-boxの元両radius/両B/明示marginと全root会計を独立監査する。全188pair最大入力では、storage/work不足やseed失敗後も全key・未照会tail・dependency_failed・返却prefixを保持し、32mesh child全部の成功とは呼ばない。

全domain/予算/故障、原本回帰、選択済みsource_enforced実binding gate、独立Fraction、GNU warning、sanitizer、通常/計装全fixture一致を経て受入とする。現時点では正式型sizeof、message省略方針、payload/全grant実装、fault分岐、全候補構築はいずれも未実装・未検証である。
