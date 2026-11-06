# 元の接触ペア位置と実行位置を保存する

2026-11-07。`world_static_mesh_flight_guard::PairRecord`全5項目のconst取得をNative有限受入。合計90record型527項目＋別Input／Child variant2型。正式記録は`reports/diagnostic-wire-guard-pair-record-verification.json`。GNUと公開は別受入。

| 宣言順 | 元の値 | 保存契約 |
| --- | --- | --- |
| 1 | pair_ordinal | 元の所有inventory内のペア位置。U64 count |
| 2 | state | 元のPairStateのenum tagとordinal |
| 3 | reason | 元の独立Reasonのenum tagとordinal |
| 4 | execution_ordinal | 最初の実child呼出位置。欠損とpresentの0を区別 |
| 5 | child | 実Child variantと全下位値、Resultまたは欠損 |

pair_ordinal、execution_ordinal、Call.attempt_ordinalは別の意味を持つ。保存順から実行順を推測せず、値を振り直さず、型やstateからresultを再構成しない。取得は既存Writerとconst getterだけを使用し、query・数値モデル・順序修復を加えない。

人工6PairRecordは元位置9、0、U64最大値、7、2、41を保持し、全4PairStateと独立Reason、欠損／0／U64最大値を含むexecution_ordinal、全3Child型を含む。各Call内の試行位置はそのまま保持する。人工診断は意味的一貫性を修正しない保存試験であり、実Worldの実行結果と読み替えない。

初early001は独立仕様のキー名をstrで構成したため、実プロトコルのbyte keyと一致せずRelease-referenceで停止した。当時の比較scriptとcpp原本、実command／fixture／stderrを001へ保持。比較のキー表現だけを修正し、別fresh `build/wfdgpr2` early002のRelease／真Debugで受入した。Cpp getterや数値核をこの修正で変更していない。

全47,762byte SHA256 `c898611ab3b999186dba2058f51e8d4b32f5b5f2e67ab3759f45fe828a51fda7`、1,464typed leaf（F64 734／負零60、U64 343、U32 136、bool83、enum163、bytes5）、存在110／欠損123、全7variantが独立一致。6,824callback境界、停止／例外13,648件、再入13,648件、4丸めmodeも確認。

正当な公開emplaceの元3型×先3型の9操作で、実MSVC値なし9／旧値保持0を観測。値なし時の54状態、親recordと先行4項目・child keyの正確な送信済みprefix36件、既存sticky失敗45件、値なし再入61,416件を確認。prefixを独立したv1 byte仕様で構成して比較し、値なしChildのvariant tokenは出ないことも確かめた。private byteを操作せず、GNUの到達結果は別に測定する。

全変更検査は入れ子対応scannerを使い、全7variantの21組を非重複20組交換と親子1組の両方向subtree置換2件に分類する。全33,503の異なる有効文法変更を16分割・各180秒で拒否した。同値129件（field126、array3）は別に数える。

fresh `build/wfdgpr3`で旧44＋新1の各45選択CTest、旧全fixtureと実行出力、20profile、394保護原本の不変を確認した。登録102／100と実際の各45件の実行数は、保存したStart／Passed／100%出力とcommand指紋から別に確認する。Web693テストskip0・構文・buildと17header gate1受理20拒否は成功。

製品2data TU＋harness1＋元Interval試験用1TU、数値model library非結合。全枝の実再帰25script閉包とGNU53sourceのAST宣言を事前照合済み。実GNU／最上位World Report／C API pump／今回取得のWASM・ゲーム接続は後続。次は準備Resultの未対応依存とGuardResult14項目。
