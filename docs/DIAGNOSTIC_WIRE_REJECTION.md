# 値を取得できない場合の明示的な拒否

2026-11-06。`diagnostic_wire::Writer::reject_invalid_value() noexcept` は、取得側が正しい値を提供できないときに使う。何も書き込まず、コールバックも呼ばない。Input variantの後続実装へ向けたprimitive APIで、variant取得そのものは未実装。

| 呼出し時の状態 | 実returned Status | Writerの状態 |
| --- | --- | --- |
| 同じWriterのsinkコールバック内 | reentrant | 外側を変更しない、一時的な拒否 |
| 既存のstickyな失敗あり | 既存Status | 既存失敗を保持 |
| その他 | invalid_state | 失敗を保持し以後の書き込みを拒否 |

未開始でも完了済みでも同じ規則を使う。新しいtag、Status ordinal、frameやデータメンバーは追加しない。既存のv1形式と62record型369項目の順序・記述を保持する。

送信済みprefixや完了済みdocumentを取り消す機能ではない。完了後の拒否でも既存の`complete()`はtrueのままなので、それだけで公開を判断しない。取得のreturned Status、`status()`、`finish()`の結果、`complete()`、transport完了の全条件を確かめる。fake ordinal、null、壊したprivate byteによる拒否の代用は使わない。

新harnessはprimitive製品1TUとharness1TUだけを結合し、Report取得・Interval・数値model libraryを結合しない。人工の正常documentと、拒否自身の出力0byteを区別して検査する。旧primitiveと全21record fixtureのバイト列・実行結果を別回帰で照合する。

実検証の結果は `reports/diagnostic-wire-rejection-verification.json` へ記録する。正当な操作でInputが実compiler上で値なしになれるかは[次のvariant段](REPORT_COVERAGE_INPUT_VARIANT_WIRE_PLAN.md)で測定する。最上位Report、物理進行C API、WASM・ゲームへの取得接続も後続。


Native実受入: Release/真Debugで60状態case/4丸めmode/既存5失敗保持/19callback境界/38停止例外、拒否0byte/0callbackを確認。正常control827byteは独立仕様一致。旧primitive/全21record fixture保持、登録80/78中各23CTest、349保護原本と20profile不変、Node693skip0/構文/Webbuild成功。GNUとInput variantは別受入。
