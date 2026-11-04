"""Capture the accepted Sphere receipt before the explicit World binding changes."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='041570543724d984c244b91a45f564d140892e30'
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
pre_path='reports/world-static-mesh-flight-guard-development/before-implementation.json'
pre=json.loads((ROOT/pre_path).read_text(encoding='utf8'))
for group in ['protected','generatedEntries','integrations']:
 for path,stamp in pre[group].items():assert info((ROOT/path).read_bytes())==stamp,path
receipt_path='reports/accelerated-sphere-box-coverage-public-verification.json'
receipt_raw=(ROOT/receipt_path).read_bytes();receipt=json.loads(receipt_raw)
assert subprocess.check_output(['git','show',BASE+':'+receipt_path],cwd=ROOT)==receipt_raw
assert receipt['status']=='PASS' and receipt['commit']=='63f5d3d7b841633980eac2006717f30614ee9e1f'
assert receipt['ctest']==45 and receipt['node']==684 and receipt['publicFiles']==113
assert json.loads((ROOT/'assets/pikapika-simulation.build.json').read_text(encoding='utf8'))==pre['sdkManifest']
allowed=['core/src/core.cpp','scripts/build-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json','CMakeLists.txt','.github/workflows/verify.yml','.gitattributes']
permitted={}
for path in allowed:
 raw=(ROOT/path).read_bytes();blob=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
 assert raw==blob or raw.replace(b'\r\n',b'\n')==blob,path
 permitted[path]={'raw':info(raw),'gitBlob':info(blob)}
 if Path(path).suffix not in {'.wasm'}:permitted[path]['gitBlobUtf8']=blob.decode('utf8')
before='reports/world-static-mesh-flight-guard-development/before-core-binding-002/capture.json'
capture=json.loads((ROOT/before).read_text(encoding='utf8'))
assert capture['status']=='PASS' and capture['allProtectedUnchanged'] and len(capture['commands'])==4
record={'schema':1,'baseCommit':BASE,'created':datetime.now(timezone.utc).isoformat(),
 'priorPublicReceipt':receipt_path,'priorPublicReceiptStamp':info(receipt_raw),'preAuthoring':{'path':pre_path,**info((ROOT/pre_path).read_bytes())},
 'protected':pre['protected'],'generatedEntries':pre['generatedEntries'],'permittedOldSources':permitted,'sdkManifest':pre['sdkManifest'],
 'lessonBefore':info((ROOT/'docs/learn/index.html').read_bytes()),'legacyBefore':{'path':before,**info((ROOT/before).read_bytes())},
 'scope':'Accepted Sphere receipt baseline. Explicit old changes are actual core.cpp SSE2 length/private configuration bridges, strict source binding/CMake and native-only guard integration, SDK build flags/provenance and regenerated SDK artifacts, CI and raw report attributes. These changes require full postchange regression and actual object/linked instruction audit; no execution or acceptance is inferred by this snapshot.'}
out=ROOT/'reports/world-static-mesh-flight-guard-baseline.json'
with out.open('x',encoding='utf8',newline='\n') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps({'status':'PASS','base':BASE,'protected':383,'entries':26,'explicitOldPaths':len(allowed)}))
