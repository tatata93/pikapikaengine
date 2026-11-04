# 素材・権利台帳

確認日: 2026-11-03。対象: 最初の縦断試作と学習教材。

エンジン本体の公開ライセンスは未選定です。この台帳は著作権の譲渡やライセンスの宣言ではありません。公開リポジトリへ置くことと、OSSライセンスを付与することを区別します。利用者が再配布できる条件の確定は公開版の残課題です。

## この版に含める素材

| 対象 | 出所・作者区分 | 取得・作成日 | 利用条件・配布境界 | 検証状態 |
|---|---|---|---|---|
| `docs/learn/diagrams/*.svg` | 本プロジェクトで新規作図 | 2026-11-03 | エンジンのライセンス決定と併せて明文化。外部図版の転載なし | 下表のSHA-256で識別 |
| 教材内のフレーム予算・派生データ概念SVG | `docs/learn/index.html`、`modeling.html`内で新規作図 | 2026-11-03 | 同上。概念/例示値であり測定結果ではない | HTML原本を管理 |
| 炎デモの輪郭・波形 | `docs/learn/flame.js`による実行時生成 | 2026-11-03 | 同上。外部画像なし | sin・独自の値ノイズによる近似 |
| サンプルのロボット・地形 | プロジェクト内の手続き形状 | 2026-11-03 | ライセンス未選定。既存ゲームのモデル、名称、UI、音源等の複製を行わない | 外部素材の取込みなし |
| サンプル音源 | プロジェクトの手続き生成 | 2026-11-03 | ライセンス未選定。外部の録音、IR、HRTFデータセットなし | 再生機器の校正なし |
| `assets/pikapika-core.wasm` | 本プロジェクトのC++ソースをclang18.1.3でコンパイル | 2026-11-03 | 外部ランタイムをリンクしない。元ソースと同じライセンス未選定状態 | 650B、SHA256と原本ハッシュ・CI来歴を同名build.jsonへ記録 |
| `assets/pikapika-simulation.wasm` / `.mjs` | 自作C++物理・光学・motion・位置skinning・派生meshとEmscripten 6.0.13標準ランタイム・生成glue | 2026-11-03 | 独自コードと第三者ランタイムを含む。第三者の通知はthird_party/emscripten-6.0.13、エンジン本体のライセンスは未選定 | 現在のまとめ読出し版はWASM592939B、glue50381B、66 exports。原本/生成物/通知のSHA256は同名build.json、ローカル検証と公開結果は最新reportsで区別 |
| `assets/iron-field.scene*` | 自作APIによる手続き生成のシーン原本 | 2026-11-03 | 原本を再編集可能な形で保存。外部モデル・モーションなし | JSON/共通テキスト形式の往復を検証 |
| ブラウザの標準フォント | 利用者のOS・ブラウザ環境 | 配布なし | フォントファイルを成果物へ含めない | 外部フォント/CDN不使用 |

## 図の原本ハッシュ

パスはリポジトリ基準。すべてSHA-256。派生PNGは作成していません。図を変更したらこの値も更新してください。

| 原本 | SHA-256 |
|---|---|
| `docs/learn/diagrams/fixed-step.svg` | `F9D7B518DFD4416146375700F8D669D38435BB5C88B5CE41A76143AFA7BBD4F1` |
| `docs/learn/diagrams/renderer.svg` | `245BDD5E98A6912AFADF869E04477070D3A86F354C5EBE903CA80A15C1C07E0D` |
| `docs/learn/diagrams/sine.svg` | `0C3FDCB8BA158ADB5A5C26711D9E5F6746FA251FC3B506A5EBE017FB716DE0F8` |
| `docs/learn/diagrams/sound.svg` | `C27C838C25E25783AE9902F4421EA805C82BBEDEA3C686FC9C9EF1FA5AC0AA48` |
| `docs/learn/diagrams/mesh-edit.svg` | `E8109929B4F6073193D2F100313EBAA5CE3D03E18BFD0AE1B66E511475AA5CD0` |
| `docs/learn/diagrams/buoyancy.svg` | `6ABE7EE02C2E580BB3D84DA76CC4C401948946EF2F0FB4D332AEF3C2F1D633A0` |
| `docs/learn/diagrams/continuous.svg` | `B9FFA9E0452146634C24695816049263D0688BB1F340C5A0BA8A57C2ADBAA6BE` |
| `docs/learn/diagrams/interval.svg` | `38EB73D4425C5416DFEC2B1D82BFA28F537DCCF4D3BB4BA82D5898BA09F06A37` |
| `docs/learn/diagrams/optical-interface.svg` | `4365C8563506EC1BA2E298F7EDF36CAD1C5344E7E8F41B954E2D4884533E5F46` |
| `docs/learn/diagrams/accelerated.svg` | `9F16B219B81B47249C848723E9C25B9C13EBFEAA0538401CC2CE5A08DE023103` |
| `docs/learn/diagrams/lens-surface.svg` | `D8429C084C8553531F207E8F505445FB68456F7C1DDE6FDA267057FFFA14F601` |
| `docs/learn/diagrams/continuous-world.svg` | `BA4C360704B9B051A8C2370714860EB046A9F63D00A0915CB7A2D9C80372F244` |
| `docs/learn/diagrams/polarization.svg` | `F9FD5CA1F72DBDD76BE80293AF5956934D88099F329E90B0668C71F1D258605F` |

## 追加原著SVG（区間光路・支持・支持運動）

2026-11-03に原本のバイト列を計測。外部の図・画像・フォント・処方・測定材質値を取り込まず、
本プロジェクトでSVGコードを作成した。サイズはUTF-8原本のbytes、ハッシュはSHA-256。
エンジン本体と同様に公開ライセンス未選定であり、以下の記録は権利譲渡・再配布許諾の宣言ではない。

| 原本 | bytes | SHA-256 | 内容・配布境界 |
|---|---:|---|---|
| `docs/learn/diagrams/optical-route.svg` | 1631 | `98A9D2005CB182C4020B3A244D55BD0875B5F4005639A03CEB7E100EC9A79DD1` | 自作平板の法線入射・指定二回反射の解析例。反射経路は識別用の模式配置で、校正レンズ画像や全ghost探索の証拠ではない |
| `docs/learn/diagrams/support.svg` | 1856 | `EA095841C2735912683730425C1DB39DBD5C33F44A2DC06BC7671455798328AA` | 自作の合成荷重stackと球対gap加速度の模式図。52/47/23Nは指定荷重の解析例で、実機測定値や支持の時間発展ではない |
| `docs/learn/diagrams/supported-world.svg` | 2029 | `4194B6CDB2C0B724176D627BD10EA1297EC977FB94BB7123BAAE0EC7F87D8A35` | 自作の支持区間・衝撃・離脱と全tick保持の概念図。時間幅・曲率は説明用で、真の連続解や実測軌跡の保証図ではない |


## 最近傍光学の追加素材

`docs/learn/diagrams/optical-selection.svg` は原著の前後面・未確定面と閉prefixの概念図。1833B、SHA256 `f10738d58c707e5c9202804b0b0f18f47f7364246d3fcbb6e118315c8ad9317a`。測定図・外部処方・実在製品の素材ではない。HTML/Canvas UIと教材18番の記事も独自作成。

## 外部素材の導入状況と次の取込み条件

外部モデル、モーション、テクスチャ、効果音、音楽、IR、HRTF、外部画像はこの教材へ導入していません。既存作品名は目標の比較としてのみ扱い、素材利用の許諾とは解釈しません。

将来の素材ごとに、作者、配布元URL、取得日、原本ハッシュ、ライセンス原文の確認日、商用利用、改変、エンジンへの同梱、ゲームへの同梱、再配布、帰属表示、派生物、AI利用等の個別制限を記録します。形式のライセンスと素材のライセンスは別です。許諾不明の素材を公開成果物へ含めません。

文献はリンク・数式の確認に使い、ページ本文、図、コード、フォントを同梱していません。参考資料一覧は[REFERENCES.md](REFERENCES.md)。

波長分散の独自図 `docs/learn/diagrams/dispersion.svg`: SHA256 `f77a4b6aa896137927ec4adf1c0f52cb3609a405e71b646915776351c6d1ae3b`。合成モデルの模式図で、実在製品・測定値・外部素材を含まない。実装/本文/係数も独自作成、エンジン本体のライセンス未選定。


## 幾何点像の追加素材

`docs/learn/diagrams/lens-spot.svg` は原著の説明用概念図、2097B、SHA256 `94448290463c322045b2f6a0d5caa907f18c69c6ef990b9ea9639c048e2c51e4`。HTML/Canvas UIと教材19番も自作。R=±50mm・厚さ5mmと合成Cauchy係数は説明用の独自profileで、実在レンズや実測材質を示さない。外部の素材・画像・フォント・処方を含まず、エンジンのライセンスは未選定。

## 偏光経路の追加素材

`docs/learn/diagrams/polarized-route.svg` は独自概念図、1418B、SHA256 `11ba65766d24a466530dedf5b79827d916a098bf4a773c63f5dd254da5e7930f`。ラボHTML/Canvas/教材20番も自作。外部画像、処方、実測材質、フォント、コードを導入していない。エンジンライセンスは未選定。

有限光束の原著図 `docs/learn/diagrams/lens-power.svg`: 1849B、SHA256 `be5b69658de9e480fb961e2f390e9e15edf9b754bc765408079b61d35e12e7a7`。HTML/Canvas UIと教材21番、合成レンズ二経路/離散packet profileも独自作成。外部の図、コード、処方、実測素材を取り込まない。エンジンライセンスは未選定。

骨格キーの原著図 `docs/learn/diagrams/motion.svg`: 1900B、SHA256 `c06c54a077888d0fcda5b943453065dfe6cef309289dd5223c346affca39310b`。4ボーンの二リンクarm/秒単位キー、HTML/Canvas制作ラボと教材22番も独自作成。外部のモデル・モーション・図・フォント・コードを含まない。線の姿勢と時間は説明用で実測ではない。エンジンライセンスは未選定。

位置スキニングの原著図 `docs/learn/diagrams/skinning.svg`: 2040B、SHA256 `caaf9d27b13339ffa943effa23ca384fb179cdf639e294d6f627b5358218aed6`。原本と作業用weight、現在骨行列×rest逆行列を混ぜる手順の概念図。教材23番も独自作成し、外部図・モデル・モーション・フォントを含まない。GPU実測/材料損傷の図とはしない。エンジンライセンス未選定を維持。

位置skinning共通SDKの操作ラボ `tools/skinning-lab.html` / `.mjs` も原著。2骨・6頂点の帯と非一様scale/相殺/underflowの合成入力、Canvas XY/XZ投影、確認用JSONと診断表示はプロジェクト内で作成した。既存の上記skinning.svgを再利用し、新しい外部モデル・モーション・画像・図・フォント・材質・コードを取り込まない。C++が返す位置の表示を、変形メッシュのゲーム描画・法線・接触・損傷や再読込可能なbindingアセットと同一視しない。本体の公開ライセンスは未選定のまま。

原本binding制作の原著図 `docs/learn/diagrams/skin-binding.svg`: 2114B、SHA256 `3c8acf8ccf79a95bfd6fb2b475fbd0d357dd343c6fd8dbf62d0ef259ff39fdcb`。全原本の所有・JSON/portable往復・全Scene/rest照合・共通C++位置照会を分けた概念図で、測定ではない。教材24番、`tools/skin-binding-lab.html` / `.mjs` と2骨6頂点の原本も独自作成。外部のモデル・モーション・画像・フォント・コード・図は追加しない。WebSDK配布物は前版のまま保ち、本体ライセンス未選定を維持する。

派生meshの原著図 `docs/learn/diagrams/derived-mesh.svg`: 1999B、SHA256 `ce131f7938bd08b44707558fe3295ecbc53f15299b9faa0258addc24950490c9`。原本保持・Float32量子化・区間面積/法線監査・全体成功bufferの概念図。教材25番も独自作成。測定やGPU描画の完成を表す図ではなく、外部モデル・図・画像・フォント・コードは追加しない。本体ライセンスは未選定。

派生mesh接続版の原本制作ラボ/教材24・25は原著のUI/本文を更新した。既存derived-mesh.svg（1999B、SHA256 ce131f7938bd08b44707558fe3295ecbc53f15299b9faa0258addc24950490c9）を継続使用する。新モデル/画像/フォント/外部素材はない。CPU監査用のJSON previewで、GPU表示の測定図ではない。

派生meshの任意3D表示（2026-11-04 JST、実装中・公開未検証）も既存の原著renderer/WGSLと原本制作ラボを更新する。小さい2骨6頂点の帯、固定cameraと色はプロジェクト内の合成設定で、外部モデル・モーション・画像・フォント・図を追加しない。教材25のderived-mesh.svgは上記1999B/SHA256のまま、局所CPU監査の概念図として継続使用する。3D表示の実測画像へ読み替えない。実ブラウザの検証画面は受入記録で別に扱う。本体ライセンス未選定を維持する。

手動3D表示90b1afeの最終照合: SDK65の53source/header・7通知・2artifactとmanifestはbyte不変。外部package/素材の追加なし。公開CI/Pagesと15操作/配信17ファイルを確認し、証拠はreports/2026-11-04-derived-render.md。本体ライセンス未選定を維持する。

Node段階計測の入力mesh/Source例、CLI、説明本文は原著。既存Sourceの帯と独自grid/既知法線を用い、外部モデル・画像・フォント・図は追加しない。既存性能教材の例示図を継続し、実測グラフやGPU測定図と読み替えない。新しい図・標準runtime配布物は追加せず、本体licenseは未選定。

ブラウザ計測（2026-11-04 JST、実装中）: 4面の原本帯、64個の非軸法線面、512面のdyadic shear gridとUIは原著の合成入力・実装。新しい原著概念図docs/learn/diagrams/derived-gpu-profile.svg（2924B、SHA256 10da7b048bd97869bdbd8eefd587c886b8faf3f0947a6fdc6ba77c1a8f5c9d50）は同期render・validation・queue待ちを区別する。幅は実測時間でなく、GPU測定画像や外部素材ではない。本体license未選定を維持する。

ブラウザ計測ebf5b5a/試験修正158f9f1の最終照合（2026-11-04 JST）: 修正CI/Pagesと公開80draw・配信15ファイルを確認し、SDK53source/header・7通知・2artifactはbyte不変。次の所有copy探索もNode/Python標準機能と原著recipeだけを使い、外部package/素材/サービスを追加せず、本番置換も採用しなかった。全raw・hashはreports/2026-11-04-derived-gpu.mdとderived-copy-archive.json。本体license未選定を維持する。


まとめ読出しの原著概念図 `docs/learn/diagrams/derived-readback.svg`（2026-11-04 JST）: 2711B、SHA256 `793c33a8ab3f45fa1905950bca90feb7a02e6d2eb151db7f6071fb0d013b67f3`。64個のF64出力内のheader4とpayload、同じ所有DTOと明示single/batch比較を独自のSVGコードで作図した。512頂点・512面のcall数と転送値数は交換形式から求めた例で、図の幅・配置は性能実測ではなく、時間短縮を保証しない。既存教材25番へ追加し記事件数は増やさない。API実装と統合/ブラウザ性能受入を区別し、ロボット適用の完成図とはしない。外部の図・モデル・画像・フォント・コードを導入せず、本体ライセンス未選定を維持する。

ブラウザsingle/batch比較（2026-11-04 JST、統合中・実ブラウザ受入/公開未確認）: 既存の原著4/64/512面の合成入力とラボを再利用し、読出し選択・記録・教材本文を原著で追加する。既存図 `docs/learn/diagrams/derived-readback.svg`（2711B、SHA256 `793c33a8ab3f45fa1905950bca90feb7a02e6d2eb151db7f6071fb0d013b67f3`）はbyte不変で再利用し、新図・外部モデル/画像/フォント/モーション素材は追加しない。教材記事数25を維持する。図の形式上のcall数を実測速度とせず、新schema2の比較rawと旧schema1の履歴を区別する。本体ライセンスは未選定。


## ロボット背面カバー（2026-11-04 JST、実装済み・統合受入中）

原著の専用Source `assets/robot-back-cover.skin.json`: 1759B、SHA256 `3be05db664848abb7806d906d8d36248668228ec3c9f1b5a2360c9483c0fd863`。6頂点・4面・2骨の浅いヒンジカバー、0..1秒/X軸+π/8のclip、全weight/rest/inverse bindはプロジェクト内の独自設計・既存C++による生成。既存arm帯や他作品のモデル/モーションを流用しない。

原著の専用authoring context `assets/robot-back-cover.scene.json`: 1243B、SHA256 `04ac3a5630f540692cab66c68082d38af45d92d00fffe74a07adb5ef6447a6d9`。同じrecipeで作った保存検査用contextであり、level colliderや外部の独立来歴証明ではない。generator `scripts/create-robot-back-cover.mjs` は原著で、既存原本の上書きを拒否し、SDK配布物を再生成しない。

新原著図 `docs/learn/diagrams/robot-back-cover.svg`: 3518B、SHA256 `93660a7c709b1da8b30f1503c7573b5adb2c2497b7208ef0db88a61de90c5096`。Source→実C++ FK/LBS/派生監査→所有token→全frame、120Hzと2tickの更新予定・旧世代退役を独自SVGコードで説明する。幅・間隔は性能実測でなく、実GPU画像・熱/損傷の結果でもない。既存教材25番へ追記し、旧SVGは変更しない。外部のモデル・モーション・画像・フォント・コード・デザインを取り込まず、本体ライセンス未選定と既存Emscripten配布通知を維持する。全npm/CI・実ブラウザ・公開受入とSDK/通知の最終byte照合は別の統合記録で確定する。


球と三角形の新原著概念図 `docs/learn/diagrams/sphere-triangle.svg`（2026-11-04 JST）: 3477B、SHA256 `aa9e209451f2b019fa184fbfebb153ab6e4c853f911c9c694ed802821f02c2fa`。球中心・最近接点・gapと、面/3辺/3頂点の全否定不能候補を囲む考え方を独自SVGコードで作図した。文献の図・code・本文・外部画像・フォントを取り込まない。2Dの長さ/配置は説明用で、実画面・誤差幅・性能測定や時間発展の図ではない。既存の区間記事へ追加して教材25記事を維持し、旧SVGは変更しない。Native-onlyの実装中で、SDK/ゲームmesh衝突・CCD等の完成とはしない。本体ライセンス未選定を維持する。


2026-11-04 JST 球×三角形のSDK接続: 既存原著概念図 docs/learn/diagrams/sphere-triangle.svg（3477B、SHA256 aa9e209451f2b019fa184fbfebb153ab6e4c853f911c9c694ed802821f02c2fa）をbyte不変で再利用し、区間記事へ共有SDKの使い方と失敗/所有の説明リンクを追加した。教材25記事を維持する。新モデル・図・外部画像/フォント/モーションは追加せず、全原本assetsは主SDKの3配布物以外byte不変。実行のraw JSON/UI画像は検証記録で、三角形衝突をゲームへ適用した結果や図の性能測定ではない。本体license未選定と既存7通知を保持する。


2026-11-04 JST 球×三角形の手動ラボ: tools/sphere-triangle-lab.html/.mjs の日本語UI、13プリセット（三角形A0/B4X/C4Zを基準）とSVG投影は原著。球中心・元の三角形と成功時のclosest区間を表示する。3px線幅は区間の視認性だけに使い、誤差幅や実物の太さではない。既存原著sphere-triangle.svg（3477B、aa9e209451f2b019fa184fbfebb153ab6e4c853f911c9c694ed802821f02c2fa）を区間教材でbyte不変のまま再利用し、25記事を維持する。外部画像/フォント/モデル/モーションを追加せず、本体license未選定を保持する。


2026-11-04 JST 球×静的三角形集合の原著概念図 `docs/learn/diagrams/sphere-triangle-mesh.svg`: 3808B、SHA256 `118da903bc8522203179b29125fbf6b11f640e0cb7fc13d8950bf825d019fb18`。各面の距離区間、最小値の包含、possible winners全保持・法線非平均を独自SVGコードで説明する。数値・幅・配置は説明用で、実GPU画面・誤差/性能の測定ではない。外部画像・フォント・文献の図/本文/codeを取り込まず、既存SVGを変更しない。区間記事内に追記し教材25記事を維持する。Native実装中・未検証、主SDK/World/ゲーム接触へ未接続。本体ライセンス未選定、既存7通知/artifactの最終照合は親の統合記録待ち。


2026-11-04 JST 球×静的三角形集合のローカル受入追記: 上記原著sphere-triangle-mesh.svgは3808B/SHA256 118da903bc8522203179b29125fbf6b11f640e0cb7fc13d8950bf825d019fb18のまま、図の幅・数値を実行/性能測定へ読み替えない。Native核/独立参照のローカル受入を文書と既存区間記事へ反映し、教材25記事・既存SVGを維持した。基準38b59f1からSDK55原本・7通知・2artifact・manifestと全assets/samplesのbyte不変を確認済み。新外部素材なし、本体ライセンス未選定、公開CI/Pagesは未確認。Native-onlyで主SDK/World/ゲームへ未接続の境界は変わらない。


2026-11-04 JST 球×三角形集合SDKの原著概念図 `docs/learn/diagrams/sphere-triangle-mesh-sdk.svg`: 3723B、SHA256 `d23cca6f0b24d5e479322f2cf50e7dca4d69d44ef3a20bb0584d6f82f7e2c8c6`。全入力所有copy→有界stage→実query→別所有snapshot、14/24/14/58/13の交換と、交換拒否/モデル失敗の違いを独自SVGコードで説明する。枠幅・配置・append件数は性能測定ではない。外部画像・フォント・文献の図/本文/codeを取り込まず、旧図・Source/assets/sampleは変更しない。区間記事内への追記で教材25記事を維持する。新主WASM/公開検証は未確定、本体license未選定を保持する。


2026-11-04 JST 球×三角形集合SDKのローカル受入追記: 原著sphere-triangle-mesh-sdk.svgは3723B / SHA256 d23cca6f0b24d5e479322f2cf50e7dca4d69d44ef3a20bb0584d6f82f7e2c8c6のまま。新74-export SDKの受入と、既存68-export受入を区別して文書/区間記事を更新し、教材25記事を維持した。基準207aa60から全authored assets/game Sourceと保護原本55＋既存通知7（合計62）のbyte不変を確認。SDK3artifact/生成HTMLは意図した変更で、linked標準algorithm.oの増加は依存台帳に記録する。ローカル実ゲーム3撃破/boost/停止・22照会成功/3常駐meshは旧機能互換の観測で、新集合mesh接触の適用や原著図の性能測定ではない。外部素材なし、本体license未選定、公開CI/Pages未確認。


2026-11-04 JST 球×三角形集合ラボの原著概念図 `docs/diagrams/sphere-triangle-mesh-lab.svg`: 3717B、SHA256 `0d96dc9427cd6061874a395155ae1c41d8a5999b41f706c809cbea61829c6b62`。全source一覧、実row診断、失敗集合のnearest不在、閲覧面の個別geometry/候補、未照会とJSON保存を独自SVGコードで説明する。IDや配置・幅は説明用で、実画面・誤差/性能の測定ではない。外部画像・フォント・文献の図/本文/code・モデルを取り込まず、旧SVGとSource/assets/sampleを変更しない。既存区間記事への最小追記で教材25記事を維持し、本体ライセンス未選定を保持する。操作・保存・公開検証はpending。

2026-11-04 JST 集合手動ラボのローカル受入追記: 原著UI/図/17合成入力、専用18/全Node544・34CTest、実ブラウザ17例と実Blob2保存、42644数値bits/独立追加4578成分を確認。C++/SDK57原本/7通知/2artifact・全assets/sample原本不変を照合した。外部依存/資料転載/素材/有料serviceを追加しない。公開受入は別途確認待ち。根拠は reports/2026-11-04-sphere-triangle-mesh-lab.md と対応JSON。

2026-11-04 JST 集合手動ラボの公開受入追記: コード203c11aのLinux CI/Pages全工程成功、Node544/34CTest、新規warning0（既存36診断保持）、42公開ファイルbyte一致。実公開17例/実Blob2保存/42644数値bitsと独立追加4578成分を確認。先行の実装中記録に対する受入更新であり、新たな外部資料・依存・素材・ライセンス選定はない。詳細は reports/sphere-triangle-mesh-lab-public-verification.json。World/一般CCD/game mesh応答の完成ではない。


2026-11-04 JST 定義線分軌道guardの原著概念図 `docs/learn/diagrams/sphere-triangle-mesh-trajectory.svg`: 4542B、SHA256 `57a5c73fc63e8505d81967aab158361bac9daccf81bc1bc63cc0a4d1f598f656`。定義pathと任意binary64 anchor、cell上界R/中点誤差E、strict非接触/点貫通witness/未認証、全closed leaf被覆と左prefix、sqrt事前予約/実work/例外時certaintyを独自SVGコードで説明する。長さ・配置・葉数は説明用で、実行結果・誤差/性能測定・TOI/World/応答の完成図ではない。外部画像・フォント・モデル・文献の図/本文/codeを取り込まず、旧SVGとassets/sample Sourceを変更しない。既存区間記事への追記で教材25記事を維持し、本体license未選定を保持する。Native数値・統合受入はpending。

2026-11-04 JST 定義線分軌道guardのローカル受入追記: Native69群/62入力、全35CTestと最終test-only拡張後専用1CTest、Node544skip0、独立48全path/4witness/297leaf/606audit・解析14/改ざん71を確認。保護98原本/SDK57source74exports/WASM638777B/7通知・既存assets/sampleはbyte不変。原著図と教材25記事を維持し、新しい外部資料/実装/依存/素材/有料serviceは追加しない。初回の回帰anchor想定誤りはrawと共に保持し訂正再実行、例外fault injectionやWorld/TOI/応答完成とはしない。公開CI/sanitizerは確認待ち。詳細は reports/2026-11-04-sphere-triangle-mesh-trajectory.md。

2026-11-04: 定義線分guardへ独立C ABI stage/recordと6exportsを追加し、共通WASMを再build。実80exports/59source-header、WASM674978B/glue56289B。既設pinned runtime linkedLibraryMembersは増減0、7通知hash不変、新package/外部数学・物理実装/素材/ライセンス選定なし。Native25交換群・36CTest、62入力の59model/3hostと全wire/19改ざん拒否、実WASM70278数値bits/2398負零照合をローカル確認。原著交換SVGとガイドSPHERE_TRIANGLE_MESH_TRAJECTORY_ABI.mdを追加。元の62 pure入力への独立有理数参照と、交換59modelの全DTO bit一致をscope分離し、host3をモデル実行と呼ばない。公開CI/Pagesは次に確認、所有JS wrapper/UI/World/TOI/応答は未接続。


2026-11-04 JST 定義線分guardの所有JS API概念図 `docs/learn/diagrams/sphere-triangle-mesh-trajectory-owned.svg`: 3577B、SHA256 `60fa469c543d91390959dff658cdccaf9988df170cb1b6b3495266ac26692035`。原入力一度copy→共有出力をgetterごとにcopy/監査→別所有DTO、originalInputとNative snapshotの別所有、失敗・未照会保持とdecode拒否の境界を独自SVGコードで示す。長さ・配置は実測や数値包含の証明ではなく、JS metadata監査を数学solverにしない。既存図/ゲームSource・外部画像/モデル/フォント/文献の図・本文・実装を流用せず、本体license未選定を維持する。今回C++/WASM/native原本・既存依存/通知を変更しない。owned59モデル＋明示pure補足host3の数学受入と、図/UI/公開操作の受入を分け、既存教材25記事を維持する。
