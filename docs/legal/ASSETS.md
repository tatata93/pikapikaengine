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
| `assets/pikapika-simulation.wasm` / `.mjs` | 自作C++物理・光学とEmscripten 6.0.13標準ランタイム・生成glue | 2026-11-03 | 独自コードと第三者ランタイムを含む。第三者の通知はthird_party/emscripten-6.0.13、エンジン本体のライセンスは未選定 | 今回の最近傍光学版はWASM447783B、glue44500B、48 exports。原本/生成物/通知のSHA256は同名build.json、統合結果はreports/supported-world-verification.json |
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
