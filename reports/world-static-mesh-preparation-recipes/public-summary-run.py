"""Capture the exact-feature public acceptance in a new evidence directory."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
commit, directory = sys.argv[1:]
out = root / directory
out.mkdir(parents=True, exist_ok=False)
args = [sys.executable, '-B', '-X', 'utf8',
        'reports/world-static-mesh-preparation-recipes/public-summary.py', commit, directory]
started = datetime.now(timezone.utc).isoformat()
clock = time.perf_counter()
process = subprocess.run(args, cwd=root, capture_output=True, timeout=120)
row = {'name': 'public-summary', 'args': args, 'started': started,
       'wallSeconds': time.perf_counter() - clock, 'exit': process.returncode}
for label in ['stdout', 'stderr']:
    raw = getattr(process, label)
    path = out / (label + '.txt')
    path.write_bytes(raw)
    row[label] = path.relative_to(root).as_posix()
    row[label + 'Hash'] = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
(out / 'commands.json').write_text(json.dumps([row], indent=2) + '\n', encoding='utf-8')
print(process.stdout.decode('utf-8', errors='replace'))
print(json.dumps({'exit': process.returncode, 'wallSeconds': row['wallSeconds']}))
raise SystemExit(process.returncode)
