"""Capture the accepted preparation baseline before new coverage integration."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[1]
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert commit.startswith('41c9cc2')
previous = json.loads((root/'reports/world-static-mesh-preparation-baseline.json').read_text(encoding='utf-8'))
local = json.loads((root/'reports/world-static-mesh-preparation-local-verification.json').read_text(encoding='utf-8'))

def info(raw):
    return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}

paths = sorted(set(previous['protected'])|set(local['newSources']))
assert len(paths)==362
protected = {path:info((root/path).read_bytes()) for path in paths}
for path, stamp in previous['protected'].items():
    assert protected[path]==stamp, path
for path, stamp in local['newSources'].items():
    assert protected[path]==stamp, path
integrations = {}
for path in previous['permittedOldSources']:
    blob = subprocess.check_output(['git','show',commit+':'+path],cwd=root)
    raw = (root/path).read_bytes()
    assert raw==blob or raw.replace(b'\r\n',b'\n')==blob
    integrations[path] = {'raw':info(raw),'gitBlob':info(blob),'gitBlobUtf8':blob.decode('utf-8')}
for path,stamp in previous['generatedEntries'].items():
    assert info((root/path).read_bytes())==stamp,path
report = {'schema':1,'baseCommit':commit,'created':datetime.now(timezone.utc).isoformat(),
          'protected':protected,'generatedEntries':previous['generatedEntries'],
          'permittedOldSources':integrations,'sdkManifest':previous['sdkManifest'],
          'priorPublicReceipt':'reports/world-static-mesh-preparation-public-verification.json',
          'scope':'All previous355 protected raw sources plus seven accepted preparation sources remain byte exact. New coverage is Native-only; prior26 generated HTML and existing SDK artifacts remain exact.'}
(root/'reports/accelerated-pair-coverage-baseline.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','baseCommit':commit,'protectedRaw':len(protected),'generatedRawHTML':26}))
