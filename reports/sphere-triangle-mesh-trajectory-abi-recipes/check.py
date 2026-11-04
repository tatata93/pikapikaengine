"""Capture finite commands, bytes, errors and failures without hiding attempts."""
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
phase, directory = sys.argv[1:]
out = root / directory
out.mkdir(parents=True, exist_ok=True)
native = root / 'build/native/Release'
node, cmake, ctest = map(shutil.which, ['node', 'cmake', 'ctest'])
commands = []

def digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}

def run(name, args, filename=None):
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    result = subprocess.run(args, cwd=root, capture_output=True, timeout=600)
    stdout, stderr = out / (filename or name + '.stdout.txt'), out / (name + '.stderr.txt')
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    record = {'name': name, 'args': args, 'started': started, 'wallSeconds': time.perf_counter() - clock, 'exit': result.returncode,
              'stdout': stdout.relative_to(root).as_posix(), 'stderr': stderr.relative_to(root).as_posix(),
              'stdoutHash': digest(result.stdout), 'stderrHash': digest(result.stderr)}
    print(json.dumps({'command': name, 'exit': result.returncode, 'directory': directory}), flush=True)
    return record

if phase == 'baseline':
    old = json.loads((root / 'reports/sphere-triangle-mesh-trajectory-baseline.json').read_text(encoding='utf-8-sig'))
    allowed = ['core/src/simulation_api.cpp', 'core/include/pikapika/simulation_api.h', 'assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json']
    paths = [name for name in old['protected'] if name not in allowed]
    paths += ['core/include/pikapika/sphere_triangle_mesh_trajectory.hpp', 'core/src/sphere_triangle_mesh_trajectory.cpp', 'tests/sphere_triangle_mesh_trajectory_tests.cpp', 'scripts/verify-sphere-triangle-mesh-trajectory.py', 'tests/sphere_triangle_mesh_trajectory_reference_tests.py']
    baseline = {'schema': 1, 'baseCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                'protected': {name: digest((root / name).read_bytes()) for name in paths},
                'allowed': allowed, 'manifest': json.loads((root / 'assets/pikapika-simulation.build.json').read_text(encoding='utf-8-sig')),
                'scope': 'Wire exchange additions may change simulation_api, shared artifacts and manifest. Original kernel, independent checker, all engine/game sources and notice bytes stay protected.'}
    target = root / 'reports/sphere-triangle-mesh-trajectory-abi-baseline.json'
    assert not target.exists()
    target.write_text(json.dumps(baseline, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'baseCommit': baseline['baseCommit'], 'protected': len(paths)}))
elif phase == 'native':
    for name, args, filename in [
        ('configure', [cmake, '-S', '.', '-B', 'build/native'], None),
        ('native-build', [cmake, '--build', 'build/native', '--config', 'Release', '--parallel', '2'], None),
        ('ctest', [ctest, '--test-dir', 'build/native', '-C', 'Release', '--output-on-failure'], None),
        ('fixtures', [str(native / 'pikapika_sphere_triangle_mesh_trajectory_tests.exe'), '--fixtures'], 'native-fixtures.json'),
        ('mesh-fixtures', [str(native / 'pikapika_sphere_triangle_mesh_tests.exe'), '--fixtures'], 'mesh-native-fixtures.json'),
    ]:
        commands.append(run(name, args, filename))
        if commands[-1]['exit']:
            break
elif phase == 'wasm':
    commands.append(run('wasm-build', [node, 'scripts/build-simulation.mjs']))
elif phase == 'native-final':
    commands.append(run('native-final-build', [cmake, '--build', 'build/native', '--config', 'Release', '--target', 'pikapika_sphere_triangle_mesh_trajectory_sdk_tests', '--parallel', '2']))
    if not commands[-1]['exit']:
        commands.append(run('native-final-test', [ctest, '--test-dir', 'build/native', '-C', 'Release', '-V', '-R', '^sphere_triangle_mesh_trajectory_sdk$']))
elif phase == 'warning-final':
    commands.append(run('warning-final-build', [cmake, '--build', 'build/native', '--config', 'Release', '--target', 'pikapika_sphere_triangle_mesh_trajectory_sdk_tests', 'pikapika-sphere-triangle-mesh-trajectory-sdk-probe', '--parallel', '2']))
    if not commands[-1]['exit']:
        commands.append(run('warning-final-test', [ctest, '--test-dir', 'build/native', '-C', 'Release', '-V', '-R', '^sphere_triangle_mesh_trajectory_sdk$']))
    if not commands[-1]['exit']:
        commands.append(run('warning-final-exchange', [sys.executable, '-X', 'utf8', 'scripts/verify-sphere-triangle-mesh-trajectory-native-sdk.py', str(out / 'native-fixtures.json'), str(native / 'pikapika-sphere-triangle-mesh-trajectory-sdk-probe.exe'), str(out / 'native-warning-final')]))
    if not commands[-1]['exit']:
        assert (out / 'native-exchange/packets.json').read_bytes() == (out / 'native-warning-final/packets.json').read_bytes(), 'Style correction changed probe output'
        (out / 'warning-final-byte-identity.json').write_text(json.dumps({'status': 'PASS', 'scope': 'Old and corrected Native probe packets exactly equal; shared WASM and production API/kernel unchanged.', 'packets': digest((out / 'native-warning-final/packets.json').read_bytes())}, indent=2) + '\n', encoding='utf-8')
elif phase == 'exchange':
    commands.append(run('native-exchange', [sys.executable, '-X', 'utf8', 'scripts/verify-sphere-triangle-mesh-trajectory-native-sdk.py', str(out / 'native-fixtures.json'), str(native / 'pikapika-sphere-triangle-mesh-trajectory-sdk-probe.exe'), str(out / 'native-exchange')]))
elif phase == 'wasm-exchange':
    commands.append(run('wasm-wire', [node, 'scripts/verify-sphere-triangle-mesh-trajectory-wasm-wire.mjs', str(out / 'native-exchange/packets.json'), str(out / 'wasm-wire')]))
    if not commands[-1]['exit']:
        commands.append(run('wasm-model', [sys.executable, '-X', 'utf8', 'scripts/verify-sphere-triangle-mesh-trajectory-native-sdk.py', str(out / 'native-fixtures.json'), '-', str(out / 'wasm-exchange'), '--packets', str(out / 'wasm-wire/wasm-packets.json'), '--scope', 'wasm-wire']))
elif phase == 'validate':
    commands.append(run('web-build', [node, 'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = [executor.submit(run, 'node', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
                executor.submit(run, 'syntax', [node, 'scripts/check.mjs']),
                executor.submit(run, 'old-mesh-sdk', [node, 'scripts/verify-sphere-triangle-mesh-sdk.mjs', str(out / 'mesh-native-fixtures.json'), str(native / 'pikapika-sphere-triangle-mesh-sdk-probe.exe'), str(out / 'old-mesh-sdk')])]
        commands.extend(job.result() for job in jobs)
    commands.append(run('old-single-fixtures', [str(native / 'pikapika_sphere_triangle_tests.exe'), '--fixtures'], 'single-native-fixtures.json'))
    if not commands[-1]['exit']:
        commands.append(run('old-single-sdk', [node, 'scripts/verify-sphere-triangle-sdk.mjs', str(out / 'single-native-fixtures.json'), str(native / 'pikapika-sphere-triangle-sdk-probe.exe'), str(out / 'old-single-sdk')]))
    commands.append(run('simulation', [node, 'scripts/verify-simulation.mjs', str(native / 'pikapika-simulation-probe.exe')]))
elif phase == 'recheck':
    commands.append(run('web-build', [node, 'scripts/build-web.mjs']))
    commands.append(run('learn', [node, '--test', 'docs/learn/learn.test.mjs']))
else:
    raise ValueError('Unknown phase')
(out / (phase + '-commands.json')).write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8')
if any(command['exit'] for command in commands):
    raise SystemExit(1)
