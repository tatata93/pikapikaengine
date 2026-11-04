"""Capture exact public acceptance in a separate fresh summary folder."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, subprocess, sys, time
root=Path(__file__).resolve().parents[2]
directory,commit=sys.argv[1:]
out=root/directory;out.mkdir(parents=True,exist_ok=False)
args=[sys.executable,'-B','-X','utf8','reports/sphere-triangle-mesh-flight-lab-recipes/public-summary.py',commit,directory]
started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
process=subprocess.run(args,cwd=root,capture_output=True,timeout=120)
row={'name':'public-summary','args':args,'started':started,'wallSeconds':time.perf_counter()-clock,'exit':process.returncode}
for stream in ['stdout','stderr']:
 data=getattr(process,stream);p=out/(stream+'.txt');p.write_bytes(data)
 row[stream]=p.relative_to(root).as_posix();row[stream+'Hash']={'bytes':len(data),'sha256':sha256(data).hexdigest()}
(out/'commands.json').write_text(json.dumps([row],indent=2)+'\n',encoding='utf8')
print(process.stdout.decode('utf8',errors='replace'));print(json.dumps({'exit':process.returncode,'wallSeconds':row['wallSeconds']}))
raise SystemExit(process.returncode)
