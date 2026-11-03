"""Retain bounded command results without replacing previous evidence."""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time

root = pathlib.Path(__file__).resolve().parents[2]
name = sys.argv[1]
npm = 'npm.cmd' if sys.platform == 'win32' else 'npm'
commands = {
    'native': (['powershell', '-NoProfile', '-File', 'scripts/build-native.ps1'], 600),
    'sdk': (['node', 'scripts/build-simulation.mjs'], 600),
    'web': ([npm, 'run', 'build'], 120),
    'syntax': ([npm, 'run', 'check'], 180),
    'node': ([npm, 'test'], 240),
    'profile': (['node', 'scripts/profile-derived-readback.mjs', '--output', 'build/derived-readback-root'], 30),
}
args, timeout = commands[name]
base = root / 'build/derived-readback-checks'
base.mkdir(exist_ok=True)
out = pathlib.Path(tempfile.mkdtemp(prefix=name + '-', dir=base))
start = time.time()
timed_out = False
try:
    result = subprocess.run(args, cwd=root, capture_output=True, timeout=timeout)
    code, stdout, stderr = result.returncode, result.stdout, result.stderr
except subprocess.TimeoutExpired as error:
    # subprocess.run kills its direct child. The measured profile is a single
    # Node process, with an additional cooperative deadline inside that process.
    code, stdout, stderr, timed_out = 124, error.stdout or b'', error.stderr or b'', True
files = []
for kind, data in [('stdout', stdout), ('stderr', stderr)]:
    path = out / (kind + '.txt')
    path.write_bytes(data)
    files.append(dict(path=str(path.relative_to(root)), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
record = dict(name=name, args=args, timeoutSeconds=timeout, timedOut=timed_out,
              exitCode=code, elapsedSeconds=time.time()-start, files=files, runDirectory=str(out))
(out / 'command.json').write_bytes((json.dumps(record, indent=2) + '\n').encode())
(base / (name + '-latest.json')).write_bytes((json.dumps(record, indent=2) + '\n').encode())
print(json.dumps(record), flush=True)
if code:
    print(stdout.decode('utf-8', errors='replace')[-6000:])
    print(stderr.decode('utf-8', errors='replace')[-4000:])
sys.exit(code)
