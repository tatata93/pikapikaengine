import hashlib
import json
import pathlib
import re
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]


def read(p):
    return json.loads((root / p).read_text(encoding='utf-8-sig'))


def sha(b):
    return hashlib.sha256(b).hexdigest()


archive = read('reports/derived-readback-archive.json')
for f in archive['files']:
    b = (root / f['path']).read_bytes()
    assert len(b) == f['bytes'] and sha(b) == f['sha256'], f['path']
for name in ['native-5deqh1ew', 'sdk-m2tud_m8', 'node-pj7nbhcr', 'syntax-n9pjd6yo', 'web-l3_827_i', 'profile-cly94mhw']:
    p = 'reports/derived-readback-checks/' + name + '/'
    c = read(p + 'command.json')
    assert c['exitCode'] == 0 and not c['timedOut']
node = (root / 'reports/derived-readback-checks/node-pj7nbhcr/stdout.txt').read_text(encoding='utf-8')
assert re.search(r'pass 452\b', node) and re.search(r'fail 0\b', node) and re.search(r'skipped 0\b', node)
ctest = (root / 'reports/derived-readback-checks/LastTest.log').read_bytes()
assert b'70 simulation C ABI test groups passed' in ctest
native = (root / 'reports/derived-readback-checks/native-5deqh1ew/stdout.txt').read_bytes()
assert b'100% tests passed, 0 tests failed out of 30' in native
assert (root / 'reports/derived-readback-checks/sdk-m2tud_m8/stderr.txt').stat().st_size == 0
profile = read('reports/derived-readback-profile/run-1793726212894-f47e88d240ce/parent-audit.json')
assert profile['status'] == 'PASS' and profile['numericComparisons'] == 406410
ref = read('reports/derived-readback-reference/run-2ho86lez/verification.json')
assert ref['sdkNumericComparisons'] == 2841
for mode, result in ref['transports'].items():
    assert result['readback'] == mode and result['nativeNumericBitComparisons'] == 2318
    assert result['referenceControls']['rejectedControls'] == 36
browser = read('reports/derived-readback-browser-verification.json')
assert (browser['status'], browser['browserReports'], browser['numericComparisons'], browser['draws']) == ('PASS', 1, 990, 20)
raw = read('reports/derived-readback-local-single-4.json')
assert raw['runtime']['wasmBytes'] == 592939 and raw['runtime']['buildId'] == 'c2aa5ebb6392265f'
game = read('reports/derived-readback-local-game.json')
assert game['launchEnabled'] and 'WEBGPU READY' in game['text']
m = read('assets/pikapika-simulation.build.json')
assert raw['manifest']['data'] == m
previous = json.loads(subprocess.check_output(['git', 'show', 'c232652:assets/pikapika-simulation.build.json'], cwd=root))
assert m['licenses'] == previous['licenses'] and m['linkedLibraryMembers'] == previous['linkedLibraryMembers']
changed = [p for p, h in m['sourceSha256'].items() if h != previous['sourceSha256'][p]]
assert sorted(changed) == ['core/include/pikapika/simulation_api.h', 'core/src/simulation_api.cpp']
sdk = []
for family in ['sourceSha256', 'licenses', 'artifacts']:
    for p, expected in m[family].items():
        h = expected['sha256'] if isinstance(expected, dict) else expected
        b = (root / p).read_bytes()
        assert sha(b) == h, p
        sdk.append(dict(path=p, bytes=len(b), sha256=h))
header = (root / 'core/include/pikapika/simulation_api.h').read_text(encoding='utf-8')
assert len(set(re.findall(r'\b(pp_sim_\w+)\s*\(', header))) == 66
names = ['.github/workflows/verify.yml', 'core/include/pikapika/simulation_api.h', 'core/src/simulation_api.cpp',
         'tests/simulation_api_tests.cpp', 'engine/simulation.mjs', 'tools/derived-profile.mjs',
         'scripts/verify-derived-profile.mjs', 'scripts/profile-derived-readback.mjs',
         'tests/derived-profile.test.mjs', 'tests/derived-profile-cli.test.mjs',
         'tests/derived-mesh-sdk.test.mjs', 'tests/derived-gpu-profile.test.mjs',
         'tests/derived-readback-cli.test.mjs', 'docs/learn/diagrams/derived-readback.svg']
sources = {p: sha((root / p).read_bytes()) for p in names}
extra = ['reports/derived-readback-local-single-4.json', 'reports/derived-readback-browser-verification.json',
         'reports/derived-readback-browser-command.txt', 'reports/derived-readback-local.png',
         'reports/derived-readback-local-game.json', 'reports/derived-readback-local-game.png',
         'reports/derived-readback-diagram.png']
for path in (root / 'reports/derived-readback-recipes').glob('*'):
    if path.is_file():
        extra.append(str(path.relative_to(root)).replace('\\', '/'))
files = [dict(path=p, bytes=len((root / p).read_bytes()), sha256=sha((root / p).read_bytes())) for p in extra]
result = dict(status='LOCAL PASS; public CI/Pages unconfirmed', nodePassed=452, nodeSkipped=0,
              nativeGroups=744, nativeAbiGroups=70, ctests=30, exports=66, sourceHashes=sources,
              sdkAudit=sdk, sdkCompiledSourceChanges=changed, noticeHashesAndLinkedStandardLibrariesUnchanged=True,
              numericComparisons=2841, profileNativeBitsPerTransport=2318, negativeControlsPerTransport=36,
              profileQueries=60, profileNumericComparisons=406410, localCompatibilityDraws=20,
              localCompatibilityNumericComparisons=990, batchBrowserComparisonImplemented=False,
              robotStartupReady=True, robotCombatRetested=False, files=files)
(root / 'reports/derived-readback-verification.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps({k: v for k, v in result.items() if k not in ['files', 'sourceHashes', 'sdkAudit']}))
