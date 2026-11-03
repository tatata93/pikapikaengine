import pathlib,subprocess,json,hashlib
r=pathlib.Path(__file__).resolve().parents[2]
def blob(p):return subprocess.check_output(['git','show',':'+p],cwd=r)
def sha(b):return hashlib.sha256(b).hexdigest()
checked={}
def check(p,h):
    b=blob(p);assert sha(b)==h,p;checked[p]=dict(bytes=len(b),sha256=h)
archive=json.loads(blob('reports/derived-profile-archive.json'))
for f in archive['files']:check(f['path'],f['sha256'])
verification=json.loads(blob('reports/derived-profile-checks/verification.json'))
for p,h in verification['sourceHashes'].items():check(p,h)
environment=json.loads(blob('reports/derived-profile-standard/environment.json'))
for f in environment['authoredSourceHashes']:check(f['path'],f['sha256'])
proof=json.loads(blob('reports/derived-profile-correctness/report.json'))
for p,h in proof['sourceHashes'].items():check(p,h)
check('assets/pikapika-simulation.build.json',environment['sdkManifestSHA256'])
m=json.loads(blob('assets/pikapika-simulation.build.json'))
for family in ['sourceSha256','licenses','artifacts']:
    for p,h in m[family].items():check(p,h['sha256'] if isinstance(h,dict) else h)
if (r/'reports/derived-profile-public-verification.json').exists():
    public=json.loads(blob('reports/derived-profile-public-verification.json'))
    for f in public['files']:check(f['path'],f['sha256'])
subprocess.run(['git','diff','--cached','--quiet','HEAD','--','core','assets','engine','samples','CMakeLists.txt'],cwd=r,check=True)
out=dict(status='PASS',scope='Actual staged blobs match archived raw/source/SDK hashes; production paths unchanged',files=checked)
(r/'reports/derived-profile-staged-audit.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS',files=len(checked),sdkSources=len(m['sourceSha256']),notices=len(m['licenses']),artifacts=len(m['artifacts']))))
