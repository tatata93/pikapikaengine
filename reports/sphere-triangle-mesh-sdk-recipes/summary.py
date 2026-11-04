"""Summarize completed local commands and preserve exact scope boundaries."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json

root = Path(__file__).resolve().parents[2]
out = root / 'reports/sphere-triangle-mesh-sdk-checks/run-20261104-root'
def read(p):
    return json.loads(p.read_text(encoding='utf8'))
def digest(p):
    data = p.read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}
commands = sum([read(out / (phase + '-commands.json')) for phase in ['native', 'wasm', 'validate']], [])
assert all(c['exit'] == 0 for c in commands)
for c in commands:
    assert digest(root / c['stdout']) == c['stdoutHash'] and digest(root / c['stderr']) == c['stderrHash']
sdk = read(out / 'sdk/report.json')
assert sdk['status'] == 'PASS' and (sdk['modelFixtures'], sdk['completed'], sdk['expectedModelFailures'], sdk['hostRejected']) == (45, 29, 16, 3)
assert (sdk['packetNumericComparisons'], sdk['modelNumericComparisons'], sdk['negativeZeroComparisons']) == (27160, 20808, 4453)
assert sdk['reference']['primitiveReference']['referenceComponents'] + sdk['reference']['aggregateReferenceComponents'] == 2775
assert len(read(out / 'sdk/negative-controls/negative-controls.json')['rejectedControls']) == 43
assert '100% tests passed, 0 tests failed out of 34' in (out / 'ctest.stdout.txt').read_text(encoding='utf8')
node = (out / 'node.stdout.txt').read_text(encoding='utf8')
assert all(marker in node for marker in ['tests 526', 'pass 526', 'fail 0', 'skipped 0'])
assert 'Web build 1f40cf023bb8472f: 46 versioned modules' in (out / 'web-build.stdout.txt').read_text(encoding='utf8')
baseline = read(root / 'reports/sphere-triangle-mesh-sdk-baseline.json')
for p, expected in baseline['protectedSourcesAndNotices'].items():
    assert digest(root / p) == expected, p
for p, expected in baseline['assetsAndSampleSourceBeforeBuild'].items():
    if p not in ['assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.build.json']:
        assert digest(root / p) == expected, p
manifest = read(root / 'assets/pikapika-simulation.build.json')
assert len(manifest['sourceSha256']) == 57 and len(manifest['licenses']) == 7
assert manifest['licenses'] == baseline['oldManifest']['licenses']
added_members = sorted(set(manifest['linkedLibraryMembers']) - set(baseline['oldManifest']['linkedLibraryMembers']))
removed_members = sorted(set(baseline['oldManifest']['linkedLibraryMembers']) - set(manifest['linkedLibraryMembers']))
assert added_members == ['libc++-debug-legacyexcept.a(algorithm.o)'] and not removed_members
exports = json.loads(next(f.split('=', 1)[1] for f in manifest['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')))
assert len(exports) == len(set(exports)) == 74
for p, expected in manifest['artifacts'].items():
    assert digest(root / p) == expected, p
assert manifest['artifacts']['assets/pikapika-simulation.wasm']['bytes'] == 638777
cover = read(root / 'reports/sphere-triangle-mesh-sdk-local-browser/cover.json')
assert cover['state'] == 'ready' and cover['failure'] is None and not cover['errors'] and cover['pending'] is None
assert cover['renderer']['residentMeshes'] == 3 and cover['counts']['queries'] == cover['counts']['checked'] == cover['counts']['validated'] == 22
assert cover['startup']['diagnostics']['wasmBytes'] == 638777 and cover['startup']['diagnostics']['buildId'] == '1f40cf023bb8472f'
assert all(r['state'] == 'completed' for r in cover['records']) and any(r['clipSeconds'] == 1 for r in cover['records'])
native = read(root / 'reports/sphere-triangle-mesh-sdk-core-proof/acceptance.json')
assert native['nativeGroups'] == 18 and native['existingApiGroups'] == 77 and native['asan']['status'] == 'NOT_COMPLETED'
old = read(out / 'single-sdk/report.json')
assert old['status'] == 'PASS' and old['packetNumericComparisons'] == 22327 and old['modelNumericComparisons'] == 13432
report = {'schema': 1, 'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(), 'commands': commands,
          'ctest': 34, 'node': 526, 'exports': 74, 'sourceHeaders': 57, 'nativeSdkGroups': 18, 'existingApiGroups': 77,
          'sdk': sdk, 'artifacts': manifest['artifacts'], 'protectedSourcesAndNoticesUnchanged': True,
          'authoredAssetsAndGameSourceUnchanged': True, 'licensesUnchanged': True,
          'linkedRuntimeMembersAdded': added_members, 'linkedRuntimeMembersRemoved': removed_members,
          'webBuild': '1f40cf023bb8472f', 'webModules': 46, 'webEntries': 22,
          'localBrowser': {'wasmBytes': 638777, 'coverQueriesAllCompleted': 22, 'fullOpenObservedInRecords': True, 'residentMeshes': 3,
                           'scope': 'Existing game compatibility, mixed generation history retained; not new mesh contact or a performance guarantee.'},
          'localAsan': native['asan'], 'publicCiAndPages': 'NOT_YET_VERIFIED',
          'scope': 'Instantaneous read-only mesh geometry SDK; no World/CCD/manifold/response integration.'}
(root / 'reports/sphere-triangle-mesh-sdk-local-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: report[k] for k in ['status', 'ctest', 'node', 'exports', 'sourceHeaders', 'nativeSdkGroups', 'existingApiGroups', 'webBuild']}))
