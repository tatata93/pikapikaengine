"""Actual finite reference and copied adversarial controls, never native faults."""
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

ROOT=Path(__file__).resolve().parents[1]
CHECKER=ROOT/'scripts/verify-world-static-mesh-flight-controlled-scheduler.py'
sys.dont_write_bytecode=True


def need(ok,message):
    if not ok:raise ValueError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();need(__debug__,'Actual controls require normal Python')
    out=args.output.resolve();need(out.is_relative_to(ROOT) and out!=ROOT and not out.exists(),'Fresh workspace output child');out.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('controlled_scheduler_reference_under_test',CHECKER)
    ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    fixture=args.fixture.resolve();legacy=ROOT/'reports/world-static-mesh-flight-controlled-tick-recipes/run-20261105-main-integration-001/controlled-full.json'
    watched=[CHECKER,Path(__file__).resolve(),fixture,legacy,ROOT/'scripts/verify-world-static-mesh-flight-controlled-tick.py',
        ROOT/'scripts/verify-world-static-mesh-flight-scheduler.py',ROOT/'scripts/verify-world-static-mesh-flight-advance.py',
        ROOT/'scripts/verify-world-static-mesh-flight-guard.py',ROOT/'reports/world-static-mesh-flight-advance-recipes/clock-reference.py']
    def stamps():
        return [{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in watched]
    def write(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    before=stamps();write('before.json',before);started=time.monotonic();result={'status':'FAIL','actualNativeFaultInjection':False,'scope':__doc__}
    try:
        data=ref.load(fixture);baseline=ref.verify(data);write('baseline.json',baseline)
        positives=['actual84-pump-full-baseline']
        # Reuse only genuine old88 external IO and ControlledReports. No new
        # artificial WorldAfter/lookup rows are constructed for old checkers.
        old=ref.load(legacy);known=ref.controlled.verify(old);actual=ref.controlled.new_stats()
        for row in old['fixtures']:
            ref.actual_controlled(row['input'],row['report'],row['worldAfter'],row['progressAfter'],old['layoutSizes'],actual)
        for key in actual:
            if key=='outerPointerBodyObservations':continue
            ref.equal(actual[key],known[key],'pure actual ControlledReport regression: '+key)
        positives.append('pure-controlled-report-core-all88-actual-regression')
        write('old88-core-regression.json',{'status':'PASS','fixtures':88,'mathematicalChildren':actual['child']['guard']['childCalls'],
            'scope':'Actual old full88 data only; pure Report core equals protected full-row math/counters. Per-child pointer/lookup rows are neither constructed nor claimed checked by the new pure core.'})
        renamed=copy.deepcopy(data);groups={name:'group-'+str(i) for i,name in enumerate(sorted({r['scenario'] for r in renamed['fixtures']}))}
        for i,row in enumerate(renamed['fixtures']):row['name']='renamed-'+str(i);row['scenario']=groups[row['scenario']]
        renamed['fixtures'].reverse();ref.verify(renamed);positives.append('actual-label-scenario-rename-and-document-reversal')
        # Closed form from actual input values, independently of returned guard
        # candidates. Select by mathematical inputs, never a fixture name.
        analytic=0
        for row in data['fixtures']:
            r=row['report'];scene=row['input']['scene'];p=row['input']['packets']
            if r['committedTicks']!=2 or len(scene['bodies'])!=1 or len(p)!=2:continue
            b=scene['bodies'][0]
            if ref.fraction(scene['horizon'])!=Fraction(1,16) or ref.fraction(b['mass'])!=2 or any(ref.fraction(v)!=0 for v in scene['gravity']):continue
            if [ref.fraction(q['loads'][0]['force'][0]) for q in p]!=[4,-4]:continue
            position,velocity=b['position'],b['velocity']
            for i,packet in enumerate(p):
                position,velocity=ref.controlled.exact_translation(position,velocity,b['mass'],packet['loads'][0]['force'],scene['gravity'],scene['horizon'])
                observed=r['boundaries'][i+1]['world']['bodies'][0]
                need(all(ref.fraction(observed['position'][j])==position[j] and ref.fraction(observed['velocity'][j])==velocity[j] for j in range(3)),'actual dyadic physical boundary disagrees with independent closed form')
            need(position[0]==Fraction(1,128) and velocity[0]==0,'actual independent two-load endpoint');analytic+=1
        need(analytic>=1,'Actual dyadic two-tick record must exist');positives.append('actual-two-tick-Fraction-closed-form')
        rejected=[]
        def reject(name,mutation,*,pinned=False):
            changed=copy.deepcopy(data);mutation(changed)
            try:ref.verify(changed,development_unpinned=not pinned)
            except (AssertionError,ValueError,KeyError,TypeError,IndexError) as error:
                rejected.append({'name':name,'rejected':True,'gate':'pinned-source' if pinned else 'metadata-or-mathematics-unpinned','error':type(error).__name__+': '+str(error)[:260]})
            else:raise ValueError('Adversarial copied JSON was accepted: '+name)
        def at(d,path):
            for k in path:d=d[k]
            return d
        def set_path(path,value):
            return lambda d:at(d,path[:-1]).__setitem__(path[-1],copy.deepcopy(value))
        first=['fixtures',0,'report'];control=first+['tickReports',0,'report'];child=control+['child'];guard=child+['guard']
        for key in ['plannedAttempts','attempts','committedTicks','packetsConsumed','boundaryCount']:
            value=at(data,first+[key]);reject('parent-count-'+key,set_path(first+[key],value+1))
        for key in ref.WORK_KEYS:reject('parent-work-'+key,set_path(first+['work',key],at(data,first+['work',key])+1))
        for key in ref.STORAGE_KEYS:reject('parent-storage-'+key,set_path(first+['storage',key],at(data,first+['storage',key])+1))
        reject('accepted-bool-is-int',set_path(first+['elapsedAccepted'],1))
        reject('count-int-is-bool',set_path(first+['committedTicks'],True))
        reject('progress-before-tick-int-is-float',set_path(first+['progressBefore','ticks'],float(at(data,first+['progressBefore','ticks']))))
        reject('progress-after-tick-int-is-float',set_path(first+['progressAfter','ticks'],float(at(data,first+['progressAfter','ticks']))))
        reject('reserved-slots-int-is-float',set_path(first+['upperBudget','attempts'],float(at(data,first+['upperBudget','attempts']))))
        reject('reserved-work-int-is-float',set_path(first+['upperBudget','guardWork','meshQueries'],float(at(data,first+['upperBudget','guardWork','meshQueries']))))
        reject('reserved-bytes-int-is-float',set_path(first+['upperBudget','guardLogicalPayloadBytes'],float(at(data,first+['upperBudget','guardLogicalPayloadBytes']))))
        reject('owned-packet-id-int-is-float',set_path(first+['original','packets',0,'loads',0,'bodyId'],101.0))
        reject('owned-mesh-id-int-is-float',set_path(first+['original','meshes',0,'id'],301.0))
        reject('owned-guard-limit-int-is-float',set_path(first+['original','settings','limits','meshQueries'],float(at(data,first+['original','settings','limits','meshQueries']))))
        reject('false-retain-only-drop',set_path(first+['droppedSeconds'],.0625))
        reject('negative-zero-drop',set_path(first+['droppedSeconds'],-0.0))
        reject('wrong-final-backlog',set_path(first+['after','backlog'],.0625))
        reject('double-sequence-admission',set_path(first+['after','sequence'],2))
        reject('unaccepted-after-real-commit',set_path(first+['elapsedAccepted'],False))
        reject('wrong-whole-tick-flag',set_path(first+['hasWholeTickBacklog'],True))
        reject('unknown-result-status',set_path(first+['status'],'unknown'))
        reject('unobserved-fault-success',set_path(first+['reason'],'allocation_failure'))
        reject('origin-capture-none',set_path(first+['capture'],'none'))
        reject('owned-origin-removed',set_path(first+['original'],None))
        reject('packet-origin-load-changed',set_path(first+['original','packets',0,'loads',0,'force',0],8))
        reject('extra-unreturned-boundary',set_path(first+['boundaries',3],at(data,first+['boundaries',2])))
        reject('missing-actual-initial-boundary',set_path(first+['boundaries',0],None))
        reject('missing-actual-after-boundary',set_path(first+['boundaries',1],None))
        reject('candidate-expected-state-as-actual-world',set_path(first+['boundaries',1,'world','bodies',0,'position',0],99))
        reject('fixed-boundary-negative-zero-lost',set_path(first+['boundaries',0,'world','gravity',0],0.0))
        reject('fixed-original-address-false',set_path(first+['boundaries',0,'originalBodyAddressSame',0],False))
        reject('fixed-progress-skipped-tick',set_path(first+['boundaries',1,'progress','ticks'],19))
        reject('packet-reused-for-second-tick',set_path(first+['tickReports',1,'packetOrdinal'],0))
        reject('wrong-queue-ordinal',set_path(first+['tickReports',1,'queueIndex'],0))
        reject('commit-without-packet-consumption',set_path(first+['tickReports',0,'packetConsumed'],False))
        reject('commit-without-credit-consumption',set_path(first+['tickReports',0,'creditConsumed'],False))
        reject('missing-executed-child',set_path(first+['tickReports',0],None))
        reject('extra-unexecuted-child',set_path(first+['tickReports',2],at(data,first+['tickReports',1])))
        reject('missing-time-plan',set_path(first+['queuePlan',0],None))
        reject('wrong-time-subtraction',set_path(first+['queuePlan',0,'proposedAfter'],.125))
        reject('fake-admission-enclosure',set_path(first+['admissionRoundingError'],[1,1]))
        reject('fake-queue-enclosure',set_path(first+['queuePlan',0,'roundingError'],[1,1]))
        reject('underreserved-unexecuted-tail',set_path(first+['upperBudget','attempts'],0))
        reject('reservation-as-zero-work',set_path(first+['upperBudget','guardWork','sqrtRefinements'],0))
        reject('logical-payload-undercounted',set_path(first+['upperBudget','guardLogicalPayloadBytes'],0))
        reject('controlled-addition-instead-of-replacement',set_path(control+['stagedBefore','bodies',0,'force',0],7))
        reject('controlled-origin-relabeled',set_path(control+['original','world','bodies',0,'force',0],4))
        reject('private-success-hidden-as-failure',set_path(control+['committed'],False))
        reject('actual-private-child-removed',set_path(child,None))
        reject('actual-guard-removed',set_path(guard,None))
        reject('actual-private-world-removed',set_path(control+['privateAfter'],None))
        reject('controlled-work-removed',lambda d:at(d,control+['work']).__delitem__('privateAfterBodiesCopied'))
        reject('controlled-upstream-id-mismatch',set_path(control+['binding','upstreamBuildId'],'a'*64))
        reject('parent-controlled-id-mismatch',set_path(first+['binding','controlledBuildId'],'a'*64))
        reject('guard-mathematical-value-forged-positive',set_path(guard+['pairs',0,'child','metric','result','audits',0,'value'],[1000,1000]))
        reject('guard-candidate-position-altered',set_path(guard+['candidateBodies',0,'position',0],99))
        reject('actual-caller-world-replaced',set_path(['fixtures',0,'inputAfter','scene','bodies',0,'position',0],99))
        reject('actual-caller-progress-replaced',set_path(['fixtures',0,'inputAfter','progress','ticks'],999))
        reject('actual-outer-pointer-claim-false',set_path(['fixtures',0,'observations','pointerStability','bodyStorageStable'],False))
        reject('actual-call-count-doubled',set_path(['fixtures',0,'observations','pumpCalls'],2))
        reject('source-preservation-claim-false',set_path(['fixtures',0,'observations','sourceSettingsPacketsUnchanged'],False))
        reject('sizeof-observation-changed',set_path(['controlledSchedulerLayoutSizes','OptionalBoundary'],data['controlledSchedulerLayoutSizes']['OptionalBoundary']+1))
        reject('extra-root-key',lambda d:d.__setitem__('syntheticSuccess',True))
        reject('missing-fixed-slot',lambda d:at(d,first+['boundaries']).pop())
        reject('source-count-subset',lambda d:d['fixtures'].pop(),pinned=True)
        reject('source-force-bit-altered',set_path(['fixtures',0,'input','scene','bodies',0,'force',0],4),pinned=True)
        reject('source-packet-load-altered',set_path(['fixtures',0,'input','packets',0,'loads',0,'force',0],5),pinned=True)
        # Reject erasure of a real nonzero rounding error at the120Hz step.
        rounded=None
        for i,row in enumerate(data['fixtures']):
            h=ref.fraction(row['report']['before']['settings']['step'])
            for j,q in enumerate(row['report']['queuePlan']):
                if q is not None and ref.fraction(q['proposedAfter'])-(ref.fraction(q['creditBefore'])-h)!=0:rounded=(i,j);break
            if rounded is not None:break
        need(rounded is not None,'Actual nonzero queue rounding error must be present')
        reject('actual-nondyadic-rounding-error-erased',set_path(['fixtures',rounded[0],'report','queuePlan',rounded[1],'roundingError'],[0,0]))
        positives.append('actual-nondyadic-time-record-selected-without-labels')
        command=[sys.executable,'-O',str(CHECKER),str(fixture)];p=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=60)
        (out/'optimized.stdout.txt').write_bytes(p.stdout);(out/'optimized.stderr.txt').write_bytes(p.stderr)
        need(p.returncode!=0 and b'normal Python' in p.stderr,'Actual optimized process explicitly refuses verification')
        write('optimized-command.json',{'argv':command,'exitCode':p.returncode})
        rejected.append({'name':'actual-optimized-python-refusal','rejected':True,'gate':'actual-process'})
        result.update(status='PASS',baseline=baseline,positiveControls=positives,copiedRejectionControls=len(rejected)-1,allRejectedControls=rejected,
            actualOld88PureCoreRegression=True,actualDyadicClosedForms=analytic,labelAndOrderIndependent=True,optimizedPythonRefused=True,
            nonzeroQueueErrorFixtureOrdinal=rounded[0],scope='Actual Native84 mathematical verification, actual old88 core regression, copied JSON controls and one actual -O process refusal. No C++ execution/fault injection by this suite, no synthetic child pointer/World rows, no formal build/GNU/SDK acceptance.')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=stamps();write('after.json',after);result.update(sourceStable=before==after,seconds=time.monotonic()-started)
        if before!=after:result['status']='FAIL'
        write('verification.json',result)
    print(json.dumps({k:result[k] for k in ['status','copiedRejectionControls','actualOld88PureCoreRegression','labelAndOrderIndependent','optimizedPythonRefused','sourceStable','seconds','error'] if k in result}))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
