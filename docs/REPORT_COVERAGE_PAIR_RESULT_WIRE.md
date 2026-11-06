# pair coverageの全Resultを保存する

2026-11-06。`accelerated_pair_coverage::Result`の全12項目を宣言順で取得する。診断全体は68record型401項目と別Input variant1型。coverage依存内13record型55項目が対応し、plane／sphere boxの16record型87項目が残る。

| 保存する項目 | 意味と境界 |
| --- | --- |
| status、reason | 元のenum tagとordinal。未知値も保持 |
| snapshot、snapshot_validated | 元入力・秒・設定の任意recordと、独立した検証済みflag |
| failed_input | 元入力位置のなしと0を区別したU64 |
| partition_complete | 保存済みflag。配列から再判定しない |
| audits、partition、frontier | 全監査行・全区画・未照会の全Cellを原順で保存 |
| current | 停止中Cellのなしと値あり |
| work、message | 保存済み全計数と、元stringの全length・byte |

取得時にqueryを呼ばず、配列をソート・重複排除せず、不整合なflagや所属先を修復しない。人工17Resultは全8optional maskと5属性の40pairwise組合せを含む。最後のResultには先行する人工Audit20件とPartitionLeaf12件をすべて入れる。逆順、重複、未照会tail、空配列、未知enum、位置0／UINT64_MAX／2^53+1／2^63を別々に比較する。これらを実モデルが生成したという主張はしない。

独立仕様との照合対象は30,168byte、941typed leaf（F64 414／負零27、U64 161、U32 110、bool71、enum168、bytes17）、present131／absent126、入れ子variant8。本文は全347byteで、全256種類のbyteと末尾NULを含む257byte本文も分割送信される。

全scalar／key／本文byteの16,856変更に加え、record順序・個数、optional wrapper、enum tag、名前付きfield、全array、variant ordinal・child・wrapper、本文lengthを検査する。異なる有効文法の変更は合計20,854件。同値field交換53件、同値array順3件、同値variant child交換4件は拒否件数へ含めない。分割実行では全8shardの受入と、実decode件数の合計一致を別に確認する。

実targetで正当な投げる変換引数のemplaceによりInputが値なしになった場合、外側Resultの送信済み74byte／13callbackのprefixを独立したv1仕様と比較する。別targetが旧alternativeを保持した場合は、元ordinalと全byteの保持を別結果にする。値なしをnullや偽ordinalで補わず、出力済みprefixを取り消さない。取得の返却値・Writer状態・finish・complete・transportをすべて確認して文書を公開する。

製品は2data TUのまま。harness1TUと既存Interval実装の試験専用1TUを明示し、数値model libraryは結合しない。Sourceは全到達先を含めて生存・不変、Writerは排他的に使用する。停止・例外・再入、4丸めmode、17header gate、旧全fixture・実行出力・20profileを検査する。Native、実GNU、公開状態の実記録はそれぞれ別に受け入れる。

全World Report、物理進行C API pump、今回の取得機能のWASM／ゲーム接続は後続。[次はplane boxの元入力とSnapshot](REPORT_COVERAGE_PLANE_SOURCE_SNAPSHOT_WIRE_PLAN.md)。検証の最終状態は`reports/diagnostic-wire-coverage-pair-result-verification.json`を参照する。
