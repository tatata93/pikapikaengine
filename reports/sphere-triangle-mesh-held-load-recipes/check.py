"""Capture held-load acceptance commands, exact source versions, and raw outputs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, shutil, subprocess, sys, time

root = Path(__file__).resolve().parents[2]
phase, directory = sys.argv[1:]
out = root / directory
out.mkdir(parents=True, exist_ok=True)
commands = []

def digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}

def authored():
    paths = ['CMakeLists.txt', '.github/workflows/verify.yml']
    paths += [p.relative_to(root).as_posix() for prefix in ['core/include/pikapika', 'core/src', 'tests', 'scripts']
              for p in (root / prefix).glob('*held_load*') if p.is_file()]
    paths += ['scripts/check-sphere-triangle-mesh-held-load.py']
    return {p: digest((root / p).read_bytes()) for p in sorted(set(paths)) if (root / p).is_file()}

def run(name, args, timeout=1200):
    before = authored()
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    proc = subprocess.run(args, cwd=root, capture_output=True, timeout=timeout)
    row = {'name': name, 'args': args, 'started': started, 'wallSeconds': time.perf_counter() - clock,
           'exit': proc.returncode, 'authoredBefore': before, 'authoredAfter': authored()}
    row['authoredStable'] = row['authoredBefore'] == row['authoredAfter']
    for stream in ['stdout', 'stderr']:
        data = getattr(proc, stream)
        path = out / (name + '.' + stream + '.txt')
        path.write_bytes(data)
        row[stream] = path.relative_to(root).as_posix()
        row[stream + 'Hash'] = digest(data)
    print(json.dumps({'command': name, 'exit': proc.returncode}), flush=True)
    return row

exe = str(root / 'build/native/Release/pikapika_sphere_triangle_mesh_held_load_tests.exe')
node = shutil.which('node')
python = shutil.which('python')
if phase == 'baseline':
    paths = subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines()
    protected = [p for p in paths if p.startswith(('core/', 'engine/', 'samples/', 'assets/', 'third_party/', 'platform/', 'tests/', 'scripts/', 'tools/'))]
    target = root / 'reports/sphere-triangle-mesh-held-load-baseline.json'
    assert not target.exists()
    result = {'schema': 1, 'baseCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'protected': {p: digest((root / p).read_bytes()) for p in protected},
              'scope': 'All pre-existing core/engine/native/SDK/tests/scripts/tools/game/assets/runtime files byte-protected. New Native-only files plus CMake/CI/docs are the permitted changes.'}
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'protected': len(protected), 'baseCommit': result['baseCommit']}))
elif phase == 'build':
    commands.append(run('configure', ['cmake', '-S', '.', '-B', 'build/native']))
    if not commands[-1]['exit']:
        commands.append(run('build', ['cmake', '--build', 'build/native', '--config', 'Release', '--parallel', '2']))
elif phase == 'native':
    commands.append(run('native-tests', [exe]))
    commands.append(run('native-fixtures', [exe, '--fixtures']))
    (out / 'native-fixtures.json').write_bytes((out / 'native-fixtures.stdout.txt').read_bytes())
elif phase == 'reference':
    fixture = str(out / 'native-fixtures.json')
    commands.append(run('fraction', [python, '-X', 'utf8', 'scripts/check-sphere-triangle-mesh-held-load.py', fixture]))
    commands.append(run('reference', [python, '-X', 'utf8', 'tests/sphere_triangle_mesh_held_load_reference_test.py', fixture, '--output', str(out / 'reference')]))
elif phase == 'regressions':
    commands.append(run('web-build', [node, 'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = [('node', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
                 ('syntax', [node, 'scripts/check.mjs']),
                 ('ctest', ['ctest', '--test-dir', 'build/native', '-C', 'Release', '--output-on-failure'])]
        commands.extend(job.result() for job in [pool.submit(run, name, args) for name, args in tasks])
elif phase == 'old-exchange':
    fixtures = root / 'reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json'
    commands.append(run('old-entry-owned', [node, 'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs', str(fixtures), str(out / 'old-entry-owned')]))
elif phase == 'summary':
    commands.append(run('summary', [python, '-X', 'utf8', 'reports/sphere-triangle-mesh-held-load-recipes/summary.py']))
else:
    raise ValueError('Unknown phase')
(out / (phase + '-commands.json')).write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8')
if any(row['exit'] for row in commands):
    raise SystemExit(1)
