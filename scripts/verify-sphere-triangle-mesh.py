"""Independent finite-union oracle: exact rational closest points, no C++ code.

The primitive oracle independently enumerates feasible projection/segments.
This module verifies the union minimum, every exact winner, copied source bits,
all rows/work counters, and the documented interval reduction separately.
"""
from fractions import Fraction as F
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

spec = importlib.util.spec_from_file_location('primitive_reference', Path(__file__).with_name('verify-sphere-triangle.py'))
primitive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(primitive)
need = primitive.need
I = primitive.bounds


def integer(value, maximum, label):
    need(type(value) is int and 0 <= value <= maximum, label)
    return value


def bits(value):
    need(type(value) in (int, float) and math.isfinite(value), 'finite binary64')
    return struct.pack('>d', value)


def source_equal(a, b):
    """A rational zero comparison would miss loss of the original -0 source."""
    if type(a) in (int, float):
        need(bits(a) == bits(b), 'owned source numeric bits')
    elif type(a) is dict:
        need(type(b) is dict and set(a) == set(b), 'owned source object')
        for key in a:
            source_equal(a[key], b[key])
    elif type(a) is list:
        need(type(b) is list and len(a) == len(b), 'owned source array')
        for x, y in zip(a, b):
            source_equal(x, y)
    else:
        need(type(a) is type(b) and a == b, 'owned source scalar')


def profile_valid(settings):
    expected = {'maxCandidates', 'sqrtRefinements', 'maxTotalSqrtRefinements', 'maximumLocalWidth', 'maximumNormalWidth', 'minimumSineSquared'}
    need(type(settings) is dict and set(settings) == expected, 'complete primitive profile')
    checks = [('maxCandidates', 7), ('sqrtRefinements', 256), ('maxTotalSqrtRefinements', 1024)]
    integers = all(type(settings[k]) is int and 1 <= settings[k] <= n for k, n in checks)
    floats = all(type(settings[k]) in (int, float) and math.isfinite(settings[k]) and 0 < settings[k] <= n
                 for k, n in [('maximumLocalWidth', 1e6), ('maximumNormalWidth', 2), ('minimumSineSquared', 1)])
    return integers and floats


def preconditions(source):
    need(type(source) is dict and set(source) == {'sphere', 'triangles', 'settings'}, 'mesh source fields')
    sphere, triangles, settings = source['sphere'], source['triangles'], source['settings']
    need(type(sphere) is dict and set(sphere) == {'center', 'radius'}, 'sphere fields')
    center, radius = primitive.vector(sphere['center']), primitive.rational(sphere['radius'])
    need(type(settings) is dict and set(settings) == {'maxSurfaces', 'primitive'}, 'collection settings')
    valid_profile = profile_valid(settings['primitive'])
    maximum = settings['maxSurfaces']
    faults = []
    if type(maximum) is not int or not 1 <= maximum <= 64 or not valid_profile:
        faults.append((1, None))
    need(type(triangles) is list and len(triangles) <= 65, 'bounded fixture source array')
    if not 1 <= len(triangles) <= 64:
        faults.append((2, None))
    if type(maximum) is int and 1 <= maximum <= 64 and len(triangles) > maximum and len(triangles) <= 64:
        faults.append((3, None))
    if not (0 < radius <= F(1e150)) or any(abs(c) > F(1e150) for c in center):
        faults.append((6, None))
    seen = set()
    for index, triangle in enumerate(triangles):
        need(type(triangle) is dict and set(triangle) == {'id', 'vertices'}, 'triangle fields')
        identifier = triangle['id']
        need(type(identifier) is int, 'integer surface identity')
        vertices = triangle['vertices']
        need(type(vertices) is list and len(vertices) == 3, 'source triangle vertices')
        vectors = [primitive.vector(v) for v in vertices]
        if not 1 <= identifier <= 9007199254740991:
            faults.append((4, index))
        if identifier in seen:
            faults.append((5, index))
        seen.add(identifier)
        if any(abs(v) > F(1e150) for p in vectors for v in p):
            faults.append((6, index))
    return faults


def primitive_shape(result):
    need(type(result) is dict, 'primitive result')
    integer(result['status'], 7, 'primitive status')
    integer(result['reason'], 17, 'primitive reason')
    examined = integer(result['candidatesExamined'], 7, 'primitive examined')
    integer(result['sqrtRefinements'], 512, 'primitive sqrt work')
    need(type(result['sqrtRefinementLimited']) is bool, 'primitive sqrt flag')
    candidates = result['candidates']
    need(type(candidates) is list and len(candidates) <= examined <= len(candidates) + 1, 'actual primitive audit prefix')
    for key in ['squaredCross', 'sineSquared']:
        if result[key] is not None:
            lo, hi = I(result[key])
            need(lo >= 0 and (key != 'sineSquared' or hi <= 1), 'primitive nonnegative diagnostic')
    for index, candidate in enumerate(candidates):
        need(candidate['feature'] == index and type(candidate['feature']) is int, 'ordered candidate prefix')
        integer(candidate['disposition'], 2, 'candidate disposition')
        dimension = 0 if index == 0 else 1 if index <= 3 else 2
        need(type(candidate['kktCount']) is int and candidate['kktCount'] == dimension, 'KKT dimension')
        need(type(candidate['barycentric']) is list and len(candidate['barycentric']) == 3, 'candidate barycentric')
        for b in candidate['barycentric']:
            I(b)
        need(type(candidate['kkt']) is list and len(candidate['kkt']) == 2, 'two KKT slots')
        for k, pair in enumerate(candidate['kkt']):
            I(pair)
            if k >= dimension:
                need(bits(pair[0]) == bits(-0.0) and bits(pair[1]) == bits(0.0), 'unused KKT signed zeros')
    need((result['geometry'] is not None) == (result['status'] == 0), 'primitive completion geometry')


def verify(data):
    need(type(data) is dict and data.get('schema') == 1 and data.get('kind') == 'sphere-triangle-mesh-fixtures', 'mesh fixture schema')
    fixtures = data.get('fixtures')
    need(type(fixtures) is list and 16 <= len(fixtures) <= 256, 'finite mesh corpus')
    names, rows_for_reference = set(), []
    stats = dict(fixtures=len(fixtures), completedMeshes=0, failedMeshes=0, prevalidationRejected=0, primitiveRows=0,
                 exactMultipleWinnerMeshes=0, strictDominanceMeshes=0, maximumCapacityMeshes=0, aggregateReferenceComponents=0)
    for fixture in fixtures:
        name, source, result = fixture['name'], fixture['input'], fixture['result']
        need(type(name) is str and name not in names, 'unique mesh fixture name')
        names.add(name)
        faults = preconditions(source)
        need(type(result) is dict, 'mesh result')
        status, reason = integer(result['status'], 5, 'mesh status'), integer(result['reason'], 11, 'mesh reason')
        need(status not in (4, 5), 'finite corpus requires supported environment and no injected allocation failure')
        nearest, rows = result['nearest'], result['rows']
        need(type(rows) is list and len(rows) <= 64, 'bounded owned rows')
        work = {k: integer(result[k], limit, 'actual ' + k) for k, limit in [('queries', 64), ('candidatesExamined', 448), ('sqrtRefinements', 32768), ('sqrtLimitedRows', 64), ('failedRows', 64)]}
        for key in ['failedIndex', 'firstFailedRow']:
            need(result[key] is None or type(result[key]) is int and 0 <= result[key] < len(source['triangles']), 'failure index')
        if status in (1, 2):
            need((reason, result['failedIndex']) in faults, 'rejection is justified by the actual source')
            need((status == 2) == (reason == 3), 'surface budget classification')
            need(nearest is None and not rows and result['firstFailedRow'] is None and all(v == 0 for v in work.values()), 'prevalidation publishes no result rows')
            stats['prevalidationRejected'] += 1
            continue
        need(not faults and result['failedIndex'] is None, 'queried source passed all validation')
        need(len(rows) == len(source['triangles']) == work['queries'], 'all surfaces enumerated once')
        failures, squared, distances, gaps, exact = [], [], [], [], []
        sums = {'candidatesExamined': 0, 'sqrtRefinements': 0, 'sqrtLimitedRows': 0, 'failedRows': 0}
        for index, row in enumerate(rows):
            need(type(row) is dict and set(row) == {'triangle', 'query'}, 'owned row fields')
            source_equal(source['triangles'][index], row['triangle'])
            query = row['query']
            need(query is not None, 'ordinary row failure is still a real query')
            primitive_shape(query)
            rows_for_reference.append({'name': str(len(rows_for_reference)), 'input': {'sphere': source['sphere'], 'triangle': row['triangle'], 'settings': source['settings']['primitive']}, 'result': query})
            stats['primitiveRows'] += 1
            sums['candidatesExamined'] += query['candidatesExamined']
            sums['sqrtRefinements'] += query['sqrtRefinements']
            sums['sqrtLimitedRows'] += int(query['sqrtRefinementLimited'])
            if query['status']:
                failures.append(index)
                sums['failedRows'] += 1
            else:
                g = query['geometry']
                squared.append(g['squaredDistance'])
                distances.append(g['distance'])
                gaps.append(g['gap'])
                center = primitive.vector(source['sphere']['center'])
                vertices = tuple(primitive.vector(v) for v in row['triangle']['vertices'])
                exact.append((row['triangle']['id'], primitive.closest(center, vertices)[2]))
        need(all(work[k] == value for k, value in sums.items()), 'exact sum of primitive work')
        need(result['firstFailedRow'] == (failures[0] if failures else None), 'first failing row matches source order')
        if failures:
            need(status == 3 and reason == 7 and nearest is None, 'any failed row prevents aggregate nearest')
            stats['failedMeshes'] += 1
            continue
        need(status == 0 and reason == 0 and type(nearest) is dict, 'fully completed mesh')
        need(set(nearest) == {'squaredDistance', 'distance', 'gap', 'possibleSurfaceIds'}, 'aggregate contains no invented point or normal')
        for key, values in [('squaredDistance', squared), ('distance', distances), ('gap', gaps)]:
            I(nearest[key])
            for side in [0, 1]:
                need(bits(nearest[key][side]) == bits(min(pair[side] for pair in values)), 'endpoint-min reduction preserves exact bits')
        upper = min(pair[1] for pair in squared)
        expected = sorted(row['triangle']['id'] for row in rows if row['query']['geometry']['squaredDistance'][0] <= upper)
        ids = nearest['possibleSurfaceIds']
        need(type(ids) is list and all(type(v) is int for v in ids) and ids == expected and len(set(ids)) == len(ids), 'all interval-possible stable IDs retained in order')
        minimum = min(value for _, value in exact)
        true_ids = {identifier for identifier, value in exact if value == minimum}
        need(true_ids <= set(ids), 'every independently exact nearest surface retained')
        primitive.contains(nearest['squaredDistance'], minimum)
        primitive.square_root_bounds(*I(nearest['distance']), minimum)
        lo, hi = I(nearest['gap'])
        radius = primitive.rational(source['sphere']['radius'])
        primitive.square_root_bounds(lo + radius, hi + radius, minimum)
        stats['aggregateReferenceComponents'] += 3
        stats['completedMeshes'] += 1
        stats['exactMultipleWinnerMeshes'] += int(len(true_ids) > 1)
        stats['strictDominanceMeshes'] += int(len(expected) < len(rows))
        stats['maximumCapacityMeshes'] += int(len(rows) == 64)
    reference = primitive.verify({'schema': 1, 'kind': 'sphere-triangle-fixtures', 'fixtures': rows_for_reference})
    need(stats['completedMeshes'] >= 12 and stats['failedMeshes'] >= 1 and stats['prevalidationRejected'] >= 1, 'success/failure/source coverage')
    need(stats['exactMultipleWinnerMeshes'] >= 3 and stats['strictDominanceMeshes'] >= 3 and stats['maximumCapacityMeshes'] >= 1, 'tie/dominance/capacity coverage')
    return {'status': 'PASS', **stats, 'primitiveReference': reference}


def load(path):
    content = Path(path).read_bytes()
    need(len(content) <= 16 * 1024 * 1024, 'bounded fixture bytes')
    def floating(token):
        value = float(token)
        mantissa = token.lower().split('e')[0]
        need(math.isfinite(value) and not (value == 0 and any(c in '123456789' for c in mantissa)), 'finite non-underflowing JSON binary64')
        return value
    return json.loads(content, object_pairs_hook=primitive.unique_object, parse_float=floating,
                      parse_int=lambda token: -0.0 if token == '-0' else int(token),
                      parse_constant=lambda _: (_ for _ in ()).throw(AssertionError('nonfinite JSON')))


if __name__ == '__main__':
    print(json.dumps(verify(load(sys.argv[1])), indent=2))
