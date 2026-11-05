# 自由飛行の終点監査を取得する

2026-11-06。free_flight_guard::EndpointAuditの全9項目をconst取得へ追加する。
診断取得は合計53型332項目。自由飛行headerの5型34項目中、Settings/Snapshot/Tube/EndpointAuditの4型22項目が対応する。
自由飛行Result、最上位Report、C API pump、今回の取得機能のJS/WASM/game接続は後続。

nominal_position、nominal_allowed、exact_position、exact_allowed、exact_differenceは各3区間を原順で取得する。
l1_error_boundの全2端点と、nominal_contained/exact_contained/l1_within_tubeの3flagを別々に保存する。
getterは区間・候補位置・L1上界を再構築せず、包含flagを比較演算で作り直さない。
保存された診断値を取得する機能であり、新たなpropagationや包含証明の数値認証ではない。

製品は既存2TU、動的確保を追加しないconst取得だけ。数値model libraryを結合しない。
全返却Statusとfinish/complete、転送成功を呼出側が確認し、不完全なdocumentを公開しない。
到達値は全初期化済み・生存中・不変、Writerは排他使用する。

人工fixtureは8監査record。3flagの全8組合せと、5箱×3軸＋L1の全128区間を識別可能な値で構成する。
区間型の有効な構築域に従い、NaNや不正な端点を内部byte書換えで捏造しない。
既存Intervalの下端ゼロは−0、上端ゼロは+0として保存される。無限境界・subnormal・最大有限境界も含める。
IntervalはRN環境で先に構築し、4丸めmodeでgetterだけを実行する。
実interval.cppは試験専用であり、新しい数値モデルを呼び出さない。

独立Python仕様で全型・キー順・原bit・3flagを比較する。
全scalar各byteとキー、rootの原順/個数、全40個の3軸配列の交換/除去/重複を文法decode後に実改変して拒否する。
全callback境界の停止/例外/再入、元値の再取得を確認する。
旧15fixtureと全run出力、16header+manifest gate、旧20profileと数値核/owner/SDK/sampleを保持する。
GNU通常/真Debug/全4TU O1 ASan-UBSanとNative全byte一致は別受入。

次は[自由飛行Resultと符号付き失敗分類](REPORT_FLIGHT_RESULT_WIRE_PLAN.md)。


実受入: Release/真Debugの8023byte/全280typed leaf、2584停止例外/1292再入拒否、4丸めmode保持。独立2400byte+3root+120固定区間配列改変拒否。16header+manifest gate1受理19拒否。登録74/72のうち各16CTestのみ実行、旧15fixture/全run出力/20profile/339保護原本不変、Node693skip0/構文/Webbuild成功。新GNUは別受入。
