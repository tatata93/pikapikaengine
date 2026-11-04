# 加速球対/平面のclosed-cell非接触coverage案

2026-11-04 JST。**契約設計と受入方針。実装はローカル受入済み、公開GNU/sanitizer確認は次段**。型案は [accelerated_pair_coverage.hpp](../core/include/pikapika/accelerated_pair_coverage.hpp)。公開済みprepareは入力所有と全pair一覧を準備する段であり、まだこの非接触証拠を発行しない。既存World/全核/92-export SDK/engine/game/旧headerは変更しない。新依存/素材/license選択はない。初期設計は実ソースと以下の数学式から行った。その後、[著者のMIT公開教材1.3.1](https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node9.html)でBernstein基底の非負性・partition of unityを確認した。プログラム・図・本文は転載せず、新依存も追加しない。

## 目的・入力・認証条件

既存 `accelerated::sphere_sphere_value` / `sphere_plane_value` は、点binary64係数を厳密実数とした次の式をclosed時刻区間へ包含する。

```text
球対:   Φ(t)=|r+vt+(a/2)t²|²−(ra+rb)²                 [m²]
平面:   Ψ(t)=n·(P+Vt+(A/2)t²)−offset−radius |n|        [|n| m]
```

球対のr/v/aは元の二つの入力の実数差。planeは静的な負半空間 `n·x≤offset`、任意の非zero raw normalで、通常doubleの正規化でunitへ昇格しない。new helperは点係数と半径をそのまま使い、F/m構成、B膨張、World body/candidateを作らない。将来のWorld guardが用いる半径/nominal係数とraw World plane中心条件の追加証拠はcaller側の別責務である。

入力は既存point `accelerated::Sphere` 二つ、またはSphere＋StaticPlane。Hは最小段 `0<H≤.1s`。component/offset/radiusの既存有限1e12域（radius>0）を維持し、H以外の値を勝手に縮めない。SpherePair/SpherePlaneのvariantとH/settingsを全copyするSnapshotを持ち、environment拒否ではsnapshot無し、supported環境では**検証前のinvalid原本もcapture**して `snapshot_validated=false` とする。−0/全値を保存し、null診断を成功入力と混同しない。

certifiedとなる条件は、全closed `[0,H]` をgaplessに被覆する全partition leafが、**その全cell評価Intervalのlower>0**であること。全callが正常返却し、parent/split/workも整合していなければならない。端点・中点だけ、zeroを含むだけ、tol以内の接近では認証しない。接線/初期境界/negative interval/予算/未返却callはnot_certified。entry、TOI、接触面・衝撃・物理応答を生成しない。位置/時刻/荷重を進めない。

## 既存searchと費用を分ける

旧accelerated searchのResultにはpositive cellの時間帯・frontier履歴がなく、後からそれを取り出したようなpacketを作れない。本helperは**public value関数だけを呼ぶ独立した有界coverage**を正証拠にする案を推奨する。旧searchを内部で二重実行せず、履歴不足を補うために既存核を変更しない。

将来callerが旧none/entry診断と比較したい場合は、旧searchを明示的に別callして別Workに記録する。その結果を本helperへ補填せず、二重評価費用も省略しない。World全pair計画の「二重評価」案は、この単独helper採用が承認された後に親が依存順を更新する。helper単独の採用だけでWorld全pair guardを受入済みにしない。

## 有界探索と全所有診断

正式型案のhard上限はevaluation255・partition leaf128・depth32。既定は255/128/depth24、time_tolerance=1e-7s。frontierは全partition内unqueriedの全件、上限128。旧DFS33や旧search max_frontierを流用しない。追加point評価は行わないので、128leafの完全binary treeの全評価は最大255で収まる。

1. environment FIRST。ResultのdefaultにIntervalを直接構築しない。次に全原本をcopyし、設定→H→入力0/入力1の順に検証する。zero normalはcomponent比較で検査し、norm²のunderflowでnonzero normalを消さない。
2. auditsはmax_evaluations、partition/frontierはmax_leavesの容量を先に要求する。全root `[+0,H]` をinstallできてから `partition_complete=true`。初期allocation失敗/invalidで空配列を全被覆と呼ばない。
3. min-depth/同率左のunqueried cellを選ぶ幅優先。audit slotを置き、public value関数の**直前**にcall_attemptedとattempt counterを増やす。返却したIをそのまま保存してreturnsを増やす。geom/Hornerのどちらかの独自値へ置換しない。
4. lower>0ならpositive/certified。upper≤0ならnonpositive_valueでblockedにし、他のpending cellは照会を続ける。残りのIは不確定。全cell幅の外向きupper≤time_toleranceならwidth_limitで停止するだけで、成功へ変えない。停止優先順はwidth_limit→depth_budget→time_resolution→leaf_budgetとし、blocked理由を残す。幅差は `point(hi)-point(lo)` のupperで判定する（lo=0は既存Intervalのexact zero分岐を含む）。Fractionの真の差≤tolは必要条件であり、外向き幅の再照合は別metadata gateである。
5. 分割できる場合だけrepresentableなstrict内点を選ぶ。原global秒のendpointをそのまま子へ渡し、parent audit/split_timeを共有する。内点が作れなければtime_resolution。既存端点を再丸めして隙間/重複を作らない。
6. evaluation予算は選択cellをcurrentへ変えてからslot前に停止し、新auditは作らない。value throwはattempted=true/value無しのauditをblocked/value_exceptionへ確定し、currentと未照会tailを保持して全体停止する。最終結果にpending outcomeは残さない。全parent/audit/valueを保持する。通常blocked cellがあっても別pendingの証拠を収集し、全leaf認証以外はnot_certified。最終reasonは全体停止理由、または時間順の最初のblocked leaf理由とする。

AuditはCell（両端/depth/parent_audit）、attempted、optional value、outcome、blocked_reason、optional split_time。partitionは全leafのstate/audit link/reason。frontierとcurrentはそのowned viewであり、borrowed vector/spanや旧globalを参照しない。初期専用点audit/witness/safeUntilは作らない。全時刻は秒、rootからの閉被覆だけを保証する。

Workは**wrapperで正確に把握できる** value_calls_attempted / value_calls_returned を返す。throw時もattemptを戻さず、absent valueを0やwhole Intervalで埋めない。planeのprivate normal helperは非instrumentedなので、plane_norm_calls_upper=attempts、plane_norm_loop_iterations_upper=64×attemptsだけを返し、実refinementsと呼ばない。sphere対は両upper0。axis normalで実loop0でもupperは保守値のまま。allocator/stack/RSS/16MiBのhard保証はこの型案では主張せず、要求capacity/実capacity/sizeofは実装後の別観測とする。

## operation graphの読取監査

- `core/src/accelerated.cpp:15–22` は内部IVのinterval component演算とIV dotを定義し、**外部Vec3::dot/core.cppを呼ばない**。PairEquation/PlaneEquation（:69–94）はそのIntervalからgeom式と係数Horner式を作り、intersectionを返す。
- public value入口は同:179–184。search/frontierの:97–166を通らず、Equationを各callで再構築する。planeはnormal_magnitudeも毎回再構築する（:41–67、loop最大64）。std::hypot/libm sqrtを真のnormとみなす経路はない。
- Intervalの実mul/add/square/Horner/intersectionは `core/src/interval.cpp`。accelerated TUとinterval TUは現CMakeのstrict source listにあり、MSVC /fp:strict、GNU nofast/contractoff/froundingを指定している。現SDK builderにも両TUのnofast/contractoff指定がある。ただし新helperはまだSDKへ含めない。
- 新helper TUにも同じstrict条件を登録し、flags/environmentを実buildで監査する。RN-even/gradual underflow・no contractionを保つ。上の事実は新cppをbuildした証拠でも、全compilerの形式検証でもない。prepareで判明した外部Vec3::dotのflags境界を無断で直したことにはしない。

## 独立Fractionで全返却Iと被覆を検査する

単にNativeのgeometric/Horner結果の一方を通常doubleで再計算したり、有限sampleを全時間と呼ばない。入力とI端点を元binary64の厳密Fractionへ戻し、**Iが真の式rangeを含むか**を次の方法で監査する。intersectionがvalidな二つの包含の共通部分になる点を踏まえ、独立な粗いInterval rangeがIへ入らないだけでNativeを不正と判断しない。

- **plane**: `q(t)=n·(P+Vt+A t²/2)−offset` は有理二次。各cellの端点と域内停留点からqの厳密min/maxを得る。N=n·n、r>0に対しI=[L,U]の包含は `qmin−L≥r√N` と `qmax−U≤r√N`。符号を先に確認し、非負両辺を二乗した有理比較で証明する。√Nをdouble中央値へ丸めず、負側を無条件に二乗しない。
- **sphere**: 元入力差から四次polynomial ΦをFractionで展開する。各Iについて `Φ−L≥0` と `U−Φ≥0` をcell全域で証明する。次数≤2なら端点/停留点で直接比較。四次はrational Bernstein係数の非負性（basis非負・和1）と有理区間分割を使う。zero polynomial、端点因子、gcd(Polynomial,derivative)による偶数多重因子の除去を別処理し、接線の厳密zeroを任意epsilonで通さない。有限checker予算内で非負証明できなければ**checker未解決/失敗**であり、Native Iや入力を広げて通さない。一般quartic/Sturm solverの完成をこの段の前提にしない。

これでcertified leafだけでなく、blocked/負/不確定の**全正常返却audit I**を監査する。全parent/split/partition/frontier/current・BFSの選択、attempt/return差、strict positive条件、停止幅の正確なFraction差、未照会tailを別の組合せ監査で再構築する。geometry包含検査とmetadata replayを一つのテストに潰さない。例外を人工wireで作る試験と実faultを混ぜず、元value関数へqueryしたactual経路かを明示する。

数学的包含とは独立した**public value原本のprovenance gate**をNative試験に設ける。全正常返却auditについて、同じsnapshotとcellを既存public valueへ直接再照会し、I両端の全binary64 bits（−0を含む）が保存されたことを比較する。geomだけ/HornerだけのIも数学的には正当な包含になり得るため、包含oracleだけでは一般にその置換を拒否できない。実public intersectionより広いが数学的にvalidなIの改変は、このgateでactual返却Iと異なる場合に拒否する。同一bitsなら改変とは判別できない。

固定corpusには静止/異加速度/平行/高速途中通過/接線/初期境界/初期負、相対位置のlost-low-term、巨大共通offset、非unit/非有理norm、−0/denorm、非有理stationary minimumの四次を含める。正例はroot一件だけでなく実subdivision全被覆を含む。偽I（endpointだけを含み内部極小を除く、plane符号を落とす）、leaf/parent/tail削除、positive偽装、attempt巻戻し、upperをactualとする改変を負例にする。

## capture・allocation・例外の固定境界

Snapshot/InputはSphere/StaticPlane・double・Settingsだけの固定サイズ型である。supported環境での全copyは動的確保を必要とせず、nothrow copyのstatic_assertを実装する。環境拒否はsnapshot無し。設定→H→入力順の検証失敗はsnapshot有り/validated=false/root無しであり、完全であることとvalidであることを分ける。全入力検証後はvalidated=trueとし、3vector reserveのどれかが失敗してもroot無しのままallocation_failureを返す。

rootをinstallする前にaudits(max_evaluations)、partition(max_leaves)、frontier(max_leaves)を全reserveする。cell/audit/optional Intervalはnothrow copy/moveでき、root後のwrapper通常経路ではcapacityを超えない。splitは全停止条件を検査してからbounded assignmentで2子をinstallする。最終frontierはpartition内unqueriedだけをcapacity内へcopyし、currentは含めない。したがってfinalization用の追加vector確保を行わない。例外メッセージassignはnoexcept fail内try/catchで囲み、失敗ならclearしstable enum/owned診断を保持する。Resultの返却moveもnothrowを検査する。これはwrapperの記録用確保に関する設計であり、例外生成/ランタイム/allocator内部を含むprocess-wide無確保保証ではない。

public value用time Intervalの構築を終えてからattemptを増やし、その直後にpublic関数を呼ぶ。正常returnを受けた時点でreturn countを増やし、Iをcopyする。後続widthやmetadata処理の例外でreturn countを巻き戻さない。value呼出し内のthrowはvalue_exception、それ以外のbad_allocはallocation_failure、想定外の内部例外はcoverage_inconsistentで全体停止する。いずれもcurrentを未照会へ戻さず、pending auditをblockedへ確定してpartitionとtailを保持する。途中の外部FP環境変更を安全な利用として主張せず、環境異常がvalueからthrowした場合も認証へ進めない。

## 受入手順と残件

このheaderのstatus/reason、255/128 bounds、Workとvalue-only方針は親が承認した。新cpp・専用Native fixtures・独立checkerを別所有で実装し、Native43CTest/69群/65入力、全1913区間の独立数学、自己14群/拒否53、Node684/skip0でローカル受入した。旧value/既存核はbyte保持し、strict/GNU warning/sanitizer・通常/sanitized全fixture bits・環境拒否/復帰・原本/旧DTO別所有・max255audit128leaf/未照会tailを検査する。自然に届かないallocation/未返却callは未実施と記録する。

先行World準備はtyped pair/sourceの所有までであり、B膨張/World raw planeの別predicate、全pair予算、全body候補の認証・公開は後段に残る。既存SDKやゲームを更新しておらず、公開確認は未実施。ローカルの原本・実行・失敗履歴は [受入記録](../reports/2026-11-04-accelerated-pair-coverage.md)に保存する。
