"""Independent exact typed oracle for real Interval accessors and SqrtResult diagnostics."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('diagnostic_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def bounds(lo,hi):return obj(lower=('f64bits',lo),upper=('f64bits',hi))
    def root(lo,hi,n,limited):return obj(value=bounds(lo,hi),refinements=('u32',n),refinement_limited=('bool',limited))
    zero=0x8000000000000000;inf=0x7ff0000000000000;one=0x3ff0000000000000;two=0x4000000000000000
    intervals=[bounds(zero,0),bounds(zero|1,1),bounds(1,1),bounds(0xffefffffffffffff,0x7fefffffffffffff),
        bounds(zero|inf,inf),bounds(zero|inf,zero|one),bounds(one,inf),bounds(zero,one),bounds(zero|one,0)]
    roots=[root(two,two,0,False),root(one,0x3ff8000000000000,1,True),root(one,two,0,False),root(zero,0,0,False),root(zero|inf,inf,2**32-1,True)]
    return 0x52495631,('array',intervals+roots)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every actual normalized endpoint bit, sqrt diagnostic and order')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits'];need(len(leaves)==38 and len(floats)==28,'All typed values')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=5,fixtureRecords=14,
        allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),u32Fields=sum(k=='u32' for k,_ in leaves),booleanFields=sum(k=='bool' for k,_ in leaves),
        scope='Real accessor output and four actual old sqrt calls plus one synthetic public SqrtResult. Not a new interval/sqrt numerical proof, complete Report/pump or JS/WASM/game acceptance.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
