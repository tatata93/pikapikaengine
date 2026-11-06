# plane boxのEvaluationを保存する

2026-11-06。`accelerated_plane_box_coverage::Evaluation`全4項目を宣言順に取得する。実装上の取得範囲は71record型412項目＋別Input variant1型。Native・GNU・公開の受入は、それぞれの実記録で確認する。coverage依存内は16record型66項目が対応し、残る13record型76項目を依存順に進める。

| member | 保存する内容 |
| --- | --- |
| tube_coordinates | x／y／zの全3Intervalを原順で保存 |
| distance | 保存済み距離Intervalの両端 |
| threshold | 保存済み閾値Intervalの両端 |
| gap | 保存済み差Intervalの両端 |

取得時にtube、距離、r+marginや差を計算しない。distance・threshold・gapはそれぞれ独立した保存値として取り出す。負のgapを0へ修復せず、3軸の順序・全要素を保持する。この取得試験は実軌道の包含やBの妥当性、実モデルの認証を意味しない。

人工Evaluation8件は、正当なpublic constructorで作ったIntervalを6個ずつ含む。whole、point(0)、point(1)、有限の正負区間、subnormal端点、片側の無限境界、最大有限点、最小正規化数等の12種類を循環させる。既存Intervalの構築契約に従う下端零-0／上端+0を独立仕様へ固定し、元入力のraw負零保存とは区別する。NaN端点や逆転区間、private byte破壊による不正objectを使わない。

全2,927byte、48Intervalの96F64端点と下端負零8個、全8件の3軸配列を独立照合する。全scalar／key byte1,536変更（うちendpoint payload768byte）、root順序・個数3、field値交換88、object内のfield順序56、3軸配列の順序・個数40の計1,723変更を検査する。同値の端点交換8件は拒否数から分離する。

Sourceは全到達先を含めて生存・不変とし、Writerは排他的に使う。返却値・Writer状態・finish・complete・transportのすべてを確認する。停止／例外の送信済みprefixを取り消さず、再入拒否と4丸めmodeでの原byte保持を調べる。

製品2data TUに演算やmodel libraryを加えない。新harness1TUに、正当な人工Intervalの構築のための既存interval.cppを試験専用1TUとして追加する。GNUでは全4TUをO1 ASan／UBSanで計装し、通常・真Debugと同じ全byteを比較する。正式な有限受入記録は`reports/diagnostic-wire-coverage-plane-evaluation-verification.json`。

planeの全Result、最上位World Report、C API pump、今回の取得のWASM／ゲーム接続は後続。[次はCellとWork](REPORT_COVERAGE_PLANE_CELL_WORK_WIRE_PLAN.md)。
