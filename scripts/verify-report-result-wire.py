"""Independent typed Result oracle: optionals, ordered diagnostic prefixes and opaque message bytes."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
geometry=load('geometry_reference','scripts/verify-report-geometry-wire.py');wire=geometry.wire
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def interval(n):
        pairs=[(2**63,0),(0x8000000000000001,1),(1,0x0010000000000000),
            (0xffefffffffffffff,0x7fefffffffffffff),(0xfff0000000000000,0x7ff0000000000000),
            (0xfff0000000000000,0xbff0000000000000),(0x3ff0000000000000,0x7ff0000000000000),(0x3ff0000000000000,0x3ff8000000000000)]
        lo,hi=pairs[n%8];return obj(lower=('f64bits',lo),upper=('f64bits',hi))
    def optional(condition,child):return ('present',child) if condition else ('absent',None)
    first,second,normal,other=geometry.expected()[1][1];rows=[]
    counts=[0,1,2,3,0,2,1,3];sizes=[0,3,255,256,257,1,16,513]
    for j in range(8):
        message=bytes((k*37+j*19)%256 for k in range(sizes[j]))
        if j==1:message=b'\x00\xff\xc0'
        if j==5:message=b'\x00'
        rows.append(obj(status=('enum',2**32-1 if j==7 else j),reason=('enum',2**31+j),
            geometry=optional(j&1,other if j&2 else normal),squared_cross=optional(j&2,interval(j*2)),sine_squared=optional(j&4,interval(j*2+1)),
            candidates=('array',[second if (j+k)%2 else first for k in range(counts[j])]),
            candidates_examined=('u32',2**32-1-j),sqrt_refinements=('u32',2**31+j),sqrt_refinement_limited=('bool',bool(j&1)),message=('bytes',message)))
    return 0x52535431,('array',rows)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every Result field, optional presence/child, candidate order/duplicates and opaque message byte')
    leaves=[];present=absent=0
    def walk(node):
        nonlocal present,absent
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        elif kind=='present':present+=1;walk(value)
        elif kind=='absent':absent+=1
        else:leaves.append(node)
    walk(actual[1]);need(present==12 and absent==12,'All8 optional combinations')
    messages=[v for k,v in leaves if k=='bytes'];need([len(v) for v in messages]==[0,3,255,256,257,1,16,513],'Exact message boundaries')
    floats=[v for k,v in leaves if k=='f64bits']
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=1,mappedFields=10,fixtureRecords=8,
        optionalPresent=present,optionalAbsent=absent,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
        messageBytes=sum(map(len,messages)),messageSizes=list(map(len,messages)),
        scope='Eight artificial public Results; no geometry query or mathematical acceptance. Complete Result data only; full Report/C API pump/JS/WASM/game remain unimplemented.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
