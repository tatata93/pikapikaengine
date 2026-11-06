# World guardの設定identityとbody記録を取得する次段

2026-11-06。未実装の次段。world_static_mesh_flight_guardのBindingInfo5項目とBodyRecord4項目を取得する。
予定合計56型353項目。既存16header gateに固定した実宣言を使用する。

BindingInfo: mode, state, checked, profile, build_id。
BodyRecord: body_ordinal, is_static, state, seed_pair_ordinal。
body_ordinalとseed_pair_ordinalの実U64を残し、optionalなしと0を分ける。state/flagからseed pairを推測しない。
BindingInfoは保存された設定identityであり、実object/executableの実行時測定hashではない。getterでcurrent_bindingを呼ばない。

build_idは所有std::array<char,65>の全65byteをopaque bytesとして保存する明示経路を追加する。
strlenやNUL終端への依存、64byteだけの切詰め、文字コード修復、hexの正規化を行わない。
正常な64hex＋NULと、人工の全零・途中NUL・末尾非NUL・非UTF8を全初期化済み固定配列で比較する。
charの符号に依存する整数化を避け、std::as_bytesなどのbyte spanから取得する。
表示用文字列の構築とraw65byte保存は別の契約。人工配列を実bindingによる受理と呼ばない。

複数recordでmode/stateの既知値とunsigned未知値、checked/is_static、profile0/最大、bodyのfull64位置、seedなし/0/最大を独立比較する。
全scalar各byte/キー・全65本文byte・enum tag・optional構造を実改変して拒否する。
全callback停止/例外/再入、4丸めmodeと原値の再取得を確認する。
製品2TUと新harness1TUだけ。新harnessにはInterval TUや数値model libraryを結合しない。
旧17fixture/全run出力・旧20profileをfresh Release/真Debugで保持する。旧Interval TUは旧回帰harnessだけ。
全getter/descriptor、16header+manifest gate、数値核/owner/SDK/sampleを維持する。GNU3TU O1 ASan-UBSanは別受入。

次にpreparation::FailureLocationのkind/index/face_indexとguard::Failureのpreparation/body_ordinal/pair_ordinalを対応する。
前者の2indexは元source位置であり、body/pairの実行順やIDへ変換しない。
その後各Callの全依存Result、Child variant、Pair、GuardResult、最上位ReportとC API pumpへ進む。


Native実装の有限検証を行った履歴計画。実結果はREPORT_GUARD_IDENTITY_BODY_WIRE.mdと正式verification JSONを参照。新GNU/全Report/C API pumpは別受入。
