"""Build Web and audit individually enumerated public-receipt publication paths."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import time

root = Path(__file__).resolve().parents[2]
prefix = 'reports/world-static-mesh-preparation'
feature = '6608bc3963a7eaca1ac8a9d40f3ae5d76f93d05e'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip() == feature
baseline = json.loads((root/(prefix+'-baseline.json')).read_text(encoding='utf-8'))
local = json.loads((root/(prefix+'-local-verification.json')).read_text(encoding='utf-8'))
public = json.loads((root/(prefix+'-public-verification.json')).read_text(encoding='utf-8'))
assert public['status']=='PASS' and public['commit']==feature

def info(raw):
    return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}

def frozen():
    for path, stamp in baseline['protected'].items():
        assert info((root/path).read_bytes()) == stamp, path
    for path, stamp in local['newSources'].items():
        assert info((root/path).read_bytes()) == stamp, path
    for path, stamp in baseline['generatedEntries'].items():
        assert info((root/path).read_bytes()) == stamp, path
    for path in baseline['permittedOldSources']:
        raw = (root/path).read_bytes()
        blob = subprocess.check_output(['git','show',feature+':'+path],cwd=root)
        assert raw == blob or raw.replace(b'\r\n',b'\n') == blob, path

frozen()
started = datetime.now(timezone.utc).isoformat()
clock = time.perf_counter()
args = ['node','scripts/build-web.mjs']
process = subprocess.run(args,cwd=root,capture_output=True,timeout=60)
command = {'name':'receipt-web-build','args':args,'started':started,
           'wallSeconds':time.perf_counter()-clock,'exit':process.returncode}
for label in ['stdout','stderr']:
    raw = getattr(process,label)
    path = prefix+'-receipt-web.'+label+'.txt'
    (root/path).write_bytes(raw)
    command[label]=path
    command[label+'Hash']=info(raw)
(root/(prefix+'-receipt-web.json')).write_text(json.dumps(command,indent=2)+'\n',encoding='utf-8')
assert process.returncode == 0
frozen()
assert process.stdout.decode('utf-8').strip() == 'Web build cd45c7f1ac2ba5e5: 54 versioned modules; generated import maps'
assert '?build=cd45c7f1ac2ba5e5' in (root/'index.html').read_text(encoding='utf-8')
changes = subprocess.check_output(['git','diff','--name-only','-z'],cwd=root).decode().split('\0')
documents = {'docs/PLAN.md','docs/RESEARCH.md','docs/WORLD_STATIC_MESH_FLIGHT_PLAN.md',
             'docs/WORLD_STATIC_MESH_PREPARATION.md','reports/2026-11-04-world-static-mesh-preparation.md'}
assert set(filter(None,changes)) == documents|{prefix+'-recipes/public.py'}
others = list(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')))
outputs = {prefix+'-receipt-paths.json',prefix+'-receipt-paths.nul',prefix+'-receipt-publication-audit.json'}
selected = {path for path in others if path.startswith(prefix) and path not in outputs}
paths = sorted(selected|documents|{prefix+'-recipes/public.py'})
assert 20 <= len(paths) <= 512 and len(paths)==len(set(paths))
assert all((root/p).is_file() for p in paths)
manifest = {'schema':1,'feature':feature,'paths':paths,'files':{p:info((root/p).read_bytes()) for p in paths},
            'excludedFuturePaths':[p for p in others if p not in selected and p not in outputs]}
(root/(prefix+'-receipt-paths.json')).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
stage_paths = sorted([*paths,*outputs])
(root/(prefix+'-receipt-paths.nul')).write_bytes(b'\0'.join(p.encode() for p in stage_paths)+b'\0')
audit = {'schema':1,'status':'PASS','feature':feature,'checked':datetime.now(timezone.utc).isoformat(),
         'protectedRaw':355,'newPreparationSources':7,'generatedRawHTML':26,'sourceIntegrationsFeatureExact':3,
         'publicAcceptance':'reports/world-static-mesh-preparation-public-verification.json',
         'scope':'Receipt/documents and public verification evidence only. Future coverage implementation is explicitly excluded.',
         'stagePaths':stage_paths,'manifest':prefix+'-receipt-paths.json','manifestHash':info((root/(prefix+'-receipt-paths.json')).read_bytes()),
         'nulManifestHash':info((root/(prefix+'-receipt-paths.nul')).read_bytes()),'webCommand':command}
(root/(prefix+'-receipt-publication-audit.json')).write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','stagePaths':len(stage_paths),'futureExcluded':len(manifest['excludedFuturePaths']),'build':'cd45c7f1ac2ba5e5'}))
