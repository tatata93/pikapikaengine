"""Independent exact held-input/seconds-cell/selected-body oracle; no model functions."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    bits=[0,2**63,1,0x8000000000000001,0x000fffffffffffff,0x0010000000000000,0x3ff0000000000000,0xbff0000000000000,
        0x7fefffffffffffff,0xffefffffffffffff,0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000042,0xfff8000000001234,0x7ff0000000000001,0xfff0000000000001]
    n=0
    def f():
        nonlocal n
        value=('f64bits',bits[n%16]);n+=1;return value
    def vec():return obj(x=f(),y=f(),z=f())
    spheres=[obj(id=('u64',identity),position=vec(),velocity=vec(),mass=f(),force=vec(),gravity=vec(),radius=f()) for identity in [2**64-1,2**53+1]]
    need(n==28,'Explicit held-input scalar count')
    cells=[obj(time_bounds=('array',[('f64bits',a),('f64bits',b)]),depth=('u32',depth)) for a,b,depth in [(2**63,0,0),(0x3ff0000000000000,0xbff0000000000000,2**32-1)]]
    worlds=[]
    for j in range(2):
        body=obj(id=('u64',2**64-2 if j else 0),is_static=('bool',j==0),mass=f(),inertia_diagonal=vec(),radius=f(),
            position=vec(),velocity=vec(),angular_momentum=vec(),orientation=obj(x=f(),y=f(),z=f(),w=f()),force=vec(),torque=vec(),material=obj(restitution=f(),friction=f()))
        worlds.append(obj(body=body,gravity=vec()))
    need(n==86,'All26 body and3 gravity scalars per snapshot')
    return 0x52485331,('array',spheres+cells+worlds)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every held original field, both seconds endpoints/depth and full selected-body bit/flag/ID')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits'];need(len(leaves)==98 and len(floats)==90,'Complete typed leaves')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=3,mappedFields=11,fixtureRecords=6,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
        u64Fields=sum(k=='u64' for k,_ in leaves),u32Fields=sum(k=='u32' for k,_ in leaves),boolFields=sum(k=='bool' for k,_ in leaves),
        scope='Six artificial held source/cell/selected-body values; all raw domains retained, no model call or time-window certification. Full held Result/Report/C API pump/JS/WASM/game remain outside scope.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
