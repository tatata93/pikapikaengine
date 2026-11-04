"""Rerun the corrected reference call, retaining every original command log."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
target = root / 'reports/sphere-triangle-mesh-local-verification.json'
r = json.loads(target.read_text(encoding='utf8'))
assert r['status'] == 'FAIL'
assert [c['name'] for c in r['commands'] if c['exit']] == ['reference']
for path, expected in r['sources'].items():
    data = (root / path).read_bytes()
    assert {'bytes': len(data), 'sha256': sha256(data).hexdigest()} == expected, path
first = root / Path(r['commands'][0]['stdout']).parent
(first / 'original-failed-summary.json').write_bytes(target.read_bytes())
fixture = next(c['stdout'] for c in r['commands'] if c['name'] == 'native-fixtures')
args = [sys.executable, 'scripts/verify-sphere-triangle-mesh.py', fixture]
started, clock = datetime.now(timezone.utc).isoformat(), time.perf_counter()
run = subprocess.run(args, cwd=root, capture_output=True, timeout=120)
def save(name, data):
    p = first / name
    p.write_bytes(data)
    return p.relative_to(root).as_posix(), {'bytes': len(data), 'sha256': sha256(data).hexdigest()}
stdout, oh = save('corrected-reference.stdout.txt', run.stdout)
stderr, eh = save('corrected-reference.stderr.txt', run.stderr)
assert run.returncode == 0, run.stderr
record = {'name': 'reference', 'args': args, 'exit': run.returncode, 'started': started,
          'wallSeconds': time.perf_counter() - clock, 'stdout': stdout, 'stderr': stderr,
          'stdoutHash': oh, 'stderrHash': eh}
r['priorReferenceFailure'] = next(c for c in r['commands'] if c['name'] == 'reference')
r['commands'] = [record if c['name'] == 'reference' else c for c in r['commands']]
for name in ['scripts/verify-sphere-triangle-mesh.py', 'reports/sphere-triangle-mesh-recipes/check.py']:
    data = (root / name).read_bytes()
    r['sources'][name] = {'bytes': len(data), 'sha256': sha256(data).hexdigest()}
r['status'] = 'PASS'
r['recovery'] = 'Only incorrect checker dispatch rerun; original failed summary/stdout/stderr retained. Other verified sources unchanged.'
r['generated'] = datetime.now(timezone.utc).isoformat()
target.write_text(json.dumps(r, indent=2) + '\n', encoding='utf8')
print(run.stdout.decode('utf8'))
