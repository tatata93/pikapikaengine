"""Capture one fresh review command and its raw streams; never edit the target."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
TARGET = ROOT / 'reports/world-static-mesh-flight-advance-recipes/clock-reference.py'


def stamp(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


if __name__ == '__main__':
    if (OUT / 'command.json').exists():
        raise SystemExit('Fresh capture required: command.json already exists')
    command = [sys.executable, '-X', 'utf8', str(OUT / 'review.py')]
    before = stamp(TARGET)
    started = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
    elapsed = time.perf_counter() - start
    (OUT / 'stdout.txt').write_bytes(result.stdout)
    (OUT / 'stderr.txt').write_bytes(result.stderr)
    after = stamp(TARGET)
    record = {
        'schema': 1, 'argv': command, 'cwd': str(ROOT), 'startedUtc': started,
        'elapsedSeconds': elapsed, 'exitCode': result.returncode,
        'source': str(TARGET), 'sourceBefore': before, 'sourceAfter': after,
        'sourceStable': before == after, 'runner': stamp(Path(__file__)),
        'recipe': stamp(OUT / 'review.py'),
        'stdout': {'path': 'stdout.txt', **stamp(OUT / 'stdout.txt')},
        'stderr': {'path': 'stderr.txt', **stamp(OUT / 'stderr.txt')},
    }
    (OUT / 'command.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(record, ensure_ascii=False, indent=2))
    raise SystemExit(result.returncode if before == after else 2)
