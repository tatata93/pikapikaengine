"""Validate final local evidence while retaining failed integration attempts."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,re
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-trajectory-lab'
def read(path):return json.loads((root/path).read_text(encoding='utf-8-sig'))
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
base=read(f'reports/{prefix}-baseline.json');assert len(base['protected'])==250
changed=[]
for name,expected in base['protected'].items():
    data=(root/name).read_bytes()
    if name=='tests/web-build.test.mjs':
        assert data.count(b'count,24,')==1
        assert digest(data.replace(b'count,24,',b'count,23,'))==expected
        changed.append({'path':name,'before':expected,'after':digest(data),'reason':'One new web entry changes expected generated entry count from23 to24; all previous assertions retained.'})
    else:assert digest(data)==expected,name
directory=f'reports/{prefix}-checks/run-20261104-final';commands=[]
for phase in ['dedicated','cases','accept','exchange','recheck']:
    rows=read(f'{directory}/{phase}-commands.json')
    assert rows and all(row['exit']==0 and row['authoredStable'] for row in rows)
    for row in rows:
        for path,expected in row['authoredAfter'].items():assert digest((root/path).read_bytes())==expected,path
        for stream in ['stdout','stderr']:assert digest((root/row[stream]).read_bytes())==row[stream+'Hash']
    commands+=rows
for name,count in [('dedicated',20),('node',586),('learn',12)]:
    row=next(row for row in commands if row['name']==name);text=(root/row['stdout']).read_text(encoding='utf-8')
    for marker in [f'ℹ tests {count}',f'ℹ pass {count}','ℹ fail 0','ℹ skipped 0']:assert marker in text,marker
native=next(row for row in commands if row['name']=='ctest');assert '100% tests passed, 0 tests failed out of 36' in (root/native['stdout']).read_text()
cases=read(f'{directory}/cases/report.json');assert cases['status']=='PASS'
assert (cases['presets'],cases['modelResults'],cases['hostRejected'],cases['separated'],cases['witness'])==(25,24,1,11,1)
owned=read(f'{directory}/owned-sdk/report.json');assert owned['status']=='PASS' and owned['actualModelFixtures']==59 and owned['hostRejected']==3
assert (owned['modelNumericComparisons'],owned['negativeControls']['rejectedControls'])==(50663,71)
browser=read(f'reports/{prefix}-local-browser-verification.json')
assert browser['status']=='PASS' and (browser['numericBits'],browser['negativeZeroBits'],browser['downloads'])==(100742,3896,2)
game=read(f'reports/{prefix}-local-browser/game-cover-report.json');state=(root/f'reports/{prefix}-local-browser/game-state.txt').read_text(encoding='utf-8')
assert game['state']=='ready' and game['failure'] is None and not game['errors']
assert game['counts']['queries']==game['counts']['checked']==game['counts']['validated']==19
assert all(row['state']=='completed' for row in game['records']) and any(row['clipSeconds']==1 for row in game['records'])
assert game['renderer']['residentMeshes']==3 and not game['renderer']['lost']
assert '撃破 2' in state and '一時停止 / Pで再開' in state
assert game['startup']['diagnostics']['wasmBytes']==674978 and game['startup']['diagnostics']['buildId']=='d70b5d9b4436650f'
manifest=read('assets/pikapika-simulation.build.json');assert len(manifest['sourceSha256'])==59 and len(manifest['licenses'])==7
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'baseCommit':base['baseCommit'],
 'dedicatedTests':20,'nodeTests':586,'ctest':36,'learnTests':12,'skipped':0,'webBuild':'d70b5d9b4436650f','modules':49,'entries':24,
 'protectedFilesUnchanged':249,'explicitTestExpectationUpdate':changed,'exports':80,'sourceHeaders':59,'licenseNoticesUnchanged':7,
 'artifacts':{name:digest((root/name).read_bytes()) for name in ['assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json']},
 'cases':cases,'ownedSdkRegression':owned,'browser':browser,'game':{'kills':2,'paused':True,'coverQueries':19,'allCompleted':True,'boostClip1Observed':True,'residentMeshes':3},'commands':commands,
 'attempts':{'initialAgent':'Full raw20test development attempts in -agent-tests; first19 had18pass1 incorrect static option count, corrected runtime25-option checks retained. CP932 console forwarding failure did not lose captured raw outputs.',
 'initialIntegration':'run-20261104-accepted is a failed initial integration attempt despite its prospective directory name: CTest36 passed, Node585/586 due old entry count23. One assertion23→24 corrected, final run-20261104-final passes586. Both raw outputs retained.',
 'initialBrowser':'Earlier c5a823... model/25preset observations retained in -initial-browser. Canonical -local-browser reruns all25 and extra actions on frozen d70b5... module.'},
 'scope':'Manual read-only defined sphere path guard UI, full owned diagnostics/edit lifecycle/view projections/JSON saving. Preset inputs match pinned accepted Native corpus bitwise; browser numeric replay uses direct public owned WASM and is not a new independent mathematical solver. Previous actual owned59 plus declared host3 mixed62 rational scope remains separate. No Native/kernel/ABI/artifact/game changes or World/TOI/contact response/fluids/damage/specialist models/IK/high-accuracy imaging completion.'}
(root/f'reports/{prefix}-local-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:report[key] for key in ['status','ctest','nodeTests','dedicatedTests','protectedFilesUnchanged','webBuild']}))
