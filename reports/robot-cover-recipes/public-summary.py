import hashlib
import json
import pathlib
import re
import subprocess

root=pathlib.Path(__file__).resolve().parents[2]
revision='8ebec4c850547c210426b65bdb3f34e9e9e17cb5'
def read(p):return json.loads((root/p).read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
jobs=[]
for run in [41693943514,41693939836]:
    data=read(f'reports/robot-cover-run-{run}.json');assert data['jobs']
    for job in data['jobs']:
        assert job['run_id']==run and job['status']=='completed' and job['conclusion']=='success'
        assert all(s['status']=='completed' and s['conclusion']=='success' for s in job['steps'] or [])
        jobs.append(job['id'])
log=(root/'reports/robot-cover-job-126119401588.txt').read_text(encoding='utf-8')
for needle in ['GNU 13.3.0','v22.23.4','100% tests passed, 0 tests failed out of 30',
               '# tests 492','# pass 492','# fail 0','# skipped 0',
               '"numericComparisons": 2841','"readback": "single"','"readback": "batch"',
               '"totalComparedNumericValues": 54410','PASS 69 skinning test groups',
               '27 skin binding IO groups passed','derived mesh: 54 groups passed (40 fixtures)',
               'WebAssembly executed: 650 bytes; 5 known-result assertions passed']:
    assert needle in log,needle
assert len(re.findall(r'"rejectedControls": 36,',log))==4
assert len(re.findall(r'"nativeNumericBitComparisons": 2318,',log))==2
warnings=sum('warning:' in line for line in log.splitlines());assert warnings==36
http=read('reports/robot-cover-http.json');assert http['revision']==revision and len(http['files'])==24
for row in http['files']:
    data=subprocess.check_output(['git','show',revision+':'+row['path']],cwd=root)
    assert row['status']==200 and row['bytes']==len(data) and row['sha256']==sha(data)
browser=read('reports/robot-cover-public-browser-verification.json')
assert browser['status']=='PASS' and browser['uiKills']==2 and browser['resourceMeshes']==3
assert browser['maximumObservedClip']==1 and browser['frame']['droppedSeconds']==0
paths=[f'reports/robot-cover-job-{j}.txt' for j in jobs]
paths += [f'reports/robot-cover-run-{r}.json' for r in [41693943514,41693939836]]
paths += ['reports/robot-cover-http.json','reports/robot-cover-public-browser-verification.json']
for family in ['robot-cover-public','robot-cover-public-release']:
    paths += [p.relative_to(root).as_posix() for p in (root/'reports'/family).glob('*') if p.is_file()]
files=[dict(path=p,bytes=len((root/p).read_bytes()),sha256=sha((root/p).read_bytes())) for p in paths]
local=read('reports/robot-cover-local-verification.json')
for p,h in local['sourceHashes'].items():assert sha((root/p).read_bytes())==h,p
record=dict(status='PASS',revision=revision,nodePassed=492,nodeSkipped=0,ctests=30,warningLines=warnings,
            publicUIKills=2,finiteCaptureCount=browser['finiteCaptureCount'],residentMeshes=3,maximumObservedClip=1,
            frame=browser['frame'],initialLongCapture=browser['initialLongCapture'],httpFiles=24,
            sourceHashes=local['sourceHashes'],files=files,strictHingeDynamicsImplemented=False,
            actualGPUReadback=False,actualHiddenBrowserPathRetested=False,
            nativeBitComparisonsPerTransport=2318,sdkBitComparisons=2841,
            independentNegativeControlBatches=4,independentNegativeControlsPerBatch=36)
(root/'reports/robot-cover-public-verification.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in record.items() if k not in ['files','sourceHashes']},indent=2))
