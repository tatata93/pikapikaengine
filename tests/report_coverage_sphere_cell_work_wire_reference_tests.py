"""Independent grammar-valid byte, optional, endpoint and Work counter mutations."""
from pathlib import Path
import argparse,importlib.util,json,itertools
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sphere_cell_work_reference',ROOT/'scripts/verify-report-coverage-sphere-cell-work-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
def verify(data):
    baseline=ref.verify(data);expected=ref.expected();pos=12;offsets=[];records=[];absents=[];presents=[];named={};arrays={};objects={};segments={};payload_bytes=0
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded scanner');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        nonlocal payload_bytes
        start=pos;tag=number(1)
        if tag in (2,3,4,6):
            size={2:1,3:4,4:8,6:8}[tag];offset=take(size);payload_bytes+=size;offsets.extend((path,offset+i,'value-byte') for i in range(size));return
        if tag==11:absents.append(start);return
        if tag==12:value(path+'/present');need(number(1)==14,'Single optional child');presents.append((start,pos));return
        need(tag in (9,10),'Expected Cell/Work grammar');elements=[];index=0;keys=[];fields=[]
        while data[pos]!=14:
            if tag==9:
                first=pos;need(number(1)==15,'Key');size=number(8);offset=take(size);key=data[offset:pos].decode();need(size>0,'Nonempty key');offsets.extend((path+'/'+key,offset+i,'key-byte') for i in range(size));begin=pos;value(path+'/'+key);named[path+'/'+key]=(begin,pos);keys.append(key);fields.append((first,pos))
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos))
                if path=='':records.append((begin,pos))
                index+=1
        if tag==9:objects[path]=keys;segments[path]=fields
        if tag==10 and path:arrays[path]=elements
        take(1)
    value('');need(data[take(1):pos]==b'\0' and pos==len(data),'Complete');need(len(records)==16 and len(absents)==4 and len(presents)==4 and payload_bytes==584,'All artificial roots, optional states and584 typed payload bytes')
    def refuses(changed):need(not ref.wire.typed_equal(ref.wire.decode(changed),expected),'Grammar-valid semantic change accepted')
    mutations=[]
    for path,offset,kind in offsets:
        changed=bytearray(data);changed[offset]^=1;refuses(bytes(changed));mutations.append(dict(path=path,byteOffset=offset,kind=kind))
    a,b=records[0];c,d=records[1]
    for changed in [data[:a]+data[c:d]+data[a:b]+data[d:],data[:a]+data[b:],data[:a]+data[a:b]+data[a:]]:refuses(changed)
    for offset in absents:refuses(data[:offset]+b'\1'+data[offset+1:])
    for a,b in presents:
        refuses(data[:a]+b'\x0b'+data[b:]);refuses(data[:a]+b'\1'+data[b:])
    def exchange(left,right):
        a,b=left;c,d=right;need(a<b<=c<d,'Ordered source');changed=data[:a]+data[c:d]+data[b:c]+data[a:b]+data[d:]
        if changed==data:return False
        refuses(changed);return True
    time_counts=0
    for i in range(8):
        elements=arrays['/'+str(i)+'/time_bounds'];need(exchange(*elements),'Different original endpoint bits')
        a,b=elements[0]
        refuses(data[:a]+data[b:]);refuses(data[:a]+data[a:b]+data[a:]);time_counts+=2
    differing=identical=orders=0
    for path,keys in objects.items():
        for left,right in itertools.combinations(keys,2):
            if exchange(named[path+'/'+left],named[path+'/'+right]):differing+=1
            else:identical+=1
        if len(keys)>1:need(exchange(*segments[path][:2]),'Different named-field order');orders+=1
    return dict(status='PASS',baseline=baseline,wellFormedSingleByteMutations=len(mutations),typedPayloadByteMutations=payload_bytes,recordOrderCountRejections=3,absentToNullRejections=4,presentToAbsentOrNullRejections=8,endpointSwapRejections=8,timeBoundsCountRejections=time_counts,fieldValueExchangeRejections=differing,objectFieldOrderRejections=orders,identicalFieldExchanges=identical,totalDifferingControls=len(mutations)+3+4+8+8+time_counts+differing+orders,mutations=mutations,scope='Artificial8 sphere Cell and8 Work; all scalar/key bytes, presence, endpoint order/count, all field-value pairs and field order. Same-value exchanges separate. Preserve observed returned-root work, unknown upper and exact flag without numerical-model certification.')

def main():
    need(__debug__,'Optimized Python refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
