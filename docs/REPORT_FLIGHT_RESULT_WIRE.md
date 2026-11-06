# 自由飛行の全Resultと符号付き失敗分類を取得する

2026-11-06。free_flight_guard::Result全12項目をconst取得へ追加する。診断取得は合計54型344項目。
自由飛行headerの全5型34項目の保存範囲を対応する。
最上位Report、C API pump、今回取得機能のJS/WASM/game接続は後続。

status/reason、失敗位置、world_body/snapshot/tube、flight_failure、candidate_evaluated、endpoint/inflated/candidate、messageを原値で保持する。
8optionalのなし/あり、失敗位置なしと0、候補の評価試行flagと実候補の存在を区別する。
元snapshot半径・tube半径・inflated内半径を混ぜず、候補bodyを再propagateしない。
不在の診断を再queryで埋めず、失敗や未知の分類を成功へ修復しない。

flight_failureの実CcdFailureは固定基底intのscoped enum。実targetの基底がint32_tであることを静的確認する。
新しいprivate optional_signed_enumeration経路は基底整数からU32へ定義されたmodulo変換を行い、既存enum tagにlittle-endian4byteで保存する。
raw objectのbyte配置へ依存しない。復元はpayloadが2^31未満ならその値、それ以外はpayload−2^32。
これをmanifestのsignedEnumFieldsとfield formに明示する。未知値をclampせず、従来のunsigned enum経路を変更しない。
I64への単なる整数化はenum型tagの区別を失うため採用しない。primitive wireのtag/versionを増やす方式も不要と判断した。
公開草案の根拠は[列挙宣言](https://eel.is/c++draft/dcl.enum#5)と[整数変換](https://eel.is/c++draft/conv.integral#3)。実C++20 compilerの受入は別の有限検証で行う。

fixtureは27人工Result。最初の10件で8optionalの全なし/全あり/one-hotを作り、任意2項目の28組×4=112有無組合せを確認する。
全256組合せの実行とは区別する。さらに既知13分類と−1/−2/INT32_MIN/MAXの17値を軽量recordで比較する。
負値などの人工値の保存を、モデルが有効分類として返すという主張には用いない。
全ありrecordの半径は元1・tube3・inflated2として保存先を識別する。
既受入の原著C++構築コードを新harnessへ組み込み、Pythonは独立した旧入力・終点監査・保持snapshot仕様を参照する。
全held Resultの33080byteは別の旧回帰で保持し、今回のenum全値に大きな入れ子を繰り返さない。

全scalar各byte・キー・本文、optionalの除去/null、enum→U32 tag置換、非空配列の交換/除去/重複を実改変して拒否する。
独立仕様treeを一度だけ作り、各改変を文法decodeと完全typed比較に通す。
全callback停止/例外/再入、4丸めmode、原値の再取得を確認する。区間構築はRN環境で事前に行う。
製品は既存2TU、試験は1harness+試験専用旧interval.cpp。getterに動的確保/数値model library/数値照会を追加しない。
全到達値の初期化・寿命・不変性とWriter排他使用、全返却Status/finish/complete/転送成功の確認が呼出側の契約。
旧16fixture/全run出力、16header+manifest gate、旧20profileと数値核/owner/SDK/sampleを保持する。
GNU通常/真Debug/全4TU O1 ASan-UBSanとNative全byte一致は別受入。

次はWorld guardのBindingInfo/BodyRecordと固定65byteの設定identityを取得する。


実受入: Release/真Debugの22016byte/全589typed leaf、6312停止例外/3156再入拒否、4丸めmode保持。独立5999byte+3root+205absent→null+74present除去/null+77enum→U32（signed19内数）+84全配列改変拒否。16header+manifest gate1受理19拒否。登録75/73のうち各17CTestのみ、旧16fixture/全run出力/20profile/341保護原本不変、Node693skip0/構文/Webbuild成功。初回は全値一致後に検証器の総数誤記で停止し原記録を保存、件数だけ修正したfresh002で受入。新GNUは別受入。
