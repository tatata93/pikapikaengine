# 元sourceの失敗位置とguard内の失敗位置を保存する後続段

2026-11-06。未実装の後続段。設定identity/BodyRecordの次に2型6項目を対応する。
その段を先に終えた場合の予定合計は58型359項目。既存16header gate内の実宣言を用いる。

world_static_mesh_flight::FailureLocation: kind, index, face_index。
world_static_mesh_flight_guard::Failure: preparation, body_ordinal, pair_ordinal。

ObjectKindはunsigned基底のsettings/world/body/plane/mesh/face。既存enum経路へ保存し、取得時にkindを推測しない。
FailureLocationのindexは元source ordinalで、faceの場合はmesh ordinal＋face_index。
重複位置が第二出現を指す意味を保持し、IDやソート後の順序へ変換しない。
guardのbody_ordinal/pair_ordinalとは別々に取得する。preparation不在と、存在するが内部indexなしの値を分ける。
元Worldやprepare inventoryを再queryして欠けた情報を補わない。

全初期化済み人工値でLocationの2optional全4組合せとguard Failureの3optional全8組合せを独立比較する。
ObjectKind全6既知値とunsigned未知値、位置なし/0/53bit超/U64最大を含める。
矛盾した人工有無を実preflightが受理したとは主張しない。
全scalar各byte/キー/enum tag、optional除去/null、rootの原順・個数を実改変して拒否する。
全callback停止/例外/再入、4丸めmode取得と原値再取得を確認する。

製品2TUと新harness1TUだけで数値model library/Interval TUを新harnessへ結合しない。
旧18fixture/全run出力、旧20profile、全getter/descriptor、16header gateと数値核/owner/SDK/sampleをfresh Release/真Debugで維持する。
GNU3TU O1 ASan-UBSanは別受入。全Call依存Result、Child variant、Pair/GuardResult、最上位ReportとC API pumpは後続。
