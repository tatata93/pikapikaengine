# 自由飛行Resultと符号付き失敗分類の取得条件

2026-11-06。未実装の次段。free_flight_guard::Result全12項目を取得する。
予定の合計は54型344項目。自由飛行header全5型34項目の取得範囲を完成させる。

status, reason, failed_index, world_body, snapshot, tube, flight_failure, candidate_evaluated,
endpoint, inflated, candidate, messageを宣言順に保存する。
8optionalのabsent/present、失敗位置なしと0、candidate_evaluatedと候補の存在を別々に保持する。
snapshot.body.radius、tube.guard_radius、inflated.snapshot.input.radiusを混ぜない。
膨張球のentry/penetrationを元形状の接触に変更せず、候補bodyを再propagateしない。
実status/reason、全message byteと入れ子の全診断を保持し、欠損した情報を再queryで補わない。

`dynamics::CcdFailure`はunsigned基底ではないため、現unsigned専用optional enum helperを流用しない。
新しい明示経路で基底がint32_tであることを静的確認し、整数変換によるmodulo2^32のenum payloadとして保存する案を別に検証する。
型・fieldのschemaで符号付き32bitの復元契約を明示し、従来のunsigned enum出力を変更しない。
負値とINT32_MIN/MAXなどの人工値も保存比較するが、モデルがそれらを有効分類として返すとは言わない。
物理headerのenum宣言を変更して取得契約を回避しない。

比較対象は宣言順の既知13値（noneからnumerical_failureまでの0..12）と、
−1、−2、INT32_MIN、INT32_MAXの人工4値を含める。
正規化・範囲内へのclamp・U32型tagへの置換を拒否し、符号付きenum fieldとしてpayloadの全4byteを比較する。
I64への単なる整数化はenum型の区別を失うため、既存enum tagに32bit表現を保存する案と比較して採否を記録する。

次段設計の一次資料確認: C++公開草案の[列挙宣言](https://eel.is/c++draft/dcl.enum#5)では、
基底未指定のscoped enumは固定基底intであり、[固定基底の値域](https://eel.is/c++draft/dcl.enum#8)はその基底型の値域になる。
[整数変換](https://eel.is/c++draft/conv.integral#3)のmodulo規則を用いる案とし、raw objectのbyte配置へ依存する案を避ける。
公開草案の確認と、実C++20/MSVC/GNUの型・出力の受入は区別する。今回のEndpointAudit取得にはこの経路を追加しない。

最初は8optionalの全なし/全あり/one-hotによる任意2項目28組×4=112組合せを独立比較する。
全256組合せの実行とは区別する。入れ子の既受入fixtureを再使用し、製品getterから期待値を生成しない。
外側全なし/全あり/各one-hotの10recordと、失敗分類だけを変える軽量recordを分け、
同じ大きな保持Resultを全enum値について再び入れ子にしない。
全ありrecordでは元半径・tube半径・inflated内半径を識別可能な別の値にし、すべての保存先を比較する。
負荷が過大にならないよう入れ子値を全初期化した小さな保持Resultから選び、旧33080byteの全held Result回帰を別に保持する。
空/NUL/非UTF8/255・256・257byte境界の本文を含め、全scalar byte/キー/本文/enum tag/optional構造を実改変して拒否する。
新しい符号付きenum経路も、全callback停止/例外/再入と4丸めmode取得の対象にする。

製品2TU、新harness1TU+試験専用旧interval.cppだけ。数値model library/再計算/World変更/動的確保をgetterへ追加しない。
fresh Release/真Debugで旧16fixtureと全run出力、全getter/descriptor、16header gate、旧20profileと数値核/owner/SDK/sampleを保持する。
独立改変検査は仕様treeを一度構築し、全対象を維持した実時間を記録する。GNU通常/真Debug/全TU O1 ASan-UBSanは別受入。
その後World guardのBindingInfo/Failure/BodyRecord、全call/Child/Pair、最上位Report、C API pumpへ進む。
