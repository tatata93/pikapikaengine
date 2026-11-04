"""Independent accepted-only Fraction audit of actual owned flight SDK DTOs."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('owned_flight_wire_reference', HERE / 'verify-sphere-triangle-mesh-flight-native-sdk.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
need, fields = wire.need, wire.fields
MESH_STATUS = ['completed', 'invalid_input', 'budget_exceeded', 'row_failure', 'numerical_failure', 'unsupported_environment']
MESH_REASON = ['none', 'settings', 'surface_count', 'surface_budget', 'surface_id', 'duplicate_id', 'input_domain', 'row_failed', 'aggregate_inconsistent', 'nonfinite_intermediate', 'allocation_failure', 'environment']
SINGLE_STATUS = ['completed', 'invalid_input', 'degenerate', 'ill_conditioned', 'quality_unresolved', 'budget_exceeded', 'numerical_failure', 'unsupported_environment']
SINGLE_REASON = ['none', 'settings', 'surface_id', 'input_domain', 'zero_cross', 'cross_uncertain', 'conditioning_rejected', 'conditioning_uncertain', 'candidate_budget', 'no_candidate', 'local_width', 'zero_distance', 'distance_uncertain', 'sqrt_budget', 'normal_width', 'nonfinite_intermediate', 'allocation_failure', 'environment']
FEATURE = ['face', 'edge_ab', 'edge_bc', 'edge_ca', 'vertex_a', 'vertex_b', 'vertex_c']
DISPOSITION = ['retained', 'outside_simplex', 'kkt_violated']
RELATION = ['separated', 'penetrating', 'touching', 'boundary_unresolved']
CCD = ['none', 'invalid_input', 'initial_contact', 'query_unresolved', 'event_budget', 'segment_budget', 'query_budget', 'root_budget', 'geometric_guard', 'propagation_failure', 'solver_failure', 'sustained_contact_required', 'numerical_failure']


def ordinal(value, choices):
    need(type(value) is str and value in choices, 'owned known string enum')
    return choices.index(value)


def project_mesh(mesh):
    mesh = copy.deepcopy(mesh)
    mesh['status'] = ordinal(mesh['status'], MESH_STATUS)
    mesh['reason'] = ordinal(mesh['reason'], MESH_REASON)
    for row in mesh['rows']:
        q = row['query']
        if q is None:
            continue
        q['status'] = ordinal(q['status'], SINGLE_STATUS)
        q['reason'] = ordinal(q['reason'], SINGLE_REASON)
        if q['geometry'] is not None:
            q['geometry']['relation'] = ordinal(q['geometry']['relation'], RELATION)
        for c in q['candidates']:
            c['feature'] = ordinal(c['feature'], FEATURE)
            c['disposition'] = ordinal(c['disposition'], DISPOSITION)
    return mesh


def project_held(result):
    result = copy.deepcopy(result)
    for audit in result['audits']:
        for key, choices in [('meshStatus', MESH_STATUS), ('meshReason', MESH_REASON)]:
            if audit[key] is not None:
                audit[key] = ordinal(audit[key], choices)
    if result['lastMesh'] is not None:
        result['lastMesh'] = project_mesh(result['lastMesh'])
    return result


def project_owned(result, mode):
    need(type(result) is dict and 'originalInput' in result, 'owned model plus explicit originalInput')
    result = copy.deepcopy(result)
    original = result.pop('originalInput')  # This one declared addition alone is removed.
    if mode == 0:
        result = project_held(result)
    else:
        if result['flightFailure'] is not None:
            result['flightFailure'] = ordinal(result['flightFailure'], CCD)
        if result['inflated'] is not None:
            result['inflated'] = project_held(result['inflated'])
    return result, original


def verify_owned(corpus, captured):
    fields(captured, {'schema', 'kind', 'fixtures'}, 'owned fixture envelope')
    need(type(captured['schema']) is int and captured['schema'] == 1 and captured['kind'] == 'sphere-triangle-mesh-flight-owned-sdk-dtos', 'owned envelope version')
    need(type(captured['fixtures']) is list and len(captured['fixtures']) == len(corpus) == 183, 'fixed complete owned input corpus')
    model_compare, original_compare, source_compare = wire.Compare(), wire.Compare(), wire.Compare()
    stats = {key: {'models': 0, 'hostRejected': 0, 'mathematicsFixturesVerified': 0,
                   'mathematics': wire.guard.held_stats() if key == 'held' else wire.guard.new_stats(0)}
             for key in ['held', 'guard', 'supplemental']}
    accepted, expected_accepted = [], []
    for (cohort, fixture, mode), row in zip(corpus, captured['fixtures']):
        fields(row, {'cohort', 'name', 'mode', 'input', 'result', 'hostError'}, 'owned captured row')
        need(type(row['mode']) is int and (row['cohort'], row['name'], row['mode']) == (cohort, fixture['name'], mode), 'owned row identity')
        source_compare.equal(row['input'], fixture['input'], 'full original caller source')
        source = row['input']
        host = wire.host_path(source, mode)[3]
        if host is not None:
            need(row['result'] is None and type(row['hostError']) is str and row['hostError'], 'host refusal has no Native result fill')
            stats[cohort]['hostRejected'] += 1
            continue
        need(row['hostError'] is None and type(row['result']) is dict, 'actual accepted owned model required')
        result, original = project_owned(row['result'], mode)
        model_compare.equal(result, fixture['result'], 'complete owned Native observable projection')
        original_compare.equal(original, dict(copy.deepcopy(source), echo=wire.query_values(source, mode)), 'owned originalInput all bits')
        if mode == 0:
            wire.held.verify_fixture(source, result, stats[cohort]['mathematics'])
        else:
            wire.guard.verify_fixture(source, result, stats[cohort]['mathematics'])
        stats[cohort]['models'] += 1
        stats[cohort]['mathematicsFixturesVerified'] += 1
        accepted.append((cohort, {'input': source}, mode))
        expected_accepted.append((cohort, fixture, mode))
    counts = {key: value['models'] for key, value in stats.items()}
    need(counts == {'held': 74, 'guard': 95, 'supplemental': 4}, 'accepted-only measured cohort counts')
    need(sum(s['hostRejected'] for s in stats.values()) == 10, 'explicit host rejected input count')
    fingerprint = wire.corpus_fingerprint(accepted)
    need(fingerprint == wire.corpus_fingerprint(expected_accepted) == '684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb', 'accepted complete original source fingerprint')
    return {'status': 'PASS', 'fixtures': 183, 'actualModels': 173, 'hostRejected': 10,
            'modelNumericBits': model_compare.numeric_count, 'modelNegativeZeroBits': model_compare.negative_zeros,
            'originalInputNumericBits': original_compare.numeric_count, 'originalInputNegativeZeroBits': original_compare.negative_zeros,
            'sourceNumericBits': source_compare.numeric_count, 'sourceNegativeZeroBits': source_compare.negative_zeros,
            'acceptedInputFingerprint': fingerprint, 'cohorts': stats,
            'scope': 'Every actual accepted owned DTO field is compared, then independently Fraction-verified. Host refusals remain null. Only declared originalInput is removed and string enums are projected; no Native result supplementation. Aggregate mathematics.fixtures is unused by per-fixture helpers; explicit mathematicsFixturesVerified records actual calls.'}


def negative_controls(corpus, captured):
    results = []
    accepted = next(i for i, r in enumerate(captured['fixtures']) if r['result'] is not None)
    guard = next(i for i, r in enumerate(captured['fixtures']) if r['mode'] == 1 and r['result'] is not None and r['result']['candidate'] is not None)
    held = next(i for i, r in enumerate(captured['fixtures']) if r['mode'] == 0 and r['result'] is not None and len(r['result']['audits']) == 256)
    host = next(i for i, r in enumerate(captured['fixtures']) if r['hostError'] is not None)

    def add(name, index, mutation):
        altered = copy.deepcopy(captured)
        mutation(altered['fixtures'][index])
        try:
            verify_owned(corpus, altered)
        except (AssertionError, KeyError, ValueError, TypeError, OverflowError) as error:
            results.append({'name': name, 'rejected': True, 'diagnostic': str(error)})
        else:
            raise AssertionError('owned mutation accepted: ' + name)

    add('missing result key', accepted, lambda r: r['result'].pop('reason'))
    add('extra result key', accepted, lambda r: r['result'].update(message='invented'))
    add('boolean enum alias', accepted, lambda r: r['result'].update(status=False))
    add('original echo negative zero corruption', accepted, lambda r: r['result']['originalInput']['echo'].__setitem__(-1, -0.0))
    add('caller source changed', accepted, lambda r: r['input']['triangles'][0]['vertices'][0].__setitem__(0, 999.0))
    add('audit256 tail removed', held, lambda r: r['result']['audits'].pop())
    add('partition tail removed', held, lambda r: r['result']['partition'].pop())
    add('work altered', held, lambda r: r['result']['work'].update(sqrtRefinements=0))
    add('nested radius is original radius', guard, lambda r: r['result']['inflated']['snapshot']['input'].update(radius=r['input']['body']['radius']))
    add('guard error erased', guard, lambda r: r['result']['tube'].update(positionError=0.0))
    add('candidate body field missing', guard, lambda r: r['result']['candidate'].pop('torque'))
    add('endpoint flag false', guard, lambda r: r['result']['endpoint'].update(exactContained=False))
    add('host receives copied model', host, lambda r: r.update(result=copy.deepcopy(captured['fixtures'][accepted]['result'])))
    add('host classification erased', host, lambda r: r.update(hostError=None))
    add('mode identity changed', accepted, lambda r: r.update(mode=1-r['mode']))
    return {'status': 'PASS', 'count': len(results), 'rejectedControls': results,
            'scope': 'Copied actual owned DTO mutations test independent field/bit fidelity, not production decoder fault injection or mathematical detection of arbitrary self-consistent counterfeit results.'}


def main():
    need(__debug__, 'run owned flight reference without Python -O')
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['held', 'guard', 'supplemental', 'owned', 'output']:
        parser.add_argument(name)
    args = parser.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    h, g, s = map(wire.held.load, [args.held, args.guard, args.supplemental])
    pure = {'held': wire.held.verify(h), 'guard': wire.guard.verify(g), 'supplemental': wire.guard.verify_supplemental(s)}
    corpus = [('held', f, 0) for f in h['fixtures']] + [('guard', f, 1) for f in g['fixtures']] + [('supplemental', f, 1) for f in s['fixtures']]
    captured = wire.held.load(args.owned)
    report = verify_owned(corpus, captured)
    controls = negative_controls(corpus, captured)
    command = [sys.executable, '-O', str(Path(__file__).resolve()), args.held, args.guard, args.supplemental, args.owned, str(out/'optimized-must-not-run')]
    process = subprocess.run(command, capture_output=True, timeout=30)
    for stream in ['stdout', 'stderr']:
        wire.write_new(out / ('optimized.' + stream + '.txt'), getattr(process, stream))
    wire.write_new(out/'optimized-command.json', json.dumps({'command': command, 'exitCode': process.returncode}, indent=2)+'\n')
    need(process.returncode != 0 and b'without Python -O' in process.stderr, 'optimized owned reference fails closed')
    wire.write_new(out/'negative-controls.json', json.dumps(controls, indent=2)+'\n')
    report.update(pureNativeReference=pure, negativeControls=controls, optimizedPythonRejected=True,
                  sources={str(Path(p).resolve()): wire.file_info(Path(p)) for p in [args.held, args.guard, args.supplemental, args.owned, __file__, str(HERE/'verify-sphere-triangle-mesh-flight-native-sdk.py')]})
    wire.write_new(out/'report.json', json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
