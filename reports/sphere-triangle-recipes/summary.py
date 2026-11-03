"""Verify saved Native/ASan/CTest/oracle evidence and unchanged main SDK."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((root / name).read_text(encoding='utf-8'))


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


local = read('reports/sphere-triangle-local-verification.json')
assert local['status'] == 'PASS' and local['assetsUnchanged'] and not local['newKernelInMainWebSDK']
for name, expected in {**local['sources'], **local['assets']}.items():
    assert digest(root / name) == expected, name
logs = {}
for command in local['commands']:
    assert command['exit'] == 0
    for stream in ['stdout', 'stderr']:
        path = root / command[stream]
        assert digest(path) == command[stream + 'Hash'], str(path)
    logs[command['name']] = (root / command['stdout']).read_bytes()
assert b'100% tests passed, 0 tests failed out of 32' in logs['ctest']
for marker in ['tests 496', 'pass 496', 'fail 0', 'skipped 0']:
    assert marker.encode() in logs['node'], marker
assert b'Web build 75daf0141409872f: 45 versioned modules' in logs['web-build']
assert b'warning' not in logs['native-build'].lower()
assert (root / 'reports/sphere-triangle-standalone/native-fixtures-final.stdout.txt').read_bytes() == logs['native-fixtures']
assert (root / 'reports/sphere-triangle-standalone/asan-fixtures-final.stdout.txt').read_bytes() == logs['native-fixtures']
for prefix in ['native', 'asan']:
    assert b'PASS 126 groups; 113 finite complete-input fixtures' in (root / f'reports/sphere-triangle-standalone/{prefix}-tests-final.stdout.txt').read_bytes()
detail = (root / 'reports/sphere-triangle-native-all.txt').read_bytes()
assert b'10 sphere triangle analytic impact groups passed' in detail
reference = read('reports/sphere-triangle-reference.json')
negative = read('reports/sphere-triangle-negative-controls.json')
assert reference['status'] == 'PASS' and reference['fixtures'] == 113 and reference['completed'] == 88 and reference['failures'] == 25 and reference['referenceComponents'] == 1848
assert all(reference['retainedFeatureCounts'])
assert negative['status'] == 'PASS' and negative['baseline'] == reference and negative['labelAndOrderIndependent']
assert len(negative['rejectedControls']) == 23 and all(case['rejected'] for case in negative['rejectedControls'])
fixtures = json.loads(logs['native-fixtures'])['fixtures']
status_counts = Counter(fixture['result']['status'] for fixture in fixtures)
assert status_counts == {0: 88, 1: 11, 2: 2, 3: 1, 4: 8, 5: 2, 6: 1}
archive = read('reports/sphere-triangle-archive.json')
assert archive['status'] == 'PASS'
for item in archive['files']:
    assert digest(root / item['path']) == {k: item[k] for k in ['bytes', 'sha256']}, item['path']
sdk = read('assets/pikapika-simulation.build.json')
for name, expected in sdk['sourceSha256'].items():
    assert digest(root / name)['sha256'] == expected, name
for name, expected in sdk['licenses'].items():
    assert digest(root / name)['sha256'] == expected, name
for name, expected in sdk['artifacts'].items():
    assert digest(root / name) == {key: expected[key] for key in ['bytes', 'sha256']}, name
assert len(sdk['sourceSha256']) == 53 and len(sdk['licenses']) == 7 and len(sdk['artifacts']) == 2
files = [path for path in sorted((root / 'reports').glob('sphere-triangle-*')) if path.is_file() and path.name != 'sphere-triangle-verification.json']
sources = [root / name for name in ['docs/SPHERE_TRIANGLE.md', 'docs/SPHERE_TRIANGLE_SDK_PLAN.md', 'docs/PHYSICS_SCOPE.md', 'docs/RESEARCH.md', 'docs/learn/index.html',
           'docs/learn/diagrams/sphere-triangle.svg', 'docs/legal/REFERENCES.md', 'docs/legal/ASSETS.md', 'docs/legal/DEPENDENCIES.md']]
recipes = list(sorted((root / 'reports/sphere-triangle-recipes').glob('*.py')))
report = {'schema': 1, 'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(),
          'nativeGroups': 126, 'asanGroups': 126, 'analyticImpactGroups': 10, 'ctest': 32, 'node': 496,
          'fixtures': 113, 'completed': 88, 'intentionalFailures': 25, 'referenceComponents': 1848, 'negativeControls': 23,
          'sdkSourceHashes': 53, 'sdkNotices': 7, 'sdkArtifacts': 2, 'mainSDKUnchanged': True,
          'sourceAndEvidence': {path.relative_to(root).as_posix(): digest(path) for path in files + sources + recipes}}
(root / 'reports/sphere-triangle-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: report[key] for key in ['status', 'nativeGroups', 'analyticImpactGroups', 'ctest', 'node', 'referenceComponents', 'negativeControls']}))
