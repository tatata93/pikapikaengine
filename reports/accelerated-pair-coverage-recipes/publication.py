"""Build and audit an explicit feature path list, excluding later public summaries."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import ast
import json
import subprocess
import time

root = Path(__file__).resolve().parents[2]
prefix = 'reports/accelerated-pair-coverage'
base = json.loads((root/(prefix+'-baseline.json')).read_text(encoding='utf-8'))
local = json.loads((root/(prefix+'-local-verification.json')).read_text(encoding='utf-8'))
assert local['status']=='PASS' and local['baseCommit']==base['baseCommit']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==base['baseCommit']

def info(raw):
    return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}

def frozen():
    for path,stamp in base['protected'].items():
        assert info((root/path).read_bytes())==stamp,path
    for path,stamp in local['newSources'].items():
        assert info((root/path).read_bytes())==stamp,path
    for path,stamp in base['generatedEntries'].items():
        assert info((root/path).read_bytes())==stamp,path
    for path,stamp in local['evidence'].items():
        assert info((root/path).read_bytes())==stamp,path

frozen()
args=['node','scripts/build-web.mjs']
started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
process=subprocess.run(args,cwd=root,capture_output=True,timeout=60)
command={'name':'final-web','args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':process.returncode}
for stream in ['stdout','stderr']:
    raw=getattr(process,stream);path=prefix+'-final-web.'+stream+'.txt'
    (root/path).write_bytes(raw);command[stream]=path;command[stream+'Hash']=info(raw)
(root/(prefix+'-final-web.json')).write_text(json.dumps(command,indent=2)+'\n',encoding='utf-8')
assert process.returncode==0
assert process.stdout.decode('utf-8').strip()=='Web build cd45c7f1ac2ba5e5: 54 versioned modules; generated import maps'
frozen()
tree=ast.parse((root/(prefix+'-recipes/summary.py')).read_text(encoding='utf-8'))
fragments={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body
           if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
           and node.targets[0].id in {'CMAKE_LIBRARY','CMAKE_TEST','CI_MAIN','CI_AUDIT','ATTRS'}}
assert len(fragments)==5
for path,names in [('CMakeLists.txt',['CMAKE_LIBRARY','CMAKE_TEST']),('.github/workflows/verify.yml',['CI_MAIN','CI_AUDIT']),('.gitattributes',['ATTRS'])]:
    raw=(root/path).read_bytes()
    for name in names:
        chunk=fragments[name].encode()
        if raw.count(chunk)!=1:chunk=chunk.replace(b'\n',b'\r\n')
        assert raw.count(chunk)==1
        raw=raw.replace(chunk,b'',1)
    assert raw==base['permittedOldSources'][path]['gitBlobUtf8'].encode() or raw.replace(b'\r\n',b'\n')==base['permittedOldSources'][path]['gitBlobUtf8'].encode(),path

changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=root).decode().split('\0')))
expected={'.gitattributes','.github/workflows/verify.yml','CMakeLists.txt','docs/PLAN.md','docs/RESEARCH.md',
          'docs/WORLD_STATIC_MESH_FLIGHT_PLAN.md','docs/learn/index.html','docs/legal/ASSETS.md',
          'docs/legal/DEPENDENCIES.md','docs/legal/REFERENCES.md'}
assert changed==expected,changed
others=list(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')))
deferred={prefix+'-recipes/public-summary.py',prefix+'-recipes/public-summary-run.py'}
outputs={prefix+'-publication-paths.json',prefix+'-publication-paths.nul',prefix+'-publication-audit.json'}
binary_suffix={'.exe','.obj','.lib','.pdb','.ilk','.log','.pyc'}
selected={p for p in others if p not in deferred|outputs and Path(p).suffix.lower() not in binary_suffix}
assert all(p in local['newSources'] or p.startswith(prefix) or p in {
    'docs/ACCELERATED_PAIR_COVERAGE.md','docs/ACCELERATED_PAIR_COVERAGE_PLAN.md',
    'docs/learn/diagrams/accelerated-pair-coverage.svg','reports/2026-11-04-accelerated-pair-coverage.md'} for p in selected)
paths=sorted(expected|selected)
assert 60<=len(paths)<=512
files={p:info((root/p).read_bytes()) for p in paths}
assert sum(v['bytes'] for v in files.values())<32*1024*1024
manifest={'schema':1,'baseCommit':base['baseCommit'],'paths':paths,'files':files,
          'excluded':sorted(set(others)-selected-outputs),'scope':'Individual feature paths only; Native object/executable files and unfinished public-summary scripts are excluded.'}
(root/(prefix+'-publication-paths.json')).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
stage=sorted(paths+list(outputs))
(root/(prefix+'-publication-paths.nul')).write_bytes(b'\0'.join(p.encode() for p in stage)+b'\0')
audit={'schema':1,'status':'PASS','baseCommit':base['baseCommit'],'checked':datetime.now(timezone.utc).isoformat(),
       'protectedRaw':362,'newCodeSources':7,'generatedRawHTML':26,'exactIntegrationInsertions':{'CMake':14,'CI':14,'attributes':2},
       'localAcceptance':prefix+'-local-verification.json','stagePaths':stage,
       'manifestHash':info((root/(prefix+'-publication-paths.json')).read_bytes()),
       'nulManifestHash':info((root/(prefix+'-publication-paths.nul')).read_bytes()),'web':command,
       'scope':'Local acceptance only; public Linux/sanitizer/distribution/browser checks remain pending.'}
(root/(prefix+'-publication-audit.json')).write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','stagePaths':len(stage),'protectedRaw':362,'publicPending':True,'excluded':len(manifest['excluded'])}))
