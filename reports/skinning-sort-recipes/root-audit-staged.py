import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[2]
def blob(path):return subprocess.check_output(['git','show',':'+path],cwd=root)
def read(path):return json.loads(blob(path).decode('utf-8'))
checks=[]
def check(path,h,size=None):
    b=blob(path);assert hashlib.sha256(b).hexdigest()==h,path
    if size is not None:assert len(b)==size,path
    checks.append(path)
manifest=read('assets/pikapika-simulation.build.json')
for key in ['sourceSha256','licenses']:
 for path,h in manifest[key].items():check(path,h)
for path,a in manifest['artifacts'].items():check(path,a['sha256'],a['bytes'])
verification=read('reports/skinning-sort-verification.json')
for f in verification['proofMapping']:check(f['report'],f['sha256'],f['bytes'])
for f in verification['sourceArtifacts']:check(f['path'],f['sha256'],f['bytes'])
def resolve(path):
 if not path.startswith('build/'):return path
 return next(m['report'] for m in verification['proofMapping'] if m['source']==path)
core=read('reports/skinning-sort-core-provenance.json')
for key in ['sources','assets','proof']:
 for f in core[key]:check(resolve(f['path']),f['sha256'],f['bytes'])
for f in read('reports/skinning-sort-root-verification.json')['sourceArtifacts']:check(resolve(f['path']),f['sha256'],f['bytes'])
result=dict(status='PASS',target='staged git blobs before warning-fix code commit',checks=len(checks),
 uniqueFiles=len(set(checks)),manifestSources=51,licenses=7,artifacts=2,paths=sorted(set(checks)))
(root/'reports/skinning-sort-staged-audit.json').write_text(json.dumps(result,indent=2)+'\n','utf-8',newline='\n')
print('PASS staged hash/byte audit:',len(checks),'checks,',len(set(checks)),'unique files')
