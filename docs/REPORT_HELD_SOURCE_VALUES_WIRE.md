# 保持荷重の原入力・時間セル・選択bodyを取得する

2026-11-06。HeldSphere/Cell/WorldBodySnapshotの3型11項目をNative診断取得へ追加し、合計41型232項目。
保持荷重全Result、最上位Report、C API pump、今回の取得機能のJS/WASM/game接続は後続。

| 型 | 全取得項目 |
|---|---|
| HeldSphere | id, position, velocity, mass, force, gravity, radius |
| Cell | time_bounds, depth |
| WorldBodySnapshot | body, gravity |

HeldSphereの元の力[N]、重力[m/s²]、質量[kg]を別々に保持する。
getter内でF/m+gや位置を再計算しない。idは全U64、各Vec3/doubleは実F64 bitの取得へ渡す。
Cell.time_boundsは秒の全2要素を原順で取得し、depthはU32。正規化や整列をせず、depthから時刻を復元しない。
WorldBodySnapshotは選択bodyの全RigidBody項目とgravityを取得する。回転・材料・is_staticも保持する。
これは選択bodyの診断であり、World全体の取得ではない。

既存Record::field/arrayと専用sinkだけで構築済みconst値を直接辿る。
製品取得libraryは2TU、新しい試験は1TUだけで、interval.cppや数値model libraryをlinkしない。
同じfresh構成で再実行する旧数値区間の取得試験には、以前どおり試験専用interval.cppを使用する。
入力寿命・不変性・排他的Writer操作、全Statusとfinish/completeの確認、停止時に未完成documentを公開しない契約は前段と同じ。

fresh `build/wfdhs1`の実MSVC19.51 x64 Release/真Debugで全2507byteが一致。
各型2件の人工診断6record、全98typed leaf（F64 90/負零7、U64 4、U32 2、bool2）を独立照合した。
公開doubleにsubnormal/最大有限/Inf/quiet・signaling NaNを含む。元のbitを保持する試験で、数値モデルへの受理や時間窓の認証とは区別する。
Cellは負零を含む0幅と逆順の時間を使用し、整列・補正が入らないことを確認した。
新harnessのモデル呼出しは0回。

全422callbackで844停止/例外と1266再入拒否（3型）、4丸めmode保持を確認した。
独立参照は全scalarの各byteと全keyを改変した886件、root record入替/削除/重複3件を拒否。
16header＋manifest gateは1受理/19変更欠落拒否。全descriptorを実getter順に比較する。
同じfresh構成で旧9fixtureの3112/4587/3706/3937/1037/3241/12924/5414/20256byteと全run出力を保持。
登録CTest68/66のうち実行は各10件。旧物理suiteや全登録testの再実行とは区別する。
旧20数値profile、数学核、owner、SDK、sampleを保持する。

正式記録は`reports/diagnostic-wire-held-source-verification.json`。新held sourceのGNUは公開CIで別受入。
前段mesh全Result ecbaf485は実GNU13.3の通常/真Debug/全4TU O1 ASan-UBSanで20256byte一致、
全16command、Engine42103140815全6job/Pages42103140879成功を確認した。
次はheld Snapshotの全原入力とWorkの実計数を取得し、小型証明record、全audit/partition/frontierへ進む。
