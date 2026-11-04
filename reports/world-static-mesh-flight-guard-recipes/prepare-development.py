"""Record a public-pending pre-authoring snapshot, never final acceptance."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[2]
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
prior=json.loads((ROOT/'reports/accelerated-sphere-box-coverage-baseline.json').read_text(encoding='utf8'))
local=json.loads((ROOT/'reports/accelerated-sphere-box-coverage-local-verification.json').read_text(encoding='utf8'))
assert local['status']=='PASS' and len(prior['protected'])==376 and len(local['newSources'])==7
protected={**prior['protected'],**local['newSources']}
assert len(protected)==383
for path,stamp in protected.items():assert info((ROOT/path).read_bytes())==stamp,path
base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert base=='63f5d3d7b841633980eac2006717f30614ee9e1f'
entries={p:info((ROOT/p).read_bytes()) for p in prior['generatedEntries']}
assert len(entries)==26
integrations={p:info((ROOT/p).read_bytes()) for p in ['CMakeLists.txt','.github/workflows/verify.yml','.gitattributes']}
record={'schema':1,'created':datetime.now(timezone.utc).isoformat(),'baseCommit':base,
 'scope':'Pre-authoring snapshot while Sphere public CI/Pages acceptance is pending. Not a final accepted integration baseline. Existing protected sources, SDK and integration files must stay unchanged until the Sphere public receipt is committed.',
 'protected':protected,'generatedEntries':entries,'integrations':integrations,
 'sdkManifest':json.loads((ROOT/'assets/pikapika-simulation.build.json').read_text(encoding='utf8')),
 'localReceipt':{'path':'reports/accelerated-sphere-box-coverage-local-verification.json',**info((ROOT/'reports/accelerated-sphere-box-coverage-local-verification.json').read_bytes())}}
out=ROOT/'reports/world-static-mesh-flight-guard-development/before-implementation.json'
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x',encoding='utf8',newline='\n') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps({'status':'PASS','protected':383,'entries':26,'scope':'Public-pending pre-authoring only'}))
