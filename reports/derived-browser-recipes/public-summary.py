import hashlib
import json
import pathlib
import re
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]
revision = 'eba356fdd7324b62ba736d6fa17860378502410c'
def read(p):
    return json.loads((root/p).read_bytes())
def sha(b):
    return hashlib.sha256(b).hexdigest()
jobs = []
for run in [41688623334,41688622286]:
    data = read(f'reports/derived-browser-run-{run}.json')
    assert data['jobs']
    for job in data['jobs']:
        assert job['run_id'] == run and job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(s['status']=='completed' and s['conclusion']=='success' for s in job['steps'] or [])
        jobs.append(job['id'])
log = (root/'reports/derived-browser-job-126100957488.txt').read_text(encoding='utf-8')
for needle in ['GNU 13.3.0','v22.23.4','100% tests passed, 0 tests failed out of 30',
               '# tests 468','# pass 468','# fail 0','# skipped 0',
               '"numericComparisons": 2841','"readback": "single"','"readback": "batch"',
               '"totalComparedNumericValues": 54410','PASS 69 skinning test groups',
               '27 skin binding IO groups passed','derived mesh: 54 groups passed (40 fixtures)',
               'WebAssembly executed: 650 bytes; 5 known-result assertions passed']:
    assert needle in log, needle
assert len(re.findall(r'"rejectedControls": 36,',log)) == 4
assert len(re.findall(r'"nativeNumericBitComparisons": 2318,',log)) == 2
warnings = sum('warning:' in line for line in log.splitlines())
assert warnings == 36
http = read('reports/derived-browser-http.json')
assert http['revision'] == revision and len(http['files']) == 16
for row in http['files']:
    data = subprocess.check_output(['git','show',revision+':'+row['path']],cwd=root)
    assert row['status'] == 200 and row['bytes'] == len(data) and row['sha256'] == sha(data)
latest = read('reports/derived-browser-raw-checks/latest-public.json')
commands = read('reports/derived-browser-raw-checks/'+pathlib.Path(latest['runDirectory']).name+'/commands.json')
assert len(commands) == 1 and commands[0]['exitCode'] == 0
auditPath = 'reports/derived-browser-verifiers/'+pathlib.Path(commands[0]['verificationRun']).name+'/verification.json'
audit = read(auditPath)
assert (audit['schema'],audit['browserReports'],audit['numericComparisons'],audit['draws'],audit['newUploads'],audit['cacheDraws']) == (2,6,270940,120,60,60)
assert audit['nodeReplay']['queries'] == 6
for publicPath in sorted((root/'reports/derived-browser-public').glob('[0-9][0-9]-*.json')):
    public = json.loads(publicPath.read_bytes())
    local = read('reports/derived-browser-local/'+publicPath.name)
    for key in ['input','settings','firstPair','execution','verified','projection','camera','model']:
        assert public[key] == local[key], publicPath.name+' '+key
    assert public['runtime']['wasmBytes'] == 592939 and public['runtime']['buildId'] == '7f5b0f537e72cef8'
game = read('reports/derived-browser-public/game-ready.json')
assert game['launchEnabled'] and 'WEBGPU READY' in game['text'] and game['url'].endswith('?v=eba356f')
paths = [f'reports/derived-browser-job-{j}.txt' for j in jobs]
paths += [f'reports/derived-browser-run-{j}.json' for j in [41688623334,41688622286]]
paths += ['reports/derived-browser-http.json',auditPath]
paths += [p.relative_to(root).as_posix() for p in (root/'reports/derived-browser-public').glob('*') if p.is_file()]
files = [dict(path=p,bytes=len((root/p).read_bytes()),sha256=sha((root/p).read_bytes())) for p in paths]
medians = [dict(caseName=r['caseName'],readback=r['readback'],baselineMs=next(row['statistics']['medianMs'] for row in r['summary'] if row['kind']=='baseline' and row['group']=='cpu' and row['stage']=='elapsedMs')) for r in audit['records']]
result = dict(status='PASS',revision=revision,nodePassed=468,nodeSkipped=0,ctests=30,warningLines=warnings,
              browserQueries=60,browserDraws=120,newUploads=60,cacheDraws=60,numericComparisons=270940,
              separateNodeReplayQueries=6,httpFiles=16,sourceHashes=audit['sourceHashes'],
              cohort=audit['cohort'],medians=medians,files=files,defaultReadback='single',
              robotStartupReady=True,robotCombatRetested=False,sampleCoverImplemented=False,
              sdkBitComparisons=2841,nativeBitComparisonsPerTransport=2318,
              independentNegativeControlBatches=4,independentNegativeControlsPerBatch=36)
(root/'reports/derived-browser-public-verification.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k not in ['files','sourceHashes','cohort']},indent=2))
