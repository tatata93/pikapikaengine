# World guardの設定identityとbody記録を取得する

2026-11-06。BindingInfo全5項目とBodyRecord全4項目をconst取得へ追加。合計56型353項目。
全ReportとC API pumpに必要な依存を順番に対応する段階であり、今回の取得機能のJS/WASM/game接続は後続。

BindingInfoはmode/state/checked/profile/build_idを取得する。保存された設定identityであり、実objectやexecutableを実行時に測定したhashではない。
getterはcurrent_bindingを呼ばず、元の状態を修復・再検証しない。未知のunsigned enumも全32bitのenum tagで残す。

build_idはstd::array<char,65>の全65byteを既存bytes tagで保存する。private fixed_bytes経路からconst char spanのstd::as_bytesを用いる。
標準公開草案の[object representation view](https://eel.is/c++draft/span.objectrep)に従う。charの符号に依存する整数化やstrlen、64byteへの切詰め、文字コード修復を行わない。
manifestのfixedBytesFieldsはsource型、65byte、wire tag、NULも含む保存範囲を固定する。
表示用の文字列変換とは別の契約。人工の非終端配列を実bindingが受理したとは主張しない。

BodyRecordはbody_ordinal/is_static/state/seed_pair_ordinalを取得する。
body位置とseed pair位置は別々のU64で、2^53を超える値も保持する。optionalなしと0を区別し、stateやstatic flagからseedを推測しない。
これは保存済みの元位置であり、body IDや実行順への変換を行わない。

人工fixtureはBindingInfo7件とBodyRecord7件。
正常64hex＋NUL、全零、途中NUL、全FF、末尾非NUL、非UTF8を含む全初期化済み65char配列を比較する。
各enumの既知値とunsigned未知値、profile0/最大、bool、元位置0/2^53超/U64最大、seedなし/0/最大を独立Python仕様と完全typed比較する。
全scalar各byte・キー・全455identity byte、optional/enum tag、固定長64/66への文法上有効な改変を拒否する。
全callbackで停止/例外/再入を試し、4丸めmodeと原値の再取得を確認する。

製品2TUと新harness1TUだけ。新harnessにInterval TUや数値model libraryを結合しない。
旧17fixtureと全run出力、旧20profile、数値核/owner/SDK/sampleを保持する。
GNU13の通常/真Debug/全3TU O1 ASan-UBSanは公開CIで別受入する。登録CTest全件をローカルで実行したとは主張しない。

次は[FailureLocation/Failure](REPORT_GUARD_FAILURE_WIRE_PLAN.md)の2型6項目。その後Callの全Result依存、Child variant、Pair、GuardResult、最上位ReportとC API pumpへ進む。
流体・塑性損傷・専門車両モデル・IK/制御・高精度撮像の完成を、この診断保存の検証からは導かない。


実受入: Release/真Debug1934byte/全61typed leaf、476停止例外/476再入拒否、4丸めmode保持。独立740byte+3root+2absent→null+10present除去/null+21enum→U32+14固定長改変拒否、全455identity byteを個別改変。16header+manifest gate1受理19拒否。登録76/74中実行各18CTest、旧17fixture/全run出力/20profile/343保護原本不変、Node693skip0/構文/Webbuild成功。新GNUは別受入。
