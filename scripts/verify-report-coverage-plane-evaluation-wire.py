"""Independent artificial plane Evaluation oracle; valid constructed Interval endpoints only."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('plane_evaluation_wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    pairs=[(2**63,0),(0xfff0000000000000,0x7ff0000000000000),(0x3ff0000000000000,0x3ff0000000000000),(0xc000000000000000,0xbff0000000000000),(1,2),(0x8000000000000002,0x8000000000000001),(2**63,1),(0x8000000000000001,0),(0xfff0000000000000,0xbff0000000000000),(0x3ff0000000000000,0x7ff0000000000000),(0x7fefffffffffffff,0x7fefffffffffffff),(0x0010000000000000,0x0020000000000000)]
    def interval(index):
        lower,upper=pairs[index%12];return obj(lower=('f64bits',lower),upper=('f64bits',upper))
    rows=[obj(tube_coordinates=('array',[interval(5*i+j) for j in range(3)]),distance=interval(5*i+3),threshold=interval(5*i+4),gap=interval(5*i+5)) for i in range(8)]
    return 0x52434531,('array',rows)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every original axis, distance, threshold and gap Interval with original endpoint order')
    leaves=[];axes=[]
    def walk(node,path=''):
        kind,value=node
        if kind=='object':
            for k,v in value:walk(v,path+'/'+k.decode())
        elif kind=='array':
            if path.endswith('/tube_coordinates'):axes.append(len(value))
            for i,v in enumerate(value):walk(v,path+'/'+str(i))
        else:leaves.append(node)
    walk(actual[1]);need(len(leaves)==96 and all(k=='f64bits' for k,_ in leaves) and axes==[3]*8,'All96 F64 endpoints and all3 axes per root')
    zeros=sum(v==2**63 for _,v in leaves);need(zeros==8,'Eight constructed lower negative zeros')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=1,mappedFields=4,fixtureRecords=8,allTypedLeaves=96,mappedFloatBitValues=96,negativeZeroOccurrences=zeros,intervalRecords=48,threeAxisArrays=8,scope='Artificial8 Evaluation records only. Public Interval constructors and existing zero normalization; no tube/threshold/gap recomputation, numerical certification, whole plane Result/World Report/pump/JS/WASM/game connection.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
