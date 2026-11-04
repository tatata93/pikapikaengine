# World全組flight guardの検証記録

2026-11-05。Native実装の個別検査・独立数学・実機binding・既存回帰・ローカルブラウザ互換をローカル受入。最終summary003と[正式local receipt](world-static-mesh-flight-guard-local-verification.json)は377326B・SHA256 `a402bbe8998c9ecfcd39a420ab776920d906d4e795b0c29a094a0a96beee765c`で同byte。公開GNU/CI/Pagesは別工程であり、公開受入済みとしない。[ガイド](../docs/WORLD_STATIC_MESH_FLIGHT_GUARD.md)・[契約策定時の履歴](../docs/WORLD_STATIC_MESH_FLIGHT_NATIVE_CONTRACT.md)。

## 今回の機能

原Worldと静的meshの所有snapshotから全必要pairを検査し、全組の全時間非接触・全動的seed・費用会計が成功した場合だけ元body順の完全な候補を返す。元World・時計・外力を変更しない。動的ID順の最小mesh seed、その後の残mesh、stable primitive順を保持する。平面は同じ原本のmetricとraw boxの二証拠、球対は元の両半径・両B・明示marginを一度ずつ使用する。全child数値証拠を所有し、非規範的message文字列だけを計数して省略する。

共有primitive audit要求枠1024に対し、E255の4回後はE4へ可視grantし、追加枠が無ければ未照会を保持する。meshの局所設定を予算都合で縮めない。正常exact返却の未使用workは精算できるが、保持要求capacityは実sizeが小さくても返さない。logical payload16MiBはsizeof×要求slotによる会計であり、allocator overhead・一時領域・stack/RSS/heap上限ではない。

## 実行した検査

| 検査 | 実測結果・原本 |
|---|---|
| Native専用試験 | 58群、51有限入力、184実child／184完全DTO再照会比較。`world-static-mesh-flight-guard-checks/run-20261105-candidate-003/` |
| 全入力の分類 | 14認証・26未認証・11不正。失敗時の外側候補はnull。最大188必要組／378全組の保持と未照会tailを確認 |
| 独立数学・所有・会計 | 実184child＝flight96・metric34・plane box33・sphere box21、候補32body、減額grant14、既知root精錬102846。12自己試験・138改変拒否（Python -O拒否含む）・label/order独立。`world-static-mesh-flight-guard-reference-development/run-008/` |
| Actual x64 binding | 最終 `world-static-mesh-flight-guard-binding-development/run-010/audit.json`。7dumpbin実行、位置差・dot・lengthのobject→linked全body一致、8命令改変拒否、actual strict compile/link記録と5安定性検査 |
| 旧Native/SDK保持 | 旧W1全report/state、simulation、W2 supportedの3出力が変更前とbyte一致。旧SDK20入力4520数値bits・24負零一致。`...checks/run-20261104-legacy-after-001/` |
| 既存SDK全交換 | simulation、flight Native/raw WASM/独立参照/所有JS/手動preset、entry所有JSの全7工程成功。flight183＝173実model＋10host拒否、entry62実model＋3host拒否。`...checks/run-20261105-sdk-regression-001/` |
| 全体回帰 | Release 46CTest、684Node・skip0、構文、Web build `25509ed4cc1d87e4`／54modules／26entries。`...checks/run-20261105-regression-003/` |
| 未設定構成 | actual Debug profile0でchild0・原本capture無し・候補無し・World保持。`...checks/run-20261105-debug-refusal-002/` |
| 実ローカルUI | 原著図の上下view、教材の新図・説明と1120×800画像load完了、更新SDKの既存ゲーム1撃破・boost・停止。35照会＝checked＝validated＝completed35、最大clip1・常駐3mesh・error0。`world-static-mesh-flight-guard-local-browser/observations.json` |

独立数学のbox座標は真の二次全域extrema±Bを検査し、その後のrecorded boxからのinteger-RN/root包含を別に検査する。全座標構築ASTの全RN選択肢を列挙したという意味ではない。実返却の由来はNative完全DTO再照会、実機接続は別binding監査である。自然なallocator例外・nonreturn故障注入を実行したとはしない。

## ビルドと配布物

actual core.cppとdynamics/continuous_world/新guardをsource固有strictに固定した。対応候補のx64平方根はSSE2 intrinsicを使用し、未対応targetの既存std::sqrt fallbackは保持する。構成identity `20a10657c454ced613172d9813637ee60a1108a91bc26b83243a1e094b80907e` はself-measured executable hashではない。

最終Release検証exeは1278976B、SHA256 `ae8d1935bbe048186435c2e5f1947e14d214de2838520a729ed69c43c11810db`。core.objは558045B、SHA256 `78cc117e4ef9f06fad505ca17d9aefa49b42fb3864b0bf1e8fd507d5aefbbbfe`。3leafの命令dataflowとactual callerのcall先・FMA/x87不使用を調べた。平面減算・閾値加算・比較順は固定sourceとactual strict/non-LTO commandからの判断であり、caller全体のsymbolic機械証明ではない。監査用exeのみNOREF/NOICFで対象symbolを保持した。

正式SDKを既存Emscripten6.0.13で再生成した。92exports／67source-header／32TU／runtime91／7通知は保持し、source hashの変更はcore.cppだけ。WASM801064B、SHA256 `6a0730e2cc30c82115c706a9c433ec3a4bb808f99850ece7a0db9acee4b0bd23`。glue61661Bは旧byte不変。新World guardのWASM exportやJS数値入口は追加しない。取得したIntel/Microsoft/GCC一次資料の実読範囲は [primary-sources.json](world-static-mesh-flight-guard-primary-sources.json)。資料・構成identityを実object命令の代用にしない。

## 失敗と訂正の履歴

元49入力はname・型・全bits・配列順を保持した。初回の専用試験では、static追加後の共通保持枠不足を成功と期待して停止した。そのほか最小Hの旧held内点不足、stable pair順のdependency reason、近接meshの旧held leaf予算不足も、実出力と独立参照に基づいて期待だけを訂正した。元の入力やstrict条件は変えず、別2入力としてE128のstatic完全候補と、遠いmeshでmetric成功/raw box失敗を調べる例を追加した。初回rawはcandidate-001に保持する。最終51入力fingerprintは `7a2804d8791140722a9ffb7cba3ab42d0274cfa2947789d1c9a5e1fbe2256e37`。candidate-002とCLI修正後003の全fixtureは同byte（SHA256 `d82aa9629fef1fc030f4176ac74d0dfbb026f1a4530c53fb9a0eefe31f80bddb`）。

CTest初回・2回目は新試験へ空文字引数を渡すCMake登録でUsage失敗し、既存45件は成功した。COMMAND_EXPAND_LISTSだけでは除けなかったため、既存通常実行の`--run`別名と、常に非空の構成別引数へ訂正した。入力・数学条件は不変。新1件の実CTest成功後、fresh全46件が成功した。旧2回の失敗rawはregression-001/002へ保持する。

実機監査ツール初期のmap pseudo-symbol/破棄COMDAT・変数shadowing・namespace選択失敗はbinding-developmentの全attemptへ保持し、製品数学の失敗へ混ぜない。旧leafのlink除去には検証exeだけのNOREF/NOICFを使用した。SDK初回sandbox実行拒否、旧probeの`--fixtures`指定漏れ、独立checkerの初期構文失敗も原記録を保持し、訂正後のfresh実行と分ける。

UI収集では新tab attach・lesson bindのtimeoutとkernel resetを保持した。数値処理終了後のbounded bindが返り、hash移動だけでは旧教材documentが残ることをDOMで確認した。明示reloadと実scroll/screenshotで新図を確認し、更新したWeb cohortで別ゲーム操作を行った。最初の旧sphere図のscroll位置を写したlesson.jpgも残し、新図はlesson-world-top/text.jpgへ別保存した。UI表示を数値guard実行の代用にしない。

## 未完

GNU13でのactual命令・3TU Werror・全依存source ASan/UBSan・別構成identityだけを除いた全fixture比較、公開CI/Pages/配信byte・公開実ブラウザは未確認。GNUレシピは作成と構文・比較器の正負例のみで、実行成功は主張しない。

World advance/commit、mesh TOI応答、一般接触と摩擦支持、材料の弾塑性損傷、CFD、専門車両/航空/鉄道モデル、IK/制御、光学撮像は後続。原著図と文を追加し、既存ゲーム素材・他チャットの変更を保持する。外部solver/code/画像/fontの取込・課金/有料契約・フォーラム/メール操作はなく、本体license未選定を維持する。


最終集計はsummary001で、旧2HTMLの混在改行を一律LF/CRLFだけで再構成しようとして停止した。BASE041のbodyをCRLFへ変え、生成inline import-mapの行末だけLFへ戻すと、保存済raw hashへ完全一致することを確認した。本文の例外を許さず、その有限な再構成だけをcollectorへ追加した。summary002では旧raw SDKのoptimizedPythonRejectedがboolではなくPASS/非零exitCodeを持つobjectであるため停止し、実schemaへの検査だけを訂正した。旧receipt・入力・数学・製品sourceを変えず、fresh summary003の全718証拠集計が成功した。001/002のstdout/stderr/failureも同梱する。
