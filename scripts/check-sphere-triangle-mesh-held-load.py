"""Independent Fraction held-load, global-seconds mesh-entry certificate checker.

Feasible face projections and three clamped edges are evaluated with Fractions,
never selected using the Native subdivision or retained KKT mask. Strict scalar
loading and independent legacy mesh diagnostics reuse prior authored references.
The reused structural checks distinguish a closed positive prefix, positive islands, pending
partition cells, and an E-corrected negative point. No time sampling or libm
square root is used as a proof of entry or of a whole-cell separation.
"""
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location(
    'entry_trajectory_reference', Path(__file__).with_name('verify-sphere-triangle-mesh-trajectory.py'))
trajectory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trajectory)
need = trajectory.need
fraction = trajectory.fraction
vector = trajectory.vector
add, sub, scale = trajectory.add, trajectory.sub, trajectory.scale
bits, source_equal = trajectory.bits, trajectory.source_equal
loads, load = trajectory.loads, trajectory.load
fields, uint = trajectory.fields, trajectory.uint
interval, bounds3 = trajectory.interval, trajectory.bounds3
contains, contains3 = trajectory.contains, trajectory.contains3
primitive = trajectory.primitive
WORK_KEYS = trajectory.WORK_KEYS
AUDIT_KEYS = trajectory.AUDIT_KEYS
SETTINGS_KEYS = trajectory.SETTINGS_KEYS | {'timeTolerance'}
ENTRY_AUDIT_KEYS = (AUDIT_KEYS - {'midpoint', 'cell'}) | {'kind', 'time', 'cell'}
RESULT_KEYS = {'status', 'reason', 'failedIndex', 'snapshot', 'initial', 'initialSeparationProven',
               'certifiedLeaves', 'safePrefix', 'bestWitness', 'window', 'candidateSurfaceIds',
               'partition', 'frontier', 'current', 'audits', 'lastMesh', 'lastMeshAuditIndex',
               'work', 'partitionLeaves', 'maximumDepth', 'worldBody', 'acceleration', 'wholePathBounds', 'wholeVelocityBounds'}
STATUSES = {'entry_window', 'separated', 'initial_penetration', 'not_certified',
            'invalid_input', 'unsupported_environment', 'numerical_failure'}
REASONS = (trajectory.REASONS - {'parameter_resolution'}) | {'initial_boundary', 'time_resolution', 'body_not_found', 'body_invalid', 'unsupported_body', 'derived_domain'}
OUTCOMES = {'initial_separated', 'initial_penetration', 'initial_uncertain',
            'separated', 'split', 'unresolved'}
# These are fixed from the complete, independently reviewed finite corpus, not
# inferred from labels, result success counts, or the order received at runtime.
EXPECTED_FIXTURE_COUNT = 79
EXPECTED_INPUT_FINGERPRINT = '3a7679cff9aa2cebf0b162bdb920821d16b272fe645cec5ccc9849f0025dc85e'


def verify_width(width, lo, hi, tolerance):
    lo, hi, tolerance = fraction(lo), fraction(hi), fraction(tolerance)
    need(0 <= lo < hi and 0 < tolerance <= fraction(.1), 'global seconds and time tolerance domain')
    a, b = interval(width)
    need(a <= hi-lo <= b <= tolerance, 'outward seconds width encloses exact U-L within tolerance')


def work(value):
    fields(value, WORK_KEYS, 'entry work')
    maxima = {'meshQueries': 256, 'primitiveQueries': 16384, 'candidatesExamined': 114688,
              'primitiveSqrtRefinements': 8388608, 'enclosureSqrtRefinements': 262144,
              'sqrtRefinements': 8650752, 'sqrtRefinementsUpper': 8650752,
              'meshSqrtLimitedRows': 16384, 'enclosureSqrtCalls': 512,
              'enclosureSqrtLimitedCalls': 512}
    for key, maximum in maxima.items():
        uint(value[key], maximum, 'bounded entry ' + key)
    need(type(value['workExact']) is bool, 'entry work certainty flag')
    need(value['sqrtRefinements'] == value['primitiveSqrtRefinements'] + value['enclosureSqrtRefinements'],
         'returned sqrt counts are actual component sum')
    need(value['sqrtRefinementsUpper'] >= value['sqrtRefinements'], 'unknown-work conservative upper')
    if value['workExact']:
        need(value['sqrtRefinementsUpper'] == value['sqrtRefinements'], 'exact work exact upper')
    need(value['enclosureSqrtLimitedCalls'] <= value['enclosureSqrtCalls'], 'bounded limited enclosure calls')
    need(value['meshSqrtLimitedRows'] <= value['primitiveQueries'], 'bounded limited mesh rows')
    need(value['candidatesExamined'] <= 7 * value['primitiveQueries'], 'KKT candidate structural work upper')
    need(value['primitiveSqrtRefinements'] <= 512 * value['primitiveQueries'], 'primitive sqrt structural work upper')
    need(value['enclosureSqrtRefinements'] <= 512 * value['enclosureSqrtCalls'], 'enclosure sqrt structural work upper')
    return value


def acceleration(source):
    sphere = source['sphere']
    mass = fraction(sphere['mass'])
    need(mass > 0, 'positive exact inertial mass')
    return add(vector(sphere['gravity']), scale(vector(sphere['force']), 1/mass))


def path_point(source, time):
    t = fraction(time)
    return add(vector(source['sphere']['position']),
               add(scale(vector(source['sphere']['velocity']), t), scale(acceleration(source), t*t/2)))


def quadratic_range(c0, c1, c2, lo, hi):
    """Exact full coordinate extrema, including every feasible stationary point."""
    c0, c1, c2, lo, hi = map(fraction, (c0, c1, c2, lo, hi))
    need(lo <= hi, 'ordered quadratic domain')
    times = [lo, hi]
    if c2:
        stationary = -c1/(2*c2)
        if lo <= stationary <= hi:
            times.append(stationary)
    values = [(c2*t+c1)*t+c0 for t in times]
    return min(values), max(values)


def path_range(source, lo, hi):
    return tuple(quadratic_range(p, v, a/2, lo, hi) for p, v, a in
                 zip(vector(source['sphere']['position']), vector(source['sphere']['velocity']), acceleration(source)))


def point_triangle_squared(point, vertices):
    """Feasible Gram projection plus THREE CLAMPED edges, no Native masks."""
    a, b, c = map(vector, vertices)
    point = vector(point)
    ab, ac, ap = sub(b,a), sub(c,a), sub(point,a)
    dot = trajectory.dot
    aa, bb, cc = dot(ab,ab), dot(ab,ac), dot(ac,ac)
    determinant = aa*cc-bb*bb
    values = []
    if determinant > 0:
        u = (cc*dot(ab,ap)-bb*dot(ac,ap))/determinant
        v = (aa*dot(ac,ap)-bb*dot(ab,ap))/determinant
        if u >= 0 and v >= 0 and u+v <= 1:
            delta = sub(ap,add(scale(ab,u),scale(ac,v)))
            values.append(dot(delta,delta))
    for x,y in ((a,b),(b,c),(c,a)):
        edge = sub(y,x)
        length = dot(edge,edge)
        u = min(F(1),max(F(0),dot(sub(point,x),edge)/length)) if length else F(0)
        delta = sub(point,add(x,scale(edge,u)))
        values.append(dot(delta,delta))
    return min(values)


def mesh_point_squared(point, triangles):
    need(triangles, 'nonempty reference source')
    return min(point_triangle_squared(point,t['vertices']) for t in triangles)


def verify_path_box(source, value, lo, hi):
    box = bounds3(value)
    exact = path_range(source,lo,hi)
    need(all(a <= x <= y <= b for (a,b),(x,y) in zip(box,exact)),
         'all quadratic coordinate endpoints AND interior extrema enclosed')
    return box


def verify_window_space(source, window, stats):
    lo, hi = interval(window['timeBounds'])
    need(0 <= lo < hi <= fraction(source['horizon']), 'entry window uses global seconds')
    box = verify_path_box(source,window['pathBounds'],lo,hi)
    width_sum = sum(b-a for a,b in box)
    contains(window['l1DiameterBound'],width_sum)
    need(interval(window['l1DiameterBound'])[1] >= 0, 'spatial diameter upper is metres, not time width')
    stats['windowSpatialReferences'] += 4


def verify_derived_domain(source, result, stats):
    """Enclose the original physical input, not a rounded acceleration/chord."""
    exact_acceleration = acceleration(source)
    boxes = []
    need(result['acceleration'] is not None, 'valid raw input retains acceleration enclosure')
    contains3(result['acceleration'], exact_acceleration)
    boxes.append((bounds3(result['acceleration']), F(10**12)))
    h = fraction(source['horizon'])
    if result['wholePathBounds'] is not None:
        boxes.append((verify_path_box(source,result['wholePathBounds'],F(0),h), F(10**12)))
    if result['wholeVelocityBounds'] is not None:
        box = bounds3(result['wholeVelocityBounds'])
        velocity = vector(source['sphere']['velocity'])
        contains3(result['wholeVelocityBounds'],velocity)
        contains3(result['wholeVelocityBounds'],add(velocity,scale(exact_acceleration,h)))
        boxes.append((box,F(10**9)))
    stats['accelerationReferences'] += 3
    outside = any(a < -cap or b > cap for box,cap in boxes for a,b in box)
    if result['reason'] == 'derived_domain':
        need(result['status'] == 'not_certified' and outside,
             'derived-domain rejection has a published enclosure outside the stated domain')
        acceleration_outside=any(a < -10**12 or b > 10**12 for a,b in bounds3(result['acceleration']))
        need((result['wholePathBounds'] is None)==acceleration_outside
             and (result['wholeVelocityBounds'] is None)==acceleration_outside,
             'derived-domain diagnostics preserve the actual A-then-whole-bounds construction prefix')
        for key in ['initial','safePrefix','bestWitness','window','current','lastMesh','lastMeshAuditIndex']:
            need(result[key] is None,'derived-domain rejection before geometric '+key)
        need(not result['initialSeparationProven'] and not any(result[k] for k in
             ['certifiedLeaves','audits','candidateSurfaceIds']),
             'derived-domain rejection does not fabricate geometric work')
        verify_unqueried_root(source,result)
        need(result['maximumDepth'] == 0 and
             all(result['work'][k] == 0 for k in WORK_KEYS-{'workExact'}),'derived-domain no geometric work')
        stats['derivedDomainFailures'] += 1
        stats['notCertified'] += 1
        return True
    need(not outside and result['wholePathBounds'] is not None and result['wholeVelocityBounds'] is not None,
         'accepted derived acceleration/path/velocity enclosures all lie within their domains')
    return False


def verify_unqueried_root(source,result):
    need(result['partitionLeaves'] == len(result['partition']) == len(result['frontier']) == 1,
         'prequery domain/budget failure retains full unqueried root')
    leaf=result['partition'][0]
    fields(leaf,{'cell','state','auditIndex','blockedReason'},'prequery partition')
    expected=(F(0),fraction(source['horizon']),0)
    need(_cell(leaf['cell'],32) == _cell(result['frontier'][0],32) == expected and
         leaf['state']=='unqueried' and leaf['auditIndex'] is None and leaf['blockedReason']=='none',
         'root source/time ownership and unexecuted state')


def input_faults(source):
    fields(source, {'sphere','horizon','triangles','settings'}, 'held-load input')
    sphere, settings = source['sphere'],source['settings']
    fields(sphere, {'id','position','velocity','mass','force','gravity','radius'}, 'held sphere')
    fields(settings, SETTINGS_KEYS, 'held-load settings')
    fields(settings['mesh'], {'maxSurfaces','primitive'}, 'mesh settings')
    faults = set()
    profile = trajectory.mesh_reference.profile_valid(settings['mesh']['primitive'])
    ranges = [('maxEvaluations',1,256),('maxLeaves',1,128),('maxDepth',0,32),
              ('enclosureSqrtRefinements',1,256),('maxTotalSqrtRefinements',1,16777216)]
    if not (profile and type(settings['mesh']['maxSurfaces']) is int
            and 1 <= settings['mesh']['maxSurfaces'] <= 64
            and all(type(settings[k]) is int and a <= settings[k] <= b for k,a,b in ranges)
            and 0 < fraction(settings['timeTolerance']) <= fraction(.1)):
        faults.add(('settings',None))
    need(type(sphere['id']) is int,'integer sphere ID token')
    if not 1 <= sphere['id'] <= 2**53-1:
        faults.add(('input_domain',None))
    values = {k:vector(sphere[k]) for k in ['position','velocity','force','gravity']}
    if (not 0 < fraction(source['horizon']) <= fraction(.1)
        or not fraction(1e-12) <= fraction(sphere['mass']) <= fraction(1e18)
        or not 0 < fraction(sphere['radius']) <= 10**9
        or any(abs(v)>cap for k,cap in [('position',10**12),('velocity',10**9),('force',10**24),('gravity',10**9)] for v in values[k])):
        faults.add(('input_domain',None))
    triangles = source['triangles']
    need(type(triangles) is list and len(triangles)<=65,'finite fixture source array')
    if not 1 <= len(triangles) <= 64:
        faults.add(('surface_count',None))
    seen = set()
    for index,t in enumerate(triangles):
        fields(t,{'id','vertices'},'source triangle')
        need(type(t['id']) is int and type(t['vertices']) is list and len(t['vertices'])==3,'triangle ID/three vertices')
        if not 1 <= t['id'] <= 2**53-1:
            faults.add(('surface_id',index))
        if t['id'] in seen:
            faults.add(('duplicate_id',index))
        seen.add(t['id'])
        if any(abs(v)>10**12 for x in t['vertices'] for v in vector(x)):
            faults.add(('input_domain',index))
    return faults


def verify_audit_math(source, audit, lo, hi, midpoint, before, stats):
    """Audit a single returned proof object, independent of traversal policy."""
    fields(audit, AUDIT_KEYS, 'entry cell proof')
    need(F(0) <= lo <= midpoint <= hi <= fraction(source['horizon']), 'proof domain includes its exact midpoint')
    settings, triangles = source['settings'], source['triangles']
    count = len(triangles)
    radius = fraction(source['sphere']['radius'])
    need(fraction(audit['midpoint']) == midpoint, 'exact selected global time')
    delta = work(audit['work'])
    need(delta['workExact'] and delta['meshQueries'] in (0, 1)
         and type(audit['meshQueried']) is bool
         and delta['meshQueries'] == int(audit['meshQueried']), 'real per-proof mesh attempt')
    need(delta['enclosureSqrtCalls'] <= 2, 'at most R and E enclosure sqrt calls')
    box = point_box = anchor = None
    if audit['pathBounds'] is not None:
        box = verify_path_box(source,audit['pathBounds'],lo,hi)
        need(audit['pointBounds'] is not None and audit['anchor'] is not None, 'complete path/point/anchor proof')
        point_box = bounds3(audit['pointBounds'])
        contains3(audit['pointBounds'], path_point(source,midpoint))
        anchor = vector(audit['anchor'])
        need(all(abs(v) <= F(1e150) for v in anchor), 'anchor within reused primitive coordinate domain')
        stats['pathBoxReferences'] += 9
    else:
        need(audit['pointBounds'] is None and audit['anchor'] is None, 'no partial invented path proof')
    if audit['meshQueried']:
        need(anchor is not None and type(audit['meshStatus']) is int and audit['meshStatus'] in (0, 3)
             and type(audit['meshReason']) is int
             and audit['meshReason'] == (0 if audit['meshStatus'] == 0 else 7), 'ordinary actual mesh result')
        need(delta['primitiveQueries'] == count, 'all original surfaces queried')
        need(before['sqrtRefinements'] + count * 512 <= settings['maxTotalSqrtRefinements'], 'mesh block pre-reservation')
        need(before['meshQueries'] < settings['maxEvaluations'], 'initial and tree calls share evaluation budget')
        if audit['meshStatus'] == 0:
            need(delta['candidatesExamined'] == 7 * count and audit['distance'] is not None,
                 'completed mesh retains every candidate and distance')
            profile = settings['mesh']['primitive']
            need(profile['maxCandidates'] == 7, 'completed mesh has complete primitive candidate budget')
            distances = []
            for triangle in triangles:
                vertices = tuple(vector(v) for v in triangle['vertices'])
                edge0, edge1 = sub(vertices[1], vertices[0]), sub(vertices[2], vertices[0])
                cross = primitive.cross(edge0, edge1)
                area_squared = trajectory.dot(cross, cross)
                need(area_squared > 0, 'completed compact mesh audit cannot hide a degenerate source')
                sine_squared = area_squared / (trajectory.dot(edge0, edge0) * trajectory.dot(edge1, edge1))
                need(sine_squared >= fraction(profile['minimumSineSquared']), 'completed compact mesh audit has conditioning evidence')
                distance_squared = point_triangle_squared(anchor, vertices)
                need(distance_squared > 0, 'completed compact mesh audit has a defined normal for every source')
                distances.append(distance_squared)
            squared = min(distances)
            primitive.square_root_bounds(*interval(audit['distance']), squared)
            stats['certificateReferences'] += 1
        else:
            need(audit['distance'] is None, 'failed mesh does not fabricate distance')
    else:
        need(audit['meshStatus'] is None and audit['meshReason'] is None and audit['distance'] is None,
             'unexecuted proof never borrows a mesh result')
        need(all(delta[k] == 0 for k in ['primitiveQueries', 'candidatesExamined',
                                       'primitiveSqrtRefinements', 'meshSqrtLimitedRows']),
             'no unexecuted primitive work')
    roots = 0
    for squared_key, root_key, exact_box in [
            ('displacementSquaredBound', 'displacementRoot', box),
            ('errorSquaredBound', 'errorRoot', point_box)]:
        squared, root = audit[squared_key], audit[root_key]
        exact_squared = None
        if squared is not None:
            need(anchor is not None and audit['meshStatus'] == 0, 'norm proof has actual successful mesh input')
            exact_squared = trajectory.box_squared_range(exact_box, anchor)
            a, b = interval(squared)
            need(a <= exact_squared[0] and b >= exact_squared[1] and b >= 0, 'whole box squared norm enclosure')
            stats['squaredBoxReferences'] += 2
        if root is not None:
            need(squared is not None, 'root retains squared source')
            trajectory.verify_root(squared, root, exact_squared)
            need(before['sqrtRefinements'] + delta['primitiveSqrtRefinements'] + 512
                 <= settings['maxTotalSqrtRefinements'], 'enclosure block can be reserved before call')
            roots += 1
            stats['squaredBoxReferences'] += 1
    need(roots == delta['enclosureSqrtCalls'], 'real returned enclosure sqrt call count')
    need(delta['enclosureSqrtRefinements'] <= 2 * settings['enclosureSqrtRefinements'] * roots,
         'configured endpoint refinement budget')
    if audit['errorRoot'] is not None:
        need(audit['displacementRoot'] is not None, 'displacement root precedes error root')
    for key, sign in [('clearanceCertificate', -1), ('penetrationCertificate', 1)]:
        if audit[key] is not None:
            need(audit['distance'] is not None and audit['displacementRoot'] is not None
                 and audit['errorRoot'] is not None, 'certificate retains every source')
            distance = interval(audit['distance'])[0 if sign < 0 else 1]
            radius_bound = interval(audit['displacementRoot' if sign < 0 else 'errorRoot'])[1]
            contains(audit[key], distance + sign * radius_bound - radius)
            stats['certificateReferences'] += 1
    if audit['meshStatus'] == 0:
        need(audit['displacementSquaredBound'] is not None and audit['errorSquaredBound'] is not None,
             'finite successful mesh audit retains both constructed squared bounds')
    need((audit['clearanceCertificate'] is None) == (audit['penetrationCertificate'] is None),
         'ordinary returned certificate pair is complete or absent')
    need((audit['errorRoot'] is not None) == (audit['clearanceCertificate'] is not None),
         'ordinary finite completed roots retain the certificate pair')
    return delta


def _proof(entry):
    fields(entry, ENTRY_AUDIT_KEYS, 'entry audit')
    need(type(entry['kind']) is str and entry['kind'] in {'initial_point', 'cell'}, 'entry audit kind')
    need(type(entry['outcome']) is str and entry['outcome'] in OUTCOMES, 'entry audit outcome')
    proof = {k: v for k, v in entry.items() if k not in {'kind', 'time'}}
    proof['midpoint'] = entry['time']
    return proof


def _cell(value, maximum_depth, initial=False):
    fields(value, {'timeBounds', 'depth'}, 'held-load time cell')
    depth = uint(value['depth'], maximum_depth, 'cell depth')
    lo, hi = interval(value['timeBounds'])
    if initial:
        need(depth == 0 and lo == hi == 0, 'initial point alone is [0,0] depth0')
    else:
        need(0 <= lo < hi <= fraction(.1), 'positive global seconds cell')
    return lo, hi, value['depth']


def _eligible(partition, best):
    values = [v for v in partition if v['state'] == 'unqueried'
              and (best is None or v['cell'][0] < best[0])]
    return min(values, key=lambda v: (v['cell'][2], v['cell'][0])) if values else None


def verify(data):
    fields(data, {'schema', 'kind', 'fixtures'}, 'entry fixture envelope')
    need(type(data['schema']) is int and data['schema'] == 1
         and data['kind'] == 'sphere-triangle-mesh-held-load-fixtures', 'entry fixture kind')
    fixtures = data['fixtures']
    need(EXPECTED_FIXTURE_COUNT is not None and EXPECTED_INPUT_FINGERPRINT is not None, 'actual complete Native corpus not frozen yet')
    need(type(fixtures) is list and len(fixtures) == EXPECTED_FIXTURE_COUNT
         and 32 <= len(fixtures) <= 256, 'fixed complete entry fixture count')
    fingerprint = trajectory.input_fingerprint(fixtures)
    need(fingerprint == EXPECTED_INPUT_FINGERPRINT, 'fixed whole-input entry fingerprint')
    stats = {'fixtures': len(fixtures), 'entryWindows': 0, 'separated': 0,
             'initialPenetrations': 0, 'notCertified': 0, 'invalidInputs': 0,
             'wholePathReferences': 0, 'initialPointReferences': 0, 'prefixReferences': 0,
             'entryWidthReferences': 0, 'witnessReferences': 0, 'certifiedLeaves': 0,
             'positiveIslandsBeyondPrefix': 0, 'cellAudits': 0, 'pathBoxReferences': 0,
             'squaredBoxReferences': 0, 'certificateReferences': 0,
             'lastMeshReferenceComponents': 0, 'workExactFixtures': 0,'accelerationReferences':0,'windowSpatialReferences':0,'derivedDomainFailures':0}
    names = set()
    for fixture in fixtures:
        fields(fixture, {'name', 'input', 'result'}, 'entry fixture')
        need(type(fixture['name']) is str and fixture['name'] and fixture['name'] not in names, 'unique entry label')
        names.add(fixture['name'])
        verify_fixture(fixture['input'], fixture['result'], stats)
    need(all(stats[k] for k in ['entryWindows', 'separated', 'initialPenetrations',
                               'notCertified', 'invalidInputs']), 'finite entry status coverage')
    nonvacuity = verify_nonvacuity(fixtures)
    return {'status': 'PASS', **stats, 'inputFingerprint': fingerprint,
            'analyticAcceptance': nonvacuity,
            'scope': 'Exact Fraction g+F/m, full quadratic coordinate extrema, independent anchor/point triangle distance, squared R/E and issued Lipschitz certificates, seconds/space diagnostics and BFS/closed coverage. Not a general quartic minimum solver, instruction counter measurement, World advance or injected exceptional execution.'}


def verify_nonvacuity(fixtures):
    """Analytic requirements selected by physical coefficients, NEVER labels."""
    specs = [
        ('chordFalseSafe',(1,1,1),(0,-4,0),(0,4,0),F(1,4),'entry_window',F(1,4)),
        ('chordFalseCollision',(-2,F(1,8),1),(8,4,0),(0,-4,0),F(1,4),'separated',None),
        ('edgeQuartic',(1,F(3,4),-F(1,4)),(0,-3,0),(0,3,0),F(5,16),'entry_window',F(1,4)),
        ('vertexQuartic',(-F(3,16),3,-F(1,4)),(0,-12,0),(0,12,0),F(13,16),'entry_window',F(1,4)),
        ('irrationalMinimumSafe',(-1,-F(1,2),-1),(1,0,0),(0,1,0),F(1),'separated',None),
        ('irrationalMinimumEntry',(-1,-F(1,2),-1),(1,0,0),(0,1,0),F(17,16),'entry_window',None)]
    reference_vertices=(((0,0,0),(4,0,0),(0,0,4)),)
    accepted={}
    for name,p,v,q,r,status,root in specs:
        matches=[]
        for fixture in fixtures:
            source=fixture['input']
            if input_faults(source): continue
            h=fraction(source['horizon'])
            sphere=source['sphere']
            if (h==F(1,16) and tuple(tuple(vector(x) for x in t['vertices']) for t in source['triangles'])==reference_vertices
                and vector(sphere['position'])==tuple(p)
                and scale(vector(sphere['velocity']),h)==tuple(v)
                and scale(acceleration(source),h*h/2)==tuple(q)
                and fraction(sphere['radius'])==r and fixture['result']['status']==status):
                matches.append(fixture)
        need(matches,'required nonvacuous analytic '+name+' succeeds under actual finite profile')
        if root is not None:
            for fixture in matches:
                lo,hi=interval(fixture['result']['window']['timeBounds'])
                need(lo<root/16<hi,'independent exact first-entry H/4 lies strictly within returned seconds window')
        accepted[name]=len(matches)
    return accepted


def verify_fixture(source, result, stats):
    faults = input_faults(source)
    fields(result, RESULT_KEYS, 'entry result')
    need(type(result['status']) is str and result['status'] in STATUSES
         and type(result['reason']) is str and result['reason'] in REASONS, 'known entry classification')
    need(result['worldBody'] is None, 'raw corpus does not pretend to execute World adapter')
    need(result['status'] not in {'unsupported_environment', 'numerical_failure'},
         'finite ordinary corpus does not fabricate injected environment/allocator failures')
    if result['failedIndex'] is not None:
        uint(result['failedIndex'], len(source['triangles']) - 1, 'source failure index')
    need(type(result['initialSeparationProven']) is bool, 'initial separation boolean')
    for key in ['certifiedLeaves', 'partition', 'frontier', 'audits', 'candidateSurfaceIds']:
        need(type(result[key]) is list, 'owned entry array ' + key)
    uint(result['partitionLeaves'], 128, 'entry partition capacity')
    uint(result['maximumDepth'], 32, 'entry maximum depth')
    total = work(result['work'])
    need(total['workExact'], 'ordinary finite corpus retains exact returned work; exception execution not inferred')
    stats['workExactFixtures'] += 1
    if faults:
        need(result['status'] == 'invalid_input' and (result['reason'], result['failedIndex']) in faults,
             'actual full input prevalidation fault')
        for key in ['snapshot', 'acceleration','wholePathBounds','wholeVelocityBounds', 'initial', 'safePrefix', 'bestWitness', 'window',
                    'current', 'lastMesh', 'lastMeshAuditIndex']:
            need(result[key] is None, 'no invented preflight ' + key)
        need(not result['initialSeparationProven']
             and not any(result[k] for k in ['certifiedLeaves', 'partition', 'frontier', 'audits', 'candidateSurfaceIds']),
             'preflight has no proof or fabricated partial partition')
        need(result['partitionLeaves'] == result['maximumDepth'] == 0
             and all(total[k] == 0 for k in WORK_KEYS - {'workExact'}), 'preflight no model work')
        stats['invalidInputs'] += 1
        return
    need(result['failedIndex'] is None and result['status'] != 'invalid_input', 'valid source not falsely preflight rejected')
    source_equal({'input':source['sphere'],'horizon':source['horizon'],'triangles':source['triangles'],'settings':source['settings']},result['snapshot'])
    saved=result['snapshot']
    need(not input_faults({'sphere':saved['input'],'horizon':saved['horizon'],
                          'triangles':saved['triangles'],'settings':saved['settings']}),
         'owned snapshot also preserves integer metadata token types')
    if result['reason'] == 'surface_budget':
        need(all(result[k] is None for k in ['acceleration','wholePathBounds','wholeVelocityBounds']),
             'surface budget precedes derived calculations')
        _verify_entry(source,result,stats)
        return
    if verify_derived_domain(source,result,stats):
        return
    _verify_entry(source, result, stats)


def _verify_entry(source, result, stats):
    settings, triangles = source['settings'], source['triangles']
    count = len(triangles)
    audits = result['audits']
    need(len(audits) <= 256 and result['work']['meshQueries'] <= settings['maxEvaluations'],
         'initial plus tree share finite audit/evaluation budget')
    horizon = fraction(source['horizon'])
    root_cell = (F(0), horizon, 0)
    if count > settings['mesh']['maxSurfaces']:
        need(result['status'] == 'not_certified' and result['reason'] == 'surface_budget', 'caller mesh capacity retained')
        need(not audits and not result['certifiedLeaves'] and result['initial'] is None
             and not result['initialSeparationProven'] and result['safePrefix'] is None
             and result['bestWitness'] is None and result['window'] is None
             and not result['candidateSurfaceIds'] and result['current'] is None
             and result['lastMesh'] is None and result['lastMeshAuditIndex'] is None, 'surface budget has no path query')
        need(len(result['partition']) == len(result['frontier']) == result['partitionLeaves'] == 1,
             'surface budget keeps the complete unqueried root')
        p = result['partition'][0]
        fields(p, {'cell', 'state', 'auditIndex', 'blockedReason'}, 'surface budget partition')
        need(_cell(p['cell'], 32) == _cell(result['frontier'][0], 32) == root_cell
             and p['state'] == 'unqueried' and p['auditIndex'] is None and p['blockedReason'] == 'none',
             'surface-budget root is unexamined')
        need(result['maximumDepth'] == 0 and all(result['work'][k] == 0 for k in WORK_KEYS - {'workExact'}), 'surface budget zero actual work')
        stats['notCertified'] += 1
        return
    radius = fraction(source['sphere']['radius'])
    def exact(lo, hi):
        need(lo == hi, 'only exact point distances are requested; cell proof is independent Lipschitz audit')
        return mesh_point_squared(path_point(source, lo), triangles)
    stats['wholePathReferences'] += 1
    partition = [{'cell': root_cell, 'state': 'unqueried', 'auditIndex': None,
                  'blockedReasons': {'none'}}]
    sums = {k: 0 for k in WORK_KEYS - {'workExact'}}
    certified = []
    best = None  # Exact parameter and audit index, not a rounded anchor.
    last_returned = None
    maximum_depth = 0
    initial_positive = False
    for index, audit in enumerate(audits):
        proof = _proof(audit)
        initial = audit['kind'] == 'initial_point'
        need(initial == (index == 0), 'exactly the first audit is initial point')
        if initial:
            current = _cell(audit['cell'], 0, True)
            lo = hi = parameter = F(0)
        else:
            need(initial_positive, 'no tree query before strict initial separation')
            selected = _eligible(partition, best)
            need(selected is not None, 'no query outside eligible frontier')
            current = _cell(audit['cell'], settings['maxDepth'])
            need(current == selected['cell'], 'lowest-depth then leftmost eligible dyadic leaf')
            lo, hi, depth = current
            maximum_depth = max(maximum_depth, depth)
            parameter = fraction(audit['time'])
            if not lo < parameter < hi:
                need(result['reason']=='time_resolution' and index==len(audits)-1
                     and lo <= parameter <= hi and fraction(math.nextafter(float(lo),float(hi))) >= hi,
                     'only a final resolution stop may lack a representable interior')
        delta = verify_audit_math(source, proof, lo, hi, parameter, sums, stats)
        if audit['meshQueried']:
            last_returned = index
        complete = audit['clearanceCertificate'] is not None and audit['penetrationCertificate'] is not None
        positive = complete and interval(audit['clearanceCertificate'])[0] > 0
        negative = complete and interval(audit['penetrationCertificate'])[1] < 0
        need(not (positive and negative), 'sound lower and upper certificates cannot contradict')
        if positive:
            need(audit['meshStatus'] == 0, 'whole-cell proof uses audited exact anchor distance and R')
        if negative:
            need(exact(parameter, parameter) < radius * radius, 'exact global-path negative witness')
        if initial:
            expected_outcome = ('initial_separated' if positive else 'initial_penetration' if negative
                                else 'initial_uncertain' if complete else 'unresolved')
            need(audit['outcome'] == expected_outcome, 'initial point outcome from strict real certificates')
            initial_positive = bool(positive)
            if not initial_positive:
                need(len(audits) == 1, 'uncertain/negative initial point stops tree work')
                if not complete:
                    need(result['reason'] == ('mesh_query_failed' if audit['meshStatus'] == 3 else 'sqrt_budget'),
                         'incomplete ordinary initial proof keeps its actual failure stage')
        else:
            if negative and (best is None or parameter < best[0]):
                best = parameter, index
            if positive:
                need(audit['outcome'] == 'separated', 'positive full cell becomes a certified leaf')
                selected.update({'state': 'certified', 'auditIndex': index, 'blockedReasons': {'none'}})
                certified.append((current, index))
            elif audit['outcome'] == 'split':
                need(complete or audit['meshStatus']==3,
                     'split requires a returned complete proof or recoverable exact-work row failure')
                need(current[2] < settings['maxDepth'] and len(partition) < settings['maxLeaves'],
                     'split obeys original profile and full-partition capacity')
                position = partition.index(selected)
                partition[position:position + 1] = [
                    {'cell': (lo, parameter, current[2] + 1), 'state': 'unqueried', 'auditIndex': None, 'blockedReasons': {'none'}},
                    {'cell': (parameter, hi, current[2] + 1), 'state': 'unqueried', 'auditIndex': None, 'blockedReasons': {'none'}}]
            else:
                need(audit['outcome'] == 'unresolved', 'nonpositive stopped cell remains unresolved')
                fatal = audit['meshStatus'] != 3 and not complete
                reasons = set()
                if current[2] == settings['maxDepth']:
                    reasons.add('depth_budget')
                if len(partition) == settings['maxLeaves']:
                    reasons.add('leaf_budget')
                if result['status'] == 'entry_window' and index == len(audits) - 1:
                    reasons.add('none')
                if fatal:
                    need(result['reason'] in {'sqrt_budget','time_resolution'}, 'ordinary incomplete cell retains its actual pre-call stage')
                    reasons.add(result['reason'])
                    need(index == len(audits) - 1, 'global incomplete proof stops further execution')
                need(reasons, 'unresolved leaf must retain a real blocking reason or accepted window')
                selected.update({'state': 'current' if fatal else 'unresolved',
                                 'auditIndex': index, 'blockedReasons': reasons})
        for key in sums:
            sums[key] += delta[key]
        need(sums['sqrtRefinementsUpper'] <= settings['maxTotalSqrtRefinements'], 'hard shared sqrt upper')
    need(all(result['work'][k] == v for k, v in sums.items()), 'global returned work is sum of every initial/cell DELTA')
    # A pre-query evaluation stop has a real current leaf, but no invented audit.
    if result['current'] is not None:
        is_initial_current = result['current']['timeBounds'] == [0, 0]
        current = _cell(result['current'], settings['maxDepth'], is_initial_current)
        if is_initial_current:
            need(not initial_positive and len(audits) == 1, 'initial current belongs only to stopped point audit')
        else:
            part = next((v for v in partition if v['cell'] == current), None)
            need(part is not None, 'current cell remains in the full partition')
            maximum_depth = max(maximum_depth, current[2])
            if part['state'] == 'unqueried':
                need(part is _eligible(partition, best) and result['reason'] == 'evaluation_budget'
                     and sums['meshQueries'] == settings['maxEvaluations'], 'evaluation budget stops before the next eligible query')
                part.update({'state': 'current', 'auditIndex': None, 'blockedReasons': {'evaluation_budget'}})
            else:
                need(part['state'] == 'current', 'current never aliases a finished certified/island leaf')
    need(len(partition) == result['partitionLeaves'] <= settings['maxLeaves']
         and len(result['partition']) == len(partition), 'complete bounded partition retained')
    for expected, actual in zip(partition, result['partition']):
        fields(actual, {'cell', 'state', 'auditIndex', 'blockedReason'}, 'entry partition leaf')
        need(_cell(actual['cell'], settings['maxDepth']) == expected['cell']
             and type(actual['state']) is str and actual['state'] == expected['state']
             and type(actual['blockedReason']) is str and actual['blockedReason'] in expected['blockedReasons'],
             'partition state/reason follows its own actual audit')
        need(type(actual['auditIndex']) is type(expected['auditIndex']) and actual['auditIndex'] == expected['auditIndex'],
             'partition audit owner index')
    cells = [v['cell'] for v in partition]
    need(cells[0][0] == 0 and cells[-1][1] == horizon
         and all(a[1] == b[0] for a, b in zip(cells, cells[1:])), 'closed full partition has no missing tail or hole')
    expected_frontier = [v['cell'] for v in partition if v['state'] == 'unqueried']
    need([_cell(v, settings['maxDepth']) for v in result['frontier']] == expected_frontier,
         'frontier is all unqueried leaves including retained witness tail')
    need(result['maximumDepth'] == maximum_depth, 'maximum depth includes popped blocked current')
    certified.sort(key=lambda v: v[0][0])
    need(len(result['certifiedLeaves']) == len(certified), 'all positive islands retained, not just prefix')
    for leaf, (proof_cell, audit_index) in zip(result['certifiedLeaves'], certified):
        fields(leaf, {'cell', 'lowerGapCertificate', 'auditIndex'}, 'entry certified island')
        uint(leaf['auditIndex'], len(audits) - 1, 'certified leaf audit index')
        need(_cell(leaf['cell'], settings['maxDepth']) == proof_cell and leaf['auditIndex'] == audit_index,
             'certified leaf links to its real full-domain proof')
        source_equal(leaf['lowerGapCertificate'], audits[audit_index]['clearanceCertificate'])
    prefix_hi = F(0)
    for leaf in partition:
        if leaf['state'] != 'certified':
            break
        need(leaf['cell'][0] == prefix_hi, 'prefix begins at zero with exact closed boundaries')
        prefix_hi = leaf['cell'][1]
    need(result['initialSeparationProven'] == initial_positive, 'initial proof flag is not inferred from later cells')
    if initial_positive:
        source_equal(result['safePrefix'], [0, float(prefix_hi)])
        need(all(p['state'] == 'certified' for p in partition if p['cell'][0] < prefix_hi), 'audited certified cells cover entire CLOSED safe prefix')
        stats['prefixReferences'] += 1
    else:
        need(result['safePrefix'] is None, 'no strict initial proof means no invented prefix')
    _verify_initial(source, result, audits, exact, radius, stats)
    _verify_witness(source, result, audits, best, exact, radius, stats)
    if last_returned is None:
        need(result['lastMesh'] is None and result['lastMeshAuditIndex'] is None, 'no unexecuted last mesh')
    else:
        uint(result['lastMeshAuditIndex'], len(audits) - 1, 'last mesh audit index')
        need(result['lastMeshAuditIndex'] == last_returned and result['lastMesh'] is not None, 'last real returned mesh audit owner')
        last, a = result['lastMesh'], audits[last_returned]
        need(type(last['status']) is int and type(last['reason']) is int
             and last['status'] == a['meshStatus'] and last['reason'] == a['meshReason'], 'mesh status/reason audit link')
        for k, other in [('queries', 'primitiveQueries'), ('candidatesExamined', 'candidatesExamined'),
                         ('sqrtRefinements', 'primitiveSqrtRefinements'), ('sqrtLimitedRows', 'meshSqrtLimitedRows')]:
            need(last[k] == a['work'][other], 'last mesh has the corresponding cell work')
        source_equal(last['nearest']['distance'] if last['nearest'] is not None else None, a['distance'])
        mesh_source={'radius':source['sphere']['radius'],'triangles':triangles,'settings':settings}
        stats['lastMeshReferenceComponents'] += trajectory.verify_mesh_result(mesh_source, a['anchor'], last)
    status, reason = result['status'], result['reason']
    if status == 'entry_window':
        window = result['window']
        fields(window, {'timeBounds', 'timeWidth', 'pathBounds', 'l1DiameterBound', 'witnessAuditIndex'}, 'entry window')
        need(initial_positive and best is not None and reason == 'none', 'entry requires initial and negative exact-path proofs')
        source_equal(window['timeBounds'], [float(prefix_hi), float(best[0])])
        need(type(window['witnessAuditIndex']) is int and window['witnessAuditIndex'] == best[1], 'window links to best witness')
        verify_width(window['timeWidth'], prefix_hi, best[0], settings['timeTolerance'])
        need(exact(F(0), F(0)) > radius*radius and exact(best[0], best[0]) < radius*radius, 'initial outside plus closed certificate prefix plus exact negative point')
        verify_window_space(source, window, stats)
        need(all(type(identifier) is int for identifier in result['candidateSurfaceIds'])
             and result['candidateSurfaceIds'] == sorted(t['id'] for t in triangles), 'all original IDs retained as conservative window candidates')
        stats['entryWindows'] += 1
        stats['entryWidthReferences'] += 1
    else:
        need(result['window'] is None and not result['candidateSurfaceIds'], 'no invented window or narrowed candidate set')
        if status == 'separated':
            need(initial_positive and reason == 'none' and prefix_hi == horizon and best is None
                 and result['current'] is None and not result['frontier']
                 and all(p['state'] == 'certified' for p in partition), 'whole path strict separation, no remaining unknown tail')
            stats['separated'] += 1
        elif status == 'initial_penetration':
            need(not initial_positive and reason == 'none' and len(audits) == 1
                 and audits[0]['outcome'] == 'initial_penetration'
                 and result['current'] is None
                 and exact(F(0), F(0)) < radius * radius, 'initial negative is not an entry window')
            stats['initialPenetrations'] += 1
        else:
            need(status == 'not_certified' and reason in {'mesh_query_failed', 'initial_boundary', 'evaluation_budget',
                 'leaf_budget', 'depth_budget', 'sqrt_budget', 'time_resolution'}, 'ordinary stopping reason')
            _verify_stopping(source, result, partition, sums)
            stats['notCertified'] += 1
    stats['cellAudits'] += len(audits)
    stats['certifiedLeaves'] += len(certified)
    stats['positiveIslandsBeyondPrefix'] += sum(lo > prefix_hi for (lo, hi, depth), _ in certified)


def _verify_initial(source, result, audits, exact, radius, stats):
    need(audits, 'ordinary valid initial input gets its own bounded proof attempt')
    audit = audits[0]
    complete = audit['clearanceCertificate'] is not None and audit['penetrationCertificate'] is not None
    initial = result['initial']
    if not complete:
        need(initial is None, 'incomplete initial proof has no fabricated certificates')
    else:
        fields(initial, {'lowerGapCertificate', 'upperGapCertificate', 'auditIndex'}, 'initial point proof')
        need(type(initial['auditIndex']) is int and initial['auditIndex'] == 0, 'initial proof belongs to initial audit0')
        source_equal(initial['lowerGapCertificate'], audit['clearanceCertificate'])
        source_equal(initial['upperGapCertificate'], audit['penetrationCertificate'])
        if result['initialSeparationProven']:
            need(interval(initial['lowerGapCertificate'])[0] > 0 and exact(F(0), F(0)) > radius * radius,
                 'initial strict positive gap proof')
        if result['status'] == 'initial_penetration':
            need(interval(initial['upperGapCertificate'])[1] < 0, 'initial strict negative expression')
    stats['initialPointReferences'] += 1


def _verify_witness(source, result, audits, best, exact, radius, stats):
    witness = result['bestWitness']
    if best is None:
        need(witness is None, 'no invented negative point witness')
        return
    fields(witness, {'cell', 'time', 'exactPathBounds', 'anchor', 'errorUpper',
                     'upperGapCertificate', 'auditIndex'}, 'best exact-path witness')
    need(type(witness['auditIndex']) is int and witness['auditIndex'] == best[1], 'smallest negative parameter uses its own audit')
    audit = audits[best[1]]
    for left, right in [('cell', 'cell'), ('time', 'time'), ('exactPathBounds', 'pointBounds'),
                        ('anchor', 'anchor'), ('upperGapCertificate', 'penetrationCertificate')]:
        source_equal(witness[left], audit[right])
    source_equal(witness['errorUpper'], audit['errorRoot'][1])
    contains3(witness['exactPathBounds'], path_point(source, best[0]))
    need(interval(witness['upperGapCertificate'])[1] < 0 and exact(best[0], best[0]) < radius * radius,
         'negative witness includes E and is on original exact path')
    stats['witnessReferences'] += 1


def _verify_stopping(source, result, partition, sums):
    reason, settings = result['reason'], source['settings']
    if reason == 'initial_boundary':
        need(not result['initialSeparationProven'] and result['initial'] is not None
             and interval(result['initial']['lowerGapCertificate'])[0] <= 0
             and interval(result['initial']['upperGapCertificate'])[1] >= 0, 'initial uncertainty remains explicit')
    elif reason == 'evaluation_budget':
        need(sums['meshQueries'] == settings['maxEvaluations'], 'shared initial/tree evaluation budget exhausted')
    elif reason == 'depth_budget':
        need(any(v['state'] == 'unresolved' and v['cell'][2] == settings['maxDepth'] for v in partition), 'real depth-blocked unresolved cell')
    elif reason == 'leaf_budget':
        need(len(partition) == settings['maxLeaves'] and any(v['state'] == 'unresolved' for v in partition), 'real full-partition leaf exhaustion')
    elif reason == 'mesh_query_failed':
        need(not result['initialSeparationProven'] and result['audits'][0]['meshStatus'] == 3, 'initial actual mesh failure cannot prove positive start')
    elif reason == 'sqrt_budget':
        need(result['audits'], 'sqrt reservation retained its attempted proof')
        a = result['audits'][-1]
        before = sums['sqrtRefinements'] - a['work']['sqrtRefinements']
        if not a['meshQueried']:
            need(before + 512 * len(source['triangles']) > settings['maxTotalSqrtRefinements'], 'mesh reservation genuinely unavailable')
        else:
            need(a['meshStatus'] == 0 and a['errorRoot'] is None, 'norm reservation blocked before completing the next root')
            need(before + a['work']['primitiveSqrtRefinements'] + a['work']['enclosureSqrtRefinements'] + 512
                 > settings['maxTotalSqrtRefinements'], 'next enclosure block genuinely unavailable')
    elif reason == 'time_resolution':
        need(result['current'] is not None and result['audits'], 'resolution stop retains current attempted cell')
        audit=result['audits'][-1]
        lo,hi,_=_cell(result['current'],settings['maxDepth'])
        need(fraction(math.nextafter(float(lo),float(hi))) >= hi and audit['kind']=='cell'
             and not audit['meshQueried'] and audit['pathBounds'] is None,
             'no representable interior and no invented geometric query')
    else:
        need(False, 'unsupported ordinary stopping branch')
    if reason in {'depth_budget', 'leaf_budget'}:
        witness = result['bestWitness']
        best = (fraction(witness['time']), witness['auditIndex']) if witness is not None else None
        need(_eligible(partition, best) is None, 'blocked earlier leaves do not prevent later eligible witness exploration')
        blocked = next((p['blockedReason'] for p in result['partition']
                        if p['state'] == 'unresolved' and p['blockedReason'] != 'none'), None)
        need(blocked == reason, 'exhausted search reports the first unresolved blocking reason')


if __name__ == '__main__':
    need(__debug__, 'run entry reference checker without Python -O')
    need(len(sys.argv) == 2, 'Usage: python check-sphere-triangle-mesh-held-load.py fixtures.json')
    print(json.dumps(verify(load(sys.argv[1])), indent=2))
