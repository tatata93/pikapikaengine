# 2026-11-04 明示B・marginによる平面box coverage

Native専用の新核をローカル・公開受入した。初回feature a909323のGNU試験補助警告による失敗と、testのみ修正したfeature 4b5bf37の全工程成功を区別して記録する。元World/SDK/gameの数値経路は変更しない。

## 実装と条件

必須4引数 `Input(sphere,plane,position_error,contact_margin)` で、位置誤差Bとsolverのmarginを推測せず受け取る。全時間座標箱へBを加え、raw法線の左結合dot/offset、別のr+margin、gapを自作Intervalで囲む。各演算nodeの実数またはbinary64 RN-evenの族を含め、同じ結合順序のFMA収縮も包含する。任意再結合・fast-math・FTZ/DAZ・拡張精度・実World全compilerを認証したとはしない。

全closed partition・全返却Evaluation・未照会tail/current・原値bitsを所有する。最大255評価/128leaf/depth32で、全leafのstrict positiveと完全被覆だけをcertifiedとする。誤差Bは宣言値であり、actual bodyの誤差上限・metric分離の別証拠・同じmargin・compilerとの対応・全pair・候補検査は後続World gateである。sqrt/metric/伝播を新核内で呼ばない。接触応答・流体・材料損傷・専門車両/航空/鉄道・IK/制御・任意高精度撮像の完成ではない。

## ローカル実測

| 検査 | 実結果 |
|---|---|
| MSVC strict standalone / CMake統合 | 新74群・67有限入力、44CTest成功 |
| 有限入力の分類 | certified20 / not_certified20 / invalid27 |
| 実public valueの由来 | 1306全Evaluationを再照会し、15672端点bits・2496負零端点一致 |
| 独立全域包含 | 全7836I、3918座標の厳密二次極値±B、2612固定AST corner、21034 node-pairs |
| 独立metadata | 750partition / 149frontier / 5current、最大255audit / 128leaf / 127tail |
| 非自明な認証 | B=.125の放物線35audit/18leafで分割認証 |
| 参照の自己検査・改変 | 16自己群 / 65拒否（Python -O含む）、label/order非依存 |
| 既存Web | 684成功・skip0、構文、build cd45c7f1ac2ba5e5 / 54module / 26entry |
| 既存保持 | 369raw原本、26生成HTML、92exports/67source-header/32TU/runtime91/7通知 |

Canonical fixtureは676814B SHA256 `0dafa4e430ad34958a25795b07a8785972cdf9dd6071cf2f24a8b1a676493cc1` でstandaloneとbyte一致。入力fingerprintは `2d660f51cb84c0bdbc8f8f9e3d26bf59caf92d53878bc12c0bf2ebce72408ec9`。実real-positiveだが個別RNでdotが0になるlost-low-term、FMA/個別積の差、near-unit metric/raw両方向の反例、margin閾値、巨大offset相殺、subnormal半加速度、環境拒否と復帰を検査した。

MSVC19.51 x64のsizeof×返却capacity観測は 59600B。Resultのinline snapshotは二重加算しない。これはallocator overhead/一時領域/stack/RSS/実heap使用量の上限ではない。全44CTestのrealは155.60s、捕捉wall155.65sで、一般性能の保証ではない。FTZ/DAZ/丸めmodeの限定probeを全target検証と呼ばない。

## 証拠と試行履歴

[ローカル集計](accelerated-plane-box-coverage-local-verification.json) と `accelerated-plane-box-coverage-checks/run-20261104-{native,regressions,reference,summary}-001/` に元stdout/stderr/実command/前後sourcehashを保持する。Native初回standalone・canonical・数学包含は成功。参照run003はcheckerと16self成功後、負例の末尾が既certifiedで変異にならないselector誤想定で停止した。製品や数学基準を変えず対象を未認証leafへ訂正し、run004の61件成功を保持、予定の4追加controlを含む最終run005/親canonicalで65件を再確認した。数学的に有効な広いdistanceと人工nonreturnの整合正例は、実public valueの由来や自然C++故障注入とは区別する。

教材のanchor追加用単発コマンドにshell引用のSyntaxErrorがあり、ファイル変更前に停止した。再利用可能な `lesson-anchor.py` で訂正して表示を確認した。baseline説明のHTML分類も受入前に訂正し、教材本文は生成26entryの外にあることを実hashで確認した。製品失敗として付け替えない。

原著SVG・教材の実表示は `accelerated-plane-box-coverage-local-browser/` の5capture＋observationsに保存。新APIのブラウザ照会やWorld接続の検証とはしない。

## 調査・配布

[Microsoft /fp](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170) と [GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) を実読し、収縮・再結合・環境・中間精度の境界を確認した。外部code/図/本文を移植せず、新package/有料service/本体license選択はない。[調査原本](accelerated-plane-box-coverage-primary-sources.json)、[FP監査](../docs/WORLD_PREDICATE_FLOATING_POINT_AUDIT.md)、[契約](../docs/ACCELERATED_PLANE_BOX_COVERAGE.md)。SDK/WASMは既存配布物を維持する。

## 公開受入（feature 4b5bf37）

[公開集計](accelerated-plane-box-coverage-public-verification.json)は、原acceptanceをbyteそのまま保存した。Engine [41839162531](https://github.com/tatata93/pikapikaengine/actions/runs/41839162531) の全24段とPages [41839160595](https://github.com/tatata93/pikapikaengine/actions/runs/41839160595) の3jobが成功。GNU新3TUのWerror、全5TUのASan/UBSan、通常/計装fixtureの同一Linux内byte比較とそれぞれの独立67入力・7836I・16自己/65改変拒否が成功した。44CTest/684Node skip0と既存回帰も成功し、旧48GNU警告は診断・file/line/columnのmultisetが同一、新診断0である。新helperのWASM APIやMSVC/GNU全DTOのbit parityを確認したという意味ではない。

完全feature blobに対し100件2937015Bが一致した。内訳は99PagesとGitHub完全commit workflow原本1件であり、100Pagesとは呼ばない。Web build cd45c7f1ac2ba5e5/54module26entry、SDK92exports/67source-header/32TU/WASM800982B/glue61661B/runtime91/7通知は保持。原著図・教材を実公開で表示し、既存ゲーム2撃破・boost・pause・20照会すべてchecked/validated/completed・3常駐mesh/error0を確認した。これは既存ゲーム互換のみで、新Native helperのブラウザ数値照会やWorld接触適用ではない。9captureは `accelerated-plane-box-coverage-public-browser/` に保存した。

初回a909323のEngine41835425148/job126592955091は、GNU13の新test `named` 補助関数の一時文字列に対するdangling-reference診断で第22段を失敗した。新ASan/UBSan部分と最終WASM工程はそのrunで完了していない。警告抑制や数値条件変更をせず、名前引数を値のstring_viewへ変更・include追加・診断文字列変換の3箇所だけ修正した。別のMSVC74群、元676814B fixtureのbyte一致、現featureの新GNU全工程をそれぞれ保存し、最初のlocal receiptのhashを書き換えない。[修正記録](2026-11-04-accelerated-plane-box-coverage-ci-fix.md) と失敗全文log・旧100配信・旧9captureも保持した。

UI収集では初回featureのexpanded JSON読取3000ms timeoutと、修正feature最初のSVG screenshot取得失敗を各development/run-001・003へ保存した。AX再同期後の実取得を正式captureとし、これらをモデル失敗・数学故障注入の成功と数えない。全status001〜004、bytes001〜002、summary001の元command/stdout/stderrを公開証拠へ含める。今回追加の外部資料実読・依存・solver・素材・有料service・本体license選択はない。宣言Bの条件付きNative証拠という範囲を維持し、実WorldのB導出/compiler/metric/全pair/候補/応答は後続gateである。
