"""Fresh Native preparation checks with exact raw logs and frozen-source assertions."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,subprocess,sys,shutil,time
if not __debug__:raise SystemExit('Run without -O')
root=Path(__file__).resolve().parents[2]
phase,directory=sys.argv[1:];assert phase in {'native','regressions'}
out=root/directory;out.mkdir(parents=True,exist_ok=False)
base=json.loads((root/'reports/world-static-mesh-preparation-baseline.json').read_text(encoding='utf8'))
frozen=['core/include/pikapika/world_static_mesh_flight.hpp','core/src/world_static_mesh_flight.cpp','tests/world_static_mesh_flight_preparation_tests.cpp','tests/world_static_mesh_flight_preparation_fixtures.cpp','tests/world_static_mesh_flight_preparation_support.hpp','CMakeLists.txt']
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
def hashes():return {p:info((root/p).read_bytes()) for p in frozen}
def originals():
 for p,v in base['protected'].items():assert info((root/p).read_bytes())==v,p
originals();initial=hashes();rows=[]
def run(name,args,timeout):
 originals();before=hashes();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
 try:
  process=subprocess.run(args,cwd=root,capture_output=True,timeout=timeout);code=process.returncode;stdout=process.stdout;stderr=process.stderr;timedout=False
 except subprocess.TimeoutExpired as e:
  code=None;stdout=e.stdout or b'';stderr=e.stderr or b'';timedout=True
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':code,'timedOut':timedout,'sourceBefore':before,'sourceAfter':hashes()}
 row['sourceStable']=row['sourceBefore']==row['sourceAfter']==initial
 for label,data in [('stdout',stdout),('stderr',stderr)]:
  p=out/(name+'.'+label+'.txt');p.write_bytes(data);row[label]=p.relative_to(root).as_posix();row[label+'Hash']=info(data)
 rows.append(row);(out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'name':name,'exit':code,'seconds':row['wallSeconds'],'stable':row['sourceStable']}),flush=True)
 originals();assert code==0 and not timedout and row['sourceStable'],name
 return stdout
if phase=='native':
 cmake=shutil.which('cmake');assert cmake
 run('configure',[cmake,'-S','.','-B','build/native'],120)
 run('build',[cmake,'--build','build/native','--config','Release','--parallel'],300)
 binary=str(root/'build/native/Release/pikapika_world_static_mesh_flight_preparation_tests.exe')
 (out/'native-fixtures.json').write_bytes(run('fixtures',[binary,'--fixtures'],120))
 (out/'native-storage.json').write_bytes(run('storage',[binary,'--storage'],120))
 run('ctest',['ctest','--test-dir','build/native','-C','Release','--output-on-failure'],300)
else:
 run('node',[shutil.which('node'),'--test',*map(str,sorted(Path('tests').glob('*.test.mjs'))),'docs/learn/learn.test.mjs'],180)
 run('syntax',[shutil.which('node'),'scripts/check.mjs'],120)
 run('web-build',[shutil.which('node'),'scripts/build-web.mjs'],60)
print(json.dumps({'status':'PASS','phase':phase,'commands':len(rows)}))
