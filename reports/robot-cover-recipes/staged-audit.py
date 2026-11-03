import hashlib
import json
import pathlib
import subprocess

root=pathlib.Path(__file__).resolve().parents[2]
def blob(p):return subprocess.check_output(['git','show',':'+p],cwd=root)
checked={}
def check(p,h):
    data=blob(p);assert hashlib.sha256(data).hexdigest()==h,p
    assert data==(root/p).read_bytes(),p+' index/working bytes differ'
    checked[p]=dict(bytes=len(data),sha256=h)
for row in json.loads(blob('reports/robot-cover-archive.json'))['files']:check(row['path'],row['sha256'])
for kind in ['local','public']:
    p='reports/robot-cover-'+kind+'-verification.json'
    if (root/p).exists():
        result=json.loads(blob(p))
        for file,h in result.get('sourceHashes',{}).items():check(file,h)
        for row in result['files']:check(row['path'],row['sha256'])
manifest=json.loads(blob('assets/pikapika-simulation.build.json'))
for family in ['sourceSha256','licenses','artifacts']:
    for p,h in manifest[family].items():check(p,h['sha256'] if isinstance(h,dict) else h)
subprocess.run(['git','diff','--cached','--quiet','HEAD','--','core','CMakeLists.txt','engine/simulation.mjs','engine/skin-binding.mjs','engine/derived-render.mjs',
                'assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json'],cwd=root,check=True)
(root/'reports/robot-cover-staged-audit.json').write_bytes((json.dumps(dict(status='PASS',files=checked),indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS',files=len(checked))))
