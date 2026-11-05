"""Independent input construction and exact all-field C API read comparison."""
import json,struct,sys
from pathlib import Path
def need(v,m):
    if not v:raise ValueError(m)
def bit(v):return struct.unpack('>Q',struct.pack('>d',v))[0]
def expected(b):
    p=16 if b==8 else b
    f=[-0.,-9.,0.,.25,-0.,1/120];w=[b,p,4,2**32-1,2**32-1]
    for i in range(b):
        k=i/16
        f.extend([2+k,.5+k,11+k,12+k,13+k,21+k,22+k,-0.,31+k,32+k,33+k,34+k,41+k,42+k,43+k,51+k,52+k,53+k,61+k,-0.,63+k,71+k,72+k,73+k,81+k,91+k])
        body_id=2**64-1 if i==0 else 0 if i==1 else 1000-3*i
        w.extend([body_id%(2**32),body_id//(2**32),i%2])
    if b:f[24]=float.fromhex('0x0.0000000000001p-1022')
    for i in range(p):f.extend([-0.,1.,0.,-0. if i==0 else i/8,.5,.25]);w.extend([i+1,0])
    return p,list(map(bit,f)),w
def verify(d):
    need(type(d)==dict and set(d)=={'schema','kind','rows','actualRows'},'Exact envelope')
    need(type(d['schema'])==int and d['schema']==1 and d['kind']=='native-session-c-api-read' and type(d['actualRows'])==int and d['actualRows']==9,'Actual ABI version/count')
    need(type(d['rows'])==list and len(d['rows'])==9,'Nine complete rows')
    mapped=0;zero=0
    for b,r in enumerate(d['rows']):
        need(type(r)==dict and set(r)=={'bodies','planes','inputFloatBits','inputWords','readFloatBits','readWords','token','sequence','backlogBits'},'Exact row keys')
        p,f,w=expected(b)
        for key,value in [('bodies',b),('planes',p),('backlogBits',0)]:need(type(r[key])==int and r[key]==value,'Typed scalar '+key)
        for key,value in [('inputFloatBits',f),('readFloatBits',f),('inputWords',w),('readWords',w),('token',[0,1,0]),('sequence',[0,0])]:
            need(type(r[key])==list and all(type(x)==int for x in r[key]) and r[key]==value,'All input/read typed bit/integer values '+key)
        mapped+=len(f);zero+=f.count(1<<63)
    return dict(status='PASS',rows=9,mappedFloatBitValues=mapped,negativeZeroOccurrences=zero,full64BodyIDsAndTicks=True,simultaneous8Bodies16Planes=True,scope='Independent fixed-input construction/all mapped read values. Lifecycle assertion proof is separate; no pump, mesh/full guard, allocator, GNU/WASM or model-step proof.')
def main():
    need(__debug__,'Use normal Python; optimized execution is refused')
    need(len(sys.argv)==2,'One actual capture required');p=Path(sys.argv[1]);need(p.stat().st_size<1024*1024,'Bounded proof input')
    print(json.dumps(verify(json.loads(p.read_bytes())),allow_nan=False))
if __name__=='__main__':main()
