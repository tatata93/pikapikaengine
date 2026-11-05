# メッシュ全Resultの12項目を取得する

2026-11-06。`sphere_triangle_mesh::Result`の全12項目をNative診断取得へ追加し、合計38型221項目。
メッシュ結果の型対応であり、最上位Report・C API pump・今回の取得機能のJS/WASM/game接続は未完。

| 項目 | wire型と保持内容 |
|---|---|
| status, reason | U32 enum tag、実ordinal |
| failed_index, first_failed_row | absent、またはpresent＋U64 child＋end |
| rows | 元順の全Row。未照会queryと実失敗prefixを保持 |
| nearest | optionalの実有無と全Nearest。rowsから作り直さない |
| queries, candidates_examined, sqrt_refinements, sqrt_limited_rows, failed_rows | 各size_tをU64へ |
| message | 空/NUL/非UTF-8を含む全byte |

Record::optional_countは、存在するsize_tを明示的にU64へ写す。generic scalarのoverloadでwire型を決めない。
位置なしと位置0を区別し、元型が32bitの場合にもU32へ切り替えない設計である。
この段階の実行検証はMSVC19.51 x64であり、32bit runtime検証を行ったという意味ではない。
各Writer呼出しが返したStatusを保持する。一時的なreentrantをWriter::status()==okで上書きしない。

構築済みconst Resultを直接辿る。statusや失敗位置からrows/nearest/計数を合成しない。
照会・再構築・一時vector・数値演算・動的確保をgetterへ追加しない。製品libraryは専用2TUを維持し、
既存interval.cppは試験targetだけで使用する。入力寿命・不変性・排他的Writer操作・全Statusとfinish/completeの確認は前段と同じ。
sink停止や例外では既にbyteが消費され得る。途中documentを完成した結果として公開しない。

fresh `build/wfdmr1`の実Release/真Debugで全20256byteが一致。
人工Result8件、外側3optionalの全8組合せ、位置0/2^53超/size_t最大値、5つの異なる実計数を比較した。
空/複数/原順の異なる/重複するrows、未照会Rowと入れ子の実診断、nearestの空候補と重複IDも保持する。
全602typed leaf、F64 416（負零33）、U64 75、本文15field計2904byteを独立参照で照合。
元triangleのNaNは公開Vec3の人工診断で、Intervalのprivate領域を書き換えたものではない。
この試験で新たな幾何queryは0回。人工のdomain外状態を実モデルが受理したとは呼ばない。

全2864callbackで5728停止/例外と2864再入拒否、実4丸めmode保持を確認。
独立参照は4763単byte改変を拒否。U64は全8byteを個別改変し、本文も全byteを調べた。
root record改変3件、absent→null21件、ID列の構造改変9件、row列の構造改変16件も拒否。
16header＋manifest gateは1受理/19変更欠落拒否。新しいoptional_countを含む全descriptorを実getter順に比較する。
同じfresh構成で旧8fixtureの3112/4587/3706/3937/1037/3241/12924/5414byteと全run出力が一致した。
登録CTest67/65のうち実行は各9件。旧物理suiteの再実行や全登録testの実行とは区別する。
旧20数値profile、数学核、owner、SDK、sampleを保持する。

正式記録は`reports/diagnostic-wire-mesh-result-verification.json`。新mesh ResultのGNUは公開CIで別受入する。
前段Row/Nearest fe9d251bは実GNU13.3の通常/真Debug/全4TU O1 ASan-UBSanで5414byte一致、
全16command・Engine42098059718全6job/Pages42098059647成功を確認した。
次は保持荷重のHeldSphere/Cell/WorldBodySnapshotの3型11項目、その後の全audit/partition/frontierへ進む。
