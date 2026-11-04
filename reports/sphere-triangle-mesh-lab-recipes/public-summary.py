from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json
root=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':sha256(b).hexdigest()}
local=read(root/'reports/sphere-triangle-mesh-lab-local-verification.json')
public=read(root/'reports/sphere-triangle-mesh-lab-public-bytes.json')
runs=read(root/'reports/sphere-triangle-mesh-lab-public-runs.json')
assert all(r['status']=='completed' and r['conclusion']=='success' and r['head_sha']==public['commit'] for r in runs['runs'])
assert len(runs['runs'])==2
jobs=[]
for id in [41755160638,41755159942]:
 j=read(root/f'reports/sphere-triangle-mesh-lab-run-{id}.json')['jobs'];assert all(x['status']=='completed' and x['conclusion']=='success' and all(s['status']=='completed' and s['conclusion']=='success' for s in x['steps']) for x in j);jobs+=j
log=read(root/'reports/sphere-triangle-mesh-lab-job-126329430810-excerpt.json')
lines=[x['text'] for x in log['lines']];text='\n'.join(lines)
for marker in ['100% tests passed, 0 tests failed out of 34','# tests 544','# pass 544','# fail 0','# skipped 0','"packetNumericComparisons": 27160','"modelNumericComparisons": 20808','"referenceComponents": 2688','"aggregateReferenceComponents": 87','PASS 59 groups','18 sphere triangle mesh C ABI test groups passed','GNU 13.3.0','v22.23.4']:assert marker in text,marker
old=read(root/'reports/sphere-triangle-mesh-sdk-job-126319411407-excerpt.json')
def warnings(source):return [x['text'].split('warning:',1)[1] for x in source['lines'] if 'warning:' in x['text']]
assert len(warnings(log))==36 and warnings(log)==warnings(old)
assert public['status']=='PASS' and len(public['files'])==42
browser=read(root/'reports/sphere-triangle-mesh-lab-public-browser-verification.json');assert browser['status']=='PASS' and (browser['numericBits'],browser['negativeZeroBits'])==(42644,5733)
rational=read(root/'reports/sphere-triangle-mesh-lab-public-rational-verification.json');assert rational['status']=='PASS' and rational['combinedComponents']==7353 and rational['browserAdditionalComponents']==4578
game=read(root/'reports/sphere-triangle-mesh-lab-game-verification.json');assert game['status']=='PASS' and game['coverQueries']==35 and game['allCompleted']
paths=set((root/'reports').glob('sphere-triangle-mesh-lab-*.json'))|set((root/'reports/sphere-triangle-mesh-lab-recipes').glob('*'))
for phase in ['local','public']:paths.update((root/f'reports/sphere-triangle-mesh-lab-{phase}-browser').glob('*'))
target=root/'reports/sphere-triangle-mesh-lab-public-verification.json';paths.discard(target)
report={'schema':1,'status':'PASS','commit':public['commit'],'checked':datetime.now(timezone.utc).isoformat(),'ctest':34,'node':544,'dedicatedLabTests':18,'webBuild':local['webBuild'],'webModules':47,'webEntries':23,'exports':74,'sourceHeaders':57,'licensesUnchanged':7,'cppSdkAssetsGameUnchanged':True,'packetNumericBits':27160,'modelNumericBits':20808,'sdkReferenceComponents':2775,'sdkNegativeControls':43,'warnings':36,'warningDiagnosticsUnchanged':True,'sdkAsanUbsanGroups':18,'pureMeshAsanUbsanGroups':59,'sdkSanitizerScope':'API cpp and SDK tests instrumented; linked regular strict kernel archive. Pure kernel instrumented in separate step. No new local Windows sanitizer success claimed.','publicFiles':42,'publicBytes':sum(x['bytes'] for x in public['files']),'publicBrowser':browser,'publicBrowserRational':rational,'publicGame':game,'ciJobs':jobs,'ciEvidenceScope':'All job/step states and bounded selected original lines including every warning, not full logs.','evidence':{p.relative_to(root).as_posix():digest(p) for p in sorted(paths) if p.is_file()},'scope':'Read-only static finite mesh inspection. World/CCD/manifold/game mesh response and specialist models remain separate.'}
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({k:report[k] for k in ['status','commit','ctest','node','warnings','publicFiles','publicBytes']}))
