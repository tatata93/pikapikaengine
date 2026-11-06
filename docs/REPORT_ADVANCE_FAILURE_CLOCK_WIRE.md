# World進行の失敗位置と時刻の丸めを保存する

2026-11-07。`world_static_mesh_flight_advance::Failure`の2項目と`ClockAudit`の4項目をconst取得する実装。作業treeは99record型581項目＋別Input／Child variant2型。Release／真Debug各66実CTestと独立変更検査をNative有限受入。正式記録は`reports/diagnostic-wire-advance-failure-clock-verification.json`。新GNU・公開は別受入。

| 型 | 宣言順の項目 | 保存する内容 |
| --- | --- | --- |
| Failure | stage, object | 型付きStage ordinalと欠損／存在する元の失敗位置 |
| ClockAudit | time_sum, represented_difference, sum_rounding_error, represented_dt | 既存3区間の両端点と、元のdoubleの全bit |

Stageの6値と未知値をそのまま保存する。objectは既存のFailureLocationのkind／index／face_indexを使い、GuardのFailure型と混同しない。getterはadvanceや衝突queryを呼ばず、World・Progressを更新しない。

実Stageは宣言順にenvironment、binding、clock、guard、commit_preparation、candidate_validation。objectのindexは元の所有prepare入力のordinalであり、stable IDの保存順ではない。呼び出し時の元入力との対応を保持して解釈する。

time_sumは元時刻＋要求H、represented_differenceは提案時刻−元時刻、sum_rounding_errorは提案時刻−（元時刻＋H）を囲む既存診断である。represented_dtは丸めた差で、要求Hと異なる場合がある。累積物理時間の厳密値や誤差の補正値ではない。取得時にIntervalを再構築したり数値関係を補正したりしない。

人工16 Failureと16 ClockAuditを検査する。全6 Stage＋未知4 ordinal、元失敗位置8通り、9種類の合法なInterval、represented_dtの16bit pattern（負零・微小値・最大有限値・無限大・NaNを含む）を保持する。fixtureは5,183byte、SHA256 `5012e5b95d0ab5b305e2bc58bf7d697c7d2dbf46f0ff00207c66753b834ec2ea`。独立144leaf＝F64bit112（負零12）＋U648＋enum24、存在16／欠損16。新対象の各構成で804 callback境界、停止／例外1,608件、再入1,608件と4丸めmodeが一致した。

全3,196の異なる有効文法変更を全文decodeで検査した。scalar／key byte2,856、root順序・個数3、欠損からnull16、存在から欠損／null32、enum tag24、field値交換177、object field順序88。同値field交換7件は拒否数に含めない。原記録は`reports/diagnostic-wire-recipes/run-20261106-advance-failure-clock-early-001`と`run-20261106-advance-failure-clock-controls-001`。

新harnessは製品2data TU＋harness1＋元の試験専用Interval1の4TU。Interval構築は人工fixture作成だけに使用し、getterで区間演算は行わない。数値model libraryは結合しない。独立oracleの実閉包は4scriptであり、後続GNUは全4TUの通常／真Debug／O1 ASan-UBSanと全変更検査を要求する。準備したCIはLinuxでの実行成功を意味しない。

続いてCommitWork15／CommitStorage4、AdvanceReport16項目を取得する。全Report／C API pump／今回取得のWASM・ゲーム接続は後続。一般接触・摩擦・流体・塑性損傷・精密光学の完成やゲーム性能の向上は主張しない。

全Nativeはfresh `build/wfdafc2`で旧65＋新1の各66実CTestを一度ずつ実行し、全132 actual assertionを独立再照合した。登録123／121に対し50 executable targetをbuildする。旧16 stop shardの引数・各240秒上限・全52,350停止例外を保持。旧49 unique fixture、20profile、81 source／386保護原本／300 baselineのbyteを保持し、前段の402保護ファイルは全てsourceまたは保護原本の範囲に含まれる。17数値headerを明示sourceへ移したため、保護一覧単独の件数を前段と直接比較しない。全JSON本文は改行以外厳密一致で、直接stdout全byte一致とは呼ばない。


公開継続受入: 84b743dfdd248ce610798b75872bd3d6cf485137の実GNU13.3全4TU3構成／16command／31 unique sourceと全3196変更を固定Git blobへ照合。Engine42303111090は全18job最終成功、Pages42303110852も成功。実manifest2527宣言／7HTTP全byte／公開READYと原著図を確認。467 unique Native／保護sourceも固定Gitへ照合した。全HTTPpayloadやtar転送、新getterゲーム接続ではない。formal diagnostic-wire-advance-failure-clock-public-final-verification.json。
