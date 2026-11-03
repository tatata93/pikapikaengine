import json
import pathlib
import subprocess
import sys
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
base = root / 'build/derived-browser-raw-checks'
base.mkdir(exist_ok=True)
out = pathlib.Path(tempfile.mkdtemp(prefix='run-', dir=base))
scope = sys.argv[1] if len(sys.argv) > 1 else 'local'
assert scope in ['local', 'public']
files = sorted((root / ('reports/derived-browser-' + scope)).glob('*.json'))
assert len(files) == 6
groups = [(scope, [str(p.relative_to(root)) for p in files])]
if scope == 'local':
    groups.append(('historical', ['reports/derived-gpu-public-' + n + '.json' for n in ['4','64','512','retry-4']]))
results = []
for name, paths in groups:
    args = ['node', 'scripts/verify-derived-gpu-lab.mjs', *paths]
    result = subprocess.run(args, cwd=root, capture_output=True, timeout=90)
    (out / (name + '.stdout.txt')).write_bytes(result.stdout)
    (out / (name + '.stderr.txt')).write_bytes(result.stderr)
    entry = dict(name=name, args=args, exitCode=result.returncode)
    results.append(entry)
    (out / 'commands.json').write_bytes((json.dumps(results, indent=2)+'\n').encode())
    print(result.stdout.decode('utf-8', errors='replace'), flush=True)
    if result.returncode:
        print(result.stderr.decode('utf-8', errors='replace'), flush=True)
        raise RuntimeError(name + ' failed')
    entry['verificationRun'] = json.loads(result.stdout)['runDirectory']
(out / 'commands.json').write_bytes((json.dumps(results, indent=2)+'\n').encode())
(base / ('latest-' + scope + '.json')).write_bytes((json.dumps(dict(runDirectory=str(out)), indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS', runDirectory=str(out))))
