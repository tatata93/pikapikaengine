"""Capture provisional model runs; independent math and artifact audit are separate."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
out=(ROOT/sys.argv[1]).resolve()
assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
sources=['core/include/pikapika/world_static_mesh_flight_guard.hpp','core/src/world_static_mesh_flight_guard.cpp','tests/world_static_mesh_flight_guard_tests.cpp','tests/world_static_mesh_flight_guard_fixtures.cpp','tests/world_static_mesh_flight_guard_test_support.hpp','core/src/core.cpp','CMakeLists.txt','cmake/WorldFlightBinding.cmake']
binary=ROOT/'build/native/Release/pikapika_world_static_mesh_flight_guard_tests.exe'
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
def hashes():return {p:info((ROOT/p).read_bytes()) for p in sources}
initial=hashes();binary_before=info(binary.read_bytes());rows=[]
for name,extra in [('fixtures',['--fixtures']),('dedicated',[]),('storage',['--storage'])]:
 before=hashes();args=[str(binary),*extra];started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
 try:
  p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=180)
  code,stdout,stderr,timedout=p.returncode,p.stdout,p.stderr,False
 except subprocess.TimeoutExpired as e:code,stdout,stderr,timedout=None,e.stdout or b'',e.stderr or b'',True
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':code,'timedOut':timedout,'sourceBefore':before,'sourceAfter':hashes(),'binaryBefore':binary_before,'binaryAfter':info(binary.read_bytes())}
 row['sourceStable']=row['sourceBefore']==row['sourceAfter']==initial and row['binaryBefore']==row['binaryAfter']
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  path=out/(name+'.'+stream+'.txt');path.write_bytes(raw);row[stream]=path.relative_to(ROOT).as_posix();row[stream+'Hash']=info(raw)
 rows.append(row);(out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'name':name,'exit':code,'timedOut':timedout,'sourceStable':row['sourceStable'],'wallSeconds':row['wallSeconds']}),flush=True)
 assert code==0 and not timedout and row['sourceStable'],name
 if name in {'fixtures','storage'}:
  json.loads(stdout);(out/(name+'.json')).write_bytes(stdout)
(out/'observation.json').write_text(json.dumps({'schema':1,'phase':'provisional-candidate-model','scope':'Actual model commands returned. Independent mathematical and actual object/linked instruction binding acceptance must be checked separately before a World milestone PASS.','commands':rows,'sourceHashes':initial,'binary':binary_before},indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'COMMANDS_COMPLETED_BINDING_AND_MATH_SEPARATE','commands':len(rows)}))
