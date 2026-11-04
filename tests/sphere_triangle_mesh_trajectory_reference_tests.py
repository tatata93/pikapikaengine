"""Analytical self-tests and later Native-packet negative controls."""
from fractions import Fraction as F
from copy import deepcopy
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
spec = importlib.util.spec_from_file_location('trajectory_reference', root / 'scripts/verify-sphere-triangle-mesh-trajectory.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
triangle = [[0, 0, 0], [4, 0, 0], [0, 0, 4]]


class ExactTrajectoryReferenceTests(unittest.TestCase):
    def test_static_face_and_reverse_parallel(self):
        self.assertEqual(oracle.path_triangle_minimum([1, 3, 1], [1, 3, 1], triangle)[0], 9)
        for start, end in [([1, 2, 1], [2, 2, 1]), ([2, 2, 1], [1, 2, 1])]:
            self.assertEqual(oracle.path_triangle_minimum(start, end, triangle)[0], 4)

    def test_crossing_and_non_midpoint_stationary(self):
        value, s = oracle.path_triangle_minimum([1, 2, 1], [1, -4, 1], triangle)
        self.assertEqual((value, s), (0, F(1, 3)))
        self.assertEqual(oracle.path_triangle_minimum([1, 2, 1], [1, -4, 1], triangle, F(1, 2), F(1, 2))[0], 1)
        self.assertEqual(oracle.path_triangle_minimum([1, 2, 1], [1, -4, 1], triangle, F(0), F(1, 4))[0], F(1, 4))

    def test_edges_clamped_vertices_and_feature_transitions(self):
        self.assertEqual(oracle.path_triangle_minimum([-3, 4, -1], [-3, 4, 1], triangle)[0], 25)
        self.assertEqual(oracle.path_triangle_minimum([1, 2, -3], [3, 2, -3], triangle)[0], 13)
        value, s = oracle.path_triangle_minimum([-2, 1, 0], [6, 1, 0], triangle)
        self.assertEqual(value, 1)
        self.assertTrue(F(1, 4) <= s <= F(3, 4))

    def test_rotated_plane_and_degenerate_convex_hull(self):
        # Plane x+y+z=0, path along its normal through the face's centroid.
        t = [[1, -1, 0], [0, 1, -1], [-1, 0, 1]]
        self.assertEqual(oracle.path_triangle_minimum([1, 1, 1], [2, 2, 2], t)[0], 3)
        self.assertEqual(oracle.path_triangle_minimum([1, 2, 0], [3, 2, 0], [[0, 0, 0], [2, 0, 0], [4, 0, 0]])[0], 4)
        self.assertEqual(oracle.path_triangle_minimum([0, 1, 0], [0, 2, 0], [[0, 0, 0]] * 3)[0], 1)

    def test_non_dyadic_stationary_and_closed_domain(self):
        # Closest vertex is the origin; ||(-1,1,0)+s(3,1,0)||² has minimum at 1/5.
        t = [[0, 0, 0], [-4, 0, 0], [0, 0, -4]]
        value, s = oracle.path_triangle_minimum([-1, 1, 0], [2, 2, 0], t)
        # Before x=0 the projection lies on edge AB; then the origin wins.
        self.assertEqual(value, 1)
        point = [[0, 0, 0]] * 3
        self.assertEqual(oracle.path_triangle_minimum([-1, 1, 0], [2, 2, 0], point), (F(8, 5), F(1, 5)))
        self.assertEqual(oracle.path_triangle_minimum([-1, 1, 0], [2, 2, 0], point, F(1, 2), F(1))[0], F(5, 2))

    def test_mesh_multiple_minimizers_and_permutation(self):
        surfaces = [{'id': 99, 'vertices': [[-1, -2, -2], [-1, 2, -2], [-1, 0, 2]]},
                    {'id': 7, 'vertices': [[1, -2, -2], [1, 2, -2], [1, 0, 2]]}]
        for rows in [surfaces, list(reversed(surfaces))]:
            c = oracle.compile_mesh_path([0, 0, 0], [0, 1, 0], rows)
            self.assertEqual(oracle.mesh_path_minimum(c), (F(1), {7, 99}))

    def test_translation_scaling_and_lost_binary64_term(self):
        shift = 2 ** 40
        moved = [[x + shift, y - shift, z + shift] for x, y, z in triangle]
        self.assertEqual(oracle.path_triangle_minimum([shift + 1, -shift + 2, shift + 1],
                                                    [shift + 2, -shift + 2, shift + 1], moved)[0], 4)
        scaled = [[3 * x, 3 * y, 3 * z] for x, y, z in triangle]
        self.assertEqual(oracle.path_triangle_minimum([3, 6, 3], [6, 6, 3], scaled)[0], 36)
        self.assertEqual(oracle.fraction(float(2 ** 53 + 1)), 2 ** 53)
        with self.assertRaises(AssertionError):
            oracle.fraction(2 ** 53 + 1)

    def test_quadratic_and_linear_feasible_clipping(self):
        self.assertEqual(oracle.clip_nonnegative((F(0), F(1)), F(-1), F(3)), (F(1, 3), F(1)))
        self.assertIsNone(oracle.clip_nonnegative((F(0), F(1)), F(-1), F(0)))
        self.assertEqual(oracle.quadratic_minimum((F(3), F(-2), F(1)), F(0), F(2)), (F(2), F(1)))

    def test_strict_json_and_signed_zero(self):
        self.assertLess(math.copysign(1, oracle.loads('{"x":-0}')['x']), 0)
        for text in ['{"x":1e999}', '{"x":1e-999}', '{"x":NaN}', '{"x":0,"x":1}', '{"x":"\\ud800"}']:
            with self.assertRaises((AssertionError, ValueError, UnicodeError)):
                oracle.loads(text)

    def test_endpoint_and_midpoint_samples_are_not_whole_path_proofs(self):
        pieces = oracle.triangle_pieces([1, 2, 1], [1, -4, 1], triangle)
        self.assertGreater(oracle.piecewise_minimum(pieces, F(0), F(0))[0], F(9, 4))
        self.assertGreater(oracle.piecewise_minimum(pieces, F(1), F(1))[0], F(9, 4))
        self.assertEqual(oracle.piecewise_minimum(pieces)[0], 0)
        # A distinct path to a point has a safe midpoint yet penetrates earlier.
        pieces = oracle.triangle_pieces([-1, 1, 0], [2, 2, 0], [[0, 0, 0]] * 3)
        self.assertGreater(oracle.piecewise_minimum(pieces, F(1, 2), F(1, 2))[0], 2)
        self.assertLess(oracle.piecewise_minimum(pieces)[0], 2)

    def test_squared_bound_negative_lower_is_valid_and_sqrt_is_upper_point(self):
        # Outward addition may put a tiny negative lower around a true zero.
        oracle.verify_root([-math.ulp(0.0), 1], [1, 1], (F(0), F(1)))
        with self.assertRaises(AssertionError):
            oracle.verify_root([0, 4], [1, 1], (F(0), F(1)))
        with self.assertRaises(AssertionError):
            oracle.verify_root([0, 1], [0, .5], (F(0), F(1)))

    def test_rounded_anchor_without_error_can_falsely_claim_path_penetration(self):
        base = 2 ** 39
        step = math.ulp(float(base))
        start, end = [base, 0, 0], [base + step, 0, 0]
        plane = [[base - 1, -4, -4], [base - 1, 4, -4], [base - 1, 0, 4]]
        exact_midpoint = F(base) + F(step) / 2
        self.assertNotEqual(exact_midpoint, F(float(exact_midpoint)))
        radius = F(1) + F(step) / 4
        anchor_distance = F(1)
        exact_error = F(step) / 2
        squared, _ = oracle.path_triangle_minimum(start, end, plane, F(1, 2), F(1, 2))
        self.assertLess(anchor_distance, radius)
        self.assertGreater(squared, radius * radius)
        self.assertGreater(anchor_distance + exact_error - radius, 0)

    def test_clearance_expression_is_not_an_upper_bound_for_actual_gap(self):
        # At y=2, r=.5, the true path gap is1.5. L-R-r=.5 is only a lower-bound expression.
        squared, _ = oracle.path_triangle_minimum([1, 2, 1], [3, 2, 1], triangle)
        self.assertEqual(squared, 4)
        expression = F(2) - F(1) - F(1, 2)
        self.assertEqual(expression, F(1, 2))
        self.assertLess(expression, F(3, 2))

    def test_inside_end_anchor_is_not_an_outside_exact_midpoint(self):
        base, step = 2 ** 39, F(1, 2 ** 13)
        t = [[base + 1, -4, -4], [base + 1, 4, -4], [base + 1, 0, 4]]
        radius = 1 - 3 * step / 4
        value, _ = oracle.path_triangle_minimum([base, 0, 0], [F(base) + step, 0, 0], t, F(1, 2), F(1, 2))
        anchor_distance, error = 1 - step, step / 2
        self.assertLess(anchor_distance, radius)
        self.assertGreater(value, radius * radius)
        self.assertGreater(anchor_distance + error - radius, 0)


def controls(data):
    """Every corruption is checked against a fresh, unmodified full corpus."""
    fs = data['fixtures']
    find = lambda test: next(i for i, f in enumerate(fs) if test(f['result']))
    separated = find(lambda r: r['status'] == 'separated')
    witness = find(lambda r: r['status'] == 'penetration_witness')
    split = find(lambda r: any(a['outcome'] == 'split' for a in r['audits']))
    prefix = find(lambda r: r['safePrefix'] is not None and r['safePrefix'][1] < 1)
    frontier = find(lambda r: bool(r['frontier']))
    failure = find(lambda r: r['reason'] == 'mesh_query_failed')
    invalid = find(lambda r: r['status'] == 'invalid_input')
    queried = find(lambda r: r['lastMesh'] is not None and r['lastMesh']['status'] == 0)
    multi_query = find(lambda r: r['work']['meshQueries'] > 1)
    unqueried = find(lambda r: r['current'] is not None and r['audits'] and not r['audits'][-1]['meshQueried'])
    with_root = find(lambda r: any(a['displacementRoot'] is not None for a in r['audits']))
    with_error = find(lambda r: any(a['errorRoot'] is not None and a['errorRoot'][1] > 0 for a in r['audits']))
    without_prefix = find(lambda r: r['snapshot'] is not None and r['safePrefix'] is None)

    def result(packet, i=separated):
        return packet['fixtures'][i]['result']

    def audit(packet, i=with_root):
        return next(a for a in result(packet, i)['audits'] if a['displacementRoot'] is not None)

    def error_audit(packet):
        return next(a for a in result(packet, with_error)['audits'] if a['errorRoot'] is not None and a['errorRoot'][1] > 0)

    def put(obj, key, value):
        obj[key] = value

    def flip_zero(packet):
        snapshot = result(packet, queried)['snapshot']
        for t in snapshot['triangles']:
            for v in t['vertices']:
                for i, value in enumerate(v):
                    if value == 0:
                        v[i] = -0.0 if math.copysign(1, value) > 0 else 0.0
                        return
        raise AssertionError('source-zero negative control requires an original zero')

    def corrupt_box(packet, key):
        a = audit(packet)
        a[key][0] = [1e13, 1e13]

    def drop_failed_row(packet):
        last = result(packet, failure)['lastMesh']
        index = next(i for i, row in enumerate(last['rows']) if row['query']['status'])
        last['rows'].pop(index)

    mutations = [
        ('unknown schema', lambda p: put(p, 'schema', 2)),
        ('boolean schema', lambda p: put(p, 'schema', True)),
        ('fixture dropped', lambda p: p['fixtures'].pop()),
        ('duplicate fixture', lambda p: p['fixtures'].append(deepcopy(p['fixtures'][0]))),
        ('unknown result status', lambda p: put(result(p), 'status', 'clear')),
        ('unknown result reason', lambda p: put(result(p), 'reason', 'close_enough')),
        ('mesh query failure mislabeled sqrt budget', lambda p: put(result(p, failure), 'reason', 'sqrt_budget')),
        ('certificate leaf dropped coverage hole', lambda p: result(p)['certifiedLeaves'].pop()),
        ('certificate leaf duplicated', lambda p: result(p)['certifiedLeaves'].append(deepcopy(result(p)['certifiedLeaves'][0]))),
        ('leaf interval boundary one ulp hole', lambda p: result(p)['certifiedLeaves'][0]['cell']['parameter'].__setitem__(1, math.nextafter(result(p)['certifiedLeaves'][0]['cell']['parameter'][1], 0))),
        ('leaf certificate made nonstrict zero', lambda p: put(result(p)['certifiedLeaves'][0], 'lowerGapCertificate', [0, 0])),
        ('leaf certificate fabricated positive', lambda p: put(result(p)['certifiedLeaves'][0], 'lowerGapCertificate', [1e10, 1e10])),
        ('leaf linked to absent audit', lambda p: put(result(p)['certifiedLeaves'][0], 'auditIndex', 9999)),
        ('boolean leaf audit ordinal alias', lambda p: put(result(p)['certifiedLeaves'][0], 'auditIndex', False)),
        ('false complete prefix across unexamined right side', lambda p: put(result(p, prefix), 'safePrefix', [0, 1])),
        ('empty proof masquerades as safe parameter zero', lambda p: put(result(p, without_prefix), 'safePrefix', [0, 0])),
        ('unexamined frontier cell dropped', lambda p: result(p, frontier)['frontier'].pop()),
        ('unexamined frontier cell shifted one ulp', lambda p: result(p, frontier)['frontier'][0]['parameter'].__setitem__(0, math.nextafter(result(p, frontier)['frontier'][0]['parameter'][0], 1))),
        ('unproved current erased', lambda p: put(result(p, frontier), 'current', None)),
        ('partition count invented', lambda p: put(result(p), 'partitionLeaves', result(p)['partitionLeaves'] + 1)),
        ('maximum depth invented', lambda p: put(result(p), 'maximumDepth', result(p)['maximumDepth'] + 1)),
        ('boolean depth alias', lambda p: put(result(p), 'maximumDepth', False)),
        ('boolean partition count alias', lambda p: put(result(p), 'partitionLeaves', True)),
        ('split node changed into certified sample', lambda p: put(next(a for a in result(p, split)['audits'] if a['outcome'] == 'split'), 'outcome', 'separated')),
        ('audit prefix dropped', lambda p: result(p, split)['audits'].pop(0)),
        ('audit midpoint changed', lambda p: put(audit(p), 'midpoint', 0)),
        ('whole path box excludes actual endpoint', lambda p: corrupt_box(p, 'pathBounds')),
        ('midpoint box excludes exact path', lambda p: corrupt_box(p, 'pointBounds')),
        ('displacement squared upper underestimated', lambda p: put(audit(p), 'displacementSquaredBound', [0, 0])),
        ('displacement root underestimated', lambda p: put(audit(p), 'displacementRoot', [0, 0])),
        ('displacement root square and root jointly underestimated', lambda p: (put(audit(p), 'displacementSquaredBound', [0, 0]), put(audit(p), 'displacementRoot', [0, 0]))),
        ('error squared upper underestimated', lambda p: put(error_audit(p), 'errorSquaredBound', [0, 0])),
        ('error root underestimated', lambda p: put(error_audit(p), 'errorRoot', [0, 0])),
        ('anchor rounding error omitted jointly', lambda p: (put(error_audit(p), 'errorSquaredBound', [0, 0]), put(error_audit(p), 'errorRoot', [0, 0]))),
        ('root upper negative', lambda p: put(audit(p), 'displacementRoot', [-1, -1])),
        ('clearance expression not enclosed', lambda p: put(audit(p), 'clearanceCertificate', [1e11, 1e11])),
        ('penetration expression not enclosed', lambda p: put(audit(p), 'penetrationCertificate', [-1e11, -1e11])),
        ('witness parameter changed', lambda p: put(result(p, witness)['witness'], 'parameter', 0)),
        ('witness positive upper-gap', lambda p: put(result(p, witness)['witness'], 'upperGapCertificate', [0, 1])),
        ('witness error omitted', lambda p: put(result(p, witness)['witness'], 'errorUpper', -1)),
        ('witness forged as whole-path separation', lambda p: put(result(p, witness), 'status', 'separated')),
        ('witness exact path replaced by arbitrary anchor', lambda p: put(result(p, witness)['witness'], 'exactPathBounds', [[1e13, 1e13]] * 3)),
        ('source ID changed in owned snapshot', lambda p: put(result(p, queried)['snapshot']['triangles'][0], 'id', 0)),
        ('source signed zero lost in owned snapshot', flip_zero),
        ('source endpoint changed in owned snapshot', lambda p: put(result(p, queried)['snapshot'], 'end', [9e11] * 3)),
        ('owned settings changed', lambda p: put(result(p, queried)['snapshot']['settings'], 'maxDepth', 31)),
        ('unqueried cell borrows old mesh status', lambda p: put(result(p, unqueried)['audits'][-1], 'meshStatus', 0)),
        ('last mesh moved to unexamined cell', lambda p: put(result(p, queried), 'lastMeshAuditIndex', len(result(p, queried)['audits']))),
        ('failed far row omitted', drop_failed_row),
        ('last mesh geometry moved', lambda p: put(result(p, queried)['lastMesh']['rows'][0]['query']['geometry'], 'closest', [[1e11, 1e11]] * 3)),
        ('boolean last mesh status alias', lambda p: put(result(p, queried)['lastMesh'], 'status', False)),
        ('negative-zero last mesh status alias', lambda p: put(result(p, queried)['lastMesh'], 'status', -0.0)),
        ('boolean last mesh reason alias', lambda p: put(result(p, queried)['lastMesh'], 'reason', False)),
        ('boolean audit reason alias', lambda p: put(audit(p), 'meshReason', False)),
        ('boolean audit status alias', lambda p: put(audit(p), 'meshStatus', False)),
        ('last mesh possible IDs erased', lambda p: put(result(p, queried)['lastMesh']['nearest'], 'possibleSurfaceIds', [])),
        ('work sum changed', lambda p: put(result(p)['work'], 'meshQueries', result(p)['work']['meshQueries'] + 1)),
        ('boolean work counter', lambda p: put(result(p)['work'], 'meshQueries', True)),
        ('reservation charged as returned actual work', lambda p: put(result(p)['work'], 'sqrtRefinements', 512)),
        ('global work certainty falsely missing on success', lambda p: put(result(p)['work'], 'workExact', False)),
        ('work conservative upper lower than actual', lambda p: put(result(p)['work'], 'sqrtRefinementsUpper', -1)),
        ('audit delta replaced by cumulative work', lambda p: put(result(p, multi_query)['audits'][-1], 'work', deepcopy(result(p, multi_query)['work']))),
        ('preflight given a successful source snapshot', lambda p: put(result(p, invalid), 'snapshot', deepcopy(result(p, queried)['snapshot']))),
        ('preflight given safe prefix', lambda p: put(result(p, invalid), 'safePrefix', [0, 1])),
        ('preflight given old last mesh', lambda p: put(result(p, invalid), 'lastMesh', deepcopy(result(p, queried)['lastMesh']))),
    ]
    records = []
    for name, mutate in mutations:
        packet = deepcopy(data)
        mutate(packet)
        try:
            oracle.verify(packet)
        except (AssertionError, ValueError, TypeError, KeyError, OverflowError) as error:
            records.append({'name': name, 'rejected': True, 'diagnostic': str(error)})
        else:
            raise AssertionError('corruption accepted: ' + name)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', nargs='?')
    parser.add_argument('--output')
    args = parser.parse_args()
    stream = io.StringIO()
    run = unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExactTrajectoryReferenceTests))
    need = oracle.need
    need(run.wasSuccessful(), stream.getvalue())
    if not args.fixture:
        print(json.dumps({'status': 'PASS', 'selfTestGroups': run.testsRun}))
        return
    data = oracle.load(args.fixture)
    baseline = oracle.verify(data)
    records = controls(data)
    for name, text in [('overflow decimal', '{"x":1e999}'), ('underflow decimal', '{"x":1e-999}'),
                       ('duplicate JSON key', '{"x":0,"x":1}'), ('nonfinite JSON', '{"x":Infinity}'),
                       ('unpaired Unicode', '{"x":"\\ud800"}')]:
        try:
            oracle.loads(text)
        except (AssertionError, ValueError, UnicodeError) as error:
            records.append({'name': name, 'rejected': True, 'diagnostic': str(error)})
        else:
            raise AssertionError('JSON corruption accepted: ' + name)
    permuted = deepcopy(data)
    permuted['fixtures'].reverse()
    for i, fixture in enumerate(permuted['fixtures']):
        fixture['name'] = 'independent-label-' + str(i)
    need(oracle.verify(permuted) == baseline, 'labels/order independent whole-path reference')
    optimized = subprocess.run([sys.executable, '-O', str(root / 'scripts/verify-sphere-triangle-mesh-trajectory.py'), args.fixture],
                               capture_output=True, text=True, timeout=60)
    need(optimized.returncode != 0 and 'without Python -O' in optimized.stderr, 'optimized Python cannot bypass checks')
    records.append({'name': 'Python -O rejected', 'rejected': True, 'diagnostic': optimized.stderr.strip().splitlines()[-1]})
    report = {'status': 'PASS', 'baseline': baseline, 'selfTestGroups': run.testsRun,
              'rejectedControls': records, 'labelAndOrderIndependent': True}
    if args.output:
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=False)
        (output / 'negative-controls.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        (output / 'reference.json').write_text(json.dumps(baseline, indent=2) + '\n', encoding='utf-8')
        (output / 'reference-self-tests.txt').write_text(stream.getvalue(), encoding='utf-8')
        (output / 'commands.json').write_text(json.dumps({'argv': sys.argv, 'python': sys.version}, indent=2) + '\n', encoding='utf-8')
        paths = [Path(args.fixture), root / 'scripts/verify-sphere-triangle-mesh-trajectory.py', Path(__file__)]
        provenance = [{'path': str(p.resolve()), 'bytes': len(p.read_bytes()), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
        (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'fixtures': baseline['fixtures'], 'selfTestGroups': run.testsRun,
                      'rejectedControls': len(records), 'labelAndOrderIndependent': True}))


if __name__ == '__main__':
    main()
