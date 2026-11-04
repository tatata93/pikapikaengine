"""Capture finite manual flight-lab commands and exact/declared authored sources."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import time

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-flight-lab'
assert len(sys.argv) >= 3, 'Usage: check.py focused|actual|regressions|owned|summary OUTPUT_DIRECTORY [--with-owned]'
phase, directory, *options = sys.argv[1:]
assert phase in {'focused', 'actual', 'regressions', 'owned', 'summary'}
assert options == [] or phase == 'regressions' and options == ['--with-owned']
out = (ROOT/directory).resolve()
assert out.is_relative_to(ROOT)
out.mkdir(parents=True, exist_ok=True)
command_file = out/(phase+'-commands.json')
assert not command_file.exists(), 'Refuse to overwrite prior phase evidence'
commands = []


def digest(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def normalized_html(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                  re.sub(rb'\?build=[a-f0-9]{16}', b'', raw), flags=re.S).replace(b'\r\n', b'\n')


def sources():
    base = json.loads((ROOT/f'reports/{PREFIX}-baseline.json').read_text(encoding='utf-8'))
    paths = [p for p in base['newSources'] if p.startswith(('tools/', 'tests/', 'scripts/'))]
    paths += list(base['permittedOldSources'])
    raw, authored, normalization = {}, {}, {}
    for path in sorted(set(paths)):
        value = (ROOT/path).read_bytes()
        raw[path] = digest(value)
        if path.endswith('.html'):
            authored[path] = digest(normalized_html(value))
            normalization[path] = 'Only importmap/build-query removal and CRLF-to-LF for generated HTML; raw bytes also captured.'
        else:
            authored[path] = raw[path]
    return authored, raw, normalization


def recipe_hashes():
    return {name: digest((ROOT/name).read_bytes()) if (ROOT/name).is_file() else None
            for name in [f'reports/{PREFIX}-recipes/check.py', f'reports/{PREFIX}-recipes/summary.py']}


def run(name, args, timeout=1800):
    assert not (out/(name+'.stdout.txt')).exists() and not (out/(name+'.stderr.txt')).exists()
    before, raw_before, normalization = sources()
    recipes_before = recipe_hashes()
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    timed_out = False
    try:
        process = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=timeout)
        code, stdout, stderr = process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        code, stdout, stderr = None, error.stdout or b'', error.stderr or b''
    elapsed = time.perf_counter()-clock
    after, raw_after, after_normalization = sources()
    assert normalization == after_normalization
    row = {'name': name, 'args': args, 'started': started, 'wallSeconds': elapsed,
           'exit': code, 'timedOut': timed_out, 'authoredBefore': before, 'authoredAfter': after,
           'authoredStable': before == after, 'rawAuthoredBefore': raw_before, 'rawAuthoredAfter': raw_after,
           'rawAuthoredStable': raw_before == raw_after, 'sourceNormalization': normalization,
           'recipeHashesBefore': recipes_before, 'recipeHashesAfter': recipe_hashes(),
           'recipeScope': 'Recipe hashes are a separate historical audit. An unexecuted summary draft changing during a UI test does not change the UI production-source stability claim.'}
    for stream, data in [('stdout', stdout), ('stderr', stderr)]:
        path = out/(name+'.'+stream+'.txt')
        with path.open('xb') as target:
            target.write(data)
        row[stream] = path.relative_to(ROOT).as_posix()
        row[stream+'Hash'] = digest(data)
    print(json.dumps({'command': name, 'exit': code, 'wallSeconds': elapsed}), flush=True)
    return row


node, python = shutil.which('node'), sys.executable
assert node


def owned():
    return run('old-owned', [node, 'scripts/verify-sphere-triangle-mesh-flight-sdk.mjs',
               'reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json',
               'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/native-fixtures.json',
               'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/supplemental-fixtures.json',
               'reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-final-002/native-exchange/packets.json', str(out/'old-owned')])


try:
    if phase == 'focused':
        commands.append(run('focused', [node, '--test', 'tests/sphere-triangle-mesh-flight-lab.test.mjs']))
    elif phase == 'actual':
        commands.append(run('actual', [node, 'scripts/verify-sphere-triangle-mesh-flight-lab.mjs', str(out/'actual')]))
    elif phase == 'regressions':
        commands.append(run('web-build', [node, 'scripts/build-web.mjs']))
        if commands[-1]['exit'] == 0:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run, name, args) for name, args in [
                    ('node', [node, '--test', 'tests/*.test.mjs', 'docs/learn/learn.test.mjs']),
                    ('syntax', [node, 'scripts/check.mjs'])]]
                commands.extend(future.result() for future in futures)
            if options:
                commands.append(owned())
    elif phase == 'owned':
        commands.append(owned())
    elif phase == 'summary':
        commands.append(run('summary', [python, '-B', '-X', 'utf8', f'reports/{PREFIX}-recipes/summary.py', str(out)]))
finally:
    with command_file.open('x', encoding='utf-8', newline='\n') as target:
        json.dump(commands, target, indent=2)
        target.write('\n')
if not commands or any(row['exit'] != 0 for row in commands):
    raise SystemExit(1)
