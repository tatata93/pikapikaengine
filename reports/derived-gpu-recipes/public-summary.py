"""Audit retained public evidence; never executes or re-times a workload."""
import hashlib
import json
import pathlib
import re
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((root / path).read_text(encoding='utf-8-sig'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


out = root / 'reports'
command = root / 'build/derived-gpu-public-browser-command.txt'
if command.exists():
    cmd = json.loads(command.read_text(encoding='utf-8-sig'))
    verification = pathlib.Path(cmd['runDirectory']) / 'verification.json'
    for src, dest in [(command, out / 'derived-gpu-public-browser-command.txt'),
                      (verification, out / 'derived-gpu-public-browser-verification.json')]:
        if dest.exists():
            assert dest.read_bytes() == src.read_bytes(), str(dest)
        else:
            dest.write_bytes(src.read_bytes())

v = read('reports/derived-gpu-public-browser-verification.json')
local = read('reports/derived-gpu-browser-verification.json')
assert (v['status'], v['browserReports'], v['numericComparisons'], v['draws'],
        v['newUploads'], v['cacheDraws']) == ('PASS', 4, 136460, 80, 40, 40)
for a, b in zip(v['records'], local['records'], strict=True):
    for k in ['caseName', 'faces', 'numericComparisons', 'exactResultSHA256',
              'execution', 'sourceUnchanged']:
        assert a[k] == b[k], (a['caseName'], k)
    public = read(a['path'])
    previous = read(b['path'])
    for k in ['input', 'settings', 'firstPair', 'execution', 'verified']:
        assert public[k] == previous[k], (a['caseName'], k)
    assert sha((root / a['path']).read_bytes()) == a['sha256']

for run in [41676872013, 41677877981, 41677879779]:
    jobs = read(f'reports/derived-gpu-run-{run}.json')['jobs']
    assert jobs
    for job in jobs:
        assert job['run_id'] == run
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(s['status'] == 'completed' and s['conclusion'] == 'success'
                   for s in job['steps'])

log = (out / 'derived-gpu-job-126063285389.txt').read_text(encoding='utf-8-sig')
needles = ['GNU 13.3.0', 'v22.23.4', '100% tests passed, 0 tests failed out of 30',
           '# tests 438', '# pass 438', '# fail 0', '# skipped 0',
           '"numericComparisons": 2841', '"nativeNumericBitComparisons": 2318',
           '"queryCount": 32', '"totalComparedNumericValues": 54410',
           'PASS 69 skinning test groups', '27 skin binding IO groups passed',
           'derived mesh: 54 groups passed (40 fixtures)',
           'WebAssembly executed: 650 bytes; 5 known-result assertions passed']
for needle in needles:
    assert needle in log, needle
assert len(re.findall(r'"rejectedControls": 36,', log)) == 3
assert sum('warning:' in line for line in log.splitlines()) == 36

http = read('reports/derived-gpu-http.json')
assert http['status'] == 'PASS' and len(http['files']) == 15
fixed = '158f9f1ec03dafac66113974542209cde14643a5'
for f in http['files']:
    assert f['status'] == 200
    data = subprocess.check_output(['git', 'show', fixed + ':' + f['path']], cwd=root)
    assert len(data) == f['bytes'] and sha(data) == f['sha256'], f['path']

game = read('reports/derived-gpu-game-dom.json')
assert game['launchEnabled'] is True and 'WEBGPU READY' in game['text']
assert game['url'].endswith('?v=158f9f1')
paths = [f'reports/derived-gpu-public-{n}.json' for n in ['4', '64', '512', 'retry-4']]
paths += [f'reports/derived-gpu-job-{j}.txt' for j in
          [126063285389, 126063288763, 126063454311, 126063454371]]
paths += [f'reports/derived-gpu-run-{r}.json' for r in
          [41676872013, 41677877981, 41677879779]]
paths += ['reports/derived-gpu-http.json', 'reports/derived-gpu-public.png',
          'reports/derived-gpu-game.png', 'reports/derived-gpu-game-dom.json',
          'reports/derived-gpu-public-browser-command.txt',
          'reports/derived-gpu-public-browser-verification.json',
          'reports/derived-gpu-recipes/public-summary.py']
files = []
for path in paths:
    data = (root / path).read_bytes()
    files.append(dict(path=path, bytes=len(data), sha256=sha(data)))
result = dict(status='PASS', runtimeCodeRevision=http['revision'], fixedTestRevision=fixed,
              httpFiles=15, httpFilesEqualFixedRevision=True, nodeTests=438, ctests=30,
              negativeControlBatches=3, negativeControlsPerBatch=36, warningLines=36,
              browserNumericComparisons=136460, browserDraws=80, newUploads=40,
              cacheDraws=40, robotStartupReady=True, robotCombatTested=False,
              sourceAndExactResultMatchLocal=True, files=files,
              limitation='Finite browser wall-time observations; no GPU timestamp/readback, presentation or general FPS proof.')
(out / 'derived-gpu-public-verification.json').write_bytes(
    (json.dumps(result, indent=2) + '\n').encode())
print(json.dumps({k: v for k, v in result.items() if k != 'files'}))
