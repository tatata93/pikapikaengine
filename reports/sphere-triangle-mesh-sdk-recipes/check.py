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
out = root / (sys.argv[2] if len(sys.argv) > 2 else 'reports/sphere-triangle-mesh-sdk-checks/' + datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%S%fZ'))
out.mkdir(parents=True, exist_ok=phase != 'native')
commands = []


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
        ('fixtures', [str(native / 'pikapika_sphere_triangle_mesh_tests.exe'), '--fixtures'], 'native-fixtures.json'),
    ]:
        commands.append(run(name, args, output))
        if commands[-1]['exit']:
            break
elif phase == 'wasm':
    commands.append(run('wasm-build', [node, 'scripts/build-simulation.mjs']))
elif phase == 'validate':
    assert (out / 'native-commands.json').exists()
    assert all(c['exit'] == 0 for c in json.loads((out / 'native-commands.json').read_text(encoding='utf8')))
    commands.append(run('web-build', [node, 'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = [executor.submit(run, 'node', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
                executor.submit(run, 'syntax', [node, 'scripts/check.mjs']),
                executor.submit(run, 'sdk', [node, 'scripts/verify-sphere-triangle-mesh-sdk.mjs', str(out / 'native-fixtures.json'),
                                            str(native / 'pikapika-sphere-triangle-mesh-sdk-probe.exe'), str(out / 'sdk')])]
        commands.extend(job.result() for job in jobs)
    commands.append(run('old-triangle-fixtures', [str(native / 'pikapika_sphere_triangle_tests.exe'), '--fixtures'], 'single-native-fixtures.json'))
    if not commands[-1]['exit']:
        commands.append(run('old-triangle-sdk', [node, 'scripts/verify-sphere-triangle-sdk.mjs', str(out / 'single-native-fixtures.json'), str(native / 'pikapika-sphere-triangle-sdk-probe.exe'), str(out / 'single-sdk')]))
    commands.append(run('existing-simulation', [node, 'scripts/verify-simulation.mjs', str(native / 'pikapika-simulation-probe.exe')]))
elif phase == 'recheck':
    commands.append(run('web-build-final', [node, 'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs = [executor.submit(run, 'node-final', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
                executor.submit(run, 'syntax-final', [node, 'scripts/check.mjs'])]
        commands.extend(job.result() for job in jobs)
else:
    raise SystemExit('Expected native, wasm, validate or recheck')
(out / (phase + '-commands.json')).write_text(json.dumps(commands, indent=2) + '\n', encoding='utf8')
if any(c['exit'] for c in commands):
    raise SystemExit(1)
