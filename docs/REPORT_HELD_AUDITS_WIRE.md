# 保持荷重の監査行と区画レコードを取得する

2026-11-06。CellAuditの18項目とPartitionLeafの4項目を取得する。診断取得は合計49型287項目。
全held Resultと最上位Report、C API pump、この取得機能のJS/WASM/game接続は後続。

CellAuditはkind/cell/time/outcome、経路と点の全3軸区間、anchor、mesh_queriedと実status/reason、
距離・変位平方量・誤差平方量・各平方根・下側と上側の証明、Workを保存する。
Workはこの行の差分を取得し、他行の値やResultの集計へ置換しない。
PartitionLeafはcell/state/audit_index/blocked_reasonを保持する。
所属indexなしと0、未照会と未解決の理由を分けて残す。

新しいRecord::optional_arrayはabsentか、presentの中に全配列を1個だけ置く。
arrayの終了とpresentの終了を両方出力し、3軸の順序と全区間端点を保持する。
Record::optional_enumerationはabsentか、present内の実enum ordinalを保存する。
U32 scalarへ変換せず、4byte unsigned基底の実enum型であることを静的確認する。
どちらもcallbackが返した実Statusを保持し、停止や再入拒否を後続操作の成功で上書きしない。
値なしをnullや空配列で補わず、入力の補正、数値照会、動的確保をgetter内で行わない。

製品libraryは既存2TUのまま。試験はharness1TUと、Interval構築だけのために旧interval.cppを結合する。
構築済みで全到達値が初期化されたconst診断を対象にする。
入力寿命・不変性とWriter排他使用を守り、全Statusとfinish/completeを確認する。
途中で停止した出力を完了documentとして公開しない。

人工CellAuditは14件で、12optionalの全なし/全あり/各1項目だけありを比較する。
66組の任意2項目について4有無組合せ、計264のpair組合せを含む。全4096組合せの実行とは区別する。
PartitionLeafは4件で所属indexなし/0/53bit超/U64最大を区別する。
unknown enum ordinal、元doubleの非有限値やNaN payload、実Intervalの許された構築域を分けて試験する。
人工の項目組合せを実モデルが返した有効な診断や実消費量とは紹介しない。

独立参照は全値・全有無・全軸とenum tagを比較する。
全scalar byteとkey、record順/個数、optional配列の軸順/個数、値なしとnull、presentの除去、enumとU32の区別を実改変で拒否する。
Native Release/真Debug、全callback停止/例外/再入と4丸めmode取得を確認し、旧12fixtureと全run出力を保持する。
正式記録は`reports/diagnostic-wire-held-audits-verification.json`。
GNU通常/真Debug/全TU O1 ASan-UBSanは公開CIで別受入。旧数値核/owner/SDK/sampleを保持する。
次は残るheld Resultの25項目で、全証明島・全区画とtail・全frontier・全auditsを取得する。


実受入: Release/真Debugの14275byteが一致。337typed leaf、present27/absent145、3544停止・例外/3544再入拒否、4丸めmode保持。独立2784byte+3root+145absent→null+54present除去/null+4enum→U32+12optional配列改変拒否。16header+manifest gate1受理19拒否。登録71/69のうち各13CTestのみ実行、Node693skip0/構文/Webbuild成功。新GNUは別受入。
