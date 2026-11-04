"""Validate public SDK CI states, bounded logs, exact bytes and real UI proof."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json
import subprocess

root = Path(__file__).resolve().parents[2]
commit = 'c9dda7991286602e6041b8303a74ffc6e2e99fad'
def read(p):
    return json.loads((root / p).read_text(encoding='utf8'))
def digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}
evidence = []
runs = read('reports/sphere-triangle-mesh-sdk-public-runs.json')
assert runs['commit'] == commit and len(runs['runs']) == 2
for run in runs['runs']:
    assert run['head_sha'] == commit and run['status'] == 'completed' and run['conclusion'] == 'success'
    p = 'reports/sphere-triangle-mesh-sdk-run-' + str(run['id']) + '.json'
    evidence.append(p)
    jobs = read(p)['jobs']
    assert jobs
    for job in jobs:
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
        p = 'reports/sphere-triangle-mesh-sdk-job-' + str(job['id']) + '-excerpt.json'
        evidence.append(p)
        excerpt = read(p)
        assert excerpt['job'] == job['id'] and excerpt['fullLines'] > len(excerpt['lines'])
ci = read('reports/sphere-triangle-mesh-sdk-job-126319411407-excerpt.json')
text = '\n'.join(l['text'] for l in ci['lines'])
for marker in ['100% tests passed, 0 tests failed out of 34', '# tests 526', '# pass 526', '# fail 0', '# skipped 0',
               '"modelFixtures": 45', '"completed": 29', '"expectedModelFailures": 16', '"hostRejected": 3',
               '"packetNumericComparisons": 27160', '"modelNumericComparisons": 20808', '"negativeZeroComparisons": 4453',
               '"referenceComponents": 2688', '"aggregateReferenceComponents": 87', '"rejectedControls": 43',
               'PASS 59 groups; 48 complete-input finite mesh fixtures', '18 sphere triangle mesh C ABI test groups passed',
               'PASS 126 groups; 113 finite complete-input fixtures', '"packetNumericComparisons": 22327',
               '"modelNumericComparisons": 13432', '"numericComparisons": 2841', '"nativeNumericBitComparisons": 2318',
               '"totalComparedNumericValues": 54410', '5 known-result assertions passed']:
    assert marker in text, marker
def warnings(excerpt):
    return [l['text'].split('warning:', 1)[1] for l in excerpt['lines'] if 'warning:' in l['text']]
assert len(warnings(ci)) == 36
assert warnings(ci) == warnings(read('reports/sphere-triangle-mesh-job-126303190486-excerpt.json'))
http = read('reports/sphere-triangle-mesh-sdk-public-bytes.json')
assert http['status'] == 'PASS' and http['commit'] == commit and len(http['files']) == 41
assert len({f['path'] for f in http['files']}) == 41
for f in http['files']:
    data = subprocess.check_output(['git', 'show', commit + ':' + f['path']], cwd=root)
    assert digest(data) == {k: f[k] for k in ['bytes', 'sha256']}
manifest = read('assets/pikapika-simulation.build.json')
assert len(manifest['sourceSha256']) == 57 and len(manifest['licenses']) == 7
for p, h in manifest['artifacts'].items():
    assert digest((root / p).read_bytes()) == h
    assert next(f['sha256'] for f in http['files'] if f['path'] == p) == h['sha256']
local = read('reports/sphere-triangle-mesh-sdk-local-verification.json')
assert local['status'] == 'PASS' and (local['ctest'], local['node'], local['exports']) == (34, 526, 74)
assert local['localAsan']['status'] == 'NOT_COMPLETED' and not local['localAsan']['runtimeExecuted']
assert local['linkedRuntimeMembersAdded'] == ['libc++-debug-legacyexcept.a(algorithm.o)'] and not local['linkedRuntimeMembersRemoved']
browser = read('reports/sphere-triangle-mesh-sdk-browser-verification.json')
assert browser['status'] == 'PASS' and browser['publicSingleLabInputAndResultNumericBits'] == 147
cover = read('reports/sphere-triangle-mesh-sdk-public-browser/cover.json')
assert cover['counts']['queries'] == cover['counts']['validated'] == cover['counts']['checked'] == 21
assert cover['renderer']['residentMeshes'] == 3 and not cover['errors'] and cover['pending'] is None
assert cover['startup']['diagnostics']['buildId'] == '1f40cf023bb8472f' and cover['startup']['diagnostics']['wasmBytes'] == 638777
assert all(r['state'] == 'completed' for r in cover['records']) and any(r['clipSeconds'] == 1 for r in cover['records'])
ax = (root / 'reports/sphere-triangle-mesh-sdk-public-browser/game-paused.ax.txt').read_text(encoding='utf8')
assert '撃破 2' in ax and '一時停止' in ax
for p in root.glob('reports/sphere-triangle-mesh-sdk-*'):
    if p.is_file() and p.name != 'sphere-triangle-mesh-sdk-public-verification.json':
        evidence.append(p.relative_to(root).as_posix())
for folder in ['reports/sphere-triangle-mesh-sdk-public-browser', 'reports/sphere-triangle-mesh-sdk-recipes']:
    evidence.extend(p.relative_to(root).as_posix() for p in (root / folder).iterdir() if p.is_file() and p.suffix != '.pyc')
report = {'schema': 1, 'status': 'PASS', 'commit': commit, 'checked': datetime.now(timezone.utc).isoformat(),
          'exports': 74, 'sourceHeaders': 57, 'ctest': 34, 'node': 526, 'sdkAsanUbsanGroups': 18, 'pureMeshAsanUbsanGroups': 59,
          'sdkSanitizerScope': 'API cpp and new SDK tests instrumented; linked regular strict kernel archive. Pure mesh kernel independently instrumented in a separate step.',
          'windowsAsan': 'NOT_COMPLETED; compile stopped, runtime not executed, original records retained.',
          'packetNumericBits': 27160, 'modelNumericBits': 20808, 'negativeZeroComparisons': 4453,
          'referenceComponents': 2775, 'negativeControls': 43, 'warnings': 36, 'warningDiagnosticsUnchanged': True,
          'publicFiles': len(http['files']), 'publicBytes': sum(f['bytes'] for f in http['files']),
          'publicExistingGame': {'killsObserved': 2, 'coverQueriesAllCompleted': 21, 'residentMeshes': 3, 'fullOpenInRecords': True},
          'publicSingleLabInputAndResultNumericBits': 147, 'licensesUnchanged': 7,
          'linkedRuntimeMembersAdded': local['linkedRuntimeMembersAdded'],
          'ciScope': 'All job/step states, bounded selected logs including every warning; not full logs.',
          'scope': 'Read-only instantaneous sphere/static mesh query SDK; World/CCD/manifold/game mesh response remain separate.',
          'evidence': {p: digest((root / p).read_bytes()) for p in sorted(set(evidence))}}
(root / 'reports/sphere-triangle-mesh-sdk-public-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: v for k, v in report.items() if k != 'evidence'}, indent=2))
