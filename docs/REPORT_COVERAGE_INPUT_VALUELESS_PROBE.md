# Inputの値なし状態を正当な操作で測る

2026-11-06。これは後続Input取得に向けた到達性試験。取得APIの実装や、あらゆる操作に対する証明ではない。

`std::variant<SpherePair,SpherePlane>` に対して、元のalternativeを0/1で用意し、target 0/1へ投げる変換引数を使って `emplace` する。4通りとも変換内の専用例外を捕捉する。private byteを書き換えない。

| 元のordinal | emplace先 | 実MSVC 19.51 Release | 実MSVC 19.51 Debug |
| --- | --- | --- | --- |
| 0 | 0 | 値なし | 値なし |
| 0 | 1 | 値なし | 値なし |
| 1 | 0 | 値なし | 値なし |
| 1 | 1 | 値なし | 値なし |

実 `_MSC_FULL_VER` は195136247。全4ケースで `valueless_by_exception()` と `index()==variant_npos` を確認した。旧値が残る実装では元のordinalと全係数のbinary64 bitsが保持されたことを別に検査し、その結果を別件数で報告する。GNUの実結果はまだこの表に含めない。

試験は1TUだけで、元の型の宣言をincludeする。Interval実装・診断Writer・Report getter・数値model libraryはbuild/linkしない。最初のMSVC試験は変数名の隠蔽警告C4456で停止したため、元のsource/recipe/logを保持し、変数名だけを直したfresh wfdip2で両構成を実行した。

Nativeの原記録は `reports/diagnostic-wire-publication/run-20261106-input-valueless-native-002/verification.json`、実compile/link監査は `run-20261106-input-valueless-final-001/verification.json`。GNU通常・Debug・全TU O1 ASan／UBSan用の有限recipeを追加したが、GNUの到達性は実返却ログを確認するまで成功と呼ばない。

次のInput getterは、既知のactive childをconstで取得してordinalと共に保存し、値なしを `reject_invalid_value()` でbyteなしに拒否する。まだmanifestの`mappedVariants`は追加していない。既存62record型369項目、全Report・物理進行C API・WASM／ゲームへの取得接続の対応状況も変わらない。
