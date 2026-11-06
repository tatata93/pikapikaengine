"""Independent complete artificial Audit/PartitionLeaf oracle; no model query."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def opt(yes,v):return ('present',v) if yes else ('absent',None)
    def f(bits):return ('f64bits',bits)
    bits=[0,2**63,1,0x8000000000000001,0x000fffffffffffff,0x0010000000000000,0x3ff0000000000000,0xbff0000000000000,0x7fefffffffffffff,0xffefffffffffffff,0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000042,0xfff8000000001234,0x7ff0000000000001,0xfff0000000000001]
    counts=[0,2**64-1,9007199254740993,2**63];depths=[0,2**32-1,31,32];kinds=[0,1,2,3,2**31,2**32-1];reasons=list(range(17))+[2**31,2**32-1]
    intervals=[(9223372036854775808, 0), (18442240474082181120, 9218868437227405312), (4607182418800017408, 4607182418800017408), (13835058055282163712, 13830554455654793216), (1, 2), (9223372036854775810, 9223372036854775809), (9223372036854775808, 1), (9223372036854775809, 0), (18442240474082181120, 13830554455654793216), (4607182418800017408, 9218868437227405312), (9218868437227405311, 9218868437227405311), (4503599627370496, 9007199254740992)]
    def evaluation(index):
        def part(j):
            lo,hi=intervals[(5*index+j)%12];return obj(lower=f(lo),upper=f(hi))
        return obj(tube_coordinates=('array',[part(0),part(1),part(2)]),distance=part(3),threshold=part(4),gap=part(5))
    audits=[]
    for i in range(20):
        cell=obj(time_bounds=('array',[f(bits[2*i%16]),f(bits[(2*i+1)%16])]),depth=('u32',depths[i%4]),parent_audit=opt(i&4,('u64',counts[i%4])))
        audits.append(obj(cell=cell,call_attempted=('bool',bool(i&8)),evaluation=opt(i&1,evaluation(i//2)),outcome=('enum',kinds[i%6]),blocked_reason=('enum',reasons[i%19]),split_time=opt(i&2,f(bits[(i+3)%16]))))
    leaves=[]
    for i in range(12):
        cell=obj(time_bounds=('array',[f(bits[(2*i+3)%16]),f(bits[(2*i+4)%16])]),depth=('u32',depths[(i+1)%4]),parent_audit=opt(i&2,('u64',counts[(i//4+i)%4])))
        leaves.append(obj(cell=cell,state=('enum',kinds[i%6]),audit_index=opt(i&1,('u64',counts[(i//2)%4])),blocked_reason=('enum',reasons[(i+7)%19])))
    return 0x52435041,('array',audits+leaves)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Complete original plane Audit/PartitionLeaf with exact type, field order and raw bits')
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
    walk(actual[1]);counts={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum']}
    need(counts==dict(f64bits=194,u64=20,u32=32,bool=20,enum=64) and len(leaves)==330,'Every330 typed leaf')
    need(present==40 and absent==44,'All84 optional boundaries')
    floats=[v for k,v in leaves if k=='f64bits'];need(floats.count(2**63)==15,'Raw negative zeros and constructed Interval negative-zero lower bounds')
    roots=actual[1][1];counts4={0,2**64-1,9007199254740993,2**63};audit_masks=set();audit_parents=set();partition_parents=set();indices=set()
    def fields(node):need(node[0]=='object','Object');return dict(node[1])
    def original_count(optional,values):
        if optional[0]=='present':need(optional[1][0]=='u64','Actual U64 optional');values.add(optional[1][1])
    for i,root in enumerate(roots):
        row=fields(root);cell=fields(row[b'cell']);parent=cell[b'parent_audit']
        if i<20:
            audit_masks.add((row[b'evaluation'][0]=='present',row[b'split_time'][0]=='present',parent[0]=='present',row[b'call_attempted'][1]));original_count(parent,audit_parents)
        else:original_count(parent,partition_parents);original_count(row[b'audit_index'],indices)
    need(len(audit_masks)==16 and audit_parents==partition_parents==indices==counts4,'All16 masks and each independent4-count set')
    need({v for k,v in leaves if k=='enum'}==set(range(17))|{2**31,2**32-1},'All known Reasons and two unknown unsigned ordinals')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=10,fixtureRecords=32,allTypedLeaves=330,mappedFloatBitValues=194,negativeZeroOccurrences=15,present=40,absent=44,auditBooleanPresenceMasks=16,eachCountBoundarySet=4,
        scope='Artificial20 plane Audit and12 PartitionLeaf. Public Interval constructors only, original optional/enum/index preserved; no model acceptance/query, full Result/Report/pump or JS/WASM/game connection.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
