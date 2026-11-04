"""Capture read-only propagation-guard commands and source-stable evidence."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,re,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[2]
phase,directory=sys.argv[1:];out=root/directory;out.mkdir(parents=True,exist_ok=True);commands=[]
prefix='sphere-triangle-mesh-free-flight-guard'
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def authored():
 paths=['CMakeLists.txt','.github/workflows/verify.yml','core/src/continuous_world.cpp','scripts/build-simulation.mjs','core/src/free_flight_internal.hpp','tools/free_flight_legacy_probe.cpp','scripts/check-sphere-triangle-mesh-free-flight-guard.py','scripts/verify-free-flight-legacy.mjs']
 paths += [p.relative_to(root).as_posix() for parent in ['core/include/pikapika','core/src','tests'] for p in (root/parent).glob('*free_flight_guard*') if p.is_file()]
 if phase=='sdk-build':
  paths=list(json.loads((root/'assets/pikapika-simulation.build.json').read_text())['sourceSha256'])+['scripts/build-simulation.mjs','core/src/free_flight_internal.hpp']
 return {p:digest((root/p).read_bytes()) for p in sorted(set(paths)) if (root/p).is_file()}
def run(name,args,timeout=1800):
 before=authored();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();proc=subprocess.run(args,cwd=root,capture_output=True,timeout=timeout)
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':proc.returncode,'authoredBefore':before,'authoredAfter':authored()};row['authoredStable']=row['authoredBefore']==row['authoredAfter']
 for stream in ['stdout','stderr']:
  data=getattr(proc,stream);p=out/(name+'.'+stream+'.txt');p.write_bytes(data);row[stream]=p.relative_to(root).as_posix();row[stream+'Hash']=digest(data)
 print(json.dumps({'command':name,'exit':proc.returncode}),flush=True);return row
node=shutil.which('node');python=shutil.which('python');exe=str(root/'build/native/Release/pikapika_sphere_triangle_mesh_free_flight_guard_tests.exe');legacy=str(root/'build/native/Release/pikapika-free-flight-legacy-probe.exe')
if phase=='baseline':
 tracked=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
 allowed={'core/src/continuous_world.cpp','scripts/build-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json'}
 generated=[p for p in tracked if p.startswith('tools/') and p.endswith('.html')]+['index.html','docs/learn/buoyancy.html']
 protected=[p for p in tracked if p not in allowed and p not in generated and p.startswith(('core/','engine/','samples/','assets/','third_party/','platform/','tests/','scripts/','tools/'))]
 def norm(data):return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',data),flags=re.S).replace(b'\r\n',b'\n')
 report={'schema':1,'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'protected':{p:digest((root/p).read_bytes()) for p in protected},'generatedEntries':{p:digest(norm((root/p).read_bytes())) for p in generated},'permittedRebuild':{p:digest((root/p).read_bytes()) for p in sorted(allowed)},'manifest':json.loads((root/'assets/pikapika-simulation.build.json').read_text()),'scope':'Only new Native guard/bridge private header/tests/probe/checkers and docs; existing W1 TU gains a private bridge without changing old numerical bodies. Builder private-header dependency, SDK provenance/artifacts and generated Web entries are audited rebuild outputs. All other old source/game/runtime/held-load kernel and tests remain byte-protected.'}
 target=root/f'reports/{prefix}-baseline.json';assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 (out/'continuous_world-before.cpp').write_bytes((root/'core/src/continuous_world.cpp').read_bytes())
 commands.append(run('old-w1-fixtures',[str(root/'build/native/Release/pikapika_continuous_world_tests.exe'),'--fixtures']))
 (out/'old-w1-fixtures.json').write_bytes((out/'old-w1-fixtures.stdout.txt').read_bytes())
 print(json.dumps({'protected':len(protected),'generatedEntries':len(generated),'baseCommit':report['baseCommit']}))
elif phase in {'build','legacy-build'}:
 commands.append(run('configure',['cmake','-S','.','-B','build/native']))
 if not commands[-1]['exit']:
  args=['cmake','--build','build/native','--config','Release','--parallel','2']
  if phase=='legacy-build':args+=['--target','pikapika-free-flight-legacy-probe']
  commands.append(run('build',args))
elif phase=='legacy':
 commands.append(run('legacy',[legacy]));(out/'legacy.json').write_bytes((out/'legacy.stdout.txt').read_bytes())
elif phase=='legacy-wasm-before':
 commands.append(run('legacy-wasm-before',[node,'scripts/verify-free-flight-legacy.mjs',f'reports/{prefix}-checks/run-20261104-before/legacy.json',str(out/'legacy-wasm')]))
elif phase=='legacy-wasm-after':
 commands.append(run('legacy-wasm-after',[node,'scripts/verify-free-flight-legacy.mjs',f'reports/{prefix}-checks/run-20261104-before/legacy.json',str(out/'legacy-wasm'),f'reports/{prefix}-checks/run-20261104-before-wasm/legacy-wasm']))
elif phase=='sdk-build':commands.append(run('sdk-build',[node,'scripts/build-simulation.mjs']))
elif phase=='native':
 commands.append(run('native-tests',[exe]));commands.append(run('native-fixtures',[exe,'--fixtures']));(out/'native-fixtures.json').write_bytes((out/'native-fixtures.stdout.txt').read_bytes())
 commands.append(run('supplemental-fixtures',[exe,'--supplemental-fixtures']));(out/'supplemental-fixtures.json').write_bytes((out/'supplemental-fixtures.stdout.txt').read_bytes())
elif phase=='reference':
 fixture=str(out/'native-fixtures.json');supplemental=str(out/'supplemental-fixtures.json');commands.append(run('fraction',[python,'-X','utf8','scripts/check-sphere-triangle-mesh-free-flight-guard.py',fixture,'--supplemental',supplemental]));commands.append(run('reference',[python,'-X','utf8','tests/sphere_triangle_mesh_free_flight_guard_reference_test.py',fixture,'--supplemental',supplemental,'--output',str(out/'reference')]))
elif phase=='regressions':
 commands.append(run('web-build',[node,'scripts/build-web.mjs']))
 with ThreadPoolExecutor(max_workers=3) as pool:
  tasks=[('node',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs']),('syntax',[node,'scripts/check.mjs']),('ctest',['ctest','--test-dir','build/native','-C','Release','--output-on-failure'])]
  commands.extend(job.result() for job in [pool.submit(run,n,a) for n,a in tasks])
elif phase=='old-exchange':
 commands.append(run('old-entry-owned',[node,'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs','reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',str(out/'old-entry-owned')]))
 commands.append(run('old-held-fixtures',[str(root/'build/native/Release/pikapika_sphere_triangle_mesh_held_load_tests.exe'),'--fixtures']));(out/'old-held-fixtures.json').write_bytes((out/'old-held-fixtures.stdout.txt').read_bytes())
 commands.append(run('old-held-fraction',[python,'-X','utf8','scripts/check-sphere-triangle-mesh-held-load.py',str(out/'old-held-fixtures.json')]))
 commands.append(run('old-held-reference',[python,'-X','utf8','tests/sphere_triangle_mesh_held_load_reference_test.py',str(out/'old-held-fixtures.json'),'--output',str(out/'old-held-reference')]))
 commands.append(run('old-w1-fixtures',[str(root/'build/native/Release/pikapika_continuous_world_tests.exe'),'--fixtures']));(out/'old-w1-fixtures.json').write_bytes((out/'old-w1-fixtures.stdout.txt').read_bytes())
 commands.append(run('old-w1-wasm',[node,'scripts/verify-continuous-world.mjs',str(out/'old-w1-fixtures.json'),str(out/'old-w1-wasm.json')]))
elif phase in {'summary','public-summary'}:commands.append(run(phase,[python,'-X','utf8',f'reports/{prefix}-recipes/{phase}.py']))
else:raise ValueError('Unknown phase')
(out/(phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
if any(row['exit'] for row in commands):raise SystemExit(1)
