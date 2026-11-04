# 球と三角形の手動照会ラボ: 次の有限受入

2026-11-04 JST。実装・ローカル/最終公開CI/Pages受入済み。共有SDK接続e100beeの公開受入後に以下を実装した。Native核・ABI・既存ゲーム原本は変更しない。

`tools/sphere-triangle-lab.html/.mjs` を、既存の学習ラボと同じ構成で追加する。同じ `SimulationRuntime.querySphereTriangle` を使い、JSで距離・候補分類を再計算しない。

- 面・3辺・3頂点・裏側・中心一致・退化・品質/候補予算不足の入力を、説明付きプリセットと編集可能なstrict JSONで選ぶ。入力を勝手に丸めたりclampしない。全設定とsurface IDを保存する。
- 成功/モデル失敗/入力交換拒否を別表示する。completedだけにgeometryの区間を表示し、失敗した後に以前のgeometryや図の成功印を残さない。候補prefix、棄却理由、KKT数と全区間を確認できる。
- source座標の三角形と球中心を2D投影で示す。closestは返却区間の領域として描き、区間中点を物理の接触点・単位法線へ変換しない。投影と縮尺は説明用で、GPU精度や性能測定とはしない。
- 入力・結果・SDK診断・表示投影をJSONへ保存する。保存はfinite値とsigned zeroを保持する。照会不能なら成功出力を合成せず、その失敗段階を明示する。旧SDK能力拒否は継承する。
- 初期化/照会中/破棄後や入力変更後の古い非同期結果が、新しい入力の成功として再表示されない。元の入力と所有snapshotを保持する。
- Node試験では実WASMの解析配置、失敗と復帰、入力不変、JSON保存再読、悪い入力、UIの古い結果消去を確認する。実ブラウザでもプリセット変更→失敗→復帰→手編集→保存を実行し、公開配信のbyte/SDK build IDと画面を保存する。

学習記事の既存区間節からリンクし、25記事を維持する。既存原著sphere-triangle.svgを再利用する。新外部package/素材/サービスを導入しない。公開節目で全Node/構文/Web buildと必要なSDK回帰を実施し、記録・commit/push・起動リンクを報告する。

World/三角形storage/隣接面/manifold/時間方向CCD/点衝撃応答への接続、ゲームのmesh接触、閉固体内部、流体/損傷・専門シミュレータはこのラボの完成へ含めない。

## ローカル受入（2026-11-04 JST）

専用14試験と全Node516件skip0、構文、Web build fc67426f445af36a/46modules/22entryが成功した。全13presetは実WASMで8成功/5モデル失敗、解析配置・Source所有・signed zero保存を確認。sync loader例外時の再試行不能と再load中の旧runtime使用を実装中に修正し、遅延編集・二重retry・disposeを含め回帰した。

実ブラウザでも全13例、手編集後の旧表示消去、ID0交換拒否とreset復帰、中心x=-0/radius2の境界未確定、XY投影への変更、実ダウンロード2926Bと表示JSONの完全一致・signed zero保存を確認した。数値SDKの55 source/header・7通知・WASM/glue/manifestと全assets/samplesはd9cf168からbyte不変。Native CTest/sanitizerは変更のないSDK段階の受入と区別する。再現と公開受入は[ラボ統合記録](../reports/2026-11-04-sphere-triangle-lab.md)に保存する。

## 最終公開受入

0db8f54で極小区間の表示inkを各側1.5 SVG px広げ、数値は変更しなかった。再ローカル/公開の全13例1491入力・結果bits一致、Node516skip0/32CTest/全Linux CI・Pages成功、公開25ファイル1,078,093B一致。最終ブラウザで編集・ID拒否・復帰・境界未確定・投影変更・実ダウンロード2926Bと表示の一致/-0保存を確認した。[最終統合証拠](../reports/sphere-triangle-lab-public-verification.json)。次の[Native有限集合案](SPHERE_TRIANGLE_MESH_PLAN.md)は設計のみで、World/CCD/ゲーム適用は未完を維持する。
