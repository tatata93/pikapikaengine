# 球×静的三角形集合: 定義線分経路のNative非接触guard

2026-11-04 JST。コード93ec576のローカル・公開受入PASS。Native純粋入口は `sphere_triangle_mesh_trajectory::audit(start,end,radius,triangles,settings)`。既存のC++/共有SDK/ゲーム原本を変更せず、新規header/cpp/testと独立Python checkerを追加した。

## 追加したモデル

binary64入力が表す厳密な実数について p(s)=start+s(end−start),0<=s<=1 を定義する。時刻・速度・荷重を入力せず、真の物理運動の包含やTOIを求めるものではない。全経路のdistance>radiusだけを非接触成功とする。

任意binary64 anchor cへの既存mesh queryが全行成功した場合、距離区間[L,U]と、cell全体の|p(s)−c|上界R・厳密中点p(m)とのずれ上界Eを使う。外向きIntervalで L−R−radius の下端>0ならcellを証明、U+E−radiusの上端<0なら厳密p(m)の点貫通witness、それ以外は分割/未認証。丸めanchorをexact pathへ昇格せず、証明の式boundsと実gapのboundsを区別する。

closed dyadic leafが[0,1]を境界一致して全被覆するときだけ全体成功。連続した左prefixと未照会frontier/currentを保持し、予算切れで残区間を捨てない。1行のmesh失敗も隠さない。全snapshot/settings/lastMesh rows/candidatesは所有copyで、各cellのcompact work/証明を保存する。

maxLeaves128/maxDepth32/maxEvaluations1024（leaf上限により実最大255meshcall）、source64。sqrt blockの最悪量を事前予約し、正常返却actualcountを記録。未返却workの可能性がある場合はwork.exact=falseと保守上限で停止する。予約数を実測値へ置き換えない。

## 実行済み検証

- Native69群・62入力=25全区間非接触/4点貫通witness/20未認証/13入力拒否。実128leaf/255meshcall、最後のleaf/audit、maxLeaves127で正prefix保持、64source、face/edge/vertex遷移、巨大offset/失われる低位項、source/settings/−0所有、全品質/予算/環境拒否と復帰。
- 初回full35CTestが成功。kernel/headerを変えずtest-only拡張後、専用1CTestを再build・verbose実行し69群成功。旧34を意味なく繰り返したとはせず、それぞれのcmd/stdout/stderrを保持した。
- 各Native auditのanchorへ旧meshを再queryし、R/Eを直接sqrt再callしてper-cell delta/global actualcountを比較。独立Pythonはsum/bounds/予約と数学包含を監査し、実命令回数の独立測定とはしない。
- Fraction参照はfeasible plane projection+3clamped edgesからsの正確な一次範囲を切り、有理二次式の端点/停留点から全区間最小を求める。48全path/4witness、297certified leaves/606audits、path box5454・二乗box3590・certificate1793・lastMesh2517成分を確認。時間標本の増量で代替しない。
- 解析self14群、71改ざん/strict-loader負例、label/order独立とPython−O拒否が成功。固定input fingerprint7188d0549482a6603328649ee5a82293806b18993d9703ba484ebbca8d93556b。
- 最終Native fixtureは1,145,339B/SHA256 70b28b358f8145b980c35c46f38612dbed9e40ca5352e7076c424049a4805a90。これはWindowsの保存byteであり、未確認の別platform byte同一性を主張しない。
- Node544/skip0・構文/Web457dd1cda43de02c/47modules23entry、旧SDK27160packet/20808modelbits・4453負零・独立2775/43負例、旧single22327/13432と既存simulationが成功。旧core/engine/assets/sample/7通知の保護98ファイルとmanifestがbyte不変。主SDK74exports/57source、WASM638777B/glue53435Bは新guard未搭載。

記録は `sphere-triangle-mesh-trajectory-local-verification.json`、`*-checks/run-20261104-root/`、`*-reference-final/`。Native最初56入力、訂正前61raw、最終62rawと実行記録を分けた。

## 初回試験と未検証

追加したlost-low-term回帰は最初、anchor=startを想定したが、実Pm区間の上端拡張でanchor=endだった。61ケースの分類は全通過した一方、この追加assertが失敗した。実boundsを保存して、元入力を保持したままplaneX=base+1/r=1−3×2^-15の別例を追加した。丸めanchorでは内側でも厳密中点は外側となり、E込みで偽witnessを防ぐ最終assertが成功した。数値kernelを失敗へ合わせて変更せず、初回rawと失敗を保持した。

独立負例の準備ではcount pin未設定でfixture削除を受理した停止と、single-auditでdelta==totalとなり変異が変化しなかった停止があった。固定corpusと複数audit対象へ訂正し、記録を保持して最終71負例を成功させた。数学結果の失敗へ読み替えない。

allocation/内部throwを故意に発生させるfault injection、未返却work.exact=falseの実行、depth<=32 dyadic域で自然未到達のparameter_resolutionは未検証。環境拒否はNative直接試験で実行し、finite JSON62の数学参照とは分ける。Windowsの新sanitizer実行は主張しない。

## 公開受入

[Engine CI 41760594530](https://github.com/tatata93/pikapikaengine/actions/runs/41760594530)と[Pages 41760593424](https://github.com/tatata93/pikapikaengine/actions/runs/41760593424)の全job/step成功。Linux35CTest/Node544skip0、独立参照と旧SDK数値照合も成功した。新cpp/test各−Wall/−Wextra/−Wpedantic/−Werrorは通過し、既存36warning診断は前段と一致した。

GNU ASan/UBSanではguard・mesh・primitive・Interval・core・portable・guard testを全てinstrumentして69群成功。Linux ReleaseとASanの62fixture byteをcmpし、sanitized出力の独立Fraction参照も成功した。Windows保存fixtureとLinuxのbyte同一性の測定とは区別する。

公開42ファイル1,528,714Bがコードcommit93ec576のblobと一致。原著SVGを実公開ブラウザで表示確認し、既存meshラボの既定入力packetをDOMから取得して実WASMと170数値bits/20負零が一致した。全preset/ゲームplayを今回新たに再実行したとはせず、98保護原本不変と既存数値回帰で継承する。公開図は概念図で、ゲームへの新接触適用や性能証明ではない。

全job/step状態、全warningを含む有限ログ抜粋（全ログではない）、配信byteとブラウザ証拠hashを `sphere-triangle-mesh-trajectory-public-verification.json` に保存した。公開確認コードcommitと後続の証拠文書commitを区別する。

## 後続

有界C ABI/JS所有snapshotの接続、専用trajectory UI、World/一般CCD/接触応答/ゲームmesh接触は後続の別受入。流体場、材料損傷、専門車両/航空/鉄道、IK/制御、高精度撮像等も未完。新依存・有料service・メール/フォーラム操作なし、原著SVGと教材25記事を維持、本体ライセンス未選定。
