"""Real byte mutations against the independent complete held snapshot/work oracle."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('report_values_reference',ROOT/'scripts/verify-report-held-snapshot-work-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
def verify(data):
    baseline=ref.verify(data);pos=12;offsets=[];records=[];triangle_lists=[]
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos,'Bounded actual stream');start=pos;pos+=n;return start
    def number(n):return int.from_bytes(data[take(n):pos],'little')
    def value(path):
        start=pos;tag=number(1)
        if tag in (2,3,4,5,6,8):
            size={2:1,3:4,4:8,5:8,6:8,8:4}[tag];offset=take(size)
            for n in range(size):offsets.append((path,offset+n,'value-byte'))
            return
        need(tag in (9,10),'Leaf fixture only contains objects/arrays/scalars')
        index=0;elements=[]
        while data[pos]!=14:
            if tag==9:
                need(number(1)==15,'Exact object key');size=number(8);offset=take(size);key=data[offset:pos];need(size>0,'Fixture keys nonempty')
                offsets.append((path+'/'+key.decode(),offset,'key'));value(path+'/'+key.decode())
            else:
                begin=pos;value(path+'/'+str(index));elements.append((begin,pos))
                if path=='':records.append((begin,pos))
                index+=1
        if path.endswith('/triangles') and len(elements)==3:triangle_lists.append(elements)
        take(1);need(pos>start,'Forward scan')
    value('');need(data[take(1):pos]==b'\x00' and pos==len(data),'Exact end')
    need(len(records)==5 and len(offsets)>150,'Every root record and field/value collected')
    rejected=[]
    for path,offset,kind in offsets:
        changed=bytearray(data);changed[offset]^=1
        # These mutations retain the wire grammar; the complete expected typed
        # field oracle, rather than a parser error, must detect the difference.
        ref.wire.decode(bytes(changed))
        try:ref.verify(bytes(changed))
        except ValueError:rejected.append(dict(path=path,byteOffset=offset,kind=kind))
        else:raise ValueError('Changed field accepted: '+path)
    first,second=records[:2];swapped=data[:first[0]]+data[second[0]:second[1]]+data[first[0]:first[1]]+data[second[1]:]
    removed=data[:first[0]]+data[first[1]:];repeated=data[:first[0]]+data[first[0]:first[1]]+data[first[0]:]
    for changed in [swapped,removed,repeated]:
        ref.wire.decode(changed)
        try:ref.verify(changed)
        except ValueError:pass
        else:raise ValueError('Reordered/missing/repeated record accepted')
    triangle_rejections=0
    need(len(triangle_lists)==2,'Two nonempty original triangle lists')
    for elements in triangle_lists:
        first,second=elements[:2]
        changes=[data[:first[0]]+data[second[0]:second[1]]+data[first[0]:first[1]]+data[second[1]:],
                 data[:first[0]]+data[first[1]:],data[:first[0]]+data[first[0]:first[1]]+data[first[0]:]]
        for changed in changes:
            ref.wire.decode(changed)
            try:ref.verify(changed)
            except ValueError:triangle_rejections+=1
            else:raise ValueError('Reordered/missing/repeated original triangle accepted')
    return dict(status='PASS',baseline=baseline,wellFormedSingleByteMutations=len(rejected),recordOrderCountRejections=3,triangleListOrderCountRejections=triangle_rejections,mutations=rejected,
                scope='Independent complete held snapshot/work fields only; no full Report/pump or numerical model acceptance.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
