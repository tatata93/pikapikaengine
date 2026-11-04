"""Recheck manual flight-lab local evidence; public acceptance is a later gate."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import math
import re
import struct
import subprocess

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'sphere-triangle-mesh-flight-lab'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory')
parser.add_argument('--browser-report', default=f'reports/{PREFIX}-browser/browser-verification.json')
parser.add_argument('--game-directory', default=f'reports/{PREFIX}-browser')
args = parser.parse_args()
FINAL = Path(args.directory).resolve()
assert FINAL.is_relative_to(ROOT) and FINAL.is_dir()
evidence = {}


def relative(path):
    p = Path(path)
    p = (p if p.is_absolute() else ROOT/p).resolve()
    assert p.is_relative_to(ROOT), p
    return p.relative_to(ROOT).as_posix()


def hash_bytes(raw):
    assert len(raw) <= 64*1024*1024
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def digest(path):
    return hash_bytes((ROOT/relative(path)).read_bytes())


def remember(path):
    key = relative(path)
    evidence[key] = digest(key)
    return evidence[key]


def read(path):
    remember(path)
    def floating(token):
        value = float(token)
        mantissa = token.lower().split('e')[0]
        assert math.isfinite(value) and not (value == 0 and any(c in '123456789' for c in mantissa))
        return value
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, key
            result[key] = value
        return result
    return json.loads((ROOT/relative(path)).read_text(encoding='utf-8-sig'), parse_float=floating,
                      parse_int=lambda token: -0.0 if token == '-0' else int(token), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(AssertionError(token)))


def normalized_html(raw):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                  re.sub(rb'\?build=[a-f0-9]{16}', b'', raw), flags=re.S).replace(b'\r\n', b'\n')


def baseline_normalized_html(raw):
    # Preserve the separately frozen original25-page normalization contract.
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'',
                  re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', raw), flags=re.S).replace(b'\r\n', b'\n')


def git_blob(commit, path):
    assert re.fullmatch('[0-9a-f]{40}', commit)
    return subprocess.check_output(['git', 'show', commit+':'+path], cwd=ROOT)


def declared_text(raw, target):
    if raw == target:
        return raw
    assert raw.replace(b'\r\n', b'\n') == target
    return raw.replace(b'\r\n', b'\n')


base_path = f'reports/{PREFIX}-baseline.json'
base = read(base_path)
assert base['baseCommit'] == 'b3d24707a0b75d1f8a7abbf26ec60c583403f515'
assert len(base['protected']) == 349 and len(base['generatedEntries']) == 25
for path, value in base['protected'].items():
    assert digest(path) == value, path
for path, value in base['generatedEntries'].items():
    assert hash_bytes(baseline_normalized_html((ROOT/path).read_bytes())) == value, path
manifest = read('assets/pikapika-simulation.build.json')
assert manifest == base['manifest']
assert (len(manifest['sources']), len(manifest['sourceSha256']), len(manifest['linkedLibraryMembers']), len(manifest['licenses'])) == (32, 67, 91, 7)
exports = json.loads(next(f.split('=', 1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 92
for path, value in [*manifest['sourceSha256'].items(), *manifest['licenses'].items()]:
    assert digest(path)['sha256'] == value, path
for path, value in base['sdkArtifacts'].items():
    assert remember(path) == value, path
assert base['sdkArtifacts']['assets/pikapika-simulation.wasm']['bytes'] == 800982
assert base['sdkArtifacts']['assets/pikapika-simulation.mjs']['bytes'] == 61661

# Archive and prove the three narrowly authorized old-file changes.
old_source_changes = {}
for path, archived in base['permittedOldSources'].items():
    old = archived['gitBlobUtf8'].encode('utf-8')
    assert hash_bytes(old) == archived['gitBlob'] and git_blob(base['baseCommit'], path) == old
    current = (ROOT/path).read_bytes()
    if path == 'scripts/build-web.mjs':
        fragment = b"['tools/sphere-triangle-mesh-flight-lab.html','../','sphere-triangle-mesh-flight-lab.mjs'],"
        assert current.count(fragment) == 1
        reconstructed = current.replace(fragment, b'', 1)
    elif path == 'tests/web-build.test.mjs':
        fragment = b"assert.equal(count,26,'all current game/lab/lesson entry points');"
        assert current.count(fragment) == 1
        reconstructed = current.replace(fragment, fragment.replace(b'26,', b'25,'), 1)
    else:
        assert path == '.github/workflows/verify.yml'
        pattern = rb'^ *node scripts/verify-sphere-triangle-mesh-flight-lab\.mjs build/ci/sphere-triangle-mesh-flight-lab\r?\n'
        assert len(re.findall(pattern, current, re.M)) == 1
        reconstructed = re.sub(pattern, b'', current, count=1, flags=re.M)
    declared_text(reconstructed, old)
    old_source_changes[path] = {'raw': remember(path), 'baseGitBlob': archived['gitBlob'],
                                'reconstruction': 'Exactly the new entry tuple,25-to26 expected entry count,or one explicit actual-UI verifier line; declared text CRLF-to-LF only if raw differs.'}
declared_text((ROOT/'CMakeLists.txt').read_bytes(), git_blob(base['baseCommit'], 'CMakeLists.txt'))

commands = []
command_files = []
for phase in ['focused', 'actual', 'regressions']:
    path = FINAL/(phase+'-commands.json')
    rows = read(path)
    assert rows
    command_files.append(relative(path))
    for row in rows:
        assert row['exit'] == 0 and row['timedOut'] is False
        assert row['authoredStable'] is True and row['authoredBefore'] == row['authoredAfter']
        assert row['rawAuthoredStable'] == (row['rawAuthoredBefore'] == row['rawAuthoredAfter'])
        assert row['sourceNormalization'] == {'tools/sphere-triangle-mesh-flight-lab.html': 'Only importmap/build-query removal and CRLF-to-LF for generated HTML; raw bytes also captured.'}
        for source, value in row['authoredAfter'].items():
            raw = (ROOT/source).read_bytes()
            assert hash_bytes(normalized_html(raw) if source.endswith('.html') else raw) == value, source
            if not source.endswith('.html'):
                assert row['rawAuthoredBefore'][source] == row['rawAuthoredAfter'][source] == digest(source)
        assert type(row['wallSeconds']) in (int, float) and math.isfinite(row['wallSeconds']) and row['wallSeconds'] >= 0
        for stream in ['stdout', 'stderr']:
            assert remember(row[stream]) == row[stream+'Hash']
    commands.extend(rows)


def stdout(name):
    rows = [r for r in commands if r['name'] == name]
    assert len(rows) == 1, name
    return (ROOT/rows[0]['stdout']).read_text(encoding='utf-8-sig')


def node_counts(text):
    result = {}
    for key in ['tests', 'pass', 'fail', 'skipped']:
        matches = re.findall(r'(?:ℹ\s+|#\s+)'+key+r'\s+(\d+)\b', text)
        assert len(matches) == 1
        result[key] = int(matches[0])
    assert result['tests'] == result['pass'] and result['fail'] == result['skipped'] == 0
    return result


focused, node = node_counts(stdout('focused')), node_counts(stdout('node'))
assert focused['tests'] == 23 and node['tests'] == 684
marker = re.findall(r'([0-9a-f]{16}): (\d+) versioned modules', stdout('web-build'))
assert len(marker) == 1 and marker[0][1] == '54'
build_id = marker[0][0]
assert b'?build='+build_id.encode() in (ROOT/'index.html').read_bytes()
html = (ROOT/'tools/sphere-triangle-mesh-flight-lab.html').read_bytes()
assert len(re.findall(rb'<script type="importmap" id="engine-imports">', html)) == 1
assert b'sphere-triangle-mesh-flight-lab.mjs?build='+build_id.encode() in html
new_sources = {p: remember(p) for p in base['newSources']}

actual = read(FINAL/'actual/report.json')
assert actual == json.loads(stdout('actual')) and actual['status'] == 'PASS'
assert (actual['presets'], actual['actualModelPresets'], actual['hostRejected'], actual['actualOwnedMethodCalls']) == (30, 29, 1, 30)
assert actual['sourceStable'] is True and actual['sourceBefore'] == actual['sourceAfter']
actual_command = next(r for r in commands if r['name'] == 'actual')
for path, value in actual['sourceAfter'].items():
    if path.endswith('.html'):
        assert value == actual_command['rawAuthoredAfter'][path]
        assert hash_bytes(normalized_html((ROOT/path).read_bytes())) == actual_command['authoredAfter'][path]
    else:
        assert digest(path) == value, path
for path, value in actual['files'].items():
    assert remember(FINAL/'actual'/path) == value
assert actual['wasm'] == base['sdkArtifacts']['assets/pikapika-simulation.wasm']
assert actual['maximums'] == {'audits': 256, 'leaves': 128, 'partition': 128, 'frontier': 127,
                             'sources': 64, 'candidateIds': 64, 'lastMeshRows': 64, 'lastMeshCandidates': 448}
for value in actual['counters'].values():
    assert type(value['numeric']) is int and value['numeric'] > 0
    assert type(value['negativeZero']) is int and value['negativeZero'] > 0
presets = read(FINAL/'actual/presets.json')
assert presets['schema'] == 1 and len(presets['rows']) == 30
assert len({r['name'] for r in presets['rows']}) == 30
assert sum(r['hostError'] is not None for r in presets['rows']) == 1

# Exact old numerical evidence is inherited through unmodified original sources.
prior_path = 'reports/sphere-triangle-mesh-flight-js-public-verification.json'
prior = read(prior_path)
assert prior['status'] == 'PASS' and prior['ctest'] == 41 and prior['node'] == 661
assert (prior['owned']['fixtures'], prior['owned']['actualModels'], prior['owned']['hostRejected']) == (183, 173, 10)
assert prior['sdkArtifacts'] == base['sdkArtifacts']
assert prior['independentOwned']['negativeControls']['count'] == 15
assert prior['independentOwned']['optimizedPythonRejected'] is True
assert prior['independentOwned']['acceptedInputFingerprint'] == '684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb'
prior_git = git_blob(base['baseCommit'], prior_path)
declared_text((ROOT/prior_path).read_bytes(), prior_git)
owned_execution = None
optional_owned_file = FINAL/'owned-commands.json'
extra_commands = []
if optional_owned_file.exists():
    extra_commands = read(optional_owned_file)
elif any(r['name'] == 'old-owned' for r in commands):
    extra_commands = [r for r in commands if r['name'] == 'old-owned']
if extra_commands:
    assert len(extra_commands) == 1
    row = extra_commands[0]
    assert row['exit'] == 0 and row['authoredStable'] is True
    for stream in ['stdout', 'stderr']:
        assert remember(row[stream]) == row[stream+'Hash']
    owned_execution = read(FINAL/'old-owned/report.json')
    assert owned_execution['status'] == 'PASS'
    assert (owned_execution['fixtures'], owned_execution['actualModels'], owned_execution['hostRejected']) == (183, 173, 10)

# A genuine browser report is required. Missing files never become a fake PASS.
browser = read(args.browser_report)
assert browser['schema'] == 1 and browser['status'] == 'PASS' and browser['phase'] == 'local'
assert browser['buildId'] == build_id and browser['wasmBytes'] == 800982
assert (browser['presets'], browser['actualModelPresets'], browser['hostRejected'], browser['downloads']) == (30, 29, 1, 2)
assert type(browser['numericBits']) is int and browser['numericBits'] > 0
assert type(browser['negativeZeroBits']) is int and browser['negativeZeroBits'] > 0
assert type(browser['extraModelPackets']) is int and browser['extraModelPackets'] >= 1
assert browser['maximums'] == actual['maximums']
assert browser['counts'] == actual['counts']
for path, value in browser['evidence'].items():
    assert remember(path) == value, path
assert browser['nodeUiReport'] == {'path': relative(FINAL/'actual/report.json'), **digest(FINAL/'actual/report.json')}
assert set(browser['counters']) == {'source', 'nodeModel', 'nativeModel', 'canonicalOwned', 'downloads', 'visiblePanels', 'view'}
for counter in browser['counters'].values():
    assert type(counter['numericBits']) is int and counter['numericBits'] >= 0
    assert type(counter['negativeZeroBits']) is int and 0 <= counter['negativeZeroBits'] <= counter['numericBits']
assert sum(c['numericBits'] for c in browser['counters'].values()) == browser['numericBits']
assert sum(c['negativeZeroBits'] for c in browser['counters'].values()) == browser['negativeZeroBits']
assert browser['displayEvidence'] and set(browser['displayEvidence']) <= set(browser['evidence'])
assert any(p.lower().endswith(('.jpg', '.jpeg')) for p in browser['displayEvidence'])
assert any(p.lower().endswith('.txt') for p in browser['displayEvidence'])
for path in browser['displayEvidence']:
    if path.lower().endswith(('.jpg', '.jpeg')):
        assert (ROOT/path).read_bytes()[:2] == b'\xff\xd8'
downloads_manifest = [p for p in browser['evidence'] if Path(p).name == 'downloads.json']
assert len(downloads_manifest) == 1
capture_directory = (ROOT/downloads_manifest[0]).parent
download_rows = read(downloads_manifest[0])
assert type(browser['realDownloadEvidence']) is list and len(browser['realDownloadEvidence']) == len(download_rows) == 2
assert sorted(row['kind'] for row in browser['realDownloadEvidence']) == ['failure', 'success']
for row, captured in zip(browser['realDownloadEvidence'], download_rows):
    assert set(row) == {'kind', 'actualPath', 'capturedFilename', 'download', 'display', 'bytes', 'sha256'}
    assert all(row[key] == captured[key] for key in row)
    original_path = Path(row['actualPath'])
    assert original_path.is_absolute() and not str(original_path).startswith(('\\\\', '//'))
    original = original_path.read_bytes()
    assert len(original) <= 8388608 and original.endswith(b'\n')
    expected_download = {'bytes': row['bytes'], 'sha256': row['sha256']}
    assert hash_bytes(original) == expected_download
    for field in ['download', 'display']:
        archived = (capture_directory/row[field]).resolve()
        assert archived.is_relative_to(capture_directory.resolve())
        assert remember(archived) == expected_download and archived.read_bytes() == original
game_dir = ROOT/relative(args.game_directory)
game = read(game_dir/'local-game-cover-report.json')
state = (game_dir/'local-game-ax.txt').read_text(encoding='utf-8-sig')
for name in ['local-game.jpg', 'local-game-ax.txt']:
    assert remember(game_dir/name)['bytes'] > 0
assert game['state'] == 'ready' and game['failure'] is None and game['pending'] is None and game['errors'] == []
assert '一時停止 / Pで再開' in state
kills = re.search(r'撃破\s+(\d+)', state)
assert kills and int(kills[1]) > 0
queries = game['counts']['queries']
assert type(queries) is int and queries > 0 and queries == game['counts']['checked'] == game['counts']['validated'] == len(game['records'])
assert all(r['state'] == 'completed' for r in game['records']) and any(r['clipSeconds'] == 1 for r in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId'] == build_id and game['startup']['diagnostics']['wasmBytes'] == 800982

history = {}
checks = ROOT/f'reports/{PREFIX}-checks'
if checks.exists():
    for directory in sorted(checks.iterdir()):
        if not directory.is_dir() or directory.resolve() == FINAL:
            continue
        for path in directory.rglob('*'):
            if path.is_file() and (path.name.endswith('-commands.json') or path.name.endswith('.stdout.txt') or path.name.endswith('.stderr.txt') or path.name in {'failure.json', 'source-before.json', 'failure-source-after.json'}):
                history[relative(path)] = remember(path)
for folder in [f'reports/{PREFIX}-agent-tests', f'reports/{PREFIX}-browser-development']:
    p = ROOT/folder
    if p.exists():
        for path in p.rglob('*'):
            if path.is_file():
                history[relative(path)] = remember(path)
assert len(evidence) <= 4096 and sum(v['bytes'] for v in evidence.values()) <= 512*1024*1024
report = {'schema': 1, 'status': 'PASS', 'checked': datetime.now(timezone.utc).isoformat(),
          'baseCommit': base['baseCommit'], 'canonicalDirectory': relative(FINAL),
          'protectedFilesUnchanged': 349, 'normalizedGeneratedEntries': 25, 'entries': 26, 'modules': 54, 'webBuild': build_id,
          'focused': 23, 'node': 684, 'skipped': 0, 'actualPresetVerification': actual,
          'exports': 92, 'sourceHeaders': 67, 'compiledTranslationUnits': 32, 'runtimeMembers': 91, 'licenseNoticesUnchanged': 7,
          'artifacts': base['sdkArtifacts'], 'sdkProvenanceUnchanged': True, 'newSources': new_sources, 'oldSourceChanges': old_source_changes,
          'inheritedNumericalEvidence': {'path': prior_path, 'hash': digest(prior_path), 'nativeCtest': 41, 'ownedModels': 173, 'ownedHosts': 10,
              'scope': 'Previously executed raw/owned/Fraction and Native41 evidence retained through exact unchanged sources and SDK. This UI milestone does not claim a fresh local Native test execution.'},
          'optionalCurrentOwnedExecution': owned_execution, 'browser': browser,
          'game': {'paused': True, 'kills': int(kills[1]), 'queries': queries, 'allCompleted': True, 'boostClip1Observed': True, 'residentMeshes': 3},
          'commands': commands, 'commandFiles': command_files, 'historicalAttempts': history,
          'historicalAttemptScopes': {'firstCanonicalCollection': 'The initial final collection retains a failed authoredStable web-build metadata gate: its new HTML had no build query before the first build, but the original recipe substituted a placeholder afterward. Numeric/UI tests passed, but that collection is not accepted as a stable canonical collection. A fresh final-002 collection uses new-page query removal. Original25-page baseline normalization is unchanged.'},
          'scope': 'Actual30 manual-lab presets/29 full model packets/1 explicit host refusal, strict source/model/saved DTO comparison and dedicated23 UI tests. Browser projection/view edits do not add queries; real download evidence and game compatibility are separate. No World response, true whole-body repeated-step guarantee, runtime performance, usedheap/stack measurement or natural fault injection is inferred. Public CI/Pages acceptance is not claimed by this local receipt.',
          'evidence': evidence}
(ROOT/f'reports/{PREFIX}-local-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['status', 'focused', 'node', 'exports', 'sourceHeaders', 'webBuild']}))
