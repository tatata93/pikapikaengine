# Reportの葉型を、そのまま取得するNative層

2026-11-06。`report_values_wire::write(Writer&, const T&)` は、進行診断に含まれる
次の12型を[診断wire v1](DIAGNOSTIC_WIRE.md)の値一つとして出力する。
**全Reportのserializer、C API pump、WASM／ゲーム接続は未実装。**

| 型 | 取得するmember（Native名・原順） |
|---|---|
| Vec3 | x, y, z |
| Quaternion | x, y, z, w |
| dynamics::Material | restitution, friction |
| dynamics::RigidBody | id, is_static, mass, inertia_diagonal, radius, position, velocity, angular_momentum, orientation, force, torque, material |
| dynamics::Plane | id, normal, offset, material |
| sphere_triangle::StaticTriangle | id, vertices |
| world_static_mesh_flight::StaticMeshSource | id, revision, triangles |
| controlled_tick::BodyLoad | body_id, force_newtons, torque_newton_meters |
| controlled_tick::TickLoadPacket | mode, expected_tick, loads |
| advance::Progress | time, ticks |
| scheduler::Settings | step_seconds, max_attempts_per_pump |
| scheduler::Snapshot | settings, backlog, sequence, busy |

合計44member。配列／vectorの原順を保持し、空のtriangles／loadsもarrayとして出す。
数値はF64 bit、ID／tick／size_tはU64、boolはboolean、modeはenum ordinal。
Quaternionの正規化、massやforceの検証、IDの重複除去、plane normalの補正は行わない。
不正な物理入力も診断値として保持できることと、それをモデルが受理することは別。

## 呼出しと停止

callerがWriterのdocumentを開始し、出力先のobject keyやarray内に`write`する。
必ず返却Statusを検査し、全値の成功後にdocumentをfinishする。
入力と到達する全vectorは、sink callbackを含む呼出し全体で生存・不変とする。
sinkへ渡すbyteの寿命はcallback終了まで。callerが必要なbyteをcopyして所有する。
同時thread操作やcallbackからの入力破棄・変更は契約外。

葉型の出力は動的確保、World再構築・再照会、物理計算やrollbackを行わない。
sink停止・例外をそのまま返し、残りのvector要素を出力し続けない。
再入拒否はWriterの外側を壊さないため、一時的に`reentrant`を返す。
その際にWriterの保存statusがokでも、葉型の返却をokに読み替えない。

この層は任意長vectorの全値を順に出す。256 byteはcallbackの最大chunkであり、
Report全体のbyte上限や物理モデルの最大body/face数を保証するものではない。
将来の全Report取得では、fixed arrayのactive prefixとcountも別に検査する必要がある。

## field変更の確認ゲート

`core/report-values-schema-v1.json` は12型・44memberと、8つの実宣言headerのhashを保持する。
`cmake/ReportValuesSchema.cmake` は、その8headerとmanifest自身のhashを実configureで照合する。
変更や欠落があればconfigureを拒否し、旧fieldだけを黙って出力しない。
将来そのheaderを編集するときは、対応fieldと独立参照を確認してmanifest／gateも更新する。
これはC++ reflection、全Report型の自動網羅証明、数値bindingやruntime unlockではない。

## 実行済みの有限検証

fresh `build/wfdv1` の正式CMake targetでMSVC19.51 x64 Release／真Debugを実行した。
14recordの3112 byteが全一致し、独立Python参照で96 F64 bit値（負零7）、
全119 scalar leaf、key・型・配列順・full64・raw modeを照合した。
16種のF64 bitには±Infinityと符号／payloadの異なるquiet/signaling NaNも含む。
実4丸めmodeで値とmodeが保持された。全FPU環境やNaN trapの証明ではない。

全521 callback境界で1042停止／例外と6252葉型再入拒否を確認した。
同じ入力の繰返し出力は不変で、callerがcopyしたbyteは元vectorをclearした後も保持した。
独立参照は文法上有効な264単byte改変と、recordの入替・削除・重複3件を拒否。
実CMakeの隔離copy試験は原本1件を通し、9変更／2欠落を拒否した。製品headerは変更していない。
登録CTestはRelease59／Debug57だが、ローカル実行は新各1件だけ。旧308原本と20構成profileは不変。
旧数値coreをbuild／linkしていない。新GNU通常／Debug／ASan-UBSanは公開CIの別受入とする。

前段のprimitive v1は実GNU13.3で通常／真Debug／O1 ASan-UBSanの14commandが成功し、
全1148 byteがNativeと一致した。返却decoded log 983135 byteを保存し、sourceと実commandを照合した。
child raw／objectはrunner-localで取得していない。この前段の成功を新しい葉型のGNU成功へ流用しない。
記録は `reports/diagnostic-wire-values-verification.json` と `reports/diagnostic-wire-gnu-verification.json`。

次はguard settings、interval／audit／partition／frontierを含む全依存型と、
最上位Report・未実行tailを[対応台帳](WORLD_STATIC_MESH_REPORT_EXPORT_INVENTORY.md)から埋める。
