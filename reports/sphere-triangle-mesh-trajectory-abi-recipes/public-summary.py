from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

root=Path(__file__).resolve().parents[2]
prefix='sphere-triangle-mesh-trajectory-abi'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
local=read(root/f'reports/{prefix}-local-verification.json')
public=read(root/f'reports/{prefix}-public-bytes.json')
runs=read(root/f'reports/{prefix}-public-runs.json')
assert len(runs['runs'])==2
assert all(run['head_sha']==public['commit'] and run['status']=='completed' and run['conclusion']=='success' for run in runs['runs'])
jobs=[]
for run in runs['runs']:
    rows=read(root/f'reports/{prefix}-run-{run["id"]}.json')['jobs']
    assert rows and all(job['status']=='completed' and job['conclusion']=='success' and all(step['status']=='completed' and step['conclusion']=='success' for step in job['steps']) for job in rows)
    jobs+=rows
engine=next(job for job in jobs if job['name']=='portable-core')
log=read(root/f'reports/{prefix}-job-{engine["id"]}-excerpt.json')
text='\n'.join(line['text'] for line in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 36','# tests 544','# pass 544','# fail 0','# skipped 0','25 sphere triangle mesh trajectory C ABI groups passed','PASS 69 groups; 62 complete-input finite trajectory fixtures','"modelFixtures": 59','"wireNumericComparisons": 71234','"numericBits": 70278','"negativeZeroBits": 2398','"count": 19','"packetNumericComparisons": 27160','"modelNumericComparisons": 20808','GNU 13.3.0']:
    assert marker in text,marker
old=read(root/'reports/sphere-triangle-mesh-trajectory-job-126347121071-excerpt.json')
def warnings(source):return [line['text'].split('warning:',1)[1] for line in source['lines'] if 'warning:' in line['text']]
assert len(warnings(log))==36 and warnings(log)==warnings(old)
assert public['status']=='PASS' and len(public['files'])==50
browser=read(root/f'reports/{prefix}-public-browser-verification.json')
assert browser['status']=='PASS' and (browser['numericBits'],browser['negativeZeroBits'])==(170,20)
game=read(root/f'reports/{prefix}-public-browser/game-cover-report.json')
assert game['state']=='ready' and game['failure'] is None and not game['errors']
assert game['counts']['queries']==game['counts']['validated']==21
assert all(row['state']=='completed' for row in game['records']) and any(row['clipSeconds']==1 for row in game['records'])
assert game['renderer']['residentMeshes']==3 and not game['renderer']['lost']
assert game['startup']['diagnostics']['wasmBytes']==674978 and game['startup']['diagnostics']['buildId']=='d692d4714c9e820a'
target=root/f'reports/{prefix}-public-verification.json'
paths=set((root/'reports').glob(prefix+'-*.json'))
paths.update((root/f'reports/{prefix}-recipes').glob('*'))
paths.update((root/f'reports/{prefix}-public-browser').glob('*'))
paths.discard(target)
report={'schema':1,'status':'PASS','commit':public['commit'],'checked':datetime.now(timezone.utc).isoformat(),
 'ctest':36,'node':544,'nativeExchangeGroups':25,'finiteInputs':62,'modelFixtures':59,'hostRejected':3,
 'nativeWireNumericComparisons':71234,'wasmWireNumericBits':70278,'wasmNegativeZeroBits':2398,'negativeControlsPerExchange':19,
 'existingWarnings':36,'warningDiagnosticsUnchanged':True,
 'apiSanitizer':'New trajectory API implementation and C ABI tests instrumented with GNU ASan/UBSan; regular strict kernel archive linked, 25 groups pass. Pure guard/mesh/primitive/Interval/core/portable separately instrumented in its 69-group step. No whole-archive instrumentation claim.',
 'windowsSanitizer':'No new local Windows sanitizer success claimed.',
 'rationalScope':'Original pinned 62 pure Native fixtures receive exact Fraction reference; all 59 exchange-accepted model DTO fields independently encoded and compared bitwise. Host3 are not claimed as WASM model execution or reconstructed DTOs.',
 'publicFiles':50,'publicBytes':sum(file['bytes'] for file in public['files']),'publicBrowser':browser,
 'publicGame':{'status':'PASS','kills':3,'paused':True,'coverQueries':21,'allCompleted':True,'boostClip1Observed':True,'residentMeshes':3,'scope':'Existing game compatibility with new shared SDK; new trajectory guard not applied to game contacts.'},
 'artifacts':local['artifacts'],'exports':80,'sourceHeaders':59,'protectedFilesUnchanged':98,'licenseNoticesUnchanged':7,'runtimeLinkedMembersAdded':[],'runtimeLinkedMembersRemoved':[],
 'ciJobs':jobs,'ciEvidenceScope':'All jobs/steps and bounded selected original log lines including every warning; not full logs.',
 'evidence':{path.relative_to(root).as_posix():digest(path) for path in sorted(paths) if path.is_file()},
 'scope':'Read-only raw C ABI/WASM exchange for defined sphere paths; owned JS wrapper/UI/World/TOI/response and unexecuted fault injection remain separate.'}
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:report[key] for key in ['status','commit','ctest','node','nativeExchangeGroups','publicFiles','publicBytes']}))
