"""Accept the recorded Native preparation milestone; public CI is a later gate."""
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
PREFIX = 'world-static-mesh-preparation'
CHECKS = ROOT/f'reports/{PREFIX}-checks'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', nargs='?', default=f'reports/{PREFIX}-checks')
args = parser.parse_args()
CAPTURE = (ROOT/args.directory).resolve()
assert CAPTURE.is_dir() and CAPTURE.is_relative_to(CHECKS.resolve())
NATIVE = CHECKS/'run-20261104-native-002'
REFERENCE = CHECKS/'run-20261104-reference-001'
REGRESSIONS = CHECKS/'run-20261104-regressions-001'
SOURCES = ['core/include/pikapika/world_static_mesh_flight.hpp',
           'core/src/world_static_mesh_flight.cpp',
           'tests/world_static_mesh_flight_preparation_tests.cpp',
           'tests/world_static_mesh_flight_preparation_fixtures.cpp',
           'tests/world_static_mesh_flight_preparation_support.hpp',
           'scripts/verify-world-static-mesh-preparation.py',
           'tests/world_static_mesh_preparation_reference_tests.py']
evidence = {}


def relative(path):
    p = Path(path)
    p = (p if p.is_absolute() else ROOT/p).resolve()
    assert p.is_relative_to(ROOT), p
    return p.relative_to(ROOT).as_posix()


def hash_bytes(raw):
    assert len(raw) <= 64*1024*1024
    return {'bytes':len(raw), 'sha256':sha256(raw).hexdigest()}


def stamp(value):
    assert set(value) >= {'bytes','sha256'}
    assert type(value['bytes']) is int and 0 <= value['bytes'] <= 64*1024*1024
    assert type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256'])
    return {'bytes':value['bytes'], 'sha256':value['sha256']}


def remember(path):
    key = relative(path)
    evidence[key] = hash_bytes((ROOT/key).read_bytes())
    return evidence[key]


def read(path):
    remember(path)
    def floating(token):
        value = float(token)
        assert math.isfinite(value) and not (value == 0 and any(c in '123456789' for c in token.lower().split('e')[0]))
        return value
    def pairs(items):
        result = {}
        for key,value in items:
            assert key not in result, key
            result[key] = value
        return result
    return json.loads((ROOT/relative(path)).read_text(encoding='utf-8-sig'),
                      parse_float=floating, parse_int=lambda t:-0.0 if t=='-0' else int(t),
                      parse_constant=lambda t:(_ for _ in ()).throw(AssertionError(t)), object_pairs_hook=pairs)


def git_blobs(commit, paths):
    assert re.fullmatch('[0-9a-f]{40}',commit)
    paths = sorted(set(paths))
    assert len(paths) <= 1024
    for path in paths:
        p = PurePosixPath(path)
        assert not p.is_absolute() and '..' not in p.parts and p.as_posix()==path
    raw = subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
                                  input=''.join(commit+':'+p+'\n' for p in paths).encode())
    assert len(raw) <= 64*1024*1024
    result = {}; offset = 0
    for path in paths:
        end = raw.index(b'\n',offset); header = raw[offset:end].split()
        assert len(header)==3 and header[1]==b'blob', path
        size = int(header[2]); offset = end+1
        result[path] = raw[offset:offset+size]
        assert len(result[path])==size and raw[offset+size:offset+size+1]==b'\n'
        offset += size+1
    assert offset==len(raw)
    return result


def text_reconstruction(raw, old):
    # Original -text C++ sources may themselves contain CRLF: exact comparison
    # precedes the sole declared Git-text CRLF-to-LF conversion.
    if raw == old:
        return None
    assert b'\r\n' in raw and raw.replace(b'\r\n',b'\n') == old
    return 'Declared text CRLF-to-LF only, after exact raw comparison.'


def normalized_html(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',
                  re.sub(rb'\?build=[a-f0-9]{16}',b'',raw),flags=re.S).replace(b'\r\n',b'\n')


base_path = f'reports/{PREFIX}-baseline.json'
base = read(base_path)
assert base['schema']==1 and base['baseCommit']=='7176c1fe283ac94d061db34411e941d376690123'
assert len(base['protected'])==355 and len(base['generatedEntries'])==26
assert set(base['permittedOldSources'])=={'CMakeLists.txt','.github/workflows/verify.yml','.gitattributes'}
assert not set(base['permittedOldSources']) & set(base['protected'])
for path,value in base['protected'].items():
    assert remember(path)==stamp(value), path
blobs = git_blobs(base['baseCommit'],[*base['permittedOldSources'],*base['generatedEntries']])
generated = {}
for path,value in base['generatedEntries'].items():
    # This build retained even the raw26 pages; the separate normalized-body
    # comparison to the base Git blob also excludes line-ending/import-map churn.
    assert remember(path)==stamp(value), path
    raw = (ROOT/path).read_bytes()
    assert normalized_html(raw)==normalized_html(blobs[path]), path
    generated[path] = {'raw':evidence[path], 'normalizedBody':hash_bytes(normalized_html(raw)),
                       'rawUnchanged':True,'baseGitBodyUnchanged':True}

# Remove only the exact authorized insertions and reconstruct each old Git blob.
CMAKE_LIBRARY = '''target_sources(pikapika_core PRIVATE core/src/world_static_mesh_flight.cpp)
if(MSVC)
  set_source_files_properties(core/src/world_static_mesh_flight.cpp PROPERTIES COMPILE_OPTIONS "/fp:strict")
else()
  set_source_files_properties(core/src/world_static_mesh_flight.cpp PROPERTIES COMPILE_OPTIONS "-fno-fast-math;-ffp-contract=off;-frounding-math")
endif()
'''
CMAKE_TEST = '''  add_executable(pikapika_world_static_mesh_flight_preparation_tests tests/world_static_mesh_flight_preparation_tests.cpp tests/world_static_mesh_flight_preparation_fixtures.cpp)
  target_link_libraries(pikapika_world_static_mesh_flight_preparation_tests PRIVATE pikapika_core)
  if(MSVC)
    target_compile_options(pikapika_world_static_mesh_flight_preparation_tests PRIVATE /W4 /permissive- /fp:strict)
  else()
    target_compile_options(pikapika_world_static_mesh_flight_preparation_tests PRIVATE -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -frounding-math)
  endif()
  add_test(NAME world_static_mesh_flight_preparation COMMAND pikapika_world_static_mesh_flight_preparation_tests)
'''
CI_COMMANDS = '''          build/ci/pikapika_world_static_mesh_flight_preparation_tests --fixtures > build/ci/world-static-mesh-preparation-fixtures.json
          build/ci/pikapika_world_static_mesh_flight_preparation_tests --storage > build/ci/world-static-mesh-preparation-storage.json
          python3 scripts/verify-world-static-mesh-preparation.py build/ci/world-static-mesh-preparation-fixtures.json
          python3 tests/world_static_mesh_preparation_reference_tests.py build/ci/world-static-mesh-preparation-fixtures.json --output build/ci/world-static-mesh-preparation-reference
'''
CI_AUDIT = '''      - name: Audit owned World static mesh preparation independently
        run: |
          for source in core/src/world_static_mesh_flight.cpp tests/world_static_mesh_flight_preparation_tests.cpp tests/world_static_mesh_flight_preparation_fixtures.cpp; do
            g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror -fno-fast-math -ffp-contract=off -frounding-math -Icore/include -Itests -c "$source" -o "build/ci/$(basename "$source" .cpp)-warning.o"
          done
          g++ -std=c++20 -O1 -g -Wall -Wextra -fno-fast-math -ffp-contract=off -frounding-math -fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer -Icore/include -Itests core/src/core.cpp core/src/portable.cpp core/src/dynamics.cpp core/src/interval.cpp core/src/world_static_mesh_flight.cpp tests/world_static_mesh_flight_preparation_tests.cpp tests/world_static_mesh_flight_preparation_fixtures.cpp -o build/ci/world-static-mesh-preparation-sanitized
          ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 build/ci/world-static-mesh-preparation-sanitized
          ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 build/ci/world-static-mesh-preparation-sanitized --fixtures > build/ci/world-static-mesh-preparation-sanitized-fixtures.json
          cmp build/ci/world-static-mesh-preparation-fixtures.json build/ci/world-static-mesh-preparation-sanitized-fixtures.json
          python3 scripts/verify-world-static-mesh-preparation.py build/ci/world-static-mesh-preparation-sanitized-fixtures.json
'''
ATTRS = '''# Owned World/static-mesh preparation proof bytes retain original line endings.
reports/world-static-mesh-* -text -whitespace
reports/world-static-mesh-*/** -text -whitespace

'''
old_changes = {}
for path,fragments in [('CMakeLists.txt',[CMAKE_LIBRARY,CMAKE_TEST]),
                       ('.github/workflows/verify.yml',[CI_COMMANDS,CI_AUDIT]),('.gitattributes',[ATTRS])]:
    archived = base['permittedOldSources'][path]
    old = archived['gitBlobUtf8'].encode()
    assert old==blobs[path] and hash_bytes(old)==stamp(archived['gitBlob'])
    raw = (ROOT/path).read_bytes(); reconstructed = raw
    for fragment in fragments:
        chunk = fragment.encode()
        if reconstructed.count(chunk)!=1:
            chunk = chunk.replace(b'\n',b'\r\n')
        assert reconstructed.count(chunk)==1, path
        reconstructed = reconstructed.replace(chunk,b'',1)
    conversion = text_reconstruction(reconstructed,old)
    old_changes[path] = {'raw':remember(path),'baseGitBlob':hash_bytes(old),
                         'insertedLines':sum(len(f.splitlines()) for f in fragments),
                         'reconstruction':'Exact declared insertions only.','normalization':conversion}

manifest = read('assets/pikapika-simulation.build.json')
assert manifest==base['sdkManifest']
assert (len(manifest['sources']),len(manifest['sourceSha256']),len(manifest['linkedLibraryMembers']),len(manifest['licenses']))==(32,67,91,7)
exports = json.loads(next(f.split('=',1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports)==len(set(exports))==92
assert all('world_static_mesh' not in p for p in manifest['sourceSha256'])
for path,value in [*manifest['sourceSha256'].items(),*manifest['licenses'].items()]:
    assert remember(path)['sha256']==value, path
for path,value in manifest['artifacts'].items():
    assert remember(path)==stamp(value), path
assert manifest['artifacts']['assets/pikapika-simulation.wasm']=={'bytes':800982,'sha256':'a7db41c64d2f9112ec5ee033371c391dddcb42ad23dcef713347c129a4ed015d'}
assert manifest['artifacts']['assets/pikapika-simulation.mjs']=={'bytes':61661,'sha256':'d4bedfdc9dcc1a60ee816e34c43afbe51623835ca5af65b0e6f4f5937484de55'}

source_hashes = {p:remember(p) for p in SOURCES}
commands = []; command_files = []
native_sources = set(SOURCES[:5])|{'CMakeLists.txt'}
reference_sources = set(SOURCES)|{relative(NATIVE/'native-fixtures.json')}
for directory,names,expected_sources in [(NATIVE,['configure','build','fixtures','storage','ctest'],native_sources),
                                        (REFERENCE,['checker','negative-controls'],reference_sources),
                                        (REGRESSIONS,['node','syntax','web-build'],native_sources)]:
    path = directory/'commands.json';rows = read(path);command_files.append(relative(path))
    assert [r['name'] for r in rows]==names
    for row in rows:
        assert type(row['exit']) is int and row['exit']==0 and row.get('timedOut',False) is False and row['sourceStable'] is True
        assert row['sourceBefore']==row['sourceAfter'] and set(row['sourceAfter'])==expected_sources
        for path,value in row['sourceAfter'].items():
            assert remember(path)==stamp(value), path
        assert type(row['wallSeconds']) in (int,float) and math.isfinite(row['wallSeconds']) and row['wallSeconds']>=0
        datetime.fromisoformat(row['started'])
        for stream in ['stdout','stderr']:
            assert remember(row[stream])==stamp(row[stream+'Hash'])
        commands.append(row)


def row(name):
    matches = [r for r in commands if r['name']==name]
    assert len(matches)==1,name
    return matches[0]


def stdout(name):
    return (ROOT/row(name)['stdout']).read_text(encoding='utf-8-sig')


assert row('configure')['args'][1:]==['-S','.','-B','build/native']
assert row('build')['args'][1:]==['--build','build/native','--config','Release','--parallel']
for name,flag in [('fixtures','--fixtures'),('storage','--storage')]:
    assert Path(row(name)['args'][0]).resolve()==ROOT/'build/native/Release/pikapika_world_static_mesh_flight_preparation_tests.exe'
    assert row(name)['args'][1:]==[flag]
assert row('ctest')['args'][1:]==['--test-dir','build/native','-C','Release','--output-on-failure']
assert row('syntax')['args'][1:]==['scripts/check.mjs'] and row('web-build')['args'][1:]==['scripts/build-web.mjs']
expected_tests = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'tests').glob('*.test.mjs'))]+['docs/learn/learn.test.mjs']
assert row('node')['args'][1]=='--test'
assert [p.replace('\\','/') for p in row('node')['args'][2:]]==expected_tests
assert row('checker')['args'][-2:]==[SOURCES[5],relative(NATIVE/'native-fixtures.json')]
assert row('negative-controls')['args'][-4:]==[SOURCES[6],relative(NATIVE/'native-fixtures.json'),'--output',relative(REFERENCE/'controls')]
assert re.search(r'warning(?: C\d+|:)',stdout('build'),re.I) is None
assert '100% tests passed, 0 tests failed out of 42' in stdout('ctest')
ctest_names = re.findall(r'add_test\(NAME\s+(\S+)',(ROOT/'CMakeLists.txt').read_text())
observed = re.findall(r'^\s*(\d+)/42 Test\s+#(\d+): (\S+)\s+\.+\s+Passed\s+([\d.]+) sec\s*$',stdout('ctest'),re.M)
assert len(ctest_names)==len(observed)==42
assert [(int(a),int(b),name) for a,b,name,_ in observed]==[(i,i,name) for i,name in enumerate(ctest_names,1)]
native_seconds = float(re.search(r'Total Test time \(real\) = ([\d.]+) sec',stdout('ctest'))[1])
assert 0<native_seconds<=row('ctest')['wallSeconds']+1
excerpt_metadata = read(NATIVE/'native-preparation-test-excerpt.json')
excerpt = (NATIVE/'native-preparation-test-excerpt.txt').read_bytes()
assert remember(NATIVE/'native-preparation-test-excerpt.txt')=={'bytes':excerpt_metadata['excerptBytes'],'sha256':excerpt_metadata['excerptSha256']}
assert b'89 groups PASS; 84 finite fixtures' in excerpt and b'Test Passed.' in excerpt
assert b'no numeric guard, propagation, candidate or World advance' in excerpt
node_text = stdout('node')
for key,value in [('tests',684),('pass',684),('fail',0),('skipped',0),('cancelled',0)]:
    assert re.search(r'^(?:#|\u2139) '+key+r' '+str(value)+r'\s*$',node_text,re.M),key
assert stdout('web-build').strip()=='Web build cd45c7f1ac2ba5e5: 54 versioned modules; generated import maps'
assert len(re.findall(r'<script type="importmap" id="engine-imports">',(ROOT/'index.html').read_text()))==1

fixture_path = NATIVE/'native-fixtures.json'
assert remember(fixture_path)=={'bytes':221918,'sha256':'ba3eb26cb98642c29b4e8a3af587450fd7dfa87540cf403ee4447e2c2095c5ac'}
assert fixture_path.read_bytes()==(ROOT/row('fixtures')['stdout']).read_bytes()
spec = importlib.util.spec_from_file_location('preparation_aggregation_reference',ROOT/SOURCES[5])
reference = importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
fixture_data = reference.load(fixture_path)
independent = reference.verify(fixture_data)
assert independent==read(row('checker')['stdout'])==read(REFERENCE/'controls/reference.json')
for key,value in {'fixtures':84,'ready':24,'invalidInputs':55,'budgetExceeded':5,'uncaptured':6,
                  'completeCaptures':78,'requiredPairs':362,'excludedPairs':864,'allPairs':1226,
                  'maximumRequiredPairs':188,'maximumAllPairs':378,'vacuousReady':5,'mixedStaticReady':2,
                  'sourceNumericBits':7373,'sourceNegativeZeroBits':801}.items():
    assert independent[key]==value,(key,independent[key])
assert independent['inputFingerprint']=='4bfee81b01fcbfe5d7539c3960f35e467fa08db3d8bdfe5dc6badb9fc5853d4c'
assert Counter(f['result']['status'] for f in fixture_data['fixtures'])=={'ready':24,'invalid_input':55,'budget_exceeded':5}
controls = read(REFERENCE/'controls/negative-controls.json')
assert controls['status']=='PASS' and controls['selfTestGroups']==12 and controls['fixtures']==84
assert controls['baseline']==independent and controls['labelAndOrderIndependent'] is True
assert len(controls['rejectedControls'])==45 and all(r['rejected'] is True for r in controls['rejectedControls'])
assert len({r['name'] for r in controls['rejectedControls']})==45
assert read(row('negative-controls')['stdout'])=={'status':'PASS','selfTestGroups':12,'fixtures':84,'labelAndOrderIndependent':True,'rejectedControls':45}
optimized = read(REFERENCE/'controls/optimized-command.json')
assert type(optimized['exitCode']) is int and optimized['exitCode']!=0 and '-O' in optimized['command'] and SOURCES[5] in optimized['command'][-2].replace('\\','/')
assert 'without Python -O' in (REFERENCE/'controls/optimized.stderr.txt').read_text()
for proof in read(REFERENCE/'controls/provenance.json'):
    assert remember(proof['path'])==stamp(proof)
for path in (REFERENCE/'controls').iterdir():
    assert path.is_file();remember(path)

# Capacity observation is one MSVC target's sizeof*returned-capacity accounting.
storage = read(NATIVE/'native-storage.json')
assert (NATIVE/'native-storage.json').read_bytes()==(ROOT/row('storage')['stdout']).read_bytes()
observation = read(f'reports/{PREFIX}-storage-observation.json')
assert observation['schema']==1 and observation['status']=='OBSERVED'
assert observation['nativeStorage']=={'path':relative(NATIVE/'native-storage.json'),**remember(NATIVE/'native-storage.json')}
assert storage['schema']==1 and storage['kind']=='world-static-mesh-flight-preparation-storage'
assert storage['sizes']==observation['sizes'] and storage['capacities']==observation['capacities']
size,cap = storage['sizes'],storage['capacities']
assert cap=={'bodies':8,'planes':16,'meshes':4,'pairs':188,'triangles':[16,16,16,16]}
components = {'inlineResult':size['result'],'bodies':cap['bodies']*size['body'],
              'planes':cap['planes']*size['plane'],'meshOwnerHeaders':cap['meshes']*size['mesh'],
              'triangleBuffers':sum(cap['triangles'])*size['triangle'],'pairBuffer':cap['pairs']*size['pair']}
assert components==observation['observedReservedPayloadComponents']
assert sum(components.values())==observation['observedReservedPayloadBytes']==21880
assert 'set(CMAKE_CXX_COMPILER_ID "MSVC")' in observation['compiler']
assert 'set(CMAKE_CXX_COMPILER_VERSION "19.51.36247.0")' in observation['compiler']
assert 'set(CMAKE_CXX_COMPILER_ARCHITECTURE_ID "x64")' in observation['compiler']

# Preserve initial collection failures without upgrading them to successes.
initial = read(CHECKS/'run-20261104-native-001/commands.json')
assert [r['name'] for r in initial]==['configure','build','ctest']
for attempt in initial:
    assert attempt['sourceStable'] is True and attempt['sourceBefore']==attempt['sourceAfter']
    assert attempt['sourceAfter']==row('build')['sourceAfter']
    for stream in ['stdout','stderr']:
        assert remember(attempt[stream])==stamp(attempt[stream+'Hash'])
    if attempt['name']=='ctest':
        assert attempt['exit'] is None and attempt['timedOut'] is True and 120<=attempt['wallSeconds']<130
        old_ctest = (ROOT/attempt['stdout']).read_text()
        assert len(re.findall(r'\bPassed\s+[\d.]+ sec',old_ctest))==12 and 'Failed' not in old_ctest
    else:
        assert attempt['exit']==0 and attempt['timedOut'] is False
agent = ROOT/f'reports/{PREFIX}-agent-tests'
for directory in sorted(agent.glob('reference-run-*')):
    assert directory.is_dir()
    for p in directory.rglob('*'):
        if p.is_file():remember(p)
    if (directory/'archive-map.json').exists():
        archive = read(directory/'archive-map.json')
        for item in archive['files']:
            assert remember(item['archive'])==stamp(item)
agent_initial = read(agent/'reference-run-001/commands.json')
assert len(agent_initial)==1 and agent_initial[0]['exit']==1
assert agent_initial[0]['sourceBefore']==agent_initial[0]['sourceAfter']
assert '1 == 1' in (agent/'reference-run-001/stderr.txt').read_text()
assert 'test_original_ordinals_and_mesh_revision_survive_reordering' in (agent/'reference-run-001/stderr.txt').read_text()
freeze = read(agent/'reference-run-005/freeze.json')
assert freeze['status']=='FROZEN' and freeze['fixtureCount']==84 and freeze['selfTestGroups']==12 and freeze['rejectedControls']==45
for source in freeze['sources']:
    assert remember(source['path'])==stamp(source)
remember(f'reports/{PREFIX}-recipes/check.py')
remember(f'reports/{PREFIX}-recipes/reference-run.py')
remember(__file__)
assert len(evidence)<=2048 and sum(v['bytes'] for v in evidence.values())<=128*1024*1024
report = {'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'baseCommit':base['baseCommit'],
          'ctest':42,'nativePreparationGroups':89,'finiteFixtures':84,'node':684,'skipped':0,
          'independentReference':independent,'selfTestGroups':12,'negativeControls':45,
          'exports':92,'sourceHeaders':67,'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
          'artifacts':{p:remember(p) for p in ['assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json']},
          'protectedFilesUnchanged':355,'generatedEntriesUnchanged':26,'generatedEntries':generated,
          'webBuild':'cd45c7f1ac2ba5e5','modules':54,'entries':26,'newSources':source_hashes,'permittedOldChanges':old_changes,
          'commandFiles':command_files,'commands':commands,'nativeCtestSeconds':native_seconds,
          'nativePreparationExcerpt':excerpt_metadata,'storageObservation':observation,
          'historicalAttempts':{'native001':initial,'agentSelf001':agent_initial},
          'historicalScopes':{'native001':'Initial whole-CTest collection timed out after120s with12 passed and no failed test. Same product source hashes as final; final full42 completed separately.',
                              'agentSelf001':'Checker self-test initially expected a three-body reversal to move the central body ordinal1. Only that self-test reference was corrected; no product/kernel input or result was changed.'},
          'scope':'Native preparation and whole original-source inventory only. Every required typed pair and all six static-only classifications are reconstructed independently. Ready is not a contact/non-overlap/propagation/candidate/World-advance certificate.',
          'notMeasured':{'linuxSanitizer':'Not yet locally executed; CI declarations are not results.',
                         'allocationFaultInjection':'Not executed; natural finite84 capture cases do not prove allocation-exception branches.',
                         'ftzDazFaultInjection':'Not claimed. FE_UPWARD rejection preserves the requested rounding control and restores it; this is not preservation of all MXCSR bits or floating-point exception flags.',
                         'nativeNonfinite':'Five Native-only NaN/Inf checks classify invalid capture/input separately from the84 finite JSON fixtures; complete NaN payload-bit equality is not tested.',
                         'floatingPointPortability':'The84 current x64 finite inputs match the independent RN field-validation reference. Vec3::dot in core.cpp is outside the per-source strict CMake flags; no claim covers every FMA-permitting target/build.',
                         'staticClassification':'Pairs follow the original isStatic flag and existing World admission. Dot-product underflow can accept subnormal nonzero static V/L; excluded static-only pairs do not prove exact zero velocity, rest or non-overlap.',
                         'storage':'Observed sizeof*returned vector capacities on MSVC19.51.36247x64 only; no allocator overhead/temporary/stack/RSS/used-heap or portable16MiB guarantee.',
                         'diagramAndBrowser':'Excluded from this numerical/local aggregate; root records separate evidence.',
                         'numericalQueries':'No contact geometry, propagation or numerical certification is implemented by prepare.'},
          'evidence':evidence}
output = ROOT/f'reports/{PREFIX}-local-verification.json'
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:report[key] for key in ['status','ctest','nativePreparationGroups','finiteFixtures','node','skipped','negativeControls','protectedFilesUnchanged','generatedEntriesUnchanged','webBuild']}))
