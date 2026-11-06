# 元の所有Snapshotと全Inventoryを保存する次段

2026-11-07。ColliderRef／Pair／StaticOnlyCountsの3型14項目の受入後、実`world_static_mesh_flight::Snapshot`6項目と`Inventory`7項目を取得する。実Native受入は[所有SnapshotとInventoryの取得](REPORT_PREPARATION_SNAPSHOT_INVENTORY_WIRE.md)を参照。この計画自体は実行証拠ではない。

| 実型 | 宣言順の全member |
| --- | --- |
| Snapshot | gravity, horizon, settings, bodies, planes, meshes |
| Inventory | dynamic_bodies, static_bodies, total_faces, colliders, all_pairs, excluded, pairs |

Snapshotは元のgravity、binary64秒horizon、全Settings、全body／plane／meshと下位値を元配列順で保存する。法線・orientation・力・gravity・horizon・mesh revisionを取得時に正規化、演算、照会、再captureしない。空配列と非空配列、重複・不整合・部分prefixも元のまま扱う。実prepareではcomplete captureでもINVALIDになり得るため、取得側でvalidなsourceに修正しない。

Inventoryは全5countと全除外計数・元total、全Pairをそのまま保存する。pairsの元順と両参照の型付き元ordinalを保持し、id順へ並べ替え直さず、all_pairsや除外totalを合算し直さない。実prepareはready inventoryを切り詰めないが、人工保存fixtureをその実行契約の証明と混同しない。

人工fixtureでは異なるgravity／horizon bit、負零、全count境界、各配列の空／単要素／複数、元順・重複、異なるid／revision／型付きordinalと全下位値を独立仕様で照合する。元の数値をGetterから再構築せず、全scalar／key／field／arrayの異なる有効文法変更を検査する。同値交換は別計数とし、byte数・fixture数・変更分割数は実測後に固定する。

各callbackでの停止／例外、全getterのsink再入、4丸めmodeを検証する。既存46＋新1の実CTest、全旧assertion JSON本文と全raw fixture、20profile、保護原本、17header gateを保持する。確認済みのCTest抽出方式を使う場合も、直接stdoutの全raw byteと同一とは呼ばず、全テスト名・実command・値・順序とraw protocolを照合する。

製品2data TU＋harness1の3TUを基本とし、fixtureで追加の元TUが必要なら試験用依存として明記する。数値model libraryは結合せず、実再帰oracle閉包をsource-before／afterへ固定する。実Native受入は95record型554項目＋別variant2型。Native、GNU、公開は別受入。

次はprepare Result7、GuardResult14、最上位World ReportとC API pump、今回取得のWASM・ゲーム接続。この保存試験を一般接触・摩擦・CFD・塑性損傷・光学モデルの完成と読み替えない。
