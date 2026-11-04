"""Read-only index audit after auto-review requested narrower publication evidence."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,re,subprocess
root=Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def blob(ref,path):return git('show',ref+':'+path)
def info(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
base=json.loads((root/'reports/sphere-triangle-mesh-flight-js-baseline.json').read_text())
assert git('rev-parse','HEAD').decode().strip()==base['baseCommit']
changes=[row.split('\t') for row in git('diff','--cached','--name-status').decode().splitlines()]
assert len(changes)==165
protected=base['protected'];generated=base['generatedEntries']
for path in protected:
 assert blob('HEAD',path)==blob('',path),path
def norm(data):
 data=re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',data)
 return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',data,flags=re.S).replace(b'\r\n',b'\n')
for path in generated:assert norm(blob('HEAD',path))==norm(blob('',path)),path
modified_docs={'docs/PLAN.md','docs/RESEARCH.md','docs/learn/index.html','docs/legal/ASSETS.md','docs/legal/DEPENDENCIES.md','docs/legal/REFERENCES.md'}
new_code={'engine/sphere-triangle-mesh-flight.mjs','scripts/verify-sphere-triangle-mesh-flight-sdk.mjs','scripts/verify-sphere-triangle-mesh-flight-owned.py','tests/sphere-triangle-mesh-flight.test.mjs','tests/sphere_triangle_mesh_flight_owned_reference_test.py'}
new_docs={'docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS.md','docs/SPHERE_TRIANGLE_MESH_FLIGHT_LAB_PLAN.md','docs/learn/diagrams/sphere-triangle-mesh-flight-owned.svg'}
groups=Counter();rows=[]
for status,path in changes:
 if path in generated:assert status=='M';group='generated HTML import maps/build IDs only'
 elif path in modified_docs:assert status=='M';group='milestone documentation'
 elif path in new_docs:assert status=='A';group='new original guide/diagram/next plan'
 elif path in new_code:assert status=='A';group='new owned API/verifiers/tests'
 elif path=='engine/simulation.mjs':assert status=='M';group='one import and two new methods'
 elif path=='.github/workflows/verify.yml':assert status=='M';group='one new proof command and timeout 15 to 20'
 else:
  assert status=='A' and (path.startswith('reports/sphere-triangle-mesh-flight-js-') or path=='reports/2026-11-04-sphere-triangle-mesh-flight-js.md'),path
  group='new task-specific proof records and recipes'
 groups[group]+=1;rows.append({'status':status,'path':path,'group':group,'staged':info(blob('',path))})
runtime=blob('','engine/simulation.mjs')
for text in [
"import {querySphereTriangleMeshHeldLoad,querySphereTriangleMeshFreeFlightGuard} from './sphere-triangle-mesh-flight.mjs';\n",
'  querySphereTriangleMeshHeldLoad(sphere,triangles,horizon,settings={}){\n    return querySphereTriangleMeshHeldLoad(this,sphere,triangles,horizon,settings,sphereTriangleMeshResult);\n  }\n',
'  querySphereTriangleMeshFreeFlightGuard(body,gravity,triangles,horizon,settings={}){\n    return querySphereTriangleMeshFreeFlightGuard(this,body,gravity,triangles,horizon,settings,sphereTriangleMeshResult);\n  }\n']:
 fragment=text.encode();assert runtime.count(fragment)==1;runtime=runtime.replace(fragment,b'',1)
assert runtime==blob('HEAD','engine/simulation.mjs')
workflow=blob('','.github/workflows/verify.yml');command=b'          node scripts/verify-sphere-triangle-mesh-flight-sdk.mjs reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/native-fixtures.json reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/supplemental-fixtures.json build/ci/sphere-triangle-mesh-flight-native-exchange/packets.json build/ci/sphere-triangle-mesh-flight-owned\n'
assert workflow.count(command)==1 and workflow.count(b'    timeout-minutes: 20')==1
assert workflow.replace(command,b'',1).replace(b'    timeout-minutes: 20',b'    timeout-minutes: 15',1)==blob('HEAD','.github/workflows/verify.yml')
verification=json.loads((root/'reports/sphere-triangle-mesh-flight-js-local-verification.json').read_text())
assert verification['status']=='PASS' and (verification['node'],verification['ctest'],verification['focused'])==(661,41,30)
result={'schema':1,'status':'PASS','baseCommit':base['baseCommit'],'stagedTree':git('write-tree').decode().strip(),'files':165,'groups':dict(groups),'protectedGitBlobsUnchanged':len(protected),'generatedHtmlBodiesUnchanged':len(generated),'runtimeOriginalExactlyReconstructed':True,'workflowOriginalExactlyReconstructed':True,'localAcceptance':info((root/'reports/sphere-triangle-mesh-flight-js-local-verification.json').read_bytes()),'changedRows':rows,'scope':'All staged files enumerated and restricted to this authorized milestone. No core/assets/sample/platform/old tool module or old verifier/test is staged. Existing25 HTML changes consist solely of generated import maps/build URLs. Proof files are counted dynamically below; no other-chat game edits are included.'}
# write-tree writes only an immutable index object; it changes no branch/ref/file.
target=root/'reports/sphere-triangle-mesh-flight-js-staged-audit.json';target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:result[k] for k in ['status','stagedTree','files','groups','protectedGitBlobsUnchanged','generatedHtmlBodiesUnchanged','runtimeOriginalExactlyReconstructed','workflowOriginalExactlyReconstructed']}))
