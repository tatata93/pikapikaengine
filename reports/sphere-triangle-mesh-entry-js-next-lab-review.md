# 次の手動entryラボの準備調査

2026-11-04。UIは未実装。既受入65入力と既存trajectoryラボを読取調査し、次段の依存を整理した。入力値・数学核・期待値は変更していない。参照元は`reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json`（2490705B、SHA256 f63520a3d79f2558879c2dff15a1f2b48dfe09fbee920c12cf828c712044a407）。

主presetの候補25名:

```
static-face
actual-256-audits-128-leaves
actual-64-entry-all-conservative-ids
breadth-frontier-budget
127-leaf-budget-preserves-prefix
255-evaluation-budget-includes-initial
analytic-entry-quarter
symmetric-midpoint-normal-failure
multiple-entries-first-quarter
wide-tolerance-is-still-proof
tight-tolerance-depth-budget
initial-strict-negative
initial-exact-boundary
initial-zero-distance-normal-failure
exact-vertex-tangency-no-negative
middle-degenerate-later-row-preserved
surface-budget-before-query
sqrt-reservation-before-mesh
sqrt-reservation-before-enclosure
duplicate-source-id
empty-source
endpoint-outside-domain
invalid-tolerance-zero
65-source-rejection
inside-rounded-anchor-no-false-witness
```

この組合せは、固定参照の24モデル（separated2/window5/initial_penetration1/not_certified12/invalid4）と65面のhost拒否1を含む。新ラボをこの25例で実行した結果ではない。256audit/128partition、127frontier、全64候補ID、初期正/負/境界、法線未確定ancestorからの回復、E補正、複数侵入、異なる予算停止を含む。reverse-entry-seven-twelfths・signed-source-zero・zero-source-idは追加入力試験候補とする。自然corpusにないunsupported_environment/numerical_failureの表示試験は人工DTOと明記し、自然実行へ数えない。

旧ラボから原入力strict parser/完全保存・load世代の無効化・read-only投影を参考にできる。ただし新default depth24、initial singleton、bestWitness/window、全partition/tail、最大frontier128を新しい契約で表示する。旧witness・DFS33・全域安全の表示を名前だけ置換して流用しない。lastMeshは所属auditだけへ重ね、別auditでは表と所属注記で保持する。projectionや選択変更は再queryせず、入力変更は古い結果と保存ボタンを消す。保存した完全JSONと実ブラウザの直接SDK再照会をbit照合する。

次段で固定する差分: `multiple-entries-first-quarter`の全保守候補ID `[5,37]`をlastMesh nearest `[37]`へ縮めない。`wide-tolerance-is-still-proof`のwindow `[0,.375]`、safePrefix `[0,0]`、後方認証島 `[.5,1]`を別表示する。`symmetric-midpoint-normal-failure`のaudit1 row_failure/splitを成功時にも保存し、最終audit61のwindowと混同しない。旧ラボmodule末尾は自動初期化するため、新helperからimportして旧DOMへ作用させない。共通strict-json等だけを参照する。保存予算は最終LFを含めて検査する。

実装・統合順は[手動ラボ計画](../docs/SPHERE_TRIANGLE_MESH_ENTRY_LAB_PLAN.md)に従う。helper/preset/codec、DOM表示/世代、実WASM試験、HTML/原著図、build登録、実ブラウザ全例/保存、公開受入を別に検証する。新UIをWorld/接触応答の完成として扱わない。
