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

コードpush後にGNU新cpp/test各-Werror、全entry/mesh/primitive/Interval/core/portableをinstrumentしたASan/UBSan、Linux Release/ASan fixture bytecmp、独立参照、全CI/Pages工程、73公開ファイルのblob一致を確認する。ここはまだ未確定。ローカル模式図の実ブラウザ表示は確認済みで、新Native核のブラウザ実行を意味しない。

## 次の最小段と残件

公開受入後に有界C ABI・所有JavaScript snapshot・手動UIを段階接続する。現在の起動先は既存[ロボット戦闘](https://tatata93.github.io/pikapikaengine/)と[線分guardラボ](https://tatata93.github.io/pikapikaengine/tools/sphere-triangle-mesh-trajectory-lab.html)。新entry核はNative-onlyで、ゲーム接触やWorldには未接続。

窓内単一根・厳密な衝突時刻/特定面/法線/manifold/一般応答、流体/損傷/車両航空鉄道/IK制御/高精度撮像の完成を主張しない。故意allocation・未知work例外注入、自然到達していないparameter_resolution、Windows sanitizerは未検証。本体licenseは未選定で外部solver/素材/課金は追加しない。
