# 接触候補全体の記録を欠落なく取得する

2026-11-07。`world_static_mesh_flight_guard::GuardResult`全14項目のconst取得をNative有限受入。合計97record型575項目＋別Input／Child variant2。正式記録は`reports/diagnostic-wire-guard-result-verification.json`。新GNU・新公開は別受入、確認済み公開版は96型の`8ebf611a`である。

| 宣言順の項目 | 保存する内容 |
| --- | --- |
| status, reason, binding | 元ordinalと設定identityの全65byte。自己計測した実行物hashではない |
| original_settings, failure, preparation | 独立した欠損／存在と、存在する場合の全下位値 |
| preparation_messages | 省略した非規範messageの元計数とflag |
| bodies, pairs | 全要素を元順で取得。重複と未実行tailも残す |
| work, reservation, initial_request | 元の計数・exact flag・予約・当初要求。合算し直さない |
| candidate_bodies | 欠損、存在する空配列、全候補bodyを区別する |
| message | 元の長さ付きbyte列。NUL・非UTF8も保存する |

このgetterはquery・World更新・候補計算・予約を行わない。statusからoptionalを書き換えず、pair_ordinal、execution_ordinal、childのattempt_ordinalを区別する。実queryの全候補認証の契約と、人工保存fixtureで不整合な値を保持できることは別である。入力値は呼出中に有効で、他のthreadが同時変更しない必要がある。

人工32rootは全17Reason／5Statusと各未知4ordinal、5個のoptionalの全32組合せを含む。空／複数配列と重複、7Pairの全3Child alternative、入れ子Input、未実行要素を保持する。candidate_bodiesは欠損と存在する空配列を区別し、元のbody bit列を正規化しない。

Release／真Debugのfixtureと独立仕様は全219,960byte SHA256 `9c900b65b091982e72f7e51b36ce64e22c0aeab12122f37d7f94de495d6e1382`で一致した。6,160leaf＝F64bit976（負零83）＋U643,728＋U32322＋bool655＋enum394＋bytes85、存在260／欠損289、variant8。これは数値queryの実行結果ではなく人工値の保存試験である。

初回early001はDebugの全停止試験が240秒に達して失敗した。4分割のearly002も最初のDebug shardで240秒に達したため、全26,175callback境界・停止／例外52,350件を16個の明示CTestへ分割した。検査件数、真Debug設定、各commandの240秒上限は維持する。今の全Nativeは旧48＋新contracts1＋stop16＝65実CTest、49build target、登録122／120を予定する。元の失敗原本と実exit1を保持する。early002のhelperが途中の個別PASSをsummaryへ残した不備も、原票を変更せず失敗説明票へ分離した。

正当な公開emplaceによる初期Release検査は、MSVC値なし9／保持0、拒否54状態、独立573byte・76callbackの正確なprefix36件、sticky45件、値なし再入235,575件を確認した。private byteを書き換えない。別compilerで旧値が保持される場合は、元の全byte一致を確認して実到達状態を分けて報告する。

全171,199の異なる有効文法変更は4明示shard（各180秒）で通過した。scalar／keyの全138,586箇所、root順序・個数3、欠損からnull289、存在から欠損／null520、enum tag394、field値交換29,092、object順序1,544、array順序・個数548、variant ordinal32、presentへの変換8、wrapper除去8、異なるchild交換26、入れ子両方向置換2、message長147。同値field340／array6／child1は拒否成功に加算しない。全8variantの28組を、非重複27組（同値1）と親子1組の両方向置換に分類した。

改変検査は、元の全文を独立仕様へ照合した後、変更部分以外の全byte一致と元のancestor深さを維持して部分木を比較する。原著supportを導入する前に、既存17,840変更の全件で全文／部分木の両decode結果が一致することを実測した。新Guardでは全variant改変と決定的sampleを全文でも比較する。全件を毎回全文decodeしたと表現しない。完全なscalar／key inventoryは一度保持し、canonical13,260,615byte SHA256 `ffe82711749f5866bf7a6d7090a0cce221ff486eb9d0e73daa7d7f9c3b39c216`を全shardへ照合した。

Webの実97型575項目gate、Node693pass／skip0、構文／buildは成功。集計欄に前段96／561とprepare文言が残った不備は、実行原本を保持して`run-20261106-guard-result-web-metadata-correction-001`へ分離した。将来producerのdocstringとsummary2literal以外のASTが不変であることを確認し、再試験や架空の修正後実行は行っていない。

新対象は製品2data TU＋harness1＋元Interval試験用1TUで、数値model libraryを結合しない。実34oracle閉包／62sourceのGNU driverは全3構成の16stopを含む67commandを準備済みで、実GNUは後続。全Native、最上位World Report／C API pump、今回取得のWASM・ゲーム接続も別受入。一般接触・摩擦・CFD・塑性損傷・精密光学の完成を示すものではない。


全Native001は成功したRelease stop0を旧--run固定parserが拒否して実親exit1。原本を保持し、実50成功CTestと12破損logで検証した別parserを使うnative-002で継続する。成功済みCpp試験を再実行せず、元の実command／raw出力を全byte保持・明記して再解析する。全Native受入はまだない。


Native004の全65実CTestを両構成で受入。旧48と新contracts＋停止16を実行し、各構成で全52350停止例外、全原raw fixture、canonical JSON本文（改行以外）、20profile、402保護原本を保持した。初回からの失敗原本と実成功command／rawを保持・再解析し、同じCpp成功試験を継続時に重複実行していない。Debugを含む実4TUのstrict flagsもsource毎に照合した。97型の実GNUと新公開は別受入である。


公開継続受入: source c9babe9188af59ea4375b3611e9b35108842619eの実GNU13.3全4TU3構成／67command／62source／全171199変更と全16stop shard各構成を固定Git blob照合。Engine42293226518は共通core・実WASM含む全17job最終成功、Pages42293226428も成功。manifest2518宣言の固定Git照合と7実HTTP全byte、公開READY／出撃有効と原著図を確認。全payloadのHTTP転送・new getterゲーム接続ではない。formal diagnostic-wire-guard-result-public-final-verification.json。
