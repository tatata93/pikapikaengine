"""Independent Fraction coordinate-box and exact/integer-RN AST audit.

No Native value routine, floating point expression replay, norm/sqrt, ordinary
polynomial solver or finite time sampling supplies this mathematical reference.
All exact-or-nearest-even choices on the declared fixed AST are enumerated at
monotone box corners. Actual public-value bit provenance is a separate gate.
"""
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

EXPECTED_FIXTURE_COUNT = 67
EXPECTED_INPUT_FINGERPRINT = '2d660f51cb84c0bdbc8f8f9e3d26bf59caf92d53878bc12c0bf2ebce72408ec9'
MAX_AST_CHOICES = 4096
RESULT_KEYS = {'status','reason','snapshot','snapshotValidated','failedInput','partitionComplete',
               'audits','partition','frontier','current','work'}
WORK_KEYS = {'valueCallsAttempted','valueCallsReturned'}
REASONS = {'none','settings','horizon','input_domain','zero_normal','position_error','contact_margin',
           'evaluation_budget','leaf_budget','depth_budget','width_limit','time_resolution',
           'nonpositive_value','value_exception','allocation_failure','environment','coverage_inconsistent'}


def need(condition,message):
    if not condition:
        raise AssertionError(message)


def fields(value,keys,label):
    need(type(value) is dict and set(value)==set(keys),label+' exact fields')


def uint(value,maximum,label):
    need(type(value) is int and 0<=value<=maximum,label+' canonical integer')
    return value


def fraction(value):
    need(type(value) in (int,float),'numeric scalar, not boolean')
    try: v=float(value)
    except OverflowError:need(False,'finite binary64 scalar')
    need(math.isfinite(v),'finite binary64 scalar')
    return F(v)


def bits(value):
    fraction(value)
    return struct.pack('>d',float(value))


def source_equal(a,b):
    if type(a) in (int,float):
        need(type(b) in (int,float) and bits(a)==bits(b),'full numeric binary64/source signed-zero equality')
        if type(a) is type(b) is int:need(a==b,'complete integer source value')
    elif type(a) is dict:
        fields(b,a,'owned object')
        for key in a:source_equal(a[key],b[key])
    elif type(a) is list:
        need(type(b) is list and len(a)==len(b),'owned array length/order')
        for x,y in zip(a,b):source_equal(x,y)
    else:
        need(type(a) is type(b) and a==b,'owned scalar type/value')


def loads(content):
    if type(content) is bytes:
        need(len(content)<=64*1024*1024,'bounded fixture bytes');content=content.decode('utf-8',errors='strict')
    need(type(content) is str and len(content.encode('utf-8',errors='strict'))<=64*1024*1024,'bounded UTF8 fixture')
    def floating(token):
        value=float(token)
        need(math.isfinite(value) and not (value==0 and any(c in '123456789' for c in token.lower().split('e')[0])),
             'finite non-underflowing JSON number')
        return value
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'duplicate JSON key');result[key]=value
        return result
    value=json.loads(content,object_pairs_hook=pairs,parse_float=floating,
                     parse_int=lambda t:-0.0 if t=='-0' else int(t),
                     parse_constant=lambda t:(_ for _ in ()).throw(AssertionError('nonfinite JSON number')))
    count=0
    def visit(v,depth=0):
        nonlocal count
        count+=1;need(count<=2000000 and depth<=40,'bounded JSON nodes/depth')
        if type(v) is str:v.encode('utf-8',errors='strict')
        elif type(v) is dict:
            for key,child in v.items():key.encode('utf-8',errors='strict');visit(child,depth+1)
        elif type(v) is list:
            for child in v:visit(child,depth+1)
        elif type(v) in (int,float):fraction(v)
    visit(value)
    return value


def load(path):
    return loads(Path(path).read_bytes())


def input_fingerprint(fixtures):
    def encode(v):
        if type(v) is dict:return '{'+','.join(json.dumps(k)+':'+encode(v[k]) for k in sorted(v))+'}'
        if type(v) is list:return '['+','.join(encode(x) for x in v)+']'
        if type(v) is int:return 'integer:'+str(v)
        if type(v) is float:return 'binary64:'+bits(v).hex()
        if type(v) is str:return 'string:'+json.dumps(v)
        need(False,'whole-input scalar type')
    return hashlib.sha256(('\n'.join(sorted(encode(f['input']) for f in fixtures))+'\n').encode()).hexdigest()


def vector(v):
    need(type(v) is list and len(v)==3,'dense Vec3')
    return tuple(fraction(x) for x in v)


def interval(v):
    need(type(v) is list and len(v)==2,'finite interval pair')
    lo,hi=map(fraction,v);need(lo<=hi,'ordered finite interval');return lo,hi


def quadratic_range(coefficients,lo,hi):
    """Exact closed-range extrema; no sampling or rounded coefficient build."""
    c,b,a=map(F,coefficients);lo,hi=F(lo),F(hi)
    need(lo<=hi,'ordered quadratic domain')
    values=[c+b*lo+a*lo*lo,c+b*hi+a*hi*hi]
    if a:
        stationary=-b/(2*a)
        if lo<stationary<hi:values.append(c+b*stationary+a*stationary*stationary)
    return min(values),max(values)


def integer_rn(value):
    """Exact real value of binary64 RN-even, built solely from integer ratios.

    Source conversion to Fraction is separate. This routine never computes a
    floating point approximation of a graph node, including subnormal ties.
    A rounded zero's sign is immaterial to real containment; source bits retain
    their original sign in the separate full ownership/fingerprint audit.
    """
    value=F(value)
    if not value:return F(0)
    negative=value<0;value=abs(value);n,d=value.numerator,value.denominator
    exponent=n.bit_length()-d.bit_length()
    if (n<d*(1<<exponent)) if exponent>=0 else (n*(1<<-exponent)<d):exponent-=1
    shift=1074 if exponent< -1022 else 52-exponent
    mantissa=_round_even(n<<shift,d) if shift>=0 else _round_even(n,d<<-shift)
    if exponent< -1022:result=F(mantissa,1<<1074)
    else:
        if mantissa==1<<53:exponent+=1;mantissa=1<<52
        need(exponent<=1023,'finite exact integer-RN graph result')
        scale=exponent-52
        result=F(mantissa<<scale) if scale>=0 else F(mantissa,1<<-scale)
    return -result if negative else result


def node_choices(operation,left,right,stats=None):
    """All exact-or-RN choices, including deferred product rounding in FMA."""
    need(operation in {'mul','add','sub'},'declared fixed AST operation')
    values=set()
    for a in left:
        for b in right:
            exact=a*b if operation=='mul' else a+b if operation=='add' else a-b
            values.add(exact);values.add(integer_rn(exact))
            if stats is not None:stats['astNodePairs']+=1
            need(len(values)<=MAX_AST_CHOICES,'finite exact AST choice budget')
    return frozenset(values)


def fixed_ast(normal,coordinates,offset,radius,margin,stats=None):
    """Explicit left AST; no factoring, reassociation or ordinary double."""
    leaves=[frozenset([F(x)]) for x in coordinates]
    products=[node_choices('mul',frozenset([F(n)]),x,stats) for n,x in zip(normal,leaves)]
    first=node_choices('add',products[0],products[1],stats)
    dot=node_choices('add',first,products[2],stats)
    distance=node_choices('sub',dot,frozenset([F(offset)]),stats)
    threshold=node_choices('add',frozenset([F(radius)]),frozenset([F(margin)]),stats)
    gap=node_choices('sub',distance,threshold,stats)
    return {'distance':distance,'threshold':threshold,'gap':gap}


def verify_evaluation(source,cell,evaluation,stats):
    fields(evaluation,{'tubeCoordinates','distance','threshold','gap'},'whole returned Evaluation')
    need(type(evaluation['tubeCoordinates']) is list and len(evaluation['tubeCoordinates'])==3,'dense coordinate tube')
    box=[interval(value) for value in evaluation['tubeCoordinates']]
    bounds={key:interval(evaluation[key]) for key in ['distance','threshold','gap']}
    data=source['input'];sphere=data['sphere'];plane=data['plane'];lo,hi=interval(cell['timeBounds'])
    error=fraction(data['positionError'])
    for k,(lower,upper) in enumerate(box):
        extrema=quadratic_range([fraction(sphere['center'][k]),fraction(sphere['velocity'][k]),
                                fraction(sphere['acceleration'][k])/2],lo,hi)
        need(lower<=extrema[0]-error and upper>=extrema[1]+error,'tube contains full quadratic extrema plus declared B')
        stats['coordinateRangeProofs']+=1
    normal=vector(plane['normal'])
    # Each exact/RN node is monotone in its operands. With fixed normal signs,
    # every graph choice has coordinate extrema at these same two corners.
    # Node choices may differ at the corners; their union safely bounds all of
    # them. This is an extrema proof, not a finite set of time samples.
    minimum=[pair[0] if n>=0 else pair[1] for n,pair in zip(normal,box)]
    maximum=[pair[1] if n>=0 else pair[0] for n,pair in zip(normal,box)]
    for corner in [minimum,maximum]:
        choices=fixed_ast(normal,corner,fraction(plane['offset']),fraction(sphere['radius']),
                          fraction(data['contactMargin']),stats)
        for key,values in choices.items():
            lower,upper=bounds[key]
            need(lower<=min(values) and max(values)<=upper,key+' contains all fixed-AST exact/integer-RN corner choices')
        stats['astCornerProofs']+=1
    stats['returnedEvaluations']+=1;stats['returnedIntervals']+=6


def _round_even(n,d):
    q,r=divmod(n,d);return q+(2*r>d or (2*r==d and q%2==1))


def rn_positive(value):
    """Integer IEEE nearest-even construction for *width metadata only*."""
    value=F(value);need(value>=0,'nonnegative metadata magnitude')
    if not value:return 0.
    n,d=value.numerator,value.denominator;e=n.bit_length()-d.bit_length()
    if (n<d*(1<<e)) if e>=0 else (n*(1<<-e)<d):e-=1
    shift=1074 if e< -1022 else 52-e
    mantissa=_round_even(n<<shift,d) if shift>=0 else _round_even(n,d<<-shift)
    if e< -1022:payload=mantissa
    else:
        if mantissa==1<<53:e+=1;mantissa=1<<52
        need(e<=1023,'finite metadata RN');payload=((e+1023)<<52)+mantissa-(1<<52)
    return struct.unpack('>d',struct.pack('>Q',payload))[0]


def next_up(value):
    need(fraction(value)>=0,'nonnegative metadata endpoint')
    payload=0 if fraction(value)==0 else struct.unpack('>Q',bits(value))[0]
    need(payload<0x7fefffffffffffff,'finite metadata successor')
    return struct.unpack('>d',struct.pack('>Q',payload+1))[0]


def width_upper(cell):
    lo,hi=cell['timeBounds']
    # interval::sub has the documented exact zero-right-operand shortcut;
    # otherwise its upper is nextUp(RN(hi-lo)), even if subtraction was exact.
    return fraction(hi) if fraction(lo)==0 else fraction(next_up(rn_positive(fraction(hi)-fraction(lo))))


def sphere_shape(value):
    fields(value,{'center','velocity','acceleration','radius'},'point nominal sphere')
    for key in ['center','velocity','acceleration']:vector(value[key])
    fraction(value['radius'])


def source_shape(source):
    fields(source,{'input','horizon','settings'},'complete source')
    fields(source['settings'],{'timeTolerance','maxEvaluations','maxLeaves','maxDepth'},'complete profile')
    fraction(source['settings']['timeTolerance']);fraction(source['horizon'])
    for key in ['maxEvaluations','maxLeaves','maxDepth']:uint(source['settings'][key],2**64-1,'input '+key)
    data=source['input'];fields(data,{'sphere','plane','positionError','contactMargin'},'explicit box input')
    sphere_shape(data['sphere']);fields(data['plane'],{'normal','offset'},'raw plane')
    vector(data['plane']['normal']);fraction(data['plane']['offset'])
    fraction(data['positionError']);fraction(data['contactMargin'])


def preflight(source):
    source_shape(source);s=source['settings'];data=source['input'];sphere=data['sphere'];plane=data['plane']
    if not (0<fraction(s['timeTolerance'])<=fraction(.1) and 1<=s['maxEvaluations']<=255
            and 1<=s['maxLeaves']<=128 and s['maxDepth']<=32):return 'settings',None
    if not 0<fraction(source['horizon'])<=fraction(.1):return 'horizon',None
    if not (0<fraction(sphere['radius'])<=10**12 and all(abs(x)<=10**12
            for key in ['center','velocity','acceleration'] for x in vector(sphere[key]))):return 'input_domain',0
    normal=vector(plane['normal'])
    if any(abs(v)>10**12 for v in normal) or abs(fraction(plane['offset']))>10**12:return 'input_domain',1
    if all(v==0 for v in normal):return 'zero_normal',1
    if not 0<=fraction(data['positionError'])<=10**12:return 'position_error',2
    if not 0<=fraction(data['contactMargin'])<=fraction(.1):return 'contact_margin',3
    return None,None


def cell_shape(cell,horizon):
    fields(cell,{'timeBounds','depth','parentAudit'},'closed global time cell')
    lo,hi=interval(cell['timeBounds']);need(0<=lo<hi<=fraction(horizon),'nondegenerate cell in global seconds')
    uint(cell['depth'],32,'cell depth')
    if cell['parentAudit'] is not None:uint(cell['parentAudit'],254,'parent audit link')


def empty_work():
    return dict.fromkeys(WORK_KEYS,0)


def work_shape(work):
    fields(work,WORK_KEYS,'exact wrapper calls only')
    for key,value in work.items():uint(value,255,'work '+key)
    need(work['valueCallsReturned']<=work['valueCallsAttempted']<=255,'bounded exact attempts/returns')


def verify_fixture(source,result,stats):
    reason,failed=preflight(source);fields(result,RESULT_KEYS,'complete coverage result')
    source_shape(result['snapshot'])
    source_equal(source,result['snapshot'])
    need(type(result['snapshotValidated']) is bool and type(result['partitionComplete']) is bool,'snapshot/partition flags')
    if result['failedInput'] is not None:uint(result['failedInput'],3,'failed input ordinal')
    source_equal(failed,result['failedInput']);work_shape(result['work'])
    need(type(result['status']) is str and type(result['reason']) is str and result['reason'] in REASONS,'result enum strings')
    for key,cap in [('audits',255),('partition',128),('frontier',128)]:
        need(type(result[key]) is list and len(result[key])<=cap,'bounded '+key)
    if reason is not None:
        need(result['status']=='invalid_input' and result['reason']==reason and not result['snapshotValidated']
             and not result['partitionComplete'],'captured invalid input is not a validated coverage')
        need(result['audits']==result['partition']==result['frontier']==[] and result['current'] is None,'invalid input has no installed root or calls')
        source_equal(empty_work(),result['work']);stats['invalidInputs']+=1;return
    need(result['snapshotValidated'] and result['partitionComplete'],'valid finite natural corpus installed the complete root')
    horizon=source['horizon'];s=source['settings']
    own=[{'cell':{'timeBounds':[0.,horizon],'depth':0,'parentAudit':None},'state':'unqueried','auditIndex':None,'blockedReason':'none'}]
    attempted=returned=0;halt=None;current=None
    def select():
        eligible=[i for i,leaf in enumerate(own) if leaf['state']=='unqueried']
        return min(eligible,key=lambda i:(own[i]['cell']['depth'],fraction(own[i]['cell']['timeBounds'][0]))) if eligible else None
    for ordinal,audit in enumerate(result['audits']):
        fields(audit,{'cell','callAttempted','evaluation','outcome','blockedReason','splitTime'},'full audit')
        cell_shape(audit['cell'],horizon)
        need(type(audit['callAttempted']) is bool and audit['callAttempted'],'actual finite value call attempt')
        need(type(audit['outcome']) is str and audit['outcome'] in {'positive','split','blocked'},'no final pending audit')
        need(type(audit['blockedReason']) is str and audit['blockedReason'] in REASONS,'audit blocked reason enum')
        index=select();need(index is not None and attempted<s['maxEvaluations'],'BFS has an eligible cell and evaluation grant')
        leaf=own[index];source_equal(leaf['cell'],audit['cell']);attempted+=1
        if audit['evaluation'] is None:
            need(ordinal==len(result['audits'])-1 and audit['outcome']=='blocked' and audit['blockedReason']=='value_exception'
                 and audit['splitTime'] is None,'nonreturned attempt is a terminal exception, not proof')
            leaf.update(state='current',auditIndex=ordinal,blockedReason='value_exception')
            current=leaf['cell'];halt='value_exception';break
        returned+=1;verify_evaluation(source,audit['cell'],audit['evaluation'],stats)
        lower,upper=interval(audit['evaluation']['gap']);leaf['auditIndex']=ordinal
        expected_stop=None
        if lower>0:
            need(audit['outcome']=='positive','strict whole-cell lower bound only')
            leaf['state']='certified';stats['certifiedLeaves']+=1
        elif upper<=0:
            expected_stop='nonpositive_value'
        elif width_upper(leaf['cell'])<=fraction(s['timeTolerance']):expected_stop='width_limit'
        elif leaf['cell']['depth']==s['maxDepth']:expected_stop='depth_budget'
        elif fraction(next_up(leaf['cell']['timeBounds'][0]))>=fraction(leaf['cell']['timeBounds'][1]):expected_stop='time_resolution'
        elif len(own)==s['maxLeaves']:expected_stop='leaf_budget'
        else:
            need(audit['outcome']=='split' and audit['blockedReason']=='none','uncertain cell split within all budgets')
            t=fraction(audit['splitTime']);lo,hi=map(fraction,leaf['cell']['timeBounds'])
            need(lo<t<hi,'representable strict split and shared child boundary')
            parent=leaf['cell'];split=audit['splitTime'];depth=parent['depth']+1
            own[index:index+1]=[{'cell':{'timeBounds':[parent['timeBounds'][0],split],'depth':depth,'parentAudit':ordinal},
                                 'state':'unqueried','auditIndex':None,'blockedReason':'none'},
                                {'cell':{'timeBounds':[split,parent['timeBounds'][1]],'depth':depth,'parentAudit':ordinal},
                                 'state':'unqueried','auditIndex':None,'blockedReason':'none'}]
            stats['splitAudits']+=1;continue
        if expected_stop is not None:
            need(audit['outcome']=='blocked' and audit['blockedReason']==expected_stop,'blocked stop priority from exact metadata')
            leaf.update(state='blocked',blockedReason=expected_stop)
            stats['blockedReasons'][expected_stop]+=1
        else:
            need(audit['blockedReason']=='none','positive audit has no blocked reason')
        need(audit['splitTime'] is None,'only split audits have a split time')
    if halt is None:
        index=select()
        if index is not None:
            need(attempted==s['maxEvaluations'],'unexamined tail only after exact evaluation exhaustion')
            leaf=own[index];leaf.update(state='current',blockedReason='evaluation_budget')
            current=leaf['cell'];halt='evaluation_budget'
    expected_reason=halt or next((leaf['blockedReason'] for leaf in own if leaf['state']!='certified'),'none')
    expected_status='certified' if expected_reason=='none' else 'not_certified'
    need(result['status']==expected_status and result['reason']==expected_reason,'terminal status cannot skip the first unresolved leaf/global stop')
    for leaf in result['partition']:
        fields(leaf,{'cell','state','auditIndex','blockedReason'},'partition leaf')
        cell_shape(leaf['cell'],horizon)
        need(type(leaf['state']) is str and leaf['state'] in {'unqueried','certified','blocked','current'},'leaf state enum')
        if leaf['auditIndex'] is not None:uint(leaf['auditIndex'],254,'leaf audit link')
        need(type(leaf['blockedReason']) is str and leaf['blockedReason'] in REASONS,'leaf reason enum')
    source_equal(own,result['partition'])
    for cell in result['frontier']:cell_shape(cell,horizon)
    if result['current'] is not None:cell_shape(result['current'],horizon)
    source_equal([leaf['cell'] for leaf in own if leaf['state']=='unqueried'],result['frontier'])
    source_equal(current,result['current'])
    expected_work={'valueCallsAttempted':attempted,'valueCallsReturned':returned}
    source_equal(expected_work,result['work'])
    need(len(own)<=s['maxLeaves'] and len(result['audits'])<=s['maxEvaluations'],'no hidden budget overflow')
    stats['certified' if expected_status=='certified' else 'notCertified']+=1
    stats['cellAudits']+=len(result['audits']);stats['partitionLeaves']+=len(own)
    stats['frontierCells']+=len(result['frontier']);stats['currentCells']+=int(current is not None)
    stats['maximumAudits']=max(stats['maximumAudits'],len(result['audits']))
    stats['maximumPartition']=max(stats['maximumPartition'],len(own))
    stats['maximumFrontier']=max(stats['maximumFrontier'],len(result['frontier']))
    stats['subdividedCertified']+=int(expected_status=='certified' and len(result['audits'])>1)


def new_stats(count=0):
    result=dict.fromkeys(['fixtures','certified','notCertified','invalidInputs','cellAudits','partitionLeaves','frontierCells',
                         'currentCells','returnedEvaluations','returnedIntervals','coordinateRangeProofs','astCornerProofs',
                         'astNodePairs','certifiedLeaves','splitAudits','maximumAudits','maximumPartition',
                         'maximumFrontier','subdividedCertified'],0)
    result['fixtures']=count
    result['blockedReasons']=dict.fromkeys(['nonpositive_value','width_limit','depth_budget','time_resolution','leaf_budget'],0)
    return result


def verify(data):
    fields(data,{'schema','kind','fixtures'},'finite box coverage fixture envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='accelerated-plane-box-coverage-fixtures','box coverage schema/kind')
    need(EXPECTED_FIXTURE_COUNT is not None,'finite corpus count/fingerprint freeze pending')
    need(type(data['fixtures']) is list and len(data['fixtures'])==EXPECTED_FIXTURE_COUNT,'complete fixed input corpus')
    fingerprint=input_fingerprint(data['fixtures'])
    need(EXPECTED_INPUT_FINGERPRINT is not None and fingerprint==EXPECTED_INPUT_FINGERPRINT,'whole input multiset/scalar-type/bit fingerprint')
    stats=new_stats(len(data['fixtures']));names=set()
    for fixture in data['fixtures']:
        fields(fixture,{'name','input','result'},'complete fixture')
        need(type(fixture['name']) is str and fixture['name'] and fixture['name'] not in names,'unique fixture labels')
        names.add(fixture['name']);verify_fixture(fixture['input'],fixture['result'],stats)
    need((stats['certified'],stats['notCertified'],stats['invalidInputs'])==(20,20,27),'finite corpus outcome profile')
    need(stats['returnedEvaluations']==1306 and stats['returnedIntervals']==7836,'all 1306 returned Evaluations / 7836 intervals')
    need(stats['returnedEvaluations']==stats['cellAudits'],'all actual audit records returned in natural finite corpus')
    need((stats['maximumAudits'],stats['maximumPartition'],stats['maximumFrontier'])==(255,128,127),'full hard capacities and complete unknown tail')
    need(stats['subdividedCertified']>=1 and all(stats['blockedReasons'].values()),'nonvacuous subdivision and each stopping condition')
    return {'status':'PASS',**stats,'inputFingerprint':fingerprint,
            'scope':'Exact Fraction quadratic tube extrema plus fixed-association exact-or-integer-binary64-RN AST containment over the recorded boxes; independent closed-global-seconds BFS/partition/work and original source bits. Conditional declared B only: no actual-body B, all-compiler/World, metric, response or fault-injection execution claim. Actual public value bit provenance is a separate Native gate.'}


if __name__=='__main__':
    need(__debug__,'run box coverage reference without Python -O')
    need(len(sys.argv)==2,'Usage: verify-accelerated-plane-box-coverage.py native-fixtures.json')
    print(json.dumps(verify(load(sys.argv[1]))))
