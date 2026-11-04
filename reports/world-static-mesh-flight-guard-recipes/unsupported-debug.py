"""Build the actual unconfigured Debug target and run its refusal assertions."""
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys,time,shutil
ROOT=Path(__file__).resolve().parents[2]
out=(ROOT/sys.argv[1]).resolve()
assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
paths=['core/src/core.cpp','core/src/world_static_mesh_flight_guard.cpp','core/include/pikapika/world_static_mesh_flight_guard.hpp','CMakeLists.txt','cmake/WorldFlightBinding.cmake','tests/world_static_mesh_flight_guard_tests.cpp','tests/world_static_mesh_flight_guard_fixtures.cpp','tests/world_static_mesh_flight_guard_test_support.hpp']
def hashes():return {p:info((ROOT/p).read_bytes()) for p in paths}
initial=hashes();rows=[];cmake=shutil.which('cmake');assert cmake
binary=ROOT/'build/native/Debug/pikapika_world_static_mesh_flight_guard_tests.exe'
commands=[('build',[cmake,'--build','build/native','--config','Debug','--target','pikapika_world_static_mesh_flight_guard_tests','--parallel'],300),('refusal',[str(binary),'--unsupported-profile'],60)]
for name,args,timeout in commands:
 start=time.perf_counter();p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=timeout)
 row={'name':name,'args':args,'exit':p.returncode,'wallSeconds':time.perf_counter()-start,'sources':hashes(),'sourceStable':hashes()==initial}
 for stream,raw in [('stdout',p.stdout),('stderr',p.stderr)]:
  q=out/(name+'.'+stream+'.txt');q.write_bytes(raw);row[stream]=q.relative_to(ROOT).as_posix();row[stream+'Hash']=info(raw)
 rows.append(row);(out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:row[k] for k in ['name','exit','wallSeconds','sourceStable']}),flush=True)
 assert p.returncode==0 and row['sourceStable'],name
profile=(ROOT/'build/native/world-flight-binding-Debug.json').read_bytes();parsed=json.loads(profile)
assert parsed['profile']==0 and parsed['configuration']=='Debug'
(out/'configured-profile.json').write_bytes(profile)
for name,path in [('actual-compile-commands','build/native/pikapika_core.dir/Debug/pikapika_core.tlog/CL.command.1.tlog'),('actual-project','build/native/pikapika_core.vcxproj')]:
 raw=(ROOT/path).read_bytes();(out/(name+'.txt')).write_bytes(raw)
 if name=='actual-compile-commands':
  t=raw.decode('utf-16');assert 'PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=0' in t
(out/'refusal.json').write_text(json.dumps({'schema':1,'status':'PASS','scope':'Actual MSVC Debug profile0 refusal assertions: no originalSettings/preparation/child/candidate and no World mutation. This is unconfigured rejection, not identity mismatch or unsupported target injection.','profile':parsed,'commands':rows,'binary':info(binary.read_bytes()),'sources':initial},indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','profile':0,'scope':'actual unconfigured Debug refusal'}))
