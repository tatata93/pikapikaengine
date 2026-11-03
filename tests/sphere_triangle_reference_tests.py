"""Deliberately corrupt saved packets to check the independent rational oracle."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sphere_triangle_oracle', root / 'scripts/verify-sphere-triangle.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
data = oracle.load(sys.argv[1])
baseline = oracle.verify(data)
first = next(i for i, fixture in enumerate(data['fixtures']) if fixture['result']['status'] == 0)
failure = next(i for i, fixture in enumerate(data['fixtures']) if fixture['result']['status'] != 0)


def geometry(packet):
    return packet['fixtures'][first]['result']['geometry']


def candidate(packet):
    return packet['fixtures'][first]['result']


def replace(target, key, value):
    target[key] = value


controls = [
    ('closest point', lambda p: replace(geometry(p), 'closest', [[1e99, 1e99]] * 3)),
    ('local closest point', lambda p: replace(geometry(p), 'closestLocal', [[1e99, 1e99]] * 3)),
    ('delta', lambda p: replace(geometry(p), 'delta', [[1e99, 1e99]] * 3)),
    ('barycentric', lambda p: replace(geometry(p), 'barycentric', [[1, 1]] * 3)),
    ('squared distance', lambda p: replace(geometry(p), 'squaredDistance', [0, 0])),
    ('distance', lambda p: replace(geometry(p), 'distance', [-1, 0])),
    ('gap', lambda p: replace(geometry(p), 'gap', [1e99, 1e99])),
    ('normal', lambda p: replace(geometry(p), 'normal', [[2, 2]] * 3)),
    ('sphere surface point', lambda p: replace(geometry(p), 'spherePoint', [[1e99, 1e99]] * 3)),
    ('stable surface ID', lambda p: replace(geometry(p), 'surfaceId', geometry(p)['surfaceId'] + 1)),
    ('missing completed geometry', lambda p: replace(candidate(p), 'geometry', None)),
    ('unknown status', lambda p: replace(candidate(p), 'status', 99)),
    ('completed with failure reason', lambda p: replace(candidate(p), 'reason', 1)),
    ('nonfinite bound', lambda p: replace(geometry(p), 'normal', [[float('nan'), 1]] * 3)),
    ('boolean bound', lambda p: replace(geometry(p), 'normal', [[False, True]] * 3)),
    ('invalid interval order', lambda p: replace(geometry(p), 'gap', [1, -1])),
    ('missing candidate', lambda p: candidate(p)['candidates'].pop()),
    ('dropped retained feature bit', lambda p: replace(geometry(p), 'survivingFeatures', 0)),
    ('wrong contact relation', lambda p: replace(geometry(p), 'relation', (geometry(p)['relation'] + 1) % 4)),
    ('partial failure geometry', lambda p: replace(p['fixtures'][failure]['result'], 'geometry', deepcopy(geometry(p)))),
    ('input radius mismatch', lambda p: replace(p['fixtures'][first]['input']['sphere'], 'radius', p['fixtures'][first]['input']['sphere']['radius'] * 2)),
    ('conditioning evidence', lambda p: replace(candidate(p), 'sineSquared', [-1, 0])),
    ('all geometry dropped', lambda p: replace(p, 'fixtures', [])),
]
records = []
for name, mutate in controls:
    packet = deepcopy(data)
    mutate(packet)
    try:
        oracle.verify(packet)
    except AssertionError as error:
        records.append({'name': name, 'rejected': True, 'diagnostic': str(error)})
    else:
        raise AssertionError('corruption was accepted: ' + name)

# Reordering fixtures and renaming labels does not alter the mathematical audit.
permuted = deepcopy(data)
permuted['fixtures'].reverse()
for i, fixture in enumerate(permuted['fixtures']):
    fixture['name'] = 'independent-label-' + str(i)
assert oracle.verify(permuted) == baseline

report = {'status': 'PASS', 'baseline': baseline, 'rejectedControls': records, 'labelAndOrderIndependent': True}
if '--output' in sys.argv:
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'reference.json').write_text(json.dumps(baseline, indent=2) + '\n', encoding='utf-8')
    (output / 'negative-controls.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'rejectedControls': len(records), 'labelAndOrderIndependent': True}))
