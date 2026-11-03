"""Independent exact-rational oracle for finite binary64 sphere/triangle inputs.

Find the minimum using a feasible plane projection and three clamped segments.
This does not reproduce the production KKT candidate rejection algorithm.
Square inequalities check irrational distances/normals without a libm/Decimal
sqrt accuracy assumption. Returned intervals denote real bounds, not estimates.
"""
from fractions import Fraction as F
from pathlib import Path
import json
import math
import sys


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def rational(value):
    need(type(value) in (int, float) and math.isfinite(value), 'finite numeric scalar')
    return F(value)


def vector(value):
    need(type(value) is list and len(value) == 3, 'three components')
    return tuple(rational(v) for v in value)


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def scale(a, k):
    return tuple(x * k for x in a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def bounds(value):
    need(type(value) is list and len(value) == 2, 'interval pair')
    lo, hi = map(rational, value)
    need(lo <= hi, 'ordered finite interval')
    return lo, hi


def contains(interval, value):
    lo, hi = bounds(interval)
    need(lo <= value <= hi, 'exact reference outside interval')


def contains_vector(intervals, value):
    need(type(intervals) is list and len(intervals) == 3, 'three intervals')
    for interval, component in zip(intervals, value):
        contains(interval, component)


def normalized_bounds(lo, hi, delta, squared):
    """Prove lo <= delta/sqrt(squared) <= hi, with exact rational inequalities."""
    need(lo <= hi and squared > 0, 'normal denominator and bounds')
    if delta < 0:
        lo, hi, delta = -hi, -lo, -delta
    if delta == 0:
        need(lo <= 0 <= hi, 'zero normal component')
    else:
        need(hi > 0 and hi * hi * squared >= delta * delta, 'normal upper enclosure')
        need(lo <= 0 or lo * lo * squared <= delta * delta, 'normal lower enclosure')


def square_root_bounds(lo, hi, squared):
    need(lo <= hi and squared >= 0, 'distance order')
    need(hi >= 0 and hi * hi >= squared, 'distance upper enclosure')
    need(lo <= 0 or lo * lo <= squared, 'distance lower enclosure')


def closest(center, vertices):
    """Enumerate exact feasible plane solution + closed segments, select minimum."""
    a, b, c = vertices
    ab, ac, w = sub(b, a), sub(c, a), sub(center, a)
    aa, bb, cc = dot(ab, ab), dot(ab, ac), dot(ac, ac)
    determinant = aa * cc - bb * bb
    need(determinant > 0, 'nondegenerate oracle triangle')
    u = (cc * dot(ab, w) - bb * dot(ac, w)) / determinant
    v = (aa * dot(ac, w) - bb * dot(ab, w)) / determinant
    candidates = []
    if u >= 0 and v >= 0 and u + v <= 1:
        candidates.append((add(a, add(scale(ab, u), scale(ac, v))), (1 - u - v, u, v)))
    for i, j in [(0, 1), (1, 2), (2, 0)]:
        edge = sub(vertices[j], vertices[i])
        t = dot(sub(center, vertices[i]), edge) / dot(edge, edge)
        t = min(F(1), max(F(0), t))
        bary = [F(0)] * 3
        bary[i], bary[j] = 1 - t, t
        candidates.append((add(vertices[i], scale(edge, t)), tuple(bary)))
    distances = [dot(sub(center, q), sub(center, q)) for q, _ in candidates]
    minimum = min(distances)
    winners = [candidate for candidate, distance in zip(candidates, distances) if distance == minimum]
    need(all(q == winners[0][0] and bary == winners[0][1] for q, bary in winners), 'unique closest convex point')
    return (*winners[0], minimum)


def feature_references(center, vertices):
    """Exact unconstrained feature parameters/residuals audit exclusion evidence."""
    a, b, c = vertices
    ab, ac, w = sub(b, a), sub(c, a), sub(center, a)
    aa, bb, cc = dot(ab, ab), dot(ab, ac), dot(ac, ac)
    determinant = aa * cc - bb * bb
    u, v = (cc * dot(ab, w) - bb * dot(ac, w)) / determinant, (aa * dot(ac, w) - bb * dot(ab, w)) / determinant
    result = [((1 - u - v, u, v), [])]
    for i, j, k in [(0, 1, 2), (1, 2, 0), (2, 0, 1)]:
        edge = sub(vertices[j], vertices[i])
        t = dot(sub(center, vertices[i]), edge) / dot(edge, edge)
        bary = [F(0)] * 3
        bary[i], bary[j] = 1 - t, t
        q = add(vertices[i], scale(edge, t))
        result.append((tuple(bary), [dot(sub(center, q), sub(vertices[k], q))]))
    for i in range(3):
        bary = [F(0)] * 3
        bary[i] = F(1)
        result.append((tuple(bary), [dot(sub(center, vertices[i]), sub(vertices[j], vertices[i])) for j in range(3) if j != i]))
    return result


def verify(data):
    need(type(data) is dict and data.get('schema') == 1 and data.get('kind') == 'sphere-triangle-fixtures', 'fixture schema')
    fixtures = data.get('fixtures')
    need(type(fixtures) is list and len(fixtures) >= 64, 'finite corpus')
    names = set()
    stats = dict(fixtures=len(fixtures), completed=0, failures=0, referenceComponents=0, retainedFeatureCounts=[0] * 7)
    for fixture in fixtures:
        name, source, result = fixture['name'], fixture['input'], fixture['result']
        need(type(name) is str and name not in names, 'unique case name')
        names.add(name)
        sphere, triangle, settings = source['sphere'], source['triangle'], source['settings']
        center, radius = vector(sphere['center']), rational(sphere['radius'])
        vertices = tuple(vector(v) for v in triangle['vertices'])
        need(len(vertices) == 3, 'three vertices')
        status = result['status']
        need(type(status) is int and 0 <= status <= 7, 'known status')
        need(type(result['reason']) is int and 0 <= result['reason'] <= 17, 'known reason')
        geometry = result['geometry']
        if status != 0:
            need(geometry is None and result['reason'] != 0, 'failure has no accepted geometry')
            stats['failures'] += 1
            continue
        need(result['reason'] == 0 and type(geometry) is dict, 'completed geometry')
        need(type(triangle['id']) is int and 1 <= triangle['id'] <= 2**53 - 1, 'stable valid ID')
        need(geometry['surfaceId'] == triangle['id'], 'surface identity')
        need(0 < radius <= F(1e150) and all(abs(x) <= F(1e150) for v in (center, *vertices) for x in v), 'input domain')
        need(1 <= settings['sqrtRefinements'] <= 256 and 1 <= settings['maxTotalSqrtRefinements'] <= 1024 and settings['maxCandidates'] == 7, 'completed budgets')
        need(type(result['sqrtRefinements']) is int and 0 <= result['sqrtRefinements'] <= min(2 * settings['sqrtRefinements'], settings['maxTotalSqrtRefinements']), 'actual sqrt work')
        q, bary, squared = closest(center, vertices)
        need(squared > 0, 'zero distance never has a normal')
        delta, local = sub(center, q), sub(q, vertices[0])
        contains_vector(geometry['barycentric'], bary)
        contains_vector(geometry['closest'], q)
        contains_vector(geometry['closestLocal'], local)
        contains_vector(geometry['delta'], delta)
        contains(geometry['squaredDistance'], squared)
        square_root_bounds(*bounds(geometry['distance']), squared)
        gap = bounds(geometry['gap'])
        square_root_bounds(gap[0] + radius, gap[1] + radius, squared)
        for i in range(3):
            normalized_bounds(*bounds(geometry['normal'][i]), delta[i], squared)
            lo, hi = bounds(geometry['spherePoint'][i])
            normalized_bounds((center[i] - hi) / radius, (center[i] - lo) / radius, delta[i], squared)
            for field in ['closestLocal', 'delta']:
                lo, hi = bounds(geometry[field][i])
                need(hi - lo <= rational(settings['maximumLocalWidth']), 'local quality gate')
            lo, hi = bounds(geometry['normal'][i])
            need(-1 <= lo <= hi <= 1 and hi - lo <= rational(settings['maximumNormalWidth']), 'normal quality gate')
        relation = 0 if gap[0] > 0 else 1 if gap[1] < 0 else 2 if gap == (0, 0) else 3
        need(type(geometry['relation']) is int and geometry['relation'] == relation, 'relation follows enclosure, not a midpoint')
        cross_value = cross(sub(vertices[1], vertices[0]), sub(vertices[2], vertices[0]))
        area_squared = dot(cross_value, cross_value)
        sine_squared = area_squared / (dot(sub(vertices[1], vertices[0]), sub(vertices[1], vertices[0])) * dot(sub(vertices[2], vertices[0]), sub(vertices[2], vertices[0])))
        contains(result['squaredCross'], area_squared)
        contains(result['sineSquared'], sine_squared)
        need(sine_squared >= rational(settings['minimumSineSquared']), 'conditioning gate')
        candidates = result['candidates']
        need(result['candidatesExamined'] == len(candidates) == 7, 'all seven candidates examined')
        need({candidate['feature'] for candidate in candidates} == set(range(7)), 'complete distinct feature set')
        references = feature_references(center, vertices)
        mask = 0
        for candidate in candidates:
            feature, disposition = candidate['feature'], candidate['disposition']
            need(type(feature) is int and type(disposition) is int and 0 <= disposition <= 2, 'feature diagnostic')
            cbary, residual = references[feature]
            feasible = all(0 <= v <= 1 for v in cbary)
            exact_valid = feasible and all(v <= 0 for v in residual)
            contains_vector(candidate['barycentric'], cbary)
            if exact_valid:
                need(disposition == 0, 'true closest feature must not be dropped')
            if disposition == 0:
                mask |= 1 << feature
                stats['retainedFeatureCounts'][feature] += 1
            elif disposition == 1:
                need(not feasible, 'simplex rejection must exclude exact feature')
            else:
                need(any(v > 0 for v in residual), 'KKT rejection must exclude exact feature')
            if feasible:
                need(candidate['kktCount'] == len(residual), 'KKT dimension')
                # Vertex residual order is not part of the geometric contract.
                intervals = candidate['kkt'][:candidate['kktCount']]
                need(all(any(bounds(interval)[0] <= v <= bounds(interval)[1] for interval in intervals) for v in residual), 'KKT residual inclusion')
        need(type(geometry['survivingFeatures']) is int and geometry['survivingFeatures'] == mask != 0, 'all retained feature bits preserved')
        stats['completed'] += 1
        stats['referenceComponents'] += 3 * 6 + 3
    need(stats['completed'] >= 64 and all(stats['retainedFeatureCounts']), 'face, every edge and every vertex independently covered')
    return {'status': 'PASS', **stats}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def load(path):
    content = Path(path).read_bytes()
    need(len(content) <= 16 * 1024 * 1024, 'bounded fixture bytes')
    return json.loads(content, object_pairs_hook=unique_object, parse_constant=lambda value: (_ for _ in ()).throw(AssertionError('nonfinite JSON')))


if __name__ == '__main__':
    print(json.dumps(verify(load(sys.argv[1])), indent=2))
