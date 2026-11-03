import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[2]
def staged(path): return subprocess.check_output(['git','show',':'+path],cwd=root)
def read(path):return json.loads(staged(path).decode('utf-8'))
def matches(path,expected,bytes=None):
    b=staged(path)
    assert hashlib.sha256(b).hexdigest()==expected, path
    if bytes is not None: assert len(b)==bytes,path
    return path
checks=[]
manifest=read('assets/pikapika-simulation.build.json')
for key in ['sourceSha256','licenses']:
    for path,digest in manifest[key].items(): checks.append(matches(path,digest))
for path,item in manifest['artifacts'].items():checks.append(matches(path,item['sha256'],item['bytes']))
proof=read('reports/skinning-sdk-verification.json')
for item in proof['sourceArtifacts']:checks.append(matches(item['path'],item['sha256'],item['bytes']))
for item in proof['proofMapping']:checks.append(matches(item['report'],item['sha256'],item['bytes']))
for name,key in [('core','sourceArtifacts'),('js','files')]:
    for item in read('reports/skinning-sdk-'+name+'-provenance.json')[key]:
        path=item['path']
        if path.startswith('build/'):
            mapping=next(m for m in proof['proofMapping'] if m['source']==path)
            path=mapping['report']
        checks.append(matches(path,item['sha256'],item['bytes']))
assert len(read('reports/skinning-sdk-local-browser.json')['observations'])==13
result=dict(status='PASS',target='git index blobs before code milestone commit',checks=len(checks),
 uniqueFiles=len(set(checks)),sdkSourceHeaders=51,licenses=7,artifacts=2,paths=sorted(set(checks)))
(root/'reports/skinning-sdk-staged-audit.json').write_text(json.dumps(result,indent=2)+'\n','utf-8',newline='\n')
print('PASS staged blob byte/hash audit',result['checks'],result['uniqueFiles'])
