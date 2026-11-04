"""Run actual full Native and authoring regressions; preserve all raw attempts."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys,time,shutil
ROOT=Path(__file__).resolve().parents[2]
out=(ROOT/sys.argv[1]).resolve()
assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
cmake=shutil.which('cmake');ctest=shutil.which('ctest');node=shutil.which('node')
assert cmake and ctest and node
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
paths=['core/src/core.cpp','core/src/dynamics.cpp','core/src/continuous_world.cpp','core/include/pikapika/world_static_mesh_flight_guard.hpp','core/src/world_static_mesh_flight_guard.cpp','tests/world_static_mesh_flight_guard_tests.cpp','tests/world_static_mesh_flight_guard_fixtures.cpp','tests/world_static_mesh_flight_guard_test_support.hpp','CMakeLists.txt','cmake/WorldFlightBinding.cmake','scripts/build-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json']
def hashes():return {p:info((ROOT/p).read_bytes()) for p in paths}
initial=hashes();rows=[]
commands=[('build-all',[cmake,'--build','build/native','--config','Release','--parallel'],300),
 ('ctest',[ctest,'--test-dir','build/native','-C','Release','--output-on-failure'],600),
 ('node-tests',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs'],240),
 ('syntax',[node,'scripts/check.mjs'],120),('web-build',[node,'scripts/build-web.mjs'],120)]
for name,args,timeout in commands:
 before=hashes();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
 try:
  p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=timeout);code,stdout,stderr,timedout=p.returncode,p.stdout,p.stderr,False
 except subprocess.TimeoutExpired as e:code,stdout,stderr,timedout=None,e.stdout or b'',e.stderr or b'',True
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':code,'timedOut':timedout,'sourceBefore':before,'sourceAfter':hashes()}
 row['sourceStable']=row['sourceBefore']==row['sourceAfter']==initial
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  path=out/(name+'.'+stream+'.txt');path.write_bytes(raw);row[stream]=path.relative_to(ROOT).as_posix();row[stream+'Hash']=info(raw)
 rows.append(row);(out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:row[k] for k in ['name','exit','timedOut','sourceStable','wallSeconds']}),flush=True)
 assert code==0 and not timedout and row['sourceStable'],name
(out/'regression.json').write_text(json.dumps({'schema':1,'status':'PASS','scope':'Actual full Release build/CTest, Node authoring tests, syntax and Web regeneration. Independent World math, compiler artifact audit, full SDK exchange and browser observations remain separate gates.','commands':rows,'sources':initial},indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','commands':len(rows)}))
