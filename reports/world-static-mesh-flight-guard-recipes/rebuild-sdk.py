"""Capture the formal existing SDK rebuild after the explicit core source change."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
out=(ROOT/sys.argv[1]).resolve()
assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
base=json.loads((ROOT/'reports/world-static-mesh-flight-guard-baseline.json').read_text(encoding='utf8'))
before_manifest=json.loads((ROOT/'assets/pikapika-simulation.build.json').read_text(encoding='utf8'))
assert before_manifest==base['sdkManifest']
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
sources=[*before_manifest['sourceSha256'],'scripts/build-simulation.mjs']
def frozen():return {p:info((ROOT/p).read_bytes()) for p in sources}
before=frozen();args=['node','scripts/build-simulation.mjs']
start=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
try:
 p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=300)
 code,stdout,stderr,timedout=p.returncode,p.stdout,p.stderr,False
except subprocess.TimeoutExpired as e:code,stdout,stderr,timedout=None,e.stdout or b'',e.stderr or b'',True
row={'name':'formal-sdk-rebuild','args':args,'started':started,'wallSeconds':time.perf_counter()-start,'exit':code,'timedOut':timedout,'sourceBefore':before,'sourceAfter':frozen()}
row['sourceStable']=row['sourceBefore']==row['sourceAfter']
for stream,raw in [('stdout',stdout),('stderr',stderr)]:
 path=out/(stream+'.txt');path.write_bytes(raw);row[stream]=path.relative_to(ROOT).as_posix();row[stream+'Hash']=info(raw)
(out/'commands.json').write_text(json.dumps([row],indent=2)+'\n',encoding='utf8')
assert code==0 and not timedout and row['sourceStable']
after=json.loads((ROOT/'assets/pikapika-simulation.build.json').read_text(encoding='utf8'))
assert after['sources']==before_manifest['sources'] and set(after['sourceSha256'])==set(before_manifest['sourceSha256'])
assert len(after['sources'])==32 and len(after['sourceSha256'])==67
changed=[p for p in after['sourceSha256'] if after['sourceSha256'][p]!=before_manifest['sourceSha256'][p]]
assert changed==['core/src/core.cpp'],changed
assert after['licenses']==before_manifest['licenses']
for path,stamp in after['artifacts'].items():assert info((ROOT/path).read_bytes())==stamp,path
exports=json.loads(next(s.split('=',1)[1] for s in after['flags'] if s.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports)==92 and not any('world_static_mesh_flight_guard' in s for s in after['sources'])
for path,stamp in base['protected'].items():
 if path not in base['permittedOldSources']:assert info((ROOT/path).read_bytes())==stamp,path
record={'schema':1,'status':'PASS','scope':'Formal SDK build/artifact provenance only. Native/SDK numerical and browser regressions are still required; no new World guard export or Native binding in Wasm.',
 'sourceStable':True,'sourcesChanged':changed,'exports':92,'compiledTranslationUnits':32,'sourceHeaders':67,
 'runtimeMembers':len(after['linkedLibraryMembers']),'runtimeMembersUnchanged':after['linkedLibraryMembers']==before_manifest['linkedLibraryMembers'],
 'licenseNotices':len(after['licenses']),'artifacts':after['artifacts'],'beforeArtifacts':before_manifest['artifacts'],
 'beforeManifest':before_manifest,'afterManifest':after,'command':row}
(out/'build-observation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:record[k] for k in ['status','sourceStable','sourcesChanged','exports','compiledTranslationUnits','sourceHeaders','runtimeMembers','runtimeMembersUnchanged','licenseNotices','artifacts']}))
