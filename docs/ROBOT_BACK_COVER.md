# 実Sourceで動かすロボットの背面カバー

2026-11-04 JST。**実装済み・ローカル操作受入、公開確認は別記録**。既存IRON FIELDのプレイヤーへ、原著の背面ヒンジカバーを1個追加する。Source専用7群、controller11群、renderer24群を含む全Node492試験が成功した。ゲーム全体の性能や全作品での60fps達成を受け入れたものではない。最終集計と公開結果は[統合報告](../reports/2026-11-04-robot-cover.md)で別に確定する。

[設計案](DERIVED_MESH_SAMPLE_PLAN.md)から、保存原本→実C++ FK/LBS→実C++派生mesh監査→所有token→全game frameへ接続した。一般の熱伝達・ヒンジ関節力学・衝突・弾塑性損傷・IKを計算する機能ではない。

## 原本と保存の境界

- `assets/robot-back-cover.skin.json`: 6頂点・4三角形・2骨のSkin Binding v1原本。targetは `robot/player/back-cover` / Native ID `71000`、骨IDは `71001` / `71002`。
- 横幅1.5m、上下幅1.25m、中段の奥行−0.125mの浅い折面。外側の法線は局所−Zを向く順序で保存する。厚い密閉装甲や体積要素ではない。
- 上段をroot、下段をhinge、中段をauthor weight 1:1で両骨へ結ぶ。原本weightを上書きせず、共通C++側で正規化する。
- 1秒clipの0秒restと1秒のX軸+π/8回転を保存する。author quaternionのbinary64値を使い、共通核の最短NLERPで補間する。途中の角速度が一定だとは主張しない。
- `assets/robot-back-cover.scene.json` は専用のauthoring context。generatorと同じ独自recipeから保存したもので、外部の独立原本との来歴証明ではない。levelへ静的colliderとして足さない。

`scripts/create-robot-back-cover.mjs` が一度だけ実C++ rest FK/bindからinverse bindを生成する。`--write` は既存原本の上書きを拒否し、`--verify` は原本を変えずJSON/portableとNative CLIの再読込みを検査する。毎起動・毎frameにbindを再生成せず、保存済みの全Sourceを読み込む。level Scene保存へtokenやassetを黙って埋め込まない。

## 固定運動と見せる姿勢

`samples/robot.mjs` が、その固定tickでenergyと移動入力から確定した `boostActive` と水平speedを渡す。キーを押しただけの停止boostを有効稼働としない。カバー開度uはgameと同じ120Hzで変化させる。

現controllerの目標開度は、有効boostかつ水平speed>1m/sなら1、それ以外は、水平speedが0.1m/s以下なら0、上回る場合は `0.25*clamp(speed/32m/s,0,1)`。1秒あたり最大4の変化で目標へ近づけ、rAF回数やwall clockから積分しない。停止付近の0.1m/sはauthorが定めた見た目のidle bandである。指数減衰する微小speedの違いで無限に別姿勢を照会せず、正確なrest clipへ到達してqueryを止める。物理速度をzeroへ丸めたりFK/LBSの精度を落とす処理ではない。これは駆動状態を見せる写像であり、温度・熱量・トルクの物理解ではない。

前/現開度を同じrenderAlphaで補間し、1秒clipのパラメータにする。player位置も既存previous/currentと同じalphaで補間し、胴体局所offset `[0,2.65,-1.32]m` を既存yawで一度回して装着する。tokenはmesh-localのまま、world移動を原本やFKへ焼き込まない。

派生姿勢の更新予定は固定2tickごと、120Hzに対する**毎秒60回のrequest候補**である。実GPU更新が60Hzで達成されるという保証ではなく、rAFとpendingによる遅延・省略を記録する。毎予定で実際にqueryできる保証ではない。最初の姿勢やpause時に必要な姿勢は別に評価し、同じclip時刻なら同tokenを再利用する。pending中は新しいchecked/queryを積み上げず、最後のtokenを表示してその年齢を記録する。待機が長ければ次の予定を遅延・省略した件数も残す。精度・面数・角度を自動で下げるfallbackを入れない。

## 実計算と描画

`samples/back-cover.mjs` は保存Sourceを検査し、`evaluateSkinBinding` でrest照合/current FK/LBSを実C++へ渡す。変形がcompletedの場合だけ全位置と全triangleを `prepareDerivedMesh(...,{readback:'single'})` へ渡す。batchの計測結果から自動切替しない。

派生監査がcompletedの場合だけ `createDerivedMeshRenderData` で所有tokenを作る。全4面・72 Float32値・288Bが対象で、JS変形・旧法線・部分bufferを代替にしない。CPU局所監査をGPU model/camera変換・画素被覆の誤差保証へ広げない。

新tokenの初回は**世界を含む全frame**を `renderChecked` へ渡し、そのframeの通常submitを1回だけ置き換える。カバーだけの別描画で画面をclearしたり、同じrAFで全frameを二重submitしない。checkedは最大1件をbackgroundで追跡し、pending中も通常full frameは同tokenと現在の親変換で描く。

rendererは同期render/submit後、最初のawaitより前にpopErrorScopeを呼び、validationが解決した後にqueue完了を呼ぶ。その間の通常frameもqueue呼出時点までの仕事へ含まれ得る。待時間を新tokenだけのGPU処理時間やdisplay提示時間へ割り当てない。

`Renderer.dropMesh(id)` は対象の派生/通常mesh cache1件だけを冪等退役する。実削除時だけepochを進め、bufferを1回destroyして累積退役数を更新する。未知IDとdispose後はfalse。deviceをdestroyせず、最後にsubmitしたframeのdraw統計とcanvas画素はこれだけでは消さない。次のfull frameやhidden/全体エラー表示と組み合わせる。旧checkedの失敗で新しい他Scene cacheを消さないことを専用deferred試験で確認する。

## 失敗・停止・原本の保持

| 状態 | 現行の扱い |
|---|---|
| SDK/asset読込中・失敗 | 追加機構の状態をREADY本体と分け、カバーを出さず既存プレイを保つ。明示再読込で再試行する |
| Source/FK/LBS/派生監査/token失敗 | 現カバーを外し、段階/statusを保持する。古い姿勢を現在の成功へ付け替えない |
| checked validation/queue失敗 | 現世代のカバーを外し、deviceが生きていればカバーなしの全base frameを1件checked復旧する。復旧失敗は全体停止/disposeへ渡す |
| reset/hidden/Scene編集・再読込 | 世代を更新して旧token/cacheを退役する。旧Promiseは新状態を採用し直さず、pending1枠が解決するまで新checkを積まない |
| pause/再開 | game固定状態と開度を止める。hiddenからのwall時間を追いつき計算せず、明示再開の固定状態から使う |
| 描画予算不足/ID衝突 | 元levelや障害物を切り捨てず、追加機構だけの利用不可を記録する。全体renderer予算は増やさない |

カバーの装着・見た目の失敗と、device lost等のbase renderer全体の破綻は別に扱う。Source・level原本を自動修正せず、既存戦闘・音声・編集保存を維持する。主SDKと既存配布通知を更新する機能ではない。

## 現時点の証拠と残る受入

Source専用7群では、既知rest/中間/終点の解析姿勢、JSON/portable/Native CLI往復、33個の有限clipパラメータで全4面の局所品質、全288Bと原本不変を調べた。33標本を全実パラメータの一般保証にはしない。controller11群では実SDKの通しqueryと、pending/旧世代・hidden/reset・GPU/数値/予算失敗のstub境界、30/60/120/144描画条件での固定game状態、idle bandから正確なrestへ到達した後のquery停止を比較する。renderer24群では単体退役、全byte/cache、checkedと通常full frame併用のscope/epoch境界を確認した。stubは実GPU性能や実画面の代わりではない。

初期Node小標本 `build/robot-cover-source-GzrtcP/measurements.json` には各時刻で初回1・warmup1・measure3を保持する。囲った全pipelineのmeasure中央値は次のとおり。

| clip時刻 [s] | measure数 | enclosing pipeline中央値 [ms] | 最大 [ms] |
|---|---:|---:|---:|
| 0 | 3 | 1.6780 | 2.3208 |
| 0.5 | 3 | 1.2251 | 1.3356 |
| 1 | 3 | 0.9495 | 1.1369 |

これはSource全検査/rest/current FK/LBS、派生監査とtoken copy、および間のstatus確認・時計の費用を含むNodeの有限wall観測である。各stageの単純和とenclosing pipelineを区別し、計器負荷を補正していない。**GPU/ゲーム全frameは含まず、2tick周期の実達成、60fpsや一般性能を保証しない**。追加の実測rawと最終値は統合報告へ対応付ける。

ローカルでは装着/開閉の視認、移動/有効boost/解除/旋回/射撃での2機撃破/pause/再出撃、Scene編集・JSON/portable保存とJSON再読込を有限操作で確認した。停止中はtick/query/資源数が変わらず、旧source・GPU失敗とhidden等の境界は別にstub試験で検証する。token年齢は同じ静止姿勢を正しく再利用する時間も含み、姿勢の遅れそのものではない。資源/予定遅延・dropped time・CI/公開操作/配信byteは統合報告へ対応付ける。既存READYだけの確認とは分け、実ブラウザの全隠蔽/復帰経路を確認済みにはしない。図は説明用で、実測画面や物理的損傷の結果ではない。
