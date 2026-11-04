"""Capture a fresh post-feature aggregate, including rejected/missing evidence."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import argparse,json,re,subprocess,sys,time

if not __debug__:raise SystemExit('Run without Python -O')
ROOT=Path(__file__).resolve().parents[2]
PREFIX='accelerated-sphere-box-coverage'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('feature');parser.add_argument('directory')
args=parser.parse_args();assert re.fullmatch('[0-9a-f]{40}',args.feature)
out=(ROOT/args.directory).resolve()
assert out.is_relative_to((ROOT/f'reports/{PREFIX}-checks').resolve())
out.mkdir(parents=True,exist_ok=False)
recipe=f'reports/{PREFIX}-recipes'
command=[sys.executable,'-B','-X','utf8',recipe+'/public-summary.py',args.feature,args.directory]
frozen=[recipe+'/'+name+'.py' for name in ['public-summary','public-summary-run','public','public-check','check','summary','summary-run','integrate','integrate-lesson','fix-public-collection']]
frozen += ['core/include/pikapika/accelerated_sphere_box_coverage.hpp','core/src/accelerated_sphere_box_coverage.cpp',
 'tests/accelerated_sphere_box_coverage_tests.cpp','tests/accelerated_sphere_box_coverage_fixtures.cpp',
 'tests/accelerated_sphere_box_coverage_test_support.hpp','scripts/verify-accelerated-sphere-box-coverage.py',
 'tests/accelerated_sphere_box_coverage_reference_tests.py','CMakeLists.txt','.github/workflows/verify.yml','.gitattributes']
frozen += [f'reports/{PREFIX}-'+name+'.json' for name in ['baseline','local-verification','public-bytes','public-runs','public-ci-evidence']]
frozen += [f'reports/{PREFIX}-public-browser/observations.json']
frozen += [f'reports/{PREFIX}-public-collection-development/run-001/'+n for n in ['correction.json','original-public.py.txt','actual.patch.txt']]
# Dynamic inputs are hashed as recorded, but their content is accepted only by
# the child verifier. Malformed/missing metadata still gets a captured failure.
for metadata,extract in [(f'reports/{PREFIX}-public-ci-evidence.json',lambda d:[d['engine']['log']['path']]),
 (f'reports/{PREFIX}-public-browser/observations.json',lambda d:[f'reports/{PREFIX}-public-browser/'+n for n in d['files']])]:
    try:
        data=json.loads((ROOT/metadata).read_text(encoding='utf-8-sig'))
        for path in extract(data):
            resolved=(ROOT/path).resolve()
            assert resolved.is_relative_to(ROOT)
            frozen.append(resolved.relative_to(ROOT).as_posix())
    except (OSError,ValueError,KeyError,TypeError,AssertionError):pass
frozen=sorted(set(frozen))


def hashes():
    result={}
    for path in frozen:
        file=ROOT/path
        if file.is_file():
            raw=file.read_bytes();result[path]={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
        else:result[path]={'missing':True}
    return result


before=hashes();started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
try:
    process=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180)
    code,stdout,stderr,timed_out=process.returncode,process.stdout,process.stderr,False
except subprocess.TimeoutExpired as error:
    code,stdout,stderr,timed_out=None,error.stdout or b'',error.stderr or b'',True
row={'name':'public-summary','args':command,'started':started,'wallSeconds':time.perf_counter()-clock,
     'exit':code,'timedOut':timed_out,'sourceBefore':before,'sourceAfter':hashes()}
row['sourceStable']=row['sourceBefore']==row['sourceAfter']
for stream,raw in [('stdout',stdout),('stderr',stderr)]:
    path=out/(stream+'.txt');path.write_bytes(raw)
    row[stream]=path.relative_to(ROOT).as_posix();row[stream+'Hash']={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
(out/'commands.json').write_text(json.dumps([row],indent=2)+'\n',encoding='utf-8')
print(stdout.decode('utf-8',errors='replace'))
print(json.dumps({'exit':code,'timedOut':timed_out,'sourceStable':row['sourceStable'],'wallSeconds':row['wallSeconds']}))
raise SystemExit(code if code is not None and row['sourceStable'] else 1)
