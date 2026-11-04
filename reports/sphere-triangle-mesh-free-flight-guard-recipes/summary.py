"""Audit local read-only guard evidence and explicit rebuild/compatibility scope."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,re
if not __debug__:raise SystemExit('Run without Python -O')
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-free-flight-guard';final=f'reports/{prefix}-checks/run-20261104-final'
def read(path):return json.loads((root/path).read_text(encoding='utf-8-sig'))
def digest(path):
 data=(root/path).read_bytes();return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
base=read(f'reports/{prefix}-baseline.json');assert base['baseCommit']=='c33bf39e31f341f5c9e96502750071e87dde9244'
assert len(base['protected'])==324 and len(base['generatedEntries'])==25
for p,h in base['protected'].items():assert digest(p)==h,p
def normalized(data):return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',data),flags=re.S).replace(b'\r\n',b'\n')
for p,h in base['generatedEntries'].items():
 data=normalized((root/p).read_bytes());assert {'bytes':len(data),'sha256':sha256(data).hexdigest()}==h,p
before=f'reports/{prefix}-checks/run-20261104-before'
old=(root/f'{before}/continuous_world-before.cpp').read_bytes()
current=(root/'core/src/continuous_world.cpp').read_bytes()
marker=b'\ndetail::FreeFlightTubeResult detail::enclose_free_flight('
assert current.count(marker)==1 and current.endswith(b'\n}\n}\n')
restored=current.split(marker)[0].replace(b'#include "free_flight_internal.hpp"\n',b'')+b'}\n'
assert restored==old,'Old W1 mathematical/World bodies changed'
assert digest(f'{before}/continuous_world-before.cpp')==base['permittedRebuild']['core/src/continuous_world.cpp']
commands=[]
for phase in ['build','native','legacy','reference','regressions','legacy-wasm-after','old-exchange']:
 rows=read(f'{final}/{phase}-commands.json');assert rows
 for r in rows:
  assert r['exit']==0 and r['authoredStable'] and r['authoredBefore']==r['authoredAfter'],r['name']
  for p,h in r['authoredAfter'].items():assert digest(p)==h,p
  for stream in ['stdout','stderr']:assert digest(r[stream])==r[stream+'Hash'],r['name']
 commands+=rows
def output(name):
 row=[r for r in commands if r['name']==name];assert len(row)==1,name;return (root/row[0]['stdout']).read_text(encoding='utf-8-sig')
for key,n in [('tests',631),('pass',631),('fail',0),('skipped',0)]:assert re.search(r'(?:ℹ\s+|#\s+)'+key+r'\s+'+str(n)+r'(?:\s|$)',output('node')),(key,n)
assert '100% tests passed, 0 tests failed out of 40' in output('ctest')
assert 'PASS 114 groups; 100 complete-input finite free-flight guard fixtures' in output('native-tests')
assert 'OBS center-binade' in output('native-tests')
assert 'Web build bbeba69b26e28cdb: 51 versioned modules' in output('web-build')
reference=read(f'{final}/reference/reference.json');controls=read(f'{final}/reference/negative-controls.json')
fraction=json.loads(output('fraction'))
assert fraction['status']=='PASS' and fraction['fixtures']==100 and fraction['inputFingerprint']=='c14d0e37cd5fe3d85d30ec0a408d46608ecefabb8b55513e31e51dbfe6ed2d37'
assert (fraction['certifiedSeparated'],fraction['notCertified'],fraction['invalidInputs'],fraction['tubeReferences'],fraction['endpointReferences'],fraction['inflatedQueries'])==(18,44,38,57,54,54)
assert (fraction['held']['cellAudits'],fraction['held']['certifiedLeaves'],fraction['held']['lastMeshReferenceComponents'])==(2080,862,2556)
assert reference==controls['baseline'];assert reference=={k:v for k,v in fraction.items() if k!='supplemental'}
supplemental=fraction['supplemental'];assert controls['supplemental']==supplemental
assert supplemental['inputFingerprint']=='a23779088fc9d7ce9bf388456b055795ccf3c5ea85fdab3b11df50ea7a604d80'
assert (supplemental['fixtures'],supplemental['certifiedSeparated'],supplemental['notCertified'],supplemental['held']['entryWindows'])==(4,3,1,1)
assert supplemental['actualBodyBinadeBits']==['425fffffffffffff','4260000000000000','4260000000000001'] and supplemental['originalPositiveGap']=={'numerator':1,'denominator':1048576}
assert controls['status']=='PASS' and controls['selfTestGroups']==12 and controls['labelAndOrderIndependent'] is True
assert len(controls['rejectedControls'])==50 and all(c['rejected'] for c in controls['rejectedControls'])
assert read(f'{final}/reference/optimized-command.json')['exitCode']==1
assert (root/f'{final}/native-fixtures.json').read_bytes()==(root/f'reports/{prefix}-checks/run-20261104-initial/native-fixtures.json').read_bytes()
assert (root/f'{final}/legacy.json').read_bytes()==(root/f'{before}/legacy.json').read_bytes()
assert (root/f'{final}/old-w1-fixtures.json').read_bytes()==(root/f'{before}/old-w1-fixtures.json').read_bytes()
assert (root/f'{final}/old-held-fixtures.json').read_bytes()==(root/'reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json').read_bytes()
old_sdk=read(f'{final}/old-entry-owned/report.json');assert old_sdk['status']=='PASS'
assert (old_sdk['actualModelFixtures'],old_sdk['hostRejected'],old_sdk['modelNumericComparisons'],old_sdk['modelNegativeZeroComparisons'],old_sdk['originalInputNumericComparisons'],old_sdk['originalInputNegativeZeroComparisons'])==(62,3,105056,3239,4728,108)
assert old_sdk['negativeControls']['rejectedControls']==90
for p,h in old_sdk['files'].items():assert digest(f'{final}/old-entry-owned/{p}')==h,p
legacy_wasm=read(f'{final}/legacy-wasm/report.json');assert legacy_wasm['status']=='PASS' and legacy_wasm['comparedToBaseline']
assert (legacy_wasm['fixtures'],legacy_wasm['completed'],legacy_wasm['modelRejected'],legacy_wasm['hostRejected'],legacy_wasm['numericBits'],legacy_wasm['negativeZeroBits'])==(20,14,5,1,4520,24)
assert digest(f'{final}/legacy-wasm/results.json')==legacy_wasm['results']==digest(f'reports/{prefix}-checks/run-20261104-before-wasm/legacy-wasm/results.json')
manifest=read('assets/pikapika-simulation.build.json');assert len(manifest['sourceSha256'])==62 and len(manifest['sources'])==30
assert manifest['sdkVersion']=='6.0.13' and manifest['sourceFlags']['core/src/dynamics.cpp']==['-fno-fast-math','-ffp-contract=off']
assert 'core/src/free_flight_internal.hpp' in manifest['sourceSha256']
for p,h in manifest['sourceSha256'].items():assert digest(p)['sha256']==h,p
for p,h in manifest['artifacts'].items():assert digest(p)==h,p
assert manifest['artifacts']['assets/pikapika-simulation.wasm']=={'bytes':719396,'sha256':'5542502ee73b62c0ca8de9f3d1fc01139bfacfd4ff83922b5568f4a0acfd03c3'}
assert manifest['linkedLibraryMembers']==base['manifest']['linkedLibraryMembers'] and manifest['licenses']==base['manifest']['licenses'] and len(manifest['licenses'])==7
sdk_rows=read(f'reports/{prefix}-checks/run-20261104-sdk-strict/sdk-build-commands.json');assert len(sdk_rows)==1
for r in sdk_rows:
 assert r['exit']==0 and r['authoredStable']
 for p,h in r['authoredAfter'].items():assert digest(p)==h,p
 for stream in ['stdout','stderr']:assert digest(r[stream])==r[stream+'Hash']
 assert '"exports": 86' in (root/r['stdout']).read_text(encoding='utf-8')
cover=read(f'reports/{prefix}-browser/game-cover-report.json')
assert cover['state']=='ready' and cover['failure'] is None and cover['pending'] is None and not cover['errors']
assert cover['startup']['diagnostics']['buildId']=='bbeba69b26e28cdb' and cover['startup']['diagnostics']['wasmBytes']==719396
assert cover['renderer']['residentMeshes']==3 and not cover['renderer']['lost'] and not cover['renderer']['disposed']
assert cover['counts']['queries']==cover['counts']['checked']==cover['counts']['validated']==len(cover['records'])==22
assert all(r['state']=='completed' for r in cover['records']) and any(r['clipSeconds']==1 for r in cover['records'])
state=(root/f'reports/{prefix}-browser/game-state.txt').read_text(encoding='utf-8')
assert '撃破 2' in state and '一時停止' in state
sources={p:digest(p) for r in commands for p in r['authoredAfter']}
for p in ['docs/SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD.md','docs/learn/diagrams/sphere-triangle-mesh-free-flight-guard.svg','scripts/verify-free-flight-legacy.mjs']:sources[p]=digest(p)
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'baseCommit':base['baseCommit'],'protectedFilesUnchanged':324,'normalizedGeneratedEntries':25,
 'nativeGroups':114,'fixtures':100,'supplementalFixtures':4,'node':631,'ctest':40,'skipped':0,'webBuild':'bbeba69b26e28cdb','modules':51,'entries':25,
 'exports':86,'sourceHeaders':62,'sdkArtifacts':manifest['artifacts'],'runtimeMembers':91,'licenseNotices':7,'reference':fraction,'negativeControls':controls,
 'legacyNativeBytes':digest(f'{final}/legacy.json'),'legacyWasm':legacy_wasm,'oldEntryOwned':old_sdk,'sources':sources,'commands':commands,'sdkBuild':sdk_rows,
 'browser':{'kills':2,'paused':True,'queries':22,'residentMeshes':3,'errors':0,'evidence':{p:digest(f'reports/{prefix}-browser/{p}') for p in ['diagram.jpg','game.jpg','game-state.txt','game-cover-report.json']}},
 'scope':'Native-only read-only selected-body guard. Whole-duration proof is the strict RN translation recurrence; full H body candidate/ownership is tested separately. Original fixed100 and supplemental4 remain distinct. SDK86 exports rebuild changes WASM bytes; old20 exposed W1 fields/4520bits24negativezeros match prior actual SDK. Linux/sanitizers/public remain separate until actual completion.'}
(root/f'reports/{prefix}-local-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','nativeGroups','fixtures','supplementalFixtures','node','ctest','protectedFilesUnchanged','webBuild']}))
