"""Grammar-valid sphere-pair and sphere-plane original input mutations."""
from pathlib import Path
import argparse,importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('flight_result_reference',ROOT/'scripts/verify-report-coverage-input-variant-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)

def need(v,m):
    if not v:raise ValueError(m)

def verify(data):
    baseline=ref.verify(data);pos=12;offsets=[];records=[];absents=[];presents=[];enums=[];arrays=[];byte_payloads=[];identity_bytes=0;named_values={};variants=[]
    # Build the independent specification once. Every mutation still traverses
    # the grammar and compares its complete typed tree with this specification.
    expected=ref.expected()
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded scanner');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        nonlocal identity_bytes
        start=pos;tag=number(1)
        if tag in (2,3,4,5,6,8):
            size={2:1,3:4,4:8,5:8,6:8,8:4}[tag];offset=take(size)
            for n in range(size):offsets.append((path,offset+n,'value-byte'))
            if tag==8:
                enums.append(start)
            return
        if tag==13:
            ordinal_offset=pos;number(4);child_start=pos;value(path);child_end=pos
            need(number(1)==14,'Exactly one variant child');variants.append(dict(start=start,ordinal=ordinal_offset,child_start=child_start,child_end=child_end,end=pos));return
        if tag==7:
            length_offset=pos;size=number(8);offset=take(size);identity_bytes+=size;byte_payloads.append((length_offset,offset,pos))
            for n in range(size):offsets.append((path,offset+n,'identity-byte'))
            return
        if tag==11:absents.append(start);return
        if tag==12:
            value(path+'/present');need(number(1)==14,'Exactly one optional child');presents.append((start,pos));return
        need(tag in (9,10),'Expected exact Result domain');elements=[];index=0
        while data[pos]!=14:
            if tag==9:
                need(number(1)==15,'Object key');size=number(8);offset=take(size);need(size>0,'Nonempty key')
                key=data[offset:pos].decode();offsets.append((path+'/'+key,offset,'key'));begin=pos;value(path+'/'+key);named_values[path+'/'+key]=(begin,pos)
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos))
                if path=='':records.append((begin,pos))
                index+=1
        if tag==10 and path and elements:arrays.append((path,elements))
        take(1)
    value('');need(data[take(1):pos]==b'\x00' and pos==len(data),'Complete document')
    need(len(records)==4 and len(absents)==0 and len(presents)==0 and len(enums)==0 and identity_bytes==0 and len(variants)==4,'All four coefficient records without optional or enum values')
    def refuses(changed):
        decoded=ref.wire.decode(changed)
        need(not ref.wire.typed_equal(decoded,expected),'Grammar-valid semantic change accepted')
    mutations=[]
    for path,offset,kind in offsets:
        changed=bytearray(data);changed[offset]^=1;refuses(bytes(changed));mutations.append(dict(path=path,byteOffset=offset,kind=kind))
    a,b=records[0];u,v=records[1]
    for changed in [data[:a]+data[u:v]+data[a:b]+data[v:],data[:a]+data[b:],data[:a]+data[a:b]+data[a:]]:refuses(changed)
    for offset in absents:refuses(data[:offset]+b'\x01'+data[offset+1:])
    for a,b in presents:
        refuses(data[:a]+b'\x0b'+data[b:]);refuses(data[:a]+b'\x01'+data[b:])
    for offset in enums:refuses(data[:offset]+b'\x03'+data[offset+1:])
    named_rejections=0
    for path,first,second in [('/0','first','second'),('/1','first','second'),('/2','sphere','plane'),('/3','sphere','plane')]:
        a,b=named_values[path+'/'+first];c,d=named_values[path+'/'+second]
        refuses(data[:a]+data[c:d]+data[b:c]+data[a:b]+data[d:]);named_rejections+=1
    ordinal_mutations=0
    for item in variants:
        for offset in range(item['ordinal'],item['ordinal']+4):
            changed=bytearray(data);changed[offset]^=1;refuses(bytes(changed));ordinal_mutations+=1
        # Replacing the variant with present requires removing its ordinal bytes.
        refuses(data[:item['start']]+b'\x0c'+data[item['child_start']:])
        refuses(data[:item['start']]+data[item['child_start']:item['child_end']]+data[item['end']:])
    child_swaps=0
    for first,second in [(0,1),(0,2),(1,3),(2,3)]:
        left,right=variants[first],variants[second];a,b=left['child_start'],left['child_end'];c,d=right['child_start'],right['child_end']
        refuses(data[:a]+data[c:d]+data[b:c]+data[a:b]+data[d:]);child_swaps+=1
    return dict(status='PASS',baseline=baseline,variantOrdinalByteMutations=ordinal_mutations,variantToPresentRejections=len(variants),variantWrapperRemovalRejections=len(variants),variantChildSwapRejections=child_swaps,wellFormedSingleByteMutations=len(mutations),recordOrderCountRejections=3,namedInputOrderRejections=named_rejections,
        absentToNullRejections=len(absents),presentToAbsentOrNullRejections=2*len(presents),enumToU32Rejections=len(enums),mutations=mutations,
        scope='Artificial named pair/plane original inputs; explicit0/1 variant; no model acceptance, numeric proof, full Report/pump or game connection.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
