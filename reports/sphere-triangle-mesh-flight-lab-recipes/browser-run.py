"""Capture full actual-browser comparator output without self-hashing evidence."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,shutil,subprocess,sys,time
root=Path(__file__).resolve().parents[2]
phase,directory=sys.argv[1:];assert phase in {'local','public'}
out=(root/directory).resolve();assert out.is_relative_to(root);out.mkdir(parents=True,exist_ok=False)
capture='reports/sphere-triangle-mesh-flight-lab-'+('browser' if phase=='local' else 'public-browser')
command=[shutil.which('node'),'reports/sphere-triangle-mesh-flight-lab-recipes/browser-check.mjs',capture,'reports/sphere-triangle-mesh-flight-lab-checks/run-20261104-final-002/actual/report.json',capture+'/browser-verification.json']
started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();p=subprocess.run(command,cwd=root,capture_output=True,timeout=180)
row={'name':'browser-'+phase,'args':command,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':p.returncode}
for name in ['stdout','stderr']:
 data=getattr(p,name);file=out/(name+'.txt');file.write_bytes(data);row[name]=file.relative_to(root).as_posix();row[name+'Hash']={'bytes':len(data),'sha256':sha256(data).hexdigest()}
(out/'browser-commands.json').write_text(json.dumps([row],indent=2)+'\n',encoding='utf8')
print(json.dumps({'phase':phase,'exit':p.returncode,'wallSeconds':row['wallSeconds']}));raise SystemExit(p.returncode)
