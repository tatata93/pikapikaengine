"""Real byte mutations against the independent complete free flight endpoint audit oracle."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('report_values_reference',ROOT/'scripts/verify-report-flight-endpoint-wire.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
def verify(data):
    baseline=ref.verify(data);expected=ref.expected();pos=12;offsets=[];records=[];fixed_bounds=[]
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
        if path.endswith(('/nominal_position','/nominal_allowed','/exact_position','/exact_allowed','/exact_difference')):fixed_bounds.append(elements)
        take(1);need(pos>start,'Forward scan')
    value('');need(data[take(1):pos]==b'\x00' and pos==len(data),'Exact end')
    need(len(records)==8 and len(offsets)>150,'Every root record and field/value collected')
    rejected=[]
    def refuses(changed):
        decoded=ref.wire.decode(changed)
        need(not ref.wire.typed_equal(decoded,expected),'Changed complete original value accepted')
    for path,offset,kind in offsets:
        changed=bytearray(data);changed[offset]^=1;refuses(bytes(changed));rejected.append(dict(path=path,byteOffset=offset,kind=kind))
    def structural(elements):
        first,second=elements[:2]
        return [data[:first[0]]+data[second[0]:second[1]]+data[first[0]:first[1]]+data[second[1]:],
                data[:first[0]]+data[first[1]:],data[:first[0]]+data[first[0]:first[1]]+data[first[0]:]]
    for changed in structural(records):refuses(changed)
    need(len(fixed_bounds)==40,'All five3-axis bounds in each of8 audit records')
    for elements in fixed_bounds:
        need(len(elements)==3,'Every fixed3-axis endpoint bound')
        for changed in structural(elements):refuses(changed)
    return dict(status='PASS',baseline=baseline,wellFormedSingleByteMutations=len(rejected),recordOrderCountRejections=3,fixedBoundsOrderCountRejections=120,flagCombinations=8,mutations=rejected,
                scope='Independent complete free flight endpoint audit fields only; no full Report/pump or numerical model acceptance.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
