# Native加速球対・平面の全closed-cell coverage

2026-11-04。baseは公開準備記録41c9cc2d28817e3491b8ab8e47922cc5cc153ae5。機能f128f5040c2a4de0c0adba48896022c759f1b215でローカル・公開受入PASS。Linux CI/Pages・GNU/sanitizerも確認した。[契約](../docs/ACCELERATED_PAIR_COVERAGE.md) / [設計](../docs/ACCELERATED_PAIR_COVERAGE_PLAN.md) / [集計](accelerated-pair-coverage-local-verification.json)。

新Native sphere_sphere / sphere_planeは点binary64を厳密実数とする球対四次式とraw plane二次式の全closed[0,H]を調べる。旧searchを二重実行せず、既存public valueの返却Iをそのまま所有する。全leaf strict positiveだけをcertifiedにし、全audit・親/分割・全partition・current・未照会tailを保持する。H/設定/invalid原本/負零をcaptureし、環境拒否を先に区別する。点witness/entry/TOI/運動候補/World更新/力消費は行わない。

## 実行と独立監査

- 全43CTest成功、専用69群（有限65＋nonvacuity/所有/非有限/環境の4群）。43件の実時間228.94秒、収集wall229.02秒。性能保証ではない。
- 有限65は18certified/19not_certified/28invalid。CMake実fixture649028B、SHA946262e5eecc4c575c69956f24881a5b3513adbf5e91fe8e90633533f8bcfcb7、単独buildとbyte一致。
- 全1913返却Iで既存public value両端bitsが一致。実−0 interval端点は0件、原入力/snapshot−0保持とは別scope。
- 独立Fractionが全1913区間（球対1223/平面690）、全1040partition・128frontier・2currentの組会計/BFS/停止順/Workを監査。原入力multiset fingerprint867fef69e55cf8461310b07f0144c8d2288987ab68311d6d86a04b01e8cca85eはscalar type/bit/全配列を含み、label/fixture順に依存しない。
- 四次は有理Bernstein46証明/50node/最大3node。actualのsquare-factor除去は0。gcd偶数因子・非有理重根・負leading/内部極小・有限proof予算拒否は14自己群で別に確認した。
- 改変拒否53（Python -Oを含む）、label/order独立、数学的validな広いIの受入と人工nonreturn整合の正例が成功。これを自然なallocation/value-throw fault注入としない。
- 安全な球対は21audit11leaf、平面は15audit8leafへ実分割。255audit128leafと、評価127時のpartition128/frontier127/current1を観測。2subnormal秒でwidth_limit/time_resolutionを区別し、tiny normal・FE_UPWARD/FTZDAZ拒否と復帰・所有を検査した。
- Node684/skip0・構文・Web build cd45c7f1ac2ba5e5/54modules26entriesが成功。362既存raw・26生成HTMLを保持し、CMake14/CI14/byte保存規約2の追加だけを元Git blobへ復元確認。SDK92exports/67source-header/32TU/runtime91/7通知、WASM800982B/glue61661Bは同一。新APIのNative/WASM parityではない。

## 費用と範囲

attempt/returnはwrapperの実回数。planeのprivate normはcalls≤attempts/loop≤64×attemptsの上界だけで実反復数ではない。MSVC x64のResult440/Snapshot208/Cell40/Audit96/PartitionLeaf72Bと、capacity255/128/128から得た保持payloadは39256B。Snapshotはinline Result内で二重加算しない。allocator overhead・一時buffer・stack・RSS/使用heap・portable hard-byte/16MiB保証は含まない。自然allocation/value-throw faultは未注入。FP試験は対象制御の拒否/復帰で、全compiler/全exception flagの一般証明ではない。

## 履歴と表示

数学run001はchecker-only PASSで、実行済み自己試験失敗ではない。−0 successorは静的レビューで発見しrun002前に正準化した。run002は14自己群PASS後、control-harnessが24整数→24.0の変更をF64等値で無変更扱いして停止した。型も区別する検出へ直し、製品・固定入力を変えずrun003と親reference001で全再実行した。全元command/stdout/stderr/source前後hashを保持する。

ローカルLastTest.logはignore規約で配布されないため、元rawと同bytesのLastTest.txtを保存した。古いrecorder hashを書き換えず、書出拡張子一箇所だけの変更を保存原本と照合した。Nodeログのcp932表示だけのUnicodeEncodeErrorも別の収集メモに残し、成功したNode実行の失敗へ読み替えない。

原著1120×780 SVGと埋込教材を実ブラウザで確認し、2viewportで全文字・区画・未認証境界・費用上界を目視した。図は概念で実測数値ではなく、ブラウザで新Native APIを実行した証拠ではない。初期設計/実装後、[著者のMIT教材1.3.1](https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node9.html)で基底非負性・partition of unityを確認した。外部code/図/本文を転載せず、新依存/素材/有料service/本体license選定は無い。

公開全23段・通常/独自依存5source ASan/UBSan・旧GNU warning比較・84原本配信・実公開UIの受入結果を以下に追記した。次は全Worldの数値統合へ進む。全WorldのB/plane追加predicate・global予算・全body候補、接触応答・摩擦・流体・材料損傷・専門モデル・IK制御・高精度撮像は未完。


## 機能f128f50の公開受入

[公開集計](../reports/accelerated-pair-coverage-public-verification.json)はfresh public-summary-001でPASS。Engine [41828267971](https://github.com/tatata93/pikapikaengine/actions/runs/41828267971) / job126568510900の全23段と、Pages [41828267271](https://github.com/tatata93/pikapikaengine/actions/runs/41828267271)の全3job/stepが成功した。

Linuxでも43CTest/Node684 skip0、専用69群/65有限入力・全1913区間を確認。通常fixtureと、interval/accelerated/新coverage/新tests2の独自5sourceをASan/UBSan計装した別fixtureがbyte一致し、両実行へ独立Fractionを適用した。自己14群/拒否53、新3TUのWerrorが成功。既存48GNU警告は前準備版とfile/line/column/診断multisetが同一、新規0だった。MSVC/GNU全DTOのbit一致や、新APIのNative/WASM parityへ拡張した主張ではない。

83Pages資源＋完全feature commitのGitHub workflow原本1、計84件2573147BがGit blobと一致。図2viewportと教材の全記事/原リンク/画像1120×780を実公開で確認し、図の文字・区画・費用上界・未実装境界に重なりは見られなかった。全11証拠を原本hashと照合した。概念図と旧ゲームの互換性であり、ブラウザで新Native coverageを実行した証拠ではない。

既存ゲームは再出撃後に射撃2撃破・boost energy59/193kmh・一時停止を操作し、22照会の全checked/validated/completed、resident mesh3/errors0を保存した。最初の出撃ではコンテナへキーを準備するUI操作が送信前にtimeoutし、フォーカス済み入力へ切替後の経過21秒で通常の敗北となった。その1撃破のAX/操作メモを別の履歴へ保存し、正式なboost/停止互換性の証拠には採用していない。製品コード変更なしでfresh再出撃し、成功記録とは分離した。

CIは全11844行/882882文字のうち4661行を原ordinal付きで保存した抜粋であり、完全remote logの保存を主張しない。ANSI色付きloop終端・inline参照JSONを初めから含めて元command照合を維持した。status/bytes/browser-record/公開集計は全exit0。既存362raw・旧26HTML・新7source・SDK92exports/67source-header/32TU/runtime91/7通知・WASM800982B/glue61661Bは公開集計時も保持された。

起動: [ロボットゲーム](https://tatata93.github.io/pikapikaengine/?v=f128f50) / [教材](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v=f128f50#accelerated) / [原著図](https://tatata93.github.io/pikapikaengine/docs/learn/diagrams/accelerated-pair-coverage.svg?v=f128f50)。次は同owned snapshotの全pairへB/半径膨張とplaneの追加条件・全体予算・H候補検査を接続する。実Worldのrounded dotと明示contact marginを考慮し、数学的な幾何非交差を既存solverのcontact無しへ読み替えない。一般応答・流体/材料損傷・専門モデル・IK制御・高精度撮像は未完。
