# 定義線分のentry window: 次のNative受入案

2026-11-04 JST。**設計のみ・未実装**。手動guardラボの公開受入後に行う最小数値核。既存の定義線分guardは全経路のstrict離隔か点witness/未認証を返すが、最初の未認証cellで停止するため、そのまま最初の接触範囲やTOIとは呼べない。Worldや応答へ先に接続せず、有界なNative-only proof objectを追加する。

## 証明する対象

入力binary64が定義する厳密な実線分 `p(s)=start+s(end−start)`、s∈[0,1]、半径r>0、最大64枚の静的両面三角形を使う。`g(s)=min_i distance(p(s),T_i)−r`。m/sや真の運動方程式を入力したモデルではない。薄い面の有限集合への距離で、閉固体内部・厚み・接触応答を推定しない。

`entry_window` の受入には次を全て要求する。

1. 初期点でg(0)>0をstrictに証明する。
2. closedな[0,L]全体でg>0を証明し、その連続被覆と原本/全auditを保持する。
3. 厳密なpath点p(U)について、丸めanchorからのE補正を含めg(U)<0のstrict witnessを持つ。
4. 0≤L<U≤1、入力から外向きに囲んだU−Lの上端≤指定parameterToleranceを確認する。

距離の連続性とこれらの証拠から、少なくとも接触/侵入への遷移が存在し、最初のstrict負集合の開始 `inf{s:g(s)<0}` は(L,U)内にある。単一の根、接線の不存在、特定面の衝突、正確な時刻・法線・反力を証明するものではない。窓の中での接線や複数回の接近を除去したと主張しない。未知cellが狭いだけ、端点だけ、負witnessだけでは受理しない。

全[0,1]のstrict正被覆ができた場合だけ `separated`。初期点のstrict負を証明できれば `initial_penetration` としentry bracketは付けない。初期boundary/符号未確定・接線のみ・予算不足・面の幾何失敗は `not_certified` 等へ保持し、missへ変えない。現primitiveは中心が面上など距離0で法線が未確定となり得るため、初期内部を常に分類できるとは約束しない。距離専用primitiveはその制約を外す別段である。

## 有限探索と所有

旧guardの「最初の未知cellで停止」を変更せず、新核で左優先の有界frontierを設計する。先行未知cellの後ろも負witness発見のために照会し、prefixは連続して証明できた分だけ更新する。後ろの成功で先行未知域を埋めない。探索順やcell再訪規則、maxEvaluations/partitionLeaves/frontierのhard boundとwork前予約を実装前に数値で固定する。幅優先のfrontierへ旧DFSの最大33件という容量を流用しない。新設定を無断で拡大しない。

cellのp(J)、exact p(m) box、任意anchor、R/E・証明式は常に元のstart/endとglobal parameterから構成する。丸めた子endpointを新pathとして再照会すると原定義が変わるため禁止する。初期点照会も評価予算へ算入し、各mesh/primitiveとR/E sqrtの予約・返却既知work・例外時保守上限を区別する。実行されなかった照会をwork0の成功へ変えない。

戻り値は原入力/settings、status/reason、初期点証拠、certified prefix/leaves、未処理frontier/current、最良の負witnessと所属、窓の幅包含、全audit/work、最後に返却されたmesh全行/候補を所有する。prefix/初期点/witness/lastMeshを異なる照会へ付け替えず、失敗時にも診断を省略しない。

窓の終端でnearestだった面のIDをentry面へ転用しない。最小段では元の全source IDを保守的候補として保持し、面の同定や単一法線を出さない。後で候補を絞る場合は窓全域でその面が離れている証明を別に要求する。

## Native-onlyの有限受入

- 新C++ module/test/fixture/proof checkerを追加し、既存guard/SDKの原本やWASM artifactを変更しない。private helper共通化で旧SDK source hashを変える場合は、この最小段とは分けて再build/全既存bits受入を行う。
- 解析的な面通過（例parameter1/4）、両端外側の高速通過、順逆、複数回侵入と面競合、接線のみ・初期負/境界/距離0失敗、退化面/後続行、64面、全予算停止、−0/巨大offset/Eが偽witnessを防ぐ場合を固定corpusにする。実採用数は実行後に確定する。
- 独立Fraction参照で全prefixの包含/被覆、exact path witnessのstrict負、窓幅包含、work整合と未知域を監査する。原本・prefix・witness所属・E・窓幅・先行未知域・面IDを改ざんする負例、label/order独立と最適化拒否も加える。
- 旧36CTest/586NodeとSDK全bits/Fraction、厳密FP・GNU警告/ASan/UBSanを別に確認する。新C ABI/JS/UI/World/TOI/接触応答はこのNative段の成功から自動的に完成扱いにしない。

外部solverやpackageは導入せず、既存原著Interval/mesh queryの数学契約を継承する。本案は既存sourceと証明条件を検討した設計で、新しい外部文献を実読したという記録ではない。流体・損傷・専門車両/航空/鉄道・IK/制御・高精度撮像の要求は維持する。
