"""Verify actual artifact provenance and gather the finite local acceptance."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import subprocess

root = Path(__file__).resolve().parents[2]
run = root / 'reports/sphere-triangle-sdk-checks/run-20261103T232431069618Z'


def digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


manifest = load(root / 'assets/pikapika-simulation.build.json')
previous = json.loads(subprocess.check_output(['git', 'show', '1e5fe84:assets/pikapika-simulation.build.json'], cwd=root))
assert len(manifest['sourceSha256']) == 55 and len(manifest['licenses']) == 7
for group in ['sourceSha256', 'licenses']:
    for name, expected in manifest[group].items():
        assert digest((root / name).read_bytes())['sha256'] == expected, name
for name, expected in manifest['artifacts'].items():
    assert digest((root / name).read_bytes()) == expected, name
assert manifest['licenses'] == previous['licenses']
assert manifest['linkedLibraryMembers'] == previous['linkedLibraryMembers']
changed = [name for name, value in previous['sourceSha256'].items() if manifest['sourceSha256'][name] != value]
assert sorted(changed) == ['core/include/pikapika/simulation_api.h', 'core/src/simulation_api.cpp']
added = sorted(set(manifest['sourceSha256']) - set(previous['sourceSha256']))
assert added == ['core/include/pikapika/sphere_triangle.hpp', 'core/src/sphere_triangle.cpp']
assert manifest['sourceFlags']['core/src/sphere_triangle.cpp'] == ['-fno-fast-math', '-ffp-contract=off']
header = (root / 'core/include/pikapika/simulation_api.h').read_text(encoding='utf8')
assert len(set(re.findall(r'\b(pp_sim_\w+)\s*\(', header))) == 68
pure = load(root / 'reports/sphere-triangle-sdk-standalone/provenance.json')['pureKernelSources']
for record in pure:
    assert digest((root / record['path']).read_bytes()) == {k: record[k] for k in ['bytes', 'sha256']}
authored = {}
for p in sorted((root / 'assets').rglob('*')):
    name = p.relative_to(root).as_posix()
    if not p.is_file() or name in ['assets/pikapika-simulation.build.json', *manifest['artifacts']]:
        continue
    data = p.read_bytes()
    assert data == subprocess.check_output(['git', 'show', '1e5fe84:' + name], cwd=root), name
    authored[name] = digest(data)
commands = {phase: load(run / (phase + '-commands.json')) for phase in ['native', 'validate', 'recheck']}
assert all(c['exit'] == 0 for c in commands['native'] + commands['recheck'])
assert [c['name'] for c in commands['validate'] if c['exit']] == ['node']
node = (run / 'node-final.stdout.txt').read_text(encoding='utf8')
assert 'tests 502' in node and 'pass 502' in node and 'fail 0' in node and 'skipped 0' in node
assert '100% tests passed' in (run / 'ctest.stdout.txt').read_text(encoding='utf8')
sdk = load(run / 'sdk/report.json')
assert sdk['status'] == 'PASS' and sdk['completed'] == 88 and sdk['expectedModelFailures'] == 23 and sdk['hostRejected'] == 2
browser = load(root / 'reports/sphere-triangle-sdk-local-browser/boost-paused.json')
assert browser['failure'] is None and browser['counts']['queries'] == browser['counts']['validated'] == 20
assert browser['renderer']['residentMeshes'] == 3 and not browser['renderer']['lost']
assert browser['startup']['diagnostics']['wasmBytes'] == manifest['artifacts']['assets/pikapika-simulation.wasm']['bytes']
assets = {name: digest((root / name).read_bytes()) for name in ['assets/pikapika-simulation.build.json', *manifest['artifacts']]}
report = {'schema': 1, 'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(), 'commands': commands,
    'initialFailure': 'Initial Node 500/502: linked report did not yet exist; profiler test hardcoded old 53 sources/66 exports. Report created; test now compares complete source/hash map and export count from actual header. Original failed outputs retained.',
    'nativeCTest': 32, 'nativeApiGroups': 77, 'nodeTests': 502, 'nodeSkipped': 0, 'sdk': sdk,
    'assets': assets, 'exports': 68, 'sourceHeaderCount': 55, 'changedExistingSources': changed, 'addedSources': added,
    'runtimeNoticesUnchanged': True, 'linkedLibraryMembersUnchanged': True, 'pureKernelUnchanged': True,
    'authoredAssetsUnchanged': authored, 'localBrowser': {'scope': 'Existing robot game compatibility only; triangle query is not integrated into game contacts.',
        'buildId': browser['startup']['diagnostics']['buildId'], 'queries': 20, 'validated': 20, 'residentMeshes': 3},
    'files': {p.relative_to(root).as_posix(): digest(p.read_bytes()) for folder in [run, root / 'reports/sphere-triangle-sdk-local-browser', root / 'reports/sphere-triangle-sdk-standalone'] for p in sorted(folder.rglob('*')) if p.is_file()},
    'publicVerification': 'Not yet checked; recorded separately after milestone push.',
    'limits': 'Finite instantaneous read-only query. No World/CCD/manifold/triangle impulse response, fluid, damage or specialized simulator completion claim.'}
(root / 'reports/sphere-triangle-sdk-local-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({'status': report['status'], 'node': 502, 'ctest': 32, 'exports': 68, 'files': len(report['files'])}))
