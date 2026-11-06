# plane boxの監査記録と区画情報の保存

2026-11-06。`accelerated_plane_box_coverage::Audit`全6項目と`PartitionLeaf`全4項目を宣言順に取得する原著実装。取得範囲は75record型427項目＋別Input variant1型。coverage依存内20record型81項目、残り9record型61項目。Native・GNU・公開の受入は、それぞれの実記録を参照する。

| 型 | 宣言順に保存する項目 |
| --- | --- |
| Audit | cell、call_attempted、evaluation、outcome、blocked_reason、split_time |
| PartitionLeaf | cell、state、audit_index、blocked_reason |

Evaluationは全3軸のtubeとdistance・threshold・gapの各区間を保存する。欠損時に再queryや零区間で埋めない。call_attempted、Evaluationの有無、outcome、停止理由、split_timeを独立した保存値として扱い、取得時に整合性修復をしない。人工的な不整合値を実数値モデルの生成物と呼ばない。

元のCellの時間両端・深さ・親位置、区画の元監査位置、分割時刻と欠損を保持する。欠損と0を区別し、2^53+1・2^63・UINT64_MAXを丸めない。raw enumの既知値と未定義の2^31・UINT32_MAXもそのまま保存する。Cellとsplit_timeの人工binary64 bitには負零・subnormal・非有限・NaN payloadを含む。Evaluationは既存の正当なpublic Interval constructorだけで作り、下端-0／上端+0という元の構築契約を別に検査する。

試験の人工20Audit／12PartitionLeafは330typed leaf、194F64、負零15、optionalの存在40／欠損44、4状態の全16maskを含む。early修正版では全10197byteを独立仕様と照合し、1658callback、3316停止・例外、3316再入、4丸めmodeを確認した。7054件の異なる有効文法変更を拒否し、同値端点10／同値field11／同値所有位置1を別に数える。全Native回帰とGNU・公開の受入をearly試験から推定しない。

初回early-001の列挙値変換不足によるコンパイル失敗は原ログと失敗時原本を保存した。明示的なUInt32変換に修正後、別fresh wfdcpap2／early-002で単体Release／Debugを受入。全Native受入は別fresh wfdcpap3と`reports/diagnostic-wire-coverage-plane-audit-partition-verification.json`で確認する。Interval実装はharnessの試験専用1TUで、製品取得層には数値演算やmodel libraryを追加しない。

Writerと参照する全recordは送信中に排他的かつ不変とする。停止・例外では送信済みprefixを保持し、返却status・sticky status・finish・完全なtransportを確認する。全plane Result、最上位World Report、C API pump、WASM／ゲーム接続は後続。[次はplane全Result](REPORT_COVERAGE_PLANE_RESULT_WIRE_PLAN.md)。
