"""Independent complete artificial pair Result oracle, reusing independently fixed child specifications."""
from pathlib import Path
import argparse,hashlib,importlib.util,itertools,json
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
wire=module('wire_reference','scripts/verify-diagnostic-wire.py')
snapshot_ref=module('snapshot_reference','scripts/verify-report-coverage-snapshot-wire.py')
audit_ref=module('audit_reference','scripts/verify-report-coverage-audit-partition-wire.py')
work_ref=module('work_reference','scripts/verify-report-coverage-cell-work-wire.py')
def need(v,m):
    if not v:raise ValueError(m)
def fields(node):need(node[0]=='object','Object');return dict(node[1])
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def opt(yes,v):return ('present',v) if yes else ('absent',None)
    snapshots=snapshot_ref.expected()[1][1];sources=audit_ref.expected()[1][1];audits=sources[:20];parts=sources[20:];cells=[fields(v)[b'cell'] for v in audits];works=work_ref.expected()[1][1][8:]
    counts=[0,2**64-1,9007199254740993,2**63];kinds=[0,1,2,3,2**31,2**32-1];reasons=list(range(15))+[2**31,2**32-1];records=[]
    for i in range(17):
        a=[audits[(i+j)%20] for j in range(i%3)];p=[parts[(i+j)%12] for j in range(i%3)];tail=[cells[(i+3*j)%20] for j in range(i%4)]
        if i==7:a=[audits[5],audits[3],audits[5]]
        if i==6:p=[parts[9],parts[3],parts[9]]
        if i==16:a=audits;p=parts;tail=[cells[0],cells[7],cells[0]]
        body=b'' if not i else bytes([0x41,i,0,255,128,0x42])
        if i==16:body=bytes(range(256))+b'\0'
        records.append(obj(status=('enum',kinds[i%6]),reason=('enum',reasons[i]),snapshot=opt(i&1,snapshots[(i//2)%16]),snapshot_validated=('bool',bool(i&1)^bool(i&2)),failed_input=opt(i&2,('u64',counts[(i//4+i)%4])),partition_complete=('bool',bool(i&2)^bool(i&4)),audits=('array',a),partition=('array',p),frontier=('array',tail),current=opt(i&4,cells[i%20]),work=works[(i+1)%4],message=('bytes',body)))
    return 0x52435231,('array',records)
def metrics(root):
    leaves=[];present=absent=variants=0
    def walk(node):
        nonlocal present,absent,variants
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        elif kind=='present':present+=1;walk(value)
        elif kind=='absent':absent+=1
        elif kind=='variant':variants+=1;walk(value[1])
        else:leaves.append(node)
    walk(root);floats=[v for k,v in leaves if k=='f64bits'];return dict(allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),present=present,absent=absent,nestedVariants=variants,leafKinds={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']})
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Complete original Result all12 fields, full child arrays, optional/variant and exact raw body')
    roots=actual[1][1];need(len(roots)==17,'All17 artificial Results');rows=[fields(x) for x in roots];masks=[];failed=set();bodies=[]
    for row in rows:
        masks.append((row[b'snapshot'][0]=='present',row[b'failed_input'][0]=='present',row[b'current'][0]=='present',row[b'snapshot_validated'][1],row[b'partition_complete'][1]))
        if row[b'failed_input'][0]=='present':failed.add(row[b'failed_input'][1][1])
        bodies.append(row[b'message'][1])
    need(len({r[:3] for r in masks[:8]})==8 and all(len({(r[a],r[b]) for r in masks[:8]})==4 for a,b in itertools.combinations(range(5),2)),'All8 optional masks and all40 pairwise flag combinations')
    need(failed=={0,2**64-1,9007199254740993,2**63},'All4 present source-position boundaries')
    need({row[b'reason'][1] for row in rows}==set(range(15))|{2**31,2**32-1},'All17 root reason ordinals')
    need(sum(map(len,bodies))==347 and set(bodies[-1])==set(range(256)) and bodies[-1].endswith(b'\0'),'Every original message byte and final257-byte two-chunk body')
    info=metrics(actual[1]);need(info==metrics(expected()[1]),'All complete child typed statistics')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=1,mappedFields=12,mappedVariants=0,fixtureRecords=17,**info,outerOptionalMasks=8,pairwiseFlagCombinations=40,presentFailedInputBoundaryValues=4,rootMessageBytes=347,scope='Artificial17 pair Results with all source20 Audit/12 PartitionLeaf in final root, original arrays/order/duplicates/tail/current, exact optional/variant/enum/body. No numerical query, full World Report/pump or JS/WASM/game connection.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
