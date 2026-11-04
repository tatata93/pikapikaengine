"""Accept captured public entry C ABI checks; never run or inherit a browser session."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import json
import re
import subprocess

if not __debug__:
    raise SystemExit('Python assertions are required; -O is unsupported.')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-entry-abi'
MAX_FILE_BYTES = 8 * 1024 * 1024

def data_digest(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def digest(path):
    return data_digest(path.read_bytes())


def read(path):
    data = (ROOT / path).read_bytes()
    assert len(data) <= MAX_FILE_BYTES, path
    return json.loads(data.decode('utf-8-sig'))


def safe_path(value):
    assert type(value) is str and value and '\\' not in value and '\n' not in value and '\r' not in value
    path = PurePosixPath(value)
    assert not path.is_absolute() and '..' not in path.parts and path.as_posix() == value, value
    return value


def expected_hash(row):
    assert type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_FILE_BYTES
    assert type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256'])
    return {'bytes': row['bytes'], 'sha256': row['sha256']}


def git_blobs(requests):
    """Read exact blobs in one bounded batch; never apply checkout conversion."""
    keys = sorted(set(requests))
    assert len(keys) <= 1024
    for commit, path in keys:
        assert re.fullmatch('[0-9a-f]{40}', commit)
        safe_path(path)
    source = ''.join(commit + ':' + path + '\n' for commit, path in keys).encode('utf-8')
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT, input=source)
    assert len(raw) <= 128 * 1024 * 1024
    offset, result = 0, {}
    for key in keys:
        end = raw.index(b'\n', offset)
        header = raw[offset:end].split()
        assert len(header) == 3 and header[1] == b'blob', key
        size = int(header[2])
        assert 0 <= size <= MAX_FILE_BYTES, key
        offset = end + 1
        result[key] = raw[offset:offset + size]
        assert len(result[key]) == size and raw[offset + size:offset + size + 1] == b'\n'
        offset += size + 1
    assert offset == len(raw)
    return result


local_path = f'reports/{PREFIX}-local-verification.json'
artifact_path = f'reports/{PREFIX}-artifacts.json'
baseline_path = f'reports/{PREFIX}-baseline.json'
public_path = f'reports/{PREFIX}-public-bytes.json'
runs_path = f'reports/{PREFIX}-public-runs.json'
browser_path = f'reports/{PREFIX}-public-browser-verification.json'
old_warning_path = 'reports/sphere-triangle-mesh-entry-job-126392164439-excerpt.json'
local, artifacts, baseline = read(local_path), read(artifact_path), read(baseline_path)
public, runs, browser = read(public_path), read(runs_path), read(browser_path)
feature = public['commit']
assert type(feature) is str and re.fullmatch('[0-9a-f]{40}', feature)
assert local['status'] == 'PASS' and (local['ctest'], local['node'], local['skipped']) == (38, 586, 0)
assert (local['nativeExchangeGroups'], local['pureEntryGroups'], local['fixtures']) == (24, 76, 65)
assert (local['exports'], local['sourceHeaders'], local['protectedFilesUnchanged'], local['generatedEntriesOnly'], local['licenseNoticesUnchanged']) == (86, 61, 303, 24, 7)
assert local['artifacts'] == artifacts and artifacts['status'] == 'PASS'
assert (artifacts['exports'], artifacts['previousExports'], artifacts['sources'], artifacts['sourceHeaders']) == (86, 80, 30, 61)
assert (artifacts['runtimeMembers'], artifacts['licenseNoticesUnchanged']) == (91, 7)
assert artifacts['runtimeMembersAdded'] == artifacts['runtimeMembersRemoved'] == []
assert (artifacts['protectedFilesUnchanged'], artifacts['generatedEntriesOnly']) == (303, 24)
assert artifacts['artifacts']['assets/pikapika-simulation.wasm']['bytes'] == 719410
assert artifacts['artifacts']['assets/pikapika-simulation.mjs']['bytes'] == 58933
assert len(baseline['protected']) == 303 and len(baseline['generatedEntries']) == 24
for path, value in baseline['protected'].items():
    assert digest(ROOT / safe_path(path)) == expected_hash(value), path
generated_comparisons = {}
for path, value in baseline['generatedEntries'].items():
    data = (ROOT / safe_path(path)).read_bytes()
    normalized = re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                        re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', data), flags=re.S).replace(b'\r\n', b'\n')
    assert data_digest(normalized) == value, path
    generated_comparisons[path] = {'currentRaw': data_digest(data), 'normalizedAuthored': value,
                                   'normalization': 'Only generated import map removal/build query placeholder and declared text CRLF-to-LF.'}
manifest = read('assets/pikapika-simulation.build.json')
assert (len(manifest['sourceSha256']), len(manifest['sources']), len(manifest['licenses']), len(manifest['linkedLibraryMembers'])) == (61, 30, 7, 91)
for path, value in manifest['sourceSha256'].items():
    assert sha256((ROOT / safe_path(path)).read_bytes()).hexdigest() == value, path
assert manifest['licenses'] == baseline['manifest']['licenses']
assert manifest['memory'] == baseline['manifest']['memory'] == artifacts['memory']
assert manifest['linkedLibraryMembers'] == baseline['manifest']['linkedLibraryMembers']
for path, value in manifest['licenses'].items():
    assert sha256((ROOT / safe_path(path)).read_bytes()).hexdigest() == value, path
assert manifest['artifacts'] == artifacts['artifacts']
for path, value in artifacts['artifacts'].items():
    assert digest(ROOT / safe_path(path)) == value, path
exports = json.loads(next(flag.split('=', 1)[1] for flag in manifest['flags'] if flag.startswith('-sEXPORTED_FUNCTIONS=')))
old_exports = json.loads(next(flag.split('=', 1)[1] for flag in baseline['manifest']['flags'] if flag.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 86 and len(old_exports) == 80
assert set(exports) - set(old_exports) == {
    '_pp_sim_sphere_triangle_mesh_entry', '_pp_sim_sphere_triangle_mesh_entry_begin', '_pp_sim_sphere_triangle_mesh_entry_append',
    '_pp_sim_sphere_triangle_mesh_entry_record', '_pp_sim_sphere_triangle_mesh_entry_last_mesh', '_pp_sim_sphere_triangle_mesh_entry_candidate'}
assert set(old_exports) <= set(exports)

native, wire, wasm = local['nativeExchange'], local['wasmWire'], local['wasmExchange']
for packet, scope in [(native, 'native'), (wasm, 'wasm-wire')]:
    assert packet['status'] == 'PASS' and packet['scope'] == scope
    assert (packet['fixtureCount'], packet['modelFixtures'], packet['hostRejected']) == (65, 62, 3)
    assert (packet['entryWindows'], packet['separated'], packet['initialPenetrations'], packet['expectedModelFailures']) == (8, 18, 2, 34)
    assert (packet['wireNumericComparisons'], packet['negativeZeroComparisons']) == (147638, 3599)
    assert (packet['audits'], packet['certifiedLeaves'], packet['partitionLeaves'], packet['frontierLeaves'], packet['lastMeshRows'], packet['lastMeshCandidates']) == (1452, 558, 866, 276, 182, 1256)
    assert (packet['maximumSourceCount'], packet['maximumAuditCount'], packet['maximumPartitionCount'], packet['maximumCertifiedLeafCount'], packet['maximumFrontierCount']) == (64, 256, 128, 128, 127)
    controls = packet['packetNegativeControls']
    assert controls['count'] == 27 and controls['allRejected'] and len(controls['controls']) == 27 and all(c['rejected'] for c in controls['controls'])
    assert packet['mathematicalNegativeControls'] == {'status': 'PASS', 'fixtures': 65, 'selfTestGroups': 17, 'rejectedControls': 90, 'labelAndOrderIndependent': True}
    ref = packet['reference']
    assert ref['status'] == 'PASS' and (ref['fixtures'], ref['certifiedLeaves'], ref['cellAudits'], ref['lastMeshReferenceComponents']) == (65, 558, 1452, 3840)
assert wire['status'] == 'PASS' and (wire['fixtures'], wire['accepted'], wire['hostRejected'], wire['numericBits'], wire['negativeZeroBits']) == (65, 62, 3, 146130, 3525)
assert wire['wasm'] == artifacts['artifacts']['assets/pikapika-simulation.wasm']
owned = local['ownedSdkRegression']
assert owned['status'] == 'PASS' and (owned['actualModelFixtures'], owned['hostRejected'], owned['modelNumericComparisons'], owned['originalInputNumericComparisons']) == (59, 3, 50663, 3877)
assert owned['negativeControls']['rejectedControls'] == 71

# The Native-only test expectation was corrected after the successful WASM
# compilation. It is not a compiled SDK input. All61 real inputs stay pinned.
stable_test_exception = []
for command in local['commands']:
    assert command['exit'] == 0 and command['authoredStable']
    for stream in ['stdout', 'stderr']:
        assert digest(ROOT / safe_path(command[stream])) == command[stream + 'Hash']
    for path, value in command['authoredAfter'].items():
        current = digest(ROOT / safe_path(path))
        if current != value:
            assert command['name'] == 'wasm-build' and path == 'tests/sphere_triangle_mesh_entry_sdk_tests.cpp'
            assert path not in manifest['sourceSha256']
            stable_test_exception.append({'command': command['name'], 'path': path, 'atOriginalBuild': value, 'currentNativeTest': current,
                                          'scope': 'Test-only fixture assertion correction; no compiled WASM source/header changed.'})
        else:
            assert current == value
initial_dir = f'reports/{PREFIX}-checks/run-20261104-initial'
initial_commands_path = initial_dir + '/native-commands.json'
initial_commands = read(initial_commands_path)
failed_test = initial_commands[-1]
assert failed_test['name'] == 'entry-sdk' and failed_test['exit'] == 1
for stream in ['stdout', 'stderr']:
    assert digest(ROOT / safe_path(failed_test[stream])) == failed_test[stream + 'Hash']
assert 'FAIL after 3 groups: Later certified island disappeared into prefix' in (ROOT / failed_test['stderr']).read_text(encoding='utf-8')
assert len(re.findall(r'^PASS ', (ROOT / failed_test['stdout']).read_text(encoding='utf-8'), flags=re.M)) == 3

assert public['status'] == 'PASS' and runs['commit'] == feature and len(public['files']) == 81
assert len(runs['runs']) == 2 and {r['name'] for r in runs['runs']} == {'Engine verification', 'pages build and deployment'}
evidence = {local_path, artifact_path, baseline_path, public_path, runs_path, browser_path, old_warning_path,
            initial_commands_path, failed_test['stdout'], failed_test['stderr'], 'assets/pikapika-simulation.build.json'}
for command in local['commands']:
    evidence.update([command['stdout'], command['stderr']])
original_packets = initial_dir + '/native-exchange/packets.json'
final_packets = f'reports/{PREFIX}-checks/run-20261104-final/native-exchange/packets.json'
assert (ROOT / original_packets).read_bytes() == (ROOT / final_packets).read_bytes()
native_attempt_packet_hashes = {path: digest(ROOT / path) for path in [original_packets, final_packets]}
jobs = []
for run in runs['runs']:
    assert run['head_sha'] == feature and run['status'] == 'completed' and run['conclusion'] == 'success'
    path = f'reports/{PREFIX}-run-{run["id"]}.json'
    evidence.add(path)
    rows = read(path)['jobs']
    assert rows
    for job in rows:
        # Connector jobs do not provide head_sha; the enclosing run pins it.
        assert job['run_id'] == run['id'] and job['status'] == 'completed' and job['conclusion'] == 'success'
        assert job['steps'] and all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
    jobs.extend(rows)
engine = [job for job in jobs if job['name'] == 'portable-core']
assert len(engine) == 1
engine = engine[0]
required_steps = {'Build and test C++ core on Linux', 'Test authoring and game logic including the built native CLI',
                  'Audit bounded entry C ABI exchange with sanitizers', 'Audit static mesh entry window independently',
                  'Audit static mesh trajectory guard independently', 'Audit trajectory C ABI exchange with sanitizers'}
assert required_steps <= {step['name'] for step in engine['steps']}
log_path = f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json'
evidence.add(log_path)
log, old_log = read(log_path), read(old_warning_path)
assert log['jobId'] == engine['id'] and type(log['fullLineCount']) is int
assert 0 < len(log['lines']) <= 4096
ordinals = [line['line'] for line in log['lines']]
assert all(type(n) is int and 1 <= n <= log['fullLineCount'] for n in ordinals) and ordinals == sorted(set(ordinals))
text = '\n'.join(line['text'] for line in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 38', '# tests 586', '# pass 586', '# fail 0', '# skipped 0',
               '24 sphere triangle mesh entry C ABI groups passed', 'PASS 76 groups; 65 complete-input finite entry fixtures',
               'PASS 69 groups; 62 complete-input finite trajectory fixtures', '25 sphere triangle mesh trajectory C ABI groups passed']:
    assert marker in text, marker
for key, value in [('wireNumericComparisons', 147638), ('negativeZeroComparisons', 3599), ('numericBits', 146130), ('negativeZeroBits', 3525),
                   ('modelFixtures', 62), ('hostRejected', 3), ('audits', 1452), ('certifiedLeaves', 558), ('partitionLeaves', 866),
                   ('frontierLeaves', 276), ('lastMeshRows', 182), ('lastMeshCandidates', 1256), ('selfTestGroups', 17), ('rejectedControls', 90),
                   ('actualModelFixtures', 59), ('modelNumericComparisons', 50663), ('originalInputNumericComparisons', 3877)]:
    assert re.search(r'"' + key + r'"\s*:\s*' + str(value) + r'\b', text), (key, value)
warnings = lambda source: [line['text'].split('warning:', 1)[1] for line in source['lines'] if 'warning:' in line['text']]
assert len(warnings(log)) == len(warnings(old_log)) == 36 and Counter(warnings(log)) == Counter(warnings(old_log))

sources = ['core/include/pikapika/simulation_api.h', 'core/src/simulation_api.cpp', 'tests/sphere_triangle_mesh_entry_sdk_tests.cpp',
           'tools/sphere_triangle_mesh_entry_sdk_probe.cpp', 'scripts/verify-sphere-triangle-mesh-entry-native-sdk.py',
           'scripts/verify-sphere-triangle-mesh-entry-wasm-wire.mjs', 'scripts/build-simulation.mjs', 'CMakeLists.txt', '.github/workflows/verify.yml']
assert len({row['path'] for row in public['files']}) == 81
blobs = git_blobs([(feature, safe_path(row['path'])) for row in public['files']] + [(feature, path) for path in sources])
for row in public['files']:
    path = safe_path(row['path'])
    assert data_digest(blobs[feature, path]) == expected_hash(row), path
    url = urlsplit(row['url'])
    assert url.scheme == 'https' and url.netloc == 'tatata93.github.io' and unquote(url.path) == '/pikapikaengine/' + path
source_comparisons = {}
for path in sources:
    raw = (ROOT / path).read_bytes()
    normalization = 'Declared Git text CRLF-to-LF only' if b'\r\n' in raw else None
    canonical = raw.replace(b'\r\n', b'\n') if normalization else raw
    assert canonical == blobs[feature, path], path
    source_comparisons[path] = {'currentRaw': data_digest(raw), 'featureBlob': data_digest(canonical), 'normalization': normalization}
changed = subprocess.check_output(['git', 'diff', '--name-only', baseline['baseCommit'], feature, '--'], cwd=ROOT, text=True).splitlines()
assert not (set(changed) & set(baseline['protected'])), 'Old protected numerical/game source changed in feature'
workflow = blobs[feature, '.github/workflows/verify.yml'].decode('utf-8')
api_step = workflow.split('      - name: Audit bounded entry C ABI exchange with sanitizers\n', 1)[1].split('      - name: ', 1)[0]
for token in ['-Werror', '-c tests/sphere_triangle_mesh_entry_sdk_tests.cpp', '-c tools/sphere_triangle_mesh_entry_sdk_probe.cpp',
              '-fsanitize=address,undefined', 'core/src/simulation_api.cpp tests/sphere_triangle_mesh_entry_sdk_tests.cpp build/ci/libpikapika_core.a']:
    assert token in api_step, token
pure_step = workflow.split('      - name: Audit static mesh entry window independently\n', 1)[1].split('      - name: ', 1)[0]
for token in ['-fsanitize=address,undefined', 'core/src/interval.cpp core/src/sphere_triangle.cpp core/src/sphere_triangle_mesh.cpp core/src/sphere_triangle_mesh_entry.cpp',
              'cmp build/ci/sphere-triangle-mesh-entry-fixtures.json build/ci/sphere-triangle-mesh-entry-sanitized-fixtures.json']:
    assert token in pure_step, token

assert browser['status'] == 'PASS' and browser['phase'] == 'public'
assert browser['guardDefault'] == {'numericBits': 324, 'negativeZeroBits': 24, 'status': 'separated'}
assert browser['wasmBytes'] == 719410 and browser['buildId'] == local['webBuild']
build_html = blobs[feature, 'tools/sphere-triangle-mesh-trajectory-lab.html'].decode('utf-8')
assert re.search(r'\?build=([0-9a-f]{16})', build_html).group(1) == browser['buildId']
browser_dir = f'reports/{PREFIX}-public-browser'
guard_path = browser_dir + '/guard-default.json'
game_path = browser_dir + '/game-cover-report.json'
state_path = browser_dir + '/game-state.txt'
guard, game = read(guard_path), read(game_path)
state = (ROOT / state_path).read_text(encoding='utf-8')
assert guard['schema'] == 1 and guard['kind'] == 'sphere-triangle-mesh-trajectory-lab' and guard['result']['status'] == 'separated'
assert (guard['diagnostics']['wasmBytes'], guard['diagnostics']['buildId']) == (719410, browser['buildId'])
assert game['state'] == 'ready' and game['failure'] is None and game['errors'] == []
assert '一時停止 / Pで再開' in state
kills = int(re.search(r'撃破 (\d+)', state).group(1))
queries = game['counts']['queries']
assert type(queries) is int and queries > 0 and queries == game['counts']['checked'] == game['counts']['validated']
assert game['records'] and all(row['state'] == 'completed' for row in game['records']) and any(row['clipSeconds'] == 1 for row in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False
assert (game['startup']['diagnostics']['wasmBytes'], game['startup']['diagnostics']['buildId']) == (719410, browser['buildId'])
assert kills > 0 and browser['game']['paused'] and browser['game']['kills'] == kills and browser['game']['coverQueries'] == queries
assert browser['game']['allCompleted'] and browser['game']['boostClip1Observed'] and browser['game']['residentMeshes'] == 3
evidence.update([guard_path, game_path, state_path])
images = sorted((ROOT / browser_dir).glob('*.jpg'))
assert {'diagram.jpg', 'game.jpg'} <= {image.name for image in images}, 'Original public SVG and game screenshots required'
for image in images:
    assert 100 < image.stat().st_size <= MAX_FILE_BYTES and image.read_bytes().startswith(b'\xff\xd8')
    evidence.add(image.relative_to(ROOT).as_posix())
for path in (ROOT / f'reports/{PREFIX}-recipes').glob('*.py'):
    evidence.add(path.relative_to(ROOT).as_posix())
evidence.add(f'reports/{PREFIX}-recipes/browser-check.mjs')
assert len(evidence) <= 512
evidence_hashes = {p: digest(ROOT / safe_path(p)) for p in sorted(evidence)}
assert sum(v['bytes'] for v in evidence_hashes.values()) <= 64 * 1024 * 1024

report = {
    'schema': 1, 'status': 'PASS', 'commit': feature, 'checked': datetime.now(timezone.utc).isoformat(),
    'ctest': 38, 'node': 586, 'skipped': 0, 'nativeExchangeGroups': 24, 'pureEntryGroups': 76, 'fixtures': 65,
    'nativeExchange': native, 'wasmWire': wire, 'wasmExchange': wasm, 'ownedSdkRegression': owned,
    'exports': 86, 'sourceHeaders': 61, 'artifacts': artifacts, 'runtimeMembers': 91, 'runtimeMembersAdded': [], 'runtimeMembersRemoved': [],
    'protectedFilesUnchanged': 303, 'generatedEntriesOnly': 24, 'generatedEntryComparisons': generated_comparisons, 'licenseNoticesUnchanged': 7,
    'publicFiles': 81, 'publicBytes': sum(row['bytes'] for row in public['files']), 'sourceComparisons': source_comparisons,
    'existingWarnings': 36, 'warningDiagnosticsUnchanged': True, 'warningComparison': 'Exact compiler diagnostic multiset including repeated warnings, independent of parallel build order.',
    'ciJobs': jobs, 'ciEvidenceScope': 'All job/step states plus bounded original log excerpts containing all compiler warnings; full logs are not archived.',
    'sanitizers': {'entryApiAndTestGroups': 24, 'entryApiScope': 'API/test fully instrumented, linked to normal strict kernel archive.',
                   'separateEntryAllKernelGroups': 76, 'separateOldGuardAllKernelGroups': 69, 'oldTrajectoryApiAndTestGroups': 25,
                   'strictNewTestAndProbeWarningAudits': 'PASS', 'entryReleaseSanitizedFixtureByteComparison': 'PASS', 'platform': 'Public GNU ASan/UBSan; no Windows sanitizer success inferred.'},
    'publicBrowser': browser, 'publicGame': {'paused': True, 'kills': kills, 'coverQueries': queries, 'allCompleted': True, 'boostClip1Observed': True, 'residentMeshes': 3,
                                          'scope': 'Actual current public session; diagnostic counters are cumulative. Decorative cover/game compatibility, not entry-window contact application.'},
    'initialTestAttempt': {'status': 'Preserved original failure', 'passedBeforeFailure': 3, 'source': initial_commands_path,
                           'correction': local['attempts']['initial'], 'kernelOrApiChangedToFitExpectation': False,
                           'originalAndCorrectedNativePacketsIdentical': native_attempt_packet_hashes},
    'wasmBuildNativeTestException': stable_test_exception,
    'mathematicalScope': 'Pinned pure65 Fraction corpus and90 controls are a separate scope. All62 exchange-accepted model fields are independently encoded and compared to Native/actual WASM packets; host3 were not model calls. Raw Node and Python comparison counts cover different fields and are not added together.',
    'browserScope': 'New public old-guard default324 numeric bits/24 negative zeros and actual game shooting/boost/kills/pause checked against the new SDK. No inherited prior browser proof; the new entry API has no owned JS decoder/UI yet.',
    'scope': 'Read-only raw entry C ABI and actual WASM. No World/TOI/contact response, game entry application, deliberate allocation/unknown-work fault injection or new physical-time claim.',
    'evidence': evidence_hashes,
}
target = ROOT / f'reports/{PREFIX}-public-verification.json'
target.write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
print(json.dumps({key: report[key] for key in ['status', 'commit', 'ctest', 'node', 'publicFiles', 'publicBytes']}))


