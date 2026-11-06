"""Independent artificial sphere Evaluation oracle; valid constructed Interval endpoints only."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sphere_evaluation_wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    pairs=[(2**63,0),(0xfff0000000000000,0x7ff0000000000000),(0x3ff0000000000000,0x3ff0000000000000),(0xc000000000000000,0xbff0000000000000),(1,2),(0x8000000000000002,0x8000000000000001),(2**63,1),(0x8000000000000001,0),(0xfff0000000000000,0xbff0000000000000),(0x3ff0000000000000,0x7ff0000000000000),(0x7fefffffffffffff,0x7fefffffffffffff),(0x0010000000000000,0x0020000000000000)]
    def interval(index):
        lower,upper=pairs[index%12];return obj(lower=('f64bits',lower),upper=('f64bits',upper))
    counts=[0,1,2**31,2**32-1]
    rows=[obj(first_coordinates=('array',[interval(7*i+j) for j in range(3)]),
              second_coordinates=('array',[interval(7*i+3+j) for j in range(3)]),
              delta=('array',[interval(7*i+6+j) for j in range(3)]),
              raw_squared_distance=interval(7*i+9),nonnegative_squared_distance=interval(7*i+10),
              root=obj(value=interval(7*i+11),refinements=('u32',counts[i%4]),refinement_limited=('bool',bool(i&4))),
              distance=interval(7*i+12),threshold=interval(7*i+13),gap=interval(7*i+14)) for i in range(8)]
    return 0x52435345,('array',rows)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every original axis, distance, threshold and gap Interval with original endpoint order')
    leaves=[];axes=[]
    def walk(node,path=''):
        kind,value=node
        if kind=='object':
            for k,v in value:walk(v,path+'/'+k.decode())
        elif kind=='array':
            if path.rsplit('/',1)[-1] in ['first_coordinates','second_coordinates','delta']:axes.append(len(value))
            for i,v in enumerate(value):walk(v,path+'/'+str(i))
        else:leaves.append(node)
    walk(actual[1]);need(len(leaves)==256 and sum(k=='f64bits' for k,_ in leaves)==240 and axes==[3]*24,'All256 leaves,240 F64 endpoints and24 three-axis arrays')
    roots=[dict(fields)[b'root'] for _,fields in actual[1][1]]
    need(len({(dict(fields)[b'refinements'][1],dict(fields)[b'refinement_limited'][1]) for _,fields in roots})==8,'All4 counts with both flags')
    need(all(not wire.typed_equal(dict(dict(fields)[b'root'][1])[b'value'],dict(fields)[b'distance']) for _,fields in actual[1][1]),'All8 original root/distance copies deliberately different')
    zeros=sum(k=='f64bits' and v==2**63 for k,v in leaves)
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=1,mappedFields=9,fixtureRecords=8,allTypedLeaves=256,mappedFloatBitValues=240,negativeZeroOccurrences=zeros,intervalRecords=120,threeAxisArrays=24,u32Fields=8,booleanFields=8,allCountFlagPairs=8,deliberatelyDifferentRootDistanceCopies=8,scope='Artificial8 Evaluation records, valid public Interval construction and synthetic SqrtResult only. No distance/root recomputation or numerical/World Report/pump/WASM/game certification.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
