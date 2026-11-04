"""Record syntax/Web build after the original Native lesson edit; no test rerun."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-docs-web-build-001'

def stamp(p):
    raw = p.read_bytes()
    return {'path': p.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}

def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf8', newline='\n')

def main():
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    protected = sorted(p for folder in ('core', 'engine', 'samples', 'assets')
                       for p in (ROOT / folder).rglob('*') if p.is_file())
    before = [stamp(p) for p in protected]
    write('before.json', before)
    result = {'schema': 1, 'status': 'FAIL', 'started': datetime.now(timezone.utc).isoformat(),
              'scope': 'Actual syntax and Web build after local original lesson edit. Existing source/SDK bytes protected. No Node suite, numerical, GNU, UI or public acceptance.',
              'commands': []}
    try:
        npm = 'npm.cmd' if os.name == 'nt' else 'npm'
        for task in ('check', 'build'):
            argv = [npm, 'run', task]
            start = time.monotonic()
            done = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=180)
            row = {'argv': argv, 'exitCode': done.returncode, 'elapsedSeconds': time.monotonic()-start}
            for stream in ('stdout', 'stderr'):
                path = OUT / (task + '.' + stream + '.txt')
                path.write_bytes(getattr(done, stream))
                row[stream] = stamp(path)
            result['commands'].append(row)
            if done.returncode:
                raise ValueError('Command failed: ' + task)
        result['status'] = 'PASS'
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = [stamp(p) for p in protected]
        write('after.json', after)
        result['protectedFiles'] = len(protected)
        result['protectedUnchanged'] = before == after
        if before != after:
            result['status'] = 'FAIL'
        result['finished'] = datetime.now(timezone.utc).isoformat()
        write('result.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'protectedFiles', 'protectedUnchanged')}))
    return 0 if result['status'] == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
