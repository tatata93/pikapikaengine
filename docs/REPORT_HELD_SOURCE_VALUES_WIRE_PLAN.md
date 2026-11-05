# 保持荷重の原入力と時間セルを取得する次段

2026-11-06。実装前の受入条件。メッシュ全Resultの後、保持荷重の下位診断を原順で対応する。
最初の対象は`sphere_triangle_mesh_held_load.hpp`の3型11項目。全held Resultや新しい物理モデルの実装ではない。

| 実型 | 項目 |
|---|---|
| HeldSphere | id, position, velocity, mass, force, gravity, radius |
| Cell | time_bounds, depth |
| WorldBodySnapshot | body, gravity |

HeldSphereは元の力[N]と重力[m/s²]、質量[kg]を別々に取得する。
getter内で加速度F/m+gや位置を再計算しない。idは全U64、各Vec3とdoubleは既存取得へ渡す。
WorldBodySnapshotは選択bodyの全RigidBody項目を保持し、無視される回転項目や材料・is_staticも捨てない。
このsnapshotだけでWorld全体を取得したとはしない。

Cell.time_boundsは閉じた秒の全2要素、depthはU32。時刻を正規化時間へ変換せず、depthから両端を復元しない。
0幅や負零、逆順などの人工診断値も補正せず保存する。取得試験の値を実モデルが認証した時間窓と混同しない。
公開doubleのInf/NaN/subnormal/最大値/負零を実bitで比較し、Interval不変条件を破った値を作らない。

製品は既存Record/array/fieldと2TUを維持する。新数値TU、照会、再構築、動的確保、外部libraryを追加しない。
複数人工recordで型・原順・full64・全F64 bit・boolを独立比較し、全callback停止/例外/再入、4丸めmode保持を確認する。
新しいfresh Release/真Debug構成で、旧9fixtureの全byteと全run出力を保持する。
旧9種は3112/4587/3706/3937/1037/3241/12924/5414/20256byte。旧20数値profile/数学核/owner/SDK/sampleを保持する。
schemaは41型232項目を見込み、実getter順の全descriptor照合で確定する。既存16header+manifest gateを維持する。
GNU通常/真Debug/全新TU O1 ASan-UBSanと全byte一致は別受入。試験だけでinterval.cppを使う場合も製品依存と分ける。

その後held::Snapshotの原入力/秒horizon/全triangles/settings、held::Workの全11項目へ進む。
CellAuditではoptionalのBounds3やenumが必要になるため、scalarへ暗黙変換せず実childの型を決めてから対応する。
全audit/partition/frontier、最上位Report、所有cache/C API pump、JS/WASM/game接続は後続。
