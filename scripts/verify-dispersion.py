"""Independent exact-rational dispersion oracle; no binary float or libm sqrt.

For corpus B,C>0 and lambda^2>C: n'<0 and n''>0; hence n and
n_g=n-lambda*n' decrease while n' increases over the entire band. Sellmeier
n''=(2*q*q''-q'^2)/(4*q^(3/2))>0 for this one-oscillator corpus because
q>1, q''=2*B*C*(3*lambda^2+C)/(lambda^2-C)^3, B,C>0.
Endpoint checks below therefore certify full continuous bands, not samples.
"""
from fractions import Fraction as F
from pathlib import Path
import csv
import sys

def decode(value):
    assert len(value)==16 and all(c in '0123456789abcdef' for c in value), 'invalid binary64 hex'
    bits=int(value,16); exponent=(bits>>52)&2047; mantissa=bits&((1<<52)-1)
    assert exponent!=2047, 'nonfinite bound/input'
    if exponent: mantissa+=1<<52; power=exponent-1075
    else: power=-1074
    return (-1 if bits>>63 else 1)*F(mantissa*(1<<max(power,0)),1<<max(-power,0))

def rational(bound,value):
    lo,hi=bound
    assert lo<=value<=hi, ('rational enclosure',lo,value,hi)

def positive_over_sqrt(bound,numerator,q):
    lo,hi=bound
    assert numerator>=0 and q>0 and hi>=0 and lo<=hi
    assert (lo<=0 or lo*lo*q<=numerator*numerator) and numerator*numerator<=hi*hi*q, 'algebraic enclosure'

def verify(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as handle: rows=list(csv.reader(handle))
    assert rows[0]==['id','kind','lambda_lo','lambda_hi','a','b','c','sell_b','sell_c','n_lo','n_hi','d_lo','d_hi','g_lo','g_hi'], 'header'
    assert len(rows)==321, 'expected all 320 cases'
    counts=[0,0]
    for j,row in enumerate(rows[1:]):
        assert len(row)==15 and int(row[0])==j and row[1] in ('0','1'), 'packet identity'
        kind=int(row[1]); counts[kind]+=1
        l,u,a,b,c,sb,sc,*bounds=map(decode,row[2:])
        assert 0<l<=u
        n,d,g=[bounds[k:k+2] for k in (0,2,4)]
        assert all(x[0]<=x[1] for x in (n,d,g))
        for wavelength in (l,u):
            x=wavelength*wavelength
            if kind==0:
                assert b>0 and c>0, 'monotonic Cauchy corpus'
                rational(n,a+b/x+c/(x*x))
                rational(d,-2*b/(x*wavelength)-4*c/(x*x*wavelength))
                rational(g,a+3*b/x+5*c/(x*x))
            else:
                assert sb>0 and sc>0 and x>sc, 'monotonic one-oscillator corpus'
                q=1+sb*x/(x-sc)
                qp=-2*sb*sc*wavelength/(x-sc)**2
                qpp=2*sb*sc*(3*x+sc)/(x-sc)**3
                assert 2*q*qpp-qp*qp>0, 'convex phase branch'
                positive_over_sqrt(n,q,q) # sqrt(q)=q/sqrt(q)
                positive_over_sqrt([-d[1],-d[0]],-qp/2,q)
                positive_over_sqrt(g,q-wavelength*qp/2,q)
    assert counts==[160,160], 'case classes'
    print(f'PASS dispersion Fraction oracle: 320 cases, 160 continuous bands, 960 intervals ({path})')

if __name__=='__main__':
    if not __debug__: raise SystemExit('Do not run this verifier with Python -O')
    if len(sys.argv)!=2: raise SystemExit('usage: python verify-dispersion.py oracle.csv')
    verify(sys.argv[1])
