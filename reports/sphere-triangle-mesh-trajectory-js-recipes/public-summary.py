"""Require exact-source CI, public byte and actual browser evidence."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json
import re
import subprocess
root=Path(__file__).resolve().parents[2]
prefix='sphere-triangle-mesh-trajectory-js'
def read(path):return json.loads((root/path).read_text(encoding='utf-8-sig'))
def digest(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
local=read(f'reports/{prefix}-local-verification.json')
public=read(f'reports/{prefix}-public-bytes.json')
runs=read(f'reports/{prefix}-public-runs.json')
assert runs['commit']==public['commit'] and len(runs['runs'])==2
assert all(run['head_sha']==public['commit'] and run['status']=='completed' and run['conclusion']=='success' for run in runs['runs'])
jobs=[]
for run in runs['runs']:
    rows=read(f'reports/{prefix}-run-{run["id"]}.json')['jobs']
    assert rows and all(job['status']=='completed' and job['conclusion']=='success' and all(step['status']=='completed' and step['conclusion']=='success' for step in job['steps']) for job in rows)
    jobs+=rows
engine=next(job for job in jobs if job['name']=='portable-core')
log=read(f'reports/{prefix}-job-{engine["id"]}-excerpt.json')
text='\n'.join(line['text'] for line in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 36','# tests 566','# pass 566','# fail 0','# skipped 0',
 '25 sphere triangle mesh trajectory C ABI groups passed','PASS 69 groups; 62 complete-input finite trajectory fixtures',
 '"actualModelFixtures": 59','"hostRejected": 3','"modelNumericComparisons": 50663','"originalInputNumericComparisons": 3877',
 '"modelNegativeZeroComparisons": 2144','"originalInputNegativeZeroComparisons": 100',
 '"selfTestGroups": 14','"rejectedControls": 71','"certifiedLeaves": 297','"cellAudits": 606',
 '"wireNumericComparisons": 71234','"numericBits": 70278','"negativeZeroBits": 2398',
 '"packetNumericComparisons": 27160','"modelNumericComparisons": 20808','GNU 13.3.0']:
    assert marker in text,marker
old=read('reports/sphere-triangle-mesh-trajectory-job-126347121071-excerpt.json')
def warnings(source):return [line['text'].split('warning:',1)[1] for line in source['lines'] if 'warning:' in line['text']]
assert len(warnings(log))==36 and sorted(warnings(log))==sorted(warnings(old))
assert public['status']=='PASS' and len(public['files'])==56
browser=read(f'reports/{prefix}-public-browser-verification.json')
assert browser['status']=='PASS' and (browser['numericBits'],browser['negativeZeroBits'])==(324,24)
game=read(f'reports/{prefix}-public-browser/game-cover-report.json')
state=(root/f'reports/{prefix}-public-browser/game-state.txt').read_text(encoding='utf-8')
kills=int(re.search(r'撃破 (\d+)',state).group(1))
assert '一時停止 / Pで再開' in state and kills>0
assert game['state']=='ready' and game['failure'] is None and not game['errors']
queries=game['counts']['queries']
assert queries>0 and queries==game['counts']['validated']==game['counts']['checked']
assert all(row['state']=='completed' for row in game['records']) and any(row['clipSeconds']==1 for row in game['records'])
assert game['renderer']['residentMeshes']==3 and not game['renderer']['lost']
assert game['startup']['diagnostics']['wasmBytes']==674978 and game['startup']['diagnostics']['buildId']=='7f0cfa4ee56be1ca'
for path in ['engine/simulation.mjs','engine/sphere-triangle-mesh-trajectory.mjs','scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs','tests/sphere_triangle_mesh_trajectory_sdk.test.mjs']:
    assert (root/path).read_bytes()==subprocess.check_output(['git','show',public['commit']+':'+path],cwd=root)
target=root/f'reports/{prefix}-public-verification.json'
paths=set((root/'reports').glob(prefix+'-*.json'))
for directory in ['recipes','public-browser']:paths.update((root/f'reports/{prefix}-{directory}').glob('*'))
paths.discard(target)
report={'schema':1,'status':'PASS','commit':public['commit'],'checked':datetime.now(timezone.utc).isoformat(),
 'ctest':36,'node':566,'skipped':0,'nativeExchangeGroups':25,'pureGuardSanitizerGroups':69,
 'owned':local['owned'],'publicFiles':56,'publicBytes':sum(row['bytes'] for row in public['files']),
 'existingWarnings':36,'warningDiagnosticsUnchanged':True,'warningComparison':'Exact diagnostic multiset preserving repeat multiplicity, independent of parallel build ordering.',
 'ciJobs':jobs,'ciEvidenceScope':'All job/step statuses plus bounded original log lines containing all warnings; full logs not archived.',
 'publicBrowser':browser,'publicGame':{'status':'PASS','paused':True,'kills':kills,'coverQueries':queries,'allCompleted':True,'boostClip1Observed':True,'residentMeshes':3,'scope':'Existing game compatibility; trajectory guard not applied to game contacts.'},
 'artifacts':local['artifacts'],'exports':80,'sourceHeaders':59,'protectedFilesUnchanged':107,'licenseNoticesUnchanged':7,
 'sourceScope':'JS-only owned wrapper; unchanged C++/C ABI/artifacts. API/test GNU ASan/UBSan25 with regular strict kernel archive; separately fully instrumented pure guard69. No new Windows sanitizer success or deliberate C++ allocation/internal fault injection claimed.',
 'mathematicalScope':'Actual owned WASM59 model DTOs matched bitwise to Native and used in mixed62 exact-rational corpus with explicitly declared pure Native host3 supplements. Metadata decoder is not an independent mathematical solver.',
 'browserScope':'Current-source public fixed example executed through UI; complete input/DTO matched bitwise to Node. No interactive trajectory editor/World/TOI/response completion claim.',
 'evidence':{path.relative_to(root).as_posix():digest(path) for path in sorted(paths) if path.is_file()}}
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:report[key] for key in ['status','commit','ctest','node','publicFiles','publicBytes']}))
