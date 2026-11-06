"""Independent raw binary64 sphere-pair/sphere-plane original input oracle; no model calls."""
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
    spheres=[obj(center=vec(),velocity=vec(),acceleration=vec(),radius=f()) for _ in range(2)]
    planes=[obj(normal=vec(),offset=f()) for _ in range(2)]
    need(n==28,'Exactly28 original binary64 coefficients')
    pairs=[obj(first=spheres[0],second=spheres[1]),obj(first=spheres[1],second=spheres[0])]
    sphere_planes=[obj(sphere=spheres[0],plane=planes[0]),obj(sphere=spheres[1],plane=planes[1])]
    inputs=[('variant',(0,x)) for x in pairs]+[('variant',(1,x)) for x in sphere_planes]
    counts=[0,2**64-1,9007199254740993,2**63];depths=[0,2**32-1,31,32]
    snapshots=[obj(input=inputs[i%4],horizon=('f64bits',bits[i]),settings=obj(time_tolerance=('f64bits',bits[(i+5)%16]),max_evaluations=('u64',counts[i%4]),max_leaves=('u64',counts[(i+1)%4]),max_depth=('u32',depths[(i+2)%4]))) for i in range(16)]
    return 0x52435331,('array',snapshots)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every named first/second and sphere/plane original input with exact IEEE bits/order')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='variant':walk(value[1])
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);need(len(leaves)==352 and sum(k=='f64bits' for k,_ in leaves)==304 and sum(k=='u64' for k,_ in leaves)==32 and sum(k=='u32' for k,_ in leaves)==16,'All352 typed leaves')
    floats=[v for k,v in leaves if k=='f64bits'];need(floats.count(2**63)==26,'All26 negative zeros')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=1,mappedFields=3,mappedVariants=0,fixtureRecords=16,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
        scope='Sixteen artificial Snapshots, all304 binary64 values including nonfinite horizon/tolerance payloads,32 U64 and16 U32, original0/1 variant; no normalization, sorting, model acceptance, numeric query, full Report/pump or JS/WASM/game connection.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
