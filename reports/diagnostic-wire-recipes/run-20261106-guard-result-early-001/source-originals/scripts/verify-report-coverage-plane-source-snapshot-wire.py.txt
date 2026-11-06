"""Independent exact-bit artificial plane Input/Snapshot oracle; no numerical model calls."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('plane_source_wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    bits=[0,2**63,1,0x8000000000000001,0x000fffffffffffff,0x0010000000000000,0x3ff0000000000000,0xbff0000000000000,0x7fefffffffffffff,0xffefffffffffffff,0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000042,0xfff8000000001234,0x7ff0000000000001,0xfff0000000000001]
    def f(i):return ('f64bits',bits[i%16])
    def input(index):
        n=3*index
        def scalar():
            nonlocal n
            value=f(n);n+=1;return value
        def vec():return obj(x=scalar(),y=scalar(),z=scalar())
        sphere=obj(center=vec(),velocity=vec(),acceleration=vec(),radius=scalar());plane=obj(normal=vec(),offset=scalar())
        return obj(sphere=sphere,plane=plane,position_error=scalar(),contact_margin=scalar())
    counts=[0,2**64-1,9007199254740993,2**63];depths=[0,32,2**31,2**32-1]
    inputs=[input(i) for i in range(8)]
    snapshots=[obj(input=input(i+8),horizon=f(i),settings=obj(time_tolerance=f(i+1),max_evaluations=('u64',counts[i%4]),max_leaves=('u64',counts[(i+1)%4]),max_depth=('u32',depths[i%4]))) for i in range(8)]
    return 0x52435042,('array',inputs+snapshots)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every original plane source/snapshot field and exact bit value in declaration order')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits'];need(len(leaves)==296 and len(floats)==272,'All296 typed leaves and272 F64')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=7,fixtureRecords=16,allTypedLeaves=296,mappedFloatBitValues=272,negativeZeroOccurrences=floats.count(2**63),u64Values=sum(k=='u64' for k,_ in leaves),u32Values=sum(k=='u32' for k,_ in leaves),scope='Artificial8 Input and8 Snapshot only. Declared scalar B/margin/raw normal/horizon/settings saved without query or input certification. Whole plane Result/World Report/pump/JS/WASM/game connection separate.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded capture');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
