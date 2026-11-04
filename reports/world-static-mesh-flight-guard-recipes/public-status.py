"""Read public push-triggered runs; the connected wrapper filters to PR events."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,sys,urllib.request
ROOT=Path(__file__).resolve().parents[2]
feature='73efa91b4a8621a19bb6f056bec5ee282f6e7c3b'
out=(ROOT/sys.argv[1]).resolve()
assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-public-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
url='https://api.github.com/repos/tatata93/pikapikaengine/actions/runs?head_sha='+feature+'&per_page=10'
request=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'pikapikaengine-public-verification'})
with urllib.request.urlopen(request,timeout=30) as response:
 raw=response.read();status=response.status;headers=dict(response.headers)
(out/'runs.json').write_bytes(raw)
data=json.loads(raw)
rows=[{k:r[k] for k in ['id','name','event','status','conclusion','head_sha','html_url']} for r in data['workflow_runs']]
assert all(r['head_sha']==feature for r in rows)
record={'schema':1,'feature':feature,'observed':datetime.now(timezone.utc).isoformat(),'url':url,'httpStatus':status,'headers':headers,'response':{'bytes':len(raw),'sha256':sha256(raw).hexdigest()},'runs':rows,'scope':'Public read-only GitHub REST listing. Empty/queued/in-progress is not success; no Actions dispatch/rerun or account/authentication change.'}
(out/'observation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'OBSERVED','runs':rows}))
