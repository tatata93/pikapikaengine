"""Capture finite owned-JS checks without losing unsuccessful attempts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[2];phase,directory=sys.argv[1:]
out=root/directory;out.mkdir(parents=True,exist_ok=True);node=shutil.which('node');native=root/'build/native/Release';commands=[]
pure=root/'reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json'
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def authored():
    names=['engine/simulation.mjs','engine/sphere-triangle-mesh-entry.mjs','tests/sphere_triangle_mesh_entry_sdk.test.mjs','scripts/verify-sphere-triangle-mesh-entry-sdk.mjs','.github/workflows/verify.yml']
    return {p:digest((root/p).read_bytes()) for p in names if (root/p).is_file()}
def run(name,args):
    before=authored();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();result=subprocess.run(args,cwd=root,capture_output=True,timeout=1200)
    stdout,stderr=out/(name+'.stdout.txt'),out/(name+'.stderr.txt');stdout.write_bytes(result.stdout);stderr.write_bytes(result.stderr)
    row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':result.returncode,'stdout':stdout.relative_to(root).as_posix(),'stderr':stderr.relative_to(root).as_posix(),'stdoutHash':digest(result.stdout),'stderrHash':digest(result.stderr),'authoredBefore':before,'authoredAfter':authored()}
    row['authoredStable']=before==row['authoredAfter'];print(json.dumps({'command':name,'exit':row['exit'],'directory':directory}),flush=True);return row
if phase=='baseline':
    paths=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
    protected=[p for p in paths if p!='engine/simulation.mjs' and (p.startswith(('core/','engine/','samples/','assets/','third_party/')) or p.startswith(('tests/','scripts/')) and p.endswith(('.cpp','.hpp','.h','.mjs','.py')) or p.startswith('tools/') and p.endswith(('.cpp','.mjs')))]
    import re
    entries=[p for p in paths if p.startswith('tools/') and p.endswith('.html')]+['index.html','docs/learn/buoyancy.html']
    def norm(p):return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',(root/p).read_bytes()),flags=re.S).replace(b'\r\n',b'\n')
    report={'schema':1,'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'protected':{p:digest((root/p).read_bytes()) for p in protected},'generatedEntries':{p:digest(norm(p)) for p in entries},'manifest':json.loads((root/'assets/pikapika-simulation.build.json').read_text()),'scope':'Only simulation.mjs minimal method/import and new owned entry JS module/tests/runner plus CI/docs/build HTML change. All C++/C ABI/SDK artifacts/build recipe, old JS wrappers/tests/checkers, game/assets/notices remain raw-byte protected.'}
    target=root/'reports/sphere-triangle-mesh-entry-js-baseline.json';assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'protected':len(protected),'generatedEntries':len(entries)}))
elif phase=='dedicated':commands.append(run('dedicated',[node,'--test','tests/sphere_triangle_mesh_entry_sdk.test.mjs']))
elif phase=='exchange':commands.append(run('owned-sdk',[node,'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs',str(pure),str(out/'owned-sdk')]))
elif phase=='regressions':
    commands.append(run('web-build',[node,'scripts/build-web.mjs']))
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(run,'node',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs']),pool.submit(run,'syntax',[node,'scripts/check.mjs']),pool.submit(run,'ctest',[shutil.which('ctest'),'--test-dir','build/native','-C','Release','--output-on-failure'])]
        commands.extend(job.result() for job in jobs)
elif phase=='old-sdk':
    old=root/'reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root'
    commands.append(run('old-owned-sdk',[node,'scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs',str(old/'native-fixtures.json'),str(out/'old-owned-sdk')]))
    commands.append(run('old-mesh-sdk',[node,'scripts/verify-sphere-triangle-mesh-sdk.mjs',str(old/'mesh-native-fixtures.json'),str(native/'pikapika-sphere-triangle-mesh-sdk-probe.exe'),str(out/'old-mesh-sdk')]))
    commands.append(run('old-single-sdk',[node,'scripts/verify-sphere-triangle-sdk.mjs',str(old/'single-native-fixtures.json'),str(native/'pikapika-sphere-triangle-sdk-probe.exe'),str(out/'old-single-sdk')]))
    commands.append(run('simulation',[node,'scripts/verify-simulation.mjs',str(native/'pikapika-simulation-probe.exe')]))
elif phase=='recheck':
    commands.append(run('web-build',[node,'scripts/build-web.mjs']));commands.append(run('learn',[node,'--test','docs/learn/learn.test.mjs']))
else:raise ValueError('Unknown phase')
(out/(phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
if any(row['exit'] for row in commands):raise SystemExit(1)
