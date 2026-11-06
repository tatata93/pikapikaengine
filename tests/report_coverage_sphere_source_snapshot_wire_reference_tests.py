"""Grammar-valid complete sphere Input/Snapshot mutations; independent from the C++ getter."""
from pathlib import Path
import argparse,importlib.util,itertools,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sphere_source_snapshot_reference',ROOT/'scripts/verify-report-coverage-sphere-source-snapshot-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
def verify(data):
    baseline=ref.verify(data);expected=ref.expected();pos=12;offsets=[];records=[];objects={};named={};segments={};payload_bytes=0
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded scan');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        nonlocal payload_bytes
        start=pos;tag=number(1)
        if tag in (3,4,6):
            size={3:4,4:8,6:8}[tag];offset=take(size);payload_bytes+=size;offsets.extend((path,offset+i,'value-byte') for i in range(size));return
        need(tag in (9,10),'Only original record and array containers');keys=[];fields=[];index=0
        while data[pos]!=14:
            if tag==9:
                first=pos;need(number(1)==15,'Key');size=number(8);offset=take(size);key=data[offset:pos].decode('ascii');need(size>0,'Named field')
                offsets.extend((path+'/'+key,offset+i,'key-byte') for i in range(size));begin=pos;value(path+'/'+key);named[path+'/'+key]=(begin,pos);keys.append(key);fields.append((first,pos))
            else:
                begin=pos;value(path+'/'+str(index));records.append((begin,pos));index+=1
        if tag==9:objects[path]=keys;segments[path]=fields
        take(1)
    value('');need(data[take(1):pos]==b'\0' and pos==len(data) and len(records)==16 and payload_bytes==3264,'All16 roots and3264 typed payload bytes')
    def refuses(changed):need(not ref.wire.typed_equal(ref.wire.decode(changed),expected),'Grammar-valid changed stream accepted')
    for path,offset,kind in offsets:
        changed=bytearray(data);changed[offset]^=1;refuses(bytes(changed))
    a,b=records[0];c,d=records[1]
    for changed in [data[:a]+data[c:d]+data[a:b]+data[d:],data[:a]+data[b:],data[:a]+data[a:b]+data[a:]]:refuses(changed)
    def exchange(left,right):
        a,b=left;c,d=right;need(a<b<=c<d,'Ordered spans');changed=data[:a]+data[c:d]+data[b:c]+data[a:b]+data[d:]
        if changed==data:return False
        refuses(changed);return True
    differing=identical=orders=0
    for path,keys in objects.items():
        for left,right in itertools.combinations(keys,2):
            if exchange(named[path+'/'+left],named[path+'/'+right]):differing+=1
            else:identical+=1
        if len(keys)>1:need(exchange(*segments[path][:2]),'Different named field order');orders+=1
    return dict(status='PASS',baseline=baseline,wellFormedSingleByteMutations=len(offsets),typedPayloadByteMutations=payload_bytes,recordOrderCountRejections=3,fieldValueExchangeRejections=differing,objectFieldOrderRejections=orders,identicalFieldExchanges=identical,totalDifferingControls=len(offsets)+3+differing+orders,scope='Artificial8 sphere Input and8 Snapshot; every scalar/key byte and every field-value pair, object order and root order/count. Equal bytes not counted as refusal. No numerical certification or whole Native regression claim.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
