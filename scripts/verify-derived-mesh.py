#!/usr/bin/env python3
"""Independent finite-corpus Float32 geometry and normal certification audit.

All binary64 inputs/endpoints and decoded binary32 outputs denote exact real
rationals. Round-to-nearest-even is implemented with integer division; no host
float32 conversion is an oracle. Oriented c/sqrt(Q) containment/error is proved
by signed rational square inequalities, without relying on libm sqrt accuracy.
Only local quantized triangles are covered, not GPU/world/clip computations.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

STATUSES = ('completed','invalid_input','budget_exceeded','degenerate',
            'quality_rejected','quality_unresolved','numerical_failure','unsupported_environment')
REASONS = ('none','settings','vertex_count','triangle_count','position_domain',
           'index_range','duplicate_index','vertex_budget','triangle_budget',
           'zero_cross','below_area_floor','cross_uncertain','area_uncertain',
           'normal_uncertain','nonfinite_intermediate','allocation_failure','environment')
FLOOR = F(1e-24)
NORMAL_TOLERANCE = F(1e-6)
# Fixed Native cases are classified by independent analytic/input witnesses.
# No trust-on-first-use/bless option is provided.
EXPECTED = {
 'xy-unit':('completed','none'),
 'rational-345':('completed','none'),
 'reverse-winding':('completed','none'),
 'rigid-180-x':('completed','none'),
 'affine-shear':('completed','none'),
 'signed-zero':('completed','none'),
 'subnormal-component':('completed','none'),
 'float32-subnormal-component':('completed','none'),
 'tie-even-low':('completed','none'),
 'tie-even-high':('completed','none'),
 'tie-next-up':('completed','none'),
 'two-face-square':('completed','none'),
 'large-offset-collapse':('degenerate','zero_cross'),
 'lbs-half-turn-collapse':('degenerate','zero_cross'),
 'exact-axis-collinear':('degenerate','zero_cross'),
 'area-below-floor':('quality_rejected','below_area_floor'),
 'floor-nearest-below':('quality_rejected','below_area_floor'),
 'floor-next-above':('completed','none'),
 'collinear-uncertain':('quality_unresolved','cross_uncertain'),
 'area-threshold-uncertain':('quality_unresolved','area_uncertain'),
 'sqrt-budget-unresolved':('quality_unresolved','normal_uncertain'),
 'sqrt-budget-maximum':('completed','none'),
 'coordinate-boundary':('completed','none'),
 'coordinate-overflow':('invalid_input','position_domain'),
 'finite-unrenderable-deformation':('invalid_input','position_domain'),
 'index-outside':('invalid_input','index_range'),
 'duplicate-index':('invalid_input','duplicate_index'),
 'second-invalid-preflight':('invalid_input','index_range'),
 'second-degenerate-no-buffer':('degenerate','zero_cross'),
 'no-vertices':('invalid_input','vertex_count'),
 'no-faces':('invalid_input','triangle_count'),
 'vertex-budget':('budget_exceeded','vertex_budget'),
 'face-budget':('budget_exceeded','triangle_budget'),
 'bad-vertex-setting-low':('invalid_input','settings'),
 'bad-vertex-setting-high':('invalid_input','settings'),
 'bad-triangle-setting-low':('invalid_input','settings'),
 'bad-triangle-setting-high':('invalid_input','settings'),
 'bad-sqrt-setting-low':('invalid_input','settings'),
 'bad-sqrt-setting-high':('invalid_input','settings'),
 'hard-budget-settings':('completed','none'),
}
INPUT_SHA256 = '79dbd0bfcf873a4044cd1e3db4d8e858dd5cae35056bb2da6256905e0586da4c'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def keys(x, names, label):
    require(type(x) is dict and set(x) == set(names.split()), label+' fields')

def number(x):
    require(type(x) in (int,float), 'finite binary64 number required')
    require(math.isfinite(x), 'finite binary64 number required')
    return float(x)

def integer(x, lo, hi, label):
    require(type(x) is int and lo <= x <= hi, label+' integer range/type')
    return x

def array(x, n, label, exact=False):
    require(type(x) is list and (len(x) == n if exact else len(x) <= n), label+' array width/count')

def finite_vector(x, n, label):
    array(x,n,label,True)
    for value in x: number(value)

def fraction(x):
    return F(number(x))

def interval(x):
    finite_vector(x,2,'interval'); lo,hi = map(fraction,x)
    require(lo <= hi, 'reversed interval')
    return lo,hi

def f64hex(x):
    return struct.pack('>d',number(x)).hex()

def pow2(exponent):
    return F(2**exponent) if exponent >= 0 else F(1,2**(-exponent))

def f32_fraction(bits):
    integer(bits,0,0xffffffff,'binary32 bits')
    sign = -1 if bits >> 31 else 1
    exponent,part = (bits >> 23) & 255,bits & 0x7fffff
    require(exponent != 255,'nonfinite binary32 output')
    return sign*F(part if exponent == 0 else part+(1 << 23))*pow2(-149 if exponent == 0 else exponent-150)

def nearest_even_integer(value):
    quotient,remainder = divmod(value.numerator,value.denominator)
    return quotient+int(2*remainder > value.denominator or
                        (2*remainder == value.denominator and quotient % 2 == 1))

def rounded_f32_bits(value):
    value = number(value)
    sign = int(struct.pack('>d',value)[0] >> 7) << 31
    exact = abs(F(value))
    if not exact: return sign
    exponent = exact.numerator.bit_length()-exact.denominator.bit_length()
    if exact < pow2(exponent): exponent -= 1
    if exponent < -126:
        rounded = nearest_even_integer(exact/pow2(-149))
        require(rounded <= 1 << 23,'subnormal conversion carry')
        return sign | rounded
    significand = nearest_even_integer(exact/pow2(exponent-23))
    if significand == 1 << 24:
        significand >>= 1; exponent += 1
    if exponent > 127: return sign | 0x7f800000
    require((1 << 23) <= significand < (1 << 24),'normal conversion significand')
    return sign | ((exponent+127) << 23) | (significand-(1 << 23))

def cross(a,b,c):
    u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
    return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]

def normal_contains(component, squared, lower, upper):
    """Prove lower <= component/sqrt(squared) <= upper without a sqrt call."""
    require(squared > 0 and lower <= upper,'normalized proof domain')
    if component < 0:
        return normal_contains(-component,squared,-upper,-lower)
    if component == 0:
        return lower <= 0 <= upper
    if upper <= 0: return False
    # For positive component, squaring preserves the relevant inequalities.
    return component*component <= upper*upper*squared and (
        lower <= 0 or lower*lower*squared <= component*component)

def pairs(items):
    out={}
    for key,value in items:
        require(key not in out,'duplicate JSON key');out[key]=value
    return out

def loads(text):
    def constant(token): raise ValueError('nonfinite JSON constant '+token)
    def decimal(token):
        value=float(token)
        require(math.isfinite(value),'nonfinite JSON decimal')
        mantissa=token.lower().split('e',1)[0]
        require(value!=0 or not any(c in '123456789' for c in mantissa),
                'nonzero JSON decimal underflow')
        return value
    return json.loads(text,object_pairs_hook=pairs,parse_int=lambda s:-0.0 if s == '-0' else int(s),
                      parse_float=decimal,parse_constant=constant)

def read(path):
    path=Path(path);require(path.stat().st_size <= 128*1024*1024,'fixture file byte budget')
    return loads(path.read_text(encoding='utf-8-sig'))

def input_fingerprint(rows):
    packet=[{'name':row['name'],'input':{
        'positions':[[f64hex(v) for v in p] for p in row['input']['positions']],
        'triangles':row['input']['triangles'],'settings':row['input']['settings']}}
        for row in rows]
    return hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def schema(row):
    keys(row,'name input result','fixture');require(type(row['name']) is str,'fixture name')
    q,r=row['input'],row['result'];keys(q,'positions triangles settings','input')
    array(q['positions'],65537,'input positions');array(q['triangles'],131073,'input triangles')
    for p in q['positions']: finite_vector(p,3,'input position')
    for t in q['triangles']:
        array(t,3,'input triangle',True)
        for j in t: integer(j,0,0xffffffff,'input index')
    array(q['settings'],3,'settings',True)
    for j in q['settings']: integer(j,0,2**64-1,'setting')
    keys(r,'status reason failedVertex failedFace positionsBits triangles interleavedBits minimumBits maximumBits audits sqrtRefinements sqrtLimitedFaces','result')
    integer(r['status'],0,len(STATUSES)-1,'status');integer(r['reason'],0,len(REASONS)-1,'reason')
    for key,length in [('failedVertex',len(q['positions'])),('failedFace',len(q['triangles']))]:
        if r[key] is not None:
            require(length>0,key+' has no source item');integer(r[key],0,length-1,key)
    integer(r['sqrtRefinements'],0,2**53-1,'sqrt count');integer(r['sqrtLimitedFaces'],0,len(q['triangles']),'sqrt limited faces')
    array(r['audits'],len(q['triangles']),'audits')
    for j,a in enumerate(r['audits']):
        keys(a,'face cross squaredCross normalized normalBits normalError sqrtRefinements sqrtRefinementLimited','face audit')
        integer(a['face'],0,max(0,len(q['triangles'])-1),'audit face');require(a['face']==j,'audit prefix/order')
        array(a['cross'],3,'cross',True)
        for x in a['cross']: interval(x)
        interval(a['squaredCross'])
        if a['normalized'] is not None:
            array(a['normalized'],3,'normalized',True)
            for x in a['normalized']: interval(x)
        if a['normalBits'] is not None:
            array(a['normalBits'],3,'normal bits',True)
            for x in a['normalBits']: f32_fraction(x)
        if a['normalError'] is not None:
            finite_vector(a['normalError'],3,'normal error')
            require(all(x >= 0 for x in a['normalError']),'negative normal error')
        integer(a['sqrtRefinements'],0,512,'face sqrt count')
        require(type(a['sqrtRefinementLimited']) is bool,'sqrt limited flag')
    fields=('positionsBits','triangles','interleavedBits','minimumBits','maximumBits')
    if r['status'] != 0:
        require(all(r[k] is None for k in fields),'failure has no partial buffer')
        require(r['reason'] != 0,'failure requires reason')
    else:
        require(all(r[k] is not None for k in fields),'completed buffer fields missing')
        require(r['reason']==0 and r['failedVertex'] is None and r['failedFace'] is None,'completed failure metadata')
        array(r['positionsBits'],len(q['positions']),'indexed output',True)
        for p in r['positionsBits']:
            array(p,3,'position bits',True)
            for v in p:f32_fraction(v)
        array(r['triangles'],len(q['triangles']),'output triangles',True)
        for t in r['triangles']:
            array(t,3,'output triangle',True)
            for j in t:integer(j,0,len(q['positions'])-1,'output index')
        require(r['triangles']==q['triangles'],'triangle index/order changed')
        array(r['interleavedBits'],len(q['triangles'])*18,'expanded output',True)
        for v in r['interleavedBits']:f32_fraction(v)
        for key in ('minimumBits','maximumBits'):
            array(r[key],3,key,True)
            for v in r[key]:f32_fraction(v)
        require(len(r['audits'])==len(q['triangles']),'completed all-face audits')

def load(path):
    data=read(path);keys(data,'schema fixtures','root');require(type(data['schema']) is int and data['schema']==1,'schema version')
    rows=data['fixtures'];array(rows,len(EXPECTED),'fixtures',True)
    require([r.get('name') if type(r) is dict else None for r in rows]==list(EXPECTED),'fixed fixture names/count/order')
    for row in rows:schema(row)
    require(input_fingerprint(rows)==INPUT_SHA256,'fixed original binary64 input fingerprint')
    return rows

def preflight(q):
    nv,nt=len(q['positions']),len(q['triangles']);mv,mt,sqrt=q['settings']
    if not(3<=mv<=65536 and 1<=mt<=131072 and 1<=sqrt<=256):return 'settings'
    if nv<3:return 'vertex_count'
    if nt<1:return 'triangle_count'
    if nv>mv:return 'vertex_budget'
    if nt>mt:return 'triangle_budget'
    for p in q['positions']:
        if any(abs(v)>1e6 for v in p):return 'position_domain'
    for t in q['triangles']:
        if any(j>=nv for j in t):return 'index_range'
        if len(set(t))!=3:return 'duplicate_index'
    return None

def verify(rows):
    report={'fixtures':len(rows),'completed':0,'expectedFailures':0,'quantizedComponents':0,'faceAudits':0,
            'crossContainments':0,'squaredContainments':0,'normalizedContainments':0,'normalErrorBounds':0,
            'completedFaces':0,'completedNormalComponents':0,'certifiedPrefixFaces':0,'certifiedPrefixNormalComponents':0,
            'expandedComponents':0,'maximumReportedNormalError':0.0,'maximumCertifiedNormalError':0.0}
    for row in rows:
        name,q,r=row['name'],row['input'],row['result'];status,reason=STATUSES[r['status']],REASONS[r['reason']]
        require((status,reason)==EXPECTED[name],name+': fixed independent expected status/reason')
        before=preflight(q)
        if before is not None:
            require(reason==before,name+': independent preflight witness');require(not r['audits'],name+': preflight cannot publish geometry audits')
            require(r['sqrtRefinements']==r['sqrtLimitedFaces']==0,name+': preflight sqrt counters')
            if before=='position_domain':
                first=next(j for j,p in enumerate(q['positions']) if any(abs(v)>1e6 for v in p))
                require(r['failedVertex']==first and r['failedFace'] is None,name+': first invalid vertex')
            elif before in ('index_range','duplicate_index'):
                first=next(j for j,t in enumerate(q['triangles']) if (any(i>=len(q['positions']) for i in t) if before=='index_range' else len(set(t))!=3))
                require(r['failedFace']==first and r['failedVertex'] is None,name+': first invalid face')
            else:require(r['failedFace'] is None and r['failedVertex'] is None,name+': count/settings failure metadata')
            report['expectedFailures']+=1;continue
        else:
            require(status not in ('invalid_input','budget_exceeded'),name+': unexpected preflight failure')
        if status in ('degenerate','quality_rejected','quality_unresolved'):
            require(r['failedFace'] is not None and r['failedVertex'] is None and len(r['audits'])==r['failedFace']+1,name+': failed face audit prefix missing')
        positions=[[f32_fraction(rounded_f32_bits(v)) for v in p] for p in q['positions']]
        require(r['sqrtRefinements']==sum(a['sqrtRefinements'] for a in r['audits']),name+': total sqrt count')
        require(r['sqrtLimitedFaces']==sum(a['sqrtRefinementLimited'] for a in r['audits']),name+': total limited-face count')
        for a in r['audits']:
            face=a['face'];t=q['triangles'][face];require(all(j<len(positions) for j in t) and len(set(t))==3,'audit source indices')
            c=cross(*(positions[j] for j in t));squared=sum(v*v for v in c)
            cb=[interval(v) for v in a['cross']];qb=interval(a['squaredCross'])
            require(all(lo<=v<=hi for v,(lo,hi) in zip(c,cb)),name+': exact rounded cross containment')
            require(qb[0]<=squared<=qb[1],name+': exact squared cross containment')
            report['faceAudits']+=1;report['crossContainments']+=3;report['squaredContainments']+=1
            if a['normalized'] is not None:
                require(squared>0,name+': zero normalized domain')
                for component,bound in zip(c,a['normalized']):
                    require(normal_contains(component,squared,*interval(bound)),name+': exact oriented unit normal containment');report['normalizedContainments']+=1
            if a['normalError'] is not None:
                require(a['normalBits'] is not None and a['normalized'] is not None,name+': optional normal evidence')
                for component,bits,error in zip(c,a['normalBits'],a['normalError']):
                    n,e=f32_fraction(bits),fraction(error)
                    require(normal_contains(component,squared,n-e,n+e),name+': claimed candidate normal error bound');report['normalErrorBounds']+=1
                    report['maximumReportedNormalError']=max(report['maximumReportedNormalError'],error)
            # sqrt(Q interval) separately refines its lower/upper endpoints.
            require(a['sqrtRefinements']<=2*q['settings'][2],name+': per-endpoint sqrt budget')
            if status=='completed' or (r['failedFace'] is not None and face<r['failedFace']):
                require(any(lo>0 or hi<0 for lo,hi in cb),name+': strict cross component proof')
                require(qb[0]>FLOOR,name+': strict squared-area floor proof')
                require(a['normalized'] is not None and a['normalBits'] is not None and a['normalError'] is not None,name+': completed normal evidence missing')
                require(all(fraction(error)<=NORMAL_TOLERANCE for error in a['normalError']),name+': candidate error exceeds fixed tolerance')
                report['maximumCertifiedNormalError']=max(report['maximumCertifiedNormalError'],*a['normalError'])
                category='completed' if status=='completed' else 'certifiedPrefix'
                report[category+'Faces']+=1;report[category+'NormalComponents']+=3
            if face==r['failedFace']:
                if reason=='zero_cross':require(all(v==0 for v in c) and all(lo==hi==0 for lo,hi in cb),name+': exact degenerate witness')
                if reason=='below_area_floor':require(qb[1]<=FLOOR and squared<=FLOOR,name+': rejected floor witness')
                if reason=='cross_uncertain':require(all(lo<=0<=hi for lo,hi in cb),name+': unresolved cross witness')
                if reason=='area_uncertain':require(qb[0]<=FLOOR<qb[1],name+': unresolved floor witness')
                if reason=='normal_uncertain':require(a['normalError'] is None or any(fraction(e)>NORMAL_TOLERANCE for e in a['normalError']),name+': unresolved normal witness')
        if status!='completed':report['expectedFailures']+=1;continue
        report['completed']+=1
        expected=[[rounded_f32_bits(v) for v in p] for p in q['positions']]
        require(r['positionsBits']==expected,name+': independent nearest-even position bits');report['quantizedComponents']+=3*len(expected)
        expanded=[]
        for triangle,a in zip(q['triangles'],r['audits']):
            for j in triangle:expanded+=expected[j]+a['normalBits']
        require(r['interleavedBits']==expanded,name+': expanded candidate/position bits and order');report['expandedComponents']+=len(expanded)
        for axis in range(3):
            values=[p[axis] for p in positions]
            for field,value in [('minimumBits',min(values)),('maximumBits',max(values))]:
                require(f32_fraction(r[field][axis])==value and r[field][axis] in [p[axis] for p in expected],name+': exact indexed bounds')
    require(report['completed']>0 and report['expectedFailures']>0,'positive and negative corpus coverage')
    return report

def main():
    require(__debug__,'Python -O is unsupported')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('native');args=parser.parse_args()
    rows=load(args.native);report=verify(rows)
    report.update(status='PASS',inputSHA256=INPUT_SHA256,floorBinary64=f64hex(1e-24),normalToleranceBinary64=f64hex(1e-6),
                  proof='Exact rational f32 quantization/cross/Q; signed-square inequalities for oriented unit normals and candidate errors.',
                  counterScope='normalErrorBounds includes failed candidates; completedNormalComponents and certifiedPrefixNormalComponents identify tolerance-certified components separately.',
                  scope='Native fixed corpus; no GPU/world/clip or continuous-surface guarantee. Expected failures are not successful buffers.')
    print(json.dumps(report,indent=2,allow_nan=False))

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OverflowError,OSError,json.JSONDecodeError) as error:
        print('FAIL '+str(error),file=sys.stderr);sys.exit(1)
