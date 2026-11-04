"""Capture commands and original streams for bounded entry C ABI acceptance."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[2];phase,directory=sys.argv[1:]
out=root/directory;out.mkdir(parents=True,exist_ok=True)
native=root/'build/native/Release';node=shutil.which('node');cmake=shutil.which('cmake');commands=[]
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def authored():
    names=['core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','tests/sphere_triangle_mesh_entry_sdk_tests.cpp','tools/sphere_triangle_mesh_entry_sdk_probe.cpp','scripts/verify-sphere-triangle-mesh-entry-native-sdk.py','scripts/verify-sphere-triangle-mesh-entry-wasm-wire.mjs','scripts/build-simulation.mjs','CMakeLists.txt','.github/workflows/verify.yml']
    return {p:digest((root/p).read_bytes()) for p in names if (root/p).is_file()}
def run(name,args,filename=None):
    before=authored();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
    result=subprocess.run(args,cwd=root,capture_output=True,timeout=1200)
    stdout,stderr=out/(filename or name+'.stdout.txt'),out/(name+'.stderr.txt');stdout.write_bytes(result.stdout);stderr.write_bytes(result.stderr)
    row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':result.returncode,'stdout':stdout.relative_to(root).as_posix(),'stderr':stderr.relative_to(root).as_posix(),'stdoutHash':digest(result.stdout),'stderrHash':digest(result.stderr),'authoredBefore':before,'authoredAfter':authored()}
    row['authoredStable']=before==row['authoredAfter'];print(json.dumps({'command':name,'exit':row['exit'],'directory':directory}),flush=True);return row
def command(name,args,filename=None):
    row=run(name,args,filename);commands.append(row);return row['exit']==0
pure=root/'reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json'
if phase=='baseline':
    paths=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
    allowed={'core/src/simulation_api.cpp','core/include/pikapika/simulation_api.h','scripts/build-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json'}
    protected=[p for p in paths if p not in allowed and (p.startswith(('core/','engine/','samples/','assets/','third_party/')) or p.startswith(('tests/','scripts/')) and p.endswith(('.cpp','.hpp','.h','.mjs','.py')) or p.startswith('tools/') and p.endswith(('.cpp','.mjs')))]
    entries=[p for p in paths if p.startswith('tools/') and p.endswith('.html')]+['index.html','docs/learn/buoyancy.html']
    def normalized(p):
        import re
        return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',(root/p).read_bytes()),flags=re.S).replace(b'\r\n',b'\n')
    target=root/'reports/sphere-triangle-mesh-entry-abi-baseline.json';assert not target.exists()
    report={'schema':1,'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'protected':{p:digest((root/p).read_bytes()) for p in protected},'generatedEntries':{p:digest(normalized(p)) for p in entries},'allowed':sorted(allowed),'manifest':json.loads((root/'assets/pikapika-simulation.build.json').read_text()),'scope':'Existing authored kernel/engine/game/test/checker and notices raw bytes protected. Only shared API, regenerated SDK artifacts/build list, new entry tests/probe/checkers and CMake/CI/docs change. HTML accepts generated import maps/build query only.'}
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'protected':len(protected),'generatedEntries':len(entries)}))
elif phase=='native':
    if command('configure',[cmake,'-S','.','-B','build/native']):
        if command('native-build',[cmake,'--build','build/native','--config','Release','--parallel','2']):
            command('entry-sdk',[str(native/'pikapika_sphere_triangle_mesh_entry_sdk_tests.exe')])
elif phase=='wasm':command('wasm-build',[node,'scripts/build-simulation.mjs'])
elif phase=='exchange':command('native-exchange',[sys.executable,'-X','utf8','scripts/verify-sphere-triangle-mesh-entry-native-sdk.py',str(pure),str(native/'pikapika-sphere-triangle-mesh-entry-sdk-probe.exe'),str(out/'native-exchange')])
elif phase=='wasm-exchange':
    if command('wasm-wire',[node,'scripts/verify-sphere-triangle-mesh-entry-wasm-wire.mjs',str(out/'native-exchange/packets.json'),str(out/'wasm-wire')]):
        command('wasm-exchange',[sys.executable,'-X','utf8','scripts/verify-sphere-triangle-mesh-entry-native-sdk.py',str(pure),'-',str(out/'wasm-exchange'),'--packets',str(out/'wasm-wire/wasm-packets.json'),'--scope','wasm-wire'])
elif phase=='regressions':
    command('web-build',[node,'scripts/build-web.mjs'])
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(run,'ctest',[shutil.which('ctest'),'--test-dir','build/native','-C','Release','--output-on-failure']),pool.submit(run,'node',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs']),pool.submit(run,'syntax',[node,'scripts/check.mjs'])]
        commands.extend(job.result() for job in jobs)
elif phase=='old-sdk':
    old=root/'reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root'
    command('owned-sdk',[node,'scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs',str(old/'native-fixtures.json'),str(out/'owned-sdk')])
    command('old-mesh-sdk',[node,'scripts/verify-sphere-triangle-mesh-sdk.mjs',str(old/'mesh-native-fixtures.json'),str(native/'pikapika-sphere-triangle-mesh-sdk-probe.exe'),str(out/'old-mesh-sdk')])
    command('old-single-sdk',[node,'scripts/verify-sphere-triangle-sdk.mjs',str(old/'single-native-fixtures.json'),str(native/'pikapika-sphere-triangle-sdk-probe.exe'),str(out/'old-single-sdk')])
    command('simulation',[node,'scripts/verify-simulation.mjs',str(native/'pikapika-simulation-probe.exe')])
elif phase=='recheck':
    command('web-build',[node,'scripts/build-web.mjs']);command('learn',[node,'--test','docs/learn/learn.test.mjs'])
else:raise ValueError('Unknown phase')
(out/(phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
if any(row['exit'] for row in commands):raise SystemExit(1)
