"""Independent rational IEEE-operation and sphere/mesh free-flight proof audit.

The RN reference is implemented using integer quotient/remainder and IEEE bits,
not the Native candidate, Python arithmetic on the proposed graph, or a compiled
solver. The all-duration statement follows rational magnitude/ULP recurrences;
finite sampled durations in self-tests are only additional regression checks.
"""
from fractions import Fraction as F
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

spec=importlib.util.spec_from_file_location('free_flight_held_reference',Path(__file__).with_name('check-sphere-triangle-mesh-held-load.py'))
held=importlib.util.module_from_spec(spec)
spec.loader.exec_module(held)
need,fraction,vector=held.need,held.fraction,held.vector
fields,uint,interval,bounds3=held.fields,held.uint,held.interval,held.bounds3
bits,source_equal,loads,load=held.bits,held.source_equal,held.loads,held.load


def float_from_bits(value):
    return struct.unpack('>d',struct.pack('>Q',value))[0]


def raw_bits(value):
    need(type(value) in (int,float),'binary64 scalar')
    return struct.unpack('>Q',struct.pack('>d',float(value)))[0]


def _round_even(numerator,denominator):
    quotient,remainder=divmod(numerator,denominator)
    doubled=2*remainder
    return quotient+(doubled>denominator or (doubled==denominator and quotient%2==1))


def rn(value,negative_zero=False):
    """Correct nearest/ties-to-even binary64 by integer construction.

    Fraction alone cannot represent signed zero, hence the explicit zero sign.
    Overflow is rejected; a caller cannot use an infinity as a finite result.
    """
    value=F(value)
    sign=value<0 or (value==0 and negative_zero)
    if not value: return float_from_bits(int(sign)<<63)
    n,d=abs(value).numerator,abs(value).denominator
    exponent=n.bit_length()-d.bit_length()
    below_power=(n < d*(1<<exponent)) if exponent>=0 else (n*(1<<-exponent)<d)
    if below_power:
        exponent-=1
    shift=1074 if exponent < -1022 else 52-exponent
    if shift>=0: mantissa=_round_even(n<<shift,d)
    else: mantissa=_round_even(n,d<<-shift)
    if exponent < -1022:
        payload=mantissa # Rounding the largest subnormal may yield min-normal.
    else:
        if mantissa==1<<53:
            exponent+=1;mantissa=1<<52
        need(exponent<=1023,'RN operation overflows binary64')
        payload=((exponent+1023)<<52)+(mantissa-(1<<52))
    need(0<=payload<0x7ff0000000000000,'finite RN output')
    return float_from_bits((int(sign)<<63)|payload)


def rn_add(a,b):
    value=fraction(a)+fraction(b)
    return rn(value,negative_zero=not value and raw_bits(a)>>63==raw_bits(b)>>63==1)


def rn_mul(a,b):
    value=fraction(a)*fraction(b)
    return rn(value,negative_zero=not value and bool((raw_bits(a)^raw_bits(b))>>63))


def rn_div(a,b):
    need(fraction(b)!=0,'nonzero RN denominator')
    value=fraction(a)/fraction(b)
    return rn(value,negative_zero=not value and bool((raw_bits(a)^raw_bits(b))>>63))


def ceil_binary64(value):
    value=F(value)
    need(value>=0,'nonnegative magnitude bound')
    rounded=rn(value)
    raw=raw_bits(rounded)
    if fraction(rounded)<value: raw+=1
    need(raw<0x7ff0000000000000,'finite upper magnitude')
    return float_from_bits(raw)


def spacing_bound(value):
    """One full adjacent spacing at an outward magnitude, incl. subnormal."""
    upper=ceil_binary64(value)
    raw=raw_bits(upper)
    need(raw+1<0x7ff0000000000000,'finite adjacent spacing')
    return fraction(float_from_bits(raw+1))-fraction(upper)


def nominal_acceleration(body,gravity):
    inverse=rn_div(1,body['mass'])
    return tuple(rn_add(g,rn_mul(f,inverse)) for g,f in zip(gravity,body['force']))


def nominal_position(body,gravity,time):
    """The declared propagator's graph: ((p+v*t)+a*((.5*t)*t))."""
    acceleration=nominal_acceleration(body,gravity)
    s=rn_mul(rn_mul(.5,time),time)
    return tuple(rn_add(rn_add(p,rn_mul(v,time)),rn_mul(a,s))
                 for p,v,a in zip(body['position'],body['velocity'],acceleration))


def nominal_velocity(body,gravity,time):
    acceleration=nominal_acceleration(body,gravity)
    return tuple(rn_add(v,rn_mul(a,time)) for v,a in zip(body['velocity'],acceleration))


def all_duration_reference(body,gravity,horizon):
    """Exact safe ULP recurrence for every representable t in [0,H].

    Every ULP is selected at a rational upper bound on that primitive's RESULT
    magnitude. Error dependencies are propagated before selecting the next ULP.
    This is a conservative recurrence, not a measured count or fitted sample.
    """
    h=fraction(horizon)
    need(0<h<=fraction(.1),'single free-flight duration domain')
    nominal=nominal_acceleration(body,gravity)
    exact=held.add(vector(gravity),held.scale(vector(body['force']),1/fraction(body['mass'])))
    roundoff=[];coefficient=[]
    for p,v,a,actual in zip(vector(body['position']),vector(body['velocity']),map(fraction,nominal),exact):
        aa,vv,pp=abs(a),abs(v),abs(p)
        q,s=h/2,h*h/2
        eq=spacing_bound(q)
        es=eq*h+spacing_bound((q+eq)*h)
        eu=aa*es+spacing_bound(aa*(s+es))
        ez=spacing_bound(vv*h)
        ex=ez+spacing_bound(pp+vv*h+ez)
        er=ex+eu+spacing_bound(pp+vv*h+aa*s+ex+eu)
        roundoff.append(er)
        coefficient.append(abs(actual-a)*s)
    return {'nominalAcceleration':nominal,'exactAcceleration':exact,
            'roundoffComponents':tuple(roundoff),'coefficientComponents':tuple(coefficient),
            'roundoff':sum(roundoff),'coefficient':sum(coefficient),
            'total':sum(roundoff)+sum(coefficient)}


EXPECTED_FIXTURE_COUNT=100
EXPECTED_INPUT_FINGERPRINT='c14d0e37cd5fe3d85d30ec0a408d46608ecefabb8b55513e31e51dbfe6ed2d37'
EXPECTED_SUPPLEMENTAL_FINGERPRINT='a23779088fc9d7ce9bf388456b055795ccf3c5ea85fdab3b11df50ea7a604d80'
BODY_KEYS={'id','isStatic','mass','inertiaDiagonal','radius','position','velocity','angularMomentum','force','torque','orientation','material'}
RESULT_KEYS={'status','reason','failedIndex','worldBody','snapshot','tube','flightFailure','candidateEvaluated','endpoint','inflated','candidate'}
STATUSES={'certified_separated','not_certified','invalid_input','unsupported_environment','numerical_failure'}
REASONS={'none','settings','body_not_found','body_invalid','unsupported_body','input_domain','surface_count','surface_id',
         'duplicate_id','surface_budget','flight_tube_failure','derived_domain','inflated_radius_domain','propagation_failure',
         'candidate_invalid','endpoint_tube_failure','held_load_not_separated','environment','allocation_failure',
         'nonfinite_intermediate','coverage_inconsistent'}


def input_fingerprint(fixtures):
    """Whole input multiset, array order/-0 preserved; bool distinct from 0/1."""
    def encode(value):
        if type(value) is bool:return 'true' if value else 'false'
        if type(value) in (int,float):return 'n:'+bits(value).hex()
        if type(value) is dict:return '{'+','.join(json.dumps(k)+':'+encode(value[k]) for k in sorted(value))+'}'
        if type(value) is list:return '['+','.join(encode(x) for x in value)+']'
        raise AssertionError('guard input fingerprint shape')
    return hashlib.sha256('\n'.join(sorted(encode(f['input']) for f in fixtures)).encode('utf-8')).hexdigest()


def squared_rn(values):
    total=rn_mul(values[0],values[0])
    for value in values[1:]: total=rn_add(total,rn_mul(value,value))
    return total


def body_valid(value):
    """Field/domain validation, separate from orientation integration correctness."""
    fields(value,BODY_KEYS,'owned rigid body')
    need(type(value['id']) is int and type(value['isStatic']) is bool,'body metadata types')
    for key in ['position','velocity','angularMomentum','force','torque','inertiaDiagonal']: vector(value[key])
    need(type(value['orientation']) is list and len(value['orientation'])==4,'quaternion four scalars')
    q=[fraction(x) for x in value['orientation']]
    fields(value['material'],{'restitution','friction'},'body material')
    ranges=(1<=value['id']<=2**53-1 and fraction(1e-12)<=fraction(value['mass'])<=10**18
            and 0<fraction(value['radius'])<=10**9
            and 0<=fraction(value['material']['restitution'])<=1
            and 0<=fraction(value['material']['friction'])<=10)
    caps={'position':10**12,'velocity':10**9,'angularMomentum':F(1e24),'force':F(1e24),'torque':F(1e24)}
    ranges=ranges and all(abs(x)<=cap for key,cap in caps.items() for x in vector(value[key]))
    inertia=vector(value['inertiaDiagonal'])
    ranges=ranges and all(fraction(1e-12)<=x<=10**18 for x in inertia)
    ranges=ranges and all(fraction(rn_add(value['inertiaDiagonal'][a],value['inertiaDiagonal'][b]))>=inertia[c]
                             for a,b,c in [(0,1,2),(0,2,1),(1,2,0)])
    # Quaternion norm is a Native field validation condition, not a proof of the
    # correctness of an integrated rotation or continuous six-DOF true solution.
    if any(abs(x)>2 for x in q): return False
    ranges=ranges and abs(fraction(rn_add(squared_rn(value['orientation']),-1)))<fraction(1e-8)
    if value['isStatic']:
        ranges=ranges and squared_rn(value['velocity'])==0 and squared_rn(value['angularMomentum'])==0
    return ranges


def held_source(source,radius=None):
    body=source['body']
    return {'sphere':{'id':body['id'],'position':body['position'],'velocity':body['velocity'],'mass':body['mass'],
                      'force':body['force'],'gravity':source['gravity'],'radius':body['radius'] if radius is None else radius},
            'horizon':source['horizon'],'triangles':source['triangles'],'settings':source['settings']['heldLoad']}


def input_faults(source):
    fields(source,{'body','gravity','horizon','triangles','settings'},'free-flight input')
    fields(source['settings'],{'heldLoad','maxAngularIncrement'},'guard settings')
    vector(source['gravity'])
    valid_body=body_valid(source['body'])
    faults=held.input_faults(held_source(source))
    if not valid_body: faults.add(('body_invalid',None))
    if not 0<fraction(source['settings']['maxAngularIncrement'])<=fraction(math.pi):
        faults.add(('settings',None))
    return faults,valid_body


def held_stats():
    return {k:0 for k in ['fixtures','entryWindows','separated','initialPenetrations','notCertified','invalidInputs',
        'wholePathReferences','initialPointReferences','prefixReferences','entryWidthReferences','witnessReferences',
        'certifiedLeaves','positiveIslandsBeyondPrefix','cellAudits','pathBoxReferences','squaredBoxReferences',
        'certificateReferences','lastMeshReferenceComponents','workExactFixtures','accelerationReferences',
        'windowSpatialReferences','derivedDomainFailures']}


def verify_tube(source,tube,stats):
    fields(tube,{'nominalAcceleration','exactAcceleration','accelerationDifference','positionError','roundoff','guardRadius'},'W1 translation tube')
    ref=all_duration_reference(source['body'],source['gravity'],source['horizon'])
    source_equal(list(ref['nominalAcceleration']),tube['nominalAcceleration'])
    held.contains3(tube['exactAcceleration'],ref['exactAcceleration'])
    delta=held.sub(ref['exactAcceleration'],tuple(map(fraction,ref['nominalAcceleration'])))
    held.contains3(tube['accelerationDifference'],delta)
    # The published difference also encloses the ENTIRE stored A interval.
    for (alo,ahi),(dlo,dhi),nominal in zip(bounds3(tube['exactAcceleration']),bounds3(tube['accelerationDifference']),map(fraction,ref['nominalAcceleration'])):
        need(dlo<=alo-nominal and ahi-nominal<=dhi,'coefficient difference source enclosure')
    b,roundoff,radius=map(fraction,[tube['positionError'],tube['roundoff'],tube['guardRadius']])
    need(b>=roundoff>=ref['roundoff'] and b>=ref['total'],'whole-duration roundoff PLUS exact coefficient discrepancy retained')
    need(radius>=fraction(source['body']['radius'])+b,'guard radius is an upward enclosure of original r+B')
    stats['tubeReferences']+=1
    stats['nominalAccelerationBits']+=3
    return ref


def verify_endpoint(source,result,ref,stats):
    value=result['endpoint'];tube=result['tube']
    fields(value,{'nominalPosition','nominalAllowed','exactPosition','exactAllowed','exactDifference','l1ErrorBound',
                  'nominalContained','exactContained','l1WithinTube'},'endpoint audit')
    h=fraction(source['horizon']);body=source['body']
    actual=nominal_position(body,source['gravity'],source['horizon'])
    nominal=held.add(vector(body['position']),held.add(held.scale(vector(body['velocity']),h),held.scale(tuple(map(fraction,ref['nominalAcceleration'])),h*h/2)))
    exact=held.path_point(held_source(source),h)
    held.contains3(value['nominalPosition'],nominal);held.contains3(value['exactPosition'],exact)
    nominal_box,exact_box=bounds3(value['nominalPosition']),bounds3(value['exactPosition'])
    nominal_allowed,exact_allowed=bounds3(value['nominalAllowed']),bounds3(value['exactAllowed'])
    difference=bounds3(value['exactDifference'])
    roundoff,b=map(fraction,[tube['roundoff'],tube['positionError']])
    for (a,z),(l,u) in zip(nominal_box,nominal_allowed): need(l<=a-roundoff and z+roundoff<=u,'nominal endpoint plus roundoff enclosure')
    for (a,z),(l,u) in zip(exact_box,exact_allowed): need(l<=a-b and z+b<=u,'real endpoint plus full tube enclosure')
    for p,(a,z),(l,u) in zip(map(fraction,actual),exact_box,difference): need(l<=p-z and p-a<=u,'actual candidate minus full real endpoint interval')
    l1=sum(max(abs(a),abs(z)) for a,z in difference)
    l1_min=sum(F(0) if a<=0<=z else min(abs(a),abs(z)) for a,z in difference)
    llo,lhi=interval(value['l1ErrorBound'])
    need(llo<=l1_min<=l1<=lhi,'L1 interval contains the full stored difference box norm range')
    expected={'nominalContained':all(l<=fraction(p)<=u for p,(l,u) in zip(actual,nominal_allowed)),
              'exactContained':all(l<=fraction(p)<=u for p,(l,u) in zip(actual,exact_allowed)),
              'l1WithinTube':interval(value['l1ErrorBound'])[1]<=b}
    need(all(type(value[k]) is bool and value[k]==flag for k,flag in expected.items()),'endpoint flags follow independent actual graph and published bounds')
    stats['endpointReferences']+=1
    stats['candidatePositionBits']+=3
    return all(expected.values()),actual


def verify_candidate(source,result,actual,stats):
    candidate=result['candidate'];body=source['body']
    need(body_valid(candidate),'published candidate complete body validation')
    for key in BODY_KEYS-{'position','velocity','orientation','angularMomentum'}: source_equal(body[key],candidate[key])
    source_equal(list(actual),candidate['position'])
    source_equal(list(nominal_velocity(body,source['gravity'],source['horizon'])),candidate['velocity'])
    expected=[rn_add(l,rn_mul(t,source['horizon'])) for l,t in zip(body['angularMomentum'],body['torque'])]
    source_equal(expected,candidate['angularMomentum'])
    stats['candidatePublished']+=1
    stats['candidateVelocityAngularBits']+=6


def verify_fixture(source,result,stats):
    faults,valid_body=input_faults(source)
    fields(result,RESULT_KEYS,'free-flight result')
    need(type(result['status']) is str and result['status'] in STATUSES and type(result['reason']) is str and result['reason'] in REASONS,'guard classification')
    need(result['status'] not in {'unsupported_environment','numerical_failure'},'ordinary finite corpus does not claim allocator/environment fault injection')
    source_equal({'body':source['body'],'gravity':source['gravity']},result['worldBody'])
    need(type(result['candidateEvaluated']) is bool,'actual candidate attempt flag')
    if result['failedIndex'] is not None: uint(result['failedIndex'],len(source['triangles'])-1,'source failure index')
    if faults:
        need(result['status']=='invalid_input' and (result['reason'],result['failedIndex']) in faults,'independent structural/body/settings preflight')
        need(all(result[k] is None for k in ['snapshot','tube','flightFailure','endpoint','inflated','candidate'])
             and not result['candidateEvaluated'],'preflight has no invented tube, candidate, or held query')
        stats['invalidInputs']+=1
        return
    need(valid_body and result['failedIndex'] is None and result['status']!='invalid_input','valid input retained')
    source_equal(source,result['snapshot'])
    saved_faults,saved_body=input_faults(result['snapshot'])
    need(not saved_faults and saved_body,'owned snapshot preserves integer and boolean metadata types')
    if source['body']['isStatic'] or len(source['triangles'])>source['settings']['heldLoad']['mesh']['maxSurfaces']:
        need(result['status']=='not_certified' and result['reason']==('unsupported_body' if source['body']['isStatic'] else 'surface_budget'),'static/source budget is explicitly unqueried')
        need(all(result[k] is None for k in ['tube','flightFailure','endpoint','inflated','candidate']) and not result['candidateEvaluated'],'no flight for static/source-budget rejection')
        stats['notCertified']+=1
        return
    if result['tube'] is None:
        need(result['status']=='not_certified' and result['reason'] in {'flight_tube_failure','derived_domain'}
             and result['flightFailure'] is not None and not result['candidateEvaluated']
             and all(result[k] is None for k in ['endpoint','inflated','candidate']),'explicit W1 tube failure before candidate')
        uint(result['flightFailure'],12,'W1 failure classification')
        need(result['flightFailure']!=0,'failed bridge has an actual failure classification')
        stats['notCertified']+=1
        stats['flightFailures']+=1
        return
    need(result['flightFailure'] is None,'returned valid flight tube has no stale W1 failure')
    ref=verify_tube(source,result['tube'],stats)
    if any(a < -10**12 or b > 10**12 for a,b in bounds3(result['tube']['exactAcceleration'])):
        need(result['status']=='not_certified' and result['reason']=='derived_domain' and not result['candidateEvaluated']
             and all(result[k] is None for k in ['endpoint','inflated','candidate']),'exact acceleration enclosure domain rejects before candidate')
        stats['notCertified']+=1
        return
    if fraction(result['tube']['guardRadius'])>10**9:
        need(result['status']=='not_certified' and result['reason']=='inflated_radius_domain' and not result['candidateEvaluated']
             and all(result[k] is None for k in ['endpoint','inflated','candidate']),'inflated radius never silently capped')
        stats['notCertified']+=1
        return
    need(result['candidateEvaluated'],'valid-domain tube proceeds to an isolated candidate attempt')
    if result['endpoint'] is None:
        need(result['status']=='not_certified' and result['reason'] in {'propagation_failure','candidate_invalid'}
             and result['inflated'] is result['candidate'] is None,'failed full six-DOF candidate has no fabricated endpoint/query')
        stats['notCertified']+=1
        stats['candidateFailures']+=1
        return
    endpoint_ok,actual=verify_endpoint(source,result,ref,stats)
    if not endpoint_ok:
        need(result['status']=='not_certified' and result['reason']=='endpoint_tube_failure'
             and result['inflated'] is result['candidate'] is None,'endpoint failure cannot publish or query')
        stats['notCertified']+=1
        return
    need(result['inflated'] is not None,'successful candidate endpoint retains actual full inflated held query')
    hs=held_source(source,result['tube']['guardRadius'])
    held.verify_fixture(hs,result['inflated'],stats['held'])
    stats['inflatedQueries']+=1
    if result['inflated']['status']=='separated':
        need(result['inflated']['work']['workExact'] and result['status']=='certified_separated' and result['reason']=='none'
             and result['candidate'] is not None,'ONLY full inflated separation publishes candidate')
        verify_candidate(source,result,actual,stats)
        stats['certifiedSeparated']+=1
    else:
        need(result['status']=='not_certified' and result['reason']=='held_load_not_separated' and result['candidate'] is None,
             'inflated entry/penetration/unknown is not original contact or successful guard')
        stats['notCertified']+=1


def verify(data):
    fields(data,{'schema','kind','fixtures'},'free-flight fixture envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='sphere-triangle-mesh-free-flight-guard-fixtures','guard schema')
    need(EXPECTED_FIXTURE_COUNT is not None and EXPECTED_INPUT_FINGERPRINT is not None,'actual complete Native corpus not frozen yet')
    need(type(data['fixtures']) is list and len(data['fixtures'])==EXPECTED_FIXTURE_COUNT,'fixed complete guard fixture count')
    fingerprint=input_fingerprint(data['fixtures'])
    need(fingerprint==EXPECTED_INPUT_FINGERPRINT,'fixed whole-input fingerprint')
    stats=new_stats(len(data['fixtures']))
    names=set()
    for fixture in data['fixtures']:
        fields(fixture,{'name','input','result'},'guard fixture')
        need(type(fixture['name']) is str and fixture['name'] and fixture['name'] not in names,'unique labels')
        names.add(fixture['name']);verify_fixture(fixture['input'],fixture['result'],stats)
    nonvacuity=verify_nonvacuity(data['fixtures'])
    need(stats['certifiedSeparated']>=4 and stats['notCertified'] and stats['invalidInputs'],'nonvacuous multiple safe bodies plus failures')
    return {'status':'PASS',**stats,'inputFingerprint':fingerprint,'analyticAcceptance':nonvacuity,'scope':'Strict noncontracted RN graph and rational all-duration ULP recurrence; coefficient discrepancy, upward r+B, endpoint and full inflated held certificates. Only H translation/velocity/L bits are independent; orientation integration and World immutability are Native test obligations. Not repeated-substep or continuous six-DOF error bounds.'}


def new_stats(count):
    return {'fixtures':count,'certifiedSeparated':0,'notCertified':0,'invalidInputs':0,'tubeReferences':0,
            'nominalAccelerationBits':0,'endpointReferences':0,'candidatePositionBits':0,'candidatePublished':0,
            'candidateVelocityAngularBits':0,'inflatedQueries':0,'flightFailures':0,'candidateFailures':0,'held':held_stats()}


def verify_supplemental(data):
    fields(data,{'schema','kind','fixtures'},'supplemental guard envelope')
    need(type(data['schema']) is int and data['schema']==1 and data['kind']=='sphere-triangle-mesh-free-flight-guard-fixtures','supplemental schema')
    need(type(data['fixtures']) is list and len(data['fixtures'])==4,'separate fixed FOUR supplemental inputs')
    need(EXPECTED_SUPPLEMENTAL_FINGERPRINT is not None,'actual supplemental cohort not frozen yet')
    fingerprint=input_fingerprint(data['fixtures'])
    need(fingerprint==EXPECTED_SUPPLEMENTAL_FINGERPRINT,'fixed supplemental full-input fingerprint')
    stats=new_stats(4);names=set();binades=[];coarse=[]
    for fixture in data['fixtures']:
        fields(fixture,{'name','input','result'},'supplemental row')
        need(type(fixture['name']) is str and fixture['name'] and fixture['name'] not in names,'unique supplemental labels')
        names.add(fixture['name']);verify_fixture(fixture['input'],fixture['result'],stats)
        source,result=fixture['input'],fixture['result']
        if result['status']=='certified_separated':
            binades.append(raw_bits(source['body']['position'][0]))
        else:coarse.append(fixture)
    middle=raw_bits(2.**39)
    need(sorted(binades)==[middle-1,middle,middle+1],'three actual body centres at adjacent binade values')
    need(len(coarse)==1 and stats['certifiedSeparated']==3 and stats['notCertified']==1,'3 safe plus one actual inflated-entry downgrade')
    source,result=coarse[0]['input'],coarse[0]['result']
    need(result['reason']=='held_load_not_separated' and result['candidate'] is None
         and result['inflated']['status']=='entry_window','actual accepted INFLATED entry remains outer guard failure')
    need(fraction(source['settings']['heldLoad']['timeTolerance'])==fraction(.1),'explicit coarse time tolerance; fixed100 default untouched')
    # This path stays vertically over the interior of its translated triangle.
    # Its TRUE original sphere has d_min-r=2^-20, independently of inflated proof.
    hs=held_source(source);h=fraction(source['horizon']);body=source['body']
    ranges=held.path_range(hs,F(0),h)
    need(h==F(1,16) and fraction(body['radius'])==1
         and vector(body['velocity'])==(0,-16,0) and held.acceleration(hs)==(0,512,0),
         'known curved original physical input')
    need(ranges[1][0]-fraction(body['radius'])==F(1,2**20),'original minimum positive gap is EXACT 2^-20')
    need(len(source['triangles'])==1,'single translated reference triangle')
    tri=source['triangles'][0]['vertices']
    for t in [F(0),h]:
        p=held.path_point(hs,t)
        need(held.point_triangle_squared(p,tri)==p[1]*p[1],'fixed x/z lies in the projected face')
    need(vector(body['velocity'])[0]==held.acceleration(hs)[0]==vector(body['velocity'])[2]==held.acceleration(hs)[2]==0,
         'face feasibility persists for ALL time, not just tested endpoints')
    return {'status':'PASS',**stats,'inputFingerprint':fingerprint,
            'actualBodyBinadeBits':[f'{x:016x}' for x in sorted(binades)],
            'originalPositiveGap':{'numerator':1,'denominator':2**20},
            'scope':'Separate four-input proof: three actual body-centre binades and accepted inflated entry despite strictly separated original sphere. No default100 profile or physical source changed.'}


def verify_nonvacuity(fixtures):
    requirements=[('face',(1,1,1),(0,0,0),(0,0,0)),
                  ('edge',(1,1,-1),(F(1,2),0,0),(0,0,0)),
                  ('vertex',(-1,1,-1),(-F(1,2),0,0),(0,0,0)),
                  ('curvedChordFalseCollision',(-2,F(1,8),1),(8,4,0),(0,-4,0))]
    accepted={}
    for name,p,v,q in requirements:
        count=0
        for fixture in fixtures:
            source=fixture['input'];body=source['body'];h=fraction(source['horizon'])
            if fixture['result']['status']!='certified_separated':continue
            if (h==F(1,16) and vector(body['position'])==tuple(p)
                and held.scale(vector(body['velocity']),h)==tuple(v)
                and held.scale(held.acceleration(held_source(source)),h*h/2)==tuple(q)
                and fraction(body['radius'])==F(1,4)
                and tuple(tuple(vector(x) for x in t['vertices']) for t in source['triangles'])==(((0,0,0),(4,0,0),(0,0,4)),)):
                count+=1
        need(count>0,'required nonvacuous guarded '+name+' family succeeds')
        accepted[name]=count
    rotational=sum(f['result']['status']=='certified_separated' and any(f['input']['body']['torque'])
                   and any(f['input']['body']['angularMomentum']) for f in fixtures)
    need(rotational>0,'at least one actual full candidate with held torque and angular momentum succeeds')
    accepted['nativeFullCandidateWithHeldAngularLoads']=rotational
    return accepted


if __name__=='__main__':
    need(__debug__,'run free-flight reference without Python -O')
    parser=argparse.ArgumentParser();parser.add_argument('fixture');parser.add_argument('--supplemental')
    args=parser.parse_args();report=verify(load(args.fixture))
    if args.supplemental:report['supplemental']=verify_supplemental(load(args.supplemental))
    print(json.dumps(report,indent=2))
