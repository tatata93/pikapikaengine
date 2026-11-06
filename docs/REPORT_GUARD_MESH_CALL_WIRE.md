# World guardのメッシュ呼出記録を保存する

2026-11-06。`world_static_mesh_flight_guard::MeshCall`全8項目のconst取得をNative有限受入。合計85record型496項目＋別Input variant1型。正式記録は`reports/diagnostic-wire-guard-mesh-call-verification.json`。GNU・公開は別受入。

| 元の項目 | 保存する内容 |
| --- | --- |
| state、attempt_ordinal | 元の状態ordinalと、全child呼出にまたがる元の64bit試行位置または欠損 |
| requested_settings、used_settings | 元の要求設定と実使用設定を別々に保持 |
| granted、grant | 元の許可boolと、拒否時も保持された計算済みGrant |
| result、messages | 返却された自由飛行Result全12項目または欠損、元のMessageOmission全4項目 |

保存位置から試行順を推測せず、要求設定を実使用設定へ置き換えない。granted=falseでも元のgrantを捨てず、grantをchargedへ読み替えない。結果が欠損していても再queryせず、省略済みmessageを復元しない。人工不整合値の保存は数値モデルの生成・認証を意味しない。

新対象だけのfresh `build/wfdgm1` Release／真Debugでは人工16MeshCallの全46,923byte SHA256 `2f2e30d9919ed7851278339e12732227faa27c473ebdef5f000cc59bb9d8d9c8`が独立した自由飛行・計数台帳仕様に一致した。1,270typed leaf（F64 375／負零27、U64 604、U32 189、bool52、enum39、bytes11）、存在35／欠損100、外側の全16optional・bool組合せと全4試行位置境界を確認。全件で要求設定と実使用設定が異なり、既知3状態と未知3ordinalを保持する。

5,453callback、停止／例外10,906件、再入10,906件、4丸めmodeの保持も単体で成功した。単体原記録は`reports/diagnostic-wire-recipes/run-20261106-guard-mesh-call-early-001/verification.json`。

全Nativeは別fresh `build/wfdgm2`で受入。39CTestを旧32＋個別7件に分け、各240秒上限を維持する。独立変更検出は全16担当shardを各180秒で検査し、35948変更と同値348交換を区別して受入。製品2data TU＋harness1＋元Interval試験用1TU、数値model library非結合。独立子仕様の自由飛行Result・Snapshot／Tube・Endpoint・保持荷重Snapshot／Work・Ledgerの5scriptも固定する。PlaneMetricCall／PlaneBoxCall／SphereCall、別Child variant、Pair／GuardResult、最上位World Report、C API pump、今回取得のWASM／ゲーム接続は後続。
