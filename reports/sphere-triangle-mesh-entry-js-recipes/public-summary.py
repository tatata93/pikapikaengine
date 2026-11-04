"""Accept captured owned entry JS, public byte, CI and current browser evidence."""
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
PREFIX = 'sphere-triangle-mesh-entry-js'
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
baseline_path = f'reports/{PREFIX}-baseline.json'
public_path = f'reports/{PREFIX}-public-bytes.json'
runs_path = f'reports/{PREFIX}-public-runs.json'
browser_path = f'reports/{PREFIX}-public-browser-verification.json'
old_warning_path = 'reports/sphere-triangle-mesh-entry-abi-job-126402141477-excerpt.json'
local, baseline = read(local_path), read(baseline_path)
public, runs, browser = read(public_path), read(runs_path), read(browser_path)
feature = public['commit']
assert type(feature) is str and re.fullmatch('[0-9a-f]{40}', feature)
assert local['status'] == 'PASS' and (local['ctest'], local['nodeTests'], local['node'], local['skipped']) == (38, 610, 610, 0)
assert (local['dedicatedTests'], local['learnTests'], local['fixtures']) == (24, 12, 65)
assert (local['exports'], local['sourceHeaders'], local['runtimeMembers'], local['licenseNoticesUnchanged']) == (86, 61, 91, 7)
assert (local['protectedFilesUnchanged'], local['generatedEntriesOnly'], local['modules'], local['entries']) == (312, 24, 50, 24)
assert len(baseline['protected']) == 312 and len(baseline['generatedEntries']) == 24
evidence = {local_path, baseline_path, public_path, runs_path, browser_path, old_warning_path,
            'assets/pikapika-simulation.build.json'}
for path, expected in baseline['protected'].items():
    assert digest(ROOT / safe_path(path)) == expected_hash(expected), path
generated = {}
for path, expected in baseline['generatedEntries'].items():
    raw = (ROOT / safe_path(path)).read_bytes()
    canonical = re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                       re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', raw), flags=re.S).replace(b'\r\n', b'\n')
    assert data_digest(canonical) == expected, path
    generated[path] = {'raw': data_digest(raw), 'normalizedAuthored': expected,
                       'normalization': 'Generated import map removal/build query placeholder and declared text CRLF-to-LF only.'}
manifest = read('assets/pikapika-simulation.build.json')
assert manifest == baseline['manifest'], 'JS-only milestone changed the SDK manifest'
assert (len(manifest['sources']), len(manifest['sourceSha256']), len(manifest['licenses']), len(manifest['linkedLibraryMembers'])) == (30, 61, 7, 91)
for path, sha in [*manifest['sourceSha256'].items(), *manifest['licenses'].items()]:
    assert sha256((ROOT / safe_path(path)).read_bytes()).hexdigest() == sha, path
exports = json.loads(next(flag.split('=', 1)[1] for flag in manifest['flags'] if flag.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 86
for path, value in local['artifacts'].items():
    assert digest(ROOT / safe_path(path)) == expected_hash(value), path
assert set(local['artifacts']) == {'assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json'}
assert local['artifacts']['assets/pikapika-simulation.wasm'] == {'bytes': 719410, 'sha256': 'd1ece57ca29df06e91cf10c7b598a9b073a86b63959d4ef76e2e0da5f84d5f58'}
assert local['artifacts']['assets/pikapika-simulation.mjs'] == {'bytes': 58933, 'sha256': '7de3e5160b478aea5fcdc10cad4187e4641c592561414b1d99acaeb184562952'}

owned, old_owned = local['owned'], local['oldOwned']
assert owned['status'] == 'PASS' and (owned['fixtureCount'], owned['actualModelFixtures'], owned['hostRejected']) == (65, 62, 3)
assert (owned['separated'], owned['entryWindows'], owned['initialPenetrations'], owned['expectedModelFailures']) == (18, 8, 2, 34)
assert (owned['modelNumericComparisons'], owned['modelNegativeZeroComparisons'], owned['originalInputNumericComparisons'], owned['originalInputNegativeZeroComparisons']) == (105056, 3239, 4728, 108)
assert (owned['hostOutputNumericComparisons'], owned['hostOutputNegativeZeroComparisons']) == (52, 0)
assert owned['wasm'] == local['artifacts']['assets/pikapika-simulation.wasm']
assert owned['source'] == {'bytes': 2490705, 'sha256': 'f63520a3d79f2558879c2dff15a1f2b48dfe09fbee920c12cf828c712044a407'}
ownership = owned['ownership']
assert (ownership['callerMutationChecks'], ownership['corpusDtosRetained'], ownership['extraModelCalls'], ownership['extraModelNumericComparisons'], ownership['extraModelNegativeZeroComparisons']) == (62, 62, 3, 636, 40)
assert all(ownership[key] is True for key in ['originalInputSnapshotSeparate', 'lastMeshRowSourcesSeparate', 'priorAndSubsequentDtosSeparate', 'exchangeScratchSeparate', 'publicOutputCopySeparate'])
reference = owned['reference']
assert reference['status'] == 'PASS' and (reference['fixtures'], reference['certifiedLeaves'], reference['cellAudits'], reference['lastMeshReferenceComponents']) == (65, 558, 1452, 3840)
assert (reference['entryWidthReferences'], reference['positiveIslandsBeyondPrefix'], reference['workExactFixtures']) == (8, 17, 65)
assert reference['inputFingerprint'] == '486bfaf8aa19f4d5a8428dbed070b56093b44c8ca7013c18e310a6dae7167404'
assert owned['negativeControls'] == {'status': 'PASS', 'fixtures': 65, 'selfTestGroups': 17, 'rejectedControls': 90, 'labelAndOrderIndependent': True}
math = owned['mathematicalCorpus']
assert (math['fixtures'], math['actualOwnedWasmDecoderResults'], math['pureNativeHostSupplements']) == (65, 62, 3)
assert old_owned['status'] == 'PASS' and (old_owned['actualModelFixtures'], old_owned['hostRejected'], old_owned['modelNumericComparisons'], old_owned['originalInputNumericComparisons']) == (59, 3, 50663, 3877)
assert old_owned['negativeControls']['rejectedControls'] == 71

# Canonical final runs must be stable against current files. Unsuccessful and
# transitional attempts remain in the local record, never substitute for these.
for row in local['commands']:
    assert row['exit'] == 0 and row['authoredStable'] is True and row['authoredBefore'] == row['authoredAfter']
    for stream in ['stdout', 'stderr']:
        path = safe_path(row[stream]);assert digest(ROOT / path) == row[stream + 'Hash'];evidence.add(path)
    for path, expected in row['authoredAfter'].items():
        assert digest(ROOT / safe_path(path)) == expected, path
owned_commands = [row for row in local['commands'] if row['name'] == 'owned-sdk']
assert len(owned_commands) == 1
owned_dir = Path(owned_commands[0]['args'][-1])
if not owned_dir.is_absolute():
    owned_dir = ROOT / owned_dir
owned_dir = owned_dir.resolve()
owned_relative = owned_dir.relative_to(ROOT).as_posix()
assert read(owned_relative + '/report.json') == owned
evidence.add(owned_relative + '/report.json')
for name, expected in owned['files'].items():
    path = safe_path(owned_relative + '/' + safe_path(name))
    assert digest(ROOT / path) == expected_hash(expected), path
    evidence.add(path)
for relative, expected in owned['dependencies'].items():
    dependency = (ROOT / 'scripts' / relative).resolve()
    path = dependency.relative_to(ROOT).as_posix()
    assert digest(dependency) == expected_hash(expected), path
origins = read(owned_relative + '/origins.json')
assert (origins['modelCount'], origins['hostSupplementCount'], len(origins['fixtures'])) == (62, 3, 65)
assert Counter(row['origin'] for row in origins['fixtures']) == Counter({'actual-wasm-owned-js-decoder': 62, 'pure-native-host-supplement': 3})
assert [row['index'] for row in origins['fixtures']] == list(range(65))
assert local['attempts'], 'Original unsuccessful and transition attempts must remain explained'

assert public['status'] == 'PASS' and runs['commit'] == feature
assert len(public['files']) == len({row['path'] for row in public['files']}) == 88
assert len(runs['runs']) == len({run['id'] for run in runs['runs']}) == 2
assert {run['name'] for run in runs['runs']} == {'Engine verification', 'pages build and deployment'}
jobs = []
for run in runs['runs']:
    assert run['head_sha'] == feature and run['status'] == 'completed' and run['conclusion'] == 'success'
    path = f'reports/{PREFIX}-run-{run["id"]}.json';evidence.add(path)
    rows = read(path)['jobs'];assert rows
    for job in rows:
        # Connector jobs expose run_id, not head_sha. Pin the enclosing run.
        assert job['run_id'] == run['id'] and job['status'] == 'completed' and job['conclusion'] == 'success'
        assert job['steps'] and all(step['status'] == 'completed' and step['conclusion'] == 'success' for step in job['steps'])
    jobs.extend(rows)
engines = [job for job in jobs if job['name'] == 'portable-core'];assert len(engines) == 1
engine = engines[0]
assert {'Build and test C++ core on Linux', 'Test authoring and game logic including the built native CLI',
        'Audit static mesh entry window independently', 'Audit bounded entry C ABI exchange with sanitizers',
        'Audit static mesh trajectory guard independently', 'Audit trajectory C ABI exchange with sanitizers'} <= {step['name'] for step in engine['steps']}
log_path = f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json';evidence.add(log_path)
log, old_log = read(log_path), read(old_warning_path)
assert log['jobId'] == engine['id'] and type(log['fullLineCount']) is int and 0 < len(log['lines']) <= 4096
ordinals = [line['line'] for line in log['lines']]
assert all(type(i) is int and 1 <= i <= log['fullLineCount'] for i in ordinals) and ordinals == sorted(set(ordinals))
text = '\n'.join(row['text'] for row in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 38', '# tests 610', '# pass 610', '# fail 0', '# skipped 0',
               'PASS 76 groups; 65 complete-input finite entry fixtures', '24 sphere triangle mesh entry C ABI groups passed',
               'PASS 69 groups; 62 complete-input finite trajectory fixtures', '25 sphere triangle mesh trajectory C ABI groups passed',
               'node scripts/verify-sphere-triangle-mesh-entry-sdk.mjs']:
    assert marker in text, marker
for key, value in [('actualModelFixtures', 62), ('hostRejected', 3), ('modelNumericComparisons', 105056), ('modelNegativeZeroComparisons', 3239),
                   ('originalInputNumericComparisons', 4728), ('originalInputNegativeZeroComparisons', 108), ('selfTestGroups', 17), ('rejectedControls', 90),
                   ('certifiedLeaves', 558), ('cellAudits', 1452), ('lastMeshReferenceComponents', 3840), ('wireNumericComparisons', 147638),
                   ('negativeZeroComparisons', 3599), ('numericBits', 146130), ('negativeZeroBits', 3525),
                   ('actualModelFixtures', 59), ('modelNumericComparisons', 50663), ('originalInputNumericComparisons', 3877)]:
    assert re.search(r'"' + key + r'"\s*:\s*' + str(value) + r'\b', text), (key, value)
warnings = lambda obj: [line['text'].split('warning:', 1)[1] for line in obj['lines'] if 'warning:' in line['text']]
assert len(warnings(log)) == len(warnings(old_log)) == 36 and Counter(warnings(log)) == Counter(warnings(old_log))

sources = ['engine/simulation.mjs', 'engine/sphere-triangle-mesh-entry.mjs', 'tests/sphere_triangle_mesh_entry_sdk.test.mjs',
           'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs', '.github/workflows/verify.yml',
           'reports/sphere-triangle-mesh-entry-js-browser/index.html']
blobs = git_blobs([(feature, safe_path(row['path'])) for row in public['files']] + [(feature, path) for path in sources])
for row in public['files']:
    path = safe_path(row['path']);assert data_digest(blobs[feature, path]) == expected_hash(row), path
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
assert not set(changed) & set(baseline['protected']), 'Protected old source/artifacts/game changed in the feature'
workflow = blobs[feature, '.github/workflows/verify.yml'].decode('utf-8')
assert 'node scripts/verify-sphere-triangle-mesh-entry-sdk.mjs build/ci/sphere-triangle-mesh-entry-fixtures.json build/ci/sphere-triangle-mesh-entry-owned-sdk' in workflow
api_step = workflow.split('      - name: Audit bounded entry C ABI exchange with sanitizers\n', 1)[1].split('      - name: ', 1)[0]
for token in ['-Werror', '-c tests/sphere_triangle_mesh_entry_sdk_tests.cpp', '-c tools/sphere_triangle_mesh_entry_sdk_probe.cpp',
              '-fsanitize=address,undefined', 'core/src/simulation_api.cpp tests/sphere_triangle_mesh_entry_sdk_tests.cpp build/ci/libpikapika_core.a']:
    assert token in api_step, token
pure_step = workflow.split('      - name: Audit static mesh entry window independently\n', 1)[1].split('      - name: ', 1)[0]
for token in ['-fsanitize=address,undefined', 'core/src/interval.cpp core/src/sphere_triangle.cpp core/src/sphere_triangle_mesh.cpp core/src/sphere_triangle_mesh_entry.cpp',
              'cmp build/ci/sphere-triangle-mesh-entry-fixtures.json build/ci/sphere-triangle-mesh-entry-sanitized-fixtures.json']:
    assert token in pure_step, token

assert browser['status'] == 'PASS' and browser['phase'] == 'public'
assert browser['entry'] == local['browser']['entry'] == {'numericBits': 3255, 'negativeZeroBits': 24,
       'nativeModel': {'numericBits': 3312, 'negativeZeroBits': 20}, 'status': 'entry_window', 'audits': 61, 'partition': 41}
assert browser['wasmBytes'] == 719410 and browser['buildId'] == local['webBuild']
proof_html = blobs[feature, sources[-1]].decode('utf-8')
assert re.search(r'\?build=([0-9a-f]{16})', proof_html).group(1) == browser['buildId']
browser_dir = f'reports/{PREFIX}-public-browser'
packet_path, game_path, state_path = [browser_dir + '/' + name for name in ['owned-case.json', 'game-cover-report.json', 'game-state.txt']]
packet, game = read(packet_path), read(game_path)
assert packet['schema'] == 1 and packet['kind'] == 'sphere-triangle-mesh-entry-owned-browser-proof'
assert packet['result']['status'] == 'entry_window' and len(packet['result']['audits']) == 61 and len(packet['result']['partition']) == 41
assert (packet['diagnostics']['wasmBytes'], packet['diagnostics']['buildId']) == (719410, browser['buildId'])
state = (ROOT / state_path).read_text(encoding='utf-8')
assert game['state'] == 'ready' and game['failure'] is None and game['errors'] == [] and '一時停止 / Pで再開' in state
kills = int(re.search(r'撃破 (\d+)', state).group(1));queries = game['counts']['queries']
assert kills > 0 and type(queries) is int and queries > 0 and queries == game['counts']['checked'] == game['counts']['validated']
assert game['records'] and all(row['state'] == 'completed' for row in game['records']) and any(row['clipSeconds'] == 1 for row in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False
assert (game['startup']['diagnostics']['wasmBytes'], game['startup']['diagnostics']['buildId']) == (719410, browser['buildId'])
assert browser['game'] == {'paused': True, 'kills': kills, 'coverQueries': queries, 'allCompleted': True, 'boostClip1Observed': True, 'residentMeshes': 3}
evidence.update([packet_path, game_path, state_path])
images = sorted((ROOT / browser_dir).glob('*.jpg'))
assert {'proof.jpg', 'game.jpg'} <= {image.name for image in images}
for image in images:
    assert 100 < image.stat().st_size <= MAX_FILE_BYTES and image.read_bytes().startswith(b'\xff\xd8')
    evidence.add(image.relative_to(ROOT).as_posix())
for path in (ROOT / f'reports/{PREFIX}-recipes').glob('*'):
    if path.is_file():
        evidence.add(path.relative_to(ROOT).as_posix())
for directory in sorted((ROOT / f'reports/{PREFIX}-agent-tests').glob('run-*')):
    for name in ['command.json', 'stdout.txt', 'stderr.txt']:
        evidence.add((directory / name).relative_to(ROOT).as_posix())
assert len(evidence) <= 512
evidence_hashes = {path: digest(ROOT / safe_path(path)) for path in sorted(evidence)}
assert sum(row['bytes'] for row in evidence_hashes.values()) <= 64 * 1024 * 1024

report = {
    'schema': 1, 'status': 'PASS', 'commit': feature, 'checked': datetime.now(timezone.utc).isoformat(),
    'ctest': 38, 'node': 610, 'skipped': 0, 'dedicatedTests': 24, 'fixtures': 65,
    'owned': owned, 'oldOwned': old_owned, 'legacyRegressions': local['legacyRegressions'],
    'exports': 86, 'sourceHeaders': 61, 'artifacts': local['artifacts'], 'runtimeMembers': 91, 'runtimeMembersAdded': [], 'runtimeMembersRemoved': [],
    'protectedFilesUnchanged': 312, 'generatedEntriesOnly': 24, 'generatedEntryComparisons': generated, 'licenseNoticesUnchanged': 7,
    'publicFiles': 88, 'publicBytes': sum(row['bytes'] for row in public['files']), 'sourceComparisons': source_comparisons,
    'existingWarnings': 36, 'warningDiagnosticsUnchanged': True, 'warningComparison': 'Exact diagnostic multiset preserving repeat multiplicity, independent of parallel log order.',
    'ciJobs': jobs, 'ciEvidenceScope': 'All current jobs/steps plus bounded original log excerpts with all warnings and original Run command blocks. Full logs are not archived.',
    'sanitizers': {'entryApiAndTestGroups': 24, 'entryApiScope': 'API/test instrumented with normal strict kernel archive.', 'separateAllEntryKernelGroups': 76,
                   'separateAllOldGuardKernelGroups': 69, 'oldTrajectoryApiAndTestGroups': 25, 'newCppTestProbeWarningAudits': 'PASS',
                   'entryReleaseSanitizedFixtureByteComparison': 'PASS', 'scope': 'Current GNU ASan/UBSan steps; JS decoder is exercised through actual WASM. No new Windows sanitizer success inferred.'},
    'publicBrowser': browser, 'publicGame': {**browser['game'], 'scope': 'Actual current public combat/boost/pause; cumulative cover counters. No entry-window game contact application.'},
    'attempts': local['attempts'],
    'mathematicalScope': 'Actual62 owned model DTOs first match pinned Native fields/bits. The independent Fraction65 corpus explicitly supplements host3 Native results; it does not call them WASM models.90 mathematical controls and synthetic decoder packets are distinct from executed C++ fault injection.',
    'browserScope': 'Current public fixed owned API call: complete visible source/DTO vs Node and enum-only model vs Native. Prior browser results are not inherited. Manual input editor is a later milestone.',
    'scope': 'JS owned decoder only. C++/C ABI/artifacts/old models unchanged. Metadata schedule/counter/ownership checks are not a new geometry solver; no World/TOI/response, game collision, or allocation/unknown-work fault injection completion claim.',
    'evidence': evidence_hashes,
}
target = ROOT / f'reports/{PREFIX}-public-verification.json'
target.write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
print(json.dumps({key: report[key] for key in ['status', 'commit', 'ctest', 'node', 'publicFiles', 'publicBytes']}))


