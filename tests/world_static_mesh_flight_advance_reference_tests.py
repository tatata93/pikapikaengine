"""Self/alteration controls for the independent advance transaction checker.

Copied JSON metadata is artificial adversarial input, not Native fault injection.
Positive physics/transaction acceptance always starts from the actual input file.
"""
from pathlib import Path
from fractions import Fraction
import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-advance.py'
spec = importlib.util.spec_from_file_location('advance_reference_controls', CHECKER)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)
need = ref.need


def stamp(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, allow_nan=False)
        stream.write('\n')


def rejected(action):
    try:
        action()
    except (AssertionError, ValueError):
        return True
    raise AssertionError('Altered evidence was accepted')


def self_tests():
    groups = []
    def test(name, action):
        action()
        groups.append(name)
    test('protected-integer-rounding-eleven-self-checks', lambda: need(ref.clock.self_test() == 11, 'integer clock reference'))
    test('ties-even-above-one', lambda: need(ref.clock.rn(Fraction(1)+Fraction(3,2**53)) == '3ff0000000000002', 'ties even'))
    test('subnormal-half-tie', lambda: need(ref.clock.rn(Fraction(1,2**1075)) == '0000000000000000', 'underflow RN tie'))
    test('signed-zero-copy-rejected', lambda: rejected(lambda: ref.equal(-0., 0., 'signed zero')))
    test('integer-bool-alias-rejected', lambda: rejected(lambda: ref.uint(False, 2, 'metadata')))
    test('float-zero-integer-alias-rejected', lambda: rejected(lambda: ref.uint(-0., 2, 'metadata')))
    test('duplicate-json-key-rejected', lambda: rejected(lambda: ref.loads('{"a":1,"a":2}')))
    test('nonfinite-constant-rejected', lambda: rejected(lambda: ref.loads('{"a":NaN}')))
    test('nonfinite-exponent-rejected', lambda: rejected(lambda: ref.loads('{"a":1e999}')))
    test('underflow-token-rejected', lambda: rejected(lambda: ref.loads('{"a":1e-999}')))
    test('json-negative-zero-retained', lambda: need(ref.bits(ref.loads('-0')).hex() == '8000000000000000', 'negative zero load'))
    test('exact-field-set-rejected', lambda: rejected(lambda: ref.fields({'a':1,'x':2}, {'a'}, 'shape')))
    test('canonical-progress-tick-rejected', lambda: rejected(lambda: ref.progress_shape({'time':0,'ticks':True})))
    test('nonfinite-direct-object-rejected', lambda: rejected(lambda: ref.finite_tree({'x':float('inf')})))
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(__debug__, 'Run controls without Python -O')
    out = args.output.resolve()
    need(out.is_relative_to(ROOT) and out != ROOT, 'Fresh workspace output child')
    out.mkdir(parents=True, exist_ok=False)
    watched = [CHECKER, Path(__file__).resolve(), args.fixture.resolve(),
               ROOT/'scripts/verify-world-static-mesh-flight-guard.py',
               ROOT/'reports/world-static-mesh-flight-advance-recipes/clock-reference.py']
    before = [stamp(p) for p in watched]
    write(out/'source-before.json', before)
    commands, controls = [], []
    started = time.perf_counter()
    try:
        self_groups = self_tests()
        data = ref.load(args.fixture)
        actual = ref.verify(data)
        write(out/'actual-reference.json', actual)
        changed = copy.deepcopy(data)
        changed['fixtures'].reverse()
        for i, row in enumerate(changed['fixtures']):
            row['name'] = 'independent-label-'+str(i)
        independent = ref.verify(changed)
        need(actual == independent, 'all input/array ordinals preserved while names/traversal change')
        rows = data['fixtures']
        successful = next(i for i, r in enumerate(rows) if r['report']['committed'] and r['input']['bodies'])
        failed = next(i for i, r in enumerate(rows) if not r['report']['committed'] and r['report']['guard'] is not None and r['input']['bodies'])
        clock_failed = next(i for i, r in enumerate(rows) if r['report']['guard'] is None)

        def document_control(name, mutate):
            altered = copy.deepcopy(data)
            mutate(altered)
            rejected(lambda: ref.verify(altered))
            controls.append({'name':name,'scope':'Artificial copied envelope/source alteration','rejected':True})

        def row_control(name, ordinal, mutate):
            altered = copy.deepcopy(rows[ordinal])
            mutate(altered)
            rejected(lambda: ref.verify_fixture(altered, data['layoutSizes'], data['advanceLayoutSizes'], ref.new_stats()))
            controls.append({'name':name,'fixtureOrdinal':ordinal,'scope':'Artificial copied transaction alteration','rejected':True})

        def after_body(row, key, value):
            row['inputAfter']['bodies'][0][key] = copy.deepcopy(value)
            row['worldAfter']['bodies'][0][key] = copy.deepcopy(value)

        document_control('schema-bool-alias', lambda d:d.update(schema=True))
        document_control('unknown-kind', lambda d:d.update(kind='other'))
        document_control('missing-fixture-tail', lambda d:d['fixtures'].pop())
        document_control('unexpected-envelope-key', lambda d:d.update(extra=None))
        document_control('missing-original-input-key', lambda d:d['fixtures'][successful]['input'].pop('gravity'))
        document_control('changed-original-input-fingerprint', lambda d:d['fixtures'][successful]['input'].update(horizon=.03125))
        document_control('initial-progress-tick-bool', lambda d:d['initialProgress'].update(ticks=True))
        document_control('sizeof-metadata-bool', lambda d:d['advanceLayoutSizes'].update(Progress=True))
        row_control('missing-report-key', successful, lambda r:r['report'].pop('guardMessage'))
        row_control('unexpected-report-key', successful, lambda r:r['report'].update(extra=0))
        row_control('unknown-status', successful, lambda r:r['report'].update(status='accepted'))
        row_control('unknown-reason', successful, lambda r:r['report'].update(reason='other'))
        row_control('integer-commit-flag', successful, lambda r:r['report'].update(committed=1))
        row_control('profile-unchecked', successful, lambda r:r['report'].update(advanceProfileChecked=False))
        row_control('profile-mismatch', successful, lambda r:r['report'].update(advanceProfileMatches=False))
        row_control('binding-profile-bool', successful, lambda r:r['report']['binding'].update(profile=True))
        row_control('guard-binding-identity-divergence', successful, lambda r:r['report']['binding'].update(buildId='f'*64))
        row_control('guard-message-null', successful, lambda r:r['report'].update(guardMessage=None))
        row_control('report-message-not-text', successful, lambda r:r['report'].update(message=False))
        row_control('requested-horizon-substitution', successful, lambda r:r['report'].update(requestedDt=0.))
        row_control('advanced-horizon-zero', successful, lambda r:r['report'].update(advancedDt=0.))
        row_control('original-progress-substitution', successful, lambda r:r['report']['originalProgress'].update(time=-0.))
        row_control('proposed-progress-substitution', successful, lambda r:r['report']['proposedProgress'].update(time=0.))
        row_control('actual-progress-substitution', successful, lambda r:r['progressAfter'].update(time=0.))
        row_control('proposed-tick-bool', successful, lambda r:r['report']['proposedProgress'].update(ticks=True))
        row_control('actual-tick-zero', successful, lambda r:r['progressAfter'].update(ticks=0))
        row_control('clock-missing-field', successful, lambda r:r['report']['clock'].pop('representedDt'))
        row_control('represented-difference-substitution', successful, lambda r:r['report']['clock'].update(representedDt=0.))
        for key in ('timeSum','representedDifference','sumRoundingError'):
            # A singleton far from the exact rational target cannot contain it.
            row_control('clock-enclosure-'+key, successful, lambda r,k=key:r['report']['clock'].update({k:[-2.,-1.]}))
        for key in sorted(ref.WORK_KEYS):
            row_control('work-alteration-'+key, successful, lambda r,k=key:r['report']['work'].__setitem__(k,r['report']['work'][k]+1))
        row_control('work-bool-alias', successful, lambda r:r['report']['work'].update(guardQueriesAttempted=True))
        row_control('work-negative-zero-alias', successful, lambda r:r['report']['work'].update(originBodiesChecked=-0.))
        for key in sorted(ref.STORAGE_KEYS):
            row_control('storage-alteration-'+key, successful, lambda r,k=key:r['report']['storage'].__setitem__(k,r['report']['storage'][k]+1))
        row_control('candidate-force-not-consumed', successful, lambda r:after_body(r,'force',[1.,0.,0.]))
        row_control('candidate-force-negative-zero', successful, lambda r:after_body(r,'force',[-0.,0.,0.]))
        row_control('world-after-body-divergence', successful, lambda r:r['worldAfter']['bodies'][0].update(radius=1.))
        row_control('candidate-prefix-only', successful, lambda r:r['report']['guard']['candidateBodies'].pop())
        row_control('guard-pair-tail-missing', successful, lambda r:r['report']['guard']['pairs'].pop())
        row_control('guard-accounting-altered', successful, lambda r:r['report']['guard']['work'].update(childCallsReturned=0))
        row_control('unknown-nested-guard-status', successful, lambda r:r['report']['guard'].update(status='safe'))
        row_control('source-after-mesh-revision', successful, lambda r:r['inputAfter']['meshes'][0].update(revision=99))
        row_control('source-after-gravity', successful, lambda r:r['inputAfter'].update(gravity=[0.,0.,0.]))
        for key in ('captureComplete','sourceUnchanged','settingsUnchanged','horizonUnchanged','planesUnchanged','gravityUnchanged'):
            row_control('observation-false-'+key, successful, lambda r,k=key:r['observations'].__setitem__(k,False))
        row_control('observation-call-bool', successful, lambda r:r['observations'].update(advanceCalls=True))
        row_control('success-claims-failure-observation', successful, lambda r:r['observations'].update(failureAtomicObserved=True))
        row_control('pointer-ordinal-bool', successful, lambda r:r['observations']['pointerStability']['bodies'][0].update(ordinal=False))
        row_control('pointer-id-bool', successful, lambda r:r['observations']['pointerStability']['bodies'][0].update(originalId=True))
        row_control('pointer-address-changed', successful, lambda r:r['observations']['pointerStability']['bodies'][0].update(sameOrdinalAddress=False))
        row_control('pointer-observation-bool-alias', successful, lambda r:r['observations']['pointerStability'].update(bodyStorageStable=1))
        row_control('pointer-source-tail-missing', successful, lambda r:r['observations']['pointerStability']['meshFaceStorageStable'].pop())
        row_control('failed-world-mutated', failed, lambda r:after_body(r,'force',[1.,0.,0.]))
        row_control('failed-progress-mutated', failed, lambda r:r['progressAfter'].update(ticks=18))
        row_control('failed-advanced-negative-zero', failed, lambda r:r['report'].update(advancedDt=-0.))
        row_control('failed-invents-body-store', failed, lambda r:r['report']['work'].update(bodyAssignments=1))
        row_control('failed-stage-unknown', failed, lambda r:r['report']['failure'].update(stage='later'))
        row_control('failed-atomic-observation-false', failed, lambda r:r['observations'].update(failureAtomicObserved=False))
        row_control('clock-refusal-query-invented', clock_failed, lambda r:r['report']['work'].update(guardQueriesAttempted=1))
        row_control('clock-refusal-stage-substitution', clock_failed, lambda r:r['report']['failure'].update(stage='guard'))
        row_control('clock-refusal-proposal-invented', clock_failed, lambda r:r['report'].update(proposedProgress={'time':.125,'ticks':18}))
        row_control('clock-refusal-message-invented', clock_failed, lambda r:r['report'].update(guardMessage='not returned'))

        argv = [sys.executable, '-O', str(CHECKER), str(args.fixture.resolve())]
        start = time.perf_counter()
        optimized = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=120, check=False)
        (out/'optimized.stdout.txt').write_bytes(optimized.stdout)
        (out/'optimized.stderr.txt').write_bytes(optimized.stderr)
        optimized_record = {'argv':argv,'exit':optimized.returncode,'elapsedSeconds':time.perf_counter()-start,
                            'stdout':stamp(out/'optimized.stdout.txt'),'stderr':stamp(out/'optimized.stderr.txt')}
        write(out/'optimized-command.json', optimized_record)
        commands.append(optimized_record)
        need(optimized.returncode != 0 and b'Protected reference stack requires normal Python' in optimized.stderr,
             'optimized checker must refuse explicitly, not silently skip protected checks')
        controls.append({'name':'optimized-python-refused','scope':'Actual separate optimized process','rejected':True})
        result = {'status':'PASS','baseline':actual,'selfTestGroups':len(self_groups),'selfTests':self_groups,
                  'rejectedControls':controls,'negativeControls':len(controls),'labelAndOrderIndependent':True,
                  'optimizedPythonRejected':{'status':'PASS','exitCode':optimized.returncode},
                  'scope':'Copied JSON adversarial controls and integer/Fraction self checks. Not Native allocation/nonreturn/CPU fault injection, binary reexecution or complete machine clock/commit attestation.'}
        write(out/'negative-controls.json', result)
    finally:
        after = [stamp(p) for p in watched]
        write(out/'source-after.json', after)
        write(out/'provenance.json', {'sourceBefore':before,'sourceAfter':after,'sourceStable':before==after,
              'commands':commands,'elapsedSeconds':time.perf_counter()-started})
        need(before == after, 'Original fixture/protected references/checker sources must remain byte identical')
    print(json.dumps({'status':'PASS','fixtures':actual['fixtures'],'selfTestGroups':len(self_groups),
                      'negativeControls':len(controls),'labelAndOrderIndependent':True}))


if __name__ == '__main__':
    main()
