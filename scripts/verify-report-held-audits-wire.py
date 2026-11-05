"""Independent typed held audit and partition oracle, not model certification."""
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
    def opt(yes,make):return ('present',make()) if yes else ('absent',None)
    records=[];masks=[0,4095]+[1<<k for k in range(12)]
    for j,mask in enumerate(masks):
        audit=obj(kind=('enum',2**32-1-j if j else 0),cell=cell(2**32-1-j if j else 0),time=f(),outcome=('enum',2**31+j),
            path_bounds=opt(mask&1,bounds),point_bounds=opt(mask&2,bounds),anchor=opt(mask&4,lambda:obj(x=f(),y=f(),z=f())),mesh_queried=('bool',j%2!=0),
            mesh_status=opt(mask&8,lambda:('enum',2**32-1-j)),mesh_reason=opt(mask&16,lambda:('enum',2**31+j)),
            distance=opt(mask&32,bound),displacement_squared_bound=opt(mask&64,bound),error_squared_bound=opt(mask&128,bound),
            displacement_root=opt(mask&256,bound),error_root=opt(mask&512,bound),clearance_certificate=opt(mask&1024,bound),penetration_certificate=opt(mask&2048,bound),
            work=obj(mesh_queries=u(j),primitive_queries=u(2**64-1-j),candidates_examined=u(2**53+1+j),primitive_sqrt_refinements=u(2**63+j),
                enclosure_sqrt_refinements=u(100+j),sqrt_refinements=u(200+j),sqrt_refinements_upper=u(300+j),mesh_sqrt_limited_rows=u(400+j),enclosure_sqrt_calls=u(500+j),enclosure_sqrt_limited_calls=u(600+j),exact=('bool',j%2==0)))
        records.append(audit)
    for j in range(4):
        index=[None,0,2**53+1,2**64-1][j]
        records.append(obj(cell=cell(2**32-1-j if j else 0),state=('enum',2**32-1-j if j else 0),audit_index=opt(j!=0,lambda:u(index)),blocked_reason=('enum',2**31+j)))
    need((ni,nf)==(26,56),'All initialized intervals and public F64 scalars')
    return 0x52484131,('array',records)

def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every audit/partition field, exact presence, enum tag, array axes, work delta and source audit index')
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
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits']
    need(len(leaves)==337 and len(floats)==108 and (present,absent)==(27,145),'All337 typed leaves and172 optional slots')
    names='path_bounds point_bounds anchor mesh_status mesh_reason distance displacement_squared_bound error_squared_bound displacement_root error_root clearance_certificate penetration_certificate'.split()
    masks=[]
    for record in actual[1][1][:14]:
        fields=dict(record[1]);masks.append(sum(1<<k for k,name in enumerate(names) if fields[name.encode()][0]=='present'))
    need(masks==[0,4095]+[1<<k for k in range(12)],'All explicit presence masks')
    pairs=sum(len({((m>>a)&1,(m>>b)&1) for m in masks}) for a in range(12) for b in range(a+1,12))
    need(pairs==264,'All four combinations for each of66 optional pairs')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=22,fixtureRecords=18,auditPresenceMasks=masks,pairPresenceCombinations=pairs,
                optionalPresent=present,optionalAbsent=absent,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
                u64Fields=sum(k=='u64' for k,_ in leaves),u32Fields=sum(k=='u32' for k,_ in leaves),enumFields=sum(k=='enum' for k,_ in leaves),boolFields=sum(k=='bool' for k,_ in leaves),
                scope='Artificial14 CellAudit and4 PartitionLeaf values, pairwise12-optional presence coverage. No actual model accounting/proof, full held Result/Report, pump, JS/WASM/game acceptance.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
