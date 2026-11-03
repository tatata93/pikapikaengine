"""Fail-closed finite rational references for optical selection fixtures/oracle.

Required Native JSON fixtures or CSV oracle; optional standalone WASM packet of
the same kind is independently validated and compared bit for bit. JSON numeric
tokens denote binary64 values, including integer-spelled negative zero.
"""
import argparse
import copy
import csv
from fractions import Fraction as F
import json
import math
from pathlib import Path
import struct

if not __debug__:
    raise SystemExit("Python -O is rejected")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def keys(obj, expected):
    require(type(obj) is dict and obj.keys() == set(expected), "missing/unknown schema keys")


def number(value):
    require(type(value) is float and math.isfinite(value), "finite binary64 number required")
    return value


def integer(value, lower, upper):
    require(number(value).is_integer() and lower <= value <= upper, "integer schema range")
    return int(value)


def vector(value, count=3):
    require(type(value) is list and len(value) == count, "vector schema")
    for v in value:
        number(v)


def bounds(value):
    vector(value, 2)
    require(value[0] <= value[1], "reversed interval")


def box(value):
    require(type(value) is list and len(value) == 3, "box schema")
    for v in value:
        bounds(v)


def identity(actual, expected, path=''):
    if type(expected) is dict:
        keys(actual, expected)
        for key in expected:
            identity(actual[key], expected[key], path + '/' + key)
    elif type(expected) is list:
        require(type(actual) is list and len(actual) == len(expected), "array identity")
        for j, (a, b) in enumerate(zip(actual, expected)):
            identity(a, b, path + '/' + str(j))
    elif type(expected) in (int, float):
        require(struct.pack('>d', number(actual)) == struct.pack('>d', float(expected)), "binary64 identity " + path + ': ' + str((actual, expected)))
    else:
        require(type(actual) is type(expected) and actual == expected, "typed identity")


def disk(identifier, z, aperture=10):
    return dict(id=identifier, kind=0, center=[0, 0, z], axis=[0, 0, -1], radius=0, aperture=aperture)


def sphere(identifier, center, radius):
    return dict(id=identifier, kind=1, center=center, axis=[0, 0, 1], radius=radius, aperture=0)


def point(v):
    return [[-0.0 if x == 0 else x, x] for x in v]


def experiments():
    base = dict(ray=dict(origin=point([0, 0, 0]), direction=point([0, 0, 1]), minimumParameter=0, maximumParameter=20),
                settings=dict(maximumParameterWidth=1e6, primitiveMaxSqrtRefinements=128, maxSurfaces=128, maxQueries=512, maxSqrtRefinements=16384, allowPrefixExclusion=True),
                surfaces=[disk(20, 1), disk(10, 3)])
    result = {}
    def add(name):
        c = copy.deepcopy(base)
        result[name] = c
        return c
    add('two-planes')
    add('all-miss')['surfaces'] = [disk(1, -1), disk(2, -3)]
    add('empty')['surfaces'] = []
    add('sphere-front')['surfaces'] = [sphere(1, [0, 0, 3], 1), disk(2, 4)]
    c = add('cap-second'); c['ray']['origin'] = point([0, 0, 5]); c['ray']['direction'] = point([0, 0, -1]); c['surfaces'] = [dict(id=1, kind=2, center=[0, 0, 0], axis=[0, 0, 1], radius=2, aperture=1), disk(2, -1)]
    add('self-zero')['surfaces'] = [disk(1, 0), disk(2, 1)]
    c = add('sphere-exit'); c['ray']['origin'] = point([0, 0, 1]); c['ray']['direction'] = point([0, 0, -1]); c['ray']['minimumParameter'] = 1e-6; c['surfaces'] = [sphere(1, [0, 0, 0], 1)]
    add('tiny-neighbor')['surfaces'] = [disk(1, 2**-30), disk(2, 1)]
    c = add('explicit-cutoff'); c['ray']['minimumParameter'] = 2**-29; c['surfaces'] = [disk(1, 2**-30), disk(2, 1)]
    c = add('order-swap'); c['ray']['origin'][0] = [-.25, .25]; c['surfaces'] = [disk(1, 1), disk(2, 1)]; c['surfaces'][0]['axis'] = [1, 0, 1]; c['surfaces'][1]['axis'] = [-1, 0, 1]
    c = add('correlated-order'); c['ray']['direction'][2] = [1, 2]; c['surfaces'] = [disk(1, 2), disk(2, 3)]
    c = add('aperture-mixed'); c['ray']['origin'][0] = [.9, 1.1]; c['surfaces'] = [disk(1, 1, 1), disk(2, 2)]
    c = add('aperture-outside'); c['ray']['origin'][0] = [1, 1]; c['surfaces'] = [disk(1, 1, .5), disk(2, 2)]
    add('coincident')['surfaces'] = [disk(1, 1), disk(2, 1)]
    add('tangent')['surfaces'] = [sphere(1, [1, 0, 1], 1), disk(2, 2)]
    for name in ['rear-aperture-uncertain', 'prefix-disabled', 'prefix-budget']:
        c = add(name); c['ray']['origin'][0] = [.9, 1.1]; c['surfaces'] = [disk(1, 1), disk(2, 4, 1)]
    result['prefix-disabled']['settings']['allowPrefixExclusion'] = False
    result['prefix-budget']['settings']['maxQueries'] = 2
    add('rear-tangent-uncertain')['surfaces'] = [disk(1, 1), sphere(2, [1, 0, 5], 1)]
    add('query-budget')['settings']['maxQueries'] = 1
    add('surface-budget')['settings']['maxSurfaces'] = 1
    for name in ['total-sqrt-budget', 'primitive-refinement-budget']:
        c = add(name); c['ray']['direction'][0] = [.125, .125]; c['surfaces'] = [sphere(1, [0, 0, 3], 1)]
    result['total-sqrt-budget']['settings']['maxSqrtRefinements'] = 1
    result['primitive-refinement-budget']['settings'].update(primitiveMaxSqrtRefinements=1, maximumParameterWidth=.01)
    add('parameter-width')['settings']['maximumParameterWidth'] = 1e-20
    add('same-id')['surfaces'] = [disk(1, 1), disk(1, 3)]
    add('zero-id')['surfaces'][1]['id'] = 0
    add('invalid-later-shape')['surfaces'].append(sphere(30, [0, 0, 0], -1))
    add('invalid-settings')['settings']['maxQueries'] = 0
    c = add('empty-invalid-ray'); c['surfaces'] = []; c['ray']['minimumParameter'] = -1
    c = add('empty-zero-direction'); c['surfaces'] = []; c['ray']['direction'] = point([0, 0, 0])
    add('parallel-miss')['surfaces'] = [dict(id=1, kind=0, center=[1, 0, 0], axis=[1, 0, 0], radius=0, aperture=1)]
    c = add('upper-boundary'); c['ray']['maximumParameter'] = 1; c['surfaces'] = [disk(1, 1)]
    c = add('back-face'); c['surfaces'] = [disk(1, 1, 1)]; c['surfaces'][0]['axis'] = [0, 0, 1]
    return result


HITS = {'two-planes': (20, F(1)), 'sphere-front': (1, F(2)), 'cap-second': (1, F(5)), 'self-zero': (1, F(0)), 'sphere-exit': (1, F(2)), 'tiny-neighbor': (1, F(1, 2**30)), 'explicit-cutoff': (2, F(1)), 'aperture-outside': (2, F(2)), 'rear-aperture-uncertain': (1, F(1)), 'back-face': (1, F(1))}
MISSES = {'all-miss', 'empty', 'parallel-miss'}
INVALID = {'same-id', 'zero-id', 'invalid-later-shape', 'invalid-settings', 'empty-invalid-ray'}
BUDGET = {'query-budget', 'prefix-budget', 'surface-budget', 'total-sqrt-budget', 'primitive-refinement-budget'}


def contains(interval, exact):
    require(F.from_float(interval[0]) <= exact <= F.from_float(interval[1]), "independent rational value not enclosed")


def hit_schema(hit):
    keys(hit, {'parameter', 'distance', 'position', 'geometricNormal', 'incidentNormal', 'frontFace'})
    bounds(hit['parameter']); bounds(hit['distance'])
    require(hit['parameter'][0] >= 0 and hit['distance'][0] >= 0, "negative accepted ray parameter/distance")
    for key in ['position', 'geometricNormal', 'incidentNormal']:
        box(hit[key])
    require(type(hit['frontFace']) is bool, "front-face flag")


def geometry_schema(g):
    keys(g, {'status', 'reason', 'rootCount', 'consideredCount', 'sqrtRefinements', 'refinementLimited', 'discriminant', 'nearest', 'candidates'})
    st = integer(g['status'], 0, 2); integer(g['reason'], 0, 14)
    integer(g['consideredCount'], 0, integer(g['rootCount'], 0, 2))
    integer(g['sqrtRefinements'], 0, 1536)
    require(type(g['refinementLimited']) is bool, "geometry budget flag")
    if g['discriminant'] is not None:
        bounds(g['discriminant'])
    require(type(g['candidates']) is list and len(g['candidates']) == 2, "two candidate slots")
    for c in g['candidates']:
        keys(c, {'parameter', 'state', 'reason'}); bounds(c['parameter']); integer(c['state'], 0, 5); integer(c['reason'], 0, 14)
    if st == 0:
        hit_schema(g['nearest'])
        require(g['reason'] == 0 and any(c['state'] == 1 and c['parameter'] == g['nearest']['parameter'] for c in g['candidates']), "accepted primitive root missing")
    else:
        require(g['nearest'] is None, "nonhit primitive leaks nearest")


def unique_keys(pairs):
    d = {}
    for k, v in pairs:
        require(k not in d, "duplicate JSON key")
        d[k] = v
    return d


def fixtures(path):
    def bad_constant(value):
        raise ValueError('nonstandard JSON number: ' + value)
    packet = json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_int=float, parse_float=float, parse_constant=bad_constant, object_pairs_hook=unique_keys)
    keys(packet, {'version', 'model', 'fixtures'}); integer(packet['version'], 1, 1)
    require(packet['model'] == 'uniform static optical surface selection', "model")
    recipes = experiments()
    require(type(packet['fixtures']) is list and len(packet['fixtures']) == 33, "33 complete fixtures required")
    names = [f.get('name') if type(f) is dict else None for f in packet['fixtures']]
    require(all(type(n) is str for n in names) and len(set(names)) == 33 and set(names) == recipes.keys(), "fixture identity/uniqueness")
    inclusions = 0
    for f in packet['fixtures']:
        keys(f, {'name', 'input', 'result'}); name = f['name']; identity(f['input'], recipes[name], name)
        r = f['result']; keys(r, {'status', 'queries', 'prefixQueries', 'sqrtRefinements', 'refinementLimited', 'nearest', 'surfaces'})
        expected = 0 if name in HITS else 1 if name in MISSES else 3 if name in INVALID else 4 if name in BUDGET else 2
        require(integer(r['status'], 0, 5) == expected, "independent classification " + name)
        settings = f['input']['settings']
        integer(r['queries'], 0, settings['maxQueries']); integer(r['prefixQueries'], 0, r['queries']); integer(r['sqrtRefinements'], 0, max(1, settings['maxSqrtRefinements']) + 1536)
        require(type(r['refinementLimited']) is bool and type(r['surfaces']) is list, "result schema")
        source_ids = sorted(x['id'] for x in f['input']['surfaces'])
        if name in INVALID or name in {'surface-budget', 'empty-zero-direction'}:
            require(not r['surfaces'], "preflight diagnostics must be empty")
        else:
            require([x['id'] for x in r['surfaces']] == source_ids, "complete canonical diagnostic IDs")
        q = pq = sqrt = 0; limited = False
        for ordinal, d in enumerate(r['surfaces']):
            keys(d, {'id', 'ordinal', 'excludedByPrefix', 'geometry', 'prefix'}); integer(d['id'], 1, 2**53 - 1)
            require(integer(d['ordinal'], 0, 1023) == ordinal and type(d['excludedByPrefix']) is bool, "diagnostic order/flag")
            for key in ['geometry', 'prefix']:
                if d[key] is not None:
                    geometry_schema(d[key]); q += 1; pq += key == 'prefix'; sqrt += d[key]['sqrtRefinements']; limited |= d[key]['refinementLimited']
            require(d['excludedByPrefix'] == (d['prefix'] is not None and d['prefix']['status'] == 1), "prefix exclusion needs certified miss")
            require(d['prefix'] is None or d['geometry'] is not None, "prefix without original")
        require((r['queries'], r['prefixQueries'], r['sqrtRefinements'], r['refinementLimited']) == (q, pq, sqrt, limited), "work counters do not match actual diagnostics")
        if expected == 0:
            keys(r['nearest'], {'id', 'hit'}); hit_schema(r['nearest']['hit'])
            identifier, exact = HITS[name]; require(integer(r['nearest']['id'], 1, 2**53 - 1) == identifier, "independent nearest ID")
            h = r['nearest']['hit']; contains(h['parameter'], exact); contains(h['distance'], exact); inclusions += 2
            z = {'two-planes': F(1), 'sphere-front': F(2), 'cap-second': F(0), 'self-zero': F(0), 'sphere-exit': F(-1),
                 'tiny-neighbor': F(1, 2**30), 'explicit-cutoff': F(1), 'aperture-outside': F(2), 'rear-aperture-uncertain': F(1), 'back-face': F(1)}[name]
            x_values = [F.from_float(.9), F.from_float(1.1)] if name == 'rear-aperture-uncertain' else [F(1)] if name == 'aperture-outside' else [F(0)]
            for x in x_values:
                contains(h['position'][0], x); inclusions += 1
            contains(h['position'][1], F(0)); contains(h['position'][2], z); inclusions += 2
            front = name not in {'cap-second', 'sphere-exit', 'back-face'}
            require(h['frontFace'] is front, "independent incident side")
            gn = 1 if name == 'back-face' else -1
            for key, normal in [('geometricNormal', gn), ('incidentNormal', gn if front else -gn)]:
                for axis, coordinate in enumerate([0, 0, normal]):
                    contains(h[key][axis], F(coordinate)); inclusions += 1
            winner = next(d for d in r['surfaces'] if d['id'] == identifier)
            identity(h, winner['geometry']['nearest'])
            for d in r['surfaces']:
                require(d['geometry'] is not None, "hit leaves original surface unchecked")
                if d is winner:
                    continue
                g = d['geometry']
                require(g['status'] == 1 or (g['status'] == 0 and h['parameter'][1] < g['nearest']['parameter'][0]) or d['excludedByPrefix'], "missing strict-before/prefix certificate")
        else:
            require(r['nearest'] is None, "nonhit leaks selection")
        if expected == 1:
            require(all(d['geometry'] is not None and d['geometry']['status'] == 1 for d in r['surfaces']), "global miss without all primitive misses")
        if name == 'cap-second':
            require(r['surfaces'][0]['geometry']['candidates'][0]['state'] == 4 and r['surfaces'][0]['geometry']['candidates'][1]['state'] == 1, "ordered second valid cap root")
        if name == 'rear-aperture-uncertain':
            require(r['surfaces'][1]['geometry']['status'] == 2 and r['surfaces'][1]['excludedByPrefix'] and r['prefixQueries'] == 1, "rear ambiguity prefix proof")
        if name == 'total-sqrt-budget':
            require(r['sqrtRefinements'] > settings['maxSqrtRefinements'], "actual total work budget failure")
    require(inclusions == 111, "independent reference coverage")
    return packet, {'status': 'PASS', 'fixtures': 33, 'independentRationalInclusions': inclusions, 'independentClassifications': 33}


HEADER = 'kind,k,originLo,originHi,directionLo,directionHi,target,selectedID,status,tLo,tHi,distanceLo,distanceHi,zLo,zHi'.split(',')


def hex_value(text):
    require(len(text) == 16 and all(c in '0123456789abcdef' for c in text), "binary64 hex format")
    value = struct.unpack('>d', bytes.fromhex(text))[0]
    require(math.isfinite(value), "finite binary64 oracle")
    return F.from_float(value)


def oracle(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.reader(stream, strict=True))
    require(len(rows) == 193 and rows[0] == HEADER, "192-row oracle/header required")
    for j, row in enumerate(rows[1:]):
        require(len(row) == len(HEADER), "oracle row length")
        kind, k = 'PSC'[j // 64], j % 64 + 1
        require(row[:2] == [kind, str(k)] and row[7:9] == ['1', '0'], "oracle identity/selection/status")
        cap = kind == 'C'; base = (k + 40) / 8
        lo = base if cap else -base; hi = lo + 1 / 65536; mag = (k % 7 + 4) / 8
        dl = -mag - 1 / 65536 if cap else mag; dh = dl + 1 / 65536
        target = (k % 3 + 1) / 4 if kind == 'P' else -(k % 3 + 1) / 4 if kind == 'S' else 0.
        expected = [struct.pack('>d', x).hex() for x in [lo, hi, dl, dh, target]]
        require(row[2:7] == expected, "binary64 corpus input identity")
        ol, oh, vl, vh, z = map(hex_value, row[2:7])
        tl, th, sl, sh, zl, zh = map(hex_value, row[9:])
        require(0 <= tl <= th and 0 <= sl <= sh and zl <= zh, "oracle output bounds")
        exact_tlo, exact_thi = ((ol - z) / -vl, (oh - z) / -vh) if cap else ((z - oh) / vh, (z - ol) / vl)
        distances = sorted([abs(z - ol), abs(z - oh)])
        require(tl <= exact_tlo <= exact_thi <= th and sl <= distances[0] <= distances[1] <= sh and zl <= z <= zh, "exact rational family extrema not enclosed")
        # Competitor disk is z=-4 for C, z=+4 otherwise. Along this SAME ray
        # every accepted winning coordinate is strictly before that plane.
        require((z > -4 and vh < 0) if cap else (z < 4 and vl > 0), "independent competitor ordering")
    return rows, {'status': 'PASS', 'oracleFamilies': 192, 'exactRationalExtremaInclusions': 1152, 'independentNearestIDs': 192}


def bit_compare(a, b):
    count = 0
    def walk(x, y):
        nonlocal count
        require(type(x) is type(y), "parity type")
        if type(x) is dict:
            require(x.keys() == y.keys(), "parity keys")
            for key in x:
                walk(x[key], y[key])
        elif type(x) is list:
            require(len(x) == len(y), "parity length")
            for xx, yy in zip(x, y):
                walk(xx, yy)
        elif type(x) is float:
            require(struct.pack('>d', x) == struct.pack('>d', y), "binary64 output parity")
            count += 1
        else:
            require(x == y, "exact value parity")
    if type(a) is dict:
        a, b = dict(a), dict(b)
        a['fixtures'] = {f['name']: f for f in a['fixtures']}; b['fixtures'] = {f['name']: f for f in b['fixtures']}
    walk(a, b)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native'); parser.add_argument('wasm', nargs='?')
    args = parser.parse_args()
    is_json = Path(args.native).read_text(encoding='utf-8-sig').lstrip().startswith('{')
    checker = fixtures if is_json else oracle
    native, report = checker(args.native)
    if args.wasm:
        wasm, other = checker(args.wasm); report['wasm'] = other; report['bitEqualNumbers' if is_json else 'identicalOraclePackets'] = bit_compare(native, wasm) if is_json else (1 if native == wasm else 0)
        require(is_json or native == wasm, "oracle binary64 packet parity")
    report['limits'] = 'Finite independent reference families; no automatic optical continuation, medium topology, whole-world transport or arbitrary geometry completeness proof.'
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, TypeError, KeyError, IndexError, OSError, OverflowError, ZeroDivisionError, csv.Error) as error:
        raise SystemExit('FAIL optical selection verification: ' + str(error)) from error
