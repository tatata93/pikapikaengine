"""Grammar-valid mutations against independent complete held audit and partition values."""
from pathlib import Path
import argparse,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('held_audit_reference',ROOT/'scripts/verify-report-held-audits-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)

def need(v,m):
    if not v:raise ValueError(m)

def verify(data):
    baseline=ref.verify(data);pos=12;offsets=[];records=[];absents=[];presents=[];enums=[];arrays=[]
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded scanner');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        start=pos;tag=number(1)
        if tag in (2,3,4,5,6,8):
            size={2:1,3:4,4:8,5:8,6:8,8:4}[tag];offset=take(size)
            for n in range(size):offsets.append((path,offset+n,'value-byte'))
            if tag==8 and path.endswith(('/mesh_status/present','/mesh_reason/present')):enums.append(start)
            return
        if tag==11:absents.append(start);return
        if tag==12:
            value(path+'/present');need(number(1)==14,'Exactly one optional child');presents.append((start,pos));return
        need(tag in (9,10),'Expected exact value domain');elements=[];index=0
        while data[pos]!=14:
            if tag==9:
                need(number(1)==15,'Object key');size=number(8);offset=take(size);need(size>0,'Nonempty key')
                key=data[offset:pos].decode();offsets.append((path+'/'+key,offset,'key'));value(path+'/'+key)
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos))
                if path=='':records.append((begin,pos))
                index+=1
        if path.endswith(('/path_bounds/present','/point_bounds/present')):arrays.append(elements)
        take(1)
    value('');need(data[take(1):pos]==b'\x00' and pos==len(data),'Complete document')
    need(len(records)==18 and len(absents)==145 and len(presents)==27 and len(enums)==4 and len(arrays)==4,'All semantic boundaries collected')
    def refuses(changed):
        ref.wire.decode(changed)
        try:ref.verify(changed)
        except ValueError:return
        raise ValueError('Grammar-valid semantic change accepted')
    mutations=[]
    for path,offset,kind in offsets:
        changed=bytearray(data);changed[offset]^=1;refuses(bytes(changed));mutations.append(dict(path=path,byteOffset=offset,kind=kind))
    a,b=records[0];u,v=records[1]
    for changed in [data[:a]+data[u:v]+data[a:b]+data[v:],data[:a]+data[b:],data[:a]+data[a:b]+data[a:]]:refuses(changed)
    for offset in absents:refuses(data[:offset]+b'\x01'+data[offset+1:])
    for a,b in presents:
        refuses(data[:a]+b'\x0b'+data[b:]);refuses(data[:a]+b'\x01'+data[b:])
    for offset in enums:refuses(data[:offset]+b'\x03'+data[offset+1:])
    array_rejections=0
    for spans in arrays:
        need(len(spans)==3,'All original three axes');a,b=spans[0];u,v=spans[1]
        for changed in [data[:a]+data[u:v]+data[a:b]+data[v:],data[:a]+data[b:],data[:a]+data[a:b]+data[a:]]:refuses(changed);array_rejections+=1
    return dict(status='PASS',baseline=baseline,wellFormedSingleByteMutations=len(mutations),recordOrderCountRejections=3,absentToNullRejections=len(absents),presentToAbsentOrNullRejections=2*len(presents),optionalEnumToU32Rejections=len(enums),optionalArrayOrderCountRejections=array_rejections,mutations=mutations,
                scope='Independent complete audit and partition values only. No actual query/proof/accounting, full Result/Report/pump or runtime connection.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
