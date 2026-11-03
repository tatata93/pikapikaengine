"""Exact rational/256-bit algebraic reference for independent index families.
Normal monotonicity and fixed 3-4-5 incidence prove continuum endpoint extrema.
This is independent of the implementation's double interval arithmetic.
"""
import csv
import sys
from fractions import Fraction as F
from math import isqrt
if not __debug__:
    raise SystemExit("Python -O disables proof assertions; rejected")
def decode(bits):
    assert 1<=len(bits)<=16 and all(c in '0123456789abcdef' for c in bits), 'invalid binary64 hex'
    bits=int(bits,16)
    sign=-1 if bits>>63 else 1
    exponent=(bits>>52)&2047
    mantissa=bits&((1<<52)-1)
    assert exponent!=2047
    if exponent: mantissa|=1<<52
    return sign*F(mantissa)*F(2)**(exponent-1023-52 if exponent else -1074)
def scalar(a): return (F(a),F(a))
def plus(a,b): return (a[0]+b[0],a[1]+b[1])
def minus(a,b): return (a[0]-b[1],a[1]-b[0])
def times(a,b):
    v=[x*y for x in a for y in b]
    return (min(v),max(v))
def divide(a,b):
    assert b[0]>0 or b[1]<0
    return times(a,(1/b[1],1/b[0]))
def square(a):
    upper=max(a[0]**2,a[1]**2)
    return (F(0) if a[0]<=0<=a[1] else min(a[0]**2,a[1]**2),upper)
def root(q):
    assert q>=0
    a,b=isqrt(q.numerator),isqrt(q.denominator)
    if a*a==q.numerator and b*b==q.denominator:
        return scalar(F(a,b))
    scale=1<<256
    k=isqrt((q.numerator<<512)//q.denominator)
    lo,hi=F(k,scale),F(k+1,scale)
    assert lo*lo<=q<=hi*hi
    return (lo,hi)
def contains(bounds,lo,hi=None):
    hi=lo if hi is None else hi
    assert bounds[0]<=lo<=hi<=bounds[1], (bounds,lo,hi)
def fresnel(eta):
    # Independent electric amplitudes and normal flux; exact rational interval
    # operations surround only the irrational transmitted cosine.
    ci=scalar(F(4,5));e=scalar(eta);ct=root(1-eta*eta*F(9,25))
    ds=plus(times(e,ci),ct);dp=plus(ci,times(e,ct))
    rs=divide(minus(times(e,ci),ct),ds)
    rp=divide(minus(ci,times(e,ct)),dp)
    es=divide(times(scalar(2),times(e,ci)),ds)
    ep=divide(times(scalar(2),times(e,ci)),dp)
    flux=divide(ct,times(e,ci))
    return (square(rs),times(flux,square(es)),square(rp),times(flux,square(ep)))
def verify(path):
    packet=list(csv.reader(open(path,encoding="utf-8-sig",newline="")))
    assert packet[0]=="kind,k,niLo,niHi,ntLo,ntHi,wavelength,transmitted6,reflected6,Rs2,Ts2,Rp2,Tp2".split(','), 'corpus header'
    rows=packet[1:]
    assert len(rows)==111
    endpoint_bits=[]
    for j,row in enumerate(rows):
        tag=row[0]
        expected=('N',j,27) if j<100 else ('S',j-100,27) if j<110 else ('F',0,27)
        assert (tag,int(row[1]),len(row))==expected, 'corpus identity/count'
        nil,nih,ntl,nth,wavelength=map(decode,row[2:7])
        assert 0<nil<=nih<ntl<=nth
        assert len(row[7:])==20
        bounds=[tuple(map(decode,row[i:i+2])) for i in range(7,len(row),2)]
        endpoint_bits.extend(row[7:])
        if tag=="N":
            for out,exact in zip(bounds[:6],[0,-1,0,0,1,0]): contains(out,F(exact))
            low=((ntl-nih)/(ntl+nih))**2
            high=((nth-nil)/(nth+nil))**2
            tlo=4*nil*nth/(nil+nth)**2
            thi=4*nih*ntl/(nih+ntl)**2
            for out in (bounds[6],bounds[8]): contains(out,low,high)
            for out in (bounds[7],bounds[9]): contains(out,tlo,thi)
        elif tag in ("S","F"):
            emin,emax=nil/nth,nih/ntl
            assert 0<emin<=emax<1
            contains(bounds[0],F(3,5)*emin,F(3,5)*emax)
            ct_hi=root(1-emin*emin*F(9,25));ct_lo=root(1-emax*emax*F(9,25))
            contains(bounds[1],-ct_hi[1],-ct_lo[0]);contains(bounds[2],F(0))
            for out,exact in zip(bounds[3:6],[F(3,5),F(4,5),F(0)]): contains(out,exact)
            low=fresnel(emin);high=fresnel(emax)
            # For eta<1 and s=3/5, both Rs/Rp decrease and Ts/Tp increase.
            for component in (0,2): contains(bounds[6+component],high[component][0],low[component][1])
            for component in (1,3): contains(bounds[6+component],low[component][0],high[component][1])
            if tag=="F":
                assert wavelength==F(1,1<<20)
                phase=F(3,2)+F(1,1<<44)/wavelength**2+F(1,1<<88)/wavelength**4
                assert phase==F(401,256)
                assert ntl<phase<nth
        else: raise AssertionError("unknown index corpus tag")
    assert len(endpoint_bits)==2220
    print(path+": 111 continuous index families / 1110 intervals / 2220 endpoint bits PASS")
    return endpoint_bits
if len(sys.argv) not in (2,3):
    raise SystemExit("usage: verify-index-bounds.py native-index.csv [wasm-index.csv]")
first=verify(sys.argv[1])
if len(sys.argv)==3:
    second=verify(sys.argv[2])
    assert first==second
    print("Native/WASM 2220 index-family endpoint bits identical")
