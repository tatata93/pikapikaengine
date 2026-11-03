#!/usr/bin/env python3
"""Fail-closed finite-fixture checker; exact Fraction + Q(sqrt(11)) oracles.

JSON numbers are parsed as binary64 first, then interpreted as exact rationals.
No ordinary-double Fresnel/polarization implementation supplies the oracle.
"""
import argparse
import csv
import hashlib
from fractions import Fraction as F
import json
import math
from pathlib import Path
import struct
import sys

NAMES = ('identity-unpolarized normal-transmit-q-plus normal-transmit-q-minus '
         'normal-transmit-u-plus normal-transmit-u-minus normal-transmit-v-plus '
         'normal-transmit-v-minus normal-transmit-mixed normal-reflect-u '
         'homogeneous-transmit homogeneous-reflect noncoplanar-unpolarized '
         'noncoplanar-u noncoplanar-v two-tir-u two-tir-v invalid-cone uncertain-cone '
         'parallel-reference sqrt-budget low-refinement geometry-miss '
         'tir-transmission-unavailable near-normal-family invalid-later-shape '
         'zero-power index-family full-sphere spherical-cap completed-power-prefix '
         'subnormal-v-transmit subnormal-v-identity').split()

def check(ok, message):
    if not ok:
        raise ValueError(message)

def keys(x, expected):
    check(type(x) is dict and set(x) == set(expected.split()), 'object schema mismatch')

def number(x):
    check(type(x) in (int, float) and math.isfinite(x), 'finite binary64 number required')
    return float(x)

def integer(x, lo, hi):
    check(type(x) is int and lo <= x <= hi, 'integer outside domain')

def bounds(x):
    check(type(x) is list and len(x) == 2, 'interval shape')
    a, b = map(number, x)
    check(a <= b, 'reversed interval')
    return F(a), F(b)

def vec(x, bounded=True):
    check(type(x) is list and len(x) == 3, 'vector shape')
    for v in x:
        bounds(v) if bounded else number(v)

def complex_bounds(x):
    check(type(x) is list and len(x) == 2, 'complex shape')
    bounds(x[0]); bounds(x[1])

def state(x):
    keys(x, 'power diagonal upper')
    lo, hi = bounds(x['power']); check(lo >= 0, 'negative power')
    check(len(x['diagonal']) == len(x['upper']) == 3, 'coherency shape')
    for y in x['diagonal']:
        a, _ = bounds(y); check(a >= 0, 'negative diagonal')
    for y in x['upper']:
        complex_bounds(y)

def schema(row):
    keys(row, 'name input result')
    q, r = row['input'], row['result']
    keys(q, 'origin direction domain index wavelength stokes reference steps settings')
    vec(q['origin']); vec(q['direction']); bounds(q['domain']); bounds(q['index'])
    number(q['wavelength']); vec(q['reference'], False)
    check(len(q['stokes']) == 4 and len(q['settings']) == 5, 'input array shape')
    for n in q['stokes'] + q['settings']:
        number(n)
    check(type(q['steps']) is list and len(q['steps']) <= 64, 'step shape')
    for s in q['steps']:
        integer(s.get('kind'), 0, 2)
        fields = ('center normal aperture' if s['kind'] == 0 else
                  'center radius' if s['kind'] == 1 else 'vertex axis radius aperture')
        keys(s, 'kind branch nextIndex domain ' + fields)
        for k in ('center', 'normal', 'vertex', 'axis'):
            if k in s: vec(s[k], False)
        for k in ('radius', 'aperture'):
            if k in s: number(s[k])
        integer(s['branch'], 0, 1); bounds(s['nextIndex']); bounds(s['domain'])
    keys(r, 'status powerFailure geometryStatus completedPowerSteps failedPowerStep counters limited initial segments completion')
    integer(r['status'], 0, 5); integer(r['powerFailure'], 0, 5); integer(r['geometryStatus'], -1, 7)
    for k in ('completedPowerSteps', 'failedPowerStep'): integer(r[k], 0, 64)
    check(type(r['limited']) is bool and len(r['counters']) == 4, 'counter shape')
    for n in r['counters']: integer(n, 0, 4000000 + 262144)
    if r['initial'] is not None: state(r['initial'])
    check(type(r['segments']) is list and len(r['segments']) <= len(q['steps']), 'segment shape')
    completed = 0
    for j, s in enumerate(r['segments']):
        keys(s, 'ordinal branch exactNormal homogeneous s p state')
        check(s['ordinal'] == j, 'segment ordinal')
        integer(s['branch'], 0, 1)
        check(type(s['exactNormal']) is bool and type(s['homogeneous']) is bool, 'segment flags')
        for k in ('s', 'p'):
            if s[k] is not None: complex_bounds(s[k])
        if s['state'] is not None: state(s['state']); completed += 1
    check(completed == r['completedPowerSteps'], 'completed prefix count')
    check(completed==r['failedPowerStep'] and len(r['segments']) in (completed,completed+1),'failed prefix position')
    check(r['counters'][0]<=64 and r['counters'][1]<=r['counters'][0],'geometry query budget')
    check((r['completion'] is not None) == (r['status'] == 0), 'completion/status mismatch')
    if r['completion'] is not None:
        c = r['completion']; keys(c, 'state origin direction index')
        state(c['state']); vec(c['origin']); vec(c['direction']); bounds(c['index'])
        check(r['geometryStatus'] == 0 and completed == len(q['steps']), 'incomplete success')
        check(bounds(c['state']['power'])[1] <= F(float(q['stokes'][0])), 'passivity')
        check(sum(r['counters'][2:])<=q['settings'][4],'completed over sqrt budget')
        check(bits(c['state'])==bits(r['segments'][-1]['state'] if completed else r['initial']),'completion differs from final prefix')

class A:
    """Exact a+b*sqrt(11)."""
    def __init__(self, a=0, b=0):
        self.a, self.b = F(a), F(b)
    def __add__(self, v):
        v = alg(v); return A(self.a + v.a, self.b + v.b)
    __radd__ = __add__
    def __neg__(self): return A(-self.a, -self.b)
    def __sub__(self, v): return self + -alg(v)
    def __rsub__(self, v): return alg(v) + -self
    def __mul__(self, v):
        v = alg(v); return A(self.a*v.a + 11*self.b*v.b, self.a*v.b + self.b*v.a)
    __rmul__ = __mul__
    def __truediv__(self, v):
        v = alg(v); den = v.a*v.a - 11*v.b*v.b
        check(den != 0, 'oracle zero division')
        return self * A(v.a/den, -v.b/den)
    def enclosure(self):
        a, b = self.a + self.b*SQRT11[0], self.a + self.b*SQRT11[1]
        return min(a,b), max(a,b)

def alg(v): return v if isinstance(v, A) else A(v)
def z(a=0, b=0): return alg(a), alg(b)
def za(a,b): return a[0]+b[0], a[1]+b[1]
def zm(a,b): return a[0]*b[0]-a[1]*b[1], a[0]*b[1]+a[1]*b[0]
def zc(a): return a[0], -a[1]
def zs(a,b): return a[0]*b, a[1]*b
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def frame_c(first, second, stokes):
    i,q,u,v = map(F,stokes)
    return [[z((i+q)/2*first[j]*first[k]+(i-q)/2*second[j]*second[k]+u/2*(first[j]*second[k]+second[j]*first[k]),v/2*(first[j]*second[k]-second[j]*first[k])) for k in range(3)] for j in range(3)]
def jones(s, pi, po, rs, rp):
    return [[za(zs(rs,s[j]*s[k]),zs(rp,po[j]*pi[k])) for k in range(3)] for j in range(3)]
def mm(a,b):
    return [[sumz(zm(a[j][k],b[k][l]) for k in range(3)) for l in range(3)] for j in range(3)]
def sumz(xs):
    out=z()
    for x in xs: out=za(out,x)
    return out
def transport(c,j): return mm(mm(j,c),[[zc(j[k][l]) for k in range(3)] for l in range(3)])
def rational_oracle(stokes):
    d0=[F(0),F(0),F(1)];s1=[F(0),F(-1),F(0)];p0=cross(d0,s1)
    d1=[F(24,25),F(0),F(-7,25)];n2=[F(-543,625),F(300,625),F(-76,625)]
    s2=[v/F(3,5) for v in cross(n2,d1)];p1=cross(d1,s1);p2i=cross(d1,s2)
    d2=[F(-1344,3125),F(96,125),F(-1483,3125)];p2o=cross(d2,s2)
    c=frame_c(s1,p0,stokes);rs=z(F(-2,7));rp=z(F(22,147))
    return transport(transport(c,jones(s1,p0,p1,rs,rp)),jones(s2,p2i,p2o,rs,rp))
def tir_oracle(stokes):
    d0=[F(4,5),F(-3,5),F(0)];s1=[F(0),F(0),F(-1)];p0=cross(d0,s1)
    d1=[F(4,5),F(3,5),F(0)];p1=cross(d1,s1);s2=[F(-12,25),F(16,25),F(-15,25)]
    p2i=cross(d1,s2);p2o=[F(-543,625),F(-276,625),F(140,625)]
    def phase(a,b):
        den=a*a+b*b
        return (a*a-b*b)/den, -2*a*b/den
    rs=phase(A(F(9,10)),A(0,F(1,5)));rp=phase(A(F(3,5)),A(0,F(3,10)))
    c=frame_c(s1,p0,stokes)
    return transport(transport(c,jones(s1,p0,p1,rs,rp)),jones(s2,p2i,p2o,rs,rp)),s2,p2o

# A libm estimate only locates adjacent doubles; exact rational squares prove
# the bracket. The oracle never assumes correctly rounded sqrt.
near=math.sqrt(11); low=math.nextafter(near,-math.inf); high=math.nextafter(near,math.inf)
check(F(low)**2 < 11 < F(high)**2,'sqrt11 rational bracket')
SQRT11=F(low),F(high)
INCLUSIONS=0
def contains(bound, value):
    global INCLUSIONS
    lo,hi=bounds(bound);a,b=alg(value).enclosure()
    check(lo<=a and b<=hi,'independent algebraic value absent from output enclosure')
    INCLUSIONS+=1

def verify_c(output, oracle):
    for j in range(3): contains(output['diagonal'][j], oracle[j][j][0])
    for out,(j,k) in zip(output['upper'],((0,1),(0,2),(1,2))):
        contains(out[0],oracle[j][k][0]);contains(out[1],oracle[j][k][1])
    contains(output['power'],sum(oracle[k][k][0] for k in range(3)))

def load(path):
    def pairs(items):
        d={}
        for k,v in items:
            check(k not in d,'duplicate JSON key');d[k]=v
        return d
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    keys(data,'schema fixtures');check(data['schema']==1,'schema version')
    rows=data['fixtures'];check(type(rows) is list and len(rows)==len(NAMES),'fixture count')
    check([r.get('name') for r in rows]==NAMES,'fixture identities/order')
    for row in rows: schema(row)
    # Fix this declared acceptance corpus' entire binary64 input, not just its
    # labels; a changed surface/index/reference cannot reuse the old oracle.
    packet=bits([{'name':r['name'],'input':r['input']} for r in rows])
    digest=hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(',',':'),default=lambda x:x.hex()).encode()).hexdigest()
    check(digest=='5e45810c35705efa4250911af3bcbb9e47929c617894a17633f1778d8201b33a','fixture exact binary64 inputs changed')
    return rows

def verify(rows):
    by={r['name']:r for r in rows}
    expected={n:0 for n in NAMES}
    for n in ('invalid-cone','invalid-later-shape'):expected[n]=3
    for n in ('uncertain-cone','parallel-reference','near-normal-family'):expected[n]=2
    for n in ('geometry-miss','tir-transmission-unavailable','completed-power-prefix'):expected[n]=1
    expected['sqrt-budget']=4
    for n,row in by.items():
        r=row['result'];check(r['status']==expected[n],n+': classification')
        check(r['powerFailure']=={'uncertain-cone':1,'parallel-reference':2,'near-normal-family':3}.get(n,0),n+': failure reason')
        check(r['geometryStatus']==(-1 if n in ('invalid-cone','invalid-later-shape') else 1 if n in ('geometry-miss','completed-power-prefix') else 4 if n=='tir-transmission-unavailable' else 0),n+': geometry reason')
        if r['initial'] is not None:contains(r['initial']['power'],F(float(row['input']['stokes'][0])))
        if r['status']!=0:continue
        if n.startswith('noncoplanar') or n in ('low-refinement','index-family'):
            oracle=rational_oracle(row['input']['stokes'])
        elif n.startswith('two-tir'):
            oracle,s,p=tir_oracle(row['input']['stokes'])
            if n=='two-tir-u':
                ss=sumz(zs(oracle[j][k],s[j]*s[k]) for j in range(3) for k in range(3))[0]
                pp=sumz(zs(oracle[j][k],p[j]*p[k]) for j in range(3) for k in range(3))[0]
                sp=sumz(zs(oracle[j][k],s[j]*p[k]) for j in range(3) for k in range(3))
                for got,want in ((ss+pp,A(1)),(ss-pp,A(F(424,625))),(2*sp[0],A(F(-10007,15625))),(2*sp[1],A(0,F(1696,15625)))):
                    check(got.a==want.a and got.b==want.b,'independent two-TIR local Stokes derivation')
        else:
            oracle=frame_c([F(1),F(0),F(0)],[F(0),F(1),F(0)],row['input']['stokes'])
            factor=F(1) if n in ('identity-unpolarized','homogeneous-transmit','subnormal-v-identity') else F(0) if n in ('zero-power','homogeneous-reflect') else F(1,25) if n=='normal-reflect-u' else F(24,25)
            oracle=[[zs(x,factor) for x in a] for a in oracle]
        verify_c(r['completion']['state'],oracle)
    exact=F(42544,17294403);wrong=F(1263376,466948881)
    check(exact!=wrong,'reset negative control')
    lo,hi=bounds(by['noncoplanar-unpolarized']['result']['completion']['state']['power'])
    check(not(lo<=wrong<=hi),'incorrect per-surface reset power was not excluded')
    contains(by['noncoplanar-unpolarized']['result']['completion']['state']['power'],exact)
    contains(by['noncoplanar-u']['result']['completion']['state']['power'],F(322768,259416045))
    check(by['low-refinement']['result']['limited'],'refinement diagnostic lost')
    check(by['completed-power-prefix']['result']['completedPowerSteps']==1,'power prefix lost')

def bits(x):
    if type(x) in (float,int):return ('n',struct.pack('>d',float(x)))
    if type(x) is list:return [bits(v) for v in x]
    if type(x) is dict:return {k:bits(v) for k,v in x.items()}
    return x

ORACLE_HEADER=('id,I,Q,U,V,frame,powerLo,powerHi,xxLo,xxHi,yyLo,yyHi,zzLo,zzHi,'
               'xyReLo,xyReHi,xyImLo,xyImHi,xzReLo,xzReHi,xzImLo,xzImHi,yzReLo,yzReHi,yzImLo,yzImHi').split(',')
def corpus(path):
    with open(path,encoding='utf-8-sig',newline='') as stream: rows=list(csv.reader(stream))
    check(len(rows)==129 and rows[0]==ORACLE_HEADER,'oracle header/count')
    output=[]
    for j,row in enumerate(rows[1:]):
        check(len(row)==26 and row[0]==str(j) and row[5]==str(j%2),'oracle identity/row shape')
        numbers=[]
        for text in row[1:5]+row[6:]:
            check(text.lower().startswith(('0x','-0x')),'oracle requires hexadecimal binary64')
            x=float.fromhex(text);check(math.isfinite(x),'nonfinite oracle binary64');numbers.append(x)
        s=[F(1)+F(j,128),F(j%7-3,16),F(j%5-2,16),F(j%3-1,16)]
        check(list(map(F,numbers[:4]))==s,'oracle input changed')
        first,second=([F(0),F(0),F(1)],[F(4,5),F(-3,5),F(0)]) if j%2 else ([F(1),F(0),F(0)],[F(0),F(1),F(0)])
        m=frame_c(first,second,s);v=numbers[4:]
        st={'power':v[:2],'diagonal':[v[2:4],v[4:6],v[6:8]],'upper':[[v[8:10],v[10:12]],[v[12:14],v[14:16]],[v[16:18],v[18:20]]]}
        state(st);verify_c(st,m);output.append(numbers)
    return output

def main():
    check(__debug__,'Python -O is unsupported: fail closed')
    parser=argparse.ArgumentParser();parser.add_argument('native');parser.add_argument('wasm',nargs='?');parser.add_argument('--oracle');parser.add_argument('--wasm-oracle');args=parser.parse_args()
    rows=load(args.native);verify(rows)
    matched=False
    if args.wasm:
        other=load(args.wasm);verify(other);check(bits(rows)==bits(other),'Native/WASM fixture binary64 bits differ');matched=True
    oracle_rows=0
    if args.oracle:
        o=corpus(args.oracle);oracle_rows=len(o)
        if args.wasm_oracle:check(bits(o)==bits(corpus(args.wasm_oracle)),'Native/WASM oracle binary64 bits differ')
    else:check(not args.wasm_oracle,'--wasm-oracle needs --oracle')
    print(json.dumps({'status':'PASS','fixtures':len(rows),'oracleRows':oracle_rows,'independentInclusions':INCLUSIONS,'wasmBitsMatch':matched,'sqrt11BracketProvedByFractionSquares':True,'resetNegativeControlExcluded':True}))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('FAIL: '+str(error),file=sys.stderr);sys.exit(1)
