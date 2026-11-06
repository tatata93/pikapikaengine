# plane boxの時間区間と呼出回数を保存する

2026-11-06。`accelerated_plane_box_coverage::Cell`全3項目と`Work`全2項目を宣言順に取得する原著実装。取得範囲は73record型417項目＋別Input variant1型。Native・GNU・公開の受入状態は、それぞれの実記録で分ける。coverage依存内は18record型71項目、残り11record型71項目。

| 型 | 取得する項目 | 保持する意味 |
| --- | --- | --- |
| Cell | time_bounds、depth、parent_audit | 元の秒の両端、元の深さ、元の親位置または欠損 |
| Work | value_calls_attempted、value_calls_returned | wrapperが保存した試行数と返却数の独立した計数 |

時間の両端をdepthから復元せず、順番も変更しない。人工値の負零・subnormal・非有限値・NaN payloadもraw binary64 bitのまま保持する。`parent_audit`の欠損と0、2^53+1、2^63、UINT64_MAXを区別する。新しい親番号を振り直さない。

planeのWorkには呼出試行数と返却数の2計数だけがある。pair用のprivate norm上限を追加せず、試行数から返却数を推測しない。人工的に返却数が試行数を超えていても取得層で修復しない。その組合せを実数値モデルが生成したという意味ではない。

新harnessは数値照会を呼ばず、Intervalの構築TUも必要としない。製品の2data TUと試験専用harnessを、既存回帰試験が使うInterval TUと区別する。Writerと全参照先は送信中に排他的かつ不変であることが前提。停止や例外では送信済みprefixを保持し、返却status・sticky status・finish・完全なtransportを確認する。未完の送信を成功扱いしない。

人工8Cell／4WorkのNative有限受入では1035byte、36typed leaf、負零1、親の欠損4／存在4を独立仕様と比較した。156callback、312停止・例外、312再入、4丸めmode、687件の異なる有効文法変更も検査した。実GNU・公開はNativeから推定せず、`reports/diagnostic-wire-coverage-plane-cell-work-verification.json`以降の実受入記録を参照する。

最上位World Report、C API pump、WASM／ゲーム接続と専門物理モデルは後続。[次はAuditとPartitionLeaf](REPORT_COVERAGE_PLANE_AUDIT_PARTITION_WIRE_PLAN.md)。
