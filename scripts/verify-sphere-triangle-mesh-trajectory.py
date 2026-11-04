"""Independent exact-rational whole-segment/triangle distance reference.

The oracle uses a feasible plane projection and three clamped closed segments,
not the production KKT mask, Lipschitz subdivision, or C++ query implementation.
Each feature is affine on a rational parameter range; its squared distance is
quadratic. Endpoints and an interior stationary point give the exact minimum.
No libm sqrt, dense time sampling, or midpoint pointification is used as proof.
"""
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

_spec = importlib.util.spec_from_file_location(
    'trajectory_mesh_reference', Path(__file__).with_name('verify-sphere-triangle-mesh.py'))
mesh_reference = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mesh_reference)
primitive = mesh_reference.primitive
need = primitive.need


def fraction(value):
    if isinstance(value, F):
        return value
    need(type(value) in (int, float), 'finite binary64 scalar')
    try:
        rounded = float(value)
    except (OverflowError, ValueError):
        raise AssertionError('finite binary64 scalar')
    need(math.isfinite(rounded), 'finite binary64 scalar')
    if type(value) is int:
        need(F(rounded) == value, 'integer numeric token is exactly binary64')
    return F(rounded)


def vector(value):
    need(type(value) in (list, tuple) and len(value) == 3, 'three coordinates')
    return tuple(fraction(v) for v in value)


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def scale(a, k):
    return tuple(x * k for x in a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def clip_nonnegative(interval, intercept, slope):
    """Intersect closed [lo,hi] with intercept+slope*s >= 0 exactly."""
    if interval is None:
        return None
    lo, hi = interval
    if slope > 0:
        lo = max(lo, -intercept / slope)
    elif slope < 0:
        hi = min(hi, -intercept / slope)
    elif intercept < 0:
        return None
    return (lo, hi) if lo <= hi else None


def squared_polynomial(origin, velocity):
    """Ascending coefficients c0+c1*s+c2*s^2, all exact rationals."""
    return dot(origin, origin), 2 * dot(origin, velocity), dot(velocity, velocity)


def quadratic_minimum(coefficients, lo, hi):
    need(lo <= hi, 'nonempty quadratic domain')
    c0, c1, c2 = coefficients
    need(c2 >= 0, 'squared affine norm is convex')
    candidates = [lo, hi]
    if c2:
        stationary = -c1 / (2 * c2)
        if lo <= stationary <= hi:
            candidates.append(stationary)
    return min(((c2 * s + c1) * s + c0, s) for s in candidates)


def triangle_pieces(start, end, vertices):
    """Compile exact feature ranges, independent of any Native feature flags.

    Degenerate triangles still have the union of their closed edges as their
    exact convex hull, useful for mathematical self-tests. Production may reject
    them; that rejection does not become a successful geometry in this checker.
    """
    start, end = vector(start), vector(end)
    need(type(vertices) in (list, tuple) and len(vertices) == 3, 'triangle vertices')
    a, b, c = tuple(vector(v) for v in vertices)
    velocity = sub(end, start)
    ab, ac, relative = sub(b, a), sub(c, a), sub(start, a)
    aa, bb, cc = dot(ab, ab), dot(ab, ac), dot(ac, ac)
    determinant = aa * cc - bb * bb
    pieces = []

    def append(feature, domain, q0, qv):
        if domain is not None:
            pieces.append({'feature': feature, 'domain': domain,
                           'coefficients': squared_polynomial(sub(start, q0), sub(velocity, qv))})

    if determinant > 0:
        u0 = (cc * dot(ab, relative) - bb * dot(ac, relative)) / determinant
        uv = (cc * dot(ab, velocity) - bb * dot(ac, velocity)) / determinant
        v0 = (aa * dot(ac, relative) - bb * dot(ab, relative)) / determinant
        vv = (aa * dot(ac, velocity) - bb * dot(ab, velocity)) / determinant
        domain = (F(0), F(1))
        for intercept, slope in [(u0, uv), (v0, vv), (1 - u0 - v0, -uv - vv)]:
            domain = clip_nonnegative(domain, intercept, slope)
        append('face', domain, add(a, add(scale(ab, u0), scale(ac, v0))),
               add(scale(ab, uv), scale(ac, vv)))

    points = (a, b, c)
    zero = (F(0), F(0), F(0))
    for i, j in ((0, 1), (1, 2), (2, 0)):
        first, last = points[i], points[j]
        edge = sub(last, first)
        length_squared = dot(edge, edge)
        if not length_squared:
            append('collapsed_edge', (F(0), F(1)), first, zero)
            continue
        t0 = dot(sub(start, first), edge) / length_squared
        tv = dot(velocity, edge) / length_squared
        left = clip_nonnegative((F(0), F(1)), -t0, -tv)
        middle = clip_nonnegative((F(0), F(1)), t0, tv)
        middle = clip_nonnegative(middle, 1 - t0, -tv)
        right = clip_nonnegative((F(0), F(1)), t0 - 1, tv)
        append('vertex_' + str(i), left, first, zero)
        append('edge_' + str(i) + str(j), middle, add(first, scale(edge, t0)), scale(edge, tv))
        append('vertex_' + str(j), right, last, zero)
    need(pieces, 'at least one exact feature covers the path')
    return pieces


def piecewise_minimum(pieces, lo=F(0), hi=F(1)):
    lo, hi = fraction(lo), fraction(hi)
    need(0 <= lo <= hi <= 1, 'closed path parameter domain')
    candidates = []
    for piece in pieces:
        a, b = max(lo, piece['domain'][0]), min(hi, piece['domain'][1])
        if a <= b:
            value, parameter = quadratic_minimum(piece['coefficients'], a, b)
            candidates.append((value, parameter))
    need(candidates, 'exact feature coverage of requested domain')
    return min(candidates)


def path_triangle_minimum(start, end, vertices, lo=F(0), hi=F(1)):
    return piecewise_minimum(triangle_pieces(start, end, vertices), lo, hi)


def compile_mesh_path(start, end, triangles):
    need(type(triangles) is list and triangles, 'nonempty exact reference mesh')
    return [(t['id'], triangle_pieces(start, end, t['vertices'])) for t in triangles]


def mesh_path_minimum(compiled, lo=F(0), hi=F(1)):
    values = [(identifier, *piecewise_minimum(pieces, lo, hi)) for identifier, pieces in compiled]
    minimum = min(value for _, value, _ in values)
    return minimum, {identifier for identifier, value, _ in values if value == minimum}


def bits(value):
    fraction(value)
    return struct.pack('>d', value)


def source_equal(a, b):
    """Source equality includes binary64 -0 and complete object/array shape."""
    if type(a) in (int, float):
        need(type(b) in (int, float) and bits(a) == bits(b), 'owned source numeric bits, not boolean aliases')
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


def loads(content):
    if type(content) is bytes:
        need(len(content) <= 64 * 1024 * 1024, 'bounded fixture bytes')
        content = content.decode('utf-8', errors='strict')
    need(type(content) is str and len(content.encode('utf-8', errors='strict')) <= 64 * 1024 * 1024,
         'bounded UTF8 fixture text')

    def floating(token):
        value = float(token)
        mantissa = token.lower().split('e')[0]
        need(math.isfinite(value) and not (value == 0 and any(c in '123456789' for c in mantissa)),
             'finite non-underflowing JSON binary64')
        return value

    value = json.loads(content, object_pairs_hook=primitive.unique_object, parse_float=floating,
                       parse_int=lambda token: -0.0 if token == '-0' else int(token),
                       parse_constant=lambda _: (_ for _ in ()).throw(AssertionError('nonfinite JSON')))
    count = 0

    def validate(item, depth=0):
        nonlocal count
        count += 1
        need(count <= 2000000 and depth <= 48, 'bounded JSON nodes/depth')
        if isinstance(item, str):
            item.encode('utf-8', errors='strict')
        elif type(item) is dict:
            for key, child in item.items():
                key.encode('utf-8', errors='strict')
                validate(child, depth + 1)
        elif type(item) is list:
            for child in item:
                validate(child, depth + 1)
    validate(value)
    return value


def load(path):
    return loads(Path(path).read_bytes())


WORK_KEYS = {'meshQueries', 'primitiveQueries', 'candidatesExamined', 'primitiveSqrtRefinements',
             'enclosureSqrtRefinements', 'sqrtRefinements', 'sqrtRefinementsUpper',
             'meshSqrtLimitedRows', 'enclosureSqrtCalls', 'enclosureSqrtLimitedCalls', 'workExact'}
AUDIT_KEYS = {'cell', 'midpoint', 'outcome', 'pathBounds', 'pointBounds', 'anchor', 'meshQueried',
              'meshStatus', 'meshReason', 'distance', 'displacementSquaredBound', 'errorSquaredBound',
              'displacementRoot', 'errorRoot', 'clearanceCertificate', 'penetrationCertificate', 'work'}
RESULT_KEYS = {'status', 'reason', 'failedIndex', 'snapshot', 'certifiedLeaves', 'safePrefix', 'witness',
               'current', 'frontier', 'audits', 'lastMesh', 'lastMeshAuditIndex', 'work', 'partitionLeaves', 'maximumDepth'}
SETTINGS_KEYS = {'mesh', 'maxEvaluations', 'maxLeaves', 'maxDepth', 'enclosureSqrtRefinements', 'maxTotalSqrtRefinements'}
STATUSES = {'separated', 'penetration_witness', 'not_certified', 'invalid_input', 'unsupported_environment', 'numerical_failure'}
REASONS = {'none', 'settings', 'surface_count', 'surface_id', 'duplicate_id', 'input_domain', 'surface_budget',
           'mesh_query_failed', 'evaluation_budget', 'leaf_budget', 'depth_budget', 'sqrt_budget',
           'parameter_resolution', 'nonfinite_intermediate', 'allocation_failure', 'environment', 'coverage_inconsistent'}
# Final finite corpus: all whole inputs are pinned, excluding result/labels and
# fixture traversal order. Triangle/source array order and numeric bits remain.
EXPECTED_FIXTURE_COUNT = 62
EXPECTED_INPUT_FINGERPRINT = '7188d0549482a6603328649ee5a82293806b18993d9703ba484ebbca8d93556b'


def fields(value, expected, label):
    need(type(value) is dict and set(value) == expected, label + ' exact fields')


def uint(value, maximum, label):
    need(type(value) is int and 0 <= value <= maximum, label)
    return value


def interval(value):
    need(type(value) is list and len(value) == 2, 'interval pair')
    lo, hi = map(fraction, value)
    need(lo <= hi, 'ordered interval')
    return lo, hi


def bounds3(value):
    need(type(value) is list and len(value) == 3, 'Bounds3 array')
    return tuple(interval(v) for v in value)


def contains(value, exact):
    lo, hi = interval(value)
    need(lo <= exact <= hi, 'exact rational reference outside interval')


def contains3(value, exact):
    for pair, q in zip(bounds3(value), exact):
        need(pair[0] <= q <= pair[1], 'exact path coordinate outside bounds')


def cell(value, maximum_depth):
    fields(value, {'parameter', 'depth'}, 'cell')
    depth = uint(value['depth'], maximum_depth, 'dyadic depth')
    lo, hi = interval(value['parameter'])
    need(0 <= lo < hi <= 1 and hi - lo == F(1, 2 ** depth) and (lo * 2 ** depth).denominator == 1,
         'complete canonical dyadic cell')
    need(all(bits(v) == bits(float(q)) for v, q in zip(value['parameter'], (lo, hi))), 'canonical dyadic bits')
    return lo, hi, depth


def work(value):
    fields(value, WORK_KEYS, 'work')
    maxima = {'meshQueries': 255, 'primitiveQueries': 16320, 'candidatesExamined': 114240,
              'primitiveSqrtRefinements': 8355840, 'enclosureSqrtRefinements': 261120,
              'sqrtRefinements': 8616960, 'sqrtRefinementsUpper': 8616960,
              'meshSqrtLimitedRows': 16320, 'enclosureSqrtCalls': 510, 'enclosureSqrtLimitedCalls': 510}
    for key, maximum in maxima.items():
        uint(value[key], maximum, 'bounded ' + key)
    need(type(value['workExact']) is bool, 'work certainty flag')
    need(value['sqrtRefinements'] == value['primitiveSqrtRefinements'] + value['enclosureSqrtRefinements'], 'returned sqrt sum')
    need(value['sqrtRefinementsUpper'] >= value['sqrtRefinements'], 'conservative work upper')
    if value['workExact']:
        need(value['sqrtRefinementsUpper'] == value['sqrtRefinements'], 'exact work has exact upper')
    need(value['enclosureSqrtLimitedCalls'] <= value['enclosureSqrtCalls'], 'limited enclosure calls')
    need(value['meshSqrtLimitedRows'] <= value['primitiveQueries'], 'limited primitive rows')
    need(value['candidatesExamined'] <= 7 * value['primitiveQueries'], 'candidate work upper')
    need(value['primitiveSqrtRefinements'] <= 512 * value['primitiveQueries'], 'primitive sqrt work upper')
    need(value['enclosureSqrtRefinements'] <= 512 * value['enclosureSqrtCalls'], 'enclosure sqrt work upper')
    return value


def input_faults(source):
    fields(source, {'start', 'end', 'radius', 'triangles', 'settings'}, 'trajectory source')
    start, end, radius = vector(source['start']), vector(source['end']), fraction(source['radius'])
    need(type(source['start']) is list and type(source['end']) is list, 'source coordinate arrays')
    s = source['settings']
    fields(s, SETTINGS_KEYS, 'trajectory settings')
    fields(s['mesh'], {'maxSurfaces', 'primitive'}, 'mesh settings')
    profile = mesh_reference.profile_valid(s['mesh']['primitive'])
    ranges = [('maxEvaluations', 1, 1024), ('maxLeaves', 1, 128), ('maxDepth', 0, 32),
              ('enclosureSqrtRefinements', 1, 256), ('maxTotalSqrtRefinements', 1, 16777216)]
    valid_settings = profile and type(s['mesh']['maxSurfaces']) is int and 1 <= s['mesh']['maxSurfaces'] <= 64
    valid_settings = valid_settings and all(type(s[k]) is int and lo <= s[k] <= hi for k, lo, hi in ranges)
    faults = set()
    if not valid_settings:
        faults.add(('settings', None))
    triangles = source['triangles']
    need(type(triangles) is list and len(triangles) <= 65, 'finite fixture source capacity')
    if not 1 <= len(triangles) <= 64:
        faults.add(('surface_count', None))
    if not 0 < radius <= 10 ** 12 or any(abs(v) > 10 ** 12 for v in (*start, *end)):
        faults.add(('input_domain', None))
    seen = set()
    for index, triangle in enumerate(triangles):
        fields(triangle, {'id', 'vertices'}, 'triangle')
        identifier = triangle['id']
        need(type(identifier) is int and type(triangle['vertices']) is list and len(triangle['vertices']) == 3,
             'triangle ID and three vertices')
        vertices = tuple(vector(v) for v in triangle['vertices'])
        if not 1 <= identifier <= 2 ** 53 - 1:
            faults.add(('surface_id', index))
        if identifier in seen:
            faults.add(('duplicate_id', index))
        seen.add(identifier)
        if any(abs(v) > 10 ** 12 for point in vertices for v in point):
            faults.add(('input_domain', index))
    return faults


def box_squared_range(box, anchor):
    lows, highs = [], []
    for (lo, hi), c in zip(box, anchor):
        lo, hi = lo - c, hi - c
        lows.append(F(0) if lo <= 0 <= hi else min(lo * lo, hi * hi))
        highs.append(max(lo * lo, hi * hi))
    return sum(lows), sum(highs)


def verify_root(squared, root, exact_box):
    lo, hi = interval(squared)
    need(lo <= exact_box[0] and hi >= exact_box[1] and hi >= 0, 'squared box norm enclosure')
    rlo, rhi = interval(root)
    need(0 <= rlo <= rhi and rlo * rlo <= hi <= rhi * rhi, 'sqrt of squared-upper point enclosure')


def verify_mesh_result(source, anchor, result):
    """Audit the last full mesh result with independent point geometry.

    This uses the earlier independent feasible-plane/closed-segment oracle,
    without requiring or fabricating a minimum corpus size for that checker.
    """
    keys = {'status', 'reason', 'failedIndex', 'firstFailedRow', 'rows', 'nearest', 'queries',
            'candidatesExamined', 'sqrtRefinements', 'sqrtLimitedRows', 'failedRows'}
    fields(result, keys, 'last mesh')
    uint(result['status'], 5, 'mesh status integer')
    uint(result['reason'], 11, 'mesh reason integer')
    need(result['status'] in (0, 3) and result['reason'] == (0 if result['status'] == 0 else 7), 'returned ordinary mesh classification')
    for key in ['failedIndex', 'firstFailedRow']:
        if result[key] is not None:
            uint(result[key], len(source['triangles']) - 1, 'mesh optional failure index')
    for key, maximum in [('queries', 64), ('candidatesExamined', 448), ('sqrtRefinements', 32768), ('sqrtLimitedRows', 64), ('failedRows', 64)]:
        uint(result[key], maximum, 'mesh work integer')
    need(result['failedIndex'] is None and len(result['rows']) == len(source['triangles']), 'all mesh source rows owned')
    need(result['queries'] == len(result['rows']), 'all source primitive calls')
    center, radius = vector(anchor), fraction(source['radius'])
    sums = {'candidatesExamined': 0, 'sqrtRefinements': 0, 'sqrtLimitedRows': 0, 'failedRows': 0}
    failure_indices, exact_values = [], []
    components = 0
    for index, (row, triangle) in enumerate(zip(result['rows'], source['triangles'])):
        fields(row, {'triangle', 'query'}, 'last mesh row')
        source_equal(triangle, row['triangle'])
        q = row['query']
        fields(q, {'status', 'reason', 'geometry', 'squaredCross', 'sineSquared', 'candidates',
                   'candidatesExamined', 'sqrtRefinements', 'sqrtRefinementLimited'}, 'primitive result')
        mesh_reference.primitive_shape(q)
        sums['candidatesExamined'] += q['candidatesExamined']
        sums['sqrtRefinements'] += q['sqrtRefinements']
        sums['sqrtLimitedRows'] += int(q['sqrtRefinementLimited'])
        if q['status']:
            need(q['reason'] != 0, 'real primitive failure reason')
            sums['failedRows'] += 1
            failure_indices.append(index)
            continue
        need(q['reason'] == 0, 'completed primitive reason')
        g = q['geometry']
        fields(g, {'surfaceId', 'survivingFeatures', 'barycentric', 'closestLocal', 'closest', 'delta',
                   'normal', 'spherePoint', 'squaredDistance', 'distance', 'gap', 'relation'}, 'primitive geometry')
        uint(g['surfaceId'], 2 ** 53 - 1, 'geometry surface ID integer')
        uint(g['survivingFeatures'], 127, 'surviving feature mask integer')
        need(g['surfaceId'] == triangle['id'], 'stable row identity')
        vertices = tuple(vector(v) for v in triangle['vertices'])
        closest, bary, squared = primitive.closest(center, vertices)
        need(squared > 0, 'accepted primitive has nonzero distance')
        delta = sub(center, closest)
        profile = source['settings']['mesh']['primitive']
        need(profile['maxCandidates'] == 7 and q['sqrtRefinements'] <= min(2 * profile['sqrtRefinements'], profile['maxTotalSqrtRefinements']),
             'successful primitive configured budgets')
        for key, value in [('barycentric', bary), ('closest', closest), ('closestLocal', sub(closest, vertices[0])), ('delta', delta)]:
            contains3(g[key], value)
        contains(g['squaredDistance'], squared)
        primitive.square_root_bounds(*interval(g['distance']), squared)
        gap = interval(g['gap'])
        primitive.square_root_bounds(gap[0] + radius, gap[1] + radius, squared)
        for k in range(3):
            primitive.normalized_bounds(*interval(g['normal'][k]), delta[k], squared)
            lo, hi = interval(g['spherePoint'][k])
            primitive.normalized_bounds((center[k] - hi) / radius, (center[k] - lo) / radius, delta[k], squared)
            for key in ['closestLocal', 'delta']:
                lo, hi = interval(g[key][k])
                need(hi - lo <= fraction(profile['maximumLocalWidth']), 'primitive local quality width')
            lo, hi = interval(g['normal'][k])
            need(-1 <= lo <= hi <= 1 and hi - lo <= fraction(profile['maximumNormalWidth']), 'primitive normal quality width')
        cross_value = primitive.cross(sub(vertices[1], vertices[0]), sub(vertices[2], vertices[0]))
        area_squared = dot(cross_value, cross_value)
        edge0, edge1 = sub(vertices[1], vertices[0]), sub(vertices[2], vertices[0])
        sine_squared = area_squared / (dot(edge0, edge0) * dot(edge1, edge1))
        contains(q['squaredCross'], area_squared)
        contains(q['sineSquared'], sine_squared)
        need(sine_squared >= fraction(profile['minimumSineSquared']), 'primitive conditioning predicate')
        relation = 0 if gap[0] > 0 else 1 if gap[1] < 0 else 2 if gap == (0, 0) else 3
        need(type(g['relation']) is int and g['relation'] == relation, 'primitive gap relation')
        references = primitive.feature_references(center, vertices)
        mask = 0
        need(len(q['candidates']) == q['candidatesExamined'] == 7, 'all successful primitive candidates')
        for candidate in q['candidates']:
            barycentric, residuals = references[candidate['feature']]
            contains3(candidate['barycentric'], barycentric)
            feasible = all(0 <= v <= 1 for v in barycentric)
            true_valid = feasible and all(v <= 0 for v in residuals)
            disposition = candidate['disposition']
            if true_valid:
                need(disposition == 0, 'true closest feature retained')
            if disposition == 0:
                mask |= 1 << candidate['feature']
            elif disposition == 1:
                need(not feasible, 'simplex exclusion is true')
            else:
                need(any(v > 0 for v in residuals), 'KKT exclusion is true')
            if feasible:
                intervals = [interval(v) for v in candidate['kkt'][:candidate['kktCount']]]
                need(all(any(lo <= v <= hi for lo, hi in intervals) for v in residuals), 'KKT reference inclusion')
        need(g['survivingFeatures'] == mask != 0, 'retained primitive features')
        exact_values.append((triangle['id'], squared))
        components += 21
    need(all(result[k] == v for k, v in sums.items()), 'last mesh work sums')
    need(result['firstFailedRow'] == (failure_indices[0] if failure_indices else None), 'last mesh first failed row')
    if failure_indices:
        need(result['status'] == 3 and result['nearest'] is None, 'failed row prevents nearest')
    else:
        need(result['status'] == 0, 'fully successful last mesh')
        nearest = result['nearest']
        fields(nearest, {'squaredDistance', 'distance', 'gap', 'possibleSurfaceIds'}, 'last nearest')
        for key in ['squaredDistance', 'distance', 'gap']:
            pairs = [row['query']['geometry'][key] for row in result['rows']]
            need(all(bits(nearest[key][side]) == bits(min(v[side] for v in pairs)) for side in (0, 1)), 'last mesh exact endpoint-min bits')
        expected = sorted(row['triangle']['id'] for row in result['rows']
                          if row['query']['geometry']['squaredDistance'][0] <= nearest['squaredDistance'][1])
        need(type(nearest['possibleSurfaceIds']) is list and all(type(v) is int for v in nearest['possibleSurfaceIds'])
             and nearest['possibleSurfaceIds'] == expected, 'all last mesh possible IDs')
        minimum = min(q for _, q in exact_values)
        need({i for i, q in exact_values if q == minimum} <= set(expected), 'all true last mesh winners')
        contains(nearest['squaredDistance'], minimum)
        primitive.square_root_bounds(*interval(nearest['distance']), minimum)
        lo, hi = interval(nearest['gap'])
        primitive.square_root_bounds(lo + radius, hi + radius, minimum)
        components += 3
    return components


def input_fingerprint(fixtures):
    def encode(value):
        if type(value) is dict:
            return '{' + ','.join(json.dumps(k) + ':' + encode(value[k]) for k in sorted(value)) + '}'
        if type(value) is list:
            return '[' + ','.join(encode(v) for v in value) + ']'
        if type(value) is int:
            return 'integer:' + str(value)
        if type(value) is float:
            return 'binary64:' + struct.pack('>d', value).hex()
        need(False, 'numeric input fingerprint shape')
    # Multiset of whole inputs, retaining each source's array order and -0.
    rows = sorted(encode(f['input']) for f in fixtures)
    return hashlib.sha256(('\n'.join(rows) + '\n').encode()).hexdigest()


def verify(data):
    fields(data, {'schema', 'kind', 'fixtures'}, 'fixture envelope')
    need(type(data['schema']) is int and data['schema'] == 1 and data['kind'] == 'sphere-triangle-mesh-trajectory-fixtures', 'trajectory fixture schema')
    fixtures = data['fixtures']
    need(type(fixtures) is list and 32 <= len(fixtures) <= 256, 'finite trajectory corpus')
    need(len(fixtures) == EXPECTED_FIXTURE_COUNT, 'fixed trajectory fixture count')
    fingerprint = input_fingerprint(fixtures)
    need(fingerprint == EXPECTED_INPUT_FINGERPRINT, 'fixed trajectory input fingerprint')
    stats = {'fixtures': len(fixtures), 'separated': 0, 'penetrationWitnesses': 0, 'notCertified': 0,
             'invalidInputs': 0, 'certifiedLeaves': 0, 'cellAudits': 0, 'wholePathReferences': 0,
             'witnessReferences': 0, 'pathBoxReferences': 0, 'squaredBoxReferences': 0,
             'certificateReferences': 0, 'lastMeshReferenceComponents': 0, 'workExactFixtures': 0}
    names = set()
    for fixture in fixtures:
        fields(fixture, {'name', 'input', 'result'}, 'fixture')
        need(type(fixture['name']) is str and fixture['name'] and fixture['name'] not in names, 'unique fixture label')
        names.add(fixture['name'])
        source, result = fixture['input'], fixture['result']
        faults = input_faults(source)
        fields(result, RESULT_KEYS, 'trajectory result')
        if result['failedIndex'] is not None:
            uint(result['failedIndex'], len(source['triangles']) - 1, 'source optional failure index')
        uint(result['partitionLeaves'], 128, 'partition leaves integer')
        uint(result['maximumDepth'], 32, 'maximum depth integer')
        status, reason = result['status'], result['reason']
        need(status in STATUSES and reason in REASONS, 'known trajectory classification')
        need(status not in ('unsupported_environment', 'numerical_failure'), 'ordinary finite corpus has no injected environment/allocation failures')
        total = work(result['work'])
        need(total['workExact'], 'ordinary finite fixture has returned work only; exceptional branch is not fabricated')
        stats['workExactFixtures'] += 1
        if faults:
            need(status == 'invalid_input' and (reason, result['failedIndex']) in faults, 'actual prevalidation fault')
            need(result['snapshot'] is None and result['lastMesh'] is None and result['lastMeshAuditIndex'] is None,
                 'preflight has no invented snapshots')
            need(not result['certifiedLeaves'] and result['safePrefix'] is None and result['witness'] is None
                 and result['current'] is None and not result['frontier'] and not result['audits'], 'preflight has no path proofs')
            need(result['partitionLeaves'] == result['maximumDepth'] == 0
                 and all(total[k] == 0 for k in WORK_KEYS - {'workExact'}), 'preflight no work')
            stats['invalidInputs'] += 1
            continue
        need(status != 'invalid_input' and result['failedIndex'] is None, 'valid source not falsely rejected')
        source_equal(source, result['snapshot'])
        need(not input_faults(result['snapshot']), 'snapshot keeps source integer ID/settings types')
        _verify_trajectory(source, result, stats)
    need(stats['separated'] and stats['penetrationWitnesses'] and stats['notCertified'] and stats['invalidInputs'], 'finite status coverage')
    return {'status': 'PASS', **stats, 'inputFingerprint': fingerprint,
            'scope': 'exact rational whole-path and returned-bound proofs; counter sums/bounds, not independent instruction execution measurement'}


def _verify_trajectory(source, result, stats):
    settings = source['settings']
    triangles = source['triangles']
    count = len(triangles)
    start, end, radius = vector(source['start']), vector(source['end']), fraction(source['radius'])
    velocity = sub(end, start)
    for key in ['certifiedLeaves', 'frontier', 'audits']:
        need(type(result[key]) is list, 'owned ' + key + ' array')
    need(len(result['audits']) <= min(settings['maxEvaluations'], 255), 'finite audit capacity')
    if count > settings['mesh']['maxSurfaces']:
        need(result['status'] == 'not_certified' and result['reason'] == 'surface_budget', 'caller surface budget')
        need(not result['audits'] and not result['certifiedLeaves'] and result['safePrefix'] is None
             and result['witness'] is None and result['current'] is None and result['lastMesh'] is None
             and result['lastMeshAuditIndex'] is None, 'surface budget performs no query')
        need(len(result['frontier']) == 1 and cell(result['frontier'][0], 32) == (F(0), F(1), 0), 'surface budget keeps whole unexamined domain')
        need(result['partitionLeaves'] == 1 and result['maximumDepth'] == 0
             and all(result['work'][k] == 0 for k in WORK_KEYS - {'workExact'}), 'surface budget has zero work')
        stats['notCertified'] += 1
        return
    compiled = compile_mesh_path(start, end, triangles)
    stats['wholePathReferences'] += 1
    whole_minimum, _ = mesh_path_minimum(compiled)
    cache = {}

    def exact_minimum(lo, hi):
        key = lo, hi
        if key not in cache:
            cache[key] = mesh_path_minimum(compiled, lo, hi)[0]
        return cache[key]

    pending = [(F(0), F(1), 0)]
    certified = []
    expected_leaves = []
    splits = 0
    maximum_depth = 0
    terminal = None
    last_returned = None
    sums = {k: 0 for k in WORK_KEYS - {'workExact'}}
    for index, audit in enumerate(result['audits']):
        fields(audit, AUDIT_KEYS, 'cell audit')
        need(pending and terminal is None, 'no audit after terminal or outside frontier')
        current = cell(audit['cell'], settings['maxDepth'])
        need(current == pending.pop(0), 'left-first closed dyadic traversal')
        lo, hi, depth = current
        maximum_depth = max(maximum_depth, depth)
        midpoint = fraction(audit['midpoint'])
        need(midpoint == (lo + hi) / 2 and bits(audit['midpoint']) == bits(float(midpoint)), 'exact representable cell midpoint')
        outcome = audit['outcome']
        need(outcome in {'separated', 'split', 'penetration_witness', 'not_certified'}, 'ordinary returned audit outcome')
        delta = work(audit['work'])
        need(delta['workExact'] and delta['meshQueries'] in (0, 1) and type(audit['meshQueried']) is bool
             and delta['meshQueries'] == int(audit['meshQueried']), 'per-cell attempted query work')
        need(delta['enclosureSqrtCalls'] <= 2, 'two norm root calls maximum')
        if audit['pathBounds'] is not None:
            box = bounds3(audit['pathBounds'])
            for s in (lo, hi):
                contains3(audit['pathBounds'], add(start, scale(velocity, s)))
            need(audit['pointBounds'] is not None and audit['anchor'] is not None, 'complete path box/point/anchor')
            point_box = bounds3(audit['pointBounds'])
            contains3(audit['pointBounds'], add(start, scale(velocity, midpoint)))
            anchor = vector(audit['anchor'])
            need(all(abs(v) <= F(1e150) for v in anchor), 'anchor in single-query domain')
            stats['pathBoxReferences'] += 9
        else:
            need(audit['pointBounds'] is None and audit['anchor'] is None, 'absent path construction')
            box = point_box = anchor = None
        if audit['meshQueried']:
            need(anchor is not None and type(audit['meshStatus']) is int and audit['meshStatus'] in (0, 3)
                 and type(audit['meshReason']) is int and audit['meshReason'] == (0 if audit['meshStatus'] == 0 else 7), 'returned ordinary mesh classification')
            need(delta['primitiveQueries'] == count, 'every source queried in returned mesh block')
            need(sums['sqrtRefinements'] + count * 512 <= settings['maxTotalSqrtRefinements'], 'mesh worst-block reservation fits before call')
            need(sums['meshQueries'] < settings['maxEvaluations'], 'evaluation budget before call')
            last_returned = index
            if audit['meshStatus'] == 0:
                need(delta['candidatesExamined'] == count * 7 and audit['distance'] is not None, 'all completed mesh candidates and distance')
                anchor_squared = min(primitive.closest(anchor, tuple(vector(v) for v in t['vertices']))[2] for t in triangles)
                primitive.square_root_bounds(*interval(audit['distance']), anchor_squared)
                stats['certificateReferences'] += 1
            else:
                need(audit['distance'] is None, 'failed mesh has no aggregate distance')
        else:
            need(audit['meshStatus'] is None and audit['meshReason'] is None and audit['distance'] is None,
                 'unqueried cell has no borrowed mesh result')
            need(delta['primitiveQueries'] == delta['candidatesExamined'] == delta['primitiveSqrtRefinements']
                 == delta['meshSqrtLimitedRows'] == 0, 'no fabricated primitive work')
        root_count = 0
        for square_key, root_key, exact_box in [
                ('displacementSquaredBound', 'displacementRoot', box), ('errorSquaredBound', 'errorRoot', point_box)]:
            squared, root = audit[square_key], audit[root_key]
            if squared is not None:
                need(anchor is not None and audit['meshStatus'] == 0, 'norm proof follows completed anchor query')
                exact_squared = box_squared_range(exact_box, anchor)
                slo, shi = interval(squared)
                need(slo <= exact_squared[0] and shi >= exact_squared[1] and shi >= 0, 'complete squared box norm inclusion')
                stats['squaredBoxReferences'] += 2
            if root is not None:
                need(squared is not None, 'root has squared source')
                verify_root(squared, root, exact_squared)
                need(sums['sqrtRefinements'] + delta['primitiveSqrtRefinements'] + 512
                     <= settings['maxTotalSqrtRefinements'], 'enclosure worst-block reservation can fit')
                root_count += 1
                stats['squaredBoxReferences'] += 1
        need(delta['enclosureSqrtCalls'] == root_count, 'actual returned enclosure root calls')
        need(delta['enclosureSqrtRefinements'] <= 2 * settings['enclosureSqrtRefinements'] * root_count,
             'configured per-endpoint enclosure work')
        if audit['errorRoot'] is not None:
            need(audit['displacementRoot'] is not None, 'displacement root precedes error root')
        certificates = [('clearanceCertificate', -1), ('penetrationCertificate', 1)]
        for key, sign in certificates:
            if audit[key] is not None:
                need(audit['distance'] is not None and audit['displacementRoot'] is not None and audit['errorRoot'] is not None,
                     'certificate has completed sources')
                d = interval(audit['distance'])[0 if sign < 0 else 1]
                root = interval(audit['displacementRoot' if sign < 0 else 'errorRoot'])[1]
                contains(audit[key], d + sign * root - radius)
                stats['certificateReferences'] += 1
        complete_certificates = audit['clearanceCertificate'] is not None and audit['penetrationCertificate'] is not None
        if outcome == 'separated':
            need(complete_certificates and interval(audit['clearanceCertificate'])[0] > 0, 'strict positive lower-bound expression')
            need(exact_minimum(lo, hi) > radius * radius, 'independent whole-leaf distance is strictly beyond radius')
            certified.append(current)
            expected_leaves.append((index, audit))
        elif outcome == 'split':
            need(complete_certificates and interval(audit['clearanceCertificate'])[0] <= 0
                 and interval(audit['penetrationCertificate'])[1] >= 0, 'split was not certified by either strict expression')
            need(depth < settings['maxDepth'] and 2 + splits <= settings['maxLeaves'], 'split respects leaf/depth budgets')
            pending[0:0] = [(lo, midpoint, depth + 1), (midpoint, hi, depth + 1)]
            splits += 1
        else:
            terminal = index
            if outcome == 'penetration_witness':
                need(complete_certificates and interval(audit['penetrationCertificate'])[1] < 0, 'strict negative upper-bound expression')
                need(exact_minimum(midpoint, midpoint) < radius * radius, 'independent exact path penetration point')
        for key in sums:
            sums[key] += delta[key]
        need(sums['sqrtRefinementsUpper'] <= settings['maxTotalSqrtRefinements'], 'hard total work upper')
    need(all(result['work'][key] == value for key, value in sums.items()), 'result work equals sum of cell DELTAs')
    need(result['work']['meshQueries'] <= min(settings['maxEvaluations'], 255), 'actual query limit')
    need(result['partitionLeaves'] == 1 + splits <= settings['maxLeaves'], 'current full partition count')
    need(len(result['certifiedLeaves']) == len(expected_leaves), 'no dropped or invented certified leaf')
    for leaf, (index, audit) in zip(result['certifiedLeaves'], expected_leaves):
        fields(leaf, {'cell', 'lowerGapCertificate', 'auditIndex'}, 'certified leaf')
        uint(leaf['auditIndex'], len(result['audits']) - 1, 'leaf audit ordinal')
        need(leaf['auditIndex'] == index, 'leaf references actual separated audit')
        source_equal(leaf['cell'], audit['cell'])
        source_equal(leaf['lowerGapCertificate'], audit['clearanceCertificate'])
    if certified:
        need(certified[0][0] == 0 and all(a[1] == b[0] for a, b in zip(certified, certified[1:])), 'left-to-right gapless certified prefix')
        need(result['safePrefix'] is not None, 'nonempty certified prefix is retained')
        source_equal(result['safePrefix'], [0, float(certified[-1][1])])
    else:
        need(result['safePrefix'] is None, 'no proof means optional safe prefix absent')
    if terminal is not None:
        need(result['current'] is not None, 'terminal unproved current is retained')
        source_equal(result['current'], result['audits'][terminal]['cell'])
    elif result['current'] is not None:
        need(pending and cell(result['current'], settings['maxDepth']) == pending.pop(0), 'budget-blocked current is next left-first cell')
        maximum_depth = max(maximum_depth, result['current']['depth'])
    need([cell(v, settings['maxDepth']) for v in result['frontier']] == pending, 'all unexamined frontier cells retained in order')
    partition = certified + ([cell(result['current'], settings['maxDepth'])] if result['current'] is not None else []) + pending
    need(len(partition) == result['partitionLeaves'] and partition[0][0] == 0 and partition[-1][1] == 1
         and all(a[1] == b[0] for a, b in zip(partition, partition[1:])), 'whole closed partition has no holes or overlaps beyond shared endpoints')
    need(result['maximumDepth'] == maximum_depth, 'maximum popped depth includes blocked current')
    if last_returned is None:
        need(result['lastMesh'] is None and result['lastMeshAuditIndex'] is None, 'no unexecuted last mesh')
    else:
        need(type(result['lastMeshAuditIndex']) is int and result['lastMeshAuditIndex'] == last_returned
             and result['lastMesh'] is not None, 'last mesh linked to last returned call')
        audit = result['audits'][last_returned]
        last = result['lastMesh']
        need(last['status'] == audit['meshStatus'] and last['reason'] == audit['meshReason'], 'last mesh classification link')
        for left, right in [('queries', 'primitiveQueries'), ('candidatesExamined', 'candidatesExamined'),
                            ('sqrtRefinements', 'primitiveSqrtRefinements'), ('sqrtLimitedRows', 'meshSqrtLimitedRows')]:
            need(last[left] == audit['work'][right], 'last mesh returned work link')
        source_equal(last['nearest']['distance'] if last['nearest'] else None, audit['distance'])
        stats['lastMeshReferenceComponents'] += verify_mesh_result(source, audit['anchor'], last)
    status, reason = result['status'], result['reason']
    if status == 'separated':
        need(reason == 'none' and result['current'] is None and not pending and result['witness'] is None
             and certified and certified[-1][1] == 1 and whole_minimum > radius * radius, 'global strict separation covers the entire exact path')
        stats['separated'] += 1
    elif status == 'penetration_witness':
        need(reason == 'none' and terminal is not None and result['audits'][terminal]['outcome'] == 'penetration_witness', 'witness has actual terminal proof')
        w = result['witness']
        fields(w, {'cell', 'parameter', 'exactPathBounds', 'anchor', 'errorUpper', 'upperGapCertificate', 'auditIndex'}, 'witness')
        audit = result['audits'][terminal]
        need(type(w['auditIndex']) is int and w['auditIndex'] == terminal, 'witness audit link')
        for left, right in [('cell', 'cell'), ('parameter', 'midpoint'), ('exactPathBounds', 'pointBounds'),
                            ('anchor', 'anchor'), ('upperGapCertificate', 'penetrationCertificate')]:
            source_equal(w[left], audit[right])
        source_equal(w['errorUpper'], audit['errorRoot'][1])
        contains3(w['exactPathBounds'], add(start, scale(velocity, fraction(w['parameter']))))
        need(interval(w['upperGapCertificate'])[1] < 0 and exact_minimum(fraction(w['parameter']), fraction(w['parameter'])) < radius * radius,
             'strict point witness includes anchor rounding error')
        stats['penetrationWitnesses'] += 1
        stats['witnessReferences'] += 1
    else:
        need(status == 'not_certified' and result['witness'] is None and result['current'] is not None,
             'not certified keeps current/frontier without a fabricated witness')
        need(reason in {'mesh_query_failed', 'evaluation_budget', 'leaf_budget', 'depth_budget', 'sqrt_budget'}, 'ordinary finite stopping reason')
        if reason == 'evaluation_budget':
            need(terminal is None and sums['meshQueries'] == settings['maxEvaluations'], 'evaluation budget blocks before query')
        elif reason == 'mesh_query_failed':
            need(terminal is not None and result['audits'][terminal]['meshStatus'] == 3, 'mesh failure remains visible')
        elif reason == 'depth_budget':
            need(result['current']['depth'] == settings['maxDepth'], 'depth budget is exhausted')
        elif reason == 'leaf_budget':
            need(result['partitionLeaves'] == settings['maxLeaves'], 'leaf budget is exhausted')
        elif reason == 'sqrt_budget':
            need(terminal is not None, 'sqrt reservation stops the current audit')
            audit = result['audits'][terminal]
            before = sums['sqrtRefinements'] - audit['work']['sqrtRefinements']
            if not audit['meshQueried']:
                need(before + count * 512 > settings['maxTotalSqrtRefinements'], 'mesh block reservation really unavailable')
            else:
                need(audit['meshStatus'] == 0 and audit['errorRoot'] is None, 'sqrt budget stops before an unexecuted root')
                used = audit['work']['primitiveSqrtRefinements'] + audit['work']['enclosureSqrtRefinements']
                need(before + used + 512 > settings['maxTotalSqrtRefinements'], 'next root worst-block reservation really unavailable')
        if reason in {'leaf_budget', 'depth_budget'}:
            need(terminal is not None, 'subdivision budget stops evaluated cell')
            audit = result['audits'][terminal]
            need(audit['clearanceCertificate'] is not None and audit['penetrationCertificate'] is not None
                 and interval(audit['clearanceCertificate'])[0] <= 0 and interval(audit['penetrationCertificate'])[1] >= 0,
                 'subdivision budget follows genuinely inconclusive certificates')
        stats['notCertified'] += 1
    stats['certifiedLeaves'] += len(certified)
    stats['cellAudits'] += len(result['audits'])


if __name__ == '__main__':
    need(__debug__, 'run reference checker without Python -O')
    need(len(sys.argv) == 2, 'Usage: python verify-sphere-triangle-mesh-trajectory.py fixtures.json')
    print(json.dumps(verify(load(sys.argv[1])), indent=2))
