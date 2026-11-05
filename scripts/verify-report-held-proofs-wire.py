"""Independent complete typed oracle for artificial held proof records, not model certification."""
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
    def fp(v):return ('f64bits',v)
    interval_bits=[(2**63,0),(0x8000000000000001,1),(1,0x0010000000000000),
                   (0xffefffffffffffff,0x7fefffffffffffff),(0xfff0000000000000,0x7ff0000000000000),
                   (0xfff0000000000000,0xbff0000000000000),(0x3ff0000000000000,0x7ff0000000000000),
                   (0x3ff0000000000000,0x3ff8000000000000)]
    bits=[0,2**63,1,0x8000000000000001,0x000fffffffffffff,0x0010000000000000,0x3ff0000000000000,0xbff0000000000000,
          0x7fefffffffffffff,0xffefffffffffffff,0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000042,0xfff8000000001234,0x7ff0000000000001,0xfff0000000000001]
    ni=nf=0
    def bound():
        nonlocal ni
        a,b=interval_bits[ni%8];ni+=1;return obj(lower=fp(a),upper=fp(b))
    def bounds():return ('array',[bound(),bound(),bound()])
    def f():
        nonlocal nf
        value=fp(bits[nf%16]);nf+=1;return value
    def cell(depth):return obj(time_bounds=('array',[f(),f()]),depth=uint(depth))
    initial=[obj(lower_gap_certificate=bound(),upper_gap_certificate=bound(),audit_index=u(v)) for v in [0,2**64-1]]
    leaves=[obj(cell=cell(2**32-1 if j else 0),lower_gap_certificate=bound(),audit_index=u(v)) for j,v in enumerate([2**53+1,2**63])]
    witnesses=[obj(cell=cell(2**32-2 if j else 1),time=f(),exact_path_bounds=bounds(),anchor=obj(x=f(),y=f(),z=f()),
                   error_upper=f(),upper_gap_certificate=bound(),audit_index=u(v)) for j,v in enumerate([2**64-2,1])]
    windows=[obj(time_bounds=('array',[f(),f()]),time_width=bound(),path_bounds=bounds(),l1_diameter_bound=bound(),witness_audit_index=u(v)) for v in [255,256]]
    need((ni,nf)==(24,22),'Every interval and public scalar explicitly generated')
    return 0x52485031,('array',initial+leaves+witnesses+windows)

def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every proof field, all interval endpoints/axis order, seconds and source audit index')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits']
    need(len(floats)==70 and len(leaves)==82,'All82 leaves including70 stored F64 endpoints/scalars')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=4,mappedFields=18,fixtureRecords=8,
                allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
                u64Fields=sum(k=='u64' for k,_ in leaves),u32Fields=sum(k=='u32' for k,_ in leaves),
                scope='Eight artificial proof records with initialized stored Interval values. No model query, proof validity, full held Result/Report, pump, JS/WASM/game acceptance.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
