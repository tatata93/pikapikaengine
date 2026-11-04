"""Collect existing isolated prototype observations without rerunning solvers."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ROOT / 'reports/world-static-mesh-flight-advance-checks'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def identity(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


default = read(CHECKS / 'run-20261105-default-002/observation.json')
configured = read(CHECKS / 'run-20261105-configured-001/observation.json')
for record in [default, configured]:
    need(record['status'] == 'PASS' and all(x['exitCode'] == 0 for x in record['commands']), 'actual prototype commands')
need(default['sourcesAndProtectedArtifactsUnchanged'] and configured['sourcesAndAcceptedArtifactsUnchanged'], 'stable source/artifact observations')
for item in default['after']:
    need(identity(ROOT / item['path']) == item, 'default source/artifact changed since actual run')
for path, item in read(CHECKS / 'run-20261105-configured-001/after.json').items():
    need(identity(ROOT / path) == item, 'configured source/artifact changed since actual run')
need(configured['formalArtifactAuditComplete'] is False, 'prototype must not claim formal artifact acceptance')
clock = read(CHECKS / 'run-20261105-configured-001/independent-clock-reference.stdout.txt')
need(clock['status'] == 'PASS' and clock['cases'] == 18 and clock['committed'] == 7 and clock['rejected'] == 11, 'actual finite clock reference result')
controls = read(CHECKS / 'run-20261105-clock-controls-001/controls.json')
need(controls['status'] == 'PASS' and controls['positiveControls'] == 2 and controls['negativeControls'] == 20 and
     all(x['passed'] for x in controls['commands']), 'actual checker controls')
clock_source = identity(Path(__file__).with_name('clock-reference.py'))
need(controls['checkerSha256'] == clock_source['sha256'], 'clock control source binding')
review = read(ROOT / 'reports/world-static-mesh-flight-advance-clock-review/run-001/result.json')
need(review['status'] == 'PASS' and review['sourceStable'] and review['roundingChecks'] == 42149 and
     review['sourceAfter']['sha256'] == clock_source['sha256'], 'separate rational RN review')
need('9 directed groups PASS' in (CHECKS / 'run-20261105-configured-001/configured-tests.stdout.txt').read_text(encoding='utf8'), 'actual Native directed groups')
roots = ['core/include/pikapika/world_static_mesh_flight_advance.hpp',
         'core/src/world_static_mesh_flight_advance.cpp', 'tests/world_static_mesh_flight_advance_tests.cpp',
         'docs/WORLD_STATIC_MESH_FLIGHT_ADVANCE_PLAN.md',
         'docs/learn/diagrams/world-static-mesh-flight-advance.svg',
         'reports/2026-11-05-world-static-mesh-flight-advance-prototype.md',
         'reports/world-static-mesh-flight-advance-recipes',
         'reports/world-static-mesh-flight-advance-checks',
         'reports/world-static-mesh-flight-advance-clock-review',
         'reports/world-static-mesh-flight-advance-local-browser']
paths = set()
for name in roots:
    path = ROOT / name
    if path.is_file():
        paths.add(path)
    else:
        paths.update(p for p in path.rglob('*') if p.is_file())
files = [identity(p) for p in sorted(paths)]
result = {'schema': 1, 'status': 'PROTOTYPE_FINITE_CHECKS_PASS',
          'scope': 'Unintegrated Native experiment only. No formal artifact audit, production CMake/CTest/CI registration, SDK/browser integration or public acceptance.',
          'formalArtifactAuditComplete': False, 'productionIntegrated': False, 'publicAccepted': False,
          'nativeDirectedGroups': 9, 'clock': clock, 'positiveControls': 2, 'negativeControls': 20,
          'rationalRoundingReview': {'checks': 42149, 'uniqueExactInputs': review['uniqueExactInputs'], 'selfTests': 11},
          'expandedExperimentalBuildId': configured['buildId'],
          'sourceAndAcceptedArtifactsRemainUnchanged': True,
          'fileCount': len(files), 'rawBytes': sum(f['bytes'] for f in files), 'files': files,
          'priority': 'First repair the GNU actual-artifact gate failed for feature73. Diagnostic-only fix4923962 is pushed; prototype remains separate local work.',
          'notTested': ['New machine-code binding acceptance', 'Production/scheduler/SDK/browser integration',
                        'Natural allocation/nonreturn failure injection', 'TOI/contact response or general simulator models']}
output = ROOT / 'reports/world-static-mesh-flight-advance-prototype-verification.json'
with output.open('x', encoding='utf8', newline='\n') as stream:
    json.dump(result, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
print(json.dumps({key: result[key] for key in ['status', 'nativeDirectedGroups', 'fileCount', 'rawBytes', 'scope']}))
