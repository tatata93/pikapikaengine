"""Exact rational optics branch oracle; standard library only."""
from fractions import Fraction
from pathlib import Path
import sys

def decode(text):
    bits = int(text,16)
    sign = -1 if bits >> 63 else 1
    exponent = (bits >> 52) & 0x7ff
    mantissa = bits & ((1 << 52)-1)
    if exponent == 0x7ff:
        raise AssertionError('nonfinite oracle value')
    if exponent:
        mantissa += 1 << 52
        power = exponent-1023-52
    else:
        power = -1074
    return sign*Fraction(mantissa*(1 << max(power,0)),1 << max(-power,0))

def verify(path):
    rows = Path(path).read_text(encoding='utf-8-sig').splitlines()
    kinds = [0,0,0]
    for j,line in enumerate(rows):
        fields = line.split(',')
        assert len(fields)==14,(j,'column count')
        ix,iy,iz,nx,ny,nz,ni,nt,lo,hi,dlo,dhi = map(decode,fields[:12])
        kind,reason = map(int,fields[12:])
        normi=ix*ix+iy*iy+iz*iz
        normn=nx*nx+ny*ny+nz*nz
        cx,cy,cz=iy*nz-iz*ny,iz*nx-ix*nz,ix*ny-iy*nx
        exact_D=nt*nt*normi*normn-ni*ni*(cx*cx+cy*cy+cz*cz)
        exact_dot=ix*nx+iy*ny+iz*nz
        assert lo<=exact_D<=hi,(j,'D enclosure')
        assert dlo<=exact_dot<=dhi,(j,'dot enclosure')
        assert exact_dot<=0,(j,'input hemisphere')
        if kind==0:
            assert ni==nt or exact_D>0,(j,'false transmission certificate')
            assert reason==0
        elif kind==1:
            assert exact_D<0 and reason==0,(j,'false TIR certificate')
        else:
            assert kind==2 and reason in (1,2,3),(j,'bad uncertainty')
            if reason==1: assert dlo<=0<=dhi
            if reason==2: assert lo<=0<=hi
        if j<5:
            assert exact_D==9-ix*ix,(j,'known independent critical equation')
            if j==0: assert exact_D==0
            if j in (1,3): assert exact_D>0
            if j in (2,4): assert exact_D<0
            assert kind==[2,2,2,0,1][j],(j,'critical-neighbor outcome')
        kinds[kind]+=1
    assert len(rows)==1029,('truncated/changed corpus',len(rows))
    print(f'OPTICS EXACT FRACTION PASS {len(rows)} D/dot enclosures; transmission/TIR/uncertain={kinds}: {path}')
    return rows

if __name__=='__main__':
    if not __debug__: raise RuntimeError('Do not run with Python -O')
    assert len(sys.argv)>1,'usage: verify-optics.py native.csv [wasm.csv]'
    results=[verify(path) for path in sys.argv[1:]]
    if len(results)==2:
        assert results[0]==results[1],'native/WASM branch certificates differ'
        print(f'OPTICS NATIVE/WASM BIT PARITY PASS {len(results[0])} certificates, {len(results[0])*4} bound values')
