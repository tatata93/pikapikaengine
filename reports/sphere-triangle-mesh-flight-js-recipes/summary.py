"""Recheck original owned-flight source, full captured commands and browser proof."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import subprocess
import struct
import sys

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-flight-js'
assert len(sys.argv) == 2, 'Usage: summary.py FINAL_CAPTURE_DIRECTORY'
FINAL = Path(sys.argv[1]).resolve()
assert FINAL.is_relative_to(ROOT) and FINAL.is_dir()
evidence = {}


def relative(path):
    value = Path(path)
    value = value if value.is_absolute() else ROOT / value
    value = value.resolve()
    assert value.is_relative_to(ROOT), value
    return value.relative_to(ROOT).as_posix()


def digest(path):
    raw = (ROOT / relative(path)).read_bytes()
    assert len(raw) <= 64 * 1024 * 1024
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def remember(path):
    key = relative(path);evidence[key] = digest(key)
    return evidence[key]


def read(path):
    remember(path)
    return json.loads((ROOT / relative(path)).read_text(encoding='utf-8-sig'))


def normalized(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                  re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', raw), flags=re.S).replace(b'\r\n', b'\n')


def git_blob(commit, path):
    assert re.fullmatch('[0-9a-f]{40}', commit)
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


base = read(f'reports/{PREFIX}-baseline.json')
assert len(base['protected']) == 345 and len(base['generatedEntries']) == 25
for path, expected in base['protected'].items():assert digest(path) == expected, path
for path, expected in base['generatedEntries'].items():
    raw = (ROOT / path).read_bytes()
    assert {'bytes': len(normalized(raw)), 'sha256': sha256(normalized(raw)).hexdigest()} == expected, path

# No old Runtime method body is replaced or reimplemented by this milestone.
runtime_path = 'engine/simulation.mjs';runtime = (ROOT / runtime_path).read_bytes()
fragments = [
    b"import {querySphereTriangleMeshHeldLoad,querySphereTriangleMeshFreeFlightGuard} from './sphere-triangle-mesh-flight.mjs';\n",
    b'  querySphereTriangleMeshHeldLoad(sphere,triangles,horizon,settings={}){\n    return querySphereTriangleMeshHeldLoad(this,sphere,triangles,horizon,settings,sphereTriangleMeshResult);\n  }\n',
    b'  querySphereTriangleMeshFreeFlightGuard(body,gravity,triangles,horizon,settings={}){\n    return querySphereTriangleMeshFreeFlightGuard(this,body,gravity,triangles,horizon,settings,sphereTriangleMeshResult);\n  }\n',
]
for fragment in fragments:
    assert runtime.count(fragment) == 1
    runtime = runtime.replace(fragment, b'', 1)
original_runtime = git_blob(base['baseCommit'], runtime_path)
assert runtime == original_runtime
assert {'bytes': len(original_runtime), 'sha256': sha256(original_runtime).hexdigest()} == base['originalRuntimeBlob']
new_sources = ['engine/simulation.mjs', 'engine/sphere-triangle-mesh-flight.mjs', 'tests/sphere-triangle-mesh-flight.test.mjs',
               'scripts/verify-sphere-triangle-mesh-flight-sdk.mjs', 'scripts/verify-sphere-triangle-mesh-flight-owned.py']
new_source_hashes = {p: remember(p) for p in new_sources}

manifest = read('assets/pikapika-simulation.build.json')
assert manifest == base['manifest'], 'SDK provenance/source/flags/artifact metadata changed'
assert len(manifest['sources']) == 32 and len(manifest['sourceSha256']) == 67
for path, expected in manifest['sourceSha256'].items():assert digest(path)['sha256'] == expected, path
assert len(manifest['linkedLibraryMembers']) == 91 and len(manifest['licenses']) == 7
for path, expected in manifest['licenses'].items():assert digest(path)['sha256'] == expected, path
exports = json.loads(next(f.split('=', 1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 92
artifacts = {p: remember(p) for p in ['assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json']}
for path, expected in manifest['artifacts'].items():assert artifacts[path] == expected
assert artifacts['assets/pikapika-simulation.wasm']['bytes'] == 800982
assert artifacts['assets/pikapika-simulation.mjs']['bytes'] == 61661

budget_path=f'reports/{PREFIX}-recipes/ci-budget-transition.json'
budget=read(budget_path)
assert budget['schema']==1 and budget['workflow']=='.github/workflows/verify.yml'
assert budget['beforeFile']==f'reports/{PREFIX}-recipes/workflow-before-budget.yml'
assert remember(budget['beforeFile'])==budget['before'] and remember(budget['workflow'])==budget['after']
old_workflow=(ROOT/budget['beforeFile']).read_bytes();current_workflow=(ROOT/budget['workflow']).read_bytes()
old_budget=b'timeout-minutes: 15';new_budget=b'timeout-minutes: 20'
assert old_workflow.count(old_budget)==1 and current_workflow==old_workflow.replace(old_budget,new_budget,1)
commands = [];command_files = {};budget_command_names=[]
for phase in ['focused', 'owned', 'regressions']:
    path = FINAL / (phase + '-commands.json');rows = read(path);command_files[relative(path)] = digest(path)
    assert rows and all(r['exit'] == 0 and r['authoredStable'] is True and r['authoredBefore'] == r['authoredAfter'] for r in rows), phase
    for row in rows:
        for path, expected in row['authoredAfter'].items():
            if path==budget['workflow']:
                assert expected==budget['before'] and digest(path)==budget['after']
                budget_command_names.append(row['name'])
            else:assert digest(path) == expected, path
        for stream in ['stdout', 'stderr']:assert remember(row[stream]) == row[stream + 'Hash']
    commands.extend(rows)


def stdout(name):
    matches = [r for r in commands if r['name'] == name]
    assert len(matches) == 1, name
    return (ROOT / matches[0]['stdout']).read_text(encoding='utf-8-sig')


def node_counts(text):
    result = {}
    for key in ['tests', 'pass', 'fail', 'skipped']:
        rows = re.findall(r'(?:ℹ\s+|#\s+)' + key + r'\s+(\d+)\b', text)
        assert len(rows) == 1, (key, rows)
        result[key] = int(rows[0])
    assert result['tests'] == result['pass'] and result['fail'] == result['skipped'] == 0
    return result


focused = node_counts(stdout('focused'));node = node_counts(stdout('node'))
assert focused['tests'] >= 30
prior = read('reports/sphere-triangle-mesh-flight-sdk-local-verification.json')
assert prior['status'] == 'PASS' and node['tests'] == prior['node'] + focused['tests']
ctest_matches = re.findall(r'100% tests passed, 0 tests failed out of (\d+)', stdout('ctest'))
assert len(ctest_matches) == 1 and int(ctest_matches[0]) == prior['ctest'] == 41
build_matches = re.findall(r'([0-9a-f]{16}): (\d+) versioned modules', stdout('web-build'))
assert len(build_matches) == 1
build_id, modules = build_matches[0]
assert int(modules) == 52 and 'generated import maps' in stdout('web-build')
assert re.search(rb'\?build=' + build_id.encode(), (ROOT/'index.html').read_bytes())

owned = read(FINAL/'owned/report.json')
assert owned == json.loads(stdout('owned')) and owned['status'] == 'PASS'
assert (owned['fixtures'],owned['actualModels'],owned['hostRejected']) == (183,173,10)
assert [(owned['cohorts'][c]['models'],owned['cohorts'][c]['hostRejected']) for c in ['held','guard','supplemental']] == [(74,5),(95,5),(4,0)]
assert owned['sourceStable'] is True and owned['sourcesBefore'] == owned['sourcesAfter']
for path, expected in owned['sourcesAfter'].items():assert digest(ROOT/'scripts'/path) == expected, path
assert owned['wasm'] == artifacts['assets/pikapika-simulation.wasm']
assert owned['originalExportsAndPrototypesUnchanged'] is True and owned['oldEntryAndWorldUnchanged'] is True
assert owned['ownership']['corpusDtosRetained'] == 173 and owned['ownership']['extraCalls'] >= 4
assert owned['maximums'] == {'sources':64,'audits':256,'leaves':128,'partition':128,'frontier':127,'candidateIds':64,'lastMeshRows':64,'lastMeshCandidates':448}
for path, expected in owned['files'].items():assert remember(FINAL/'owned'/path) == expected
reference = read(FINAL/'owned/independent/report.json')
assert reference == owned['reference'] and reference['status'] == 'PASS'
assert (reference['fixtures'],reference['actualModels'],reference['hostRejected']) == (183,173,10)
assert reference['acceptedInputFingerprint'] == '684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb'
assert reference['optimizedPythonRejected'] is True
for c,n in [('held',74),('guard',95),('supplemental',4)]:
    assert reference['cohorts'][c]['models'] == reference['cohorts'][c]['mathematicsFixturesVerified'] == n
assert owned['counters']['model']['numeric'] == reference['modelNumericBits'] > 0
assert owned['counters']['model']['negativeZero'] == reference['modelNegativeZeroBits'] > 0
native_source=ROOT/'reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-final-002/native-exchange/packets.json'
assert remember(native_source)==owned['nativePackets']==prior['nativeExchange']['files']['packets.json']
# Preserve a JSON integer token -0 as negative zero when checking raw bit tokens.
native=json.loads(native_source.read_text(encoding='utf-8'),parse_int=lambda text:-0.0 if text=='-0' else int(text))
echo_counts={'numeric':0,'negativeZero':0};getter_counts={'numeric':0,'negativeZero':0}
def count_raw(values,bits,counter):
    assert len(values)==len(bits)
    for value,token in zip(values,bits):
        assert type(value) in (int,float) and struct.pack('>d',value).hex()==token
        counter['numeric']+=1;counter['negativeZero']+=int(token=='8000000000000000')
assert len(native['fixtures'])==183
for row in native['fixtures']:
    count_raw(row['input'],row['inputBits'],echo_counts)
    if row['exchangeStatus']!=0:continue
    for packet in row['packets']:count_raw(packet['values'],packet['bits'],getter_counts)
    if row['lastMeshSummary'] is not None:count_raw(row['lastMeshSummary'],row['lastMeshSummaryBits'],getter_counts)
    for mesh_row in row['lastMeshRows']:
        if mesh_row['packet'] is not None:count_raw(mesh_row['packet'],mesh_row['bits'],getter_counts)
        for values,bits in zip(mesh_row['candidates'],mesh_row['candidateBits'],strict=True):count_raw(values,bits,getter_counts)
assert echo_counts=={'numeric':7520,'negativeZero':12}
assert owned['counters']['originalInput']['numeric']==reference['originalInputNumericBits']+echo_counts['numeric']
assert owned['counters']['originalInput']['negativeZero']==reference['originalInputNegativeZeroBits']+echo_counts['negativeZero']
assert owned['counters']['rawGetters']==getter_counts
controls = read(FINAL/'owned/independent/negative-controls.json')
assert controls == reference['negativeControls'] and controls['status']=='PASS' and controls['count']==len(controls['rejectedControls'])==15
assert all(row['rejected'] is True for row in controls['rejectedControls'])
assert read(FINAL/'owned/independent/optimized-command.json')['exitCode'] != 0
for cohort,n in [('held',79),('guard',100),('supplemental',4)]:
    assert reference['pureNativeReference'][cohort]['status']=='PASS' and reference['pureNativeReference'][cohort]['fixtures']==n
for path in (FINAL/'owned/independent').glob('*'):
    if path.is_file():remember(path)
assert owned['memory']['usedHeapBytes'] is None and owned['memory']['stackHighWaterBytes'] is None

# Summary24 was consumed by the public owned method. Getter replay must not
# manufacture it from Native, replace exports, or issue a hidden second query.
getter_packets = read(FINAL/'owned/actual-getter-packets.json')
assert len(getter_packets['fixtures']) == 173
assert all(row['summary'] is None and row['summaryUnavailable'] and row['packets'] for row in getter_packets['fixtures'])
hosts = read(FINAL/'owned/host-rejections.json');assert len(hosts['fixtures']) == 10
dtos = read(FINAL/'owned/wasm-owned-dtos.json')
assert len(dtos['fixtures']) == 183 and sum(row['result'] is None for row in dtos['fixtures']) == 10

before = ROOT/'reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-before'
assert remember(FINAL/'legacy-native.json') == remember(before/'legacy-native-before.json')
legacy = read(FINAL/'legacy-wasm/report.json')
assert legacy['status']=='PASS' and legacy['comparedToBaseline'] is True
assert tuple(legacy[k] for k in ['fixtures','completed','modelRejected','hostRejected','numericBits','negativeZeroBits']) == (20,14,5,1,4520,24)
assert remember(FINAL/'legacy-wasm/results.json') == remember(before/'legacy-wasm-before/results.json')
old_entry = read(FINAL/'old-entry-owned/report.json')
assert old_entry['status']=='PASS' and tuple(old_entry[k] for k in ['actualModelFixtures','hostRejected','modelNumericComparisons','modelNegativeZeroComparisons','originalInputNumericComparisons','originalInputNegativeZeroComparisons']) == (62,3,105056,3239,4728,108)
assert old_entry['negativeControls']['rejectedControls']==90
for path,value in old_entry['files'].items():assert remember(FINAL/'old-entry-owned'/path)==value

browser_dir=ROOT/f'reports/{PREFIX}-browser'
browser=read(browser_dir/'browser-verification.json')
assert browser['status']=='PASS' and browser['buildId']==build_id and browser['wasmBytes']==artifacts['assets/pikapika-simulation.wasm']['bytes']
browser_names={'local-diagram.jpg','local-api.jpg','local-api-result.json','local-api-ax.txt','local-game.jpg','local-game-ax.txt','local-game-cover-report.json'}
assert set(browser['evidence'])==browser_names
for name,value in browser['evidence'].items():assert remember(browser_dir/name)==value
game=read(browser_dir/'local-game-cover-report.json');game_state=(browser_dir/'local-game-ax.txt').read_text(encoding='utf-8-sig')
assert game['state']=='ready' and game['failure'] is None and game['pending'] is None and game['errors']==[]
assert '一時停止 / Pで再開' in game_state
kills=int(re.search(r'撃破 (\d+)',game_state).group(1));queries=game['counts']['queries']
assert kills>0 and type(queries) is int and queries>0 and queries==game['counts']['checked']==game['counts']['validated']==len(game['records'])
assert all(row['state']=='completed' for row in game['records']) and any(row['clipSeconds']==1 for row in game['records'])
assert game['renderer']['residentMeshes']==3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId']==build_id and game['startup']['diagnostics']['wasmBytes']==800982

# Preserve unsuccessful/superseded captures as history, never current proof.
historical={}
checks=ROOT/f'reports/{PREFIX}-checks'
for directory in sorted(checks.iterdir()):
    if not directory.is_dir() or directory.resolve()==FINAL:continue
    for path in directory.rglob('*'):
        if path.is_file() and (path.name.endswith('-commands.json') or path.name in ['failure.json','source-before.json','failure-source-after.json'] or path.name.endswith('.stdout.txt') or path.name.endswith('.stderr.txt')):
            historical[relative(path)]=remember(path)
development=ROOT/'reports/sphere-triangle-mesh-flight-js-test-development'
if development.exists():
    for path in development.rglob('*'):
        if path.is_file():historical[relative(path)]=remember(path)
extra_histories={
    f'reports/{PREFIX}-agent-tests':'Initial actual owned replay failed in reference provenance serialization (str passed to file_info expecting Path). Original captured DTO/getters/source/child error remain history; no successful reference or current-source acceptance is inferred.',
    f'reports/{PREFIX}-reference-attempts':'Six successful synthetic projection/fidelity/reference self-tests. These are separate from actual WASM173-model/10-host evidence and do not replace the canonical replay.'}
for directory in extra_histories:
    assert (ROOT/directory).is_dir()
    for path in (ROOT/directory).rglob('*'):
        if path.is_file():historical[relative(path)]=remember(path)
assert read(f'reports/{PREFIX}-agent-tests/run-001/command.json')['exitCode']==1
assert read(f'reports/{PREFIX}-reference-attempts/run-001/command.json')['exitCode']==0
synthetic_stderr=(ROOT/f'reports/{PREFIX}-reference-attempts/run-001/stderr.txt').read_text(encoding='utf-8-sig')
assert re.search(r'Ran 6 tests\b',synthetic_stderr) and re.search(r'\bOK\s*$',synthetic_stderr)
assert len(evidence)<=2048 and sum(v['bytes'] for v in evidence.values())<=256*1024*1024
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'baseCommit':base['baseCommit'],'canonicalDirectory':relative(FINAL),
    'protectedFilesUnchanged':345,'normalizedGeneratedEntries':25,'focused':focused['tests'],'node':node['tests'],'skipped':0,'ctest':41,
    'exports':92,'sourceHeaders':67,'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNoticesUnchanged':7,
    'artifacts':artifacts,'sdkProvenanceUnchanged':True,'onlyNewRuntimeImportAndTwoMethods':True,'newSources':new_source_hashes,
    'modules':int(modules),'entries':25,'webBuild':build_id,'owned':owned,'reference':reference,'negativeControls':controls,
    'all183OriginalEchoComparisons':echo_counts,'actual173OwnedOriginalInputComparisons':{'numeric':reference['originalInputNumericBits'],'negativeZero':reference['originalInputNegativeZeroBits']},
    'actualPostReturnGetterComparisons':getter_counts,
    'mathematicsFixturesVerified':{'held':74,'guard':95,'supplemental':4,'total':173},'legacyW1':legacy,'oldEntryOwned':old_entry,
    'browser':browser,'game':{'kills':kills,'paused':True,'queries':queries,'boostClip1Observed':True,'residentMeshes':3},
    'commands':commands,'commandFiles':command_files,'historicalAttempts':historical,
    'historicalAttemptScopes':extra_histories,
    'ciExecutionBudgetTransition':{'record':budget,'commandsCapturedBeforeBudgetChange':budget_command_names,
        'scope':'Only the CI timeout15-to20-minute budget changed after stable local commands. Original workflow source hashes stay in those captures; the complete saved old workflow and exact one-occurrence replacement are audited. All code/test/SDK hashes remain current, without other exceptions. No local execution of the new workflow is claimed; its execution is a separate public-CI acceptance.'},
    'scope':'Current frozen public owned methods restore173 actual model DTOs and explicitly refuse10 host rows, without supplementing hosts. All available post-return getters are compared; summary24 is explicitly unavailable in this replay and is covered separately by raw ABI proof and synthetic decoder controls. Only actual173 decoded owned models enter independent Fraction calls. Synthetic fault/growth tests are metadata/ownership tests, not actual Native allocator/fenv or WASM usedheap/stack measurements. SDK, Native kernels, old wrapper/game sources remain exact; World contact response/UI/repeated-step guarantees are not inferred.',
    'evidence':evidence}
target=ROOT/f'reports/{PREFIX}-local-verification.json'
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','focused','node','ctest','exports','sourceHeaders','webBuild','mathematicsFixturesVerified']}))
