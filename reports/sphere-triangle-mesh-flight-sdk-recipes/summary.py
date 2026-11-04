"""Aggregate captured local raw flight-SDK evidence; public acceptance is separate."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import subprocess

if not __debug__:
    raise SystemExit('Run without Python -O')
root = Path(__file__).resolve().parents[2]
prefix = 'sphere-triangle-mesh-flight-sdk'
final = f'reports/{prefix}-checks/run-20261104-final-002'
evidence = {}


def digest_bytes(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def digest(path):
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    assert p.resolve().is_relative_to(root), p
    return digest_bytes(p.read_bytes())


def remember(path):
    path = Path(path).as_posix()
    evidence[path] = digest(path)
    return evidence[path]


def read(path):
    remember(path)
    return json.loads((root / path).read_text(encoding='utf-8-sig'))


def git_blob(commit, path):
    assert re.fullmatch('[0-9a-f]{40}', commit)
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=root)


def exports(manifest):
    flags = [x for x in manifest['flags'] if x.startswith('-sEXPORTED_FUNCTIONS=')]
    assert len(flags) == 1
    values = json.loads(flags[0].split('=', 1)[1])
    assert len(set(values)) == len(values)
    return values


def generated_normalized(data):
    data = re.sub(rb'\?build=[a-f0-9]{16}', b'?build=GENERATED', data)
    data = re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*', b'', data, flags=re.S)
    return data.replace(b'\r\n', b'\n')


base = read(f'reports/{prefix}-baseline.json')
assert base['baseCommit'] == '3012b152fb1b27011d618abccac595a25e6fab82'
assert len(base['protected']) == 333 and len(base['generatedEntries']) == 25
for path, expected in base['protected'].items():
    assert digest(path) == expected, path
for path, expected in base['generatedEntries'].items():
    assert digest_bytes(generated_normalized((root / path).read_bytes())) == expected, path

# These are exact byte reconstructions, not a whitespace-insensitive API audit.
api_path = 'core/src/simulation_api.cpp'
api = (root / api_path).read_bytes()
removed = [b'#include "pikapika/sphere_triangle_mesh_free_flight_guard.hpp"\n',
           b'#include "sphere_triangle_mesh_flight_api_internal.hpp"\n',
           b'for(auto& stage:flight_stages){stage.reset();}for(auto& record:flight_records){record.reset();}']
for fragment in removed:
    assert api.count(fragment) == 1
    api = api.replace(fragment, b'', 1)
assert api == git_blob(base['baseCommit'], api_path), 'old API implementation changed'
header_path = 'core/include/pikapika/simulation_api.h'
header = (root / header_path).read_bytes()
start = header.index(b'enum pp_sim_sphere_triangle_mesh_flight_mode {')
end = header.index(b'int32_t pp_sim_polarized_packet(uint32_t value_count);', start)
assert header[:start] + header[end:] == git_blob(base['baseCommit'], header_path), 'old header changed'

manifest = read('assets/pikapika-simulation.build.json')
assert len(manifest['sources']) == 32 and len(manifest['sourceSha256']) == 67
for path, expected in manifest['sourceSha256'].items():
    assert digest(path)['sha256'] == expected, path
assert len(manifest['licenses']) == 7 and manifest['licenses'] == base['manifest']['licenses']
for path, expected in manifest['licenses'].items():
    assert digest(path)['sha256'] == expected, path
assert manifest['linkedLibraryMembers'] == base['manifest']['linkedLibraryMembers']
assert len(manifest['linkedLibraryMembers']) == 91
old_exports, new_exports = exports(base['manifest']), exports(manifest)
new_family = ['_pp_sim_sphere_triangle_mesh_flight_' + name
              for name in ['begin', 'append', 'query', 'record', 'last_mesh', 'candidate']]
assert len(old_exports) == 86 and len(new_exports) == 92
assert [x for x in new_exports if x not in new_family] == old_exports
assert [x for x in new_exports if x not in old_exports] == new_family
assert manifest['memory'] == {'initialBytes': 67108864, 'maximumBytes': 268435456, 'stackBytes': 1048576}
for path in ['core/src/dynamics.cpp', 'core/src/continuous_world.cpp',
             'core/src/sphere_triangle_mesh_held_load.cpp', 'core/src/sphere_triangle_mesh_free_flight_guard.cpp']:
    assert manifest['sourceFlags'][path] == ['-fno-fast-math', '-ffp-contract=off']
artifacts = {p: remember(p) for p in ['assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json']}
assert artifacts['assets/pikapika-simulation.wasm'] == {'bytes': 800982, 'sha256': 'a7db41c64d2f9112ec5ee033371c391dddcb42ad23dcef713347c129a4ed015d'}
assert artifacts['assets/pikapika-simulation.mjs'] == {'bytes': 61661, 'sha256': 'd4bedfdc9dcc1a60ee816e34c43afbe51623835ca5af65b0e6f4f5937484de55'}
for path, expected in manifest['artifacts'].items():
    assert artifacts[path] == expected

commands = []
command_files = []
historical_noncompiled_source = []
for directory, phases in [('build-final-002', ['build']), ('sdk-final-002', ['sdk-build']),
                          ('final-002', ['native', 'wire', 'regressions', 'pure-regressions'])]:
    for phase in phases:
        path = f'reports/{prefix}-checks/run-20261104-{directory}/{phase}-commands.json'
        command_files.append(path)
        rows = read(path)
        assert rows, path
        for row in rows:
            assert row['exit'] == 0 and row['authoredStable'] is True
            assert row['authoredBefore'] == row['authoredAfter'], row['name']
            for source, expected in row['authoredAfter'].items():
                assert digest(source) == expected, source
            for stream in ['stdout', 'stderr']:
                assert remember(row[stream]) == row[stream + 'Hash'], row['name']
        commands.extend(rows)

# Keep the earlier successful captures, without calling the old internal header current.
historical_commands = []
historical_source_change = []
for directory, phases in [('initial', ['build', 'abi-tests']), ('sdk-initial', ['sdk-build']),
                          ('final', ['native', 'wire', 'regressions', 'pure-regressions'])]:
    for phase in phases:
        path = f'reports/{prefix}-checks/run-20261104-{directory}/{phase}-commands.json'
        rows = read(path)
        assert rows
        for row in rows:
            assert row['exit'] == 0 and row['authoredStable'] is True
            assert row['authoredBefore'] == row['authoredAfter']
            for source, expected in row['authoredAfter'].items():
                current = digest(source)
                if current == expected:
                    continue
                record = {'commandFile': path, 'command': row['name'], 'source': source,
                          'captured': expected, 'current': current}
                if source == 'tests/sphere_triangle_mesh_flight_wire_reference_test.py':
                    assert (directory, phase, row['name']) == ('initial', 'abi-tests', 'native-tests')
                    assert expected == {'bytes': 5760, 'sha256': '91f32e39a0239a27718eb3594f53ae4bc4bb9efe55c5e77e599fd7a93da4c4c0'}
                    record['scope'] = 'Not compiled or executed by this initial Native ABI test; final synthetic and actual verification captures use the current source.'
                    historical_noncompiled_source.append(record)
                else:
                    assert source == 'core/src/sphere_triangle_mesh_flight_api_internal.hpp'
                    assert expected == {'bytes': 48736, 'sha256': '1f05888960aaa3dc29eed5d88d64ea24de4a504fb24f22968a11ae15f1c58168'}
                    record['scope'] = 'Superseded by removal of one unused internal function; all compiled source and regression evidence are accepted again in the canonical final-002 run.'
                    historical_source_change.append(record)
            for stream in ['stdout', 'stderr']:
                assert remember(row[stream]) == row[stream + 'Hash']
        historical_commands.extend(rows)


def output(name):
    rows = [r for r in commands if r['name'] == name]
    assert rows and all(r['stdoutHash'] == rows[0]['stdoutHash'] for r in rows), name
    return (root / rows[0]['stdout']).read_text(encoding='utf-8-sig')


for label, count in [('tests', 631), ('pass', 631), ('fail', 0), ('skipped', 0)]:
    assert re.search(r'(?:ℹ\s+|#\s+)' + label + r'\s+' + str(count) + r'(?:\s|$)', output('node'))
assert '100% tests passed, 0 tests failed out of 41' in output('ctest')
assert '200 sphere triangle mesh flight C ABI groups passed; 183 complete inputs; 173 actual models; 10 host refusals' in output('native-tests')
assert '26d4da108a67b9d9: 51 versioned modules' in output('web-build')

# The first prebuilt baseline overlapped a header edit. Preserve that exception.
before = f'reports/{prefix}-checks/run-20261104-before'
baseline_commands = read(f'{before}/baseline-commands.json')
baseline_scope = read(f'{before}/baseline-scope.json')
assert [r['name'] for r in baseline_commands] == ['legacy-native-before', 'legacy-wasm-before']
assert [r['authoredStable'] for r in baseline_commands] == [False, True]
changed = [p for p in set(baseline_commands[0]['authoredBefore']) | set(baseline_commands[0]['authoredAfter'])
           if baseline_commands[0]['authoredBefore'].get(p) != baseline_commands[0]['authoredAfter'].get(p)]
assert changed == ['core/include/pikapika/simulation_api.h']
assert baseline_scope['overlap'][0]['paths'] == changed
assert baseline_scope['overlap'][0]['authoredStable'] is False
for row in baseline_commands:
    assert row['exit'] == 0
    for stream in ['stdout', 'stderr']:
        assert remember(row[stream]) == row[stream + 'Hash']
assert (root / f'{before}/legacy-native-before.json').read_bytes() == (root / f'{final}/legacy-native-after.json').read_bytes()
remember(f'{before}/legacy-native-before.json')
remember(f'{final}/legacy-native-after.json')
legacy = read(f'{final}/legacy-wasm-after/report.json')
assert legacy['status'] == 'PASS' and legacy['comparedToBaseline'] is True
assert (legacy['fixtures'], legacy['numericBits'], legacy['negativeZeroBits']) == (20, 4520, 24)
assert legacy['wasm'] == artifacts['assets/pikapika-simulation.wasm']
assert digest(f'{before}/legacy-wasm-before/results.json') == digest(f'{final}/legacy-wasm-after/results.json')

native = read(f'{final}/native-exchange/report.json')
independent = read(f'{final}/wasm-independent/report.json')
wire = read(f'{final}/wasm-wire/report.json')
same_keys = ['fixtureCount', 'accepted', 'hostRejected', 'numericBits', 'negativeZeroBits',
             'decodedNumericBits', 'decodedNegativeZeroBits', 'acceptedInputFingerprint', 'records', 'maximums', 'cohorts', 'fullInputFingerprint']
assert all(native[k] == independent[k] for k in same_keys)
assert (native['fixtureCount'], native['accepted'], native['hostRejected'], native['numericBits'], native['negativeZeroBits'],
        native['decodedNumericBits'], native['decodedNegativeZeroBits'], native['records']) == (183, 173, 10, 415506, 5738, 272814, 5424, 10397)
assert native['acceptedInputFingerprint'] == '684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb'
assert native['maximums'] == {'sources': 64, 'audits': 256, 'leaves': 128, 'partition': 128,
                             'frontier': 127, 'candidateIds': 64, 'lastMeshRows': 64, 'lastMeshCandidates': 448}
mathematics = {'held': 74, 'guard': 95, 'supplemental': 4}
for cohort, count in mathematics.items():
    assert native['cohorts'][cohort]['models'] == count
    assert native['cohorts'][cohort]['mathematics']['fixtures'] == 0
for folder, report in [('native-exchange', native), ('wasm-independent', independent)]:
    assert report['status'] == 'PASS'
    assert report['scope'] == ('native' if folder == 'native-exchange' else 'wasm-wire')
    for path, expected in report['files'].items():
        assert remember(f'{final}/{folder}/{path}') == expected, path
    for path, expected in report['sources'].items():
        assert digest(path) == expected, path
    controls = read(f'{final}/{folder}/packet-negative-controls.json')
    assert controls['status'] == 'PASS' and controls['count'] == len(controls['rejectedControls']) == 16
    assert all(c['rejected'] is True for c in controls['rejectedControls'])
    assert len({c['name'] for c in controls['rejectedControls']}) == 16
    assert read(f'{final}/{folder}/optimized-command.json')['exitCode'] == 1
    remember(f'{final}/{folder}/optimized.stdout.txt')
    remember(f'{final}/{folder}/optimized.stderr.txt')
    assert report['optimizedPythonRejected'] == {'status': 'PASS', 'exitCode': 1}
assert wire['status'] == 'PASS'
assert (wire['fixtures'], wire['accepted'], wire['hostRejected'], wire['numericBits'], wire['negativeZeroBits']) == (183, 173, 10, 415689, 5738)
assert len(wire['controls']) == 15 and all(c['status'] == 'PASS' for c in wire['controls'])
assert wire['sourceNativePackets'] == digest(f'{final}/native-exchange/packets.json')
assert wire['capturedPackets'] == digest(f'{final}/wasm-wire/wasm-packets.json') == digest(f'{final}/wasm-independent/packets.json')
assert wire['wasm'] == artifacts['assets/pikapika-simulation.wasm']
memory = wire['memory']
assert memory['initialCapacityBytes'] == memory['maximumCapacityBytes'] == memory['finalCapacityBytes'] == 67108864
assert memory['bufferChanges'] == 0 and memory['viewChecks'] > 0 and memory['memoryGrowthExercised'] is False
assert memory['usedHeapBytes'] is None and memory['stackHighWaterBytes'] is None

pure_paths = {'held': 'reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json',
              'guard': 'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/native-fixtures.json',
              'supplemental': 'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/supplemental-fixtures.json'}
for name, original in pure_paths.items():
    assert remember(original) == remember(f'{final}/{name}.json')
    assert (root / f'{final}/{name}.json').read_bytes() == (root / f'{final}/{name}.stdout.txt').read_bytes()
owned = read(f'{final}/old-entry-owned/report.json')
assert owned['status'] == 'PASS'
assert (owned['fixtureCount'], owned['actualModelFixtures'], owned['hostRejected']) == (65, 62, 3)
assert (owned['modelNumericComparisons'], owned['modelNegativeZeroComparisons'], owned['originalInputNumericComparisons'], owned['originalInputNegativeZeroComparisons']) == (105056, 3239, 4728, 108)
assert owned['negativeControls'] == {'status': 'PASS', 'fixtures': 65, 'selfTestGroups': 17, 'rejectedControls': 90, 'labelAndOrderIndependent': True}
for path, expected in owned['files'].items():
    assert remember(f'{final}/old-entry-owned/{path}') == expected
assert owned['wasm'] == artifacts['assets/pikapika-simulation.wasm']

archive_path = f'reports/{prefix}-reference-attempts/freeze.json'
archive = read(archive_path)
assert archive['status'] == 'PASS' and archive['finalGroups'] == 6 and archive['finalExit'] == 0 and archive['stableDuringFinalRun'] is True
assert set(archive['attempts']) == {'run-001', 'run-002', 'run-003', 'run-004'}
assert archive['attempts']['run-001']['exit'] != 0
for row in archive['sources']:
    assert digest(row['path']) == {'bytes': row['bytes'], 'sha256': row['sha256']}
for row in archive['archive']:
    assert remember(row['path']) == {'bytes': row['bytes'], 'sha256': row['sha256']}
for run in archive['attempts']:
    remember(f'reports/{prefix}-reference-attempts/{run}/provenance.json')
last_synthetic = read(f'reports/{prefix}-reference-attempts/run-004/command.json')
assert last_synthetic['exitCode'] == 0 and last_synthetic['before'] == last_synthetic['after'] == archive['sources']
synthetic_stderr = (root / f'reports/{prefix}-reference-attempts/run-004/stderr.txt').read_text(encoding='utf-8-sig')
assert re.search(r'Ran 6 tests\b', synthetic_stderr) and re.search(r'\bOK\s*$', synthetic_stderr)

browser_dir = f'reports/{prefix}-browser'
initial_browser_dir = f'{browser_dir}/initial-055e57b764eb7731'
initial_browser_evidence = {name: remember(f'{initial_browser_dir}/{name}')
                            for name in ['game.jpg', 'game-state.txt', 'game-cover-report.json']}
initial_cover = read(f'{initial_browser_dir}/game-cover-report.json')
assert initial_cover['startup']['diagnostics']['buildId'] == '055e57b764eb7731'
assert initial_cover['counts']['queries'] == 21
for name in ['diagram.jpg', 'game.jpg', 'game-state.txt', 'game-cover-report.json']:
    assert remember(f'{browser_dir}/{name}')['bytes'] > 0
cover = read(f'{browser_dir}/game-cover-report.json')
assert cover['state'] == 'ready' and cover['failure'] is None and cover['pending'] is None and cover['errors'] == []
assert type(cover['counts']['queries']) is int and cover['counts']['queries'] > 0
assert cover['counts']['queries'] == cover['counts']['checked'] == cover['counts']['validated'] == len(cover['records'])
assert all(r['state'] == 'completed' for r in cover['records']) and any(r['clipSeconds'] == 1 for r in cover['records'])
assert cover['renderer']['residentMeshes'] == 3 and cover['renderer']['lost'] is False and cover['renderer']['disposed'] is False
assert cover['startup']['diagnostics']['buildId'] == '26d4da108a67b9d9' and cover['startup']['diagnostics']['wasmBytes'] == 800982
game_state = (root / f'{browser_dir}/game-state.txt').read_text(encoding='utf-8-sig')
kills = re.search(r'撃破\s+(\d+)', game_state)
assert kills is not None and int(kills[1]) > 0 and '一時停止 / Pで再開' in game_state
observed_speed = re.search(r'(\d+) km/h', game_state)
assert observed_speed is not None

report = {'schema': 1, 'status': 'PASS', 'checked': datetime.now(timezone.utc).isoformat(),
          'baseCommit': base['baseCommit'], 'protectedFilesUnchanged': 333, 'generatedEntriesOnly': 25,
          'nativeExchangeGroups': 200, 'ctest': 41, 'node': 631, 'skipped': 0,
          'exports': 92, 'sourceHeaders': 67, 'compiledTranslationUnits': 32,
          'runtimeMembers': 91, 'licenseNoticesUnchanged': 7, 'webBuild': '26d4da108a67b9d9', 'modules': 51, 'entries': 25,
          'artifacts': artifacts, 'nativeExchange': native, 'wasmWire': wire, 'wasmExchange': independent,
          'mathematicsFixturesVerified': {**mathematics, 'total': 173},
          'mathematicsCountNote': 'Each accepted decoded model calls verify_fixture. Its aggregate fixtures counter is unused and remains 0 in the preserved raw reports; this does not mean zero verified fixtures.',
          'legacyW1': legacy, 'oldEntryOwned': owned, 'memory': memory,
          'baselineScope': baseline_scope, 'baselineCommands': baseline_commands,
          'historicalNoncompiledSource': historical_noncompiled_source,
          'historicalSupersededSource': historical_source_change, 'historicalCommands': historical_commands,
          'sourcePreservation': {'apiReconstructedExactBaseBlob': True, 'headerInsertionOnlyExactBaseBlob': True,
                                 'oldExportsPreservedInOrder': 86, 'generatedNormalization': 'Only existing importmap/build-query stripping and CRLF to LF, as captured in baseline.'},
          'browser': {'scope': 'Original diagram visibly inspected and existing game compatibility only; no new held/guard UI or mesh response.',
                      'game': {'paused': True, 'kills': int(kills[1]), 'coverQueries': cover['counts']['queries'],
                               'allCompleted': True, 'boostClip1Observed': True, 'residentMeshes': 3,
                               'observedSpeedKmh': int(observed_speed[1])},
                      'buildId': '26d4da108a67b9d9', 'wasmBytes': 800982},
          'syntheticAttempts': archive, 'commands': commands, 'commandFiles': command_files,
          'initialBrowser': {'buildId': '055e57b764eb7731', 'evidence': initial_browser_evidence,
                             'scope': 'Preserved previous-build observation only; not current canonical browser acceptance.'},
          'evidence': evidence,
          'scope': 'Local Native/raw main-WASM exchange and accepted-only independent Fraction evidence. Messages alone are excluded. Host rejections are not filled with Native models. No public owned JS API/UI, World response, repeated-substep guarantee, actual allocation fault injection, allocator-used-byte or stack-highwater measurement. Public CI/Pages acceptance remains separate.'}
target = root / f'reports/{prefix}-local-verification.json'
target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['status', 'protectedFilesUnchanged', 'node', 'ctest', 'exports', 'sourceHeaders', 'mathematicsFixturesVerified']}))
