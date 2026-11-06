# pair coverageの監査行と区画を保存する

2026-11-06。`accelerated_pair_coverage::Audit` 全6項目と`PartitionLeaf`全4項目の取得を追加する。診断全体は67record型389項目＋別Input variant1型。coverage依存内12record型43項目を取得し、17record型99項目が残る。

| 型 | 宣言順の保存項目 |
| --- | --- |
| Audit | cell, call_attempted, value, outcome, blocked_reason, split_time |
| PartitionLeaf | cell, state, audit_index, blocked_reason |

valueなしは未返却・例外等を表す保存上の欠損であり、whole/zero区間を補わない。call_attemptedとvalueの有無も独立に残す。split_timeなしと負零を区別し、Cellの親と区画のaudit_indexを同一視しない。既知・未知のunsigned enum ordinalをenum tagで保持し、none等へ修復しない。

新getterは既存Recordとconst取得だけを使い、Intervalの構築や演算、coverage queryを行わない。試験sourceのIntervalは既存public constructorだけで作る。既存仕様では零の下端は-0、上端は+0となるため、独立仕様は構築後の保存値を比較する。Cell端点とsplit_timeの原binary64 bitsの保持とは区別する。private byteの変更やNaN/逆転区間の不正構築を使わない。

人工Audit20件の最初の16件で、value・split・親の有無とcall_attemptedの全16組合せを作る。区画12件は親・所属先の全有無組合せ、既知state4種と未知2値を含む。Auditの親、区画の親、区画のaudit_indexの値あり側を、それぞれ0/UINT64_MAX/2^53+1/2^63の独立4値集合として確認する。既知Reason0..14と未知2値を保持する。これらの人工的不整合な組合せを実モデルが生成したとは報告しない。

独立比較は6,937byte、230typed leaf（F64 94/U64 20/U32 32/bool20/enum64）、負零7、present40/absent44を対象とする。全scalar/key byte3,800変更と、root3・absent→null44・present除去/null80・enum→U32 64・端点42・外側field363・Cell field96・親/所属先2の計4,594変更を検査する。外側fieldの同値交換9件と親/所属先の同値交換1件はbyteが変わらないため、拒否件数には数えない。

Sourceは生存・不変、Writerは排他的に使う。getter・Writer・finish・complete・transportの実結果を確認して公開する。失敗後の送信済みprefixを取り消さない。停止・例外・再入、4丸めmode、旧全fixture/実行出力/20profileと保護原本を検査する。

製品は2data TUのまま。新harnessは1TUに加え、既存interval.cppを試験専用の追加TUとしてコンパイルする。数値model libraryは結合しない。GNUでは4TUすべてへO1 ASan/UBSanを適用した実結果を、Nativeと別に受け入れる。原記録は`reports/diagnostic-wire-coverage-audit-partition-verification.json`へ集約する。

全Result、最上位Report、物理進行C API、今回取得のWASM／ゲーム接続は後続。[次は全Result12項目](REPORT_COVERAGE_PAIR_RESULT_WIRE_PLAN.md)。
