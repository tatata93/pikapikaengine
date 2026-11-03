# 依存と配布境界

確認日: 2026-11-03。外部の完成済みゲームエンジン、数学・物理・音響ライブラリは導入していません。

| 項目 | 版・利用箇所 | 製品へ混入する範囲 | 条件・確認状態 |
|---|---|---|---|
| ECMAScript / DOM / Canvas 2D | 利用者のブラウザ標準API | ブラウザ自体を配布しない。教材のJSは自作 | 本文/検索/炎は外部ランタイムなし。共通C++のWASM実験には下記Emscripten標準ランタイムを含む |
| WebGPU / WGSL | ブラウザ試作のGPU API・シェーダー | ブラウザのGPU実装を同梱しない。自作WGSLをJS内に含める | WebGPU 2026-09-15、WGSL 2026-10-26のW3C Candidate Recommendation Draftを確認。WebGL2の実装経路はこの版にない |
| Web Audio | ブラウザ試作の音声出力 | API実装を同梱しない | 標準API。音声開始にはユーザー操作が必要 |
| Node.js | 実行環境でv24.14.1を確認。ローカル配信・検証 | ブラウザ配布物へ同梱しない | `node:test`、`node:assert`、`node:vm`等の組込みのみ。npm外部パッケージなし。Node本体を再配布する場合は同梱ライセンス別途確認 |
| Python標準ライブラリ | ローカル3.12.10、区間演算の独立検証 | `fractions.Fraction`、整数演算、標準の入出力のみ。製品にPythonやパッケージを同梱しない | IEEE bitを厳密有理数へ復号する検証用。外部数値ライブラリの追加なし。SDKによるコンパイラ起動用Pythonとは用途を分ける |
| C++標準ライブラリ / MSVC | MSVC 19.51、共通C++20コアとWindows試作 | 標準ライブラリとランタイムのリンク方式による | インストール済みツールによるビルドを実施。インポートDLL一覧・必要な再頒布条件の最終監査はWindowsバイナリ配布の残課題 |
| Windows SDK / DirectX 12 / DXGI / D3DCompiler | SDK 10.0.26100。Windowsビューアの描画、HLSL実行時コンパイル | OS APIへリンク。SDKやコンパイラ本体をブラウザへ配布しない | `platform/windows/viewer.cpp`をコンパイル・起動済み。SDKの配布可能ファイル一覧と必要DLLの同梱可否は別途確認 |
| CMake | 4.3.3、ビルド用 | ビルドツール本体を製品へ同梱しない | 使用版を記録。ツール本体を再配布する場合はCMake本体と同梱コンポーネントのライセンスを別途確認 |
| Clang / WebAssembly | CI Ubuntu clang18.1.3、freestanding wasm32 | 自作portable.cpp由来の650B WASMのみ。-nostdlib、外部ランタイムなし | コンパイラは製品に同梱しない。4関数のC ABIをnative/Webで実使用。ビルド来歴・SHA256はassets/pikapika-core.build.json。LLVMコンパイラ本体を再配布する場合はApache-2.0 WITH LLVM-exception等を別途確認 |
| Qt | 未導入 | なし | 将来のGUI候補。モジュールと配布形態ごとの条件確認が必要 |
| Emscripten | 6.0.13、emsdk d7b4130688bfa348392b921ab04015aa15c4f154、共通物理・光学・motion・位置skinning・派生meshのWeb出力 | 現在の派生mesh接続版は生成ES module 50029BとWASM 590964B、65 exports。libc/libc++/例外/allocator/compiler builtinsを含む | 公式SDKの既設固定版を継続利用。MIT/NCSA、musl、LLVM等の原文とリンクしたmathの個別通知をthird_party/emscripten-6.0.13に保存。固定版・flags・source/artifact/license SHA256とリンクmember一覧はassets/pikapika-simulation.build.json。ローカルで全source/artifact/license hashを照合済み。今回公開CI/Pagesの結果は最新reportsで別途確定 |

教材はシステムフォントだけを利用し、外部CDN・外部フォント・ログインを必要としません。本文・SVG・既存の炎classic scriptは`file://`でも利用できます。追加の浮力操作ラボは実際のエンジンES moduleを読み込むためHTTP/HTTPS配信を必要とし、ページに条件と静的な既知値を併記しています。外部CDNへ計算を委譲していません。

ネイティブビューアとブラウザ版は描画機能が異なります。ブラウザ版はWGSL内のGGX直接光と環境光近似、ネイティブ版は箱の面ごとの色とHLSLの表示変換です。両者の画素一致や同一品質を達成したとは扱いません。

静的配信の選択肢と費用条件の確認は[HOSTING.md](HOSTING.md)に記録します。無償の対象条件と、アカウント全体の請求状態を分離します。

追加依存を採る前に、目的、代替、自作しない理由、ライセンス、版、再配布条件、推移的依存、ソース/バイナリへの混入範囲を記録します。中核実装を置き換える依存は既定の許可に含めません。暗号・安全な通信はOS等の提供する基盤を使う方針です。

共通物理Web出力では、標準コンテナと例外を取り除く再実装より、同じC++原本をコンパイルして検証する方式を採用しました。Emscriptenは完成済み物理ソルバーではなくコンパイラと標準実行基盤です。独自の剛体/静水圧アルゴリズムは置換していません。freestandingへの手動移植と二重実装の代替を比較した経緯は[WASM_DYNAMICS_PLAN.md](../WASM_DYNAMICS_PLAN.md)。SDK本体・SDKが取得したNode/Python・link mapは無視対象build/に置き、公開成果物へ含めません。ブラウザはCDNへ接続せず、同梱WASM/glueだけを読みます。再配布時には[通知と原文](../../third_party/emscripten-6.0.13/NOTICE.md)を保持してください。

今回の区間光路・独立屈折率区間・法線支持照会は原著C++と既存の自作intervalを使います。
外部の交差/光学/接触ソルバー、実材質データ、追加SDK・npm/Python packageは導入していません。
独立検証はPython標準のFraction/整数平方根と、既設Native/Emscriptenの実行を利用します。
製品へPythonや検証用buildディレクトリを同梱せず、既存Emscripten標準ランタイムの配布条件は引き続き適用します。


W2の追加（2026-11-03）: RATTLE候補、private有限vn支持選別、全区間軌道監査とWorld driverも原著C++である。
外部のMoreau/Stewart–Trinkle/RATTLE実装、LCP solver、新SDKやnpm/Python packageは導入していない。
独立検証は既存の自作interval、C++標準機能、Python標準Fraction、既設MSVC/Emscripten6.0.13を利用する。
WASMの標準ランタイム・例外・allocatorの通知と配布条件は従来どおり保持する。
今回artifactのbytesは再生成結果であり、最終全tests・source/artifact/license hash照合と公開成功は根本で確定する。
手動WorldラボのUI/Canvas/SVGと教材17記事は自作で、外部の画像・フォント・素材は追加していない。
engineライセンス未選定を維持し、数式の参照を論文コードや図の再配布許諾と読み替えない。

静的複数面の最近傍選択も原著C++と自作interval/既存の単一面核を使用する。新SDK・solver・npm/Python packageの導入はない。PBRTは契約と丸め誤差の一次資料として参照し、その実装・図・処方データは取り込まない。新ラボ/教材/SVGは原著で、既設Emscripten6.0.13標準ランタイムの配布通知と未選定のエンジンライセンスを維持する。


有限rayの幾何点像核/合成レンズprofile/ラボも原著C++/JSと既存の自作区間核を使用する。追加ライブラリ・SDK・npm/Python package・実レンズデータはない。独立検証にはPython標準Fraction、既設MSVC/Emscripten6.0.13を使い、配布物の標準ランタイム通知と未選定のエンジンライセンスを維持する。

指定経路の区間偏光POWERと共通sqrtも原著C++/JS/Pythonで実装。外部偏光/区間/行列ライブラリ、新SDK、npm/Python packageを追加していない。既存標準Fractionによる独立検査を使用し、Python/検証buildは製品配布しない。既設Emscripten6.0.13の標準ランタイム通知を保持し、エンジンのライセンスは未選定。参照数式と他者の実装・図・データの利用許諾は区別する。

有限の明示POWER packet核・レンズ2経路profile・ラボも原著C++/JS/Python。新ライブラリ/SDK/package/材質処方の導入はない。既設Emscripten6.0.13の標準ランタイム通知と未選定のエンジンライセンスを維持する。独立検証は既存MSVC/Emscripten、Python標準Fractionのみで、検証用buildは製品へ同梱しない。

M2骨格キー・FK・portable motion v1の編集/保存読込・CLIも原著C++/JS。外部の行列/アニメーション/IKライブラリ、SDK、npm/Python package、既存モデル/モーション素材を導入しない。独立検査は標準Python Fraction/Decimalを使用し、binary64の点近似をinterval包含保証と混同しない。既設MSVCとEmscripten6.0.13を使用し、配布runtime通知と未選定のエンジンライセンスを保持する。

位置のみのskinning核も原著C++。3×3 affine inverseと重み付き行列blendを自作し、既存motionとC++標準ライブラリを使う。独立参照は標準Python Fractionによる別構成4×4 inverseと有理weight比。外部数学/animation libraryや新SDK/package/素材は追加しない。Native/standaloneに加え共通SDKへ4exportsを接続し、計63exportsの実WASMと自作Canvas操作ラボから使用する。JSにはinverse/LBS/FKの代替実装を置かない。確認用JSON出力とbinding原本codec/CLI往復を区別し、renderer/GPU skinningも後続とする。既存runtime通知・未選定engine licenseを保持する。

今回SDK接続の独立検証も既存Node組込み機能とPython標準Fractionのみ。65fixtureは60実C++モデル結果と5host交換拒否へ明示分類し、128oracle/retryを含む5288出力数値bitsを比較した。検証用Python/Native executable/ignored build記録を製品へ同梱しない。既存7件のEmscripten通知原文はbyte不変で、新たな外部runtime・モデル・画像・フォントの導入はない。ライセンス未選定のエンジン原著部分と、同梱標準ランタイムの再配布条件を混同しない。

整列警告修正も最大4 influenceの原著bounded insertionで、新しいsort/数学/animation libraryを追加しない。ASanの修正前後69群とpositive control、全652群/28CTest・Node323skip0、33順列、main5288bitsと既存24回帰をローカルで確認した。sanitizer検証を任意入力の安全性証明や製品に追加したruntimeと扱わない。WASM SHA256は`4f0a2bfb026dafe5e4cb8929a5fca37d3b9c2e9b24e096bece9419efdc2a7812`。次の[owned binding計画](../SKIN_BINDING_PLAN.md)は提案・未実装で、新外部依存を導入する計画ではない。本体ライセンス未選定と既存配布通知を維持する。
## 所有skin binding原本

`engine/strict-json.mjs`、`engine/skin-binding.mjs`、`skinning_io`とNative CLIは原著で、JSON/hash/assetの外部packageを導入しない。UTF-8、binary64変換、排他的file作成は既設のJS/C++標準libraryとOS機能を使う。FNVは診断/索引だけで全geometry比較を省略しない。新IOはNative/authoring用で、既存共有SDK63のcompile source配列へは追加しない。WASM574261B/既存glueと7runtime通知は変更しない。Linux sanitizerは既存標準runnerで検証用binaryを生成するだけで、配布runtimeや有料serviceを追加しない。

派生mesh初段（Native実装・ローカル受入済み）は原著Native C++と既存interval/sqrt核、C++標準ライブラリだけを利用する。外部の数学/描画libraryやpackageは追加しない。主WebSDKへ新kernelをまだ組み込まず、既存の7通知・配布WASM/glueを保持する。Float32局所geometryとnormal監査の条件を、GPU実装全体の保証へ拡張しない。

派生mesh SDK接続（2026-11-03）: 原著C++核を既存Emscripten6.0.13のstrict flagsで共有SDKへ含めた。全53 source/header・7通知・2artifactを照合する。新package/外部solver/素材は追加しない。Native原本parser/CLIはSDKへ含めず、JSは交換・検査・snapshotコピーだけを行う。新WASM SHA256は`67daefd24c39af1aefa516d28b35c11808684604bed457c1e16eed15b64e8f73`。公開受入は今回のreportsで別に確定する。既存7通知と未選定の本体ライセンスを保持する。

派生meshの任意3D表示（2026-11-04 JST、実装中・公開未検証）は既存のブラウザWebGPU/WGSL経路を拡張する。opaque tokenの所有copy、GPU upload、validation/queue完了確認、resource解放とUIは原著JS。外部renderer/数学library/ポリフィル、新SDKやnpm/Python package、素材を導入しない。共有SDK65exportsのC++/ABI仕様は変更せず、既存配布物を利用する。WASM/glueと既存7通知のbyte不変は今回の最終照合で確定し、未照合の時点で保証済みとはしない。ライセンス未選定の原著部分と既設Emscripten標準runtimeの配布条件を区別し、Python/mock GPU/検証buildを製品に追加した依存と数えない。

手動3D表示90b1afeの最終照合: SDK65の53source/header・7通知・2artifactとmanifestはbyte不変。外部package/素材の追加なし。公開CI/Pagesと15操作/配信17ファイルを確認し、証拠はreports/2026-11-04-derived-render.md。本体ライセンス未選定を維持する。

Node段階計測は原著JSと既設Node標準perf_hooks/crypto/assert/fs/osだけで実装する。追加npm/Python package・SDK・solver・外部profiler/runtimeは導入しない。診断wrapperは元のC++/WASM/engine runtimeを書き換えない。測定用Nodeやraw build記録を製品runtimeとして同梱するものではなく、既存7通知と本体license未選定を保持する。最終source/artifact hash不変は検証記録で確定する。
