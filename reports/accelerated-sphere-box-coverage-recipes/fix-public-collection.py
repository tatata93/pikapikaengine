"""Correct two stale distribution counts in a read-only collection driver."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import difflib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
FEATURE='63f5d3d7b841633980eac2006717f30614ee9e1f'
SOURCE='reports/accelerated-sphere-box-coverage-recipes/public.py'
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
original=subprocess.check_output(['git','show',FEATURE+':'+SOURCE],cwd=ROOT)
assert (ROOT/SOURCE).read_bytes()==original
before=original.decode('utf8')
pairs=[("'channels': {'pages': 99, 'githubSource': 1}","'channels': {'pages': 112, 'githubSource': 1}"),
       ("sum(row['distribution'] == 'pages' for row in files) == 99","sum(row['distribution'] == 'pages' for row in files) == 112")]
after=before
for old,new in pairs:
 assert after.count(old)==1
 after=after.replace(old,new,1)
assert 'len(set(PATHS)) == 113' in after
compile(after,SOURCE,'exec')
out=ROOT/'reports/accelerated-sphere-box-coverage-public-collection-development/run-001'
out.mkdir(parents=True,exist_ok=False)
(out/'original-public.py.txt').write_bytes(original)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+SOURCE,tofile='b/'+SOURCE))
(out/'actual.patch.txt').write_bytes(patch.encode())
(ROOT/SOURCE).write_bytes(after.encode())
failed=ROOT/'reports/accelerated-sphere-box-coverage-checks/run-20261104-public-bytes-001'
commands=json.loads((failed/'commands.json').read_text(encoding='utf8'))
assert len(commands)==1 and commands[0]['exit']==1
assert b"sum(row['distribution'] == 'pages' for row in files) == 99" in (failed/'stderr.txt').read_bytes()
record={'schema':1,'feature':FEATURE,'created':datetime.now(timezone.utc).isoformat(),
 'source':SOURCE,'original':info(original),'new':info(after.encode()),'literalReplacements':pairs,
 'patch':info(patch.encode()),'failure':'reports/accelerated-sphere-box-coverage-checks/run-20261104-public-bytes-001/commands.json',
 'scope':'Read-only driver count correction only: PATHS already contained 113 and every loop item was compared before the stale footer count assertion failed. First attempt is not accepted as a completed receipt. Fresh full113 collection must pass; no numerical source, thresholds, fixtures, CI, or public feature bytes changed.'}
(out/'correction.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'CORRECTED_NOT_YET_RECOLLECTED','original':record['original'],'new':record['new'],'pagesExpected':112,'githubSourceExpected':1}))
