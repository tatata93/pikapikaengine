"""Grammar-valid advance CommitWork/CommitStorage values mutations; identical exchanges are counted separately."""
from pathlib import Path
import argparse,importlib.util,itertools,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sphere_result_reference',ROOT/'scripts/verify-report-advance-commit-ledgers-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
def verify(data,shard=0,shards=1):
    need(1<=shards<=32 and 0<=shard<shards,'Bounded explicit control shard')
    baseline=ref.verify(data);expected=ref.expected();pos=12;offsets=[];records=[];absents=[];presents=[];enums=[];variants=[];bodies=[];named={};arrays={};objects={};field_segments={}
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
        if tag==7:
            size=number(8);offset=take(size);offsets.extend((path,offset+i,'message-byte') for i in range(size));bodies.append((start,offset,pos));return
        if tag==11:absents.append(start);return
        if tag==12:value(path+'/present');need(number(1)==14,'Single optional child');presents.append((start,pos));return
        if tag==13:
            ordinal=pos;number(4);child_start=pos;value(path);child_end=pos;need(number(1)==14,'Single variant child');variants.append((start,ordinal,child_start,child_end,pos));return
        need(tag in (9,10),'Expected advance CommitWork/CommitStorage values grammar');elements=[];fields=[];segments=[];index=0
        while data[pos]!=14:
            if tag==9:
                key_start=pos;need(number(1)==15,'Key');size=number(8);offset=take(size);key=data[offset:pos].decode();need(size>0,'Nonempty key');offsets.extend((path+'/'+key,offset+i,'key-byte') for i in range(size));begin=pos;value(path+'/'+key);named[path+'/'+key]=(begin,pos);fields.append(key);segments.append((key_start,pos))
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos))
                if path=='':records.append((begin,pos))
                index+=1
        if tag==10 and path:arrays[path]=elements
        if tag==9:objects[path]=fields;field_segments[path]=segments
        take(1)
    value('');need(data[take(1):pos]==b'\0' and pos==len(data),'Complete');need(len(records)==32 and len(absents)==0 and len(presents)==0 and len(enums)==0 and len(variants)==0 and len(bodies)==0,'All artificial roots/optional/enum/variant/body boundaries')
    considered=executed=0
    def refuses(changed):
        nonlocal considered,executed
        selected=considered%shards==shard;considered+=1
        if selected:
            need(not ref.wire.typed_equal(ref.wire.decode(changed),expected),'Grammar-valid semantic change accepted')
            executed+=1
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
    field_swaps=field_identity=field_orders=0
    for path,keys in objects.items():
        for first,second in itertools.combinations(keys,2):
            if exchange(named[path+'/'+first],named[path+'/'+second]):field_swaps+=1
            else:field_identity+=1
        if len(keys)>1:need(exchange(*field_segments[path][:2]),'Different named field order');field_orders+=1
    array_changes=array_identity=0
    for path,elements in arrays.items():
        if elements:
            a,b=elements[0]
            refuses(data[:a]+data[b:]);refuses(data[:a]+data[a:b]+data[a:]);array_changes+=2
        if len(elements)>=2:
            if exchange(*elements[:2]):array_changes+=1
            else:array_identity+=1
            start=elements[0][0];end=elements[-1][1];changed=data[:start]+b''.join(data[a:b] for a,b in reversed(elements))+data[end:]
            if changed==data:array_identity+=1
            else:refuses(changed);array_changes+=1
    ordinal_changes=0
    for start,ordinal,child_start,child_end,end in variants:
        for offset in range(ordinal,ordinal+4):
            changed=bytearray(data);changed[offset]^=1;refuses(bytes(changed));ordinal_changes+=1
        refuses(data[:start]+b'\x0c'+data[child_start:]);refuses(data[:start]+data[child_start:child_end]+data[end:])
    variant_swaps=variant_identity=nested_pairs=nested_replacements=0
    # Disjoint children can be exchanged. A parent/descendant pair overlaps;
    # exercise BOTH finite subtree replacements instead of an invalid exchange.
    ordered=sorted(variants,key=lambda v:v[2])
    for left,right in itertools.combinations(ordered,2):
        a,b=left[2],left[3];c,d=right[2],right[3]
        if b<=c:
            if exchange((a,b),(c,d)):variant_swaps+=1
            else:variant_identity+=1
        else:
            need(a<c<d<=b,'Exact nested child intervals')
            for start,end,replacement in [(a,b,data[c:d]),(c,d,data[a:b])]:
                changed=data[:start]+replacement+data[end:];need(changed!=data,'Differing nested subtree replacement');refuses(changed);nested_replacements+=1
            nested_pairs+=1
    pair_count=len(variants)*(len(variants)-1)//2
    need(variant_swaps+variant_identity+nested_pairs==pair_count and nested_replacements==2*nested_pairs,'Every unordered child pair exercised as a disjoint exchange or both nested replacements')
    body_lengths=0
    for start,begin,end in bodies:
        body=data[begin:end]
        for changed in ([body[:-1]] if body else [])+[body+b'\0']:
            refuses(data[:start]+b'\x07'+len(changed).to_bytes(8,'little')+changed+data[end:]);body_lengths+=1
    return dict(status='PASS' if shards==1 else 'PASS_SHARD',shard=shard,shards=shards,controlsConsidered=considered,controlsDecoded=executed,baseline=baseline,wellFormedSingleByteMutations=len(mutations),recordOrderCountRejections=3,absentToNullRejections=len(absents),presentToAbsentOrNullRejections=2*len(presents),enumToU32Rejections=len(enums),fieldValueExchangeRejections=field_swaps,objectFieldOrderRejections=field_orders,arrayOrderCountRejections=array_changes,variantOrdinalByteMutations=ordinal_changes,variantToPresentRejections=len(variants),variantWrapperRemovalRejections=len(variants),variantChildExchangeRejections=variant_swaps,variantChildPairsConsidered=pair_count,disjointVariantChildPairs=variant_swaps+variant_identity,nestedVariantChildPairs=nested_pairs,nestedVariantChildReplacementRejections=nested_replacements,messageLengthRejections=body_lengths,identicalFieldExchanges=field_identity,identicalArrayOrders=array_identity,identicalVariantChildExchanges=variant_identity,mutations=mutations,scope='Complete artificial advance CommitWork/CommitStorage values: only differing grammar-valid streams counted as rejections; equal-value exchanges remain unchanged. Sharded PASS requires a separate all-shards acceptance. No numerical acceptance or World Report/pump/game claim.')
def main():
    need(__debug__,'Optimized Python refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=1);a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data,a.shard,a.shards)))
if __name__=='__main__':main()
