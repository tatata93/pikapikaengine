# 保持荷重・自由伝播guardの所有JavaScript API

2026-11-04。ローカル受入成功、公開CI/Pagesは次に検証する。feature commitは公開受入追記で確定する。

## 実装範囲

`engine/sphere-triangle-mesh-flight.mjs`を追加し、既存runtimeにはimportと`querySphereTriangleMeshHeldLoad`/`querySphereTriangleMeshFreeFlightGuard`の2methodのみを追加した。全6能力を最初の書込前に確認し、原入力の全階層を一度captureする。モデル上不正でも有限な入力はNative診断へ渡し、host型/配列長/非有限/unsafe ID等は書込前に拒否する。元runtime/native/export/prototypeを置き換えない。

全21record kind、lastMesh全行/candidate、全audit/partition/frontier/tail、秒のclosed被覆と幅優先履歴、Work既知値/予約上限を復元する。元入力・echo・Native snapshot・inflated照会・Hの成功candidateを別所有にする。合法な区間/原入力/KKTの負零と、metadata/予約領域の正零を区別する。成功candidateの数値domain監査は、不正な元bodyを診断する際のコピーへ適用しない。

数学solverのJS代替やWorldの時間進行・応答は追加しない。原著[ガイド](../docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS.md)、[SVG](../docs/learn/diagrams/sphere-triangle-mesh-flight-owned.svg)、既存教材の追記を同梱した。新依存・転載素材・有料serviceなし、本体license未選定。

## ローカルの実行結果

[集計JSON](sphere-triangle-mesh-flight-js-local-verification.json)と[再実行recipe](sphere-triangle-mesh-flight-js-recipes/check.py)を保存した。最終canonicalは`reports/sphere-triangle-mesh-flight-js-checks/run-20261104-final/`。

| 対象 | 実測結果 |
|---|---|
| 専用Node | 30/30、skip0 |
| 全Node / Native CTest | 661/661 skip0 / 41/41 |
| 所有APIへの固定入力 | 183完全入力、173実モデル / host拒否10 |
| cohort | held74/5、guard95/5、supplemental4/0（実モデル/host） |
| 数学DTOの全bit比較 | 263083数値 / 負零5102 |
| 実173のoriginalInput全bit比較 | 16851数値 / 負零334 |
| 全183入力echoの追加比較 | 7520数値 / 負零12（上記とは別scope） |
| 所有API後の実getter比較 | 368904数値 / 負零4978 |
| 独立Fraction | WASM由来の173モデル、コピーDTO改ざん15拒否、Python -O拒否 |
| 保護 | 345原本byte不変、25HTMLの生成import map/build URLのみ更新 |
| SDK | 92exports / 67source-header / 32TU、runtime91members / 7通知、manifest全保持 |
| Web | build836a4c2102a528cd、52modules / 25entries |
| 実ブラウザ | 新API固定2例3891数値bit / 負零66、既存ゲーム2撃破/boost/停止、52照会全完了/3常駐/error0 |

実入力の上限profileはsource64、audit256、leaf128、partition128、frontier127、保守ID64、lastMesh64行/448候補。各上限profileの観測であり、全上限の同時heap最大測定ではない。実173入力fingerprintは`684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb`。

WASMは800982B、SHA `a7db41c64d2f9112ec5ee033371c391dddcb42ad23dcef713347c129a4ed015d`。glue61661BとSDK provenanceを再生成せずbyte保持した。旧W1 Native全20のJSON byte、旧SDK20の4520数値/負零24、旧entryの全所有DTO/原本/90負例を再照合した。

query summary24は正式decoderが実際に消費して検査するが、所有API後は後続getterが共有出力を上書きし、summary専用getterはない。この段のraw readback値は全21kind/lastMesh/candidateだけであり、summaryをNativeから補填したりexportを置き換えて収集したとは扱わない。summary全fieldの人工改ざん試験、全DTO照合、前段raw ABIの全wire照合を出自別に保持する。enumをstring化した所有DTOの数値件数をraw DTO件数と同一視しない。

HEAP容量の初期/最大/終了は67108864B、buffer変化0、view取得12514回。usedHeapBytes/stackHighWaterBytesはnull、実growthは未行使。人工view差替えは実allocator/fenv/exception故障注入ではない。能力/入力拒否は書込前だが、正常query後のdecoder拒否でNative record/outputのrollbackは保証しない。

## 初回失敗と訂正

- 初回専用30群の29成功/1失敗: 成功candidateのq=2への人工改ざんを見逃した。原入力を過剰拒否せず、成功candidateのみ既存Native数値domainとq正規化条件を検査し、同じ30群を再実行して成功。[root初回](sphere-triangle-mesh-flight-js-checks/run-20261104-focused-001/)と[独立初回/再試行](sphere-triangle-mesh-flight-js-test-development/)を保存。
- 初回実183 replayは、全実DTO・原本・getter・173 Fraction/15負例/-Oの処理後、証拠パスをstrでhelperへ渡した報告コードの型誤りでexit1。[原command/全capture/child raw](sphere-triangle-mesh-flight-js-agent-tests/run-001/)を残し、Pathへ直して新fresh directoryで全実行をやり直した。最終ownedは82.313783秒、source前後不変でexit0。
- [合成codec6群](sphere-triangle-mesh-flight-js-reference-attempts/run-001/)の成功は、実WASMの173モデル成功件数へ加算しない。
- 前回の公開Engineは約13分40秒で、今回追加した所有/Fraction実行82.314秒が15分枠の残り80秒を超える。既存標準runnerのjob上限を20分へ変更した。ローカル実行時の旧workflow全byteと[変更の出自](sphere-triangle-mesh-flight-js-recipes/ci-budget-transition.json)を保存し、timeout行だけの差を監査する。実コード/テストの成功を改変しておらず、新workflow自体の受入は公開CIで確認する。

## 次段

[手動ラボ計画](../docs/SPHERE_TRIANGLE_MESH_FLIGHT_LAB_PLAN.md)の入力編集・世代管理・全診断閲覧・負零を保つ原本/結果JSON保存を実装する。固定API実行画面は手動編集ラボ完成を意味しない。一般形状の全pair順序/接触応答、流体・材料損傷・専門モデル・IK制御・高精度撮像は未完。
