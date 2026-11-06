# 所有prepare結果の取得依存台帳

2026-11-07。実header `core/include/pikapika/world_static_mesh_flight.hpp`と現在のschemaを照合した開発用台帳。全6型34項目のうち、ColliderRef／Pair／StaticOnlyCountsの3型14項目と[Snapshot／Inventoryの2型13項目](REPORT_PREPARATION_SNAPSHOT_INVENTORY_WIRE.md)をNative有限受入。残るResultの1型7項目は未実装。この台帳自体は数値モデルの認証や実行成功の証拠ではない。

既存取得はStaticMeshSource3項目、Settings5項目、FailureLocation3項目。RigidBody、Plane、StaticTriangleなどの下位値も既存getterを使う。取得時にWorldを再captureしたり、geometryやpairを再queryしたりしない。

| 実型と取得状況 | 項目数 | 宣言順の全member |
| --- | --- | --- |
| Snapshot（Native取得済み） | 6 | gravity, horizon, settings, bodies, planes, meshes |
| ColliderRef（Native取得済み） | 4 | kind, id, ordinal, revision |
| Pair（Native取得済み） | 3 | kind, first, second |
| StaticOnlyCounts（Native取得済み） | 7 | body_body, body_plane, body_mesh, plane_plane, plane_mesh, mesh_mesh, total |
| Inventory（Native取得済み） | 7 | dynamic_bodies, static_bodies, total_faces, colliders, all_pairs, excluded, pairs |
| Result | 7 | status, reason, failure, capture, snapshot, inventory, message |

ColliderRef.ordinalはSnapshot内の元の型付き配列位置で、idとは別。revisionは元の値を保持し、body／planeの場合の0を欠損へ変換しない。Pairのfirst／secondは元の順を保持する。実prepareで生成された一覧の安定キー順と、元の配列順・型付き位置は意味が異なる。人工sourceの不整合を取得側で修正しない。

StaticOnlyCountsは全6種類の除外計数と元のtotalを別々に保存し、取得時に合計し直さない。Inventoryも全5個のcount、除外計数、全pairsを元順で保持し、先頭の一部だけをreadyの一覧として表示しない。

Snapshotは元のgravity、binary64秒horizon、Settings、全bodies／planes／meshesの順序と全値を保持する。planeの法線やoffsetを正規化せず、mesh revisionを計測済み内容hashに見せない。complete captureでも入力がINVALIDな場合があり、allocation failureのpartial snapshotにはコピー済みvector prefixが残り得る。capture状態とsnapshotの有無・内容を独立に保存する。

Result.failure、snapshot、inventoryの各optionalは欠損と存在を区別する。実prepareのinventoryはready時だけ存在し切り詰めないが、保存fixtureでは元の値をそのまま比較し、statusからoptionalを書き換えない。messageは埋め込みNULや非UTF8を含む元のbyte列として扱い、数値モデルの認証に使わない。

[ColliderRef／Pair／StaticOnlyCountsの14項目](REPORT_PREPARATION_PAIR_VALUES_WIRE.md)をNative有限受入。Snapshot6とInventory7もNative有限受入し、次は[Result7](REPORT_PREPARATION_RESULT_WIRE_PLAN.md)を取得する。World guard GuardResult14項目と最上位World Report、C API pump、今回取得のWASM・ゲーム接続は後続。
