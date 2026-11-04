"""Capture commands, source stability, raw output and bounded SDK provenance."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,re,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-flight-sdk'
phase,directory,*extra=sys.argv[1:];out=root/directory;out.mkdir(parents=True,exist_ok=True);commands=[]
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def sources():
 paths=['CMakeLists.txt','.github/workflows/verify.yml','core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','scripts/build-simulation.mjs']
 paths += [p.relative_to(root).as_posix() for d in ['core/src','tests','tools','scripts'] for p in (root/d).glob('*sphere_triangle_mesh_flight*') if p.is_file()]
 paths += [p.relative_to(root).as_posix() for p in (root/'scripts').glob('*sphere-triangle-mesh-flight*') if p.is_file()]
 if phase in {'build','abi-tests'}:paths=['CMakeLists.txt','core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp']+[p.relative_to(root).as_posix() for d in ['core/src','tests','tools'] for p in (root/d).glob('*sphere_triangle_mesh_flight*') if p.is_file()]
 if phase=='sdk-build':paths=list(json.loads((root/'assets/pikapika-simulation.build.json').read_text())['sourceSha256'])+['scripts/build-simulation.mjs','core/src/sphere_triangle_mesh_held_load.cpp','core/src/sphere_triangle_mesh_free_flight_guard.cpp','core/include/pikapika/sphere_triangle_mesh_held_load.hpp','core/include/pikapika/sphere_triangle_mesh_free_flight_guard.hpp','core/src/sphere_triangle_mesh_flight_api_internal.hpp']
 return {p:digest((root/p).read_bytes()) for p in sorted(set(paths)) if (root/p).is_file()}
def run(name,args,timeout=1800):
 before=sources();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();proc=subprocess.run(args,cwd=root,capture_output=True,timeout=timeout)
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':proc.returncode,'authoredBefore':before,'authoredAfter':sources()};row['authoredStable']=row['authoredBefore']==row['authoredAfter']
 for stream in ['stdout','stderr']:
  data=getattr(proc,stream);path=out/(name+'.'+stream+'.txt');path.write_bytes(data);row[stream]=path.relative_to(root).as_posix();row[stream+'Hash']=digest(data)
 print(json.dumps({'command':name,'exit':proc.returncode}),flush=True);return row
node=shutil.which('node');python=shutil.which('python');legacy=str(root/'build/native/Release/pikapika-free-flight-legacy-probe.exe')
pure='reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/'
held='reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json'
probe=str(root/'build/native/Release/pikapika-sphere-triangle-mesh-flight-sdk-probe.exe')
if phase=='baseline':
 tracked=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
 allowed={'core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','scripts/build-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json'}
 generated=[p for p in tracked if p.startswith('tools/') and p.endswith('.html')]+['index.html','docs/learn/buoyancy.html']
 protected=[p for p in tracked if p not in allowed and p not in generated and p.startswith(('core/','engine/','samples/','assets/','third_party/','platform/','tests/','scripts/','tools/'))]
 def norm(data):return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',data),flags=re.S).replace(b'\r\n',b'\n')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
 report={'schema':1,'baseCommit':commit,'protected':{p:digest((root/p).read_bytes()) for p in protected},'generatedEntries':{p:digest(norm((root/p).read_bytes())) for p in generated},'permitted':{p:digest(subprocess.check_output(['git','show',commit+':'+p],cwd=root)) for p in sorted(allowed)},'manifest':json.loads((root/'assets/pikapika-simulation.build.json').read_text()),'scope':'Existing pure kernels, game, JS and all old tests/probes remain byte protected. Only API header/TU, builder and audited SDK/Web rebuild outputs may change, with new bounded-flight files.'}
 target=root/f'reports/{prefix}-baseline.json';assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 commands.append(run('legacy-native-before',[legacy]));(out/'legacy-native-before.json').write_bytes((out/'legacy-native-before.stdout.txt').read_bytes())
 commands.append(run('legacy-wasm-before',[node,'scripts/verify-free-flight-legacy.mjs',str(out/'legacy-native-before.json'),str(out/'legacy-wasm-before'),'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-before-wasm/legacy-wasm']))
 print(json.dumps({'protected':len(protected),'generated':len(generated),'base':commit}))
elif phase=='build':
 commands.append(run('configure',['cmake','-S','.','-B','build/native']))
 if not commands[-1]['exit']:commands.append(run('build',['cmake','--build','build/native','--config','Release','--parallel','2']))
elif phase=='sdk-build':commands.append(run('sdk-build',[node,'scripts/build-simulation.mjs']))
elif phase=='abi-tests':commands.append(run('native-tests',[str(root/'build/native/Release/pikapika_sphere_triangle_mesh_flight_sdk_tests.exe')]))
elif phase=='native':
 commands.append(run('native-tests',[str(root/'build/native/Release/pikapika_sphere_triangle_mesh_flight_sdk_tests.exe')]))
 commands.append(run('native-exchange',[python,'-X','utf8','scripts/verify-sphere-triangle-mesh-flight-native-sdk.py',held,pure+'native-fixtures.json',pure+'supplemental-fixtures.json',probe,str(out/'native-exchange')]))
elif phase=='wire':
 commands.append(run('wasm-wire',[node,'scripts/verify-sphere-triangle-mesh-flight-wasm-wire.mjs',str(out/'native-exchange/packets.json'),str(out/'wasm-wire')]))
 commands.append(run('wasm-independent',[python,'-X','utf8','scripts/verify-sphere-triangle-mesh-flight-native-sdk.py',held,pure+'native-fixtures.json',pure+'supplemental-fixtures.json','-',str(out/'wasm-independent'),'--packets',str(out/'wasm-wire/wasm-packets.json'),'--scope','wasm-wire']))
elif phase=='regressions':
 commands.append(run('web-build',[node,'scripts/build-web.mjs']))
 with ThreadPoolExecutor(max_workers=3) as pool:
  tasks=[('node',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs']),('syntax',[node,'scripts/check.mjs']),('ctest',['ctest','--test-dir','build/native','-C','Release','--output-on-failure'])]
  commands.extend(job.result() for job in [pool.submit(run,n,a) for n,a in tasks])
 commands.append(run('legacy-native-after',[legacy]));(out/'legacy-native-after.json').write_bytes((out/'legacy-native-after.stdout.txt').read_bytes())
 commands.append(run('legacy-wasm-after',[node,'scripts/verify-free-flight-legacy.mjs',str(out/'legacy-native-after.json'),str(out/'legacy-wasm-after'),'reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-before/legacy-wasm-before']))
elif phase=='pure-regressions':
 for name,target,arg in [('held','pikapika_sphere_triangle_mesh_held_load_tests.exe','--fixtures'),('guard','pikapika_sphere_triangle_mesh_free_flight_guard_tests.exe','--fixtures'),('supplemental','pikapika_sphere_triangle_mesh_free_flight_guard_tests.exe','--supplemental-fixtures')]:
  commands.append(run(name,[str(root/'build/native/Release'/target),arg]));(out/(name+'.json')).write_bytes((out/(name+'.stdout.txt')).read_bytes())
 commands.append(run('old-entry-owned',[node,'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs','reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',str(out/'old-entry-owned')]))
elif phase in {'summary','public-summary'}:commands.append(run(phase,[python,'-X','utf8',f'reports/{prefix}-recipes/{phase}.py',*extra]))
else:raise ValueError('Unknown phase')
(out/(phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
if any(row['exit'] for row in commands):raise SystemExit(1)
