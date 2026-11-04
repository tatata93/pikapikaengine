"""Keep actual older UI/game evidence separate from the new Native-only kernel."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,subprocess
root=Path(__file__).resolve().parents[2]
previous='656f59d931c48441c8a8697ef0729a9e0fa2e5c1';current='058a919aa2b0176f58130f92e554693ea9a4f2e6'
def blob(commit,p):return subprocess.check_output(['git','show',commit+':'+p],cwd=root)
old=json.loads((root/'reports/sphere-triangle-mesh-trajectory-lab-public-verification.json').read_text())
assert old['status']=='PASS' and old['commit']==previous
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',previous,'engine','samples','assets','tools','index.html','style.css'],cwd=root,text=True).splitlines()
cohort=[]
for p in paths:
    if p.startswith('tools/') and not p.endswith(('.mjs','.html')):continue
    before=blob(previous,p);now=blob(current,p);assert now==before,p
    data=(root/p).read_bytes()
    # Existing browser source uses Git text normalization on Windows.
    assert data==now or data.replace(b'\r\n',b'\n')==now,p
    cohort.append({'path':p,'bytes':len(now),'sha256':sha256(now).hexdigest()})
report={'schema':1,'status':'PASS','commit':current,'checked':datetime.now(timezone.utc).isoformat(),
 'diagram':{'path':'docs/learn/diagrams/sphere-triangle-mesh-entry.svg','url':'https://tatata93.github.io/pikapikaengine/docs/learn/diagrams/sphere-triangle-mesh-entry.svg?v=058a919','screenshot':'reports/sphere-triangle-mesh-entry-public-browser/diagram.jpg','scope':'Original conceptual illustration visibly checked; not numerical browser execution of Native entry kernel.'},
 'inherited':{'previousCommit':previous,'sourceCohortFiles':cohort,'publicBrowser':old['publicBrowser'],'publicGame':old['publicGame'],
 'scope':'Previous actual public all25 guard presets/7 extra packets/2 Blob downloads and robot3 kills/21 validated cover queries retained from their original record. All existing browser engine/sample/assets/tools modules and entries compared byte-for-byte between source commits; current public73 comparison covers its intersection. These are inherited compatibility observations, not new executions or application of the entry kernel to browser/game contacts. Current Native SDK regression ran separately.'}}
target=root/'reports/sphere-triangle-mesh-entry-public-browser-verification.json'
assert (root/report['diagram']['screenshot']).is_file()
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','unchangedSourceCohort':len(cohort),'inheritedFrom':previous}))
