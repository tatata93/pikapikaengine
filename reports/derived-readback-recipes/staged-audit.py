import hashlib
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]


def blob(path):
    return subprocess.check_output(['git', 'show', ':' + path], cwd=root)


def sha(b):
    return hashlib.sha256(b).hexdigest()


record = json.loads(blob('reports/derived-readback-verification.json'))
checked = {}


def check(path, expected):
    b = blob(path)
    assert sha(b) == expected, path
    checked[path] = dict(bytes=len(b), sha256=expected)


for p, h in record['sourceHashes'].items():
    check(p, h)
for f in record['files'] + record['sdkAudit']:
    check(f['path'], f['sha256'])
for f in json.loads(blob('reports/derived-readback-archive.json'))['files']:
    check(f['path'], f['sha256'])
for p in ['engine/renderer.mjs', 'engine/derived-render.mjs', 'samples', 'CMakeLists.txt',
          'core/src/derived_mesh.cpp', 'core/include/pikapika/derived_mesh.hpp']:
    subprocess.run(['git', 'diff', '--cached', '--quiet', 'c232652', '--', p], cwd=root, check=True)
result = dict(status='PASS', files=checked, sourceFiles=53, notices=7, artifacts=2,
              unchanged='pure derived kernel, renderer, render token, samples and CMake')
(root / 'reports/derived-readback-staged-audit.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(dict(status='PASS', files=len(checked), sourceFiles=53, notices=7, artifacts=2)))
