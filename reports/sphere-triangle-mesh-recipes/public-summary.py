"""Validate exact public states, bounded excerpts, bytes and prior UI evidence."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json
import subprocess

root = Path(__file__).resolve().parents[2]
commit = '5c9093b473930f8040cb3c2c6b377beebb7d54ec'
def read(p):
    return json.loads((root / p).read_text(encoding='utf8'))
def digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}

runs = read('reports/sphere-triangle-mesh-public-runs.json')
assert runs['commit'] == commit and len(runs['runs']) == 2
evidence = []
for run in runs['runs']:
    assert run['head_sha'] == commit and run['status'] == 'completed' and run['conclusion'] == 'success'
    path = 'reports/sphere-triangle-mesh-run-' + str(run['id']) + '.json'
    evidence.append(path)
    jobs = read(path)['jobs']
    assert jobs
    for job in jobs:
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
        path = 'reports/sphere-triangle-mesh-job-' + str(job['id']) + '-excerpt.json'
        evidence.append(path)
        excerpt = read(path)
        assert excerpt['job'] == job['id'] and excerpt['fullLines'] > len(excerpt['lines'])
ci = read('reports/sphere-triangle-mesh-job-126303190486-excerpt.json')
text = '\n'.join(line['text'] for line in ci['lines'])
for marker in ['100% tests passed, 0 tests failed out of 33', '# tests 516', '# pass 516', '# fail 0', '# skipped 0',
               '"fixtures": 48', '"completedMeshes": 29', '"failedMeshes": 6', '"prevalidationRejected": 13',
               '"primitiveRows": 136', '"referenceComponents": 2688', '"aggregateReferenceComponents": 87',
               '"rejectedControls": 43', 'PASS 59 groups; 48 complete-input finite mesh fixtures',
               'PASS 126 groups; 113 finite complete-input fixtures', '"numericComparisons": 2841',
               '"nativeNumericBitComparisons": 2318', '"totalComparedNumericValues": 54410', '5 known-result assertions passed']:
    assert marker in text, marker
def warnings(excerpt):
    return [line['text'].split('warning:', 1)[1] for line in excerpt['lines'] if 'warning:' in line['text']]
assert len(warnings(ci)) == 36
assert warnings(ci) == warnings(read('reports/sphere-triangle-lab-job-126290485434-excerpt.json'))
assert not any('sphere_triangle_mesh' in l['text'] and 'warning:' in l['text'] for l in ci['lines'])

http = read('reports/sphere-triangle-mesh-public-bytes.json')
assert http['commit'] == commit and http['status'] == 'PASS' and len(http['files']) == 29
for f in http['files']:
    data = subprocess.check_output(['git', 'show', commit + ':' + f['path']], cwd=root)
    assert digest(data) == {k: f[k] for k in ['bytes', 'sha256']}
# Browser proof was taken on the first code commit; verify all observed resources
# are byte-identical on the final one rather than pretending a second UI run.
initial = read('reports/sphere-triangle-mesh-initial-public-bytes.json')
old = {f['path']: f for f in initial['files']}
observed = ['docs/learn/diagrams/sphere-triangle-mesh.svg', 'index.html', 'samples/app.mjs',
            'samples/back-cover.mjs', 'engine/simulation.mjs', 'engine/renderer.mjs',
            'tools/sphere-triangle-lab.html', 'tools/sphere-triangle-lab.mjs',
            'assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json',
            'assets/robot-back-cover.skin.json', 'assets/robot-back-cover.scene.json']
for p in observed:
    final = next(f for f in http['files'] if f['path'] == p)
    assert digest(subprocess.check_output(['git', 'show', initial['commit'] + ':' + p], cwd=root)) == {k: final[k] for k in ['bytes', 'sha256']}
    assert old[p]['sha256'] == final['sha256']
b = root / 'reports/sphere-triangle-mesh-public-browser'
assert 'C++ WASM / WEBGPU READY' in (b / 'game-ready.ax.txt').read_text(encoding='utf8')
assert '成功 / separated' in (b / 'lab-default.ax.txt').read_text(encoding='utf8')
local = read('reports/sphere-triangle-mesh-local-verification.json')
assert local['status'] == 'PASS' and all(c['exit'] == 0 for c in local['commands'])
native = read('reports/sphere-triangle-mesh-core-proof/acceptance.json')
assert native['status'] == 'PASS' and native['nativeGroups'] == native['asanGroups'] == 59
fixture = (root / 'reports/sphere-triangle-mesh-marker-proof/fixtures.stdout.txt').read_bytes()
assert sha256(fixture).hexdigest() == native['fixtureSHA256'] and len(fixture) == native['fixtureBytes']
for p in root.glob('reports/sphere-triangle-mesh-*'):
    if p.is_file() and p.name != 'sphere-triangle-mesh-public-verification.json':
        evidence.append(p.relative_to(root).as_posix())
for folder in ['reports/sphere-triangle-mesh-public-browser', 'reports/sphere-triangle-mesh-marker-proof']:
    evidence.extend(p.relative_to(root).as_posix() for p in (root / folder).iterdir() if p.is_file())
report = {'schema': 1, 'status': 'PASS', 'commit': commit, 'checked': datetime.now(timezone.utc).isoformat(),
          'ctest': 33, 'node': 516, 'nativeGroups': 59, 'asanUbsanGroups': 59,
          'fixtures': 48, 'referenceComponents': 2775, 'negativeControls': 43,
          'warningLines': 36, 'warningDiagnosticsUnchanged': True,
          'publicFiles': len(http['files']), 'publicBytes': sum(f['bytes'] for f in http['files']),
          'browserCommit': initial['commit'], 'observedResourcesUnchanged': observed,
          'scope': 'Native finite read-only set query; current SDK/World/CCD/game mesh contact not connected.',
          'ciScope': 'All job and step states; bounded selected log lines including all warnings, not full logs.',
          'evidence': {p: digest((root / p).read_bytes()) for p in sorted(set(evidence))}}
(root / 'reports/sphere-triangle-mesh-public-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: v for k, v in report.items() if k != 'evidence'}, indent=2))
