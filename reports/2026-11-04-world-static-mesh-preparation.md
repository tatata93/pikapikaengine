# Native World/static-mesh原本と全必要pair準備

2026-11-04。baseは公開済み7176c1fe283ac94d061db34411e941d376690123。新prepareは機能6608bc3963a7eaca1ac8a9d40f3ae5d76f93d05eでローカル・公開受入PASS。公開Linux CI/Pages・warning/sanitizer監査も確認した。準備readyは構造検証であり、衝突照会・自由伝播・候補・World更新の成功ではない。

新 `world_static_mesh_flight::prepare` はWorld全body/raw plane/gravity、静的mesh ID/revision/全face、Hと設定を一括所有し、snapshotだけを再検証する。環境とhard countを先に検査し、入力不正を保持したcomplete snapshotと、ready時だけの全inventoryを分ける。低profileで先頭だけの一覧を返さず、型別元ordinal・mesh revision・全原順・負零を保つ。force/torque・caller pointer/storageを変更しない。

最大8dynamic/16plane/4mesh/全64facesの必要188組とstatic-only190組が全378組へ閉じる。face IDはmesh内namespace、collider IDはWorld/body/plane/mesh共通、revisionはcaller宣言である。静的除外・退化faceの準備成功を非接触や厳密restの証明としない。[契約](../docs/WORLD_STATIC_MESH_PREPARATION.md) / [後続guard計画](../docs/WORLD_STATIC_MESH_FLIGHT_PLAN.md) / [原著図解](../docs/learn/diagrams/world-static-mesh-preparation.svg)。

## 実行・完全入力・回帰

[ローカル集計](world-static-mesh-preparation-local-verification.json)は、`world-static-mesh-preparation-checks/run-20261104-local-summary-001/`でPASS。全command/開始/所要秒/exit/stdout/stderrと前後source hashを記録する。canonicalはNative002、reference001、regressions001。

| 対象 | 確認した範囲 |
|---|---|
| Native | 全42CTest成功、新89群（有限84＋所有・置換・最大容量・非有限・環境の5群） |
| 有限完全入力 | 84：ready24 / invalid55 / budget5 |
| capture | hard前拒否none6 / complete78。invalid completeをreadyへ変えない |
| 完全所有入力 | complete78の7373数値成分のbit一致、負零801。整数metadataはexact int値も比較 |
| 組会計 | ready集合の必要362＋除外864＝全1226、最大必要188/全378、全6静的分類 |
| 独立参照 | 全collider二元部分集合から型別pairを再構築。label/fixture順には非依存、原配列順・全入力型/bitのmultiset fingerprintは固定 |
| 検証器の負例 | 自己試験12群、44コピー/入力等の改変＋Python -O拒否＝45。正常packetを通しただけで正しい検証器としない |
| Node/Web | 全684/skip0、構文成功、build cd45c7f1ac2ba5e5 / 54modules / 26entries |
| 原本保全 | 355既存raw、旧26HTML生成rawと本文を保持。CMake/CI/byte保存規約だけへ宣言した追加 |
| SDK | export92 / source-header67 / TU32 / runtime91 / 7通知。WASM800982B・glue61661Bと全manifest byte同一 |

原本JSONは221918B、SHA256 `ba3eb26cb98642c29b4e8a3af587450fd7dfa87540cf403ee4447e2c2095c5ac`。全input multiset fingerprintは `4bfee81b01fcbfe5d7539c3960f35e467fa08db3d8bdfe5dc6badb9fc5853d4c`。これはraw file hashや固定name一覧とは別で、label/fixture順だけの置換を許す。Native NaN/Inf5検査とFE_UPWARD優先/丸めcontrol保持/復帰は有限JSON84とは別に実行した。全NaN payloadや全MXCSR/例外flag保持を検査したとはしない。

## 容量観測と既存浮動小数点規約

[storage観測](world-static-mesh-preparation-storage-observation.json)はMSVC19.51.36247.0/x64。最大入力の返却vector実capacity×sizeofとinline Resultから得た保持payloadは21880B。Result内のSnapshot/Inventoryを重複加算しない。allocator overhead、外部sourceと呼出一時領域、vector成長の一時buffer、stack、RSS/使用heap、portable hard-byte/16MiB上限は含まない。実allocation faultを注入したとも扱わない。

新prepare TUはstrict/noFMAでbuildするが、既存Vec3::dotは外部core.cppへ委譲し、現CMakeはcore.cppをstrict source指定していない。実行した既定x64/有限84の整合を、FMA可全targetの別RN境界保証にはしない。既存static validatorはdot(V,V)/dot(L,L)のunderflowによって微小非zeroを受け入れ得る。その元値は保持し、is_staticタグで組を分類する。準備は厳密zero/restの証明ではない。旧数学核のsource/flagsは変更せず、後続数値guardで全operation graphと境界fixtureを監査する。

## 初回試行・原本・公開

最初のNative001はconfigure/build・新専用0.08秒と既存11件が通過したが、全CTestを120秒で待ち切れず停止した。失敗判定ではなくtimeoutをそのまま保存し、製品sourceを変えずNative002で全42件を180.94秒（wrapper180.99秒）で完走した。待ち枠は300秒で、モデルの上限や合格条件は変更していない。

独立自己試験の初回1失敗は、3body反転の中央ordinalが変わるという誤期待だった。実際に変化するplane ordinalを参照するよう自己試験を直し、元raw/source前後hashを保持した。初期の自己12群と実84件前の参照を、最終actual受入へ混ぜない。最終agent検証はreference-run-005、親の再実行はreference-001。

新依存/package/外部solver・素材/有料serviceなし。本体licenseは未選定。ゲーム原本は保持し、このNative準備をゲームの接触モデルへ適用していない。原著SVGはローカル実ブラウザで文字・矢印・378組会計の表示を確認したが、図を数値証拠へ代用しない。

公開受入の詳細は以下に追記した。次は、同じ所有snapshotの全pairに数値非接触証拠・全体予算・seed順を接続し、全認証後だけ全body候補を返す。接触応答・摩擦/支持・World advance、専門シミュレーター・流体・材料損傷・IK制御・高精度撮像は未完である。


## 機能6608bc3の公開受入

[公開集計](../reports/world-static-mesh-preparation-public-verification.json)はfresh public-summary-002でPASS。Engine [41820304200](https://github.com/tatata93/pikapikaengine/actions/runs/41820304200) / job126541504170の全22段と、Pages [41820303901](https://github.com/tatata93/pikapikaengine/actions/runs/41820303901)の全3job/stepが成功した。Linuxの42CTest/684Node skip0、新89群、通常実行84入力と全依存7sourceをASan/UBSanで計装した別84入力を確認。両fixture JSONはbyte一致し、各実行の全入力・結果を独立Pythonで検査した。自己12群/改変拒否45、新3TUのWerrorが成功し、既存48警告は前段とfile/line/column/診断のmultisetが同一、新規0だった。これはNativeの検証であり、準備APIのNative/WASM parityではない。

公開73件＋Pages対象外のworkflowのGitHub完全commit原本1件、計74件2430924Bがfeature Git blobと一致。初回bytes001はworkflowをPagesから取得して404になった。そのrawを保持し、collectorの取得先・distribution/channelだけを明示的4置換で直してbytes002を全件再実行した。製品sourceや照合対象は削らない。最初の集計001はexcerptにANSI色付きloop終端doneが欠けて拒否された。同じ取得済みjob logの原行4件を追加し、doneも含む元の全command照合を維持して集計002が成功した。初回失敗のstdout/stderr/exitを保持する。

公開図と教材は実ブラウザで画像1120×780の読み込み、原本リンク、全記事文字、図の文字・矢印・組会計を確認した。図は概念説明で数値実測ではない。同じ公開ゲームは射撃2撃破・boost energy59・129km/h・一時停止を操作し、23照会すべてchecked/validated/completed、resident mesh3、errors0を記録した。prepareをブラウザやゲームの数値接触に接続した証拠ではない。

保存したCI抜粋は全11818行/876630文字のうち4621行を原ordinal付きで選択したもので、完全remote logを保存したとは主張しない。既存355raw・旧26HTML・7つの新準備source・92export SDK/runtime91/32TU/7通知・WASM800982B/glue61661Bは公開集計時も保持された。scope、所有入力bit、capacity観測の限界は上記ローカル記録を維持する。

起動: [ロボットゲーム](https://tatata93.github.io/pikapikaengine/?v=6608bc3) / [原著教材](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v=6608bc3#accelerated) / [準備の概念図](https://tatata93.github.io/pikapikaengine/docs/learn/diagrams/world-static-mesh-preparation.svg?v=6608bc3)。次は球対/平面の全closed-cell非接触coverageを所有して独立監査する核へ進む。全World候補・接触応答・流体/材料損傷・専門モデル・IK制御・高精度撮像は未完。
