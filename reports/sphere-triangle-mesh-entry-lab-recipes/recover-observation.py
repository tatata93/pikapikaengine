"""Archive an orchestration routing error, then restore only its five proof files."""
from pathlib import Path
from hashlib import sha256
import json,subprocess
root=Path(__file__).resolve().parents[2];prefix='reports/sphere-triangle-mesh-entry-lab-local-browser/'
names=['actions.json','capacity-earlier.json','capacity-last.json','extras.json','frontier-last.json']
expected={prefix+n for n in names}
changed=set(subprocess.check_output(['git','diff','--name-only','--',prefix],cwd=root,text=True).splitlines());assert changed==expected,changed
target=root/'reports/sphere-triangle-mesh-entry-lab-browser-routing-attempt-001';target.mkdir()
verification=json.loads((root/'reports/sphere-triangle-mesh-entry-lab-local-verification.json').read_text(encoding='utf-8'));rows=[]
def digest(b):return {'bytes':len(b),'sha256':sha256(b).hexdigest()}
for name in names:
 path=prefix+name;current=(root/path).read_bytes();(target/name).write_bytes(current)
 original=subprocess.check_output(['git','show','263d53127989b3779bcb214ead3c12415449e094:'+path],cwd=root)
 assert digest(original)==verification['browserEvidence'][path],path
 (root/path).write_bytes(original);rows.append({'path':path,'misrouted':digest(current),'restored':digest(original)})
record={'schema':1,'status':'RESTORED','commit':'263d53127989b3779bcb214ead3c12415449e094','files':rows,'scope':'Browser REPL helpers retained their earlier local directory/array bindings when the caller switched to public context. Three public view captures affected only these five local proof files; current bytes are archived here and original accepted local bytes restored from the pinned Git blob. No model/SDK/UI source or user game data changed. Public view captures are repeated with an explicit immutable context object; no discarded data is claimed as accepted public proof.'}
(target/'recovery.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':'RESTORED','files':len(rows)}))
