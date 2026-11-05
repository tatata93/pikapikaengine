# 球・三角形の候補監査と幾何結果を取得する

2026-11-06。`sphere_triangle::CandidateAudit`の5項目と`Geometry`の12項目を追加し、
診断取得は合計34型193項目になった。全Result／全Report／C API pump／WASM・ゲーム接続は未完。

| 実型 | 取得対象 |
|---|---|
| CandidateAudit | feature, disposition, barycentric, kkt, kkt_count |
| Geometry | surface_id, surviving_features, barycentric, closest_local, closest, delta, normal, sphere_point, squared_distance, distance, gap, relation |

Bounds3は`array<Interval,3>`のalias。各3成分とKKTの全2slotを元順で取得する。
kkt_countが0でも、配列を空へ切り詰めない。Geometryの特徴maskを一意featureへ変換せず、
relationからmaskを推測しない。IDはU64、maskとcountはU32、列挙値はU32 enum tagで保持する。
区間は[実端点の取得](REPORT_INTERVALS_WIRE.md)へ渡す。中点や代替normalを計算しない。

実const memberを既存Record／array／専用sinkへ直接渡す。追加の演算・照会・動的確保は行わない。
取得libraryは既存2TUのままで、数値core libraryへ依存を追加しない。
試験targetだけで旧interval.cppを使用し、公開値を実Intervalから構築した。
入力寿命・不変性・排他的Writer操作・Status確認とfinishは[値取得](REPORT_VALUES_WIRE.md)と同じ。

fresh `build/wfdge1` の実MSVC19.51 x64 Release／真Debugで全3241 byteが一致した。
4件の人工診断recordを独立参照で全照合。116scalarの内訳はF64 104・U32 4・U64 2・enum 6、
F64の負零は6個。KKT count=0／最大値、full64 ID、全bit mask、raw enum ordinalを含む。
人工診断であり、球・三角形queryの実行やモデルによる有効性判断は行っていない。

全540 callback境界の1080停止／例外と1080再入拒否、実4丸めmode保持を確認した。
独立参照は文法を保つ254単byte改変とrecord入替／削除／重複3件を拒否。
16header＋manifestの実CMake gateは1受理／19変更欠落拒否。
旧5種の3112／4587／3706／3937／1037 byteと全実行結果が、同じfresh構成で一致した。
登録CTestはRelease64／Debug62、実行は新幾何と旧5種の各6件だけ。
旧20数値構成profile、数学核、owner、SDK、ゲームは保持した。
Node693 skip0・構文・Web build25509ed4cc1d87e4／54modulesも成功。

正式要約は`reports/diagnostic-wire-geometry-verification.json`。
新幾何取得のGNUは公開CIで別受入する。
次はsphere_triangle::Resultの10項目へ進み、optionalのabsent／presentとmessageの実byteを取得する。
前段のIntervalで発生した初GNUの試験書式エラーと修正後の受入は別の原記録へ保持する。
