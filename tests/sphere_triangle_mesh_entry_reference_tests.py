"""Analytical entry-window self-tests and complete-corpus corruption controls."""
from copy import deepcopy
from fractions import Fraction as F
import argparse
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('entry_reference', root / 'scripts/verify-sphere-triangle-mesh-entry.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
trajectory = oracle.trajectory
TRIANGLE = [[0, 0, 0], [4, 0, 0], [0, 0, 4]]


def compile_path(start, end, triangles=None):
    if triangles is None:
        triangles = [{'id': 37, 'vertices': TRIANGLE}]
    return trajectory.compile_mesh_path(start, end, triangles)


def profile():
    return {'mesh': {'maxSurfaces': 64, 'primitive': {'maxCandidates': 7,
             'sqrtRefinements': 128, 'maxTotalSqrtRefinements': 1024,
             'maximumLocalWidth': 1e-7, 'maximumNormalWidth': 1e-8,
             'minimumSineSquared': 1e-12}}, 'maxEvaluations': 256,
             'maxLeaves': 128, 'maxDepth': 16, 'enclosureSqrtRefinements': 128,
             'maxTotalSqrtRefinements': 1000000, 'parameterTolerance': 1/64}


class EntryReferenceSelfTests(unittest.TestCase):
    def test_analytical_plane_entry_one_quarter(self):
        path = compile_path([1, 2, 1], [1, -4, 1])
        self.assertEqual(trajectory.mesh_path_minimum(path, F(1, 4), F(1, 4))[0], F(1, 4))
        self.assertTrue(oracle.entry_predicate(path, F(1, 2), F(1, 8), F(5, 16)))
        oracle.verify_width([F(3, 16), F(3, 16)], F(1, 8), F(5, 16), F(1, 4))

    def test_closed_prefix_cannot_include_contact_endpoint(self):
        path = compile_path([1, 2, 1], [1, -4, 1])
        self.assertFalse(oracle.entry_predicate(path, F(1, 2), F(1, 4), F(5, 16)))

    def test_reverse_has_a_different_first_entry(self):
        path = compile_path([1, -4, 1], [1, 2, 1])
        self.assertEqual(trajectory.mesh_path_minimum(path, F(7, 12), F(7, 12))[0], F(1, 4))
        self.assertTrue(oracle.entry_predicate(path, F(1, 2), F(1, 2), F(5, 8)))
        self.assertFalse(oracle.entry_predicate(path, F(1, 2), F(1, 8), F(5, 16)))

    def test_initial_penetration_is_not_entry_window(self):
        path = compile_path([1, F(1, 4), 1], [1, -2, 1])
        self.assertFalse(oracle.entry_predicate(path, F(1, 2), F(0), F(1, 4)))

    def test_initial_boundary_is_not_strict_positive(self):
        path = compile_path([1, F(1, 2), 1], [1, -1, 1])
        self.assertFalse(oracle.entry_predicate(path, F(1, 2), F(0), F(1, 4)))

    def test_contact_without_strict_negative_has_no_witness(self):
        path = compile_path([1, F(1, 2), 1], [2, F(1, 2), 1])
        self.assertEqual(trajectory.mesh_path_minimum(path)[0], F(1, 4))
        self.assertFalse(oracle.entry_predicate(path, F(1, 2), F(0), F(1)))

    def test_positive_island_does_not_fill_an_earlier_unknown_region(self):
        triangles = [{'id': i, 'vertices': [[x, -4, -4], [x, 4, -4], [x, 0, 4]]}
                     for i, x in [(99, 2), (7, 6)]]
        path = compile_path([0, 0, 0], [8, 0, 0], triangles)
        self.assertGreater(trajectory.mesh_path_minimum(path, F(1, 2), F(1, 2))[0], F(1, 4))
        self.assertLess(trajectory.mesh_path_minimum(path, F(23, 32), F(23, 32))[0], F(1, 4))
        self.assertFalse(oracle.entry_predicate(path, F(1, 2), F(1, 2), F(23, 32)))

    def test_mesh_order_does_not_select_an_entry_surface(self):
        triangles = [{'id': 99, 'vertices': TRIANGLE},
                     {'id': 7, 'vertices': [[0, -2, 0], [4, -2, 0], [0, -2, 4]]}]
        for rows in [triangles, list(reversed(triangles))]:
            path = compile_path([1, 2, 1], [1, -4, 1], rows)
            self.assertTrue(oracle.entry_predicate(path, F(1, 2), F(1, 8), F(5, 16)))

    def test_safe_endpoints_do_not_prove_a_positive_prefix(self):
        path = compile_path([1, 2, 1], [1, -4, 1])
        self.assertGreater(trajectory.mesh_path_minimum(path, F(0), F(0))[0], F(1, 4))
        self.assertGreater(trajectory.mesh_path_minimum(path, F(1), F(1))[0], F(1, 4))
        self.assertEqual(trajectory.mesh_path_minimum(path)[0], 0)

    def test_arbitrary_anchor_negative_is_not_exact_path_witness(self):
        base, step = 2 ** 39, F(1, 2 ** 13)
        triangle = [[base + 1, -4, -4], [base + 1, 4, -4], [base + 1, 0, 4]]
        path = compile_path([base, 0, 0], [F(base) + step, 0, 0], [{'id': 37, 'vertices': triangle}])
        radius = 1 - 3 * step / 4
        self.assertLess(1 - step, radius)
        self.assertGreater(trajectory.mesh_path_minimum(path, F(1, 2), F(1, 2))[0], radius * radius)
        self.assertFalse(oracle.entry_predicate(path, radius, F(0), F(1, 2)))

    def test_width_uses_outward_bounds_instead_of_rounded_subtraction(self):
        lo, hi = F(1, 2 ** 54), F(1)
        self.assertEqual(float(hi) - float(lo), 1)
        with self.assertRaises(AssertionError):
            oracle.verify_width([1, 1], lo, hi, 1)
        oracle.verify_width([0, 1], lo, hi, 1)

    def test_width_tolerance_is_not_an_epsilon_gap(self):
        with self.assertRaises(AssertionError):
            oracle.verify_width([0, F(1, 8)], F(1, 4), F(1, 2), F(1, 8))
        for tolerance in [0, -1, 2]:
            with self.assertRaises(AssertionError):
                oracle.verify_width([0, 1], 0, 1, tolerance)

    def test_width_requires_ordered_distinct_parameters(self):
        for lo, hi in [(0, 0), (1, 0), (-1, 1), (0, 2)]:
            with self.assertRaises(AssertionError):
                oracle.verify_width([0, 1], lo, hi, 1)

    def test_subnormal_and_signed_zero_are_not_silently_replaced(self):
        value = oracle.loads('{"x":-0,"tiny":5e-324}')
        self.assertLess(math.copysign(1, value['x']), 0)
        self.assertGreater(oracle.fraction(value['tiny']), 0)
        with self.assertRaises(AssertionError):
            oracle.source_equal(value, {'x': 0, 'tiny': value['tiny']})

    def test_strict_json_rejects_aliases_and_invalid_numbers(self):
        for text in ['{"x":0,"x":1}', '{"x":NaN}', '{"x":1e999}',
                     '{"x":1e-999}', '{"x":"\\ud800"}']:
            with self.assertRaises((AssertionError, ValueError, UnicodeError)):
                oracle.loads(text)

    def test_initial_call_shares_hard_work_budget(self):
        w = {k: 0 for k in oracle.WORK_KEYS}
        w.update({'meshQueries': 256, 'primitiveQueries': 16384, 'candidatesExamined': 114688,
                  'primitiveSqrtRefinements': 8388608, 'enclosureSqrtRefinements': 262144,
                  'sqrtRefinements': 8650752, 'sqrtRefinementsUpper': 8650752,
                  'enclosureSqrtCalls': 512, 'workExact': True})
        oracle.work(w)
        for key, bad in [('meshQueries', 257), ('sqrtRefinementsUpper', 8650753), ('meshQueries', True)]:
            malformed = dict(w);malformed[key] = bad
            with self.assertRaises(AssertionError):
                oracle.work(malformed)

    def test_input_tolerance_checked_without_changing_old_profile(self):
        source = {'start': [1, 2, 1], 'end': [1, -4, 1], 'radius': .5,
                  'triangles': [{'id': 37, 'vertices': TRIANGLE}], 'settings': profile()}
        self.assertFalse(oracle.input_faults(source))
        for value in [0, -1, 2]:
            malformed = deepcopy(source);malformed['settings']['parameterTolerance'] = value
            self.assertIn(('settings', None), oracle.input_faults(malformed))


def controls(data):
    """Corrupt one output in a fresh full corpus; source pins stay mandatory.

    The edited fixture is moved to the front to fail early, without changing
    whole-input multiset identity. Selection uses proof structure, never names.
    """
    fixtures = data['fixtures']

    def select(predicate):
        choices = [i for i, f in enumerate(fixtures) if predicate(f['result'])]
        oracle.need(choices, 'complete corpus contains required independent negative-control feature')
        return min(choices, key=lambda i: (len(fixtures[i]['input']['triangles']),
                                          len(fixtures[i]['result']['audits']), i))

    def put(obj, key, value):
        obj[key] = value

    entry = select(lambda r: r['status'] == 'entry_window')
    separated = select(lambda r: r['status'] == 'separated')
    initial_negative = select(lambda r: r['status'] == 'initial_penetration')
    boundary = select(lambda r: r['reason'] == 'initial_boundary')
    invalid = select(lambda r: r['status'] == 'invalid_input')
    prefix = select(lambda r: r['safePrefix'] is not None and 0 < r['safePrefix'][1] < 1)
    initial_only = select(lambda r: r['safePrefix'] == [0, 0] and r['status'] == 'not_certified')
    island = select(lambda r: r['safePrefix'] is not None and any(
        v['cell']['parameter'][0] > r['safePrefix'][1] for v in r['certifiedLeaves']))
    frontier = select(lambda r: bool(r['frontier']))
    capacity = select(lambda r: len(r['audits']) == 256 and len(r['certifiedLeaves']) == 128)
    candidate_set = select(lambda r: r['window'] is not None and len(r['candidateSurfaceIds']) > 1)
    unqueried = select(lambda r: bool(r['audits']) and not r['audits'][-1]['meshQueried'])
    current = select(lambda r: r['current'] is not None and any(p['state'] == 'current' and p['auditIndex'] is None for p in r['partition']))
    queried = select(lambda r: r['lastMesh'] is not None and r['lastMesh']['status'] == 0)
    failed = select(lambda r: r['lastMesh'] is not None and r['lastMesh']['failedRows'] > 0 and len(r['lastMesh']['rows']) > 1)
    recovered = select(lambda r: r['status'] == 'entry_window' and any(
        a['kind'] == 'cell' and a['meshStatus'] == 3 and a['outcome'] == 'split' for a in r['audits']))
    with_error = select(lambda r: any(a['kind'] == 'cell' and a['errorRoot'] is not None
                                     and a['errorRoot'][1] > 0 for a in r['audits']))
    with_radius = select(lambda r: any(a['kind'] == 'cell' and a['displacementRoot'] is not None
                                      and a['displacementRoot'][1] > 1e-6 for a in r['audits']))
    records = []

    def add(name, index, mutate):
        packet = deepcopy(data)
        target = packet['fixtures'][index]
        mutate(target)
        packet['fixtures'].insert(0, packet['fixtures'].pop(index))
        try:
            oracle.verify(packet)
        except (AssertionError, ValueError, TypeError, KeyError, OverflowError, IndexError) as error:
            records.append({'name': name, 'rejected': True, 'diagnostic': str(error)})
        else:
            raise AssertionError('entry corruption accepted: ' + name)

    r = lambda f: f['result']
    def norm(f, key):
        return next(a for a in r(f)['audits'] if a['kind'] == 'cell' and a[key] is not None
                    and a[key][1] > (1e-6 if key == 'displacementRoot' else 0))

    add('unknown result field', entry, lambda f: put(r(f), 'invented', 0))
    add('source endpoint changed', entry, lambda f: put(f['input'], 'end', [9e11] * 3))
    add('source radius changed', entry, lambda f: put(f['input'], 'radius', .125))
    add('source tolerance changed', entry, lambda f: put(f['input']['settings'], 'parameterTolerance', .75))
    add('source id changed', entry, lambda f: put(f['input']['triangles'][0], 'id', 900))
    add('source owned settings changed', entry, lambda f: put(r(f)['snapshot']['settings'], 'maxLeaves', 1))
    add('source owned endpoint changed', entry, lambda f: put(r(f)['snapshot'], 'start', [0, 0, 0]))
    def flip_source_zero(f):
        for triangle in r(f)['snapshot']['triangles']:
            for point in triangle['vertices']:
                for i, value in enumerate(point):
                    if value == 0:
                        point[i] = -0.0 if math.copysign(1, value) > 0 else 0.0
                        return
        raise AssertionError('signed-zero source control needs zero coordinate')
    add('source owned signed zero lost', queried, flip_source_zero)
    add('boolean source id alias', queried, lambda f: put(r(f)['snapshot']['triangles'][0], 'id', True))
    add('initial separation flag false', entry, lambda f: put(r(f), 'initialSeparationProven', False))
    add('initial separation flag boolean alias', entry, lambda f: put(r(f), 'initialSeparationProven', 1))
    add('initial proof erased', entry, lambda f: put(r(f), 'initial', None))
    add('initial proof borrowed from a cell', entry, lambda f: put(r(f)['initial'], 'auditIndex', 1))
    add('initial positive expression changed', entry, lambda f: put(r(f)['initial'], 'lowerGapCertificate', [0, 0]))
    add('initial negative expression changed', initial_negative, lambda f: put(r(f)['initial'], 'upperGapCertificate', [0, 1]))
    add('initial negative forged as an entry', initial_negative, lambda f: put(r(f), 'status', 'entry_window'))
    add('initial boundary forged positive', boundary, lambda f: put(r(f), 'initialSeparationProven', True))
    add('initial point relabeled cell', entry, lambda f: put(r(f)['audits'][0], 'kind', 'cell'))
    add('initial point parameter moved', entry, lambda f: put(r(f)['audits'][0], 'parameter', .5))
    add('initial point cell moved to whole path', entry, lambda f: put(r(f)['audits'][0]['cell'], 'parameter', [0, 1]))
    add('safe prefix erased', entry, lambda f: put(r(f), 'safePrefix', None))
    add('safe prefix advanced over unknown cells', prefix, lambda f: put(r(f), 'safePrefix', [0, 1]))
    add('initial proof only mistaken for whole path', initial_only, lambda f: put(r(f), 'safePrefix', [0, 1]))
    add('positive island incorrectly used as prefix', island, lambda f: put(r(f), 'safePrefix', [0, r(f)['certifiedLeaves'][-1]['cell']['parameter'][1]]))
    add('positive island omitted', island, lambda f: r(f)['certifiedLeaves'].pop())
    add('closed proof leaf dropped', separated, lambda f: r(f)['certifiedLeaves'].pop())
    add('maximum leaf tail dropped', capacity, lambda f: r(f)['certifiedLeaves'].pop())
    add('maximum audit tail dropped', capacity, lambda f: r(f)['audits'].pop())
    add('closed leaf boundary changed one ulp', separated, lambda f: put(r(f)['certifiedLeaves'][0]['cell'], 'parameter', [0, math.nextafter(1., 0)]))
    add('certified leaf owner changed', entry, lambda f: put(r(f)['certifiedLeaves'][0], 'auditIndex', 0))
    add('window erased', entry, lambda f: put(r(f), 'window', None))
    add('window lower bound crosses an unknown region', entry, lambda f: r(f)['window']['parameter'].__setitem__(0, r(f)['bestWitness']['parameter']))
    add('window upper bound changed', entry, lambda f: r(f)['window']['parameter'].__setitem__(1, 1))
    add('window width underestimated to zero', entry, lambda f: put(r(f)['window'], 'width', [0, 0]))
    add('window width upper exceeds tolerance', entry, lambda f: put(r(f)['window'], 'width', [0, 2]))
    add('window width lower excludes exact subtraction', entry, lambda f: put(r(f)['window'], 'width', [1, 1]))
    add('window witness owner changed', entry, lambda f: put(r(f)['window'], 'witnessAuditIndex', 0))
    add('window candidates narrowed to one witness face', candidate_set, lambda f: put(r(f), 'candidateSurfaceIds', r(f)['candidateSurfaceIds'][:1]))
    add('window candidate identity changed', entry, lambda f: r(f)['candidateSurfaceIds'].__setitem__(0, 0))
    add('window candidate boolean alias', entry, lambda f: r(f)['candidateSurfaceIds'].__setitem__(0, True))
    add('negative witness erased', entry, lambda f: put(r(f), 'bestWitness', None))
    add('negative witness owner changed', entry, lambda f: put(r(f)['bestWitness'], 'auditIndex', 0))
    add('negative witness parameter moved', entry, lambda f: put(r(f)['bestWitness'], 'parameter', 0))
    add('negative witness E omitted', entry, lambda f: put(r(f)['bestWitness'], 'errorUpper', 0))
    add('negative witness upper certificate nonnegative', entry, lambda f: put(r(f)['bestWitness'], 'upperGapCertificate', [0, 1]))
    add('negative witness path replaced by arbitrary point', entry, lambda f: put(r(f)['bestWitness'], 'exactPathBounds', [[9e11, 9e11]] * 3))
    add('error square and root jointly underestimated', with_error, lambda f: (put(norm(f, 'errorRoot'), 'errorSquaredBound', [0, 0]), put(norm(f, 'errorRoot'), 'errorRoot', [0, 0])))
    add('whole cell radius square and root underestimated', with_radius, lambda f: (put(norm(f, 'displacementRoot'), 'displacementSquaredBound', [0, 0]), put(norm(f, 'displacementRoot'), 'displacementRoot', [0, 0])))
    add('whole path box excludes endpoint', with_radius, lambda f: put(norm(f, 'displacementRoot'), 'pathBounds', [[9e11, 9e11]] * 3))
    add('point box excludes exact global path', with_error, lambda f: put(norm(f, 'errorRoot'), 'pointBounds', [[9e11, 9e11]] * 3))
    add('clearance expression forged positive', with_radius, lambda f: put(norm(f, 'displacementRoot'), 'clearanceCertificate', [1e11, 1e11]))
    add('penetration expression forged negative', with_error, lambda f: put(norm(f, 'errorRoot'), 'penetrationCertificate', [-1e11, -1e11]))
    add('partition tail dropped', frontier, lambda f: r(f)['partition'].pop())
    add('partition hole introduced', frontier, lambda f: r(f)['partition'][0]['cell']['parameter'].__setitem__(0, math.ulp(0.)))
    add('unqueried frontier dropped', frontier, lambda f: r(f)['frontier'].pop())
    add('partition count changed', separated, lambda f: put(r(f), 'partitionLeaves', r(f)['partitionLeaves'] + 1))
    add('partition state invents separation', frontier, lambda f: put(next(v for v in r(f)['partition'] if v['state'] == 'unqueried'), 'state', 'certified'))
    add('partition audit owner changed', entry, lambda f: put(r(f)['partition'][0], 'auditIndex', 0))
    add('blocked reason erased', select(lambda r: any(v['blockedReason'] != 'none' for v in r['partition'])),
        lambda f: put(next(v for v in r(f)['partition'] if v['blockedReason'] != 'none'), 'blockedReason', 'none'))
    add('current prequery gets old audit', current, lambda f: put(next(v for v in r(f)['partition'] if v['state'] == 'current'), 'auditIndex', 0))
    add('unqueried audit borrows mesh status', unqueried, lambda f: put(r(f)['audits'][-1], 'meshStatus', 0))
    add('BFS cell audit order swapped', entry, lambda f: r(f)['audits'].__setitem__(slice(2, 4), list(reversed(r(f)['audits'][2:4]))))
    add('recoverable ancestor mesh failure omitted', recovered,
        lambda f: r(f)['audits'].pop(next(i for i, a in enumerate(r(f)['audits']) if a['kind'] == 'cell' and a['meshStatus'] == 3)))
    add('returned work total changed', entry, lambda f: put(r(f)['work'], 'meshQueries', r(f)['work']['meshQueries'] + 1))
    add('initial work missing from total', entry, lambda f: put(r(f)['work'], 'meshQueries', r(f)['work']['meshQueries'] - 1))
    add('returned work boolean counter', entry, lambda f: put(r(f)['work'], 'meshQueries', True))
    add('reservation incorrectly charged as actual', entry, lambda f: put(r(f)['work'], 'sqrtRefinements', 512))
    add('unknown work falsely claimed on success', entry, lambda f: put(r(f)['work'], 'workExact', False))
    add('work upper smaller than known count', entry, lambda f: put(r(f)['work'], 'sqrtRefinementsUpper', -1))
    add('cell delta replaced by global cumulative work', entry, lambda f: put(r(f)['audits'][-1], 'work', deepcopy(r(f)['work'])))
    add('last mesh moved to earlier audit', entry, lambda f: put(r(f), 'lastMeshAuditIndex', 0))
    add('last mesh rows omit a failed distant surface', failed, lambda f: put(r(f)['lastMesh'], 'rows', [v for v in r(f)['lastMesh']['rows'] if v['query']['status'] == 0]))
    add('last mesh possible ids erased', queried, lambda f: put(r(f)['lastMesh']['nearest'], 'possibleSurfaceIds', []))
    add('last mesh boolean status', queried, lambda f: put(r(f)['lastMesh'], 'status', False))
    add('last mesh geometry moved', queried, lambda f: put(r(f)['lastMesh']['rows'][0]['query']['geometry'], 'closest', [[9e11, 9e11]] * 3))
    add('last mesh candidate prefix truncated', queried, lambda f: r(f)['lastMesh']['rows'][0]['query']['candidates'].pop())
    add('preflight invents initial proof', invalid, lambda f: put(r(f), 'initial', deepcopy(fixtures[entry]['result']['initial'])))
    add('preflight invents safe prefix', invalid, lambda f: put(r(f), 'safePrefix', [0, 0]))
    add('preflight invents successful snapshot', invalid, lambda f: put(r(f), 'snapshot', deepcopy(fixtures[entry]['result']['snapshot'])))
    add('maximum depth invented', entry, lambda f: put(r(f), 'maximumDepth', r(f)['maximumDepth'] + 1))
    add('maximum depth boolean alias', entry, lambda f: put(r(f), 'maximumDepth', False))
    for name, mutate in [('whole fixture omitted', lambda p: p['fixtures'].pop()),
                         ('duplicate input with different label', lambda p: p['fixtures'].__setitem__(-1, deepcopy(p['fixtures'][0]))),
                         ('unknown envelope field', lambda p: put(p, 'unexpected', 0))]:
        packet = deepcopy(data);mutate(packet)
        try:
            oracle.verify(packet)
        except (AssertionError, ValueError, TypeError, KeyError, OverflowError) as error:
            records.append({'name': name, 'rejected': True, 'diagnostic': str(error)})
        else:
            raise AssertionError('entry corruption accepted: ' + name)
    for name, text in [('JSON overflow', '{"x":1e999}'), ('JSON underflow', '{"x":1e-999}'),
                       ('JSON duplicate key', '{"x":0,"x":1}'), ('JSON nonfinite', '{"x":NaN}'),
                       ('JSON unpaired Unicode', '{"x":"\\ud800"}')]:
        try:
            oracle.loads(text)
        except (AssertionError, ValueError, UnicodeError) as error:
            records.append({'name': name, 'rejected': True, 'diagnostic': str(error)})
        else:
            raise AssertionError('entry JSON corruption accepted: ' + name)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', nargs='?')
    parser.add_argument('--output')
    args = parser.parse_args()
    stream = io.StringIO()
    run = unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(EntryReferenceSelfTests))
    oracle.need(run.wasSuccessful(), stream.getvalue())
    if not args.fixture:
        print(json.dumps({'status': 'PASS', 'selfTestGroups': run.testsRun}))
        return
    data = oracle.load(args.fixture)
    baseline = oracle.verify(data)
    records = controls(data)
    permuted = deepcopy(data)
    permuted['fixtures'].reverse()
    for index, fixture in enumerate(permuted['fixtures']):
        fixture['name'] = 'entry-independent-label-' + str(index)
    oracle.need(oracle.verify(permuted) == baseline, 'entry result independent of labels/corpus traversal order')
    optimized = subprocess.run([sys.executable, '-O', str(root / 'scripts/verify-sphere-triangle-mesh-entry.py'), args.fixture],
                               capture_output=True, text=True, timeout=120)
    oracle.need(optimized.returncode != 0 and 'without Python -O' in optimized.stderr, 'optimized Python cannot bypass entry checks')
    records.append({'name': 'Python -O rejected', 'rejected': True,
                    'diagnostic': optimized.stderr.strip().splitlines()[-1]})
    report = {'status': 'PASS', 'baseline': baseline, 'selfTestGroups': run.testsRun,
              'rejectedControls': records, 'labelAndOrderIndependent': True}
    if args.output:
        output = Path(args.output);output.mkdir(parents=True, exist_ok=False)
        for name, content in [('negative-controls.json', json.dumps(report, indent=2) + '\n'),
                              ('reference.json', json.dumps(baseline, indent=2) + '\n'),
                              ('reference-self-tests.txt', stream.getvalue()),
                              ('commands.json', json.dumps({'argv': sys.argv, 'python': sys.version}, indent=2) + '\n')]:
            (output / name).write_text(content, encoding='utf-8')
        paths = [Path(args.fixture), root / 'scripts/verify-sphere-triangle-mesh-entry.py', Path(__file__)]
        provenance = [{'path': str(p.resolve()), 'bytes': len(p.read_bytes()), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
        (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'fixtures': baseline['fixtures'], 'selfTestGroups': run.testsRun,
                      'rejectedControls': len(records), 'labelAndOrderIndependent': True}))


if __name__ == '__main__':
    main()
