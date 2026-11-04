# 現在地と再開位置

更新: 2026-11-04。製品仕様は `PROJECT_SPEC.md`。この記録は実装した範囲と未完を区別する。ユーザーは節目でのGitHubプッシュ・起動リンク・継続開発を明示的に指示している。

再開位置: Native sphere×static mesh entry windowを実装し、76群/65入力・独立Fraction558葉1452audit/90負例・37CTest/586Nodeをローカル受入済み。コード058a919の公開GNU CI/Pages全工程を受入済み。新核ASan/UBSan76群・通常/検査fixture byte一致・既存36warning multiset不変、73ファイルbyte一致を確認。現在の主SDKはentry未接続の80exports/59source-header/WASM674978B、既存Web d70b5d9b4436650fを維持する。次に[entryの有界SDK設計](SPHERE_TRIANGLE_MESH_ENTRY_SDK_PLAN.md)に従って独立C ABI/Native probeから実装する。詳細は[entry検証記録](../reports/2026-11-04-sphere-triangle-mesh-entry.md)。World/CCD/manifold、ゲームmesh接触、摩擦支持/関節、流体/損傷、専門車両/航空/鉄道、IK/制御と高精度光学撮像は引き続き未完。

以下は各段階の履歴。現在の再開位置は冒頭と末尾の追記を優先する。

公開済みmotion制作コードeffe123はLinux CI/Pagesと15観測・配信7ファイルbyte一致を確認済み。公開入口 https://tatata93.github.io/pikapikaengine/tools/motion-lab.html?v=effe123 。主ABI59、WASM544541B、Web build4160515ffa5ab2d4/35modulesを保持。新しい原著教材は23記事。FKとキー/原本往復の記録はreports/2026-11-03-motion.md。

新入口 tools/motion-lab.html は4ボーンのオリジナルarmをキー編集し、全local/world行列を返す。非一様scaleのshearを保持する。回転は最短NLERPで、SLERPの定速回転、glTF入出力、skinning/ゲーム描画、IK・関節・物理制御の完成ではない。既存IRON FIELDと他チャットのsample原本は変更しない。

docs/SKINNING_SDK_PLAN.mdの有界照会を実装した。actual上限128bone/2048vertex/8192influenceとNative Settings上限128/65536/262144を区別し、全入力検査・失敗時record/output保持・reset/復帰を確認済み。次の最小受入案は[SKIN_BINDING_PLAN.md](SKIN_BINDING_PLAN.md)。既存sceneを変えず、sidecarが全mesh/weight/joint/motion原本を所有する2048頂点/8192 influenceの共通subsetとJSON/portable/Native CLI往復を計画する。全形状の値と観測可能な配列順を照合し、hashだけで一致としない。同内容の重複頂点の概念的入替や履歴は検出不能で、persistent vertex IDは別versionの残件。確認用ラボJSON出力を原本保存読込の完成と扱わない。その後に法線/Float32/ゲーム描画とoriginal robot sample更新へ進む。

制御/IKより先に描画・原本往復の前提を固める。光学の照度bin/連続source測度・全ghost/自己根/媒質証明・干渉/回折/描画接続、および一般接触/摩擦・車両航空鉄道・流体/材料損傷は未完として継続する。

## 実行できる入口

- 公開ブラウザ: https://tatata93.github.io/pikapikaengine/ （Pages設定済み。公開応答・起動の最新結果はreports参照）
- ローカル: `npm start` → http://localhost:8080
- 教材: `docs/learn/index.html` / `flame.html`
- Windows: `./scripts/build-native.ps1` → `build/native/Release/pikapika-viewer.exe`
- CLI: `build/native/Release/pikapika.exe help`

## 最初の受入項目

| 段階/仕様 | 現在の実体 | 検証と残り |
|---|---|---|
| M0 ビルド・方針・資料 | CMake/Node入口、原仕様、ADR、依存/素材/出典台帳 | ローカルビルド実行済み。OSSライセンス未選定、配布バイナリのランタイム同梱監査が残る |
| M1 数学・時間 | C++ Vec3/Quaternion/Transform/FixedClock、JS math/time | Native core15検証群。JS描画30/60/120/144周期比較、リプレイ一致 |
| M1 シーン | C++版付きテキスト、Web原本JSON、camera/source/listener、共通形式アダプタ、編集API | 生成→変更→保存→再読込、Web原本→native CLI変更→Web再読込。ID/位置/色保持を実行確認。原本シーンのWeb回転はYのみ。動的表示はquaternionを追加 |
| M1 描画・入力 | Windows DirectX12 + 自作WebGPU/WGSL、手続き床・箱・ロボット | DX12実GPU120フレームとGPU読戻し画像。IABでWebGPU起動・移動・射撃・停止を確認。視覚/操作の網羅試験は未完 |
| M1 固定運動 | 120Hz、補間、軸別箱接触、球/箱の連続衝突 | 高速すり抜け、周期差テスト。ブーストはゲーム用制御。汎用剛体ではない |
| M1 音響 | 自作PCMインパルスWAV、d/c遅延と1/r振幅、Web操作後の発音 | 遅延・分数サンプル・倍距離-6.0206dB・WAVテスト。聴感未確認、移動経路の継続更新未実装 |
| M1 CLI | init/inspect/move/roundtrip/audio/audio-scene/simulate | 実行済み。GUIとCLIが全く同じ内部コードである段階には未到達 |
| M1 Native/WASM | 共通物理・光学・motion・位置skinning ABI63関数。既存650B freestanding核も保持 | 整列修正の主WASM574261B/glue49388B。Native28CTest/652群、Node323/323・skip0がローカル成功。修正版公開CI/Pagesは最終確認待ち。ゲーム全ロジック共通化はM2残件 |
| M1 性能 | Web生ログJSON、Native生CSV・p50/p95/p99/最大/超過 | Native loop p95 17.9802ms、p99 18.8144ms、max29.1888ms、63/120超過。60fps目標未達。GPU/実提示未測定 |
| M1 教材 | 原著図解23記事と検索、有限光束レンズの手動オフラインラボ | 非共面反射/全反射/法線透過、未知と未実行の区別、prefix閲覧、入力エラー消去・予算不足・再読込復帰を実公開で確認。教材/ラボは物理モデルの適用範囲を表示 |
| サンプル初版 | オリジナルIRON FIELD、移動/ブースト/上昇/ロック射撃/敵/3波/勝敗/再出撃 | 純粋シミュレーションとブラウザ実操作を確認。Native版の戦闘未実装 |
| M2 制作A初段 | 原本三角形メッシュ・単一頂点編集・Undo/Redo・v2 JSON/共通形式、WebGPU/DX12実形状描画 | GUIで頂点移動→Undo/Redo、CLIの作成→編集→保存→Native読込を実行。衝突AABB再生成を試験。面編集/押出し/UV/地形/音響形状伝搬は未実装 |
| M2 制作B初段 | 親木/局所TRS・秒キー・最短NLERP/step・FK行列、Web編集/Undo/Redo/JSON、Native portable v1/CLI | motion原本往復・既知2リンク・shear・30/60/120同時刻・同時上限128/128/4096を確認。GPU/ゲーム描画接続、IK/制御/物理関節は後続 |
| M2 制作B位置変形 | 原著rest inverse/affine matrix LBSと共通SDK4関数、2骨のCanvas XY/XZ実操作ラボ | actual128骨/2048頂点/8192 influence、上限超過拒否、失敗時保持/コピー/reset、65fixture分類と128oracleを確認。binding原本codec/CLI、法線/Float32/ゲーム描画は次段 |
| 物理C1初段 | 既存6自由度/W1/read-only支持に、摩擦0の球proxy/静的平面を進めるW2を追加。RATTLE・有限vn支持選別・衝撃・離脱と全区間幾何監査 | 新核はRATTLE17/guard24/driver13/private policy8群、ABI追加3群。Native総計361群・CTest20/20がローカル成功。曲率球対・非直交共有bodyも対象。一般形状・摩擦支持・関節・車両/ゲーム接続は未完 |
| 任意光学の継続基盤 | 全区間の幾何/phase index/指定route、有限点像と世界coherencyによるPOWER輸送 | 単一nearestと指定routeは未連成。source/sensor測度、全ghost列挙、媒質配置/自動継続、撮像/収差画像、経路間干渉・回折とゲーム描画接続は未完 |
| 流体F1初段 | JS/C++閉メッシュの静水圧・排水体積/浮心・浮力/復原トルク、無接触1体のNative中点結合、JS係数抗力 | JS14解析試験・Native20検証群、両言語12形状153値比較。釣合い・既知上下振動・偏心復原・100秒誤差。非定常流/CFD/一般接触結合/弾塑性破壊は未実装 |

## 次の最小マイルストーン

追加要求（2026-11-03）: 空気・水の流体を使う航空/潜水艦等のシミュレーター、衝突の残留へこみと被弾による装甲の材料損傷。正式な受入項目は `PHYSICS_SCOPE.md`。通常の追加は適切な依存順で取り込み、「今やれ」「至急」の指定は優先変更として扱う。現在のM2制作Aは変形形状の原本・描画・派生データの前提なので継続する。

1. 現行W2はコードb0a7a6aで公開検証済み。有限刻みモデルと残差・失敗時保持を明示する。続いて摩擦支持/一般形状・関節と、明示面列を超えたレンズ形状/媒質・遮蔽・経路の選択へ進む。M2制作Aの面編集/モーションと各専門物理の未完項目も維持する。製品全体の完成、全作品60fps達成、音の聴感確認と混同しない。
2. 初回Web30秒試験を reports/webgpu-benchmark.json に保存。1800フレーム、p95=16.755ms、p99=16.785ms、max=17.465ms、厳密予算超過1193件。GPU/実提示未計測で合格にしない。初回の負の開始間隔を含む試験も別ログに保持。今後はGPUタイムスタンプと実提示・音声負荷を含め、Native超過の原因を分解する。
3. Native剛体/静水圧の無接触1体を共通WASMへ出力し、上下動/復原、一定速度TOI、加速軌道とW1の順に実装した。過去の生ログ・誤差・配布条件は`reports/2026-11-03-wasm-simulation.md`、`reports/2026-11-03-continuous.md`、`reports/2026-11-03-lens-world.md`を参照。今回のW2は独立した有限刻みdriverとして切替/残時間/粗細差と定義軌道の幾何を検査する。公開read-only支持照会へ状態更新を追加したものではなく、厳密連続解や一般接触の完成とも区別する。一般形状、ゲームや箱形状への接続も残る。
4. M2制作B: 少数ボーン/キーの原本・時間サンプリング・保存を作り、30/60/120描画で同じ姿勢/イベントを検証する。FK/IKと制御グラフの候補は `CONTROL_DESIGN.md`、任意の高精度レンズ計算は `OPTICS_SCOPE.md` に受入を保持する。
5. サンプルは上記エンジン機能を使って更新。別チャット由来の変更があれば先に確認・統合する。

### これまでの独立核と公開検証（過去の再開記録）

物理の後続基盤: 荷重を保持する候補の自由伝播と時刻固定接触を内部分離し、既存Worldの公開挙動を維持した。8ケース27,224値の保存baselineと統合ReleaseのJSONがバイト一致。独自区間演算はNative18群・standalone実WASM17群、両対象各6,829区間の厳密有理数包含・13,658端点bit一致を確認。統合CTest7/7・114群、Node89/89・skip0。主WASMは184044Bへ再生成、30336値比較成功。reports/2026-11-03-interval-foundation.md。次は二次/四次の加速軌道の保守的な照会と根の存在確認であり、World CCD完成ではない。

その後、一定加速度の球対/静的平面照会と単一光学界面を実装し、共通WASM32関数へ接続した。
Native CTest9/9・154群、Node114/114・skip0、Native/WASM30697値比較、主光学ABI1029入力の分類/4116端点bit一致が成功。
加速/光学の操作ラボと図解10項目を追加。reports/2026-11-03-optics-accelerated.md。
次はWorldへ時間幅を空間誤差へ換算した接触応答・残時間・持続支持を統合する。光学はレンズ面交差・複数面・反射光路・分散と偏光輸送へ進む。
現段階の光学をレンズの収差/ゴースト/フレアや描画接続の完成とはしない。

今回、held荷重下のW1 World CCD、平面/球/球面capと開口の幾何、Stokes基底と複素反射位相の偏光輸送を主WASM36関数へ統合した。
Native CTest12/12・212群、Node144/144・skip0、面交差200例/330根のFraction確認と主ABI2400端点bit一致、W1完全入力fixture41値のNative/WASM比較が成功。
W1の独立corridorでは空間guard縮小により最終X誤差約21µm→0.48µm→5nmへ減少した。有限集合の観測であり普遍的精度保証ではない。
両ラボの実ブラウザで根選別/距離換算/未確定、3衝撃/rollback/同じWorldでの再実行を確認。reports/2026-11-03-lens-world.md。
次はW2持続支持と、交点/法線の不確かさを引き継ぐ複数レンズ面の光路へ進む。波長分散・収差・ゴースト・フレアの描画や一般材料損傷は残る。

## 残っている製品目標

M2: 同一ゲームロジックをWindows/Webへ出力、共通アセット・入力・音声、モデリングとモーション、許諾済みglTF導入。M3: 基礎光学の参照比較、影、反射・残響、視認性、性能。M4: 権威サーバー・PC/Web通信、予測と補正、精密シミュレーション拡張。M5: 高度光学・音響・気象・大世界。M6: 同じ編集APIを使う人間向けGUI。各分野の詳細要件は原仕様に保持し、この短い記録で削除したことにしない。

## 継続時の注意

30分heartbeatがこのチャットに設定済み。これは実行環境が利用可能なときの再開であり、無停止の無期限稼働を保証しない。能動goalも継続中。進捗がない同じ通知を繰り返さない。課金・有料契約・フォーラム投稿・メール操作は禁止。公開repoの標準GitHubホストrunnerのみ利用し、追加artifact/cache保存や課金設定は作らない。

初回push: `358870e`。それ以降のコード版はgit logで確認。実績に先行して完了チェックを付けない。

以下の版番号付き追記は過去の節目ログ。「次は」の記述は当時の再開位置であり、最新の再開位置は冒頭と末尾を優先する。

現在の動作確認済み公開版: https://tatata93.github.io/pikapikaengine/?v=1ab868a 、浮力ラボ https://tatata93.github.io/pikapikaengine/docs/learn/buoyancy.html?v=1ab868a 。コード1ab868aの公開CI（JS/Native/WASM/parity）・Pages成功、公開WebGPU READYとラボの釣合い操作を確認。前節3d463d7では公開メッシュ編集を実行（reports/m2-public-mesh-edit.png）。最新記録は reports/2026-11-03-buoyancy.md。共通C++のWeb出力に向けた次の受入・調査は WASM_DYNAMICS_PLAN.md。起動リンクに版queryを付け、PagesのHTML/ESMキャッシュを区別する。前版9064a2fのNative arena性能はp95 26.9045ms、p99 53.9267ms、max75.2425ms（reports/native-arena*）、M2のWeb/Native測定は reports/2026-11-03-m2.md。60fps未達と遅延原因の調査は残る。

追記: 最新コードfe3a9f3の公開CI・Pagesが成功。動的実験 https://tatata93.github.io/pikapikaengine/tools/float-lab.html?v=fe3a9f3 を公開ブラウザで起動し、1tick、再生/停止、39.283s/4714tickの進行を確認。build 8277480dc456d30f。Linux GNU13.3.0/Node22.23.4でもWASM30180値の比較が成功。CIのJSは74成功/Native CLI依存3skip、Windowsローカルは77成功。reports/2026-11-03-wasm-simulation.md が最新。次項の一定速度球/平面・球同士の接触時刻核に着手中。一般WorldのCCD受入完了ではない。

追記: コード1ebcfc5の公開CI・Pagesが成功。接触時刻ラボ https://tatata93.github.io/pikapikaengine/tools/contact-lab.html?v=1ebcfc5 を公開ブラウザで操作し、実WASMによる高速球2ms・接線3ms・移動平面4msを確認。build 178d4cd2a8d0d543。Linux GNU13.3.0/Node22.23.4でCTest5/5、Node89/89・skip0、Native/WASM30336値の最大絶対差0（この実行の結果）。生ログと公開画面は reports/2026-11-03-continuous.md。次は荷重を保持する区間伝播と時刻固定接触の内部分離、および加速軌道を安全に調べる区間演算。World全体のCCD、任意選択の厳密なレンズ光学は未実装。

追記: コード41b7564の公開Linux CIが成功し、CTest7/7・厳密有理数6,829区間・Node89/89/skip0を確認。原本のバイト保持を修正したa17e11aのPages配信も成功。https://tatata93.github.io/pikapikaengine/tools/contact-lab.html?v=a17e11a を公開IABで起動、184044B/build9057db191e652b4aの実WASMを確認。reports/2026-11-03-interval-foundation.md が最新。次は一定加速度の保守的な照会と、光学の単一界面Snell/Fresnel参照核に着手中。これらは次の未完マイルストーン。

追記: コード180c68eのLinux CIとPagesが成功。CTest9/9・Node114/114/skip0、光学1029例の分類/4116区間端点bit一致、Native/WASM30697値の最大絶対差3.3306690738754696e−16を確認。この実行の観測値であり一様精度保証ではない。公開光学ラボ https://tatata93.github.io/pikapikaengine/tools/optics-lab.html?v=180c68e と加速ラボ https://tatata93.github.io/pikapikaengine/tools/accelerated-lab.html?v=180c68e で216160B/build4094312d5095c3ddの実WASM操作を確認。reports/2026-11-03-optics-accelerated.md にログ抜粋・入力結果・公開画面を保持。次の実装は曲面/平面と開口の光学交差、held荷重下のtransactional World CCD。単一界面の成功を多面レンズや持続接触の完成と混同しない。

追記: コード0c9d26fのLinux CIとPagesが成功。GNU13.3.0/Node22.23.4でCTest12/12、Node144/144/skip0、光学4116/面交差2400端点bit一致とW1の41値比較（最大差0）を確認。公開レンズ面 https://tatata93.github.io/pikapikaengine/tools/lens-surface-lab.html?v=0c9d26f とWorld https://tatata93.github.io/pikapikaengine/tools/continuous-world-lab.html?v=0c9d26f の実ブラウザ操作も成功。288519B/build873219b2bdcf8530。reports/2026-11-03-lens-world.md に公開入力/画面/ログ抜粋を保持。次はW2支持の独立力モデルと、包含を持つ光路の複数面への継続を進める。

波長分散の独立核を共通37関数ABIへ接続。Cauchy/Sellmeierの全波長帯についてn/dn/dλ/ngを囲み、有効帯・特異点・正値・幅/予算を検証する。
Native14群・standalone実WASM14群、320例（連続帯160）の独立Fraction960区間と主ABI1920端点bit一致、全Native227群/CTest13/13・Node153試験を確認。
合成係数の操作ラボと図解14項目を追加。reports/2026-11-03-dispersion.md。次は交点/法線区間を維持する光路核と、read-only normal支持核の統合レビュー。
分散の数値包含を、実ガラスの校正・複数面の色収差画像・フレア/ゴースト描画の完成とはしない。

追記: コード8e7ee42のLinux CI/Pages成功。CTest13/13、Node153/153/skip0、分散Fraction320例/960区間と主ABI1920端点bit一致。公開 https://tatata93.github.io/pikapikaengine/tools/dispersion-lab.html?v=8e7ee42 で298291B/build bbc6487a7ebb83f9、両モデル・予算1・極の未解決と復帰を実操作した。reports/2026-11-03-dispersion.md に生証拠。次は区間光学の継続とread-only支持をレビューして共通APIへ統合する。

## 直前公開: 区間光路と法線支持照会

[OPTICAL_BOUNDS.md](OPTICAL_BOUNDS.md)の20群は、原点/方向/法線と独立ni/nt区間を全幅保持する。
旧302族・1880区間に加え111指数族・1110区間を独立Fraction/代数平方根で確認し、
Native/standalone実WASMの出力端点3760+2220bitが一致した。有限corpusの証拠であり、任意入力のビット一致や現実の測定誤差までは保証しない。

[OPTICAL_ROUTE.md](OPTICAL_ROUTE.md)の23群は、指定したsurface/branch列だけを継続する。
主光路・内部二回反射の解析例、球/cap、点波長の分散phase全幅、t=0、失敗prefixと予算を扱う。
OPLは位相指数のΣn dsで、群遅延ではない。s/pのmin/max包絡を掛け、各面で無偏光にリセットしない。
任意のレンズ系の経路探索、校正済み撮像、色収差・ghost/flare画像、回折や光路間干渉は後続である。
[操作ラボ](../tools/optical-route-lab.html)は二球面capと合成分散も調べるが、レンズ設計全体の検証とは区別する。

[SUPPORT.md](SUPPORT.md)の21群は、現在姿勢の球proxy/静的平面に対するnormal-onlyの加速度LCP。
全gap包含が明示band内にある近似境界を使い、正gapも隠さない。微小でも確定した接近は衝撃要求、離反はlambda0。
曲率、保持荷重、悪条件・残差・予算を検査し、World・荷重・clockを書き換えずsnapshotを返す。
[支持ラボ](../tools/support-lab.html)はこの照会であり、摩擦支持やstackの時間発展を完成扱いにしない。

ローカル統合で確認: 44 exports / WASM361007B / glue43071B、Native296群・CTest16、Node175、教材16記事。
実行結果・配布物hashはreports/route-support-verification.json、公開結果はreports/route-support-public-verification.json。
追加SVG2枚のサイズ/hashは [素材台帳](legal/ASSETS.md)、PBRT/CMUの実読範囲は [参考記録](legal/REFERENCES.md)。

追記: コードc262c0cのLinux CI/Pagesが成功。GNU13.3.0/Node22.23.4、CTest16/16・Node175/175/skip0。支持689値/光路1560値最大差0、区間幾何/指数5980端点bit一致。公開IABで361007B/build4e0d00dbdb939b92、光路6条件と支持7条件、失敗後復帰を確認。reports/2026-11-03-route-support.md。次は支持を保つ時間積分と離脱/再接触の整合へ進む。


## 現行公開: W2支持・離脱・衝撃と候補軌道監査

[CONSTRAINED.md](CONSTRAINED.md)は明示active集合の法線RATTLE候補を返す。
位置段はJ1 M^-1 J0^Tの非対称Newton系、速度段は終端法線で連成し、両stageと元の離散式の残差を監査する。
負のstage係数をclampせずrelease_requiredとする。固定集合の滑らかな系の二次収束を、接触切替を含むdriver全体の精度保証へ拡張しない。

[TRAJECTORY_GUARD.md](TRAJECTORY_GUARD.md)はq(s)=q0+h v0 s+(q1-q0-h v0)s²の全s∈[0,1]を監査する。
相対始終位置を先に差し引き、球対の四次式と座標boxの包含を交差する。sqrt精度仮定や終点だけの合格はない。
Native24/standalone実WASM23群（Nativeだけ丸めmode変更拒否を追加）、Fraction640例、320負witnessの包含、Native/WASM元入力/出力bits一致を確認した。
これは定義した離散経路の幾何証明で、真の連続拘束運動の包含ではない。

[SUPPORTED_WORLD.md](SUPPORTED_WORLD.md)は保持荷重下の全tickをtransactionalに進める。
既存公開support::solveのstrict zero/微小接近policyは変更せず、private有限vn LCPで支持候補を選び、負の行を一度に全削除せず一行ずつ外して必要な行を再追加する。
A=[[1,-.8],[-.8,1]], b=(-7,9.2)の反例で、bilateral(-1,-10)から正しい片側解(7,0)を落とさないことを受入に含める。
tick末尾の衝撃も処理した右連続snapshotを返す。cold input以外の小さい負速度の修復には小さな物理的新接触も含み得るため、丸め起因と断定しない。
held_force_workは保持並進力の仕事だけで、torque仕事は含めない。静的collider同士だけは明示除外し、動的bodyの全pairを監査する。

[手動Worldラボ](../tools/supported-world-lab.html)は床・stack・非直交面・再接触・支持中衝突・高速球・曲率球対の7例を同じC++で操作する。
各120Hz tick前に保持荷重を置換再設定し、成功後の一度消費と、失敗前後の全body/荷重/info/clock一致を確認する。
1/12/96tick操作、4tick毎の描画yield、実時間同期なし/dropped0、完全入力・設定と前後状態のJSONを備える。

最終ローカル集計は46 exports、Native361群・CTest20/20（既存296+RATTLE17+guard24+driver13+ABI追加3+private policy8）、
Node193/193・skip0（175+lab14+API4）、教材17記事。全ローカルリンクも照合した。
最終主WASM430397B/glue43782B、Web build `4ba0bda196575a16`。
WASM SHA-256は `40bf870a6c423c50b773293a394121b81f8d50cd22bfde69fd9aaa0bc4d53659`。
コードb0a7a6aのLinux CI/Pagesと公開ラボ9条件が成功。reports/2026-11-03-supported-world.mdに全証拠。次の最小受入は、静的複数面の全競合を排除できる場合だけ共通の最近傍IDを返す光学照会。遮蔽・自己交差・媒質整合と撮像は段階を分け、uncertainを捨ててnearestとしない。
外部solver/依存/素材の追加、ライセンス選定は行わない。一般形状・摩擦・関節・長時間大規模性能、流体/弾塑性連成と専門車両の未完は維持する。

## 最新: 静的複数面の最近傍

閉parameter領域で全競合を調べ、primitive hitが一意に最初と証明できたときだけ選ぶ。共有rayとの相関喪失や接線/開口の未確定を捨てず、後方の不確定は閉prefix missでのみ排除する。全数値根拠はreports/2026-11-03-optical-selection.md。コード9c3387eの公開CI/Pagesと13操作が成功。次は媒質境界の整合と、レンズの点像・収差の参照計算を制作/描画の経路へ結び付ける。一般接触・摩擦支持・流体/損傷・共有ゲームコード・M2制作の残件も維持する。


追記: 指定routeに沿う有限rayのsensor幾何投影と重み付きcentroid/MSR²を追加。全区間をC++へ維持し、未知/未実行があると最終統計を返さない。profileの有限物点/平行光、等面積瞳、点波長の全phase区間、保存読込と明示オフライン実行を接続。1024点の既定総予算は不足し得ることを実測し、予算失敗を成功扱いしない。放射画像/回折PSF/全ghostと60fpsゲーム描画への接続は残る。

次のM2制作Bの最小受入: 安定IDの親木/循環と欠損の拒否、少数リンクの既知FK、局所TRSと親合成（非一様scaleのshearを失わないmatrix結果）、秒単位のtranslation/rotationキー、境界/loop/静止姿勢、保存→再読込でID/キー保持。30/60/120描画時刻で同じ秒の姿勢を返すことを確認する。イベント・IK・力学制御・skinning/描画接続の完成とは分ける。


追記: M2制作Bコードeffe123の公開CI/Pages/15観測が成功。FKとキー・原本保存の次は、docs/SKINNING_PLAN.mdに沿ってpure C++のrest inverse bindと1..4骨の頂点変形に着手した。新kernelの検証・統合は未完で、現在の公開SDK59へ含めたとはしない。


追記: pure位置skinningのローカル68群/独立Fraction/実WASM比較を完了。巨大translationの先行頂点変換で失った値はmatrix先blendへ改め、既知x1の回帰で誤差0を確認。これは任意相殺の精度保証ではない。次は共通SDK/原本binding/描画への接続で、現在の公開SDK59やsampleが変形メッシュを描くとはしない。


追記: 位置skinningコード1099240/配布整理ae6b707のLinux CI/Pages、23番教材とSVG/配信5ファイルを検証済み。次は4export候補・2048vertexの有界共通SDK照会と、原本binding/CLI保存往復へ進む。Native65536vertexや描画済み機能と同一視しない。

追記: 上の次段だった有界SDK4関数とtools/skinning-lab.htmlを実装。63exports/583708B WASMのNative651群/28CTest・Node322/322がローカル成功。60実C++モデル結果と5host交換拒否を分け、128oracle/retryを含む5288数値bits一致、既存Fractionの304+4480点を再確認した。コード051c2a9のLinux CI/Pages・公開13操作も成功。次はcompiler境界警告の調査とbinding原本codec/Native CLI往復で、ラボの確認用JSON出力や位置だけのCanvas表示をその完成と扱わない。

追記: 最大4 influenceの整列をbounded insertionへ変更し、Native69群/全652群・CTest28、Node323skip0、33順列、main5288bitsと旧24回帰をローカル検証。ASan旧/新69群とheap-overflow positive controlも観測記録を保持した。SDK574261B/glue49388B/63exports、Web387edd206ca3270e/36modules。修正版の公開Linux CI/Pages確認後、提案・未実装のdocs/SKIN_BINDING_PLAN.mdへ進む。次のsourceは全mesh/weight/joint/motionを持つsidecarで、signed zero保存とstrict parser方式を実装前に固定する。

追記: owned skin binding原本を実装し、JSON/portable/Native CLI保存往復とブラウザ編集をローカル検証した。Native679群/CTest29、Node355skip0、8原本26322bits/30モデル結果650bits一致。内訳20completed/5numerical_failure/5ill_conditionedと10source品質例外を分離し、独立Fraction288成分・23負例も確認。SDK63/WASM574261Bはbyte不変、Web51c633e84fbbf290/39modules。公開CI/Pagesはreports/2026-11-03-skin-binding.mdで確定する。次は原本を保持した派生meshのFloat32/面退化/法線検査と3D描画を最小単位に進め、robot sampleへ段階的に適用する。一般接触・車両/航空/鉄道・流体/損傷・IK/制御・高精度撮像の残件は維持する。

追記: bindingコード4356c8aのLinux CI/Pagesが成功。GNU13.3/Node22.23.4でCTest29/Node355skip0、新IO ASan/UBSan27群、独立288成分/23負例を確認。公開ラボ18操作の全packetがローカル一致、配信11ファイルbyte一致。reports/2026-11-03-skin-binding.mdに全証拠を保存。IOに2件のmisleading-indentation warningが残るため先に整理し、その後派生meshの検査・法線・3D表示を進める。

追記: IO warning修正3a47142の公開CI/Pages成功。対象2warningは0、既存36warningは保持。Node355skip0/CTest29/IO sanitizer27群。次はdocs/DERIVED_MESH_PLAN.mdのNative純粋核を実装する。現行Web/SDKは変更せず、原本と派生bufferを分離したままFloat32位置・面積包含・法線誤差監査を小単位で受け入れる。

追記: Native派生meshの純粋核を実装・ローカル受入。全733群/CTest30、新54群とASan54群、Node355skip0、40固定入力/独立36負例、同時65536頂点・131072面を確認。最大容量prepareの単発Native約31秒で、実時間描画の性能達成ではない。面積/法線はstrict環境下の局所Float32について監査する。SDK/Web runtime/source/sampleは不変。reports/2026-11-03-derived-mesh.mdへ証拠を保存し、公開CI/Pagesを確認してから有界SDK接続と実LBS照会へ進む。

追記: 派生mesh修正a67b0abのLinux CI/Pages成功。GNU13.3/Node22.23.4でCTest30/Node355skip0、新kernelASan/UBSan54群と独立36負例を確認。最初のCI出力先guard停止は記録を保持しconfigだけ訂正した。公開教材25項目/SVG/配信7ファイルを確認。次のdocs/DERIVED_MESH_SDK_PLAN.mdは未実装の接続案で、既存容量内の2048頂点/32768面・2exportsと実LBS→derived通し照会を進める。Native局所の認証をGPU/ゲーム描画や一般物理の完成へ広げない。


追記: 有界派生meshの2exportsとJS copied snapshot、原本ラボの手動監査、実Source→LBS→derived Native probeを実装した。65exports/WASM590964B、Native739群/CTest30、Node369skip0がローカル成功。既存40モデル+実原本11例の2841数値bit一致、実WASM40結果の独立Fraction参照/36負例も確認。SDK上限は2048頂点/32768面で、原本/Native hard上限とは別。公開CI/Pagesと操作結果はreports/2026-11-03-derived-mesh-sdk.mdで確定する。次の最小受入は、小さい成功bufferを既存3D rendererへ接続し、時刻/原本/Scene変更や失敗時に古いgeometryを表示しないこと。world/view/clip/GPU精度とcamera条件を明示してからrobotへ段階適用する。局所CPU監査を一般物理・流体・損傷・高精度撮像の完成へ広げない。

追記: 派生mesh SDK接続d43dcd4のLinux CI/Pagesが成功。GNU13.3/Node22.23.4でCTest30/Node369skip0、新旧各backend36負例とsanitizer69/27/54群が成功。公開12操作の原本/全数値packetはローカル一致、配信14ファイルはcommit blobとbyte一致。既存warning36行を保持。reports/2026-11-03-derived-mesh-sdk.mdへ全証拠を保存した。続く[小メッシュ3D表示の受入](DERIVED_MESH_RENDER_PLAN.md)は提案・未実装で、camera条件と失敗時のGPU資源/古い形状の消去を先に固定する。

追記: 成功した派生bufferの手動WebGPU表示を実装・ローカル受入。opaque所有copyから再normal生成なしで全bytesをuploadし、原本/時刻/Scene/予算変更で古いmeshを消す。GPU作成/validation/deviceLost/遅延結果と数値原本を分ける。Node391skip0・新renderer18群/旧描画5群・lab19群、実ブラウザ15操作/4面288Bを確認。SDK/C++/sampleは不変。公開結果はreports/2026-11-04-derived-render.mdで確定する。次はCPU参照prepareとGPUuploadの費用を分けた性能調査・更新頻度の受入を行い、手動小メッシュを実時間animationの完成としない。

追記: 手動3D表示90b1afeのLinux CI/Pages成功。GNU13.3/Node22.23.4でCTest30・Node391skip0、2841bits/両backend36負例・sanitizer69/27/54群を再確認。公開WebGPU15操作の全原本/数値/表示状態がローカル一致、配信17ファイルbyte一致。既存robotは起動READYを確認し戦闘操作試験とは分けた。全証拠はreports/2026-11-04-derived-render.md。次は[CPU参照と転送費用の測定](DERIVED_MESH_PERFORMANCE_PLAN.md)を最小受入として進め、更新頻度/予算を固定してからrobotへ適用する。既存warning36行と一般物理/流体/損傷/IK/光学撮像の残件を維持する。

次段の探索pilotを実行し reports/derived-render-performance-pilot*.jsonへ保存。Nodeの同一XY面繰返し5規模/各5計測で、SDK全体とtoken検査・所有copyを別に測った。4面中央値0.535ms/32768面873.147msはこの限定環境だけの値で、C++核単独/実GPUや一般fpsの評価ではない。正式性能受入は未完で、cold費用・多様なgeometry・C++/getter/転送内訳を次に調べる。エンジンsourceは192c8ad時点から不変。

追記: [Node段階計測](DERIVED_MESH_PROFILE.md)を実装・ローカル受入。Node407skip0、構文/Web build、標準100prepareの全8,123,305数値比較、計測経路48queryのNative派生2318bitsと独立Fraction/36負例が成功。5段階と未分類残差・別token生成を分け、初回/warmupも保持。C++/SDK/renderer/sample不変、公開結果はreports/2026-11-04-derived-profile.mdへ確定する。大容量は同grid面の繰返し負荷で、32768面baseline中央値1040.972msを一般性能やfpsへ拡張しない。次の最小受入は実ブラウザの小入力でCPU照会と全byte GPU upload/queue完了を区別する測定。Native同条件・連続animation・robot適用は未受入。

追記: 計測ツール5602496のLinux CI/Pages成功。GNU13.3/Node22.23.4でCTest30/Node407skip0、旧2841bits・新2318bitsと各backend36負例、sanitizer69/27/54群を確認。quick32prepareも54,410反復数値一致。公開16ファイルbyte一致と教材25記事・既存robotのREADY起動を確認し、reports/2026-11-04-derived-profile.mdへ全証拠を保存した。次の[ブラウザCPU照会と転送の計測](DERIVED_MESH_GPU_PROFILE_PLAN.md)は未実装の最小受入。既存warning36行と一般物理・流体・損傷・IK/制御・高精度光学撮像の未完を維持する。

追記: [ブラウザ計測ラボ](DERIVED_MESH_GPU_PROFILE.md)を実装・ローカル受入。Node438skip0/Web44modules、実IABで4/64/512面+計算核再読込後4面の40prepare/80drawが成功。Node実WASMと136,460反復数値/全typed bytesが一致、記録検査器の7変異と旧独立Fraction/36負例も通した。原本/SDK/C++/renderer/sampleは不変。全rawはreports/2026-11-04-derived-gpu.mdへ対応付け、公開CI/Pagesと公開操作を別に確定する。GPU待ちをGPU単独時間やfpsにしない。次は[所有snapshotコピーの比較](DERIVED_MESH_READBACK_PLAN.md)で実SDK全体の効果を測り、数値条件とDTO型/所有を維持して最小改善を選ぶ。一般物理・流体・損傷・IK/制御・高精度撮像の未完も維持する。

追記: 計測コードebf5b5aの初回CIは生成build IDを許容しない静的試験1件で停止した。試験修正158f9f1のLinux CI/Pagesは全成功し、CTest30/Node438skip0、旧2841bits・新2318bits、3batch各36負例、sanitizer69/27/54群を確認。公開IABの別40prepare/80drawも136,460数値と全typed bytesが一致し、配信15ファイルはcommit blobとbyte一致。既存robotはREADY起動を確認。reports/2026-11-04-derived-gpu.mdに全証拠を保持した。次候補の所有copyを有限比較したが、孤立copy短縮に対してSDK全体は4/64/512面で一貫した改善がなく、本番置換を採用しなかった。全30prepare/135,470数値と500,000micro copyを保存。次の最小受入は64 F64容量内の複数record読出し設計と旧getterとの全bit等価で、更新頻度/robot適用、一般物理・流体・損傷・IK/制御・高精度撮像の残件を維持する。

次段の具体案は[有界まとめ読出し](DERIVED_MESH_BATCH_READ_PLAN.md)。未実装で、最初は明示single/batch比較・既定singleを維持する。新1exportとheader4、厳密count/atomic失敗/旧SDK能力判定、独立参照と全bit同一性を固定した。512面でgetter2048→479回の計算でもpayloadは約7.48%増え、速度向上は未測定。次の実作業は既存snapshotのNative getterと失敗保持試験から始める。

追記: [有界まとめ読出し](DERIVED_MESH_BATCH_READ.md)を実装・ローカル受入。新SDK66/WASM592939B/glue50381B、Native744群/API70/CTest30、Node452skip0、Web c2aa5ebb6392265f/44modules。fresh40/Source11の2841bitsに加えsingle/batch各48派生query/2318bitsと独立Fraction/各36負例が成功。全byte/末尾/cache/退役の既存renderer回帰も維持した。独立4module・固定60prepare比較の406,410反復数値と全型/key順/typed bytesが一致。3sampleの64面通常経路はbatchが長く、既定singleを維持して明示比較APIに留める。初回warning/旧export数assert失敗もreports/2026-11-04-derived-readback.mdへ保持。公開CI/Pagesと公開互換動作を次に確定し、その後ブラウザの両transport比較UIを最小単位で実装する。更新頻度/robotへの適用、一般物理・流体・損傷・IK/制御・高精度光学撮像の未完を維持する。

追記: まとめ読出しef01017のLinux CI/Pagesが全成功。GNU13.3/Node22.23.4でCTest30/Node452skip0、SDK2841bits・single/batch各2318bits、4batch各36負例、sanitizer69/27/54群を確認。公開16ファイルはcommit blobとbyte一致。公開single互換20draw/990数値はローカルと一致し、既存robotはREADYを確認した。全証拠はreports/2026-11-04-derived-readback.md。既存warning36行を保持。次の最小受入は[ブラウザ両transport比較](DERIVED_MESH_BROWSER_READBACK_PLAN.md)で、設計のみ・UI未実装。既定singleを維持し、6run60prepare/120drawで全DTO/原本・入力/転送/資源とmode別会計を照合する。更新頻度/robot適用と一般物理・流体・損傷・IK/制御・高精度撮像の未完も維持する。

追記: [ブラウザ両読出し比較](DERIVED_MESH_BROWSER_READBACK.md)を実装・ローカル受入。Node468skip0/Web7f5b0f537e72cef8/44modules、実IAB6run60prepare/120draw/60新規転送/60cacheで270,940数値と全typed bytesがNode実SDKへ一致した。旧schema1の4rawも136,460数値を再照合し、旧新cohortを分離した。GPU機能一覧の順序だけの差で最初の検査が停止した事実とrawを保持し、重複/型/集合差は拒否したまま順序比較を修正。C++/SDK/engine/renderer/sampleは不変、既定singleを維持する。公開CI/Pagesはreports/2026-11-04-derived-browser.mdで別に確定する。次は[ロボット背面カバー](DERIVED_MESH_SAMPLE_PLAN.md)へ実Source/FK/LBSを接続し、ゲームの固定stepとGPU資源/更新費用を受け入れる。計画のみで適用済みとはしない。一般物理・流体・損傷・IK/制御・高精度撮像の未完と他チャットの改変保持を継続する。

追記: 比較UI eba356fのLinux CI/Pagesが全成功。GNU13.3/Node22.23.4でCTest30/Node468skip0、SDK2841bits・両transport各2318bits、4batch各36負例、sanitizer69/27/54群を確認。公開16ファイルはcommit blobとbyte一致。公開IABの別6run60prepare/120drawも270,940数値/全typed bytesを照合し、既存robotはREADYを確認した。全証拠はreports/2026-11-04-derived-browser.md。次の最小実装は背面カバーの原著Sourceと既知姿勢/保存往復・実FK/LBS/derived照合、その後ゲーム固定step/描画への接続。比較の追加測定を繰り返すこと自体を次の開発目標にしない。既定singleと未完の一般物理/流体/損傷/IK/高精度撮像を維持する。

追記: [背面カバー](ROBOT_BACK_COVER.md)をSource/FK/LBS/derivedから実ゲームへ接続し、ローカル受入。原著6頂点4面2骨/最大π8、120Hz visual状態と2tickごとの更新予定を分け、checked1件待ち中も通常全frameを進める。renderer対象単体dropMeshと旧世代/失敗復旧・既存128mesh level保持を試験した。Source7/controller11/renderer24を含むNode492skip0、Web b576823ff1731dba/45modules、SDK53source+7通知+2artifact不変。実IABでboost全開/復帰・2撃破・停止/再出撃・Scene編集undo/redo/保存再読込と常駐3meshを確認。停止帯で無限に微小姿勢を更新しない。reports/2026-11-04-robot-cover.mdへ初回pilot・修正・最終全rawを保持し、公開CI/Pagesを別に確定する。hidden/BFCacheの実ブラウザ全経路、無計器とのgame費用比較と全連続parameter品質は未受入のまま。公開確認後はPHYSICS_SCOPEの一般角運動・摩擦接触等の未完を調べ、共通engineの次の最小受入へ戻る。装飾animationを厳密ヒンジ/熱/損傷の完成にしない。

追記: 背面カバー8ebec4cのLinux CI/Pagesが全成功。CTest30/Node492skip0、SDK2841bits・両transport各2318bits、独立36負例×4とsanitizer69/27/54を確認。公開24ファイルがcommit blobとbyte一致し、実戦2撃破/全開・停止・編集保存再読込/再出撃を別runで確認。ツール遅延で上限に達した最初のframeログを保持し、新規239frameを別保存した。全証拠はreports/2026-11-04-robot-cover.md。次の最小実作業はscripts/build-web.mjsのasset-only変更cache key検証（Source/context JSONが現hash入力にない）と、その原本依存の追加・隔離fixture回帰。既存ゲームや他チャットの変更を保持し、元assetを試験のために書き換えない。その後[静的三角形と球](SPHERE_TRIANGLE_PLAN.md)のNative狭域照会へ進む。既存自由角運動/摩擦衝撃は実装済みで、摩擦支持・一般形状・関節/変形連成等が残ることを再確認した。一般流体/損傷/専門車両/IK/制御/高精度撮像の全scopeを維持する。

追記: asset-only cache key修正をローカル受入。assets直下のJSON/portable scene/SDK metadataを既存module/CSS/2WASMのbuild入力へ追加し、Sourceだけの変更を同じURLへ残さない。隔離fixtureの旧版2失敗→新4成功を保持し、全Node496skip0/構文/Web75daf0141409872f・45modules、全asset hash不変を確認。実IABで新Source URLとSDK ID一致/boost全開/停止、19照会全成功・常駐3meshを確認した。21HTMLは生成map/URLだけの変更。reports/2026-11-04-web-cache.mdへ証拠を保存し、公開CI/Pagesを別確認する。新format/下位asset directoryの対応と古いHTML自体のcacheは別条件。公開確認後はSPHERE_TRIANGLE_PLANのNative純粋照会を最小単位で実装し、一般物理/流体/損傷/専門車両/IK/光学の未完scopeを維持する。

追記: cache修正474e88cのLinux CI/Pages全工程成功。Node496skip0/CTest30・旧SDK/両transport照合・sanitizer等を確認し、既存warning36行を保持。公開76ファイル1,483,559Bがcommit blobに一致し、実公開で新Source/SDK build ID一致・全開・20照会全成功/常駐3meshを確認した。reports/2026-11-04-web-cache.mdとweb-cache-public-verification.jsonへ全状態/有限抜粋/配信/ブラウザ証拠を保存。全CIログの一括保存は64KBツール上限で拒否されたため、原ログURLと全warning/必要検証行・原行番号の抜粋に限定し、全文保存とはしない。次の最小未完はdocs/SPHERE_TRIANGLE_PLAN.mdのNative read-only狭域照会。まず既存Intervalと候補分類/退化/法線不定の失敗境界を固定して核・独立参照試験を実装する。SDK/World/CCD/一般mesh連成はこの一段の完成へ混同しない。

追記: 球×静的両面三角形のNative read-only狭域核をローカル受入。全7KKT候補を否定できる場合だけ除き、closest/距離/gap/normalをIntervalで包含。Native/ASan各126群、既知解析衝撃10群、32CTest/Node496skip0/構文/Web75daf0141409872fが成功。113入力の88成功・25意図した拒否/未確定を保持し、独立Fraction1848成分と23改ざん負例を検査。幅閾値のRN減算を外向き上限へ修正し、境界回帰を追加した。主SDK53source/7通知/2artifactと全原本不変、Native-onlyでWorld/CCD/game mesh接触へ未接続。docs/SPHERE_TRIANGLE.mdとreports/2026-11-04-sphere-triangle.mdへ根拠を保存し、公開Linux CI/Pagesを別確認する。次の最小未完はSPHERE_TRIANGLE_SDK_PLAN.mdの入力24/結果58/候補13・2exportの有界共通SDK接続案。現在は設計のみで、新しい主WASMを配布済みとしない。一般物理/摩擦支持/関節/流体/損傷/専門車両/IK/光学撮像のscopeを維持する。

追記: 球×三角形Native核f017d79の公開Linux CI/Pagesが全成功。GNU13.3/Node22.23.4で32CTest/Node496skip0、新核ASan/UBSan126群、独立88例1848成分と23負例、旧SDK/両transportの回帰を確認。既存warning36行を保持。公開26ファイル1,019,267Bがcommit blobに一致し、原著図の実表示と既存ゲームREADY/cover1照会/常駐3meshを確認した。全証拠はreports/2026-11-04-sphere-triangle.mdとsphere-triangle-public-verification.jsonへ保存。Native-onlyで主SDK/ゲームへの三角形照会接続はまだ無い。次の最小実作業はSPHERE_TRIANGLE_SDK_PLAN.mdの2export/input24/output58/candidate13、旧output保持/モデル失敗/所有DTO/独立参照を実装し、同じC++核を共有すること。区間中点を点衝撃へ無断変換せず、World/CCD/manifold、摩擦支持/専門車両/流体/損傷/IK/高精度撮像の未完scopeも保持する。

追記: 球×三角形の共有SDKをローカル受入。68exports/55 source-header/主WASM612824B、Native API77群/32CTest/Node502skip0、113入力の111modelと2host、packet22327・model13432 numeric bits一致、Fraction1848成分/23負例が成功。初回Node500/502の未作成リンク・旧件数固定を修正し、失敗rawを保持した。純核/header・全原本assets・7通知とlinked標準runtime集合は保持。Web f7448823095f375b/45modules、実ローカルゲーム出撃/boost20照会全成功3常駐meshは旧機能互換の確認で、三角形接触適用ではない。reports/2026-11-04-sphere-triangle-sdk.mdとsphere-triangle-sdk-local-verification.jsonへ証拠を保存。公開CI/Pages確認後、手動browser triangle labの入力編集・候補/失敗の区間検査・JSON保存へ進む。World/CCD/manifold・摩擦支持・専門車両/流体/損傷/IK/高精度撮像は未完のまま継続。

追記: SDKコードe100beeの公開Linux CI/Pagesは全工程成功。GNU13.3/Node22.23.4で32CTest/Node502skip0、新SDK22327packet・13432model numeric bits、Fraction1848/23負例、旧SDK/両transport/quick54410とkernel sanitizer126群を確認した。既存warning36行の診断列は前回と同じ、新核warning0。公開31ファイル1,330,820Bがcommit blobに一致し、実ブラウザのREADY/出撃/boost21照会全成功・3常駐mesh・新612824B SDK/build ID一致を確認。reports/sphere-triangle-sdk-public-verification.jsonへ全工程状態/有限ログ抜粋/配信/画面証拠を保存した。次はdocs/SPHERE_TRIANGLE_LAB_PLAN.mdの手動照会ラボ。既存ゲーム接触は三角形核へ未接続のまま区別し、World/CCD/manifold・流体/損傷/専門シミュレータ等の未完scopeを維持する。

追記: 手動球×三角形ラボをローカル受入。全13presetの実SDK8成功/5モデル失敗、専用14/全Node516skip0・構文/Web fc67426f445af36a/46modules/22entryが成功。実ブラウザの全13例・手編集即旧表示消去・ID0拒否/reset復帰・-0/radius2の境界未確定・XY投影・実JSONダウンロードと表示一致を確認。SDK55source/7通知/両artifact/manifest・全assets/samplesはd9cf168からbyte不変。同期load例外後retry不能とreload中旧runtime使用の2bugを回帰で修正。reports/2026-11-04-sphere-triangle-lab.mdへ根拠を保存し公開確認へ進む。次は静的三角形meshの入力/所有/安定ID・有界read-only照会を最小単位で設計する。World/CCD/manifold・ゲームmesh接触・流体/損傷・専門シミュレータは未完のまま。

追記: ラボeef9e51の公開確認後、極小区間の白枠が描画解像度で消えやすかったため、表示inkだけを各辺1.5 SVG px広げた0db8f54を公開。数値区間/DTOを変えず、再度Node516skip0・構文/Web50e73448d9d02126/46modules/22entry・ローカル全13例1491入力/結果numeric bits不変を確認。最終公開Linux CI/Pages全工程成功、32CTest/Node516/SDK全照合・独立1848/23負例・sanitizer等も成功、既存warning36行の診断列を保持。公開25ファイル1,078,093Bはcommit blob一致。最終公開13例、手編集ID拒否/復帰、境界未確定・XY投影、2926B実ダウンロード/表示一致/-0保存を確認し、公開とローカルの1491数値bitsも一致。reports/sphere-triangle-lab-public-verification.jsonへ全工程/有限抜粋/byte/ブラウザ証拠を保存した。次はdocs/SPHERE_TRIANGLE_MESH_PLAN.mdのNative有限集合照会。設計のみで、未解決面を成功へ隠さず同率候補を全保持する方針。World/CCD/manifold・ゲームmesh接触・専門モデル等の未完scopeは維持する。

追記: [球×静的三角形集合](SPHERE_TRIANGLE_MESH.md)のNative純粋核をローカル受入。最大64面を全列挙し、1面失敗もnearestへ隠さず、同率候補IDと面固有geometryを保持する。新核/ASan59群、33CTest/Node516skip0、48入力29成功6row失敗13事前拒否、独立2775成分と43改ざん負例が成功。Native/ASanの373170B fixtureはbyte一致。統合recipeの旧検査器呼出し1件を訂正再実行し、初回失敗rawを保持。主SDK55source/7通知/2artifact/manifest・全assets/samples/単一核は38b59f1からbyte不変。Web50e73448d9d02126/46modules/22entry。reports/2026-11-04-sphere-triangle-mesh.mdへ証拠を保存し、公開Linux CI/Pagesを次に確認する。Native-onlyでWorld/CCD/ゲームへ未接続。公開後は有界C ABI/JS所有snapshotの入力/全行診断/失敗保持を設計し、一般接触・流体/損傷・専門モデル等の未完scopeを維持する。

追記: 集合核7b598e7の初回Linux CI/Pages全成功と28配信byte一致を確認。新試験だけに出たGNU2warningを行配置で整理し、strict59群/独立2775成分と373170B fixture不変を再確認。修正版の公開検証へ進む。次段の[集合SDK接続案](SPHERE_TRIANGLE_MESH_SDK_PLAN.md)を具体化し、64面stagingと6exports/14入力/24header/14source/58row/13candidateの所有・失敗保持を固定した。これは設計のみで現SDK68exportへ未実装。Native/World/ゲーム接触の境界を維持する。

追記: 集合核修正版5c9093bの公開Linux CI/Pages全工程が成功。33CTest/Node516skip0、独立2775成分/43負例、新mesh ASan/UBSan59群と旧SDK/単一面回帰が成功し、新規warning0・既存36診断を保持。公開29ファイル1,097,707Bがcommit blob一致。初回7b598e7での原著図/ゲームREADY/単一面ラボ成功観測について、最終の13観測資源byte不変を確認した。reports/sphere-triangle-mesh-public-verification.jsonへ全工程状態/有限ログ/配信/証拠hashを保存。Native-onlyで新集合は主SDK/World/game未接続。次の最小実作業はSPHERE_TRIANGLE_MESH_SDK_PLAN.mdのC ABI staging64/6exportsとNative probe・失敗交換の旧snapshot/output保持から実装し、次にJS所有decoderと実WASM全bit/Fractionを受け入れる。現行68-export SDKへ追加済みとはしない。一般接触/流体/損傷/専門モデル等の残件を維持する。

追記: [集合照会の共有SDK](SPHERE_TRIANGLE_MESH_SDK.md)をローカル受入。6追加/計74exports・57原本、WASM638777B/glue53435B。Native新18/旧API77/34CTest、Node526skip0/構文/Web1f40cf023bb8472f46modules22entry成功。48入力45model29成功16失敗/3hostを分け、実WASM27160packet/20808model numeric bitsと4453negativezeroがNative一致、独立2775成分/43負例・旧single22327/13432回帰成功。55保護原本+7通知/元assets/game source不変。既存libc++ algorithm.oの標準sort部品1追加をpinned源/通知と監査し、runtime集合不変とはしない。独立MSVC ASanは247.548s compile未完exit15/runtime未実行を保持。公開GNUでAPI/testinstrument+regularstrictkernelとpurekernel別ASanを検証予定。実localゲームで新SDK読込/3撃破/boostclip1/停止・22照会全成功3常駐を確認した。新mesh接触適用ではない。reports/2026-11-04-sphere-triangle-mesh-sdk.mdへ全根拠を保存し公開CI/Pagesへ進む。公開受入後は手動集合browser labの原本編集/全行・possibleID/失敗とJSON保存を最小段にする。World/CCD/manifold・一般接触/専門モデル等の未完scopeは維持。

追記: 集合SDKコードc9dda79の公開Linux CI/Pages全job/step成功。34CTest/Node526skip0、新SDK27160packet/20808model bits・2775独立成分/43負例と旧回帰を再確認。API/test ASan/UBSan18群（通常strict核と結合）とpure mesh別59群が成功し、Windows ASan compile未完は別記録を保持。既存36warning診断を維持、新API/kernel追加warning0。公開41ファイル1,438,875Bがcommit blob一致。実公開2撃破/boostclip1/停止、21照会全成功3常駐mesh・新SDK638777B/buildID1f40一致、旧ラボ147数値bits一致も確認した。reports/sphere-triangle-mesh-sdk-public-verification.jsonへ全工程状態/有限抜粋/配信/ブラウザ/証拠hashを保存。次の最小実作業はSPHERE_TRIANGLE_MESH_LAB_PLAN.mdの手動集合ラボUIと独立専用試験。設計のみで未実装のURLを案内せず、既存C++/SDKとgame原本をそのUI段階で変更しない。World/CCD/manifold・一般接触/流体/損傷/専門モデル/IK/光学撮像の未完scopeを維持する。

追記: 最大64面の手動集合ラボをローカル受入。専用18/全Node544skip0・構文/Web457dd1cda43de02c47modules23entry・既存34CTest成功。実ブラウザ17例10成功6モデル失敗1host拒否、全64source/全ID/末尾7候補、edit即旧表示消去、ID0/reset、−0/radius1のedit/retry、面別閲覧/XY・YZ表示、失敗後続面と実Blob2保存を確認。42644数値bits/5733負零が実WASM再照会・表示保存一致。独立参照は既存45にbrowser21packet追加し7353成分（追加4578）成功。SDK27160packet/20808modelbits・独立2775/43負例と旧single回帰も再確認。C++/SDK57原本74exports/7通知/全assets/sample原本不変を監査する。reports/2026-11-04-sphere-triangle-mesh-lab.mdへ根拠を保存し、公開CI/Pages・配信byte・操作を次に確認する。World/CCD/manifold・一般応答/流体/損傷/専門モデル/IK/高精度撮像は未完。公開受入後は三角形集合に対する線形軌道全区間の安全性guardを最小段で設計する。

追記: 手動集合ラボ203c11aの公開Linux CI/Pages全job/step成功。34CTest/Node544skip0、SDK27160packet/20808modelbitsと独立2775/43負例、pure mesh ASan/UBSan59群・SDK API/test18群も成功し、既存36warning診断を維持。42配信ファイル1,428,296Bがcommit blob一致。実公開17例・edit/reset/retry・全64行/全ID/最終7候補・XY/YZ・失敗後続面閲覧・2実Blob保存、42644数値bits/5733負零と独立追加4578成分を確認した。既存ゲームの2撃破/boostclip1/停止と35照会全成功3常駐も確認したが、新mesh接触適用ではない。reports/sphere-triangle-mesh-lab-public-verification.jsonに全工程/有限ログ/byte/操作/証拠hashを保存。次の最小実作業はSPHERE_TRIANGLE_MESH_TRAJECTORY_PLAN.mdのNative線形軌道guardで、三角不等式による全区間の非接触証明と、証明できない/失敗/点貫通witnessを区別する。新guardは設計のみでまだ実装せず、World/一般CCD/接触応答・流体/損傷/専門モデル/IK/高精度撮像の未完scopeを維持する。

追記: 定義線分軌道×静的三角形集合のNative guardをローカル受入。Native69群/62入力=25全区間非接触・4厳密点貫通witness・20未認証・13入力拒否。実128leaf/255照会/末尾と127leaf予算時prefix保持、64source、丸めanchorのE補正、所有/settings/−0・環境拒否を確認。初回35CTest＋test-only拡張後専用1CTest、Node544skip0/構文/Web457dd1cda43de02c47module23entry成功。独立Fraction48全path/4witness/297leaf/606audit、解析14/改ざん71・label/order独立/最適化拒否成功。保護98原本/主SDK57source74exports/WASM638777B/7通知/全assets/sample不変、旧SDK27160packet/20808modelbitsと独立2775/43負例・旧single回帰も成功。回帰anchor想定の初回失敗/旧56・61rawと最終62PASSを別保持。allocation/未返却workfault injection・parameter_resolution自然未到達は未検証。reports/2026-11-04-sphere-triangle-mesh-trajectory.mdへ証拠を保存し、公開GNU新cpp/test-Werror・全核ASan/UBSanとLinux Native/ASanfixturebytecmp・Pagesへ進む。Native-onlyで主SDK/UI/World/game/TOI応答未接続。公開受入後は有界C ABI/JS所有snapshotの接続を次の最小段にし、一般物理/流体/損傷/専門モデル/IK/光学撮像の残件を維持する。

次段の具体案: SPHERE_TRIANGLE_MESH_TRAJECTORY_SDK_PLAN.mdに独立stage64、意味19+reserved5の24入力、最大64F64内のheader/audit/getter群、全source/255audit/128leaf/33frontier/lastMesh全行と候補、work.exact/上界とoptionalの保持を設計した。旧62入力はhost3/実model59となる予定だが未実行で、現74export SDKへ追加済みとはしない。Native probe/失敗原子性→JS所有decoder→実WASM全wire/DTO bits・独立Fraction→配布runtime/通知監査を次の受入順とする。

追記: 定義線分guardコード93ec576の公開Linux CI/Pages全job/step成功。35CTest/Node544skip0、Native69群/62入力と独立297leaf/606audit・71負例が成功。新cpp/test各-Wall/-Wextra/-Wpedantic/-Werrorを通過、guard/mesh/primitive/Interval/core/portable/testを全instrumentしたGNU ASan/UBSan69群とLinux Release/ASan fixture bytecmp・sanitized独立参照も成功。既存36warning診断を維持し、公開42ファイル1,528,714Bが当該blob一致。実公開原著図と既存meshラボ既定入力170数値bits/20負零を確認。98保護原本/SDK74exports57source/WASM638777B/7通知不変で、新guardはNative-only。reports/sphere-triangle-mesh-trajectory-public-verification.jsonへ全工程/有限ログ/配信/ブラウザの根拠を保存。次の実装はSPHERE_TRIANGLE_MESH_TRAJECTORY_SDK_PLAN.mdに従い独立stage64と有界C ABI/Native probeの失敗原子性から進め、JS所有decoderと実WASM照合へ接続する。未実行fault injection/parameter_resolution、未接続World/TOI/応答・流体/損傷/専門モデル/IK/高精度撮像を成功扱いにしない。

追記: 定義線分guardの独立C ABI/raw WASM交換をローカル受入。新6exports/計80、59source-header、WASM674978B/glue56289B、runtime linked members増減0・7通知hash不変。Native25群/全36CTest、test側C4267 2件修正後の専用25再試験、Node544skip0・構文/Webd692d4714c9e820a47module23entry成功。62入力59model/3host、606audit/297葉/120lastMesh行815候補を全保持、pureDTO→Native wire71234数値2472負零、実WASM全wire70278bits2398負零と各19改ざん拒否が成功。原本62への独立Fraction参照と交換59model bit一致のscopeを分離。保護98原本/旧mesh・single・simulation回帰、実local3撃破/移動boostclip1/停止・20SDK照会全成功3常駐を確認。公開GNU API/test sanitizerとCI/Pages/配信を次に確認する。新JS所有decoder/trajectory UI/World/TOI/応答は未実装、故意allocation/未知workfault注入・Windows sanitizerを成功扱いにしない。次の実装は既設80exportsを使うowned JS decoderとcapability全検出・packet strict validation/DTO所有/無fallbackの受入とし、その後専用UIへ進む。

追記: raw交換初回公開コード7a8300bは全CI/Pages/ASan25群・pure guard69群と50配信byte/公開3撃破・21照会全成功まで確認。ただし新test/probe4箇所のGNU indentation警告が受入gateで判明。brace/改行のみ修正し、両target/25群/62probe再実行と全packet byte同一を確認、WASM/API/kernel不変。新test/probe各-Werror監査を追加した訂正コードで公開GNU再確認へ進む。初回46警告出現の内訳/工程成功とgate停止は独立保持し、警告監査まで完了したとはしない。

追記: raw軌道交換の訂正コード84afb8cを公開受入。Engine CI41764778386/Pages41764778247全job/step成功、36CTest/Node544skip0、Native/WASM59model3host・全wire/DTO bitsと各19負例が再成功。新test/probe各-Werror監査通過、既存36warning診断のmultiset/出現数一致、API/test ASan25群（通常strictarchive）＋pure guard全核別69群も成功。50公開ファイル1,710,851Bがblob一致。初回7a公開3撃破/boostclip1/停止・21照会全成功3常駐/旧ラボ170bits20負零は、entry/JS/SDK/assets11ファイルのbyte不変を監査して継承。初回46warning/gate停止と訂正全packet byte不変を隠さずpublic-verification.jsonへ保存。C ABI80exports59source/WASM674978B・runtime部品/7通知/保護98原本不変。次の最小実装はowned JS decoderと全capability preflight、strict packet監査/DTO所有/旧74拒否/無fallback、および実62入力からのJS DTO bit照合。UI/World/TOI/応答・流体/損傷/専門モデル/IK/高精度撮像・fault注入未実行の境界を維持する。

追記: 定義線分guardの所有JavaScript APIをローカル受入。専用22/全Node566skip0・構文/Web7f0cfa4ee56be1ca（48module/23entry）成功。実model59の50663数値bits/2144負零とoriginalInput3877bits/100負零を照合し、全59caller変更/古いDTO不変・追加3回で所有分離を確認。host3はモデル未実行と分け、実owned59＋明示pure補足3のmixed62から独立297leaf/606audit・71負例/14解析群成功。初回テスト期待2件と入力アクセサ多重読取りの修正履歴を保持。全107保護原本/Native C ABI/80exports59source/674978B WASM/通知不変、旧mesh・single・simulation回帰成功。実browser固定例324bits24負零一致、ゲーム1撃破/boostclip1/停止・20照会全成功3常駐を確認。reports/2026-11-04-sphere-triangle-mesh-trajectory-js.mdとlocal-verification.jsonへ根拠保存。公開CI/Pages/配信/操作を次に確認し、公開受入後はSPHERE_TRIANGLE_MESH_TRAJECTORY_LAB_PLAN.mdの手動線分ラボへ進む。metadata監査を独立数学solverと呼ばず、Native故意fault注入/World/TOI/応答・流体/損傷/専門モデル/IK/高精度撮像の未完scopeを維持。

追記: owned JSコード5ff5723を公開受入。Engine CI41768169352/Pages41768168303全job/step成功、36CTest/Node566skip0、実owned59モデルの全50663bits/原入力3877bits、明示補足host3と合わせたmixed62の独立297leaf606audit/71負例14解析群・旧SDK回帰を確認。API/test GNU sanitizer25群とpure guard別全核69群も成功、既存36warning診断のmultiset/数一致。56公開ファイル1798436Bがblob一致。実公開所有API324bits24負零一致、ゲーム3撃破/boostclip1/停止・20照会全成功3常駐を確認し、public-verification.jsonへ全工程/有限ログ/全warning/byte/実操作を保存。次はSPHERE_TRIANGLE_MESH_TRAJECTORY_LAB_PLAN.mdの手動線分編集ラボを最小段として実装する。計画のみのUI、未接続World/一般CCD/TOI応答、流体/損傷/専門モデル/IK/高精度撮像と故意Native fault注入を完成扱いにしない。

追記: 手動線分guardラボをローカル受入。専用20/全Node586skip0・構文/36CTest、Web d70b5d9b4436650f（49module/24entry）。25preset全input bitsが既受入Native62に一致し、24model=11sep1witness10未認証2invalid・host1を別保持。実browser全25＋追加7packetと2実Blob保存は100742bits3896負零まで直接SDK/表示と一致。255audit/128leaf末尾、127partition=126certified＋current/prefix0.984375、64source元順末尾ID1/全possibleID/7候補、auditとlastMesh所属分離、edit即全消去/ID0reset/−0手編集retry/XY-YZを確認。既存ゲーム2撃破/boostclip1/停止・19照会全成功3常駐。旧owned/mesh/single/simulation回帰・独立mixed62/71負例も成功。249保護原本不変、旧entry試験期待23→24のみ明示変更し初回Node585/586と専用誤期待rawを保持。reports/2026-11-04-sphere-triangle-mesh-trajectory-lab.mdへ根拠保存。次は公開CI/Pages/配信byte/実操作を確認。World/一般CCD/TOI応答・流体/損傷/専門モデル/IK/制御/高精度撮像の未完scopeを維持。

追記: 手動線分ラボ656f59dを公開受入。Engine CI41770992200/Pages41770991665全job/step成功、36CTest/586Nodeskip0・独立mixed62/71負例・API/test sanitizer25/pure guard全核別69群成功。既存36warning診断のmultiset/数一致、64公開ファイル1925537Bがblob一致。実公開25例＋追加7packet/2実DL=100742bits3896負零、ゲーム3撃破/boostclip1/停止・21SDK照会全完了3常駐を確認。249保護原本不変と旧entry期待23→24を明示、private ACLの原試験記録13ファイルは77e03caのarchiveへ全byte/hash不変で追加しGit blobも一致。reports/sphere-triangle-mesh-trajectory-lab-public-verification.jsonへ全工程/有限ログ/byte/実操作を保存。次の最小Native数値段はSPHERE_TRIANGLE_MESH_ENTRY_PLAN.mdのentry window設計。厳密安全prefix・E込み負witness・窓幅を揃え、未知の狭さだけで成功とせず、元pathのglobal parameterを保持する。hard boundsを実装前に固定し旧DFSfrontier33を新探索へ流用しない。新核/SDK接続/World/TOI応答・流体/損傷/専門モデル/IK/制御/高精度撮像は未完のまま。

追記: Native sphere×static mesh entry windowをローカル受入。strict初期正・closed安全prefix・E補正負witness・外向き幅を揃え、元path/global parameterと全partitionを保持。76群/65入力=18separated・8窓・20未認証・2初期貫通・17invalid。独立558leaf/1452audit/3840成分・17解析/90改ざん拒否、37CTest/586Node skip0・旧SDK/数学回帰成功。256audit/128partition/127frontier/64全ID、法線未確定ancestorから子証拠で回復を確認。276保護原本/80exports59source/WASM674978B/7通知/Web d70b5d9b4436650f不変。reports/2026-11-04-sphere-triangle-mesh-entry.mdへ原出力と境界を保存。次に公開GNU各-Werror・全核ASan/UBSan/fixture bytecmp・CI/Pages/73配信を確認し、受入後に有界C ABI/所有JS接続へ進む。新核はNative-only、World/TOI応答・流体/損傷/専門モデル/IK/高精度撮像・故意例外注入未完。

追記: Native entryコード058a919を公開受入。Engine41774681284/Pages41774680814全job/step成功、37CTest/586Node skip0、65入力/独立558leaf1452audit3840成分・17解析90負例、新cpp/test各-Werror・全核ASan/UBSan76群とLinux Release/ASan fixture bytecmp成功。旧guard69/API25 sanitizerと旧数値/数学回帰、既存36warning診断multiset不変を確認。73公開file2078382Bはfeature blob一致。原著図の実公開表示と、同一80sourceに基づく旧ラボ/ゲーム操作の継承を区別しpublic-verification.jsonへ全工程/有限348原行/byte/証拠hashを保存。276原本/SDK80exports59source/674978B/7通知不変。次はSPHERE_TRIANGLE_MESH_ENTRY_SDK_PLAN.mdの独立stage/C ABIとNative probeを実装する。6追加exports/全packetmapは未実装の設計で、新核はNative-only。未実行fault注入/自然parameter_resolution/World/一般TOI応答・流体/損傷/専門モデル/IK/撮像の残件を維持する。
