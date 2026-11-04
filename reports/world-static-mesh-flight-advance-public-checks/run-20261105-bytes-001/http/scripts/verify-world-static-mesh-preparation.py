"""Independent owned-source and complete typed-pair preparation audit.

This checker does not calculate a contact, a trajectory, a propagated candidate,
or a separation certificate. Preparation is a finite combinatorial/ownership
contract; every required pair is rebuilt from the original collider arrays.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

# Fixed complete finite Native corpus; labels and fixture traversal order are
# excluded, while every original field/array ordinal and signed zero is pinned.
EXPECTED_FIXTURE_COUNT = 84
EXPECTED_INPUT_FINGERPRINT = '4bfee81b01fcbfe5d7539c3960f35e467fa08db3d8bdfe5dc6badb9fc5853d4c'
MAX_BYTES = 64 * 1024 * 1024
MAX_ID = 2**53-1
BODY_KEYS = {'id', 'isStatic', 'mass', 'inertiaDiagonal', 'radius', 'position',
             'velocity', 'angularMomentum', 'force', 'torque', 'orientation', 'material'}
PLANE_KEYS = {'id', 'normal', 'offset', 'material'}
SETTING_CAPS = {'maxBodies':8, 'maxPlanes':16, 'maxMeshes':4,
                'maxTotalFaces':64, 'maxPairs':256}
INPUT_KEYS = {'bodies', 'planes', 'gravity', 'meshes', 'horizon', 'settings'}
RESULT_KEYS = {'status', 'reason', 'failure', 'capture', 'snapshot', 'inventory'}
EXCLUDED_KEYS = {'bodyBody', 'bodyPlane', 'bodyMesh', 'planePlane', 'planeMesh', 'meshMesh', 'total'}


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def fields(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), label+' exact fields')


def uint(value, maximum=MAX_ID, label='unsigned integer'):
    need(type(value) is int and 0 <= value <= maximum, label)
    return value


def number(value):
    need(type(value) in (int, float), 'finite binary64 number, not boolean')
    try:
        result = float(value)
    except OverflowError:
        need(False, 'finite binary64 number')
    need(math.isfinite(result), 'finite binary64 number')
    return result


def bits(value):
    return struct.pack('>d', number(value))


def source_equal(left, right):
    """All fields and array ordinals, with binary64 signed zero preserved."""
    if type(left) in (int, float):
        need(type(right) in (int, float) and bits(left) == bits(right), 'original binary64 bits')
        if type(left) is type(right) is int:
            need(left == right, 'original uint64 integer value beyond binary64 safe domain')
    elif type(left) is dict:
        fields(right, left, 'owned object')
        for key in left:
            source_equal(left[key], right[key])
    elif type(left) is list:
        need(type(right) is list and len(left) == len(right), 'owned array length/order')
        for a, b in zip(left, right):
            source_equal(a, b)
    else:
        need(type(left) is type(right) and left == right, 'owned scalar type/value')


def loads(content):
    if type(content) is bytes:
        need(len(content) <= MAX_BYTES, 'bounded fixture bytes')
        content = content.decode('utf-8', errors='strict')
    need(type(content) is str and len(content.encode('utf-8', errors='strict')) <= MAX_BYTES,
         'bounded UTF8 fixture bytes')

    def floating(token):
        value = float(token)
        mantissa = token.lower().split('e')[0]
        need(math.isfinite(value) and not (value == 0 and any(c in '123456789' for c in mantissa)),
             'finite non-underflowing JSON number')
        return value

    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    value = json.loads(content, parse_float=floating,
                       parse_int=lambda token: -0.0 if token == '-0' else int(token),
                       parse_constant=lambda _: need(False, 'nonfinite JSON number'),
                       object_pairs_hook=pairs)
    count = 0

    def visit(item, depth=0):
        nonlocal count
        count += 1
        need(count <= 2000000 and depth <= 40, 'bounded JSON nodes/depth')
        if type(item) is str:
            item.encode('utf-8', errors='strict')
        elif type(item) is dict:
            for key, child in item.items():
                key.encode('utf-8', errors='strict')
                visit(child, depth+1)
        elif type(item) is list:
            for child in item:
                visit(child, depth+1)
        elif type(item) in (int, float):
            number(item)
    visit(value)
    return value


def load(path):
    return loads(Path(path).read_bytes())


def input_fingerprint(fixtures):
    def encode(value):
        if type(value) is dict:
            return '{'+','.join(json.dumps(k)+':'+encode(value[k]) for k in sorted(value))+'}'
        if type(value) is list:
            return '['+','.join(encode(v) for v in value)+']'
        if type(value) is bool:
            return 'boolean:'+str(value)
        if type(value) is int:
            return 'integer:'+str(value)
        if type(value) is float:
            return 'binary64:'+bits(value).hex()
        if value is None:
            return 'null'
        if type(value) is str:
            return 'string:'+json.dumps(value, ensure_ascii=True)
        need(False, 'fingerprint scalar shape')
    # Labels and fixture traversal order are not the mathematical input. Each
    # source array's order, scalar type and every signed-zero bit remain fixed.
    rows = sorted(encode(f['input']) for f in fixtures)
    return hashlib.sha256(('\n'.join(rows)+'\n').encode()).hexdigest()


def vector(value, size=3):
    need(type(value) is list and len(value) == size, 'dense numeric vector')
    return tuple(number(v) for v in value)


def bounded_vector(value, bound):
    return all(abs(v) <= bound for v in vector(value))


def material_valid(value):
    fields(value, {'restitution', 'friction'}, 'material')
    return 0 <= number(value['restitution']) <= 1 and 0 <= number(value['friction']) <= 10


def choose2(count):
    uint(count, 1000000, 'finite combinatorial count')
    return count*(count-1)//2


def squared_norm_rn(values):
    # Field validation uses the declared RN binary64 norm, not an exact unit
    # normal or a normalization of the stored raw source. This is not geometry.
    values = [number(v) for v in values]
    need(values, 'nonempty norm')
    total = values[0]*values[0]
    for v in values[1:]:
        total = total+v*v
    return total


def body_shape(value):
    fields(value, BODY_KEYS, 'whole rigid body')
    uint(value['id'], 2**64-1, 'body ID metadata')
    need(type(value['isStatic']) is bool, 'static body flag')
    for key in ('position', 'velocity', 'angularMomentum', 'force', 'torque', 'inertiaDiagonal'):
        vector(value[key])
    vector(value['orientation'], 4)
    for key in ('mass', 'radius'):
        number(value[key])
    material_valid(value['material'])


def body_valid(value):
    body_shape(value)
    if not (1 <= value['id'] <= MAX_ID and 1e-12 <= number(value['mass']) <= 1e18
            and 0 < number(value['radius']) <= 1e9 and material_valid(value['material'])):
        return False
    for key, cap in [('position',1e12), ('velocity',1e9), ('angularMomentum',1e24),
                     ('force',1e24), ('torque',1e24)]:
        if not bounded_vector(value[key], cap):
            return False
    inertia = vector(value['inertiaDiagonal'])
    if not all(1e-12 <= x <= 1e18 for x in inertia):
        return False
    if not all(inertia[a]+inertia[b] >= inertia[c] for a,b,c in [(0,1,2),(0,2,1),(1,2,0)]):
        return False
    q2 = squared_norm_rn(value['orientation'])
    if not (math.isfinite(q2) and abs(q2-1) < 1e-8):
        return False
    # Given the preceding finite caps, rotation of L with q2 near one and
    # division by principal inertia >=1e-12 cannot overflow kinetic energy.
    return not value['isStatic'] or (squared_norm_rn(value['velocity']) == 0
                                     and squared_norm_rn(value['angularMomentum']) == 0)


def plane_shape(value):
    fields(value, PLANE_KEYS, 'whole raw plane')
    uint(value['id'], 2**64-1, 'plane ID metadata')
    vector(value['normal'])
    number(value['offset'])
    material_valid(value['material'])


def plane_valid(value):
    plane_shape(value)
    q2 = squared_norm_rn(value['normal'])
    return (1 <= value['id'] <= MAX_ID and math.isfinite(q2) and abs(q2-1) < 1e-8
            and abs(number(value['offset'])) <= 1e12 and material_valid(value['material']))


def input_shape(source):
    fields(source, INPUT_KEYS, 'original World input')
    fields(source['settings'], SETTING_CAPS, 'preparation profile')
    for key in SETTING_CAPS:
        uint(source['settings'][key], 2**64-1, 'profile integer '+key)
    vector(source['gravity'])
    number(source['horizon'])
    for key, maximum in [('bodies',1024), ('planes',64), ('meshes',65)]:
        need(type(source[key]) is list and len(source[key]) <= maximum, 'bounded input '+key)
    for body in source['bodies']:
        body_shape(body)
    for plane in source['planes']:
        plane_shape(plane)
    for mesh in source['meshes']:
        fields(mesh, {'id','revision','triangles'}, 'owned static mesh source')
        uint(mesh['id'], 2**64-1, 'mesh ID metadata')
        uint(mesh['revision'], 2**64-1, 'mesh revision metadata')
        need(type(mesh['triangles']) is list and len(mesh['triangles']) <= 4096, 'bounded face source')
        for triangle in mesh['triangles']:
            fields(triangle, {'id','vertices'}, 'whole triangle source')
            uint(triangle['id'], 2**64-1, 'face ID metadata')
            need(type(triangle['vertices']) is list and len(triangle['vertices']) == 3, 'three triangle vertices')
            for point in triangle['vertices']:
                vector(point)


def ref(kind, value, ordinal):
    return {'kind':kind, 'id':value['id'], 'ordinal':ordinal,
            'revision':value['revision'] if kind == 'mesh' else 0}


def expected_inventory(source):
    """Enumerate *all* unordered collider combinations independently.

    This deliberately does not duplicate the kernel's three required nested
    loops. A six-way static exclusion classification closes every collider pair.
    """
    refs = []
    for kind, key in [('body','bodies'), ('plane','planes'), ('mesh','meshes')]:
        refs.extend((ref(kind,v,i), v.get('isStatic',True)) for i,v in enumerate(source[key]))
    excluded = dict.fromkeys(EXCLUDED_KEYS, 0)
    pairs = []
    kind_rank = {'body_mesh':0,'body_plane':1,'body_body':2}
    static_names = {('body','body'):'bodyBody', ('body','plane'):'bodyPlane',
                    ('body','mesh'):'bodyMesh', ('plane','plane'):'planePlane',
                    ('plane','mesh'):'planeMesh', ('mesh','mesh'):'meshMesh'}
    for i, (left, left_static) in enumerate(refs):
        for right, right_static in refs[i+1:]:
            if left_static and right_static:
                excluded[static_names[left['kind'],right['kind']]] += 1
                excluded['total'] += 1
                continue
            need(left['kind'] == 'body', 'dynamic collider must be body')
            kind = 'body_'+right['kind']
            first, second = left, right
            if right['kind'] == 'body' and right['id'] < left['id']:
                first, second = right, left
            pairs.append({'kind':kind, 'first':first, 'second':second})
    pairs.sort(key=lambda p:(min(p['first']['id'],p['second']['id']),
                             max(p['first']['id'],p['second']['id']),kind_rank[p['kind']]))
    dynamic = sum(not b['isStatic'] for b in source['bodies'])
    static = len(source['bodies'])-dynamic
    expected_count = dynamic*(len(source['meshes'])+len(source['planes']))+choose2(len(source['bodies']))-choose2(static)
    need(len(pairs) == expected_count and len(pairs)+excluded['total'] == choose2(len(refs)),
         'complete finite collider pair partition')
    return {'dynamicBodies':dynamic, 'staticBodies':static,
            'totalFaces':sum(len(m['triangles']) for m in source['meshes']),
            'colliders':len(refs), 'allPairs':choose2(len(refs)), 'excluded':excluded, 'pairs':pairs}


def failure(kind, index=None, face_index=None):
    return {'kind':kind, 'index':index, 'faceIndex':face_index}


def expected_preflight(source):
    """Independent finite-domain contract, before any pair inventory exists."""
    input_shape(source)
    b, p, m = (len(source[k]) for k in ('bodies','planes','meshes'))
    faces = sum(len(mesh['triangles']) for mesh in source['meshes'])
    def first_face_overflow(cap):
        total = 0
        for ordinal, mesh in enumerate(source['meshes']):
            total += len(mesh['triangles'])
            if total > cap:
                return ordinal
        need(False, 'a face overflow must have an original source ordinal')
    for reason, bad, where in [('body_count',b>8,failure('body',8)),
                               ('plane_count',p>16,failure('plane',16)),
                               ('mesh_count',not 1<=m<=4,failure('mesh',4 if m>4 else None))]:
        if bad:
            return 'invalid_input', reason, where, 'none'
    if faces > 64:
        return 'invalid_input', 'total_face_count', failure('mesh',first_face_overflow(64)), 'none'
    settings = source['settings']
    if any(not (int(key!='maxPlanes') <= settings[key] <= cap) for key,cap in SETTING_CAPS.items()):
        return 'invalid_input', 'settings', failure('settings'), 'complete'
    if not 0 < number(source['horizon']) <= .1:
        return 'invalid_input', 'horizon', failure('world'), 'complete'
    if not bounded_vector(source['gravity'], 1e9):
        return 'invalid_input', 'gravity', failure('world'), 'complete'
    seen = set()
    for kind, key in [('body','bodies'), ('plane','planes'), ('mesh','meshes')]:
        for ordinal, value in enumerate(source[key]):
            location = failure(kind, ordinal)
            identifier = value['id']
            if not 1 <= identifier <= MAX_ID:
                return 'invalid_input', 'collider_id', location, 'complete'
            if identifier in seen:
                return 'invalid_input', 'duplicate_collider_id', location, 'complete'
            seen.add(identifier)
            if kind == 'body' and not body_valid(value):
                return 'invalid_input', 'body_invalid', location, 'complete'
            if kind == 'plane' and not plane_valid(value):
                return 'invalid_input', 'plane_invalid', location, 'complete'
            if kind != 'mesh':
                continue
            if not 1 <= value['revision'] <= MAX_ID:
                return 'invalid_input', 'mesh_revision', location, 'complete'
            if not 1 <= len(value['triangles']) <= 64:
                return 'invalid_input', 'mesh_face_count', location, 'complete'
            ids = set()
            for face, triangle in enumerate(value['triangles']):
                location = failure('face', ordinal, face)
                if not 1 <= triangle['id'] <= MAX_ID:
                    return 'invalid_input', 'face_id', location, 'complete'
                if triangle['id'] in ids:
                    return 'invalid_input', 'duplicate_face_id', location, 'complete'
                ids.add(triangle['id'])
                if not all(bounded_vector(v, 1e12) for v in triangle['vertices']):
                    return 'invalid_input', 'vertex_domain', location, 'complete'
    for reason, count, key, kind in [('body_budget',b,'maxBodies','body'), ('plane_budget',p,'maxPlanes','plane'),
                                     ('mesh_budget',m,'maxMeshes','mesh')]:
        if count > settings[key]:
            return 'budget_exceeded', reason, failure(kind,settings[key]), 'complete'
    if faces > settings['maxTotalFaces']:
        return 'budget_exceeded', 'face_budget', failure('mesh',first_face_overflow(settings['maxTotalFaces'])), 'complete'
    if len(expected_inventory(source)['pairs']) > settings['maxPairs']:
        return 'budget_exceeded', 'pair_budget', failure('settings'), 'complete'
    return 'ready', 'none', None, 'complete'


def inventory_shape(value):
    fields(value, {'dynamicBodies','staticBodies','totalFaces','colliders','allPairs','excluded','pairs'}, 'prepared inventory')
    for key in ('dynamicBodies','staticBodies','totalFaces','colliders','allPairs'):
        uint(value[key], 378, 'inventory integer '+key)
    fields(value['excluded'], EXCLUDED_KEYS, 'six static-only classifications')
    for count in value['excluded'].values():
        uint(count, 378, 'excluded pair count')
    need(type(value['pairs']) is list and len(value['pairs']) <= 256, 'complete bounded pair list')
    for pair in value['pairs']:
        fields(pair, {'kind','first','second'}, 'typed pair')
        need(type(pair['kind']) is str and pair['kind'] in {'body_mesh','body_plane','body_body'}, 'pair kind enum')
        for key in ('first','second'):
            collider = pair[key]
            fields(collider, {'kind','id','ordinal','revision'}, 'owned collider link')
            need(type(collider['kind']) is str and collider['kind'] in {'body','plane','mesh'}, 'collider kind enum')
            uint(collider['id'], label='stable collider ID')
            uint(collider['ordinal'], 63, 'source ordinal')
            uint(collider['revision'], label='declared revision')


def verify_fixture(source, result, stats):
    expected_status, reason, location, capture = expected_preflight(source)
    fields(result, RESULT_KEYS, 'preparation result with no numerical certificate')
    need(type(result['status']) is str and result['status'] == expected_status, 'preparation status from whole input')
    need(type(result['reason']) is str and result['reason'] == reason, 'first preflight reason')
    need(type(result['capture']) is str and result['capture'] == capture, 'captured diagnostic source is not readiness')
    if result['failure'] is not None:
        fields(result['failure'], {'kind','index','faceIndex'}, 'failure location')
        need(type(result['failure']['kind']) is str, 'failure kind enum')
        for key in ('index','faceIndex'):
            if result['failure'][key] is not None:
                uint(result['failure'][key], 4095, 'original failure ordinal')
    source_equal(location, result['failure'])
    if capture == 'none':
        need(result['snapshot'] is None, 'unperformed capture has no partial diagnostic source')
        stats['uncaptured'] += 1
    else:
        input_shape(result['snapshot'])
        source_equal(source, result['snapshot'])
        stats['completeCaptures'] += 1
        stats['sourceNumericBits'] += count_numeric(source)[0]
        stats['sourceNegativeZeroBits'] += count_numeric(source)[1]
    if expected_status != 'ready':
        need(result['inventory'] is None, 'invalid/budget input cannot publish partial prepared pairs')
        stats['invalidInputs' if expected_status == 'invalid_input' else 'budgetExceeded'] += 1
        return
    inventory_shape(result['inventory'])
    inventory = expected_inventory(source)
    source_equal(inventory, result['inventory'])
    stats['ready'] += 1
    stats['requiredPairs'] += len(inventory['pairs'])
    stats['excludedPairs'] += inventory['excluded']['total']
    stats['allPairs'] += inventory['allPairs']
    stats['maximumRequiredPairs'] = max(stats['maximumRequiredPairs'], len(inventory['pairs']))
    stats['maximumAllPairs'] = max(stats['maximumAllPairs'], inventory['allPairs'])
    stats['vacuousReady'] += int(inventory['dynamicBodies'] == 0)
    stats['mixedStaticReady'] += int(inventory['dynamicBodies'] > 0 and inventory['staticBodies'] > 0)
    for key in EXCLUDED_KEYS-{'total'}:
        stats['staticOnlyCounts'][key] += inventory['excluded'][key]
    for pair in inventory['pairs']:
        stats['pairKinds'][pair['kind']] += 1


def count_numeric(value):
    if type(value) in (int,float):
        return 1, int(bits(value) == b'\x80'+b'\0'*7)
    if type(value) is dict:
        counts = [count_numeric(v) for v in value.values()]
    elif type(value) is list:
        counts = [count_numeric(v) for v in value]
    else:
        return 0, 0
    return tuple(sum(row[i] for row in counts) for i in range(2))


def verify(data):
    fields(data, {'schema','kind','fixtures'}, 'complete preparation fixture envelope')
    need(type(data['schema']) is int and data['schema'] == 1
         and data['kind'] == 'world-static-mesh-flight-preparation-fixtures', 'preparation schema/kind')
    need(EXPECTED_FIXTURE_COUNT is not None and EXPECTED_INPUT_FINGERPRINT is not None,
         'complete actual finite corpus not yet frozen')
    fixtures = data['fixtures']
    need(type(fixtures) is list and len(fixtures) == EXPECTED_FIXTURE_COUNT, 'fixed complete fixture count')
    fingerprint = input_fingerprint(fixtures)
    need(fingerprint == EXPECTED_INPUT_FINGERPRINT, 'fixed complete whole-input multiset fingerprint')
    stats = new_stats(len(fixtures))
    names = set()
    for fixture in fixtures:
        fields(fixture, {'name','input','result'}, 'complete fixture')
        need(type(fixture['name']) is str and fixture['name'] and fixture['name'] not in names, 'unique nonempty fixture labels')
        names.add(fixture['name'])
        verify_fixture(fixture['input'], fixture['result'], stats)
    need(stats['maximumRequiredPairs'] == 188 and stats['maximumAllPairs'] == 378,
         'actual hard-capacity complete pair closure')
    need(stats['vacuousReady'] and stats['mixedStaticReady'] and stats['invalidInputs'] and stats['budgetExceeded'],
         'nonvacuous mixed/static/invalid/budget acceptance')
    need(all(stats['staticOnlyCounts'].values()) and stats['sourceNegativeZeroBits'] > 0,
         'all six static-only exclusions and exact negative-zero source copies')
    return {'status':'PASS', **stats, 'inputFingerprint':fingerprint,
            'scope':'Finite original-source ownership, strict schema and exhaustive typed-pair preparation only. No propagation, contact, non-overlap certificate, candidate, World advance, allocator fault, heap or stack measurement is inferred.'}


def new_stats(count=0):
    stats = dict.fromkeys(['fixtures','ready','invalidInputs','budgetExceeded','uncaptured','completeCaptures',
                          'requiredPairs','excludedPairs','allPairs','maximumRequiredPairs','maximumAllPairs',
                          'vacuousReady','mixedStaticReady','sourceNumericBits','sourceNegativeZeroBits'],0)
    stats['fixtures'] = count
    stats['staticOnlyCounts'] = dict.fromkeys(sorted(EXCLUDED_KEYS-{'total'}),0)
    stats['pairKinds'] = dict.fromkeys(['body_mesh','body_plane','body_body'],0)
    return stats


def main():
    need(__debug__, 'run preparation reference without Python -O')
    need(len(sys.argv) == 2, 'Usage: verify-world-static-mesh-preparation.py native-fixtures.json')
    print(json.dumps(verify(load(sys.argv[1]))))


if __name__ == '__main__':
    main()
