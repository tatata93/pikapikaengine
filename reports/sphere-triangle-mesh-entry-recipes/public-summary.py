"""Accept captured feature-source CI, public bytes and inherited browser evidence.

No network request or browser operation is performed here. All prerequisites must
already have been captured; an incomplete run cannot produce a PASS report.
"""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import json
import re
import subprocess

if not __debug__:
    raise SystemExit('This acceptance script requires Python assertions; -O is unsupported.')

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-entry'
FEATURE = '058a919aa2b0176f58130f92e554693ea9a4f2e6'
PREVIOUS = 'sphere-triangle-mesh-trajectory-lab'
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
public_path = f'reports/{PREFIX}-public-bytes.json'
runs_path = f'reports/{PREFIX}-public-runs.json'
browser_path = f'reports/{PREFIX}-public-browser-verification.json'
baseline_path = f'reports/{PREFIX}-baseline.json'
previous_path = f'reports/{PREVIOUS}-public-verification.json'
old_warning_path = f'reports/{PREVIOUS}-job-126380383543-excerpt.json'
local, public, runs = read(local_path), read(public_path), read(runs_path)
browser, baseline, previous = read(browser_path), read(baseline_path), read(previous_path)

assert local['status'] == 'PASS' and (local['ctest'], local['nodeTests'], local['skipped']) == (37, 586, 0)
assert (local['nativeGroups'], local['fixtures']) == (76, 65)
assert local['statuses'] == {'separated': 18, 'entry_window': 8, 'not_certified': 20, 'initial_penetration': 2, 'invalid_input': 17}
assert local['reference']['status'] == 'PASS'
assert (local['reference']['certifiedLeaves'], local['reference']['cellAudits'], local['reference']['lastMeshReferenceComponents']) == (558, 1452, 3840)
assert local['reference']['entryWidthReferences'] == 8
assert local['negativeControls'] == {'status': 'PASS', 'fixtures': 65, 'selfTestGroups': 17, 'rejectedControls': 90, 'labelAndOrderIndependent': True}
owned = local['ownedSdkRegression']
assert owned['status'] == 'PASS' and (owned['actualModelFixtures'], owned['hostRejected']) == (59, 3)
assert (owned['modelNumericComparisons'], owned['originalInputNumericComparisons']) == (50663, 3877)
assert (local['exports'], local['sourceHeaders'], local['licenseNoticesUnchanged']) == (80, 59, 7)
assert local['protectedFilesUnchanged'] == 276 and len(baseline['protected']) == 276
for path, value in baseline['protected'].items():
    assert digest(ROOT / safe_path(path)) == expected_hash(value), path
for command in local['commands']:
    assert command['exit'] == 0 and command['authoredStable']
    for stream in ['stdout', 'stderr']:
        assert digest(ROOT / safe_path(command[stream])) == command[stream + 'Hash']
    for path, value in command['authoredAfter'].items():
        assert digest(ROOT / safe_path(path)) == value, path

assert public['status'] == 'PASS' and public['commit'] == runs['commit'] == browser['commit'] == FEATURE
assert len(public['files']) == 73 and len(runs['runs']) == 2
assert {r['name'] for r in runs['runs']} == {'Engine verification', 'pages build and deployment'}
assert len({r['id'] for r in runs['runs']}) == 2
evidence = {local_path, public_path, runs_path, browser_path, baseline_path, previous_path, old_warning_path}
jobs = []
for run in runs['runs']:
    assert run['head_sha'] == FEATURE and run['status'] == 'completed' and run['conclusion'] == 'success'
    path = f'reports/{PREFIX}-run-{run["id"]}.json'
    evidence.add(path)
    rows = read(path)['jobs']
    assert rows
    for job in rows:
        # The captured connector job schema provides run_id, not head_sha.
        # The enclosing run's fixed head_sha establishes the source commit.
        assert job['run_id'] == run['id']
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert job['steps'] and all(step['status'] == 'completed' and step['conclusion'] == 'success' for step in job['steps'])
    jobs.extend(rows)
engines = [job for job in jobs if job['name'] == 'portable-core']
assert len(engines) == 1
engine = engines[0]
step_names = {step['name'] for step in engine['steps']}
for name in ['Build and test C++ core on Linux', 'Test authoring and game logic including the built native CLI',
             'Audit static mesh entry window independently', 'Audit static mesh trajectory guard independently',
             'Audit trajectory C ABI exchange with sanitizers']:
    assert name in step_names, name

log_path = f'reports/{PREFIX}-job-{engine["id"]}-excerpt.json'
evidence.add(log_path)
log, old = read(log_path), read(old_warning_path)
assert log['jobId'] == engine['id'] and type(log['fullLineCount']) is int
assert 0 < len(log['lines']) <= 4096
ordinals = [line['line'] for line in log['lines']]
assert all(type(n) is int and 1 <= n <= log['fullLineCount'] for n in ordinals)
assert ordinals == sorted(set(ordinals))
text = '\n'.join(line['text'] for line in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 37', '# tests 586', '# pass 586', '# fail 0', '# skipped 0',
               'PASS 76 groups; 65 complete-input finite entry fixtures',
               'PASS 69 groups; 62 complete-input finite trajectory fixtures',
               '25 sphere triangle mesh trajectory C ABI groups passed']:
    assert marker in text, marker
for key, value in [('selfTestGroups', 17), ('rejectedControls', 90), ('certifiedLeaves', 558), ('cellAudits', 1452),
                   ('lastMeshReferenceComponents', 3840), ('actualModelFixtures', 59), ('hostRejected', 3),
                   ('modelNumericComparisons', 50663), ('originalInputNumericComparisons', 3877)]:
    assert re.search(r'"' + key + r'"\s*:\s*' + str(value) + r'\b', text), (key, value)


def warnings(source):
    return [line['text'].split('warning:', 1)[1] for line in source['lines'] if 'warning:' in line['text']]


assert len(warnings(log)) == len(warnings(old)) == 36
assert Counter(warnings(log)) == Counter(warnings(old)), 'New or changed compiler warning diagnostic/multiplicity'

assert browser['status'] == previous['status'] == 'PASS'
inherited = browser['inherited']
assert inherited['previousCommit'] == previous['commit']
assert inherited['publicBrowser'] == previous['publicBrowser'] and inherited['publicGame'] == previous['publicGame']
assert type(inherited['scope']) is str and inherited['scope']
cohort = inherited['sourceCohortFiles']
assert len(cohort) == 80 and len({row['path'] for row in cohort}) == len(cohort)
required_cohort = {p for p in baseline['protected'] if p.startswith(('engine/', 'samples/', 'assets/'))}
required_cohort.update(['index.html', 'style.css', 'tools/sphere-triangle-mesh-trajectory-lab.html', 'tools/sphere-triangle-mesh-trajectory-lab.mjs'])
assert required_cohort <= {row['path'] for row in cohort}
assert len({row['path'] for row in public['files']}) == 73
sources = ['core/include/pikapika/sphere_triangle_mesh_entry.hpp', 'core/src/sphere_triangle_mesh_entry.cpp',
           'tests/sphere_triangle_mesh_entry_tests.cpp', 'tests/sphere_triangle_mesh_entry_fixture.hpp',
           'scripts/verify-sphere-triangle-mesh-entry.py', 'tests/sphere_triangle_mesh_entry_reference_tests.py',
           'CMakeLists.txt', '.github/workflows/verify.yml']
requests = [(FEATURE, safe_path(row['path'])) for row in public['files'] + cohort]
requests += [(inherited['previousCommit'], safe_path(row['path'])) for row in cohort]
requests += [(FEATURE, path) for path in sources]
blobs = git_blobs(requests)
for row in public['files']:
    path = safe_path(row['path'])
    assert data_digest(blobs[FEATURE, path]) == expected_hash(row), path
    url = urlsplit(row['url'])
    assert url.scheme == 'https' and url.netloc == 'tatata93.github.io' and unquote(url.path) == '/pikapikaengine/' + path
public_by_path = {row['path']: expected_hash(row) for row in public['files']}
intersection = []
cohort_comparisons = {}
declared_text_suffixes = {'.mjs', '.js', '.html', '.css', '.svg', '.json', '.scene'}
raw_preserved = {'tools/derived-gpu-lab.mjs', 'tools/derived-gpu-lab.html', 'tests/derived-gpu-lab.test.mjs'}
for row in cohort:
    path = safe_path(row['path'])
    current_raw = (ROOT / path).read_bytes()
    feature_blob = blobs[FEATURE, path]
    assert feature_blob == blobs[inherited['previousCommit'], path], path
    normalization = None
    current = current_raw
    if current_raw != feature_blob:
        assert PurePosixPath(path).suffix in declared_text_suffixes and path not in raw_preserved, path
        normalization = 'Declared Git text conversion: CRLF to LF only'
        current = current_raw.replace(b'\r\n', b'\n')
    assert current == feature_blob, path
    assert data_digest(feature_blob) == expected_hash(row), path
    cohort_comparisons[path] = {'currentRaw': data_digest(current_raw), 'featureAndPreviousBlob': data_digest(feature_blob),
                                'normalization': normalization}
    if path in public_by_path:
        assert public_by_path[path] == expected_hash(row), path
        intersection.append(path)
assert intersection
source_comparisons = {}
for path in sources:
    data = (ROOT / path).read_bytes()
    normalization = None
    if path in ['CMakeLists.txt', '.github/workflows/verify.yml'] and b'\r\n' in data:
        normalization = 'Declared Git text conversion: CRLF to LF only'
    canonical = data.replace(b'\r\n', b'\n') if normalization else data
    assert canonical == blobs[FEATURE, path], path
    source_comparisons[path] = {'currentRaw': data_digest(data), 'featureBlob': data_digest(canonical), 'normalization': normalization}
changed = subprocess.check_output(['git', 'diff', '--name-only', baseline['baseCommit'], FEATURE, '--'], cwd=ROOT, text=True).splitlines()
assert not (set(changed) & set(baseline['protected'])), 'Protected file changed in feature commit'

# A successful full step includes strict warning compiles, fully instrumented
# dependencies/test, execution, fixture byte comparison and Fraction recheck.
workflow = blobs[FEATURE, '.github/workflows/verify.yml'].decode('utf-8')
entry_step = workflow.split('      - name: Audit static mesh entry window independently\n', 1)[1].split('      - name: ', 1)[0]
for token in ['-Werror', '-c core/src/sphere_triangle_mesh_entry.cpp', '-c tests/sphere_triangle_mesh_entry_tests.cpp',
              '-fsanitize=address,undefined', 'core/src/interval.cpp core/src/sphere_triangle.cpp core/src/sphere_triangle_mesh.cpp core/src/sphere_triangle_mesh_entry.cpp',
              'cmp build/ci/sphere-triangle-mesh-entry-fixtures.json build/ci/sphere-triangle-mesh-entry-sanitized-fixtures.json',
              'python3 scripts/verify-sphere-triangle-mesh-entry.py build/ci/sphere-triangle-mesh-entry-sanitized-fixtures.json']:
    assert token in entry_step, token
diagram = browser['diagram']
assert diagram['path'] == 'docs/learn/diagrams/sphere-triangle-mesh-entry.svg'
assert diagram['path'] in public_by_path
assert type(diagram['scope']) is str and diagram['scope']
image = ROOT / safe_path(diagram['screenshot'])
assert image.read_bytes().startswith(b'\xff\xd8') and 100 < image.stat().st_size <= MAX_FILE_BYTES
evidence.add(diagram['screenshot'])
for path in (ROOT / f'reports/{PREFIX}-recipes').glob('*.py'):
    evidence.add(path.relative_to(ROOT).as_posix())
agent_summary = f'reports/{PREFIX}-agent-tests/summary.json'
assert read(agent_summary)['status'] == 'PASS'
evidence.add(agent_summary)
assert len(evidence) <= 512
evidence_hashes = {p: digest(ROOT / safe_path(p)) for p in sorted(evidence)}
assert sum(v['bytes'] for v in evidence_hashes.values()) <= 64 * 1024 * 1024

report = {
    'schema': 1, 'status': 'PASS', 'commit': FEATURE, 'checked': datetime.now(timezone.utc).isoformat(),
    'ctest': 37, 'node': 586, 'skipped': 0, 'nativeGroups': 76, 'fixtures': 65, 'statuses': local['statuses'],
    'reference': local['reference'], 'negativeControls': local['negativeControls'], 'ownedSdkRegression': owned,
    'publicFiles': 73, 'publicBytes': sum(row['bytes'] for row in public['files']),
    'existingWarnings': 36, 'warningDiagnosticsUnchanged': True,
    'warningComparison': 'Exact warning diagnostic multiset with repeat multiplicity; order may differ under parallel builds.',
    'ciJobs': jobs, 'ciEvidenceScope': 'All job/step statuses plus bounded original excerpts containing all compiler warnings; full logs are not archived.',
    'entrySanitizer': {'groups': 76, 'allDependenciesAndTestInstrumented': True, 'releaseFixtureByteComparison': 'PASS', 'strictCppAndTestWarningAudits': 'PASS', 'scope': 'GNU ASan/UBSan CI only; no Windows sanitizer success inferred.'},
    'pureGuardSanitizerGroups': 69, 'trajectoryExchangeSanitizerGroups': 25,
    'protectedFilesUnchanged': 276, 'exports': 80, 'sourceHeaders': 59, 'licenseNoticesUnchanged': 7, 'artifacts': local['artifacts'],
    'sourceComparisons': source_comparisons,
    'inheritedCohort': {'files': len(cohort), 'previousCommit': inherited['previousCommit'], 'previousAndFeatureBlobBytesIdentical': True,
                        'currentMatchesFeatureUnderDeclaredTextConversion': True, 'comparisons': cohort_comparisons,
                        'publicIntersectionCount': len(intersection), 'publicIntersectionPaths': sorted(intersection),
                        'scope': 'Only this intersection was fetched in the 73-file public byte run. Previous/feature Git blobs match exactly. Current raw bytes match directly or after the explicitly recorded Git text CRLF-to-LF conversion only; 276 protected raw files are independently unchanged.'},
    'publicBrowser': browser,
    'browserScope': 'The new original concept SVG was visibly checked. Prior guard-lab and robot observations are inherited from their original unchanged-source cohort, not performed again and not execution/application of the Native entry kernel.',
    'sourceScope': 'Native-only entry proof kernel and tests/checker. Existing C ABI, SDK artifacts, browser numerical runtime and game sources remain unchanged. No new JS entry API/UI, World/TOI/response or deliberate allocation/unknown-work fault injection is claimed.',
    'mathematicalScope': 'Initial strict positive sign, closed certified prefix, E-corrected negative exact-path witness and outward parameter width. This is not a unique root, exact physical time or identified contact face/normal.',
    'evidence': evidence_hashes,
}
target = ROOT / f'reports/{PREFIX}-public-verification.json'
target.write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
print(json.dumps({key: report[key] for key in ['status', 'commit', 'ctest', 'node', 'publicFiles', 'publicBytes']}))
