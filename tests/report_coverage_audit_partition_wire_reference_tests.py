"""Complete grammar-valid scalar/key, optional, enum, endpoint and ownership mutations."""
from pathlib import Path
import argparse,importlib.util,itertools,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit_partition_reference',ROOT/'scripts/verify-report-coverage-audit-partition-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
def verify(data):
    baseline=ref.verify(data);expected=ref.expected();pos=12;offsets=[];records=[];absents=[];presents=[];enums=[];named={};arrays={};objects={}
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded scanner');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        start=pos;tag=number(1)
        if tag in (2,3,4,6,8):
            size={2:1,3:4,4:8,6:8,8:4}[tag];offset=take(size);offsets.extend((path,offset+i,'value-byte') for i in range(size))
            if tag==8:enums.append(start)
            return
        if tag==11:absents.append(start);return
        if tag==12:value(path+'/present');need(number(1)==14,'Single optional child');presents.append((start,pos));return
        need(tag in (9,10),'Expected Audit/Partition grammar');elements=[];fields=[];index=0
        while data[pos]!=14:
            if tag==9:
                need(number(1)==15,'Key');size=number(8);offset=take(size);key=data[offset:pos].decode();need(size>0,'Nonempty key');offsets.extend((path+'/'+key,offset+i,'key-byte') for i in range(size));begin=pos;value(path+'/'+key);named[path+'/'+key]=(begin,pos);fields.append(key)
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos))
                if path=='':records.append((begin,pos))
                index+=1
        if tag==10 and path:arrays[path]=elements
        if tag==9:objects[path]=fields
        take(1)
    value('');need(data[take(1):pos]==b'\0' and pos==len(data),'Complete');need(len(records)==32 and len(absents)==44 and len(presents)==40 and len(enums)==64,'All artificial roots and optional/enum states')
    def refuses(changed):need(not ref.wire.typed_equal(ref.wire.decode(changed),expected),'Grammar-valid semantic change accepted')
    mutations=[]
    for path,offset,kind in offsets:
        changed=bytearray(data);changed[offset]^=1;refuses(bytes(changed));mutations.append(dict(path=path,byteOffset=offset,kind=kind))
    a,b=records[0];c,d=records[1]
    for changed in [data[:a]+data[c:d]+data[a:b]+data[d:],data[:a]+data[b:],data[:a]+data[a:b]+data[a:]]:refuses(changed)
    for offset in absents:refuses(data[:offset]+b'\1'+data[offset+1:])
    for a,b in presents:
        refuses(data[:a]+b'\x0b'+data[b:]);refuses(data[:a]+b'\1'+data[b:])
    for offset in enums:refuses(data[:offset]+b'\x03'+data[offset+1:])
    def exchange(left,right):
        a,b=left;c,d=right;need(a<b<=c<d,'Ordered source')
        changed=data[:a]+data[c:d]+data[b:c]+data[a:b]+data[d:]
        if changed==data:return False
        refuses(changed);return True
    endpoints=0;root_swaps=0;root_identity=0;cell_swaps=0;owner_swaps=0;owner_identity=0
    for i in range(32):
        path='/'+str(i);need(exchange(*arrays[path+'/cell/time_bounds']),'Distinct original time endpoints');endpoints+=1
        for first,second in itertools.combinations(objects[path],2):
            if exchange(named[path+'/'+first],named[path+'/'+second]):root_swaps+=1
            else:root_identity+=1
        for first,second in itertools.combinations(objects[path+'/cell'],2):need(exchange(named[path+'/cell/'+first],named[path+'/cell/'+second]),'Distinct Cell field representations');cell_swaps+=1
        if i<20 and i&1:need(exchange(named[path+'/value/present/lower'],named[path+'/value/present/upper']),'Distinct saved interval endpoint bits');endpoints+=1
        if i>=20 and ((i-20)&3)==3:
            if exchange(named[path+'/cell/parent_audit'],named[path+'/audit_index']):owner_swaps+=1
            else:owner_identity+=1
    need(endpoints==42 and root_swaps==363 and root_identity==9 and cell_swaps==96 and owner_swaps==2 and owner_identity==1,'All distinct exchanges and explicitly unchanged equal-value swaps')
    return dict(status='PASS',baseline=baseline,wellFormedSingleByteMutations=len(mutations),recordOrderCountRejections=3,absentToNullRejections=44,presentToAbsentOrNullRejections=80,enumToU32Rejections=64,endpointSwapRejections=endpoints,rootFieldSwapRejections=root_swaps,cellFieldSwapRejections=cell_swaps,parentAuditIndexSwapRejections=owner_swaps,identicalRootFieldExchanges=root_identity,identicalOwnershipExchanges=owner_identity,mutations=mutations,scope='Actual differing grammar-valid bytes rejected; equal-value exchanges explicitly unchanged, not counted as rejection. Artificial diagnostics only, no numerical acceptance.')
def main():
    need(__debug__,'Optimized Python refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
