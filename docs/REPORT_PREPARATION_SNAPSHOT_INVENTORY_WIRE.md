# 所有SnapshotとInventoryを元の値のまま取得する

2026-11-07。Snapshot6項目／Inventory7項目のconst取得をNative有限受入。合計95record型554項目＋別Input／Child variant2型。正式記録は`reports/diagnostic-wire-preparation-snapshot-inventory-verification.json`。GNU・公開は別受入。

| 実型 | 宣言順の全値 | 取得時の契約 |
| --- | --- | --- |
| Snapshot | gravity, horizon, settings, bodies, planes, meshes | 下位値と全vectorを元の順序で保存する |
| Inventory | dynamic_bodies, static_bodies, total_faces, colliders, all_pairs, excluded, pairs | 全5count、全除外計数、元の全Pairを保存する |

Snapshotは元の所有値である。取得時にWorldを再captureせず、gravity・法線・orientation・力を正規化しない。horizonの負零や非有限値もbit列を保存する。空vector、重複、元の順序、人工的な不整合を勝手に補正しない。mesh revisionを計測した内容hashへ読み替えない。

Inventoryのall_pairsやexcluded.totalは、取得側で再計算しない。pairsの順序と両参照のkind・id・型付き元ordinal・revisionも保存する。実prepareのready一覧を受け取った場合と、人工保存fixtureで不整合な値を保持できた場合は、異なる検証である。

人工入力は4Snapshot＋4Inventoryの8record。各vectorに空・単要素・複数・重複を用意し、整数境界0／U64最大／2^53+1／2^63を含める。binary64は正負零・正負subnormal・正負最大有限・正負無限・quiet／signaling NaNを元bitのまま検査する。独立仕様は元の葉値とPair仕様を読み込み、実再帰oracle全4本を指紋対象へ含める。

新対象のfresh `build/wfdpsi1` Release／真Debugで全8,821byte SHA256 `d8d60093554c997da2349653f41dd8a0dc79a20c37f0c621a8f1a80069051c86`が一致。320typed leaf＝F64bit148（負零12）＋U64142＋bool3＋enum27、1,392callback、停止／例外2,784件、再入2,784件、4丸めmodeを確認。製品2data TU＋harness1の3TUで、Interval TUと数値model libraryは不要である。

全5,537の異なる有効文法変更を単一180秒上限内で拒否した。内訳はscalar／key byte4,583、root順序・個数3、enum tag27、field値交換766、object field順序104、array順序・個数54。同じ値になるfield交換7とarray順序2を別集計し、拒否成功へ加算しない。

全Nativeは別fresh `build/wfdpsi2`で旧46＋新1の各47実CTest（登録104／102）、全旧raw fixture、20profile、399保護原本を受入。親93型のschema2 assertionResultsに保存したcanonical JSON本文と実CTest原logをbaselineに使い、存在しない単独runを作らない。全テストは実行し、JSON本文は改行以外厳密一致、protocol fixtureは全raw byte比較を保持する。

source `7715a6909972bbd8f4fca7ea0206a371b4c09b8a` の実GNU13.3通常・真Debug・全3TU O1 ASan-UBSan、全8,821byteと全assertion／全5,537変更を正式受入。実4参照／30sourceをfeature Git blobへ照合した。正式`reports/diagnostic-wire-preparation-snapshot-inventory-gnu-verification.json`を参照。

prepare Result7、GuardResult14、最上位World Report／C API pump、今回取得のWASM・ゲーム接続は後続。これは保存経路の検証であり、衝突応答、CFD、車体の塑性損傷や精密レンズモデルの完成ではない。


Engine42269272010は共通core／実WASMを含む全15jobが成功。Pages42269271912はbuild／実archive成功、deploy128069596791が13秒で配信側失敗を返し、実HTTPは8fdを保持した。timeout失敗ではない。正式public-failureと[PAGES_DEPLOYMENT_QUEUE_BUDGET.md](PAGES_DEPLOYMENT_QUEUE_BUDGET.md)に、入力660000msが実装上600000msへ丸められていた訂正も記録する。Web票の説明行に前段の型名が残っていた点は、旧票を保持したweb-label訂正票へ分離。実95record554fieldの結果は変更せず、producerの実行ASTも不変である。
