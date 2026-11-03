from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import math

root = Path(__file__).resolve().parents[2]
run = root / 'reports/sphere-triangle-lab-checks/run-20261103T234822368732Z'
browser = root / 'reports/sphere-triangle-lab-local-browser'


def load(path):
    # Python's default parse_int turns JSON -0 into integer +0. Preserve the
    # original binary64 sign for the download audit; do not modify the file.
    return json.loads(path.read_text(encoding='utf8'), parse_int=lambda s: -0.0 if s == '-0' else int(s))


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


checks = load(run / 'commands.json')
assert checks['status'] == 'PASS' and all(c['exit'] == 0 for c in checks['commands'])
node = (run / 'node.stdout.txt').read_text(encoding='utf8')
for marker in ['tests 516', 'pass 516', 'fail 0', 'skipped 0']:
    assert marker in node
for name, expected in checks['sdkAndAuthoredAssetsUnchanged'].items():
    assert digest(root / name) == expected, name
names = ['face', 'edge_ab', 'edge_bc', 'edge_ca', 'vertex_a', 'vertex_b', 'vertex_c', 'back', 'coincident', 'degenerate', 'thin', 'budget', 'normal_precision']
for index, name in enumerate(names):
    r = load(browser / (name + '.json'))
    assert r['diagnostics']['buildId'] == 'fc67426f445af36a' and r['diagnostics']['wasmBytes'] == 612824
    assert (r['result']['status'] == 'completed') == (index < 8)
    assert (r['result']['geometry'] is not None) == (index < 8)
dirty = load(browser / 'host-rejection.json')
assert not dirty['dirty']['saveEnabled'] and not dirty['dirty']['json']
assert not dirty['rejection']['saveEnabled'] and not dirty['rejection']['json']
assert 'ID requires' in dirty['rejection']['error']
downloaded, displayed = browser / 'downloaded.json', browser / 'edited-boundary.json'
assert downloaded.read_bytes() == displayed.read_bytes() and downloaded.stat().st_size == 2926
record = load(downloaded)
assert math.copysign(1, record['input']['sphere']['position'][0]) == -1
assert record['projection'] == 'xy' and record['result']['geometry']['relation'] == 'boundary_unresolved'
assert record['result']['geometry']['gap'][0] < 0 < record['result']['geometry']['gap'][1]
sources = ['tools/sphere-triangle-lab.mjs', 'tools/sphere-triangle-lab.html', 'tests/sphere-triangle-lab.test.mjs', 'scripts/build-web.mjs', 'tests/web-build.test.mjs', 'docs/learn/index.html']
report = {'schema': 1, 'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(), 'node': 516, 'dedicatedTests': 14,
          'browserPresets': 13, 'completedPresets': 8, 'expectedModelFailures': 5, 'signedZeroDownloadExact': True,
          'sdkAndAuthoredAssetsUnchanged': checks['sdkAndAuthoredAssetsUnchanged'], 'checks': checks['commands'],
          'files': {p.relative_to(root).as_posix(): digest(p) for folder in [run, browser] for p in sorted(folder.rglob('*')) if p.is_file()},
          'sources': {name: digest(root / name) for name in sources},
          'scope': 'Instantaneous manual read-only query lab; unchanged SDK. No new World, CCD, triangle response or GPU/physics performance claim.',
          'publicVerification': 'Not yet checked; recorded separately after milestone push.'}
(root / 'reports/sphere-triangle-lab-local-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({'status': report['status'], 'node': 516, 'browserPresets': 13, 'downloadBytes': 2926}))
