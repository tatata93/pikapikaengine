"""Independent typed complete mesh Result oracle, including U64 optional positions and all rows."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mesh_values_reference',ROOT/'scripts/verify-report-mesh-values-wire.py');mesh=importlib.util.module_from_spec(spec);spec.loader.exec_module(mesh);wire=mesh.wire
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def opt(yes,value):return ('present',value) if yes else ('absent',None)
    values=mesh.expected()[1][1];rows=values[:3];nearest=values[3:];results=[];maximum=2**64-1
    counts=[0,1,2,3,0,2,1,3];sizes=[0,1,3,255,256,257,16,513]
    for j in range(8):
        failed=0 if j==1 else (2**53+1 if j==3 else (maximum if j==5 else maximum-j))
        first=0 if j==2 else (maximum if j==3 else 2**53+j)
        message=bytes((k*37+j*19)%256 for k in range(sizes[j]))
        if j==1:message=b'\x00'
        if j==2:message=b'\x00\xff\xc0'
        results.append(obj(status=('enum',maximum%2**32 if j==7 else j),reason=('enum',2**31+j),
            failed_index=opt(j&1,('u64',failed)),first_failed_row=opt(j&2,('u64',first)),
            rows=('array',[rows[(j+(0 if k==2 else k))%3] for k in range(counts[j])]),nearest=opt(j&4,nearest[j%3]),
            queries=('u64',maximum-j if j else 0),candidates_examined=('u64',2**53+1+j if j else 0),
            sqrt_refinements=('u64',2**63+j if j else 0),sqrt_limited_rows=('u64',17*j),failed_rows=('u64',maximum-101*j if j else 0),message=('bytes',message)))
    return 0x524d5231,('array',results)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'All mesh Result fields, exact optional U64s, ordered full rows/nearest and arbitrary message bytes')
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
    need(len(leaves)==602 and len(floats)==416 and present==36 and absent==21,'All typed nested values including presence')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=1,mappedFields=12,fixtureRecords=8,outerOptionalCombinations=8,
        optionalPresent=present,optionalAbsent=absent,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
        u64Leaves=sum(k=='u64' for k,_ in leaves),messageFields=len(messages),messageBytes=sum(map(len,messages)),rowCounts=[0,1,2,3,0,2,1,3],
        scope='Eight artificial complete mesh Results. Diagnostic domain violations retained, not admitted geometry queries. Complete top-level Report/C API pump/JS/WASM/game remain outside scope.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
