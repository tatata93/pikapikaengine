"""Finite JS integration checks with preserved command output and hashes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil
import subprocess
import sys
import time

root=Path(__file__).resolve().parents[2]
phase,directory=sys.argv[1:]
out=root/directory
out.mkdir(parents=True,exist_ok=True)
native=root/'build/native/Release'
node=shutil.which('node')
source=root/'reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root/native-fixtures.json'
oldmesh=root/'reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root/mesh-native-fixtures.json'
oldsingle=root/'reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root/single-native-fixtures.json'
commands=[]

def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def authored():
    names=['engine/simulation.mjs','engine/sphere-triangle-mesh-trajectory.mjs','tests/sphere_triangle_mesh_trajectory_sdk.test.mjs','scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs']
    return {name:digest((root/name).read_bytes()) for name in names if (root/name).is_file()}
def run(name,args,filename=None):
    started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();before=authored()
    result=subprocess.run(args,cwd=root,capture_output=True,timeout=600)
    stdout,stderr=out/(filename or name+'.stdout.txt'),out/(name+'.stderr.txt')
    stdout.write_bytes(result.stdout);stderr.write_bytes(result.stderr)
    record={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':result.returncode,
            'stdout':stdout.relative_to(root).as_posix(),'stderr':stderr.relative_to(root).as_posix(),'stdoutHash':digest(result.stdout),'stderrHash':digest(result.stderr),
            'authoredSourcesBefore':before,'authoredSourcesAfter':authored()}
    record['authoredSourcesStable']=record['authoredSourcesBefore']==record['authoredSourcesAfter']
    print(json.dumps({'command':name,'exit':result.returncode,'directory':directory}),flush=True)
    return record

if phase=='baseline':
    old=json.loads((root/'reports/sphere-triangle-mesh-trajectory-abi-baseline.json').read_text(encoding='utf-8-sig'))
    paths=[name for name in old['protected'] if name!='engine/simulation.mjs']
    paths+=['core/src/simulation_api.cpp','core/include/pikapika/simulation_api.h','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json','tests/sphere_triangle_mesh_trajectory_sdk_tests.cpp','tools/sphere_triangle_mesh_trajectory_sdk_probe.cpp','scripts/build-simulation.mjs','scripts/verify-sphere-triangle-mesh-trajectory-native-sdk.py','scripts/verify-sphere-triangle-mesh-trajectory-wasm-wire.mjs']
    assert len(set(paths))==len(paths)
    baseline={'schema':1,'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
              'protected':{name:digest((root/name).read_bytes()) for name in paths},
              'manifest':json.loads((root/'assets/pikapika-simulation.build.json').read_text(encoding='utf-8-sig')),
              'scope':'Only engine/simulation.mjs and new authored JS decoder may change in engine. All Native kernels/C ABI/probes, SDK artifacts/build recipe, model checkers, samples/assets/notices are protected.'}
    target=root/'reports/sphere-triangle-mesh-trajectory-js-baseline.json';assert not target.exists()
    target.write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'baseCommit':baseline['baseCommit'],'protected':len(paths)}))
elif phase=='dedicated':
    commands.append(run('dedicated',[node,'--test','tests/sphere_triangle_mesh_trajectory_sdk.test.mjs']))
elif phase=='exchange':
    commands.append(run('owned-sdk',[node,'scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs',str(source),str(out/'owned-sdk')]))
elif phase=='regressions':
    commands.append(run('web-build',[node,'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(run,'node',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs']),
              pool.submit(run,'syntax',[node,'scripts/check.mjs']),
              pool.submit(run,'old-mesh-sdk',[node,'scripts/verify-sphere-triangle-mesh-sdk.mjs',str(oldmesh),str(native/'pikapika-sphere-triangle-mesh-sdk-probe.exe'),str(out/'old-mesh-sdk')])]
        commands.extend(job.result() for job in jobs)
    commands.append(run('old-single-sdk',[node,'scripts/verify-sphere-triangle-sdk.mjs',str(oldsingle),str(native/'pikapika-sphere-triangle-sdk-probe.exe'),str(out/'old-single-sdk')]))
    commands.append(run('simulation',[node,'scripts/verify-simulation.mjs',str(native/'pikapika-simulation-probe.exe')]))
elif phase=='recheck':
    commands.append(run('web-build',[node,'scripts/build-web.mjs']))
    commands.append(run('learn',[node,'--test','docs/learn/learn.test.mjs']))
else:raise ValueError('Unknown phase')
(out/(phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
if any(row['exit'] or not row.get('authoredSourcesStable',True) for row in commands):raise SystemExit(1)
