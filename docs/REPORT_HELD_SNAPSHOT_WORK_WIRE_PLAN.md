# 保持荷重の全入力snapshotと計算記録の取得条件

2026-11-06。未実装の次段。HeldSphere/Cell/WorldBodySnapshotの次に、同じheld headerの2型15項目を取得する。

| 型 | 全member |
|---|---|
| Snapshot | input, horizon, triangles, settings |
| Work | mesh_queries, primitive_queries, candidates_examined, primitive_sqrt_refinements, enclosure_sqrt_refinements, sqrt_refinements, sqrt_refinements_upper, mesh_sqrt_limited_rows, enclosure_sqrt_calls, enclosure_sqrt_limited_calls, exact |

Snapshot.inputは実HeldSphere、horizonは元の秒のF64 bit、trianglesは元順の全StaticTriangle、settingsは実held Settings。
getterで入力を再構築・補正せず、力/質量から加速度を作らない。空/複数/重複/異なる元順のtrianglesを人工診断で区別する。
設定値が物理モデルで有効という判断とは分ける。

Workはsize_t10項目をU64、exactをboolで取得する。guard::WorkやHeldLedgerとは別の実型。
sqrt_refinements_upperを実回数から再計算せず、既知/未返却の予約上限を実記録のまま残す。
CellAudit.workは差分、Result.workは集計であり、取得時にそれらを合算・検算して置換しない。

最初は構築済み公開値の人工fixture。各型の複数record、全typed field/原順/F64 bit/full64/flagを独立比較する。
数値照会・再構築・動的確保・新しい数値TUを製品へ追加しない。新testはこれらの値を直接構築し、数値libraryをlinkしない。
全callback停止/例外/再入、4丸めmode保持、全byte再取得を確認する。
fresh Release/真Debugで旧10fixtureの3112/4587/3706/3937/1037/3241/12924/5414/20256/2507byteと全run出力を保持する。
schemaは43型247項目を見込み、実getter順との全descriptor照合で確定する。既存16header+manifest gateと旧20数値profileを維持する。
GNU通常/真Debug/全新TU O1 ASan-UBSanとNative全byte一致は別受入。数学核/owner/SDK/sampleを保持する。

その後InitialProof/CertifiedLeaf/Witness/EntryWindowなどの小型証明recordへ進み、
optional配列・optional enumの型を明示してCellAudit/PartitionLeaf、全Result、最上位Reportへ接続する。
この計画は全Report、C API pump、JS/WASM/game接続の実装ではない。

初fixtureの具体案: Snapshotは空triangle、複数triangle、異なる元順を持つ複数recordを使う。
full64のIDと重複、頂点の逆順、異なるhorizonと入れ子設定の全memberを保持し、ソートやsource修復が入らないことを比較する。
Workは全0/trueと、10項目がそれぞれ異なる0・2^53超・U64最大値を含むfalseを用意する。
人工的に値とflagを組み合わせた取得試験であり、実モデルの計測値や有効な予算として紹介しない。
新harnessにはInterval構築も不要なので、3TU（製品2＋試験1）だけの実flags/link入力を記録する。
