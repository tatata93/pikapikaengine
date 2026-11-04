"""Run the frozen independent finite preparation checker and negative controls."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,subprocess,sys,time
if not __debug__:raise SystemExit('Run without -O')
root=Path(__file__).resolve().parents[2]
native,directory=sys.argv[1:];out=root/directory;out.mkdir(parents=True,exist_ok=False)
fixture=(root/native/'native-fixtures.json').relative_to(root).as_posix()
paths=['scripts/verify-world-static-mesh-preparation.py','tests/world_static_mesh_preparation_reference_tests.py',fixture,
'core/include/pikapika/world_static_mesh_flight.hpp','core/src/world_static_mesh_flight.cpp',
'tests/world_static_mesh_flight_preparation_tests.cpp','tests/world_static_mesh_flight_preparation_fixtures.cpp','tests/world_static_mesh_flight_preparation_support.hpp']
def info(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def hashes():return {p:info((root/p).read_bytes()) for p in paths}
initial=hashes();rows=[]
for name,args in [('checker',[sys.executable,'-B','-X','utf8',paths[0],fixture]),('negative-controls',[sys.executable,'-B','-X','utf8',paths[1],fixture,'--output',(out/'controls').relative_to(root).as_posix()])]:
 before=hashes();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();process=subprocess.run(args,cwd=root,capture_output=True,timeout=120)
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':process.returncode,'sourceBefore':before,'sourceAfter':hashes()}
 row['sourceStable']=row['sourceBefore']==row['sourceAfter']==initial
 for label in ['stdout','stderr']:
  data=getattr(process,label);p=out/(name+'.'+label+'.txt');p.write_bytes(data);row[label]=p.relative_to(root).as_posix();row[label+'Hash']=info(data)
 rows.append(row);(out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'name':name,'exit':row['exit'],'seconds':row['wallSeconds'],'stable':row['sourceStable']}),flush=True)
 assert process.returncode==0 and row['sourceStable'],name
print(json.dumps({'status':'PASS','commands':len(rows)}))
