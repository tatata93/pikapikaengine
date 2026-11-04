"""Capture Native preparation local aggregate in a fresh output folder."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,subprocess,sys,time
root=Path(__file__).resolve().parents[2]
directory=sys.argv[1];out=root/directory;out.mkdir(parents=True,exist_ok=False)
args=[sys.executable,'-B','-X','utf8','reports/world-static-mesh-preparation-recipes/summary.py',directory]
started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();process=subprocess.run(args,cwd=root,capture_output=True,timeout=120)
row={'name':'local-summary','args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':process.returncode}
for label in ['stdout','stderr']:
 raw=getattr(process,label);p=out/(label+'.txt');p.write_bytes(raw);row[label]=p.relative_to(root).as_posix();row[label+'Hash']={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
(out/'commands.json').write_text(json.dumps([row],indent=2)+'\n',encoding='utf8')
print(process.stdout.decode('utf8',errors='replace'));print(json.dumps({'exit':process.returncode,'wallSeconds':row['wallSeconds']}))
raise SystemExit(process.returncode)
