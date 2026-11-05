# 静的meshの行と最近傍候補を取得する次段

2026-11-06。設計・実装前の受入条件。Result取得3516d037の次段であり、下記2型はまだ取得対応していない。

`sphere_triangle_mesh.hpp`は既存16header gateの対象。新しい数値核・照会・外部libraryは不要。
最初の最小実装はRowの2項目とNearestの4項目。既存Record::optional/arrayと区間・Result取得を再使用する。

| 実型 | 項目と型 |
|---|---|
| Row | triangle: StaticTriangle、query: optional sphere_triangle::Result |
| Nearest | squared_distance/distance/gap: Interval、possible_surface_ids: vector U64 |

Row.queryなしはfatalな外側例外後などの未照会を表し、分離やmissの結果にしない。
元triangleの安定ID・頂点順と、実queryの全診断を別々に保持する。queryから元triangleを再構築しない。
NearestのID列を一意winnerへ変えず、ソート・重複削除・53bitへの丸めもしない。
取得の型保存試験は、公開memberの人工値と実モデルが受理した結果を区別する。

人工fixtureはqueryなし/ありの複数Rowと、空/複数/重複IDのNearestを含める。
triangleは異なるID・頂点順・F64 bitを使い、queryありには前段Resultのoptional/候補/messageまで含める。
ID列は0、2^53+1、U64最大値、重複・異なる原順を区別する。人工的なdomain外の値をモデル成功とは呼ばない。
区間は既存実Intervalの負零/subnormal/最大有限/無限境界を使い、NaNを内部へ捏造しない。

独立Python参照で全typed値・原順を比較し、field/byte/ID/recordの改変、optionalの有無の改変を拒否する。
全callbackで停止/例外/同writer再入を試し、構築済み値の4丸めmode保持と元入力不変を確認する。
旧7fixtureの3112/4587/3706/3937/1037/3241/12924byteと全run出力を同じfresh Release/Debug構成で比較する。
旧20数値profile、owner/SDK/sampleと数値原本を保つ。製品2TUと試験専用interval.cppの分離を維持する。
16header＋manifest gateの変更欠落拒否とdescriptor全項目一致、GNU通常/真Debug/全4TU ASan-UBSanは別に受け入れる。

次のmesh::Resultは全12項目。failed_index/first_failed_rowはoptional size_tとしてU64へ明示的に写す。
現在のResult用optional helperを32bit環境のsize_tへ暗黙適用してU32にしない。
rows全体・未照会row・nearestの有無、queries/candidates_examined/sqrt_refinements/sqrt_limited_rows/failed_rows、
status/reason/messageを保持する。外側の失敗位置からrowの実queryを推測しない。
全audit/partition/frontier、最上位Report、C API pump、JS/WASM/game接続はさらに後続。


追記: この2型のNative有限実装を受入。現状は[実装ガイド](REPORT_MESH_VALUES_WIRE.md)。新GNUは別受入、mesh全Resultは次段。
