"""Grammar-valid complete held Result mutations including every message byte and stored container."""
from pathlib import Path
import argparse,importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('held_result_reference',ROOT/'scripts/verify-report-held-result-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)

def need(v,m):
    if not v:raise ValueError(m)

def verify(data):
    baseline=ref.verify(data);pos=12;offsets=[];records=[];absents=[];presents=[];enums=[];arrays=[];message_bytes=0
    # Build the independent specification once. Every mutation still traverses
    # the grammar and compares its complete typed tree with this specification.
    expected=ref.expected()
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded scanner');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        nonlocal message_bytes
        start=pos;tag=number(1)
        if tag in (2,3,4,5,6,8):
            size={2:1,3:4,4:8,5:8,6:8,8:4}[tag];offset=take(size)
            for n in range(size):offsets.append((path,offset+n,'value-byte'))
            if tag==8:enums.append(start)
            return
        if tag==7:
            size=number(8);offset=take(size);message_bytes+=size
            for n in range(size):offsets.append((path,offset+n,'message-byte'))
            return
        if tag==11:absents.append(start);return
        if tag==12:
            value(path+'/present');need(number(1)==14,'Exactly one optional child');presents.append((start,pos));return
        need(tag in (9,10),'Expected exact Result domain');elements=[];index=0
        while data[pos]!=14:
            if tag==9:
                need(number(1)==15,'Object key');size=number(8);offset=take(size);need(size>0,'Nonempty key')
                key=data[offset:pos].decode();offsets.append((path+'/'+key,offset,'key'));value(path+'/'+key)
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos))
                if path=='':records.append((begin,pos))
                index+=1
        if tag==10 and path and elements:arrays.append((path,elements))
        take(1)
    value('');need(data[take(1):pos]==b'\x00' and pos==len(data),'Complete document')
    need(len(records)==15 and len(absents)==212 and len(presents)==56 and message_bytes==1808,'All root/nested presence and message bytes')
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
    array_rejections=outer_rejections=optional_rejections=0
    optional_suffixes=tuple('/'+k+'/present' for k in ['acceleration','whole_path_bounds','whole_velocity_bounds','safe_prefix','path_bounds','point_bounds'])
    for path,spans in arrays:
        need(len(spans)>=2,'Every nonempty fixture array supports order comparison');a,b=spans[0];u,v=spans[1]
        for changed in [data[:a]+data[u:v]+data[a:b]+data[v:],data[:a]+data[b:],data[:a]+data[a:b]+data[a:]]:
            refuses(changed);array_rejections+=1
            if re.fullmatch(r'/\d+/(certified_leaves|candidate_surface_ids|partition|frontier|audits)',path):outer_rejections+=1
            if path.endswith(optional_suffixes):optional_rejections+=1
    need(outer_rejections==30 and optional_rejections==36,'All five outer containers and all twelve optional arrays')
    return dict(status='PASS',baseline=baseline,outerPresencePairCombinations=baseline['outerPresencePairCombinations'],wellFormedSingleByteMutations=len(mutations),recordOrderCountRejections=3,
        absentToNullRejections=len(absents),presentToAbsentOrNullRejections=2*len(presents),enumToU32Rejections=len(enums),allArrayOrderCountRejections=array_rejections,outerContainerOrderCountRejections=outer_rejections,optionalArrayOrderCountRejections=optional_rejections,messageBytesIndividuallyMutated=message_bytes,mutations=mutations,
        scope='Complete artificial held Results with all stored nested values; no actual query/proof/accounting, top-level Report/pump or runtime connection.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
