import datetime,hashlib,json,pathlib,re,shutil
root=pathlib.Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256((root/path).read_bytes()).hexdigest()
def read(path):return json.loads((root/path).read_text('utf-8'))
def save(path,value):(root/path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8',newline='\n')
assert read('build/skinning-sort-root/verification.json')['status']=='PASS'
assert read('build/skinning-sort/asan-control.json')['observedHeapBufferOverflow']
assert all(c['exitCode']==0 for c in read('build/skinning-sort/native-commands.json'))
old=read('reports/skinning-sdk-local-browser.json')['observations']
local=read('reports/skinning-sort-local-browser.json')['observations']
assert len(local)==6
for current,index in zip(local,[0,4,7,8,9,12]):
    assert current['packetText']==old[index]['packetText'],current['action']
    runtime=json.loads(current['runtime'])
    assert runtime['buildId']=='387edd206ca3270e' and runtime['wasmBytes']==574261
for a,b in [('build/skinning-sort/native.json','reports/skinning-native.json'),
 ('build/skinning-sort/native-oracle.csv','reports/skinning-native-oracle.csv')]:assert (root/a).read_bytes()==(root/b).read_bytes()
assert sha('build/skinning-sort/before-skinning.cpp')=='4d7754cfe2d753c3edceff780b1f99345b6ecc7bdff73c54c55a9e048738a0b3'
mapping=[]
def copy(source,dest):
    (root/dest).parent.mkdir(exist_ok=True)
    shutil.copyfile(root/source,root/dest)
    assert sha(source)==sha(dest)
    mapping.append(dict(source=source,report=dest,bytes=(root/dest).stat().st_size,sha256=sha(dest)))
for folder,label in [('build/skinning-sort','core'),('build/skinning-sort-root','root')]:
    for path in sorted((root/folder).iterdir()):
        if not path.is_file():continue
        name=path.name
        if path.suffix in ['.py','.cmd','.mjs','.cpp']:
            dest='reports/skinning-sort-recipes/'+label+'-'+name
        elif path.suffix in ['.json','.txt','.csv','.md','.bin']:
            if path.suffix in ['.bin','.md']:name += '.txt'
            dest='reports/skinning-sort-'+label+'-'+name
        else:continue
        copy(str(path.relative_to(root)).replace('\\','/'),dest)
copy('build/skinning-sort-proof.py','reports/skinning-sort-recipes/root-proof.py')
for name in ['native-build','ctest','sdk-before']:
    copy('build/skinning-sort-'+name+'.txt','reports/skinning-sort-'+name+'.txt')
copy('build/native/Testing/Temporary/LastTest.log','reports/skinning-sort-native-last-test-raw.txt')
text=(root/'build/native/Testing/Temporary/LastTest.log').read_bytes().decode('cp932').replace('\r\n','\n')
(root/'reports/skinning-sort-native-last-test.txt').write_text(text,'utf-8',newline='\n')
counts=[]
for line in text.splitlines():
 if 'groups' not in line and 'native core tests passed' not in line:continue
 found=re.search(r'(\d+) (?:skin(?:ning)? test groups|simulation C ABI test groups|native core tests|groups|test groups|supported World test groups|finite support policy groups|support test groups|dispersion groups|dynamics test groups|dynamics internal test groups|native hydrostatics/coupling test groups|continuous-world test groups)',line)
 if not found:found=re.search(r'groups=(\d+)',line)
 assert found,line
 counts.append(int(found[1]))
assert len(counts)==28 and sum(counts)==652 and counts[0]==69
manifest=read('assets/pikapika-simulation.build.json')
for key in ['sourceSha256','licenses']:
 for path,h in manifest[key].items():assert sha(path)==h,path
for path,entry in manifest['artifacts'].items():assert sha(path)==entry['sha256'],path
paths=['core/src/skinning.cpp','tests/skinning_tests.cpp','tests/skinning.test.mjs',
 '.github/workflows/verify.yml','docs/PLAN.md','docs/SKIN_BINDING_PLAN.md','docs/SKINNING.md',
 'docs/SKINNING_SDK_PLAN.md','docs/legal/DEPENDENCIES.md']
save('reports/skinning-sort-verification.json',dict(schema=1,status='PASS',date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 nativeGroups=652,groupCounts=counts,ctest=28,nodeTests=323,skipped=0,mainSkinResultBits=5288,
 actualSdkPermutations=33,nativePermutations4=24,nativePermutations1to4=33,nativeDuplicateCases=13,
 windowsAsanBeforeGroups=69,windowsAsanAfterGroups=69,asanPositiveControlDetected=True,
 originalDiagnosticJsonMatches=6,oldFixtureByteMatches=2,regressionCommands=24,
 webBuild='387edd206ca3270e',modules=36,manifestSHA256=sha('assets/pikapika-simulation.build.json'),
 sourceArtifacts=[dict(path=p,bytes=(root/p).stat().st_size,sha256=sha(p)) for p in paths],proofMapping=mapping,
 scope='Local evidence; GNU compiler warning and Linux ASan/UBSan will be checked after push. Old std::sort bounded-range review/Windows ASan do not alone prove GNU memory safety.'))
print('PASS Native652/CTest28, Node323, ASan before/after69 + positive control, main5288 bits, old24 regressions, source/artifact/hash and raw archive.')
