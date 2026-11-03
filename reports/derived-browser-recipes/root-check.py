import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time

root = pathlib.Path(__file__).resolve().parents[2]
base = root / 'build/derived-browser-checks'
base.mkdir(exist_ok=True)
out = pathlib.Path(tempfile.mkdtemp(prefix='run-', dir=base))
commands = []
npm = 'npm.cmd' if sys.platform == 'win32' else 'npm'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(name, args, timeout):
    start = time.time()
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, timeout=timeout)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr = 124, error.stdout or b'', error.stderr or b''
    files = []
    for kind, data in [('stdout', stdout), ('stderr', stderr)]:
        path = out / (name + '.' + kind + '.txt')
        path.write_bytes(data)
        files.append(dict(path=str(path.relative_to(root)), bytes=len(data), sha256=sha(data)))
    commands.append(dict(name=name, args=args, timeoutSeconds=timeout, exitCode=code,
                         elapsedSeconds=time.time()-start, files=files))
    (out / 'commands.json').write_bytes((json.dumps(commands, indent=2) + '\n').encode())
    print(name, code, flush=True)
    if code:
        print(stdout.decode('utf-8', errors='replace')[-7000:])
        print(stderr.decode('utf-8', errors='replace')[-4000:])
        raise RuntimeError(name + ' failed')


run('web', [npm, 'run', 'build'], 120)
names = ['tools/derived-gpu-lab.html', 'tools/derived-gpu-lab.mjs', 'tests/derived-gpu-lab.test.mjs',
         'scripts/verify-derived-gpu-lab.mjs', 'tests/derived-browser-verifier.test.mjs',
         'tools/derived-profile.mjs', 'tools/derived-gpu-profile.mjs', 'tools/derived-gpu-cases.mjs',
         'engine/simulation.mjs', 'engine/renderer.mjs', 'engine/derived-render.mjs',
         'docs/learn/index.html', 'docs/learn/diagrams/derived-readback.svg']
before = {p: sha((root / p).read_bytes()) for p in names}
run('node', [npm, 'test'], 240)
run('syntax', [npm, 'run', 'check'], 180)
after = {p: sha((root / p).read_bytes()) for p in names}
assert before == after, 'Source changed during verification'
manifest = json.loads((root / 'assets/pikapika-simulation.build.json').read_text())
audit = []
for family in ['sourceSha256', 'licenses', 'artifacts']:
    for p, expected in manifest[family].items():
        h = expected['sha256'] if isinstance(expected, dict) else expected
        data = (root / p).read_bytes()
        assert sha(data) == h, p
        audit.append(dict(path=p, bytes=len(data), sha256=h))
subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'core', 'assets', 'engine', 'samples', 'CMakeLists.txt'], cwd=root, check=True)
text = (out / 'node.stdout.txt').read_text(encoding='utf-8')
passed = re.findall(r'(?:# |\u2139 )pass (\d+)', text)
skipped = re.findall(r'(?:# |\u2139 )skipped (\d+)', text)
assert passed and skipped and int(skipped[-1]) == 0
result = dict(status='LOCAL PASS; browser and public acceptance separate', nodePassed=int(passed[-1]),
              nodeSkipped=0, sourceHashes=after, sdkAudit=audit, commands=commands,
              unchanged='core/assets/engine/samples/CMakeLists.txt versus HEAD',
              web=(out / 'web.stdout.txt').read_text(encoding='utf-8'), runDirectory=str(out))
(out / 'verification.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
(base / 'latest.json').write_bytes((json.dumps(dict(runDirectory=str(out)), indent=2) + '\n').encode())
print(json.dumps(dict(status='PASS', nodePassed=result['nodePassed'], nodeSkipped=0, runDirectory=str(out))), flush=True)
