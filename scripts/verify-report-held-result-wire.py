"""Independent complete held Result oracle using independently specified nested value fixtures."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def dependency(name):
    spec=importlib.util.spec_from_file_location('held_result_'+name,ROOT/('scripts/verify-report-'+name+'-wire.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
original=dependency('held-source');inputs=dependency('held-snapshot-work');proofs=dependency('held-proofs');audits=dependency('held-audits');wire=original.wire

def need(v,m):
    if not v:raise ValueError(m)

def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def u(v):return ('u64',v)
    def uint(v):return ('u32',v)
    def opt(yes,make):return ('present',make()) if yes else ('absent',None)
    def array(values):return ('array',values)
    old=original.expected()[1][1];snapshots=inputs.expected()[1][1];proof=proofs.expected()[1][1];rows=audits.expected()[1][1]
    pairs=[(2**63,0),(0x8000000000000001,1),(1,0x0010000000000000),(0xffefffffffffffff,0x7fefffffffffffff),
           (0xfff0000000000000,0x7ff0000000000000),(0xfff0000000000000,0xbff0000000000000),(0x3ff0000000000000,0x7ff0000000000000),(0x3ff0000000000000,0x3ff8000000000000)]
    ni=0
    def bound():
        nonlocal ni
        a,b=pairs[ni%8];ni+=1;return obj(lower=('f64bits',a),upper=('f64bits',b))
    def bounds():return array([bound(),bound(),bound()])
    triangles=dict(snapshots[1][1])[b'triangles'][1]
    mesh0=obj(status=('enum',2**32-1),reason=('enum',2**31+1),failed_index=('present',u(2**64-1)),first_failed_row=('present',u(0)),
              rows=array([obj(triangle=t,query=('absent',None)) for t in triangles[:2]]),
              nearest=('present',obj(squared_distance=bound(),distance=bound(),gap=bound(),possible_surface_ids=array([u(2**64-1),u(2**53+1),u(2**64-1)]))),
              queries=u(1),candidates_examined=u(2**53+1),sqrt_refinements=u(2**64-1),sqrt_limited_rows=u(255),failed_rows=u(256),message=('bytes',b'\x00\xff\xc0'))
    mesh1=obj(status=('enum',2**31+2),reason=('enum',2**32-2),failed_index=('absent',None),first_failed_row=('present',u(2**64-1)),rows=array([]),nearest=('absent',None),
              queries=u(17),candidates_examined=u(18),sqrt_refinements=u(19),sqrt_limited_rows=u(20),failed_rows=u(21),message=('bytes',b'mesh\x00x'))
    sizes=[0,1,3,255,256,257,16,513,2,4,8,32,64,128,260];results=[]
    for j,mask in enumerate([0,8191]+[1<<k for k in range(13)]):
        first=j==1;which=0 if first else 1;indices=[0,1,0] if j==1 else [1,0] if j==2 else []
        message=bytes((k*37+j*19)%256 for k in range(sizes[j]))
        if j==1:message=b'\x00'
        if j==2:message=b'\x00\xff\xc0'
        work=obj(mesh_queries=u(11+j),primitive_queries=u(2**64-1-j),candidates_examined=u(2**53+1+j),primitive_sqrt_refinements=u(2**63+j),
                 enclosure_sqrt_refinements=u(100+j),sqrt_refinements=u(200+j),sqrt_refinements_upper=u(300+j),mesh_sqrt_limited_rows=u(400+j),enclosure_sqrt_calls=u(500+j),enclosure_sqrt_limited_calls=u(600+j),exact=('bool',j%2==0))
        results.append(obj(status=('enum',2**32-1 if j==14 else j),reason=('enum',2**31+j),failed_index=opt(mask&1,lambda:u(0 if first else 2**64-1)),
            snapshot=opt(mask&2,lambda:snapshots[which]),world_body=opt(mask&4,lambda:old[4+which]),acceleration=opt(mask&8,bounds),whole_path_bounds=opt(mask&16,bounds),whole_velocity_bounds=opt(mask&32,bounds),
            initial=opt(mask&64,lambda:proof[which]),initial_separation_proven=('bool',j%2!=0),certified_leaves=array([proof[2+k] for k in indices]),
            safe_prefix=opt(mask&128,lambda:array([('f64bits',2**63),('f64bits',0)] if first else [('f64bits',0x3ff0000000000000),('f64bits',0xbff0000000000000)])),
            best_witness=opt(mask&256,lambda:proof[4+which]),window=opt(mask&512,lambda:proof[6+which]),candidate_surface_ids=array([u(2**53+1 if k else 2**64-1) for k in indices]),
            partition=array([rows[17 if k else 14] for k in indices]),frontier=array([old[2+k] for k in indices]),current=opt(mask&1024,lambda:old[2+which]),
            audits=array([rows[k] for k in indices]),last_mesh=opt(mask&2048,lambda:mesh0 if first else mesh1),last_mesh_audit_index=opt(mask&4096,lambda:u(2**53+1 if first else 2**64-1)),
            work=work,partition_leaves=u(2**64-1-j if j else 0),maximum_depth=uint(2**32-1-j),message=('bytes',message)))
    need(ni==21,'All stored interval boxes including mesh nearest')
    return 0x52485231,array(results)

def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every full held Result field, complete source/nested diagnostics, all islands/tail/frontier/audits, presence and raw bytes')
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
    names='failed_index snapshot world_body acceleration whole_path_bounds whole_velocity_bounds initial safe_prefix best_witness window current last_mesh last_mesh_audit_index'.split();masks=[]
    for record in actual[1][1]:
        fields=dict(record[1]);masks.append(sum(1<<k for k,name in enumerate(names) if fields[name.encode()][0]=='present'))
    need(masks==[0,8191]+[1<<k for k in range(13)],'Every outer optional individually present and absent')
    pair_count=sum(len({((m>>a)&1,(m>>b)&1) for m in masks}) for a in range(13) for b in range(a+1,13))
    need(pair_count==312 and (present,absent)==(56,212) and len(messages)==17 and sum(map(len,messages))==1808,'All outer pairs and full nested presence/messages')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=1,mappedFields=25,fixtureRecords=15,outerPresenceMasks=masks,outerPresencePairCombinations=pair_count,
        optionalPresent=present,optionalAbsent=absent,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
        u64Fields=sum(k=='u64' for k,_ in leaves),u32Fields=sum(k=='u32' for k,_ in leaves),enumFields=sum(k=='enum' for k,_ in leaves),boolFields=sum(k=='bool' for k,_ in leaves),messageFields=len(messages),messageBytes=sum(map(len,messages)),
        scope='Artificial15 complete held Results, 13-optional pairwise coverage and all stored containers. No actual model query/proof/accounting, complete top-level Report, pump, JS/WASM/game acceptance.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
