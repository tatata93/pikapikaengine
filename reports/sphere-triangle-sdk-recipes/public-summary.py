"""Accept exact public commit, all job steps, numerical markers and browser run."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[2]
commit = 'e100bee2a7e53f55031b0103d32147668a7f447a'


def load(name):
    return json.loads((root / name).read_text(encoding='utf8'))


def digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


runs = load('reports/sphere-triangle-sdk-public-runs.json')
assert runs['commit'] == commit and len(runs['runs']) == 2
for run in runs['runs']:
    assert run['head_sha'] == commit and run['status'] == 'completed' and run['conclusion'] == 'success'
    jobs = load('reports/sphere-triangle-sdk-run-' + str(run['id']) + '.json')['jobs']
    assert jobs
    for job in jobs:
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
        excerpt = load('reports/sphere-triangle-sdk-job-' + str(job['id']) + '-excerpt.json')
        assert excerpt['job'] == job['id'] and excerpt['fullLines'] > len(excerpt['lines'])
ci = load('reports/sphere-triangle-sdk-job-126279255789-excerpt.json')
text = '\n'.join(line['text'] for line in ci['lines'])
for marker in ['100% tests passed, 0 tests failed out of 32', '# tests 502', '# pass 502', '# fail 0', '# skipped 0',
               '"modelFixtures": 111', '"expectedModelFailures": 23', '"hostRejected": 2',
               '"packetNumericComparisons": 22327', '"modelNumericComparisons": 13432', '"negativeZeroComparisons": 3472',
               '"referenceComponents": 1848', '"rejectedControls": 23', 'PASS 126 groups; 113 finite complete-input fixtures',
               '"numericComparisons": 2841', '"nativeNumericBitComparisons": 2318', '"totalComparedNumericValues": 54410',
               '5 known-result assertions passed']:
    assert marker in text, marker
audit = load('reports/sphere-triangle-sdk-job-126279255789-audit-excerpt.json')
assert any('GNU 13.3.0' in line['text'] for line in audit['lines'])
warnings = [line['text'] for line in ci['lines'] if 'warning:' in line['text']]
old = load('reports/sphere-triangle-job-126265294391-excerpt.json')
old_warnings = [line['text'] for line in old['lines'] if 'warning:' in line['text']]
clean = lambda s: s[s.index('warning:'):]
assert len(warnings) == ci['warningLines'] == 36
assert [clean(s) for s in warnings] == [clean(s) for s in old_warnings]
assert not any('core/src/sphere_triangle.cpp' in s for s in warnings)
http = load('reports/sphere-triangle-sdk-public-bytes.json')
assert http['status'] == 'PASS' and http['commit'] == commit and len(http['files']) == 31
assert len({f['path'] for f in http['files']}) == 31
for f in http['files']:
    data = subprocess.check_output(['git', 'show', commit + ':' + f['path']], cwd=root)
    assert digest(data) == {k: f[k] for k in ['bytes', 'sha256']}, f['path']
ready = load('reports/sphere-triangle-sdk-public-ready.json')
game = load('reports/sphere-triangle-sdk-public-game.json')
entry = load('reports/sphere-triangle-sdk-public-entry.json')
for r in [ready, game]:
    assert r['state'] == 'ready' and r['failure'] is None and not r['errors'] and r['pending'] is None
    assert r['renderer']['residentMeshes'] == 3 and not r['renderer']['lost'] and not r['renderer']['disposed']
    assert r['startup']['diagnostics']['buildId'] == 'f7448823095f375b'
    assert r['startup']['diagnostics']['wasmBytes'] == 612824
    assert r['authorSource'] == (root / 'assets/robot-back-cover.skin.json').read_text(encoding='utf8').strip()
assert ready['counts']['queries'] == ready['counts']['validated'] == 1
assert game['counts']['queries'] == game['counts']['validated'] == 21
assert game['opening'] > .8
assert entry['entry'] == 'samples/app.mjs?build=f7448823095f375b'
local = load('reports/sphere-triangle-sdk-local-verification.json')
assert local['status'] == 'PASS' and local['pureKernelUnchanged'] and local['runtimeNoticesUnchanged']
for name, expected in local['files'].items():
    assert digest((root / name).read_bytes()) == expected, name
files = [p for p in sorted((root / 'reports').glob('sphere-triangle-sdk-*')) if p.is_file() and p.name != 'sphere-triangle-sdk-public-verification.json']
recipes = list(sorted((root / 'reports/sphere-triangle-sdk-recipes').glob('*.py')))
report = {'schema': 1, 'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(), 'commit': commit,
    'ctest': 32, 'node': 502, 'newKernelSanitizerGroups': 126, 'packetNumericComparisons': 22327, 'modelNumericComparisons': 13432,
    'referenceComponents': 1848, 'negativeControls': 23, 'compilerWarningLines': 36, 'warningDiagnosticSequenceUnchanged': True,
    'publicFiles': 31, 'publicBytes': sum(f['bytes'] for f in http['files']),
    'browser': {'queries': 21, 'validated': 21, 'residentMeshes': 3, 'buildId': 'f7448823095f375b', 'scope': entry['scope']},
    'ciEvidenceScope': 'All step states and bounded selected verification/compiler/sanitizer markers plus all warning lines. Not full decoded logs.',
    'files': {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in files + recipes}}
(root / 'reports/sphere-triangle-sdk-public-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: report[k] for k in ['status', 'ctest', 'node', 'packetNumericComparisons', 'publicFiles', 'publicBytes']}))
