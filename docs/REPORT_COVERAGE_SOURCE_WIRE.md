# coverageの元の球・平面係数を取得する

2026-11-06。accelerated::Sphere全4項目とStaticPlane全2項目のconst取得を追加。
合計60型365項目。既存F64/Vec3 getterを用い、primitive tag/versionを変えない。

Sphereはcenter/velocity/acceleration/radius、StaticPlaneはnormal/offsetを原順で保存する。
accelerationは呼出者の元の点係数であり、getterでF/mを計算しない。
normalを正規化せず、元半径にBやmarginを加えず、非有限値や負零を修復しない。
入力域の判定や数値queryは行わず、元データのbinary64 bitsを取得する。

accelerated.hppを明示includeし、SHA256 ccc36df04a2a7fb6f617b723d9af586c84a25ee1015a035ba7f1048dd81094c1を17番目の取得source gateに追加する。
schema manifestとCMake gateを対応させ、既存16headerと数値binding profileを変更しない。
取得sourceのレビューと数値モデルのビルド受入は別の契約。

完全初期化済みの人工Sphere2件/StaticPlane2件の4root record、28F64 leafを独立Pythonと比較する。
元の16種類のbinary64 bit patternを循環させ、±0、subnormal、正規境界、±1、有限最大、±Inf、正負qNaN/sNaNのpayloadを保持する。
負零は2か所。型付きbit列の比較を使い、NaN同士の浮動小数点比較に置き換えない。
非有限の人工係数を実モデルが有効入力として受理したという主張には用いない。

全F64の各byteとキー、rootの交換/除去/重複を実改変して拒否する。
callback全境界の停止/例外/再入、4丸めmode、元値の再取得を確認する。
製品2TUと新harness1TUだけで、Interval TU/数値model libraryを新harnessへ結合しない。
旧19fixtureと全run出力/旧20profile/数値核/owner/SDK/sampleを保持する。
17header+manifestの1受理20拒否を検査し、新GNU通常/真Debug/全3TU O1 ASan-UBSanは公開CIで別受入する。

次は[SpherePair/SpherePlane](REPORT_COVERAGE_PAIR_SOURCES_WIRE_PLAN.md)の2型4項目。
Input variant、全Snapshot/Result、guard Call/最上位Report/C API pump、今回取得機能のJS/WASM/game接続は後続。


実受入: Release/真Debug727byte/全28F64 leaf/負零2、256停止例外/256再入拒否、4丸めmode保持。独立260byte+3root改変拒否、17header+manifest gate1受理20拒否。登録78/76中実行各20CTest、旧19fixture/全run出力/20profile/347保護原本不変、Node693skip0/構文/Webbuild成功。新GNUは別受入。
