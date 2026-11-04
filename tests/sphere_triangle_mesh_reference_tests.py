"""Corrupt finite-union packets; reference checks must reject every mutation."""
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mesh_reference', root / 'scripts/verify-sphere-triangle-mesh.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
data = oracle.load(sys.argv[1])
baseline = oracle.verify(data)
completed = next(i for i, f in enumerate(data['fixtures']) if f['result']['status'] == 0)
multiple = next(i for i, f in enumerate(data['fixtures']) if f['result']['status'] == 0 and len(f['result']['nearest']['possibleSurfaceIds']) > 1)
dominated = next(i for i, f in enumerate(data['fixtures']) if f['result']['status'] == 0 and len(f['result']['nearest']['possibleSurfaceIds']) < len(f['result']['rows']))
failure = next(i for i, f in enumerate(data['fixtures']) if f['result']['status'] == 3)
invalid = next(i for i, f in enumerate(data['fixtures']) if f['result']['status'] in (1, 2))


def result(packet, index=completed):
    return packet['fixtures'][index]['result']


def nearest(packet):
    return result(packet)['nearest']


def geometry(packet):
    return result(packet)['rows'][0]['query']['geometry']


def put(target, key, value):
    target[key] = value


def flip_source_zero(packet):
    rows = result(packet)['rows']
    for row in rows:
        for vertex in row['triangle']['vertices']:
            for i, value in enumerate(vertex):
                if value == 0:
                    vertex[i] = 0.0 if math.copysign(1, value) < 0 else -0.0
                    return
    raise AssertionError('control requires an exact zero coordinate')


def add_dominated_id(packet):
    r = result(packet, dominated)
    ids = r['nearest']['possibleSurfaceIds']
    ids.append(next(row['triangle']['id'] for row in r['rows'] if row['triangle']['id'] not in ids))
    ids.sort()


controls = [
    ('unknown mesh status', lambda p: put(result(p), 'status', 99)),
    ('boolean mesh status', lambda p: put(result(p), 'status', False)),
    ('completed with failed reason', lambda p: put(result(p), 'reason', 7)),
    ('missing nearest', lambda p: put(result(p), 'nearest', None)),
    ('dropped tied possible surface', lambda p: result(p, multiple)['nearest']['possibleSurfaceIds'].pop()),
    ('all winners dropped', lambda p: put(nearest(p), 'possibleSurfaceIds', [])),
    ('duplicate winner ID', lambda p: nearest(p)['possibleSurfaceIds'].append(nearest(p)['possibleSurfaceIds'][0])),
    ('unknown winner ID', lambda p: put(nearest(p), 'possibleSurfaceIds', [9007199254740991])),
    ('strictly dominated surface retained', add_dominated_id),
    ('wrong scalar squared distance', lambda p: put(nearest(p), 'squaredDistance', [0, 0])),
    ('wrong scalar distance', lambda p: put(nearest(p), 'distance', [-1, 0])),
    ('wrong scalar gap', lambda p: put(nearest(p), 'gap', [1e90, 1e90])),
    ('reversed aggregate interval', lambda p: put(nearest(p), 'distance', [2, 1])),
    ('boolean aggregate interval', lambda p: put(nearest(p), 'gap', [False, True])),
    ('nonfinite aggregate interval', lambda p: put(nearest(p), 'distance', [0, float('inf')])),
    ('invented aggregate normal', lambda p: put(nearest(p), 'normal', [0, 1, 0])),
    ('copied source ID mismatch', lambda p: put(result(p)['rows'][0]['triangle'], 'id', 0)),
    ('copied source position mismatch', lambda p: put(result(p)['rows'][0]['triangle'], 'vertices', [[9, 9, 9]] * 3)),
    ('copied source negative zero lost', flip_source_zero),
    ('row dropped', lambda p: result(p)['rows'].pop()),
    ('real query replaced by null', lambda p: put(result(p)['rows'][0], 'query', None)),
    ('row count fabricated', lambda p: put(result(p), 'queries', result(p)['queries'] + 1)),
    ('boolean work count', lambda p: put(result(p), 'queries', True)),
    ('candidate work fabricated', lambda p: put(result(p), 'candidatesExamined', result(p)['candidatesExamined'] + 1)),
    ('sqrt work fabricated', lambda p: put(result(p), 'sqrtRefinements', result(p)['sqrtRefinements'] + 1)),
    ('limited work fabricated', lambda p: put(result(p), 'sqrtLimitedRows', result(p)['sqrtLimitedRows'] + 1)),
    ('failed work fabricated', lambda p: put(result(p), 'failedRows', 1)),
    ('completed with failed index', lambda p: put(result(p), 'failedIndex', 0)),
    ('completed with first failure', lambda p: put(result(p), 'firstFailedRow', 0)),
    ('failed row hidden as global success', lambda p: put(result(p, failure), 'status', 0)),
    ('failed rows given nearest', lambda p: put(result(p, failure), 'nearest', deepcopy(nearest(p)))),
    ('failed work hidden', lambda p: put(result(p, failure), 'failedRows', 0)),
    ('first failure hidden', lambda p: put(result(p, failure), 'firstFailedRow', None)),
    ('prevalidation exposes rows', lambda p: put(result(p, invalid), 'rows', deepcopy(result(p)['rows']))),
    ('prevalidation exposes nearest', lambda p: put(result(p, invalid), 'nearest', deepcopy(nearest(p)))),
    ('valid source falsely rejected', lambda p: put(result(p), 'status', 1)),
    ('primitive closest point', lambda p: put(geometry(p), 'closest', [[1e80, 1e80]] * 3)),
    ('primitive normal', lambda p: put(geometry(p), 'normal', [[2, 2]] * 3)),
    ('primitive distance', lambda p: put(geometry(p), 'distance', [0, 0])),
    ('primitive candidate omitted', lambda p: result(p)['rows'][0]['query']['candidates'].pop()),
    ('unused KKT sign removed', lambda p: put(result(p)['rows'][0]['query']['candidates'][0], 'kkt', [[0, 0], [0, 0]])),
    ('primitive sqrt flag type', lambda p: put(result(p)['rows'][0]['query'], 'sqrtRefinementLimited', 0)),
    ('all fixtures dropped', lambda p: put(p, 'fixtures', [])),
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
        raise AssertionError('corruption accepted: ' + name)
permuted = deepcopy(data)
permuted['fixtures'].reverse()
for i, fixture in enumerate(permuted['fixtures']):
    fixture['name'] = 'independent-label-' + str(i)
assert oracle.verify(permuted) == baseline
report = {'status': 'PASS', 'baseline': baseline, 'rejectedControls': records, 'labelAndOrderIndependent': True}
if '--output' in sys.argv:
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    output.mkdir(parents=True, exist_ok=False)
    (output / 'reference.json').write_text(json.dumps(baseline, indent=2) + '\n', encoding='utf8')
    (output / 'negative-controls.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({'status': 'PASS', 'rejectedControls': len(records), 'labelAndOrderIndependent': True}))
