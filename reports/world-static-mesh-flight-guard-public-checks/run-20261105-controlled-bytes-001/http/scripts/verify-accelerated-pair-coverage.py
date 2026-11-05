"""Independent rational range and complete coverage audit of point SI paths.

No Native value function, interval implementation, floating point polynomial
solver, or finite time sampling supplies the mathematical reference. Exact
quadratic extrema and sign-aware squared norm comparisons cover planes. Sphere
quartics use rational Bernstein certificates with square-factor removal.
Actual public-value bit provenance is a separate Native test obligation: a
different, wider but mathematically valid interval is not inherently false.
"""
from fractions import Fraction as F
from math import comb
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

EXPECTED_FIXTURE_COUNT = 65
EXPECTED_INPUT_FINGERPRINT = '867fef69e55cf8461310b07f0144c8d2288987ab68311d6d86a04b01e8cca85e'
MAX_PROOF_NODES = 65536
MAX_PROOF_DEPTH = 128
RESULT_KEYS = {'status','reason','snapshot','snapshotValidated','failedInput','partitionComplete',
               'audits','partition','frontier','current','work'}
WORK_KEYS = {'valueCallsAttempted','valueCallsReturned','planeNormCallsUpper','planeNormLoopIterationsUpper'}
REASONS = {'none','settings','horizon','input_domain','zero_normal','evaluation_budget','leaf_budget',
           'depth_budget','width_limit','time_resolution','nonpositive_value','value_exception',
           'allocation_failure','environment','coverage_inconsistent'}


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


def trim(p):
    p=list(map(F,p))
    while len(p)>1 and p[-1]==0:p.pop()
    return p or [F(0)]


def evaluate(p,x):
    value=F(0)
    for c in reversed(p):value=value*x+c
    return value


def derivative(p):
    return trim([i*c for i,c in enumerate(p)][1:])


def multiply(a,b):
    result=[F(0)]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):result[i+j]+=x*y
    return trim(result)


def divide(a,b):
    a,b=trim(a),trim(b);need(b!=[0],'nonzero exact polynomial divisor')
    quotient=[F(0)]*max(1,len(a)-len(b)+1)
    while a!=[0] and len(a)>=len(b):
        k=len(a)-len(b);factor=a[-1]/b[-1];quotient[k]+=factor
        for j,c in enumerate(b):a[k+j]-=factor*c
        a=trim(a)
    return trim(quotient),a


def quotient(a,b):
    q,r=divide(a,b);need(r==[0],'exact polynomial factorization');return q


def gcd(a,b):
    a,b=trim(a),trim(b)
    while b!=[0]:_,r=divide(a,b);a,b=b,r
    return [c/a[-1] for c in a] if a!=[0] else [F(0)]


def odd_part(p):
    """Remove even multiplicities, preserving the exact leading sign.

    P>=0 on a nondegenerate closed interval iff its odd-multiplicity residual
    is nonnegative. Removed squares have isolated zeros; continuity handles
    those zeros without an epsilon or a finite sample assumption.
    """
    p=trim(p)
    if len(p)<=1:return p,0
    leading=p[-1];f=[c/leading for c in p]
    c=gcd(f,derivative(f));w=quotient(f,c);i=1;result=[leading];removed=0
    while w!=[1]:
        y=gcd(w,c);factor=quotient(w,y)
        if i%2:result=multiply(result,factor)
        else:removed+=len(factor)-1
        w=y;c=quotient(c,y);i+=1
        need(i<=6,'bounded quartic square-factor decomposition')
    return trim(result),removed


def quadratic_range(p,lo,hi):
    p=trim(p);need(len(p)<=3 and lo<=hi,'quadratic closed range')
    times=[lo,hi]
    if len(p)==3 and p[2]:
        stationary=-p[1]/(2*p[2])
        if lo<=stationary<=hi:times.append(stationary)
    values=[evaluate(p,t) for t in times]
    return min(values),max(values)


def bernstein(p,lo,hi):
    p=trim(p);n=len(p)-1;w=hi-lo
    power=[sum((p[k]*comb(k,j)*lo**(k-j)*w**j for k in range(j,n+1)),F(0)) for j in range(n+1)]
    return [sum((power[j]*F(comb(i,j),comb(n,j)) for j in range(i+1)),F(0)) for i in range(n+1)]


def bisect_bernstein(coefficients):
    rows=[list(coefficients)]
    while len(rows[-1])>1:
        rows.append([(a+b)/2 for a,b in zip(rows[-1],rows[-1][1:])])
    return [r[0] for r in rows],[r[-1] for r in reversed(rows)]


def nonnegative(p,lo,hi,stats=None):
    """Exact sufficient proof, or fail closed within finite checker budgets."""
    p=trim(p);need(lo<=hi,'ordered polynomial proof cell')
    if lo==hi:
        need(evaluate(p,lo)>=0,'point polynomial lower bound');return
    if len(p)<=3:
        need(quadratic_range(p,lo,hi)[0]>=0,'quadratic whole-cell nonnegativity')
        if stats is not None:stats['quadraticProofs']+=1
        return
    need(len(p)<=5,'degree at most four')
    residual,removed=odd_part(p)
    if stats is not None:stats['squareFactorsRemoved']+=removed
    if len(residual)<=3:
        need(quadratic_range(residual,lo,hi)[0]>=0,'square-free residual nonnegative')
        if stats is not None:stats['quadraticProofs']+=1
        return
    stack=[(bernstein(residual,lo,hi),0)];nodes=0
    while stack:
        coefficients,depth=stack.pop();nodes+=1
        need(nodes<=MAX_PROOF_NODES,'checker polynomial proof-node budget unresolved')
        need(coefficients[0]>=0 and coefficients[-1]>=0,'negative exact polynomial point contradicts enclosure')
        if min(coefficients)>=0:continue
        need(depth<MAX_PROOF_DEPTH,'checker polynomial proof-depth unresolved')
        left,right=bisect_bernstein(coefficients)
        stack.extend([(right,depth+1),(left,depth+1)])
    if stats is not None:
        stats['bernsteinProofs']+=1;stats['bernsteinNodes']+=nodes
        stats['maximumBernsteinNodes']=max(stats['maximumBernsteinNodes'],nodes)


def sphere_polynomial(source):
    a,b=source['input']['first'],source['input']['second']
    components=[]
    for axis in range(3):
        components.append([fraction(b['center'][axis])-fraction(a['center'][axis]),
                           fraction(b['velocity'][axis])-fraction(a['velocity'][axis]),
                           (fraction(b['acceleration'][axis])-fraction(a['acceleration'][axis]))/2])
    result=[F(0)]*5
    for component in components:
        for i,c in enumerate(multiply(component,component)):result[i]+=c
    result[0]-=(fraction(a['radius'])+fraction(b['radius']))**2
    return trim(result)


def plane_equation(source):
    sphere,plane=source['input']['sphere'],source['input']['plane'];n=vector(plane['normal'])
    coeff=[sum((n[i]*fraction(sphere['center'][i]) for i in range(3)),F(0))-fraction(plane['offset']),
           sum((n[i]*fraction(sphere['velocity'][i]) for i in range(3)),F(0)),
           sum((n[i]*fraction(sphere['acceleration'][i])/2 for i in range(3)),F(0))]
    return trim(coeff),fraction(sphere['radius'])**2*sum((x*x for x in n),F(0))


def verify_range(source,cell,value,stats):
    lo,hi=map(fraction,cell['timeBounds']);lower,upper=interval(value)
    if source['input']['kind']=='sphere_plane':
        q,norm_squared_radius=plane_equation(source);qmin,qmax=quadratic_range(q,lo,hi)
        left=qmin-lower;right=qmax-upper
        need(left>=0 and left*left>=norm_squared_radius,'plane lower enclosure: sign then exact squared norm')
        need(right<=0 or right*right<=norm_squared_radius,'plane upper enclosure: sign then exact squared norm')
        stats['planeRangeProofs']+=1
    else:
        p=sphere_polynomial(source);lower_poly=p.copy();lower_poly[0]-=lower
        upper_poly=[-c for c in p];upper_poly[0]+=upper
        nonnegative(lower_poly,lo,hi,stats);nonnegative(upper_poly,lo,hi,stats)
        stats['sphereRangeProofs']+=1
    stats['returnedIntervals']+=1


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
    fields(value,{'center','velocity','acceleration','radius'},'point sphere')
    for key in ['center','velocity','acceleration']:vector(value[key])
    fraction(value['radius'])


def source_shape(source):
    fields(source,{'input','horizon','settings'},'complete source')
    fields(source['settings'],{'timeTolerance','maxEvaluations','maxLeaves','maxDepth'},'complete profile')
    fraction(source['settings']['timeTolerance']);fraction(source['horizon'])
    for key in ['maxEvaluations','maxLeaves','maxDepth']:uint(source['settings'][key],2**64-1,'input '+key)
    data=source['input'];need(type(data) is dict and type(data.get('kind')) is str,'input variant')
    if data['kind']=='sphere_pair':
        fields(data,{'kind','first','second'},'sphere pair variant');sphere_shape(data['first']);sphere_shape(data['second'])
    else:
        need(data['kind']=='sphere_plane','known input variant')
        fields(data,{'kind','sphere','plane'},'sphere plane variant');sphere_shape(data['sphere'])
        fields(data['plane'],{'normal','offset'},'raw plane');vector(data['plane']['normal']);fraction(data['plane']['offset'])


def sphere_valid(value):
    return 0<fraction(value['radius'])<=10**12 and all(abs(x)<=10**12 for key in ['center','velocity','acceleration'] for x in vector(value[key]))


def preflight(source):
    source_shape(source);s=source['settings'];data=source['input']
    if not (0<fraction(s['timeTolerance'])<=fraction(.1) and 1<=s['maxEvaluations']<=255
            and 1<=s['maxLeaves']<=128 and s['maxDepth']<=32):return 'settings',None
    if not 0<fraction(source['horizon'])<=fraction(.1):return 'horizon',None
    if not sphere_valid(data['first'] if data['kind']=='sphere_pair' else data['sphere']):return 'input_domain',0
    if data['kind']=='sphere_pair':
        if not sphere_valid(data['second']):return 'input_domain',1
    else:
        plane=data['plane'];normal=vector(plane['normal'])
        if any(abs(v)>10**12 for v in normal) or abs(fraction(plane['offset']))>10**12:return 'input_domain',1
        if all(v==0 for v in normal):return 'zero_normal',1
    return None,None


def cell_shape(cell,horizon):
    fields(cell,{'timeBounds','depth','parentAudit'},'closed global time cell')
    lo,hi=interval(cell['timeBounds']);need(0<=lo<hi<=fraction(horizon),'nondegenerate cell in global seconds')
    uint(cell['depth'],32,'cell depth')
    if cell['parentAudit'] is not None:uint(cell['parentAudit'],254,'parent audit link')


def empty_work():
    return dict.fromkeys(WORK_KEYS,0)


def work_shape(work):
    fields(work,WORK_KEYS,'wrapper exact calls and private-norm upper bounds')
    for key,value in work.items():uint(value,16320,'work '+key)
    need(work['valueCallsReturned']<=work['valueCallsAttempted']<=255,'bounded exact attempts/returns')


def verify_fixture(source,result,stats):
    reason,failed=preflight(source);fields(result,RESULT_KEYS,'complete coverage result')
    source_shape(result['snapshot'])
    source_equal(source,result['snapshot'])
    need(type(result['snapshotValidated']) is bool and type(result['partitionComplete']) is bool,'snapshot/partition flags')
    if result['failedInput'] is not None:uint(result['failedInput'],1,'failed input ordinal')
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
    horizon=source['horizon'];s=source['settings'];kind=source['input']['kind']
    own=[{'cell':{'timeBounds':[0.,horizon],'depth':0,'parentAudit':None},'state':'unqueried','auditIndex':None,'blockedReason':'none'}]
    attempted=returned=0;halt=None;current=None
    def select():
        eligible=[i for i,leaf in enumerate(own) if leaf['state']=='unqueried']
        return min(eligible,key=lambda i:(own[i]['cell']['depth'],fraction(own[i]['cell']['timeBounds'][0]))) if eligible else None
    for ordinal,audit in enumerate(result['audits']):
        fields(audit,{'cell','callAttempted','value','outcome','blockedReason','splitTime'},'full audit')
        cell_shape(audit['cell'],horizon)
        need(type(audit['callAttempted']) is bool and audit['callAttempted'],'actual finite value call attempt')
        need(type(audit['outcome']) is str and audit['outcome'] in {'positive','split','blocked'},'no final pending audit')
        need(type(audit['blockedReason']) is str and audit['blockedReason'] in REASONS,'audit blocked reason enum')
        index=select();need(index is not None and attempted<s['maxEvaluations'],'BFS has an eligible cell and evaluation grant')
        leaf=own[index];source_equal(leaf['cell'],audit['cell']);attempted+=1
        if audit['value'] is None:
            need(ordinal==len(result['audits'])-1 and audit['outcome']=='blocked' and audit['blockedReason']=='value_exception'
                 and audit['splitTime'] is None,'nonreturned attempt is a terminal exception, not proof')
            leaf.update(state='current',auditIndex=ordinal,blockedReason='value_exception')
            current=leaf['cell'];halt='value_exception';break
        returned+=1;verify_range(source,audit['cell'],audit['value'],stats)
        lower,upper=interval(audit['value']);leaf['auditIndex']=ordinal
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
    expected_work={'valueCallsAttempted':attempted,'valueCallsReturned':returned,
                   'planeNormCallsUpper':attempted if kind=='sphere_plane' else 0,
                   'planeNormLoopIterationsUpper':64*attempted if kind=='sphere_plane' else 0}
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
                         'currentCells','returnedIntervals','planeRangeProofs','sphereRangeProofs','quadraticProofs',
                         'bernsteinProofs','bernsteinNodes','maximumBernsteinNodes','squareFactorsRemoved',
                         'certifiedLeaves','splitAudits','maximumAudits','maximumPartition','maximumFrontier','subdividedCertified'],0)
    result['fixtures']=count
    result['blockedReasons']=dict.fromkeys(['nonpositive_value','width_limit','depth_budget','time_resolution','leaf_budget'],0)
    return result


def verify(data):
    fields(data,{'schema','kind','fixtures'},'finite coverage fixture envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='accelerated-pair-coverage-fixtures','coverage schema/kind')
    need(type(data['fixtures']) is list and len(data['fixtures'])==EXPECTED_FIXTURE_COUNT,'complete fixed65 inputs')
    fingerprint=input_fingerprint(data['fixtures'])
    need(EXPECTED_INPUT_FINGERPRINT is not None and fingerprint==EXPECTED_INPUT_FINGERPRINT,'whole input multiset/scalar-type/bit fingerprint')
    stats=new_stats(len(data['fixtures']));names=set()
    for fixture in data['fixtures']:
        fields(fixture,{'name','input','result'},'complete fixture')
        need(type(fixture['name']) is str and fixture['name'] and fixture['name'] not in names,'unique fixture labels')
        names.add(fixture['name']);verify_fixture(fixture['input'],fixture['result'],stats)
    need((stats['certified'],stats['notCertified'],stats['invalidInputs'])==(18,19,28),'finite corpus outcome profile')
    need(stats['returnedIntervals']==stats['cellAudits']==1913,'all1913 actual returned intervals independently audited')
    need((stats['maximumAudits'],stats['maximumPartition'],stats['maximumFrontier'])==(255,128,127),'full hard capacities and complete unknown tail')
    need(stats['subdividedCertified']>=2 and all(stats['blockedReasons'].values()),'nonvacuous subdivision and each stopping condition')
    return {'status':'PASS',**stats,'inputFingerprint':fingerprint,
            'scope':'Exact rational full-cell interval containment plus independent global-seconds BFS/partition/work metadata. Actual public-value bit provenance belongs to the separate Native1913 replay; a wider mathematically valid interval need not fail this checker. No finite sampling, TOI, response, World advance or allocation-fault execution is inferred.'}


if __name__=='__main__':
    need(__debug__,'run coverage reference without Python -O')
    need(len(sys.argv)==2,'Usage: verify-accelerated-pair-coverage.py native-fixtures.json')
    print(json.dumps(verify(load(sys.argv[1]))))
