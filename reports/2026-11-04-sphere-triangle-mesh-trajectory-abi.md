# 線分経路guardのC ABI・実WASM raw交換

2026-11-04 JST。ローカル受入PASS、公開CI/Pagesは確認待ち。Native純粋核を変えず、独立stage/recordと6exportsを追加した。使いやすいJS所有decoder/UI/World/TOI/接触応答は次段である。

## 実装

0..64面の専用stageと1..6面append、意味19+予約+0×5のquery24、header32と全getterを追加。各packetは64F64以内で、全source/最大255audit・128leaf・33frontier/current/witness/lastMesh全行と候補を保持する。echo/sourceはNative.snapshotの有無と独立に所有し、旧single/mesh/Worldや後のstage編集と共有しない。

交換拒否は旧stage/record/output/countを保持。正常交換のモデル失敗は新失敗recordを公開する。全packet/optional/settings/source/work/linkを先に監査し、nothrow move後にpublishする。旧mesh helperはconst source/Resultの純粋overloadとして再利用し、旧global recordへ一時代入しない。

## 実行・数値受入

- 新Native交換25群・全36CTestが成功。実255audit/128leaf/末尾、127葉予算のprefix保持、64source/最後の候補、全chunk・不正末尾・reserved−0・再試行・snapshot/output保持・環境/復帰・旧API/World/reset独立を含む。
- 初回Native buildは成功したがテスト側のsize_t→unsignedにC4267が2件あった。型/範囲を明示してtestのみ修正し、専用再build/verbose25群が警告なし成功。初回出力を保持し、本番API/kernel/probeは試験に合わせて変更していない。
- 固定62入力を丸め変更せずprobeへ渡し、59model/3host拒否が確定。25全経路非接触/4点貫通/30モデル失敗を区別。606audit/297certified leaf/lastMesh120行815候補、全optional/Work/−0/予約をpure Native DTOから独立encodeして71,234数値/2,472負零をbit比較。19改ざん拒否が成功。
- 実共通WASMで同じ62入力/全getterを再生し、70,278数値bits/2,398負零がNative一致。WASM rawも同じPython packet検査と19改ざん拒否を通過。これは通常のJS owned wrapperの試験ではない。
- 独立Fraction checkerは元の固定62 pure入力に実行し、48wholepath/4witness/297leaf/606auditを確認。交換59modelの完全bit一致とこの数学scopeを分け、host3をWASMのモデル実行や復元DTOとして数えない。
- 全Node544skip0・構文/Web `d692d4714c9e820a`47modules/23entries成功。旧mesh SDK27160packet/20808modelbits・4453負零/独立2775成分43負例、旧single22327packet/13432modelbitsと既存simulationも成功。

## 配布物・ゲーム・権利

固定Emscripten6.0.13で80exports・59source-headerを実build。WASM674,978B/SHA256 `5f3c633b0f4a209ad07dc8fb3f847d496e0264ecf0ca1eb7667dd38deac0b0e7`、glue56,289B/SHA256 `25dad6ad39c0734d172dd2fee7937a5b33af235a26868dfd2af1954929c72855`。runtime linkedLibraryMembers増減0、7通知hash不変、保護98原本不変を監査した。manifestのsource/artifact/notice全hashも一致する。

実localゲームは新SDKを読み込み、3撃破/移動boost/停止、clip1と20SDK照会全成功・resident meshes3を確認した。最初のshift単独では移動がなく、shift+wの実操作でenergy77・236km/h/開度93%を観測した。hiddenの計測欄は開く前に「未実行」だったため、実際に開いてからJSONを取得し最終証拠へ保存した。新guardをゲームmesh接触へ適用した試験ではない。

原著交換SVG・HTML教材リンク・ガイドと研究/権利台帳を更新。本体ライセンス未選定、新素材/package/外部数学物理実装や課金/投稿/メール操作は追加しない。

## 未検証と次段

故意allocation/internal throw・未知work.exact=falseの例外注入、自然未到達parameter_resolutionは未実行。Windows sanitizerの新成功は主張しない。公開GNUでは新API/testをinstrumentして通常strict核archiveへ結合し、pure guardの別ASan/UBSan工程と区別する。公開CI/Pages/配信byte/実公開ブラウザはこれから確認する。

次は既設80exportsに対するowned JS decoderの全capability事前検出、strict packet/count/enum/flags/padding/全link監査、全DTO所有・caller/後続照会からの分離・旧74exports拒否・無fallbackを実装する。その後専用UIへ進む。一般World/CCD/応答・流体/損傷/専門モデル/IK/高精度撮像の残件を維持する。

根拠は `sphere-triangle-mesh-trajectory-abi-local-verification.json`、`*-abi-checks/run-20261104-root/`、`*-abi-local-browser/` と実行recipesに保存した。exe/obj/lib等のbuild成果物は報告へ混入しない。
