# 自由飛行guardの元snapshotと誤差tubeの取得条件

2026-11-06。未実装の次段。保持荷重Result取得の後に、実free_flight_guard headerの2型11項目を取得する。
予定の合計は52型323項目。既存16header gateで固定された実宣言を使用する。
全下位型の台帳は[自由飛行guard診断](REPORT_FLIGHT_DIAGNOSTIC_INVENTORY.md)。

| 型 | 全member |
|---|---|
| Snapshot | body, gravity, horizon, triangles, settings |
| Tube | nominal_acceleration, exact_acceleration, acceleration_difference, position_error, roundoff, guard_radius |

Snapshotは全RigidBody、元gravity、秒のhorizon、全trianglesの原順/頂点順/重複、free flight設定の全値を保持する。
bodyのforce/torqueと回転・材料・is_staticを落とさず、取得時にsnapshotを再構築しない。
元半径をtube.guard_radiusへ置換しない。後続のinflatedの別snapshotとも分ける。

Tubeのnominal_accelerationは保存された丸め値、exact_accelerationは全3区間、acceleration_differenceも全3区間として別々に取得する。
getterでF/m+gや差分を計算せず、position_error/roundoff/guard_radiusの元F64 bitを保持する。
これらは元のW1から返された上界を保存する経路であり、取得試験で上界の数学的正しさを再認証したとは言わない。

初fixtureは各型複数の全初期化済み人工値。Snapshotの空/複数/別順/重複triangles、全body/全settings、53bit超/U64最大IDを独立比較する。
Tubeは全軸と両端が識別できる値を使い、全scalar byteとkey、原順/個数を改変して拒否する。
公開doubleのraw域と実Intervalの構築域を区別し、区間中点や新しい証拠を作らない。
製品2TUのconst取得、新harness1TU+試験専用旧interval.cppだけで数値model libraryをlinkしない。
全callback停止/例外/再入、4丸めmode取得、全byte再取得を確認する。

fresh Release/真Debugで旧14fixtureの3112/4587/3706/3937/1037/3241/12924/5414/20256/2507/4907/2487/14275/33080byteと全run出力を保持する。
16header+manifest gate、全getter順descriptor、旧20profile、数値核/owner/SDK/sampleを維持する。
GNU通常/真Debug/全TU O1 ASan-UBSanとNative全byte一致は別受入。
先行held Resultの独立改変検査では期待値を毎回作ると実133秒だったため、仕様を一度構築して再使用し全出力一致を確認した経路を使う。
新しい改変検査でも全対象byteと全構造を維持し、実時間を測って有界CIへ収める。

その後EndpointAudit9項目、CcdFailureの実ordinalとfree flight Result12項目を別に固定する。
基底unsignedを指定しないCcdFailureには現行のunsigned専用optional enum helperをそのまま使わず、符号付き表現の別受入を行う。
全guardのcall/pair/variant、最上位Report、C API pump、JS/WASM/game接続は後続。
