# pair coverageの全Resultを保存する次段

2026-11-06。Audit/PartitionLeaf後の未実装計画。既存67record型389項目＋別variant1型にResult1型12項目を追加する。

宣言順はstatus、reason、snapshot、snapshot_validated、failed_input、partition_complete、audits、partition、frontier、current、work、message。保存済みの各値を独立に取得し、snapshot_validatedやpartition_completeを配列の内容から再判定しない。

| member | v1取得form | 保存する型・境界 |
| --- | --- | --- |
| status / reason | enumeration | unsigned ordinalをenum tagで保存 |
| snapshot | optional | なし、または元Snapshot全体とInput variant |
| snapshot_validated | field | boolの原値 |
| failed_input | optional_count | なし、またはU64位置。0と欠損を区別 |
| partition_complete | field | boolの原値 |
| audits / partition / frontier | array | 全Audit / 全PartitionLeaf / 全Cellを原順で保存 |
| current | optional | なし、または停止中Cell全体 |
| work | field | 保存済みWork全4計数 |
| message | bytes | 元stringの全lengthと本文byte |

snapshot/current/failed_inputの有無を全8組合せで比較し、保存された不正入力と実validated flag、failed_inputなしと0を区別する。valueなしの監査行、未知のenum、原順・重複の全監査/区画/frontierを保持する。未照会tailやcurrentを省略せず、空配列と欠損を混ぜない。

最終Resultの合理的な組合せだけでなく、人工の矛盾したflag・順序・所属先もそのまま取得する試験を含める。whole coverageの認証や再queryをgetterで行わない。messageの全byte（空・途中NUL・非UTF8を含む）とoptional wrapper、U64位置、別Input variantの型・元値を独立比較する。

値なしInputを含むSnapshotを正当なemplace例外で実target上に作れた場合は、外側Resultの送信済みprefixと失敗の伝播を検査する。旧alternativeを保持するtargetでは保持を別結果にする。送信取消やfake null/ordinalを導入しない。

製品2data TUに演算を追加しない。Interval構築が必要な場合は試験専用TUとして明記する。停止/例外/再入、4丸めmode、17header gate、旧全fixture/20profile/保護原本、Nativeと実GNUを分けて受け入れる。pair全Resultの後はplane box・sphere boxの取得依存を進め、最上位Report/C API pumpへつなぐ。

人工fixtureの具体案（未実装・未受入）:

| source | 設計 |
| --- | --- |
| 外側Result | 17件でReason既知0..14と未知2値、Status既知4種と未知2値を巡回 |
| 最初の8件 | a,b,cをsnapshot/failed_input/currentの有無に対応し全8組合せ |
| 独立flag | snapshot_validated=a XOR b、partition_complete=b XOR cとし、最初の8件で5属性の任意2属性の全4組合せを被覆 |
| failed_inputの値あり側 | 境界count[(i/4+i)%4]（整数除算）で0/UINT64_MAX/2^53+1/2^63をすべて含む |
| 配列 | 空・1件・複数、監査/区画の逆順と重複、frontierの同じCellを繰り返すtailを含む |
| 全child保存case | 末尾caseで先行人工Audit20件/PartitionLeaf12件をすべて入れる |
| 本文 | 空、途中NUL、非UTF8、全256byteを含む本文を原lengthで保存 |

各arrayの全要素を独立仕様で比較し、外側optional maskだけの比較で済ませない。同じfield値の交換はbyteが変わらないため、拒否件数から分離する。最終fixture長・leaf数・callback数・改変件数は、実装後の実行結果で決め、ここでは未測定とする。

実値なしInputの伝播試験ではResultのstatus/reason/snapshot wrapperも先行出力される。invalid_input/input_domainを明示した人工Resultの場合、許される途中状態ではobject・status enum・reason enum・snapshot key/present・Snapshot object/input keyまでがprefixとなる。prefixを独立したv1 byte仕様から組み立てて比較し、Sourceが値なしになった実targetだけで追加拒否を数える。先行Snapshot試験の15byteを外側Result全体のprefixとして流用しない。
