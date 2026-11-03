from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import struct

root = Path(__file__).resolve().parents[2]
run = root / 'reports/sphere-triangle-lab-checks/run-20261103T235808657751Z'
old = root / 'reports/sphere-triangle-lab-local-browser'
new = root / 'reports/sphere-triangle-lab-final-local-browser'


def load(path):
    return json.loads(path.read_text(encoding='utf8'), parse_int=lambda s: -0.0 if s == '-0' else int(s))


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


comparisons = 0


def compare(a, b):
    global comparisons
    if isinstance(a, (float, int)) and not isinstance(a, bool):
        assert not isinstance(b, bool) and isinstance(b, (float, int))
        assert struct.pack('>d', a) == struct.pack('>d', b)
        comparisons += 1
    elif isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b)
        for key in a:
            compare(a[key], b[key])
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b)
        for x, y in zip(a, b):
            compare(x, y)
    else:
        assert type(a) is type(b) and a == b


commands = load(run / 'commands.json')
assert commands['status'] == 'PASS' and all(c['exit'] == 0 for c in commands['commands'])
for key, expected in commands['sdkAndAuthoredAssetsUnchanged'].items():
    assert digest(root / key) == expected
node = (run / 'node.stdout.txt').read_text(encoding='utf8')
assert all(x in node for x in ['tests 516', 'pass 516', 'fail 0', 'skipped 0'])
names = ['face', 'edge_ab', 'edge_bc', 'edge_ca', 'vertex_a', 'vertex_b', 'vertex_c', 'back', 'coincident', 'degenerate', 'thin', 'budget', 'normal_precision']
for name in names:
    a, b = load(old / (name + '.json')), load(new / (name + '.json'))
    assert b['diagnostics']['buildId'] == '50e73448d9d02126' and b['diagnostics']['wasmBytes'] == 612824
    compare(a['input'], b['input'])
    compare(a['result'], b['result'])
report = {'schema': 1, 'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(), 'node': 516, 'browserCases': 13,
          'inputAndResultNumericBitsUnchanged': comparisons, 'sdkAndAuthoredAssetsUnchanged': commands['sdkAndAuthoredAssetsUnchanged'],
          'buildId': '50e73448d9d02126', 'scope': 'Only the drawing glyph ink expands by 1.5 SVG px per side. Original interval DTOs and numerical SDK remain unchanged. Full initial runs and final runs are retained separately.',
          'source': digest(root / 'tools/sphere-triangle-lab.mjs'),
          'files': {p.relative_to(root).as_posix(): digest(p) for folder in [run, new] for p in sorted(folder.rglob('*')) if p.is_file()}}
(root / 'reports/sphere-triangle-lab-marker-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({'status': 'PASS', 'node': 516, 'browserCases': 13, 'unchangedNumericBits': comparisons}))
