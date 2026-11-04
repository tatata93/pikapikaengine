"""Capture bounded coverage integration commands; every attempt uses a fresh directory."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
import shutil
import subprocess
import sys
import time

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'accelerated-sphere-box-coverage'
SOURCES = ['core/include/pikapika/accelerated_sphere_box_coverage.hpp',
           'core/src/accelerated_sphere_box_coverage.cpp',
           'tests/accelerated_sphere_box_coverage_tests.cpp',
           'tests/accelerated_sphere_box_coverage_fixtures.cpp',
           'tests/accelerated_sphere_box_coverage_test_support.hpp']
INTEGRATION = ['CMakeLists.txt', '.github/workflows/verify.yml', '.gitattributes']
REFERENCE = ['scripts/verify-accelerated-sphere-box-coverage.py',
             'tests/accelerated_sphere_box_coverage_reference_tests.py']
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('phase', choices=['native', 'regressions', 'reference'])
parser.add_argument('directory')
parser.add_argument('--fixtures')
args = parser.parse_args()
out = (ROOT/args.directory).resolve()
assert out.is_relative_to((ROOT/f'reports/{PREFIX}-checks').resolve())
out.mkdir(parents=True, exist_ok=False)
base = json.loads((ROOT/f'reports/{PREFIX}-baseline.json').read_text(encoding='utf8'))
assert len(base['protected']) == 376 and len(base['generatedEntries']) == 26
frozen = [*SOURCES, *INTEGRATION, f'reports/{PREFIX}-recipes/check.py']
if args.phase == 'reference':
    assert args.fixtures
    frozen += [*REFERENCE, args.fixtures]

def info(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}

def hashes():
    return {p: info((ROOT/p).read_bytes()) for p in frozen}

def originals():
    for p, value in base['protected'].items():
        assert info((ROOT/p).read_bytes()) == value, p

originals()
initial = hashes()
rows = []
(out/'invocation.json').write_text(json.dumps({'args':sys.argv,'cwd':str(ROOT),'python':sys.version,
    'started':datetime.now(timezone.utc).isoformat(),'sourceHashes':initial},indent=2)+'\n',encoding='utf8')

def run(name, command, timeout):
    originals()
    before = hashes()
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    try:
        process = subprocess.run(command,cwd=ROOT,capture_output=True,timeout=timeout)
        code, stdout, stderr, timedout = process.returncode,process.stdout,process.stderr,False
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr, timedout = None,error.stdout or b'',error.stderr or b'',True
    row = {'name':name,'args':command,'started':started,'timeoutSeconds':timeout,
           'wallSeconds':time.perf_counter()-clock,'exit':code,'timedOut':timedout,
           'sourceBefore':before,'sourceAfter':hashes()}
    row['sourceStable'] = row['sourceBefore'] == row['sourceAfter'] == initial
    for stream, raw in [('stdout',stdout),('stderr',stderr)]:
        path = out/f'{name}.{stream}.txt'
        path.write_bytes(raw)
        row[stream] = path.relative_to(ROOT).as_posix()
        row[stream+'Hash'] = info(raw)
    rows.append(row)
    (out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'name':name,'exit':code,'seconds':row['wallSeconds'],
                      'stable':row['sourceStable'],'timedOut':timedout}),flush=True)
    originals()
    assert code == 0 and not timedout and row['sourceStable'], name
    return stdout

if args.phase == 'native':
    cmake = shutil.which('cmake')
    assert cmake
    run('configure',[cmake,'-S','.','-B','build/native'],120)
    run('build',[cmake,'--build','build/native','--config','Release','--parallel'],300)
    binary = str(ROOT/'build/native/Release/pikapika_accelerated_sphere_box_coverage_tests.exe')
    run('dedicated',[binary],120)
    (out/'native-fixtures.json').write_bytes(run('fixtures',[binary,'--fixtures'],120))
    (out/'native-storage.json').write_bytes(run('storage',[binary,'--storage'],120))
    try:
        run('ctest',[shutil.which('ctest'),'--test-dir','build/native','-C','Release','--output-on-failure'],300)
    finally:
        log = ROOT/'build/native/Testing/Temporary/LastTest.log'
        if log.is_file():
            (out/'LastTest.txt').write_bytes(log.read_bytes())
elif args.phase == 'regressions':
    node = shutil.which('node')
    assert node
    run('node',[node,'--test',*[p.as_posix() for p in sorted(Path('tests').glob('*.test.mjs'))],
                'docs/learn/learn.test.mjs'],240)
    run('syntax',[node,'scripts/check.mjs'],120)
    run('web-build',[node,'scripts/build-web.mjs'],90)
else:
    run('checker',[sys.executable,'-B','-X','utf8',REFERENCE[0],args.fixtures],120)
    run('negative-controls',[sys.executable,'-B','-X','utf8',REFERENCE[1],args.fixtures,
                              '--output',(out/'controls').relative_to(ROOT).as_posix()],180)
print(json.dumps({'status':'PASS','phase':args.phase,'commands':len(rows)}))
