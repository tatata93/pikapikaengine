# World静的mesh自由伝播の失敗原子的advance計画

2026-11-05。**次featureの試作契約。Native header/CPPを配置し、別ビルドで9群と時計18例の有限動作試験が成功した。本体統合・新構成実命令監査・正式受入は未完。現在のWorld guardの機能manifest・ローカル／公開receiptへ含めない。** 現段の [read-only guard](WORLD_STATIC_MESH_FLIGHT_GUARD.md) が所有する全候補を、実Worldと明示的な進行時計へ一度に反映する最小段を定義する。新しい数値前提helperを連鎖して追加せず、既存guardの証拠・候補・source-enforced bindingを使用する。[試作実行記録](../reports/2026-11-05-world-static-mesh-flight-advance-prototype.md)と正式公開受入を区別する。

[原著概念図](learn/diagrams/world-static-mesh-flight-advance.svg) は処理順と境界の説明であり、実行trace・性能図ではない。原著図は実ローカルブラウザーで上下表示を確認し、Native数値検査と別scopeの画像記録へ保存する。

## 接続できる既存箇所

以下は2026-11-05に実ソースを読んだ根拠であり、新APIの受入結果ではない。

| 実ソース | この計画で利用する事実 |
|---|---|
| [dynamics.hpp](../core/include/pikapika/dynamics.hpp) の `World`（97行付近）、[dynamics.cpp](../core/src/dynamics.cpp) 201–202行 | Worldはbody／plane／gravityを持つが時計を持たない。`find_body` は既存body格納先のmutable pointerを返す。 |
| dynamics.cpp 258–269行 | 通常stepは全候補を別vectorで作り、force／torqueを消費してから既存body格納先へcopyする。 |
| [continuous_world.cpp](../core/src/continuous_world.cpp) 385–387行 | W1も全bodyの荷重を消去・検証後にcopyし、成功時だけ `advanced_dt=dt` を返す。 |
| [supported_world.cpp](../core/src/supported_world.cpp) 260–263行 | W2は全検査後の割当なしcommitでbody addressを保持する。 |
| [world_static_mesh_flight_guard.cpp](../core/src/world_static_mesh_flight_guard.cpp) 500–507行 | 全必要pair／seed成功後だけ、全bodyのowned `candidate_bodies` を返す。失敗では候補を公開しない。これはWorld更新ではない。 |
| [simulation_api.cpp](../core/src/simulation_api.cpp) 103行、248–251行、1527–1562行付近 | SDK側はWorldと別にtime／ticksを持ち、W1／W2成功時だけ候補stateの時計を進めてcommitする。 |
| [core.hpp](../core/include/pikapika/core.hpp) の `FixedClock`、[core.cpp](../core/src/core.cpp) 99–115行 | `void(double)` callbackの正常復帰後は、結果を検査せずaccumulator消費・tick加算を行う。 |

既存SDK・World::step・W1／W2・FixedClockをこの段で置換しない。Native新入口を独立して検証する。ゲーム／scene／別チャットの変更を上書きしない。

## 入口と所有する返却値

配置済みの [試作header](../core/include/pikapika/world_static_mesh_flight_advance.hpp) は `pikapika::world_static_mesh_flight_advance` に次を宣言する。宣言の存在と実装受入を区別する。

```cpp
struct Progress { double time{}; std::uint64_t ticks{}; };
AdvanceReport advance(dynamics::World& world,
                      std::span<const StaticMeshSource> meshes,
                      double horizon_seconds, const GuardSettings& settings,
                      Progress& progress) noexcept;
```

`Progress` はNative Worldに存在しない時計を明示する小さい値型。SDKのWorldStateやFixedClockとの接続済みを意味しない。入力は同期呼出し中だけ借用し、返却値へpointer／span／referenceを残さない。guardが既に持つ上限（body8、plane16、mesh4、全face64、全体work／retained予算）をそのまま使用する。commit用bufferとdestination pointer配列もbody上限8で有界とし、guard予約とcommit側の小さい追加storageを区別する。allocator全体のheap上限は主張しない。

Reportは少なくともstatus／reason、`committed`、`requested_dt`、`advanced_dt`、元と提案Progress、optionalな完全owned GuardResultを持つ。失敗時の `advanced_dt` は必ず `+0`。元の `requested_dt`／Progressの負零を勝手に正準化しない。失敗位置はclock／guard／candidate-validation／commit-preparation等を区別する。割当失敗時に巨大診断を必ず保存できるとはせず、保存済み証拠と未返却を区別した最小失敗値を返せる形にする。

試作の `ClockAudit` は `time_sum`、`represented_difference`、`sum_rounding_error`、`represented_dt` を所有する。`CommitWork` はguard attempts／returnsと元source・候補・宛先の検査数、最終body／Progress store数を分け、失敗時の両store数を0とする。`CommitStorage` は固定bufferのslots／sizeof観測であり、guardの予約・heap上限とは別である。環境受入前にIntervalを作らないoptional形を維持する。

**古い外部certificateを受け取るcommit入口を作らない。** 毎回、現在のWorldとsourceからguardを入口内部で一回だけ呼ぶ。別の時点で取得した候補を現在Worldへ適用する経路、revisionだけで形状同一とみなす経路を設けない。証拠を再利用して伝播したふりをせず、guardが実際に計算した候補を使用する。全childの数値workと、commitのcopy／検査を別に記録する。

## 全失敗可能処理を終えてからcommitする

1. 実行環境と既存source-enforced bindingを確認する。caller boolで監査済みにせず、未対応profile／identity／環境は拒否する。現在guardの機械監査済みtargetと同じartifact／strict演算条件を引き継ぎ、新入口の時計演算にも既知のbinary64評価条件を設定する。未検証targetを有限入力の成功だけで昇格しない。
2. ProgressとHを検証し、提案時計を計算する。clock不正／overflow／非進行では数値child未照会で返す。
3. guardを一回呼ぶ。`certified_separated`、全pair／全body候補の完備、exactな必要accountingを要求する。不認証・予算・例外・unknown workでは全体失敗とする。read-only失敗証拠の全tail／依存失敗を保存し、成功prefixだけを進めない。
4. 全候補からprivate commit bufferを作る。全ID／元ordinal／件数／static属性と準備snapshotの対応を検証し、全destinationを先に解決する。現在Worldの格納順・body原値・gravity・raw planeがguardの元snapshotに対応することもcommit前に確認する。同期中の外部変更を許容するための競合検出器ではない。
5. private bufferの**全body**のforce／torqueを `+0` vectorへ消去し、全bodyを検証する。動的／静的とも既存public tickの消費規則に合わせる。証拠内候補や元snapshotの荷重を消さず、commit bufferだけを変える。位置／速度／向き／角運動量／mass／inertia／material／ID等は認証候補の全値を保持する。
6. 返却Reportの全証拠所有・診断・metadata・移動準備を終える。copy／move／returnに必要な型のnothrow条件を実装で検証する。`RigidBody` copy assignmentとReportのmoveがnothrowであることをstatic assertion等で確定し、destination書込開始後に割当、validate、検索、文字列生成、失敗可能な処理を残さない。
7. 全destinationの既存格納先へ全bodyをcopyし、最後にProgressのtime／ticksを格納する。vectorのswap／再確保で既存body addressや順序を変えない。完了Reportをnothrowで返す。

これは**単一同期呼出しの失敗原子的transaction**であり、thread／hardware atomicな複数storeではない。callerは全期間、World／source／Progressへの並行read/writeとreentrant mutationを排除する。commit途中の観測を許容する契約ではない。最初の実World書込以後にcatchして「失敗なので無変更」と返す実装を禁止する。最終commitをnothrowにできなければ、その実装を受入しない。

すべての失敗は実World全field・荷重・gravity・raw plane・source・body address／順序とProgressをbit不変に保つ。候補の一部commit、勝手なH縮小、部分時刻進行を行わない。旧step／W1／W2へ自動fallbackしない。それらにはこの静的meshの応答経路がなく、fallback成功はmeshを含む認証の代用にならない。

## 秒・時計・荷重の意味

Hはguardと同じglobal秒の有限 `(0,.1]`。ProgressはSDKの既存慣例に合わせ、有限time `[0,1e9]`、整数ticks `[0,2^53−1]` を計画域とする。成功にはticksが上限未満、`newTicks=ticks+1`、`newTime=RN_binary64(time+H)` が有限かつ上限内で `newTime>time` を要求する。巨大timeに小さいHが吸収される場合はtime_resolutionとして全体無変更にする。timeの元 `−0` は診断へ保つ。

`advanced_dt=H` は実行した自由伝播の要求区間を表す。**表現時計の `newTime−time` がHとbit一致するとは限らない。** Reportには提案timeと表現時計差を別に保持し、必要な和／差の外向区間診断も既存interval演算でcommit前に確定する。累積timeの厳密実数一致を主張しない。独立時計検査は整数／FractionによるRN参照と区別する。

成功した一tickだけが保持荷重を一度消費する。失敗後の再試行では荷重が残り、成功後の次tickでは消去済み荷重から改めてguardを呼ぶ。static bodyの原tiny velocity／angular momentum等は候補のcopyを保ち、荷重だけを消費する。

**FixedClockのvoid callbackへ単純接続しない。** 現実装はcallbackが正常復帰すると、その内部advanceが失敗を返してもtickを加算する。戻りboolを捨てる接続ではWorld停止と時計進行が食い違う。この段はProgressをtransaction対象にし、既存FixedClockを変更しない。transaction-aware scheduler／accumulator／dropped-time接続は別の明示受入とする。失敗を制御用例外にして既存clockへ流す方法も、今回のnoexcept APIの代用にしない。

## 最小の有限受入案

| 入力／場面 | 必須の観測 |
|---|---|
| 2dynamic×2mesh＋plane、元guardの7pair／9child成功例、非零force／torque・回転 | 全candidateと実bodyを荷重消去差分以外すべてbit比較。Progress一増分、source／gravity／raw plane／格納先不変。9はこの明示例の値で、全入力共通値にしない。 |
| 明示primitive E128のmixed-static成功例 | static込み全候補commitと荷重消費、static元tiny値保持。別profileを元default予算失敗の成功扱いにしない。 |
| 先行seed成功後、後方mesh／primitive／依存／global予算で失敗 | 全World／Progress／荷重／負零／pointer不変。失敗tailと未照会を完全保存。候補prefixをcommitしない。 |
| 失敗→予算だけ直した再試行→次tick | 元失敗入力を保持し、再試行の新証拠を分離。荷重一回消費と次tickの現状態再照会を確認。外部古certificateを適用しない。 |
| 時計の不正、上限、tick上限、吸収される小H、env／profile拒否 | 全無変更、clock preflight失敗ではchild0／commit0。非有限値はNative直接試験に分け、有限JSONへ捏造しない。 |
| 非零timeで時計差とHが異なる有限例、time `−0` | RN和・整数tick・保存原値を独立照合。`advanced_dt` と表現時計差を混同しない。 |

fixtureは全元入力、元World／Progress、owned guard、commit用候補の荷重規則、実World／Progress後値、全pointer安定観測を保存する。最終件数・bit比較数・性能値は実行前に設定しない。guard childの独立数学包含、Native直接再照会のprovenance、実World commit全bit照合、時計RN参照、実target bindingはそれぞれ別gateとする。allocator／child非返却faultを注入していない限り、その動的故障試験を通過と呼ばない。nothrow境界のソース／型監査だけを注入成功に昇格しない。

今後の統合対象案は試作Native header／cppと専用tests／fixture。既存CMake・CIへの登録は現在featureの公開受入後に別baselineから行う。新依存・外部実装・有料機能は不要。本段の目標は離隔認証された区間の実自由伝播までであり、TOI、mesh衝突応答、接触支持・摩擦、損傷・流体・専門simulator完成を含まない。
