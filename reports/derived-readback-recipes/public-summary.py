import hashlib
import json
import pathlib
import re
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]


def read(p):
    return json.loads((root / p).read_text(encoding='utf-8-sig'))


def sha(b):
    return hashlib.sha256(b).hexdigest()


revision = 'ef01017af1ccaff82d94c3df9c0114107e22c7b7'
for run in [41684477714, 41684476904]:
    jobs = read(f'reports/derived-readback-run-{run}.json')['jobs']
    assert jobs
    for job in jobs:
        assert job['run_id'] == run and job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
log = (root / 'reports/derived-readback-job-126086472388.txt').read_text(encoding='utf-8-sig')
for needle in ['GNU 13.3.0', 'v22.23.4', '100% tests passed, 0 tests failed out of 30',
               '# tests 452', '# pass 452', '# fail 0', '# skipped 0',
               '"numericComparisons": 2841', '"readback": "single"', '"readback": "batch"',
               '"totalComparedNumericValues": 54410', 'PASS 69 skinning test groups',
               '27 skin binding IO groups passed', 'derived mesh: 54 groups passed (40 fixtures)',
               'WebAssembly executed: 650 bytes; 5 known-result assertions passed']:
    assert needle in log, needle
assert len(re.findall(r'"rejectedControls": 36,', log)) == 4
assert len(re.findall(r'"nativeNumericBitComparisons": 2318,', log)) == 2
assert sum('warning:' in l for l in log.splitlines()) == 36
http = read('reports/derived-readback-http.json')
assert http['status'] == 'PASS' and http['revision'] == revision and len(http['files']) == 16
for f in http['files']:
    b = subprocess.check_output(['git', 'show', revision + ':' + f['path']], cwd=root)
    assert f['status'] == 200 and len(b) == f['bytes'] and sha(b) == f['sha256'], f['path']
v = read('reports/derived-readback-public-browser-verification.json')
assert (v['status'], v['browserReports'], v['numericComparisons'], v['draws'], v['newUploads'], v['cacheDraws']) == ('PASS', 1, 990, 20, 10, 10)
public = read('reports/derived-readback-public-single-4.json')
local = read('reports/derived-readback-local-single-4.json')
for k in ['input', 'settings', 'firstPair', 'execution', 'verified']:
    assert public[k] == local[k], k
manifest = json.loads(subprocess.check_output(['git', 'show', revision + ':assets/pikapika-simulation.build.json'], cwd=root))
assert public['manifest']['data'] == manifest
assert public['runtime']['wasmBytes'] == 592939 and public['runtime']['buildId'] == 'c2aa5ebb6392265f'
game = read('reports/derived-readback-public-game.json')
assert game['launchEnabled'] and 'WEBGPU READY' in game['text'] and game['url'].endswith('?v=ef01017')
paths = [f'reports/derived-readback-job-{i}.txt' for i in [126086472388, 126086477421, 126086615575, 126086615607]]
paths += [f'reports/derived-readback-run-{i}.json' for i in [41684477714, 41684476904]]
paths += ['reports/derived-readback-http.json', 'reports/derived-readback-public-single-4.json',
          'reports/derived-readback-public-browser-verification.json', 'reports/derived-readback-public-browser-command.txt',
          'reports/derived-readback-public.png', 'reports/derived-readback-public-game.json',
          'reports/derived-readback-public-game.png', 'reports/derived-readback-recipes/public-bytes.py',
          'reports/derived-readback-recipes/public-summary.py']
files = [dict(path=p, bytes=len((root / p).read_bytes()), sha256=sha((root / p).read_bytes())) for p in paths]
result = dict(status='PASS', revision=revision, nodePassed=452, nodeSkipped=0, ctests=30,
              nativeBitComparisonsPerTransport=2318, sdkBitComparisons=2841, independentNegativeControlBatches=4,
              independentNegativeControlsPerBatch=36, warningLines=36, httpFiles=16,
              publicSingleCompatibilityNumericComparisons=990, publicSingleCompatibilityDraws=20,
              robotStartupReady=True, robotCombatRetested=False, batchBrowserComparisonImplemented=False, files=files)
(root / 'reports/derived-readback-public-verification.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps({k: v for k, v in result.items() if k != 'files'}))
