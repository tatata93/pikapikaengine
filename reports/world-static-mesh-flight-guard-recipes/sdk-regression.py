"""Fresh existing SDK exchanges after the deliberate actual-core rebuild."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys,time,shutil
ROOT=Path(__file__).resolve().parents[2]
out=(ROOT/sys.argv[1]).resolve();assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
def rel(p):return p.relative_to(ROOT).as_posix()
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
manifest=json.loads((ROOT/'assets/pikapika-simulation.build.json').read_text(encoding='utf8'))
paths=sorted(set([*manifest['sourceSha256'],*manifest['licenses'],'assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json']))
def hashes():return {p:info((ROOT/p).read_bytes()) for p in paths}
initial=hashes();rows=[];node=shutil.which('node');assert node
py=[sys.executable,'-B','-X','utf8']
held='reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json'
guard='reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/native-fixtures.json'
supp='reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/supplemental-fixtures.json'
entry='reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json'
flight_native=rel(out/'flight-native');flight_wire=rel(out/'flight-wire')
commands=[
 ('simulation',[node,'scripts/verify-simulation.mjs','build/native/Release/pikapika-simulation-probe.exe']),
 ('flight-native',py+['scripts/verify-sphere-triangle-mesh-flight-native-sdk.py',held,guard,supp,'build/native/Release/pikapika-sphere-triangle-mesh-flight-sdk-probe.exe',flight_native]),
 ('flight-wire',[node,'scripts/verify-sphere-triangle-mesh-flight-wasm-wire.mjs',flight_native+'/packets.json',flight_wire]),
 ('flight-independent',py+['scripts/verify-sphere-triangle-mesh-flight-native-sdk.py',held,guard,supp,'-',rel(out/'flight-independent'),'--packets',flight_wire+'/wasm-packets.json','--scope','wasm-wire']),
 ('flight-owned',[node,'scripts/verify-sphere-triangle-mesh-flight-sdk.mjs',held,guard,supp,flight_native+'/packets.json',rel(out/'flight-owned')]),
 ('flight-lab',[node,'scripts/verify-sphere-triangle-mesh-flight-lab.mjs',rel(out/'flight-lab')]),
 ('entry-owned',[node,'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs',entry,rel(out/'entry-owned')])]
for name,args in commands:
 before=hashes();start=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
 try:
  p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=240);code,stdout,stderr,timedout=p.returncode,p.stdout,p.stderr,False
 except subprocess.TimeoutExpired as e:code,stdout,stderr,timedout=None,e.stdout or b'',e.stderr or b'',True
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-start,'exit':code,'timedOut':timedout,'sourceBefore':before,'sourceAfter':hashes()}
 row['sourceStable']=row['sourceBefore']==row['sourceAfter']==initial
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  q=out/(name+'.'+stream+'.txt');q.write_bytes(raw);row[stream]=rel(q);row[stream+'Hash']=info(raw)
 rows.append(row);(out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:row[k] for k in ['name','exit','timedOut','sourceStable','wallSeconds']}),flush=True)
 assert code==0 and not timedout and row['sourceStable'],name
(out/'sdk-regression.json').write_text(json.dumps({'schema':1,'status':'PASS','scope':'Existing simulation tolerance checks, complete finite Native/WASM raw/owned flight exchange, existing flight presets and entry owned decoder mathematical regressions. No new World guard browser API or cross-compiler whole-output bit claim.','commands':rows,'sources':initial},indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','commands':len(rows)}))
