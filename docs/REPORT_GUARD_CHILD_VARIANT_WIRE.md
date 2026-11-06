# Childの実active型と全診断を保存する

2026-11-07。`world_static_mesh_flight_guard::Child`のconst取得をNative有限受入。89record型522項目は不変、別variantはInputとChildの2型になった。正式記録は`reports/diagnostic-wire-guard-child-variant-verification.json`。GNUと公開は別受入。

| 実ordinal | 実active型 | 保存内容 |
| --- | --- | --- |
| 0 | MeshCall | 全8項目と自由飛行Result全値または欠損 |
| 1 | PlaneCalls | metricとboxの全Call、独立result、入れ子Input variant |
| 2 | SphereCall | 全8項目と球coverage Result全値または欠損 |

既存v1のvariant tag、32bit ordinal、実active child、endを出力する。`std::get_if`で実型を取得し、既存の各getterへ渡す。値の再計算やquery、attempt_ordinalの振り直し、欠損の補完を行わない。実値なしは既存Writerの`reject_invalid_value()`へ渡し、新しいbyteを送信しない。既に送信した外側prefixや既存sticky失敗を取り消さない。

全3alternativeにわたる人工6Childの全47,050byte SHA256 `db51ed704d13c9ca4a092b5b35b8eba54efac41d6d3fcdcdcd653fa561dcb7b0`を独立比較。1,442typed leaf（F64 734／負零60、U64 333、U32 136、bool83、enum151、bytes5）、存在106／欠損121、外側6＋入れ子Input1の全7variantが一致した。原著の既存Call定数と既存pair Result人工source headerを再利用し、共有headerを追加しない。

6,720callback境界、停止／例外13,440件、再入13,440件、4丸めmodeを確認。正当な公開emplaceを元3型×先3型の9操作で試し、実MSVCは値なし9／旧値保持0だった。値なし時のbyteなし拒否54状態、既存sticky失敗45件、値なし再入60,480件を確認。private byteは操作しない。GNUの到達結果は別に測定し、MSVCから推定しない。

最初の変更scannerは入れ子variantの重なるchild範囲を交換しようとして`ValueError: Ordered source`で停止した。`shards-001`に当時のscanner、recipe、実command、stdout、stderrと失敗観測を保持する。Native source-beforeに記録された元scannerは変更せず残す。NativeのC++44CTestはこのPython scannerを呼ばない。修正は別の`tests/report_guard_child_variant_wire_reference_nested_tests.py`へ追加し、実使用原本を`shards-002/scanner.py.txt`と照合する。

修正版は全7variantの全21組を、非重複20組と入れ子1組に分類する。非重複ではchildを交換し、親子の範囲が重なる1組では両方向の有限subtree置換2件を検査する。全33,018の異なる有効文法変更を16分割・各180秒で拒否した。同値128件（field125、array3）は分離する。元の失敗を成功に書き換えず、両scannerの役割と実行範囲を区別する。

fresh `build/wfdgch2`の実Release／真Debugで旧43＋新1の各44選択CTest、旧全fixtureと実行出力、20profile、391保護原本の不変を確認。登録数101／99と実行数44を混同しない。17header gate1受理20拒否、Web693テストskip0・構文・buildも成功。

製品2data TU＋harness1＋元Interval試験用1TU、数値model library非結合。GNU52sourceにはMesh／PlaneCalls／Sphere全枝の実再帰24scriptと実nested scannerを固定する。ASTと実module graphの事前照合は、実GNU実行とは別の受入。全11既存jobを保ち、public-onlyの独立20分Child jobを追加する。

PairRecord5項目、準備Resultの依存、GuardResult14項目、最上位World ReportとC API pump、今回取得のWASM・ゲーム接続は後続。保存試験を実Worldの数値モデル認証、CFD、摩擦や塑性損傷の完成と読み替えない。
