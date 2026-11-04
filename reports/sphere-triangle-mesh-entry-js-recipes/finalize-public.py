from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
v=json.loads((root/'reports/sphere-triangle-mesh-entry-js-public-verification.json').read_text(encoding='utf-8'))
assert v['status']=='PASS' and v['commit']=='578895de6295acf77b2fffd1acb1bd645adc799e'
assert (v['node'],v['ctest'],v['publicFiles'],v['publicBytes'])==(610,38,88,2387746)
resume='再開位置: entry-window所有JS APIコード578895dを公開受入。専用24群/610Node skip0/38CTest、実62model3hostの全DTO105056数値3239負零・原入力4728数値108負零、明示補足mixed65の独立558leaf1452audit3840成分/90負例成功。SDK86exports/61source-header/WASM719410B/glue58933B/runtime91/7通知と312保護原本不変。Web733ad5671fc0b4b3/50modules24entries。Engine41781369977/Pages41781369241全job/step成功、既存36warning診断multiset不変、88公開file2387746Bがfeatureblob一致。実公開固定API3255bits24負零/Native model3312bits20負零、ゲーム1撃破/boostclip1/停止・20全照会完了3常駐/error0を確認。次は[手動entryラボ](SPHERE_TRIANGLE_MESH_ENTRY_LAB_PLAN.md)の実装。[25例と依存調査](../reports/sphere-triangle-mesh-entry-js-next-lab-review.md)も保存済み。詳細は[JS検証記録](../reports/2026-11-04-sphere-triangle-mesh-entry-js.md)。World/一般TOI応答/摩擦・流体/材料損傷/専門車両航空鉄道/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';s=p.read_text(encoding='utf-8');i=s.index('再開位置:');j=s.index('\n',i);s=s[:i]+resume+s[j:];s+='\n追記: '+resume.removeprefix('再開位置: ')+' GNU API/test ASan24群は通常strict核archiveを使い、全entry核76群とRelease/sanitized fixture bytecmpを別工程で確認した。未実行の実fault注入/Windows sanitizer/UI/Worldを受入に含めない。\n';p.write_text(s,encoding='utf-8',newline='\n')
def replace(path,old,new):
 p=root/path;s=p.read_text(encoding='utf-8');assert old in s,path;p.write_text(s.replace(old,new,1),encoding='utf-8',newline='\n')
replace('docs/SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md','実装・ローカル受入済み、公開受入確認待ち','実装・公開受入済み（コード578895d）')
replace('docs/SPHERE_TRIANGLE_MESH_ENTRY_JS.md','実装・ローカル統合検証済み。公開CI/配信の結果は別追記。','実装・公開統合検証済み（コード578895d）。全結果は検証記録を参照。')
replace('docs/SPHERE_TRIANGLE_MESH_ENTRY_LAB_PLAN.md','現在の所有JS APIは実装・統合検証中で、公開受入を完了してから着手する。','所有JS APIはコード578895dで公開受入済み。次はこの手動UIを実装する。')
replace('reports/2026-11-04-sphere-triangle-mesh-entry-js.md','確認待ち。ローカル成功を公開成功へ読み替えない。','''コード578895de6295acf77b2fffd1acb1bd645adc799eのEngine41781369977（job126413438313）、Pages41781369241（build126413439521/deploy126413516133/report126413516156）全job/stepが成功。GNU38CTest/610Node skip0、実owned62model/3hostと全DTO/負零・mixed65 Fraction/90負例、旧SDK回帰が成功した。新test/probe各-Werror、API/test ASan24群（通常strict核archive）と全entry核別76群/Release-sanitized fixture bytecmp、旧guard全核69/API25も成功。既存36warning診断は同一multiset/同数で追加なし。

88選定公開ファイル計2387746Bは当該featureのGit blobと完全一致。実公開固定API3255bits24負零/Native投影3312bits20負零、ゲーム射撃1撃破/boostclip1/停止・20照会全正常/3mesh常駐を確認し、過去操作の継承とは分けた。完全JSON・画面は[public-browser](sphere-triangle-mesh-entry-js-public-browser)。[公開機械集計](sphere-triangle-mesh-entry-js-public-verification.json)へ全job/step・原Run command/全warningを含む有限ログ・配信bytes・原出力のhashを保存。Gitの宣言済みCRLF→LF変換はsource比較の正規化として明記した。

[固定APIを起動](https://tatata93.github.io/pikapikaengine/reports/sphere-triangle-mesh-entry-js-browser/index.html?v=578895d) · [オリジナルゲームを起動](https://tatata93.github.io/pikapikaengine/?v=578895d)。[次ラボの25例と依存調査](sphere-triangle-mesh-entry-js-next-lab-review.md)は未実装UIの準備記録であり、実行したUI結果ではない。''')
p=root/'docs/RESEARCH.md';p.write_text(p.read_text(encoding='utf-8')+'\nentry所有JS公開受入: 578895dのEngine41781369977/Pages41781369241全工程成功。38CTest/610Node・62実owned全bits/負零と明示補足mixed65/90負例、旧回帰・既存36warning multiset不変、API/test ASan24と全核別76/fixture bytecmp成功。88配信2387746B blob一致、新APIとゲームを公開画面で実操作し完全JSON照合。312保護原本/SDK86・61source・719410B・runtime91/7通知不変。新外部資料実読/依存/転載素材/有料service/本体license選定なし。次の手動entry UIは計画・依存調査のみ。\n',encoding='utf-8',newline='\n')
print('Public acceptance documented; next manual entry UI remains unimplemented.')
