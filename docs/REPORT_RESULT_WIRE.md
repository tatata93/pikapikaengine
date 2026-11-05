# 球・三角形Resultの全項目を取得する

2026-11-06。`sphere_triangle::Result`の全10項目を原著のNative診断取得へ追加。
合計35型203項目。全ReportとC API pump、今回の取得機能のJS/WASM・ゲーム接続は未完。

| 項目 | 保持方法 |
|---|---|
| status, reason | 実ordinalをU32 enum tagで保持 |
| geometry, squared_cross, sine_squared | absent leaf、またはpresent＋実child1個＋end |
| candidates | 失敗prefixも含め全vectorを原順で保持 |
| candidates_examined, sqrt_refinements | 実unsignedをU32で保持 |
| sqrt_refinement_limited | 実boolを保持 |
| message | 実stringの全byte。空、NUL、非UTF-8も変換しない |

構築済みconst Resultを直接辿る。成功geometryから候補を再構成せず、statusからoptionalの有無を推測しない。
区間の実端点を既存accessorへ渡し、getter内で数値照会・再構築・演算・動的確保を行わない。
Recordのoptional/bytes経路は、Writerが返したStatusを保持する。
callback中の再入拒否は一時的でWriter::status()がokのままなので、返却値をその値で上書きしない。

messageは文字列のC終端やUTF-8を仮定しない。長さとdata()を専用bytes経路へ渡す。
chunkは最大256byteだが、全document長や候補数を256へ切り詰めない。
sinkはchunkを消費した後に停止・例外となり得る。失敗した取得を完成documentとして公開しない。
呼出側は元値と到達可能なvector/stringを生存・不変に保ち、Writerを排他的に操作し、全Statusとfinish/completeを確認する。

fresh `build/wfdrs1`の実MSVC19.51 x64 Release/真Debugで全12,924byteが一致。
人工Result8件で3optionalの全8組合せ（present12/absent12）、空/複数/重複候補、
message長0/3/255/256/257/1/16/513を比較した。全400typed leaf、F64 304・負零20、message計1301byte。
公開memberの人工診断であり、球・三角形queryを実行した結果や数値モデルの受理とは区別する。
Intervalは実構築された値で、NaNをprivate領域へ書き込んだ不正な値は作らない。

全1898callback境界で3796停止/例外と1898再入拒否、4丸めmode保持を確認。
独立Python参照は2185単byte改変、root record入替/削除/重複3件、absent→null12件を拒否。
16header＋manifestのCMake gateは1受理/19変更欠落拒否。
同じfresh構成で旧6fixtureの3112/4587/3706/3937/1037/3241byteと全実行結果を保持。
登録CTestは65/63、実行は各7件。旧物理suiteの再実行や全登録testの実行とは呼ばない。
取得libraryは専用2TU、旧interval.cppは試験targetだけに使用。旧20数値profileも保持する。

正式記録は`reports/diagnostic-wire-result-verification.json`。
新ResultのGNUは公開CIで別受入する。前段Geometry source87342e8のGNUは通常/真Debug/全4TU O1 ASan-UBSanで
全3241byte一致を確認し、Engine42089030791全6job/Pages42089030975も成功した。

次はmesh::Rowの元triangleとoptional query、Nearestの3区間と全候補IDを取得する。
構造失敗位置/未照会rowを保持するmesh::Result、全audit/partition/frontierと最上位Reportへ進む。
