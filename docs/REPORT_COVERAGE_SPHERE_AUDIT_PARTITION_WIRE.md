# sphere boxの監査と区画を保存する

2026-11-06。`accelerated_sphere_box_coverage::Audit`全6項目と`PartitionLeaf`全4項目のconst取得をNative有限受入。取得範囲は83record型476項目＋別variant1型、coverage内28record130項目／残り全Result1record12項目。Native実結果は`reports/diagnostic-wire-coverage-sphere-audit-partition-verification.json`を参照。GNU・公開は別受入。

| 元の項目 | 保存する内容 |
| --- | --- |
| Audit.cell、call_attempted | 元の秒区間・深さ・親位置と、元の試行flag |
| evaluation | 返却されたEvaluation全9項目、または欠損 |
| outcome、blocked_reason | UInt32の元のenum ordinal |
| split_time | 元のbinary64 bit、または欠損 |
| PartitionLeaf.cell、state | 元のCellと区画状態のenum ordinal |
| audit_index、blocked_reason | 元の64bit監査位置または欠損、元の理由 |

監査位置を振り直さず、未返却Evaluationを再queryで埋めず、flagと理由を再判定しない。Evaluationの全3軸、平方根の戻り値と元のdistanceコピーも別々に保持する。public Interval constructorを使用し、NaNや反転Intervalを偽造しない。Cellのraw秒とsplit_timeのNaN payloadは元のbitを保存する。人工不整合値の保存は、数値モデルがその値を生成・認証した証拠ではない。

新対象のみのfresh `build/wfdcsap1` Release／真Debugは、人工Audit20／PartitionLeaf12、全16,467byte SHA256 `090b83943f754f37331646e230d80a56b4e35d3acffbf57765c9fddaa10eb4c1`と530typed leafが独立仕様に一致した。F64 374／負零29、U64 20、U32 42、bool30、enum64、存在40／欠損44、全16presence／試行maskを含む。2,618callback、停止・例外5,236件、再入5,236件と4丸めmodeを確認した。

全scalar／key byte9,050変更、root順序・個数3件、optional混同124件、enum型混同64件、端点157件、root field359件、Cell field96件、owner2件、軸90件、Evaluation field360件、平方根field30件、固定配列個数124件、object順序1,008件の計11,467件を拒否。同じbyte列になる39交換（端点25／root13／owner1）は拒否へ混ぜない。原記録は`reports/diagnostic-wire-recipes/run-20261106-coverage-sphere-audit-partition-controls-001/`。

新harnessは製品2data TU＋harness1＋元Interval試験用1TUで、数値model libraryを結合しない。全回帰は別fresh `build/wfdcsap2`。GNU通常・真Debug・全4TU O1 ASan／UBSan、最上位World Report、C API pump、今回取得のWASM／ゲーム接続は別受入。[次は全Result12項目](REPORT_COVERAGE_SPHERE_RESULT_WIRE_PLAN.md)。
