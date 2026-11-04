"""Accept captured Native guard, exact feature bytes, CI and public browser proof."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, unquote, urlsplit
import json
import re
import runpy
import subprocess
import struct
import sys

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-flight-sdk'
assert len(sys.argv) == 2, 'Usage: public-summary.py FULL_FEATURE_COMMIT'
FEATURE = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}', FEATURE)
assert subprocess.check_output(['git', 'rev-parse', FEATURE + '^{commit}'], cwd=ROOT, text=True).strip() == FEATURE
MAX_FILE = 16 * 1024 * 1024
PUBLIC_RECIPE = f'reports/{PREFIX}-recipes/public.py'
PUBLIC_PATHS = runpy.run_path(str(ROOT / PUBLIC_RECIPE), run_name='guard_public_recipe')['PATHS']


def safe_path(value):
    assert type(value) is str and value and '\\' not in value and '\r' not in value and '\n' not in value
    p = PurePosixPath(value)
    assert not p.is_absolute() and '..' not in p.parts and p.as_posix() == value
    return value


def read(path):
    raw = (ROOT / safe_path(path)).read_bytes();assert len(raw) <= MAX_FILE
    return json.loads(raw.decode('utf-8-sig'))


def data_hash(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def digest(path):
    return data_hash((ROOT / safe_path(path)).read_bytes())


def expected_hash(value):
    assert type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_FILE
    assert re.fullmatch('[0-9a-f]{64}', value['sha256'])
    return {'bytes': value['bytes'], 'sha256': value['sha256']}


def blobs(requests):
    keys = sorted(set(requests));assert len(keys) <= 2048
    for commit, path in keys:
        assert re.fullmatch('[0-9a-f]{40}', commit);safe_path(path)
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT,
                                  input=''.join(c + ':' + p + '\n' for c, p in keys).encode())
    assert len(raw) <= 128 * 1024 * 1024
    result = {};offset = 0
    for key in keys:
        end = raw.index(b'\n', offset);header = raw[offset:end].split()
        assert len(header) == 3 and header[1] == b'blob', key
        size = int(header[2]);assert 0 <= size <= MAX_FILE
        offset = end + 1;result[key] = raw[offset:offset + size]
        assert len(result[key]) == size and raw[offset + size:offset + size + 1] == b'\n'
        offset += size + 1
    assert offset == len(raw)
    return result


def normalized_entry(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                  re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', raw), flags=re.S).replace(b'\r\n', b'\n')


def jpeg_dimensions(raw):
    assert raw[:2] == b'\xff\xd8'
    at = 2
    while at < len(raw):
        assert raw[at] == 255
        marker = raw[at + 1];at += 2
        length = int.from_bytes(raw[at:at + 2], 'big');assert length >= 2
        if marker in (192, 193, 194):
            return int.from_bytes(raw[at + 5:at + 7], 'big'), int.from_bytes(raw[at + 3:at + 5], 'big')
        at += length
    raise AssertionError('No JPEG frame')


local_path = f'reports/{PREFIX}-local-verification.json'
base_path = f'reports/{PREFIX}-baseline.json'
runs_path = f'reports/{PREFIX}-public-runs.json'
bytes_path = f'reports/{PREFIX}-public-bytes.json'
local, base, runs, public = map(read, [local_path, base_path, runs_path, bytes_path])
assert local['status'] == 'PASS'
assert tuple(local[k] for k in ['nativeExchangeGroups','ctest','node','skipped','exports','sourceHeaders','compiledTranslationUnits','runtimeMembers','licenseNoticesUnchanged','protectedFilesUnchanged','generatedEntriesOnly']) == (200,41,631,0,92,67,32,91,7,333,25)
assert local['mathematicsFixturesVerified'] == {'held':74,'guard':95,'supplemental':4,'total':173}
assert local['baseCommit'] == base['baseCommit'] and re.fullmatch('[0-9a-f]{16}', local['webBuild'])
assert local['sourcePreservation']['apiReconstructedExactBaseBlob'] is True
assert local['sourcePreservation']['headerInsertionOnlyExactBaseBlob'] is True
assert local['sourcePreservation']['oldExportsPreservedInOrder'] == 86
assert runs['commit'] == public['commit'] == FEATURE and public['status'] == 'PASS'
assert public['build'] == local['webBuild']
assert len(public['files']) == len(PUBLIC_PATHS) == 45
assert {r['path'] for r in public['files']} == set(PUBLIC_PATHS)
assert len(base['protected']) == 333 and len(base['generatedEntries']) == 25
evidence = {local_path, base_path, runs_path, bytes_path, PUBLIC_RECIPE}
for path, value in local['evidence'].items():
    assert digest(path) == expected_hash(value), path
    evidence.add(path)
manifest_path = 'assets/pikapika-simulation.build.json'
manifest = read(manifest_path);evidence.add(manifest_path)
assert manifest['sdkVersion'] == '6.0.13' and len(manifest['sources']) == 32 and len(manifest['sourceSha256']) == 67
exports = json.loads(next(f.split('=', 1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 92
old_exports = json.loads(next(f.split('=',1)[1] for f in base['manifest']['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
new_family = ['_pp_sim_sphere_triangle_mesh_flight_'+s for s in ['begin','append','query','record','last_mesh','candidate']]
assert len(old_exports)==86 and [x for x in exports if x not in new_family]==old_exports
assert [x for x in exports if x not in old_exports]==new_family
assert manifest['linkedLibraryMembers'] == base['manifest']['linkedLibraryMembers'] and len(manifest['linkedLibraryMembers']) == 91
assert manifest['licenses'] == base['manifest']['licenses'] and len(manifest['licenses']) == 7
assert manifest['artifacts']['assets/pikapika-simulation.wasm']['bytes'] == 800982
assert manifest['artifacts']['assets/pikapika-simulation.mjs']['bytes'] == 61661
assert manifest['sourceFlags']['core/src/dynamics.cpp'] == ['-fno-fast-math', '-ffp-contract=off']
assert {'core/src/sphere_triangle_mesh_held_load.cpp', 'core/src/sphere_triangle_mesh_free_flight_guard.cpp'} <= set(manifest['sources'])
assert 'core/src/sphere_triangle_mesh_flight_api_internal.hpp' in manifest['sourceSha256']
for path, value in [*manifest['sourceSha256'].items(), *manifest['licenses'].items()]:
    assert digest(path)['sha256'] == value, path
for path, value in manifest['artifacts'].items():assert digest(path) == expected_hash(value), path
for path, value in local['artifacts'].items():assert digest(path) == expected_hash(value), path
requests = [(base['baseCommit'], p) for p in base['protected']]
requests += [(base['baseCommit'],p) for p in ['core/src/simulation_api.cpp','core/include/pikapika/simulation_api.h']]
requests += [(FEATURE, p) for p in set(base['protected']) | set(base['generatedEntries']) | set(PUBLIC_PATHS) | set(manifest['sourceSha256']) | {'.github/workflows/verify.yml'}]
source_blobs = blobs(requests)
api = source_blobs[FEATURE,'core/src/simulation_api.cpp']
for fragment in [b'#include "pikapika/sphere_triangle_mesh_free_flight_guard.hpp"\n',b'#include "sphere_triangle_mesh_flight_api_internal.hpp"\n',b'for(auto& stage:flight_stages){stage.reset();}for(auto& record:flight_records){record.reset();}']:
    assert api.count(fragment)==1
    api=api.replace(fragment,b'',1)
assert api==source_blobs[base['baseCommit'],'core/src/simulation_api.cpp']
header=source_blobs[FEATURE,'core/include/pikapika/simulation_api.h']
start=header.index(b'enum pp_sim_sphere_triangle_mesh_flight_mode {')
end=header.index(b'int32_t pp_sim_polarized_packet(uint32_t value_count);',start)
assert header[:start]+header[end:]==source_blobs[base['baseCommit'],'core/include/pikapika/simulation_api.h']
for path, value in base['protected'].items():
    assert digest(path) == expected_hash(value), path
    assert source_blobs[base['baseCommit'], path] == source_blobs[FEATURE, path], path
source_comparisons = {}
for path in set(PUBLIC_PATHS) | set(manifest['sourceSha256']) | {'.github/workflows/verify.yml'}:
    raw = (ROOT / path).read_bytes();distributed = source_blobs[FEATURE, path]
    canonical = raw if path.endswith('.wasm') else raw.replace(b'\r\n', b'\n')
    assert canonical == distributed, path
    source_comparisons[path] = {'raw': data_hash(raw), 'featureBlob': data_hash(distributed),
        'normalization': 'Declared Git text CRLF-to-LF only' if raw != canonical else None}
generated = {}
for path, value in base['generatedEntries'].items():
    raw = (ROOT / path).read_bytes();distributed = source_blobs[FEATURE, path]
    assert data_hash(normalized_entry(raw)) == data_hash(normalized_entry(distributed)) == value, path
    assert raw.replace(b'\r\n', b'\n') == distributed
    generated[path] = {'raw': data_hash(raw), 'featureBlob': data_hash(distributed), 'normalizedAuthored': value}
for item in public['files']:
    path = safe_path(item['path']);assert data_hash(source_blobs[FEATURE, path]) == expected_hash(item)
    url = urlsplit(item['url'])
    assert url.scheme == 'https' and url.netloc == 'tatata93.github.io' and unquote(url.path) == '/pikapikaengine/' + path

# Current final command streams are rechecked independently of the local summary.
final = f'reports/{PREFIX}-checks/run-20261104-final-002'
commands = []
for phase in ['native', 'wire', 'regressions', 'pure-regressions']:
    path = final + '/' + phase + '-commands.json';rows = read(path);evidence.add(path)
    assert rows and all(r['exit'] == 0 and r['authoredStable'] is True and r['authoredBefore'] == r['authoredAfter'] for r in rows)
    commands.extend(rows)
for row in commands:
    for path, value in row['authoredAfter'].items():assert digest(path) == expected_hash(value), path
    for stream in ['stdout', 'stderr']:
        path = safe_path(row[stream]);assert digest(path) == expected_hash(row[stream + 'Hash']);evidence.add(path)
def stdout(name):
    rows = [r for r in commands if r['name'] == name];assert len(rows) == 1, name
    return (ROOT / rows[0]['stdout']).read_text(encoding='utf-8-sig')
assert '200 sphere triangle mesh flight C ABI groups passed; 183 complete inputs; 173 actual models; 10 host refusals' in stdout('native-tests')
assert '100% tests passed, 0 tests failed out of 41' in stdout('ctest')
for key, value in [('tests', 631), ('pass', 631), ('fail', 0), ('skipped', 0)]:
    assert re.search(r'(?:ℹ\s+|#\s+)' + key + r'\s+' + str(value) + r'(?:\s|$)', stdout('node'))
native, wasm = [read(final + '/' + d + '/report.json') for d in ['native-exchange', 'wasm-independent']]
wire = read(final + '/wasm-wire/report.json')
for directory, result, scope in [('native-exchange', native, 'native'), ('wasm-independent', wasm, 'wasm-wire')]:
    assert result['status'] == 'PASS' and result['scope'] == scope
    assert tuple(result[k] for k in ['fixtureCount', 'accepted', 'hostRejected', 'numericBits', 'negativeZeroBits', 'decodedNumericBits', 'decodedNegativeZeroBits']) == (183,173,10,415506,5738,272814,5424)
    assert result['acceptedInputFingerprint'] == '684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb'
    assert result['fullInputFingerprint'] == '4149030bf7278b5a91db1f2739c55491c82f57fc733254ee384153867f19ca54'
    assert result['maximums'] == {'sources':64,'audits':256,'leaves':128,'partition':128,'frontier':127,'candidateIds':64,'lastMeshRows':64,'lastMeshCandidates':448}
    assert [(result['cohorts'][c]['models'],result['cohorts'][c]['hostRejected']) for c in ['held','guard','supplemental']] == [(74,5),(95,5),(4,0)]
    controls = result['packetNegativeControls']
    assert controls == read(final + '/' + directory + '/packet-negative-controls.json')
    assert controls['status'] == 'PASS' and controls['count'] == len(controls['rejectedControls']) == 16
    assert all(r['rejected'] is True for r in controls['rejectedControls'])
    assert result['optimizedPythonRejected'] == {'status':'PASS','exitCode':1}
    assert result['pureNativeReference']['held']['fixtures'] == 79
    assert result['pureNativeReference']['guard']['fixtures'] == 100
    assert result['pureNativeReference']['supplemental']['fixtures'] == 4
    assert all(result['pureNativeReference'][c]['status']=='PASS' for c in ['held','guard','supplemental'])
    assert result['records']==10397
    for path, value in result['files'].items():
        full = final + '/' + directory + '/' + safe_path(path);assert digest(full) == expected_hash(value);evidence.add(full)
    evidence.add(final + '/' + directory + '/report.json')
assert native['cohorts'] == wasm['cohorts'] and native['pureNativeReference'] == wasm['pureNativeReference']
assert local['nativeExchange'] == native and local['wasmExchange'] == wasm and local['wasmWire'] == wire
def compare_decoded(a, b):
    # JSON decimal spelling can differ (1 versus 1.0); binary64 bits, booleans,
    # optional nulls, full keys and all array ordering must agree exactly.
    if type(a) in (int, float) and type(b) in (int, float):
        assert struct.pack('>d', a) == struct.pack('>d', b)
        return 1
    assert type(a) is type(b)
    if type(a) is dict:
        assert set(a) == set(b)
        return sum(compare_decoded(a[k], b[k]) for k in a)
    if type(a) is list:
        assert len(a) == len(b)
        return sum(compare_decoded(x, y) for x, y in zip(a, b))
    assert a == b
    return 0
decoded_tree_bits = compare_decoded(read(final+'/native-exchange/decoded-models.json'), read(final+'/wasm-independent/decoded-models.json'))
assert decoded_tree_bits >= 272814
assert wire['status'] == 'PASS' and tuple(wire[k] for k in ['fixtures','accepted','hostRejected','numericBits','negativeZeroBits']) == (183,173,10,415689,5738)
assert len(wire['controls'])==15 and all(r['status']=='PASS' for r in wire['controls'])
assert wire['sourceNativePackets'] == digest(final + '/native-exchange/packets.json')
assert wire['capturedPackets'] == digest(final + '/wasm-wire/wasm-packets.json')
assert wire['wasm'] == manifest['artifacts']['assets/pikapika-simulation.wasm']
assert wire['memory']['usedHeapBytes'] is None and wire['memory']['stackHighWaterBytes'] is None
evidence.update([final+'/wasm-wire/report.json',final+'/wasm-wire/wasm-packets.json'])
before = f'reports/{PREFIX}-checks/run-20261104-before'
legacy = read(final + '/legacy-native-after.json')
assert digest(final+'/legacy-native-after.json') == digest(before+'/legacy-native-before.json')
assert legacy['counts'] == {'fixtures':20,'successes':14,'failures':6,'multipleEventCases':5}
legacy_wasm = read(final+'/legacy-wasm-after/report.json')
assert legacy_wasm['status']=='PASS' and legacy_wasm['comparedToBaseline'] is True
assert tuple(legacy_wasm[k] for k in ['fixtures','completed','modelRejected','hostRejected','numericBits','negativeZeroBits']) == (20,14,5,1,4520,24)
assert digest(final+'/legacy-wasm-after/results.json') == digest(before+'/legacy-wasm-before/results.json')
for part, old in [('held','reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json'),('guard','reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/native-fixtures.json'),('supplemental','reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/supplemental-fixtures.json')]:
    assert digest(final+'/'+part+'.json')==digest(old);evidence.update([final+'/'+part+'.json',old])
old_owned = read(final+'/old-entry-owned/report.json')
assert old_owned['status']=='PASS' and tuple(old_owned[k] for k in ['actualModelFixtures','hostRejected','modelNumericComparisons','modelNegativeZeroComparisons','originalInputNumericComparisons','originalInputNegativeZeroComparisons']) == (62,3,105056,3239,4728,108)
assert old_owned['negativeControls']['rejectedControls']==90
for path,value in old_owned['files'].items():
    full=final+'/old-entry-owned/'+safe_path(path);assert digest(full)==expected_hash(value);evidence.add(full)
for path in [final+'/legacy-native-after.json',before+'/legacy-native-before.json',final+'/legacy-wasm-after/report.json',final+'/legacy-wasm-after/results.json',before+'/legacy-wasm-before/results.json',final+'/old-entry-owned/report.json',before+'/baseline-scope.json']:evidence.add(path)

# Exact feature run states plus excerpts; no previous milestone success substituted.
assert len(runs['runs']) == len({r['id'] for r in runs['runs']}) == 2
assert {r['name'] for r in runs['runs']} == {'Engine verification','pages build and deployment'}
jobs=[]
for run in runs['runs']:
    assert run['head_sha']==FEATURE and run['status']=='completed' and run['conclusion']=='success'
    path=f'reports/{PREFIX}-run-{run["id"]}.json';evidence.add(path);rows=read(path)['jobs'];assert rows
    for job in rows:
        assert job['run_id']==run['id'] and job['status']=='completed' and job['conclusion']=='success'
        assert job['steps'] and all(s['status']=='completed' and s['conclusion']=='success' for s in job['steps'])
    jobs.extend(rows)
engine_rows=[j for j in jobs if j['name']=='portable-core'];assert len(engine_rows)==1
engine=engine_rows[0];assert len(jobs)==4
required_steps={'Build and test C++ core on Linux','Test authoring and game logic including the built native CLI','Audit bounded flight C ABI exchange with sanitizers','Audit held-load static mesh path independently','Audit rounded free flight mesh guard independently'}
assert required_steps <= {s['name'] for s in engine['steps']}
log_path=f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json';log=read(log_path);evidence.add(log_path)
assert log['jobId']==engine['id'] and type(log['fullLineCount']) is int and 0<len(log['lines'])<=4096
ordinals=[r['line'] for r in log['lines']];assert ordinals==sorted(set(ordinals)) and ordinals[0]>=1 and ordinals[-1]<=log['fullLineCount']
text='\n'.join(r['text'] for r in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 41','# tests 631','# pass 631','# fail 0','# skipped 0','200 sphere triangle mesh flight C ABI groups passed; 183 complete inputs; 173 actual models; 10 host refusals','PASS 114 groups; 100 complete-input finite free-flight guard fixtures','PASS 92 groups; 79 complete-input finite held-load fixtures','cmp build/ci/free-flight-legacy-before.json build/ci/free-flight-legacy-after.json','cmp build/ci/sphere-triangle-mesh-flight-native-exchange/packets.json build/ci/sphere-triangle-mesh-flight-sanitized-exchange/packets.json','cmp build/ci/sphere-triangle-mesh-free-flight-guard-fixtures.json build/ci/sphere-triangle-mesh-free-flight-guard-sanitized-fixtures.json','cmp build/ci/sphere-triangle-mesh-free-flight-guard-supplemental.json build/ci/sphere-triangle-mesh-free-flight-guard-sanitized-supplemental.json']:
    assert marker in text, marker
for key,value in [('fixtureCount',183),('accepted',173),('hostRejected',10),('numericBits',415506),('numericBits',415689),('negativeZeroBits',5738),('decodedNumericBits',272814),('decodedNegativeZeroBits',5424),('count',16),('selfTestGroups',12),('rejectedControls',50)]:
    assert re.search('"'+key+r'"\s*:\s*'+str(value)+r'\b',text),(key,value)
assert native['acceptedInputFingerprint'] in text and native['fullInputFingerprint'] in text
old_log_path='reports/sphere-triangle-mesh-free-flight-guard-job-126460730559-excerpt.json';old_log=read(old_log_path);evidence.add(old_log_path)
def warning_suffixes(source):return [r['text'].split('warning:',1)[1] for r in source['lines'] if 'warning:' in r['text']]
warnings,old_warnings=warning_suffixes(log),warning_suffixes(old_log)
assert len(warnings)==len(old_warnings)==40 and Counter(warnings)==Counter(old_warnings)
workflow=source_blobs[FEATURE,'.github/workflows/verify.yml'].decode()
step=workflow.split('      - name: Audit bounded flight C ABI exchange with sanitizers\n',1)[1].split('      - name: ',1)[0]
for marker in ['-Werror','-fsanitize=address,undefined','core/src/simulation_api.cpp tests/sphere_triangle_mesh_flight_sdk_tests.cpp','core/src/simulation_api.cpp tools/sphere_triangle_mesh_flight_sdk_probe.cpp','tests/sphere_triangle_mesh_held_load_fixtures.cpp tests/sphere_triangle_mesh_free_flight_guard_fixtures.cpp build/ci/libpikapika_core.a','sphere-triangle-mesh-flight-sdk-sanitized','sphere-triangle-mesh-flight-probe-sanitized','cmp build/ci/sphere-triangle-mesh-flight-native-exchange/packets.json build/ci/sphere-triangle-mesh-flight-sanitized-exchange/packets.json']:assert marker in step,marker

# Public gameplay remains an old-API compatibility check, not a new flight UI.
browser_dir=f'reports/{PREFIX}-browser';screens={}
for name in ['public-diagram.jpg','public-game.jpg']:
    path=browser_dir+'/'+name;raw=(ROOT/path).read_bytes();width,height=jpeg_dimensions(raw)
    assert 900<=width<=4096 and 500<=height<=4096
    screens[name]={'path':path,'width':width,'height':height,**data_hash(raw)};evidence.add(path)
game_path,state_path=browser_dir+'/public-game-cover-report.json',browser_dir+'/public-game-state.txt'
game=read(game_path);state=(ROOT/state_path).read_text(encoding='utf-8')
assert game['state']=='ready' and game['failure'] is None and game['pending'] is None and game['errors']==[]
assert '一時停止 / Pで再開' in state
kills=int(re.search(r'撃破 (\d+)',state).group(1));queries=game['counts']['queries']
assert kills>0 and type(queries) is int and queries>0 and queries==game['counts']['checked']==game['counts']['validated']==len(game['records'])
assert all(r['state']=='completed' for r in game['records']) and any(r['clipSeconds']==1 for r in game['records'])
assert game['renderer']['residentMeshes']==3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId']==public['build'] and game['startup']['diagnostics']['wasmBytes']==800982
asset_url=urlsplit(game['startup']['assetURL'])
assert asset_url.scheme=='https' and asset_url.netloc=='tatata93.github.io' and asset_url.path=='/pikapikaengine/assets/robot-back-cover.skin.json'
assert parse_qs(asset_url.query).get('build')==[public['build']]
evidence.update([game_path,state_path])
for directory in [f'reports/{PREFIX}-recipes']:
    for path in (ROOT/directory).glob('*'):
        if path.is_file():evidence.add(path.relative_to(ROOT).as_posix())
evidence_hashes={p:digest(p) for p in sorted(evidence)}
assert len(evidence_hashes)<=1024 and sum(v['bytes'] for v in evidence_hashes.values())<=160*1024*1024
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'commit':FEATURE,
    'nativeGroups':200,'fixtures':183,'actualModelFixtures':173,'hostRejected':10,'ctest':41,'node':631,'skipped':0,
    'exports':92,'sourceHeaders':67,'sourceTranslationUnits':32,'runtimeMembers':91,'licenseNotices':7,'sdkArtifacts':manifest['artifacts'],
    'nativeExchange':native,'wasmWire':wire,'wasmIndependent':wasm,'decodedTreeNumericBits':decoded_tree_bits,
    'protectedFilesUnchanged':333,'normalizedGeneratedEntries':25,'generatedEntries':generated,'sourceComparisons':source_comparisons,
    'legacyNativeBytes':digest(final+'/legacy-native-after.json'),'legacyWasm':legacy_wasm,'oldEntryOwned':old_owned,
    'baselineScope':local['baselineScope'],'historicalNoncompiledSource':local['historicalNoncompiledSource'],
    'historicalSupersededSource':local['historicalSupersededSource'],'historicalCommands':local['historicalCommands'],
    'syntheticAttempts':local['syntheticAttempts'],
    'initialBrowser':local['initialBrowser'],
    'historyScope':'The original prebuilt baseline header-edit overlap, unused synthetic Python source5760-to6001B transition and superseded successful runs before removing an unused internal helper remain archived. They are not called current-source builds. All four final-002 compilation/exchange/regression command phases require stable current sources. Synthetic6 tests are separate from actual173-model and16-wire-negative evidence.',
    'publicFiles':45,'publicBytes':sum(r['bytes'] for r in public['files']),'webBuild':public['build'],'jobs':jobs,
    'warnings':{'currentOccurrences':40,'priorOccurrences':40,'priorDiagnosticMultisetPreserved':True,'newDiagnosticOccurrences':0},
    'sanitizers':{'apiGroups':200,'probeFixtures':183,'releaseSanitizedPacketsByteComparison':'PASS',
        'scope':'Current simulation_api.cpp, new ABI tests/probe and both fixture writers are instrumented and link the existing pure archive. Held/guard complete pure-kernel ASan/UBSan steps run separately. This API step does not imply that every archive member was instrumented.'},
    'browserDisplay':screens,'publicGame':{'status':'PASS','kills':kills,'queries':queries,'paused':True,'boostClip1Observed':True,'residentMeshes':3,'errors':0,
        'scope':'Actual public old-method gameplay compatibility with rebuilt92-export SDK. No flight owned JS API, manual UI or game contact integration inferred.'},
    'ciEvidenceScope':'Exact current run/job/all step states and saved finite excerpts; full job logs are not archived.',
    'scope':'183 raw inputs produce173 actual Native/WASM models and10 host refusals. Only actual173 decoded models enter their Fraction references; pure79/100+4 reference counts are separately retained, not fabricated into rejected wire results. Native and Node numeric counts differ by183 mode metadata values. Complete packets/decoded math, ownership/atomic rejection, and existing game compatibility are distinct evidence. No World advance/contact response, heap usage, stack highwater, injected allocation failure or owned public flight JS API is claimed.',
    'evidence':evidence_hashes}
(ROOT/f'reports/{PREFIX}-public-verification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
print(json.dumps({k:report[k] for k in ['status','commit','nativeGroups','fixtures','actualModelFixtures','hostRejected','ctest','node','publicFiles','publicBytes']}))


