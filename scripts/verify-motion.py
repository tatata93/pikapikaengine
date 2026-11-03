#!/usr/bin/env python3
"""Fail-closed point-motion acceptance, independent Fraction affine oracle.

This checks bounded point errors; unlike the optical kernels this API does not
claim exact-real interval containment. JSON means exact input binary64 values.
"""
import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

NAMES=('rest two-link permuted-tree shear linear-start linear-quarter linear-mid '
       'linear-terminal clamp-after loop-duration loop-multiple loop-offset '
       'loop-huge-clock hold-before hold-after exact-first-key single-key '
       'step-before step-boundary step-after antipodal-mid antipodal-terminal '
       'huge-quaternion subnormal-quaternion subnormal-duration missing-track-rest '
       'maximum-id duplicate-id zero-id unsafe-id missing-parent multiple-roots '
       'disconnected-cycle self-cycle unknown-track duplicate-track empty-track '
       'duplicate-time descending-time outside-time zero-quaternion negative-scale '
       'zero-scale outside-position outside-quaternion zero-duration negative-sample '
       'invalid-mode invalid-interpolation invalid-budget bone-budget track-budget '
       'key-budget empty-tree world-overflow branching-order').split()
MAX_ID=9007199254740991
TOLERANCE=F(256,2**52)
CHECKS=0
MAX_ABS=F(0)
MAX_SCALED=F(0)

def check(ok,message):
    if not ok:raise ValueError(message)
def keys(x,names):check(type(x) is dict and set(x)==set(names.split()),'object schema mismatch')
def number(x):
    check(type(x) in (int,float) and math.isfinite(x),'finite binary64 number required')
    return float(x)
def integer(x,lo,hi):check(type(x) is int and lo<=x<=hi,'integer outside domain')
def vector(x,count=3):
    check(type(x) is list and len(x)==count,'vector width')
    for v in x:number(v)
def transform(x):
    keys(x,'position rotation scale');vector(x['position']);vector(x['rotation'],4);vector(x['scale'])
def bits(x):
    if type(x) in (int,float):return ('n',struct.pack('>d',float(x)))
    if type(x) is list:return [bits(v) for v in x]
    if type(x) is dict:return {k:bits(v) for k,v in x.items()}
    return x
def schema(row):
    keys(row,'name input result');q,r=row['input'],row['result']
    keys(q,'bones tracks duration time mode settings')
    check(type(q['bones']) is list and len(q['bones'])<=128,'source bone shape')
    for b in q['bones']:
        keys(b,'id parentId rest');integer(b['id'],0,MAX_ID+1);integer(b['parentId'],0,MAX_ID+1);transform(b['rest'])
    check(type(q['tracks']) is list and len(q['tracks'])<=128,'source track shape')
    for t in q['tracks']:
        keys(t,'boneId interpolation keys');integer(t['boneId'],0,MAX_ID+1);integer(t['interpolation'],0,9)
        check(type(t['keys']) is list and len(t['keys'])<=4096,'source key shape')
        for k in t['keys']:keys(k,'time pose');number(k['time']);transform(k['pose'])
    number(q['duration']);number(q['time']);integer(q['mode'],0,9)
    check(type(q['settings']) is list and len(q['settings'])==3,'settings shape')
    for x in q['settings']:integer(x,0,4096)
    keys(r,'status pose');integer(r['status'],0,3)
    check((r['pose'] is not None)==(r['status']==0),'completion/status mismatch')
    if r['pose'] is not None:
        p=r['pose'];keys(p,'requestedTime sampledTime evaluationOrder bones');number(p['requestedTime']);number(p['sampledTime'])
        check(bits(p['requestedTime'])==bits(q['time']),'requested clock changed')
        check(type(p['evaluationOrder']) is list and type(p['bones']) is list and len(p['evaluationOrder'])==len(p['bones'])==len(q['bones']),'pose array width')
        check(len(set(p['evaluationOrder']))==len(p['evaluationOrder']),'duplicate evaluation ID')
        for v in p['evaluationOrder']:integer(v,1,MAX_ID)
        for j,b in enumerate(p['bones']):
            keys(b,'id parentId local localMatrix worldMatrix');integer(b['id'],1,MAX_ID);integer(b['parentId'],0,MAX_ID);transform(b['local']);vector(b['localMatrix'],16);vector(b['worldMatrix'],16)
            check(b['id']==q['bones'][j]['id'] and b['parentId']==q['bones'][j]['parentId'],'stable source order/IDs changed')
            for m in (b['localMatrix'],b['worldMatrix']):check([m[k] for k in (3,7,11,15)]==[0,0,0,1],'affine homogeneous row changed')

def load(path):
    def pairs(items):
        out={}
        for k,v in items:check(k not in out,'duplicate JSON key');out[k]=v
        return out
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs,
                    parse_int=lambda token:-0.0 if token=='-0' else int(token),
                    parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
    keys(data,'schema fixtures');check(data['schema']==1,'schema version');rows=data['fixtures']
    check(type(rows) is list and len(rows)==len(NAMES) and [r.get('name') for r in rows]==NAMES,'fixture identity/count/order')
    for r in rows:schema(r)
    packet=bits([{'name':r['name'],'input':r['input']} for r in rows])
    digest=hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(',',':'),default=lambda x:x.hex()).encode()).hexdigest()
    check(digest==INPUT_SHA,'fixed corpus binary64 inputs changed')
    return rows

INPUT_SHA='5bad6c08fa0eb0e11d7f7b8f1b2bc5edd5af6e0f8a435eaeaff4c54a8fafbdd7'

def fvec(v):return list(map(lambda x:F(float(x)),v))
def mm(a,b):
    # Independent row-major Fraction derivation; public output is column-major.
    return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]
def flatten(m):return [m[r][c] for c in range(4) for r in range(4)]
def matrix(t,q,s):
    x,y,z,w=q;n=sum(v*v for v in q);check(n>0,'oracle zero orientation')
    r=[[(n-2*(y*y+z*z))/n,2*(x*y-w*z)/n,2*(x*z+w*y)/n],
       [2*(x*y+w*z)/n,(n-2*(x*x+z*z))/n,2*(y*z-w*x)/n],
       [2*(x*z-w*y)/n,2*(y*z+w*x)/n,(n-2*(x*x+y*y))/n]]
    return [[r[j][k]*s[k] for k in range(3)]+[t[j]] for j in range(3)]+[[F(0),F(0),F(0),F(1)]]
def perfect_sqrt(v):
    n,d=math.isqrt(v.numerator),math.isqrt(v.denominator)
    return F(n,d) if n*n==v.numerator and d*d==v.denominator else None
def proportional(a,b):return all(a[j]*b[k]==a[k]*b[j] for j in range(4) for k in range(4))
def decimal(v):return Decimal(v.numerator)/Decimal(v.denominator)
def q_unit_decimal(q):
    d=list(map(decimal,q));norm=sum(v*v for v in d).sqrt();return [v/norm for v in d]
def local_ref(rest,track,time):
    if track is None:
        t,q,s=fvec(rest['position']),fvec(rest['rotation']),fvec(rest['scale'])
        return t,q,s,q_unit_decimal(q)
    ks=track['keys'];left=right=ks[0]
    if time>=F(float(ks[-1]['time'])):left=right=ks[-1]
    elif time>F(float(ks[0]['time'])):
        for j in range(1,len(ks)):
            kt=F(float(ks[j]['time']))
            if time<kt:left,right=ks[j-1],ks[j];break
            if time==kt:left=right=ks[j];break
    a,b=left['pose'],right['pose']
    if left is right or track['interpolation']==1:
        t,q,s=fvec(a['position']),fvec(a['rotation']),fvec(a['scale'])
        return t,q,s,q_unit_decimal(q)
    alpha=(time-F(float(left['time'])))/(F(float(right['time']))-F(float(left['time'])))
    t=[(1-alpha)*x+alpha*y for x,y in zip(fvec(a['position']),fvec(b['position']))]
    s=[(1-alpha)*x+alpha*y for x,y in zip(fvec(a['scale']),fvec(b['scale']))]
    q0,q1=fvec(a['rotation']),fvec(b['rotation']);sign=-1 if sum(x*y for x,y in zip(q0,q1))<0 else 1
    norm0=perfect_sqrt(sum(v*v for v in q0));norm1=perfect_sqrt(sum(v*v for v in q1))
    if proportional(q0,q1):q=q0
    else:
        check(norm0 is not None and norm1 is not None,'this finite Fraction corpus needs rational normalized key endpoints')
        q=[(1-alpha)*x/norm0+alpha*sign*y/norm1 for x,y in zip(q0,q1)]
    d0,d1=q_unit_decimal(q0),q_unit_decimal(q1);ad=decimal(alpha)
    mixed=[(1-ad)*x+ad*sign*y for x,y in zip(d0,d1)];norm=sum(v*v for v in mixed).sqrt();qd=[v/norm for v in mixed]
    return t,q,s,qd

def close(actual,expected):
    global CHECKS,MAX_ABS,MAX_SCALED
    value=actual if isinstance(actual,F) else F(number(actual));reference=F(expected);error=abs(value-reference);scale=max(F(1),abs(reference))
    check(error<=TOLERANCE*scale,'independent affine/linear reference error exceeds point tolerance')
    CHECKS+=1;MAX_ABS=max(MAX_ABS,error);MAX_SCALED=max(MAX_SCALED,error/scale)

def expected_pose(row):
    q=row['input'];seconds=F(float(q['time']));duration=F(float(q['duration']));time=min(seconds,duration) if q['mode']==0 else seconds%duration
    source={b['id']:b for b in q['bones']};tracks={t['boneId']:t for t in q['tracks']};pending=set(source);order=[];world={};locals_={}
    while pending:
        ready=[i for i in pending if source[i]['parentId']==0 or source[i]['parentId'] in world]
        check(bool(ready),'oracle invalid hierarchy in completed input');i=min(ready);b=source[i]
        t,rotation,s,qd=local_ref(b['rest'],tracks.get(i),time);local=matrix(t,rotation,s)
        world[i]=local if b['parentId']==0 else mm(world[b['parentId']],local)
        locals_[i]=(t,s,qd,local);pending.remove(i);order.append(i)
    return time,order,locals_,world

def verify(rows):
    good=set(NAMES[:27])|{'branching-order'}
    for row in rows:
        n,q,r=row['name'],row['input'],row['result']
        expected=0 if n in good else 2 if n in ('bone-budget','track-budget','key-budget') else 3 if n=='world-overflow' else 1
        check(r['status']==expected,n+': classification')
        if n=='world-overflow':check(F(1000000)**len(q['bones'])>F(sys.float_info.max),'independent overflow witness')
        if r['status']!=0:continue
        time,order,locals_,world=expected_pose(row);p=r['pose']
        check(F(float(p['sampledTime']))==time,'clamp/loop phase differs from exact corpus clock')
        check(p['evaluationOrder']==order,'parent-first stable ready-ID traversal differs')
        for b in p['bones']:
            t,s,qd,local=locals_[b['id']]
            for actual,want in zip(b['local']['position'],t):close(actual,want)
            for actual,want in zip(b['local']['scale'],s):close(actual,want)
            for actual,want in zip(b['local']['rotation'],qd):close(actual,F(want))
            for actual,want in zip(b['localMatrix'],flatten(local)):close(actual,want)
            for actual,want in zip(b['worldMatrix'],flatten(world[b['id']])):close(actual,want)
    by={r['name']:r for r in rows}
    a={b['id']:b['worldMatrix'] for b in by['two-link']['result']['pose']['bones']}
    b={b['id']:b['worldMatrix'] for b in by['permuted-tree']['result']['pose']['bones']}
    check(bits(a)==bits(b),'input permutation changed FK binary64 result')
    # Deliberately excludes the tempting but wrong TRS-redecomposition result:
    # parent-scaled child columns are not perpendicular for this exact example.
    shear=by['shear']['result']['pose']['bones'][0]['worldMatrix']
    close(sum(F(float(shear[k]))*F(float(shear[k+4])) for k in range(3)),F(-54,25))
    check(abs(sum(shear[k]*shear[k+4] for k in range(3)))>1,'shear was silently discarded')

ORACLE_HEADER=['id','time']+['world'+str(j) for j in range(16)]
def corpus(path):
    with open(path,encoding='utf-8-sig',newline='') as stream:rows=list(csv.reader(stream))
    check(len(rows)==129 and rows[0]==ORACLE_HEADER,'oracle header/count');out=[]
    for j,row in enumerate(rows[1:]):
        check(len(row)==18 and row[0]==str(j),'oracle identity/row width');v=[]
        for text in row[1:]:
            check(text.lower().startswith(('0x','-0x')),'oracle requires exact hexadecimal binary64');x=float.fromhex(text);check(math.isfinite(x),'nonfinite oracle');v.append(x)
        time=F(j,64);check(F(v[0])==time,'oracle point time changed');alpha=time/2
        t=[4*alpha,2*alpha,-2*alpha];q=[F(0),F(0),alpha*F(3,5),1-alpha*F(1,5)];s=[1+2*alpha,1+alpha,F(1)]
        parent=matrix(t,q,s);child=matrix([F(1),F(2),F(0)],[F(0),F(0),F(1),F(2)],[F(2),F(1,2),F(1)])
        for actual,reference in zip(v[1:],flatten(mm(parent,child))):close(actual,reference)
        out.append(v)
    return out

def main():
    check(__debug__,'Python -O is unsupported: fail closed')
    parser=argparse.ArgumentParser();parser.add_argument('native');parser.add_argument('wasm',nargs='?');parser.add_argument('--oracle');parser.add_argument('--wasm-oracle');args=parser.parse_args()
    with localcontext() as context:
        context.prec=120
        rows=load(args.native);verify(rows);matched=False;oracle_rows=0
        if args.wasm:
            other=load(args.wasm);verify(other);check(bits(rows)==bits(other),'Native/WASM fixture binary64 bits differ');matched=True
        if args.oracle:
            o=corpus(args.oracle);oracle_rows=len(o)
            if args.wasm_oracle:check(bits(o)==bits(corpus(args.wasm_oracle)),'Native/WASM oracle binary64 bits differ')
        else:check(not args.wasm_oracle,'--wasm-oracle requires --oracle')
    print(json.dumps({'status':'PASS','fixtures':len(rows),'oracleRows':oracle_rows,'independentPointChecks':CHECKS,'maximumAbsoluteError':float(MAX_ABS),'maximumScaledError':float(MAX_SCALED),'scaledTolerance':float(TOLERANCE),'wasmBitsMatch':matched,'model':'point binary64; no interval containment claim'}))

if __name__=='__main__':
    try:main()
    except Exception as error:print('FAIL: '+str(error),file=sys.stderr);sys.exit(1)
