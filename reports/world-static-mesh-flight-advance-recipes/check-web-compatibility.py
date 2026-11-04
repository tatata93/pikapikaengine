"""Capture actual Node/syntax/Web regression after local Native registration.

This does not add an advance SDK export or claim any browser physics acceptance.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-web-integration-001'
OUT.mkdir(parents=True, exist_ok=False)

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf8', newline='\n')

def snapshot():
    paths = set()
    for directory in ['core', 'cmake', 'engine', 'samples', 'scripts', 'tests', 'tools', 'assets', 'docs/learn']:
        paths.update(p for p in (ROOT / directory).rglob('*') if p.is_file())
    paths.update(ROOT.glob('*.html'))
    paths.update([ROOT / 'CMakeLists.txt', ROOT / 'package.json', Path(__file__)])
    return {p.relative_to(ROOT).as_posix(): {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
            for p in sorted(paths) for raw in [p.read_bytes()]}

before = snapshot()
write('before.json', before)
(OUT / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
commands = []
result = {'schema': 1, 'status': 'FAIL', 'started': datetime.now(timezone.utc).isoformat(),
          'scope': 'Actual existing Node suite, syntax and Web build compatibility after local Native CMake/auditor registration. No new browser advance API or formal Native clock/commit acceptance.'}
try:
    cases = sorted((ROOT / 'tests').glob('*.test.mjs')) + [ROOT / 'docs/learn/learn.test.mjs']
    calls = [('syntax', ['node', 'scripts/check.mjs']),
             ('node-tests', ['node', '--test', *[str(p.relative_to(ROOT)) for p in cases]]),
             ('web-build', ['node', 'scripts/build-web.mjs'])]
    for name, argv in calls:
        start = time.monotonic()
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=600)
        row = {'name': name, 'argv': argv, 'cwd': str(ROOT), 'exitCode': p.returncode,
               'elapsedSeconds': time.monotonic() - start}
        for label, raw in [('stdout', p.stdout), ('stderr', p.stderr)]:
            (OUT / (name + '.' + label + '.txt')).write_bytes(raw)
            row[label] = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        commands.append(row)
        write(name + '.command.json', row)
        if p.returncode != 0:
            raise ValueError('Command failed: ' + name)
    result['status'] = 'PASS'
except Exception as error:
    result['error'] = type(error).__name__ + ': ' + str(error)
finally:
    after = snapshot()
    write('after.json', after)
    result.update(commands=commands, files=len(before), sourcesAndArtifactsUnchanged=before == after,
                  finished=datetime.now(timezone.utc).isoformat())
    if before != after:
        result.update(status='FAIL', sourceError='Monitored source/assets/SDK/HTML changed during execution')
    write('result.json', result)
print(json.dumps({key: result[key] for key in ('status', 'files', 'sourcesAndArtifactsUnchanged', 'error') if key in result}))
sys.exit(0 if result['status'] == 'PASS' else 1)
