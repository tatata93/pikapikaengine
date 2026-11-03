import datetime,hashlib,json,pathlib,shutil
root=pathlib.Path(__file__).resolve().parents[2]
def read(p):return json.loads((root/p).read_text('utf-8'))
local=read('reports/skinning-sort-local-browser.json')['observations']
public=read('reports/skinning-sort-public-browser.json')['observations']
assert len(local)==len(public)==6
for a,b in zip(local,public):
 for key in ['action','status','packetText','saveDisabled']:assert a[key]==b[key],(a['action'],key)
 runtime=json.loads(b['runtime'])
 assert runtime['buildId']=='387edd206ca3270e' and runtime['wasmBytes']==574261 and runtime['backend']=='C++ WebAssembly'
 assert b['url']=='https://tatata93.github.io/pikapikaengine/tools/skinning-lab.html?v=331b6cc'
http=read('reports/skinning-sort-public-http.json');assert http['status']=='PASS' and len(http['files'])==8
jobs=read('reports/skinning-sort-public-workflows.json')
for group in ['ci','pages']:assert all(j['status']=='completed' and j['conclusion']=='success' for j in jobs[group]['jobs'])
step=next(s for s in jobs['ci']['jobs'][0]['steps'] if s['name']=='Audit skinning memory and undefined behavior independently')
assert step['conclusion']=='success'
log=(root/'reports/skinning-sort-public-ci.txt').read_text('utf-8')
for text in ['100% tests passed, 0 tests failed out of 28','# tests 323','# pass 323','# skipped 0',
 '"actualResultBitsCompared": 5288','SORT-COVERAGE permutations4=24 permutations1to4=33 duplicateCases=13 invalid5=1',
 'PASS 69 skinning test groups','-Werror=array-bounds','-fsanitize=address,undefined','-fno-sanitize-recover=undefined']:
 assert text in log,text
warnings=[line for line in log.splitlines() if 'warning:' in line]
assert not any('array-bounds' in line for line in warnings)
assert 'ERROR: AddressSanitizer' not in log and 'runtime error:' not in log
for name in ['audit-public.py','verify-public.py']:shutil.copyfile(root/'build/skinning-sort-root'/name,root/'reports/skinning-sort-recipes'/name)
paths=['reports/skinning-sort-public-browser.json','reports/skinning-sort-public-http.json',
 'reports/skinning-sort-public-ci.txt','reports/skinning-sort-public-workflows.json','reports/skinning-sort-public.png',
 'reports/skinning-sort-recipes/audit-public.py','reports/skinning-sort-recipes/verify-public.py']
result=dict(schema=1,status='PASS',date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 codeCommit=jobs['codeCommit'],engineRun=jobs['engineRun'],pagesRun=jobs['pagesRun'],ctest=28,nodeTests=323,skipped=0,
 mainSkinResultBits=5288,gnuWarningAudit='O2 -Werror=array-bounds passed; no array-bounds warnings in full CI log',
 linuxSanitizer='GNU13 ASan/UBSan O1 69 groups; halt on error, no sanitizer diagnostic',
 publicObservations=6,exactLocalPublicDiagnosticJSONMatches=6,byteEqualPublicFiles=8,otherWarnings=warnings,
 files=[dict(path=p,bytes=(root/p).stat().st_size,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in paths],
 scope='Observed finite cases, not all-input safety/precision or renderer/material-damage completion.')
(root/'reports/skinning-sort-public-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8',newline='\n')
print('PASS GNU warning audit + ASan/UBSan69, CI/Pages, Node323, 6 DOM packets, 8 byte-equal files. Other warning lines:',len(warnings))
