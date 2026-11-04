# Worldと静的meshの所有原本・必要pair準備

2026-11-04。新Native APIは機能6608bc3でローカル・公開Linux CI/Pagesの受入を確認。本書の準備段と、[後続の全pair数値guard計画](WORLD_STATIC_MESH_FLIGHT_PLAN.md)を分ける。準備readyは非接触認証ではない。衝突/距離の数値照会・自由伝播・候補body・World更新をこのAPIは行わない。

## 原本を先に所有する

`pikapika::world_static_mesh_flight::prepare(const dynamics::World&, std::span<const StaticMeshSource>, double H, const Settings&)` は同期・read-only。既存Worldはbodyとplaneを所有する。静的meshは新しい値型 `StaticMeshSource{id,revision,triangles}` をcallerが所有し、prepare中はどの入力も他threadから変更しない。constはrace防止ではない。

環境のRN-even/gradual underflow条件を最初に確認する。次にbody8・plane16・mesh1..4・総64faceというhard countを確認し、World gravity/body/plane、全mesh、H、設定を一括copyする。以後の入力検査・組列挙はそのsnapshotだけを読む。byte/allocator/stackのhard上限を約束する段ではない。

`Result.capture` はnone/partial/complete。全copy後のsnapshotにも不良bodyやIDを保持し得るため、completeをvalidと呼ばない。`inventory` はstatus=readyのときだけ存在する。失敗はstatus/reasonとtyped元index/face indexを持つ。allocation失敗のpartial snapshotは完全な入力の代用ではない。

## 全fields・ID・原順

- bodyは既存 `RigidBody::validate()` を再実行する。mutable `find_body` で壊れた値や重複IDも検出する。mass/radius/慣性/位置/q/速度/L/force/torque/material/is_staticの全原本を保存し、force/torqueを消費しない。
- planeは既存Worldのraw normal/offset/material条件で再検証する。near-unit normalを正規化しない。後続guardで必要なWorld中心条件とmetric半空間条件の二つを、この準備だけで証明したとはしない。
- meshはworld座標の静的三角形原本を所有する。ID/revision/face IDは1..2^53−1、collider IDはbody/plane/mesh共通で一意。face IDはmesh内だけ一意で、別meshの同じface IDは許される。
- revisionはcallerの宣言であり、増加履歴やgeometry identityを証明しない。全vertices/order/−0を保存し、revision/hashだけでgeometry比較を省略しない。
- 各mesh1..64面・総64面、頂点各成分±1e12m、Hは有限(0,.1]秒、gravity各成分±1e9。退化面も構造条件内ならreadyになり得る。距離・法線・交差品質は未照会である。

profileの合法範囲はmaxBodies1..8、maxPlanes0..16、maxMeshes1..4、maxTotalFaces1..64、maxPairs1..256で、既定は各hard最大値。設定自体の範囲外はinvalid_input/settings。合法profileを入力件数が超える場合はbudget_exceededを返し、先頭だけの組一覧をreadyにしない。全原本の構造検証は小profile超過の判定より先である。hard超過はbounded capture前に拒否し、無制限の原本copyを行わない。入力拒否・環境拒否・計算失敗を空sceneの成功へ変えない。

## 必要pairと静的除外

body数B、dynamic数D、static body数S=B−D、plane数P、mesh数Mに対して必要数は
`D*M + D*P + C(B,2) − C(S,2)`。各mesh全体が1 colliderであり、この数はface同士の接触数ではない。

| 必要pair | 中身 |
|---|---|
| body_mesh | 各dynamic球proxy × 各静的mesh |
| body_plane | 各dynamic球proxy × 各plane |
| body_body | 少なくとも片方がdynamicの球proxy対 |

各refはkind、ID、元型別ordinalとmesh revision（body/planeは0）を持つ。body_mesh/body_planeはbodyをfirstとし、body_bodyは小さいbody IDをfirstとする。一覧は `(minID,maxID,PairKind)` の順で、元配列順とは独立。元ordinalはsnapshotとの所属を保持する。

除外6種類はstatic body同士、static body×plane、static body×mesh、plane同士、plane×mesh、mesh同士。除外数と必要数の和は `C(B+P+M,2)` に一致する。static-onlyを除外したことは静的形状間の非交差証明ではない。dynamic0でも全入力を検証し、必要0という結果だけを返す。

最大8dynamic/16plane/4meshでは必要32+128+28=188、静的除外120+64+6=190、全28 colliderの378組と会計が閉じる。64faceは全mesh合計である。準備に成功しても、後続数値guardが188組をその診断予算内で認証できるという意味ではない。

## 検証と後続

ローカルではNative42CTest・新89群、Node684/skip0・構文・Web build cd45c7f1ac2ba5e5/54modules26entriesが成功。有限fixture84件（ready24/invalid55/budget5）は全項目を独立Pythonで検査し、complete snapshot78件の7373数値bit/負零801を照合した。hard上限前拒否6件はsnapshot無しと区別する。自己試験12群・改変拒否45件（Python -O拒否を含む）と、label/fixture順序に依存しない照合も成功した。Native専用の非有限入力5検査、FE_UPWARD環境拒否と復帰、caller編集/破棄後の所有・元pointer保持はfinite84のJSON比較とは別である。初回の全CTest120秒timeoutを保存し、製品を変更せず300秒枠で全42件を180.94秒で完走した。SDKへexportしたものではなく、既存92-export/32TUのWASM・Web/ゲームを保持する。

その後、同一snapshotの全pairに対する数値非接触guardを作る。旧acceleratedが返さない証明cell、throw時unknown Work、seed実行順、vectorの保持capacity・一時コピーの会計を解決し、全認証後だけ全body候補を公開する。一般形状応答・摩擦・支持・World advance、専門車両/航空/鉄道、流体・材料損傷・IK制御・任意の高精度撮像は未完である。

本段は既存原本ソースと独自実装のみを使い、新外部library/素材/契約/有料serviceは追加しない。本体licenseは未選定のまま維持する。

Native Worldに時計fieldはなく、既存ABI時刻やゲームtickはこのAPIに接続していない。入力検証はbodyの既存浮動小数点検証を含むが、幾何非接触証拠や運動候補を作るものではない。

再検証は既存のコンパイル済みWorld規約に従う。Vec3::dotはcore.cppの外部関数で、現CMakeではcore.cppをstrict source指定していない。今回の既定x64/有限84入力の一致を、FMA可能な全targetで独立Pythonと同じ別RN境界判定になる一般証明とは扱わない。旧数学核のflagsは変更せず、後続の数値guardで全operation graphのstrict条件と境界入力を別受入にする。

既存static validatorのdot(V,V)==0 / dot(L,L)==0は、非zeroのsubnormalがunderflowする入力も受け入れ得る。prepareは元V/Lを保持し、is_staticタグで組を分類する。厳密zeroや物理的restを証明した意味ではない。FE_UPWARD試験が確認したのは環境優先・丸めcontrol保持と復帰で、全MXCSR/例外flag保持ではない。NaN/Inf専用検査も分類とcaptureの確認であり、全NaN payload bitの検証とはしない。

MSVC19.51.36247.0/x64の最大入力では、sizeofと返却vector実capacityの積から得た保持payloadは21880Bだった（Result内のSnapshot/Inventoryを二重加算しない）。これはallocator overhead・source/call一時領域・stack・RSS/使用heapを含まない観測で、portable hard-byte上限や16MiB保証ではない。[観測](../reports/world-static-mesh-preparation-storage-observation.json)。このローカル時点ではLinux warning/sanitizerは未実施だった。その後の公開受入は下記の別実行で確認した。allocation fault、FTZ/DAZ注入、全pair数値認証は未実施のままである。


## 機能6608bc3の公開受入

[公開集計](../reports/world-static-mesh-preparation-public-verification.json)はfresh public-summary-002でPASS。Engine [41820304200](https://github.com/tatata93/pikapikaengine/actions/runs/41820304200) / job126541504170の全22段と、Pages [41820303901](https://github.com/tatata93/pikapikaengine/actions/runs/41820303901)の全3job/stepが成功した。Linuxの42CTest/684Node skip0、新89群、通常実行84入力と全依存7sourceをASan/UBSanで計装した別84入力を確認。両fixture JSONはbyte一致し、各実行の全入力・結果を独立Pythonで検査した。自己12群/改変拒否45、新3TUのWerrorが成功し、既存48警告は前段とfile/line/column/診断のmultisetが同一、新規0だった。これはNativeの検証であり、準備APIのNative/WASM parityではない。

公開73件＋Pages対象外のworkflowのGitHub完全commit原本1件、計74件2430924Bがfeature Git blobと一致。初回bytes001はworkflowをPagesから取得して404になった。そのrawを保持し、collectorの取得先・distribution/channelだけを明示的4置換で直してbytes002を全件再実行した。製品sourceや照合対象は削らない。最初の集計001はexcerptにANSI色付きloop終端doneが欠けて拒否された。同じ取得済みjob logの原行4件を追加し、doneも含む元の全command照合を維持して集計002が成功した。初回失敗のstdout/stderr/exitを保持する。

公開図と教材は実ブラウザで画像1120×780の読み込み、原本リンク、全記事文字、図の文字・矢印・組会計を確認した。図は概念説明で数値実測ではない。同じ公開ゲームは射撃2撃破・boost energy59・129km/h・一時停止を操作し、23照会すべてchecked/validated/completed、resident mesh3、errors0を記録した。prepareをブラウザやゲームの数値接触に接続した証拠ではない。

保存したCI抜粋は全11818行/876630文字のうち4621行を原ordinal付きで選択したもので、完全remote logを保存したとは主張しない。既存355raw・旧26HTML・7つの新準備source・92export SDK/runtime91/32TU/7通知・WASM800982B/glue61661Bは公開集計時も保持された。scope、所有入力bit、capacity観測の限界は上記ローカル記録を維持する。

起動: [ロボットゲーム](https://tatata93.github.io/pikapikaengine/?v=6608bc3) / [原著教材](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v=6608bc3#accelerated) / [準備の概念図](https://tatata93.github.io/pikapikaengine/docs/learn/diagrams/world-static-mesh-preparation.svg?v=6608bc3)。次は球対/平面の全closed-cell非接触coverageを所有して独立監査する核へ進む。全World候補・接触応答・流体/材料損傷・専門モデル・IK制御・高精度撮像は未完。
