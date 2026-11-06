# pair coverageの元の入力recordを取得する

2026-11-06。accelerated_pair_coverage::SpherePair全2項目とSpherePlane全2項目のconst取得を追加。
合計62型369項目。既存field/元係数getterを使い、primitive tag/versionや数値モデルを変更しない。

SpherePairはfirst/secondを保存する。入力が(A,B)なら(A,B)、(B,A)なら(B,A)を保存する。
対称な問題でもIDや座標で並べ替えない。SpherePlaneはsphere/planeを区別し、raw normal/offsetと元radiusを保存する。
F/m計算、normal正規化、半径へのB/margin加算、元係数の修復や再queryを行わない。
headerを明示includeし、既存17header gateの実宣言を用いる。

人工SpherePair2件とSpherePlane2件、4root recordを用いる。
元Sphere A/BとPlane A/BからPair(A,B)/(B,A)、Plane(A,Plane A)/(B,Plane B)を作る。
独立Pythonは元のbit列から名前付きの入れ子を構成し、全68F64 leaf/負零6とNaN payloadを比較する。
非有限の人工係数を実coverageが受理したという主張には用いない。

全scalar各byteとキー、root交換/除去/重複、名前を保持したままfirst/secondやsphere/planeの値を交換する改変を拒否する。
全callback停止/例外/再入、4丸めmodeと原値の再取得を検査する。
製品2TU+harness1TUのみで、新harnessにInterval TU/数値model libraryを結合しない。
旧20fixtureと全run出力/旧20profile/数値核/owner/SDK/sampleを保持する。
17header+manifestの1受理20拒否と全getter/descriptorを検査する。新GNU3TU O1 ASan-UBSanは公開CIで別受入。

Input variantはこの2recordとは別の境界で、今回の取得には含めない。
次は[明示的な値拒否の設計](DIAGNOSTIC_WIRE_REJECTION_PLAN.md)を先行し、[Input variant](REPORT_COVERAGE_INPUT_VARIANT_WIRE_PLAN.md)の失敗・再入契約を固定する。
全Snapshot/Result、guard Call/最上位Report/C API pump、今回取得機能のJS/WASM/game接続は後続。


実受入: Release/真Debug1875byte/全68F64 leaf/負零6、656停止例外/656再入拒否、4丸めmode保持。独立640byte+3root+4名前付きchild交換拒否、17header+manifest gate1受理20拒否。登録79/77中実行各21CTest、旧20fixture/全run出力/20profile/349保護原本不変、Node693skip0/構文/Webbuild成功。新GNU/Input variantは別受入。
