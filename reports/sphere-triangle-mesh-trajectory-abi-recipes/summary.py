from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

root=Path(__file__).resolve().parents[2]
out=root/'reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
commands=[]
for phase in ['native','native-final','wasm','exchange','wasm-exchange','validate','recheck']:
    rows=read(out/(phase+'-commands.json'))
    assert rows and all(row['exit']==0 for row in rows),phase
    for row in rows:
        assert digest(root/row['stdout'])==row['stdoutHash']
        assert digest(root/row['stderr'])==row['stderrHash']
    commands+=rows
baseline=read(root/'reports/sphere-triangle-mesh-trajectory-abi-baseline.json')
for name,expected in baseline['protected'].items():assert digest(root/name)==expected,name
manifest=read(root/'assets/pikapika-simulation.build.json')
for name,expected in manifest['sourceSha256'].items():assert digest(root/name)['sha256']==expected,name
for name,expected in manifest['artifacts'].items():assert digest(root/name)==expected,name
for name,expected in manifest['licenses'].items():assert digest(root/name)['sha256']==expected,name
assert manifest['licenses']==baseline['manifest']['licenses']
assert manifest['linkedLibraryMembers']==baseline['manifest']['linkedLibraryMembers']
assert len(manifest['sourceSha256'])==59
native=read(out/'native-exchange/report.json');wasm=read(out/'wasm-exchange/report.json');wire=read(out/'wasm-wire/report.json')
assert native['status']==wasm['status']==wire['status']=='PASS'
assert native['modelFixtures']==wasm['modelFixtures']==59
assert native['hostRejected']==wasm['hostRejected']==3
assert native['negativeControls']['count']==wasm['negativeControls']['count']==19
assert native['negativeControls']['allRejected'] and wasm['negativeControls']['allRejected']
assert wire['numericBits']==70278 and wire['negativeZeroBits']==2398
assert '100% tests passed, 0 tests failed out of 36' in (out/'ctest.stdout.txt').read_text()
assert '25 sphere triangle mesh trajectory C ABI groups passed' in (out/'native-final-test.stdout.txt').read_text()
assert 'warning' not in (out/'native-final-build.stdout.txt').read_text().lower()
assert 'tests 544' in (out/'node.stdout.txt').read_text(encoding='utf-8')
game=read(root/'reports/sphere-triangle-mesh-trajectory-abi-local-browser/game-cover-report.json')
assert game['state']=='ready' and game['failure'] is None and not game['errors']
assert game['counts']['queries']==20 and game['counts']['validated']==20
assert game['renderer']['residentMeshes']==3 and not game['renderer']['lost']
assert game['startup']['diagnostics']['wasmBytes']==674978
assert any(record['clipSeconds']==1 for record in game['records'])
oldmesh=read(out/'old-mesh-sdk/report.json');oldsingle=read(out/'old-single-sdk/report.json')
assert oldmesh['status']==oldsingle['status']=='PASS'
report={'schema':1,'status':'PASS','generated':datetime.now(timezone.utc).isoformat(),'baseCommit':baseline['baseCommit'],
 'ctest':36,'nativeExchangeGroups':25,'node':544,'webBuild':'d692d4714c9e820a','exports':80,'sourceHeaders':59,
 'protectedFilesUnchanged':len(baseline['protected']),'licenseNoticesUnchanged':7,'runtimeLinkedMembersAdded':[],'runtimeLinkedMembersRemoved':[],
 'artifacts':manifest['artifacts'],'nativeExchange':native,'wasmExchange':wasm,'wasmWire':wire,
 'oldMesh':oldmesh,'oldSingle':oldsingle,'commands':commands,
 'initialWarnings':'First Native build passed with two C4267 test-side size_t-to-unsigned warnings. Test-only range-checked conversion correction followed by dedicated rebuild/25-group retest passes without warnings; original build output retained. Production API/kernel/probe unchanged.',
 'localGame':{'status':'PASS','kills':3,'paused':True,'coverQueries':20,'allCompleted':all(row['state']=='completed' for row in game['records']),'boostClip1Observed':True,'residentMeshes':3,'scope':'Existing game compatibility with new shared WASM; no new trajectory guard applied to game contacts.'},
 'publicCiPages':'NOT_YET_VERIFIED','sanitizer':'New public API/test instrumentation with regular strict kernel archive planned; pure guard separately instrumented. No new local Windows sanitizer success claimed.',
 'scope':'Bounded raw C ABI for read-only defined sphere paths. Owned JavaScript wrapper, UI, World/TOI/response remain unimplemented; original pinned rational reference and accepted exchange DTO bit identity are reported separately.'}
(root/'reports/sphere-triangle-mesh-trajectory-abi-local-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:report[key] for key in ['status','ctest','nativeExchangeGroups','node','exports','sourceHeaders','protectedFilesUnchanged']}))
