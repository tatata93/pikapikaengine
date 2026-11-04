"""Accept current manual entry UI public evidence, preserving inherited scope."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import json
import math
import re
import struct
import subprocess

if not __debug__:
    raise SystemExit('Python assertions are required; -O is unsupported.')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-entry-lab'
MAX_FILE_BYTES = 8 * 1024 * 1024


def data_digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def digest(path):
    return data_digest(path.read_bytes())


def safe_path(value):
    assert type(value) is str and value and '\\' not in value and '\n' not in value and '\r' not in value
    path = PurePosixPath(value)
    assert not path.is_absolute() and '..' not in path.parts and path.as_posix() == value, value
    return value


def read(path):
    raw = (ROOT / safe_path(path)).read_bytes()
    assert len(raw) <= MAX_FILE_BYTES, path
    return json.loads(raw.decode('utf-8-sig'))


def expected_hash(value):
    assert type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_FILE_BYTES
    assert type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256'])
    return {'bytes': value['bytes'], 'sha256': value['sha256']}


def git_blobs(requests):
    keys = sorted(set(requests))
    assert len(keys) <= 2048
    for commit, path in keys:
        assert re.fullmatch('[0-9a-f]{40}', commit)
        safe_path(path)
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT,
                                  input=''.join(c + ':' + p + '\n' for c, p in keys).encode())
    assert len(raw) <= 128 * 1024 * 1024
    offset, result = 0, {}
    for key in keys:
        end = raw.index(b'\n', offset)
        header = raw[offset:end].split()
        assert len(header) == 3 and header[1] == b'blob', key
        size = int(header[2]);assert 0 <= size <= MAX_FILE_BYTES
        offset = end + 1
        result[key] = raw[offset:offset + size]
        assert len(result[key]) == size and raw[offset + size:offset + size + 1] == b'\n'
        offset += size + 1
    assert offset == len(raw)
    return result


def normalized_entry(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                  re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', raw), flags=re.S).replace(b'\r\n', b'\n')


def positive(value):
    return type(value) is int and value > 0


def packet_json(path):
    """All JS JSON numbers are binary64, including integer-looking -0."""
    raw = (ROOT / safe_path(path)).read_bytes()
    assert len(raw) <= MAX_FILE_BYTES
    def pairs(values):
        result = {}
        for key, value in values:
            assert key not in result, ('Duplicate packet key', key)
            result[key] = value
        return result
    def reject(value):
        raise ValueError('Nonfinite packet number: ' + value)
    result = json.loads(raw.decode('utf-8'), parse_int=float, parse_float=float,
                        parse_constant=reject, object_pairs_hook=pairs)
    count = 0
    def bounded(value, depth=0):
        nonlocal count
        count += 1
        assert count <= 1000000 and depth <= 32
        if type(value) is float:assert math.isfinite(value)
        elif type(value) is dict:
            for child in value.values():bounded(child, depth + 1)
        elif type(value) is list:
            for child in value:bounded(child, depth + 1)
        else:assert value is None or type(value) in (str, bool)
    bounded(result)
    return result


def compare_packet(left, right, counts):
    assert type(left) is type(right), (type(left), type(right))
    if type(left) is float:
        assert struct.pack('>d', left) == struct.pack('>d', right), (left, right)
        counts['numericBits'] += 1
        if left == 0 and math.copysign(1, left) < 0:counts['negativeZeroBits'] += 1
    elif type(left) is dict:
        assert left.keys() == right.keys()
        for key in left:compare_packet(left[key], right[key], counts)
    elif type(left) is list:
        assert len(left) == len(right)
        for a, b in zip(left, right):compare_packet(a, b, counts)
    else:assert left == right


def node_counts(text):
    result = {}
    for name in ['tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo']:
        values = re.findall(r'(?m)^(?:#|ℹ)\s+' + name + r'\s+(\d+)\s*$', text)
        assert len(values) == 1, (name, values)
        result[name] = int(values[0])
    assert result['tests'] == result['pass'] > 0
    assert all(result[k] == 0 for k in ['fail', 'cancelled', 'skipped', 'todo'])
    return result['tests']


local_path = f'reports/{PREFIX}-local-verification.json'
baseline_path = f'reports/{PREFIX}-baseline.json'
public_path = f'reports/{PREFIX}-public-bytes.json'
runs_path = f'reports/{PREFIX}-public-runs.json'
browser_path = f'reports/{PREFIX}-public-browser-verification.json'
prior_path = 'reports/sphere-triangle-mesh-entry-js-public-verification.json'
old_warning_path = 'reports/sphere-triangle-mesh-entry-js-job-126413438313-excerpt.json'
local, baseline, public, runs, browser, prior = map(read, [local_path, baseline_path, public_path, runs_path, browser_path, prior_path])
feature, base = public['commit'], baseline['baseCommit']
assert re.fullmatch('[0-9a-f]{40}', feature) and re.fullmatch('[0-9a-f]{40}', base)
assert local['status'] == 'PASS' and local['ctest'] == 38 and local['skipped'] == 0
assert positive(local['nodeTests']) and local['nodeTests'] == local['node'] and positive(local['dedicatedTests'])
assert local['fixtures'] == 65
assert (local['exports'], local['sourceHeaders'], local['runtimeMembers'], local['licenseNoticesUnchanged']) == (86, 61, 91, 7)
assert (local['protectedFilesUnchanged'], local['generatedEntriesOnly'], local['modules'], local['entries']) == (314, 24, 51, 25)
assert len(baseline['protected']) == 314 and len(baseline['generatedEntries']) == 24
assert public['status'] == 'PASS' and runs['commit'] == feature
assert len(public['files']) == len({r['path'] for r in public['files']}) == 93
new_sources = ['tools/sphere-triangle-mesh-entry-lab.html', 'tools/sphere-triangle-mesh-entry-lab.mjs',
               'tests/sphere-triangle-mesh-entry-lab.test.mjs', 'docs/SPHERE_TRIANGLE_MESH_ENTRY_LAB.md',
               'docs/learn/diagrams/sphere-triangle-mesh-entry-lab.svg']
source_paths = new_sources + ['scripts/build-web.mjs', 'tests/web-build.test.mjs', '.github/workflows/verify.yml']
evidence = {local_path, baseline_path, public_path, runs_path, browser_path, prior_path, old_warning_path,
            'assets/pikapika-simulation.build.json'}
requests = [(feature, r['path']) for r in public['files']]
requests += [(feature, p) for p in source_paths + list(baseline['protected']) + list(baseline['generatedEntries'])]
requests += [(base, p) for p in list(baseline['protected']) + [prior_path]]
blobs = git_blobs(requests)
for path, value in baseline['protected'].items():
    assert digest(ROOT / safe_path(path)) == expected_hash(value), path
    assert blobs[base, path] == blobs[feature, path], ('Protected committed source changed', path)
assert (ROOT / prior_path).read_bytes() == blobs[base, prior_path], 'Inherited proof changed since UI baseline'
changed = subprocess.check_output(['git', 'diff', '--name-only', base, feature, '--'], cwd=ROOT, text=True).splitlines()
assert not set(changed) & set(baseline['protected'])
generated = {}
for path, value in baseline['generatedEntries'].items():
    raw = (ROOT / safe_path(path)).read_bytes()
    assert data_digest(normalized_entry(raw)) == value, path
    assert data_digest(normalized_entry(blobs[feature, path])) == value, path
    assert raw.replace(b'\r\n', b'\n') == blobs[feature, path], path
    generated[path] = {'raw': data_digest(raw), 'featureBlob': data_digest(blobs[feature, path]),
                       'normalizedAuthored': value, 'normalization': 'Generated import map/build query only; declared CRLF-to-LF for text blob comparison.'}
source_comparisons = {}
for path in source_paths:
    raw = (ROOT / path).read_bytes();canonical = raw.replace(b'\r\n', b'\n')
    assert canonical == blobs[feature, path], path
    source_comparisons[path] = {'currentRaw': data_digest(raw), 'featureBlob': data_digest(canonical),
                                'normalization': 'Declared Git text CRLF-to-LF only' if raw != canonical else None}
for row in public['files']:
    path = safe_path(row['path'])
    assert data_digest(blobs[feature, path]) == expected_hash(row), path
    url = urlsplit(row['url'])
    assert url.scheme == 'https' and url.netloc == 'tatata93.github.io' and unquote(url.path) == '/pikapikaengine/' + path
assert set(new_sources) <= {row['path'] for row in public['files']}
manifest = read('assets/pikapika-simulation.build.json')
assert manifest == baseline['manifest']
assert (len(manifest['sourceSha256']), len(manifest['licenses']), len(manifest['linkedLibraryMembers'])) == (61, 7, 91)
for path, value in [*manifest['sourceSha256'].items(), *manifest['licenses'].items()]:
    assert sha256((ROOT / safe_path(path)).read_bytes()).hexdigest() == value, path
exports = json.loads(next(flag.split('=', 1)[1] for flag in manifest['flags'] if flag.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 86
assert local['artifacts'] == prior['artifacts']
assert local['artifacts']['assets/pikapika-simulation.wasm']['bytes'] == 719410
assert local['artifacts']['assets/pikapika-simulation.mjs']['bytes'] == 58933
for path, value in local['artifacts'].items():
    assert digest(ROOT / safe_path(path)) == expected_hash(value), path

# Current owned replay is distinct from inherited compatibility and independent
# mathematics. Host supplements are never relabelled as actual WASM models.
owned = local['owned']
assert owned['status'] == 'PASS' and (owned['fixtureCount'], owned['actualModelFixtures'], owned['hostRejected']) == (65, 62, 3)
for key, value in [('modelNumericComparisons', 105056), ('modelNegativeZeroComparisons', 3239),
                   ('originalInputNumericComparisons', 4728), ('originalInputNegativeZeroComparisons', 108)]:
    assert owned[key] == value
assert owned['source'] == prior['owned']['source'] and owned['wasm'] == local['artifacts']['assets/pikapika-simulation.wasm']
assert owned['mathematicalCorpus']['actualOwnedWasmDecoderResults'] == 62 and owned['mathematicalCorpus']['pureNativeHostSupplements'] == 3
assert owned['reference']['status'] == 'PASS'
assert (owned['reference']['fixtures'], owned['reference']['certifiedLeaves'], owned['reference']['cellAudits'], owned['reference']['lastMeshReferenceComponents']) == (65, 558, 1452, 3840)
assert owned['negativeControls'] == {'status': 'PASS', 'fixtures': 65, 'selfTestGroups': 17, 'rejectedControls': 90, 'labelAndOrderIndependent': True}
assert prior['status'] == 'PASS' and (prior['ctest'], prior['node']) == (38, 610)
assert len(prior['evidence']) > 0
command_names = []
for row in local['commands']:
    assert row['exit'] == 0 and row['authoredStable'] is True and row['authoredBefore'] == row['authoredAfter']
    command_names.append(row['name'])
    for stream in ['stdout', 'stderr']:
        path = safe_path(row[stream]);assert digest(ROOT / path) == row[stream + 'Hash'];evidence.add(path)
    for path, value in row['authoredAfter'].items():
        assert digest(ROOT / safe_path(path)) == value, path
    text = (ROOT / row['stdout']).read_text(encoding='utf-8-sig')
    if row['name'] == 'dedicated':assert node_counts(text) == local['dedicatedTests']
    if row['name'] == 'node':assert node_counts(text) == local['nodeTests']
    if row['name'] == 'ctest':assert '100% tests passed, 0 tests failed out of 38' in text
assert {'dedicated', 'node', 'ctest', 'syntax', 'web-build', 'owned-sdk', 'learn'} <= set(command_names)
exchange = [r for r in local['commands'] if r['name'] == 'owned-sdk'];assert len(exchange) == 1
exchange_dir = Path(exchange[0]['args'][-1])
if not exchange_dir.is_absolute():exchange_dir = ROOT / exchange_dir
exchange_dir = exchange_dir.resolve();exchange_relative = exchange_dir.relative_to(ROOT).as_posix()
assert read(exchange_relative + '/report.json') == owned
evidence.add(exchange_relative + '/report.json')
for name, value in owned['files'].items():
    path = safe_path(exchange_relative + '/' + safe_path(name))
    assert digest(ROOT / path) == expected_hash(value);evidence.add(path)
for path, value in owned['dependencies'].items():
    dependency = (ROOT / 'scripts' / path).resolve();dependency.relative_to(ROOT)
    assert digest(dependency) == expected_hash(value)
origins_path = exchange_relative + '/origins.json';origins = read(origins_path);evidence.add(origins_path)
assert (origins['modelCount'], origins['hostSupplementCount'], len(origins['fixtures'])) == (62, 3, 65)
assert Counter(row['origin'] for row in origins['fixtures']) == Counter({'actual-wasm-owned-js-decoder': 62, 'pure-native-host-supplement': 3})
assert [row['index'] for row in origins['fixtures']] == list(range(65))

# Run/job identifiers and measured Node counts come from the current capture.
assert len(runs['runs']) == len({r['id'] for r in runs['runs']}) == 2
assert {r['name'] for r in runs['runs']} == {'Engine verification', 'pages build and deployment'}
jobs = []
for run in runs['runs']:
    assert run['head_sha'] == feature and run['status'] == 'completed' and run['conclusion'] == 'success'
    path = f'reports/{PREFIX}-run-{run["id"]}.json';evidence.add(path)
    rows = read(path)['jobs'];assert rows
    for job in rows:
        assert job['run_id'] == run['id'] and job['status'] == 'completed' and job['conclusion'] == 'success'
        assert job['steps'] and all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
    jobs += rows
engines = [j for j in jobs if j['name'] == 'portable-core'];assert len(engines) == 1
engine = engines[0]
required_steps = {'Build and test C++ core on Linux', 'Test authoring and game logic including the built native CLI',
                  'Audit static mesh entry window independently', 'Audit bounded entry C ABI exchange with sanitizers',
                  'Audit static mesh trajectory guard independently', 'Audit trajectory C ABI exchange with sanitizers'}
assert required_steps <= {s['name'] for s in engine['steps']}
log_path = f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json';evidence.add(log_path)
log, old_log = read(log_path), read(old_warning_path)
assert log['jobId'] == engine['id'] and positive(log['fullLineCount']) and 0 < len(log['lines']) <= 4096
ordinals = [line['line'] for line in log['lines']]
assert all(type(i) is int and 1 <= i <= log['fullLineCount'] for i in ordinals) and ordinals == sorted(set(ordinals))
text = '\n'.join(line['text'] for line in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 38', f'# tests {local["nodeTests"]}', f'# pass {local["nodeTests"]}', '# fail 0', '# skipped 0',
               'PASS 76 groups; 65 complete-input finite entry fixtures', '24 sphere triangle mesh entry C ABI groups passed',
               'PASS 69 groups; 62 complete-input finite trajectory fixtures', '25 sphere triangle mesh trajectory C ABI groups passed',
               'node scripts/verify-sphere-triangle-mesh-entry-sdk.mjs']:
    assert marker in text, marker
for key, value in [('actualModelFixtures', 62), ('hostRejected', 3), ('modelNumericComparisons', 105056), ('modelNegativeZeroComparisons', 3239),
                   ('originalInputNumericComparisons', 4728), ('originalInputNegativeZeroComparisons', 108), ('selfTestGroups', 17), ('rejectedControls', 90),
                   ('certifiedLeaves', 558), ('cellAudits', 1452), ('lastMeshReferenceComponents', 3840), ('wireNumericComparisons', 147638),
                   ('negativeZeroComparisons', 3599), ('numericBits', 146130), ('negativeZeroBits', 3525)]:
    assert re.search(r'"' + key + r'"\s*:\s*' + str(value) + r'\b', text), (key, value)
warnings = lambda obj: [line['text'].split('warning:', 1)[1] for line in obj['lines'] if 'warning:' in line['text']]
assert len(warnings(log)) == len(warnings(old_log)) == 36 and Counter(warnings(log)) == Counter(warnings(old_log))
workflow = blobs[feature, '.github/workflows/verify.yml'].decode('utf-8')
for marker in ['node scripts/verify-sphere-triangle-mesh-entry-sdk.mjs build/ci/sphere-triangle-mesh-entry-fixtures.json',
               '-Werror', '-fsanitize=address,undefined',
               'cmp build/ci/sphere-triangle-mesh-entry-fixtures.json build/ci/sphere-triangle-mesh-entry-sanitized-fixtures.json']:
    assert marker in workflow

# The current actual browser proof and raw downloads are checked below once
# the shared root browser recipe has emitted its final schema. Missing evidence
# always stops the script; the local/browser PASS alone is insufficient.
assert browser['status'] == 'PASS' and browser['phase'] == 'public'
assert browser['buildId'] == local['webBuild'] and browser['wasmBytes'] == 719410
for key, value in [('presets', 25), ('actualModelPresets', 24), ('hostRejected', 1), ('separated', 2),
                   ('entryWindows', 5), ('initialPenetrations', 1), ('notCertified', 12), ('invalidInputs', 4),
                   ('expectedModelFailures', 16), ('downloads', 2)]:
    assert browser[key] == value
assert positive(browser['numericBits']) and positive(browser['negativeZeroBits']) and positive(browser['extraModelPackets'])
assert (browser['numericBits'], browser['negativeZeroBits']) == (local['browser']['numericBits'], local['browser']['negativeZeroBits'])
entry_html = blobs[feature, new_sources[0]].decode('utf-8')
assert re.search(r'\?build=([0-9a-f]{16})', entry_html).group(1) == browser['buildId']
browser_dir = f'reports/{PREFIX}-public-browser'
for name in ['presets.json', 'extras.json', 'actions.json', 'downloads.json']:
    path = browser_dir + '/' + name;read(path);evidence.add(path)
presets = read(browser_dir + '/presets.json')
local_presets_path = f'reports/{PREFIX}-local-browser/presets.json'
local_presets = read(local_presets_path);evidence.add(local_presets_path)
assert type(presets) is list and len(presets) == 25
assert [r['name'] for r in presets] == [r['name'] for r in local_presets]
assert len({r['name'] for r in presets}) == 25
copy_counts = {'numericBits': 0, 'negativeZeroBits': 0}
model_statuses = Counter();host_count = 0
for row in presets:
    assert re.fullmatch('[a-z0-9-]{1,96}', row['name'])
    assert type(row['canSave']) is bool and type(row['packetBytes']) is int
    if not row['canSave']:
        host_count += 1
        assert row['packetBytes'] == 0 and row['error']
        continue
    assert row['error'] == ''
    assert row.get('errorVisible', False) is False
    packet_path = browser_dir + '/' + row['name'] + '.json'
    local_packet_path = f'reports/{PREFIX}-local-browser/' + row['name'] + '.json'
    assert (ROOT / packet_path).stat().st_size == row['packetBytes']
    packet, local_packet = packet_json(packet_path), packet_json(local_packet_path)
    for key in ['input', 'result']:
        compare_packet(packet[key], local_packet[key], copy_counts)
    assert packet['schema'] == 1 and packet['kind'] == 'sphere-triangle-mesh-entry-lab'
    result = packet['result'];model_statuses[result['status']] += 1
    assert (len(packet['input']['triangles']), len(result['audits']), len(result['certifiedLeaves'])) == (row['rows'], row['audits'], row['leaves'])
    assert result['status'] in row['status']
    assert packet['diagnostics']['buildId'] == browser['buildId'] and packet['diagnostics']['wasmBytes'] == 719410
    assert packet['projection'] in ('xy', 'xz', 'yz')
    for selected, count in [('inspectedAudit', len(result['audits'])), ('inspectedOrdinal', len(packet['input']['triangles']))]:
        value = packet[selected]
        assert (value is None and count == 0) or (type(value) is float and value.is_integer() and 0 <= value < count)
    ordinal = packet['inspectedOrdinal']
    expected_id = None if ordinal is None else packet['input']['triangles'][int(ordinal)]['id']
    compare_packet(packet['inspectedSurfaceId'], expected_id, copy_counts)
    evidence.update([packet_path, local_packet_path])
assert host_count == 1
assert model_statuses == Counter({'separated': 2, 'entry_window': 5, 'initial_penetration': 1, 'not_certified': 12, 'invalid_input': 4})
assert copy_counts['numericBits'] > 0 and copy_counts['negativeZeroBits'] > 0
extras = read(browser_dir + '/extras.json')
local_extras_path = f'reports/{PREFIX}-local-browser/extras.json'
local_extras = read(local_extras_path);evidence.add(local_extras_path)
assert type(extras) is list and len(extras) == browser['extraModelPackets']
assert extras == local_extras and len({row['file'] for row in extras}) == len(extras)
extra_copy_counts = {'numericBits': 0, 'negativeZeroBits': 0}
for row in extras:
    assert set(row) == {'file', 'kind'} and re.fullmatch('[a-z0-9-]{1,96}', row['file'])
    assert type(row['kind']) is str and row['kind']
    path = browser_dir + '/' + row['file'] + '.json'
    local_packet_path = f'reports/{PREFIX}-local-browser/' + row['file'] + '.json'
    packet, local_packet = packet_json(path), packet_json(local_packet_path)
    assert packet['schema'] == 1 and packet['kind'] == 'sphere-triangle-mesh-entry-lab'
    for key in ['input', 'result', 'projection', 'inspectedAudit', 'inspectedOrdinal', 'inspectedSurfaceId']:
        compare_packet(packet[key], local_packet[key], extra_copy_counts)
    assert packet['diagnostics']['buildId'] == browser['buildId'] and packet['diagnostics']['wasmBytes'] == 719410
    evidence.update([path, local_packet_path])
downloads = read(browser_dir + '/downloads.json')
assert type(downloads) is list and len(downloads) == browser['downloads'] == 2
assert len({row['download'] for row in downloads}) == 2
download_counts = {'numericBits': 0, 'negativeZeroBits': 0}
for row in downloads:
    assert set(row) == {'download', 'display'}
    for key in ['download', 'display']:
        assert re.fullmatch(r'[a-z0-9-]{1,120}\.json', row[key])
    path, display_path = [browser_dir + '/' + row[key] for key in ['download', 'display']]
    downloaded, visible = packet_json(path), packet_json(display_path)
    compare_packet(downloaded, visible, download_counts)
    assert downloaded['schema'] == 1 and downloaded['kind'] == 'sphere-triangle-mesh-entry-lab'
    assert downloaded['diagnostics']['buildId'] == browser['buildId'] and downloaded['diagnostics']['wasmBytes'] == 719410
    evidence.update([path, display_path])
assert download_counts['numericBits'] > 0 and download_counts['negativeZeroBits'] > 0
expected_browser_reads = {browser_dir + '/' + name for name in ['presets.json', 'extras.json', 'actions.json', 'downloads.json', 'game-cover-report.json']}
expected_browser_reads.update(browser_dir + '/' + row['name'] + '.json' for row in presets if row['canSave'])
expected_browser_reads.update(browser_dir + '/' + row['file'] + '.json' for row in extras)
expected_browser_reads.update(browser_dir + '/' + row[key] for row in downloads for key in ['download', 'display'])
assert set(browser['evidence']) == expected_browser_reads
for path, value in browser['evidence'].items():
    assert digest(ROOT / safe_path(path)) == expected_hash(value), path
    evidence.add(path)
local_browser_evidence = local['browser']['evidence']
for path, value in local_browser_evidence.items():
    assert path.startswith(f'reports/{PREFIX}-local-browser/')
    assert digest(ROOT / safe_path(path)) == expected_hash(value), path
    evidence.add(path)
game_path, state_path = browser_dir + '/game-cover-report.json', browser_dir + '/game-state.txt'
game = read(game_path);state = (ROOT / state_path).read_text(encoding='utf-8')
assert game['state'] == 'ready' and game['failure'] is None and game['errors'] == []
assert '一時停止 / Pで再開' in state
kills = int(re.search(r'撃破 (\d+)', state).group(1));queries = game['counts']['queries']
assert kills > 0 and positive(queries) and queries == game['counts']['checked'] == game['counts']['validated']
assert game['records'] and all(r['state'] == 'completed' for r in game['records']) and any(r['clipSeconds'] == 1 for r in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False
assert (game['startup']['diagnostics']['wasmBytes'], game['startup']['diagnostics']['buildId']) == (719410, browser['buildId'])
assert browser['game'] == {'paused': True, 'kills': kills, 'coverQueries': queries, 'allCompleted': True, 'boostClip1Observed': True, 'residentMeshes': 3}
evidence.update([game_path, state_path])
browser_files = sorted((ROOT / browser_dir).glob('*'))
assert 'game.jpg' in {p.name for p in browser_files}
for path in browser_files:
    assert path.is_file() and 0 < path.stat().st_size <= MAX_FILE_BYTES
    if path.suffix == '.jpg':assert path.read_bytes().startswith(b'\xff\xd8')
    evidence.add(path.relative_to(ROOT).as_posix())
historical_browser_files = {}
for directory in sorted((ROOT / 'reports').glob(PREFIX + '-local-browser-attempt-*')):
    assert directory.is_dir()
    for path in sorted(directory.iterdir()):
        assert path.is_file()
        relative = path.relative_to(ROOT).as_posix();historical_browser_files[relative] = digest(path);evidence.add(relative)
initial_observation = f'reports/{PREFIX}-local-browser/presets-initial-error-observation.json'
assert (ROOT / initial_observation).is_file()
historical_browser_files[initial_observation] = digest(ROOT / initial_observation);evidence.add(initial_observation)
assert historical_browser_files
routing_directory = f'reports/{PREFIX}-browser-routing-attempt-001'
recovery_path = routing_directory + '/recovery.json'
recovery = read(recovery_path)
assert recovery['schema'] == 1 and recovery['status'] == 'RESTORED' and recovery['commit'] == feature
expected_restored = {f'reports/{PREFIX}-local-browser/' + name for name in
                     ['actions.json', 'capacity-earlier.json', 'capacity-last.json', 'extras.json', 'frontier-last.json']}
assert len(recovery['files']) == 5 and {row['path'] for row in recovery['files']} == expected_restored
restored_blobs = git_blobs([(recovery['commit'], safe_path(row['path'])) for row in recovery['files']])
routing_files = {recovery_path: digest(ROOT / recovery_path)}
evidence.add(recovery_path)
for row in recovery['files']:
    path = safe_path(row['path']);archive_path = routing_directory + '/' + PurePosixPath(path).name
    assert digest(ROOT / archive_path) == expected_hash(row['misrouted']), archive_path
    assert digest(ROOT / path) == expected_hash(row['restored']) == local['browserEvidence'][path], path
    assert data_digest(restored_blobs[recovery['commit'], path]) == row['restored'], path
    routing_files[archive_path] = digest(ROOT / archive_path)
    evidence.update([archive_path, path])
recovery_recipe = f'reports/{PREFIX}-recipes/recover-observation.py'
assert (ROOT / recovery_recipe).is_file()
evidence.add(recovery_recipe)
for path in (ROOT / f'reports/{PREFIX}-recipes').glob('*'):
    if path.is_file():evidence.add(path.relative_to(ROOT).as_posix())
assert len(evidence) <= 1024
evidence_hashes = {path: digest(ROOT / safe_path(path)) for path in sorted(evidence)}
assert sum(row['bytes'] for row in evidence_hashes.values()) <= 96 * 1024 * 1024
report = {
    'schema': 1, 'status': 'PASS', 'commit': feature, 'checked': datetime.now(timezone.utc).isoformat(),
    'ctest': 38, 'node': local['nodeTests'], 'skipped': 0, 'dedicatedTests': local['dedicatedTests'], 'fixtures': 65,
    'owned': owned, 'exports': 86, 'sourceHeaders': 61, 'artifacts': local['artifacts'], 'runtimeMembers': 91,
    'runtimeMembersAdded': [], 'runtimeMembersRemoved': [], 'licenseNoticesUnchanged': 7,
    'protectedFilesUnchanged': 314, 'generatedEntriesOnly': 24, 'generatedEntryComparisons': generated,
    'modules': 51, 'entries': 25, 'sourceComparisons': source_comparisons,
    'publicFiles': 93, 'publicBytes': sum(row['bytes'] for row in public['files']),
    'existingWarnings': 36, 'warningDiagnosticsUnchanged': True,
    'warningComparison': 'Exact diagnostic multiset preserving repeat multiplicity, compared to prior JS job126413438313.',
    'ciJobs': jobs, 'ciEvidenceScope': 'All current jobs/steps and bounded original Run blocks/counts/all warnings; full logs not archived.',
    'sanitizers': {'entryApiAndTestGroups': 24, 'entryApiScope': 'API/test instrumented against normal strict kernel archive.',
                   'separateAllEntryKernelGroups': 76, 'separateAllOldGuardKernelGroups': 69, 'oldTrajectoryApiAndTestGroups': 25,
                   'entryReleaseSanitizedFixtureByteComparison': 'PASS', 'scope': 'Actual current GNU CI steps; no Windows sanitizer or deliberate C++ fault injection inferred.'},
    'inheritedCompatibility': {'proof': prior_path, 'proofHash': digest(ROOT / prior_path), 'commit': prior['commit'],
                               'scope': 'Old SDK regressions inherited from the prior accepted JS proof only because all314 protected source/artifact files remain exact. They are not new local reruns.'},
    'publicBrowser': browser, 'publicGame': {**browser['game'], 'scope': 'Current public gameplay compatibility; manual entry window is not applied to game contact.'},
    'localPublicPresetPacketComparison': {**copy_counts, 'actualModelPresets': 24, 'hostRejectedPresets': 1,
                                          'scope': 'All public input/result types, keys, nulls and binary64 bits including negative zero match the separately accepted actual local packets. This is copy consistency, not an independent mathematical solver or a replacement for browser direct-SDK and download checks.'},
    'localPublicExtraPacketComparison': {**extra_copy_counts, 'packets': len(extras),
                                         'scope': 'All input/result and view fields of the same additional actual local/public browser operations compare bitwise; SDK diagnostics timing is deliberately excluded.'},
    'actualDownloadDisplayComparison': {**download_counts, 'downloads': 2,
                                        'scope': 'Complete real downloaded JSON and the recorded visible packet compare types/keys/nulls/binary64 bits including diagnostics and negative zero. Browser capture establishes actual Blob/download operation; this parser establishes retained content consistency.'},
    'attempts': local['attempts'],
    'browserAttempts': {'files': historical_browser_files,
                        'scope': 'Initial30-second collector cutoff retained partial16 model packets. Final local data came from a fresh tab in bounded batches. Initial summary observation retained text from a hidden prior host error; raw observations remain archived. Final model rows use actual visibility and an empty visible error. No source/API/model-result change is inferred from correcting the collector observation.',
                        'routingRecovery': {'record': recovery, 'files': routing_files, 'recipe': {'path': recovery_recipe, **digest(ROOT / recovery_recipe)},
                                            'scope': 'An orchestration closure kept the earlier local directory while public views were captured. All5 misrouted local proof files are archived, including empty files; each restored file exactly matches its feature Git blob and the original local-verification hash. The13 public extras were recaptured using an explicit immutable context. Misrouted captures are history, not accepted public evidence.'}},
    'mathematicalScope': 'Actual62 owned DTOs matched pinned Native bits. Independent mixed65 explicitly supplements3 host Native results, with90 mathematical negatives. Metadata/UI ownership is not a geometry solver.',
    'browserScope': 'Actual current25 manual presets, complete extra packets, and2 real Blob downloads; full source/DTO/optional/negative-zero comparison is distinct from screenshots.',
    'scope': 'Original manual entry UI only. No World/general CCD/TOI response/manifold/friction/game-contact completion, no new dependency or native/artifact change, and no actual allocation/unknown-work fault injection completion.',
    'evidence': evidence_hashes,
}
target = ROOT / f'reports/{PREFIX}-public-verification.json'
target.write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
print(json.dumps({k: report[k] for k in ['status', 'commit', 'ctest', 'node', 'publicFiles', 'publicBytes']}))
