"""Independent full scheduler transcript audit; no production query or fake rows.

Actual outer observations, integer-RN credit/clock ledgers, actual AdvanceReport
metadata and owned guard mathematics are separate gates. Intermediate expected
candidate chains are compared to actual captured origins, never labelled measured
WorldAfter/pointer observations or passed to advance.verify_fixture.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


advance = module('scheduler_full_advance_helpers', ROOT/'scripts/verify-world-static-mesh-flight-advance.py')
credit = module('scheduler_full_credit_helpers', ROOT/'scripts/verify-world-static-mesh-flight-scheduler-credit.py')
guard = advance.guard
need, fields, uint = advance.need, advance.fields, advance.uint
bits, fraction, equal = advance.bits, advance.fraction, advance.equal
load, loads = advance.load, advance.loads
EXPECTED_FIXTURE_COUNT = 28
EXPECTED_INPUT_FINGERPRINT = '318b16b5d2d3bb30067ee4d65e7675dd3c22bdd4f4eb4ce872f1094b2a2acb23'
MAX_DOCUMENT_BYTES = 64*1024*1024
REPORT_KEYS = {'status','reason','binding','before','after','requestedElapsedBits','elapsedAccepted',
               'admittedCredit','admissionRoundingError','progressBefore','progressAfter','queuePlan',
               'plannedAttempts','attempts','committedTicks','tickReports','upperBudget','droppedSeconds',
               'hasWholeTickBacklog'}
ROW_KEYS = {'name','scenario','frameOrdinal','externalEdit','input','inputAfter','worldBefore','worldAfter',
            'progressBefore','progressAfter','schedulerBefore','schedulerAfter','elapsedBits','report','observations'}
OBS_KEYS = {'captureComplete','pumpCalls','sourceUnchanged','settingsUnchanged','horizonUnchanged',
            'planesUnchanged','gravityUnchanged','worldUnchanged','progressUnchanged','pointerStability'}
STATUSES = {'waiting','step_budget','tick_rejected','invalid_input','unsupported_environment','numerical_failure','reentrant'}
REASONS = {'none','environment','binding_unsupported','elapsed','backlog_limit','sequence_limit','queue_arithmetic',
           'cost_overflow','allocation_failure','unexpected_exception','busy','advance_rejected'}
HARD_WORK = {'meshQueries':1024,'primitiveQueries':65536,'candidatesExamined':458752,
             'sqrtRefinements':16777216,'propagations':32,'planeMetricValues':1048576,
             'boxValues':1048576,'planeNormLoopIterationsUpper':64*1048576,'bridgeCallsUpper':32}


def interval(value, exact, label):
    need(type(value) is list and len(value) == 2, label+' interval pair')
    lo, hi = map(fraction, value)
    need(lo <= exact <= hi, label+' contains exact Fraction expression')


def same(a, b):
    try:
        equal(a, b, 'captured equality')
        return True
    except AssertionError:
        return False


def snapshot(value):
    fields(value, {'settings','backlog','sequence','busy'}, 'complete scheduler snapshot')
    fields(value['settings'], {'stepSeconds','maxAttemptsPerPump'}, 'immutable scheduler settings')
    h = fraction(value['settings']['stepSeconds'])
    cap = value['settings']['maxAttemptsPerPump']
    uint(cap, 8, 'attempt cap'); need(cap >= 1, 'positive attempt cap')
    need(fraction(2**-20) <= h <= fraction(.1), 'immutable step domain')
    b = fraction(value['backlog'])
    need(0 <= b <= 1 and not (int(bits(value['backlog']).hex(),16) >> 63), 'positive represented backlog including +0')
    uint(value['sequence'], 2**64-1, 'scheduler sequence')
    advance.boolean(value['busy'], 'snapshot busy')
    return h, b, cap


def binding(value):
    fields(value, {'profile','configured','buildId'}, 'owned scheduler binding')
    uint(value['profile'], 1, 'scheduler profile')
    advance.boolean(value['configured'], 'scheduler configured')
    advance.text(value['buildId'], 'scheduler identity')
    need(value['buildId'] == '' or re.fullmatch('[0-9a-f]{64}',value['buildId']), 'scheduler identity encoding')
    if value['configured']:
        need(value['profile'] == 1 and re.fullmatch('[0-9a-f]{64}',value['buildId']), 'separate configured source identity')
    else:
        need(value['profile'] == 0 and value['buildId'] == '', 'default unavailable binding')


def budget(value, count):
    fields(value, {'attempts','guardWork','guardLogicalPayloadBytes'}, 'complete retained planned upper budget')
    uint(value['attempts'], 8, 'budget attempts')
    fields(value['guardWork'], HARD_WORK, 'all nine settled work upper fields')
    for key, cap in HARD_WORK.items():
        uint(value['guardWork'][key], 2**64-1, 'upper budget '+key)
        need(value['guardWork'][key] == count*cap, 'planned slots retain hard settled upper '+key)
    uint(value['guardLogicalPayloadBytes'], 2**64-1, 'logical payload upper')
    need(value['attempts'] == count and value['guardLogicalPayloadBytes'] == count*16777216,
         'full reserved slots, including unexecuted tail; not physical heap/stack')


def source_fingerprint(rows):
    def encode(v):
        if type(v) is dict:
            return '{'+','.join(json.dumps(k)+':'+encode(v[k]) for k in sorted(v))+'}'
        if type(v) is list:
            return '['+','.join(encode(x) for x in v)+']'
        if type(v) is bool:return 'bool:'+str(v)
        if type(v) is int:return 'int:'+str(v)
        if type(v) is float:return 'f64:'+bits(v).hex()
        if type(v) is str:return 'string:'+json.dumps(v)
        need(v is None, 'fingerprint source scalar'); return 'null'
    # Context labels and document traversal order are excluded; per-scenario
    # ordinal, explicit edit kind and each original field/array ordinal remain.
    selected = [{key:r[key] for key in ('input','progressBefore','schedulerBefore','elapsedBits','frameOrdinal','externalEdit')} for r in rows]
    return hashlib.sha256(('\n'.join(sorted(encode(v) for v in selected))+'\n').encode()).hexdigest()


def new_stats():
    return {'fixtures':0,'scenarios':0,'elapsedAccepted':0,'unaccepted':0,'plannedAttempts':0,
            'advanceAttempts':0,'committedTicks':0,'unexecutedSlots':0,'actualOwnedGuardsVerified':0,
            'clockRefusedAdvances':0,'candidateBodyLinks':0,'outerPointerBodyObservations':0,
            'externallyObservedRefusals':0,'settledChargedWork':{key:0 for key in HARD_WORK},
            'guard':guard.new_stats()}


def advance_report(source, original_progress, report, layout, stats):
    """Pure actual Report audit. No constructed WorldAfter or pointer row input."""
    r = report
    fields(r, advance.RESULT_KEYS, 'complete actual nested AdvanceReport')
    need(type(r['status']) is str and r['status'] in advance.STATUSES and
         type(r['reason']) is str and r['reason'] in advance.REASONS, 'known actual advance enums')
    for key in ('committed','advanceProfileChecked','advanceProfileMatches'):
        advance.boolean(r[key], key)
    need(r['advanceProfileChecked'] and r['advanceProfileMatches'], 'actual scheduler called configured advance')
    advance.binding_shape(r['binding']); advance.failure_shape(r['failure'])
    advance.text(r['message'], 'retained outer AdvanceReport message')
    fields(r['work'], advance.WORK_KEYS, 'actual CommitWork')
    for key,value in r['work'].items():uint(value,2**64-1,'advance Work '+key)
    fields(r['storage'], advance.STORAGE_KEYS, 'actual CommitStorage')
    for key,value in r['storage'].items():uint(value,2**64-1,'advance storage '+key)
    advance.progress_shape(r['originalProgress'])
    equal(original_progress,r['originalProgress'],'actual original Progress links expected clock chain')
    equal(source['horizon'],r['requestedDt'],'actual advance uses the immutable requested step')
    status,reason,proposal=advance.predicted_clock(original_progress,source['horizon'])
    work={key:0 for key in advance.WORK_KEYS};storage={key:0 for key in advance.STORAGE_KEYS}
    expected_world={key:copy.deepcopy(source[key]) for key in ('bodies','planes','gravity')}
    expected_progress=copy.deepcopy(original_progress)
    if proposal is None:
        need(r['status']==status and r['reason']==reason and not r['committed'],'actual clock-first rejection')
        need(r['proposedProgress'] is r['clock'] is r['guard'] is r['guardMessage'] is None,
             'clock refusal has no manufactured guard or clock completion')
        equal({'stage':'clock','object':None},r['failure'],'clock failure metadata')
        stats['clockRefusedAdvances']+=1
    else:
        advance.progress_shape(r['proposedProgress'])
        need(bits(r['proposedProgress']['time']).hex()==proposal['bits'] and
             r['proposedProgress']['ticks']==proposal['ticks'],'independent integer-RN clock chain')
        advance.clock_audit(r['clock'],original_progress,source['horizon'],proposal)
        need(r['guard'] is not None,'missing actual guard remains unverified; never fill it from an expected result')
        advance.text(r['guardMessage'],'retained actual outer GuardResult message')
        # This is the expected caller/source chain, checked against the ACTUAL
        # captured guard origin. It is not an externally measured intermediate.
        guard.verify_fixture(source,r['guard'],layout,stats['guard'])
        stats['guard']['fixtures']+=1;stats['actualOwnedGuardsVerified']+=1
        equal(r['binding'],r['guard']['binding'],'actual guard/advance source identity')
        work.update(guardQueriesAttempted=1,guardQueriesReturned=1)
        settled=r['guard']['reservation']['charged']
        for key,cap in HARD_WORK.items():
            need(settled[key]<=cap,'actual settled charged upper within reserved per-call hard maximum')
            stats['settledChargedWork'][key]+=settled[key]
        if r['guard']['status']!='certified_separated':
            need(r['status']==r['guard']['status'] and r['reason']=='guard_failed' and not r['committed'],
                 'actual failed/unknown guard does not advance or consume credit')
            equal({'stage':'guard','object':None},r['failure'],'actual guard failure metadata')
        else:
            need(r['status']=='committed' and r['reason']=='none' and r['committed'] and r['failure'] is None,
                 'finite complete certified advance must retain its complete commit report')
            candidates=r['guard']['candidateBodies'];count=len(source['bodies'])
            need(type(candidates) is list and len(candidates)==count,'whole actual owned candidates')
            expected_world['bodies']=copy.deepcopy(candidates)
            for body in expected_world['bodies']:
                body['force']=[0.,0.,0.];body['torque']=[0.,0.,0.]
            expected_progress=copy.deepcopy(r['proposedProgress'])
            work.update(pairRecordsChecked=len(r['guard']['pairs']),callRecordsChecked=r['guard']['work']['childCallsAttempted'],
                originBodiesChecked=2*count,originPlanesChecked=2*len(source['planes']),
                originMeshesChecked=2*len(source['meshes']),originFacesChecked=2*sum(len(m['triangles']) for m in source['meshes']),
                candidatesCopied=count,candidateValidationsAttempted=count,candidatesValidated=count,
                destinationLookups=count,destinationsResolved=count,bodyAssignments=count,progressAssignments=1)
            storage.update(bodyBufferSlots=8,destinationSlots=8,bodyBufferSizeofBytes=8*layout['rigidBody'],destinationBufferSizeofBytes=64)
            stats['candidateBodyLinks']+=count
    equal(work,r['work'],'all actual nested advance work counters')
    equal(storage,r['storage'],'fixed named-buffer storage observation')
    if r['committed']:
        equal(source['horizon'],r['advancedDt'],'performed requested step, not represented time difference')
    else:
        need(bits(r['advancedDt']).hex()=='0000000000000000','failed advance +0 horizon and no candidate-prefix publication')
    return expected_world,expected_progress


def verify_row(row, layout, stats):
    fields(row,ROW_KEYS,'complete scheduler fixture')
    for key in ('name','scenario'):advance.text(row[key],key);need(row[key],'nonempty fixture context')
    uint(row['frameOrdinal'],1000000,'scenario frame ordinal')
    need(row['externalEdit'] is None or row['externalEdit']=='body-position-y-to-2','explicit bounded external edit')
    source,after,r=row['input'],row['inputAfter'],row['report']
    guard.source_shape(source);guard.source_shape(after)
    advance.world_shape(row['worldBefore']);advance.world_shape(row['worldAfter'])
    for key in ('progressBefore','progressAfter'):advance.progress_shape(row[key])
    h,before,cap=snapshot(row['schedulerBefore']);snapshot(row['schedulerAfter'])
    equal(row['worldBefore'],{key:source[key] for key in ('bodies','planes','gravity')},'actual outer original World/source')
    equal(row['worldAfter'],{key:after[key] for key in ('bodies','planes','gravity')},'actual outer final World/inputAfter')
    equal(source['horizon'],row['schedulerBefore']['settings']['stepSeconds'],'immutable exact step as source horizon')
    for key in ('planes','gravity','meshes','horizon','settings'):
        equal(source[key],after[key],'borrowed input unchanged '+key)
    fields(r,REPORT_KEYS,'all PumpReport fields')
    need(type(r['status']) is str and r['status'] in STATUSES and type(r['reason']) is str and r['reason'] in REASONS,'known scheduler enums')
    binding(r['binding']);snapshot(r['before']);snapshot(r['after'])
    equal(row['schedulerBefore'],r['before'],'actual outer scheduler before/report')
    equal(row['schedulerAfter'],r['after'],'actual outer scheduler after/report')
    equal(r['before']['settings'],r['after']['settings'],'immutable scheduler settings')
    equal(row['progressBefore'],r['progressBefore'],'actual outer Progress before/report')
    equal(row['progressAfter'],r['progressAfter'],'actual outer Progress after/report')
    credit.rawbits(row['elapsedBits']);need(r['requestedElapsedBits']==row['elapsedBits'],'full elapsed bits including nonfinite payload/-0')
    advance.boolean(r['elapsedAccepted'],'elapsed accepted');advance.boolean(r['hasWholeTickBacklog'],'backlog whole-tick flag')
    need(bits(r['droppedSeconds']).hex()=='0000000000000000','retain-only droppedSeconds is +0')
    counts=[r[k] for k in ('plannedAttempts','attempts','committedTicks')]
    for n in counts:uint(n,8,'scheduler slot count')
    planned,attempts,committed=counts;need(committed<=attempts<=planned<=cap,'complete bounded attempt/prefix counts')
    need(type(r['queuePlan']) is list and len(r['queuePlan'])==8 and type(r['tickReports']) is list and len(r['tickReports'])==8,
         'all eight nullable plan and report slots, including unexecuted tail')
    for i in range(8):
        need((r['queuePlan'][i] is not None)==(i<planned),'dense planned prefix and null tail')
        need((r['tickReports'][i] is not None)==(i<attempts),'dense executed prefix and null tail')
    accepted=r['elapsedAccepted'];finite_elapsed=credit.finite(row['elapsedBits'])
    elapsed=credit.number(row['elapsedBits']) if finite_elapsed else None
    domain_elapsed=finite_elapsed and 0<=elapsed<=1
    theoretical_credit=None;queue=[]
    if domain_elapsed and r['before']['sequence']<2**64-1:
        candidate=credit.rn(before+elapsed)
        if credit.number(candidate)<=1:
            theoretical_credit=candidate
            current=candidate
            while credit.number(current)>=h and len(queue)<cap:
                nxt=credit.rn(credit.number(current)-h)
                need(0<=credit.number(nxt)<credit.number(current),'independent represented queue progress')
                queue.append((current,nxt,credit.number(nxt)-(credit.number(current)-h)))
                current=nxt
    if r['admittedCredit'] is not None:
        need(theoretical_credit is not None and bits(r['admittedCredit']).hex()==theoretical_credit,'actual optional admission candidate')
        interval(r['admissionRoundingError'],credit.number(theoretical_credit)-(before+elapsed),'admission error')
    else:
        need(r['admissionRoundingError'] is None,'admission optional pair')
    need(planned==0 or r['admittedCredit'] is not None,'prepared queue requires its original admission proposal')
    need(planned<=len(queue),'stored pre-admission queue prefix within independently due plan')
    for i in range(planned):
        value=r['queuePlan'][i];fields(value,{'creditBefore','proposedAfter','roundingError'},'full QueueStep')
        a,b,error=queue[i]
        need(bits(value['creditBefore']).hex()==a and bits(value['proposedAfter']).hex()==b,'all queue integer-RN values')
        interval(value['roundingError'],error,'queue rounding error')
    expected_world=copy.deepcopy(row['worldBefore']);expected_progress=copy.deepcopy(row['progressBefore'])
    if not accepted:
        need(attempts==committed==0,'unaccepted input performs no advances')
        equal(r['before'],r['after'],'unaccepted scheduler state remains unchanged')
        budget(r['upperBudget'],0)
        if r['reason']=='elapsed':
            need(r['status']=='invalid_input' and not domain_elapsed,'actual elapsed validation priority')
        elif r['reason']=='sequence_limit':
            need(r['status']=='invalid_input' and domain_elapsed and r['before']['sequence']==2**64-1,'actual sequence limit')
        elif r['reason']=='backlog_limit':
            need(r['status']=='invalid_input' and domain_elapsed and r['before']['sequence']<2**64-1 and
                 credit.number(credit.rn(before+elapsed))>1,'actual represented backlog cap refusal')
        else:
            allowed={'environment':'unsupported_environment','binding_unsupported':'unsupported_environment',
                     'queue_arithmetic':'numerical_failure','cost_overflow':'invalid_input',
                     'allocation_failure':'numerical_failure','unexpected_exception':'numerical_failure','busy':'reentrant'}
            need(r['reason'] in allowed and r['status']==allowed[r['reason']],'external/exception pre-admission observation class')
            stats['externallyObservedRefusals']+=1
        if r['reason'] in {'elapsed','sequence_limit','backlog_limit','environment','binding_unsupported','busy'}:
            need(r['admittedCredit'] is None and planned==0,'early pre-admission refusal has no prepared proposal')
        need(r['hasWholeTickBacklog']==(before>=h),'refusal backlog flag describes retained original state')
        stats['unaccepted']+=1
    else:
        need(not r['before']['busy'] and r['binding']['configured'] and theoretical_credit is not None,
             'actual admitted call has configured/nonbusy finite state')
        need(r['admittedCredit'] is not None and planned==len(queue),'complete admission and precomputed due plan')
        budget(r['upperBudget'],planned)
        need(r['after']['sequence']==r['before']['sequence']+1 and r['after']['busy'] is False,'one scalar admission and nonbusy return')
        seen=0;settled_before=stats['settledChargedWork'].copy()
        for i in range(attempts):
            tick=r['tickReports'][i];fields(tick,{'queueIndex','creditConsumed','report'},'actual owned Attempt')
            uint(tick['queueIndex'],7,'actual queue index');need(tick['queueIndex']==i,'original planned attempt ordinal')
            advance.boolean(tick['creditConsumed'],'credit consumed')
            need(tick['creditConsumed']==tick['report']['committed'],'only actual complete commit consumes credit')
            call_source=copy.deepcopy(source)
            for key in ('bodies','planes','gravity'):call_source[key]=copy.deepcopy(expected_world[key])
            expected_world,expected_progress=advance_report(call_source,expected_progress,tick['report'],layout,stats)
            if tick['creditConsumed']:
                seen+=1
            else:
                need(i+1==attempts and r['status']=='tick_rejected' and r['reason']=='advance_rejected','first actual tick refusal stops all later slots')
        need(seen==committed and (attempts==planned or (attempts>0 and not r['tickReports'][attempts-1]['creditConsumed'])),
             'complete observed committed prefix and unexecuted rejection tail')
        for key in HARD_WORK:
            need(stats['settledChargedWork'][key]-settled_before[key]<=r['upperBudget']['guardWork'][key],
                 'actual settled charged upper bounded; never compare cumulative granted/refunded work')
        after_credit=theoretical_credit if committed==0 else queue[committed-1][1]
        need(bits(r['after']['backlog']).hex()==after_credit,'only committed ticks consume retained credit')
        whole=credit.number(after_credit)>=h
        need(r['hasWholeTickBacklog']==whole,'actual final represented backlog flag')
        if attempts==committed:
            need(r['reason']=='none' and r['status']==('step_budget' if whole else 'waiting'),'waiting/budget result, no implicit drop')
        stats['elapsedAccepted']+=1
    equal(expected_world,row['worldAfter'],'expected candidate chain endpoint versus ACTUAL outer WorldAfter')
    equal(expected_progress,row['progressAfter'],'independent clock chain versus ACTUAL outer ProgressAfter')
    o=row['observations'];fields(o,OBS_KEYS,'all actual outer-only observations')
    uint(o['pumpCalls'],1,'actual outer pump calls');need(o['pumpCalls']==1,'one fresh actual pump')
    for key in ('captureComplete','sourceUnchanged','settingsUnchanged','horizonUnchanged','planesUnchanged','gravityUnchanged'):
        advance.boolean(o[key],key);need(o[key],'outer unchanged source observation '+key)
    for key,a,b in [('worldUnchanged',row['worldBefore'],row['worldAfter']),('progressUnchanged',row['progressBefore'],row['progressAfter'])]:
        advance.boolean(o[key],key);need(o[key]==same(a,b),'actual full before/after observation '+key)
    advance.pointer_observations(o['pointerStability'],source)
    stats['outerPointerBodyObservations']+=len(source['bodies'])
    stats['fixtures']+=1;stats['plannedAttempts']+=planned;stats['advanceAttempts']+=attempts
    stats['committedTicks']+=committed;stats['unexecutedSlots']+=planned-attempts


def histories(rows):
    groups={}
    for row in rows:groups.setdefault(row['scenario'],[]).append(row)
    for frames in groups.values():
        frames=sorted(frames,key=lambda r:r['frameOrdinal'])
        need([r['frameOrdinal'] for r in frames]==list(range(len(frames))),'dense unique scenario frame ordinals independent of document order')
        first=frames[0]
        need(first['externalEdit'] is None and first['schedulerBefore']['sequence']==0 and
             bits(first['schedulerBefore']['backlog']).hex()=='0000000000000000' and
             first['schedulerBefore']['busy'] is False,'fresh Scheduler initial state, no invented prior admission')
        for previous,current in zip(frames,frames[1:]):
            equal(previous['schedulerAfter'],current['schedulerBefore'],'actual scheduler history continuity')
            equal(previous['progressAfter'],current['progressBefore'],'actual Progress history continuity')
            expected=copy.deepcopy(previous['inputAfter'])
            if current['externalEdit'] is not None:
                need(current['externalEdit']=='body-position-y-to-2','only explicit authored World edit')
                body=next((b for b in expected['bodies'] if b['id']==101),None)
                need(body is not None,'explicit edited body exists');body['position'][1]=2.
            equal(expected,current['input'],'actual frame input continuity with only the explicitly stored caller edit')
    return len(groups)


def verify(data, *, development_unpinned=False):
    need(__debug__,'Protected references require normal Python; optimized execution is refused')
    advance.finite_tree(data)
    fields(data,{'schema','kind','scope','layoutSizes','advanceLayoutSizes','schedulerLayoutSizes','maximumDocumentBytes','fixtures'},'full scheduler envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='world-static-mesh-flight-scheduler-fixtures','scheduler schema/kind')
    advance.text(data['scope'],'serializer scope');uint(data['maximumDocumentBytes'],MAX_DOCUMENT_BYTES,'document budget')
    need(data['maximumDocumentBytes']==MAX_DOCUMENT_BYTES,'declared bounded complete document')
    guard.layout_shape(data['layoutSizes'])
    for key,names in [('advanceLayoutSizes',{'AdvanceReport','Progress','ClockAudit','CommitWork','CommitStorage'}),
                      ('schedulerLayoutSizes',{'Settings','Snapshot','Binding','QueueStep','Attempt','UpperBudget','PumpReport','Scheduler'})]:
        fields(data[key],names,'same-run public sizeof observations')
        for value in data[key].values():uint(value,1048576,'observed sizeof');need(value>0,'positive sizeof')
    rows=data['fixtures'];need(type(rows) is list and 0<len(rows)<=512,'bounded actual finite corpus')
    for row in rows:fields(row,ROW_KEYS,'complete row before input fingerprint')
    fingerprint=source_fingerprint(rows)
    frozen=EXPECTED_FIXTURE_COUNT is not None and EXPECTED_INPUT_FINGERPRINT is not None
    need(frozen or development_unpinned,'Actual complete input corpus not yet pinned; use explicit development mode only')
    if frozen:
        need(len(rows)==EXPECTED_FIXTURE_COUNT and fingerprint==EXPECTED_INPUT_FINGERPRINT,'full original input types/bits/array order fingerprint')
    stats=new_stats();labels=set();scheduler_ids=set();advance_ids=set()
    for row in rows:
        need(type(row['name']) is str and row['name'] and row['name'] not in labels,'unique labels, not expected mathematical results')
        labels.add(row['name']);verify_row(row,data['layoutSizes'],stats)
        if row['report']['binding']['configured']:scheduler_ids.add(row['report']['binding']['buildId'])
        for tick in row['report']['tickReports']:
            if tick is not None:advance_ids.add(tick['report']['binding']['buildId'])
    need(len(scheduler_ids)<=1 and len(advance_ids)<=1,'distinct scheduler/advance identities consistent within their own corpus, not equated')
    stats['scenarios']=histories(rows)
    return {'status':'PASS' if frozen else 'DEVELOPMENT_PASS_UNPINNED',**stats,'inputFingerprint':fingerprint,
        'scope':'Actual outer World/Progress/source/scheduler/pointer observations; exact integer/Fraction RN admission, queue, prefix and clock ledgers; complete actual nested AdvanceReports/owned guard mathematics and expected candidate-to-captured-origin chain. No fabricated intermediate WorldAfter/pointer rows and no production queries. Settled charged hard upper products retain all planned/unexecuted slots; granted/refunded totals are separate. Outer pointer booleans and sizeof are Native observations, not address or memory/atomicity proofs. Missing actual guard remains unverified. Protected child references retain their exact quadratic+B versus downstream recorded-box RN/root scope. Exception causes, natural faults, complete machine clock/commit/scheduler proof, response, SDK and game integration remain outside this finite acceptance.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture',type=Path)
    parser.add_argument('--development-unpinned',action='store_true')
    args=parser.parse_args()
    print(json.dumps(verify(load(args.fixture),development_unpinned=args.development_unpinned)))
