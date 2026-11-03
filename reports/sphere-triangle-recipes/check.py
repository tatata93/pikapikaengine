"""Reproducible Native integration checks; never rebuild or replace the Web SDK."""
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
report_root = root / 'reports/sphere-triangle-checks' / datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%S%fZ')
report_root.mkdir(parents=True, exist_ok=False)


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def asset_snapshot():
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted((root / 'assets').rglob('*')) if p.is_file()}


def run(name, args, stdout_name=None):
    clock = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(args, cwd=root, capture_output=True, timeout=600)
    stdout = report_root / (stdout_name or ('sphere-triangle-' + name + '-stdout.bin'))
    stderr = report_root / ('sphere-triangle-' + name + '-stderr.bin')
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    record = {'name': name, 'args': args, 'started': started, 'wallSeconds': time.perf_counter() - clock,
              'exit': result.returncode, 'stdout': stdout.relative_to(root).as_posix(), 'stderr': stderr.relative_to(root).as_posix(),
              'stdoutHash': digest(stdout), 'stderrHash': digest(stderr)}
    print(json.dumps({'command': name, 'exit': result.returncode}), flush=True)
    return record


commands = []
before = asset_snapshot()
node, cmake, ctest = shutil.which('node'), shutil.which('cmake'), shutil.which('ctest')
if sys.platform == 'win32':
    build_dir = 'build/native'
    executable = str(root / 'build/native/Release/pikapika_sphere_triangle_tests.exe')
    configuration = ['--config', 'Release']
    test_configuration = ['-C', 'Release']
else:
    build_dir = 'build/ci'
    executable = str(root / 'build/ci/pikapika_sphere_triangle_tests')
    configuration, test_configuration = [], []
commands.append(run('configure', [cmake, '-S', '.', '-B', build_dir]))
if not commands[-1]['exit']:
    commands.append(run('native-build', [cmake, '--build', build_dir, *configuration, '--parallel', '2']))
if any(c['exit'] for c in commands):
    (report_root / 'sphere-triangle-failed-commands.json').write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8')
    raise SystemExit('Native configure/build failed; original output retained')
commands.append(run('web-build', [node, 'scripts/build-web.mjs']))
with ThreadPoolExecutor(max_workers=3) as executor:
    jobs = [executor.submit(run, 'ctest', [ctest, '--test-dir', build_dir, *test_configuration, '--output-on-failure']),
            executor.submit(run, 'node', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
            executor.submit(run, 'syntax', [node, 'scripts/check.mjs'])]
    commands.extend(job.result() for job in jobs)
commands.append(run('native-fixtures', [executable, '--fixtures'], 'sphere-triangle-native-fixtures.json'))
if not commands[-1]['exit']:
    fixture_file = commands[-1]['stdout']
    commands.append(run('reference', [sys.executable, 'scripts/verify-sphere-triangle.py', fixture_file]))
    commands.append(run('negative-controls', [sys.executable, 'tests/sphere_triangle_reference_tests.py', fixture_file, '--output', 'build/sphere-triangle-reference-integrated']))
after = asset_snapshot()
assert before == after, 'Web SDK or authored asset changed'
sources = ['CMakeLists.txt', '.github/workflows/verify.yml', 'core/include/pikapika/sphere_triangle.hpp',
           'core/src/sphere_triangle.cpp', 'tests/sphere_triangle_tests.cpp', 'tests/sphere_triangle_impact_tests.cpp',
           'scripts/verify-sphere-triangle.py', 'tests/sphere_triangle_reference_tests.py']
report = {'schema': 1, 'status': 'PASS' if all(c['exit'] == 0 for c in commands) else 'FAIL',
          'generated': datetime.now(timezone.utc).isoformat(), 'commands': commands,
          'sources': {name: digest(root / name) for name in sources}, 'assetsUnchanged': True, 'assets': before,
          'nodeVersion': subprocess.check_output([node, '--version'], text=True).strip(),
          'newKernelInMainWebSDK': False}
(root / 'reports/sphere-triangle-local-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'commands': len(commands), 'assetsUnchanged': True}))
if report['status'] != 'PASS':
    raise SystemExit(1)
