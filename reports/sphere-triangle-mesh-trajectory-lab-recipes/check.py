"""Finite commands with original output and source stability records."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[2]
phase,directory=sys.argv[1:]
out=root/directory;out.mkdir(parents=True,exist_ok=True)
prefix='sphere-triangle-mesh-trajectory-lab'
node=shutil.which('node');native=root/'build/native/Release'
commands=[]
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def authored():
    paths=['tools/sphere-triangle-mesh-trajectory-lab.mjs','tests/sphere-triangle-mesh-trajectory-lab.test.mjs','tests/web-build.test.mjs','scripts/build-web.mjs']
    return {name:digest((root/name).read_bytes()) for name in paths if (root/name).is_file()}
def run(name,args):
    before=authored();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
    result=subprocess.run(args,cwd=root,capture_output=True,timeout=600)
    stdout,stderr=out/(name+'.stdout.txt'),out/(name+'.stderr.txt')
    stdout.write_bytes(result.stdout);stderr.write_bytes(result.stderr)
    row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':result.returncode,
      'stdout':stdout.relative_to(root).as_posix(),'stderr':stderr.relative_to(root).as_posix(),
      'stdoutHash':digest(result.stdout),'stderrHash':digest(result.stderr),'authoredBefore':before,'authoredAfter':authored()}
    row['authoredStable']=row['authoredBefore']==row['authoredAfter']
    print(json.dumps({'command':name,'exit':row['exit'],'directory':directory}),flush=True);return row
if phase=='baseline':
    paths=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
    protected=[p for p in paths if p.startswith(('core/','engine/','samples/','assets/','third_party/')) or p.endswith(('.cpp','.hpp')) or p.startswith('tests/') and p.endswith('.mjs') or p.startswith('tools/') and p.endswith('.mjs')]
    protected+=['CMakeLists.txt','scripts/build-simulation.mjs','scripts/verify-sphere-triangle-mesh-trajectory.py','tests/sphere_triangle_mesh_trajectory_reference_tests.py','scripts/verify-sphere-triangle-mesh-trajectory-native-sdk.py','scripts/verify-sphere-triangle-mesh-trajectory-wasm-wire.mjs','scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs']
    protected=sorted(set(protected));target=root/f'reports/{prefix}-baseline.json';assert not target.exists()
    report={'schema':1,'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'protected':{p:digest((root/p).read_bytes()) for p in protected},'scope':'All existing engine/core/sample/assets/runtime notices and old tool modules/tests/Native and reference/probe sources remain unchanged. New UI module/test and generated HTML import maps are separate.'}
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'protected':len(protected),'baseCommit':report['baseCommit']}))
elif phase=='dedicated':commands.append(run('dedicated',[node,'--test','tests/sphere-triangle-mesh-trajectory-lab.test.mjs']))
elif phase=='cases':commands.append(run('cases',[node,'reports/sphere-triangle-mesh-trajectory-lab-recipes/cases.mjs',str(out.relative_to(root)/'cases')]))
elif phase=='accept':
    commands.append(run('web-build',[node,'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(run,'node',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs']),pool.submit(run,'syntax',[node,'scripts/check.mjs']),pool.submit(run,'ctest',[shutil.which('ctest'),'--test-dir','build/native','-C','Release','--output-on-failure'])]
        commands.extend(job.result() for job in jobs)
elif phase=='exchange':
    old=root/'reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root'
    commands.append(run('owned-sdk',[node,'scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs',str(old/'native-fixtures.json'),str(out/'owned-sdk')]))
    commands.append(run('old-mesh-sdk',[node,'scripts/verify-sphere-triangle-mesh-sdk.mjs',str(old/'mesh-native-fixtures.json'),str(native/'pikapika-sphere-triangle-mesh-sdk-probe.exe'),str(out/'old-mesh-sdk')]))
    commands.append(run('old-single-sdk',[node,'scripts/verify-sphere-triangle-sdk.mjs',str(old/'single-native-fixtures.json'),str(native/'pikapika-sphere-triangle-sdk-probe.exe'),str(out/'old-single-sdk')]))
    commands.append(run('simulation',[node,'scripts/verify-simulation.mjs',str(native/'pikapika-simulation-probe.exe')]))
elif phase=='recheck':
    commands.append(run('web-build',[node,'scripts/build-web.mjs']))
    commands.append(run('learn',[node,'--test','docs/learn/learn.test.mjs']))
else:raise ValueError('Unknown phase')
(out/(phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
if any(row['exit'] or not row['authoredStable'] for row in commands):raise SystemExit(1)
