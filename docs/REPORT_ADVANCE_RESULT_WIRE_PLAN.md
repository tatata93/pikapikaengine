# 進行結果全体の取得：次の実装条件

2026-11-07。`core/include/pikapika/world_static_mesh_flight_advance.hpp` の `AdvanceReport` 全16項目を対象とする計画。CommitWork／CommitStorageの全Native検証と公開を終えた後に実装する。この文書は取得実装、Linux実行、Worldの進行、ゲーム接続の受入記録ではない。

| 宣言順の項目 | 取得形式と保持する意味 |
| --- | --- |
| status, reason | 元のunsigned enum ordinal。Status全5値、Reason全19値と未知値を保存する |
| committed | 元のboolを保存する |
| requested_dt, advanced_dt | binary64の全bitを保存する。成功／失敗から値を作らない |
| original_progress | 既存Progress getterへ委譲する |
| proposed_progress | optionalの欠損／存在と、存在時のProgressを保存する |
| clock | optionalの欠損／存在と、既存ClockAuditを保存する |
| binding | 既存guardのBindingInfoを保存する |
| advance_profile_checked, advance_profile_matches | advance固有の構成確認結果をそれぞれ保存する |
| failure | optionalの欠損／存在と、既存advance Failureを保存する |
| guard | optionalの欠損／存在と、既存GuardResult全体を保存する |
| work, storage | 既存CommitWork／CommitStorageを保存する |
| message | 元の長さ付きbyte列。NULや不正UTF-8を落とさない |

既存101record型600項目とInput／Child別variant2型を前提とし、この1型16項目の追加後は102record型616項目を予定する。descriptorの宣言順と全旧descriptorを比較する。新getterはconst参照だけを受け、advance、query、時刻演算、Interval再構築、候補検査、World／Progress更新を行わない。

人工fixtureでは、実advanceの不変条件から値を補正しないことを調べる。たとえばcommittedとstatus、advanced_dtとrequested_dt、提案時刻とclock、bindingとadvance固有の2bool、failureとguardの欠損、失敗時のassignment計数を独立に設定する。これらの人工的な組合せを実モデルが生成した結果と呼ばない。

4つのroot optionalは全16maskを検査する。Status／Reason全ordinalと未知ordinal、元のfloat bit列、2⁵³を超える整数、空／NUL入り／任意byte／長いmessageを含める。子GuardResultは元のbody／pair順、重複、未実行tailとoptionalの欠損を保持し、親statusに応じて省略しない。既存GuardResult試験の全子データ検証は残す。

最初にfreshの新targetだけを両構成で実行し、fixture全byte数、callback境界数、停止／例外検査の所要時間を実測する。その値から有限の停止shardを決める。fixtureや単一commandの既存上限を無断で緩めず、旧16停止shardを省略しない。必要なInterval TUは実harnessの構築要件を確認して決め、getterによる数値演算と混同しない。

独立decoderは型、field名と順序、全optional、enum ordinal、元byteを全文比較する。変更controlは文法を満たす異なる値を拒否し、同値交換と実行前のprecondition失敗を別に記録する。recursive oracle閉包とGNUのunique source数は実module graphから求め、共有headerを二重加算しない。

全回帰ではCommitWork／CommitStorage段の実67CTestを各一度残し、新Report試験と必要な新shardを追加する。先行段の51種類のraw fixture、20profile、全source／保護ファイルと実引数を保持し、各CTest数とexecutable数を別々に測る。Windowsのsource毎strict flags／真Debug、GNUの通常／真Debug／全新TU O1 ASan-UBSan、実ログと固定Git blobを別の受入条件にする。

この後も全World Report、C API pump、WASM／ゲーム接続は別作業となる。一般接触、摩擦、空気・水の流体、塑性損傷、精密光学の完成をこのgetterの成功から主張しない。
