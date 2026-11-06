"""Grammar-valid complete plane Evaluation mutations; independent from the C++ getter."""
from pathlib import Path
import argparse,importlib.util,itertools,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('plane_evaluation_reference',ROOT/'scripts/verify-report-coverage-plane-evaluation-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
def verify(data):
    baseline=ref.verify(data);expected=ref.expected();pos=12;offsets=[];records=[];objects={};named={};segments={};arrays={};payload_bytes=0
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded scan');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        nonlocal payload_bytes
        start=pos;tag=number(1)
        if tag in (3,4,6):
            size={3:4,4:8,6:8}[tag];offset=take(size);payload_bytes+=size;offsets.extend((path,offset+i,'value-byte') for i in range(size));return
        need(tag in (9,10),'Only original record and array containers');keys=[];fields=[];elements=[];index=0
        while data[pos]!=14:
            if tag==9:
                first=pos;need(number(1)==15,'Key');size=number(8);offset=take(size);key=data[offset:pos].decode('ascii');need(size>0,'Named field')
                offsets.extend((path+'/'+key,offset+i,'key-byte') for i in range(size));begin=pos;value(path+'/'+key);named[path+'/'+key]=(begin,pos);keys.append(key);fields.append((first,pos))
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos));index+=1
                if not path:records.append((begin,pos))
        if tag==9:objects[path]=keys;segments[path]=fields
        if tag==10 and path:arrays[path]=elements
        take(1)
    value('');need(data[take(1):pos]==b'\0' and pos==len(data) and len(records)==8 and payload_bytes==768 and len(arrays)==8 and all(len(v)==3 for v in arrays.values()),'All8 roots, all3 axes and768 endpoint payload bytes')
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
    axis_changes=axis_identity=0
    for path,elements in arrays.items():
        need(path.endswith('/tube_coordinates'),'Only original3-axis arrays')
        a,b=elements[0]
        refuses(data[:a]+data[b:]);refuses(data[:a]+data[a:b]+data[a:]);axis_changes+=2
        for left,right in itertools.combinations(elements,2):
            if exchange(left,right):axis_changes+=1
            else:axis_identity+=1
    return dict(status='PASS',baseline=baseline,wellFormedSingleByteMutations=len(offsets),typedPayloadByteMutations=payload_bytes,recordOrderCountRejections=3,fieldValueExchangeRejections=differing,objectFieldOrderRejections=orders,fixedAxisArrayOrderCountRejections=axis_changes,identicalFieldExchanges=identical,identicalAxisExchanges=axis_identity,totalDifferingControls=len(offsets)+3+differing+orders+axis_changes,scope='Artificial8 plane Evaluation; every scalar/key byte, all field pairs and all3-axis element pairs/order/count. Equal endpoint exchanges separate. Public valid Interval construction only, no numerical model certification or whole Native regression claim.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
