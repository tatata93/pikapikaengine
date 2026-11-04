"""Verify the local coverage evidence; public CI/sanitizer acceptance is separate."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
import argparse
import ast
import importlib.util
import json
import math
import re
import subprocess
import sys

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'accelerated-sphere-box-coverage'
CHECKS = ROOT/f'reports/{PREFIX}-checks'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory')
args = parser.parse_args()
OUT = (ROOT/args.directory).resolve()
assert OUT.is_dir() and OUT.is_relative_to(CHECKS.resolve())
NATIVE = CHECKS/'run-20261104-native-001'
REGRESSIONS = CHECKS/'run-20261104-regressions-001'
REFERENCE = CHECKS/'run-20261104-reference-001'
SOURCES = ['core/include/pikapika/accelerated_sphere_box_coverage.hpp',
           'core/src/accelerated_sphere_box_coverage.cpp',
           'tests/accelerated_sphere_box_coverage_tests.cpp',
           'tests/accelerated_sphere_box_coverage_fixtures.cpp',
           'tests/accelerated_sphere_box_coverage_test_support.hpp',
           'scripts/verify-accelerated-sphere-box-coverage.py',
           'tests/accelerated_sphere_box_coverage_reference_tests.py']
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
assert base['schema']==1 and base['baseCommit']=='2901905b56c984f1b0a946684143d64394eda6c4'
assert base['priorPublicReceipt']=='reports/accelerated-plane-box-coverage-public-verification.json'
prior_public=load(base['priorPublicReceipt']);assert prior_public['status']=='PASS' and prior_public['commit']=='4b5bf37e5f501088647d735dd45a86ed27d30e5b'
assert len(base['protected'])==376 and len(base['generatedEntries'])==26
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

# Remove exact declared additions and reconstruct the final accepted baseline.
integration_literals={}
for node in ast.parse((ROOT/f'reports/{PREFIX}-recipes/integrate.py').read_text(encoding='utf8')).body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'CMAKE_SOURCE','CMAKE_TEST','CI_STAGE','ATTR_LINES'}:
        integration_literals[node.targets[0].id]=ast.literal_eval(node.value)
assert set(integration_literals)=={'CMAKE_SOURCE','CMAKE_TEST','CI_STAGE','ATTR_LINES'}
CMAKE_LIBRARY=integration_literals['CMAKE_SOURCE'];CMAKE_TEST=integration_literals['CMAKE_TEST']
CI_AUDIT=integration_literals['CI_STAGE'];ATTRS=integration_literals['ATTR_LINES']
assert (len(CMAKE_LIBRARY.splitlines()),len(CMAKE_TEST.splitlines()),len(CI_AUDIT.splitlines()),len(ATTRS.splitlines()))==(6,8,13,2)
assert CMAKE_LIBRARY.startswith('target_sources(pikapika_core PRIVATE core/include/pikapika/accelerated_sphere_box_coverage.hpp core/src/accelerated_sphere_box_coverage.cpp)\n')
assert 'PROPERTIES COMPILE_OPTIONS "/fp:strict"' in CMAKE_LIBRARY
assert 'PROPERTIES COMPILE_OPTIONS "-fno-fast-math;-ffp-contract=off;-frounding-math"' in CMAKE_LIBRARY
assert 'PRIVATE /W4 /permissive- /fp:strict' in CMAKE_TEST
assert 'PRIVATE -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -frounding-math' in CMAKE_TEST
assert CI_AUDIT.startswith('      - name: Audit two-declared-error sphere box coverage independently\n')
assert 'core/src/interval.cpp core/src/accelerated.cpp core/src/accelerated_sphere_box_coverage.cpp tests/accelerated_sphere_box_coverage_tests.cpp tests/accelerated_sphere_box_coverage_fixtures.cpp' in CI_AUDIT
old_changes = {}
for path,fragments in [('CMakeLists.txt',[CMAKE_LIBRARY,CMAKE_TEST]),
                       ('.github/workflows/verify.yml',[CI_AUDIT]),('.gitattributes',[ATTRS])]:
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
assert [old_changes[p]['insertedLines'] for p in INTEGRATION]==[14,13,2]

# The standalone lesson is outside the26 versioned HTML entry points. Remove
# the ONE literal original addition, including its already-present deep link.
lesson_path = 'docs/learn/index.html'
lesson_old = git_blobs(base['baseCommit'],[lesson_path])[lesson_path]
lesson_raw = (ROOT/lesson_path).read_bytes()
lesson_literals={}
for node in ast.parse((ROOT/f'reports/{PREFIX}-recipes/integrate-lesson.py').read_text(encoding='utf8')).body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='added':lesson_literals['added']=ast.literal_eval(node.value)
assert set(lesson_literals)=={'added'}
lesson_added = lesson_literals['added'].encode()
assert lesson_added.startswith(b'<figure id="sphere-box-coverage">')
assert lesson_raw.count(lesson_added)==1
lesson_reconstructed = lesson_raw.replace(lesson_added,b'',1)
lesson_normalization = None
if lesson_reconstructed!=lesson_old:
    assert b'\r\n' in lesson_reconstructed and lesson_reconstructed.replace(b'\r\n',b'\n')==lesson_old
    lesson_normalization='Declared text CRLF-to-LF only.'
lesson_change={'path':lesson_path,'raw':remember(lesson_path),'baseGitBlob':info(lesson_old),
               'addedLiteral':info(lesson_added),'normalization':lesson_normalization,
               'scope':'One original figure/paragraph appended within the existing article; all prior lesson bytes preserved after declared text normalization. This file is outside the26 unchanged generated entries.'}
remember(f'reports/{PREFIX}-recipes/integrate.py');remember(f'reports/{PREFIX}-recipes/integrate-lesson.py')

manifest = load('assets/pikapika-simulation.build.json')
assert manifest==base['sdkManifest']
assert (len(manifest['sources']),len(manifest['sourceSha256']),len(manifest['linkedLibraryMembers']),len(manifest['licenses']))==(32,67,91,7)
exports = json.loads(next(f.split('=',1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports)==len(set(exports))==92
assert not any('accelerated_sphere_box_coverage' in p for p in manifest['sourceSha256'])
for path,value in [*manifest['sourceSha256'].items(),*manifest['licenses'].items()]:
    assert remember(path)['sha256']==value, path
for path,value in manifest['artifacts'].items():
    assert remember(path)==stamp(value), path

source_hashes = {p:remember(p) for p in SOURCES}
assert source_hashes==base['newSources'],'All seven authored sources unchanged from accepted baseline capture'
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
binary = ROOT/'build/native/Release/pikapika_accelerated_sphere_box_coverage_tests.exe'
for name,tail in [('dedicated',[]),('fixtures',['--fixtures']),('storage',['--storage'])]:
    assert Path(command(name)['args'][0]).resolve()==binary and command(name)['args'][1:]==tail
assert command('ctest')['args'][1:]==['--test-dir','build/native','-C','Release','--output-on-failure']
assert command('ctest')['timeoutSeconds']==300
assert '84 groups PASS; 75 finite fixtures; 955 full Evaluation exact-bit replays / 28650 endpoint comparisons / 6371 negative-zero endpoints / 1910 root diagnostic comparisons' in stdout('dedicated')
assert re.search(r'warning(?: C\d+|:)', stdout('build'),re.I) is None
assert '100% tests passed, 0 tests failed out of 45' in stdout('ctest')
names = re.findall(r'add_test\(NAME\s+(\S+)',(ROOT/'CMakeLists.txt').read_text())
observed = re.findall(r'^\s*(\d+)/45 Test\s+#(\d+): (\S+)\s+\.+\s+Passed\s+([\d.]+) sec\s*$',stdout('ctest'),re.M)
assert len(names)==len(observed)==45
assert [(int(a),int(b),n) for a,b,n,_ in observed]==[(i,i,n) for i,n in enumerate(names,1)]
native_seconds = float(re.search(r'Total Test time \(real\) = ([\d.]+) sec',stdout('ctest'))[1])
assert 0<native_seconds<=command('ctest')['wallSeconds']+1
lasttest = (NATIVE/'LastTest.txt').read_bytes(); remember(NATIVE/'LastTest.txt')
assert b'84 groups PASS; 75 finite fixtures; 955 full Evaluation exact-bit replays / 28650 endpoint comparisons / 6371 negative-zero endpoints / 1910 root diagnostic comparisons' in lasttest

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
assert fixtures['schema']==1 and fixtures['kind']=='accelerated-sphere-box-coverage-fixtures' and len(fixtures['fixtures'])==75
assert Counter(f['result']['status'] for f in fixtures['fixtures'])=={'certified':20,'not_certified':21,'invalid_input':34}
assert sum(len(f['result']['audits']) for f in fixtures['fixtures'])==955
assert sum(f['result']['work']['valueCallsAttempted'] for f in fixtures['fixtures'])==955
assert sum(f['result']['work']['valueCallsReturned'] for f in fixtures['fixtures'])==955

# Use the independent checker itself; this is a mathematical acceptance distinct
# from Native direct-public-value exact-bit replays, not a translated value graph.
spec = importlib.util.spec_from_file_location('coverage_aggregation_reference',ROOT/SOURCES[5])
reference = importlib.util.module_from_spec(spec); sys.modules[spec.name]=reference; spec.loader.exec_module(reference)
independent = reference.verify(reference.load(fixture_path))
assert independent == load(command('checker')['stdout'])
for key,value in {'fixtures':75,'certified':20,'notCertified':21,'invalidInputs':34,
                  'cellAudits':955,'partitionLeaves':583,'frontierCells':163,'currentCells':7,
                  'returnedEvaluations':955,'returnedIntervals':14325,'coordinateRangeProofs':5730,
                  'deltaSquareProofs':955,'rootSquareProofs':955,'sqrtRefinementsReturned':96929,
                  'sqrtLimitedReturns':1,'limitedPositiveEvaluations':1,'maximumAudits':255,
                  'maximumPartition':128,'maximumFrontier':127,'subdividedCertified':1}.items():
    assert independent[key]==value,(key,independent[key])
assert independent['inputFingerprint']=='f4f2b48cb4834d95916b5b1a4e9711c27166b65bbc987454af111212416fefbb'
assert all(f['result']['work']['exact'] is True for f in fixtures['fixtures'])
assert sum(f['result']['work']['sqrtRefinementsReturned'] for f in fixtures['fixtures'])==96929
assert all(f['result']['work']['sqrtRefinementsUpper']==f['result']['work']['sqrtRefinementsReturned'] for f in fixtures['fixtures'])
assert all(f['result']['work']['sqrtResultsReturned']==f['result']['work']['valueCallsReturned'] for f in fixtures['fixtures'])
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
assert controls['selfTestGroups']==controls_stdout['selfTestGroups']==16
assert controls_stdout['rejectedControls']==89
assert controls['positiveControls']['mathematicallyValidWiderRootAccepted'] is True
assert controls['positiveControls']['syntheticNonreturnedValueReservationAccepted'] is True
assert controls['positiveControls']['limitedValidRootSelfTestAccepted'] is True
assert len(controls['rejectedControls'])==controls_stdout['rejectedControls']
assert all(c['rejected'] is True for c in controls['rejectedControls'])
assert len({c['name'] for c in controls['rejectedControls']})==len(controls['rejectedControls'])
optimized = load(REFERENCE/'controls/optimized-command.json')
assert type(optimized['exitCode']) is int and optimized['exitCode']!=0 and '-O' in optimized['command']
for proof in load(REFERENCE/'controls/provenance.json'):
    assert remember(proof['path'])==stamp(proof)

storage = load(NATIVE/'native-storage.json')
assert (NATIVE/'native-storage.json').read_bytes()==(ROOT/command('storage')['stdout']).read_bytes()
assert storage['schema']==1 and storage['kind']=='accelerated-sphere-box-coverage-storage'
sizes,caps = storage['sizes'],storage['capacities']
assert caps=={'audits':255,'partition':128,'frontier':128}
assert all(type(v) is int and v>0 for v in sizes.values())
components = {'inlineResult':sizes['result'],'auditBuffer':caps['audits']*sizes['audit'],
              'partitionBuffer':caps['partition']*sizes['partitionLeaf'],
              'frontierBuffer':caps['frontier']*sizes['cell']}

assert sum(components.values())==98456 and sizes['result']==480
assert sum(v for k,v in components.items() if k!='inlineResult')==97976

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
standalone_dir=ROOT/f'reports/{PREFIX}-native-development/run-001'
standalone = load(standalone_dir/'commands.json')

def standalone_stream(row,stream):
    # These source-owned standalone records deliberately use run-local names.
    name=Path(row[stream]);assert not name.is_absolute() and len(name.parts)==1
    path=(standalone_dir/name).resolve();assert path.parent==standalone_dir.resolve()
    assert remember(path)==stamp(row[stream+'Hash'])
    return path

assert [r['name'] for r in standalone]==['compile','native-tests','native-fixtures','storage']
for r in standalone:
    for stream in ['stdout','stderr']:standalone_stream(r,stream)
    assert r['exit']==0 and r['sourceStable'] is True and r['sourceBefore']==r['sourceAfter']
    for p,value in r['sourceAfter'].items():
        assert remember(p)==stamp(value), p
assert fixture_path.read_bytes()==(ROOT/f'reports/{PREFIX}-native-development/run-001/native-fixtures.json').read_bytes()
assert remember(fixture_path)=={'bytes':894178,'sha256':'83a2402cd2a86491f325b1f2345c48218b364f4d372dde405afdfc87f2cc2174'}
assert b'84 groups PASS; 75 finite fixtures; 955 full Evaluation exact-bit replays / 28650 endpoint comparisons / 6371 negative-zero endpoints / 1910 root diagnostic comparisons' in standalone_stream(standalone[1],'stdout').read_bytes()
browser_dir=ROOT/f'reports/{PREFIX}-local-browser'
browser_observations=load(browser_dir/'observations.json')
assert browser_observations['schema']==1
assert browser_observations['scope']=='Native-only conditional sphere-box helper: local diagram and lesson display; no browser numerical query or actual World certification.'
assert set(browser_observations['files'])=={'diagram-ax.txt','diagram.jpg','lesson-article.txt','lesson-ax.txt','lesson.jpg'}
assert len(browser_observations['files'])==5
browser_files={relative(browser_dir/'observations.json'):remember(browser_dir/'observations.json')}
for name in browser_observations['files']:
    path=browser_dir/name;assert path.is_file() and path.parent.resolve()==browser_dir.resolve()
    browser_files[relative(path)]=remember(path);assert browser_files[relative(path)]['bytes']>0
assert set(browser_observations['sourceHashes'])=={'docs/learn/index.html','docs/learn/diagrams/accelerated-sphere-box-coverage.svg','docs/ACCELERATED_SPHERE_BOX_COVERAGE.md'}
for path,value in browser_observations['sourceHashes'].items():
    assert remember(path)==stamp(value),path
assert browser_observations['lessonImage']['complete'] is True
assert (browser_observations['lessonImage']['width'],browser_observations['lessonImage']['height'])==(1120,760)
assert browser_observations['lessonImage']['src']=='diagrams/accelerated-sphere-box-coverage.svg'
assert browser_observations['lessonGuideHref']=='../ACCELERATED_SPHERE_BOX_COVERAGE.md'
article_html=(ROOT/'docs/learn/index.html').read_text(encoding='utf8')
articles=[m for m in re.finditer(r'<article\b[^>]*>.*?</article>',article_html,re.S) if 'accelerated-sphere-box-coverage.svg' in m[0]]
assert len(articles)==1
from html.parser import HTMLParser
class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[]
    def handle_data(self,data):self.parts.append(data)
parser=VisibleText();parser.feed(articles[0][0]);parser.close()
article_text=(browser_dir/'lesson-article.txt').read_text(encoding='utf-8-sig')
assert re.sub(r'\s+','',article_text)==re.sub(r'\s+','',''.join(parser.parts))
local_browser={'observations':browser_observations,'evidence':browser_files,'capturedDisplayFiles':5,
               'recordCountIncludingObservations':6,'scope':'Local diagram/lesson display observations only; no browser box query or World certification. Screenshot readability is reviewed separately by the parent.'}

for path in [f'reports/{PREFIX}-recipes/check.py', f'reports/{PREFIX}-recipes/summary-run.py',__file__]:
    remember(path)
assert len(evidence)<=4096 and sum(x['bytes'] for x in evidence.values())<=128*1024*1024
report = {'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),
          'baseCommit':base['baseCommit'],'ctest':45,'nativeGroups':84,'finiteFixtures':75,
          'nativePublicValueFullEvaluationReplays':955,'nativeEndpointBitComparisons':28650,'nativeNegativeZeroEndpoints':6371,'nativeRootDiagnosticComparisons':1910,'node':684,'skipped':0,
          'independentReference':independent,'independentReferenceScope':{'coordinateProof':'Exact Fraction quadratic extrema plus each declared B for six coordinates; no independent enumeration of the coordinate-construction I-AST RN family.','downstreamProof':'From recorded coordinate boxes: delta/square/left-associated sum/threshold/gap exact-or-integer-RN bounds, full root square inequalities and representable-endpoint RN inclusion.','nativeProvenance':'All15 returned I, including root.value/distance copy and both root metadata fields, are separate direct public-value bit replays.'},
          'rootWork':{'returnedResults':955,'returnedRefinements':96929,'limitedResults':1,'limitedPositiveEvaluations':1,'allNaturalWorkExact':True,'sumUpper':96929,'privateRootAttemptCount':None},'selfTestGroups':controls['selfTestGroups'],
          'negativeControls':len(controls['rejectedControls']),'positiveControls':controls['positiveControls'],'exports':92,'sourceHeaders':67,
          'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
          'artifacts':{p:remember(p) for p in manifest['artifacts']},
          'protectedFilesUnchanged':376,'generatedEntriesUnchanged':26,'generatedEntries':generated,
          'newSources':source_hashes,'permittedOldChanges':old_changes,'lessonChange':lesson_change,'webBuild':web[1],'modules':54,
          'commandFiles':command_files,'commands':commands,'nativeCtestSeconds':native_seconds,
          'localBrowser':local_browser,'storageObservation':{'sizes':sizes,'capacities':caps,'sizeofCapacityComponents':components,
                                'sizeofCapacityBytes':sum(components.values()),'scope':storage['scope']},
          'historicalAttempts':history,'collectionNotes':collection_notes,
          'scope':'Native conditional two-declared-B/margin sphere-box coverage. Independent six-coordinate proofs enclose exact quadratic extrema plus each B; integer-RN choices apply from recorded coordinate boxes through delta/square/left-sum/threshold/gap, with root square inequalities and RN representable-endpoint lemma. Coordinate construction AST provenance and all15 returned intervals/root metadata are separately checked by Native public-value replay. No actual B derivation, external std::sqrt/compiler binding, World propagation, entry, response or state mutation.',
          'notMeasured':{'publicLinuxCI':'Not part of this local aggregate; declarations are not completed runs.',
                         'allocationAndValueFaults':'No natural allocator/value-throw injection performed.',
                         'negativeZeroIntervals':'6371 negative-zero endpoints were observed in28650 endpoint comparisons; source/snapshot signed-zero is separately preserved.',
                         'storage':'sizeof*returned capacity only; no allocator overhead/temporary/stack/RSS/used-heap guarantee. Original standalone logical payload97976B excludes inline Result480B; corrected aggregate total98456B includes it exactly once. Snapshot is already inline and is not added twice.',
                         'rootWork':'Returned complete Evaluation roots expose counts/limited flags. Wrapper attempts/returns remain exact; unknown value block retains2*sqrtRefinements upper with exact=false. Actual private root attempts on throw are not observed. All actual finite75 returns were exact; artificial unknown packets are not fault injection.',
                         'mathematicalProvenance':'Exact coordinate quadratic extrema plus B do not enumerate coordinate-construction AST rounding choices. Recorded-box downstream exact/integer-RN families and full sqrt containment are independent math; mathematically valid wider root/records are not rejected as false provenance. Native all15I/root metadata direct-value replay is a separate bit gate. Correct external std::sqrt binding remains unverified.',
                         'floatingEnvironment':'Requested rounding-control and FTZ/DAZ refusal/recovery tests are bounded target probes, not all-target compiler verification or preservation of every exception flag.',
                         'wholeWorld':'No all-body/pair World certification, candidate publication, response, CCD or tolerance-based contact acceptance.'},
          'evidence':evidence}
output = OUT/'acceptance.json'
assert not output.exists()
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:report[k] for k in ['status','ctest','nativeGroups','finiteFixtures','nativePublicValueFullEvaluationReplays','node','skipped','selfTestGroups','negativeControls','protectedFilesUnchanged','generatedEntriesUnchanged','webBuild']}))
