# 安全区間と侵入証拠の保存済みレコードを取得する

2026-11-06。保持荷重のInitialProof/CertifiedLeaf/Witness/EntryWindowの4型18項目を取得する。
診断取得は合計47型265項目。全held Resultと最上位Report、C API pump、この取得機能のJS/WASM/game接続は後続。

| 型 | 保存するmember |
|---|---|
| InitialProof | lower_gap_certificate, upper_gap_certificate, audit_index |
| CertifiedLeaf | cell, lower_gap_certificate, audit_index |
| Witness | cell, time, exact_path_bounds, anchor, error_upper, upper_gap_certificate, audit_index |
| EntryWindow | time_bounds, time_width, path_bounds, l1_diameter_bound, witness_audit_index |

初期点の両証明、証明済み区画、侵入の証拠とその時刻、入口の窓をそれぞれ取得する。
Intervalの実lower()/upper()、秒の両端、3軸全要素、anchorとerror_upper、全64bit監査indexを保持する。
getterでp(t)や幅を再計算せず、軸を並べ替えたり欠けた証拠を補ったりしない。
EntryWindowのtime_widthは秒、経路箱とl1_diameter_boundはメートル。
l1_diameter_boundの下端を、実際の変位や侵入の下限として扱わない。

取得は既存Record::field/array/countとInterval取得だけでconst値を辿る。製品libraryは2TUのまま。
試験だけで実Intervalを構築するため、harness1TUに旧interval.cppを明示的に結合する。
モデル照会や数値model libraryのlinkは行わない。
全到達値の初期化・不変性・寿命とWriter排他使用は呼出側の契約。
全返却Statusとfinish/completeを確認し、不完全なdocumentを成功として公開しない。

各型2件、8件の人工診断を独立参照で比較する。
Intervalの構築可能な端点と、公開doubleのraw bit取得域を区別する。
人工の証拠recordを保存できることから、物理モデルがその証拠を認証したとは主張しない。
Intervalは丸めmode変更前に構築し、4modeで取得する間は端点を作り直さない。

正式な有限検証記録は`reports/diagnostic-wire-held-proofs-verification.json`。
旧11fixtureと全実行出力、16header+manifest gate、旧20profile、数値核/owner/SDK/sampleを保持する。
GNU通常/真Debug/試験用旧Intervalを含む全TU O1 ASan-UBSanは公開CIで別に受け入れる。
次はoptional配列とoptional enumを明示し、CellAudit/PartitionLeafと全Resultへ進む。


実受入: Release/真Debugの2487byteが一致。82typed leaf（F64 70/負零5、U64 8、U32 4）、756停止・例外/1512再入拒否、4丸めmode保持を確認。独立738byte+3root構造+30固定配列構造改変を拒否。16header+manifest gate1受理19拒否。登録70/68のうち各12CTestのみ実行、Node693skip0/構文/Webbuild成功。新GNUは別受入。
