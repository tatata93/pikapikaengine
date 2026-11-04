"""Verify frozen evidence and build an exact feature staging manifest."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
PREFIX='reports/accelerated-sphere-box-coverage'
base=json.loads((ROOT/(PREFIX+'-baseline.json')).read_text(encoding='utf8'))
local=json.loads((ROOT/(PREFIX+'-local-verification.json')).read_text(encoding='utf8'))
assert local['status']=='PASS'
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
def frozen():
    for p,s in {**base['protected'],**base['generatedEntries'],**local['evidence']}.items():
        assert info((ROOT/p).read_bytes())==s,p
frozen()
args=['node','scripts/build-web.mjs'];start=time.perf_counter()
process=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=60)
row={'name':'final-web','args':args,'started':datetime.now(timezone.utc).isoformat(),'wallSeconds':time.perf_counter()-start,'exit':process.returncode}
for stream in ['stdout','stderr']:
    raw=getattr(process,stream);p=PREFIX+'-final-web.'+stream+'.txt'
    (ROOT/p).write_bytes(raw);row[stream]=p;row[stream+'Hash']=info(raw)
(ROOT/(PREFIX+'-final-web.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf8')
assert process.returncode==0 and process.stdout.decode().strip()=='Web build cd45c7f1ac2ba5e5: 54 versioned modules; generated import maps'
frozen()
assert subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0,'Existing index changes require review'
changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')))
expected={'.gitattributes','.github/workflows/verify.yml','CMakeLists.txt','docs/learn/index.html',
          'docs/PLAN.md','docs/RESEARCH.md','docs/legal/ASSETS.md','docs/legal/DEPENDENCIES.md','docs/legal/REFERENCES.md'}
assert changed==expected,changed
others=set(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')))
deferred={PREFIX+'-recipes/public-summary.py',PREFIX+'-recipes/public-summary-run.py',
          'docs/WORLD_STATIC_MESH_FLIGHT_NATIVE_CONTRACT.md'}
outputs={PREFIX+'-publication-paths.json',PREFIX+'-publication-paths.nul',PREFIX+'-publication-audit.json'}
binary={'.exe','.obj','.lib','.pdb','.ilk','.log','.pyc'}
selected={p for p in others if p not in deferred|outputs and Path(p).suffix.lower() not in binary}
allowed_docs={'docs/ACCELERATED_SPHERE_BOX_COVERAGE.md','docs/ACCELERATED_SPHERE_BOX_COVERAGE_PLAN.md',
 'docs/learn/diagrams/accelerated-sphere-box-coverage.svg',
 'reports/2026-11-04-accelerated-sphere-box-coverage.md'}
assert all(p in local['newSources'] or p.startswith(PREFIX) or p in allowed_docs for p in selected),selected
paths=sorted(expected|selected)
assert 60<=len(paths)<=512
files={p:info((ROOT/p).read_bytes()) for p in paths}
assert sum(s['bytes'] for s in files.values())<32*1024*1024
manifest={'schema':1,'baseCommit':base['baseCommit'],'paths':paths,'files':files,
          'excluded':sorted(others-selected-outputs),'scope':'Only reviewed feature/evidence files. Native binaries/objects and future World contract/public receipt helpers excluded.'}
(ROOT/(PREFIX+'-publication-paths.json')).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
stage=sorted(paths+list(outputs))
(ROOT/(PREFIX+'-publication-paths.nul')).write_bytes(b'\0'.join(p.encode() for p in stage)+b'\0')
audit={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'baseCommit':base['baseCommit'],
       'protectedRaw':376,'generatedHTML':26,'newCodeSources':7,
       'exactIntegrationInsertions':{'CMake':14,'CI':13,'attributes':2},
       'stagePaths':stage,'bytesBeforeAuditFiles':sum(s['bytes'] for s in files.values()),
       'localAcceptance':PREFIX+'-local-verification.json'}
(ROOT/(PREFIX+'-publication-audit.json')).write_text(json.dumps(audit,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','files':len(stage),'bytesBeforeAuditFiles':audit['bytesBeforeAuditFiles'],'excluded':len(manifest['excluded'])}))
