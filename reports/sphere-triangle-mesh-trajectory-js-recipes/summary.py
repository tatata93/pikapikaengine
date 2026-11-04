"""Summarize archived local acceptance without substituting previous results."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json

root=Path(__file__).resolve().parents[2]
prefix='sphere-triangle-mesh-trajectory-js'
def read(path):return json.loads((root/path).read_text(encoding='utf-8-sig'))
def digest(path):
    data=(root/path).read_bytes()
    return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
base=read(f'reports/{prefix}-baseline.json')
assert len(base['protected'])==107
assert all(digest(path)==expected for path,expected in base['protected'].items())
directory=f'reports/{prefix}-checks/run-20261104-accepted'
commands=[]
for phase in ['dedicated','exchange','regressions','recheck']:
    rows=read(f'{directory}/{phase}-commands.json')
    assert rows and all(row['exit']==0 and row['authoredSourcesStable'] for row in rows)
    for row in rows:
        assert all(digest(path)==expected for path,expected in row['authoredSourcesAfter'].items())
        assert digest(row['stdout'])==row['stdoutHash'] and digest(row['stderr'])==row['stderrHash']
    commands+=rows
for name,count in [('dedicated',22),('node',566),('learn',12)]:
    row=next(row for row in commands if row['name']==name)
    text=(root/row['stdout']).read_text(encoding='utf-8')
    for marker in [f'ℹ tests {count}',f'ℹ pass {count}','ℹ fail 0','ℹ skipped 0']:assert marker in text,marker
owned=read(f'{directory}/owned-sdk/report.json')
assert owned['status']=='PASS'
assert (owned['actualModelFixtures'],owned['hostRejected'],owned['modelNumericComparisons'],owned['originalInputNumericComparisons'])==(59,3,50663,3877)
assert owned['mathematicalCorpus']['actualOwnedWasmDecoderResults']==59 and owned['mathematicalCorpus']['pureNativeHostSupplements']==3
assert (owned['negativeControls']['rejectedControls'],owned['negativeControls']['selfTestGroups'])==(71,14)
assert (owned['reference']['certifiedLeaves'],owned['reference']['cellAudits'])==(297,606)
for name,expected in owned['files'].items():assert digest(f'{directory}/owned-sdk/{name}')==expected
browser=read(f'reports/{prefix}-local-browser-verification.json')
assert browser['status']=='PASS' and (browser['numericBits'],browser['negativeZeroBits'])==(324,24)
game=read(f'reports/{prefix}-local-browser/game-cover-report.json')
state=(root/f'reports/{prefix}-local-browser/game-state.txt').read_text(encoding='utf-8')
assert '撃破 1' in state and '一時停止 / Pで再開' in state
assert game['state']=='ready' and not game['errors'] and game['failure'] is None
assert game['counts']['queries']==game['counts']['validated']==20
assert all(row['state']=='completed' for row in game['records']) and any(row['clipSeconds']==1 for row in game['records'])
assert game['renderer']['residentMeshes']==3 and not game['renderer']['lost']
assert game['startup']['diagnostics']['buildId']==browser['webBuild']=='7f0cfa4ee56be1ca'
assert game['startup']['diagnostics']['wasmBytes']==browser['wasmBytes']==674978
manifest=read('assets/pikapika-simulation.build.json')
assert manifest==base['manifest'] and len(manifest['sources'])==29 and len(manifest['sourceSha256'])==59 and len(manifest['licenses'])==7
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),
 'baseCommit':base['baseCommit'],'protectedFilesUnchanged':107,'dedicatedTests':22,'nodeTests':566,'learnTests':12,'skipped':0,
 'exports':80,'sourceHeaders':59,'webBuild':browser['webBuild'],'owned':owned,'browser':browser,
 'artifacts':{name:digest(name) for name in ['assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json']},
 'game':{'kills':1,'paused':True,'boostClip1Observed':True,'coverQueries':20,'allCompleted':True,'residentMeshes':3},
 'commands':commands,
 'initialAttempts':'Initial ordinary corpus acceptance predates accessor-read fix; retained in run-20261104-root. First agent 18/20 test attempt recorded honestly without unavailable raw streams; two incorrect test assumptions were corrected. Final sources frozen across 22 dedicated/566 regression tests and final corpus acceptance.',
 'nativeScope':'C++ kernels/C ABI/artifacts/probes unchanged and protected. No new local CTest or Windows sanitizer execution claimed; prior public36 CTest is historical. Current public CI will rerun36 and sanitizers.',
 'scope':'Defined linear path read-only guard owned JavaScript wrapper; metadata auditing is not a second mathematical solver. Mixed62 independent exact-rational acceptance contains actual owned59 plus declared pure Native host3. Fixed browser example only; interactive editor/World/TOI/response/fluids/damage/specialist models/IK/high-accuracy imaging and Native fault injection are not completed.'}
target=root/f'reports/{prefix}-local-verification.json'
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:report[key] for key in ['status','protectedFilesUnchanged','dedicatedTests','nodeTests','webBuild']}))
