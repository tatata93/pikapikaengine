# ロボットの背面カバーへ実スキニングを適用する案

2026-11-04 JST。**設計のみ・未実装**。今回追加するのはこの計画書だけで、sample、原本、engine API、renderer、SDKを変更しない。ブラウザ読出し比較の受入とは別の、ゲームで見える次の最小更新を定義する。性能・表示・公開受入の成功を先取りしない。

目的は、プレイヤー機の背面に原著のヒンジカバーを1個取り付け、実際の移動・有効なboostに応じて開閉させること。実Source→C++ FK/LBS→C++派生mesh監査→所有token→ゲーム描画を通す。ラボの既存帯をそのまま浮かせるdebug表示、JSだけの頂点変形、shaderだけの見かけの変形は採用しない。一般の熱伝達・関節力学・衝突・弾塑性損傷の完成とはしない。

## 調査した現行の接続点

以下は本設計時の原本であり、実装前に最新差分を再確認する。

- `samples/app.mjs` は `initializePortableCore()` と `Renderer.create()` を起動する。これは小さいportable coreであり、FK/LBS/derivedを含む `loadSimulationRuntime()` はまだ起動していない。既存の入力、音声、シーン編集・JSON/portable保存、戦闘・結果画面を維持する。
- `FixedClock` は120Hz、最大24 step、超過の `droppedSeconds` を保持する。appは固定stepで `game.step()`、描画で `game.view(renderAlpha)` を呼び、rAF回数で物理を進めない。
- `RobotGame.reset()` はplayerとtimeを作り直す。`step()` は有効boostとenergyから速度32/80 m/sを選び、加減速・移動・射撃を処理する。見た目の噴射は現在energy/speed条件で出るが、その見た目を正確な有効boost判定として再利用しない。
- `RobotGame.view()` の機体はScene外でboxを組み立て、playerのprevious/current位置を補間し、player yawで局所offsetを回す。敵・弾体・既存bodyを作り直す必要はない。
- `Scene` v1/v2はparentを拒否し、`derived-mesh` やowned tokenを原本形式へ保存しない。game obstacleはSceneのbox/meshから作られる。装着用描画物をそこへ混ぜると静的障害物になり得るため分離する。
- `evaluateSkinBinding()` は所有source検査、rest FK照合、現在FK、LBSを実C++へ通す。`prepareDerivedMesh()` と `createDerivedMeshRenderData()` は別段階であり、前段失敗から成功tokenを作らない。
- `Renderer.render()` は同期CPU処理・submitで、同じid/tokenならuploadを再利用する。新tokenは新bufferを用意し、submit後に旧同id/除去idを退役する。準備/submit失敗では新candidateを捨て、前のcommitted meshを保持する。
- `renderChecked()` は同期 `render()` の後に非同期validation、次にqueue完了を待つ。旧renderEpochの失敗が新frameのresourceを消さない境界がある。appの通常rAFは現在 `render()` を呼び、全frameにqueue待ちはしていない。

## 見える最小の原著形状

案は、胴体中央の背面に付く薄い二分割ヒンジカバー。通常移動で少し開き、energyを消費する有効boostで大きく開き、解除・減速で戻る。熱の数値シミュレーションではなく、駆動状態を伝える機体の機構アニメーションである。playerだけ1個、敵・武器・既存噴射の振舞いは維持する。

形状の初期候補を次のように固定し、実装時にsourceとして保存する。

- 6頂点・4三角形。各段の左右幅はx=±0.75m、3段のyは+0.625/0/−0.625m、zは0/−0.125/0m。左右対称の浅い折面を持たせる。既存arm帯の座標・motion・targetを流用しない。
- 外側の法線が機体局所−Zを向く4面の順序を明示する。例として頂点を上左/上右/中左/中右/下左/下右の順にし、trianglesを `[[0,3,2],[0,1,3],[2,5,4],[2,3,5]]` とする。上端は胴体に固定し、中段にヒンジ、下段が外側へ開く。
- 2骨。rootのrestは上端 `[0,.625,0]`、childはroot局所 `[0,-.625,0]`。上段はroot、下段はchild、中段は両者の既知非負weightとする。bind/rest/currentの全行列をC++で求める。
- childのclipは0秒のrestから1秒のX軸+π/8回転までの2key、loopなし。sourceにauthor quaternionを保存する。範囲全体で面積/法線の監査が成功するかは受入で調べ、失敗を角度・精度の自動縮小で隠さない。
- 装着offset候補は胴体局所 `[0,2.65,-1.32]`、倍率 `[1,1,1]`。既存胴体の背面外側に付け、追従cameraで装着と開閉が分かる寸法・対照色にする。初段は両面の薄板であり、厚い装甲・密閉体積とはしない。

値は設計候補である。姿勢ごとの断面や背面cameraで面の重なり・隙間を確認し、実装前のauthor変更が必要ならsourceへ明記する。ゲーム実行中に形状を縮めたり法線を生成し直すfallbackは入れない。既存の機体名称・UI・他作品のasset/デザインを複製しない。

## 原本とゲーム/engineの責任

新しい `assets/robot-back-cover.skin.json` 等へ、既存Skin Binding v1の全mesh/weight/joint/rest/full motionを保存する案とする。必要なinverse bindは一度だけ既存C++ `sampleMotion`/`bindSkin` で生成し、生成recipeとJSON/portable保存再読込みの照合を保持する。毎起動のラボdefault生成や、毎frameのbind再生成をしない。

targetはこのasset専用の安定object/native IDを使い、level Sceneの物体IDを流用しない。必要なcontext確認には、同じassetのrest meshを持つ独立の小さいauthoring Sceneを明示して用意する。levelへ架空の親や隠しcolliderを挿入しない。自己のsourceから同じcontextを再構築しただけの一致を、他のScene原本との独立照合と呼ばない。ゲームでの装着はsource targetとplayer anchorのsample側の明示対応である。

assetを既存制作ラボで編集して再保存する場合は、target/mesh/rest/weight/motionとNative CLI再読込みを検証し、再導入は新asset revisionとして扱う。levelの既存save/loadにbindingを黙って埋め込む、level保存だけでassetも保存できたと表示する、一般project asset-reference形式が完成したとすることはしない。

ゲーム固有のsource選択、boost/speed→clip時刻、色、装着位置、player IDは `samples/` の小さい専用moduleへ置く。FK/LBS/derivedの代替実装は置かず、既存 `engine/skin-binding.mjs`、`engine/simulation.mjs`、`engine/derived-render.mjs` を呼ぶ。最初から汎用animation graphや大きいcontroller frameworkを追加しない。source検査/数値照会/token factoryの共通契約が不足すると判明した場合だけ、試験可能な小さいengine APIを別に設計する。

main simulation SDKは初期化時に一度loadし、game表示用の専用runtimeを使う。既存portable core、物理tickや音声の状態をresetしない。SDK fetch/instantiate、asset fetch/parse、初回Source評価は別の起動費用として保存する。読み込み成功を待ってからcoverを利用可能にし、不正SDK・asset・数値の失敗を既存game READYへ混ぜない。既存gameの出撃可否と追加表現の準備中/利用可能/利用不可を分け、未準備の間はtokenを表示しない。非同期初期化の完了も現在play/asset/scene世代を検査し、reset/reload前の要求で新状態を上書きしない。装飾機能の失敗は明示してcoverを出さず、保存原本と既存プレイを保持する。base renderer/deviceの破綻は別の全体エラーとして扱う。

## 120Hz状態と描画・clip時刻

sampleの固定stepに、表示用の開度u∈[0,1]と直前uを持つ。targetはそのtickで確定した有効boostと水平speedから決める。キーを押しただけ、energy不足、停止中のboost要求を本稼働としない。移動中の小さい開度と有効boost時の大きい開度を区別し、既知の固定秒応答で変化させる。これに乱数を使わず、弾道、hp、energy、衝突、waveの数値を変更しない。

`clipSeconds = interpolatedU * clip.duration` とし、これはauthor clipへの状態写像である。ゲームのelapsed秒を熱量やヒンジ角の物理解として扱わない。uをrAF回数やwall clockから積分しない。player位置は既存previous/currentを同じrenderAlphaで補間し、coverも同じ表示状態に装着する。

親変換は既存robotと同じY回転と平行移動だけ。局所offset `[x,y,z]` は `[x*cos(yaw)+z*sin(yaw),y,-x*sin(yaw)+z*cos(yaw)]` にして、補間player位置へ一度加える。source FKにplayer世界移動を焼き込まず、tokenはmesh-localのまま、render itemへ位置/yaw/scale1を渡す。yawは初段で既存bodyと同じ値を使用し、coverだけ別の補間をして胴体からずらさない。一般Scene parentや非一様scale/shearの追加には拡張しない。

物理は引き続き120Hz。派生meshの評価・token更新周期は**追加費用の実測後に固定**し、120Hz物理と同一頻度だと仮定しない。候補は120Hzの整数tick周期に限るが、未計測の段階で30/60/120Hzを採用済みとしない。表示のsample時刻、最後に計算したclip時刻、token年齢、予定更新/実行/遅延・省略件数を区別する。描画間の保持tokenを現在時刻に新規計算した姿勢と偽らない。

同じsource/clip時刻を再度表示するだけなら同tokenを使い、C++を再照会しない。新clip時刻を計算するときは成功したLBSの全位置と原本の全triangleをsingle経路の `prepareDerivedMesh` へ渡す。既定singleを維持し、計測結果からbatchへ自動切替しない。位置・normalをJSで補間した未監査bufferを新tokenへ渡さない。

## game frameでのchecked描画と最小のAPI候補

通常frameを `await renderChecked()` の完了ごとに次のrAFを予約する構造へ置換しない。全体の物理・カメラをqueue待ちに結合し、GPU待ちをframe時間へ直列化する変更を避ける。既存 `render()` のcache・同id置換を使い、新tokenを最初に描くframeだけ既存 `renderChecked()` を呼ぶ案から検証する。**checkedへ渡すのはカバーを含む全frameのitems/camera/time**で、通常の `renderer.render(fullItems,...)` 1回を置き換える。カバーだけのchecked drawはcanvasをclearして世界を上書きするため禁止し、通常frameとchecked frameを同一rAFで二重submitしない。

このchecked呼出しはrender/submitまでは同じframeで行い、validation→queueのPromiseを1件だけbackgroundで追う。pending中も通常frameは同tokenの描画と親transform更新を続ける。新しいchecked/token更新は同時に積み上げず、待ち中の更新予定は件数・時刻を記録する。勝手な精度/形状/LOD低下や未検証tokenへのfallbackで隠さない。この制約で選んだ更新周期を満たせない場合は未受入とし、周期や遅延の根拠を再検討する。

この併用はまだ検証済みではない。実sourceの順序は `pushErrorScope → render/submit → popErrorScope() → await validation → onSubmittedWorkDone() → await queue`。popは最初のawaitより前に呼ぶため、通常frameをscopeの内側に意図せず積み上げる構造ではないが、queue完了の呼出し自体はvalidation解決の**後**である。その間に送った通常frameもqueue呼出時点以前の仕事へ含まれ得る。待時間を新token1個のGPU処理時間へ割り当てない。scope stackの均衡、後続frameと解決順、Promise rejectionの全経路をstubと実ブラウザで受け入れるまで、この併用を安全だと前提にしない。

CPU/source/derived成功と、GPU pending/観測成功/失敗を分ける。最初の描画はGPU確認pendingであり、既に全描画が検証済みとはしない。解決時にはasset/play/scene/renderer世代とtokenを照合し、旧Promiseで現tokenを採用し直さない。失敗した旧tokenの状態を現在成功へ付け替えない。GPU device lost/uncaptured errorは既存の全体エラー処理へつなぎ、停止時にはrendererをdisposeして最後のframeのresourceを放置しない。

checked失敗時のrenderer側の作用も対象単体とは限らない。同じrenderEpochのままなら現実装は **全mesh cache** を退役し、draw統計をclearする。後続通常frameでepochが変わった場合は新cacheを消さず、そのままrejectする。この違いを隠さず記録する。CPUのScene/戦闘/sourceは変更せず、現在coverを外して失敗を表示する。deviceが生きていればcover無しの**全base frame**で一度だけchecked復旧を試み、既存world meshの再uploadが必要ならその費用も数える。復旧が失敗すれば全体停止/disposeとし、描けていないgameを正常扱いにしない。復旧成功はbase frameの観測成功であり、coverの失敗を消さず、再試行は別の明示操作または新play世代で行う。

追加が必要な最小API候補は `Renderer.dropMesh(id)` 相当の**指定idのcache退役だけ**。現 `render()` は他のmeshが残るframeで、除去idをsubmit成功後に退役する。hidden/reset/数値失敗の瞬間には次の成功drawが無い場合があるため、装着meshだけを即時に外し、他のScene meshを壊さない契約が必要になる。

候補の契約は、未知idの冪等no-op、既存bufferの1回だけdestroy/map削除、累積退役count、実際の退役時のrenderer epoch無効化、device非destroy。epoch無効化により旧checked失敗が他Sceneの新cacheまで掃除しないこと、削除したidが次のfull frameへ再投入されないことを試験する。描画成功/数値成功を返すAPIではない。canvasに既に描いた画素はこれだけで消えず、次の正常frameのclearまたはhidden/全体エラー表示と組み合わせる。新APIなしで同じ境界を満たせるなら追加しない。新しい汎用GPU scheduler、buffer ring、専用WGSL、毎frame timestamp queryは初段に含めない。

## 無効化・pause・保存再読込み

| 操作/状態 | 初段の扱い |
|---|---|
| P pause / blur | game固定状態とclipを止める。現在の正しい停止姿勢を必要なら一度評価し、停止中の反復queryをしない。親/coverの補間時点を揃える |
| hidden / pagehide | 入力停止、pending世代を取消し、cover token参照とGPU cacheを退役する。復帰時にwall時間をcatch-upせず、明示再開時の固定状態から再評価 |
| restart / game.reset | 新player/play世代、uと前uを初期化。旧tokenとpendingを無効化し、時刻0のsourceを再評価。scene原本を作り直さない |
| level Scene load | 読込候補を既存規約で検査し、成功commit時に旧play/scene世代を捨てる。source assetは保持し、新playerへ装着。読込失敗では既存scene/sourceを保持 |
| Scene edit / undo / redo | Scene APIの既存ID/原本履歴を維持。assetとの依存/世代を再確認し、必要なら同じclipから再評価。保存済みlevelへtokenを混入しない |
| asset変更 | 全source候補検査/保存再読込みの後にrevisionをcommit。途中結果と旧可視tokenを混ぜない |
| FK/LBS/derived/token factory失敗 | 現在のcoverを外し、段階/status/reasonを保持。古い成功姿勢を現在の成功と表示しない。sourceの自動補正・三角形切捨てなし |
| GPU validation/queue/作成失敗 | CPU原本・結果と別に記録。現在世代のcoverを外す。新世代の結果を旧callbackで書き換えず、device全体破綻時は全体停止とdispose |

renderer予算は既存全itemへ新1mesh/4triangleを足して監査する。IDはsample専用namespaceで衝突を拒否する。以前有効だった128meshのlevelを壊して1枠を奪わず、装着を含む予算が不足した場合は新機能の明示的な利用不可として記録する。既存levelを切捨てたり、黙って軽いcover形状へ差し替えない。標準arenaで装着可能なことは独立に受け入れる。

## 有限な実測と受入

公開Nodeの4面derived全体約0.3msはSource検査・rest/current FK・LBSの費用を含まない。これをゲームの追加費用、fpsまたはbudget達成の根拠にしない。実装時の同じassetとSDKで次の段階を分け、初回/warmup/有限な全計測を保存してから更新周期を決める。

1. asset parse/検査/bind生成の一回費用、`evaluateSkinBinding` 全体（source検査/rest照合/current FK/LBSを含む）、derived全体、token検査/所有copy、game render submitの増分を別に測る。独立の通常経路と計器付き、source/token更新あり・同token再描画を比較する。残差をC++核だけの時間と呼ばない。
2. NodeでsourceのJSON/portable再読込みと既知rest/最大角/中間時刻のFK/LBSを確認し、全4面・全72float/288bytesを既存derived/token/rendererへ通す。端頂点と末尾面を省略しない。原本/全DTO bitsと型/所有を確認し、全範囲の品質を有限標本だけから一般保証しない。
3. 120Hz入力replayを30/60/120/144描画条件で再生し、player/弾体/hp/energy/kill/waveとvisual固定状態を比較する。同じ明示clip時刻の派生DTOを照合する。異なる描画頻度で実行しなかった中間tokenを、計算済みと数えない。
4. renderer stubでは同token cache0B、新token288B、同id旧buffer退役、drop/clear/disposeの一回性、全byte/末尾、validation/queue待ち中の通常full frame・pause/reset/hidden/Scene交換を確認する。全itemsによる1frame1submit、scope均衡、queueの遅い呼出時点、旧epochと同epochそれぞれの遅延failure、他Scene cacheの保持/退役、cover無しbase復旧の成功/失敗、旧callback、deviceLost、数値/SDK失敗後の明示再試行を受け入れる。GPU memory readbackを実施したとはしない。
5. ローカルと公開の実ブラウザで、出撃→通常移動→有効boost→解除/減速→旋回→射撃→P停止/再開→再出撃を有限操作する。cameraからカバーの装着・開閉が見え、弾体と戦闘進行が維持されることを画像と状態で確認する。既存READYだけでは受け入れない。
6. editorで既存障害物を編集→save→reloadし、位置・mesh/ID・履歴境界とプレイ再開、cover原本不変を確認する。level保存とasset保存を分ける。hidden/復帰やreload後に古いカバーが浮く、旧sceneへ戻る、資源が積み上がる場合は不合格。
7. 通常移動/boost/射撃を含む固定した小さな区間で、既存FrameLogのrAF間隔・CPU submit・超過件数・droppedSecondsと新しい追加stage/更新数/最大token年齢を保存する。実GPU単独時間・実画面提示fpsは未測定とし、失敗や遅いframeを除外しない。

追加stageが選んだ周期に収まらない、開閉が見えない、原本保存や戦闘replayが壊れる場合は成功扱いにしない。計算条件を弱くして受け入れるのではなく、原因と最小変更を見直す。ローカル検証後にbuild/全回帰・CI/Pagesと影響配信byteを確認し、起動リンクと有意味なプレイ操作の結果を報告する。

## 継続する範囲と一次根拠

これは1装飾機構を実スキニングへ接続する最小更新であり、全機体の骨格化、IK/制御graph、可変collider、被弾損傷、空気/水の流体、車両/航空/鉄道、任意接触、任意精度光学撮像、Native/ネットワーク全機能を完了・縮小する計画ではない。実装受入後も共通engineの未完と次の小さな受入へ戻る。ユーザーの明示停止までの自律開発方針、課金/投稿/メール禁止、他チャットの改変保持を維持する。

根拠はrepositoryの `PROJECT_SPEC.md`、`PLAN.md`、[原本形式](SKIN_BINDING_FORMAT.md)、[手動表示](DERIVED_MESH_RENDER.md)、[まとめ読出し](DERIVED_MESH_BATCH_READ.md)、[ブラウザ比較](DERIVED_MESH_BROWSER_READBACK.md)と、上記sample/engineの実source、`tests/engine.test.mjs`、`mesh-integration.test.mjs`、`derived-renderer.test.mjs`。外部文献/code/asset/新packageは導入しない。本体ライセンスは未選定。実装前にoriginと作業treeの最新差分を確認し、同じsampleの他チャット変更を上書きせず統合する。
