"""Audit a concrete public-receipt path list and leave future work un-staged."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import time

root=Path(__file__).resolve().parents[2]
prefix='reports/accelerated-pair-coverage'
feature='f128f5040c2a4de0c0adba48896022c759f1b215'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==feature
base=json.loads((root/(prefix+'-baseline.json')).read_text(encoding='utf-8'))
local=json.loads((root/(prefix+'-local-verification.json')).read_text(encoding='utf-8'))
public=json.loads((root/(prefix+'-public-verification.json')).read_text(encoding='utf-8'))
assert public['status']=='PASS' and public['commit']==feature
documents={'docs/PLAN.md','docs/RESEARCH.md','docs/ACCELERATED_PAIR_COVERAGE.md',
           'docs/ACCELERATED_PAIR_COVERAGE_PLAN.md','reports/2026-11-04-accelerated-pair-coverage.md'}
def info(raw):
    return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
def frozen():
    for path,stamp in base['protected'].items():assert info((root/path).read_bytes())==stamp,path
    for path,stamp in local['newSources'].items():assert info((root/path).read_bytes())==stamp,path
    for path,stamp in base['generatedEntries'].items():assert info((root/path).read_bytes())==stamp,path
    for path,stamp in public['evidence'].items():
        if path not in documents:assert info((root/path).read_bytes())==stamp,path
    for path in base['permittedOldSources']:
        raw=(root/path).read_bytes();blob=subprocess.check_output(['git','show',feature+':'+path],cwd=root)
        assert raw==blob or raw.replace(b'\r\n',b'\n')==blob,path
frozen()
args=['node','scripts/build-web.mjs'];started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
process=subprocess.run(args,cwd=root,capture_output=True,timeout=60)
command={'name':'receipt-web-build','args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':process.returncode}
for name in ['stdout','stderr']:
    raw=getattr(process,name);path=prefix+'-receipt-web.'+name+'.txt';(root/path).write_bytes(raw)
    command[name]=path;command[name+'Hash']=info(raw)
(root/(prefix+'-receipt-web.json')).write_text(json.dumps(command,indent=2)+'\n',encoding='utf-8')
assert process.returncode==0 and process.stdout.decode('utf-8').strip()=='Web build cd45c7f1ac2ba5e5: 54 versioned modules; generated import maps'
frozen()
changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=root).decode().split('\0')))
assert changed==documents,changed
others=list(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')))
outputs={prefix+'-receipt-paths.json',prefix+'-receipt-paths.nul',prefix+'-receipt-publication-audit.json'}
selected={p for p in others if p.startswith(prefix) and p not in outputs and Path(p).suffix.lower() not in {'.exe','.obj','.lib','.pdb','.ilk','.log','.pyc'}}
paths=sorted(selected|documents)
assert 20<=len(paths)<=256 and all((root/p).is_file() for p in paths)
manifest={'schema':1,'feature':feature,'paths':paths,'files':{p:info((root/p).read_bytes()) for p in paths},
          'excludedFutureOrBinaryPaths':sorted(set(others)-selected-outputs)}
(root/(prefix+'-receipt-paths.json')).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
stage=sorted(paths+list(outputs));(root/(prefix+'-receipt-paths.nul')).write_bytes(b'\0'.join(p.encode() for p in stage)+b'\0')
audit={'schema':1,'status':'PASS','feature':feature,'checked':datetime.now(timezone.utc).isoformat(),'stagePaths':stage,
       'protectedRaw':362,'newCodeSources':7,'generatedRawHTML':26,'integrationsFeatureExact':3,
       'manifestHash':info((root/(prefix+'-receipt-paths.json')).read_bytes()),'nulManifestHash':info((root/(prefix+'-receipt-paths.nul')).read_bytes()),
       'publicAcceptance':prefix+'-public-verification.json','web':command,
       'scope':'Verified public evidence and five declared documentation updates; Native binaries and new plane-box/World design work explicitly excluded.'}
(root/(prefix+'-receipt-publication-audit.json')).write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','stagePaths':len(stage),'excluded':len(manifest['excludedFutureOrBinaryPaths']),'protectedRaw':362}))
