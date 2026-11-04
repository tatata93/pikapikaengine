"""Actual old-five/new-seven MSVC artifact audits with the MOVHPD interpreter.

The GNU instruction addition is exercised separately using saved records. These
read-only Windows artifact audits do not execute the binaries or prove clocks.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-windows-audits-001'
OUT.mkdir(parents=True, exist_ok=False)
CASES = [
    {'name': 'old-five', 'script': 'build/world-flight-publication/audit-movhpd-candidate.py',
     'build': 'build/native', 'target': 'pikapika_world_static_mesh_flight_guard_tests.exe',
     'map': 'world-flight-guard.map', 'output': 'reports/world-static-mesh-flight-guard-binding-development/run-014'},
    {'name': 'new-seven', 'script': 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py',
     'build': 'build/wfa2', 'target': 'pikapika_world_static_mesh_flight_advance_tests.exe',
     'map': 'world-flight-advance.map', 'output': 'reports/world-static-mesh-flight-advance-checks/run-20261105-post-movhpd-artifact-001'},
]

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8', newline='\n')

def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}

watched = {Path(__file__).resolve(), ROOT / 'CMakeLists.txt', ROOT / 'cmake/WorldFlightBinding.cmake'}
for case in CASES:
    b = ROOT / case['build']
    watched.update([ROOT / case['script'], b / 'world-flight-binding-Release.json',
                    b / 'pikapika_core.dir/Release/core.obj', b / 'Release' / case['target'],
                    b / 'Release' / case['map'], b / 'Release/pikapika_core.lib'])
before = [stamp(p) for p in sorted(watched)]
write(OUT / 'before.json', before)
(OUT / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
result = {'schema': 1, 'status': 'FAIL', 'started': datetime.now(timezone.utc).isoformat(),
          'scope': 'Actual old5/new7 MSVC object/link/compile provenance after MOVHPD auditor addition; not GNU acceptance, binary execution or complete clock/commit proof.', 'commands': []}
try:
    for case in CASES:
        b = ROOT / case['build']
        argv = [sys.executable, '-B', '-X', 'utf8', str(ROOT / case['script']),
                '--profile', str(b / 'world-flight-binding-Release.json'), '--object', str(b / 'pikapika_core.dir/Release/core.obj'),
                '--binary', str(b / 'Release' / case['target']), '--map', str(b / 'Release' / case['map']),
                '--build-directory', str(b), '--output', str(ROOT / case['output'])]
        start = time.monotonic()
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=180)
        row = {'name': case['name'], 'argv': argv, 'cwd': str(ROOT), 'exitCode': p.returncode,
               'elapsedSeconds': time.monotonic() - start}
        for key, raw in [('stdout', p.stdout), ('stderr', p.stderr)]:
            (OUT / (case['name'] + '.' + key + '.txt')).write_bytes(raw)
            row[key] = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        result['commands'].append(row)
        write(OUT / (case['name'] + '.command.json'), row)
        if p.returncode != 0:
            raise ValueError('Artifact audit failed: ' + case['name'])
        proof = json.loads(p.stdout)
        if proof['status'] != 'PASS' or proof['binaryExecuted'] is not False:
            raise ValueError('Artifact audit scope/status mismatch')
        if case['name'] == 'new-seven':
            scope = proof['advanceScope']
            if any(scope[k] is not False for k in ('clockInstructionsAudited', 'commitPathAudited', 'WorldAdvanceAccepted')):
                raise ValueError('Whole clock/commit proof must remain unclaimed')
        row['audit'] = stamp(ROOT / case['output'] / 'audit.json')
        row['profileSourceCount'] = len(proof['profile']['sources'])
        row['buildId'] = proof['profile']['buildId']
    result['status'] = 'PASS'
except Exception as error:
    result['error'] = type(error).__name__ + ': ' + str(error)
finally:
    after = [stamp(p) for p in sorted(watched)]
    write(OUT / 'after.json', after)
    result.update(inputsStable=before == after, finished=datetime.now(timezone.utc).isoformat())
    if before != after:
        result.update(status='FAIL', error='Source/artifact changed during observation')
    write(OUT / 'result.json', result)
print(json.dumps({k: result[k] for k in ('status', 'inputsStable', 'error') if k in result}))
sys.exit(0 if result['status'] == 'PASS' else 1)
