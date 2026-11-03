import pathlib,subprocess,json,hashlib
r=pathlib.Path(__file__).resolve().parents[2]
def blob(p):return subprocess.check_output(['git','show',':'+p],cwd=r)
def sha(b):return hashlib.sha256(b).hexdigest()
checked={}
def check(p,h):
    b=blob(p);assert sha(b)==h,p;checked[p]=dict(bytes=len(b),sha256=h)
for f in json.loads(blob('reports/derived-gpu-archive.json'))['files']:check(f['path'],f['sha256'])
for p,h in json.loads(blob('reports/derived-gpu-checks/verification.json'))['sourceHashes'].items():check(p,h)
for p,h in json.loads(blob('reports/derived-gpu-correctness/report.json'))['sourceHashes'].items():check(p,h)
for p,h in json.loads(blob('reports/derived-gpu-browser-verification.json'))['sourceHashes'].items():check(p,h)
m=json.loads(blob('assets/pikapika-simulation.build.json'))
for family in ['sourceSha256','licenses','artifacts']:
    for p,h in m[family].items():check(p,h['sha256'] if isinstance(h,dict) else h)
for name in ['derived-gpu-local-verification.json','derived-gpu-public-verification.json']:
    if (r/'reports'/name).exists():
        for f in json.loads(blob('reports/'+name))['files']:check(f['path'],f['sha256'])
subprocess.run(['git','diff','--cached','--quiet','HEAD','--','core','assets','engine','samples','CMakeLists.txt'],cwd=r,check=True)
(r/'reports/derived-gpu-staged-audit.json').write_bytes((json.dumps(dict(status='PASS',files=checked),indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS',files=len(checked),sdkSources=len(m['sourceSha256']),notices=len(m['licenses']),artifacts=len(m['artifacts']))))
