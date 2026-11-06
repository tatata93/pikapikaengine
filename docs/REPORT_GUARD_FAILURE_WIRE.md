# 元sourceの失敗位置とguardの失敗位置を取得する

2026-11-06。world_static_mesh_flight::FailureLocation全3項目とguard::Failure全3項目をconst取得へ追加する。
診断取得は合計58型359項目。既存のoptional_countとoptional経路を用い、primitive tagや版番号を変更しない。

FailureLocationのkind/index/face_indexは元sourceの位置を表す。faceの場合はmesh位置とその内部face位置を別々に保持する。
重複を指す診断では第二出現の元位置を変えず、IDやソート後の順序へ変換しない。
kindはunsigned基底のenum tagで保存し、settings/world/body/plane/mesh/faceと未知の全32bit値を区別する。
getterはkindから位置の有無を推測せず、矛盾した人工データも修復しない。

guard::Failureのpreparation/body_ordinal/pair_ordinalはそれぞれ独立したoptional。
preparationなしと、preparationはあるが内部indexがない値を区別する。
guardのbody/pair位置とpreparationの元source/face位置を混ぜず、それぞれU64で保存する。
位置なしと0、2^53を超える値、U64最大を保持し、元Worldやinventoryを再queryしない。

fixtureは元Location8件とguard Failure8件の計16root record。
Locationの2optional全4maskを各2回、guardの3optional全8maskを比較する。guard内には4件のLocationを入れ子に保存する。
ObjectKindは既知6値と人工の0x80000000/UINT32_MAX。全64bit位置は0/2^53+1/U64最大などを独立に振り分ける。
人工の有無・値の保存を、実preflightがその状態を受理したという主張には用いない。

独立Python仕様で全型・キー・原順・個数・全位置・欠損を比較する。
全scalar各byteとキー、enum→U32、absent→null、present除去/null、rootの交換/除去/重複を実改変して拒否する。
全callback停止/例外/再入、4丸めmodeと元値の再取得を検査する。
製品2TUと新harness1TUのみで、新harnessにInterval TUや数値model libraryを結合しない。
旧18fixture/全run出力/旧20profile、数値核/owner/SDK/sampleを保持する。

全Report/C API pump/今回取得機能のJS/WASM/game接続、物理モデルの追加認証は後続。
GNU通常/真Debug/全3TU O1 ASan-UBSanは公開CIで別受入する。
次は[coverageの元係数](REPORT_COVERAGE_SOURCE_WIRE_PLAN.md)のSphere/StaticPlane2型6項目。


実受入: Release/真Debug1415byte/全32typed leaf、536停止例外/536再入拒否、4丸めmode保持。独立268byte+3root+24absent→null+48present除去/null+12enum→U32改変拒否、16header+manifest gate1受理19拒否。登録77/75中実行各19CTest、旧18fixture/全run出力/20profile/345保護原本不変、Node693skip0/構文/Webbuild成功。新GNUは別受入。
