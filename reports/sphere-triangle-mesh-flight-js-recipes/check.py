"""Capture owned-JS commands and immutable Native/SDK inputs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,re,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-flight-js'
phase,directory,*extra=sys.argv[1:];out=root/directory;out.mkdir(parents=True,exist_ok=True);commands=[]
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def authored():
 paths=['engine/simulation.mjs','.github/workflows/verify.yml','engine/sphere-triangle-mesh-flight.mjs']
 paths += [p.relative_to(root).as_posix() for d in ['tests','scripts'] for p in (root/d).glob('*sphere-triangle-mesh-flight*') if p.is_file()]
 paths += [p.relative_to(root).as_posix() for p in (root/'tests').glob('*sphere_triangle_mesh_flight_owned*') if p.is_file()]
 return {p:digest((root/p).read_bytes()) for p in sorted(set(paths)) if (root/p).is_file()}
def run(name,args,timeout=1800):
 before=authored();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();proc=subprocess.run(args,cwd=root,capture_output=True,timeout=timeout)
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':proc.returncode,'authoredBefore':before,'authoredAfter':authored()};row['authoredStable']=row['authoredBefore']==row['authoredAfter']
 for stream in ['stdout','stderr']:
  data=getattr(proc,stream);p=out/(name+'.'+stream+'.txt');p.write_bytes(data);row[stream]=p.relative_to(root).as_posix();row[stream+'Hash']=digest(data)
 print(json.dumps({'command':name,'exit':proc.returncode}),flush=True);return row
node=shutil.which('node');python=shutil.which('python')
held='reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json'
guard='reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/'
native='reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-final-002/native-exchange/packets.json'
if phase=='baseline':
 tracked=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines();allowed={'engine/simulation.mjs'}
 generated=[p for p in tracked if p.startswith('tools/') and p.endswith('.html')]+['index.html','docs/learn/buoyancy.html']
 protected=[p for p in tracked if p not in allowed and p not in generated and p.startswith(('core/','engine/','samples/','assets/','third_party/','platform/','tests/','scripts/','tools/'))]
 def norm(data):return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',data),flags=re.S).replace(b'\r\n',b'\n')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
 data={'schema':1,'baseCommit':commit,'protected':{p:digest((root/p).read_bytes()) for p in protected},'generatedEntries':{p:digest(norm((root/p).read_bytes())) for p in generated},'originalRuntimeBlob':digest(subprocess.check_output(['git','show',commit+':engine/simulation.mjs'],cwd=root)),'manifest':json.loads((root/'assets/pikapika-simulation.build.json').read_text()),'scope':'Native kernels/C ABI/SDK artifacts, source/provenance/runtime/notices, old JS wrappers, samples, all old tests/checkers/probes are byte protected. Only simulation.mjs imports/two methods, new owned flight module/tests/proofs and generated Web URLs may change.'}
 target=root/f'reports/{prefix}-baseline.json';assert not target.exists();target.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps({'protected':len(protected),'generated':len(generated),'base':commit}))
elif phase=='owned':commands.append(run('owned',[node,'scripts/verify-sphere-triangle-mesh-flight-sdk.mjs',held,guard+'native-fixtures.json',guard+'supplemental-fixtures.json',native,str(out/'owned')]))
elif phase=='focused':commands.append(run('focused',[node,'--test','tests/sphere-triangle-mesh-flight.test.mjs']))
elif phase=='finalize':
 commands.append(run('web-final',[node,'scripts/build-web.mjs']))
 commands.append(run('browser-page',[node,f'reports/{prefix}-recipes/browser-proof.mjs']))
 commands.append(run('browser-check',[node,f'reports/{prefix}-recipes/browser-check.mjs','local',str(Path(directory).parent/'run-20261104-final/owned/wasm-owned-dtos.json')]))
elif phase=='regressions':
 commands.append(run('web-build',[node,'scripts/build-web.mjs']))
 with ThreadPoolExecutor(max_workers=3) as pool:
  tasks=[('node',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs']),('syntax',[node,'scripts/check.mjs']),('ctest',['ctest','--test-dir','build/native','-C','Release','--output-on-failure'])]
  commands.extend(j.result() for j in [pool.submit(run,n,a) for n,a in tasks])
 commands.append(run('legacy-native',[str(root/'build/native/Release/pikapika-free-flight-legacy-probe.exe')]))
 (out/'legacy-native.json').write_bytes((out/'legacy-native.stdout.txt').read_bytes())
 commands.append(run('legacy-wasm',[node,'scripts/verify-free-flight-legacy.mjs',str(out/'legacy-native.json'),str(out/'legacy-wasm'),'reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-before/legacy-wasm-before']))
 commands.append(run('old-entry-owned',[node,'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs','reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',str(out/'old-entry-owned')]))
elif phase in {'summary','public-summary'}:commands.append(run(phase,[python,'-X','utf8',f'reports/{prefix}-recipes/{phase}.py',*extra]))
else:raise ValueError('Unknown phase')
(out/(phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
if any(r['exit'] for r in commands):raise SystemExit(1)
