"""Verify the local coverage evidence; public CI/sanitizer acceptance is separate."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
import argparse
import importlib.util
import json
import math
import re
import subprocess
import sys

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'accelerated-pair-coverage'
CHECKS = ROOT/f'reports/{PREFIX}-checks'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory')
args = parser.parse_args()
OUT = (ROOT/args.directory).resolve()
assert OUT.is_dir() and OUT.is_relative_to(CHECKS.resolve())
NATIVE = CHECKS/'run-20261104-native-001'
REGRESSIONS = CHECKS/'run-20261104-regressions-001'
REFERENCE = CHECKS/'run-20261104-reference-001'
SOURCES = ['core/include/pikapika/accelerated_pair_coverage.hpp',
           'core/src/accelerated_pair_coverage.cpp',
           'tests/accelerated_pair_coverage_tests.cpp',
           'tests/accelerated_pair_coverage_fixtures.cpp',
           'tests/accelerated_pair_coverage_test_support.hpp',
           'scripts/verify-accelerated-pair-coverage.py',
           'tests/accelerated_pair_coverage_reference_tests.py']
INTEGRATION = ['CMakeLists.txt', '.github/workflows/verify.yml', '.gitattributes']
evidence = {}


def relative(path):
    p = Path(path)
    p = (p if p.is_absolute() else ROOT/p).resolve()
    assert p.is_relative_to(ROOT), p
    return p.relative_to(ROOT).as_posix()


def info(raw):
    assert len(raw) <= 64*1024*1024
    return {'bytes':len(raw), 'sha256':sha256(raw).hexdigest()}


def stamp(value):
    assert type(value['bytes']) is int and 0 <= value['bytes'] <= 64*1024*1024
    assert re.fullmatch('[0-9a-f]{64}', value['sha256'])
    return {k:value[k] for k in ['bytes','sha256']}


def remember(path):
    name = relative(path)
    evidence[name] = info((ROOT/name).read_bytes())
    return evidence[name]


def load(path):
    remember(path)
    def floating(token):
        value = float(token)
        assert math.isfinite(value)
        assert not (value == 0 and any(c in '123456789' for c in token.lower().split('e')[0]))
        return value
    def pairs(items):
        value = {}
        for key,item in items:
            assert key not in value, key
            value[key] = item
        return value
    return json.loads((ROOT/relative(path)).read_text(encoding='utf-8-sig'),
                      parse_float=floating, parse_int=lambda t:-0.0 if t=='-0' else int(t),
                      parse_constant=lambda t:(_ for _ in ()).throw(AssertionError(t)),
                      object_pairs_hook=pairs)


def git_blobs(commit, paths):
    assert re.fullmatch('[0-9a-f]{40}', commit)
    paths = sorted(set(paths))
    assert len(paths) <= 1024
    for path in paths:
        p = PurePosixPath(path)
        assert not p.is_absolute() and '..' not in p.parts and p.as_posix()==path
    raw = subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
                                  input=''.join(commit+':'+p+'\n' for p in paths).encode())
    result = {}; offset = 0
    for path in paths:
        end = raw.index(b'\n',offset); header = raw[offset:end].split()
        assert len(header)==3 and header[1]==b'blob'
        size = int(header[2]); offset = end+1
        result[path] = raw[offset:offset+size]
        assert len(result[path])==size and raw[offset+size:offset+size+1]==b'\n'
        offset += size+1
    assert offset == len(raw)
    return result


def normalized_html(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                  re.sub(rb'\?build=[a-f0-9]{16}', b'', raw),flags=re.S).replace(b'\r\n',b'\n')


base = load(f'reports/{PREFIX}-baseline.json')
assert base['schema']==1 and base['baseCommit']=='41c9cc2d28817e3491b8ab8e47922cc5cc153ae5'
assert len(base['protected'])==362 and len(base['generatedEntries'])==26
assert set(base['permittedOldSources'])==set(INTEGRATION)
for path,value in base['protected'].items():
    assert remember(path)==stamp(value), path
blobs = git_blobs(base['baseCommit'],[*INTEGRATION,*base['generatedEntries']])
generated = {}
for path,value in base['generatedEntries'].items():
    assert remember(path)==stamp(value), path
    raw = (ROOT/path).read_bytes()
    assert normalized_html(raw)==normalized_html(blobs[path]), path
    generated[path] = {'raw':evidence[path], 'normalizedBody':info(normalized_html(raw)),
                       'rawUnchanged':True, 'baseGitBodyUnchanged':True}

CMAKE_LIBRARY = '''target_sources(pikapika_core PRIVATE core/src/accelerated_pair_coverage.cpp)
if(MSVC)
  set_source_files_properties(core/src/accelerated_pair_coverage.cpp PROPERTIES COMPILE_OPTIONS "/fp:strict")
else()
  set_source_files_properties(core/src/accelerated_pair_coverage.cpp PROPERTIES COMPILE_OPTIONS "-fno-fast-math;-ffp-contract=off;-frounding-math")
endif()
'''
CMAKE_TEST = '''  add_executable(pikapika_accelerated_pair_coverage_tests tests/accelerated_pair_coverage_tests.cpp tests/accelerated_pair_coverage_fixtures.cpp)
  target_link_libraries(pikapika_accelerated_pair_coverage_tests PRIVATE pikapika_core)
  if(MSVC)
    target_compile_options(pikapika_accelerated_pair_coverage_tests PRIVATE /W4 /permissive- /fp:strict)
  else()
    target_compile_options(pikapika_accelerated_pair_coverage_tests PRIVATE -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -frounding-math)
  endif()
  add_test(NAME accelerated_pair_coverage COMMAND pikapika_accelerated_pair_coverage_tests)
'''
CI_MAIN = '''          build/ci/pikapika_accelerated_pair_coverage_tests --fixtures > build/ci/accelerated-pair-coverage-fixtures.json
          build/ci/pikapika_accelerated_pair_coverage_tests --storage > build/ci/accelerated-pair-coverage-storage.json
          python3 scripts/verify-accelerated-pair-coverage.py build/ci/accelerated-pair-coverage-fixtures.json
          python3 tests/accelerated_pair_coverage_reference_tests.py build/ci/accelerated-pair-coverage-fixtures.json --output build/ci/accelerated-pair-coverage-reference
'''
CI_AUDIT = '''      - name: Audit owned accelerated pair coverage independently
        run: |
          for source in core/src/accelerated_pair_coverage.cpp tests/accelerated_pair_coverage_tests.cpp tests/accelerated_pair_coverage_fixtures.cpp; do
            g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror -fno-fast-math -ffp-contract=off -frounding-math -Icore/include -Itests -c "$source" -o "build/ci/$(basename "$source" .cpp)-warning.o"
          done
          g++ -std=c++20 -O1 -g -Wall -Wextra -fno-fast-math -ffp-contract=off -frounding-math -fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer -Icore/include -Itests core/src/interval.cpp core/src/accelerated.cpp core/src/accelerated_pair_coverage.cpp tests/accelerated_pair_coverage_tests.cpp tests/accelerated_pair_coverage_fixtures.cpp -o build/ci/accelerated-pair-coverage-sanitized
          ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 build/ci/accelerated-pair-coverage-sanitized
          ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 build/ci/accelerated-pair-coverage-sanitized --fixtures > build/ci/accelerated-pair-coverage-sanitized-fixtures.json
          cmp build/ci/accelerated-pair-coverage-fixtures.json build/ci/accelerated-pair-coverage-sanitized-fixtures.json
          python3 scripts/verify-accelerated-pair-coverage.py build/ci/accelerated-pair-coverage-sanitized-fixtures.json
'''
ATTRS = '''reports/accelerated-pair-coverage-* -text -whitespace
reports/accelerated-pair-coverage-*/** -text -whitespace
'''
old_changes = {}
for path,fragments in [('CMakeLists.txt',[CMAKE_LIBRARY,CMAKE_TEST]),
                       ('.github/workflows/verify.yml',[CI_MAIN,CI_AUDIT]),('.gitattributes',[ATTRS])]:
    archived = base['permittedOldSources'][path]
    old = archived['gitBlobUtf8'].encode()
    assert old==blobs[path] and info(old)==stamp(archived['gitBlob'])
    raw = (ROOT/path).read_bytes(); reconstructed = raw
    for fragment in fragments:
        chunk = fragment.encode()
        if reconstructed.count(chunk)!=1:
            chunk = chunk.replace(b'\n',b'\r\n')
        assert reconstructed.count(chunk)==1, path
        reconstructed = reconstructed.replace(chunk,b'',1)
    conversion = None
    if reconstructed != old:
        assert b'\r\n' in reconstructed and reconstructed.replace(b'\r\n',b'\n')==old, path
        conversion = 'Declared text CRLF-to-LF only, after exact raw comparison.'
    old_changes[path] = {'raw':remember(path),'baseGitBlob':info(old),
                         'insertedLines':sum(len(x.splitlines()) for x in fragments),
                         'reconstruction':'Exact declared insertions only.','normalization':conversion}
assert [old_changes[p]['insertedLines'] for p in INTEGRATION]==[14,14,2]

manifest = load('assets/pikapika-simulation.build.json')
assert manifest==base['sdkManifest']
assert (len(manifest['sources']),len(manifest['sourceSha256']),len(manifest['linkedLibraryMembers']),len(manifest['licenses']))==(32,67,91,7)
exports = json.loads(next(f.split('=',1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports)==len(set(exports))==92
assert not any('accelerated_pair_coverage' in p for p in manifest['sourceSha256'])
for path,value in [*manifest['sourceSha256'].items(),*manifest['licenses'].items()]:
    assert remember(path)['sha256']==value, path
for path,value in manifest['artifacts'].items():
    assert remember(path)==stamp(value), path

source_hashes = {p:remember(p) for p in SOURCES}
recorder_change = load(NATIVE/'log-extension-change.json')
old_recorder = ROOT/recorder_change['source']['beforeArchive']
assert remember(old_recorder)==stamp(recorder_change['source']['before'])
assert remember(recorder_change['source']['path'])==stamp(recorder_change['source']['after'])
assert old_recorder.read_bytes().replace(b"(out/'LastTest.log').write_bytes",b"(out/'LastTest.txt').write_bytes")== (ROOT/recorder_change['source']['path']).read_bytes()
assert recorder_change['testReruns']==0
assert remember(NATIVE/'LastTest.txt')==stamp(recorder_change['lastTest'])
commands = []; command_files = []
common_sources = set(SOURCES[:5])|set(INTEGRATION)|{f'reports/{PREFIX}-recipes/check.py'}
for directory,names,expected_sources in [
        (NATIVE,['configure','build','dedicated','fixtures','storage','ctest'],common_sources),
        (REGRESSIONS,['node','syntax','web-build'],common_sources),
        (REFERENCE,['checker','negative-controls'],common_sources|set(SOURCES[5:])|{relative(NATIVE/'native-fixtures.json')})]:
    path = directory/'commands.json'; rows = load(path); command_files.append(relative(path))
    assert [r['name'] for r in rows]==names
    for row in rows:
        assert type(row['exit']) is int and row['exit']==0 and row['timedOut'] is False
        assert row['sourceStable'] is True and row['sourceBefore']==row['sourceAfter']
        assert set(row['sourceAfter'])==expected_sources
        for path,value in row['sourceAfter'].items():
            if path==f'reports/{PREFIX}-recipes/check.py' and directory in {NATIVE,REGRESSIONS}:
                assert stamp(value)==stamp(recorder_change['source']['before'])
            else:
                assert remember(path)==stamp(value), path
        assert type(row['wallSeconds']) in (int,float) and math.isfinite(row['wallSeconds']) and row['wallSeconds']>=0
        datetime.fromisoformat(row['started'])
        for stream in ['stdout','stderr']:
            assert remember(row[stream])==stamp(row[stream+'Hash'])
        commands.append(row)


def command(name):
    matches = [r for r in commands if r['name']==name]
    assert len(matches)==1, name
    return matches[0]


def stdout(name):
    return (ROOT/command(name)['stdout']).read_text(encoding='utf-8-sig')


assert command('configure')['args'][1:]==['-S','.','-B','build/native']
assert command('build')['args'][1:]==['--build','build/native','--config','Release','--parallel']
binary = ROOT/'build/native/Release/pikapika_accelerated_pair_coverage_tests.exe'
for name,tail in [('dedicated',[]),('fixtures',['--fixtures']),('storage',['--storage'])]:
    assert Path(command(name)['args'][0]).resolve()==binary and command(name)['args'][1:]==tail
assert command('ctest')['args'][1:]==['--test-dir','build/native','-C','Release','--output-on-failure']
assert command('ctest')['timeoutSeconds']==300
assert '69 groups PASS; 65 finite fixtures; 1913 actual public-value exact-bit replays' in stdout('dedicated')
assert re.search(r'warning(?: C\d+|:)', stdout('build'),re.I) is None
assert '100% tests passed, 0 tests failed out of 43' in stdout('ctest')
names = re.findall(r'add_test\(NAME\s+(\S+)',(ROOT/'CMakeLists.txt').read_text())
observed = re.findall(r'^\s*(\d+)/43 Test\s+#(\d+): (\S+)\s+\.+\s+Passed\s+([\d.]+) sec\s*$',stdout('ctest'),re.M)
assert len(names)==len(observed)==43
assert [(int(a),int(b),n) for a,b,n,_ in observed]==[(i,i,n) for i,n in enumerate(names,1)]
native_seconds = float(re.search(r'Total Test time \(real\) = ([\d.]+) sec',stdout('ctest'))[1])
assert 0<native_seconds<=command('ctest')['wallSeconds']+1
lasttest = (NATIVE/'LastTest.txt').read_bytes(); remember(NATIVE/'LastTest.txt')
assert b'69 groups PASS; 65 finite fixtures; 1913 actual public-value exact-bit replays' in lasttest

expected_tests = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'tests').glob('*.test.mjs'))]+['docs/learn/learn.test.mjs']
assert command('node')['args'][1:] == ['--test',*expected_tests]
for key,value in [('tests',684),('pass',684),('fail',0),('skipped',0),('cancelled',0)]:
    assert re.search(r'^(?:#|\u2139) '+key+r' '+str(value)+r'\s*$',stdout('node'),re.M), key
assert command('syntax')['args'][1:]==['scripts/check.mjs']
assert command('web-build')['args'][1:]==['scripts/build-web.mjs']
web = re.fullmatch(r'Web build ([a-f0-9]{16}): (\d+) versioned modules; generated import maps',stdout('web-build').strip())
assert web and web[1]=='cd45c7f1ac2ba5e5' and int(web[2])==54

fixture_path = NATIVE/'native-fixtures.json'
assert fixture_path.read_bytes()==(ROOT/command('fixtures')['stdout']).read_bytes()
fixtures = load(fixture_path)
assert fixtures['schema']==1 and fixtures['kind']=='accelerated-pair-coverage-fixtures' and len(fixtures['fixtures'])==65
assert Counter(f['result']['status'] for f in fixtures['fixtures'])=={'certified':18,'not_certified':19,'invalid_input':28}
assert sum(len(f['result']['audits']) for f in fixtures['fixtures'])==1913
assert sum(f['result']['work']['valueCallsAttempted'] for f in fixtures['fixtures'])==1913
assert sum(f['result']['work']['valueCallsReturned'] for f in fixtures['fixtures'])==1913

# Use the independent checker itself; this is a mathematical acceptance distinct
# from Native direct-public-value exact-bit replays, not a translated value graph.
spec = importlib.util.spec_from_file_location('coverage_aggregation_reference',ROOT/SOURCES[5])
reference = importlib.util.module_from_spec(spec); sys.modules[spec.name]=reference; spec.loader.exec_module(reference)
independent = reference.verify(reference.load(fixture_path))
assert independent == load(command('checker')['stdout'])
for key,value in {'fixtures':65,'certified':18,'notCertified':19,'invalidInputs':28,
                  'cellAudits':1913,'partitionLeaves':1040,'frontierCells':128,'currentCells':2,
                  'returnedIntervals':1913,'planeRangeProofs':690,'sphereRangeProofs':1223,
                  'maximumAudits':255,'maximumPartition':128,'maximumFrontier':127,
                  'subdividedCertified':2}.items():
    assert independent[key]==value, (key,independent[key])
assert independent['inputFingerprint']=='867fef69e55cf8461310b07f0144c8d2288987ab68311d6d86a04b01e8cca85e'
assert command('checker')['args'][-2:]==[SOURCES[5],relative(fixture_path)]
assert command('negative-controls')['args'][-4:]==[SOURCES[6],relative(fixture_path),'--output',relative(REFERENCE/'controls')]
controls_stdout = load(command('negative-controls')['stdout'])
assert controls_stdout['status']=='PASS'
for p in sorted((REFERENCE/'controls').rglob('*')):
    if p.is_file():
        remember(p)
controls = load(REFERENCE/'controls/negative-controls.json')
assert controls['status']=='PASS' and controls['baseline']==independent
assert controls['labelAndOrderIndependent'] is True
assert controls['selfTestGroups']==controls_stdout['selfTestGroups']==14
assert controls_stdout['rejectedControls']==53
assert controls['positiveControls']['mathematicallyValidWiderIntervalAccepted'] is True
assert controls['positiveControls']['syntheticNonreturnedAttemptAccepted'] is True
assert len(controls['rejectedControls'])==controls_stdout['rejectedControls']
assert all(c['rejected'] is True for c in controls['rejectedControls'])
assert len({c['name'] for c in controls['rejectedControls']})==len(controls['rejectedControls'])
optimized = load(REFERENCE/'controls/optimized-command.json')
assert type(optimized['exitCode']) is int and optimized['exitCode']!=0 and '-O' in optimized['command']
for proof in load(REFERENCE/'controls/provenance.json'):
    assert remember(proof['path'])==stamp(proof)

storage = load(NATIVE/'native-storage.json')
assert (NATIVE/'native-storage.json').read_bytes()==(ROOT/command('storage')['stdout']).read_bytes()
assert storage['schema']==1 and storage['kind']=='accelerated-pair-coverage-storage'
sizes,caps = storage['sizes'],storage['capacities']
assert caps=={'audits':255,'partition':128,'frontier':128}
assert all(type(v) is int and v>0 for v in sizes.values())
components = {'inlineResult':sizes['result'],'auditBuffer':caps['audits']*sizes['audit'],
              'partitionBuffer':caps['partition']*sizes['partitionLeaf'],
              'frontierBuffer':caps['frontier']*sizes['cell']}

# Keep every pre-canonical attempt, including failures. Binary/compiler objects
# are excluded; all raw commands, invocation, source hashes and streams remain.
history = []
for directory in [ROOT/f'reports/{PREFIX}-native-development',
                  ROOT/f'reports/{PREFIX}-reference-development', ROOT/f'reports/{PREFIX}-agent-tests']:
    if not directory.exists():
        continue
    for p in sorted(directory.rglob('*')):
        if p.is_file() and p.suffix.lower() not in {'.exe','.obj','.lib','.pdb','.ilk','.log'}:
            remember(p)
    for p in sorted(directory.rglob('commands.json')):
        attempts = load(p)
        history.append({'path':relative(p),'attempts':attempts})
collection_notes = []
for directory in sorted(CHECKS.iterdir()):
    if not directory.is_dir() or directory.resolve()==OUT:
        continue
    for p in sorted(directory.rglob('*')):
        if p.is_file() and p.suffix.lower() not in {'.exe','.obj','.lib','.pdb','.ilk','.log'}:
            remember(p)
    if (directory/'command.json').exists():
        collection_notes.append({'path':relative(directory/'command.json'),'record':load(directory/'command.json')})
standalone = load(ROOT/f'reports/{PREFIX}-native-development/run-001/commands.json')
assert [r['name'] for r in standalone]==['compile','native-tests','native-fixtures','storage']
for r in standalone:
    assert r['exit']==0 and r['sourceStable'] is True and r['sourceBefore']==r['sourceAfter']
    for p,value in r['sourceAfter'].items():
        assert remember(p)==stamp(value), p
assert fixture_path.read_bytes()==(ROOT/f'reports/{PREFIX}-native-development/run-001/native-fixtures.json').read_bytes()
assert b'69 groups PASS; 65 finite fixtures; 1913 actual public-value exact-bit replays' in (ROOT/standalone[1]['stdout']).read_bytes()
for path in [f'reports/{PREFIX}-recipes/check.py', f'reports/{PREFIX}-recipes/summary-run.py',__file__]:
    remember(path)
assert len(evidence)<=4096 and sum(x['bytes'] for x in evidence.values())<=128*1024*1024
report = {'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),
          'baseCommit':base['baseCommit'],'ctest':43,'nativeGroups':69,'finiteFixtures':65,
          'nativePublicValueExactBitReplays':1913,'nativeNegativeZeroIntervalBounds':0,'node':684,'skipped':0,
          'independentReference':independent,'selfTestGroups':controls['selfTestGroups'],
          'negativeControls':len(controls['rejectedControls']),'positiveControls':controls['positiveControls'],'exports':92,'sourceHeaders':67,
          'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
          'artifacts':{p:remember(p) for p in manifest['artifacts']},
          'protectedFilesUnchanged':362,'generatedEntriesUnchanged':26,'generatedEntries':generated,
          'newSources':source_hashes,'permittedOldChanges':old_changes,'webBuild':web[1],'modules':54,
          'commandFiles':command_files,'commands':commands,'nativeCtestSeconds':native_seconds,
          'storageObservation':{'sizes':sizes,'capacities':caps,'sizeofCapacityComponents':components,
                                'sizeofCapacityBytes':sum(components.values()),'scope':storage['scope']},
          'historicalAttempts':history,'collectionNotes':collection_notes,'recorderEvidenceExtensionChange':recorder_change,
          'scope':'Native public-value-only closed coverage. Mathematical range containment is independent of exact public-value output provenance. No old search, World propagation, inflation, entry, response or state mutation.',
          'notMeasured':{'publicLinuxCI':'Not part of this local aggregate; declarations are not completed runs.',
                         'allocationAndValueFaults':'No natural allocator/value-throw injection performed.',
                         'negativeZeroIntervals':'The1913 returned intervals contain zero negative-zero endpoints. Source/snapshot signed-zero preservation is tested separately; no observed negative-zero returned-bound coverage is invented.',
                         'storage':'sizeof*returned capacity only; no allocator overhead/temporary/stack/RSS/used-heap or process-wide allocation guarantee.',
                         'normalWork':'Private plane norm actual iterations/refinements are not observable: reported attempts and64*attempts are conservative upper bounds.',
                         'mathematicalProvenance':'Mathematically valid wider geom-only/Horner-only intervals cannot generally be rejected by range containment alone. Native direct-value bit replay separately checks unchanged public intersection output.',
                         'floatingEnvironment':'Requested rounding-control and FTZ/DAZ refusal/recovery tests are bounded target probes, not all-target compiler verification or preservation of every exception flag.',
                         'wholeWorld':'No all-body/pair World certification, candidate publication, response, CCD or tolerance-based contact acceptance.'},
          'evidence':evidence}
output = OUT/'acceptance.json'
assert not output.exists()
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:report[k] for k in ['status','ctest','nativeGroups','finiteFixtures','nativePublicValueExactBitReplays','node','skipped','selfTestGroups','negativeControls','protectedFilesUnchanged','generatedEntriesUnchanged','webBuild']}))
