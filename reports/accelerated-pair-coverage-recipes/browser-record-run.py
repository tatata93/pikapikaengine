"""Capture validation of existing public UI observations in a fresh directory."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys
import time

root=Path(__file__).resolve().parents[2]
feature,directory=sys.argv[1:]
out=root/directory;out.mkdir(parents=True,exist_ok=False)
source='reports/accelerated-pair-coverage-recipes/browser-record.py'
def info(raw):
    return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
before={source:info((root/source).read_bytes())}
args=[sys.executable,'-B','-X','utf8',source,feature]
started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
process=subprocess.run(args,cwd=root,capture_output=True,timeout=120)
after={source:info((root/source).read_bytes())}
row={'name':'browser-record','args':args,'started':started,'wallSeconds':time.perf_counter()-clock,
     'exit':process.returncode,'sourceBefore':before,'sourceAfter':after,'sourceStable':before==after}
for stream in ['stdout','stderr']:
    raw=getattr(process,stream);path=out/(stream+'.txt');path.write_bytes(raw)
    row[stream]=path.relative_to(root).as_posix();row[stream+'Hash']=info(raw)
(out/'commands.json').write_text(json.dumps([row],indent=2)+'\n',encoding='utf-8')
print(process.stdout.decode('utf-8',errors='replace'))
print(json.dumps({'exit':process.returncode,'sourceStable':row['sourceStable'],'wallSeconds':row['wallSeconds']}))
raise SystemExit(process.returncode)
