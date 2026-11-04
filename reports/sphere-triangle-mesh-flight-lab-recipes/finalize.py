"""Final idempotent Web regeneration before publishing the lab milestone."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,subprocess,shutil,time
root=Path(__file__).resolve().parents[2]
out=root/'reports/sphere-triangle-mesh-flight-lab-checks/run-20261104-finalize';out.mkdir(parents=True,exist_ok=False)
paths=[root/'index.html',root/'docs/learn/buoyancy.html']+sorted((root/'tools').glob('*.html'))
def hashes():return {p.relative_to(root).as_posix():{'bytes':len(b:=p.read_bytes()),'sha256':sha256(b).hexdigest()} for p in paths}
before=hashes();command=[shutil.which('node'),'scripts/build-web.mjs'];started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();process=subprocess.run(command,cwd=root,capture_output=True,timeout=60)
row={'schema':1,'command':command,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':process.returncode,'before':before,'after':hashes()}
for name in ['stdout','stderr']:
 data=getattr(process,name);p=out/(name+'.txt');p.write_bytes(data);row[name]=p.relative_to(root).as_posix();row[name+'Hash']={'bytes':len(data),'sha256':sha256(data).hexdigest()}
row['rawStable']=row['before']==row['after'];(out/'command.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf8')
assert process.returncode==0 and row['rawStable'] and b'cd45c7f1ac2ba5e5: 54 versioned modules' in process.stdout
print(json.dumps({'status':'PASS','rawHtmlUnchanged':len(paths),'build':'cd45c7f1ac2ba5e5'}))
