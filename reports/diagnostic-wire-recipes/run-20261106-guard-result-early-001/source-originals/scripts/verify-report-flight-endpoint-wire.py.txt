"""Independent exact typed oracle for stored free flight endpoint audit fields, without model execution."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,struct
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)

def need(v,m):
    if not v:raise ValueError(m)

def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    pairs=[(2**63,0),(0x8000000000000001,1),(0xfff0000000000000,0x7ff0000000000000),
           (0xffefffffffffffff,0x7fefffffffffffff),(1,0x0010000000000000),
           (0x3ff0000000000000,0x7ff0000000000000),(0xfff0000000000000,0xbff0000000000000),
           (0x3ff0000000000000,0x3ff8000000000000)]
    def bits(v):return int.from_bytes(struct.pack('<d',v),'little')
    # Compare the stored Interval: a zero lower endpoint is canonical -0.
    pairs += [(bits(-1000-2*k),bits(1000+3*k)) for k in range(8,128)]
    def bound(k):
        a,b=pairs[k];return obj(lower=('f64bits',a),upper=('f64bits',b))
    def bounds(k):return ('array',[bound(k+a) for a in range(3)])
    audits=[obj(nominal_position=bounds(16*j),nominal_allowed=bounds(16*j+3),exact_position=bounds(16*j+6),
                exact_allowed=bounds(16*j+9),exact_difference=bounds(16*j+12),l1_error_bound=bound(16*j+15),
                nominal_contained=('bool',bool(j&1)),exact_contained=('bool',bool(j&2)),l1_within_tube=('bool',bool(j&4))) for j in range(8)]
    return 0x52464531,('array',audits)

def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every stored endpoint audit box/axis/endpoint and all3 separate containment flags')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits']
    need(len(floats)==256 and len(leaves)==280,'All280 typed leaves including256 stored interval endpoints')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=1,mappedFields=9,fixtureRecords=8,flagCombinations=8,
                allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
                u64Fields=sum(k=='u64' for k,_ in leaves),u32Fields=sum(k=='u32' for k,_ in leaves),boolFields=sum(k=='bool' for k,_ in leaves),
                scope='Eight artificial endpoint audits and all8 flag combinations. No actual propagation, containment proof, complete Report, pump, JS/WASM/game acceptance.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
