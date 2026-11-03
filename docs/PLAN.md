# 現在地と再開位置

更新: 2026-11-03。製品仕様は `PROJECT_SPEC.md`。この記録は実装した範囲と未完を区別する。ユーザーは節目でのGitHubプッシュ・起動リンク・継続開発を明示的に指示している。

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
| M1 Native/WASM | 650B freestanding ABIに加え共通剛体/静水圧/線形/加速接触・光学・面交差・偏光・W1 Worldの36関数ABI、288519B WASMと40451B glue | 公式Emscripten6.0.13で現地ビルド、Native/Node実WASMの30697値比較、ブラウザ実行。標準ランタイム通知/全source/artifact hash保持。ゲーム全ロジックのC++共通化はM2残件 |
| M1 性能 | Web生ログJSON、Native生CSV・p50/p95/p99/最大/超過 | Native loop p95 17.9802ms、p99 18.8144ms、max29.1888ms、63/120超過。60fps目標未達。GPU/実提示未測定 |
| M1 教材 | 図解13項目と検索、原本メッシュ教材、静的/動的浮力ラボ、炎4モード・波形・パラメーター・停止/コマ送り | 教材と実WASMを含むNode144試験成功。IABで指定姿勢の釣合いと実際に積分した上下動・復原を確認 |
| サンプル初版 | オリジナルIRON FIELD、移動/ブースト/上昇/ロック射撃/敵/3波/勝敗/再出撃 | 純粋シミュレーションとブラウザ実操作を確認。Native版の戦闘未実装 |
| M2 制作A初段 | 原本三角形メッシュ・単一頂点編集・Undo/Redo・v2 JSON/共通形式、WebGPU/DX12実形状描画 | GUIで頂点移動→Undo/Redo、CLIの作成→編集→保存→Native読込を実行。衝突AABB再生成を試験。面編集/押出し/UV/地形/音響形状伝搬は未実装 |
| 物理C1初段 | Native/Web共通6自由度、世界角運動量・主慣性、球/平面接触、摩擦/反発/回転 | Native全212群/CTest12/12。内訳はcore15/dynamics16/内部10/hydro20/ABI27/線形17/区間18/加速19/光学16/W1 World21/面交差16/偏光17。W1は球proxy/静的平面の有限精度衝撃と全tick保持。持続支持/多形状/関節/戦闘接続は未完 |
| 流体F1初段 | JS/C++閉メッシュの静水圧・排水体積/浮心・浮力/復原トルク、無接触1体のNative中点結合、JS係数抗力 | JS14解析試験・Native20検証群、両言語12形状153値比較。釣合い・既知上下振動・偏心復原・100秒誤差。非定常流/CFD/一般接触結合/弾塑性破壊は未実装 |

## 次の最小マイルストーン

追加要求（2026-11-03）: 空気・水の流体を使う航空/潜水艦等のシミュレーター、衝突の残留へこみと被弾による装甲の材料損傷。正式な受入項目は `PHYSICS_SCOPE.md`。通常の追加は適切な依存順で取り込み、「今やれ」「至急」の指定は優先変更として扱う。現在のM2制作Aは変形形状の原本・描画・派生データの前提なので継続する。

1. M2制作Aの最小縦断と、追加要求の物理C1/流体F1の独立核を実装。公開検証と測定結果は `reports/2026-11-03-m2.md` に集約する。製品全体の完成、全作品60fps達成、音の聴感確認と混同しない。
2. 初回Web30秒試験を reports/webgpu-benchmark.json に保存。1800フレーム、p95=16.755ms、p99=16.785ms、max=17.465ms、厳密予算超過1193件。GPU/実提示未計測で合格にしない。初回の負の開始間隔を含む試験も別ログに保持。今後はGPUタイムスタンプと実提示・音声負荷を含め、Native超過の原因を分解する。
3. Native剛体と静水圧の無接触1体結合をWebAssemblyへ出力し、同じ実C++経路で上下動/復原のWebGPU実験を追加。`reports/2026-11-03-wasm-simulation.md`に生ログ・誤差・配布条件。JS77試験、Native67群。一定速度の球同士・移動平面のTOI核と実WASM操作ラボを追加し、Native全86群/CTest5/5、Node89試験、30336値比較を検証。reports/2026-11-03-continuous.md。次は重力/異なる外力の区間軌道と、接触時刻での応答・残り時間・持続接触をWorldへ統合し、一般形状へ拡張する。ゲームや箱形状への接続と混同しない。
4. M2制作B: 少数ボーン/キーの原本・時間サンプリング・保存を作り、30/60/120描画で同じ姿勢/イベントを検証する。FK/IKと制御グラフの候補は `CONTROL_DESIGN.md`、任意の高精度レンズ計算は `OPTICS_SCOPE.md` に受入を保持する。
5. サンプルは上記エンジン機能を使って更新。別チャット由来の変更があれば先に確認・統合する。

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

現在の動作確認済み公開版: https://tatata93.github.io/pikapikaengine/?v=1ab868a 、浮力ラボ https://tatata93.github.io/pikapikaengine/docs/learn/buoyancy.html?v=1ab868a 。コード1ab868aの公開CI（JS/Native/WASM/parity）・Pages成功、公開WebGPU READYとラボの釣合い操作を確認。前節3d463d7では公開メッシュ編集を実行（reports/m2-public-mesh-edit.png）。最新記録は reports/2026-11-03-buoyancy.md。共通C++のWeb出力に向けた次の受入・調査は WASM_DYNAMICS_PLAN.md。起動リンクに版queryを付け、PagesのHTML/ESMキャッシュを区別する。前版9064a2fのNative arena性能はp95 26.9045ms、p99 53.9267ms、max75.2425ms（reports/native-arena*）、M2のWeb/Native測定は reports/2026-11-03-m2.md。60fps未達と遅延原因の調査は残る。

追記: 最新コードfe3a9f3の公開CI・Pagesが成功。動的実験 https://tatata93.github.io/pikapikaengine/tools/float-lab.html?v=fe3a9f3 を公開ブラウザで起動し、1tick、再生/停止、39.283s/4714tickの進行を確認。build 8277480dc456d30f。Linux GNU13.3.0/Node22.23.4でもWASM30180値の比較が成功。CIのJSは74成功/Native CLI依存3skip、Windowsローカルは77成功。reports/2026-11-03-wasm-simulation.md が最新。次項の一定速度球/平面・球同士の接触時刻核に着手中。一般WorldのCCD受入完了ではない。

追記: コード1ebcfc5の公開CI・Pagesが成功。接触時刻ラボ https://tatata93.github.io/pikapikaengine/tools/contact-lab.html?v=1ebcfc5 を公開ブラウザで操作し、実WASMによる高速球2ms・接線3ms・移動平面4msを確認。build 178d4cd2a8d0d543。Linux GNU13.3.0/Node22.23.4でCTest5/5、Node89/89・skip0、Native/WASM30336値の最大絶対差0（この実行の結果）。生ログと公開画面は reports/2026-11-03-continuous.md。次は荷重を保持する区間伝播と時刻固定接触の内部分離、および加速軌道を安全に調べる区間演算。World全体のCCD、任意選択の厳密なレンズ光学は未実装。

追記: コード41b7564の公開Linux CIが成功し、CTest7/7・厳密有理数6,829区間・Node89/89/skip0を確認。原本のバイト保持を修正したa17e11aのPages配信も成功。https://tatata93.github.io/pikapikaengine/tools/contact-lab.html?v=a17e11a を公開IABで起動、184044B/build9057db191e652b4aの実WASMを確認。reports/2026-11-03-interval-foundation.md が最新。次は一定加速度の保守的な照会と、光学の単一界面Snell/Fresnel参照核に着手中。これらは次の未完マイルストーン。

追記: コード180c68eのLinux CIとPagesが成功。CTest9/9・Node114/114/skip0、光学1029例の分類/4116区間端点bit一致、Native/WASM30697値の最大絶対差3.3306690738754696e−16を確認。この実行の観測値であり一様精度保証ではない。公開光学ラボ https://tatata93.github.io/pikapikaengine/tools/optics-lab.html?v=180c68e と加速ラボ https://tatata93.github.io/pikapikaengine/tools/accelerated-lab.html?v=180c68e で216160B/build4094312d5095c3ddの実WASM操作を確認。reports/2026-11-03-optics-accelerated.md にログ抜粋・入力結果・公開画面を保持。次の実装は曲面/平面と開口の光学交差、held荷重下のtransactional World CCD。単一界面の成功を多面レンズや持続接触の完成と混同しない。
