"""Independent typed-field oracle for the twelve Native Report leaf types."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('diagnostic_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    bits=[int(x,16) for x in ['0','8000000000000000','1','8000000000000001','fffffffffffff','10000000000000',
        '3ff0000000000000','bff0000000000000','7fefffffffffffff','ffefffffffffffff','7ff0000000000000','fff0000000000000',
        '7ff8000000000042','fff8000000001234','7ff0000000000001','fff0000000000001']]
    n=0
    def f():
        nonlocal n
        x=('f64bits',bits[n%16]);n+=1;return x
    def obj(**fields):return ('object',[(k.encode(),v) for k,v in fields.items()])
    def vec():return obj(x=f(),y=f(),z=f())
    def quat():return obj(x=f(),y=f(),z=f(),w=f())
    def mat():return obj(restitution=f(),friction=f())
    def arr(items):return ('array',items)
    def u(x):return ('u64',x)
    body=obj(id=u(2**64-1),is_static=('bool',True),mass=f(),inertia_diagonal=vec(),radius=f(),position=vec(),velocity=vec(),
             angular_momentum=vec(),orientation=quat(),force=vec(),torque=vec(),material=mat());need(n==26,'Independent body26')
    plane=obj(id=u(2**53+1),normal=vec(),offset=f(),material=mat())
    vertices=[vec() for _ in range(3)];triangle=obj(id=u(0),vertices=arr(vertices))
    mesh=obj(id=u(2**64-1),revision=u(2**53+1),triangles=arr([triangle,obj(id=u(0),vertices=arr(list(reversed(vertices))))]))
    loads=[obj(body_id=u(i),force_newtons=vec(),torque_newton_meters=vec()) for i in [0,2**64-1,0]]
    packet=obj(mode=('enum',2**32-1),expected_tick=u(2**64-1),loads=arr(loads))
    vector=vec();quaternion=quat();progress=obj(time=f(),ticks=u(2**64-1))
    settings=obj(step_seconds=f(),max_attempts_per_pump=u(2**64-1))
    snapshot=obj(settings=obj(step_seconds=f(),max_attempts_per_pump=u(0)),backlog=f(),sequence=u(2**64-1),busy=('bool',True))
    need(n==70,'Independent generator70')
    material=dict(body[1])[b'material']
    return 0x52564c31,arr([body,plane,triangle,mesh,loads[0],packet,progress,settings,snapshot,vector,quaternion,material,
        obj(id=u(0),revision=u(2**64-1),triangles=arr([])),obj(mode=('enum',0),expected_tick=u(0),loads=arr([]))])
def verify(data):
    actual=wire.decode(data);wanted=expected();need(wire.typed_equal(actual,wanted),'All exact typed Native fields/ordering/bit patterns')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits'];need(len(floats)==96,'All96 F64 leaves')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=12,fixtureRecords=14,
        mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),allTypedLeaves=len(leaves),
        scope='Leaf values only; deliberately invalid physical inputs are preserved data. No complete Report/pump/model/allocator or JS/WASM/game acceptance.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
