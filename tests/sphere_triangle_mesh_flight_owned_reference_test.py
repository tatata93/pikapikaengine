"""Synthetic codec controls; these are not actual owned-WASM executions."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('flight_owned_independent', ROOT/'scripts/verify-sphere-triangle-mesh-flight-owned.py')
owned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned)


def string_mesh(mesh):
    mesh = copy.deepcopy(mesh)
    mesh['status'] = owned.MESH_STATUS[mesh['status']]
    mesh['reason'] = owned.MESH_REASON[mesh['reason']]
    for row in mesh['rows']:
        q = row['query']
        if q is None:
            continue
        q['status'] = owned.SINGLE_STATUS[q['status']]
        q['reason'] = owned.SINGLE_REASON[q['reason']]
        if q['geometry'] is not None:
            q['geometry']['relation'] = owned.RELATION[q['geometry']['relation']]
        for c in q['candidates']:
            c['feature'] = owned.FEATURE[c['feature']]
            c['disposition'] = owned.DISPOSITION[c['disposition']]
    return mesh


def string_held(h):
    h = copy.deepcopy(h)
    for a in h['audits']:
        if a['meshStatus'] is not None:
            a['meshStatus'] = owned.MESH_STATUS[a['meshStatus']]
        if a['meshReason'] is not None:
            a['meshReason'] = owned.MESH_REASON[a['meshReason']]
    if h['lastMesh'] is not None:
        h['lastMesh'] = string_mesh(h['lastMesh'])
    return h


class OwnedReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = ['reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json',
                 'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/native-fixtures.json',
                 'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/supplemental-fixtures.json']
        cls.corpus = []
        cls.capture = {'schema': 1, 'kind': 'sphere-triangle-mesh-flight-owned-sdk-dtos', 'fixtures': []}
        for index, file in enumerate(paths):
            cohort, mode = ['held', 'guard', 'supplemental'][index], int(index != 0)
            for f in owned.wire.held.load(ROOT/file)['fixtures']:
                cls.corpus.append((cohort, f, mode))
                source = copy.deepcopy(f['input'])
                host = owned.wire.host_path(source, mode)[3]
                result = None
                if host is None:
                    if mode == 0:
                        result = string_held(f['result'])
                    else:
                        result = copy.deepcopy(f['result'])
                        if result['flightFailure'] is not None:
                            result['flightFailure'] = owned.CCD[result['flightFailure']]
                        if result['inflated'] is not None:
                            result['inflated'] = string_held(result['inflated'])
                    result['originalInput'] = dict(copy.deepcopy(source), echo=owned.wire.query_values(source, mode))
                cls.capture['fixtures'].append({'cohort': cohort, 'name': f['name'], 'mode': mode, 'input': source,
                                                'result': result, 'hostError': None if host is None else 'Synthetic host classification only'})

    def test_full_synthetic_projection_and_fraction(self):
        report = owned.verify_owned(self.corpus, self.capture)
        self.assertEqual((report['fixtures'], report['actualModels'], report['hostRejected']), (183, 173, 10))
        self.assertEqual([report['cohorts'][c]['mathematicsFixturesVerified'] for c in ['held', 'guard', 'supplemental']], [74, 95, 4])

    def test_fifteen_independent_fidelity_negatives(self):
        controls = owned.negative_controls(self.corpus, self.capture)
        self.assertEqual(controls['count'], 15)
        self.assertTrue(all(r['rejected'] for r in controls['rejectedControls']))

    def test_strict_loader_nonfinite_underflow_duplicates(self):
        for text in ['{"x":1e999}', '{"x":1e-999}', '{"x":0,"x":1}', '{"x":NaN}']:
            with self.assertRaises((AssertionError, ValueError)):
                owned.wire.held.loads(text)

    def test_signed_zero_roundtrip(self):
        x = {'zero': -0.0, 'tiny': float.fromhex('0x0.0000000000001p-1022')}
        y = owned.wire.held.loads(owned.wire.signed_json(x))
        self.assertEqual(owned.wire.bits(y['zero']), '8000000000000000')
        self.assertEqual(owned.wire.bits(y['tiny']), '0000000000000001')

    def test_metadata_bool_and_float_zero_are_distinct(self):
        for value in [False, -0.0]:
            altered = copy.deepcopy(self.capture)
            altered['fixtures'][0]['mode'] = value
            with self.assertRaises(AssertionError):
                owned.verify_owned(self.corpus, altered)

    def test_original_input_is_not_ignored(self):
        altered = copy.deepcopy(self.capture)
        row = next(r for r in altered['fixtures'] if r['result'] is not None)
        row['result']['originalInput']['echo'].pop()
        with self.assertRaises(AssertionError):
            owned.verify_owned(self.corpus, altered)


if __name__ == '__main__':
    unittest.main()
