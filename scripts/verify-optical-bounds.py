"""Independent exact-real checks. Decode binary64 with integers/Fraction only.
Sampling and native/WASM agreement are separate evidence, not these proofs.
"""
import csv
import sys
from fractions import Fraction as F
if not __debug__:
    raise SystemExit("Python -O disables proof assertions; rejected")
def decode(bits):
    assert 1<=len(bits)<=16 and all(c in '0123456789abcdef' for c in bits), 'invalid binary64 hex'
    bits=int(bits,16)
    sign=-1 if bits>>63 else 1
    exponent=(bits>>52)&2047
    mantissa=bits&((1<<52)-1)
    assert exponent!=2047, "finite proof output required"
    if exponent: mantissa|=1<<52
    power=(exponent-1023-52) if exponent else -1074
    return sign*F(mantissa)*(F(2)**power)
def contains(bounds,lo,hi=None):
    hi=lo if hi is None else hi
    assert bounds[0]<=lo<=hi<=bounds[1], (bounds,lo,hi)
def verify(path):
    packet=list(csv.reader(open(path,encoding="utf-8-sig",newline="")))
    assert packet[0]=="kind,k,originLo,originHi,directionLo,directionHi,plane,tLo,tHi,dLo,dHi,xLo,xHi,yLo,yHi,zLo,zHi".split(','), 'corpus header'
    rows=packet[1:]
    assert len(rows)==302
    endpoints=[]
    for j,row in enumerate(rows):
        kind=row[0]
        expected=('P',j+1,17) if j<120 else ('Q',j-119,21) if j<240 else ('C',j-239,21) if j<300 else ('B',0,27) if j==300 else ('N',0,27)
        assert (kind,int(row[1]),len(row))==expected, 'corpus identity/count'
        values=[decode(x) for x in row[2:7]]
        raw=row[7:]
        assert len(raw)%2==0
        bounds=[(decode(raw[i]),decode(raw[i+1])) for i in range(0,len(raw),2)]
        assert all(lo<=hi for lo,hi in bounds)
        endpoints.extend(raw)
        if kind in ("P","Q","C"):
            ol,oh,dl,dh,value=values
            assert ol<=oh and dl<=dh and (dl>0 if kind!='C' else dh<0), 'family domain'
            if kind in ('Q','C'): assert value>0
            if kind=="P":
                z=value
                tl,th=(z-oh)/dh,(z-ol)/dl
                contains(bounds[0],tl,th)
                contains(bounds[1],z-oh,z-ol)
            elif kind=="Q":
                z=-value
                tl,th=(-value-oh)/dh,(-value-ol)/dl
                contains(bounds[0],tl,th)
                contains(bounds[1],-value-oh,-value-ol)
                contains(bounds[5],tl,th)
                contains(bounds[6],(value-oh)/dh,(value-ol)/dl)
            else:
                assert dl<dh<0
                z=F(0)
                tl,th=(-ol)/dl,(-oh)/dh
                contains(bounds[0],tl,th)
                contains(bounds[1],ol,oh)
                contains(bounds[5],(2*value-ol)/dl,(2*value-oh)/dh)
                contains(bounds[6],tl,th)
            contains(bounds[2],F(0));contains(bounds[3],F(0));contains(bounds[4],z)
        elif kind in ("B","N"):
            assert all(x==0 for x in values), 'fixed-case reserved inputs'
            assert len(bounds)==10
            transmitted=[F(4,5),F(-3,5),F(0)] if kind=="B" else [F(0),F(-1),F(0)]
            reflected=[F(3,5),F(4,5),F(0)] if kind=="B" else [F(0),F(1),F(0)]
            power=[F(49,625),F(576,625),F(0),F(1)] if kind=="B" else [F(1,25),F(24,25),F(1,25),F(24,25)]
            for enclosure,exact in zip(bounds,transmitted+reflected+power):
                contains(enclosure,exact)
        else: raise AssertionError("unknown corpus tag")
    assert len(endpoints)==3760
    print(path+": 302 exact-family cases, 1880 intervals / 3760 endpoint bits PASS")
    return endpoints
if len(sys.argv) not in (2,3): raise SystemExit("usage: verify-bounds.py native.csv [wasm.csv]")
first=verify(sys.argv[1])
if len(sys.argv)==3:
    second=verify(sys.argv[2])
    assert first==second, "native/WASM endpoint bit mismatch"
    print("Native/WASM 3760 endpoint bits identical")
