"""Accept manual flight-lab feature bytes, fresh CI and complete public browser/Blob evidence."""
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
PREFIX = 'sphere-triangle-mesh-flight-lab'
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
bytes_path = f'reports/{PREFIX}-public-bytes.json'
local, base, runs, public = map(read, [local_path, base_path, runs_path, bytes_path])
assert local['status'] == 'PASS' and local['baseCommit'] == base['baseCommit'] == 'b3d24707a0b75d1f8a7abbf26ec60c583403f515'
assert tuple(local[k] for k in ['protectedFilesUnchanged', 'normalizedGeneratedEntries', 'focused', 'node', 'skipped', 'entries', 'modules', 'exports', 'sourceHeaders', 'compiledTranslationUnits', 'runtimeMembers', 'licenseNoticesUnchanged']) == (349,25,23,684,0,26,54,92,67,32,91,7)
assert local['sdkProvenanceUnchanged'] is True
assert public['status'] == 'PASS' and public['commit'] == runs['commit'] == FEATURE
assert public['build'] == local['webBuild'] == 'cd45c7f1ac2ba5e5'
PUBLIC_RECIPE = f'reports/{PREFIX}-recipes/public.py'
public_paths = runpy.run_path(str(ROOT/PUBLIC_RECIPE), run_name='flight_lab_public_recipe')['PATHS']
assert len(public_paths) == len(set(public_paths)) == len(public['files']) == 62
assert {r['path'] for r in public['files']} == set(public_paths)
for path, value in local['evidence'].items():
    assert remember(path) == expected(value), path
assert len(base['protected']) == 349 and len(base['generatedEntries']) == 25
manifest = read('assets/pikapika-simulation.build.json')
assert manifest == base['manifest']
assert (len(manifest['sources']),len(manifest['sourceSha256']),len(manifest['linkedLibraryMembers']),len(manifest['licenses'])) == (32,67,91,7)
exports = json.loads(next(f.split('=',1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 92
for path, value in [*manifest['sourceSha256'].items(), *manifest['licenses'].items()]:
    assert digest(path)['sha256'] == value, path
assert local['artifacts'] == base['sdkArtifacts']
for path, value in local['artifacts'].items():
    assert remember(path) == expected(value)
assert local['artifacts']['assets/pikapika-simulation.wasm'] == {'bytes':800982,'sha256':'a7db41c64d2f9112ec5ee033371c391dddcb42ad23dcef713347c129a4ed015d'}
assert local['artifacts']['assets/pikapika-simulation.mjs'] == {'bytes':61661,'sha256':'d4bedfdc9dcc1a60ee816e34c43afbe51623835ca5af65b0e6f4f5937484de55'}

prior_path = 'reports/sphere-triangle-mesh-flight-js-public-verification.json'
prior = read(prior_path)
assert prior['status'] == 'PASS' and prior['node'] == 661 and prior['ctest'] == 41
assert (prior['owned']['fixtures'],prior['owned']['actualModels'],prior['owned']['hostRejected']) == (183,173,10)
assert prior['independentOwned']['negativeControls']['count'] == 15 and prior['independentOwned']['optimizedPythonRejected'] is True
assert prior['inheritedRawSdk']['nativeGroups'] == 200 and prior['inheritedRawSdk']['wireNegativeControls'] == 16
assert prior['sdkArtifacts'] == local['artifacts']
selected = set(public_paths) | set(manifest['sourceSha256']) | set(local['newSources']) | {'.github/workflows/verify.yml','CMakeLists.txt'}
requests = [(FEATURE,p) for p in selected | set(base['protected']) | set(base['generatedEntries']) | {prior_path}]
requests += [(base['baseCommit'],p) for p in set(base['protected']) | set(base['permittedOldSources']) | {prior_path,'CMakeLists.txt'}]
source_blobs = blobs(requests)
assert source_blobs[base['baseCommit'],prior_path] == source_blobs[FEATURE,prior_path]
assert source_blobs[base['baseCommit'],'CMakeLists.txt'] == source_blobs[FEATURE,'CMakeLists.txt']
for path, value in base['protected'].items():
    assert digest(path) == expected(value), path
    assert source_blobs[base['baseCommit'],path] == source_blobs[FEATURE,path], path
source_comparisons = {p:git_current(p,source_blobs[FEATURE,p]) for p in selected}

old_source_changes = {}
for path, archived in base['permittedOldSources'].items():
    old, new = source_blobs[base['baseCommit'],path], source_blobs[FEATURE,path]
    assert hash_bytes(old) == archived['gitBlob'] and old == archived['gitBlobUtf8'].encode('utf-8')
    if path == 'scripts/build-web.mjs':
        fragment = b"['tools/sphere-triangle-mesh-flight-lab.html','../','sphere-triangle-mesh-flight-lab.mjs'],"
        assert new.count(fragment) == 1
        rebuilt = new.replace(fragment,b'',1)
    elif path == 'tests/web-build.test.mjs':
        fragment = b"assert.equal(count,26,'all current game/lab/lesson entry points');"
        assert new.count(fragment) == 1
        rebuilt = new.replace(fragment,fragment.replace(b'26,',b'25,'),1)
    else:
        assert path == '.github/workflows/verify.yml'
        pattern = rb'^ *node scripts/verify-sphere-triangle-mesh-flight-lab\.mjs build/ci/sphere-triangle-mesh-flight-lab\r?\n'
        assert len(re.findall(pattern,new,re.M)) == 1
        rebuilt = re.sub(pattern,b'',new,count=1,flags=re.M)
    assert rebuilt == old
    old_source_changes[path] = {'baseGitBlob':hash_bytes(old),'featureGitBlob':hash_bytes(new),'exactOnlyAuthorizedInsertion':True}
generated = {}
for path, value in base['generatedEntries'].items():
    raw, feature = (ROOT/path).read_bytes(),source_blobs[FEATURE,path]
    assert hash_bytes(normalized_entry(raw)) == hash_bytes(normalized_entry(feature)) == value
    generated[path] = {**git_current(path,feature),'normalizedAuthored':value}
for item in public['files']:
    path = safe_path(item['path'])
    assert hash_bytes(source_blobs[FEATURE,path]) == expected(item)
    url = urlsplit(item['url'])
    assert url.scheme == 'https' and url.netloc == 'tatata93.github.io' and unquote(url.path) == '/pikapikaengine/'+path

# New-page authored comparison removes the query, unlike the unchanged old25 contract.
def new_html(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',
                  re.sub(rb'\?build=[a-f0-9]{16}',b'',raw),flags=re.S).replace(b'\r\n',b'\n')

final = ROOT/relative(local['canonicalDirectory'])
assert final.name == 'run-20261104-final-002'
commands = []
for phase in ['focused','actual','regressions']:
    rows = read(final/(phase+'-commands.json'))
    assert rows
    for row in rows:
        assert row['exit'] == 0 and row['timedOut'] is False and row['authoredStable'] is True
        assert row['authoredBefore'] == row['authoredAfter']
        for path,value in row['authoredAfter'].items():
            raw = (ROOT/path).read_bytes()
            assert hash_bytes(new_html(raw) if path.endswith('.html') else raw) == value,path
        for stream in ['stdout','stderr']:
            assert remember(row[stream]) == expected(row[stream+'Hash'])
    commands.extend(rows)

def stdout(name):
    rows = [r for r in commands if r['name'] == name]
    assert len(rows) == 1,name
    return (ROOT/rows[0]['stdout']).read_text(encoding='utf-8-sig')

for name,count in [('focused',23),('node',684)]:
    for label,value in [('tests',count),('pass',count),('fail',0),('skipped',0)]:
        assert re.search(r'(?:ℹ\s+|#\s+)'+label+r'\s+'+str(value)+r'\b',stdout(name))
assert public['build']+': 54 versioned modules' in stdout('web-build')
actual = read(final/'actual/report.json')
assert actual == local['actualPresetVerification'] and actual['status'] == 'PASS'
assert (actual['presets'],actual['actualModelPresets'],actual['hostRejected'],actual['actualOwnedMethodCalls']) == (30,29,1,30)
assert actual['sourceStable'] is True and actual['sourceBefore'] == actual['sourceAfter']
assert actual['counters'] == {'source':{'numeric':4625,'negativeZero':112},'model':{'numeric':83292,'negativeZero':1779},'saved':{'numeric':85265,'negativeZero':1835}}
for path,value in actual['sourceAfter'].items():
    assert digest(path) == expected(value),path
for path,value in actual['files'].items():
    assert remember(final/'actual'/path) == expected(value)
assert actual['wasm'] == local['artifacts']['assets/pikapika-simulation.wasm']
assert actual['maximums'] == {'audits':256,'leaves':128,'partition':128,'frontier':127,'sources':64,'candidateIds':64,'lastMeshRows':64,'lastMeshCandidates':448}
node_presets = read(final/'actual/presets.json')['rows']
assert len(node_presets) == 30 and sum(r['hostError'] is not None for r in node_presets) == 1

# Exact new feature CI, every step and unchanged warning locations/diagnostics.
assert len(runs['runs']) == 2 and len({r['id'] for r in runs['runs']}) == 2
assert {r['name'] for r in runs['runs']} == {'Engine verification','pages build and deployment'}
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
workflow = source_blobs[FEATURE,'.github/workflows/verify.yml'].decode('utf-8')
step_names = ['Set up job']+re.findall(r'^      - name: (.+)$',workflow,re.M)+['Complete job']
assert len(step_names) == len(engine['steps']) == 21
assert [s['name'] for s in engine['steps']] == step_names
log = read(f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json')
assert log['jobId'] == engine['id'] and type(log['fullLineCount']) is int and 0 < len(log['lines']) <= 8192
ordinals = [r['line'] for r in log['lines']]
assert all(type(n) is int for n in ordinals) and ordinals == sorted(set(ordinals)) and 1 <= ordinals[0] <= ordinals[-1] <= log['fullLineCount']
text = '\n'.join(r['text'] for r in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 41','# tests 684','# pass 684','# fail 0','# skipped 0',
               'node scripts/verify-sphere-triangle-mesh-flight-lab.mjs build/ci/sphere-triangle-mesh-flight-lab',
               'node scripts/verify-sphere-triangle-mesh-flight-sdk.mjs',
               '200 sphere triangle mesh flight C ABI groups passed; 183 complete inputs; 173 actual models; 10 host refusals',
               'cmp build/ci/sphere-triangle-mesh-flight-native-exchange/packets.json build/ci/sphere-triangle-mesh-flight-sanitized-exchange/packets.json']:
    assert marker in text,marker
for key,value in [('presets',30),('actualModelPresets',29),('hostRejected',1),('actualOwnedMethodCalls',30),('actualModels',173),('hostRejected',10),('count',15),('count',16),('numericBits',415506),('numericBits',415689)]:
    assert re.search('"'+key+r'"\s*:\s*'+str(value)+r'\b',text),(key,value)
for value in [4625,112,83292,1779,85265,1835]:
    assert re.search(r':\s*'+str(value)+r'\b',text),value
previous_engine = [j for j in prior['jobs'] if j['name'] == 'portable-core']
assert len(previous_engine) == 1
previous_log = read(f'reports/sphere-triangle-mesh-flight-js-job-{previous_engine[0]["id"]}-excerpt.json')

def warning_records(data):
    result = []
    for row in data['lines']:
        if 'warning:' not in row['text']:
            continue
        match = re.search(r'((?:core|tests|tools|reports)/[^\s:]+):(\d+):(\d+): warning:(.*)$',row['text'])
        assert match,row['text']
        result.append((match[1],int(match[2]),int(match[3]),match[4]))
    return result

old_warnings,warnings = warning_records(previous_log),warning_records(log)
assert len(old_warnings) == len(warnings) == 48 and Counter(old_warnings) == Counter(warnings)

# Fresh public UI, full models, recorded views and real Blob bytes.
browser_dir = ROOT/f'reports/{PREFIX}-public-browser'
browser = read(browser_dir/'browser-verification.json')
assert browser['schema'] == 1 and browser['status'] == 'PASS' and browser['phase'] == 'public'
assert browser['buildId'] == public['build'] and browser['wasmBytes'] == 800982
assert (browser['presets'],browser['actualModelPresets'],browser['hostRejected'],browser['downloads']) == (30,29,1,2)
assert browser['counts'] == actual['counts'] and browser['maximums'] == actual['maximums']
assert browser['nodeUiReport'] == {'path':relative(final/'actual/report.json'),**digest(final/'actual/report.json')}
assert type(browser['browserRetryTransientClearObserved']) is bool
assert set(browser['counters']) == {'source','nodeModel','nativeModel','canonicalOwned','downloads','visiblePanels','view'}
assert sum(c['numericBits'] for c in browser['counters'].values()) == browser['numericBits'] > 0
assert sum(c['negativeZeroBits'] for c in browser['counters'].values()) == browser['negativeZeroBits'] > 0
assert 1 <= browser['extraModelPackets'] <= 32
for path,value in browser['evidence'].items():
    assert remember(path) == expected(value),path
assert browser['displayEvidence'] and set(browser['displayEvidence']) <= set(browser['evidence'])
screens = {}
for p in browser['displayEvidence']:
    if p.lower().endswith(('.jpg','.jpeg')):
        width,height = jpeg_dimensions((ROOT/p).read_bytes())
        assert 200 <= width <= 4096 and 100 <= height <= 4096
        screens[p] = {'width':width,'height':height,**digest(p)}
assert screens and any(p.lower().endswith('.txt') for p in browser['displayEvidence'])
presets_path = relative(browser_dir/'presets.json')
assert presets_path in browser['evidence']
assert remember(presets_path) == expected(browser['evidence'][presets_path])
capture_dir = browser_dir
rows = read(presets_path)
assert len(rows) == 30 and [r['name'] for r in rows] == [r['name'] for r in node_presets]
independent_browser_counts = [0,0]
for observed,node_row in zip(rows,node_presets):
    for key in ['name','mode','cohort','fixtureName']:
        assert observed[key] == node_row[key]
    if node_row['hostError'] is not None:
        assert observed['packetFile'] is None and observed['packetBytes'] == 0 and observed['canSave'] is False and observed['errorVisible'] is True
        continue
    node_packet = read(final/'actual'/node_row['file'])
    input_packet = read(capture_dir/observed['inputFile'])
    ui_packet = read(capture_dir/observed['packetFile'])
    for count in [compare_tree(input_packet,node_packet['input']),compare_tree(ui_packet['input'],node_packet['input']),compare_tree(ui_packet['result'],node_packet['result'])]:
        independent_browser_counts = [a+b for a,b in zip(independent_browser_counts,count)]
    assert observed['errorVisible'] is False and observed['canSave'] is True
downloads_path = relative(browser_dir/'downloads.json')
assert downloads_path in browser['evidence']
assert remember(downloads_path) == expected(browser['evidence'][downloads_path])
download_rows = read(downloads_path)
assert len(browser['realDownloadEvidence']) == len(download_rows) == 2
assert sorted(r['kind'] for r in browser['realDownloadEvidence']) == ['failure','success']
for row,captured in zip(browser['realDownloadEvidence'],download_rows):
    assert all(row[k] == captured[k] for k in row)
    original_path = Path(row['actualPath'])
    assert original_path.is_absolute() and not str(original_path).startswith(('\\\\','//'))
    original = original_path.read_bytes()
    assert 0 < len(original) <= 8388608 and original.endswith(b'\n')
    stamp = {'bytes':row['bytes'],'sha256':row['sha256']}
    assert hash_bytes(original) == stamp
    for field in ['download','display']:
        archived = (capture_dir/row[field]).resolve()
        assert archived.is_relative_to(capture_dir.resolve())
        assert remember(archived) == stamp and archived.read_bytes() == original
game = read(browser_dir/'public-game-cover-report.json')
state = (browser_dir/'public-game-ax.txt').read_text(encoding='utf-8-sig')
for name in ['public-game.jpg','public-game-ax.txt']:
    assert remember(browser_dir/name)['bytes'] > 0
assert game['state'] == 'ready' and game['failure'] is None and game['pending'] is None and game['errors'] == []
assert '一時停止 / Pで再開' in state
kills = re.search(r'撃破\s+(\d+)',state)
assert kills and int(kills[1]) > 0
queries = game['counts']['queries']
assert type(queries) is int and queries > 0 and queries == game['counts']['checked'] == game['counts']['validated'] == len(game['records'])
assert all(r['state'] == 'completed' for r in game['records']) and any(r['clipSeconds'] == 1 for r in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId'] == public['build'] and game['startup']['diagnostics']['wasmBytes'] == 800982
asset = urlsplit(game['startup']['assetURL'])
assert asset.scheme == 'https' and asset.netloc == 'tatata93.github.io' and asset.path == '/pikapikaengine/assets/robot-back-cover.skin.json'
assert parse_qs(asset.query).get('build') == [public['build']]

# Final read-only status/bytes/browser command captures are separate from self.
capture_root = (ROOT/f'reports/{PREFIX}-checks').resolve()
assert capture_root.is_dir() and CAPTURE.is_relative_to(capture_root)
command_paths = sorted(p for p in capture_root.rglob('*commands.json') if 'public' in str(p.relative_to(capture_root)) and 'summary' not in p.name and 'public-summary' not in str(p))
assert 1 <= len(command_paths) <= 128
public_commands = []
failed_public_attempts = []
for p in command_paths:
    rows = read(p)
    for row in rows:
        if row['name'] not in {'status','bytes','browser-public','browser'}:
            continue
        if row['name'] in {'status','bytes'}:
            assert row['args'][-3:] == [PUBLIC_RECIPE,row['name'],FEATURE]
        else:
            assert row['args'][-4:] == [f'reports/{PREFIX}-recipes/browser-check.mjs',relative(browser_dir),relative(final/'actual/report.json'),relative(browser_dir/'browser-verification.json')]
        assert type(row['wallSeconds']) in (int,float) and math.isfinite(row['wallSeconds']) and row['wallSeconds'] >= 0
        for stream in ['stdout','stderr']:
            assert remember(row[stream]) == expected(row[stream+'Hash'])
        if row['exit'] != 0:
            # One captured, exact sandbox socket refusal. It is not successful
            # network/CI evidence and never participates in latest-success gates.
            assert relative(p) == f'reports/{PREFIX}-checks/run-20261104-public-status-001/commands.json'
            assert FEATURE == '788ac1bbe6abe10ecf0c38c3dd6dc1b6be51e61b' and row['name'] == 'status' and row['exit'] == 1
            assert row['stdoutHash'] == {'bytes':0,'sha256':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
            assert row['stderrHash'] == {'bytes':3778,'sha256':'a75b66beceb5713bac5da7011f127630cf0b8a907ae8851a7306dc44ee8f1653'}
            error_text = (ROOT/row['stderr']).read_text(encoding='utf-8')
            assert '[WinError 10013]' in error_text and 'urllib.error.URLError' in error_text
            failed_public_attempts.append({**row,'commandFile':relative(p),
                'scope':'Preserved initial sandbox socket refusal, not successful public status/CI evidence. Subsequent successful status/bytes/browser and final exact job states remain required.'})
            continue
        assert row['exit'] == 0
        public_commands.append({**row,'commandFile':relative(p)})
assert len(failed_public_attempts) == 1
assert {r['name'] for r in public_commands} >= {'status','bytes'} and any(r['name'] in {'browser-public','browser'} for r in public_commands)
latest = {kind:max((r for r in public_commands if r['name'] == kind),key=lambda r:datetime.fromisoformat(r['started'])) for kind in ['status','bytes']}
statuses = read(latest['status']['stdout'])
assert len(statuses) == 2 and {r['id'] for r in statuses} == {r['id'] for r in runs['runs']}
for status in statuses:
    actual_run = next(r for r in runs['runs'] if r['id'] == status['id'])
    assert all(status[k] == actual_run[k] for k in ['id','name','status','conclusion','html_url'])
assert read(latest['bytes']['stdout']) == {'status':'PASS','files':62,'bytes':sum(r['bytes'] for r in public['files']),'build':public['build']}
browser_command = max((r for r in public_commands if r['name'] in {'browser-public','browser'}),key=lambda r:datetime.fromisoformat(r['started']))
browser_stdout = read(browser_command['stdout'])
assert browser_stdout == {**browser,'evidence':len(browser['evidence'])}
restoration_dir = ROOT/f'reports/{PREFIX}-public-browser-development/run-001-old-handle'
restoration = read(restoration_dir/'restoration.json')
assert restoration['status'] == 'RESTORED' and len(restoration['files']) == 19
assert len({row['path'] for row in restoration['files']}) == 19
restored_blobs = blobs([(FEATURE,row['path']) for row in restoration['files']])
for row in restoration['files']:
    assert row['path'].startswith(f'reports/{PREFIX}-browser/')
    assert remember(row['path']) == {'bytes':row['restoredBytes'],'sha256':row['restoredSha256']}
    assert (ROOT/row['path']).read_bytes() == restored_blobs[FEATURE,row['path']]
    discarded = restoration_dir/Path(row['path']).name
    assert remember(discarded) == {'bytes':row['discardedBytes'],'sha256':row['discardedSha256']}
remember(PUBLIC_RECIPE)
remember(__file__)
assert len(evidence) <= 4096 and sum(v['bytes'] for v in evidence.values()) <= 512*1024*1024
report = {'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'commit':FEATURE,
          'localVerification':digest(local_path),'ctest':41,'nativeLocalExecution':'Inherited previous41 only; no fresh local Native execution was claimed. Current public CI reran41.',
          'node':684,'focused':23,'skipped':0,'exports':92,'sourceHeaders':67,'compiledTranslationUnits':32,'runtimeMembers':91,'licenseNotices':7,
          'protectedFilesUnchanged':349,'normalizedGeneratedEntries':25,'entries':26,'modules':54,'webBuild':public['build'],
          'sdkArtifacts':local['artifacts'],'sourceComparisons':source_comparisons,'oldSourceChanges':old_source_changes,'generatedEntries':generated,
          'actualPresetVerification':actual,'browser':browser,'independentPublicModelInputNumericBits':independent_browser_counts[0],
          'independentPublicModelInputNegativeZeroBits':independent_browser_counts[1],'browserScreens':screens,
          'retryScope':'The actually observed browser retry path is retained. False transient-clear observation is allowed for a cached completed retry; delayed-loader clear is separately proven by the23 Node groups, not fabricated browser latency.',
          'publicGame':{'paused':True,'kills':int(kills[1]),'queries':queries,'allCompleted':True,'boostClip1Observed':True,'residentMeshes':3},
          'inheritedOwnedAndRaw':{'path':prior_path,'hash':digest(prior_path),'ownedModels':173,'ownedHosts':10,'ownedNegatives':15,'rawInputs':183,'rawModels':173,'rawHosts':10,'rawNegatives':16,
             'scope':'Unchanged Native/SDK/old-wrapper sources retain the separate prior numerical receipt. Fresh public CI also executes the old owned/raw/Fraction acceptance; it is not counted as new UI model packets.'},
          'jobs':jobs,'warnings':{'currentOccurrences':48,'priorOccurrences':48,'sameFileLineColumnDiagnosticMultiset':True,'newDiagnostics':0},
          'publicFiles':62,'publicBytes':sum(r['bytes'] for r in public['files']),'publicCommands':public_commands,
          'failedPublicAttempts':failed_public_attempts,
          'browserCaptureHistory':{'restoration':restoration,'scope':'Nineteen wrong helper captures referenced an old tab/root. Quarantined bytes are history, not public models; original local bytes match the feature blobs exactly. Fresh public30 comparison and downloads are required above.'},
          'historicalAttempts':local['historicalAttempts'],'historicalAttemptScopes':local['historicalAttemptScopes'],
          'scope':'Fresh manual UI30/29actual models/1host refusal, complete source/model/saved bits, separate pairwise browser counters and2 real Blob downloads. Display proxies/views and cached retry are not numerical dynamics, extra query counts, natural fault injection or World response. No runtime performance, repeated-step guarantee or usedheap/stack measurement is inferred.',
          'ciEvidenceScope':'Exact current run/job/all-step states and finite original command/warning excerpts; complete remote logs are not claimed archived.',
          'evidence':evidence}
(ROOT/f'reports/{PREFIX}-public-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','commit','node','ctest','publicFiles','publicBytes','webBuild']}))


