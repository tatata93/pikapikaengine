"""Independent complete free flight Result oracle; signed failure payload and original nested values."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def dependency(name):
    spec=importlib.util.spec_from_file_location('flight_result_'+name,ROOT/('scripts/verify-report-'+name+'-wire.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
inputs=dependency('flight-source-tube');endpoints=dependency('flight-endpoint');held_inputs=dependency('held-snapshot-work');wire=inputs.wire
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def u(v):return ('u64',v)
    def uint(v):return ('u32',v)
    def array(v):return ('array',v)
    def opt(yes,value):return ('present',value) if yes else ('absent',None)
    def field(node,name):return dict(node[1])[name.encode()]
    def replace(node,name,value):return ('object',[(k,value if k==name.encode() else v) for k,v in node[1]])
    free=inputs.expected()[1][1];audits=endpoints.expected()[1][1];old=held_inputs.expected()[1][1]
    held_snapshot=replace(old[0],'input',replace(field(old[0],'input'),'radius',('f64bits',0x4000000000000000)))
    absent=('absent',None)
    held=obj(status=('enum',4),reason=('enum',21),failed_index=absent,snapshot=('present',held_snapshot),world_body=absent,
        acceleration=absent,whole_path_bounds=absent,whole_velocity_bounds=absent,initial=absent,initial_separation_proven=('bool',False),certified_leaves=array([]),
        safe_prefix=('present',array([('f64bits',2**63),('f64bits',0)])),best_witness=absent,window=absent,candidate_surface_ids=array([u(2**64-1),u(2**53+1),u(2**64-1)]),
        partition=array([]),frontier=array([obj(time_bounds=array([('f64bits',2**63),('f64bits',0)]),depth=uint(0)),obj(time_bounds=array([('f64bits',0x3ff0000000000000),('f64bits',0xbff0000000000000)]),depth=uint(2**32-1))]),
        current=absent,audits=array([]),last_mesh=absent,last_mesh_audit_index=absent,work=old[4],partition_leaves=u(2**64-1),maximum_depth=uint(2**32-1),message=('bytes',b'\0held\xff'))
    world=obj(body=field(free[2],'body'),gravity=field(free[0],'gravity'))
    sizes=[0,1,3,255,256,257,16,513,2,4];records=[]
    for j,mask in enumerate([0,255]+[1<<k for k in range(8)]):
        first=j==1;which=0 if first else 1
        snapshot=replace(free[which],'body',replace(field(free[which],'body'),'radius',('f64bits',0x3ff0000000000000)))
        tube=replace(free[3+which],'guard_radius',('f64bits',0x4008000000000000))
        message=bytes((k*37+j*19)%256 for k in range(sizes[j]))
        if j==1:message=b'\0'
        if j==2:message=b'\0\xff\xc0'
        records.append(obj(status=('enum',j),reason=('enum',2**31+j),failed_index=opt(mask&1,u(0 if first else 2**64-1)),world_body=opt(mask&2,world),
            snapshot=opt(mask&4,snapshot),tube=opt(mask&8,tube),flight_failure=opt(mask&16,('enum',2**32-1 if first else 2**31)),candidate_evaluated=('bool',j%2!=0),
            endpoint=opt(mask&32,audits[7 if first else 0]),inflated=opt(mask&64,held),candidate=opt(mask&128,field(free[2],'body')),message=('bytes',message)))
    for value in list(range(13))+[-1,-2,-2**31,2**31-1]:
        records.append(obj(status=('enum',2),reason=('enum',0),failed_index=absent,world_body=absent,snapshot=absent,tube=absent,flight_failure=('present',('enum',value%(2**32))),
            candidate_evaluated=('bool',False),endpoint=absent,inflated=absent,candidate=absent,message=('bytes',b'')))
    return 0x52465231,array(records)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every complete original free flight Result field, signed enum payload, nested presence, raw bits and bytes')
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
    names='failed_index world_body snapshot tube flight_failure endpoint inflated candidate'.split();masks=[]
    for record in actual[1][1][:10]:
        fields=dict(record[1]);masks.append(sum(1<<k for k,name in enumerate(names) if fields[name.encode()][0]=='present'))
    need(masks==[0,255]+[1<<k for k in range(8)],'Each optional individually present/absent')
    pairs=sum(len({((m>>a)&1,(m>>b)&1) for m in masks}) for a in range(8) for b in range(a+1,8))
    need(pairs==112 and (present,absent)==(37,205) and len(messages)==29 and sum(map(len,messages))==1319,'Complete nested presence/messages and all outer pairs')
    need(len(floats)==357 and len(leaves)==589,'All589 typed leaves including357 stored F64 values')
    signed=[]
    for node in actual[1][1][10:]:
        payload=dict(node[1])[b'flight_failure'][1][1];signed.append(payload if payload<2**31 else payload-2**32)
    need(signed==list(range(13))+[-1,-2,-2**31,2**31-1],'All13 known ordinals and4 signed boundary/negative patterns')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=1,mappedFields=12,fixtureRecords=27,outerPresenceMasks=masks,outerPresencePairCombinations=pairs,
        signedFailureValues=signed,knownFailureOrdinals=13,artificialSignedFailureValues=4,optionalPresent=present,optionalAbsent=absent,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),
        u64Fields=sum(k=='u64' for k,_ in leaves),u32Fields=sum(k=='u32' for k,_ in leaves),enumFields=sum(k=='enum' for k,_ in leaves),boolFields=sum(k=='bool' for k,_ in leaves),messageFields=len(messages),messageBytes=sum(map(len,messages)),
        scope='Artificial27 full free flight Results, 8-optional pairwise coverage and signed enum representation. No model query, propagation/containment proof, full top-level Report, pump, JS/WASM/game acceptance.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
