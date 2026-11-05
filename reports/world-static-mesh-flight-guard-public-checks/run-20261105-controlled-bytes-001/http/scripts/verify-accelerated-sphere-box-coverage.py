"""Independent Fraction two-sphere boxes and integer-RN/root enclosure audit.

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

EXPECTED_FIXTURE_COUNT = 75
EXPECTED_INPUT_FINGERPRINT = 'f4f2b48cb4834d95916b5b1a4e9711c27166b65bbc987454af111212416fefbb'
MAX_AST_CHOICES = 4096
RESULT_KEYS = {'status','reason','snapshot','snapshotValidated','failedInput','partitionComplete',
               'audits','partition','frontier','current','work'}
WORK_KEYS = {'valueCallsAttempted','valueCallsReturned','sqrtResultsReturned','sqrtRefinementsReturned','sqrtLimitedReturns','sqrtRefinementsUpper','exact'}
REASONS = {'none','settings','horizon','input_domain','position_error','contact_margin',
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


def extrema_choices(operation,left,right,stats=None):
    """Monotonic exact/RN addition/subtraction extrema over two closed boxes."""
    choices=set()
    for x in left:
        for y in right:choices.update(node_choices(operation,{x},{y},stats))
    return min(choices),max(choices)


def square_range(bounds,stats=None):
    """Squaring is not monotone across zero: include its interior minimum."""
    lo,hi=bounds
    points={lo,hi}
    if lo<=0<=hi:points.add(F(0))
    choices=set()
    for x in points:choices.update(node_choices('mul',{x},{x},stats))
    return min(choices),max(choices)


def threshold_choices(first,second,margin,stats=None):
    return node_choices('add',node_choices('add',{F(first)},{F(second)},stats),{F(margin)},stats)


def contains(bounds,expected,label):
    need(bounds[0]<=expected[0] and expected[1]<=bounds[1],label+' includes complete exact/integer-RN extrema')


def verify_evaluation(source,cell,evaluation,stats):
    fields(evaluation,{'firstCoordinates','secondCoordinates','delta','rawSquaredDistance',
                      'nonnegativeSquaredDistance','root','distance','threshold','gap'},'whole returned sphere Evaluation')
    data=source['input'];lo,hi=interval(cell['timeBounds'])
    boxes={}
    for name,sphere_key,error_key in [('firstCoordinates','first','firstPositionError'),
                                      ('secondCoordinates','second','secondPositionError')]:
        values=evaluation[name]
        need(type(values) is list and len(values)==3,'complete three-coordinate tube')
        boxes[name]=[interval(v) for v in values]
        sphere=data[sphere_key];error=fraction(data[error_key])
        for k,bounds in enumerate(boxes[name]):
            exact=quadratic_range([fraction(sphere['center'][k]),fraction(sphere['velocity'][k]),
                                   fraction(sphere['acceleration'][k])/2],lo,hi)
            contains(bounds,(exact[0]-error,exact[1]+error),'full quadratic extrema plus declared B')
            stats['coordinateRangeProofs']+=1
    need(type(evaluation['delta']) is list and len(evaluation['delta'])==3,'complete delta box')
    delta=[interval(v) for v in evaluation['delta']]
    for k,bounds in enumerate(delta):
        expected=extrema_choices('sub',boxes['secondCoordinates'][k],boxes['firstCoordinates'][k],stats)
        contains(bounds,expected,'recorded delta')
    squares=[square_range(v,stats) for v in delta]
    first_sum=extrema_choices('add',squares[0],squares[1],stats)
    q_expected=extrema_choices('add',first_sum,squares[2],stats)
    raw=interval(evaluation['rawSquaredDistance'])
    contains(raw,q_expected,'left-associated square sum')
    need(raw[1]>=0,'raw square upper is nonnegative, never silently clamped')
    safe=interval(evaluation['nonnegativeSquaredDistance'])
    need(safe==(max(F(0),raw[0]),raw[1]),'square lower-only exact clamp and unchanged upper')
    # Upper copy is a wire-level requirement, including source signed zero.
    need(bits(evaluation['nonnegativeSquaredDistance'][1])==bits(evaluation['rawSquaredDistance'][1]),'square upper copy bits')
    root=evaluation['root'];fields(root,{'value','refinements','refinementLimited'},'full returned public SqrtResult')
    lower,upper=interval(root['value']);need(lower>=0,'nonnegative root enclosure')
    need(lower*lower<=safe[0] and upper*upper>=safe[1],'full sqrt enclosure by exact square inequalities')
    # These endpoints are binary64. Monotone RN fixes both endpoints; hence
    # every correctly-rounded sqrt of q in Qsafe is enclosed as well. No libm.
    need(integer_rn(lower)==lower and integer_rn(upper)==upper,'representable root endpoints for RN monotonic inclusion')
    uint(root['refinements'],2*source['settings']['sqrtRefinements'],'returned endpoint root refinements')
    need(type(root['refinementLimited']) is bool,'root limited boolean')
    interval(evaluation['distance']);source_equal(root['value'],evaluation['distance'])
    threshold=threshold_choices(fraction(data['first']['radius']),fraction(data['second']['radius']),fraction(data['contactMargin']),stats)
    contains(interval(evaluation['threshold']),(min(threshold),max(threshold)),'left-associated radius/margin threshold')
    # Use the entire recorded root/threshold boxes, not only nominal values.
    gap=extrema_choices('sub',(lower,upper),interval(evaluation['threshold']),stats)
    contains(interval(evaluation['gap']),gap,'gap over recorded root and original threshold AST')
    stats['returnedEvaluations']+=1;stats['returnedIntervals']+=15
    stats['rootSquareProofs']+=1;stats['deltaSquareProofs']+=1;stats['sqrtLimitedReturns']+=int(root['refinementLimited'])
    stats['limitedPositiveEvaluations']+=int(root['refinementLimited'] and interval(evaluation['gap'])[0]>0)
    stats['sqrtRefinementsReturned']+=root['refinements']


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
    fields(source['settings'],{'timeTolerance','maxEvaluations','maxLeaves','maxDepth','sqrtRefinements'},'complete profile')
    fraction(source['settings']['timeTolerance']);fraction(source['horizon'])
    for key in ['maxEvaluations','maxLeaves','maxDepth','sqrtRefinements']:uint(source['settings'][key],2**64-1,'input '+key)
    data=source['input'];fields(data,{'first','second','firstPositionError','secondPositionError','contactMargin'},'explicit two-box input')
    sphere_shape(data['first']);sphere_shape(data['second'])
    for key in ['firstPositionError','secondPositionError','contactMargin']:fraction(data[key])


def preflight(source):
    source_shape(source);s=source['settings'];data=source['input']
    if not (0<fraction(s['timeTolerance'])<=fraction(.1) and 1<=s['maxEvaluations']<=255
            and 1<=s['maxLeaves']<=128 and s['maxDepth']<=32 and 1<=s['sqrtRefinements']<=256):return 'settings',None
    if not 0<fraction(source['horizon'])<=fraction(.1):return 'horizon',None
    for ordinal,key in enumerate(['first','second']):
        sphere=data[key]
        if not (0<fraction(sphere['radius'])<=10**12 and all(abs(x)<=10**12
                for name in ['center','velocity','acceleration'] for x in vector(sphere[name]))):return 'input_domain',ordinal
    for ordinal,key in [(2,'firstPositionError'),(3,'secondPositionError')]:
        if not 0<=fraction(data[key])<=10**12:return 'position_error',ordinal
    if not 0<=fraction(data['contactMargin'])<=fraction(.1):return 'contact_margin',4
    return None,None


def cell_shape(cell,horizon):
    fields(cell,{'timeBounds','depth','parentAudit'},'closed global time cell')
    lo,hi=interval(cell['timeBounds']);need(0<=lo<hi<=fraction(horizon),'nondegenerate cell in global seconds')
    uint(cell['depth'],32,'cell depth')
    if cell['parentAudit'] is not None:uint(cell['parentAudit'],254,'parent audit link')


def empty_work():
    return {key:True if key=='exact' else 0 for key in WORK_KEYS}


def work_shape(work):
    fields(work,WORK_KEYS,'complete wrapper/observed-root/reservation Work')
    for key,value in work.items():
        if key=='exact':need(type(value) is bool,'root work exact boolean')
        else:uint(value,130560 if 'Refinements' in key else 255,'work '+key)
    need(work['valueCallsReturned']<=work['valueCallsAttempted']<=255,'bounded exact wrapper attempts/returns')


def verify_fixture(source,result,stats):
    reason,failed=preflight(source);fields(result,RESULT_KEYS,'complete coverage result')
    source_shape(result['snapshot'])
    source_equal(source,result['snapshot'])
    need(type(result['snapshotValidated']) is bool and type(result['partitionComplete']) is bool,'snapshot/partition flags')
    if result['failedInput'] is not None:uint(result['failedInput'],4,'failed input ordinal')
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
    attempted=returned=root_work=limited=0;halt=None;current=None
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
        root_work+=audit['evaluation']['root']['refinements'];limited+=int(audit['evaluation']['root']['refinementLimited'])
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
    unknown=attempted-returned
    need(unknown in (0,1),'at most one terminal unreturned value call')
    expected_work={'valueCallsAttempted':attempted,'valueCallsReturned':returned,'sqrtResultsReturned':returned,
                   'sqrtRefinementsReturned':root_work,'sqrtLimitedReturns':limited,
                   'sqrtRefinementsUpper':root_work+unknown*2*s['sqrtRefinements'],'exact':unknown==0}
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
                         'currentCells','returnedEvaluations','returnedIntervals','coordinateRangeProofs','deltaSquareProofs',
                         'astNodePairs','limitedPositiveEvaluations','rootSquareProofs','sqrtLimitedReturns','sqrtRefinementsReturned','certifiedLeaves','splitAudits','maximumAudits','maximumPartition',
                         'maximumFrontier','subdividedCertified'],0)
    result['fixtures']=count
    result['blockedReasons']=dict.fromkeys(['nonpositive_value','width_limit','depth_budget','time_resolution','leaf_budget'],0)
    return result


def verify(data):
    fields(data,{'schema','kind','fixtures'},'finite box coverage fixture envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='accelerated-sphere-box-coverage-fixtures','box coverage schema/kind')
    need(EXPECTED_FIXTURE_COUNT is not None,'finite corpus count/fingerprint freeze pending')
    need(type(data['fixtures']) is list and len(data['fixtures'])==EXPECTED_FIXTURE_COUNT,'complete fixed input corpus')
    fingerprint=input_fingerprint(data['fixtures'])
    need(EXPECTED_INPUT_FINGERPRINT is not None and fingerprint==EXPECTED_INPUT_FINGERPRINT,'whole input multiset/scalar-type/bit fingerprint')
    stats=new_stats(len(data['fixtures']));names=set()
    for fixture in data['fixtures']:
        fields(fixture,{'name','input','result'},'complete fixture')
        need(type(fixture['name']) is str and fixture['name'] and fixture['name'] not in names,'unique fixture labels')
        names.add(fixture['name']);verify_fixture(fixture['input'],fixture['result'],stats)
    need(stats['returnedEvaluations']==stats['cellAudits'],'all actual audit records returned in natural finite corpus')
    need((stats['maximumAudits'],stats['maximumPartition'],stats['maximumFrontier'])==(255,128,127),'full hard capacities and complete unknown tail')
    need(stats['subdividedCertified']>=1 and all(stats['blockedReasons'].values()),'nonvacuous subdivision and each stopping condition')
    need((stats['certified'],stats['notCertified'],stats['invalidInputs'])==(20,21,34),'fixed finite outcome profile')
    need(stats['returnedEvaluations']==955 and stats['returnedIntervals']==14325,'all 955 full Evaluations / 14325 intervals')
    need(stats['sqrtLimitedReturns']>0 and stats['limitedPositiveEvaluations']>0,'limited-but-valid actual positive root coverage')
    return {'status':'PASS',**stats,'inputFingerprint':fingerprint,
            'scope':'Exact Fraction six quadratic tubes plus both declared B, recorded-box delta/square/left-sum exact-or-integer-binary64-RN extrema, lower-only clamp and full sqrt square inequalities/RN endpoint lemma, threshold/gap AST; independent complete BFS/source-bit/root-work replay. Actual public value endpoint bits are a separate Native provenance gate. No actual World/B derivation, external std::sqrt binding, response or fault injection claim.'}


if __name__=='__main__':
    need(__debug__,'run box coverage reference without Python -O')
    need(len(sys.argv)==2,'Usage: verify-accelerated-sphere-box-coverage.py native-fixtures.json')
    print(json.dumps(verify(load(sys.argv[1]))))
