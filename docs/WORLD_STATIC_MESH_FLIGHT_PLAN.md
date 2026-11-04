# World全pairと静的meshのread-only自由伝播guard案

2026-11-04 JST。**次のNative数値段の設計・未実装**。本書は新API、全pair証明、候補、予算、試験の成功を示さない。保持荷重/自由伝播の[単体契約](SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD.md)と[手動ラボ](SPHERE_TRIANGLE_MESH_FLIGHT_LAB.md)を前提に、単一bodyを選ぶ照会から、宣言したWorld全体の非接触監査へ進む。既存92-export SDK、World/serialization、ゲーム、既存の全数値核はこのNative段では変更しない。新依存/素材/license選択はない。外部資料は今回閲覧せず、以下は既存ソースと三角不等式による設計である。

## 直近の実装段

新Nativeの [`prepare` 段](WORLD_STATIC_MESH_PREPARATION.md)を分離して実装し、所有snapshot・再検証・typed全必要pair一覧とstatic-only会計を公開受入した（機能6608bc3、Native42CTest/有限84、Linux全22段・ASan/UBSanとPages成功）。最大378全組＝188必要＋190除外を原本から独立に検査し、caller変更/破棄後の所有と−0を確認する。準備readyは構造準備だけであり、退化面を含むこともある。非接触認証・flight・candidate・World更新・時計/荷重消費は行わない。以下の全pair数値guard、global診断容量、plane二条件とproof transcriptはその後の未実装段である。準備の成功をそれらの完成へ読み替えない。

## 現物からの判断

- `core/include/pikapika/dynamics.hpp`のWorldはbody/planeを所有し、const `bodies()/planes()` と `gravity` を公開する。mesh storage、revision、時計/ticksは持たない。ABIが別に持つ時刻を新Native照会へ混ぜない。
- `core/src/dynamics.cpp`の `add_body/add_plane` はIDを共通で検査・整列し、body1024/plane64まで受け入れる。一方 `find_body` のmutable pointerとpublic gravityで不正値を作れるため、照会時に全snapshotを再検証する。Worldへ追加済みという理由で現在の値を信用しない。
- RigidBodyはradiusによる**中心COMの球collision proxy**である。mass、principal inertia、q、world L/F/torque/materialを持つが、renderer mesh/box、非中心offset、一般凸形状を表すtagはない。新照会も宣言された球proxyだけを保証し、描画形状を検査したとは言わない。
- `sphere_triangle_mesh_free_flight_guard::query_body` は選択bodyをcopyするだけで、他body/planeを検査しない。単体の成功を全Worldへ拡張できない。
- `core/src/continuous_world.cpp`のW1はdynamic関与sphere対とdynamic×planeを全列挙し、既存flight tubeとaccelerated照会を使う。`free_flight_internal.hpp`のconst bridgeは同じflight返値を再使用できる。新guardはW1の応答/残時間/commitループを呼ばない。
- `accelerated.hpp`は点のnominal加速度による四次/二次式の全時間除外を返す。`Kind::none`だけを全区間strict非接触証拠として使える。entry/unresolved、初期境界、点witnessは成功でない。`trajectory_guard::audit`は別の定義した離散放物線と貫通許容を監査するため、この丸めfree-flight契約の代わりにしない。

**最小段は新World containerではなく、const World＋owned値型mesh sourceの全pair aggregatorとする。** Worldのadd/removeやserializationを先に増やすと、編集・material・transform・lifetimeの仕様まで広がる。まず全入力を一括所有し、必要pairを落とさず認証できる数値境界を作る。名前候補は `world_static_mesh_flight::query`。単体しか調べない関数をworld/all-pairと命名しない。

## 入力・所有・ID・revision

新header案の概念形（正式型は実装承認時に固定）:

```cpp
struct StaticMeshSource {
    std::uint64_t id;       // collider stable ID
    std::uint64_t revision; // caller-declared original revision, nonzero
    std::vector<sphere_triangle::StaticTriangle> triangles; // WORLD coordinates
};
Result query(const dynamics::World& world,
             std::span<const StaticMeshSource> meshes,
             double horizon_seconds, const Settings& settings = {});
```

Source値自体がvertices/face orderを所有する。queryはsource span、World gravity/全body/全plane、H、全設定を環境確認後に一括copyし、全preflightを終えてから数値照会する。以後はcopyだけを使い、caller pointer/span/World referenceを診断へ残さない。同期call中に別threadから入力を変更することは対象外で、constはrace防止を意味しない。

mesh IDはWorld body/planeと共通のcollider namespaceで一意、1..2^53−1。face IDはmesh内一意で同範囲、他meshとの重複は許可し、診断は `(meshId,revision,faceId)` で区別する。mesh IDをface IDと混同しない。revisionも1..2^53−1とし、stateless関数は増加履歴を検証しない。同revisionに別verticesを渡せるため、revision/hashだけで同一geometryやcache妥当性を証明せず、full source bits/orderをsnapshotへ固定する。

初段は静的・world座標のsourceだけ。transformを適用したlocal vertices、moving/deforming mesh、非中心sphereや実描画形状の自動変換はない。将来container/編集APIを導入する段ではcandidate sourceを全validate→新revisionでatomic replaceし、古いResultが新storageを参照しない受入を追加する。ここではその編集APIを作らない。

初期hard profile案は **World body8（静的込み）・plane16・mesh4・全mesh合計64faces、H∈(0,.1]s**。既存World最大1024/64より小さいことを明記し、超過を切詰めず事前拒否する。meshは1..4を必須とする最小縦断で、mesh無しの新APIを旧World guard代替として作らない。dynamicが0の入力は、全source/静的body/planeを検証したうえでdynamic pairが0というvacuous結果を明記する。static-staticの重なりを運動接触として誤失敗させない。

gravity、全body、全plane、全mesh、profile、H、全ID/重複を先に検査する。planeも元normal/offset/materialを全copyする。source invalidやcount/profile failureは数値pair未照会、snapshot有無/failed object kind/indexを明確にし、allocation prefixを普通の検証完了と混ぜない。snapshotはoriginal −0と全fieldsを保持する。

## 全pairの一覧を先に固定する

snapshotだけから次の必要pair全件をstable collider ID順に作り、**1pairでもunknown/未照会なら外側非接触成功にしない**。

1. 各dynamic球proxy × 全static mesh。
2. 各dynamic球proxy × 全World plane。
3. World sphere pairのうち少なくとも一方がdynamicの全組。static相手も省かない。

static sphere×plane、static/static sphere、static sphere×static mesh、plane×plane、plane×mesh、mesh×meshは時間不変のstatic-only pairとして明示的に除外し、kind別件数を保存する。これは全静的形状が互いに非交差という主張ではない。描画scene中の別形状を自動収集せず、保証はこの宣言済みproxy World/source集合に限る。

各PairRecordはkind、両collider ID、snapshot ordinal、mesh revision/source数、state（unexamined/returned/failed）、用いたbody flightの所属、完全な既存query結果、ローカル/総Workを所有する。mesh内の全保守ID・row/candidateを保存する。pair ordinalやfirst failureだけを返して後続pairを存在しなかったことにしない。通常のモデル失敗は可能な予算内で後続pairも照会し、fatal環境/未知work/allocationは停止して残りをunexaminedとする。

初段の最大pair数は `D*M + D*P + C(B,2)-C(S,2)`。B≤8/P≤16/M≤4から最大188、固定上限256で全一覧が収まる。件数計算にchecked integer arithmeticを使う。入力配列の置換でもstable key順のpairと真偽を維持し、snapshot元順へのordinal linkは別に保持する。

static-only件数は `S*P + S*M + C(S,2) + C(P,2) + P*M + C(M,2)`。必要pairとこの和が `C(B+P+M,2)` に一致することを監査する。最大28colliderの全378組のうち、D=8の必要188組とstatic-only190組を閉じて数える。全必要keyは保持し、除外組はkind別count＋全元collider一覧から再構成できる。除外378組までを256必要pair slotへ無理に詰めない。

## 既存guardを再使用する最小実装

dynamic×meshは既存 `free_flight_guard::query(body,gravity,triangles,H,settings)` をそのまま呼び、全Resultを所有する。古いWorldやglobalへ仮代入しない。各dynamicの最初のmesh照会からtube/endpoint/H候補のbody flight診断を得る。meshが複数なら、初段は既存guardを各pairで再実行し、成功返値同士のtube/candidate bits一致を監査する。重複したcopy/伝播の費用を隠さず、候補を一回だけ計算したと主張しない。

この選択は旧guardのbody-preparationを抽出して旧数値出力を変えるより変更範囲が小さい。将来cache/private helper抽出をする場合は別受入とし、既存100+補足4・旧W1 Native20/WASM全field bits・単体guard全入力を前後比較する。初段のために旧kernel/bridge/propagate_freeを複製・書換えしない。

保存順と実行順を分離する。まず全必要pair keyを固定し、**seed phase**で各dynamic bodyをstable ID順に、そのbody×最小stable mesh IDの既存pairを一度照会する。PairRecordへexecutionOrdinalを保存する。次に未実行のmesh pair、依存tubeを使えるsphere/plane pairをstable key順で処理する。seed済みpairを再照会しない。plane/sphere keyが保存順で前にあるだけで、まだ準備していないbodyをdependency failureにして安全sceneを落とさない。実際にseed/残meshで行った重複body伝播は全て実Workへ計上する。seed失敗で必要tubeが無い場合は依存pairを未照会として明示し、他の独立pairまで存在しなかったことにはしない。

同じbodyの元state、nominal A、B、roundoff、r_guard、endpoint・candidate・H/settingsが一致することをpair linkで確認する。最初のmeshが失敗してcandidateなしの場合、他pair診断を保持しても全scene候補を返せない。単体guardの成功candidateが後続pair失敗の診断中に残る場合は**局所候補**であり、外側の全body候補とは別である。

static bodyはbody.validateの既存条件を要求し、P固定/V=0/A=0/B=0としてpairへ入れる。静的force/torqueは保存するが自由加速度へ使わない。dynamicは実H candidateの全q/L/慣性/torque/material検査を単体guardに委ねる。全必要pair成功時だけ `candidateBodies` 全件を原body順で返し、staticは元bitsのcopy、dynamicは検証済みH候補とする。成功でもWorldや荷重をconsume/commitしない。

## sphere/plane pairの証拠と注意点

dynamic iのnominal pathを `p̄_i(t)=P_i+V_it+½aNom_i t²` とする。既存tubeのroundoff/Bは各representable durationの実並進branchとの誤差を囲み、B≥roundoffを監査する。sphere pairでは既存acceleratedにnominal point係数と `rGuard_i=up(r_i+B_i)` を渡す。両球の膨張和によるstrict `Kind::none` はnominal inflated pathsの全real秒非接触を証明し、各同durationの実丸め位置の非接触を含む。static相手は元radiusだけ。加速度を再び `g+F/m` のpointへ丸めたり、片方のBだけを加えたりしない。

**planeには既存二契約の差がある。** dynamics.hppのWorldは `n·p-offset ≥ r` と書き、add_planeは通常double norm²が1から1e-8以内を許す。一方acceleratedはraw normalの実normを囲み、球/半空間幾何に対応する `n·p-offset-r|n|` を使う。near-unitだから同じと仮定したり、通常doubleで正規化してexact unitへ昇格させない。

初段はplaneについて **両方をstrict証明**する。既存acceleratedのinflated sphere-plane全除外に加え、Worldのcenter predicateへ次の保守式を監査する:

```text
n·p̄(t) - offset - r - |n| B > 0    （World center条件＋位置tube）
n·p̄(t) - offset - |n|(r+B) > 0    （実halfspace/sphere幾何）
```

二つ目は上向きrGuardで呼ぶaccelerated noneが供給する。一つ目は新aggregator内の小さいInterval quadratic range監査と有限subdivisionで証明する。normは既存Interval square/sqrt_enclosureから外向きに囲み、upper×Bを引く。whole cellのlower>0だけを成功とし、point/端点だけにしない。使った各秒cell・predicate区間・norm boundsをPairRecordへ返す。これをしない実装なら、non-exact-unit planeを**unsupported**にする設計変更を先に相談し、全World対応を主張しない。

acceleratedのentry/unresolvedを元球の衝突・TOIへ変換しない。mesh側のinflated entry/initial overlap、sphere/planeの接線・初期境界・normal/品質失敗も、全sceneではnot_certifiedである。最初の衝突pairの順序付けや衝撃はこの段では計算しない。

ただし既存accelerated Resultはpositive cell transcriptを返さない。新段で「発行済み全cellをFraction監査」するには、**別の有界closed-cell coverage証拠をaggregatorが所有する**。sphereは既存 `sphere_sphere_value`、planeのmetric側は `sphere_plane_value` を各closed秒cellへ呼び、planeのWorld側は上の新Interval式も併記する。全必要predicateのlower>0だけをcertified leafにし、未知ならrepresentable内点で分割する。maxDepth/leaf/evaluation/storageを超えればnot_certified。全[0,H]のgapless被覆、各cell/predicate bounds/outcome、split/未照会tailを保存する。点検査や一つのnone summaryでleafを捏造しない。

この案ではaccelerated searchのnone診断と、別coverageのvalue呼出しを両方行う。**二重評価の実費**を分けてWorkに計上し、どちらか失敗なら認証しない。positive coverageには新scene-globalのstored cell/audit上限1024を置き、heldの1024auditとは別枠にする。value関数は証明用幾何式を既存C++から再使用し、参照checkerはKKTmask/Native判定を候補選択に使わず、各返却cellに対して原入力の有理多項式・norm平方不等式を独立監査する。旧accelerated内部frontierを回収したと主張しない。性能整理で一方を省く場合は後続の別受入である。

これらは宣言した幾何predicateと位置tubeの証拠であり、旧World solverの通常double接触検出やcontact_margin/slopが「接触なし」を返す保証ではない。strict正でも有限margin内に入る入力はあり得る。旧step/W1/W2をこの候補へ適用して衝撃を省略できるという接続は、別のguard/丸め/残差受入なしに行わない。

## 有限予算と全体状態

profileには `maxBodies/maxPlanes/maxMeshes/maxTotalTriangles/maxPairRecords` と、ローカル既存guard/accelerated設定、scene-globalの `maxMeshQueries/maxPrimitiveQueries/maxSqrtRefinements/maxAcceleratedEvaluations/maxPlanePredicateEvaluations/maxBodyPropagationAttempts` を置く。hard上限は上記8/16/4/64/256、sqrt16,777,216、accelerated/plane評価各1,048,576案。既存heldの各256audit/128partition等を全保持し、圧縮で末尾を捨てない。

**診断storageにも別のglobal予算が必要**であり、32mesh pairへ各256auditを無条件に蓄積しない。初期hard案は全stored audit1024、certified leaf1024、partition1024、frontier1024、lastMesh row512、candidate3584、メッセージ合計65536B。sceneのoriginal source64に加えて既存childが所有するsnapshot/lastMeshのsource copiesも別countで追跡し、全owned face copies1600を上限案とする。BodyRecordは最初のpair ordinalへlinkし、同じ巨大child Resultをさらに複製しない。

child call前にそのcallが返し得る**全**診断のworst（最大256audit/128leaf/128partition/128frontier、当該Nrow/7Ncandidate、source copies）とpair metadataのslotを予約する。足りなければ呼ばず、残りのtyped pair key全件をunexamined/budgetとして返す。**実sizeと保持capacityを別会計にし、返却後actual sizeが少ないだけでcapacity予約を戻さない**。local maxLeaves等を勝手に縮めたり、結果を先頭N件へ切る方法は使わない。既定childのaudit要求capacity256は安全なactual2件でも残るため、1024枠なら既定childは最大4個までの案である。最大8body×4mesh全safeはこのstorage案で完走できるという受入にせず、全key保持/未照会tail付きbudget失敗とする。初段の非vacuous成功は**2dynamic×2mesh＋plane/sphere全必要pair**とする。full32child成功はsizeof/payload/容量設計を確認した別受入へ残す。

さらにNative型の `sizeof` と保守的な各要素/所有buffer数から、call前のowned payload予約をchecked arithmeticで計算し、初期16MiB案へ収まるか確認する。これは論理payload budgetであり、allocator overhead・vector実装の一時容量・プロセスheap/stackの測定値ではない。厳密なheap上限を約束するには既存child内部allocationまで別監査が必要で、本段では主張しない。実装時の型確定後にcount/payload上限を再計算し、都合で上限を黙って増やさない。

mesh blockは旧guardの原本hard worst/当該local total budgetから保守的に全予約してから呼び、返却actual/upperで精算する。局所設定を残予算都合で黙って下げない。予約不足ならpairをunexamined/budgetとし、モデル照会を行ったことにしない。unknown Workは既知actualと予約upperを保持して全体停止する。global workExact=falseを全pair成功へ昇格しない。実装前にfree-flight/heldの全call pathからreservation boundを再確認し、推測の予約値でhard guaranteeを名乗らない。

acceleratedはmax_evaluationsの返却countを加算し、必要なら残global内のexplicit per-call grantを診断へ保存する。これは呼出profileの明示grantであり、時間/品質条件を緩めない。呼ぶ前にfull grantを予約し、throwでResultを受け取れなければknown returned=0/upper=grant/workExact=falseとして全体停止する。これは実使用0ではない。既存searchはcount増加後の式評価/allocでthrowし得てpartial Resultを返さない。新value coverageのcallについてもattemptと正常返却を分け、未返却cellの証拠を作らない。

plane norm helperの既存private反復はaccelerated Resultに公開countが無いため、それをsqrt実countへ捏造せず、1回最大64 loop-bodyと呼出件数を別のupper Workに記録する。追加plane value呼出しも毎回helperを構成し直すので、その費用を落とさない。新plane World式のsqrtは実refinement/limitedを全加算する。full scene counterは型別のworkを分離し、異種counterを一つの「root数」に混ぜない。

Result案はstatus/reason/failed object、optional snapshot、全body flight records、全pair一覧と全returned diagnostics、global work/known upper、skipped static counts、optional candidateBodies、message。`certified_separated`は全必要pairが返却済み・両plane条件を含む全非接触・全dynamic H候補監査・exact/global budgetが揃う場合だけ。**全必要pair認証後に限って外側candidateBodiesを構成・publish**する。unknown/unsupported/予算/失敗でcandidateBodiesはnull。既存childが途中で計算した局所candidateを外側へ先行公開しない。body tubeが無ければ依存pairをunexamined/dependency_failureとし、未実行をquery失敗へ偽装しない。環境firstでInterval defaultを環境検査より先に構築しない。allocation失敗時のowned diagnostic prefixと未照会を明示し、fault injection未実施を成功としない。

## 証明が及ぶ時間と及ばないもの

nominal inflated pathの連続実数秒上の証明と、同一初期bodyから各representable durationで行う**一回の**既存translation branchの包含を分ける。q/角運動/torqueを含むH候補はvalidateするが、全内部時刻の回転誤差や連続6DOF真解、各内部durationでの完全propagate_free成功を新たに保証しない。球proxyなので位置geometryは姿勢に依存しない。実非球形状に同じ証明を適用できない。

全bodyは同じ初期snapshot・gravity・global Hで独立自由伝播する。途中の衝撃・拘束・支持・接触によるforce変更がない仮定の非接触guardである。実World.stepやW1/W2を呼ぶものではなく、繰り返しsubstepの累積B、前tickからの誤差、時刻丸め、荷重再設定を含むとは言わない。r+Bの域外・angular increment・q/energy/candidate失敗を位置の非接触だけで無視しない。

## 独立受入と変更範囲

予定ファイルは新 `core/include/pikapika/world_static_mesh_flight.hpp`、新 `core/src/world_static_mesh_flight.cpp`、新Native test/fixture、独立Python checker/negative controls、CMake/CI/契約docs。旧World/body/serialization/SDK/engine/gameへstorageやmethodを足さない。親が正式型・ownership・global予約をレビューしてから実装する。

受入は次を満たす:

1. 全pair列挙を数学的件数とstable key集合から独立再構築。2dynamic×2mesh＋plane/sphere全成功を最小正例とする。8dynamic body/16plane/4mesh/64facesはsnapshot/全188必要keyの実保持と、容量不足時の未照会末尾の試験であり、既定32child全成功とはしない。この最大例は全collider組378＝必要188＋static-only除外190。bodyの一部がstaticなら必要/除外は上記D/Sの式で再計算する。最後のpair/row/candidate、総件数会計、順序置換、seed executionOrdinal、mesh ID/revision/face namespace、失敗後retryを試験。
2. 自由落下・異mass/F・相対sphere途中通過・静的球・斜plane・安全mesh/途中entry・異なる近接meshを用い、端点が安全でも途中交差があることを独立有理解析で確認。1pair失敗で他pairの成功や局所candidateがscene成功へ混ざらない。
3. Fractionで原F/m、nominal RN演算、B/roundoff、r+B上向き、各mesh既存Lipschitz certificate、aggregatorが別に所有するsphere四次/plane二次coverageの各closed cellを監査する。旧accelerated none summaryだけをFraction監査したとしない。固定dyadic解析と内点極値を含め、一般Sturm solverを無断で必須化しない。既存単体checker結果をSceneの全pair列挙正しさの代用にしない。
4. near-unit raw planeで `r` と `r|n|` の間に入る中心、片方のbody Bを落とす相対pair、F/m相殺、巨大共通offset、tangent/initial support、遠い退化mesh、invalid mutableWorld、局所成功後の別pair failureを負例にする。source/mesh/pair/ID/Work/coverage/candidate/tubeを改変したchecker拒否も保存。
5. World全fields/force/torque/gravity、元body pointer/順序、source全bits/−0/revision、旧DTOの前後一致。caller編集/破棄後もResult全source/candidate/診断が別所有。clockはNative Worldに存在しないことと、既存ABI時刻が未接続であることを区別。
6. strict Native/GNU warning audit、新kernel全依存instrument ASan/UBSan、RN-even/gradual underflow・fenv拒否後復帰、既存dynamics.cpp strict/noFMA build条件を保持。通常/strict/sanitized fixture bits、旧W1/単体held/guardの全原本回帰を照合する。使用heap/stack/性能は計測後にのみ記す。

これは既存singlebody guardの証拠を、**同一所有snapshotの全必要pairと全H候補**へ接続する実質的なNative段である。一般形状応答、衝突窓の全pair順序、manifold、反発/摩擦/支持、transactional World advance、専門車両/流体/材料損傷の完成ではない。以後それらを個別の保存量・仕事・残差・rollbackと結び付ける。

## 2026-11-04 予約/型の実ソース監査追記

ここからも**読取監査だけ**。新型のcompile/sizeof、allocator観測、fault注入、全pair実行はしていない。前節の容量値は実装承認前の案であり、以下の根拠と未確定を優先する。

### 返却pathとsourceの所有数

根拠は `sphere_triangle_mesh_free_flight_guard.cpp:102–170`、`sphere_triangle_mesh_held_load.cpp:130–253`、`sphere_triangle_mesh.cpp:38–81`。当該source面数をNとする。

| guard返却位置/保持stage | 返却時のStaticTriangle複製上限 | 備考 |
|---|---|---|
| environment/settings/body/H/source preflight前後 | 0 | world_bodyはbody/gravityのみ。guard snapshotはまだ無い |
| guard snapshot後、flight/derived/radius/propagation/candidate/endpoint失敗 | N | guard Snapshot.triangles。candidateは失敗finalizerでreset |
| nested heldの環境/初期preflight失敗 | N | optional inflatedがあってもheld snapshot無しの場合 |
| nested held snapshot後、mesh未照会/予約停止 | 2N | guard snapshot＋held snapshot |
| nested lastMeshのsource行を保持した返却 | 3N | 上記＋lastMesh.rows各Row.triangle。全履歴meshを保存するわけではない |

guard snapshotは `free_flight_guard.cpp:117`、held snapshotと各reserveは `held_load.cpp:152–153`、meshは `mesh.cpp:55–56` で全sourceをコピーしてからrow照会する。通常のrow failure後も全rowを続ける (`mesh.cpp:57–64`)。fatal時のrows/null queryを通常の失敗queryへ変換しない。返却sourceの順と−0をそのまま保持する。

**実行中は最大4N**になる。次のmesh `auto m=mesh::query(...)` を構築している間も、held Resultは前回lastMeshを保持する。`held_load.cpp:187` のnothrow move代入まで、旧lastMesh.rows Nと新m.rows Nが並存する。mesh result内の各queryのvectorはmoveでrowへ移るため、同時に全履歴分へ増えるとは数えない。

全source合計T≤64、dynamic D≤8なら、返却する旧guard全childを保存したsource copiesは `T+3DT≤1600`（Tはscene snapshot）。最後のchild中の新m用一時Nを加えたsource論理上限は1664。返却lastMesh rowは `DT≤512`、一時旧/新並存込み576。candidateは各row最大7なので返却3584、一時分を含む4032。これらは**要素数の上限**であり、vector.capacityやheap byte数の上限ではない。今後body record等へguard Resultをcopyすればこの式を破るため、const index link＋nothrow move所有を必須とする。

### size・reserve要求・実capacityは別

| vector | 原本の確定動作 | 返却size上限 / 予約会計 |
|---|---|---|
| held.audits | `held_load.cpp:153` reserve(max_evaluations)、:166 emplace | size≤E≤256。actual2でも要求capacity Eを保持 |
| held.partition | 同:153 reserve(max_leaves)、:231 split insert | size≤L≤128。予約L |
| held.frontier | 同:153 reserve(L)、:122–131 finishで全unqueriedを再構成 | size≤partition≤128。旧DFS33上限は使わない。予約L |
| held.certified_leaves | 同:153 reserve(L)、:218付近push | size≤partition≤128。予約L |
| held.candidate_surface_ids | 同:153 reserve(N)、:108 window時push | size≤N。window無しでsize0でも要求capacity Nを保持 |
| mesh.rows | `mesh.cpp:55` reserve(N)後source全copy | size≤N。Row内のoptional primitive Resultもinline storageに含む |
| mesh.nearest.possible_surface_ids | 同:72 reserve(N) | size≤N。nearest構築中の一時vectorとold lastMeshを別計上 |
| primitive.candidates | `sphere_triangle.cpp:80` **reserve(7)** | max_candidatesが1でも要求capacity7。通常/失敗prefix size≤7 |

`std::vector::reserve(k)` は少なくともkのcapacityを保証するが、portableにcapacity==kを保証しない。したがって「要求capacity会計」と実 `.capacity()*sizeof(T)` を混同しない。既存childはshrinkしない。返却sizeに精算して保存済みchildのmemory予約を返す案は撤回する。サイズだけを制限する別proof-record arenaを導入するなら新DTO/所有/複写の受入が必要であり、この計画に既実装として持ち込まない。

本案のheld audit1024要求slotでは既定E256のchild4個が限界。2dynamic×2meshはseed2＋残mesh2の4callで枠を使い、sphere/planeの**新coverage storageは別枠**を使う。最大8×4のkeyは作れても32child全診断を保持して成功するとはしない。新4-child成功例、最大key/budget-tail例、将来full32-child成功を別受入にする。

### 固定型とsizeof論理payload

実型は `sphere_triangle.hpp:38/48/62`、`sphere_triangle_mesh.hpp:18/24/32`、`held_load.hpp:54/103`、`free_flight_guard.hpp:40` にある。CandidateAuditはBounds3＋2個のKKT Interval等、Geometryは6個のBounds3＋3scalar Interval等。Bounds/optional/Geometry/Workはinlineだが、vector/stringが別allocationを持つ。RowのsizeofにはStaticTriangleとoptional primitive Resultの**inline Geometry/候補vector header**を含むので、さらにGeometry sizeofを重複加算しない。

既存guard一個のdynamic payloadを見積もる式は、メッセージを除き次を出発点にする（E/L/Nは**保持する要求capacity**、実capacityを採用した式も別に監査する）:

```text
2N*sizeof(StaticTriangle)                    // guard/held snapshots
+ E*sizeof(CellAudit)
+ L*(sizeof(PartitionLeaf)+sizeof(CertifiedLeaf)+sizeof(Cell))
+ N*sizeof(uint64_t)                        // held candidate IDs capacity
+ N*sizeof(mesh::Row)                       // lastMesh rows; source inline
+ 7N*sizeof(CandidateAudit)                 // primitive candidate capacities
+ N*sizeof(uint64_t)                        // lastMesh nearest IDs
```

これにfixed root `sizeof(guard::Result)`、外側Snapshot/body/plane/mesh ownerのvector storage、PairRecordの実型、全message、実行中の追加m rows/candidates/IDs、既存bridge/searchの一時storageを加える。もしPairRecordがguard Resultをinlineのvariant/optionalに含むなら、sizeof(PairRecord)で既に含めたfixed rootを再加算しない。sizeofはABI/standard library/targetで変わるため、**現時点でbyte値は未確定**。16MiBは測定済み値でもこの式の証明済み上限でもない。

正式型決定後、親の独立Native型監査programで `sizeof/alignof`、各vector requested/actual capacity、通常/失敗返却で保持するpayloadを記録し、sizeof式と照合する。これはまだ実行していない。allocator overhead、vector成長中の旧buffer、call stack、RSSをその数値へ混ぜず、別の観測/監査とする。全return pathでmessageには固定文だけでなく `std::exception::what()` があり、portableな最大文字数はソースだけでは確定できない。65536B text案のpre-call worstや、超過時にchild全Resultを保持できない場合の明示failure/診断方針も実装前に固定が必要。未確定の文字列/allocator上限をhard heap保証へ昇格しない。

### sqrt予約とunknown Work

- mesh queryはsingle sqrt呼出し一回/row（`sphere_triangle.cpp:124`）、各endpoint最大primitive.sqrt_refinements≤256。mesh worstはN×512。
- heldは各auditのmesh前にN×512、R/E各root前に512を予約する（`held_load.cpp:178/198`）。R/E入力はpoint(squared.upper())であり、shared sqrtは同一点なら一端点だけ精錬する（`interval.cpp:232`）。このより小さい実countを根拠に、**現行unknown-block予約512を変更しない**。
- audit E≤256なら保守的root上限は `E*(512N+1024)`、N64で8,650,752。local max_total budgetと各block pre-reservationが優先し、global予約は少なくとも当該childが保持し得るupperを覆う。正常返却では既存Workのactual/upperを合計する。
- `held_load.cpp:70–82` はmesh numerical_failure/null query/primitive numerical_failureをunknownとし、globalBefore+N512へupperを固定する。mesh内部は失敗row後も後続rowを実行するため、known returned workは**時系列prefixとは限らない**。unknown blockを含んでも既知counterが最大に達すればupper==knownとなり得る。
- R/E未返却ならknown+512を保持し、callsはattemptを含む。workExact=falseで全体停止し、後続pairへ余ったと推測した予約を渡さない。body propagationも `candidate_evaluated` がattemptであることを保ち、uncaught delivery failureなら一回予約の不確定上界を残す。

### acceleratedの返却しない情報と一時storage

`accelerated.cpp:120/122/165` はprivate `frontier,next` の2vectorを使い、各sizeはmax_frontier以下（:154で追加前検査）。clear/swapはcapacityを解放せず、二つのbufferが並存する。Resultにはどちらも、positive cellの時間boundsも返らない。論理Node数≤2Fは読めるが、各vectorの実capacityやgrowth中のbufferはこのsourceだけからportableなbyte上限を決められない。返却Resultをsizeofしただけではsearch一時storageを測れない。

`accelerated.cpp:101` はeval counterを増やしてから式を評価する。式例外やfrontier allocationでthrowするとpartial Result/counterは呼出元へ返らない。従ってfull eval grantをcall前予約し、throw時はattempt有り/Result無し/known returned0/upper grant/exactfalseで停止する。noneを捏造しない。normal helperは:49の最大64 loop-bodyで、search一回につきplane equation構成時一回、value関数は:175–184の各呼出しで再構成する。これは共有sqrt APIのrefinementsではない。

別coverageは証明cellを新aggregatorが所有するため、そのcell record・frontier・predicate evaluationに独立したglobal上限を設定する。旧searchの私有cellを埋めたり、その返却summaryだけでFraction全cell検証済みと記録しない。未返却eval、局所unknown、未照会tailの規約を新tests/oracleと先に合わせる。

### 実装承認までの残確認

prepare段のread-onlyレビューで、Vec3::dotはcore.cppの外部関数で現CMakeのstrict source指定外である点を確認した。現在の既定x64/有限corpus整合は、FMA可target全般の別RN境界保証ではない。後続guardはdynamics/interval TUだけでなく呼出先の全operation graphとcompiler flags・境界fixtureを監査する。prepareのために旧core.cpp flags/sourceを変更したとはしない。

1. 新Result/PairRecordと全固定/動的型の正式layout、nothrow move、requested/actual capacity会計、text超過failure規約を決める。sizeof測定はその後。
2. global1024 held要求slotで4-child成功、残32-childはstorage budgetというprofileを公開し、新coverage1024枠と混ぜない。全188key保持と最大入力の受理/成功を区別する。
3. seed→残mesh→依存sphere/planeのscheduler、executionOrdinal、全reserved/returned/unknown work、static-only総件数のoracle入力shapeを固定する。
4. source返却1600/一時1664、row512/一時576、candidate3584/一時4032という要素数と、型確定後のpayload式を同じ所有モデルで確認する。別copyを追加したら再監査する。
5. strict/sanitizer/allocator・fault分岐や新proof transcriptの試験を実施して初めて受入とする。この読取段ではいずれも未実行である。
