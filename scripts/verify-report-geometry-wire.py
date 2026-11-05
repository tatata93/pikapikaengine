"""Independent exact typed oracle for CandidateAudit and Geometry, including all fixed slots."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('diagnostic_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def e(v):return ('enum',v)
    def u(v):return ('u32',v)
    def interval(n):
        table=[(0x8000000000000000,0),(0x8000000000000001,1),(1,0x0010000000000000),
            (0xffefffffffffffff,0x7fefffffffffffff),(0xfff0000000000000,0x7ff0000000000000),
            (0xfff0000000000000,0xbff0000000000000),(0x3ff0000000000000,0x7ff0000000000000),(0x3ff0000000000000,0x3ff8000000000000)]
        lo,hi=table[n%8];return obj(lower=('f64bits',lo),upper=('f64bits',hi))
    def array(*indices):return ('array',[interval(n) for n in indices])
    first=obj(feature=e(6),disposition=e(2),barycentric=array(0,1,2),kkt=array(3,4),kkt_count=u(0))
    second=obj(feature=e(2**32-1),disposition=e(0x80000001),barycentric=array(5,6,7),kkt=array(8,9),kkt_count=u(2**32-1))
    def geometry(other):return obj(surface_id=('u64',2**53+1 if other else 2**64-1),surviving_features=u(0 if other else 2**32-1),
        barycentric=array(10,11,12),closest_local=array(13,14,15),closest=array(16,17,18),delta=array(19,20,21),
        normal=array(31,32,33) if other else array(22,23,24),sphere_point=array(25,26,27),
        squared_distance=interval(28),distance=interval(34 if other else 29),gap=interval(30),relation=e(3 if other else 2**32-1))
    return 0x52475431,('array',[first,second,geometry(False),geometry(True)])
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every ordinal/mask/full64 ID, all3 Bounds3 components, both KKT slots and endpoint bit')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits'];need(len(leaves)==116 and len(floats)==104,'All typed geometry values')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=17,fixtureRecords=4,
        allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),u32Fields=sum(k=='u32' for k,_ in leaves),u64Fields=sum(k=='u64' for k,_ in leaves),enumFields=sum(k=='enum' for k,_ in leaves),
        scope='Four artificial public CandidateAudit/Geometry records; no geometry query executed. Invalid ordinals/masks/counts retained as diagnostics, not admitted model results. No full Result/Report/pump or JS/WASM/game acceptance.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
