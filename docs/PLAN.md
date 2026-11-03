# 現在地と再開位置

更新: 2026-11-03。製品仕様は `PROJECT_SPEC.md`。この記録は実装した範囲と未完を区別する。ユーザーは節目でのGitHubプッシュ・起動リンク・継続開発を明示的に指示している。

再開位置: W2のローカル最終検証は成功。未コミット・未公開のため、記録を最終照合してpushし、公開CI/Pagesと起動リンクを検証する。
対象は法線支持・離脱・衝撃を進めるW2と候補軌道の全区間監査。共通ABI46 exports、主WASM430397B / glue43782B、ローカルWeb build `4ba0bda196575a16`。
ローカル結果はNative361群・CTest20/20、Node193/193・skip0、教材17記事。今回の公開成功とは区別する。
直前公開c262c0cは44 exports / WASM361007B / glue43071B、Native296群・CTest16/16、Node175件。
同版のLinux CI・Pages・両公開ラボは確認済み。過去の証拠はreports/2026-11-03-route-support.md。

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
| M1 Native/WASM | 650B freestanding ABIに加え共通物理・光学の主ABI。今回W2 step/eventの2関数を加え46関数 | 既設Emscripten6.0.13と通知を維持。ローカル最終WASM430397B/glue43782B、Native20CTestとNode193件が成功。直前公開44関数のCI/Pagesは確認済み、今回の公開確認はpush後。ゲーム全ロジック共通化はM2残件 |
| M1 性能 | Web生ログJSON、Native生CSV・p50/p95/p99/最大/超過 | Native loop p95 17.9802ms、p99 18.8144ms、max29.1888ms、63/120超過。60fps目標未達。GPU/実提示未測定 |
| M1 教材 | 図解17記事と検索、既存ラボに手動120Hzの支持Worldラボを追加。read-only支持ラボも保持 | 新ラボは7プリセット、1/12/96tick、失敗時全状態保持と同じWorldでの再試行。最終ローカル全Node193件（lab14/既存教材12を含む）がskip0で成功。今回の公開検証はpush後 |
| サンプル初版 | オリジナルIRON FIELD、移動/ブースト/上昇/ロック射撃/敵/3波/勝敗/再出撃 | 純粋シミュレーションとブラウザ実操作を確認。Native版の戦闘未実装 |
| M2 制作A初段 | 原本三角形メッシュ・単一頂点編集・Undo/Redo・v2 JSON/共通形式、WebGPU/DX12実形状描画 | GUIで頂点移動→Undo/Redo、CLIの作成→編集→保存→Native読込を実行。衝突AABB再生成を試験。面編集/押出し/UV/地形/音響形状伝搬は未実装 |
| 物理C1初段 | 既存6自由度/W1/read-only支持に、摩擦0の球proxy/静的平面を進めるW2を追加。RATTLE・有限vn支持選別・衝撃・離脱と全区間幾何監査 | 新核はRATTLE17/guard24/driver13/private policy8群、ABI追加3群。Native総計361群・CTest20/20がローカル成功。曲率球対・非直交共有bodyも対象。一般形状・摩擦支持・関節・車両/ゲーム接続は未完 |
| 任意光学の継続基盤 | 位置/方向/法線/屈折率の全区間を維持し、指定面・反射/透過の列を継続。距離/OPL/任意偏光のパワー包絡を返す | 点波長のCauchy/Sellmeier phase区間を接続。全段成功時のみ最終結果。未指定面の遮蔽、自動nearest探索、全ghost列挙、撮像・収差画像・波動干渉は未完 |
| 流体F1初段 | JS/C++閉メッシュの静水圧・排水体積/浮心・浮力/復原トルク、無接触1体のNative中点結合、JS係数抗力 | JS14解析試験・Native20検証群、両言語12形状153値比較。釣合い・既知上下振動・偏心復原・100秒誤差。非定常流/CFD/一般接触結合/弾塑性破壊は未実装 |

## 次の最小マイルストーン

追加要求（2026-11-03）: 空気・水の流体を使う航空/潜水艦等のシミュレーター、衝突の残留へこみと被弾による装甲の材料損傷。正式な受入項目は `PHYSICS_SCOPE.md`。通常の追加は適切な依存順で取り込み、「今やれ」「至急」の指定は優先変更として扱う。現在のM2制作Aは変形形状の原本・描画・派生データの前提なので継続する。

1. 現行W2はローカル検証済み。記録・配布物を最終照合してpushし、公開CI/Pagesと操作ラボの起動・復帰を確認し、起動リンクを提示する。有限刻みモデルと残差・失敗時保持を明示する。続いて摩擦支持/一般形状・関節と、明示面列を超えたレンズ形状/媒質・遮蔽・経路の選択へ進む。M2制作Aの面編集/モーションと各専門物理の未完項目も維持する。製品全体の完成、全作品60fps達成、音の聴感確認と混同しない。
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


## 現行未コミット: W2支持・離脱・衝撃と候補軌道監査

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
今回の結果はローカル成功で、未コミット・未公開。push後の公開CI/Pagesと実ラボの起動・復帰確認を次に行う。
外部solver/依存/素材の追加、ライセンス選定は行わない。一般形状・摩擦・関節・長時間大規模性能、流体/弾塑性連成と専門車両の未完は維持する。
