"""Exact-Fraction audit of the shared nonnegative binary64 square-root corpus.
No reference floating-point sqrt, random sampling claim, or Python -O.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse,csv,io,json,struct
if not __debug__: raise SystemExit('Python -O is rejected')
def require(ok,message):
    if not ok: raise ValueError(message)
def decode(h):
    require(len(h)==16 and all(c in '0123456789abcdef' for c in h),'canonical binary64 hex')
    b=int(h,16);sign=-1 if b>>63 else 1;e=(b>>52)&2047;m=b&((1<<52)-1)
    require(e!=2047,'finite endpoint required')
    if e:m+=1<<52;p=e-1023-52
    else:p=-1074
    return sign*F(m*(1<<max(0,p)),1<<max(0,-p))
def expected():
    rows=[(0,0,128)]
    for e in range(-1074,1024):
        bits=(e+1023)<<52 if e>=-1022 else 1<<(e+1074)
        rows.append((bits,bits,128))
    t=1;n=0x0010000000000000;m=0x7fefffffffffffff
    rows.extend((a,b,128) for a,b in [(0,t),(t,2*t),(t,n),(n,m),(0,m),(m,m),(n-1,n),(0x3ff0000000000000,0x4010000000000000),(0x4000000000000000,0x4008000000000000),(0x3fd0000000000000,0x3ff0000000000000),(0x3fefffffffffffff,0x3ff0000000000001),(0x400fffffffffffff,0x4010000000000000)])
    seed=0x743fea0c98152d67;mask=(1<<64)-1
    def random():
        nonlocal seed
        seed=(seed^(seed<<13))&mask;seed^=seed>>7;seed=(seed^(seed<<17))&mask
        return seed&0x7fefffffffffffff
    for j in range(512):
        a=random();b=random();rows.extend([(a,a,128),(min(a,b),max(a,b),128)])
    for j in range(64):
        x=random();rows.extend((x,x,k) for k in [1,2,8])
    require(len(rows)==3327,'internal corpus size');return rows
def check(path):
    text=Path(path).read_text(encoding='utf-8-sig');reader=csv.DictReader(io.StringIO(text))
    require(reader.fieldnames==['ordinal','inputLo','inputHi','budget','outputLo','outputHi','refinements','limited'],'exact schema required')
    rows=list(reader);want=expected();require(len(rows)==len(want),'complete corpus required');limited=0
    for j,(row,(a,b,budget)) in enumerate(zip(rows,want)):
        require(None not in row and all(v is not None for v in row.values()),'row shape')
        require(row['ordinal']==str(j),'ordinal/order mismatch')
        require(row['inputLo']==f'{a:016x}' and row['inputHi']==f'{b:016x}' and row['budget']==str(budget),'source input mismatch')
        lo=decode(row['inputLo']);hi=decode(row['inputHi']);outlo=decode(row['outputLo']);outhi=decode(row['outputHi'])
        require(0<=outlo<=outhi,'nonnegative ordered finite roots')
        require(outlo*outlo<=lo and outhi*outhi>=hi,'exact squared endpoint inclusion')
        require(row['refinements'].isdigit() and int(row['refinements'])<=budget*(1 if a==b else 2),'reported work exceeds endpoint budget')
        require(row['limited'] in ['0','1'],'limited flag');limited+=int(row['limited'])
        if a==b and budget==128:
            require(row['limited']=='0','full budget point unresolved')
            require((outhi-outlo)*10**12<=outhi,'measured point root precision')
    return text,dict(status='PASS',rows=len(rows),exactSquaredEndpointInclusions=2*len(rows),allPowerOfTwoExponents=2098,limitedCases=limited)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native');p.add_argument('wasm',nargs='?');a=p.parse_args();text,r=check(a.native)
    if a.wasm:
        other,r['wasm']=check(a.wasm);require(text==other,'Native/WASM complete hex packet parity');r['bitEqualEndpoints']=2*r['rows']
    r['limits']='Every finite input interval is audited at its exact rational endpoints using monotonicity. Finite corpus and supported strict-FP targets only, not a formal compiler proof or correctly rounded scalar sqrt.';print(json.dumps(r,sort_keys=True))
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError,csv.Error,OverflowError) as e:raise SystemExit('FAIL interval sqrt: '+str(e)) from e
