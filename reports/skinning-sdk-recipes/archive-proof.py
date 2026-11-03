import datetime, hashlib, json, pathlib, re, shutil

root = pathlib.Path(__file__).resolve().parents[2]
def read(p): return json.loads((root/p).read_text('utf-8'))
def sha(p): return hashlib.sha256((root/p).read_bytes()).hexdigest()
def save(p, value): (root/p).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n','utf-8',newline='\n')

# Assert observed DOM packets, without reconstructing a skin result in JavaScript.
observations = read('reports/skinning-sdk-local-browser.json')['observations']
assert len(observations) == 13
packets = [json.loads(o['packetText']) if o['packetText'].startswith('{') else None for o in observations]
def close(a,b): assert len(a)==len(b) and all(abs(x-y)<2e-14 for x,y in zip(a,b)), (a,b)
expected = [[0,-.2,0],[1.1,-.1,0],[1.2,1,0],[0,.2,0],[.9,.1,0],[.8,1,0]]
for a,b in zip(packets[0]['deformation']['positions'], expected): close(a,b)
assert packets[1] is None and observations[1]['saveDisabled']
close(packets[2]['deformation']['positions'][1], [1.15,-.05,0])
for a,b in zip(packets[3]['deformation']['positions'], packets[3]['source']['vertices']): close(a,b['position'])
matrix=next(p['matrix'] for p in packets[4]['input']['pose'] if p['id']==19)
dot=sum(matrix[i]*matrix[4+i] for i in range(3))
assert abs(dot + 36/25)<2e-14, dot
assert packets[5]['binding']['status']=='ill_conditioned' and packets[5]['binding']['joints'] is None and packets[5]['deformation'] is None
assert packets[6]['deformation']['status']=='completed'
assert packets[7]['deformation']['positions']==[[1,0,0]]
assert packets[8]['deformation']['status']=='numerical_failure' and packets[8]['deformation']['positions'] is None
assert packets[8]['source']['vertices'][0]['influences'][0]['weight']>0
assert packets[9]['deformation']['status']=='completed'
assert packets[10]['deformation']['status']=='invalid_input' and packets[10]['deformation']['positions'] is None
assert packets[11] is None and observations[11]['saveDisabled']
assert packets[12]['deformation']['status']=='completed'
save('reports/skinning-sdk-local-browser-audit.json',dict(status='PASS',observations=13,knownPoseVertices=6,
 shearColumnDot=dot,knownDot=-36/25,scope='Fixed observed DOM packets. Export tested by Node UI harness; no browser file reimport or renderer claim.'))

mapping=[]
for folder,label in [('build/skinning-sdk','core'),('build/skinning-sdk-js','js')]:
    for path in sorted((root/folder).iterdir()):
        if not path.is_file() or path.name=='archive-proof.py': continue
        if path.suffix in ['.py','.mjs']:
            dest='reports/skinning-sdk-recipes/'+label+'-'+path.name
        elif path.suffix in ['.json','.txt','.csv']:
            dest='reports/skinning-sdk-'+label+'-'+path.name
        else: continue
        (root/dest).parent.mkdir(exist_ok=True)
        shutil.copyfile(path,root/dest)
        assert sha(dest)==sha(str(path.relative_to(root)))
        mapping.append(dict(source=str(path.relative_to(root)).replace('\\','/'),report=dest,bytes=path.stat().st_size,sha256=sha(dest)))
for src,dest in [('build/skinning-sdk-node-tests.txt','reports/skinning-sdk-node-tests.txt'),
 ('build/skinning-sdk-native-build.txt','reports/skinning-sdk-native-build.txt'),
 ('build/skinning-sdk-ctest.txt','reports/skinning-sdk-ctest.txt'),
 ('build/skinning-sdk-check.txt','reports/skinning-sdk-check.txt'),
 ('build/skinning-sdk-web-build.txt','reports/skinning-sdk-web-build.txt'),
 ('build/native/Testing/Temporary/LastTest.log','reports/skinning-sdk-native-last-test-raw.txt'),
 ('build/skinning-sdk/archive-proof.py','reports/skinning-sdk-recipes/archive-proof.py'),
 ('build/skinning-lab-actual-tests.txt','reports/skinning-sdk-lab-tests.txt')]:
    shutil.copyfile(root/src,root/dest)
    mapping.append(dict(source=src,report=dest,bytes=(root/dest).stat().st_size,sha256=sha(dest)))
text=(root/'build/native/Testing/Temporary/LastTest.log').read_bytes().decode('cp932').replace('\r\n','\n')
(root/'reports/skinning-sdk-native-last-test.txt').write_text(text,'utf-8',newline='\n')
assert '59 simulation C ABI test groups passed' in text and 'PASS 68 skinning test groups' in text
counts=[]
for line in text.splitlines():
    if '<end of output>' in line: continue
    if 'groups' not in line and 'native core tests passed' not in line: continue
    found=re.search(r'(\d+) (?:skin(?:ning)? test groups|simulation C ABI test groups|native core tests|groups|test groups|supported World test groups|finite support policy groups|support test groups|dispersion groups|dynamics test groups|dynamics internal test groups|native hydrostatics/coupling test groups|continuous-world test groups)',line)
    if not found: found=re.search(r'groups=(\d+)',line)
    assert found,line
    counts.append(int(found[1]))
assert len(counts)==28 and sum(counts)==651, counts

manifest=read('assets/pikapika-simulation.build.json')
core=read('build/skinning-sdk/provenance.json')
js=read('build/skinning-sdk-js/provenance.json')
checks=[]
for item in core['sourceArtifacts']+js['files']:
    assert sha(item['path'])==item['sha256'], item['path']
    checks.append(item['path'])
for key in ['allManifestSourceHeaderHashes','allRuntimeLicenseHashes']:
    for p,h in core[key].items(): assert sha(p)==h, p
assert len(core['allManifestSourceHeaderHashes'])==51 and len(core['allRuntimeLicenseHashes'])==7
assert read('build/skinning-sdk/regressions.json')['status']=='PASS'
assert len(read('build/skinning-sdk/regressions.json')['commands'])==24
assert 'pass 322' in (root/'build/skinning-sdk-node-tests.txt').read_text('utf-8')
sources=['tools/skinning-lab.html','tools/skinning-lab.mjs','tests/skinning-lab.test.mjs',
 'scripts/build-web.mjs','.github/workflows/verify.yml','docs/SKINNING.md','docs/SKINNING_PLAN.md',
 'docs/SKINNING_SDK_PLAN.md','docs/PLAN.md','docs/legal/ASSETS.md','docs/legal/REFERENCES.md','docs/legal/DEPENDENCIES.md']
save('reports/skinning-sdk-verification.json',dict(schema=1,createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 status='PASS',nativeGroups=651,ctest=28,nodeTests=322,skipped=0,abiGroups=59,labTests=11,regressionCommands=24,
 mainReplay=read('build/skinning-sdk-js/report.json'),manifestSourcesChecked=51,licenseFilesChecked=7,
 nativeGroupCounts=counts,webBuild='dbbe1310b6a753ab',modules=36,
 artifactBytes=dict(wasm=(root/'assets/pikapika-simulation.wasm').stat().st_size,glue=(root/'assets/pikapika-simulation.mjs').stat().st_size),
 manifestSHA256=sha('assets/pikapika-simulation.build.json'),sourceChecks=checks,
 sourceArtifacts=[dict(path=p,bytes=(root/p).stat().st_size,sha256=sha(p)) for p in sources],
 proofMapping=mapping,scope='Local verification only. Public CI, Pages and browser verification follow the milestone push.'))
print('PASS observed DOM packets, 51 SDK source/header hashes, 7 licenses, core/JS artifacts, copied evidence; Native28, Node322, regressions24.')
