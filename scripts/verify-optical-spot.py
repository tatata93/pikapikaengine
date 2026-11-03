"""Fail-closed rational checks of finite prescribed-route geometric spots.

Required Native JSON fixtures or CSV oracle, optional standalone WASM packet.
JSON numeric tokens have binary64 semantics; -O is refused. Finite sampling is
not a continuous-pupil integration or diffraction/radiometric-image proof.
"""
import argparse
import copy
import csv
from fractions import Fraction as F
import itertools
import json
import math
from pathlib import Path
import struct

if not __debug__:
    raise SystemExit('Python -O is rejected')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def keys(value, expected):
    require(type(value) is dict and value.keys() == set(expected), 'missing/unknown schema keys')


def number(value):
    require(type(value) is float and math.isfinite(value), 'finite binary64 number required')
    return value


def integer(value, lo, hi):
    require(number(value).is_integer() and lo <= value <= hi, 'integer range/schema')
    return int(value)


def vector(value, count=3):
    require(type(value) is list and len(value) == count, 'vector length/schema')
    for v in value:
        number(v)


def bounds(value):
    vector(value, 2)
    require(value[0] <= value[1], 'reversed interval')


def box(value):
    require(type(value) is list and len(value) == 3, 'box length/schema')
    for v in value:
        bounds(v)


def identity(actual, expected, path=''):
    if type(expected) is dict:
        keys(actual, expected)
        for k in expected:
            identity(actual[k], expected[k], path + '/' + k)
    elif type(expected) is list:
        require(type(actual) is list and len(actual) == len(expected), 'array identity ' + path)
        for j, (a, b) in enumerate(zip(actual, expected)):
            identity(a, b, path + '/' + str(j))
    elif type(expected) in (int, float):
        require(struct.pack('>d', number(actual)) == struct.pack('>d', float(expected)), 'binary64 identity ' + path)
    else:
        require(type(actual) is type(expected) and actual == expected, 'typed identity ' + path)


def point(values):
    return [[-0.0 if v == 0 else v, v] for v in values]


def ray(origin, direction, lo=0, hi=10):
    return dict(origin=point(origin), direction=point(direction), minimumParameter=lo, maximumParameter=hi)


def shape(kind=0, center=None, axis=None, radius=0, aperture=10):
    return dict(kind=kind, center=center if center is not None else [0, 0, 0], axis=axis if axis is not None else [0, 0, -1], radius=radius, aperture=aperture)


def step(surface, index):
    return dict(surface=surface, branch=1, nextIndex=index, minimumParameter=0, maximumParameter=10)


def experiments():
    positions = [[-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0]]
    base = dict(samples=[dict(ray=ray(v, [0, 0, 2]), weight=j + 1) for j, v in enumerate(positions)], steps=[], initialIndex=[1, 1], wavelength=550e-9,
                sensor=shape(center=[0, 0, 1]), sensorMinimumParameter=0, sensorMaximumParameter=10,
                settings=dict(maximumSteps=64, maximumParameterWidth=1e6, primitiveMaxSqrtRefinements=128, maxSamples=1024, maxEvaluations=1024, maxSqrtRefinements=1000000))
    out = {}
    def add(name):
        c = copy.deepcopy(base); out[name] = c; return c
    def plates(n=None):
        return [step(shape(), n if n is not None else [1.5, 1.5]), step(shape(center=[0, 0, .25], axis=[0, 0, 1]), [1, 1])]
    def lens(c, h):
        c['sensor']['center'][2] = 639. / 11800.
        c['steps'] = [step(shape(2, radius=.05, axis=[0, 0, 1], aperture=.015), [1.5, 1.5]), step(shape(2, center=[0, 0, .005], axis=[0, 0, 1], radius=-.05, aperture=.015), [1, 1])]
        c['samples'] = [dict(ray=ray(v, [0, 0, 1]), weight=1) for v in [[h, 0, -.025], [-h, 0, -.025], [0, h, -.025], [0, -h, -.025]]]
    add('identity')
    c = add('scaled-weights')
    for sample in c['samples']:
        sample['weight'] *= 8
    add('tilted-sensor')['sensor']['axis'] = [3, 0, 4]
    for name, n in [('plates', [1.5, 1.5]), ('spectral-interval', [1.49, 1.51])]:
        c = add(name); c['steps'] = plates(n); c['sensor']['center'][2] = 1.25
        for sample in c['samples']:
            sample['ray']['origin'][2] = [-1, -1]
    c = add('route-miss'); c['samples'] = c['samples'][:1]; c['steps'] = [step(shape(aperture=.25), [1, 1])]
    c = add('mixed-route-miss'); c['samples'] = c['samples'][:2]; c['samples'][0]['ray']['origin'][0] = [-0., 0]; c['steps'] = [step(shape(aperture=.25), [1, 1])]
    c = add('sensor-miss'); c['samples'] = c['samples'][:1]; c['sensor']['aperture'] = .25
    c = add('mixed-sensor-miss'); c['samples'] = c['samples'][:2]; c['samples'][0]['ray']['origin'][0] = [-0., 0]; c['sensor']['aperture'] = .25
    c = add('unknown-sensor'); c['samples'] = c['samples'][:2]; c['samples'][0]['ray']['origin'][0] = [-0., 0]; c['samples'][1]['ray']['origin'][0] = [.25, .25]; c['sensor']['aperture'] = .25
    c = add('unknown-route'); c['samples'] = c['samples'][:2]; c['samples'][0]['ray']['origin'][0] = [-0., 0]; c['steps'] = [step(shape(aperture=1), [1, 1])]
    c = add('unavailable-transmission'); c['samples'] = [dict(ray=ray([0, 0, -1], [4, 0, 3]), weight=1)]; c['initialIndex'] = [1.5, 1.5]; c['steps'] = [step(shape(), [1, 1])]
    add('evaluation-budget')['settings']['maxEvaluations'] = 1
    c = add('total-sqrt-budget'); lens(c, .001); c['settings']['maxSqrtRefinements'] = 1
    c = add('primitive-budget'); c['samples'] = [dict(ray=ray([0, 0, 0], [.125, 0, 1]), weight=1)]; c['steps'] = [step(shape(1, center=[0, 0, 3], axis=[0, 0, 1], radius=1, aperture=0), [1.5, 1.5])]; c['settings'].update(primitiveMaxSqrtRefinements=1, maximumParameterWidth=.01)
    add('invalid-late-weight')['samples'][-1]['weight'] = 0
    c = add('invalid-late-shape'); c['steps'] = plates(); c['steps'][1]['surface'] = shape(1, axis=[0, 0, 1], radius=-1, aperture=0)
    add('empty')['samples'] = []
    add('sample-budget')['settings']['maxSamples'] = 1
    c = add('step-budget'); c['steps'] = plates(); c['settings']['maximumSteps'] = 1
    c = add('zero-direction'); c['samples'] = c['samples'][:1]; c['samples'][0]['ray']['direction'] = point([0, 0, 0])
    c = add('sensor-boundary'); c['samples'] = c['samples'][:1]; c['sensorMaximumParameter'] = .5
    lens(add('lens-small'), .0005); lens(add('lens-marginal'), .014)
    c = add('finite-source')
    for j, v in enumerate(positions):
        c['samples'][j]['ray'] = ray([0, 0, -1], v[:2] + [1])
        c['samples'][j]['ray']['direction'][2] = [math.nextafter(1, -math.inf), math.nextafter(1, math.inf)]
    return out


def ray_schema(v):
    keys(v, {'origin', 'direction', 'minimumParameter', 'maximumParameter'}); box(v['origin']); box(v['direction'])
    require(0 <= number(v['minimumParameter']) <= number(v['maximumParameter']) <= 1e9, 'ray domain')


def completion_schema(c):
    keys(c, {'ray', 'index', 'totals'}); ray_schema(c['ray']); bounds(c['index']); require(1e-6 <= c['index'][0] <= c['index'][1] <= 1e6, 'phase range')
    keys(c['totals'], {'distance', 'opticalPathLength', 'throughput'})
    for v in c['totals'].values():
        bounds(v); require(v[0] >= 0, 'negative path total')
    require(c['totals']['throughput'][1] <= 1, 'power range')


def hit_schema(h):
    keys(h, {'parameter', 'distance', 'position', 'geometricNormal', 'incidentNormal', 'frontFace'})
    bounds(h['parameter']); bounds(h['distance']); require(h['parameter'][0] >= 0 and h['distance'][0] >= 0, 'accepted hit parameter')
    for k in ['position', 'geometricNormal', 'incidentNormal']:
        box(h[k])
    require(type(h['frontFace']) is bool, 'front flag')


def sensor_schema(g):
    keys(g, {'status', 'reason', 'rootCount', 'consideredCount', 'sqrtRefinements', 'refinementLimited', 'nearest'})
    integer(g['status'], 0, 2); integer(g['reason'], 0, 14); integer(g['consideredCount'], 0, integer(g['rootCount'], 0, 1)); integer(g['sqrtRefinements'], 0, 1024)
    require(type(g['refinementLimited']) is bool, 'sensor limited flag')
    if g['status'] == 0:
        hit_schema(g['nearest'])
    else:
        require(g['nearest'] is None, 'nonhit sensor leaks hit')


def fraction(value):
    return F.from_float(number(value))


def includes(interval, lo, hi=None):
    bounds(interval); hi = lo if hi is None else hi
    require(fraction(interval[0]) <= lo <= hi <= fraction(interval[1]), 'independent rational enclosure')


def variance_axis(boxes, weights):
    """Exact min/max of weighted finite-sample variance over independent boxes.

    Convexity makes the maximum a box vertex. The minimum uses xi=clamp(c,boxi)
    with c the weighted mean; each interval between endpoints has a linear
    fixed-point equation. These fixtures have at most four accepted points.
    """
    total = sum(weights)
    def variance(values):
        mean = sum(w*x for w, x in zip(weights, values)) / total
        return sum(w*(x-mean)**2 for w, x in zip(weights, values)) / total
    maximum = max(variance(v) for v in itertools.product(*boxes))
    endpoints = sorted({v for pair in boxes for v in pair})
    candidates = list(endpoints)
    for lo, hi in zip(endpoints, endpoints[1:]):
        middle = (lo + hi) / 2; outside_weight = outside_sum = F(0)
        for (a, b), w in zip(boxes, weights):
            if middle < a or middle > b:
                outside_weight += w; outside_sum += w*(a if middle < a else b)
        if outside_weight:
            root = outside_sum / outside_weight
            if lo <= root <= hi:
                candidates.append(root)
        else:
            candidates.append(middle)
    minimum = min(variance([max(a, min(b, c)) for a, b in boxes]) for c in candidates)
    return minimum, maximum


def stats_references(r, samples):
    st = r['finalStats']; keys(st, {'totalWeight', 'acceptedWeight', 'moments'})
    total = sum(fraction(x['weight']) for x in samples)
    accepted = [rec for rec in r['records'] if rec['status'] == 1]
    weights = [fraction(rec['weight']) for rec in accepted]; weight = sum(weights)
    includes(st['totalWeight'], total); includes(st['acceptedWeight'], weight)
    if not accepted:
        require(st['moments'] is None, 'empty acceptance has no centroid/variance')
        return 2
    m = st['moments']; keys(m, {'centroid', 'meanSquaredRadius', 'hull'}); box(m['centroid']); box(m['hull']); bounds(m['meanSquaredRadius']); require(m['meanSquaredRadius'][0] >= 0, 'variance nonnegative')
    minimum = maximum = F(0)
    for k in range(3):
        boxes = [(fraction(rec['sensor']['nearest']['position'][k][0]), fraction(rec['sensor']['nearest']['position'][k][1])) for rec in accepted]
        lo = sum(w*x[0] for w, x in zip(weights, boxes)) / weight; hi = sum(w*x[1] for w, x in zip(weights, boxes)) / weight
        includes(m['centroid'][k], lo, hi); includes(m['hull'][k], min(x[0] for x in boxes), max(x[1] for x in boxes))
        a, b = variance_axis(boxes, weights); minimum += a; maximum += b
    includes(m['meanSquaredRadius'], minimum, maximum)
    return 9


def unique_keys(pairs):
    out = {}
    for k, v in pairs:
        require(k not in out, 'duplicate JSON key'); out[k] = v
    return out


def fixtures(path):
    def bad_constant(v):
        raise ValueError('nonstandard JSON number ' + v)
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_int=float, parse_float=float, parse_constant=bad_constant, object_pairs_hook=unique_keys)
    keys(data, {'version', 'model', 'fixtures', 'launch', 'paraxial'}); integer(data['version'], 1, 1)
    require(data['model'] == 'prescribed-route finite geometric spot', 'model')
    recipes = experiments(); require(type(data['fixtures']) is list and len(data['fixtures']) == 25, '25 complete fixtures')
    names = [x.get('name') if type(x) is dict else None for x in data['fixtures']]
    require(all(type(n) is str for n in names) and len(set(names)) == 25 and set(names) == recipes.keys(), 'fixture identity/uniqueness')
    unknown = {'unknown-sensor', 'unknown-route', 'zero-direction', 'sensor-boundary'}
    invalid = {'invalid-late-weight', 'invalid-late-shape'}
    budget = {'evaluation-budget', 'total-sqrt-budget', 'primitive-budget', 'sample-budget', 'step-budget'}
    record_states = {name: [1]*4 for name in ['identity', 'scaled-weights', 'tilted-sensor', 'plates', 'spectral-interval', 'lens-small', 'lens-marginal', 'finite-source']}
    record_states.update({'route-miss': [2], 'mixed-route-miss': [1, 2], 'sensor-miss': [4], 'mixed-sensor-miss': [1, 4],
                          'unknown-sensor': [1, 6], 'unknown-route': [1, 5], 'unavailable-transmission': [3], 'evaluation-budget': [1, 0, 0, 0],
                          'total-sqrt-budget': [7, 0, 0, 0], 'primitive-budget': [7], 'zero-direction': [6], 'sensor-boundary': [6],
                          'invalid-late-weight': [], 'invalid-late-shape': [], 'empty': [], 'sample-budget': [], 'step-budget': []})
    references = 0
    for f in data['fixtures']:
        keys(f, {'name', 'input', 'result'}); name = f['name']; identity(f['input'], recipes[name], name)
        r = f['result']; keys(r, {'status', 'evaluations', 'accepted', 'routeMisses', 'branchUnavailable', 'sensorMisses', 'unknown', 'geometryQueries', 'interfaceQueries', 'sqrtRefinements', 'refinementLimited', 'finalStats', 'records'})
        expected = 1 if name in unknown else 2 if name in invalid else 3 if name in budget else 0
        require(integer(r['status'], 0, 4) == expected, 'independent classification ' + name)
        inp = f['input']; settings = inp['settings']; preflight = name in invalid or name in {'sample-budget', 'step-budget'}
        require(type(r['records']) is list and len(r['records']) == (0 if preflight else len(inp['samples'])), 'complete admitted records')
        require([rec.get('status') if type(rec) is dict else None for rec in r['records']] == record_states[name], 'independent per-sample classification')
        for k in ['evaluations', 'accepted', 'routeMisses', 'branchUnavailable', 'sensorMisses', 'unknown']:
            integer(r[k], 0, len(inp['samples']))
        require(r['evaluations'] <= settings['maxEvaluations'], 'evaluation budget')
        for k, hi in [('geometryQueries', 66560), ('interfaceQueries', 65536), ('sqrtRefinements', settings['maxSqrtRefinements'] + 263680)]:
            integer(r[k], 0, hi)
        require(type(r['refinementLimited']) is bool, 'result flag')
        counts = [0]*10; evaluations = gq = iq = sq = 0; limited = False
        for j, rec in enumerate(r['records']):
            keys(rec, {'ordinal', 'weight', 'status', 'route', 'sensor'}); require(integer(rec['ordinal'], 0, 1023) == j, 'record order')
            identity(rec['weight'], inp['samples'][j]['weight']); st = integer(rec['status'], 0, 9); counts[st] += 1
            if rec['route'] is not None:
                evaluations += 1; q = rec['route']; keys(q, {'status', 'completedSteps', 'failedStep', 'geometryQueries', 'interfaceQueries', 'sqrtRefinements', 'refinementLimited', 'completion'})
                rs = integer(q['status'], 0, 7)
                for k in ['completedSteps', 'failedStep', 'geometryQueries', 'interfaceQueries']:
                    integer(q[k], 0, len(inp['steps']))
                integer(q['sqrtRefinements'], 0, 262144); require(type(q['refinementLimited']) is bool, 'route flag')
                gq += q['geometryQueries']; iq += q['interfaceQueries']; sq += q['sqrtRefinements']; limited |= q['refinementLimited']
                if rs == 0:
                    completion_schema(q['completion']); require(q['completedSteps'] == len(inp['steps']) == q['failedStep'], 'route completion steps')
                    require(q['geometryQueries'] == len(inp['steps']) == q['interfaceQueries'], 'completed route query counts')
                    current = inp['initialIndex']
                    for route_step in inp['steps']:
                        if route_step['branch'] == 1:
                            current = route_step['nextIndex']
                    identity(q['completion']['index'], current, 'held final phase index')
                    if not inp['steps']:
                        identity(q['completion']['ray'], inp['samples'][j]['ray'], 'empty route identity ray')
                        identity(q['completion']['totals'], dict(distance=[-0., 0.], opticalPathLength=[-0., 0.], throughput=[1, 1]), 'empty route totals')
                    else:
                        require(q['completion']['ray']['minimumParameter'] == 0 and q['completion']['ray']['maximumParameter'] == 1e6, 'continued ray explicit domain')
                else:
                    require(q['completion'] is None, 'failed route leaks completion')
                    require(q['failedStep'] == q['completedSteps'] and q['geometryQueries'] == q['completedSteps'] + 1, 'failed attempted route step')
                    require(q['completedSteps'] <= q['interfaceQueries'] <= q['completedSteps'] + 1, 'failed interface count')
            if rec['sensor'] is not None:
                require(rec['route'] is not None and rec['route']['status'] == 0, 'sensor without completed route'); sensor_schema(rec['sensor']); gq += 1; sq += rec['sensor']['sqrtRefinements']; limited |= rec['sensor']['refinementLimited']
            if st == 0:
                require(rec['route'] is None and rec['sensor'] is None, 'unexamined sample has work')
            elif st == 1:
                require(rec['route'] is not None and rec['route']['status'] == 0 and rec['sensor'] is not None and rec['sensor']['status'] == 0, 'accepted sample lacks hit')
            elif st in {2, 3, 5}:
                require(rec['route'] is not None and rec['route']['status'] in ({1} if st == 2 else {4} if st == 3 else {2, 3}) and rec['sensor'] is None, 'route record classification')
            elif st in {4, 6}:
                require(rec['sensor'] is not None and rec['sensor']['status'] == (1 if st == 4 else 2), 'sensor record classification')
        require((r['evaluations'], r['geometryQueries'], r['interfaceQueries'], r['sqrtRefinements'], r['refinementLimited']) == (evaluations, gq, iq, sq, limited), 'actual diagnostic counters')
        require((r['accepted'], r['routeMisses'], r['branchUnavailable'], r['sensorMisses'], r['unknown']) == (counts[1], counts[2], counts[3], counts[4], sum(counts[k] for k in [0, 5, 6, 7, 8, 9])), 'classification totals')
        if expected == 0:
            require(r['unknown'] == 0 and r['finalStats'] is not None, 'complete statistics')
            references += stats_references(r, inp['samples'])
        else:
            require(r['finalStats'] is None, 'unknown/budget/invalid statistics fabricated')
        if name == 'total-sqrt-budget':
            require(r['sqrtRefinements'] > settings['maxSqrtRefinements'] and r['evaluations'] == 1 and r['records'][0]['status'] == 7, 'actual total work overshoot')
    known = {f['name']: f['result'] for f in data['fixtures']}
    for name, cx, cy, cz, variance in [('identity', F(1,10), F(1,10), F(1), F(49,50)), ('scaled-weights', F(1,10), F(1,10), F(1), F(49,50)), ('plates', F(1,10), F(1,10), F(5,4), F(49,50)), ('spectral-interval', F(1,10), F(1,10), F(5,4), F(49,50)), ('tilted-sensor', F(1,10), F(1,10), F(37,40), F(1829,1600)), ('finite-source', F(1,5), F(1,5), F(1), F(98,25))]:
        m = known[name]['finalStats']['moments']
        for k, v in enumerate([cx, cy, cz]):
            includes(m['centroid'][k], v)
        includes(m['meanSquaredRadius'], variance); references += 4
    for name in ['plates', 'spectral-interval']:
        for rec in known[name]['records']:
            totals = rec['route']['completion']['totals']; includes(totals['distance'], F(5,4)); references += 1
            ns = [F(3,2)] if name == 'plates' else [F.from_float(1.49), F.from_float(1.51)]
            for n in ns:
                includes(totals['opticalPathLength'], 1+n/4); includes(totals['throughput'], 16*n*n/(1+n)**4); references += 2
    require(type(data['launch']) is list and len(data['launch']) == 2, 'two source helper references')
    for j, launch in enumerate(data['launch']):
        keys(launch, {'kind', 'reference', 'point', 'ray'}); integer(launch['kind'], j, j); vector(launch['reference']); vector(launch['point']); ray_schema(launch['ray'])
        expected_ref = [2**19, 0, -1] if j == 0 else [.125, .25, 2]
        expected_point = [2**-40, 0, -.01] if j == 0 else [.3, -.2, -.01]
        identity(launch['reference'], expected_ref); identity(launch['point'], expected_point)
        require(launch['ray']['minimumParameter'] == 0 and launch['ray']['maximumParameter'] == 1e6, 'helper domain')
        for k in range(3):
            a, b = fraction(launch['reference'][k]), fraction(launch['point'][k]); includes(launch['ray']['origin'][k], a if j == 0 else b); includes(launch['ray']['direction'][k], b-a if j == 0 else a); references += 2
    require(type(data['paraxial']) is list and len(data['paraxial']) == 3, 'three pupil refinement levels')
    # The convenient decimal-ideal matrix gives 639/11800. Actual shape inputs
    # are exact binary64 .05/.005, so compute their own exact rational target.
    radius, thickness, index = F.from_float(.05), F.from_float(.005), F(3,2)
    aperture = F.from_float(.015)
    require(aperture**2 < radius*thickness-thickness**2/4, 'synthetic surfaces do not cross within aperture')
    power = (index-1)/radius; a = 1-thickness/index*power; c = -2*power+thickness/index*power**2
    paraxial_focus = thickness-a/c
    error_ranges = []
    for j, q in enumerate(data['paraxial']):
        keys(q, {'pupilRadius', 'focus', 'meanSquaredRadius'}); identity(q['pupilRadius'], .002/2**j); bounds(q['focus']); bounds(q['meanSquaredRadius'])
        lo, hi = map(fraction, q['focus']); require(thickness < lo <= hi < paraxial_focus, 'positive back focus with finite-pupil spherical aberration')
        error_ranges.append((paraxial_focus-hi, paraxial_focus-lo))
        require(0 < q['meanSquaredRadius'][0] <= q['meanSquaredRadius'][1] < 1e-8, 'finite-pupil spread reference')
    for a, b in zip(error_ranges, error_ranges[1:]):
        require(F(19,5) < a[0]/b[1] <= a[1]/b[0] < F(21,5), 'second-order paraxial focus convergence')
    require(known['lens-marginal']['finalStats']['moments']['meanSquaredRadius'][0] > known['lens-small']['finalStats']['moments']['meanSquaredRadius'][1], 'finite-pupil aberration is not erased')
    require(references == 166, 'independent reference coverage')
    return data, dict(status='PASS', fixtures=25, rationalInclusionChecks=references, paraxialRefinements=3, sourceHelperCases=2,
                      paraxialTargetForExactBinary64Profile=str(paraxial_focus))


HEADER = 'k,a,weight0,weight1,weight2,weight3,totalLo,totalHi,cxLo,cxHi,cyLo,cyHi,czLo,czHi,varLo,varHi,hxLo,hxHi,hyLo,hyHi,hzLo,hzHi'.split(',')


def decode(text):
    require(len(text) == 16 and all(c in '0123456789abcdef' for c in text), 'binary64 hex format')
    v = struct.unpack('>d', bytes.fromhex(text))[0]; require(math.isfinite(v), 'nonfinite binary64 oracle')
    return F.from_float(v)


def oracle(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.reader(stream, strict=True))
    require(len(rows) == 129 and rows[0] == HEADER, '128-row oracle and exact header required')
    for k, row in enumerate(rows[1:], 1):
        require(len(row) == len(HEADER) and row[0] == str(k), 'row length/unique identity')
        a = k/256; weights = [(k+j)%7+1 for j in range(4)]
        require(row[1:6] == [struct.pack('>d', float(v)).hex() for v in [a]+weights], 'binary64 corpus input identity')
        values = list(map(decode, row[1:])); a = values[0]; weights = values[1:5]; total = sum(weights)
        cx = a*(weights[1]-weights[0])/total; cy = a*(weights[3]-weights[2])/total
        expected = [total, cx, cy, F(1), a*a-cx*cx-cy*cy, -a, a, -a, a, F(1), F(1)]
        pairs = [values[j:j+2] for j in range(5, len(values), 2)]
        for pair in pairs:
            require(pair[0] <= pair[1], 'ordered oracle output')
        checks = [(pairs[0], expected[0]), (pairs[1], expected[1]), (pairs[2], expected[2]), (pairs[3], expected[3]), (pairs[4], expected[4]),
                  (pairs[5], expected[5]), (pairs[5], expected[6]), (pairs[6], expected[7]), (pairs[6], expected[8]), (pairs[7], expected[9]), (pairs[7], expected[10])]
        require(all(pair[0] <= exact <= pair[1] for pair, exact in checks), 'exact weighted moment/hull reference not enclosed')
    return rows, dict(status='PASS', oracleCases=128, independentRationalInclusions=1408)


def compare(a, b):
    numbers = 0
    def walk(x, y):
        nonlocal numbers
        require(type(x) is type(y), 'parity type')
        if type(x) is dict:
            require(x.keys() == y.keys(), 'parity keys')
            for k in x:
                walk(x[k], y[k])
        elif type(x) is list:
            require(len(x) == len(y), 'parity length')
            for xx, yy in zip(x, y):
                walk(xx, yy)
        elif type(x) is float:
            require(struct.pack('>d', x) == struct.pack('>d', y), 'binary64 bit parity'); numbers += 1
        else:
            require(x == y, 'exact parity')
    if type(a) is dict:
        a, b = dict(a), dict(b); a['fixtures'] = {f['name']: f for f in a['fixtures']}; b['fixtures'] = {f['name']: f for f in b['fixtures']}
    walk(a, b); return numbers


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('native'); parser.add_argument('wasm', nargs='?'); args = parser.parse_args()
    is_json = Path(args.native).read_text(encoding='utf-8-sig').lstrip().startswith('{'); checker = fixtures if is_json else oracle
    a, report = checker(args.native)
    if args.wasm:
        b, other = checker(args.wasm); report['wasm'] = other
        if is_json:
            report['bitEqualNumbers'] = compare(a, b)
        else:
            require(a == b, 'exact oracle packet parity'); report['identicalOraclePackets'] = 1
    report['limits'] = 'Finite geometric weighted samples and specified routes only; no radiometric image, continuous-pupil quadrature enclosure, diffraction PSF, automatic visibility or global optimal focus.'
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, TypeError, KeyError, IndexError, OSError, OverflowError, ZeroDivisionError, csv.Error) as error:
        raise SystemExit('FAIL optical spot verification: ' + str(error)) from error
