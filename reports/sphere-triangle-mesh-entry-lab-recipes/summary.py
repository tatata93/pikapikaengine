"""Audit local manual entry lab evidence without claiming public acceptance."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

if not __debug__:
    raise SystemExit('Python assertions are required; -O is unsupported.')

root = Path(__file__).resolve().parents[2]
prefix = 'sphere-triangle-mesh-entry-lab'
final = f'reports/{prefix}-checks/run-20261104-final'
authored_names = {'tools/sphere-triangle-mesh-entry-lab.mjs', 'tools/sphere-triangle-mesh-entry-lab.html',
                  'tests/sphere-triangle-mesh-entry-lab.test.mjs', 'scripts/build-web.mjs', 'tests/web-build.test.mjs'}


def read(path):
    return json.loads((root / path).read_text(encoding='utf-8-sig'))


def digest(path):
    data = (root / path).read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def norm_html(path):
    data = (root / path).read_bytes()
    data = re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', data)
    data = re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'', data, flags=re.S)
    return data.replace(b'\r\n', b'\n')


def audit_streams(row):
    for stream in ['stdout', 'stderr']:
        assert digest(row[stream]) == row[stream + 'Hash'], row[stream]
    assert row['authoredStable'] == (row['authoredBefore'] == row['authoredAfter']), row['name']


def command_text(rows, name, stream='stdout'):
    matches = [r for r in rows if r['name'] == name]
    assert matches, name
    return (root / matches[-1][stream]).read_text(encoding='utf-8-sig')


def node_totals(text, expected):
    for label, count in [('tests', expected), ('pass', expected), ('fail', 0), ('skipped', 0)]:
        assert re.search(r'(?:ℹ\s+|#\s+)' + label + r'\s+' + str(count) + r'(?:\s|$)', text), (label, count)


def audit_owned(directory, value, current_dependencies=False):
    assert value['status'] == 'PASS'
    for name, expected in value['files'].items():
        assert digest(f'{directory}/{name}') == expected, name
    if current_dependencies:
        for relative, expected in value['dependencies'].items():
            path = (root / 'scripts' / relative).resolve()
            assert path.is_relative_to(root) and digest(path) == expected, str(path)


base_path = f'reports/{prefix}-baseline.json'
base = read(base_path)
assert len(base['protected']) == 314 and len(base['generatedEntries']) == 24
for path, expected in base['protected'].items():
    assert digest(path) == expected, path
for path, expected in base['generatedEntries'].items():
    data = norm_html(path)
    assert {'bytes': len(data), 'sha256': sha256(data).hexdigest()} == expected, path
manifest = read('assets/pikapika-simulation.build.json')
assert manifest == base['manifest'], 'UI-only milestone changed the SDK manifest'
assert (len(manifest['sources']), len(manifest['sourceSha256']), len(manifest['licenses']), len(manifest['linkedLibraryMembers'])) == (30, 61, 7, 91)
for path, expected in [*manifest['sourceSha256'].items(), *manifest['licenses'].items()]:
    assert digest(path)['sha256'] == expected, path
for path, expected in manifest['artifacts'].items():
    assert digest(path) == expected, path
assert digest('assets/pikapika-simulation.wasm') == {'bytes': 719410, 'sha256': 'd1ece57ca29df06e91cf10c7b598a9b073a86b63959d4ef76e2e0da5f84d5f58'}
assert digest('assets/pikapika-simulation.mjs') == {'bytes': 58933, 'sha256': '7de3e5160b478aea5fcdc10cad4187e4641c592561414b1d99acaeb184562952'}
flags = [flag for flag in manifest['flags'] if flag.startswith('-sEXPORTED_FUNCTIONS=')]
assert len(flags) == 1
exports = json.loads(flags[0].split('=', 1)[1])
assert len(exports) == len(set(exports)) == 86

commands, command_files = [], {}
for phase in ['dedicated', 'exchange', 'regressions', 'recheck']:
    path = f'{final}/{phase}-commands.json'
    rows = read(path)
    assert rows, path
    command_files[path] = digest(path)
    for row in rows:
        audit_streams(row)
        assert row['exit'] == 0 and row['authoredStable'], (phase, row['name'])
        assert set(row['authoredBefore']) == set(row['authoredAfter']) == authored_names
        for name, expected in row['authoredAfter'].items():
            assert digest(name) == expected, (row['name'], name)
    commands.extend(rows)
for name, count in [('dedicated', 21), ('node', 631), ('learn', 12)]:
    node_totals(command_text(commands, name), count)
assert '100% tests passed, 0 tests failed out of 38' in command_text(commands, 'ctest')
builds = [re.search(r'Web build ([a-f0-9]{16}): (\d+) versioned modules;',
                   (root / row['stdout']).read_text(encoding='utf-8'))
          for row in commands if row['name'] == 'web-build']
assert builds and all(match and match.group(2) == '51' for match in builds)
web_build = builds[-1].group(1)
assert all(match.group(1) == web_build for match in builds)
for path in ['index.html', 'tools/sphere-triangle-mesh-entry-lab.html']:
    assert re.search(r'\?build=' + web_build, (root / path).read_text(encoding='utf-8'))

owned_directory = f'{final}/owned-sdk'
owned = read(f'{owned_directory}/report.json')
audit_owned(owned_directory, owned, current_dependencies=True)
assert (owned['fixtureCount'], owned['actualModelFixtures'], owned['hostRejected']) == (65, 62, 3)
assert (owned['modelNumericComparisons'], owned['modelNegativeZeroComparisons'], owned['originalInputNumericComparisons'], owned['originalInputNegativeZeroComparisons']) == (105056, 3239, 4728, 108)
assert (owned['separated'], owned['entryWindows'], owned['initialPenetrations'], owned['expectedModelFailures']) == (18, 8, 2, 34)
assert (owned['mathematicalCorpus']['fixtures'], owned['mathematicalCorpus']['actualOwnedWasmDecoderResults'], owned['mathematicalCorpus']['pureNativeHostSupplements']) == (65, 62, 3)
assert owned['negativeControls'] == {'status': 'PASS', 'fixtures': 65, 'selfTestGroups': 17, 'rejectedControls': 90, 'labelAndOrderIndependent': True}
assert (owned['reference']['fixtures'], owned['reference']['certifiedLeaves'], owned['reference']['cellAudits'], owned['reference']['lastMeshReferenceComponents']) == (65, 558, 1452, 3840)
assert owned['reference']['inputFingerprint'] == '486bfaf8aa19f4d5a8428dbed070b56093b44c8ca7013c18e310a6dae7167404'
assert (owned['ownership']['callerMutationChecks'], owned['ownership']['corpusDtosRetained'], owned['ownership']['extraModelCalls']) == (62, 62, 3)
for name in ['originalInputSnapshotSeparate', 'lastMeshRowSourcesSeparate', 'priorAndSubsequentDtosSeparate', 'exchangeScratchSeparate', 'publicOutputCopySeparate']:
    assert owned['ownership'][name] is True, name
assert owned['source'] == digest('reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json') == digest(f'{owned_directory}/source-fixtures.json')
assert owned['wasm'] == digest('assets/pikapika-simulation.wasm')
origins = read(f'{owned_directory}/origins.json')
assert len(origins['fixtures']) == 65 and origins['modelCount'] == 62 and origins['hostSupplementCount'] == 3
assert sum(row['origin'] == 'actual-wasm-owned-js-decoder' for row in origins['fixtures']) == 62
assert sum(row['origin'] == 'pure-native-host-supplement' for row in origins['fixtures']) == 3

agent_runs = []
for index, count in [(1, 20), (2, 21)]:
    directory = f'reports/{prefix}-agent-tests/run-{index:03d}'
    metadata = read(f'{directory}/command.json')
    assert metadata['exit'] == 0 and metadata['before'] == metadata['after']
    for stream in ['stdout', 'stderr']:
        assert digest(f'{directory}/{stream}.txt') == metadata[stream]
    node_totals((root / directory / 'stdout.txt').read_text(encoding='utf-8'), count)
    if index == 2:
        for path, expected in metadata['after'].items():
            # Keep the earlier raw HTML hash as historical evidence. Current
            # HTML is separately pinned by the canonical final command rows.
            if path != 'tools/sphere-triangle-mesh-entry-lab.html':
                assert digest(path) == expected, path
    agent_runs.append({'directory': directory, 'exit': 0, 'tests': count, 'passed': count,
                       'command': digest(f'{directory}/command.json'), 'stdout': metadata['stdout'], 'stderr': metadata['stderr']})

# Earlier successful nonfinal commands are retained as history, not promoted
# to canonical current-source acceptance. Preserve any failing command too.
historical_commands = []
for directory in sorted((root / f'reports/{prefix}-checks').iterdir()):
    if not directory.is_dir() or directory.name == Path(final).name:
        continue
    for path in sorted(directory.glob('*-commands.json')):
        rows = read(path)
        for row in rows:
            audit_streams(row)
        historical_commands.append({'path': path.relative_to(root).as_posix(), **digest(path), 'commands': rows,
                                    'scope': 'Historical attempt, not the final frozen source acceptance.'})

previous_path = 'reports/sphere-triangle-mesh-entry-js-local-verification.json'
previous = read(previous_path)
assert previous['status'] == 'PASS' and previous['owned']['wasm'] == owned['wasm']
for path, expected in previous['frozenAuthoredSources'].items():
    if path in base['protected']:
        assert digest(path) == expected, path
inherited_old = {'sourceReport': previous_path, 'sourceReportHash': digest(previous_path),
                 'legacyRegressions': previous['legacyRegressions'],
                 'scope': 'Historical old trajectory/mesh/single full-wire reports from previous owned-entry acceptance. Their kernels, SDK, wrappers, tests and checkers are protected unchanged. This UI stage freshly reruns631 Node/38 CTest and the entry owned62+3/math90 corpus; it does not claim a new separate old-sdk phase.'}

browser_path = f'reports/{prefix}-local-browser-verification.json'
browser = read(browser_path)
assert browser['status'] == 'PASS' and browser['phase'] == 'local'
assert browser['buildId'] == web_build and browser['wasmBytes'] == 719410
for key, expected in [('presets', 25), ('actualModelPresets', 24), ('hostRejected', 1), ('separated', 2),
                      ('entryWindows', 5), ('initialPenetrations', 1), ('notCertified', 12), ('invalidInputs', 4),
                      ('expectedModelFailures', 16), ('downloads', 2)]:
    assert browser[key] == expected, key
for key in ['numericBits', 'negativeZeroBits', 'extraModelPackets']:
    assert type(browser[key]) is int and browser[key] > 0, key
browser_directory = f'reports/{prefix}-local-browser'
for name in ['presets.json', 'extras.json', 'actions.json', 'downloads.json']:
    read(f'{browser_directory}/{name}')
presets = read(f'{browser_directory}/presets.json')
assert len(presets) == 25 and len({row['name'] for row in presets}) == 25
assert sum(row['canSave'] is True for row in presets) == 24
refused = [row for row in presets if row['canSave'] is False]
assert len(refused) == 1 and refused[0]['name'] == '65-source-rejection'
assert all(not row['error'] for row in presets if row['canSave'])
game = read(f'{browser_directory}/game-cover-report.json')
state = (root / browser_directory / 'game-state.txt').read_text(encoding='utf-8')
assert '一時停止 / Pで再開' in state
kills = int(re.search(r'撃破 (\d+)', state).group(1))
assert kills > 0 and game['state'] == 'ready' and game['failure'] is None and game['errors'] == []
queries = game['counts']['queries']
assert type(queries) is int and queries > 0 and queries == game['counts']['checked'] == game['counts']['validated']
assert game['records'] and all(row['state'] == 'completed' for row in game['records']) and any(row['clipSeconds'] == 1 for row in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False
assert (game['startup']['diagnostics']['wasmBytes'], game['startup']['diagnostics']['buildId']) == (719410, web_build)
assert browser['game'] == {'paused': True, 'kills': kills, 'coverQueries': queries, 'allCompleted': True, 'boostClip1Observed': True, 'residentMeshes': 3}
browser_files = {path.relative_to(root).as_posix(): digest(path) for path in sorted((root / browser_directory).iterdir()) if path.is_file()}
assert len(browser_files) <= 128 and sum(value['bytes'] for value in browser_files.values()) <= 64 * 1024 * 1024

report = {'schema': 1, 'status': 'PASS', 'checked': datetime.now(timezone.utc).isoformat(),
          'baseCommit': base['baseCommit'], 'protectedFilesUnchanged': 314, 'generatedEntriesOnly': 24,
          'dedicatedTests': 21, 'ctest': 38, 'node': 631, 'nodeTests': 631, 'learnTests': 12, 'skipped': 0,
          'labPresets': 25, 'labModelPresets': 24, 'labHostPresets': 1, 'fixtures': 65,
          'exports': 86, 'sourceHeaders': 61, 'licenseNoticesUnchanged': 7, 'runtimeMembers': 91,
          'webBuild': web_build, 'modules': 51, 'entries': 25,
          'artifacts': {path: digest(path) for path in ['assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json']},
          'exportScope': 'UI-only milestone, byte-identical current SDK/manifest;86 existing exports61 source-header91 linked runtime7 notices, no new SDK build or kernel change.',
          'owned': owned, 'inheritedOldSdk': inherited_old,
          'newSources': {path: digest(path) for path in sorted(authored_names) if path.startswith('tools/') or path.startswith('tests/sphere-')},
          'browser': browser, 'game': browser['game'], 'browserEvidence': browser_files,
          'browserVerification': {'path': browser_path, **digest(browser_path)},
          'commands': commands, 'commandFiles': command_files,
          'frozenAuthoredSources': {path: digest(path) for path in sorted(authored_names)},
          'attempts': {'agentRuns': agent_runs, 'historicalCommands': historical_commands,
                       'agentScope': 'Initial20/20 passed. One explicit artificial environment/allocation DTO display group was added; final21/21 passed. Complete commands/exit/stdout/stderr and six before/after hashes retained. Earlier HTML raw hashes remain historical; current final HTML is pinned by canonical final command rows.',
                       'artificialScope': 'Unknown-work, unsupported-environment and pre-initial-allocation display packets are artificial UI shapes, not naturally reached model cases or actual C++ fault injection.'},
          'scope': 'Manual read-only entry-window UI. Natural25 presets comprise24 actual models and1 host refusal, distinct from the fresh full62+3 owned SDK/mixed65 Fraction90 acceptance. Current complete browser input/result and Blob payload checks are separate from images and older SDK proofs. No World/TOI/response/game-contact, new dependency, or actual Native allocation/unknown-work fault injection completion. Public CI/Pages/bytes remain separate.'}
target = root / f'reports/{prefix}-local-verification.json'
target.write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
print(json.dumps({key: report[key] for key in ['status', 'dedicatedTests', 'nodeTests', 'ctest', 'protectedFilesUnchanged', 'webBuild']}))


