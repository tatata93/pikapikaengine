"""Audit final local owned-entry evidence; retain every earlier failed attempt."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
prefix = 'sphere-triangle-mesh-entry-js'
final = f'reports/{prefix}-checks/run-20261104-final'
stable_old = f'reports/{prefix}-checks/run-20261104-stable-old'
authored_names = {'engine/simulation.mjs', 'engine/sphere-triangle-mesh-entry.mjs',
                  'tests/sphere_triangle_mesh_entry_sdk.test.mjs',
                  'scripts/verify-sphere-triangle-mesh-entry-sdk.mjs', '.github/workflows/verify.yml'}


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


base = read(f'reports/{prefix}-baseline.json')
assert len(base['protected']) == 312 and len(base['generatedEntries']) == 24
for path, expected in base['protected'].items():
    assert digest(path) == expected, path
for path, expected in base['generatedEntries'].items():
    data = norm_html(path)
    assert {'bytes': len(data), 'sha256': sha256(data).hexdigest()} == expected, path
manifest = read('assets/pikapika-simulation.build.json')
assert manifest == base['manifest'], 'compiled SDK manifest changed in a JS-only milestone'
assert (len(manifest['sourceSha256']), len(manifest['licenses']), len(manifest['linkedLibraryMembers'])) == (61, 7, 91)
for path, expected in manifest['sourceSha256'].items():
    assert digest(path)['sha256'] == expected, path
for path, expected in manifest['licenses'].items():
    assert digest(path)['sha256'] == expected, path
for path, expected in manifest['artifacts'].items():
    assert digest(path) == expected, path
assert digest('assets/pikapika-simulation.wasm')['bytes'] == 719410
assert digest('assets/pikapika-simulation.mjs')['bytes'] == 58933
export_flags = [flag for flag in manifest['flags'] if flag.startswith('-sEXPORTED_FUNCTIONS=')]
assert len(export_flags) == 1
export_names = json.loads(export_flags[0].split('=', 1)[1])
assert len(export_names) == len(set(export_names)) == 86
abi_artifacts = read('reports/sphere-triangle-mesh-entry-abi-artifacts.json')
assert abi_artifacts['status'] == 'PASS' and abi_artifacts['exports'] == 86
assert abi_artifacts['artifacts'] == manifest['artifacts']

commands = []
command_files = {}
for directory, phases in [(final, ['dedicated', 'exchange', 'regressions', 'recheck']),
                          (stable_old, ['old-sdk'])]:
    for phase in phases:
        source_path = f'{directory}/{phase}-commands.json'
        rows = read(source_path)
        assert rows, source_path
        command_files[source_path] = digest(source_path)
        for row in rows:
            audit_streams(row)
            assert row['exit'] == 0 and row['authoredStable'], (phase, row['name'])
            assert set(row['authoredBefore']) == set(row['authoredAfter']) == authored_names
            for path, expected in row['authoredAfter'].items():
                assert digest(path) == expected, (phase, row['name'], path)
        commands.extend(rows)
for name, expected in [('dedicated', 24), ('node', 610), ('learn', 12)]:
    node_totals(command_text(commands, name), expected)
assert '100% tests passed, 0 tests failed out of 38' in command_text(commands, 'ctest')
builds = [re.search(r'Web build ([a-f0-9]{16}): (\d+) versioned modules;',
                   (root / row['stdout']).read_text(encoding='utf-8'))
          for row in commands if row['name'] == 'web-build']
assert builds and all(match and match.group(2) == '50' for match in builds)
web_build = builds[-1].group(1)
assert all(match.group(1) == web_build for match in builds)
assert re.search(r'\?build=' + web_build, (root / 'index.html').read_text(encoding='utf-8'))

owned_directory = f'{final}/owned-sdk'
owned = read(f'{owned_directory}/report.json')
audit_owned(owned_directory, owned, current_dependencies=True)
assert (owned['fixtureCount'], owned['actualModelFixtures'], owned['hostRejected']) == (65, 62, 3)
assert (owned['modelNumericComparisons'], owned['modelNegativeZeroComparisons'],
        owned['originalInputNumericComparisons'], owned['originalInputNegativeZeroComparisons']) == (105056, 3239, 4728, 108)
assert (owned['separated'], owned['entryWindows'], owned['initialPenetrations'], owned['expectedModelFailures']) == (18, 8, 2, 34)
assert (owned['mathematicalCorpus']['fixtures'], owned['mathematicalCorpus']['actualOwnedWasmDecoderResults'],
        owned['mathematicalCorpus']['pureNativeHostSupplements']) == (65, 62, 3)
assert (owned['reference']['fixtures'], owned['reference']['entryWindows'], owned['reference']['certifiedLeaves'],
        owned['reference']['cellAudits'], owned['reference']['positiveIslandsBeyondPrefix']) == (65, 8, 558, 1452, 17)
assert (owned['negativeControls']['rejectedControls'], owned['negativeControls']['selfTestGroups']) == (90, 17)
assert owned['negativeControls']['labelAndOrderIndependent']
assert (owned['ownership']['callerMutationChecks'], owned['ownership']['corpusDtosRetained'],
        owned['ownership']['extraModelCalls']) == (62, 62, 3)
for key in ['originalInputSnapshotSeparate', 'lastMeshRowSourcesSeparate', 'priorAndSubsequentDtosSeparate',
            'exchangeScratchSeparate', 'publicOutputCopySeparate']:
    assert owned['ownership'][key] is True, key
origins = read(f'{owned_directory}/origins.json')
assert len(origins['fixtures']) == 65 and origins['modelCount'] == 62 and origins['hostSupplementCount'] == 3
assert sum(r['origin'] == 'actual-wasm-owned-js-decoder' for r in origins['fixtures']) == 62
assert sum(r['origin'] == 'pure-native-host-supplement' for r in origins['fixtures']) == 3
assert owned['source'] == digest('reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json')
assert owned['source'] == digest(f'{owned_directory}/source-fixtures.json')
assert owned['wasm'] == digest('assets/pikapika-simulation.wasm')

old_owned = read(f'{stable_old}/old-owned-sdk/report.json')
old_mesh = read(f'{stable_old}/old-mesh-sdk/report.json')
old_single = read(f'{stable_old}/old-single-sdk/report.json')
for name, value in [('old-owned-sdk', old_owned), ('old-mesh-sdk', old_mesh), ('old-single-sdk', old_single)]:
    audit_owned(f'{stable_old}/{name}', value)
    assert value['wasm'] == digest('assets/pikapika-simulation.wasm')
assert (old_owned['actualModelFixtures'], old_owned['hostRejected'], old_owned['modelNumericComparisons'],
        old_owned['originalInputNumericComparisons']) == (59, 3, 50663, 3877)
assert old_owned['negativeControls']['rejectedControls'] == 71
assert (old_mesh['modelFixtures'], old_mesh['hostRejected'], old_mesh['packetNumericComparisons'],
        old_mesh['modelNumericComparisons']) == (45, 3, 27160, 20808)
assert (old_single['modelFixtures'], old_single['hostRejected'], old_single['packetNumericComparisons'],
        old_single['modelNumericComparisons']) == (111, 2, 22327, 13432)

# Preserve unsuccessful acceptance and earlier successes without promoting any
# of those different source revisions to the final frozen acceptance above.
initial_commands = read(f'reports/{prefix}-checks/run-20261104-initial/exchange-commands.json')
second_commands = read(f'reports/{prefix}-checks/run-20261104-second/exchange-commands.json')
assert len(initial_commands) == len(second_commands) == 1
for row in initial_commands + second_commands:
    audit_streams(row)
assert initial_commands[0]['exit'] == 1 and second_commands[0]['exit'] == 0
assert 'audit nonnegative bounds' in command_text(initial_commands, 'owned-sdk', 'stderr')
second = read(f'reports/{prefix}-checks/run-20261104-second/owned-sdk/report.json')
audit_owned(f'reports/{prefix}-checks/run-20261104-second/owned-sdk', second)
assert second['status'] == 'PASS' and second['actualModelFixtures'] == 62
agent_runs = []
for index, exit_code in [(1, 1), (2, 1), (3, 0), (4, 0), (5, 0)]:
    directory = f'reports/{prefix}-agent-tests/run-{index:03d}'
    metadata = read(f'{directory}/command.json')
    assert metadata['exit'] == exit_code and metadata['before'] == metadata['after'], directory
    for stream in ['stdout', 'stderr']:
        assert digest(f'{directory}/{stream}.txt') == metadata[stream], directory
    text = (root / directory / 'stdout.txt').read_text(encoding='utf-8')
    if index >= 3:
        node_totals(text, 24)
    if index == 5:
        for path, expected in metadata['after'].items():
            assert digest(path) == expected, path
    agent_runs.append({'directory': directory, 'exit': exit_code, 'command': digest(f'{directory}/command.json'),
                       'stdout': metadata['stdout'], 'stderr': metadata['stderr']})
transition = read(f'{final}/old-sdk-commands.json')
assert transition
for row in transition:
    audit_streams(row)
    assert row['exit'] == 0
assert transition[0]['name'] == 'old-owned-sdk' and not transition[0]['authoredStable']

browser_path = f'reports/{prefix}-local-browser-verification.json'
browser = read(browser_path)
assert browser['status'] == 'PASS' and browser['phase'] == 'local'
assert browser['buildId'] == web_build and browser['wasmBytes'] == 719410
assert browser['entry'] == {'numericBits': 3255, 'negativeZeroBits': 24,
                            'nativeModel': {'numericBits': 3312, 'negativeZeroBits': 20},
                            'status': 'entry_window', 'audits': 61, 'partition': 41}
browser_directory = f'reports/{prefix}-local-browser'
packet, game = read(f'{browser_directory}/owned-case.json'), read(f'{browser_directory}/game-cover-report.json')
assert packet['kind'] == 'sphere-triangle-mesh-entry-owned-browser-proof'
assert packet['result']['status'] == 'entry_window' and packet['result']['initialSeparationProven'] is True
assert len(packet['result']['audits']) == 61 and len(packet['result']['partition']) == 41
assert packet['diagnostics']['buildId'] == web_build and packet['diagnostics']['wasmBytes'] == 719410
assert game['state'] == 'ready' and game['failure'] is None and not game['errors']
assert game['counts']['queries'] == game['counts']['checked'] == game['counts']['validated'] == 20
assert all(row['state'] == 'completed' for row in game['records']) and any(row['clipSeconds'] == 1 for row in game['records'])
assert game['renderer']['residentMeshes'] == 3 and game['renderer']['lost'] is False
assert game['startup']['diagnostics']['buildId'] == web_build and game['startup']['diagnostics']['wasmBytes'] == 719410
state = (root / browser_directory / 'game-state.txt').read_text(encoding='utf-8')
assert '撃破 1' in state and '一時停止 / Pで再開' in state
assert browser['game'] == {'paused': True, 'kills': 1, 'coverQueries': 20, 'allCompleted': True,
                           'boostClip1Observed': True, 'residentMeshes': 3}
browser_files = {p.relative_to(root).as_posix(): digest(p) for p in sorted((root / browser_directory).iterdir()) if p.is_file()}

report = {'schema': 1, 'status': 'PASS', 'checked': datetime.now(timezone.utc).isoformat(),
          'baseCommit': base['baseCommit'], 'protectedFilesUnchanged': 312, 'generatedEntriesOnly': 24,
          'dedicatedTests': 24, 'ctest': 38, 'node': 610, 'nodeTests': 610, 'learnTests': 12, 'skipped': 0,
          'fixtures': 65, 'exports': 86, 'sourceHeaders': 61, 'licenseNoticesUnchanged': 7, 'runtimeMembers': 91,
          'webBuild': web_build, 'modules': 50, 'entries': 24,
          'artifacts': {p: digest(p) for p in ['assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json']},
          'exportScope': '86 explicit exports in the unchanged pinned manifest and byte-identical artifacts to the prior raw ABI export audit; no new SDK build claimed.',
          'owned': owned, 'oldOwned': old_owned, 'legacyRegressions': {'owned': old_owned, 'mesh': old_mesh, 'single': old_single},
          'browser': browser, 'game': browser['game'], 'browserEvidence': browser_files,
          'browserVerification': {'path': browser_path, **digest(browser_path)},
          'commands': commands, 'commandFiles': command_files,
          'frozenAuthoredSources': {p: digest(p) for p in sorted(authored_names)},
          'attempts': {
              'initialExchange': initial_commands, 'secondExchange': second_commands, 'agentRuns': agent_runs,
              'originalOldSdkNoncanonical': transition,
              'decoderCorrection': 'Initial owned exchange and agent run001 rejected a legitimate negative subnormal lower endpoint of an outward norm-squared enclosure. Decoder validation split square-upper and root-lower checks. Native, ABI, artifacts, pure fixture and mathematical expectations remained unchanged.',
              'testCorrection': 'Agent run002 intended to change a frontier endpoint to .5, which was already its value; the .5..1 region was a certified island. Test-only changed to actual frontier-row removal with consistent count. Runs003..005 and final24 dedicated tests pass; later metadata/accessor/reservation hardening is covered by final frozen checks.',
              'oldSdkRerun': 'The first old-owned run passed while a new authored test changed; it is retained as noncanonical. The entire old-sdk phase was rerun in stable-old with all five authored sources stable and equal to current bytes.',
              'browserRecipeCorrection': 'Root reported a first browser checker failure comparing string-enum DTOs directly to numeric-enum Native fixtures. Recipe-only enum projection was corrected before the final PASS, with no DTO/model/math change. This summary certifies the final visible browser evidence; it does not assert a separately archived failed browser command stream.'},
          'scope': 'Owned JavaScript entry decoder and metadata/ownership acceptance only. Actual62 models plus declared pure host3 form mixed65 mathematical acceptance; raw wire counts are separate. Existing game combat/boost/pause is a regression, not entry-window game contact. C++/C ABI/artifacts/game remain unchanged; no World/TOI/response/UI completion or real Native allocation/unknown-work fault injection. Public CI/Pages and exact-byte distribution remain separate.'}
(root / f'reports/{prefix}-local-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['status', 'dedicatedTests', 'nodeTests', 'ctest', 'protectedFilesUnchanged', 'webBuild']}))
