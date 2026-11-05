"""Independent finite controlled-load transaction reference.

Helpers do not query production or turn synthetic data into Native acceptance.
The full-row audit checks the actual owned serializer. Original, staged private and externally committed
states remain distinct; no intermediate pointer observations are fabricated.
"""
from pathlib import Path
from fractions import Fraction
import copy
import importlib.util
import json
import argparse
import hashlib
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('controlled_tick_advance_primitives',ROOT/'scripts/verify-world-static-mesh-flight-advance.py')
advance=importlib.util.module_from_spec(spec);spec.loader.exec_module(advance)
guard=advance.guard
spec=importlib.util.spec_from_file_location('controlled_tick_actual_report_primitives',ROOT/'scripts/verify-world-static-mesh-flight-scheduler.py')
scheduler=importlib.util.module_from_spec(spec);spec.loader.exec_module(scheduler)
need,fields,uint=advance.need,advance.fields,advance.uint
load,loads,bits,fraction,equal=advance.load,advance.loads,advance.bits,advance.fraction,advance.equal
MAX_ID=(1<<53)-1
MAX_U64=(1<<64)-1
LOAD_CAP=fraction(1e24)
EXPECTED_FIXTURE_COUNT=88
EXPECTED_INPUT_FINGERPRINT='9f0648d696a5dbd349c2882ccfb1427a7f5a690b1dbd9572e6200997e8f6ed75'
WORK_KEYS={'originalBodiesCopied','originalPlanesCopied','originalMeshesCopied','originalFacesCopied','packetRowsCopied',
 'originalValidationsAttempted','originalValidationsReturned','packetRowsChecked','packetValidationsAttempted','packetValidationsReturned',
 'privateCopiesAttempted','privateCopiesReturned','stagedBodiesCopied','stagedPlanesCopied','privateAfterBodiesCopied','privateAfterPlanesCopied',
 'childAttempts','childReturns','candidateBodiesChecked','candidateValidationsAttempted','candidateValidationsReturned',
 'originBodiesChecked','originPlanesChecked','originMeshesChecked','originFacesChecked','originPacketRowsChecked',
 'destinationLookups','destinationsResolved','bodyAssignments','progressAssignments'}


def original_progress_shape(progress):
    fields(progress,{'time','ticks'},'original Progress, including finite model-invalid values')
    fraction(progress['time']);uint(progress['ticks'],MAX_U64,'original uint64 ticks, not binary64')


def input_shape(source):
    fields(source,{'scene','progress','packet'},'full original controlled input')
    guard.source_shape(source['scene']);original_progress_shape(source['progress']);packet_shape(source['packet'])


def preflight_reference(source):
    """Input-only count/capture/body/packet contract; never executes a query.

    Normal finite semantic phases only. Allocation/environment/configuration
    observations are not inferred from input and cannot be filled as successes.
    """
    input_shape(source);scene=source['scene'];packet=source['packet']
    bodies,planes,meshes=scene['bodies'],scene['planes'],scene['meshes'];rows=packet['loads']
    result={'capture':'none','originalBodiesValidated':False,'mappings':[None]*8,
            'work':{k:0 for k in WORK_KEYS},'failure':None,'stagedWorld':None}
    work=result['work']
    def fail(reason,stage,body=None,row=None,mesh=None):
        result['failure']={'reason':reason,'stage':stage,'bodyOrdinal':body,'packetOrdinal':row,'meshOrdinal':mesh}
        return result
    if len(bodies)>8:return fail('body_count','counts')
    if len(planes)>16:return fail('plane_count','counts')
    if not 1<=len(meshes)<=4:return fail('mesh_count','counts')
    total=0
    for i,mesh in enumerate(meshes):
        total+=len(mesh['triangles'])
        if total>64:return fail('face_count','counts',mesh=i)
    if len(rows)>8:return fail('packet_count','counts')
    result['capture']='complete'
    work.update(originalBodiesCopied=len(bodies),originalPlanesCopied=len(planes),originalMeshesCopied=len(meshes),
                originalFacesCopied=total,packetRowsCopied=len(rows))
    for i,body in enumerate(bodies):
        work['originalValidationsAttempted']+=1
        if not guard.prep.body_valid(body):return fail('original_body','original_validation',body=i)
        work['originalValidationsReturned']+=1
    result['originalBodiesValidated']=True
    if packet['mode']!=0:return fail('packet_mode','packet')
    if packet['expectedTick']>MAX_ID or packet['expectedTick']!=source['progress']['ticks']:
        return fail('expected_tick','packet')
    if len(rows)!=len(bodies):return fail('packet_count','packet')
    seen=set()
    for row_ordinal,row in enumerate(rows):
        work['packetRowsChecked']+=1
        ordinal=next((i for i,b in enumerate(bodies) if b['id']==row['bodyId']),None) if 1<=row['bodyId']<=MAX_ID else None
        if ordinal is None:return fail('packet_id','packet',row=row_ordinal)
        if ordinal in seen:return fail('packet_duplicate','packet',body=ordinal,row=row_ordinal)
        seen.add(ordinal)
        result['mappings'][row_ordinal]={'packetOrdinal':row_ordinal,'bodyOrdinal':ordinal,'bodyId':row['bodyId']}
        candidate=copy.deepcopy(bodies[ordinal]);candidate['force']=copy.deepcopy(row['force']);candidate['torque']=copy.deepcopy(row['torque'])
        if candidate['isStatic'] and any(fraction(v)!=0 for k in ('force','torque') for v in candidate[k]):
            return fail('static_load','packet',body=ordinal,row=row_ordinal)
        work['packetValidationsAttempted']+=1
        if not guard.prep.body_valid(candidate):return fail('packet_load','packet',body=ordinal,row=row_ordinal)
        work['packetValidationsReturned']+=1
    staged={key:copy.deepcopy(scene[key]) for key in ('bodies','planes','gravity')}
    for row,mapping in zip(rows,result['mappings']):
        for key in ('force','torque'):staged['bodies'][mapping['bodyOrdinal']][key]=copy.deepcopy(row[key])
    result['stagedWorld']=staged
    return result


def packet_shape(packet):
    fields(packet,{'mode','expectedTick','loads'},'full original absolute load packet')
    uint(packet['mode'],(1<<32)-1,'original numeric mode')
    uint(packet['expectedTick'],MAX_U64,'original integer expected tick')
    rows=packet['loads'];need(type(rows) is list and len(rows)<=1024,'bounded dense original packet rows')
    for row in rows:
        fields(row,{'bodyId','force','torque'},'whole BodyLoad row')
        uint(row['bodyId'],MAX_U64,'original body ID metadata')
        for key in ('force','torque'):
            need(type(row[key]) is list and len(row[key])==3,'full world-frame '+key)
            for component in row[key]:fraction(component)


def replacement_reference(bodies, progress, packet):
    """Valid-input reference, preserving source order/bits and packet row order.

    Raises on invalid input; formal failure-priority classification is separate.
    The existing body-domain helper retains its documented validation/RN scope.
    """
    need(type(bodies) is list and len(bodies)<=8,'complete original body domain')
    advance.progress_shape(progress);packet_shape(packet)
    ids={}
    for ordinal,body in enumerate(bodies):
        guard.prep.body_shape(body)
        need(guard.prep.body_valid(body),'original body validation precedes replacement; no repair')
        need(body['id'] not in ids,'original body identity unique')
        ids[body['id']]=ordinal
    need(packet['mode']==0,'explicit replace_total_world_loads mode only')
    need(packet['expectedTick']<=MAX_ID and packet['expectedTick']==progress['ticks'],'exact integer expected tick; no float comparison')
    need(len(packet['loads'])==len(bodies),'one explicit row for every body including static')
    seen=set();mapping=[]
    for packet_ordinal,row in enumerate(packet['loads']):
        body_id=row['bodyId']
        need(1<=body_id<=MAX_ID and body_id in ids,'safe known body ID')
        need(body_id not in seen,'duplicate packet body ID');seen.add(body_id)
        body_ordinal=ids[body_id]
        for key in ('force','torque'):
            values=[fraction(v) for v in row[key]]
            need(all(abs(v)<=LOAD_CAP for v in values),'finite bounded absolute total '+key)
            if bodies[body_ordinal]['isStatic']:
                need(all(v==0 for v in values),'static row load components exactly zero, signs retained')
        mapping.append({'packetOrdinal':packet_ordinal,'bodyOrdinal':body_ordinal,'bodyId':body_id})
    staged=copy.deepcopy(bodies)
    for row,item in zip(packet['loads'],mapping):
        body=staged[item['bodyOrdinal']]
        body['force']=copy.deepcopy(row['force']);body['torque']=copy.deepcopy(row['torque'])
    return staged,mapping


def cleared_candidates(candidates):
    """Expected load clearing only; never represents measured private/external IO."""
    need(type(candidates) is list and len(candidates)<=8,'whole candidate body list')
    result=copy.deepcopy(candidates)
    for body in result:
        guard.prep.body_shape(body)
        body['force']=[0.,0.,0.];body['torque']=[0.,0.,0.]
    return result


def exact_translation(position, velocity, mass, force, gravity, horizon):
    """Real held-load closed form in Fraction, not a floating kernel replay."""
    values=[]
    for vector in (position,velocity,force,gravity):
        need(type(vector) in (list,tuple) and len(vector)==3,'three exact translation coordinates')
        values.append(tuple(v if type(v) is Fraction else fraction(v) for v in vector))
    mass=mass if type(mass) is Fraction else fraction(mass)
    horizon=horizon if type(horizon) is Fraction else fraction(horizon)
    need(mass>0 and horizon>0,'positive analytic mass and horizon')
    p,v,f,g=values;a=tuple(g[i]+f[i]/mass for i in range(3))
    return (tuple(p[i]+v[i]*horizon+a[i]*horizon*horizon/2 for i in range(3)),
            tuple(v[i]+a[i]*horizon for i in range(3)))


REPORT_KEYS={'status','reason','committed','requestedDt','advancedDt','originalProgress','requestedMode','requestedTick',
 'binding','failure','capture','stagedCapture','privateAfterCapture','originalBodiesValidated','original','mappings',
 'stagedBefore','privateAfter','privateProgressAfter','child','work','storage','message'}
ROW_KEYS={'name','scenario','frameOrdinal','input','inputAfter','worldBefore','worldAfter','progressBefore','progressAfter','report','observations'}
OBS_KEYS={'captureComplete','controlledCalls','worldUnchanged','progressUnchanged','packetUnchanged','meshesUnchanged',
 'settingsUnchanged','horizonUnchanged','planesUnchanged','gravityUnchanged','pointerStability'}
REASONS={'none','environment','binding_unsupported','body_count','plane_count','mesh_count','face_count','packet_count',
 'original_body','packet_mode','expected_tick','packet_id','packet_duplicate','packet_load','static_load','private_copy',
 'child_failed','child_inconsistent','origin_mismatch','candidate_mismatch','destination_mismatch','allocation_failure','unexpected_exception'}
STAGES={'environment','binding','counts','capture','original_validation','packet','staging','child','post_child','commit_preparation'}
CONTROLLED_LAYOUT={'BodyLoad','TickLoadPacket','Binding','WorldState','OriginalSnapshot','Mapping','Work','Storage','ControlledReport'}


def same(a,b):
    try:equal(a,b,'bit equality');return True
    except AssertionError:return False


def fingerprint(rows):
    # Full source scalar type and binary64 bits, all source array ordinals.
    # Context labels/scenario names and document traversal order are excluded.
    def encode(value):
        if type(value) is dict:return '{'+','.join(json.dumps(k)+':'+encode(value[k]) for k in sorted(value))+'}'
        if type(value) is list:return '['+','.join(encode(x) for x in value)+']'
        if type(value) is bool:return 'bool:'+str(value)
        if type(value) is int:return 'int:'+str(value)
        if type(value) is float:return 'f64:'+bits(value).hex()
        if type(value) is str:return 'str:'+json.dumps(value)
        need(value is None,'source fingerprint scalar');return 'null'
    return hashlib.sha256(('\n'.join(sorted(encode({'input':r['input'],'frameOrdinal':r['frameOrdinal']}) for r in rows))+'\n').encode()).hexdigest()


def binding_shape(value):
    fields(value,{'profile','configured','buildId','upstreamBuildId'},'separate controlled binding')
    uint(value['profile'],1,'controlled profile');advance.boolean(value['configured'],'controlled configured')
    need(value['profile']==1 and value['configured'],'finite corpus requires actually configured wrapper; no refusal substitution')
    for key in ('buildId','upstreamBuildId'):
        need(type(value[key]) is str and re.fullmatch('[0-9a-f]{64}',value[key]),'full controlled identity '+key)


def report_shape(r):
    fields(r,REPORT_KEYS,'complete ControlledReport')
    need(type(r['status']) is str and r['status'] in advance.STATUSES,'known controlled status')
    need(type(r['reason']) is str and r['reason'] in REASONS,'known controlled reason')
    for key in ('committed','originalBodiesValidated'):advance.boolean(r[key],key)
    for key in ('requestedDt','advancedDt'):fraction(r[key])
    original_progress_shape(r['originalProgress']);uint(r['requestedMode'],(1<<32)-1,'requested source mode')
    uint(r['requestedTick'],MAX_U64,'requested source tick');binding_shape(r['binding'])
    for key in ('capture','stagedCapture','privateAfterCapture'):
        need(type(r[key]) is str and r[key] in {'none','partial','complete'},'known '+key)
    advance.text(r['message'],'actual controlled message')
    if r['failure'] is not None:
        fields(r['failure'],{'stage','bodyOrdinal','packetOrdinal','meshOrdinal'},'controlled failure location')
        need(type(r['failure']['stage']) is str and r['failure']['stage'] in STAGES,'known controlled failure stage')
        for key in ('bodyOrdinal','packetOrdinal','meshOrdinal'):
            if r['failure'][key] is not None:uint(r['failure'][key],MAX_U64,'actual failure '+key)
    need(type(r['mappings']) is list and len(r['mappings'])==8,'all fixed eight mapping slots including null tail')
    for item in r['mappings']:
        if item is not None:
            fields(item,{'packetOrdinal','bodyOrdinal','bodyId'},'packet-ID to original ordinal')
            for key in item:uint(item[key],MAX_U64,'mapping '+key)
    fields(r['work'],WORK_KEYS,'all thirty phase counters')
    for key in WORK_KEYS:uint(r['work'][key],MAX_U64,'work '+key)
    fields(r['storage'],{'candidateSlots','destinationSlots','candidateSizeofBytes','destinationSizeofBytes'},'two fixed named buffers')
    for key,value in r['storage'].items():uint(value,MAX_U64,'storage '+key)
    for key in ('stagedBefore','privateAfter'):
        if r[key] is not None:advance.world_shape(r[key])
    if r['privateProgressAfter'] is not None:original_progress_shape(r['privateProgressAfter'])
    if r['original'] is not None:
        o=r['original'];fields(o,{'horizon','settings','progress','world','meshes','packet'},'complete owned original snapshot')
        advance.world_shape(o['world']);original_progress_shape(o['progress']);packet_shape(o['packet'])
        guard.source_shape({**o['world'],'meshes':o['meshes'],'horizon':o['horizon'],'settings':o['settings']})


def new_stats():
    # Only counters actually updated by the reused pure Report auditor. The
    # containing call is not a scheduler pump or a new top-level child corpus.
    child={'actualOwnedGuardsVerified':0,'clockRefusedAdvances':0,'candidateBodyLinks':0,
           'settledChargedWork':{k:0 for k in scheduler.HARD_WORK},'guard':guard.new_stats()}
    return {'fixtures':0,'committed':0,'failed':0,'preflightRefusals':0,'privateRefusals':0,'actualChildrenVerified':0,
            'candidateBodiesCompared':0,'outerPointerBodyObservations':0,'statusCounts':{k:0 for k in sorted(advance.STATUSES)},'child':child}


def verify_row(row,layout,stats):
    fields(row,ROW_KEYS,'complete actual controlled fixture')
    for key in ('name','scenario'):advance.text(row[key],key);need(row[key],'nonempty context label')
    uint(row['frameOrdinal'],MAX_U64,'context frame ordinal')
    source=row['input'];input_shape(source);input_shape(row['inputAfter'])
    scene=source['scene'];packet=source['packet'];progress=source['progress'];r=row['report'];report_shape(r)
    for key in ('worldBefore','worldAfter'):advance.world_shape(row[key])
    for key in ('progressBefore','progressAfter'):original_progress_shape(row[key])
    world={k:copy.deepcopy(scene[k]) for k in ('bodies','planes','gravity')}
    equal(world,row['worldBefore'],'actual external origin fully equals source World')
    equal(progress,row['progressBefore'],'actual external original Progress')
    equal(scene['horizon'],r['requestedDt'],'requested H raw bits');equal(progress,r['originalProgress'],'original Progress raw bits')
    equal(packet['mode'],r['requestedMode'],'requested numeric mode');equal(packet['expectedTick'],r['requestedTick'],'requested uint64 tick')
    equal({'candidateSlots':8,'destinationSlots':8,'candidateSizeofBytes':8*layout['rigidBody'],'destinationSizeofBytes':64},r['storage'],'fixed local buffer observations only')
    expected=preflight_reference(source);work=copy.deepcopy(expected['work'])
    equal(expected['capture'],r['capture'],'hard counts before owned capture')
    equal(expected['originalBodiesValidated'],r['originalBodiesValidated'],'original validation prefix')
    equal(expected['mappings'],r['mappings'],'all ID mappings and unused tail')
    original=None if expected['capture']=='none' else {'horizon':scene['horizon'],'settings':scene['settings'],
        'progress':progress,'world':world,'meshes':scene['meshes'],'packet':packet}
    equal(original,r['original'],'full owned original, including invalid values and signed zeros')
    expected_world=copy.deepcopy(world);expected_progress=copy.deepcopy(progress)
    expected_status='invalid_input';expected_reason=None;expected_failure=None
    if expected['failure'] is not None:
        f=expected['failure'];expected_reason=f['reason'];expected_failure={k:v for k,v in f.items() if k!='reason'}
        need(r['stagedBefore'] is r['privateAfter'] is r['privateProgressAfter'] is r['child'] is None,
             'input rejection cannot fabricate private state or child')
        need(r['stagedCapture']==r['privateAfterCapture']=='none','input rejection private capture none')
        stats['preflightRefusals']+=1
    else:
        staged=expected['stagedWorld'];equal(staged,r['stagedBefore'],'actual private staged state uses absolute packet replacement')
        need(r['stagedCapture']==r['privateAfterCapture']=='complete','returned finite child has both actual private captures')
        work.update(privateCopiesAttempted=1,privateCopiesReturned=1,stagedBodiesCopied=len(world['bodies']),
            stagedPlanesCopied=len(world['planes']),privateAfterBodiesCopied=len(world['bodies']),privateAfterPlanesCopied=len(world['planes']),
            childAttempts=1,childReturns=1)
        need(r['child'] is not None,'actual finite private child cannot be filled from a separate query')
        staged_scene={**copy.deepcopy(scene),**copy.deepcopy(staged)}
        # Pure actual Report audit only: no constructed WorldAfter/pointer row is
        # ever passed to protected advance.verify_fixture.
        child_world,child_progress=scheduler.advance_report(staged_scene,progress,r['child'],layout,stats['child'])
        equal(child_world,r['privateAfter'],'actual private capture matches audited child candidates or refusal origin')
        equal(child_progress,r['privateProgressAfter'],'actual private Progress matches integer/Fraction child clock')
        need(r['child']['binding']['buildId']==r['binding']['upstreamBuildId'],'controlled upstream links actual advance/guard identity')
        stats['actualChildrenVerified']+=1
        if r['child']['committed']:
            count=len(world['bodies']);work.update(candidateBodiesChecked=count,candidateValidationsAttempted=count,
                candidateValidationsReturned=count,originBodiesChecked=count,originPlanesChecked=len(world['planes']),
                originMeshesChecked=len(scene['meshes']),originFacesChecked=sum(len(m['triangles']) for m in scene['meshes']),
                originPacketRowsChecked=len(packet['loads']),destinationLookups=count,destinationsResolved=count,
                bodyAssignments=count,progressAssignments=1)
            for body in child_world['bodies']:
                need(guard.prep.body_valid(body),'complete actual cleared candidate validates')
                for key in ('force','torque'):
                    need(all(bits(x).hex()=='0000000000000000' for x in body[key]),'actual candidate consumes all loads as positive zero')
            expected_world=child_world;expected_progress=child_progress;expected_status='committed';expected_reason='none'
            stats['candidateBodiesCompared']+=count
        else:
            expected_status=r['child']['status'];expected_reason='child_failed'
            expected_failure={'stage':'child','bodyOrdinal':None,'packetOrdinal':None,'meshOrdinal':None}
            stats['privateRefusals']+=1
    need(r['status']==expected_status and r['reason']==expected_reason and r['committed']==(expected_status=='committed'),
         'normal finite phase status; unknown/nonreturn faults are not silently certified')
    equal(expected_failure,r['failure'],'exact first-failure phase/location')
    equal(work,r['work'],'all attempt/returned/copy/validation/origin/destination/store counters')
    equal(expected_world,row['worldAfter'],'whole external World; no partial commit/load modification on failure')
    equal(expected_progress,row['progressAfter'],'external Progress advances only on outer success')
    if r['committed']:
        equal(scene['horizon'],r['advancedDt'],'outer committed original requested duration');need(r['message']=='','successful message empty')
        stats['committed']+=1
    else:
        need(bits(r['advancedDt']).hex()=='0000000000000000','all outer refusal advancedDt positive zero')
        stats['failed']+=1
    input_after=copy.deepcopy(source);input_after['scene'].update(copy.deepcopy(expected_world));input_after['progress']=copy.deepcopy(expected_progress)
    equal(input_after,row['inputAfter'],'full actual inputAfter: only external bodies and Progress may commit')
    o=row['observations'];fields(o,OBS_KEYS,'outer actual observations only')
    uint(o['controlledCalls'],1,'actual controlled call count');need(o['controlledCalls']==1,'one real call per row')
    wanted={'captureComplete':True,'worldUnchanged':same(row['worldBefore'],row['worldAfter']),
        'progressUnchanged':same(row['progressBefore'],row['progressAfter']),
        **{k:True for k in ('packetUnchanged','meshesUnchanged','settingsUnchanged','horizonUnchanged','planesUnchanged','gravityUnchanged')}}
    for key,value in wanted.items():advance.boolean(o[key],key);need(o[key]==value,'actual outer observation '+key)
    advance.pointer_observations(o['pointerStability'],scene)
    stats['outerPointerBodyObservations']+=len(world['bodies']);stats['fixtures']+=1;stats['statusCounts'][r['status']]+=1


def histories(rows):
    groups={}
    for row in rows:groups.setdefault(row['scenario'],[]).append(row)
    for group in groups.values():
        group.sort(key=lambda r:r['frameOrdinal'])
        need([r['frameOrdinal'] for r in group]==list(range(len(group))),'unique complete contiguous scenario ordinal history')
        for before,after in zip(group,group[1:]):
            previous=before['inputAfter'];current=after['input']
            equal(previous['scene'],current['scene'],'actual scene/source/H/settings continuous without external edit')
            equal(previous['progress'],current['progress'],'actual Progress continuous; packet alone may change')
    return len(groups)


def verify(data,*,development_unpinned=False):
    need(__debug__,'Protected references require normal Python; optimized verification is rejected')
    advance.finite_tree(data)
    fields(data,{'schema','kind','scope','layoutSizes','advanceLayoutSizes','controlledLayoutSizes','maximumDocumentBytes','fixtures'},'controlled full fixture envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='world-static-mesh-flight-controlled-tick-fixtures','known exact schema/kind')
    advance.text(data['scope'],'actual serializer scope');uint(data['maximumDocumentBytes'],67108864,'private document budget')
    need(data['maximumDocumentBytes']==67108864,'declared finite document bound')
    guard.layout_shape(data['layoutSizes'])
    for value,keys in ((data['advanceLayoutSizes'],{'AdvanceReport','Progress','ClockAudit','CommitWork','CommitStorage'}),(data['controlledLayoutSizes'],CONTROLLED_LAYOUT)):
        fields(value,keys,'same-run sizeof observations')
        for k,v in value.items():uint(v,1048576,'sizeof '+k);need(v>0,'positive sizeof observation')
    rows=data['fixtures'];need(type(rows) is list and 1<=len(rows)<=256,'bounded complete actual fixtures')
    for row in rows:fields(row,ROW_KEYS,'full row before fingerprint');input_shape(row['input']);uint(row['frameOrdinal'],MAX_U64,'frame ordinal')
    fp=fingerprint(rows)
    if not development_unpinned:
        need(EXPECTED_FIXTURE_COUNT is not None and EXPECTED_INPUT_FINGERPRINT is not None,'actual corpus has not yet been independently verified/pinned')
        need(len(rows)==EXPECTED_FIXTURE_COUNT and fp==EXPECTED_INPUT_FINGERPRINT,'all original source types/bits/array ordinals; label/order-independent multiset')
    stats=new_stats()
    labels=set();identities=set()
    for row in rows:
        need(type(row['name']) is str and row['name'] and row['name'] not in labels,'unique nonempty row label');labels.add(row['name'])
        verify_row(row,data['layoutSizes'],stats);identities.add(tuple(row['report']['binding'][k] for k in ('buildId','upstreamBuildId')))
    need(len(identities)==1,'one observed independent controlled/upstream configuration pair')
    stats['scenarios']=histories(rows)
    return {'status':'PASS',**stats,'inputFingerprint':fp,'developmentUnpinned':development_unpinned,
        'scope':'Finite source/packet/H/Progress full captures only. Independent ID-based absolute replacement and original-body validation, actual private staged/after/child correspondence, pure integer/Fraction clock and all actual returned guard mathematics, full outer all-or-none World/Progress/load/bit preservation and phase Work. No production requery, synthetic intermediate WorldAfter/pointer row, absent-guard fill, allocation-fault injection, nonfinite-child full diagnostic acceptance, address/ISA/thread atomicity proof or SDK integration. Coordinates use exact quadratic extrema plus declared B; downstream recorded-box RN/root proof and Native public-value provenance remain separate. sizeof describes named buffers only.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixture',type=Path)
    parser.add_argument('--development-unpinned',action='store_true');args=parser.parse_args()
    need(args.fixture.stat().st_size<=67108864,'bounded actual JSON document')
    print(json.dumps(verify(load(args.fixture),development_unpinned=args.development_unpinned)))
