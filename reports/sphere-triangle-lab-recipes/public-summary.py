from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import math
import struct
import subprocess

root = Path(__file__).resolve().parents[2]
commit = '0db8f54d075078c535461040ba4e1795e61eae44'
browser = root / 'reports/sphere-triangle-lab-final-public-browser'
local = root / 'reports/sphere-triangle-lab-final-local-browser'


def load(path):
    return json.loads(path.read_text(encoding='utf8'), parse_int=lambda s: -0.0 if s == '-0' else int(s))


def digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


comparisons = 0


def compare(a, b):
    global comparisons
    if isinstance(a, (int, float)) and not isinstance(a, bool):
        assert isinstance(b, (int, float)) and not isinstance(b, bool)
        assert struct.pack('>d', a) == struct.pack('>d', b)
        comparisons += 1
    elif isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b)
        for k in a:
            compare(a[k], b[k])
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b)
        for x, y in zip(a, b):
            compare(x, y)
    else:
        assert type(a) is type(b) and a == b


runs = load(root / 'reports/sphere-triangle-lab-final-public-runs.json')
assert runs['commit'] == commit and len(runs['runs']) == 2
for run in runs['runs']:
    assert run['head_sha'] == commit and run['status'] == 'completed' and run['conclusion'] == 'success'
    jobs = load(root / ('reports/sphere-triangle-lab-run-' + str(run['id']) + '.json'))['jobs']
    assert jobs
    for job in jobs:
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
ci = load(root / 'reports/sphere-triangle-lab-job-126290485434-excerpt.json')
text = '\n'.join(l['text'] for l in ci['lines'])
for marker in ['GNU 13.3.0', '100% tests passed, 0 tests failed out of 32', '# tests 516', '# pass 516', '# fail 0', '# skipped 0',
               '"packetNumericComparisons": 22327', '"modelNumericComparisons": 13432', '"referenceComponents": 1848', '"rejectedControls": 23',
               '"numericComparisons": 2841', '"nativeNumericBitComparisons": 2318', '"totalComparedNumericValues": 54410',
               'PASS 126 groups; 113 finite complete-input fixtures', '5 known-result assertions passed']:
    assert marker in text, marker
warnings = [l['text'] for l in ci['lines'] if 'warning:' in l['text']]
old = load(root / 'reports/sphere-triangle-sdk-job-126279255789-excerpt.json')
clean = lambda s: s[s.index('warning:'):]
assert len(warnings) == ci['warningLines'] == 36
assert [clean(s) for s in warnings] == [clean(l['text']) for l in old['lines'] if 'warning:' in l['text']]
http = load(root / 'reports/sphere-triangle-lab-final-public-bytes.json')
assert http['status'] == 'PASS' and http['commit'] == commit and len(http['files']) == 25
for f in http['files']:
    data = subprocess.check_output(['git', 'show', commit + ':' + f['path']], cwd=root)
    assert digest(data) == {k: f[k] for k in ['bytes', 'sha256']}
names = ['face', 'edge_ab', 'edge_bc', 'edge_ca', 'vertex_a', 'vertex_b', 'vertex_c', 'back', 'coincident', 'degenerate', 'thin', 'budget', 'normal_precision']
for index, name in enumerate(names):
    a, b = load(local / (name + '.json')), load(browser / (name + '.json'))
    assert b['diagnostics']['buildId'] == '50e73448d9d02126' and b['diagnostics']['wasmBytes'] == 612824
    assert (b['result']['geometry'] is not None) == (index < 8)
    compare(a['input'], b['input'])
    compare(a['result'], b['result'])
assert comparisons == 1491
dirty = load(browser / 'host-rejection.json')
assert not dirty['dirty']['saveEnabled'] and not dirty['dirty']['json'] and '表示していません' in dirty['dirty']['view']
assert not dirty['rejection']['saveEnabled'] and not dirty['rejection']['json'] and 'ID requires' in dirty['rejection']['error']
download = (browser / 'downloaded.json').read_bytes()
assert download == (browser / 'edited-boundary.json').read_bytes()
r = load(browser / 'downloaded.json')
assert math.copysign(1, r['input']['sphere']['position'][0]) == -1
assert r['result']['geometry']['relation'] == 'boundary_unresolved' and r['projection'] == 'xy'
entry = load(browser / 'entry.json')
assert entry['entry'] == 'sphere-triangle-lab.mjs?build=50e73448d9d02126'
accepted = load(root / 'reports/sphere-triangle-lab-marker-verification.json')
assert accepted['status'] == 'PASS' and accepted['node'] == 516
assert digest((root / 'tools/sphere-triangle-lab.mjs').read_bytes()) == accepted['source']
for name, expected in accepted['sdkAndAuthoredAssetsUnchanged'].items():
    assert digest((root / name).read_bytes()) == expected
for name, expected in accepted['files'].items():
    assert digest((root / name).read_bytes()) == expected
files = [p for p in (root / 'reports').glob('sphere-triangle-lab-*') if p.is_file() and p.name != 'sphere-triangle-lab-public-verification.json']
files += list(browser.rglob('*')) + list((root / 'reports/sphere-triangle-lab-public-browser').rglob('*'))
files += list((root / 'reports/sphere-triangle-lab-recipes').glob('*.py'))
report = {'schema': 1, 'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(), 'commit': commit, 'node': 516, 'ctest': 32,
          'browserPresets': 13, 'completedPresets': 8, 'expectedModelFailures': 5, 'browserInputAndResultNumericBits': comparisons,
          'downloadBytes': len(download), 'downloadExact': True, 'signedZeroPreserved': True,
          'publicFiles': 25, 'publicBytes': sum(f['bytes'] for f in http['files']), 'compilerWarningLines': 36,
          'sdkAndAuthoredAssetsUnchanged': True, 'scope': 'Manual instantaneous query lab; no World/CCD/game mesh contact integration.',
          'ciEvidenceScope': 'All job/step states and bounded numerical/compiler/sanitizer excerpts, including all warnings; not full logs.',
          'files': {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in sorted(files) if p.is_file()}}
(root / 'reports/sphere-triangle-lab-public-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: report[k] for k in ['status', 'node', 'ctest', 'browserPresets', 'browserInputAndResultNumericBits', 'publicFiles', 'downloadBytes']}))
