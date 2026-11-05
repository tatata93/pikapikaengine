"""Independent complete Row/Nearest oracle; source triangle and unexamined query stay distinct."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('result_reference',ROOT/'scripts/verify-report-result-wire.py');result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);wire=result.wire
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def interval(n):
        pairs=[(2**63,0),(0x8000000000000001,1),(1,0x0010000000000000),(0xffefffffffffffff,0x7fefffffffffffff),
            (0xfff0000000000000,0x7ff0000000000000),(0xfff0000000000000,0xbff0000000000000),(0x3ff0000000000000,0x7ff0000000000000),(0x3ff0000000000000,0x3ff8000000000000)]
        lo,hi=pairs[n%8];return obj(lower=('f64bits',lo),upper=('f64bits',hi))
    coords=[2**63,1,0x8000000000000001,0x7fefffffffffffff,0xffefffffffffffff,0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000042,0x3ff0000000000000]
    points=[obj(x=('f64bits',coords[n]),y=('f64bits',coords[n+1]),z=('f64bits',coords[n+2])) for n in [0,3,6]]
    results=result.expected()[1][1];rows=[]
    for j,identity in enumerate([2**64-1,2**53+1,0]):
        triangle=obj(id=('u64',identity),vertices=('array',points[j:]+points[:j]))
        rows.append(obj(triangle=triangle,query=('absent',None) if j==0 else ('present',results[j+5])))
    ids=[[],[0,2**64-1,2**53+1,2**64-1],[2**53+1,2**64-1,0,2**64-1]]
    nearest=[obj(squared_distance=interval(j*3),distance=interval(j*3+1),gap=interval(j*3+2),possible_surface_ids=('array',[('u64',n) for n in ids[j]])) for j in range(3)]
    return 0x524d5631,('array',rows+nearest)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every Row source vertex/ID, actual optional query and all Nearest interval endpoints/ordered full64 IDs')
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
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits'];messages=[v for k,v in leaves if k=='bytes']
    need(len(leaves)==173 and len(floats)==135 and present==7 and absent==2,'All typed nested diagnostic values')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=6,fixtureRecords=6,rowRecords=3,nearestRecords=3,optionalPresent=present,optionalAbsent=absent,
        allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),messageSizes=list(map(len,messages)),nearestIDCounts=[0,4,4],
        scope='Six artificial Row/Nearest values. Raw invalid source domains and possible IDs preserve diagnostics, not accepted mesh query results. Complete mesh Result/Report/pump/JS/WASM/game remain outside scope.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
