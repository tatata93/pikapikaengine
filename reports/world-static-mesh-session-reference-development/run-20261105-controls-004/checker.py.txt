"""Independent finite owner protocol and actual delegated pump mathematics.

Public read value copies are observations. No candidate-built observed World,
invented pointer/lookup rows, guard query or unknown-fault success is used.
"""
if not __debug__:
    raise RuntimeError('Use normal Python for owner verification; optimized mode is refused')
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('owned_actual_pump_reference',ROOT/'scripts/verify-world-static-mesh-flight-controlled-scheduler.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
need,fields,uint=q.need,q.fields,q.uint
MAX_GENERATION=(1<<53)-1
U64=(1<<64)-1
MAX_DOCUMENT=64*1024*1024
EXPECTED_ROWS=77
EXPECTED_INPUT_FINGERPRINT='e3b5e3dcdbf48f9c2904ca651637ba98d4ea4d075cb91a69bf15fee4119f6597'
KINDS={'create','reset','destroy','read','pump','edit_caller'}
STATUSES={'ok','busy','slot_range','not_alive','stale_generation','foreign_session','no_free_slot','generation_exhausted','source_counts','invalid_settings','allocation_failure','unexpected_exception'}
ROW_KEYS={'name','scenario','frameOrdinal','registryGenerationLimit','kind','input','inputAfter','result','before','after','retainedSnapshots','retainedPumps'}


def typed(value):
    # JSON object order has no owner protocol meaning. Numeric scalar type,
    # array order and every represented binary64/signed-zero bit are preserved.
    if type(value) is dict:return ['object',[[k,typed(value[k])] for k in sorted(value)]]
    if type(value) is list:return ['array',[typed(v) for v in value]]
    if type(value) is float:return ['binary64',struct.pack('>d',value).hex()]
    if type(value) is int:return ['integer',str(value)]
    if type(value) is bool:return ['boolean',value]
    if value is None:return ['null']
    need(type(value) is str,'known scalar type');return ['string',value]


def same(a,b,message):need(typed(a)==typed(b),message)


def token_shape(value,*,live=False):
    fields(value,{'slot','generation'},'complete native token')
    uint(value['slot'],(1<<32)-1,'uint32 slot');uint(value['generation'],U64,'uint64 generation')
    if live:need(value['slot']<4 and 1<=value['generation']<=MAX_GENERATION,'live finite generation token')


def clock_source(value):
    fields(value,{'step','maxAttempts'},'raw constructor settings');h=q.fraction(value['step']);uint(value['maxAttempts'],U64,'raw attempt cap')
    return q.fraction(2**-20)<=h<=q.fraction(.1) and 1<=value['maxAttempts']<=8


def source_shape(value):
    fields(value,{'scene','progress','clockSettings'},'complete authored source')
    q.source_shape({'scene':value['scene'],'progress':value['progress'],'packets':[]})
    clock_source(value['clockSettings'])
    q.equal(value['scene']['horizon'],value['clockSettings']['step'],'producer explicitly represents constructor step as input H')


def scene_of(snapshot):
    # Input-only representation of ACTUAL read values, not an observed World
    # reconstructed from a candidate or a fabricated full-row pointer fixture.
    return {**copy.deepcopy(snapshot['world']),'meshes':copy.deepcopy(snapshot['meshes']),
            'horizon':snapshot['scheduler']['settings']['step'],'settings':copy.deepcopy(snapshot['guard'])}


def snapshot_shape(value):
    fields(value,{'token','world','meshes','guard','progress','scheduler'},'whole owned read snapshot')
    token_shape(value['token'],live=True);q.snapshot(value['scheduler']);q.advance.world_shape(value['world'])
    q.source_shape({'scene':scene_of(value),'progress':value['progress'],'packets':[]})
    need(len(value['world']['bodies'])<=8 and len(value['world']['planes'])<=16 and len(value['meshes'])<=4 and
         sum(len(x['triangles']) for x in value['meshes'])<=64,'owned hard source bounds')


def owner_status(value):need(type(value) is str and value in STATUSES,'known owner status')


def read_shape(value):
    fields(value,{'status','snapshot'},'whole read result');owner_status(value['status'])
    need((value['snapshot'] is not None)==(value['status']=='ok'),'owned snapshot only on successful read')
    if value['snapshot'] is not None:snapshot_shape(value['snapshot'])


def pump_shape(value):
    fields(value,{'status','target','schedulerCalls','report'},'whole owner pump result');owner_status(value['status']);token_shape(value['target']);uint(value['schedulerCalls'],1,'actual scheduler calls')
    need((value['report'] is not None)==(value['schedulerCalls']==1)==(value['status']=='ok'),'owner gate distinct from actual model outcome')


def probe_shape(value):
    fields(value,{'readCalls','knownLiveSlotReads'},'whole actual public-read probe');uint(value['readCalls'],4,'actual probe calls')
    need(type(value['knownLiveSlotReads']) is list and len(value['knownLiveSlotReads'])==4,'all4 known-handle slots including nulls')
    count=0
    for i,result in enumerate(value['knownLiveSlotReads']):
        if result is None:continue
        read_shape(result);need(result['status']=='ok' and result['snapshot']['token']['slot']==i,'actual successful known-slot value read');count+=1
    need(count==value['readCalls'],'actual public read call count, no invented inactive observations')


def make_snapshot(source,token):
    return {'token':copy.deepcopy(token),'world':{k:copy.deepcopy(source['scene'][k]) for k in ['bodies','planes','gravity']},
            'meshes':copy.deepcopy(source['scene']['meshes']),'guard':copy.deepcopy(source['scene']['settings']),
            'progress':copy.deepcopy(source['progress']),
            'scheduler':{'settings':copy.deepcopy(source['clockSettings']),'backlog':0,'sequence':0,'busy':False}}


class Model:
    def __init__(self,limit):
        self.limit=limit;self.generations=[0]*4;self.live=[None]*4;self.retained_snapshots=[];self.retained_pumps=[]

    def gate(self,token):
        token_shape(token);slot,gen=token['slot'],token['generation']
        if slot>=4:return 'slot_range'
        if gen==0 or gen!=self.generations[slot]:return 'stale_generation'
        if self.live[slot] is None:return 'not_alive'
        return 'ok'

    def probe(self,actual):
        probe_shape(actual);count=0
        for i,snapshot in enumerate(self.live):
            observed=actual['knownLiveSlotReads'][i]
            if snapshot is None:need(observed is None,'no current harness token; not a heap-state measurement')
            else:
                need(observed is not None,'all independently known live sessions must be read')
                same(snapshot,observed['snapshot'],'every actual owned field/token/clock and raw source copy');count+=1
        need(actual['readCalls']==count,'known live public read probes complete')


def row_input_shape(row):
    kind=row['kind'];need(type(kind) is str and kind in KINDS,'known operation, labels not an oracle')
    value=row['input'];after=row['inputAfter']
    if kind in {'create','edit_caller'}:source_shape(value);source_shape(after)
    elif kind=='reset':
        for item in [value,after]:fields(item,{'target','source'},'reset input');token_shape(item['target']);source_shape(item['source'])
    elif kind in {'read','destroy'}:
        for item in [value,after]:fields(item,{'target'},'handle-only input');token_shape(item['target'])
    else:
        for item in [value,after]:
            fields(item,{'target','owner','elapsed','packets'},'full owner pump input');token_shape(item['target']);token_shape(item['owner']);q.fraction(item['elapsed'])
            need(type(item['packets']) is list and len(item['packets'])<=1024,'bounded raw packet input')
            for packet in item['packets']:q.controlled.packet_shape(packet)
    if kind!='edit_caller':same(value,after,'caller input unchanged by actual owner API')
    # edit_caller is an exogenous caller edit, not an engine solver. Both actual
    # source representations are pinned as authored corpus; owners must retain
    # their original values regardless of that external change.


def verify_row(row,model,data,stats):
    kind=row['kind'];value=row['input'];result=row['result'];model.probe(row['before'])
    if kind in {'create','reset'}:
        fields(result,{'status','token'},'whole creation/reset result');owner_status(result['status']);token_shape(result['token'])
        source=value if kind=='create' else value['source'];bad_count=q.count_failure(source['scene'],[]) is not None
        if kind=='create':
            status='source_counts' if bad_count else 'no_free_slot'
            slot=next((i for i in range(4) if model.live[i] is None and model.generations[i]<model.limit),None)
            if not bad_count and slot is not None:status='ok' if clock_source(source['clockSettings']) else 'invalid_settings'
        else:
            status=model.gate(value['target']);slot=value['target']['slot']
            if status=='ok':
                if model.generations[slot]>=model.limit:status='generation_exhausted'
                elif bad_count:status='source_counts'
                elif not clock_source(source['clockSettings']):status='invalid_settings'
        need(result['status']==status,'creation/reset deterministic gate; unknown faults cannot become success')
        expected_token={'slot':0,'generation':0}
        if status=='ok':
            model.generations[slot]+=1;expected_token={'slot':slot,'generation':model.generations[slot]}
            model.live[slot]=make_snapshot(source,expected_token)
        same(expected_token,result['token'],'whole token publication only after successful staging')
    elif kind=='destroy':
        fields(result,{'status'},'whole destroy result');owner_status(result['status']);status=model.gate(value['target']);need(result['status']==status,'destroy exact lifetime gate')
        if status=='ok':model.live[value['target']['slot']]=None
    elif kind=='read':
        read_shape(result);status=model.gate(value['target']);need(result['status']==status,'read exact lifetime gate')
        if status=='ok':
            expected=model.live[value['target']['slot']];same(expected,result['snapshot'],'actual owned read value')
            model.retained_snapshots.append(copy.deepcopy(result['snapshot']))
        stats['publicReadCalls']+=1
    elif kind=='edit_caller':
        fields(result,{'status'},'external caller edit result');need(result['status']=='caller_edited','external edit marker only')
    else:
        pump_shape(result);same(value['target'],result['target'],'actual selected target, including invalid token')
        status=model.gate(value['target'])
        if status=='ok':
            if value['owner']['slot']!=value['target']['slot']:status='foreign_session'
            elif value['owner']['generation']!=value['target']['generation']:status='stale_generation'
        need(result['status']==status,'foreign/stale owner envelope gate before model/time admission')
        if status=='ok':
            slot=value['target']['slot'];before=model.live[slot];after_probe=row['after']['knownLiveSlotReads'][slot]
            need(after_probe is not None,'actual post-call read required');after=after_probe['snapshot'];snapshot_shape(after)
            for key in ['token','meshes','guard']:same(before[key],after[key],'pump immutable owner '+key)
            report=result['report'];same(before['scheduler'],report['before'],'actual owner clock before delegated call');same(after['scheduler'],report['after'],'actual owner clock after delegated call')
            source_before={'scene':scene_of(before),'progress':copy.deepcopy(before['progress']),'packets':copy.deepcopy(value['packets'])}
            source_after={'scene':scene_of(after),'progress':copy.deepcopy(after['progress']),'packets':copy.deepcopy(value['packets'])}
            # Pure actual Report API intentionally has no outer pointer/lookup
            # observations. Only real fixed child boundaries and read values.
            q.verify_pump(source_before,source_after,report,value['elapsed'],data['layoutSizes'],data['controlledSchedulerLayoutSizes'],stats['pump'])
            model.live[slot]=copy.deepcopy(after);stats['delegatedSchedulerCalls']+=1;stats['committedTicks']+=report['committedTicks']
        else:need(result['schedulerCalls']==0 and result['report'] is None,'owner refusal invokes no model or fake report')
        stats['ownerPumpCalls']+=1;model.retained_pumps.append(copy.deepcopy(result))
    model.probe(row['after'])
    need(type(row['retainedSnapshots']) is list and type(row['retainedPumps']) is list,'all retained actual values')
    for value in row['retainedSnapshots']:snapshot_shape(value)
    for value in row['retainedPumps']:pump_shape(value)
    same(model.retained_snapshots,row['retainedSnapshots'],'past actual snapshots survive operations and destruction')
    same(model.retained_pumps,row['retainedPumps'],'past actual returned reports survive reset/destroy; no query replacement')
    stats['publicReadCalls']+=row['before']['readCalls']+row['after']['readCalls'];stats['rows']+=1
    stats['kindCounts'][kind]=stats['kindCounts'].get(kind,0)+1
    stats['ownerStatusCounts'][result['status']]=stats['ownerStatusCounts'].get(result['status'],0)+1


def fingerprint(rows):
    return q.controlled.fingerprint([{'frameOrdinal':r['frameOrdinal'],'input':{'kind':r['kind'],'registryGenerationLimit':r['registryGenerationLimit'],
        'arguments':r['input'],'externalCallerEditAfter':r['inputAfter'] if r['kind']=='edit_caller' else None}} for r in rows])


def verify(data,*,development_unpinned=False):
    q.advance.finite_tree(data)
    fields(data,{'schema','kind','scope','maximumDocumentBytes','layoutSizes','controlledSchedulerLayoutSizes','ownerLayoutSizes','hardMaxSessions','maximumGeneration','fixtures','actualCounts'},'complete owner envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='world-static-mesh-session-fixtures','known owner schema/kind')
    q.advance.text(data['scope'],'scope');uint(data['maximumDocumentBytes'],MAX_DOCUMENT,'document bound');need(data['maximumDocumentBytes']==MAX_DOCUMENT,'exact document budget')
    uint(data['hardMaxSessions'],4,'fixed registry slots');need(data['hardMaxSessions']==4,'exact maximum4 sessions')
    uint(data['maximumGeneration'],MAX_GENERATION,'maximum generation');need(data['maximumGeneration']==MAX_GENERATION,'exact non-wrap generation domain')
    q.guard.layout_shape(data['layoutSizes'])
    for key,keys in [('controlledSchedulerLayoutSizes',{'PumpReport','WorldState','Boundary','OptionalBoundary','Original','Attempt','OptionalAttempt','Storage'}),('ownerLayoutSizes',{'Registry','Token','Created','Snapshot','Read','Pump','Request'})]:
        fields(data[key],keys,'named observed sizeof only')
        for size in data[key].values():uint(size,1048576,'observed sizeof');need(size>0,'positive named size, not a whole-heap bound')
    rows=data['fixtures'];need(type(rows) is list and 1<=len(rows)<=256,'bounded owner corpus')
    groups={};names=set()
    for row in rows:
        fields(row,ROW_KEYS,'all actual owner row fields')
        for key in ['name','scenario']:q.advance.text(row[key],key);need(row[key],'nonempty label, not a semantic oracle')
        need(row['name'] not in names,'unique observation label');names.add(row['name'])
        uint(row['frameOrdinal'],255,'history ordinal');uint(row['registryGenerationLimit'],MAX_GENERATION,'constructor generation limit');need(row['registryGenerationLimit']>=1,'positive constructor generation limit')
        row_input_shape(row);probe_shape(row['before']);probe_shape(row['after']);groups.setdefault(row['scenario'],[]).append(row)
    fp=fingerprint(rows)
    if not development_unpinned:
        need(EXPECTED_ROWS is not None and EXPECTED_INPUT_FINGERPRINT is not None,'Actual owner corpus unpinned; explicit development mode required')
        need(len(rows)==EXPECTED_ROWS and fp==EXPECTED_INPUT_FINGERPRINT,'whole authored input types/bits/operation/ordinal fingerprint')
    stats={'rows':0,'scenarios':len(groups),'ownerPumpCalls':0,'delegatedSchedulerCalls':0,'committedTicks':0,'publicReadCalls':0,'kindCounts':{},'ownerStatusCounts':{},
           'pump':{'frames':0,'admitted':0,'attempts':0,'committedTicks':0,'statusCounts':{},'fixedBoundaryBodyObservations':0,'controlled':q.controlled.new_stats()}}
    for group in groups.values():
        group.sort(key=lambda r:r['frameOrdinal']);need([r['frameOrdinal'] for r in group]==list(range(len(group))),'dense actual operation history')
        limit=group[0]['registryGenerationLimit'];need(all(r['registryGenerationLimit']==limit for r in group),'one immutable constructor limit per registry')
        model=Model(limit)
        for row in group:verify_row(row,model,data,stats)
    fields(data['actualCounts'],{'rows','scenarios','ownerPumpCalls','delegatedSchedulerCalls','committedTicks','publicReadCalls'},'all producer counters')
    for key,value in data['actualCounts'].items():uint(value,100000,'producer '+key);need(value==stats[key],'independent complete producer count: '+key)
    return {'status':'PASS',**stats,'inputFingerprint':fp,'developmentUnpinned':development_unpinned,
            'scope':'Finite protocol/lifetime/generation/reset ownership and actual pure pump/control/guard mathematics. Public read value probes and real retained values only. No pointer/lookup fabrication, query replacement, unknown-fault success, cross-registry authentication, busy/allocator/post-child fault injection, full machine/whole-heap/deadline/GNU/SDK acceptance.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixture',type=Path);parser.add_argument('--development-unpinned',action='store_true');args=parser.parse_args()
    need(args.fixture.stat().st_size<=MAX_DOCUMENT,'bounded full input file')
    print(json.dumps(verify(q.load(args.fixture),development_unpinned=args.development_unpinned)))
