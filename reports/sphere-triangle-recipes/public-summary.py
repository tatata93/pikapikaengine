"""Check saved public Actions, exact commit bytes and unchanged-game READY."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((root / name).read_text(encoding='utf-8'))


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


commit = 'f017d79c9bafadedb7c37556abacb1c50f4c49db'
runs = read('reports/sphere-triangle-public-runs.json')
assert runs['commit'] == commit and len(runs['runs']) == 2
for run in runs['runs']:
    assert run['head_sha'] == commit and run['status'] == 'completed' and run['conclusion'] == 'success'
    jobs = read('reports/sphere-triangle-run-' + str(run['id']) + '.json')['jobs']
    assert jobs
    for job in jobs:
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(step['status'] == 'completed' and step['conclusion'] == 'success' for step in job['steps'])
        excerpt = read('reports/sphere-triangle-job-' + str(job['id']) + '-excerpt.json')
        assert excerpt['job'] == job['id'] and excerpt['fullLines'] > len(excerpt['lines'])
ci = read('reports/sphere-triangle-job-126265294391-excerpt.json')
text = '\n'.join(line['text'] for line in ci['lines'])
for marker in ['100% tests passed, 0 tests failed out of 32', '# tests 496', '# pass 496', '# fail 0', '# skipped 0',
               '"fixtures": 113', '"completed": 88', '"failures": 25', '"referenceComponents": 1848',
               '"rejectedControls": 23', 'PASS 126 groups; 113 finite complete-input fixtures',
               '"numericComparisons": 2841', '"nativeNumericBitComparisons": 2318', '"totalComparedNumericValues": 54410',
               '5 known-result assertions passed']:
    assert marker in text, marker
assert sum('warning:' in line['text'] for line in ci['lines']) == 36
http = read('reports/sphere-triangle-public-bytes.json')
assert http['status'] == 'PASS' and http['commit'] == commit and len(http['files']) == 26
assert len({file['path'] for file in http['files']}) == 26
for file in http['files']:
    data = subprocess.check_output(['git', 'show', commit + ':' + file['path']], cwd=root)
    assert {'bytes': len(data), 'sha256': sha256(data).hexdigest()} == {k: file[k] for k in ['bytes', 'sha256']}, file['path']
game = read('reports/sphere-triangle-public-game.json')
ui = read('reports/sphere-triangle-public-game-ui.json')
assert game['state'] == 'ready' and game['failure'] is None and not game['errors'] and game['pending'] is None
assert game['renderer']['residentMeshes'] == 3 and not game['renderer']['lost'] and not game['renderer']['disposed']
assert game['counts']['queries'] == game['counts']['validated'] == 1
assert game['startup']['diagnostics']['buildId'] == '75daf0141409872f'
assert game['authorSource'] == (root / 'assets/robot-back-cover.skin.json').read_text(encoding='utf-8').strip()
assert ui['status'] == 'C++ WASM / WEBGPU READY' and ui['openingVisible'] and ui['entry'].endswith('?build=75daf0141409872f')
local = read('reports/sphere-triangle-verification.json')
assert local['status'] == 'PASS' and local['mainSDKUnchanged']
for path, expected in local['sourceAndEvidence'].items():
    assert digest(root / path) == expected, path
files = [p for p in sorted((root / 'reports').glob('sphere-triangle-*')) if p.is_file() and p.name != 'sphere-triangle-public-verification.json']
recipes = list(sorted((root / 'reports/sphere-triangle-recipes').glob('*.py')))
report = {'schema': 1, 'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(), 'commit': commit,
          'ctest': 32, 'node': 496, 'newSanitizerGroups': 126, 'referenceComponents': 1848, 'negativeControls': 23,
          'compilerWarningLines': 36, 'publicFiles': 26, 'publicBytes': sum(file['bytes'] for file in http['files']),
          'browserScope': 'Existing game READY and original cover only; new Native query is not in the main Web SDK',
          'ciEvidenceScope': 'All step states and selected numerical evidence/all warning lines; not full decoded logs',
          'files': {p.relative_to(root).as_posix(): digest(p) for p in files + recipes}}
(root / 'reports/sphere-triangle-public-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: report[key] for key in ['status', 'ctest', 'node', 'newSanitizerGroups', 'referenceComponents', 'publicFiles']}))
