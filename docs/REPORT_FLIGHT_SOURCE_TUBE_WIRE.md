# 自由飛行の元入力と誤差tubeを取得する

2026-11-06。free_flight_guard::Snapshot/Tubeの2型11項目を追加する。
診断取得は合計52型323項目。自由飛行headerの5型34項目のうちSettingsと合わせ3型13項目が対応する。
最上位Report、C API pump、今回の取得機能のJS/WASM/game接続は後続。

Snapshotは全RigidBody、元gravity、秒のhorizon、全triangles、全settingsを取得する。
force/torque、回転、材料、static flagを含み、三角形の原順・頂点順・重複と64bit IDを保持する。
Tubeの保存済みnominal_accelerationと、exact_acceleration/acceleration_differenceの各3区間を別に取得する。
position_error/roundoff/guard_radiusのraw F64値を保持し、元bodyのradiusを置き換えない。
getterでF/m+g、区間の差、中点、上界、証明を再計算しない。

製品は既存2TUのconst取得だけ。数値model libraryを結合せず、取得時の動的確保を追加しない。
全返却Status、finish/complete、転送完了の確認が呼出側の契約であり、不完全なdocumentを成功として公開しない。
到達値は全初期化済み・生存中・不変、Writerは排他使用する。

試験は3人工Snapshotと2人工Tube。入力の空/複数/逆順/重複列と、識別可能な全12区間を使用する。
公開doubleのraw域と実Intervalの構築可能域を区別する。区間はRN環境で先に構築し、4丸めmodeでgetterだけを実行する。
実interval.cppは試験専用で、モデルのquery/World更新は行わない。
人工のNaNや不正な物理入力の保存を、物理モデルの受理・誤差上界の正しさと呼ばない。

独立Python仕様で全型・キー順・原bitを比較し、全scalar各byteとキーを実改変する。
root、全非空triangle列、全3軸区間配列の交換/除去/重複を文法decode後の完全比較で拒否する。
期待treeは一度構築して再使用し、全改変対象を維持する。
全callback境界の停止/例外/再入、原値の再取得を確認する。
旧14fixtureと全run出力、16header+manifest gate、旧20profile、数値核/owner/SDK/sampleを保持する。
GNU通常/真Debug/全4TU O1 ASan-UBSanとNative全byte一致は別受入。

次はEndpointAuditの9項目。その後、符号付き基底CcdFailureの表現を別に固定して自由飛行Resultへ進む。


実受入: Release/真Debugの6629byte/234typed leaf、2032停止例外/2032再入拒否、4丸めmode保持。独立2082byte+3root+6triangle列+12固定区間配列改変拒否。16header+manifest gate1受理19拒否。登録73/71のうち各15CTestのみ実行、旧14fixture/全run出力/20profile/337保護原本不変、Node693skip0/構文/Webbuild成功。初回は期待値のInterval下端ゼロ符号の誤りを検出し原記録保存、期待値だけ修正したfresh002で受入。新GNUは別受入。
