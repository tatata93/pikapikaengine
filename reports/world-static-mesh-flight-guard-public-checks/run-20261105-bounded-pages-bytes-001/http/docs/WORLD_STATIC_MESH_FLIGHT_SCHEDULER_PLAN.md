# World flight advance用transaction-aware固定tick scheduler計画

2026-11-05。**次のNative単独段の契約案。schedulerは未実装・未ビルド・未実行。** 草稿作成時はGNU advance検証が進行中だった。その後の `GNU_FINITE_ADVANCE_PASS` は[別receipt](../reports/world-static-mesh-flight-advance-gnu-verification.json)を正本とし、このschedulerの検証と混同しない。公開全体の受入は親の正式記録に従う。既存 `FixedClock`、7-source advance／guard構成ID、C ABI／SDK artifact、ゲーム、既存CMake／CIは変更しない。[advance計画](WORLD_STATIC_MESH_FLIGHT_ADVANCE_PLAN.md)の失敗原子的な一tickを、明示したelapsed creditへ接続する。

## 実読した接続境界

| 既存ソース | 今回確認した振る舞い |
|---|---|
| `core/include/pikapika/core.hpp:39–50` | FixedClockはstep／accumulator／dropped／tick countを持ち、callback型は `void(double)`。 |
| `core/src/core.cpp:96–115` | `advance` はelapsedを先に加算し、`accumulator + step*1e-10 >= step` でcallbackを呼ぶ。正常復帰後は結果にかかわらず減算・tick加算。max_steps後のwhole backlogはfmodで破棄する。 |
| `tests/core_tests.cpp:44–54` | 既存30／60／144Hzの有限例と過負荷時drop表示を検査する。これらの既存仕様を置換しない。 |
| `core/include/pikapika/world_static_mesh_flight_advance.hpp:15–99` | Progressと完全owned AdvanceReport、失敗時advanced_dt=+0、全bodyとProgressの一括commit、成功時の荷重消費を定義する。 |
| `core/src/world_static_mesh_flight_advance.cpp:133–168, 373–434` | 時計事前検査、内部guard一回、private候補／全source検査の後にnoexcept commit。失敗Reportの通常復帰もあり、void callbackへ渡すだけではFixedClockが失敗tickを消費する。 |

失敗を例外に変換して旧FixedClockの消費を偶然止めるadapterは採用しない。今回は旧clockに互換branchを足さず、独立した小さいNative schedulerが**実advanceの `committed` を見て**creditを消費する。新しい幾何solver／guard helperは追加しない。

## 最小入口と所有

新namespace／header／cppの候補を `world_static_mesh_flight_scheduler` とする。正式型は実装着手時に固定する。以下は契約を示す擬似signatureであって配置済みAPIではない。

```cpp
Scheduler(Settings); // 有効設定から作る。World／Progressを所有しない。
PumpReport pump(World&, span<const StaticMeshSource>, const GuardSettings&,
                Progress&, double elapsed_seconds) noexcept;
SchedulerSnapshot snapshot() const; // owned値のみ
```

Schedulerはprivateな固定step・represented backlog・pump sequence・busy状態を持つ。copyによる未処理creditの複製を禁止し、初段はcopy／moveとも不可とする。stateの読み取りはowned scalar snapshotとし、外部からaccumulatorへ直接書き込む経路を作らない。World／Progress／mesh／settingsへの永続referenceやpointerを保持しない。callerは同じschedulerを一つの論理World／Progressの時間供給に専用とし、並行／再入アクセスやcreditの別Worldへの移送を行わない。

初段は任意callback、per-tick callback、外部candidate入力、途中のload供給hookを設けない。呼出し中はWorld／Progress／mesh／settingsの同時read/writeをcallerが排除する。busy guardは同じschedulerへの再入を入力受理前に拒否するためのもので、thread／signal安全なlockや複数scheduler間のWorld競合検出器ではない。非同期signal handlerからの利用は対象外。

## 設定・秒・creditの意味

初段の固定案は次の通り。実装時に値を黙って広げたり、成功のためstepを短くしたりしない。

- `step_seconds`：binary64既定 `1.0/120.0`、有限 `2^-20 <= step <= .1`。表現されたstepそのものを**毎回同じbitのH**としてadvanceへ渡す。正確な実数1/120と同一とは呼ばない。
- `max_attempts_per_pump`：既定4、hard最大8、1以上。成功と拒否の両方をattemptとして数える。
- `elapsed_seconds`：有限 `[0,1]`。`-0`は入力診断へ保持するが、creditへの加算は+0と同じ。NaN／Inf／負数を拒否する。
- represented backlog：初期+0、有限 `[0,1]` 秒。frame先頭の `credit=RN64(backlog+elapsed)` が範囲外なら、そのelapsedを**一切受理せず**全状態を保持する。過大入力をclampして受理しない。
- Progressの域とtick上限は既存advanceに従う。scheduler独自のtime／tickをWorldの真時計として並立させない。

backlogは**binary64の時間credit ledger**であり、入力elapsedの実数総和と厳密一致する時計ではない。加算・成功tick減算の各RN差を、commit前に外向Interval診断として保存する。会計は `C=RN(B+e)`、`Cnext=RN(C-h)` と各stored rounding errorから再構成できる。長期間の累積実時間誤差、全render rateで完全に同数tickになること、時間許容値から空間精度を保証することは主張しない。厳密な実数creditや有理120Hz時計は別段である。

具体的には `δadd=C−(B+e)`、各成功tickの `δsub=Cnext−(C−h)` を既存Interval演算で囲む。k回成功後のexact-real会計は `Bfinal=Bbefore+e−k*h+δadd+Σδsub`。拒否／未実行tickのproposal誤差をこの和へ入れない。elapsed未受理ならeもδaddも適用しない。参照checkerは保存値のRN bitsと各区間包含を検査し、widthを時間消費の許容誤差として使わない。Progress側の表現時計差と要求Hも既存Reportどおり別物として保存する。

due判定はrepresented `credit >= step` だけとし、旧clockの `step*1e-10` 等のepsilonを使わない。ただしRN加算自体が閾値へ丸まることはある。exactな `B+e < h` からRN値がhになる例も独立参照で検査し、これを「真の経過時間がh以上だった」と説明しない。初段ではこの明示されたrepresented-credit方針を採る。

## retain-only：拒否tickを消費しない

初段のpolicyは**retain-only**。自動fmod、frame上限後のwhole tick破棄、clampによるdrop、背景catch-upを設けない。各PumpReportへ `droppedSeconds:+0` とpolicyを必ず出す。上限で返ったcreditは次のpumpへ残す。drop機能を後で作るなら、明示入口・元backlog・捨てた量・理由・残量を別transactionで受け入れる。この段で未実装のdrop APIを説明しない。

入力elapsedの受理と、tick成功は別のcommitである。

1. 環境／設定／再入／入力域／全診断slot／credit計算を検査する。この段の拒否は `elapsedAccepted=false`、World／Progress／scheduler全値不変。
2. elapsedを一回受理してcreditをledgerへ置く。`elapsedAccepted=true` を返却値へ固定する。tickが一度も成功しなくても、受理済みelapsedを再加算しない。
3. due tickごとに現在のWorld／Progressから実advanceを一回呼ぶ。**`committed=true` のときだけ**そのtick用に準備したcredit減算をstoreする。
4. 最初の拒否Reportで停止する。そのattempt直前のWorld／Progress／backlogを保つ。拒否したstepを消費せず、同じpumpで再試行・H縮小・旧stepへのfallbackを行わない。
5. 全due tickを終えればwaiting、attempt上限でまだdueならstep_budgetとする。両者とも自動dropは0。

例えばB=0、elapsed=3hで一tick成功・次tick拒否なら、WorldとProgressは**成功prefix一tick分だけ**進み、backlogは約2h（明示RN会計）を保持する。frame入口へrollbackしたとは呼ばない。外側statusは `tick_rejected`、`committedTicks=1`、拒否Reportを保存する。`frameFailureAtomic=true` というfieldは設けない。

再試行は `elapsed=0` で現在backlogを処理する。callerは `elapsedAccepted` を確認し、同じelapsedを重ねて供給しない。APIはネットワークのexactly-once配送や同じ引数の再送検出を保証しない。入力受理前の失敗なら、元elapsedを再提出できる。

backlogがstep以上の状態を `alpha` と呼んで0..1に見せない。raw backlog秒と `hasWholeTickBacklog` を出す。将来描画向けfractionを出す場合も、遅延中のinterpolation／clampは別の表示policyとし、未実行tickの実時間進行を捏造しない。

## commit前準備と返却値

返却値は `PumpReport` の全scalar原本、入力elapsed、受理前／受理後credit、終了backlog、pump順序、入力受理flag、停止理由、attempt数／成功tick数、元／後Progress、最大8個の**実AdvanceReport**を所有する。各attemptはcreditBefore／proposedCreditAfter／実消費flagとRN差診断を持つ。failed Reportの完全owned guard、message、work、reservation、全tailも落とさない。未実行slotを成功Reportやゼロworkとして埋めない。Reportに借用span／pointerを残さない。

固定slot配列（optional×8）を使い、outer診断保存のためのvector増設・文字列生成を成功tick後へ残さない。入力受理前に、最大attempt分の**queue arithmetic plan**をすべて準備する。各候補減算が有限・非負でcreditを厳密に減らすこと、Interval診断が有限であることをここで確認する。候補queue値は未実行／拒否tickの消費を意味しない。

実advanceのreturnと、そのReportを空slotへ移す操作、成功時のbacklog／counter store、PumpReportのreturn moveはnoexcept条件をstatic assertionで確認する。advanceは既存noexcept境界をそのまま呼ぶ。入れ子のvector割当等がadvance内部で失敗した場合は実失敗Reportを受け取り、成功済みprefixを保って止まる。外側はその失敗を例外成功へ変換しない。新しい非規範messageを後から割り当てる必要があるなら固定enum／既に準備した値で表現する。

事前準備の例外はelapsed未受理のtyped失敗。成功prefix後にframe全体無変更を返すcatchは禁止する。unexpectedな外部故障からのhardware crash安全や、他threadに中間storeを見せない保証は対象外。浮動小数点環境を変更して戻す実装にもせず、対応RN-even／gradual-underflowを入口で要求する。

## 数値work・storage・荷重

attempt数最大8により、各advanceの全必要pair／子query予算の繰返し回数も有限になる。各attemptは同じ入力GuardSettingsを用いて新しいguardを実行し、前tickのcertificate／B／candidateを再利用しない。外側は全attempt分のworst work grantとlogical retained上限を**整数のchecked積**で先に算定し、返却known／upper／exactを個別保存する。unknown workを0へ置換しない。

初段は「8回まで」という制限と、既存per-call限度から得る保守的な積の予算で開始する。成功したactual workが小さいからといってattempt slotや保持診断枠をrefundして9回目を呼ばない。将来別global work上限を追加する場合も、呼出し前full grant、unknown nonreturnのupper、未照会末尾を定義する。guardのlogicalPayloadBytesだけでReport全体の実heapを上限化しない。fixed配列・全子vectorのsizeof/capacity・実際の保持量を測定し、allocator overhead／RSS／used stackのhard保証は別問題として残す。

成功advanceはforce／torqueを全bodyで一回+0へ消去する。したがって一pumpで複数tick進む場合、外部で積んだ荷重は最初の成功tickだけへ適用され、その後は消去済み状態から新queryになる。gravityはWorld原値のまま。frame内ずっと同じ入力力を保持したいゲーム制御を、このcallback無しの最小schedulerが代行するとはしない。後続のper-tick control packet／入力適用transactionを別受入とし、今回勝手な荷重再投入を行わない。

## Native単独の有限受入

以下を新scheduler用の完全fixtureへ保存する。件数／最終status分布／性能は実行後に確定し、既存9群や18時計を新scheduler実行の代用にしない。

| 場面 | 独立に必要な確認 |
|---|---|
| 既定120Hz設定と正確dyadic stepの0／1／複数due tick | 整数／Fraction RN参照でcredit加算・各減算・due分類・rounding enclosure・末尾会計を照合。閾値前後nextafter、−0、subnormal elapsedも含む。 |
| 最初のguard拒否 | elapsed受理flag、実拒否Report一つ、World／Progress／荷重／pointer不変、credit減算0。retry elapsed0でも二重受理しない。 |
| 一tick成功後に後続が接触帯へ到達して拒否 | 非空Worldの解析plane例等を固定。実成功prefixだけの全body／Progress、後続failureの現原本、保持backlogを保存。frame全体rollbackと誤認しない。 |
| 上限4（別設定8）成功後もbacklogあり | attempt数上限、全Report、未処理時間、drop+0。次のelapsed0呼出しで現Worldから実行を続ける。 |
| 非零held力／torqueで複数成功tick | 最初tickだけ荷重消費、以後zero-loadでの解析運動と全candidate／実body対応。守られた全source／raw plane／gravity／addressを検査。 |
| backlog cap超過、負／非finite elapsed、設定不正、busy拒否、env／新TU構成拒否 | 受理前失敗はscheduler／World／Progress無変更。Native-only非finiteはJSON数値へ偽装しない。busy人工注入と自然再入試験のscopeを区別。 |
| Progress tick／time上限、途中allocator／child failure | 実advance失敗を伝播、成功prefixと実未照会を保持。このschedulerの最小stepはtime域上端のULPより大きいため、合法設定のtime吸収を自然到達caseとして要求しない。微小H吸収は既存advance時計原本に残す。allocation／nonreturnは注入していなければ動的故障試験成功と呼ばない。 |
| callerの再試行とsource編集 | retry0と新elapsed供給を区別し、毎attemptの実owned source／settings／guardを保存。修正前の失敗証拠を後続成功で上書きしない。 |

数学childは既存独立guard checkerへ**実返却guardだけ**を再包絡する。schedulerの会計参照はNative結果から答えを作らず、binary64 bits→整数／FractionでRN、due判定、closed counter／queue順序を再構築する。全World／Progressの前後と成功candidate＋荷重消去をbit比較する。消費flag改ざん、拒否後credit減算、成功prefix省略、drop偽装、unknown work削除、同elapsed二重計上、負零消失、古いguard差替等の負例を用意する。実装／参照／provenanceの共通ミスを避け、個々のgateを分ける。

## 統合順と未完

最初は新Native header／cpp／test／全transaction fixture／独立会計checkerだけ。旧FixedClockのtestsを維持し、新scheduler TUへstrict binary64／no contraction／no reassociation／非LTOと対応環境を明示する。**旧7sourceSetとbuildIdの計算対象を変更せず**、advanceの実bindingを各Reportへ残す。scheduler自身のsource／compiler／actual command／構成identityは別のprovenanceとして保存し、旧7sourceの監査が新credit算術まで証明したとはしない。対応外scheduler構成は拒否し、caller boolでunlockしない。

MSVC／GNUの有限Native・独立RN参照・負例・新TU warning拒否・全依存sanitizer・旧7source／SDK全bit互換の後で統合判断する。全clock／commit機械形式証明、実時間deadline、背景実行、SDK／JS、ゲームの実fixed update、FixedClock置換、接触応答／支持摩擦は今回の完了条件に混ぜない。既存SDK artifact・export・license／素材／外部依存も追加しない。
