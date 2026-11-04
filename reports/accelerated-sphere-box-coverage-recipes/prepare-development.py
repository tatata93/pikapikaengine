"""Snapshot current sources before independent future-kernel authoring."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[2]
prior=json.loads((ROOT/'reports/accelerated-plane-box-coverage-baseline.json').read_text(encoding='utf8'))
local=json.loads((ROOT/'reports/accelerated-plane-box-coverage-local-verification.json').read_text(encoding='utf8'))
fix=json.loads((ROOT/'reports/accelerated-plane-box-coverage-ci-fix-development/run-001/acceptance.json').read_text(encoding='utf8'))
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
protected=dict(prior['protected'])
for p,s in local['newSources'].items():protected[p]=fix['new'] if p==fix['source'] else s
assert len(protected)==376
for p,s in protected.items():assert info((ROOT/p).read_bytes())==s,p
entries={p:info((ROOT/p).read_bytes()) for p in prior['generatedEntries']}
assert entries==prior['generatedEntries']
record={'schema':1,'created':datetime.now(timezone.utc).isoformat(),
 'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'scope':'Pre-authoring source snapshot only. Current plane-box release passed local numerical tests but its corrected GNU public CI is pending; this is NOT a public acceptance or the final integration baseline.',
 'protected':protected,'generatedEntries':entries,
 'integrations':{p:info((ROOT/p).read_bytes()) for p in prior['permittedOldSources']},
 'sdkManifest':prior['sdkManifest']}
out=ROOT/'reports/accelerated-sphere-box-coverage-development/before-implementation.json'
out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists()
out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','protected':376,'entries':26,'scope':'pre-authoring only; corrected public CI pending'}))
