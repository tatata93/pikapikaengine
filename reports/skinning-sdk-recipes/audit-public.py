import datetime,hashlib,json,pathlib,re,shutil
root=pathlib.Path(__file__).resolve().parents[2]
def read(p):return json.loads((root/p).read_text('utf-8'))
local=read('reports/skinning-sdk-local-browser.json')['observations']
public=read('reports/skinning-sdk-public-browser.json')['observations']
assert len(local)==len(public)==13
for a,b in zip(local,public):
    for key in ['action','status','error','errorHidden','packetText','rows','saveDisabled']:
        assert a[key]==b[key],(a['action'],key)
    runtime=json.loads(b['runtime'])
    assert runtime['buildId']=='dbbe1310b6a753ab' and runtime['wasmBytes']==583708 and runtime['backend']=='C++ WebAssembly'
    assert b['url']=='https://tatata93.github.io/pikapikaengine/tools/skinning-lab.html?v=051c2a9'
http=read('reports/skinning-sdk-public-http.json');assert http['status']=='PASS' and len(http['files'])==7
jobs=read('reports/skinning-sdk-public-workflows.json')
for group in ['ci','pages']:
    assert all(j['status']=='completed' and j['conclusion']=='success' for j in jobs[group]['jobs'])
log=(root/'reports/skinning-sdk-public-ci.txt').read_text('utf-8')
for text in ['100% tests passed, 0 tests failed out of 28','# tests 322','# pass 322','# skipped 0','"actualResultBitsCompared": 5288']:
    assert text in log,text
warnings=[line for line in log.splitlines() if 'warning:' in line]
for name in ['audit-public.py','verify-public.py']:
    shutil.copyfile(root/'build/skinning-sdk'/name,root/'reports/skinning-sdk-recipes'/name)
paths=['reports/skinning-sdk-public-browser.json','reports/skinning-sdk-public-http.json',
 'reports/skinning-sdk-public-ci.txt','reports/skinning-sdk-public-workflows.json','reports/skinning-sdk-public.png',
 'reports/skinning-sdk-recipes/audit-public.py','reports/skinning-sdk-recipes/verify-public.py']
result=dict(schema=1,status='PASS',observedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 codeCommit=jobs['codeCommit'],engineRun=jobs['engineRun'],pagesRun=jobs['pagesRun'],
 ctest=28,nodeTests=322,skipped=0,mainSkinResultBits=5288,publicObservations=13,
 exactLocalPublicDiagnosticJSONMatches=13,byteEqualPublicFiles=7,warnings=warnings,
 warningFollowup='GNU13 std::sort optimization emits array-bounds warnings in 1..4 checked influence array; investigate separately. This run passed but is not warning-free.',
 files=[dict(path=p,bytes=(root/p).stat().st_size,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in paths],
 scope='Observed finite cases on actual public browser and Linux CI; no asset reimport, GPU skinning, contact or precision claim beyond these tests.')
(root/'reports/skinning-sdk-public-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8',newline='\n')
print('PASS public CI/Pages, 7 byte-equal files, 13 observed packets exactly match local; compiler warning lines:',len(warnings))
