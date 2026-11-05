# 自由飛行guard診断の全memberと依存台帳

2026-11-06。実宣言を読んだ次段の台帳。**全体の取得対応は未完**。
根拠は`core/include/pikapika/sphere_triangle_mesh_free_flight_guard.hpp`、SHA256
`e2782e2759b8bb87e920fc022b54fbbee4a456b9ca09a961f6bd26a878f5ea7a`。
既存16header gateで固定している。

| 型 | 項目数 | 全member |
|---|---:|---|
| Settings（取得対応済み） | 2 | held_load, max_angular_increment |
| Snapshot（Native取得済み） | 5 | body, gravity, horizon, triangles, settings |
| Tube（Native取得済み） | 6 | nominal_acceleration, exact_acceleration, acceleration_difference, position_error, roundoff, guard_radius |
| EndpointAudit | 9 | nominal_position, nominal_allowed, exact_position, exact_allowed, exact_difference, l1_error_bound, nominal_contained, exact_contained, l1_within_tube |
| Result | 12 | status, reason, failed_index, world_body, snapshot, tube, flight_failure, candidate_evaluated, endpoint, inflated, candidate, message |

宣言上は5型34項目。Settings/Snapshot/Tubeの3型13項目がNative取得対応済み、未対応2型21項目。
Snapshot/Tubeの結果は[ガイド](REPORT_FLIGHT_SOURCE_TUBE_WIRE.md)。次は[EndpointAudit9項目](REPORT_FLIGHT_ENDPOINT_WIRE_PLAN.md)。
続いてEndpointAudit、符号付き失敗分類の保存経路、Resultへ進む。
inflatedの実held::Result下位13型98項目は先行段で取得対応している。

nominal_accelerationの丸め値とexact_acceleration、acceleration_differenceは別の保存値。
Snapshot.bodyの元半径とtube.guard_radius、inflated.snapshot.input.radiusを混ぜない。
EndpointAuditの全5箱・l1_error_boundと3flagはそれぞれ原値を保存し、getterで再検算しない。
candidate_evaluatedとendpoint/candidateの存在も別々に保持する。
膨張球のentry/penetrationを元の形状の接触と呼ばない。

注意: `dynamics::CcdFailure`はdynamics.hppで`enum class CcdFailure { ... }`と宣言され、基底unsignedの指定がない。
現行Record::optional_enumerationは4byte unsigned基底だけを静的受理するため、flight_failureへそのまま適用してはならない。
符号付き列挙のordinal/32bit表現の契約を明示し、実コンパイラで基底型を確認する。
既知の非負値と負値・境界値の人工fixtureを独立比較し、従来のunsigned enum出力を全保持してからResultへ接続する。
先行のSnapshot/Tube/EndpointAudit取得には、この拡張は不要。

この台帳は取得範囲と依存順の確認であり、数学核の新認証、全Report、C API pump、JS/WASM/game接続の実装ではない。
