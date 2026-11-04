"""Capture Native compilation before numerical and artifact binding acceptance."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys,time,shutil
ROOT=Path(__file__).resolve().parents[2]
out=(ROOT/sys.argv[1]).resolve()
assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
base=json.loads((ROOT/'reports/world-static-mesh-flight-guard-baseline.json').read_text(encoding='utf8'))
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
new=['core/include/pikapika/world_static_mesh_flight_guard.hpp','core/src/world_static_mesh_flight_guard.cpp',
 'tests/world_static_mesh_flight_guard_tests.cpp','tests/world_static_mesh_flight_guard_fixtures.cpp','tests/world_static_mesh_flight_guard_test_support.hpp',
 'core/src/core.cpp','CMakeLists.txt','cmake/WorldFlightBinding.cmake','scripts/build-simulation.mjs']
def hashes():return {p:info((ROOT/p).read_bytes()) for p in new}
def protected():
 for path,stamp in base['protected'].items():
  if path not in base['permittedOldSources']:assert info((ROOT/path).read_bytes())==stamp,path
initial=hashes();rows=[]
def run(name,args,timeout):
 protected();before=hashes();start=time.perf_counter();now=datetime.now(timezone.utc).isoformat()
 try:
  p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=timeout)
  code,stdout,stderr,timedout=p.returncode,p.stdout,p.stderr,False
 except subprocess.TimeoutExpired as e:code,stdout,stderr,timedout=None,e.stdout or b'',e.stderr or b'',True
 row={'name':name,'args':args,'started':now,'timeoutSeconds':timeout,'wallSeconds':time.perf_counter()-start,'exit':code,'timedOut':timedout,'sourceBefore':before,'sourceAfter':hashes()}
 row['sourceStable']=row['sourceBefore']==row['sourceAfter']==initial
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  path=out/(name+'.'+stream+'.txt');path.write_bytes(raw);row[stream]=path.relative_to(ROOT).as_posix();row[stream+'Hash']=info(raw)
 rows.append(row);(out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'name':name,'exit':code,'timedOut':timedout,'sourceStable':row['sourceStable'],'wallSeconds':row['wallSeconds']}),flush=True)
 protected();assert code==0 and not timedout and row['sourceStable'],name
cmake=shutil.which('cmake');assert cmake
run('configure',[cmake,'-S','.','-B','build/native'],120)
profile=(ROOT/'build/native/world-flight-binding-Release.json').read_bytes();parsed=json.loads(profile)
(out/'configured-profile.json').write_bytes(profile)
assert parsed['profile']==1 and parsed['configuration']=='Release'
run('build',[cmake,'--build','build/native','--config','Release','--target','pikapika_world_static_mesh_flight_guard_tests','pikapika-free-flight-legacy-probe','pikapika-simulation-probe','pikapika-supported-probe','--parallel'],300)
assert hashes()==initial
(out/'build-observation.json').write_text(json.dumps({'schema':1,'status':'PASS','scope':'Compilation/linking only. No unit execution, independent mathematical validation, actual artifact binding or World guard acceptance yet.','profile':parsed,'commands':rows,'sources':initial},indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','scope':'compile-only','configuredProfile':parsed['profile']}))
