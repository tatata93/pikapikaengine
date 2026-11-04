# Schedulerの次段：Native一tick荷重packet transaction

2026-11-05。**調査・次段計画のみ。以下のpacket API／owner／WASM対応は未実装・未実行。** main scheduler統合8a69932のGNU検証は別receiptで確定する。この文書は進行中CIを成功へ変更せず、既存scheduler2源／advance7-source identity／SDK／sampleを変更しない。次の実装対象は、callbackを持たない**単一tickの絶対荷重packet transaction**一つとする。一般接触応答・流体・制御器全体の完成ではない。

## 実ソースで確認した不足

| 実読箇所 | 現能力と境界 |
|---|---|
| `core/include/pikapika/world_static_mesh_flight_scheduler.hpp`／同cpp `Scheduler::pump` | World／Progressを所有せず、同じWorldに既存advanceをdue数だけ呼ぶ。成功tickだけcreditを消費し、拒否時はretry elapsed=0。tick間の荷重入力口はない。 |
| `core/src/world_static_mesh_flight_advance.cpp` `validate_commit`／`commit`／`advance` | 内部guardを一回だけ呼び、全検査後に既存body格納先とProgressへnoexcept commit。成功時force／torqueはstaticを含め全bodyで+0へ消去する。 |
| `core/include/pikapika/dynamics.hpp` `RigidBody`／`World` | forceは世界座標N、torqueは世界座標N m。Worldはbody／plane vectorとgravityを持つ。`find_body`はmutable pointer、`bodies()`はconst vector参照を返す。 |
| `core/src/dynamics.cpp` `World::apply_force`／`apply_torque` | 各呼出しは一bodyのcandidateを検査して即storeする。複数bodyの入力全体を一transactionにせず、失敗tickへ再投入した同じ荷重の重複を検出しない。forceの点適用は追加cross積と加算を行う。 |
| 同cpp `add_body`／`add_plane` | vectorへ追加しID順sortする。構造編集後まで借用body address／ordinalが維持されるとはいえない。 |
| `engine/simulation.mjs` `SimulationWorld`／`bodyInput` | 既存SDK World handleとbody DTOはあるが、これは新Native all-pair guard／advance／schedulerのhandleではない。既存setBody／stepContinuous等へ新証明を暗黙に付けない。 |

従って一frameの冒頭でforceを積み、現在のschedulerで複数tickを進めても、その力は最初の成功tickにしか作用しない。逆に、拒否後に毎frame `apply_force`を再実行すると保持中の力へ足し重ね得る。従来APIの契約違反ではなく、連続制御入力を接続する際の不足である。

Worldを所有するcontainerだけ先に作っても荷重の一回性は解けない。WASMへ同名exportを増やしても数値bindingが成立しない。最小の実用前進は、各物理tickの全荷重を明示し、拒否後も安全に再提出できるNative入口である。

## 提案入口と荷重の意味

新独立namespace／hpp／cppの候補を `world_static_mesh_flight_controlled_tick` とする。以下は型案であり、既存公開APIではない。

```cpp
struct BodyLoad { uint64_t body_id; Vec3 force_newtons, torque_newton_meters; };
// expected_tick、明示的replace_total_world_loads mode、最大8個のowned行。
struct TickLoadPacket;
ControlledReport advance_with_loads(World&, span<const StaticMeshSource>,
    double H, const GuardSettings&, Progress&, const TickLoadPacket&) noexcept;
```

packetは**その一tick全体へ保持する総force／総torqueの置換命令**である。増分加算、impulse、世界点force、ローカル座標変換、PID／vehicle／fluid modelを含めない。元の非零荷重へ自動加算せず、frame間へ自動保持しない。元荷重と置換値の両方を診断へ残す。既存 `apply_force` の別名とはしない。modeは必須で、暗黙のdefault増分／置換を作らない。

- `expected_tick` は現在の `Progress.ticks` と整数で一致すること。初段は既存域0..2^53−1を使い、double変換で比較しない。成功後の再提出はstale拒否。失敗時はtickが変わらず、同packetまたは別packetを同tickへ再提出できる。
- 全bodyについて一行ずつ必須、最大8。行順は原本として保存し、stable IDで元body ordinalへ解決する。重複・欠落・未知／unsafe IDを拒否。bodyが0なら0行。subsetに対する「省略は前の力を保持」規則を作らない。
- static bodyのpacket値は各成分が厳密に0（±0は保持）を要求する。dynamic値は有限かつ既存body domain内。元Worldの全bodyfieldを既存検証へ渡し、mass／inertia／radius／rotationをpacketの便宜で補正しない。
- Hは既存advanceの有限(0,.1]秒、明示margin等は既存GuardSettingsのまま。source最大8body／16plane／4mesh／総64faceを広げない。packetは位置／速度／姿勢／gravity／shape／mesh revisionを編集しない。

expected_tickは同じ論理Worldでの再使用防止であり、世界を跨ぐ認証token／永続配送のexactly-once保証ではない。WorldやProgressを別物に交換したcallerを自動検出するowner handleはまだない。callerが一つの論理World／Progressとpacket列を排他的に管理する前提を残す。

## private実行と外部commit

現在のWorldはcopyを明示deleteしておらず、private状態は値gravityとstd::vectorである。**private copy案は現宣言に基づく設計で、まだ実compileで証明していない。** 実装時にcopy可否のtrait／ビルド、全field・原順・負零・無効原本を含むcopy試験を行う。`add_body`／`add_plane`で再構築するとsort／再検証で原本が変わり得るため、captureの代替にしない。raw memcmpによるpadding比較もしない。

1. 環境first、新wrapper構成と既存binding、hard countsを検査。全packet／settings／原World／mesh／Progressをowned captureし、capture none／partial／completeを区別する。置換前の全bodyも既存validateで検査し、元の不正forceをpacketで消して正常化しない。この構造／入力検査は幾何queryの追加ではなく、実検査数を別記する。失敗する全alloc・metadata準備を外部storeより前へ置く。
2. packet全体を検査し、private Worldへ置換する。元Worldへ一時forceを書いてundoする方式にしない。元body順序は変えず、packet行→元ordinal対応を固定する。
3. private Progressとowned mesh／settingsを使って**既存advanceを一回だけ**呼ぶ。再query、旧step fallback、H縮小、失敗後に元荷重へ戻して別試行する処理を作らない。
4. private childが成功なら、その実private WorldAfterを固定最大8body bufferへ取り、既存advanceのactual Report／guard／candidateと対応検査する。元World／Progress／sourceが元captureと全field一致すること、元bodyへの全destination解決とaddress／順序を確認する。必要なvalidate／alloc／report生成はここで完了する。
5. 全段成功時だけ既存body格納先へ値を代入し、外部Progressへprivate Progressをstoreする。World全体へのmove代入／swapは禁止（body pointerやvector storageが変わる）。body／Progress代入とReportのmove／destructのnothrow条件をstatic assertionで固定し、最後のstore phaseをcatch外へ分離する。

private childが `committed=true` でも、その後のouter検査が拒否すれば**外部commit=false／advanced_dt=+0**で元WorldとProgressは不変である。Reportにはprivate execution成功を隠さず残す。private成功を外部進行と呼ばない。逆に外部store開始後の失敗Reportは作らない。全同期call中のconcurrent／signal／reentrant World/source操作をcallerが排除する。これはthread atomicity／crash recoveryの保証ではない。

## 原本・診断・費用

ControlledReportは最低限、入力packet全行／mode／tick、original World／Progress／source／settings、capture状態、置換行対応、実private WorldBefore／After、実private Progress、完全なactual AdvanceReport、outer status／reason／stage、候補検査とdestinationの実prefix、外部body／Progress store数を所有する。失敗originを補填するためのguard再queryを禁止する。

**failed guardのpreparation.snapshotはpacket適用済みprivate Worldのoriginで、元Worldとは荷重が異なる。** `originalWorld` と `stagedWorldBefore` を別fieldにし、child.guardのoriginを前者へ付替えない。実private状態の捕捉と、独立checkerが導くexpected candidate chainも区別する。非規範messageの省略は既存MessageOmissionに従い、actual文字列を架空に再構築しない。

child呼出しは最大1回。数値work known／upper／exact／非return予約を完全保持する。外側はsource／packet capture、検査、lookup、copy、storeを別counterにし、childがprivateで成功してouter拒否した費用も落とさない。private World／sourceの追加コピーと返却snapshotは旧guardの16MiB論理payloadだけでは上限化できない。hard count・固定bufferと全vectorの要求／返却capacity／sizeofを測定し、allocator overhead／RSS／実stack／deadlineを保証しない。新wrapper source/compiler/strict構成は別identity、旧7-source式とscheduler2-source式は不変とする。

## 一つのNative受入

新cpp／hpp、専用tests／full fixture、独立参照／負例を新所有範囲で作り、まず隔離Nativeで以下を保存する。件数や成功は実行後に確定する。

| 場面 | 必須証拠 |
|---|---|
| 二tickの異なる荷重 | m=2、g=0、H=1/16、静的mesh／planeから十分離れた球にFx=4、次tick−4。exact dyadic解析で初回vx=1/8、x=1/256、次vx=0、x=1/128。力を初回だけ使う旧batchのx=3/256と区別。両tickは別packet／期待tick。 |
| 原荷重と置換／消費 | 元Fx=3＋packet Fx=5なら実guard originは5であり8ではない。成功後の外部force／torqueは全+0、失敗時は元3の全bitsを保持。static行±0／dynamic負零も保存。 |
| guard拒否→retry | 接触帯へ入る荷重の拒否時、外部World／Progress／pointer／荷重は完全不変。expected_tickを変えずsafe packetへ変更して再試行可能。成功後に旧packetを再提出するとquery0でstale拒否。 |
| packet全体の拒否 | 後半行のNaN／Inf、ID重複／欠落／unsafe、静的非零、count9、wrong mode／tickを一つずつ検査。早い行だけを元Worldへ適用しない。finite JSONと非finite bit記録を分離。 |
| 全owned lifetime | caller packet／mesh／settingsを返却後に編集しても過去Report不変。元body address／順序／plane／gravity／mesh原値は成功時も維持。vectorの将来構造編集後まで旧pointer有効とはしない。 |
| failure scope | private child成功後のouter検査拒否は外部進行0、private診断を保持。実allocation／nonreturn faultを注入していなければ人工metadata controlsを実故障成功と呼ばない。env／default binding拒否はquery0。 |

独立checkerはoriginal→packet置換expected stateをIDごとに作り、**実返却child.guardだけ**を既存guard参照へ渡す。旧advanceの時計整数RN参照、全body candidate＋loadclear対応、実外部Before／Afterを照合する。負例はorigin付替え、packet加算偽装、stale受理、未適用行、外部部分store、private成功の外部成功化、wrong−0、unknown work削除を含む。Native直接再照会とのbit一致は別provenance gateとし、独立解析の代替にしない。

## 依存順とWASM前提

今回選ぶ次段は上記Native単一tickだけ。次にdata-only per-tick packet列を処理するscheduler入口を設計する。現pumpへ無断でcallbackを差し込まず、frame elapsedの一回受理／retry0／成功prefix／packet消費を結び付ける新受入が必要である。この単一tick案を現在のmulti-tick pumpへ接続済みと呼ばない。World／mesh／Progressのowned session、世代付きhandle、destroy/reset後のstale入力とReport寿命はその後の独立owner受入とする。

WASMへはさらに以下が先行する。

1. `guard::current_binding`、advanceのmatching gate、schedulerのgateは現実装でWASM／Clangを除外する。`core.cpp`のNative x64 root bridgeもWASMではstd::sqrt fallbackである。既存92-export SDKや既存単体flight照会の成功をall-World bindingの証明に流用しない。
2. 実WASM toolchain／flags／linked module／演算順／root実装／gradual underflow／例外／linear-memory成長を調べ、専用bindingと拒否条件を定める。NativeのMSVC／GNU IDやcaller boolでunlockしない。現builderへ新World源が揃うこともまだ保証されていない。
3. owned World lifetime＋packet／Progress／sourceの原子的交換、bounded getter／全診断、Host拒否とモデル失敗、loader capability／missing exports、memory-view再取得とowned copyを別ABI計画にする。旧World DTOと新Native全fieldを暗黙変換しない。
4. Native／actualWASM全wire bits・負零・各側独立数学・旧SDK全互換・実browser動作・source/member/license差分を実測してから配布する。現Node／Native receiptやunused heap capacityをこの将来gateの成功に数えない。

外部資料／ライブラリは今回追加していない。球proxyの非接触free flightに荷重入力のtransactionを足す計画であり、一般形状の応答、支持／摩擦／接触manifold、vehicle／fluid／damage、ゲーム内制御、実時間deadlineは引き続き未完である。
