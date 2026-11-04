"""Independent scheduler self/alteration controls on actual full transcripts.

Copied metadata/interval alterations are artificial JSON controls, not Native
fault injection. No intermediate World/pointer observations are manufactured.
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
CHECKER = ROOT/'scripts/verify-world-static-mesh-flight-scheduler.py'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('scheduler_full_reference_controls', CHECKER)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)
need = ref.need


def stamp(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=True,allow_nan=False,indent=2)
        stream.write('\n')


def rejected(action):
    try:
        action()
    except (AssertionError,ValueError):
        return True
    raise AssertionError('Altered evidence was accepted')


def self_tests():
    groups=[]
    def test(name, action):
        action();groups.append(name)
    test('protected-eleven-integer-rn-self-checks',lambda:need(ref.credit.reference.self_test()==11,'integer RN reference'))
    test('ties-even-credit',lambda:need(ref.credit.rn(Fraction(1)+Fraction(3,2**53))=='3ff0000000000002','exact ties even'))
    test('subnormal-half-tie',lambda:need(ref.credit.rn(Fraction(1,2**1075))=='0000000000000000','exact underflow tie'))
    test('negative-credit-zero-retained-as-input-bits',lambda:need(ref.credit.number('8000000000000000')==0 and ref.credit.rawbits('8000000000000000')==2**63,'raw signed zero input'))
    test('duplicate-json-key-rejected',lambda:rejected(lambda:ref.loads('{"a":1,"a":2}')))
    test('nonfinite-json-constant-rejected',lambda:rejected(lambda:ref.loads('{"a":NaN}')))
    test('overflow-json-exponent-rejected',lambda:rejected(lambda:ref.loads('{"a":1e999}')))
    test('underflow-json-token-rejected',lambda:rejected(lambda:ref.loads('{"a":1e-999}')))
    test('json-negative-zero-preserved',lambda:need(ref.bits(ref.loads('-0')).hex()=='8000000000000000','negative zero loader'))
    test('bool-is-not-counter',lambda:rejected(lambda:ref.uint(False,8,'ordinal')))
    test('float-negative-zero-is-not-counter',lambda:rejected(lambda:ref.uint(-0.,8,'ordinal')))
    test('bool-is-not-time',lambda:rejected(lambda:ref.fraction(True)))
    test('strict-boolean',lambda:rejected(lambda:ref.advance.boolean(1,'flag')))
    test('exact-field-set',lambda:rejected(lambda:ref.fields({'a':0,'extra':None},{'a'},'shape')))
    test('signed-zero-bit-equality',lambda:rejected(lambda:ref.equal(-0.,0.,'source bits')))
    test('bit-payload-width',lambda:rejected(lambda:ref.credit.rawbits('7ff000000000000')))
    return groups


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    need(__debug__,'Run alteration controls without Python -O')
    out=args.output.resolve()
    need(out.is_relative_to(ROOT) and out!=ROOT,'Fresh workspace child output')
    out.mkdir(parents=True,exist_ok=False)
    watched=[CHECKER,Path(__file__).resolve(),args.fixture.resolve(),
             ROOT/'scripts/verify-world-static-mesh-flight-advance.py',
             ROOT/'scripts/verify-world-static-mesh-flight-scheduler-credit.py',
             ROOT/'scripts/verify-world-static-mesh-flight-guard.py',
             ROOT/'reports/world-static-mesh-flight-advance-recipes/clock-reference.py']
    before=[stamp(p) for p in watched]
    write(out/'source-before.json',before)
    commands=[];controls=[];positive=[];started=time.perf_counter()
    try:
        groups=self_tests()
        data=ref.load(args.fixture);actual=ref.verify(data)
        write(out/'actual-reference.json',actual)
        changed=copy.deepcopy(data);changed['fixtures'].reverse()
        labels={name:'renamed-scenario-'+str(i) for i,name in enumerate(sorted({r['scenario'] for r in changed['fixtures']}))}
        for i,row in enumerate(changed['fixtures']):
            row['name']='independent-label-'+str(i);row['scenario']=labels[row['scenario']]
        need(ref.verify(changed)==actual,'document order and all scenario/fixture labels independent')
        positive.append('document-reversal-and-complete-label-renaming')
        rows=data['fixtures']
        success=next(i for i,r in enumerate(rows) if r['report']['committedTicks']>=2 and r['input']['bodies'])
        failed=next(i for i,r in enumerate(rows) if r['report']['attempts'] and not r['report']['committedTicks'] and r['report']['tickReports'][0]['report']['guard'] is not None)
        prefix=next(i for i,r in enumerate(rows) if r['report']['committedTicks'] and r['report']['status']=='tick_rejected')
        clock_failed=next(i for i,r in enumerate(rows) if r['report']['attempts'] and r['report']['tickReports'][0]['report']['guard'] is None)
        unaccepted=next(i for i,r in enumerate(rows) if not r['report']['elapsedAccepted'])
        no_due=next(i for i,r in enumerate(rows) if r['report']['elapsedAccepted'] and not r['report']['plannedAttempts'])
        large=next(i for i,r in enumerate(rows) if r['report']['attempts']==8)
        edited=next(i for i,r in enumerate(rows) if r['externalEdit'] is not None)

        def document_control(name,mutate):
            altered=copy.deepcopy(data);mutate(altered)
            rejected(lambda:ref.verify(altered))
            controls.append({'name':name,'scope':'Artificial copied document/source/history alteration','rejected':True})

        def row_control(name,ordinal,mutate):
            altered=copy.deepcopy(rows[ordinal]);mutate(altered)
            need(not ref.same(altered,rows[ordinal]),'Control must actually change evidence: '+name)
            rejected(lambda:ref.verify_row(altered,data['layoutSizes'],ref.new_stats()))
            controls.append({'name':name,'fixtureOrdinal':ordinal,'scope':'Artificial copied actual pump/Report alteration; no input-fingerprint shortcut','rejected':True})

        def tick(row,index=0):return row['report']['tickReports'][index]['report']
        def after_body(row,key,value):
            row['worldAfter']['bodies'][0][key]=copy.deepcopy(value)
            row['inputAfter']['bodies'][0][key]=copy.deepcopy(value)

        document_control('schema-bool-alias',lambda d:d.update(schema=True))
        document_control('kind-unknown',lambda d:d.update(kind='other'))
        document_control('envelope-extra-field',lambda d:d.update(extra=None))
        document_control('missing-full-fixture-tail',lambda d:d['fixtures'].pop())
        document_control('source-fingerprint-original-horizon',lambda d:d['fixtures'][success]['input'].update(horizon=.03125))
        document_control('source-fingerprint-original-negative-zero',lambda d:d['fixtures'][0]['input']['gravity'].__setitem__(0,0.))
        document_control('maximum-document-bool',lambda d:d.update(maximumDocumentBytes=True))
        document_control('scheduler-layout-missing',lambda d:d['schedulerLayoutSizes'].pop('QueueStep'))
        document_control('scheduler-layout-bool',lambda d:d['schedulerLayoutSizes'].update(Scheduler=True))
        document_control('advance-layout-negative-zero',lambda d:d['advanceLayoutSizes'].update(Progress=-0.))
        document_control('duplicate-frame-context',lambda d:d['fixtures'][1].update(frameOrdinal=0))
        document_control('history-scenario-fragmented',lambda d:d['fixtures'][1].update(scenario='new-context'))
        document_control('history-unrecorded-edit',lambda d:d['fixtures'][edited].update(externalEdit=None))
        document_control('history-unknown-edit',lambda d:d['fixtures'][edited].update(externalEdit='move-anything'))
        # Call history gate directly so these do not succeed merely by the
        # frozen input multiset check.
        for name,ordinal,mutate in [
            ('history-source-revision-jump',edited,lambda r:r['input']['meshes'][0].update(revision=99)),
            ('history-progress-tick-jump',edited,lambda r:r['progressBefore'].update(ticks=999)),
            ('history-backlog-jump',edited,lambda r:r['schedulerBefore'].update(backlog=.5)),
            ('history-edit-additional-x-change',edited,lambda r:r['input']['bodies'][0]['position'].__setitem__(0,7.))]:
            altered=copy.deepcopy(rows);mutate(altered[ordinal]);rejected(lambda:ref.histories(altered))
            controls.append({'name':name,'scope':'Artificial captured inter-frame history discontinuity; pure history gate','rejected':True})

        row_control('pump-status-unknown',success,lambda r:r['report'].update(status='safe'))
        row_control('pump-reason-unknown',success,lambda r:r['report'].update(reason='other'))
        row_control('pump-flag-integer',success,lambda r:r['report'].update(elapsedAccepted=1))
        row_control('whole-flag-integer',success,lambda r:r['report'].update(hasWholeTickBacklog=0))
        row_control('scheduler-profile-bool',success,lambda r:r['report']['binding'].update(profile=True))
        row_control('scheduler-binding-unconfigured',success,lambda r:r['report']['binding'].update(configured=False))
        row_control('scheduler-identity-short',success,lambda r:r['report']['binding'].update(buildId='abc'))
        row_control('requested-elapsed-bits-changed',success,lambda r:r['report'].update(requestedElapsedBits='0000000000000000'))
        row_control('requested-elapsed-malformed',success,lambda r:r.update(elapsedBits='0'))
        row_control('drop-negative-zero',success,lambda r:r['report'].update(droppedSeconds=-0.))
        row_control('drop-credit-not-retain',success,lambda r:r['report'].update(droppedSeconds=.0625))
        row_control('planned-bool-alias',success,lambda r:r['report'].update(plannedAttempts=True))
        row_control('attempt-negative-zero-alias',success,lambda r:r['report'].update(attempts=-0.))
        row_control('committed-inflated',success,lambda r:r['report'].update(committedTicks=3))
        row_control('queue-array-tail-removed',success,lambda r:r['report']['queuePlan'].pop())
        row_control('tick-array-tail-removed',success,lambda r:r['report']['tickReports'].pop())
        row_control('queue-unplanned-slot-nonnull',success,lambda r:r['report']['queuePlan'].__setitem__(7,copy.deepcopy(r['report']['queuePlan'][0])))
        row_control('tick-unexecuted-slot-nonnull',prefix,lambda r:r['report']['tickReports'].__setitem__(2,copy.deepcopy(r['report']['tickReports'][0])))
        row_control('queue-last-slot-missing',large,lambda r:r['report']['queuePlan'].__setitem__(7,None))
        row_control('tick-last-slot-missing',large,lambda r:r['report']['tickReports'].__setitem__(7,None))
        row_control('admission-value-wrong',success,lambda r:r['report'].update(admittedCredit=0.))
        row_control('admission-error-wrong',success,lambda r:r['report'].update(admissionRoundingError=[1.,2.]))
        row_control('admission-error-missing',success,lambda r:r['report'].update(admissionRoundingError=None))
        row_control('admission-value-missing',success,lambda r:r['report'].update(admittedCredit=None))
        row_control('queue-credit-wrong',success,lambda r:r['report']['queuePlan'][0].update(creditBefore=0.))
        row_control('queue-next-wrong',success,lambda r:r['report']['queuePlan'][0].update(proposedAfter=0.))
        row_control('queue-error-wrong',success,lambda r:r['report']['queuePlan'][0].update(roundingError=[1.,2.]))
        row_control('queue-extra-field',success,lambda r:r['report']['queuePlan'][0].update(extra=None))
        row_control('queue-index-bool',success,lambda r:r['report']['tickReports'][0].update(queueIndex=False))
        row_control('queue-index-order',success,lambda r:r['report']['tickReports'][1].update(queueIndex=0))
        row_control('credit-consumed-false',success,lambda r:r['report']['tickReports'][0].update(creditConsumed=False))
        row_control('failed-credit-consumed',failed,lambda r:r['report']['tickReports'][0].update(creditConsumed=True))
        for key in sorted(ref.HARD_WORK):
            row_control('reserved-upper-'+key,prefix,lambda r,k=key:r['report']['upperBudget']['guardWork'].__setitem__(k,r['report']['upperBudget']['guardWork'][k]-1))
        row_control('reserved-tail-only-executed',prefix,lambda r:r['report']['upperBudget'].update(attempts=r['report']['attempts']))
        row_control('reserved-logical-payload-cut',prefix,lambda r:r['report']['upperBudget'].update(guardLogicalPayloadBytes=0))
        row_control('reserved-work-bool',success,lambda r:r['report']['upperBudget']['guardWork'].update(meshQueries=True))
        row_control('no-due-invented-attempt',no_due,lambda r:r['report'].update(attempts=1))
        row_control('unaccepted-invented-commit',unaccepted,lambda r:r['report'].update(committedTicks=1))
        row_control('unaccepted-changes-progress',unaccepted,lambda r:r['progressAfter'].update(ticks=999))
        row_control('unaccepted-invents-proposal',unaccepted,lambda r:r['report'].update(admittedCredit=0.,admissionRoundingError=[0.,0.]))
        row_control('unaccepted-wrong-priority',unaccepted,lambda r:r['report'].update(reason='elapsed'))
        row_control('after-credit-wrong',success,lambda r:r['report']['after'].update(backlog=.5))
        row_control('actual-scheduler-after-diverges',success,lambda r:r['schedulerAfter'].update(sequence=999))
        row_control('actual-progress-after-diverges',success,lambda r:r['progressAfter'].update(ticks=999))
        row_control('report-progress-before-diverges',success,lambda r:r['report']['progressBefore'].update(time=0.))
        row_control('immutable-settings-changed',success,lambda r:r['report']['after']['settings'].update(stepSeconds=.03125))
        row_control('busy-return',success,lambda r:r['report']['after'].update(busy=True))
        row_control('backlog-negative-zero',no_due,lambda r:r['schedulerBefore'].update(backlog=-0.))
        row_control('sequence-bool',success,lambda r:r['schedulerBefore'].update(sequence=True))
        row_control('nested-report-missing-field',success,lambda r:tick(r).pop('guardMessage'))
        row_control('nested-status-unknown',success,lambda r:tick(r).update(status='advanced'))
        row_control('nested-message-type',success,lambda r:tick(r).update(message=False))
        row_control('nested-guard-message-type',success,lambda r:tick(r).update(guardMessage=None))
        row_control('nested-profile-unchecked',success,lambda r:tick(r).update(advanceProfileChecked=False))
        row_control('nested-profile-mismatch',success,lambda r:tick(r).update(advanceProfileMatches=False))
        row_control('nested-original-clock',success,lambda r:tick(r).update(originalProgress={'time':0.,'ticks':0}))
        row_control('nested-proposed-clock',success,lambda r:tick(r)['proposedProgress'].update(time=0.))
        row_control('nested-clock-interval',success,lambda r:tick(r)['clock'].update(timeSum=[-2.,-1.]))
        row_control('nested-clock-difference',success,lambda r:tick(r)['clock'].update(representedDt=0.))
        row_control('nested-requested-dt',success,lambda r:tick(r).update(requestedDt=.03125))
        row_control('nested-advanced-dt',success,lambda r:tick(r).update(advancedDt=0.))
        row_control('nested-guard-missing-no-fill',success,lambda r:tick(r).update(guard=None))
        row_control('nested-guard-status',success,lambda r:tick(r)['guard'].update(status='ready'))
        row_control('nested-guard-candidate-tail',success,lambda r:tick(r)['guard']['candidateBodies'].pop())
        row_control('nested-guard-pair-tail',success,lambda r:tick(r)['guard']['pairs'].pop())
        row_control('nested-guard-child-work',success,lambda r:tick(r)['guard']['work'].update(childCallsReturned=0))
        def child(row,kind,call):
            return next(p['child'][call]['result'] for p in tick(row)['guard']['pairs'] if p['child']['kind']==kind)
        row_control('nested-metric-mathematical-interval',success,lambda r:child(r,'plane','metric')['audits'][0].update(value=[7.,8.]))
        row_control('nested-box-mathematical-coordinate',success,lambda r:child(r,'plane','box')['audits'][0]['evaluation']['tubeCoordinates'].__setitem__(1,[7.,8.]))
        row_control('nested-box-mathematical-gap',success,lambda r:child(r,'plane','box')['audits'][0]['evaluation'].update(gap=[7.,8.]))
        row_control('nested-flight-declared-tube-deleted',success,lambda r:child(r,'mesh','mesh')['tube'].update(positionError=0.))
        row_control('nested-known-upper-cut',success,lambda r:tick(r)['guard']['work']['held']['meshQueries'].update(upper=0))
        def unknown_work(row):
            w=tick(row)['guard']['work'];w['exact']=False
            w['held']['sqrtRefinements']['exact']=False
            w['held']['sqrtRefinements']['upper']+=512
        row_control('nested-unknown-work-cannot-certify',success,unknown_work)
        for key in sorted(ref.advance.WORK_KEYS):
            row_control('nested-work-'+key,success,lambda r,k=key:tick(r)['work'].__setitem__(k,tick(r)['work'][k]+1))
        for key in sorted(ref.advance.STORAGE_KEYS):
            row_control('nested-storage-'+key,success,lambda r,k=key:tick(r)['storage'].__setitem__(k,tick(r)['storage'][k]+1))
        row_control('nested-work-bool',success,lambda r:tick(r)['work'].update(guardQueriesAttempted=True))
        row_control('clock-refusal-invented-query',clock_failed,lambda r:tick(r)['work'].update(guardQueriesAttempted=1))
        row_control('clock-refusal-invented-guardmessage',clock_failed,lambda r:tick(r).update(guardMessage='not returned'))
        row_control('clock-refusal-invented-proposal',clock_failed,lambda r:tick(r).update(proposedProgress={'time':1.,'ticks':18}))
        row_control('clock-refusal-advanced-negative-zero',clock_failed,lambda r:tick(r).update(advancedDt=-0.))
        row_control('failed-tick-invented-store',failed,lambda r:tick(r)['work'].update(bodyAssignments=1))
        row_control('failed-tick-wrong-stage',failed,lambda r:tick(r)['failure'].update(stage='clock'))
        row_control('failed-tick-body-mutation',failed,lambda r:after_body(r,'velocity',[9.,0.,0.]))
        row_control('commit-load-not-cleared',success,lambda r:after_body(r,'force',[1.,0.,0.]))
        row_control('commit-clear-negative-zero',success,lambda r:after_body(r,'torque',[-0.,0.,0.]))
        row_control('actual-body-final-position',success,lambda r:after_body(r,'position',[0.,0.,0.]))
        # Pure next-call Report gate: no fictional WorldAfter/pointer row.
        altered=copy.deepcopy(rows[success]);second=tick(altered,1)
        # Deliberately supply previous loaded source to the actual second owned
        # guard; copied source mismatch must be caught by captured-origin checks.
        rejected(lambda:ref.advance_report(altered['input'],tick(altered,0)['proposedProgress'],second,data['layoutSizes'],ref.new_stats()))
        controls.append({'name':'candidate-to-next-captured-origin-load-chain','scope':'Artificial wrong expected source versus actual second Report, not a fake measured World','rejected':True})
        row_control('actual-source-revision-changed',success,lambda r:r['inputAfter']['meshes'][0].update(revision=999))
        row_control('actual-gravity-negative-zero-lost',success,lambda r:r['inputAfter']['gravity'].__setitem__(0,0.))
        for key in ('captureComplete','sourceUnchanged','settingsUnchanged','horizonUnchanged','planesUnchanged','gravityUnchanged'):
            row_control('actual-observation-'+key,success,lambda r,k=key:r['observations'].__setitem__(k,False))
        row_control('actual-pump-count-bool',success,lambda r:r['observations'].update(pumpCalls=True))
        row_control('actual-world-unchanged-flag',success,lambda r:r['observations'].update(worldUnchanged=True))
        row_control('actual-progress-unchanged-flag',success,lambda r:r['observations'].update(progressUnchanged=True))
        row_control('pointer-ordinal-bool',success,lambda r:r['observations']['pointerStability']['bodies'][0].update(ordinal=False))
        row_control('pointer-original-id-bool',success,lambda r:r['observations']['pointerStability']['bodies'][0].update(originalId=True))
        row_control('pointer-address-observation',success,lambda r:r['observations']['pointerStability']['bodies'][0].update(sameOrdinalAddress=False))
        row_control('pointer-storage-int-alias',success,lambda r:r['observations']['pointerStability'].update(bodyStorageStable=1))
        row_control('pointer-face-tail-missing',success,lambda r:r['observations']['pointerStability']['meshFaceStorageStable'].pop())

        # Wider error intervals are sound mathematical evidence; the independent
        # gate must not pretend to enforce Native exact public-value provenance.
        widened=copy.deepcopy(rows[success]);widened['report']['admissionRoundingError']=[-1.,1.]
        for q in widened['report']['queuePlan']:
            if q is not None:q['roundingError']=[-1.,1.]
        ref.verify_row(widened,data['layoutSizes'],ref.new_stats())
        positive.append('artificial-wider-valid-credit-intervals-math-scope-only')

        argv=[sys.executable,'-O',str(CHECKER),str(args.fixture.resolve())]
        start=time.perf_counter();optimized=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120,check=False)
        (out/'optimized.stdout.txt').write_bytes(optimized.stdout);(out/'optimized.stderr.txt').write_bytes(optimized.stderr)
        optimized_record={'argv':argv,'exit':optimized.returncode,'elapsedSeconds':time.perf_counter()-start,
                          'stdout':stamp(out/'optimized.stdout.txt'),'stderr':stamp(out/'optimized.stderr.txt')}
        write(out/'optimized-command.json',optimized_record);commands.append(optimized_record)
        need(optimized.returncode!=0 and b'normal Python' in optimized.stderr,'Actual optimized child explicitly refuses protected reference execution')
        controls.append({'name':'optimized-python-refused','scope':'Actual separate optimized Python process','rejected':True})
        result={'status':'PASS','baseline':actual,'selfTestGroups':len(groups),'selfTests':groups,
                'rejectedControls':controls,'negativeControls':len(controls),'positiveControls':positive,
                'labelAndOrderIndependent':True,'optimizedPythonRejected':{'status':'PASS','exitCode':optimized.returncode},
                'scope':'Actual finite full transcript audit; copied adversarial JSON controls and integer/Fraction self checks. No Native exception/allocator fault injection, no manufactured intermediate World/pointer observations, no production query or complete machine attestation.'}
        write(out/'negative-controls.json',result)
    finally:
        after=[stamp(p) for p in watched];write(out/'source-after.json',after)
        write(out/'provenance.json',{'sourceBefore':before,'sourceAfter':after,'sourceStable':before==after,
              'commands':commands,'elapsedSeconds':time.perf_counter()-started})
        need(before==after,'Original actual fixture/protected references/checker sources remain byte identical')
    print(json.dumps({'status':'PASS','fixtures':actual['fixtures'],'selfTestGroups':len(groups),
                      'negativeControls':len(controls),'labelAndOrderIndependent':True}))


if __name__=='__main__':
    main()
