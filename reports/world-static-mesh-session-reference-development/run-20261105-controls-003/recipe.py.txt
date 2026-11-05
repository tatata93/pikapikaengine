"""Actual owner corpus, independent closed forms and copied rejection controls.

No C++ or allocator fault injection. Mutated JSON is never presented as a new
Native observation. An actual optimized Python process must refuse verification.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
CHECKER=ROOT/'scripts/verify-world-static-mesh-session.py'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixture',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();need=lambda ok,msg: None if ok else (_ for _ in ()).throw(ValueError(msg))
    need(out.is_relative_to(ROOT) and out!=ROOT and not out.exists(),'Fresh repository evidence child');out.mkdir(parents=True);sys.dont_write_bytecode=True
    (out/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());(out/'checker.py.txt').write_bytes(CHECKER.read_bytes())
    spec=importlib.util.spec_from_file_location('owned_reference_controls',CHECKER);ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    fixture=args.fixture.resolve();data=ref.q.load(fixture);paths={Path(__file__),CHECKER,fixture,ROOT/'scripts/verify-world-static-mesh-flight-controlled-scheduler.py',ROOT/'scripts/verify-world-static-mesh-flight-controlled-tick.py',ROOT/'scripts/verify-world-static-mesh-flight-advance.py',ROOT/'scripts/verify-world-static-mesh-flight-guard.py'}
    paths.update(ROOT/p for p in ['core/include/pikapika/world_static_mesh_session.hpp','core/src/world_static_mesh_session.cpp','tests/world_static_mesh_session_tests.cpp','tests/world_static_mesh_session_fixtures.cpp','tests/world_static_mesh_flight_controlled_scheduler_fixture_support.hpp','tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp'])
    stamps=lambda:{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    before=stamps();(out/'before.json').write_text(json.dumps(before,indent=2)+'\n');started=time.monotonic();result={'status':'FAIL','actualNativeFaultInjected':False,'scope':__doc__}
    def write(name,value):(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
    try:
        baseline=ref.verify(data);rejected=[];positive=['actual'+str(baseline['rows'])+'-operation-baseline']
        def reject(name,mutate,*,pinned=False):
            clone=deepcopy(data);mutate(clone)
            try:ref.verify(clone,development_unpinned=not pinned)
            except (AssertionError,ValueError,KeyError,TypeError,IndexError,OverflowError) as error:
                rejected.append({'name':name,'rejected':True,'gate':'pinned-input' if pinned else 'independent-protocol/math/shape','error':type(error).__name__+': '+str(error)});return
            raise ValueError('Copied alteration accepted: '+name)
        def setpath(path,value):
            def mutate(d):
                for key in path[:-1]:d=d[key]
                d[path[-1]]=value
            return mutate
        def find(predicate):return next(i for i,row in enumerate(data['fixtures']) if predicate(row))
        first_create=find(lambda r:r['kind']=='create' and r['result']['status']=='ok')
        first_pump=find(lambda r:r['kind']=='pump' and r['result']['report'] is not None)
        foreign=find(lambda r:r['kind']=='pump' and r['result']['status']=='foreign_session')
        stale=find(lambda r:r['kind']=='pump' and r['result']['status']=='stale_generation')
        dead=find(lambda r:r['kind']=='read' and r['result']['status']=='not_alive')
        failed_reset=find(lambda r:r['kind']=='reset' and r['result']['status']=='invalid_settings')
        saturated=find(lambda r:r['kind']=='reset' and r['result']['status']=='generation_exhausted')
        cap=find(lambda r:r['kind']=='create' and r['result']['status']=='no_free_slot')
        hard=find(lambda r:r['result']['status']=='source_counts')
        retained=find(lambda r:len(r['retainedSnapshots'])>0 and r['kind']=='destroy')
        maximum=find(lambda r:r['kind']=='create' and r['result']['status']=='ok' and len(r['input']['scene']['bodies'])==8 and len(r['input']['scene']['planes'])==16 and len(r['input']['scene']['meshes'])==4 and sum(len(m['triangles']) for m in r['input']['scene']['meshes'])==64)
        rp=['fixtures',first_pump,'result'];created=['fixtures',first_create,'result'];af=['fixtures',first_create,'after','knownLiveSlotReads',0,'snapshot']
        reject('missing-root-field',lambda d:d.pop('maximumGeneration'))
        reject('unknown-root-field',lambda d:d.update(extraOwnerState=True))
        reject('metadata-maximum-generation-bool',setpath(['maximumGeneration'],True))
        reject('metadata-hard-cap-float',setpath(['hardMaxSessions'],4.0))
        reject('named-registry-size-float',setpath(['ownerLayoutSizes','Registry'],float(data['ownerLayoutSizes']['Registry'])))
        reject('root-count-float',setpath(['actualCounts','ownerPumpCalls'],float(data['actualCounts']['ownerPumpCalls'])))
        reject('history-ordinal-float',setpath(['fixtures',0,'frameOrdinal'],0.0))
        reject('constructor-limit-float',setpath(['fixtures',0,'registryGenerationLimit'],float(data['fixtures'][0]['registryGenerationLimit'])))
        reject('created-generation-float',setpath(created+['token','generation'],1.0))
        reject('created-slot-float',setpath(created+['token','slot'],0.0))
        reject('created-generation-zero',setpath(created+['token','generation'],0))
        reject('created-token-not-first-free',setpath(created+['token','slot'],1))
        reject('unknown-fault-as-normal-create',setpath(created+['status'],'allocation_failure'))
        reject('unknown-busy-as-normal-pump',setpath(rp+['status'],'busy'))
        reject('omit-actual-delegated-report',setpath(rp+['report'],None))
        reject('erase-actual-call-count',setpath(rp+['schedulerCalls'],0))
        reject('actual-call-count-float',setpath(rp+['schedulerCalls'],1.0))
        reject('selected-target-drift',setpath(rp+['target','generation'],2))
        reject('foreign-refusal-as-owner-success',setpath(['fixtures',foreign,'result','status'],'ok'))
        reject('foreign-refusal-invents-model-call',setpath(['fixtures',foreign,'result','schedulerCalls'],1))
        reject('stale-refusal-as-other-reason',setpath(['fixtures',stale,'result','status'],'foreign_session'))
        reject('destroyed-read-as-success',setpath(['fixtures',dead,'result','status'],'ok'))
        reject('invalid-settings-reset-as-success',setpath(['fixtures',failed_reset,'result','status'],'ok'))
        reject('generation-wrap-as-success',setpath(['fixtures',saturated,'result','status'],'ok'))
        reject('capacity-as-source-counts',setpath(['fixtures',cap,'result','status'],'source_counts'))
        reject('hard-count-as-allocation-fault',setpath(['fixtures',hard,'result','status'],'allocation_failure'))
        reject('probe-read-count-float',setpath(['fixtures',first_create,'after','readCalls'],1.0))
        reject('probe-drop-live-session',setpath(['fixtures',first_create,'after','knownLiveSlotReads',0],None))
        reject('probe-slot-array-truncated',lambda d:d['fixtures'][first_create]['after']['knownLiveSlotReads'].pop())
        reject('read-copy-clock-sequence-float',setpath(af+['scheduler','sequence'],0.0))
        reject('read-copy-progress-tick-float',setpath(af+['progress','ticks'],17.0))
        reject('read-copy-clock-backlog-changed',setpath(af+['scheduler','backlog'],.0625))
        reject('read-copy-original-force-repaired',setpath(af+['world','bodies',0,'force',0],0))
        reject('read-copy-world-coordinate-changed',setpath(af+['world','bodies',0,'position',0],.25))
        reject('read-copy-loses-negative-zero',setpath(af+['world','gravity',0],0.0))
        reject('read-copy-mesh-altered',setpath(af+['meshes',0,'triangles',0,'vertices',0,0],99))
        reject('read-copy-guard-altered',setpath(af+['guard','contactMargin'],.1))
        reject('retained-snapshot-removed',lambda d:d['fixtures'][retained]['retainedSnapshots'].pop())
        reject('retained-snapshot-after-destroy-mutated',setpath(['fixtures',retained,'retainedSnapshots',0,'world','gravity',0],0.0))
        reject('retained-pump-removed',lambda d:d['fixtures'][first_pump]['retainedPumps'].pop())
        reject('retained-pump-call-count-float',setpath(['fixtures',first_pump,'retainedPumps',0,'schedulerCalls'],1.0))
        reject('missing-row-field',lambda d:d['fixtures'][0].pop('before'))
        reject('extra-read-pointer-observation',lambda d:d['fixtures'][first_create]['after']['knownLiveSlotReads'][0]['snapshot'].update(pointerStable=True))
        reject('model-committed-prefix-erased',setpath(rp+['report','committedTicks'],0))
        reject('model-input-consumption-erased',setpath(rp+['report','packetsConsumed'],0))
        reject('model-boundary-progress-changed',setpath(rp+['report','boundaries',1,'progress','ticks'],19))
        reject('model-controlled-binding-relabel',setpath(rp+['report','tickReports',0,'report','binding','buildId'],'0'*64))
        reject('model-original-packet-force-changed',setpath(rp+['report','original','packets',0,'loads',0,'force',0],5))
        reject('model-unused-slot-as-result',setpath(rp+['report','tickReports',7],False))
        reject('model-copy-cost-erased',setpath(rp+['report','work','boundaryCaptures'],0))
        reject('root-read-count-erased',setpath(['actualCounts','publicReadCalls'],0))
        max_snapshot=['fixtures',maximum,'after','knownLiveSlotReads',0,'snapshot']
        reject('max-body-original-order-reversed',lambda d:d['fixtures'][maximum]['after']['knownLiveSlotReads'][0]['snapshot']['world']['bodies'].reverse())
        reject('max-plane-original-order-reversed',lambda d:d['fixtures'][maximum]['after']['knownLiveSlotReads'][0]['snapshot']['world']['planes'].reverse())
        reject('max-mesh-original-order-reversed',lambda d:d['fixtures'][maximum]['after']['knownLiveSlotReads'][0]['snapshot']['meshes'].reverse())
        reject('max-face-original-vertex-order-reversed',lambda d:d['fixtures'][maximum]['after']['knownLiveSlotReads'][0]['snapshot']['meshes'][0]['triangles'][0]['vertices'].reverse())
        reject('max-time-negative-zero-lost',setpath(max_snapshot+['progress','time'],0.0))
        reject('max-guard-negative-zero-lost',setpath(max_snapshot+['guard','contactMargin'],0.0))
        reject('max-body-prefix-truncated',lambda d:d['fixtures'][maximum]['after']['knownLiveSlotReads'][0]['snapshot']['world']['bodies'].pop())
        reject('max-face-prefix-truncated',lambda d:d['fixtures'][maximum]['after']['knownLiveSlotReads'][0]['snapshot']['meshes'][0]['triangles'].pop())
        largest=data['fixtures'][maximum]['after']['knownLiveSlotReads'][0]['snapshot']
        need(ref.q.bits(largest['progress']['time']).hex()=='8000000000000000' and ref.q.bits(largest['guard']['contactMargin']).hex()=='8000000000000000','actual maximum source contains observed raw negative-zero time/margin')
        ids=[b['id'] for b in largest['world']['bodies']];need(ids!=sorted(ids),'actual maximum original body order is non-sorted')
        positive.append('actual-simultaneous8-body16-plane4-mesh64-face-copy')
        # Change authored gate inputs in a copy with pinning explicitly disabled;
        # the old outcome must then be rejected by the independent model.
        def wrong_range(d):
            row=d['fixtures'][foreign]
            for key in ['input','inputAfter']:row[key]['target']['slot']=4
            row['result']['target']['slot']=4
        reject('target-range-precedes-foreign-reason',wrong_range)
        def wrong_generation(d):
            row=d['fixtures'][foreign]
            for key in ['input','inputAfter']:
                row[key]['owner']['slot']=row[key]['target']['slot'];row[key]['owner']['generation']=99
        reject('owner-generation-precedes-original-foreign-reason',wrong_generation)
        reject('authored-create-source-bit-changed',setpath(['fixtures',first_create,'input','scene','bodies',0,'force',0],5),pinned=True)
        reject('authored-registry-limit-changed',setpath(['fixtures',0,'registryGenerationLimit'],1),pinned=True)
        rounded=None
        for i,row in enumerate(data['fixtures']):
            if row['kind']!='pump' or row['result']['report'] is None:continue
            r=row['result']['report'];h=ref.q.fraction(r['before']['settings']['step'])
            for j,step in enumerate(r['queuePlan']):
                if step is not None and ref.q.fraction(step['proposedAfter'])-(ref.q.fraction(step['creditBefore'])-h)!=0:rounded=(i,j);break
            if rounded is not None:break
        need(rounded is not None,'actual nonzero120Hz rounding error must exist')
        reject('actual-nondyadic-queue-error-erased',setpath(['fixtures',rounded[0],'result','report','queuePlan',rounded[1],'roundingError'],[0,0]))
        positive.append('actual-nonzero-queue-error-selected-without-labels')
        renamed=deepcopy(data)
        for row in renamed['fixtures']:row['name']='renamed/'+row['name'];row['scenario']='renamed/'+row['scenario']
        renamed['fixtures'].reverse();need(ref.verify(renamed)['rows']==baseline['rows'],'labels and document order independent');positive.append('renamed-scenarios-and-reversed-document')
        # Verify all actually observed dyadic two-packet results directly from
        # the force/mass equation, independent of labels and the model metadata.
        closed=[]
        for row in data['fixtures']:
            if row['kind']!='pump' or row['result']['report'] is None:continue
            r=row['result']['report'];packets=row['input']['packets'];slot=row['input']['target']['slot']
            if r['committedTicks']!=2 or len(packets)!=2 or ref.q.fraction(r['before']['settings']['step'])!=Fraction(1,16):continue
            before_snapshot=row['before']['knownLiveSlotReads'][slot]['snapshot'];after=row['after']['knownLiveSlotReads'][slot]['snapshot'];b=before_snapshot['world']['bodies'][0]
            if len(before_snapshot['world']['bodies'])!=1 or [p['loads'][0]['force'][0] for p in packets]!=[4,-4]:continue
            h=Fraction(1,16);m=ref.q.fraction(b['mass']);x=ref.q.fraction(b['position'][0]);v=ref.q.fraction(b['velocity'][0]);positions=[]
            for packet in packets:
                a=ref.q.fraction(packet['loads'][0]['force'][0])/m;x=x+v*h+a*h*h/2;v=v+a*h;positions.append(x)
            need(ref.q.fraction(r['boundaries'][1]['world']['bodies'][0]['position'][0])==positions[0],'actual first dyadic boundary closed form')
            need(ref.q.fraction(after['world']['bodies'][0]['position'][0])==x and ref.q.fraction(after['world']['bodies'][0]['velocity'][0])==v,'actual external read closed form')
            closed.append({'frameOrdinal':row['frameOrdinal'],'position':str(x),'velocity':str(v)})
        need(len(closed)==3,'all three actual dyadic start positions');positive.append('three-actual-Fraction-dyadic-world-reads')
        old=ROOT/'reports/world-static-mesh-session-recipes/run-20261105-bridge-002/controlled-scheduler-full.json';old_result=ref.q.verify(ref.q.load(old));need(old_result['frames']==84 and old_result['controlled']['child']['guard']['childCalls']==279,'full original84 pointer-aware regression');positive.append('actual84-original-full-row-and-pointer-regression')
        # A genuinely valid smaller copied corpus must still be refused by the
        # pinned gate. Compute its counters without using production code.
        subset=deepcopy(data);last=subset['fixtures'][-1]['scenario'];subset['fixtures']=[r for r in subset['fixtures'] if r['scenario']!=last]
        subset['actualCounts']={'rows':len(subset['fixtures']),'scenarios':len({r['scenario'] for r in subset['fixtures']}),'ownerPumpCalls':sum(r['kind']=='pump' for r in subset['fixtures']),
            'delegatedSchedulerCalls':sum(r['result']['schedulerCalls'] for r in subset['fixtures'] if r['kind']=='pump'),
            'committedTicks':sum(r['result']['report']['committedTicks'] for r in subset['fixtures'] if r['kind']=='pump' and r['result']['report'] is not None),
            'publicReadCalls':sum(r['before']['readCalls']+r['after']['readCalls']+int(r['kind']=='read') for r in subset['fixtures'])}
        need(ref.verify(subset,development_unpinned=True)['scenarios']==baseline['scenarios']-1,'copied smaller corpus is protocol/math valid')
        try:ref.verify(subset)
        except (AssertionError,ValueError):rejected.append({'name':'complete-pinned-corpus-rejects-valid-subset','rejected':True,'gate':'pinned-input'})
        else:raise ValueError('Pinned actual corpus accepted coverage deletion')
        positive.append('copied-valid-subset-before-pinned-refusal')
        argv=[sys.executable,'-O',str(CHECKER),str(fixture)];p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60)
        (out/'optimized.stdout.txt').write_bytes(p.stdout);(out/'optimized.stderr.txt').write_bytes(p.stderr);need(p.returncode!=0 and b'normal Python' in p.stderr,'actual optimized process explicitly refused');write('optimized-command.json',{'argv':argv,'exitCode':p.returncode})
        result.update(status='PASS',baseline=baseline,copiedRejectionControls=len(rejected),allCopiedRejected=rejected,positiveControls=positive,actualDyadicClosedForms=closed,
                      labelAndOrderIndependent=True,original84FullRowRegression=True,actualOptimizedPythonRefused=True,
                      actualNativeFaultInjected=False,scope='Actual77 mathematics/protocol with simultaneous maximum owned values, original84 full row regression, copied JSON rejection controls and one real -O process refusal. No native owner fault/busy injection or GNU/SDK acceptance.')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=stamps();write('after.json',after);result.update(sourceStable=before==after,seconds=time.monotonic()-started)
        if before!=after:result['status']='FAIL'
        write('verification.json',result)
    print(json.dumps({k:result[k] for k in ['status','copiedRejectionControls','labelAndOrderIndependent','original84FullRowRegression','actualOptimizedPythonRefused','sourceStable','seconds','error'] if k in result}));return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
