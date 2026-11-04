"""Compare complete old Native/SDK results after the explicit core binding change."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
out=(ROOT/sys.argv[1]).resolve()
assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
old=ROOT/'reports/world-static-mesh-flight-guard-development/before-core-binding-002'
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
before=json.loads((old/'capture.json').read_text(encoding='utf8'));assert before['status']=='PASS'
source_paths=['core/src/core.cpp','core/include/pikapika/core.hpp','core/src/dynamics.cpp','core/src/continuous_world.cpp','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json']
def hashes():return {p:info((ROOT/p).read_bytes()) for p in source_paths}
initial=hashes();rows=[]
def run(name,args,timeout=180):
 started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
 try:
  p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=timeout)
  code,stdout,stderr,timedout=p.returncode,p.stdout,p.stderr,False
 except subprocess.TimeoutExpired as e:code,stdout,stderr,timedout=None,e.stdout or b'',e.stderr or b'',True
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':code,'timedOut':timedout,'sourceBefore':initial,'sourceAfter':hashes()}
 row['sourceStable']=row['sourceBefore']==row['sourceAfter']
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  path=out/(name+'.'+stream+'.txt');path.write_bytes(raw);row[stream]=path.relative_to(ROOT).as_posix();row[stream+'Hash']=info(raw)
 rows.append(row);(out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 assert code==0 and not timedout and row['sourceStable'],name
 return stdout
same={}
for name,file in [('legacy','pikapika-free-flight-legacy-probe.exe'),('simulation','pikapika-simulation-probe.exe'),('supported','pikapika-supported-probe.exe')]:
 args=[str(ROOT/'build/native/Release'/file)]+(['--fixtures'] if name=='supported' else [])
 raw=run(name,args);(out/(name+'.json')).write_bytes(raw)
 same[name]={'before':info((old/(name+'.json')).read_bytes()),'after':info(raw),'byteEqual':raw==(old/(name+'.json')).read_bytes()}
 assert same[name]['byteEqual'],name
run('legacy-wasm',['node','scripts/verify-free-flight-legacy.mjs',(out/'legacy.json').relative_to(ROOT).as_posix(),(out/'legacy-wasm').relative_to(ROOT).as_posix(),(old/'legacy-wasm').relative_to(ROOT).as_posix()])
wasm=json.loads((out/'legacy-wasm/report.json').read_text(encoding='utf8'))
assert wasm['status']=='PASS' and wasm['comparedToBaseline'] and wasm['fixtures']==20
record={'schema':1,'status':'PASS','scope':'Existing finite Native full report/state byte comparisons and same-backend SDK field bit regression only. This does not accept the new World guard, all floating inputs, or a Native/Wasm whole-output equality claim.',
 'native':same,'legacyWasm':wasm,'commands':rows,'sourceStable':hashes()==initial}
(out/'regression.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','nativeByteEqual':list(same),'legacyWasmFixtures':wasm['fixtures'],'numericBits':wasm['numericBits'],'negativeZeros':wasm['negativeZeroBits']}))
