from pathlib import Path
root=Path(__file__).resolve().parents[2]
def update(path,old,new):
 p=root/path;s=p.read_text(encoding='utf-8');assert old in s,path;p.write_text(s.replace(old,new,1),encoding='utf-8',newline='\n')
resume='再開位置: entry-window所有JS APIをローカル受入。専用24群/610Node skip0/38CTest、実62model3hostの全DTO105056数値3239負零・原入力4728数値108負零、出自付きmixed65の独立558leaf1452audit3840成分/90負例と旧SDK回帰成功。SDK86exports/61source-header/WASM719410B/glue58933B/runtime91/7通知と312保護原本不変。Web733ad5671fc0b4b3/50modules24entries。実local固定API3255bits24負零/Native model3312bits20負零、ゲーム1撃破/boostclip1/停止・20全照会完了3常駐。公開CI/Pages/87配信は確認待ち。次は[手動entryラボ](SPHERE_TRIANGLE_MESH_ENTRY_LAB_PLAN.md)。詳細は[JS検証記録](../reports/2026-11-04-sphere-triangle-mesh-entry-js.md)。World/TOI/ゲーム接触・一般応答、流体/材料損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';s=p.read_text(encoding='utf-8');start=s.index('再開位置:');end=s.index('\n',start);s=s[:start]+resume+s[end:];s+='\n追記: '+resume.removeprefix('再開位置: ')+' 初回decoderは合法なnorm²の負subnormal下端を過剰拒否し訂正、専用試験の無変異frontier操作も試験のみ訂正。失敗原出力を保持し、Native核/モデル入力は変えない。未返却workの人工packetを故意fault実注入とせず、Native commit後のdecoder拒否はrollbackを保証しない。\n';p.write_text(s,encoding='utf-8',newline='\n')
update('docs/SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md','2026-11-04 JST。**計画のみ・未実装**。','2026-11-04 JST。**実装・ローカル受入済み、公開受入確認待ち**。[実装契約](SPHERE_TRIANGLE_MESH_ENTRY_JS.md)と[実測記録](../reports/2026-11-04-sphere-triangle-mesh-entry-js.md)を参照。以下は実装前に定めた受入計画であり、現在の再開位置はPLANを優先する。')
update('docs/SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md','本計画のJS所有APIは未実装のまま。','本計画のJS所有APIは実装・ローカル検証を完了し、手動編集UIは後続とする。')
update('docs/SPHERE_TRIANGLE_MESH_ENTRY_JS.md','実装・統合検証中。','実装・ローカル統合検証済み。公開CI/配信の結果は別追記。')
update('docs/SPHERE_TRIANGLE_MESH_ENTRY_JS.md','独立参照へ渡す計画である。','独立参照へ渡して成功した。全model105056数値/3239負零、originalInput4728数値/108負零が一致し、独立558葉/1452audit/3840成分と90改ざん拒否を確認した。')
update('docs/learn/index.html','所有JavaScript API（検証中）','所有JavaScript API')
for path,text in [
 ('docs/RESEARCH.md','entry所有JSローカル受入: 専用24群/610Node skip0/38CTest、実62model3host・全DTO/負零と出自付きmixed65 Fraction/90負例が成功。新法線/幾何solverをJSへ追加せず、交換metadata/所有と独立数学を分けた。312保護原本/SDK86・61source・719410B・runtime91/7通知不変、原著図を実ブラウザ目視。初回の合法負subnormal過剰拒否と無変異test、browser比較のenum投影漏れを記録し、核や数学原本は変えない。公開受入は次段。'),
 ('docs/legal/DEPENDENCIES.md','entry所有JS配布監査: 86exports/61source-header/719410B WASM/58933B glue、runtime91/7通知は前ABIからraw byte/hash不変。新package/solver/外部素材/有料serviceなし。本体license未選定。'),
 ('docs/legal/REFERENCES.md','entry所有JS検証: 新しい外部資料実読/転載なし。62実decoderモデルを元Native全field bitsへenumだけ投影して比較し、host3を明示補足したmixed65の独立Fraction/90負例を成功。ブラウザ固定例は実Node/Native比対と区別して記録する。'),
 ('docs/legal/ASSETS.md','entry所有SVGをローカル実ブラウザで目視し、全文字・矩形配置を確認。スクリーンショットはreports/sphere-triangle-mesh-entry-js-local-browser/diagram.jpg。図は性能/数学包含の実測ではない。')]:
 p=root/path;p.write_text(p.read_text(encoding='utf-8')+'\n'+text+'\n',encoding='utf-8',newline='\n')
print('Local documentation updated; public acceptance remains pending.')
