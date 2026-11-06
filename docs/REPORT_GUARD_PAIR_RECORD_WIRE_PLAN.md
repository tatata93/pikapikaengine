# 接触ペアの元順と実行位置を保存する次段

2026-11-07。Child variantの次は、実宣言`world_static_mesh_flight_guard::PairRecord`全5項目を取得する。

| 宣言順 | 項目 | 保存契約 |
| --- | --- | --- |
| 1 | pair_ordinal | 元の所有inventory内のペア位置。保存順や実行順へ振り直さない |
| 2 | state | 実PairStateをenum tagで保存 |
| 3 | reason | 実Reasonをenum tagで保存 |
| 4 | execution_ordinal | 最初の実child呼出位置のoptional count。欠損と0を区別 |
| 5 | child | 実Child variantと全下位値。型から成功・実行済みを推測しない |

既存const getterとWriterだけを使い、query、数値モデル、順序修復を加えない。異なるpair_ordinal／execution_ordinal／Call.attempt_ordinal、未実行・依存失敗・非認証・認証の全状態、独立Reason、全3Child alternative、Resultの存在／欠損と未処理tailを人工fixtureで検査する。実際の型・値・順序は独立仕様で比較し、byte数とfixture数は実測後に固定する。

各callbackでの停止・例外と再入、4丸めmode、正当な公開emplaceによるChildの実値なしと旧値保持を別々に測定する。実値なしの場合は親recordと先行4項目を含む実送信済みprefixを保持し、新しいvariant byteを送信しない。既存sticky失敗と親の処理位置も検査する。private representationを変更しない。MSVCとGNUの分岐は別実測にする。

全field／optional／enum／array／variantの異なる有効文法変更を照合する。入れ子variantの非重複child交換と親子両方向subtree置換を維持し、全組を分類して省略しない。同値交換を別計数にする。実使用scannerの原本と全再帰oracle moduleをsource-before／afterとGit blobへ固定する。

旧44＋新1の各45選択CTest、旧全fixtureと実行出力、20profile、保護原本、17header gateを維持する。製品2data TU＋harness1＋元Interval試験用1TUだけを使い、数値model libraryは結合しない。Webテスト・構文・buildと原著図解を確認する。受入後の予定は90record型527項目＋別variant2型であり、この計画自体は実装・実行成功の証拠ではない。

準備Resultの未対応依存、GuardResult14項目、最上位World ReportとC API pump、今回取得のWASM・ゲーム接続は後続。人工診断の保存試験を実Worldの接触モデル・摩擦・CFD・塑性損傷の認証に読み替えない。
