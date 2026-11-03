import hashlib
import json
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[2]
subprocess.run([sys.executable, str(root / 'reports/derived-readback-recipes/staged-audit.py')], cwd=root, check=True)
record = json.loads(subprocess.check_output(['git', 'show', ':reports/derived-readback-public-verification.json'], cwd=root))
checked = []
for f in record['files']:
    data = subprocess.check_output(['git', 'show', ':' + f['path']], cwd=root)
    assert len(data) == f['bytes'] and hashlib.sha256(data).hexdigest() == f['sha256'], f['path']
    checked.append(f)
subprocess.run(['git', 'diff', '--cached', '--quiet', 'ef01017', '--', 'core', 'assets', 'engine', 'samples',
                'tests', 'tools', 'scripts', '.github', 'CMakeLists.txt'], cwd=root, check=True)
result = dict(status='PASS', publicFiles=checked, testedCodeRevision=record['revision'], runtimeChanged=False)
(root / 'reports/derived-readback-public-staged-audit.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(dict(status='PASS', publicFiles=len(checked), runtimeChanged=False)))
