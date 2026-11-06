"""Independent grammar-valid byte, optional, endpoint and Work counter mutations."""
from pathlib import Path
import argparse,importlib.util,json,itertools
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('plane_cell_work_reference',ROOT/'scripts/verify-report-coverage-plane-cell-work-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
def verify(data):
    baseline=ref.verify(data);expected=ref.expected();pos=12;offsets=[];records=[];absents=[];presents=[];named={};arrays={}
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded scanner');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        start=pos;tag=number(1)
        if tag in (3,4,6):
            size=4 if tag==3 else 8;offset=take(size);offsets.extend((path,offset+i,'value-byte') for i in range(size));return
        if tag==11:absents.append(start);return
        if tag==12:value(path+'/present');need(number(1)==14,'Single optional child');presents.append((start,pos));return
        need(tag in (9,10),'Expected Cell/Work grammar');elements=[];index=0
        while data[pos]!=14:
            if tag==9:
                need(number(1)==15,'Key');size=number(8);offset=take(size);key=data[offset:pos].decode();need(size>0,'Nonempty key');offsets.extend((path+'/'+key,offset+i,'key-byte') for i in range(size));begin=pos;value(path+'/'+key);named[path+'/'+key]=(begin,pos)
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos))
                if path=='':records.append((begin,pos))
                index+=1
        if tag==10 and path:arrays[path]=elements
        take(1)
    value('');need(data[take(1):pos]==b'\0' and pos==len(data),'Complete');need(len(records)==12 and len(absents)==4 and len(presents)==4,'All artificial roots and optional states')
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
        a,b=left;c,d=right;need(a<b<=c<d,'Ordered source');refuses(data[:a]+data[c:d]+data[b:c]+data[a:b]+data[d:])
    time_counts=0
    for i in range(8):
        elements=arrays['/'+str(i)+'/time_bounds'];exchange(*elements)
        a,b=elements[0]
        refuses(data[:a]+data[b:]);refuses(data[:a]+data[a:b]+data[a:]);time_counts+=2
    names=['value_calls_attempted','value_calls_returned'];swaps=0
    for i in range(8,12):
        for first,second in itertools.combinations(names,2):exchange(named['/'+str(i)+'/'+first],named['/'+str(i)+'/'+second]);swaps+=1
    return dict(status='PASS',baseline=baseline,wellFormedSingleByteMutations=len(mutations),recordOrderCountRejections=3,absentToNullRejections=4,presentToAbsentOrNullRejections=8,endpointSwapRejections=8,timeBoundsCountRejections=time_counts,workCounterSwapRejections=swaps,totalDifferingControls=len(mutations)+3+4+8+8+time_counts+swaps,mutations=mutations,scope='Complete artificial plane Cell/Work preservation; original seconds/parent and exact wrapper counts, no private norm upper counter or numerical-model acceptance claim.')
def main():
    need(__debug__,'Optimized Python refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
