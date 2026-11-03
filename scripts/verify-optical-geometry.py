"""Original optical geometry oracle using exact fractions, no float reference."""
from fractions import Fraction as F
from pathlib import Path
from math import isqrt
import sys

def decode(s):
    bits=int(s,16);sgn=-1 if bits>>63 else 1;e=(bits>>52)&2047;m=bits&((1<<52)-1)
    assert e!=2047,'nonfinite corpus value'
    if e:m+=(1<<52);power=e-1075
    else:power=-1074
    return sgn*F(m*(1<<max(power,0)),1<<max(-power,0))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return [x-y for x,y in zip(a,b)]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def sqrt_rational(x):
    a,b=isqrt(x.numerator),isqrt(x.denominator)
    assert a*a==x.numerator and b*b==x.denominator,'corpus expects a rational axis norm'
    return F(a,b)
def quadratic_range(a,b,c,lo,hi):
    f=lambda t:a*t*t+b*t+c
    values=[f(lo),f(hi)]
    if a and lo<=-b/(2*a)<=hi:values.append(f(-b/(2*a)))
    return min(values),max(values)
def verify(path):
    rows=Path(path).read_text(encoding='utf-8-sig').splitlines();counts=[0,0,0];roots=0
    for j,line in enumerate(rows):
        f=line.split(',');assert len(f)==37,(j,'column count',len(f))
        typ=f[0];assert typ in ('P','S','C'),(j,'unknown surface kind')
        v=list(map(decode,f[1:17]));o,d=v[:3],v[3:6];tmin,tmax=v[6:8];anchor,axis=v[8:11],v[11:14];radius,ap=v[14:16]
        status,reason,n,considered,has_hit=map(int,f[17:22]);bounds=list(map(decode,f[22:26]));states=list(map(int,f[26:28]));point=list(map(decode,f[28:34]));dist=list(map(decode,f[34:36]));front=int(f[36])
        assert status in (0,1,2) and has_hit==(status==0)
        assert 0<=reason<=12 and 0<=considered<=n<=2 and front in (0,1),(j,'invalid packet counts/tags')
        assert all(0<=s<=5 for s in states),(j,'invalid candidate state')
        counts[status]+=1
        center=anchor
        if typ=='C':
            norm=sqrt_rational(dot(axis,axis));axis=[x/norm for x in axis]
            center=[x+radius*y for x,y in zip(anchor,axis)]
        oc=sub(o,center);a=dot(d,d);h=dot(oc,d);c=dot(oc,oc)-radius*radius
        if typ=='P':
            denominator=dot(d,axis);exact_t=dot(sub(center,o),axis)/denominator
            assert n==1 and bounds[0]<=exact_t<=bounds[1],(j,'plane rational root')
        else:
            delta=h*h-a*c
            if n==0:
                assert status in (1,2)
                if status==1:assert delta<0,(j,'false no-real-roots')
                continue
            assert delta>0 and n==2,(j,'quadratic classification')
            vertex=-h/a
            polynomial=lambda t:a*t*t+2*h*t+c
            l,u=bounds[:2];assert l<=u and l<=vertex and polynomial(l)>=0 and (u>=vertex or polynomial(u)<=0),(j,'lower root enclosure')
            l,u=bounds[2:];assert l<=u and (l<=vertex or polynomial(l)<=0) and u>=vertex and polynomial(u)>=0,(j,'upper root enclosure')
        roots+=n
        for k in range(considered):
            lo,hi=bounds[2*k:2*k+2];state=states[k]
            if state==2:assert hi<tmin or lo>tmax,(j,'false domain rejection')
            if state in (1,3,4):
                assert tmin<=lo<=hi<=tmax,(j,'parameter domain proof')
                if typ=='C':
                    hemi=lambda t:radius*dot([x+t*y-z for x,y,z in zip(o,d,center)],axis)
                    hmin,hmax=min(hemi(lo),hemi(hi)),max(hemi(lo),hemi(hi))
                    if state==4:assert hmin>0,(j,'false cap hemisphere rejection')
                    else:assert hmax<0,(j,'cap hemisphere proof')
                if ap>0 and state in (1,3):
                    u=sub(o,anchor);w=d
                    if typ=='C':u,w=cross(u,axis),cross(w,axis)
                    rmin,rmax=quadratic_range(dot(w,w),2*dot(u,w),dot(u,u),lo,hi)
                    if state==3:assert rmin>ap*ap,(j,'false aperture rejection')
                    else:assert rmax<ap*ap,(j,'aperture interior proof')
        if has_hit:
            chosen=considered-1;assert states[chosen]==1 and all(s in (2,3,4) for s in states[:chosen]),(j,'nearest valid ordering')
            lo,hi=bounds[2*chosen:2*chosen+2]
            for k in range(3):
                endpoints=[o[k]+d[k]*lo,o[k]+d[k]*hi]
                assert point[2*k]<=min(endpoints)<=max(endpoints)<=point[2*k+1],(j,'hit position enclosure')
            assert dist[0]>=0 and dist[0]*dist[0]<=lo*lo*a and dist[1]*dist[1]>=hi*hi*a,(j,'physical distance enclosure')
            if typ=='P':assert front==(dot(d,axis)<0)
            else:
                incidence=[h+a*lo,h+a*hi]
                assert max(incidence)<0 if front else min(incidence)>0,(j,'normal orientation certificate')
    assert len(rows)==200,('changed or truncated corpus',len(rows))
    assert roots==330 and counts==[197,2,1],('changed root/status corpus',roots,counts)
    print(f'OPTICAL GEOMETRY FRACTION PASS {len(rows)} cases, {roots} root enclosures, hit/miss/unresolved={counts}: {path}')
    return rows
if __name__=='__main__':
    if not __debug__:raise RuntimeError('Do not use Python -O')
    assert len(sys.argv)>1,'usage: verify-geometry.py native.csv [wasm.csv]'
    out=[verify(p) for p in sys.argv[1:]]
    if len(out)==2:
        assert out[0]==out[1],'Native/WASM bit/packet parity differs'
        print(f'OPTICAL GEOMETRY NATIVE/WASM BIT PARITY PASS {len(out[0])} complete rows')
