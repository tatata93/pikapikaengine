# Native sphere × static mesh entry-window受入

2026-11-04 JST。定義線分に沿う球について、初期strict正・closed安全prefix・E補正したstrict負witness・外向き窓幅の四条件を満たす窓を返すNative純粋核を追加した。未知域の幅だけで成功にしない。途中の法線未確定はそのancestorの診断を残し、別点の子区間の証拠で回復できる。元pathとglobal parameterを保持する。

## ローカル受入

- MSVC strict FPの初回ビルド/76群が成功。完全有限入力65件＝18 separated /8 entry_window /20 not_certified /2 initial_penetration /17 invalid_input。最終再実行の全fixture bytesは初回と同一。
- 独立Fraction初回65入力成功。47全path・47初期点・36closed prefix・8width・9witness、558葉/1452audit/17prefix外の島/3840lastMesh成分。自己解析17・改ざん90拒否・label/order独立・Python−O拒否。
- 解析1/4、7/12、3/8と大変位1999/4000を所定幅で囲む。既定幅例の幅上端9.536743164062502e−7。別のwide tolerance例は[0,0.375]であり全8例を1e−6以内としない。
- 実256audit/128partition、255評価/127leaf予算、127frontier、64source全candidate IDs、settings/−0/所有copyと環境拒否を確認。最大容量試験は実時間性能の測定ではない。
- 37CTest/586Node skip0・教材12・構文/Web build、旧owned SDK59model3host/50663model bits・原入力3877bitsと独立mixed62/71負例、旧mesh/single/simulation回帰成功。
- 276既存原本不変。80exports/59source-header・WASM674978B/glue56289B・7通知不変。Web d70b5d9b4436650f/49modules/24entries。CMake/CI登録、教材/原著SVG/研究・法務記録だけを併せて更新した。

統合原出力は[sphere-triangle-mesh-entry-checks/run-20261104-final](sphere-triangle-mesh-entry-checks/run-20261104-final/)と[機械検査summary](sphere-triangle-mesh-entry-local-verification.json)。初回Native原出力・代理試験の凍結hash・独立開発の全試行も各entryディレクトリへ保存した。独立negative-testの最初の構文検査1件は余分な括弧で失敗し、その原出力を保持して修正した。数学照合やfixture数値の調整によるPASSではない。

## 公開受入

コード[058a919](https://github.com/tatata93/pikapikaengine/commit/058a919aa2b0176f58130f92e554693ea9a4f2e6)の[Engine CI41774681284](https://github.com/tatata93/pikapikaengine/actions/runs/41774681284)と[Pages41774680814](https://github.com/tatata93/pikapikaengine/actions/runs/41774680814)は全job/step成功。GNU13.3で37CTest/586Node skip0、独立65入力/17解析/90負例、旧owned59model3hostと数学回帰が再成功した。

新cpp/test各-Wall/-Wextra/-Wpedantic/-Werrorが成功。全entry/mesh/primitive/Interval/core/portable/testをinstrumentしたGNU ASan/UBSan76群、Linux Release/ASan fixture bytecmp、そのsanitized65結果への独立参照も成功。旧pure guard全核69群、C ABI/test sanitizer25群（通常strict archive）も別に成功。既存36warningの診断multiset/出現数は前受入と一致した。LinuxとWindowsの全結果byte一致やWindows sanitizerの成功を推定しない。

73公開ファイル2,078,382Bが当該commit blobと完全一致。新しい原著[模式図](https://tatata93.github.io/pikapikaengine/docs/learn/diagrams/sphere-triangle-mesh-entry.svg?v=058a919)を実公開ブラウザで目視し、[画像](sphere-triangle-mesh-entry-public-browser/diagram.jpg)を保存した。これは新Native核のブラウザ数値実行ではない。

既存engine/sample/assets/tools/entryの80ファイルは前実操作コード656f59dと058a919で全Git blob一致。現checkoutのCRLF→LFが必要なtextだけ明示して同値を監査し、276保護原本のraw不変とも分けた。この不変cohortを根拠に、前回の全25preset＋追加7packet/2Blob=100742bits3896負零と、ゲーム3撃破/boostclip1/停止・21全照会完了/3常駐の実操作記録を継承する。今回再操作したとはしない。73配信byte検査はcohortとのintersectionだけを実fetchした。全工程/有限原log348行（全36warningを含む）/配信/継承根拠/証拠hashを[公開機械受入](sphere-triangle-mesh-entry-public-verification.json)へ保存した。

## 次の最小段と残件

次は[entry SDK接続案](../docs/SPHERE_TRIANGLE_MESH_ENTRY_SDK_PLAN.md)の独立stage/C ABIとNative probeを実装し、所有JavaScript snapshot・手動UIへ段階接続する。6追加export/全64F64内packet等は設計だけで未実装。現在の起動先は既存[ロボット戦闘](https://tatata93.github.io/pikapikaengine/?v=058a919)と[線分guardラボ](https://tatata93.github.io/pikapikaengine/tools/sphere-triangle-mesh-trajectory-lab.html?v=058a919)。新entry核はNative-onlyで、ゲーム接触やWorldには未接続。

窓内単一根・厳密な衝突時刻/特定面/法線/manifold/一般応答、流体/損傷/車両航空鉄道/IK制御/高精度撮像の完成を主張しない。故意allocation・未知work例外注入、自然到達していないparameter_resolution、Windows sanitizerは未検証。本体licenseは未選定で外部solver/素材/課金は追加しない。
