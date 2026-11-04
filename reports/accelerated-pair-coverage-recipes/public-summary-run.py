"""Capture an exact-feature public acceptance attempt without overwriting older raw."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import argparse,json,re,subprocess,sys,time
if not __debug__: raise SystemExit('Run without Python -O')
ROOT=Path(__file__).resolve().parents[2]
PREFIX='accelerated-pair-coverage'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('feature');parser.add_argument('directory')
args=parser.parse_args()
assert re.fullmatch('[0-9a-f]{40}',args.feature)
out=(ROOT/args.directory).resolve()
assert out.is_relative_to((ROOT/f'reports/{PREFIX}-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
command=[sys.executable,'-B','-X','utf8',f'reports/{PREFIX}-recipes/public-summary.py',args.feature,args.directory]
frozen=[f'reports/{PREFIX}-recipes/'+n+'.py' for n in ['public-summary','public-summary-run','browser-record','public','check','summary','summary-run']]
frozen += ['core/include/pikapika/accelerated_pair_coverage.hpp','core/src/accelerated_pair_coverage.cpp',
           'tests/accelerated_pair_coverage_tests.cpp','tests/accelerated_pair_coverage_fixtures.cpp',
           'tests/accelerated_pair_coverage_test_support.hpp','scripts/verify-accelerated-pair-coverage.py',
           'tests/accelerated_pair_coverage_reference_tests.py',f'reports/{PREFIX}-local-verification.json',
           'CMakeLists.txt','.github/workflows/verify.yml','.gitattributes']
def hashes():
 return {p:{'bytes':len(b),'sha256':sha256(b).hexdigest()} for p in frozen for b in [(ROOT/p).read_bytes()]}
before=hashes(); started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
try:
 process=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180)
 code,stdout,stderr,timedout=process.returncode,process.stdout,process.stderr,False
except subprocess.TimeoutExpired as error:
 code,stdout,stderr,timedout=None,error.stdout or b'',error.stderr or b'',True
row={'name':'public-summary','args':command,'started':started,'wallSeconds':time.perf_counter()-clock,
     'exit':code,'timedOut':timedout,'sourceBefore':before,'sourceAfter':hashes()}
row['sourceStable']=row['sourceBefore']==row['sourceAfter']
for stream,raw in [('stdout',stdout),('stderr',stderr)]:
 path=out/(stream+'.txt');path.write_bytes(raw)
 row[stream]=path.relative_to(ROOT).as_posix();row[stream+'Hash']={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
(out/'commands.json').write_text(json.dumps([row],indent=2)+'\n',encoding='utf8')
print(stdout.decode('utf8',errors='replace'));print(json.dumps({'exit':code,'timedOut':timedout,'sourceStable':row['sourceStable'],'wallSeconds':row['wallSeconds']}))
raise SystemExit(code if code is not None and row['sourceStable'] else 1)
