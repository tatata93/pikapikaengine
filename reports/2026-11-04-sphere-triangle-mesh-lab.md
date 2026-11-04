# 球×静的三角形集合の手動ラボ

2026-11-04 JST。ローカル受入PASS、公開CI/Pages・配信byte・公開操作は確認待ち。実装原本は tools/sphere-triangle-mesh-lab.html / .mjs。既存の74-export SDKを使い、C++/SDK/全assets/sample原本に変更を加えていない。

## 追加した操作

最大64面のsourceを元順で保持し、全行のstatus/reason・候補prefix数・検査数・sqrt反復/制限を表示する。最小になり得る全IDを保持し、閲覧面を最小面の確定と扱わない。面固有geometry/候補/KKTの閲覧、XY/XZ/YZの説明図、strict signed-zero JSONの全結果保存を追加した。集合失敗後も実行済みの正常/失敗/後続行を残す。事前拒否の入力面は未照会と表示し、架空のNative rowを作らない。

input/edit/reset/retryは旧結果を即消去する。loadをcoalesceし、同期throw/rejectからretry可能、reload中に旧runtimeを使用しない。遅延完了/disposeと入力変更の世代を検査する。旧SDK/host拒否にJS幾何fallbackを置かない。入力64KiB/depth10/6000nodes、出力4MiB/depth20/200000nodes。65面は入力例として編集できるが実SDKで拒否し、切り詰めない。

## 実行した検証

- 専用Node/DOM18、全Node544/skip0、構文、Web build457dd1cda43de02c・47modules/23entry成功。専用harnessは実HTMLの全control ID/17optionとの配線も確認する。
- 変更していないRelease Native binariesの34CTestを再実行。新C++buildやWindows sanitizer実行はこのUI段階では主張しない。
- SDK48入力=45model(29成功/16失敗)+3host拒否を再照合。実WASM27160packet/20808model numeric bits・4453負零、独立2775成分と43改ざん負例、旧single22327/13432 bits、既存simulation回帰が成功。
- 実ローカルブラウザ17例=10成功/6モデル失敗/1host65拒否。64行/全64possible IDs/最終面の7候補、編集即旧表示消去、ID0拒否/reset、−0/radius1編集/retry、失敗後の最終正常面閲覧と集合nearest不在、XY/YZ表示を確認。
- 実ブラウザ21結果packetと2実Blob downloadを保存。入力/結果と保存DTOの42644数値bits（5733負零）が実WASM再照会/表示保存と一致。ダウンロードは表示JSONとbyte一致。timing/起動msをNodeと同値だとはしない。
- 既存45fixtureのcoverageを維持した独立Fraction参照へ実ブラウザ21packetを追加し、7353成分（既存2775+追加4578）を検査。source/result/候補/全workとnearestの包含を再確認した。
- SDK57原本/7通知/2artifactのmanifest hash一致、全assets/sample原本の前段hash一致、core/engine/assets/samples/third_partyのgit差分なし。新依存なし、教材25記事と原著図を維持。

証拠: sphere-triangle-mesh-lab-local-verification.json、*-local-browser-verification.json、*-local-rational-verification.json、*-checks/run-20261104-root/ のcommand/stdout/stderr/hash、*-local-browser/ の可視DOM/JSON/実download/PNG。再現recipeは *-recipes/。

初回の専用試験ではcapacity65の通常ErrorをSimulationErrorに固定した期待が1件誤っていた。実交換境界に合わせて訂正し18件成功。数値queryの意味変更ではない。UI確認で最初のdetailsをAX由来button selectorで取得できなかったため、実summary selectorで操作を続けた。未実行の操作を成功としない。

## 境界と次段

このラボは瞬間のread-only照会である。World/時間発展/CCD/接触応答/manifold・ゲームmesh衝突は未接続。流体場、材料損傷、専門車両/航空/鉄道、IK/制御、高精度撮像等の残件も維持する。公開受入後、有限の線形軌道全区間について球と静的三角形集合の非接触を確認するguardの契約から進める。非接触を証明できない場合を衝突確定や成功軌道へ読み替えず、最初はNative純粋照会に限定する。
