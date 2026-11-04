"""Summarize original command evidence, independent proofs and preserved SDK scope."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from collections import Counter
import json,re
root=Path(__file__).resolve().parents[2]
out=root/'reports/sphere-triangle-mesh-trajectory-checks/run-20261104-root'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':sha256(b).hexdigest()}
commands=read(out/'native-commands.json')+read(out/'final-accepted/native-final-commands.json')+read(out/'regressions-commands.json')+read(out/'trajectory-validate-commands.json')
assert all(c['exit']==0 for c in commands)
for c in commands:assert digest(root/c['stdout'])==c['stdoutHash'] and digest(root/c['stderr'])==c['stderrHash']
assert '100% tests passed, 0 tests failed out of 35' in (out/'ctest.stdout.txt').read_text()
final_test=(out/'final-accepted/native-final-test.stdout.txt').read_text()
assert '100% tests passed, 0 tests failed out of 1' in final_test and 'PASS 69 groups; 62 complete-input finite trajectory fixtures' in final_test
node=(out/'node.stdout.txt').read_text(encoding='utf8');assert all(x in node for x in ['tests 544','pass 544','fail 0','skipped 0'])
assert 'Web build 457dd1cda43de02c: 47 versioned modules' in (out/'web-build.stdout.txt').read_text()
baseline=read(root/'reports/sphere-triangle-mesh-trajectory-baseline.json')
for p,h in baseline['protected'].items():assert digest(root/p)==h,p
manifest=read(root/'assets/pikapika-simulation.build.json');assert manifest==baseline['manifest']
assert len(manifest['sourceSha256'])==57 and len(manifest['licenses'])==7
exports=json.loads(next(f.split('=',1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')));assert len(set(exports))==len(exports)==74
reference=read(out/'trajectory-reference.stdout.txt');assert reference['status']=='PASS'
fixtures=read(out/'final-accepted/native-final-fixtures.json');assert fixtures['kind']=='sphere-triangle-mesh-trajectory-fixtures'
assert reference['fixtures']==len(fixtures['fixtures']) and reference['fixtures']>=32
counts=dict(Counter(f['result']['status'] for f in fixtures['fixtures']))
assert counts.get('separated',0)>=8 and counts.get('penetration_witness',0)>=2 and counts.get('not_certified',0)>=3 and counts.get('invalid_input',0)>=3
negative=read(out/'trajectory-negative-controls/negative-controls.json');assert negative['status']=='PASS' and len(negative['rejectedControls'])>=20
sdk=read(out/'sdk/report.json');assert (sdk['packetNumericComparisons'],sdk['modelNumericComparisons'],sdk['negativeZeroComparisons'])==(27160,20808,4453)
assert sdk['reference']['primitiveReference']['referenceComponents']+sdk['reference']['aggregateReferenceComponents']==2775
assert len(read(out/'sdk/negative-controls/negative-controls.json')['rejectedControls'])==43
old=read(out/'single-sdk/report.json');assert (old['packetNumericComparisons'],old['modelNumericComparisons'])==(22327,13432)
prior=read(out/'native-final-commands.json');assert [c['exit'] for c in prior]==[0,8]
report={'schema':1,'status':'PASS','generated':datetime.now(timezone.utc).isoformat(),'baseCommit':baseline['baseCommit'],'commands':commands,'ctest':35,'ctestScope':'All 35 passed with this unchanged kernel. Final test-only corpus expansion was rebuilt and verified as one dedicated CTest with 69 groups.','nativeGroups':69,'node':544,'webBuild':'457dd1cda43de02c','webModules':47,'webEntries':23,'nativeFixtures':len(fixtures['fixtures']),'statusCounts':counts,'reference':reference,'negativeControls':negative,'nativeFixtureFile':digest(out/'final-accepted/native-final-fixtures.json'),'protectedFiles':len(baseline['protected']),'protectedSourcesAssetsSdkUnchanged':True,'exportsUnchanged':74,'sdkSourcesUnchanged':57,'licensesUnchanged':7,'artifacts':manifest['artifacts'],'sdk':sdk,'oldSingle':old,'earlierTestOnlyAttempt':{'commands':prior,'status':'CORRECTED','reason':'The extra lost-low-term regression assumed anchor=start; actual interval operations gave anchor=end. Kept original input and added a separately analysed inside-anchor case; kernel unchanged, final69 pass.'},'publicCiPages':'NOT_YET_VERIFIED','sanitizer':'New GNU ASan/UBSan and warning audit scheduled in public CI; no new local Windows sanitizer success claimed.','scope':'Native-only proof for a defined linear parameterized sphere path against static triangles; no new shared SDK, TOI, World/response/game integration.'}
(root/'reports/sphere-triangle-mesh-trajectory-local-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:report[k] for k in ['status','ctest','node','nativeFixtures','statusCounts','protectedFiles','webBuild']}))
