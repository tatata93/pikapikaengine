"""Independent exact typed oracle for held snapshots and stored work, without model execution."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)

def need(v,m):
    if not v:raise ValueError(m)

def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def u(v):return ('u64',v)
    def uint(v):return ('u32',v)
    bits=[0,2**63,1,0x8000000000000001,0x000fffffffffffff,0x0010000000000000,0x3ff0000000000000,0xbff0000000000000,
          0x7fefffffffffffff,0xffefffffffffffff,0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000042,0xfff8000000001234,0x7ff0000000000001,0xfff0000000000001]
    n=0
    def f():
        nonlocal n
        value=('f64bits',bits[n%16]);n+=1;return value
    def vec():return obj(x=f(),y=f(),z=f())
    a=obj(id=u(2**64-1),vertices=('array',[vec(),vec(),vec()]))
    b=obj(id=u(2**53+1),vertices=('array',[vec(),vec(),vec()]))
    reverse=obj(id=u(2**64-1),vertices=('array',list(reversed(a[1][1][1][1]))))
    triangles=[[],[a,b,a],[b,reverse,a]]
    snapshots=[]
    for j in range(3):
        sphere=obj(id=u(2**53+1 if j else 2**64-1),position=vec(),velocity=vec(),mass=f(),force=vec(),gravity=vec(),radius=f())
        horizon=f()
        primitive=obj(max_candidates=uint(j),sqrt_refinements=uint(2**32-1-j),max_total_sqrt_refinements=uint(0x80000002+j),
                      maximum_local_width=f(),maximum_normal_width=f(),minimum_sine_squared=f())
        mesh=obj(max_surfaces=u(2**64-1-j),primitive=primitive)
        settings=obj(mesh=mesh,time_tolerance=f(),max_evaluations=u(2**53+1+j),max_leaves=u(j),max_depth=uint(2**32-1-j),
                     enclosure_sqrt_refinements=uint(j),max_total_sqrt_refinements=u(2**64-1-17*j))
        snapshots.append(obj(input=sphere,horizon=horizon,triangles=('array',triangles[j]),settings=settings))
    need(n==75,'All explicitly generated input/settings/triangle scalars')
    names='mesh_queries primitive_queries candidates_examined primitive_sqrt_refinements enclosure_sqrt_refinements sqrt_refinements sqrt_refinements_upper mesh_sqrt_limited_rows enclosure_sqrt_calls enclosure_sqrt_limited_calls'.split()
    counts=[0,2**64-1,2**53+1,2**63,1,2**64-18,2**53+3,255,256,257]
    work=[obj(**{k:u(v) for k,v in zip(names,values)},exact=('bool',exact)) for values,exact in [([0]*10,True),(counts,False)]]
    return 0x52485731,('array',snapshots+work)

def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every original snapshot field/order/bit and all separate stored work counts/flag')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits']
    need(len(floats)==111 and len(leaves)==169,'All169 typed leaves including111 raw floats')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=15,fixtureRecords=5,
                allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
                u64Fields=sum(k=='u64' for k,_ in leaves),u32Fields=sum(k=='u32' for k,_ in leaves),boolFields=sum(k=='bool' for k,_ in leaves),
                scope='Three artificial snapshots and two stored Work values. No model call, budget admission, full Report, pump, JS/WASM/game acceptance.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
