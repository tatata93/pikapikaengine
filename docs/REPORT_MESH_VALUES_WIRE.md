# メッシュの行と最近傍候補を欠落なく取得する

2026-11-06。`sphere_triangle_mesh::Row`の2項目と`Nearest`の4項目をNative診断取得へ追加し、合計37型209項目。
メッシュ全Result、最上位Report、C API pump、今回の取得機能のJS/WASM・ゲーム接続は未完。

| 実型 | 取得項目 |
|---|---|
| Row | triangle, query |
| Nearest | squared_distance, distance, gap, possible_surface_ids |

Rowは元triangleのID・全頂点の原順と、optionalの実Resultを別々に保持する。
queryがない行は未照会であり、衝突なしや分離の結果へ変えない。queryから元triangleを復元しない。
Nearestの3区間は既存の実端点取得を使い、IDは全U64を原順で取得する。
IDを並べ替えず、重複や0を削除せず、53bitへ丸めず、一意winnerを合成しない。
実モデルで有効なNearestはそのモデルの契約に従うが、取得処理自体は公開値の型と実内容をそのまま運ぶ。

既存Record::field/optional/arrayだけでconst値を直接辿る。製品取得libraryは2TUのまま。
数値照会・再構築・演算・一時vector・追加の数値libraryを導入しない。interval.cppは試験targetだけで使用する。
専用sinkのchunk上限256、元値の寿命・不変性、排他的Writer操作と全返却Statusの確認は前段と同じ。
停止・例外後の途中documentを成功として公開しない。

fresh `build/wfdmv1`の実MSVC19.51 x64 Release/真Debugで全5414byteが一致した。
3Rowと3Nearestの人工診断6件、173typed leaf（F64 135、負零11）、present7/absent2を独立照合した。
元triangleは異なる頂点順とfull64 ID、負零/subnormal/最大有限/Inf/quiet NaNの実bitを含む。
NaNは公開Vec3の診断値であり、Intervalのprivate領域へ書き込んだものではない。
この入力を数値モデルへ提出して受理したとは主張しない。新しい幾何照会は0回。
入れ子のResultには失敗prefixと全geometry/候補/messageを保持し、16/513byteの本文も比較した。
NearestのID列は空、4要素、順序の異なる4要素。0、2^53+1、U64最大値と重複を区別する。

全821callbackで1642停止/例外、1642再入拒否、4丸めmode保持を確認。
独立参照は文法を保つ911単byte改変、root record入替/削除/重複3件、absent→null2件、ID列構造改変6件を拒否。
16header＋manifestのCMake gateは1受理/19変更欠落拒否。型と全fieldのdescriptorを実getter順に照合する。
旧7fixtureの3112/4587/3706/3937/1037/3241/12924byteと全run出力を同じfresh構成で保持。
登録CTest66/64のうち、実行は新1種と旧7種の各8件。旧物理suiteの再実行とは区別する。
旧20数値profile、数学核、owner、SDK、ゲームと他チャットの変更を保持する。

正式記録は`reports/diagnostic-wire-mesh-values-verification.json`。
新Row/NearestのGNUは公開CIで別受入。前段Result3516d037はGNU13.3の通常/真Debug/全4TU O1 ASan-UBSanで
12924byte一致と全16command成功、Engine42094033783全6job/Pages42094034027成功を確認した。
次はmesh::Resultの全12項目。2つのoptional size_tをU64へ明示して取得し、全rowsとnearestの実有無、
各実計数とmessageを保持する。全audit/partition/frontierと最上位Reportはその後に進める。
