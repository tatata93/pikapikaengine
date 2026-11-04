"""Finite, reproducible integration checks. Retain original command outputs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
phase = sys.argv[1]
out = root / (sys.argv[2] if len(sys.argv) > 2 else 'reports/sphere-triangle-mesh-trajectory-checks/' + datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%S%fZ'))
out.mkdir(parents=True, exist_ok=phase != 'native')
commands = []
final_fixtures = root / 'reports/sphere-triangle-mesh-trajectory-checks/run-20261104-root/final-accepted/native-final-fixtures.json'


def digest(p):
    data = p.read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def run(name, args, stdout_name=None):
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    result = subprocess.run(args, cwd=root, capture_output=True, timeout=600)
    stdout, stderr = out / (stdout_name or name + '.stdout.txt'), out / (name + '.stderr.txt')
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    record = {'name': name, 'args': args, 'started': started, 'wallSeconds': time.perf_counter() - clock, 'exit': result.returncode,
              'stdout': stdout.relative_to(root).as_posix(), 'stderr': stderr.relative_to(root).as_posix(), 'stdoutHash': digest(stdout), 'stderrHash': digest(stderr)}
    print(json.dumps({'command': name, 'exit': result.returncode, 'directory': out.relative_to(root).as_posix()}), flush=True)
    return record


node, cmake, ctest = map(shutil.which, ['node', 'cmake', 'ctest'])
native = root / 'build/native/Release'
if phase == 'native':
    for name, args, output in [
        ('configure', [cmake, '-S', '.', '-B', 'build/native'], None),
        ('native-build', [cmake, '--build', 'build/native', '--config', 'Release', '--parallel', '2'], None),
        ('ctest', [ctest, '--test-dir', 'build/native', '-C', 'Release', '--output-on-failure'], None),
        ('fixtures', [str(native / 'pikapika_sphere_triangle_mesh_trajectory_tests.exe'), '--fixtures'], 'native-fixtures.json'),
        ('mesh-fixtures', [str(native / 'pikapika_sphere_triangle_mesh_tests.exe'), '--fixtures'], 'mesh-native-fixtures.json'),
    ]:
        commands.append(run(name, args, output))
        if commands[-1]['exit']:
            break
elif phase == 'native-final':
    commands.append(run('native-final-build', [cmake, '--build', 'build/native', '--config', 'Release', '--target', 'pikapika_sphere_triangle_mesh_trajectory_tests', '--parallel', '2']))
    if commands[-1]['exit'] == 0:
        commands.append(run('native-final-test', [ctest, '--test-dir', 'build/native', '-C', 'Release', '-V', '-R', '^sphere_triangle_mesh_trajectory$']))
    if commands[-1]['exit'] == 0:
        commands.append(run('native-final-fixtures', [str(native / 'pikapika_sphere_triangle_mesh_trajectory_tests.exe'), '--fixtures'], 'native-final-fixtures.json'))
elif phase in ('validate', 'regressions'):
    assert (out / 'native-commands.json').exists()
    assert all(c['exit'] == 0 for c in json.loads((out / 'native-commands.json').read_text(encoding='utf8')))
    commands.append(run('web-build', [node, 'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = [executor.submit(run, 'node', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
                executor.submit(run, 'syntax', [node, 'scripts/check.mjs']),
                executor.submit(run, 'sdk', [node, 'scripts/verify-sphere-triangle-mesh-sdk.mjs', str(out / 'mesh-native-fixtures.json'),
                                            str(native / 'pikapika-sphere-triangle-mesh-sdk-probe.exe'), str(out / 'sdk')])]
        if phase == 'validate':
            jobs.append(executor.submit(run, 'trajectory-reference', [sys.executable, '-X', 'utf8', 'scripts/verify-sphere-triangle-mesh-trajectory.py', str(final_fixtures)]))
        commands.extend(job.result() for job in jobs)
    if phase == 'validate':
        commands.append(run('trajectory-negative', [sys.executable, '-X', 'utf8', 'tests/sphere_triangle_mesh_trajectory_reference_tests.py', str(final_fixtures), '--output', str(out / 'trajectory-negative-controls')]))
    commands.append(run('old-triangle-fixtures', [str(native / 'pikapika_sphere_triangle_tests.exe'), '--fixtures'], 'single-native-fixtures.json'))
    if not commands[-1]['exit']:
        commands.append(run('old-triangle-sdk', [node, 'scripts/verify-sphere-triangle-sdk.mjs', str(out / 'single-native-fixtures.json'), str(native / 'pikapika-sphere-triangle-sdk-probe.exe'), str(out / 'single-sdk')]))
    commands.append(run('existing-simulation', [node, 'scripts/verify-simulation.mjs', str(native / 'pikapika-simulation-probe.exe')]))
elif phase == 'trajectory-validate':
    commands.append(run('trajectory-reference', [sys.executable, '-X', 'utf8', 'scripts/verify-sphere-triangle-mesh-trajectory.py', str(final_fixtures)]))
    commands.append(run('trajectory-negative', [sys.executable, '-X', 'utf8', 'tests/sphere_triangle_mesh_trajectory_reference_tests.py', str(final_fixtures), '--output', str(out / 'trajectory-negative-controls')]))
elif phase == 'recheck':
    commands.append(run('web-build-final', [node, 'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs = [executor.submit(run, 'node-final', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
                executor.submit(run, 'syntax-final', [node, 'scripts/check.mjs'])]
        commands.extend(job.result() for job in jobs)
else:
    raise SystemExit('Expected native, native-final, regressions, trajectory-validate, validate or recheck')
(out / (phase + '-commands.json')).write_text(json.dumps(commands, indent=2) + '\n', encoding='utf8')
if any(c['exit'] for c in commands):
    raise SystemExit(1)
