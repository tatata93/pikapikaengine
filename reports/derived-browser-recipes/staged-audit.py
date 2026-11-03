import hashlib
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]
def blob(p):
    return subprocess.check_output(['git','show', ':'+p], cwd=root)
checked = {}
def check(p, expected):
    data = blob(p)
    assert hashlib.sha256(data).hexdigest() == expected, p
    assert data == (root/p).read_bytes(), p+' working/index mismatch'
    checked[p] = dict(bytes=len(data), sha256=expected)
for row in json.loads(blob('reports/derived-browser-archive.json'))['files']:
    check(row['path'], row['sha256'])
manifest = json.loads(blob('assets/pikapika-simulation.build.json'))
for family in ['sourceSha256','licenses','artifacts']:
    for p, expected in manifest[family].items():
        check(p, expected['sha256'] if isinstance(expected,dict) else expected)
for name in ['local','public']:
    record = root/('reports/derived-browser-'+name+'-verification.json')
    if record.exists():
        result = json.loads(blob(str(record.relative_to(root)).replace('\\','/')))
        for p,h in result.get('sourceHashes',{}).items():
            check(p,h)
        for row in result.get('files',[]):
            check(row['path'],row['sha256'])
subprocess.run(['git','diff','--cached','--quiet','HEAD','--','core','assets','engine','samples','CMakeLists.txt'],cwd=root,check=True)
record=dict(status='PASS', sdkSources=len(manifest['sourceSha256']), notices=len(manifest['licenses']),
            artifacts=len(manifest['artifacts']), files=checked)
(root/'reports/derived-browser-staged-audit.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS', files=len(checked))))
