# 所有prepareの型付きペアと除外計数を保存する次段

2026-11-07。Guard PairRecord5項目の受入後、実`world_static_mesh_flight`のColliderRef4、Pair3、StaticOnlyCounts7の3型14項目を取得する。全依存は[prepare台帳](REPORT_PREPARATION_DIAGNOSTIC_INVENTORY.md)。実装・実行はまだ行っていない。

ColliderRefはkind、id、ordinal、revisionの宣言順。kindはenum、id／revisionはU64、ordinalはcount。Pairはkind、first、secondの順で、両方のColliderRefをそのまま保持する。StaticOnlyCountsは全6除外countとtotalを宣言順に保存し、取得時に計数を合算・修正しない。

人工fixtureで全ColliderKind／PairKind、独立したid・型付きordinal・revision、0／U64最大値／2^53+1／2^63の整数境界、元のfirst／secondの異なる順序を比較する。静止のみの全6計数とtotalは互いに異なる値にし、totalの不整合も保存する。これは保存契約の試験であり、実prepareの入力受理条件や静止物体間の非接触認証ではない。

既存Writerとconst getterだけを使い、World再capture、pairの再列挙、query、順序修復を行わない。独立仕様で全type tag・値・key・順序を照合し、各callback停止／例外、sink再入、4丸めmodeと全変更検査を行う。同値交換は分離し、実参照moduleの全閉包を固定する。byte数やfixture数、変更数は実測後に記録する。

旧45件を含む選択CTest、旧全fixtureと実行出力、20profile、保護原本、17header gateを保持する。製品2data TU＋新harness1を基本とし、元Interval TUが必要なら試験用依存として明示して数値model libraryを結合しない。受入後の予定は93record型541項目＋別variant2型。Native、GNU、公開は別受入。

その後Snapshot6／Inventory7、Result7、GuardResult14、全World Report／pump／WASM・ゲーム接続へ進む。この計画だけで各型を取得済みと数えない。
