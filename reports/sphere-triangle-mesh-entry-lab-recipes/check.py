"""Capture the next UI milestone without changing earlier proof recipes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,re,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[2];phase,directory=sys.argv[1:]
out=root/directory;out.mkdir(parents=True,exist_ok=True);node=shutil.which('node');commands=[]
names=['tools/sphere-triangle-mesh-entry-lab.mjs','tools/sphere-triangle-mesh-entry-lab.html','tests/sphere-triangle-mesh-entry-lab.test.mjs','scripts/build-web.mjs','tests/web-build.test.mjs']
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
def authored():return {p:digest((root/p).read_bytes()) for p in names if (root/p).is_file()}
def run(name,args):
 before=authored();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();r=subprocess.run(args,cwd=root,capture_output=True,timeout=1200)
 for stream in ['stdout','stderr']:(out/(name+'.'+stream+'.txt')).write_bytes(getattr(r,stream))
 row={'name':name,'args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':r.returncode,'authoredBefore':before,'authoredAfter':authored()}
 row['authoredStable']=before==row['authoredAfter']
 for stream in ['stdout','stderr']:row[stream]=(out/(name+'.'+stream+'.txt')).relative_to(root).as_posix();row[stream+'Hash']=digest(getattr(r,stream))
 print(json.dumps({'command':name,'exit':r.returncode}),flush=True);return row
if phase=='baseline':
 paths=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines();allowed={'scripts/build-web.mjs','tests/web-build.test.mjs'}
 protected=[p for p in paths if p not in allowed and (p.startswith(('core/','engine/','samples/','assets/','third_party/')) or p.startswith(('tests/','scripts/')) and p.endswith(('.cpp','.hpp','.h','.mjs','.py')) or p.startswith('tools/') and p.endswith(('.cpp','.mjs')))]
 entries=[p for p in paths if p.startswith('tools/') and p.endswith('.html')]+['index.html','docs/learn/buoyancy.html']
 def norm(p):return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',(root/p).read_bytes()),flags=re.S).replace(b'\r\n',b'\n')
 report={'schema':1,'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'protected':{p:digest((root/p).read_bytes()) for p in protected},'generatedEntries':{p:digest(norm(p)) for p in entries},'manifest':json.loads((root/'assets/pikapika-simulation.build.json').read_text()),'scope':'Only new manual entry UI/helper/test/docs plus build registration and web-build expected entry count. All old engine/SDK/native/math/game data and code are byte-protected.'}
 target=root/'reports/sphere-triangle-mesh-entry-lab-baseline.json';assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'protected':len(protected),'generatedEntries':len(entries)}))
elif phase=='dedicated':commands.append(run('dedicated',[node,'--test','tests/sphere-triangle-mesh-entry-lab.test.mjs']))
elif phase=='regressions':
 commands.append(run('web-build',[node,'scripts/build-web.mjs']))
 with ThreadPoolExecutor(max_workers=3) as pool:
  jobs=[pool.submit(run,'node',[node,'--test','tests/*.test.mjs','docs/learn/learn.test.mjs']),pool.submit(run,'syntax',[node,'scripts/check.mjs']),pool.submit(run,'ctest',[shutil.which('ctest'),'--test-dir','build/native','-C','Release','--output-on-failure'])]
  commands.extend(job.result() for job in jobs)
elif phase=='exchange':commands.append(run('owned-sdk',[node,'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs','reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',str(out/'owned-sdk')]))
elif phase=='recheck':
 commands.append(run('web-build',[node,'scripts/build-web.mjs']));commands.append(run('learn',[node,'--test','docs/learn/learn.test.mjs']))
elif phase=='summary':commands.append(run('summary',[shutil.which('python'),'-X','utf8','reports/sphere-triangle-mesh-entry-lab-recipes/summary.py']))
elif phase=='public-summary':commands.append(run('public-summary',[shutil.which('python'),'-X','utf8','reports/sphere-triangle-mesh-entry-lab-recipes/public-summary.py']))
else:raise ValueError('Unknown phase')
(out/(phase+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
if any(row['exit'] for row in commands):raise SystemExit(1)
