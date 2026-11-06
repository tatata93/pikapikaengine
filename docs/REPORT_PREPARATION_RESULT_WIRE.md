# 準備結果の理由・保存状態・元の値を一緒に取得する

2026-11-07。`world_static_mesh_flight::Result`の全7項目をconst取得する実装。全Native48件を有限受入。合計96record型561項目＋別Input／Child variant2型。正式記録は`reports/diagnostic-wire-preparation-result-verification.json`。GNU・公開は別受入。

| 宣言順の項目 | 保存する内容 |
| --- | --- |
| status, reason | 元の型付きordinal。未知の値も保存する |
| failure | 欠損、または元の失敗位置全値 |
| capture | 元のCaptureState ordinal |
| snapshot | 欠損、または所有Snapshotの全値・全配列 |
| inventory | 欠損、または全count・除外計数・全Pair |
| message | 長さ付き元byte列。埋め込みNUL・非UTF8を保持する |

status・captureと3個のoptionalを独立に保存する。getterはprepareやWorld capture、衝突queryを呼ばず、元の組合せを補正しない。実prepareではready時だけ完全なinventoryがあるが、人工保存fixtureでそれ以外の組合せを取得できても、実prepareの契約を検証したことにはならない。partial snapshotのコピー済みprefixを完全な入力と見なさない。

人工30Resultは全26Reason／5Status／3CaptureStateと、それぞれ未知4ordinalを含む。最初の16件で全8optional maskを二巡し、失敗位置8通りとSnapshot／Inventory各4通りを保持する。messageは空、埋め込みNUL、非UTF8、513byte中の位置256／511にNULがある例を検査する。

fresh `build/wfdpres1`の新対象Release／真Debugで、全26,194byte SHA256 `8af9c976bdd5f701d5ad90b3d1893e4334bc355c91ea65e71fbc2dc0890d937f`と全assertionが一致。独立776leaf＝F64bit296（負零24）＋U64292＋bool6＋enum152＋bytes30、存在32／欠損74。3,634callback境界、停止／例外7,268件、再入3,634件と4丸めmodeを確認した。

全17,840の異なる有効文法変更を4明示shard（各180秒上限）で漏れなく拒否。scalar／key byte15,037、root順序・個数3、欠損からnull74、存在から欠損／null64、enum tag152、field値交換2,104、object field順序246、array順序・個数108、message長52。同値field交換96／array順序4は拒否成功に加算しない。

全Nativeの別fresh `build/wfdpres2`では旧47＋新1のRelease／真Debug各48実CTest、登録105／103、全旧raw fixture・20profile・401保護原本を受入した。schema2親のcanonical JSON本文と実CTest原logを基準にし、存在しない単独run出力は作らない。新対象は製品2data TU＋harness1の3TUで、Intervalと数値model libraryを結合しない。旧回帰harnessに必要なIntervalは別である。

独立oracleの実再帰閉包6scriptをsourceへ固定し、GNU driverは32source／19command、通常・真Debug・全3TU O1 ASan-UBSanと全4変更shardを要求する。Windowsでの閉包事前照合はLinux実行の受入ではない。

source `8ebf611a3c37281f5248b2d0422d2cd8c988f65f`は実GNU13.3の全3TU通常／真Debug／O1 ASan-UBSan、全26,194byte・assertion・17,840変更がNativeと一致。実6oracle／32source／19commandを固定Git blobへ照合し、受信親exit0を観測した。Engine42277633195は共通core・実WASMを含む全16job成功、Pages42277633088もbuild／deploy成功。実manifest、7HTTP応答、公開READY／出撃有効と原著図解全体を保存し、正式`diagnostic-wire-preparation-result-public-final-verification.json`へ継続受入した。全2,507payloadのHTTP転送や新getterのゲーム接続は主張しない。

次は[GuardResult全14項目](REPORT_GUARD_RESULT_WIRE_PLAN.md)、最上位World Report／C API pump、今回取得のWASM・ゲーム接続。これは診断データ保存経路であり、一般接触・摩擦・CFD・塑性損傷・精密レンズ計算の完成ではない。既存ロボットサンプルのゲーム処理は変更していない。
