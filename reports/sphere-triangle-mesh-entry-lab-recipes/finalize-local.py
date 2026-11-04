from pathlib import Path
from hashlib import sha256
import json
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-entry-lab'
v=json.loads((root/f'reports/{prefix}-local-verification.json').read_text(encoding='utf-8'));assert v['status']=='PASS'
def digest(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':sha256(b).hexdigest()}
partial=root/f'reports/{prefix}-local-browser-attempt-001';files={p.relative_to(root).as_posix():digest(p) for p in partial.glob('*.json')}
assert len(files)==16
attempts={'schema':1,'scope':'Driver/observation attempts, not changes to the numerical model.',
 'browserDeadline':{'status':'INCOMPLETE','partialModelPackets':16,'files':files,'reason':'A 25-case UI orchestration call exceeded its30s tool deadline; one tab rebind then timed out. Inventory and a new browser2 tab recovered. Five-case batches with immediate per-case manifests completed all25. No application/helper/SDK change was made.'},
 'hiddenErrorObservation':{'status':'CORRECTED','originalManifest':f'reports/{prefix}-local-browser/presets-initial-error-observation.json','failedSummary':f'reports/{prefix}-checks/run-20261104-initial/summary-commands.json','reason':'The collector read innerText of a hidden prior host-error node into the last successful-model manifest. The visible model result was correct. Its error isVisible=false was verified by revisiting that preset; only the observational error field was corrected. Original manifest and failing summary streams are preserved; no acceptance condition or result/fixture changed.'}}
(root/f'reports/{prefix}-attempts.json').write_text(json.dumps(attempts,indent=2)+'\n',encoding='utf-8')
resume='再開位置: 手動entryラボをローカル受入。25例=24実model/65面host拒否1、専用21群/631Node skip0/38CTestとfresh所有SDK62model3host/mixed65 Fraction/90負例が成功。実ローカル全25例・追加13packet・2実Blob保存=180165数値bits5061負零、全256audit/128partition/127frontier/64IDと所属/初期点prefix/失敗祖先を確認。ゲーム1撃破/boostclip1/停止・22全照会完了3常駐。314保護原本/SDK86exports61source-header719410B/glue58933B/runtime91/7通知不変。Web6aa725ed1898f4e9/51modules25entries。公開CI/Pages/93配信は確認待ち。[検証記録](../reports/2026-11-04-sphere-triangle-mesh-entry-lab.md)を参照。World/一般TOI応答/摩擦・流体/材料損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';s=p.read_text(encoding='utf-8');i=s.index('再開位置:');j=s.index('\n',i);s=s[:i]+resume+s[j:];s=s.replace('\n\n進行中: 手動entryラボの実装を開始。25代表原入力/実API一回/全診断/strict JSON保存、全partitionとinitial/windowの別表示、編集・loader世代の消去を追加する。基準は公開受入66c6cf9、314保護原本/旧24HTML生成部を保存。UIの実行・公開受入は未確認。','');s+='\n追記: '+resume.removeprefix('再開位置: ')+' 自動操作の30秒上限とhidden過去errorを観測した集計失敗は元データ保持後にdriverだけを訂正し、model/kernelや検証条件を変えず成功した。人工環境/未返却work表示を自然実行/実fault注入へ混ぜない。\n';p.write_text(s,encoding='utf-8',newline='\n')
def replace(path,old,new):
 p=root/path;s=p.read_text(encoding='utf-8');assert old in s,path;p.write_text(s.replace(old,new,1),encoding='utf-8',newline='\n')
replace('docs/SPHERE_TRIANGLE_MESH_ENTRY_LAB_PLAN.md','**UIは未実装の計画**。','**UI実装・ローカル受入済み、公開受入確認待ち**。以下は実装前に定めた設計で、現在地と実測は[ラボ契約](SPHERE_TRIANGLE_MESH_ENTRY_LAB.md)と[検証記録](../reports/2026-11-04-sphere-triangle-mesh-entry-lab.md)を優先する。')
replace('docs/SPHERE_TRIANGLE_MESH_ENTRY_LAB.md','**実装・統合検証中**。','**実装・ローカル統合受入済み、公開確認待ち**。実測は[検証記録](../reports/2026-11-04-sphere-triangle-mesh-entry-lab.md)へ保存。')
replace('docs/learn/index.html','侵入開始窓の手動ラボ（実装中）','侵入開始窓の手動ラボ')
for path,text in [
 ('docs/RESEARCH.md','手動entry UIローカル受入: 専用21群/631Node/38CTest、25代表入力の24実モデル＋host1、全画面JSON/追加13view入力packet/2実Blob=180165数値bits5061負零が直接SDKと一致。fresh62model3hostの全DTO bitsと明示補足mixed65 Fraction/90負例も成功。314保護原本/SDK/通知を維持し、旧SDK回帰は前公開受入とsource/artifact同一を確認して継承。driver上限/hiddenerror観測の原失敗と訂正を保持。公開受入は次段。'),
 ('docs/legal/DEPENDENCIES.md','手動entry UIの配布監査: 314既存原本と86exports/61source-header/719410B WASM/58933B glue/runtime91/7通知は全raw hash不変。新package/solver/外部素材/有料serviceなし。本体license未選定。'),
 ('docs/legal/REFERENCES.md','手動entry UIの受入: 原著25presetの全input bitsを固定65へ照合。24自然モデルとhost1、13追加packetの所有/表示/直接SDK bits一致と2実Blob bytesを別に検証。追加viewは同一queryを共有でき、packet数を実query数と呼ばない。独立数学mixed65/90負例と説明投影を分ける。'),
 ('docs/legal/ASSETS.md',f'2026-11-04 原著entry手動ラボ図 docs/learn/diagrams/sphere-triangle-mesh-entry-lab.svg: {digest(root/"docs/learn/diagrams/sphere-triangle-mesh-entry-lab.svg")["bytes"]}B SHA256 {digest(root/"docs/learn/diagrams/sphere-triangle-mesh-entry-lab.svg")["sha256"]}。四証拠、全被覆と未照会tail、audit/lastMesh所属、全所有JSONを原著SVGコードで説明。960x800、実ブラウザ全体を目視し文字・配置を確認。帯/番号は実計算/誤差/性能の測定ではない。外部画像/font/model/図本文の流用なし。本体license未選定。')]:
 p=root/path;p.write_text(p.read_text(encoding='utf-8')+'\n'+text+'\n',encoding='utf-8',newline='\n')
print('Local manual entry lab documented; public acceptance pending.')
