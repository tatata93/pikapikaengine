"""Collect completed finite observations; never rerun or accept unexecuted gates."""
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf8'))
def require(ok, reason):
    if not ok:
        raise ValueError(reason)
def stamp(path):
    raw = (ROOT / path).read_bytes()
    return {'path': path, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}

native_path = 'reports/world-static-mesh-flight-advance-checks/run-20261105-native-integration-002/result.json'
web_path = 'reports/world-static-mesh-flight-advance-checks/run-20261105-web-integration-001/result.json'
post_path = 'reports/world-static-mesh-flight-advance-checks/run-20261105-post-movhpd-artifact-001/audit.json'
machine_path = 'reports/world-static-mesh-flight-advance-machine-review/run-integrated-001/evidence.json'
legacy_path = 'reports/world-static-mesh-flight-advance-checks/run-20261105-legacy-integration-001/result.json'
capture_path = 'reports/world-static-mesh-flight-advance-checks/run-20261105-transaction-capture-001/result.json'
provenance_path = 'reports/world-static-mesh-flight-advance-checks/run-20261105-transaction-provenance-001/result.json'
reference_path = 'reports/world-static-mesh-flight-advance-reference-development/run-001/freeze.json'
probe_command_path = 'reports/world-static-mesh-flight-advance-checks/run-20261105-probe-command-001/result.json'
native, web, post = read(native_path), read(web_path), read(post_path)
legacy = read(legacy_path)
capture, provenance = read(capture_path), read(provenance_path)
reference, probe_command = read(reference_path), read(probe_command_path)
require(native['status'] == 'PASS' and len(native['commands']) == 12 and
        all(row['exitCode'] == 0 for row in native['commands']), 'Actual Native12 commands')
require(native['advanceGroups'] == 9 and native['ctestPassed'] == native['ctestDiscovered'] == 47,
        'Actual Native finite groups/CTest')
require(native['clockReference']['status'] == 'PASS' and native['clockReference']['cases'] == 18,
        'Actual Native clock corpus')
require(web['status'] == 'PASS' and web['sourcesAndArtifactsUnchanged'] is True and
        all(row['exitCode'] == 0 for row in web['commands']), 'Actual Node/syntax/Web compatibility')
require(post['status'] == 'PASS' and post['binaryExecuted'] is False and post['artifactsStable'] and
        post['sourcesStable'] and post['toolsStable'] and post['recipeStable'], 'Post-MOVHPD actual MSVC gate')
require(post['profile']['buildId'] == native['buildId'] and len(post['profile']['sources']) == 7,
        'Actual same seven-source identity')
require(all(post['advanceScope'][key] is False for key in
            ('clockInstructionsAudited', 'commitPathAudited', 'WorldAdvanceAccepted')), 'Incomplete proof stays explicit')
require(legacy['status'] == 'PASS' and legacy['sourceAndArtifactStable'] is True and
        len(legacy['commands']) == 18 and all(row['exitCode'] == 0 for row in legacy['commands']),
        'Actual old/new legacy and reference commands')
require(len(legacy['rawComparisons']) == 6 and all(row['rawByteEqual'] is True and
        row['normalization'] == 'NONE' for row in legacy['rawComparisons']), 'Six raw-byte probe pairs')
require(legacy['guardComparison']['status'] == 'PASS' and legacy['guardComparison']['fixtures'] == 51 and
        legacy['newBuildId'] == native['buildId'] and
        legacy['independentSelfTestGroups'] == 12 and legacy['independentRejectedControls'] == 138 and
        legacy['independentLabelAndOrder'] is True, 'Integrated 51-input independent references')
require(capture['status'] == 'FINITE_FIXTURE_CAPTURE_PASS' and capture['cases'] == 51 and
        capture['protectedUnchanged'] is True and capture['newArtifactMachineAccepted'] is False and
        capture['independentTransactionCheckerPassed'] is False, 'Actual saved transaction capture scope')
require(provenance['status'] == 'PASS' and provenance['inputPairs'] == 51 and
        provenance['actualOwnedGuardsCompared'] == 50 and provenance['actualPreGuardClockRefusals'] == 1 and
        provenance['inputsAndRecipeUnchanged'] is True, 'Actual saved input/owned-guard provenance')
require(reference['status'] == 'PASS' and reference['actualReference']['status'] == 'PASS' and
        reference['actualReference']['fixtures'] == 51 and reference['actualReference']['committed'] == 14 and
        reference['actualReference']['actualOwnedGuardsVerified'] == 50 and
        reference['selfTestGroups'] == 14 and reference['negativeControls'] == 85 and
        reference['labelAndOrderIndependent'] is True and
        reference['optimizedPythonRejected']['status'] == 'PASS', 'Actual independent transaction reference/controls')
require(reference['actualFixture'] == stamp(capture['fixture']['path']) and
        all(row == stamp(row['path']) for row in reference['sources']), 'Actual fixture/checker source bytes')
require(probe_command['status'] == 'COMMAND_PROVENANCE_PASS' and probe_command['before'] == probe_command['after'] and
        probe_command['actualNewStrictWerrorMainCommands'] == 1 and probe_command['newArtifactMachineAccepted'] is False,
        'Actual new fixture-main command observation, not instruction proof')
for item in native['actualArtifacts']:
    require(stamp(item['path']) == item, 'Actual integrated artifact changed: ' + item['path'])
current_sources = [item['path'] for item in post['profile']['sources']] + [
    'CMakeLists.txt', 'cmake/WorldFlightBinding.cmake', 'tests/world_static_mesh_flight_advance_tests.cpp',
    'tests/world_static_mesh_flight_advance_fixtures.cpp', 'tests/world_static_mesh_flight_advance_fixture_support.hpp',
    'scripts/verify-world-static-mesh-flight-advance.py', 'tests/world_static_mesh_flight_advance_reference_tests.py',
    'reports/world-static-mesh-flight-guard-recipes/audit-binding.py']
result = {'schema': 1, 'status': 'LOCAL_FINITE_INTEGRATION_PASS', 'localCMakeRegistered': True,
          'committed': False, 'publicAccepted': False, 'GNUAccepted': False,
          'completeClockGraphProved': False, 'completeCommitCompilerAttestation': False,
          'scope': 'Local actual CMake/MSVC integration, finite9/18 behavior, independent clocks,47CTest, Debug refusals, existing Vec3/caller/compile gate and Web compatibility. Separate saved transaction51 and independent14self/85reject verify complete pre/post data and180 actual mathematical children. New probe command provenance is not new instruction proof; machine review remains observational. No SDK/FixedClock/response integration.',
          'native': stamp(native_path), 'web': stamp(web_path), 'postMovhpdAudit': stamp(post_path),
          'legacyAndIndependentReference': stamp(legacy_path),
          'transactionCapture': stamp(capture_path), 'transactionProvenance': stamp(provenance_path),
          'transactionIndependentReference': stamp(reference_path), 'transactionProbeCommands': stamp(probe_command_path),
          'savedTransactionPacket': stamp(capture['fixture']['path']),
          'rawProbePairsEqual': 6, 'guardFixturesEqualExceptBindingId': 51,
          'guardIndependentSelfTests': 12, 'guardIndependentRejectedControls': 138,
          'completeAdvanceTransactionFixturePersisted': True,
          'independentTransactionCheckerPassed': True,
          'transactionIndependentSelfTests': 14, 'transactionRejectedControls': 85,
          'actualTransactionCommitted': 14, 'actualTransactionFailed': 37,
          'newTransactionProbeMachineAccepted': False,
          'observationalMachineReview': stamp(machine_path), 'buildId': native['buildId'],
          'advanceGroups': 9, 'clock': native['clockReference'], 'ctestPassed': 47,
          'currentSources': [stamp(path) for path in current_sources],
          'historicalPrototype': 'reports/world-static-mesh-flight-advance-prototype-verification.json',
          'history': 'Long-path initial Native001 failed MSB3491; short-path fresh002 succeeded. Initial raw is retained. Header/CPP/test and frozen149 prototype evidence remain unchanged.',
          'next': ['Five-source GNU guard public acceptance was completed at d302 and recorded at0635542; retain its separate scope.',
                   'Extend actual GNU advance/Werror/sanitizer/clock gates; local legacy and independent reference regressions have passed.',
                   'Register the transaction fixture target and independent checks in the main build/GNU workflow. Local saved51/independent14self85reject have passed; standalone probe command evidence is distinct from new executable instruction proof.',
                   'Keep source-contract inferences, finite runtime checks and machine observations distinct from full symbolic clock/commit proof.']}
output = ROOT / 'reports/world-static-mesh-flight-advance-native-integration-verification.json'
output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8', newline='\n')
print(json.dumps({'status': result['status'], 'buildId': result['buildId'], 'committed': False, 'publicAccepted': False}))
