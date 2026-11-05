"""Independent finite packet-scheduler reference; no production execution.

Integer/Fraction RN credit, packet consumption, actual fixed World boundaries
and actual ControlledReport mathematics are checked separately. No fabricated
child WorldAfter/lookup/pointer rows are passed to protected full-row checkers.
"""
from pathlib import Path
import argparse
import copy
import importlib.util
import json
import re
import sys

if not __debug__:
    raise ValueError('Protected reference requires normal Python; -O verification is refused')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('packet_scheduler_controlled_primitives',ROOT/'scripts/verify-world-static-mesh-flight-controlled-tick.py')
controlled=importlib.util.module_from_spec(spec);spec.loader.exec_module(controlled)
advance,guard,clock=controlled.advance,controlled.guard,controlled.advance.clock
need,fields,uint=controlled.need,controlled.fields,controlled.uint
equal,bits,fraction,load=controlled.equal,controlled.bits,controlled.fraction,controlled.load
EXPECTED_FIXTURE_COUNT=84
EXPECTED_INPUT_FINGERPRINT='26e21e83eadab0b998100dc1ee9e7ef45f03adfee93c49f0ce920d04fad46a7c'
MAX_DOCUMENT=64*1024*1024
U64=(1<<64)-1
REPORT_KEYS={'status','reason','binding','before','after','requestedElapsed','elapsedAccepted','admittedCredit','admissionRoundingError',
 'progressBefore','progressAfter','capture','original','boundaries','queuePlan','tickReports','boundaryCount','plannedAttempts','attempts',
 'committedTicks','packetsConsumed','upperBudget','work','storage','droppedSeconds','hasWholeTickBacklog'}
ROW_KEYS={'name','scenario','frameOrdinal','requestedElapsed','input','inputAfter','report','observations'}
WORK_KEYS={'boundaryCaptures','bodyObservations','planeObservations','meshCopies','faceCopies','packetCopies','loadCopies'}
STORAGE_KEYS={'boundarySlots','boundarySizeofBytes','addressSlots','addressSizeofBytes'}
STATUSES={'waiting','step_budget','awaiting_input','tick_rejected','invalid_input','unsupported_environment','numerical_failure','reentrant'}
REASONS={'none','busy','environment','binding_unsupported','body_count','plane_count','mesh_count','face_count','packet_count','packet_load_count',
 'elapsed','backlog_limit','sequence_limit','queue_arithmetic','cost_overflow','allocation_failure','unexpected_exception','packet_unavailable','controlled_rejected'}


def source_shape(source):
    fields(source,{'scene','progress','packets'},'whole caller input')
    guard.source_shape(source['scene']);controlled.original_progress_shape(source['progress'])
    need(type(source['packets']) is list and len(source['packets'])<=1024,'bounded original packet vector')
    for packet in source['packets']:controlled.packet_shape(packet)


def snapshot(value):
    fields(value,{'settings','backlog','sequence','busy'},'all scheduler snapshot fields')
    fields(value['settings'],{'step','maxAttempts'},'immutable exact scheduler settings')
    h=fraction(value['settings']['step']);cap=value['settings']['maxAttempts']
    need(fraction(2**-20)<=h<=fraction(.1),'fixed step domain');uint(cap,8,'attempt cap');need(cap>=1,'positive attempt cap')
    backlog=fraction(value['backlog']);need(0<=backlog<=1 and not (int(bits(value['backlog']).hex(),16)>>63),'nonnegative represented backlog, +0 only')
    uint(value['sequence'],U64,'pump sequence');advance.boolean(value['busy'],'busy');need(value['busy'] is False,'finite nonreentrant corpus')
    return h,backlog,cap


def binding(value):
    fields(value,{'profile','configured','buildId','controlledBuildId','schedulerBuildId','upstreamBuildId'},'four distinct configuration identities')
    need(type(value['profile']) is int and value['profile']==1 and value['configured'] is True,'actually configured finite corpus')
    ids=[]
    for key in ('buildId','controlledBuildId','schedulerBuildId','upstreamBuildId'):
        v=value[key];need(type(v) is str and re.fullmatch('[0-9a-f]{64}',v),'full identity '+key);ids.append(v)
    need(len(set(ids))==4,'new parent/controlled/clock/seven-source identities stay separate')
    return tuple(ids)


def interval(value,exact,label):
    need(type(value) is list and len(value)==2,label+' interval pair')
    lo,hi=map(fraction,value);need(lo<=exact<=hi,label+' contains the exact Fraction expression')


def boundary_shape(value):
    fields(value,{'world','progress','originalBodyAddressSame'},'actual fixed boundary only')
    advance.world_shape(value['world']);controlled.original_progress_shape(value['progress'])
    need(len(value['world']['bodies'])<=8 and len(value['world']['planes'])<=16,'fixed active prefixes')
    flags=value['originalBodyAddressSame'];need(type(flags) is list and len(flags)==len(value['world']['bodies']),'all active body address observations')
    for v in flags:advance.boolean(v,'original body address observation');need(v,'actual stable original body address')


def actual_controlled(source,report,actual_world_after,actual_progress_after,layout,stats):
    """Pure Report audit with ACTUAL fixed-boundary IO, no invented pointer row.

    Input phases reuse the frozen input-only reference. Only the actual returned
    AdvanceReport goes to the frozen pure advance_report/guard mathematics.
    """
    controlled.input_shape(source);controlled.report_shape(report)
    scene,packet,p=source['scene'],source['packet'],source['progress'];r=report
    world={k:copy.deepcopy(scene[k]) for k in ('bodies','planes','gravity')}
    equal(scene['horizon'],r['requestedDt'],'actual controlled H');equal(p,r['originalProgress'],'actual controlled original Progress')
    equal(packet['mode'],r['requestedMode'],'actual source mode');equal(packet['expectedTick'],r['requestedTick'],'actual integer tick')
    equal({'candidateSlots':8,'destinationSlots':8,'candidateSizeofBytes':8*layout['rigidBody'],'destinationSizeofBytes':64},r['storage'],'controlled fixed named buffers')
    expected=controlled.preflight_reference(source);work=copy.deepcopy(expected['work'])
    equal(expected['capture'],r['capture'],'controlled capture phase');equal(expected['originalBodiesValidated'],r['originalBodiesValidated'],'original validation prefix')
    equal(expected['mappings'],r['mappings'],'ID resolution prefix and null tail')
    original=None if expected['capture']=='none' else {'horizon':scene['horizon'],'settings':scene['settings'],'progress':p,'world':world,'meshes':scene['meshes'],'packet':packet}
    equal(original,r['original'],'all owned original data')
    result_world=copy.deepcopy(world);result_progress=copy.deepcopy(p);result_status='invalid_input';result_reason=None;failure=None
    if expected['failure'] is not None:
        f=expected['failure'];result_reason=f['reason'];failure={k:v for k,v in f.items() if k!='reason'}
        need(r['stagedBefore'] is r['privateAfter'] is r['privateProgressAfter'] is r['child'] is None,'preflight cannot fabricate private state/child')
        need(r['stagedCapture']==r['privateAfterCapture']=='none','private capture absent before child');stats['preflightRefusals']+=1
    else:
        staged=expected['stagedWorld'];equal(staged,r['stagedBefore'],'absolute replacement, not addition')
        need(r['stagedCapture']==r['privateAfterCapture']=='complete' and r['child'] is not None,'actual finite private child/captures required')
        count=len(world['bodies']);planes=len(world['planes'])
        work.update(privateCopiesAttempted=1,privateCopiesReturned=1,stagedBodiesCopied=count,stagedPlanesCopied=planes,
                    privateAfterBodiesCopied=count,privateAfterPlanesCopied=planes,childAttempts=1,childReturns=1)
        staged_scene={**copy.deepcopy(scene),**copy.deepcopy(staged)}
        child_world,child_progress=controlled.scheduler.advance_report(staged_scene,p,r['child'],layout,stats['child'])
        equal(child_world,r['privateAfter'],'actual private after matches actual child');equal(child_progress,r['privateProgressAfter'],'actual private Progress')
        need(r['child']['binding']['buildId']==r['binding']['upstreamBuildId'],'actual upstream identity linkage');stats['actualChildrenVerified']+=1
        if r['child']['committed']:
            work.update(candidateBodiesChecked=count,candidateValidationsAttempted=count,candidateValidationsReturned=count,
                originBodiesChecked=count,originPlanesChecked=planes,originMeshesChecked=len(scene['meshes']),
                originFacesChecked=sum(len(m['triangles']) for m in scene['meshes']),originPacketRowsChecked=len(packet['loads']),
                destinationLookups=count,destinationsResolved=count,bodyAssignments=count,progressAssignments=1)
            for body in child_world['bodies']:
                need(guard.prep.body_valid(body),'actual cleared candidate validates')
                need(all(bits(x).hex()=='0000000000000000' for key in ('force','torque') for x in body[key]),'all consumed loads +0')
            result_world,result_progress=child_world,child_progress;result_status='committed';result_reason='none';stats['candidateBodiesCompared']+=count
        else:
            result_status=r['child']['status'];result_reason='child_failed';failure={'stage':'child','bodyOrdinal':None,'packetOrdinal':None,'meshOrdinal':None};stats['privateRefusals']+=1
    need(r['status']==result_status and r['reason']==result_reason and r['committed']==(result_status=='committed'),'normal finite controlled outcome; unknown faults fail closed')
    equal(failure,r['failure'],'controlled first failure');equal(work,r['work'],'all controlled operation counters')
    equal(result_world,actual_world_after,'ACTUAL fixed World boundary after child, no expected-state substitution')
    equal(result_progress,actual_progress_after,'ACTUAL fixed Progress boundary after child')
    if r['committed']:equal(scene['horizon'],r['advancedDt'],'performed requested H');need(r['message']=='','successful message empty');stats['committed']+=1
    else:need(bits(r['advancedDt']).hex()=='0000000000000000','failed outer +0 duration');stats['failed']+=1
    stats['fixtures']+=1;stats['statusCounts'][r['status']]+=1
    return result_world,result_progress


def count_failure(scene,packets):
    if len(scene['bodies'])>8:return 'body_count'
    if len(scene['planes'])>16:return 'plane_count'
    if len(scene['meshes'])>4:return 'mesh_count'
    if sum(len(m['triangles']) for m in scene['meshes'])>64:return 'face_count'
    if len(packets)>8:return 'packet_count'
    if any(len(p['loads'])>8 for p in packets):return 'packet_load_count'
    return None


def verify_row(row,layout,parent_layout,stats):
    fields(row,ROW_KEYS,'complete native parent row');source_shape(row['input']);source_shape(row['inputAfter'])
    for key in ('name','scenario'):advance.text(row[key],key);need(row[key],'nonempty label, not semantic oracle')
    uint(row['frameOrdinal'],512,'frame ordinal');elapsed=fraction(row['requestedElapsed'])
    source,after,r=row['input'],row['inputAfter'],row['report'];scene,p,packets=source['scene'],source['progress'],source['packets']
    fields(r,REPORT_KEYS,'all parent report fields');binding(r['binding']);h,backlog,cap=snapshot(r['before']);snapshot(r['after'])
    equal(r['before']['settings'],r['after']['settings'],'immutable settings');equal(scene['horizon'],r['before']['settings']['step'],'actual constructor step used as H')
    fraction(r['requestedElapsed']);controlled.original_progress_shape(r['progressBefore']);controlled.original_progress_shape(r['progressAfter'])
    equal(row['requestedElapsed'],r['requestedElapsed'],'raw elapsed bits');equal(p,r['progressBefore'],'actual original Progress');equal(after['progress'],r['progressAfter'],'actual final Progress')
    need(type(r['status']) is str and r['status'] in STATUSES and type(r['reason']) is str and r['reason'] in REASONS,'known enums')
    for key in ('elapsedAccepted','hasWholeTickBacklog'):advance.boolean(r[key],key)
    need(type(r['capture']) is str and r['capture'] in {'none','partial','complete'},'capture state')
    need(bits(r['droppedSeconds']).hex()=='0000000000000000','retain-only +0 dropped time')
    for key in ('boundaryCount','plannedAttempts','attempts','committedTicks','packetsConsumed'):uint(r[key],9,'bounded '+key)
    need(type(r['boundaries']) is list and len(r['boundaries'])==9 and type(r['queuePlan']) is list and len(r['queuePlan'])==8 and type(r['tickReports']) is list and len(r['tickReports'])==8,'all fixed slots, including null tail')
    fields(r['work'],WORK_KEYS,'all parent copy/observation work');fields(r['storage'],STORAGE_KEYS,'named fixed-buffer observations')
    for k,v in {**r['work'],**r['storage']}.items():uint(v,U64,k)
    expected_work={k:0 for k in WORK_KEYS};expected_storage={k:0 for k in STORAGE_KEYS}
    failure=count_failure(scene,packets);capture='none' if failure else 'complete'
    equal(capture,r['capture'],'hard counts before capture')
    expected_original=None if failure else {'settings':scene['settings'],'meshes':scene['meshes'],'packets':packets}
    if r['original'] is not None:
        fields(r['original'],{'settings','meshes','packets'},'typed owned parent source')
        guard.source_shape({**scene,'meshes':r['original']['meshes'],'settings':r['original']['settings']})
        need(type(r['original']['packets']) is list,'owned packet array')
        for packet in r['original']['packets']:controlled.packet_shape(packet)
    equal(expected_original,r['original'],'whole owned source/settings/packet vector')
    world={k:copy.deepcopy(scene[k]) for k in ('bodies','planes','gravity')};progress=copy.deepcopy(p)
    if not failure:
        expected_storage={'boundarySlots':9,'boundarySizeofBytes':9*parent_layout['OptionalBoundary'],'addressSlots':8,'addressSizeofBytes':64}
        expected_work.update(boundaryCaptures=1,bodyObservations=len(world['bodies']),planeObservations=len(world['planes']),
            meshCopies=len(scene['meshes']),faceCopies=sum(len(m['triangles']) for m in scene['meshes']),packetCopies=len(packets),loadCopies=sum(len(x['loads']) for x in packets))
        need(r['boundaries'][0] is not None,'actual initial fixed boundary');boundary_shape(r['boundaries'][0])
        equal(world,r['boundaries'][0]['world'],'actual original fixed World');equal(p,r['boundaries'][0]['progress'],'actual original fixed Progress')
    credit_bits=None;queue=[]
    if not failure:
        if not 0<=elapsed<=1:failure='elapsed'
        elif r['before']['sequence']==U64:failure='sequence_limit'
        else:
            candidate=clock.rn(backlog+elapsed)
            if clock.number(candidate)>1:failure='backlog_limit'
            else:
                credit_bits=candidate;current=candidate
                while clock.number(current)>=h and len(queue)<cap:
                    nxt=clock.rn(clock.number(current)-h);need(0<=clock.number(nxt)<clock.number(current),'RN queue numerical progress')
                    queue.append((current,nxt,clock.number(nxt)-(clock.number(current)-h)));current=nxt
    equal(credit_bits is not None,r['elapsedAccepted'],'admission derived from actual finite inputs, not status')
    expected_status='invalid_input';expected_reason=failure;attempts=committed=0;final_credit=bits(r['before']['backlog']).hex()
    if credit_bits is None:
        equal(r['before'],r['after'],'pre-admission snapshot unchanged');need(r['admittedCredit'] is r['admissionRoundingError'] is None,'unadmitted optional data absent')
    else:
        need(bits(r['admittedCredit']).hex()==credit_bits,'integer ties-even admitted credit')
        interval(r['admissionRoundingError'],clock.number(credit_bits)-(backlog+elapsed),'admission RN error')
        need(r['after']['sequence']==r['before']['sequence']+1,'elapsed accepted exactly once');final_credit=credit_bits
        expected_status='waiting';expected_reason='none'
        for i in range(len(queue)):
            if i>=len(packets):expected_status='awaiting_input';expected_reason='packet_unavailable';break
            tick=r['tickReports'][i];need(tick is not None,'actual controlled report for available due packet')
            fields(tick,{'queueIndex','packetOrdinal','creditConsumed','packetConsumed','report'},'whole actual controlled attempt')
            need(type(tick['queueIndex']) is int and tick['queueIndex']==i and type(tick['packetOrdinal']) is int and tick['packetOrdinal']==i,'actual sequential queue/packet ordinals')
            before=r['boundaries'][i];observed=r['boundaries'][i+1];need(before is not None and observed is not None,'actual before/after fixed boundaries')
            boundary_shape(before);boundary_shape(observed);equal(world,before['world'],'actual continuous World prefix');equal(progress,before['progress'],'actual continuous clock prefix')
            child_source={'scene':{**copy.deepcopy(scene),**copy.deepcopy(before['world'])},'progress':copy.deepcopy(before['progress']),'packet':copy.deepcopy(packets[i])}
            tr=tick['report'];need(tr['binding']['buildId']==r['binding']['controlledBuildId'] and tr['binding']['upstreamBuildId']==r['binding']['upstreamBuildId'],'actual two-layer identity references')
            world,progress=actual_controlled(child_source,tr,observed['world'],observed['progress'],layout,stats['controlled'])
            attempts+=1
            for key in ('creditConsumed','packetConsumed'):advance.boolean(tick[key],key);need(tick[key]==tr['committed'],'consume only actual OUTER controlled commit')
            expected_work['boundaryCaptures']+=1;expected_work['bodyObservations']+=len(world['bodies']);expected_work['planeObservations']+=len(world['planes'])
            if not tr['committed']:expected_status='tick_rejected';expected_reason='controlled_rejected';break
            committed+=1;final_credit=queue[i][1]
        else:
            expected_status='step_budget' if clock.number(final_credit)>=h else 'waiting'
        need(bits(r['after']['backlog']).hex()==final_credit,'retained exact credit after committed prefix only')
    need(r['status']==expected_status and r['reason']==expected_reason,'complete normal finite parent outcome; external faults are not fabricated')
    need(r['plannedAttempts']==len(queue) and r['attempts']==attempts and r['committedTicks']==committed and r['packetsConsumed']==committed,'all due/attempt/consumption counts')
    boundary_count=0 if capture=='none' else attempts+1;need(r['boundaryCount']==boundary_count,'all actual attempted boundaries including failed child')
    for i in range(9):
        need((r['boundaries'][i] is not None)==(i<boundary_count),'complete fixed boundary prefix and null tail')
        if r['boundaries'][i] is not None:boundary_shape(r['boundaries'][i]);stats['fixedBoundaryBodyObservations']+=len(r['boundaries'][i]['world']['bodies'])
    for i in range(8):
        need((r['tickReports'][i] is not None)==(i<attempts),'dense actual reports and null unexecuted tail')
        q=r['queuePlan'][i];need((q is not None)==(i<len(queue)),'dense time plan and null unplanned tail')
        if q is not None:
            fields(q,{'creditBefore','proposedAfter','roundingError'},'complete queue subtraction');a,b,e=queue[i]
            need(bits(q['creditBefore']).hex()==a and bits(q['proposedAfter']).hex()==b,'integer RN every planned subtraction');interval(q['roundingError'],e,'queue RN error')
    fields(r['upperBudget'],{'attempts','guardWork','guardLogicalPayloadBytes'},'reserved upper budget including unexecuted tail')
    uint(r['upperBudget']['attempts'],8,'reserved slots');uint(r['upperBudget']['guardLogicalPayloadBytes'],U64,'logical byte reservation')
    fields(r['upperBudget']['guardWork'],controlled.scheduler.HARD_WORK,'all reserved guard-work counters')
    for key,value in r['upperBudget']['guardWork'].items():uint(value,U64,'reserved '+key)
    equal({'attempts':len(queue),'guardWork':{k:len(queue)*v for k,v in controlled.scheduler.HARD_WORK.items()},'guardLogicalPayloadBytes':len(queue)*16*1024*1024},r['upperBudget'],'checked per-slot reservation, not measured heap/work')
    equal(expected_work,r['work'],'all actual parent capture/copy/fixed-observation counters');equal(expected_storage,r['storage'],'observed named buffers only; default0 does not mean physical allocation0')
    equal(clock.number(final_credit)>=h,r['hasWholeTickBacklog'],'whole tick backlog flag')
    expected_after=copy.deepcopy(source);expected_after['scene'].update(world);expected_after['progress']=progress
    equal(expected_after,after,'actual caller IO: World/Progress successful prefix only')
    o=row['observations'];fields(o,{'pumpCalls','sourceSettingsPacketsUnchanged','pointerStability'},'actual outer pump observations')
    need(type(o['pumpCalls']) is int and o['pumpCalls']==1 and o['sourceSettingsPacketsUnchanged'] is True,'actual one call and unchanged external source/settings/packet')
    advance.pointer_observations(o['pointerStability'],scene)
    stats['frames']+=1;stats['admitted']+=int(credit_bits is not None);stats['attempts']+=attempts;stats['committedTicks']+=committed;stats['statusCounts'][r['status']]=stats['statusCounts'].get(r['status'],0)+1


def histories(rows):
    groups={}
    for row in rows:groups.setdefault(row['scenario'],[]).append(row)
    for group in groups.values():
        group.sort(key=lambda r:r['frameOrdinal']);need([r['frameOrdinal'] for r in group]==list(range(len(group))),'unique dense scenario ordinals')
        first=group[0]['report']['before'];need(first['sequence']==0 and bits(first['backlog']).hex()=='0000000000000000','fresh scheduler origin')
        for previous,current in zip(group,group[1:]):
            equal(previous['report']['after'],current['report']['before'],'actual pump state history')
            equal(previous['inputAfter']['scene'],current['input']['scene'],'actual scene history, no hidden edit')
            equal(previous['inputAfter']['progress'],current['input']['progress'],'actual Progress history; packets alone may change')
    return len(groups)


def fingerprint(rows):
    # Reuse only the frozen generic type/bit/array-preserving input encoder.
    # This is not a fabricated child or a call to a protected full-row checker.
    return controlled.fingerprint([{'frameOrdinal':r['frameOrdinal'],'input':{'source':r['input'],'elapsed':r['requestedElapsed'],'settings':r['report']['before']['settings']}} for r in rows])


def verify(data,*,development_unpinned=False):
    advance.finite_tree(data)
    fields(data,{'schema','kind','scope','maximumDocumentBytes','layoutSizes','controlledSchedulerLayoutSizes','fixtures','directedHardCountAssertions'},'complete parent envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='world-static-mesh-flight-controlled-scheduler-fixtures','known schema/kind')
    advance.text(data['scope'],'producer scope');need(type(data['maximumDocumentBytes']) is int and data['maximumDocumentBytes']==MAX_DOCUMENT,'bounded document contract')
    need(type(data['directedHardCountAssertions']) is int and data['directedHardCountAssertions']==4,'actual producer hard-bound assertions')
    guard.layout_shape(data['layoutSizes']);layout=data['controlledSchedulerLayoutSizes']
    fields(layout,{'PumpReport','WorldState','Boundary','OptionalBoundary','Original','Attempt','OptionalAttempt','Storage'},'same-run named sizeof')
    for k,v in layout.items():uint(v,1048576,'sizeof '+k);need(v>0,'positive sizeof observation')
    rows=data['fixtures'];need(type(rows) is list and 1<=len(rows)<=512,'bounded finite rows')
    for r in rows:fields(r,ROW_KEYS,'whole row before fingerprint');source_shape(r['input'])
    fp=fingerprint(rows)
    if not development_unpinned:
        need(EXPECTED_FIXTURE_COUNT is not None and EXPECTED_INPUT_FINGERPRINT is not None,'Actual full corpus not pinned; explicit development mode required')
        need(len(rows)==EXPECTED_FIXTURE_COUNT and fp==EXPECTED_INPUT_FINGERPRINT,'complete actual input types/bits/ordinal fingerprint')
    stats={'frames':0,'admitted':0,'attempts':0,'committedTicks':0,'statusCounts':{},'fixedBoundaryBodyObservations':0,'controlled':controlled.new_stats()}
    names=set();identities=set()
    for row in rows:
        need(row['name'] not in names,'unique labels');names.add(row['name']);verify_row(row,data['layoutSizes'],layout,stats);identities.add(binding(row['report']['binding']))
    need(len(identities)==1,'one actually observed four-identity family tuple')
    stats['scenarios']=histories(rows)
    return {'status':'PASS',**stats,'inputFingerprint':fp,'developmentUnpinned':development_unpinned,
        'scope':'Finite actual fixed-boundary/packet/credit metadata and pure actual controlled/advance/guard mathematics. Integer/Fraction RN time plan, complete successful prefix and all unused slots. No production query, fabricated intermediate World/pointer/lookup row, unknown-fault success, allocation/post-child fault injection, whole instruction proof, GNU/new formal CMake/SDK acceptance. sizeof is an observation of named buffers only.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixture',type=Path);parser.add_argument('--development-unpinned',action='store_true');args=parser.parse_args()
    need(args.fixture.stat().st_size<=MAX_DOCUMENT,'bounded actual input file')
    print(json.dumps(verify(load(args.fixture),development_unpinned=args.development_unpinned)))
