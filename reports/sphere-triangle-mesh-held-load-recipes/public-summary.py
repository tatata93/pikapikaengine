"""Accept exact public Native milestone, jobs/steps/logs and selected Pages bytes."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, re, subprocess
if not __debug__: raise SystemExit('Run without Python -O')
root=Path(__file__).resolve().parents[2]
prefix='sphere-triangle-mesh-held-load'
feature='7844b46863a9b3168e9f831adc5a362f53ce13c8'
def read(path): return json.loads((root/path).read_text(encoding='utf-8-sig'))
def digest(path):
    data=(root/path).read_bytes()
    return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def blob(commit,path): return subprocess.check_output(['git','show',commit+':'+path],cwd=root)
local_path=f'reports/{prefix}-local-verification.json'
base_path=f'reports/{prefix}-baseline.json'
runs_path=f'reports/{prefix}-public-runs.json'
bytes_path=f'reports/{prefix}-public-bytes.json'
local,base,runs,public=map(read,[local_path,base_path,runs_path,bytes_path])
assert local['status']=='PASS' and (local['ctest'],local['node'],local['fixtures'])==(39,631,79)
assert runs['commit']==public['commit']==feature and public['status']=='PASS'
assert public['build']=='6aa725ed1898f4e9' and len(public['files'])==33
assert len(base['protected'])==local['protectedFilesUnchanged']==345
requests=[(base['baseCommit'],p) for p in base['protected']]+[(feature,p) for p in base['protected']]
raw=subprocess.check_output(['git','cat-file','--batch'],cwd=root,input=''.join(c+':'+p+'\n' for c,p in requests).encode())
offset=0;blobs={}
for key in requests:
    end=raw.index(b'\n',offset);header=raw[offset:end].split();assert header[1]==b'blob'
    size=int(header[2]);offset=end+1;data=raw[offset:offset+size];assert raw[offset+size:offset+size+1]==b'\n';offset+=size+1;blobs[key]=data
assert offset==len(raw)
for path,expected in base['protected'].items():
    assert digest(path)==expected,path
    assert blobs[base['baseCommit'],path]==blobs[feature,path],path
for path,expected in local['sources'].items(): assert digest(path)==expected,path
for item in public['files']:
    data=blob(feature,item['path'])
    assert {'bytes':len(data),'sha256':sha256(data).hexdigest()}=={k:item[k] for k in ['bytes','sha256']},item['path']
assert len({f['path'] for f in public['files']})==33
assert {'Engine verification','pages build and deployment'}=={r['name'] for r in runs['runs']}
job_records=[];evidence={local_path,base_path,runs_path,bytes_path}
for run in runs['runs']:
    assert run['head_sha']==feature and run['status']=='completed' and run['conclusion']=='success'
    path=f'reports/{prefix}-run-{run["id"]}.json';evidence.add(path);data=read(path)
    assert data['jobs']
    for job in data['jobs']:
        assert job['run_id']==run['id'] and job['status']=='completed' and job['conclusion']=='success'
        assert job['steps'] and all(s['status']=='completed' and s['conclusion']=='success' for s in job['steps'])
        job_records.append(job)
engine=next(j for j in job_records if j['name']=='portable-core')
assert engine['id']==126443232581
assert 'Audit held-load static mesh path independently' in {s['name'] for s in engine['steps']}
assert len([j for j in job_records if j['name']!='portable-core'])==3
log_path=f'reports/{prefix}-job-{engine["id"]}-excerpt.json'
log=read(log_path);evidence.add(log_path)
assert log['jobId']==engine['id'] and 0<len(log['lines'])<=4096 and log['fullLineCount']>=len(log['lines'])
ordinals=[r['line'] for r in log['lines']];assert ordinals==sorted(set(ordinals)) and ordinals[0]>=1 and ordinals[-1]<=log['fullLineCount']
text='\n'.join(r['text'] for r in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 39','# tests 631','# pass 631','# fail 0','# skipped 0',
               'PASS 92 groups; 79 complete-input finite held-load fixtures','PASS 76 groups; 65 complete-input finite entry fixtures',
               '24 sphere triangle mesh entry C ABI groups passed','PASS 69 groups; 62 complete-input finite trajectory fixtures',
               '25 sphere triangle mesh trajectory C ABI groups passed','3a7679cff9aa2cebf0b162bdb920821d16b272fe645cec5ccc9849f0025dc85e',
               'cmp build/ci/sphere-triangle-mesh-held-load-fixtures.json build/ci/sphere-triangle-mesh-held-load-sanitized-fixtures.json']:
    assert marker in text,marker
for key,value in [('fixtures',79),('selfTestGroups',16),('rejectedControls',63),('certifiedLeaves',748),('cellAudits',2028),('lastMeshReferenceComponents',2268),
                  ('actualModelFixtures',62),('hostRejected',3),('modelNumericComparisons',105056),('modelNegativeZeroComparisons',3239),('originalInputNumericComparisons',4728),('originalInputNegativeZeroComparisons',108)]:
    assert re.search('"'+key+r'"\s*:\s*'+str(value)+r'\b',text),(key,value)
old_path='reports/sphere-triangle-mesh-entry-lab-job-126425511379-excerpt.json';evidence.add(old_path)
warnings=lambda value:[r['text'].split('warning:',1)[1] for r in value['lines'] if 'warning:' in r['text']]
assert len(warnings(log))==len(warnings(read(old_path)))==36
assert Counter(warnings(log))==Counter(warnings(read(old_path)))
workflow=blob(feature,'.github/workflows/verify.yml').decode()
for marker in ['-Werror','-fsanitize=address,undefined','core/src/dynamics.cpp core/src/interval.cpp core/src/sphere_triangle.cpp core/src/sphere_triangle_mesh.cpp core/src/sphere_triangle_mesh_held_load.cpp',
               'python3 scripts/check-sphere-triangle-mesh-held-load.py build/ci/sphere-triangle-mesh-held-load-sanitized-fixtures.json']:
    assert marker in workflow,marker
def jpeg_dimensions(data):
    assert data[:2]==b'\xff\xd8'
    at=2
    while at<len(data):
        assert data[at]==255;marker=data[at+1];at+=2
        length=int.from_bytes(data[at:at+2],'big');assert length>=2
        if marker in {192,193,194}:
            return int.from_bytes(data[at+5:at+7],'big'),int.from_bytes(data[at+3:at+5],'big')
        at+=length
    raise AssertionError('Missing JPEG frame')
screens={}
for name in ['diagram','public-diagram']:
    path=f'reports/sphere-triangle-mesh-held-load-browser/{name}.jpg'
    old=f'reports/sphere-triangle-mesh-held-load-browser/{name}.png'
    data=(root/path).read_bytes()
    assert data==(root/old).read_bytes()
    assert jpeg_dimensions(data)==(1265,760)
    evidence.update([path,old]);screens[name]={'format':'JPEG','width':1265,'height':760,'file':path,'hash':digest(path)}
assert screens['diagram']['hash']==screens['public-diagram']['hash']
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'commit':feature,'local':local,
        'publicFiles':33,'publicBytes':sum(f['bytes'] for f in public['files']),'protectedFilesUnchanged':345,
        'node':631,'ctest':39,'nativeGroups':92,'fixtures':79,'warningsUnchanged':36,'jobs':job_records,
        'browserDisplay':screens,
        'evidence':{p:digest(p) for p in sorted(evidence)},
        'scope':'Native-only exact held-load path versus static finite triangles, independently audited on Windows and Linux. New kernel, interval/mesh/dynamics and tests all instrumented in a separate GNU ASan/UBSan build; Release/sanitized JSON byte comparison succeeded. No Windows sanitizer, Native allocation fault injection, SDK export, World advance/contact response, or new game-contact completion is inferred. Selected public sources and unchanged game/SDK bytes are compared to the exact feature blobs; browser image proves only the original diagram display.'}
(root/f'reports/{prefix}-public-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','commit','nativeGroups','fixtures','node','ctest','publicFiles','publicBytes','warningsUnchanged']}))
