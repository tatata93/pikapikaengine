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

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-free-flight-guard'
FEATURE = 'bd7c1f7f0828aa9dfb67678550c45794b26781d7'
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
assert local['status'] == 'PASS' and (local['nativeGroups'], local['fixtures'], local['supplementalFixtures'], local['ctest'], local['node'], local['skipped']) == (114, 100, 4, 40, 631, 0)
assert (local['exports'], local['sourceHeaders'], local['runtimeMembers'], local['licenseNotices'], local['modules'], local['entries']) == (86, 62, 91, 7, 51, 25)
assert runs['commit'] == public['commit'] == FEATURE and public['status'] == 'PASS'
assert public['build'] == local['webBuild'] == 'bbeba69b26e28cdb'
assert len(public['files']) == len(PUBLIC_PATHS) and {f['path'] for f in public['files']} == set(PUBLIC_PATHS)
assert len({f['path'] for f in public['files']}) == len(public['files'])
assert len(base['protected']) == local['protectedFilesUnchanged'] == 324
assert len(base['generatedEntries']) == local['normalizedGeneratedEntries'] == 25
assert local['baseCommit'] == base['baseCommit']
evidence = {local_path, base_path, runs_path, bytes_path, PUBLIC_RECIPE}
requests = [(base['baseCommit'], p) for p in base['protected']]
requests += [(FEATURE, p) for p in set(base['protected']) | set(base['generatedEntries']) | set(local['sources']) | set(PUBLIC_PATHS)]
source_blobs = blobs(requests)
for path, value in base['protected'].items():
    assert digest(path) == expected_hash(value), path
    assert source_blobs[base['baseCommit'], path] == source_blobs[FEATURE, path], path
source_comparisons = {}
for path, value in local['sources'].items():
    assert digest(path) == expected_hash(value), path
    raw = (ROOT / path).read_bytes();canonical = raw.replace(b'\r\n', b'\n')
    assert canonical == source_blobs[FEATURE, path], path
    source_comparisons[path] = {'raw': data_hash(raw), 'featureBlob': data_hash(canonical),
                                'normalization': 'Declared Git text CRLF-to-LF only' if raw != canonical else None}
generated = {}
for path, value in base['generatedEntries'].items():
    raw = (ROOT / path).read_bytes();distributed = source_blobs[FEATURE, path]
    assert data_hash(normalized_entry(raw)) == data_hash(normalized_entry(distributed)) == value, path
    assert raw.replace(b'\r\n', b'\n') == distributed, path
    generated[path] = {'raw': data_hash(raw), 'featureBlob': data_hash(distributed), 'normalizedAuthored': value}
for item in public['files']:
    path = safe_path(item['path']);assert data_hash(source_blobs[FEATURE, path]) == expected_hash(item), path
    url = urlsplit(item['url'])
    assert url.scheme == 'https' and url.netloc == 'tatata93.github.io' and unquote(url.path) == '/pikapikaengine/' + path

# Shared W1 numerical functions are unchanged; the private bridge and header
# dependency are explicit audited changes rather than hidden hash exceptions.
before = f'reports/{PREFIX}-checks/run-20261104-before'
old_world = (ROOT / before / 'continuous_world-before.cpp').read_bytes()
current_world = (ROOT / 'core/src/continuous_world.cpp').read_bytes()
marker = b'\ndetail::FreeFlightTubeResult detail::enclose_free_flight('
assert current_world.count(marker) == 1 and current_world.endswith(b'\n}\n}\n')
restored = current_world.split(marker)[0].replace(b'#include "free_flight_internal.hpp"\n', b'') + b'}\n'
assert restored == old_world
assert data_hash(old_world) == base['permittedRebuild']['core/src/continuous_world.cpp']
evidence.add(before + '/continuous_world-before.cpp')
manifest_path = 'assets/pikapika-simulation.build.json';manifest = read(manifest_path);evidence.add(manifest_path)
assert manifest['sdkVersion'] == '6.0.13' and len(manifest['sources']) == 30 and len(manifest['sourceSha256']) == 62
assert manifest['sourceFlags']['core/src/dynamics.cpp'] == ['-fno-fast-math', '-ffp-contract=off']
assert 'core/src/free_flight_internal.hpp' in manifest['sourceSha256']
assert manifest['artifacts'] == local['sdkArtifacts']
assert manifest['artifacts']['assets/pikapika-simulation.wasm'] == {'bytes': 719396, 'sha256': '5542502ee73b62c0ca8de9f3d1fc01139bfacfd4ff83922b5568f4a0acfd03c3'}
assert manifest['artifacts']['assets/pikapika-simulation.mjs'] == {'bytes': 58933, 'sha256': '7de3e5160b478aea5fcdc10cad4187e4641c592561414b1d99acaeb184562952'}
assert manifest['licenses'] == base['manifest']['licenses'] and len(manifest['licenses']) == 7
assert manifest['linkedLibraryMembers'] == base['manifest']['linkedLibraryMembers'] and len(manifest['linkedLibraryMembers']) == 91
for path, value in [*manifest['sourceSha256'].items(), *manifest['licenses'].items()]:
    assert digest(path)['sha256'] == value, path
for path, value in manifest['artifacts'].items():assert digest(path) == expected_hash(value), path
exports = json.loads(next(flag.split('=', 1)[1] for flag in manifest['flags'] if flag.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 86

# Every canonical command stream and its source freeze is checked again.
for row in local['commands'] + local['sdkBuild']:
    assert row['exit'] == 0 and row['authoredStable'] is True and row['authoredBefore'] == row['authoredAfter']
    for path, value in row['authoredAfter'].items():assert digest(path) == value, path
    for stream in ('stdout', 'stderr'):
        path = safe_path(row[stream]);assert digest(path) == row[stream + 'Hash'];evidence.add(path)
final = f'reports/{PREFIX}-checks/run-20261104-final'
def stdout(name):
    rows = [r for r in local['commands'] if r['name'] == name];assert len(rows) == 1
    return (ROOT / rows[0]['stdout']).read_text(encoding='utf-8-sig')
assert 'PASS 114 groups; 100 complete-input finite free-flight guard fixtures' in stdout('native-tests')
assert '100% tests passed, 0 tests failed out of 40' in stdout('ctest')
for key, value in [('tests', 631), ('pass', 631), ('fail', 0), ('skipped', 0)]:
    assert re.search(r'(?:ℹ\s+|#\s+)' + key + r'\s+' + str(value) + r'(?:\s|$)', stdout('node'))
reference = local['reference'];controls = local['negativeControls']
assert reference == json.loads(stdout('fraction')) and reference['status'] == 'PASS'
assert reference['inputFingerprint'] == 'c14d0e37cd5fe3d85d30ec0a408d46608ecefabb8b55513e31e51dbfe6ed2d37'
assert (reference['fixtures'], reference['certifiedSeparated'], reference['notCertified'], reference['invalidInputs'], reference['tubeReferences'], reference['endpointReferences']) == (100, 18, 44, 38, 57, 54)
assert (reference['held']['certifiedLeaves'], reference['held']['cellAudits'], reference['held']['lastMeshReferenceComponents']) == (862, 2080, 2556)
supplemental = reference['supplemental']
assert (supplemental['fixtures'], supplemental['certifiedSeparated'], supplemental['notCertified'], supplemental['held']['entryWindows']) == (4, 3, 1, 1)
assert supplemental['inputFingerprint'] == 'a23779088fc9d7ce9bf388456b055795ccf3c5ea85fdab3b11df50ea7a604d80'
assert supplemental['actualBodyBinadeBits'] == ['425fffffffffffff', '4260000000000000', '4260000000000001']
assert supplemental['originalPositiveGap'] == {'numerator': 1, 'denominator': 1048576}
assert controls == read(final + '/reference/negative-controls.json') and controls['status'] == 'PASS'
assert controls['selfTestGroups'] == 12 and len(controls['rejectedControls']) == 50 and all(r['rejected'] for r in controls['rejectedControls'])
assert controls['labelAndOrderIndependent'] is True and controls['supplemental'] == supplemental
assert controls['baseline'] == {k: v for k, v in reference.items() if k != 'supplemental'}
assert read(final + '/reference/optimized-command.json')['exitCode'] == 1
for path in ['native-fixtures.json', 'supplemental-fixtures.json', 'reference/reference.json', 'reference/negative-controls.json', 'reference/optimized-command.json']:
    evidence.add(final + '/' + path)
assert (ROOT / final / 'native-fixtures.json').read_bytes() == (ROOT / f'reports/{PREFIX}-checks/run-20261104-initial/native-fixtures.json').read_bytes()
assert digest(final + '/legacy.json') == digest(before + '/legacy.json') == local['legacyNativeBytes']
assert local['legacyNativeBytes']['bytes'] == 53907
legacy = read(final + '/legacy.json');assert len(legacy['fixtures']) == 20
assert legacy['counts'] == {'fixtures': 20, 'successes': 14, 'failures': 6, 'multipleEventCases': 5}
assert all(r['pointerStable'] is True and (r['report']['success'] or r['rollbackVerified'] is True) for r in legacy['fixtures'])
legacy_wasm = local['legacyWasm'];assert legacy_wasm == read(final + '/legacy-wasm/report.json')
assert legacy_wasm['status'] == 'PASS' and legacy_wasm['comparedToBaseline'] is True
assert (legacy_wasm['fixtures'], legacy_wasm['completed'], legacy_wasm['modelRejected'], legacy_wasm['hostRejected'], legacy_wasm['numericBits'], legacy_wasm['negativeZeroBits']) == (20, 14, 5, 1, 4520, 24)
assert digest(final + '/legacy-wasm/results.json') == legacy_wasm['results'] == digest(f'reports/{PREFIX}-checks/run-20261104-before-wasm/legacy-wasm/results.json')
old_owned = local['oldEntryOwned'];assert old_owned == read(final + '/old-entry-owned/report.json') and old_owned['status'] == 'PASS'
assert (old_owned['actualModelFixtures'], old_owned['hostRejected'], old_owned['modelNumericComparisons'], old_owned['modelNegativeZeroComparisons'], old_owned['originalInputNumericComparisons'], old_owned['originalInputNegativeZeroComparisons']) == (62, 3, 105056, 3239, 4728, 108)
assert old_owned['negativeControls']['rejectedControls'] == 90
for path, value in old_owned['files'].items():
    full = final + '/old-entry-owned/' + safe_path(path);assert digest(full) == expected_hash(value);evidence.add(full)
for path in ['legacy.json', 'legacy-wasm/report.json', 'legacy-wasm/results.json', 'old-entry-owned/report.json', 'old-held-fixtures.json', 'old-w1-fixtures.json']:
    evidence.add(final + '/' + path)
evidence.update([before + '/legacy.json', f'reports/{PREFIX}-checks/run-20261104-before-wasm/legacy-wasm/results.json'])
assert (ROOT / final / 'old-held-fixtures.json').read_bytes() == (ROOT / 'reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json').read_bytes()

# Exact current run and step states; no hardcoded success from prior milestones.
assert len(runs['runs']) == len({r['id'] for r in runs['runs']}) == 2
assert {r['name'] for r in runs['runs']} == {'Engine verification', 'pages build and deployment'}
jobs = []
for run in runs['runs']:
    assert run['head_sha'] == FEATURE and run['status'] == 'completed' and run['conclusion'] == 'success'
    path = f'reports/{PREFIX}-run-{run["id"]}.json';evidence.add(path)
    rows = read(path)['jobs'];assert rows
    for job in rows:
        assert job['run_id'] == run['id'] and job['status'] == 'completed' and job['conclusion'] == 'success'
        assert job['steps'] and all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps'])
    jobs += rows
engine_rows = [j for j in jobs if j['name'] == 'portable-core'];assert len(engine_rows) == 1
engine = engine_rows[0]
assert engine['id'] == 126460730559
assert len([j for j in jobs if j['name'] != 'portable-core']) == 3
assert {'Audit rounded free flight mesh guard independently', 'Audit held-load static mesh path independently',
        'Build and test C++ core on Linux', 'Test authoring and game logic including the built native CLI'} <= {s['name'] for s in engine['steps']}
log_path = f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json';log = read(log_path);evidence.add(log_path)
assert log['jobId'] == engine['id'] and type(log['fullLineCount']) is int and 0 < len(log['lines']) <= 4096
ordinals = [r['line'] for r in log['lines']]
assert ordinals == sorted(set(ordinals)) and ordinals[0] >= 1 and ordinals[-1] <= log['fullLineCount']
text = '\n'.join(r['text'] for r in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 40', '# tests 631', '# pass 631', '# fail 0', '# skipped 0',
               'PASS 114 groups; 100 complete-input finite free-flight guard fixtures', 'PASS 92 groups; 79 complete-input finite held-load fixtures',
               'cmp build/ci/free-flight-legacy-before.json build/ci/free-flight-legacy-after.json',
               'cmp build/ci/sphere-triangle-mesh-free-flight-guard-fixtures.json build/ci/sphere-triangle-mesh-free-flight-guard-sanitized-fixtures.json',
               'cmp build/ci/sphere-triangle-mesh-free-flight-guard-supplemental.json build/ci/sphere-triangle-mesh-free-flight-guard-sanitized-supplemental.json']:
    assert marker in text, marker
for key, value in [('fixtures', 100), ('selfTestGroups', 12), ('rejectedControls', 50), ('tubeReferences', 57), ('endpointReferences', 54),
                   ('certifiedLeaves', 862), ('cellAudits', 2080), ('lastMeshReferenceComponents', 2556),
                   ('fixtures', 4), ('numericBits', 4520), ('negativeZeroBits', 24), ('completed', 14), ('modelRejected', 5), ('hostRejected', 1),
                   ('actualModelFixtures', 62), ('modelNumericComparisons', 105056), ('modelNegativeZeroComparisons', 3239),
                   ('originalInputNumericComparisons', 4728), ('originalInputNegativeZeroComparisons', 108)]:
    assert re.search(r'"' + key + r'"\s*:\s*' + str(value) + r'\b', text), (key, value)
assert reference['inputFingerprint'] in text and supplemental['inputFingerprint'] in text
old_log_path = 'reports/sphere-triangle-mesh-held-load-job-126443232581-excerpt.json';old_log = read(old_log_path);evidence.add(old_log_path)
def warning_suffixes(source):
    return [row['text'].split('warning:', 1)[1] for row in source['lines'] if 'warning:' in row['text']]
old_warnings, warnings = warning_suffixes(old_log), warning_suffixes(log)
query_diagnostics = {value for value in old_warnings if 'missing initializer' in value and 'Query::result' in value}
assert len(query_diagnostics) == 1
extra_diagnostic = next(iter(query_diagnostics))
assert len(old_warnings) == 36 and len(warnings) == 40
assert Counter(warnings) == Counter(old_warnings) + Counter({extra_diagnostic: 4})
workflow = source_blobs[FEATURE, '.github/workflows/verify.yml'].decode('utf-8')
guard_step = workflow.split('      - name: Audit rounded free flight mesh guard independently\n', 1)[1].split('      - name: ', 1)[0]
for marker in ['-Werror', '-fno-fast-math -ffp-contract=off -frounding-math', '-fsanitize=address,undefined',
               'core/src/core.cpp core/src/portable.cpp',
               'core/src/dynamics.cpp core/src/interval.cpp core/src/accelerated.cpp core/src/continuous_world.cpp',
               'core/src/sphere_triangle_mesh_held_load.cpp core/src/sphere_triangle_mesh_free_flight_guard.cpp',
               'tests/sphere_triangle_mesh_free_flight_guard_tests.cpp tests/sphere_triangle_mesh_free_flight_guard_fixtures.cpp tests/sphere_triangle_mesh_held_load_fixtures.cpp',
               '--supplemental-fixtures', '--supplemental build/ci/sphere-triangle-mesh-free-flight-guard-sanitized-supplemental.json']:
    assert marker in guard_step, marker
cmake = source_blobs[FEATURE, 'CMakeLists.txt'].decode('utf-8')
assert 'set_source_files_properties(core/src/dynamics.cpp PROPERTIES COMPILE_OPTIONS "/fp:strict")' in cmake
assert 'set_source_files_properties(core/src/dynamics.cpp PROPERTIES COMPILE_OPTIONS "-fno-fast-math;-ffp-contract=off;-frounding-math")' in cmake

# Current screenshots show the original diagram; raw gameplay diagnostics prove
# the existing exposed SDK still works. These are not Native guard UI results.
browser_dir = f'reports/{PREFIX}-browser'
screens = {}
for name in ['public-diagram.jpg', 'public-diagram-bottom.jpg', 'public-game.jpg']:
    path = browser_dir + '/' + name;raw = (ROOT / path).read_bytes()
    width, height = jpeg_dimensions(raw);assert 900 <= width <= 4096 and 500 <= height <= 4096
    screens[name] = {'path': path, 'format': 'JPEG', 'width': width, 'height': height, **data_hash(raw)};evidence.add(path)
for name, value in local['browser']['evidence'].items():
    path = browser_dir + '/' + safe_path(name);assert digest(path) == value;evidence.add(path)
game_path, state_path = browser_dir + '/public-game-cover-report.json', browser_dir + '/public-game-state.txt'
game = read(game_path);state = (ROOT / state_path).read_text(encoding='utf-8')
assert game['state'] == 'ready' and game['failure'] is None and game['pending'] is None and game['errors'] == []
assert '一時停止 / Pで再開' in state
kills = int(re.search(r'撃破 (\d+)', state).group(1));queries = game['counts']['queries']
assert kills > 0 and type(queries) is int and queries > 0 and queries == game['counts']['checked'] == game['counts']['validated'] == len(game['records'])
assert all(row['state'] == 'completed' for row in game['records']) and any(row['clipSeconds'] == 1 for row in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId'] == public['build'] and game['startup']['diagnostics']['wasmBytes'] == 719396
asset_url = urlsplit(game['startup']['assetURL'])
assert asset_url.scheme == 'https' and asset_url.netloc == 'tatata93.github.io' and asset_url.path == '/pikapikaengine/assets/robot-back-cover.skin.json'
assert parse_qs(asset_url.query).get('build') == [public['build']]
evidence.update([game_path, state_path])
for path in (ROOT / f'reports/{PREFIX}-recipes').glob('*'):
    if path.is_file():evidence.add(path.relative_to(ROOT).as_posix())
attempt_path = f'reports/{PREFIX}-reference-attempts/freeze.json'
attempts = read(attempt_path);evidence.add(attempt_path)
assert attempts['status'] == 'PASS' and attempts['finalExit'] == 0 and attempts['stableDuringFinalRun'] is True
for row in attempts['sources']:
    assert digest(safe_path(row['path'])) == expected_hash(row)
attempt_files = {}
for path in sorted((ROOT / f'reports/{PREFIX}-reference-attempts').rglob('*')):
    if path.is_file():
        relative = path.relative_to(ROOT).as_posix();attempt_files[relative] = digest(relative);evidence.add(relative)
assert len(evidence) <= 1024
evidence_hashes = {path: digest(path) for path in sorted(evidence)}
assert sum(value['bytes'] for value in evidence_hashes.values()) <= 128 * 1024 * 1024
report = {
    'schema': 1, 'status': 'PASS', 'checked': datetime.now(timezone.utc).isoformat(), 'commit': FEATURE,
    'nativeGroups': 114, 'fixtures': 100, 'supplementalFixtures': 4, 'node': 631, 'ctest': 40, 'skipped': 0,
    'reference': reference, 'negativeControls': controls, 'legacyNativeBytes': local['legacyNativeBytes'], 'legacyWasm': legacy_wasm,
    'oldEntryOwned': old_owned, 'exports': 86, 'sourceHeaders': 62, 'sdkArtifacts': local['sdkArtifacts'], 'runtimeMembers': 91, 'licenseNotices': 7,
    'protectedFilesUnchanged': 324, 'normalizedGeneratedEntries': 25, 'generatedEntries': generated, 'sourceComparisons': source_comparisons,
    'publicFiles': len(public['files']), 'publicBytes': sum(f['bytes'] for f in public['files']), 'webBuild': public['build'], 'jobs': jobs,
    'warnings': {'currentOccurrences': 40, 'priorOccurrences': 36, 'priorDiagnosticMultisetPreserved': True, 'extraOccurrences': 4,
                 'extraDiagnostic': extra_diagnostic.strip(), 'scope': 'Two old Query::result missing-initializer diagnostics from the saved original World/probe compilation and two from the newly fully instrumented guard dependency build. New files pass separate -Werror audits; no blanket warning suppression.'},
    'sanitizers': {'guardGroups': 114, 'mainFixtures': 100, 'supplementalFixtures': 4, 'bothReleaseSanitizedByteComparisons': 'PASS',
                   'scope': 'Current GNU ASan/UBSan compiles guard, both guard tests, held fixture writer and all contributing core/dynamics/interval/accelerated/World/mesh/held translation units. Separate original W1 before/after report+World byte comparison and existing SDK compatibility run are distinct evidence. No Windows sanitizer or actual allocation-fault injection inferred.'},
    'browserDisplay': screens, 'publicGame': {'status': 'PASS', 'kills': kills, 'paused': True, 'queries': queries,
                    'boostClip1Observed': True, 'residentMeshes': 3, 'errors': 0,
                    'scope': 'Actual current public game combat/boost/pause with rebuilt existing86-export SDK; guard remains Native-only and is not used for game contact.'},
    'attempts': {'record': attempt_path, 'hash': digest(attempt_path), 'files': attempt_files,
                 'scope': 'Preparation fingerprint/control failures and initial112→final114 test additions remain archived; fixed100 inputs/outputs unchanged. Missing raw run003 stderr is explicitly documented rather than reconstructed.'},
    'ciEvidenceScope': 'All current run/job/step states and finite original command/count/warning excerpts; full job logs are not archived.',
    'scope': 'Read-only selected-body single free interval. Strict noncontracted RN translation B plus whole inflated-path separated and full H candidate are separate obligations. No all-internal-time six-DOF accuracy, repeated-substep/clock accumulation, World tick advance, other-pair ordering, response/support/manifold, new guard SDK capability, or game-contact completion inferred.',
    'evidence': evidence_hashes,
}
(ROOT / f'reports/{PREFIX}-public-verification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
print(json.dumps({key: report[key] for key in ['status', 'commit', 'nativeGroups', 'fixtures', 'supplementalFixtures', 'node', 'ctest', 'publicFiles', 'publicBytes']}))
