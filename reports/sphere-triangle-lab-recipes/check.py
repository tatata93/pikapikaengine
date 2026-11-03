"""Check the new UI while proving the accepted numerical SDK is unchanged."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil
import subprocess
import time

root = Path(__file__).resolve().parents[2]
out = root / 'reports/sphere-triangle-lab-checks' / datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%S%fZ')
out.mkdir(parents=True, exist_ok=False)


def digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


manifest = json.loads((root / 'assets/pikapika-simulation.build.json').read_text(encoding='utf8'))
unchanged = {}
for name in ['assets/pikapika-simulation.build.json', *manifest['artifacts'], *manifest['sourceSha256'], *manifest['licenses']]:
    data = (root / name).read_bytes()
    assert data == subprocess.check_output(['git', 'show', 'd9cf168:' + name], cwd=root), name
    unchanged[name] = digest(data)
for folder in ['assets', 'samples']:
    for p in sorted((root / folder).rglob('*')):
        if p.is_file():
            name = p.relative_to(root).as_posix()
            data = p.read_bytes()
            assert data == subprocess.check_output(['git', 'show', 'd9cf168:' + name], cwd=root), name
            unchanged[name] = digest(data)


def run(name, args):
    started, clock = datetime.now(timezone.utc).isoformat(), time.perf_counter()
    result = subprocess.run(args, cwd=root, capture_output=True, timeout=300)
    stdout, stderr = out / (name + '.stdout.txt'), out / (name + '.stderr.txt')
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    print(json.dumps({'command': name, 'exit': result.returncode, 'directory': out.relative_to(root).as_posix()}), flush=True)
    return {'name': name, 'args': args, 'exit': result.returncode, 'started': started, 'wallSeconds': time.perf_counter() - clock,
            'stdout': stdout.relative_to(root).as_posix(), 'stderr': stderr.relative_to(root).as_posix(), 'stdoutHash': digest(result.stdout), 'stderrHash': digest(result.stderr)}


node = shutil.which('node')
commands = [run('web-build', [node, 'scripts/build-web.mjs'])]
with ThreadPoolExecutor(max_workers=2) as executor:
    jobs = [executor.submit(run, 'node', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
            executor.submit(run, 'syntax', [node, 'scripts/check.mjs'])]
    commands.extend(job.result() for job in jobs)
report = {'schema': 1, 'status': 'PASS' if all(c['exit'] == 0 for c in commands) else 'FAIL', 'commands': commands,
          'sdkAndAuthoredAssetsUnchanged': unchanged, 'note': 'C++ SDK and sample code/Source are byte unchanged from d9cf168. Native CTest/sanitizers last accepted in the linked SDK milestone; this local UI check does not rerun them.'}
(out / 'commands.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
if report['status'] != 'PASS':
    raise SystemExit(1)
