"""Accept exact-feature owned-flight CI, selected public bytes and fresh browser proof."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, unquote, urlsplit
import json
import math
import re
import runpy
import struct
import subprocess
import sys

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-flight-js'
assert len(sys.argv) == 3, 'Usage: public-summary.py FULL_FEATURE_COMMIT FINAL_PUBLIC_CAPTURE_DIRECTORY'
FEATURE = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}', FEATURE)
assert subprocess.check_output(['git', 'rev-parse', FEATURE+'^{commit}'], cwd=ROOT, text=True).strip() == FEATURE
CAPTURE = Path(sys.argv[2]).resolve()
assert CAPTURE.is_relative_to(ROOT) and CAPTURE.is_dir()
MAX_FILE = 64 * 1024 * 1024
evidence = {}


def relative(path):
    p = Path(path)
    p = (p if p.is_absolute() else ROOT/p).resolve()
    assert p.is_relative_to(ROOT), p
    return p.relative_to(ROOT).as_posix()


def safe_path(value):
    assert type(value) is str and value and '\\' not in value and '\r' not in value and '\n' not in value
    p = PurePosixPath(value)
    assert not p.is_absolute() and '..' not in p.parts and p.as_posix() == value
    return value


def hash_bytes(raw):
    assert len(raw) <= MAX_FILE
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def digest(path):
    return hash_bytes((ROOT/relative(path)).read_bytes())


def expected(value):
    assert type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_FILE
    assert type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256'])
    return {'bytes': value['bytes'], 'sha256': value['sha256']}


def remember(path):
    key = relative(path)
    evidence[key] = digest(key)
    return evidence[key]


def read(path):
    remember(path)
    def floating(token):
        value = float(token)
        mantissa = token.lower().split('e')[0]
        assert math.isfinite(value) and not (value == 0 and any(c in '123456789' for c in mantissa)), token
        return value
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, key
            result[key] = value
        return result
    return json.loads((ROOT/relative(path)).read_text(encoding='utf-8-sig'), parse_float=floating,
                      parse_int=lambda token: -0.0 if token == '-0' else int(token),
                      parse_constant=lambda token: (_ for _ in ()).throw(AssertionError(token)), object_pairs_hook=pairs)


def blobs(requests):
    keys = sorted(set(requests))
    assert len(keys) <= 2048
    for commit, path in keys:
        assert re.fullmatch('[0-9a-f]{40}', commit)
        safe_path(path)
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT,
                                  input=''.join(c+':'+p+'\n' for c, p in keys).encode())
    assert len(raw) <= 256 * 1024 * 1024
    result, offset = {}, 0
    for key in keys:
        end = raw.index(b'\n', offset)
        header = raw[offset:end].split()
        assert len(header) == 3 and header[1] == b'blob', key
        size = int(header[2])
        assert 0 <= size <= MAX_FILE
        offset = end+1
        result[key] = raw[offset:offset+size]
        assert len(result[key]) == size and raw[offset+size:offset+size+1] == b'\n'
        offset += size+1
    assert offset == len(raw)
    return result


def normalized_entry(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                  re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', raw), flags=re.S).replace(b'\r\n', b'\n')


def git_current(path, blob):
    raw = (ROOT/path).read_bytes()
    # Compare exact bytes FIRST: several authored sources intentionally use -text.
    if raw == blob:
        conversion = None
    else:
        assert Path(path).suffix in {'.cpp', '.hpp', '.h', '.mjs', '.py', '.yml', '.md', '.txt', '.html', '.css', '.json'}
        assert b'\r\n' in raw and raw.replace(b'\r\n', b'\n') == blob, path
        conversion = 'Declared Git text CRLF-to-LF only; exact raw comparison was attempted first.'
    return {'raw': hash_bytes(raw), 'featureBlob': hash_bytes(blob), 'normalization': conversion}


def compare_tree(a, b):
    if type(a) in (int, float) and type(b) in (int, float):
        assert math.isfinite(a) and math.isfinite(b) and struct.pack('>d', a) == struct.pack('>d', b)
        return (1, int(struct.pack('>d', a) == b'\x80'+b'\0'*7))
    assert type(a) is type(b)
    if type(a) is dict:
        assert set(a) == set(b)
        counts = [compare_tree(a[k], b[k]) for k in a]
    elif type(a) is list:
        assert len(a) == len(b)
        counts = [compare_tree(x, y) for x, y in zip(a, b)]
    else:
        assert a == b
        return (0, 0)
    return tuple(sum(c[i] for c in counts) for i in range(2))


def jpeg_dimensions(raw):
    assert raw[:2] == b'\xff\xd8'
    at = 2
    while at < len(raw):
        assert raw[at] == 255
        marker = raw[at+1]
        at += 2
        length = int.from_bytes(raw[at:at+2], 'big')
        assert length >= 2
        if marker in (192, 193, 194):
            return int.from_bytes(raw[at+5:at+7], 'big'), int.from_bytes(raw[at+3:at+5], 'big')
        at += length
    raise AssertionError('No JPEG frame')


local_path = f'reports/{PREFIX}-local-verification.json'
base_path = f'reports/{PREFIX}-baseline.json'
runs_path = f'reports/{PREFIX}-public-runs.json'
public_path = f'reports/{PREFIX}-public-bytes.json'
local, base, runs, public = map(read, [local_path, base_path, runs_path, public_path])
assert local['status'] == 'PASS' and local['baseCommit'] == base['baseCommit']
assert tuple(local[k] for k in ['protectedFilesUnchanged', 'normalizedGeneratedEntries', 'ctest', 'skipped', 'exports', 'sourceHeaders', 'compiledTranslationUnits', 'runtimeMembers', 'licenseNoticesUnchanged']) == (345, 25, 41, 0, 92, 67, 32, 91, 7)
assert type(local['focused']) is int and local['focused'] >= 30 and local['node'] == 631+local['focused']
assert local['modules'] == 52 and local['entries'] == 25
assert local['sdkProvenanceUnchanged'] is True and local['onlyNewRuntimeImportAndTwoMethods'] is True
assert local['mathematicsFixturesVerified'] == {'held': 74, 'guard': 95, 'supplemental': 4, 'total': 173}
assert runs['commit'] == public['commit'] == FEATURE and public['status'] == 'PASS'
assert public['build'] == local['webBuild'] and re.fullmatch('[0-9a-f]{16}', public['build'])
assert public['build'] == '836a4c2102a528cd'
PUBLIC_RECIPE = f'reports/{PREFIX}-recipes/public.py'
public_paths = runpy.run_path(str(ROOT/PUBLIC_RECIPE), run_name='flight_owned_public_recipe')['PATHS']
assert len(public_paths) == len(set(public_paths)) == len(public['files']) == 52
assert {r['path'] for r in public['files']} == set(public_paths)
for path, value in local['evidence'].items():
    assert remember(path) == expected(value), path
assert len(base['protected']) == 345 and len(base['generatedEntries']) == 25
manifest = read('assets/pikapika-simulation.build.json')
assert manifest == base['manifest']
assert len(manifest['sources']) == 32 and len(manifest['sourceSha256']) == 67
assert len(manifest['linkedLibraryMembers']) == 91 and len(manifest['licenses']) == 7
exports = json.loads(next(f.split('=', 1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 92
for path, value in [*manifest['sourceSha256'].items(), *manifest['licenses'].items()]:
    assert digest(path)['sha256'] == value, path
for path, value in local['artifacts'].items():
    assert remember(path) == expected(value)
assert local['artifacts']['assets/pikapika-simulation.wasm'] == {'bytes': 800982, 'sha256': 'a7db41c64d2f9112ec5ee033371c391dddcb42ad23dcef713347c129a4ed015d'}
assert local['artifacts']['assets/pikapika-simulation.mjs'] == {'bytes': 61661, 'sha256': 'd4bedfdc9dcc1a60ee816e34c43afbe51623835ca5af65b0e6f4f5937484de55'}
for path, value in manifest['artifacts'].items():
    assert local['artifacts'][path] == value

# Old raw proof is inherited only through unchanged sources/artifacts/evidence.
raw_path = 'reports/sphere-triangle-mesh-flight-sdk-public-verification.json'
raw = read(raw_path)
assert raw['status'] == 'PASS' and raw['nativeGroups'] == 200 and raw['fixtures'] == 183
assert (raw['actualModelFixtures'], raw['hostRejected'], raw['ctest']) == (173, 10, 41)
assert raw['exports'] == 92 and raw['sourceHeaders'] == 67 and raw['runtimeMembers'] == 91 and raw['licenseNotices'] == 7
assert raw['sdkArtifacts'] == manifest['artifacts']
assert raw['nativeExchange']['packetNegativeControls']['count'] == raw['wasmIndependent']['packetNegativeControls']['count'] == 16
assert raw['nativeExchange']['optimizedPythonRejected']['status'] == raw['wasmIndependent']['optimizedPythonRejected']['status'] == 'PASS'
for path, value in raw['evidence'].items():
    # Old generated HTML and documentary files intentionally change this turn;
    # retain their prior recorded hashes without claiming current raw equality.
    if path in base['protected']:
        assert digest(path) == expected(value), path

selected = set(public_paths) | set(manifest['sourceSha256']) | set(local['newSources']) | {'.github/workflows/verify.yml'}
requests = [(FEATURE, p) for p in selected | set(base['protected']) | set(base['generatedEntries']) | {raw_path}]
requests += [(base['baseCommit'], p) for p in set(base['protected']) | {raw_path, 'engine/simulation.mjs'}]
source_blobs = blobs(requests)
assert source_blobs[base['baseCommit'], raw_path] == source_blobs[FEATURE, raw_path]
for path, value in base['protected'].items():
    assert digest(path) == expected(value), path
    assert source_blobs[base['baseCommit'], path] == source_blobs[FEATURE, path], path
source_comparisons = {p: git_current(p, source_blobs[FEATURE, p]) for p in selected}
runtime = source_blobs[FEATURE, 'engine/simulation.mjs']
for fragment in [b"import {querySphereTriangleMeshHeldLoad,querySphereTriangleMeshFreeFlightGuard} from './sphere-triangle-mesh-flight.mjs';\n",
                 b'  querySphereTriangleMeshHeldLoad(sphere,triangles,horizon,settings={}){\n    return querySphereTriangleMeshHeldLoad(this,sphere,triangles,horizon,settings,sphereTriangleMeshResult);\n  }\n',
                 b'  querySphereTriangleMeshFreeFlightGuard(body,gravity,triangles,horizon,settings={}){\n    return querySphereTriangleMeshFreeFlightGuard(this,body,gravity,triangles,horizon,settings,sphereTriangleMeshResult);\n  }\n']:
    assert runtime.count(fragment) == 1
    runtime = runtime.replace(fragment, b'', 1)
assert runtime == source_blobs[base['baseCommit'], 'engine/simulation.mjs']
generated = {}
for path, value in base['generatedEntries'].items():
    current, feature = (ROOT/path).read_bytes(), source_blobs[FEATURE, path]
    assert hash_bytes(normalized_entry(current)) == hash_bytes(normalized_entry(feature)) == value
    generated[path] = {**git_current(path, feature), 'normalizedAuthored': value}
for item in public['files']:
    path = safe_path(item['path'])
    assert hash_bytes(source_blobs[FEATURE, path]) == expected(item)
    url = urlsplit(item['url'])
    assert url.scheme == 'https' and url.netloc == 'tatata93.github.io' and unquote(url.path) == '/pikapikaengine/'+path

# Re-audit canonical command captures independently from the local summary.
final = ROOT/relative(local['canonicalDirectory'])
budget_transition = local['ciExecutionBudgetTransition']
budget = read(f'reports/{PREFIX}-recipes/ci-budget-transition.json')
assert budget == budget_transition['record']
assert budget['workflow'] == '.github/workflows/verify.yml'
assert budget['beforeFile'] == f'reports/{PREFIX}-recipes/workflow-before-budget.yml'
assert remember(budget['beforeFile']) == expected(budget['before'])
assert digest(budget['workflow']) == expected(budget['after'])
old_workflow = (ROOT/budget['beforeFile']).read_bytes()
assert old_workflow.count(b'timeout-minutes: 15') == 1
assert (ROOT/budget['workflow']).read_bytes() == old_workflow.replace(b'timeout-minutes: 15', b'timeout-minutes: 20', 1)
budget_command_names = []
commands = []
for phase in ['focused', 'owned', 'regressions']:
    path = final/(phase+'-commands.json')
    rows = read(path)
    assert rows
    for row in rows:
        assert row['exit'] == 0 and row['authoredStable'] is True and row['authoredBefore'] == row['authoredAfter']
        for path, value in row['authoredAfter'].items():
            if path == budget['workflow']:
                assert value == budget['before'] and digest(path) == expected(budget['after'])
                budget_command_names.append(row['name'])
            else:
                assert digest(path) == expected(value), path
        for stream in ['stdout', 'stderr']:
            assert remember(row[stream]) == expected(row[stream+'Hash'])
    commands.extend(rows)
assert budget_command_names == budget_transition['commandsCapturedBeforeBudgetChange']


def stdout(name):
    rows = [r for r in commands if r['name'] == name]
    assert len(rows) == 1, name
    return (ROOT/rows[0]['stdout']).read_text(encoding='utf-8-sig')


for key, value in [('tests', local['node']), ('pass', local['node']), ('fail', 0), ('skipped', 0)]:
    assert re.search(r'(?:ℹ\s+|#\s+)'+key+r'\s+'+str(value)+r'\b', stdout('node'))
assert '100% tests passed, 0 tests failed out of 41' in stdout('ctest')
assert public['build']+': 52 versioned modules' in stdout('web-build')
owned = read(final/'owned/report.json')
assert owned == local['owned'] and owned['status'] == 'PASS'
assert (owned['fixtures'], owned['actualModels'], owned['hostRejected']) == (183, 173, 10)
assert owned['originalExportsAndPrototypesUnchanged'] is True and owned['oldEntryAndWorldUnchanged'] is True
assert owned['sourceStable'] is True and owned['sourcesBefore'] == owned['sourcesAfter']
for path, value in owned['sourcesAfter'].items():
    assert digest(ROOT/'scripts'/path) == expected(value)
for path, value in owned['files'].items():
    assert remember(final/'owned'/path) == expected(value)
reference = read(final/'owned/independent/report.json')
assert reference == owned['reference'] == local['reference'] and reference['status'] == 'PASS'
assert (reference['fixtures'], reference['actualModels'], reference['hostRejected']) == (183, 173, 10)
assert reference['acceptedInputFingerprint'] == raw['nativeExchange']['acceptedInputFingerprint'] == '684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb'
assert reference['optimizedPythonRejected'] is True
for key, models, rejected in [('held', 74, 5), ('guard', 95, 5), ('supplemental', 4, 0)]:
    assert owned['cohorts'][key] == {'models': models, 'hostRejected': rejected}
    assert reference['cohorts'][key]['models'] == reference['cohorts'][key]['mathematicsFixturesVerified'] == models
    assert reference['cohorts'][key]['hostRejected'] == rejected
assert owned['counters']['model'] == {'numeric': reference['modelNumericBits'], 'negativeZero': reference['modelNegativeZeroBits']}
assert owned['counters']['model'] == {'numeric': 263083, 'negativeZero': 5102}
assert owned['counters']['rawGetters'] == {'numeric': 368904, 'negativeZero': 4978}
assert (reference['originalInputNumericBits'], reference['originalInputNegativeZeroBits']) == (16851, 334)
native_packets = read('reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-final-002/native-exchange/packets.json')
assert digest('reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-final-002/native-exchange/packets.json') == owned['nativePackets']
echo_counts = {'numeric': 0, 'negativeZero': 0}
getter_counts = {'numeric': 0, 'negativeZero': 0}
def count_packet(values, tokens, counter):
    assert type(values) is list and type(tokens) is list and len(values) == len(tokens)
    for value, token in zip(values, tokens):
        assert type(value) in (int, float) and struct.pack('>d', value).hex() == token
        counter['numeric'] += 1
        counter['negativeZero'] += token == '8000000000000000'
assert len(native_packets['fixtures']) == 183
for row in native_packets['fixtures']:
    count_packet(row['input'], row['inputBits'], echo_counts)
    if row['exchangeStatus'] != 0:
        continue
    for p in row['packets']:
        count_packet(p['values'], p['bits'], getter_counts)
    if row['lastMeshSummary'] is not None:
        count_packet(row['lastMeshSummary'], row['lastMeshSummaryBits'], getter_counts)
    for item in row['lastMeshRows']:
        if item['packet'] is not None:
            count_packet(item['packet'], item['bits'], getter_counts)
        assert len(item['candidates']) == len(item['candidateBits'])
        for values, tokens in zip(item['candidates'], item['candidateBits']):
            count_packet(values, tokens, getter_counts)
assert echo_counts == local['all183OriginalEchoComparisons'] == {'numeric': 7520, 'negativeZero': 12}
assert getter_counts == owned['counters']['rawGetters'] == local['actualPostReturnGetterComparisons']
assert local['actual173OwnedOriginalInputComparisons'] == {'numeric': reference['originalInputNumericBits'], 'negativeZero': reference['originalInputNegativeZeroBits']}
assert owned['counters']['originalInput'] == {key: echo_counts[key]+local['actual173OwnedOriginalInputComparisons'][key] for key in echo_counts}
assert owned['maximums'] == {'sources': 64, 'audits': 256, 'leaves': 128, 'partition': 128, 'frontier': 127, 'candidateIds': 64, 'lastMeshRows': 64, 'lastMeshCandidates': 448}
controls = read(final/'owned/independent/negative-controls.json')
assert controls == reference['negativeControls'] == local['negativeControls']
assert controls['status'] == 'PASS' and controls['count'] == len(controls['rejectedControls']) == 15
assert all(r['rejected'] is True for r in controls['rejectedControls']) and len({r['name'] for r in controls['rejectedControls']}) == 15
assert read(final/'owned/independent/optimized-command.json')['exitCode'] != 0
dtos = read(final/'owned/wasm-owned-dtos.json')
assert len(dtos['fixtures']) == 183 and sum(r['result'] is None for r in dtos['fixtures']) == 10
getter_packets = read(final/'owned/actual-getter-packets.json')
assert len(getter_packets['fixtures']) == 173
assert all(r['summary'] is None and r['summaryUnavailable'] and r['packets'] for r in getter_packets['fixtures'])
memory = owned['memory']
assert memory['initialCapacityBytes'] == memory['maximumCapacityBytes'] == memory['finalCapacityBytes'] == 67108864
assert memory['bufferChanges'] == 0 and memory['memoryGrowthExercised'] is False
assert memory['usedHeapBytes'] is None and memory['stackHighWaterBytes'] is None

# Exact current run/job origin, every step, complete captured warning multiset.
assert len(runs['runs']) == 2 and len({r['id'] for r in runs['runs']}) == 2
assert {r['name'] for r in runs['runs']} == {'Engine verification', 'pages build and deployment'}
jobs = []
for run in runs['runs']:
    assert run['head_sha'] == FEATURE and run['status'] == 'completed' and run['conclusion'] == 'success'
    rows = read(f'reports/{PREFIX}-run-{run["id"]}.json')['jobs']
    assert rows
    for job in rows:
        assert job['run_id'] == run['id'] and job['status'] == 'completed' and job['conclusion'] == 'success'
        assert job['steps'] and all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
    jobs.extend(rows)
assert len(jobs) == 4
engine = [j for j in jobs if j['name'] == 'portable-core']
assert len(engine) == 1
engine = engine[0]
workflow = source_blobs[FEATURE, '.github/workflows/verify.yml'].decode('utf-8')
step_names = ['Set up job']+re.findall(r'^      - name: (.+)$', workflow, re.M)+['Complete job']
assert len(step_names) == len(engine['steps']) == 21
assert [s['name'] for s in engine['steps']] == step_names
log_path = f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json'
log = read(log_path)
assert log['jobId'] == engine['id'] and type(log['fullLineCount']) is int
assert 0 < len(log['lines']) <= 8192
ordinals = [r['line'] for r in log['lines']]
assert all(type(n) is int for n in ordinals) and ordinals == sorted(set(ordinals)) and 1 <= ordinals[0] <= ordinals[-1] <= log['fullLineCount']
text = '\n'.join(r['text'] for r in log['lines'])
for marker in ['node scripts/verify-sphere-triangle-mesh-flight-sdk.mjs', '100% tests passed, 0 tests failed out of 41',
               '# tests '+str(local['node']), '# pass '+str(local['node']), '# fail 0', '# skipped 0',
               '200 sphere triangle mesh flight C ABI groups passed; 183 complete inputs; 173 actual models; 10 host refusals',
               'cmp build/ci/sphere-triangle-mesh-flight-native-exchange/packets.json build/ci/sphere-triangle-mesh-flight-sanitized-exchange/packets.json']:
    assert marker in text, marker
for key, value in [('actualModels', 173), ('hostRejected', 10), ('modelNumericBits', 263083), ('modelNegativeZeroBits', 5102),
                   ('originalInputNumericBits', 16851), ('originalInputNegativeZeroBits', 334), ('count', 15), ('count', 16),
                   ('numericBits', 415506), ('numericBits', 415689)]:
    assert re.search('"'+key+r'"\s*:\s*'+str(value)+r'\b', text), (key, value)
assert reference['acceptedInputFingerprint'] in text
previous_log_path = 'reports/sphere-triangle-mesh-flight-sdk-job-126481408910-excerpt.json'
previous_log = read(previous_log_path)


def warning_records(data):
    records = []
    for row in data['lines']:
        if 'warning:' not in row['text']:
            continue
        match = re.search(r'((?:core|tests|tools|reports)/[^\s:]+):(\d+):(\d+): warning:(.*)$', row['text'])
        assert match, row['text']
        records.append((match[1], int(match[2]), int(match[3]), match[4]))
    return records


old_warnings, warnings = warning_records(previous_log), warning_records(log)
assert len(old_warnings) == len(warnings) == 48 and Counter(old_warnings) == Counter(warnings)
assert 'node scripts/verify-sphere-triangle-mesh-flight-sdk.mjs' in workflow
assert 'Audit bounded flight C ABI exchange with sanitizers' in workflow

# Fresh public browser full DTOs are compared again, not inherited from local UI.
browser_dir = ROOT/f'reports/{PREFIX}-browser'
browser = read(browser_dir/'public-browser-verification.json')
assert browser['status'] == 'PASS' and browser['phase'] == 'public'
assert browser['buildId'] == public['build'] and browser['wasmBytes'] == 800982
browser_files = {'public-'+name for name in ['diagram.jpg', 'api.jpg', 'api-result.json', 'api-ax.txt', 'game.jpg', 'game-ax.txt', 'game-cover-report.json']}
assert set(browser['evidence']) == browser_files
for path, value in browser['evidence'].items():
    assert remember(browser_dir/path) == expected(value)
screens = {}
for name in ['public-diagram.jpg', 'public-api.jpg', 'public-game.jpg']:
    width, height = jpeg_dimensions((browser_dir/name).read_bytes())
    assert 900 <= width <= 4096 and 500 <= height <= 4096
    screens[name] = {'width': width, 'height': height, **digest(browser_dir/name)}
packet = read(browser_dir/'public-api-result.json')
assert packet['schema'] == 1 and packet['kind'] == 'sphere-triangle-mesh-flight-owned-browser-proof' and len(packet['rows']) == 2
browser_counts, cases = [0, 0], []
for row in packet['rows']:
    candidates = [r for r in dtos['fixtures'] if r['cohort'] == row['mode'] and r['name'] == row['name']]
    assert len(candidates) == 1 and candidates[0]['result'] is not None
    input_count = compare_tree(row['input'], candidates[0]['input'])
    result_count = compare_tree(row['result'], candidates[0]['result'])
    count = tuple(a+b for a, b in zip(input_count, result_count))
    browser_counts = [a+b for a, b in zip(browser_counts, count)]
    cases.append({'mode': row['mode'], 'name': row['name'], 'status': row['result']['status'], 'numericBits': count[0], 'negativeZeroBits': count[1]})
assert [r['result']['status'] for r in packet['rows']] == ['entry_window', 'certified_separated']
assert browser['api']['fixtures'] == 2 and browser['api']['cases'] == cases
assert (browser['api']['numericBits'], browser['api']['negativeZeroBits']) == tuple(browser_counts)
assert tuple(browser_counts) == (3891, 66)
assert packet['diagnostics']['buildId'] == public['build'] and packet['diagnostics']['wasmBytes'] == 800982
game = read(browser_dir/'public-game-cover-report.json')
state = (browser_dir/'public-game-ax.txt').read_text(encoding='utf-8-sig')
assert game['state'] == 'ready' and game['failure'] is None and game['pending'] is None and game['errors'] == []
assert '一時停止 / Pで再開' in state
kills = re.search(r'撃破\s+(\d+)', state)
assert kills and int(kills[1]) > 0
queries = game['counts']['queries']
assert type(queries) is int and queries > 0 and queries == game['counts']['checked'] == game['counts']['validated'] == len(game['records'])
assert all(r['state'] == 'completed' for r in game['records']) and any(r['clipSeconds'] == 1 for r in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId'] == public['build'] and game['startup']['diagnostics']['wasmBytes'] == 800982
asset = urlsplit(game['startup']['assetURL'])
assert asset.scheme == 'https' and asset.netloc == 'tatata93.github.io' and asset.path == '/pikapikaengine/assets/robot-back-cover.skin.json'
assert parse_qs(asset.query).get('build') == [public['build']]
assert browser['game'] == {'paused': True, 'kills': int(kills[1]), 'coverQueries': queries, 'allCompleted': True, 'boostClip1Observed': True, 'residentMeshes': 3}

capture_root = CAPTURE.parent if re.fullmatch(r'run-\d{8}-public-(?:(?:status|bytes)-)?\d+', CAPTURE.name) else CAPTURE
capture_command_files = sorted(p for p in capture_root.glob('run-*-public-*/commands.json')
                               if re.fullmatch(r'run-\d{8}-public-(?:status|bytes)-\d+', p.parent.name))
capture_command_files += sorted(p for p in capture_root.glob('run-*-public-*/*/commands.json')
                                if re.fullmatch(r'run-\d{8}-public-\d+', p.parent.parent.name)
                                and p.parent.name in {'status-initial', 'status-final', 'bytes', 'browser'})
if (CAPTURE/'commands.json').is_file() and CAPTURE/'commands.json' not in capture_command_files and 'public-summary' not in CAPTURE.name:
    capture_command_files.append(CAPTURE/'commands.json')
assert 1 <= len(capture_command_files) <= 64
public_commands = []
for path in capture_command_files:
    rows = read(path)
    assert type(rows) is list and rows
    for row in rows:
        assert row['name'] in {'status', 'bytes', 'browser'} and row['exit'] == 0
        if row['name'] == 'browser':
            assert row['args'][-3:] == [f'reports/{PREFIX}-recipes/browser-check.mjs', 'public', relative(final/'owned/wasm-owned-dtos.json')]
        else:
            assert row['args'][-3:] == [PUBLIC_RECIPE, row['name'], FEATURE]
        assert type(row['started']) is str and datetime.fromisoformat(row['started']).tzinfo is not None
        assert type(row['wallSeconds']) in (int, float) and math.isfinite(row['wallSeconds']) and row['wallSeconds'] >= 0
        for stream in ['stdout', 'stderr']:
            assert remember(row[stream]) == expected(row[stream+'Hash'])
            copied_stream = path.parent/(stream+'.txt')
            if copied_stream.is_file():
                assert remember(copied_stream) == expected(row[stream+'Hash'])
        public_commands.append({**row, 'commandFile': relative(path)})
assert {row['name'] for row in public_commands} == {'status', 'bytes', 'browser'}
latest = {phase: max((r for r in public_commands if r['name'] == phase), key=lambda r: datetime.fromisoformat(r['started'])) for phase in ['status', 'bytes', 'browser']}
latest_status = read(latest['status']['stdout'])
assert type(latest_status) is list and len(latest_status) == 2
assert {r['id'] for r in latest_status} == {r['id'] for r in runs['runs']}
for row in latest_status:
    actual = next(r for r in runs['runs'] if r['id'] == row['id'])
    assert all(row[k] == actual[k] for k in ['id', 'name', 'status', 'conclusion', 'html_url'])
assert read(latest['bytes']['stdout']) == {'status': 'PASS', 'files': 52, 'bytes': sum(r['bytes'] for r in public['files']), 'build': public['build']}
assert read(latest['browser']['stdout']) == browser
remember(PUBLIC_RECIPE)
remember(__file__)
assert len(evidence) <= 2048 and sum(v['bytes'] for v in evidence.values()) <= 512*1024*1024
report = {'schema': 1, 'status': 'PASS', 'checked': datetime.now(timezone.utc).isoformat(), 'commit': FEATURE,
          'localVerification': digest(local_path), 'finalPublicCaptureDirectory': relative(CAPTURE),
          'ctest': 41, 'node': local['node'], 'focused': local['focused'], 'skipped': 0,
          'exports': 92, 'sourceHeaders': 67, 'compiledTranslationUnits': 32, 'runtimeMembers': 91, 'licenseNotices': 7,
          'protectedFilesUnchanged': 345, 'normalizedGeneratedEntries': 25, 'generatedEntries': generated,
          'sdkArtifacts': local['artifacts'], 'sourceComparisons': source_comparisons, 'onlyNewRuntimeImportAndTwoMethods': True,
          'owned': owned, 'independentOwned': reference, 'ownedNegativeControls': controls,
          'all183OriginalEchoComparisons': echo_counts, 'actual173OwnedOriginalInputComparisons': local['actual173OwnedOriginalInputComparisons'],
          'actualPostReturnGetterComparisons': getter_counts, 'ciExecutionBudgetTransition': budget_transition,
          'inheritedRawSdk': {'report': raw_path, 'hash': digest(raw_path), 'nativeGroups': 200, 'actualModels': 173, 'hostRejected': 10,
                              'wireNegativeControls': 16, 'scope': 'Previously executed raw ABI proof retained through unchanged Native/SDK bytes; its public browser proof is not presented as fresh owned-JS execution.'},
          'memory': memory, 'summaryReadbackScope': 'Summary24 is consumed inside the owned decoder. Post-return replay captures every accessible getter, not a re-query or substituted Native summary. Separate actual raw proof and synthetic decoder tamper tests cover summary24.',
          'publicFiles': 52, 'publicBytes': sum(r['bytes'] for r in public['files']), 'webBuild': public['build'], 'modules': 52, 'entries': 25,
          'jobs': jobs, 'publicCommands': public_commands,
          'publicCommandScope': 'All saved command files and stream copies are hashed. Duplicate archived rows are retained as copies, not counted as additional executions. The latest actual status/bytes/browser outputs must match the final accepted metadata. The aggregator capture itself is excluded to avoid a self-referential hash.',
          'warnings': {'currentOccurrences': 48, 'priorOccurrences': 48, 'sameFileLineColumnDiagnosticMultiset': True, 'newDiagnostics': 0},
          'browser': browser, 'browserScreens': screens, 'independentBrowserNumericBits': browser_counts[0], 'independentBrowserNegativeZeroBits': browser_counts[1],
          'scope': 'Actual173 public owned model DTOs/10 explicit host refusals, full original input/type/bit ownership, accessible raw getter comparison, independent Fraction references and15 copied-DTO controls. Fresh public fixed2 API examples and old game compatibility are separate from a future editable flight UI or World response. No usedheap/stack watermark, natural allocation fault, repeated-substep or performance guarantee is inferred.',
          'ciEvidenceScope': 'Exact feature run/job/all-step states and finite original command/warning excerpts; complete job logs are not claimed archived.',
          'evidence': evidence}
(ROOT/f'reports/{PREFIX}-public-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['status', 'commit', 'node', 'ctest', 'publicFiles', 'publicBytes', 'webBuild']}))
