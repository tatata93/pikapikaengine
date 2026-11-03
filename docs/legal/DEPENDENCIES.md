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
| Emscripten | 6.0.13、emsdk d7b4130688bfa348392b921ab04015aa15c4f154、共通物理のWeb出力 | 生成ES module 38078BとWASM 184044Bを配布。libc/libc++/例外/allocator/compiler builtinsを含む | 公式SDKのローカル導入。MIT/NCSA、musl、LLVM等の原文とリンクしたmathの個別通知をthird_party/emscripten-6.0.13に保存。固定版・flags・source/artifact/license SHA256とリンクmember一覧はassets/pikapika-simulation.build.json |

教材はシステムフォントだけを利用し、外部CDN・外部フォント・ログインを必要としません。本文・SVG・既存の炎classic scriptは`file://`でも利用できます。追加の浮力操作ラボは実際のエンジンES moduleを読み込むためHTTP/HTTPS配信を必要とし、ページに条件と静的な既知値を併記しています。外部CDNへ計算を委譲していません。

ネイティブビューアとブラウザ版は描画機能が異なります。ブラウザ版はWGSL内のGGX直接光と環境光近似、ネイティブ版は箱の面ごとの色とHLSLの表示変換です。両者の画素一致や同一品質を達成したとは扱いません。

静的配信の選択肢と費用条件の確認は[HOSTING.md](HOSTING.md)に記録します。無償の対象条件と、アカウント全体の請求状態を分離します。

追加依存を採る前に、目的、代替、自作しない理由、ライセンス、版、再配布条件、推移的依存、ソース/バイナリへの混入範囲を記録します。中核実装を置き換える依存は既定の許可に含めません。暗号・安全な通信はOS等の提供する基盤を使う方針です。

共通物理Web出力では、標準コンテナと例外を取り除く再実装より、同じC++原本をコンパイルして検証する方式を採用しました。Emscriptenは完成済み物理ソルバーではなくコンパイラと標準実行基盤です。独自の剛体/静水圧アルゴリズムは置換していません。freestandingへの手動移植と二重実装の代替を比較した経緯は[WASM_DYNAMICS_PLAN.md](../WASM_DYNAMICS_PLAN.md)。SDK本体・SDKが取得したNode/Python・link mapは無視対象build/に置き、公開成果物へ含めません。ブラウザはCDNへ接続せず、同梱WASM/glueだけを読みます。再配布時には[通知と原文](../../third_party/emscripten-6.0.13/NOTICE.md)を保持してください。
