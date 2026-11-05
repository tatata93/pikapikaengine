# メッシュ全Resultの取得条件

2026-11-06。実装前の次段。Row/NearestのNative取得fe9d251bに続き、`sphere_triangle_mesh::Result`の全12項目を対応する。
全Report/C API pumpの実装ではない。追加する数値核・照会・外部libraryはない。

| 項目 | 取得契約 |
|---|---|
| status, reason | 実ordinalをU32 enum tagへ |
| failed_index, first_failed_row | optionalの実有無、存在するsize_tをU64へ |
| rows | 元順の全Row。未照会query/実失敗prefixも保持 |
| nearest | optionalの実有無と全Nearest。rowsから合成しない |
| queries, candidates_examined, sqrt_refinements, sqrt_limited_rows, failed_rows | 各size_tを独立したU64へ |
| message | 空/NUL/非UTF-8を含む全byte |

2つの位置とnearestの3optionalは、全8有無の組合せを人工診断で比較する。
位置なしと位置0、2^53超とsize_t最大値を区別する。5計数も0/最大値/異なる値を使い、失敗statusから補完しない。
rowsの空/複数/異なる原順/重複、未照会Row、geometry不在の失敗Result、全診断のあるResultを含める。
nearest不在を「候補なし」や初期値で埋めない。人工的なdomain外の位置・状態を実モデルの受理とは呼ばない。
message長0/1/3/255/256/257/16/513と任意byteを比較する。入力は公開値を構築し、Interval不変条件を破らない。

Recordにはsize_t optionalを明示的にU64へ写す専用経路を用意する。
現在のscalar overloadへ暗黙に渡すだけでは32bit size_tがU32になるため、その方法でwire型を決めない。
absentはleaf、presentは実U64 child1個とend。各Writer呼出しの返却Statusを保持し、
一時reentrantをWriter::status()==okで上書きしない。getter内で照会・vector構築・数値演算をしない。

独立参照は全field/typed値/byte/原順、位置なし→null、存在するU64のbit改変、row/ID列の入替・削除・重複を検査する。
全callbackの停止/例外/同Writer再入、構築済み値の4丸めmode保持、source再取得の全byte一致を確認する。
新しいfresh Release/真Debug構成で旧8fixtureの3112/4587/3706/3937/1037/3241/12924/5414byteと全run出力を保持する。
schemaは38型221項目になる見込みだが、実getterとdescriptorを全項目照合してから確定する。
16header＋manifest gateの1受理/19変更欠落拒否、旧20数値profileと製品2TU/試験専用interval.cppの分離を保つ。
GNU通常/真Debug/全4TU O1 ASan-UBSanとNative全byte一致は別受入。旧数学核/owner/SDK/sampleを保持する。
全audit/partition/frontierと最上位Report、その後の所有cache/C API pumpへ順に進む。


追記: この12項目のNative有限実装を受入。現状は[実装ガイド](REPORT_MESH_RESULT_WIRE.md)。新GNUと最上位Reportは別受入。
