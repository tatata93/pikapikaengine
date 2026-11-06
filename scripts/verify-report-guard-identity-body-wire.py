"""Independent complete BindingInfo65-byte identity and BodyRecord oracle; no model or binding call."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    ids=[(b'0123456789abcdef'*4)+b'\0',bytes(65),bytes(0 if k==32 else (k*37+11)%256 for k in range(65)),b'\xff'*65,
         bytes((k*19+7)%256 for k in range(65)),b'a'*64+b'Z',b'\xc0\xff'+bytes(62)+b'\x80']
    modes=[0,1,2**31,2**32-1,0,0,0];states=[0,1,2,3,4,2**31,2**32-1];profiles=[0,2**32-1,2**31,1,17,2**32-2,42]
    bindings=[obj(mode=('enum',modes[j]),state=('enum',states[j]),checked=('bool',j%2!=0),profile=('u32',profiles[j]),build_id=('bytes',ids[j])) for j in range(7)]
    ordinals=[0,2**53+1,2**64-1,1,2**63,2**64-2,42];seeds=[None,0,2**64-1,2**53+1,None,1,2**64-2]
    bodies=[obj(body_ordinal=('u64',ordinals[j]),is_static=('bool',j%3==0),state=('enum',states[j]),seed_pair_ordinal=('absent',None) if seeds[j] is None else ('present',('u64',seeds[j]))) for j in range(7)]
    return 0x52474231,('array',bindings+bodies)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every typed identity/body field and all65 raw identity bytes')
    leaves=[];absents=0;presents=0
    def walk(node):
        nonlocal absents,presents
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        elif kind=='present':presents+=1;walk(value)
        elif kind=='absent':absents+=1
        else:leaves.append(node)
    walk(actual[1]);need(len(leaves)==61 and absents==2 and presents==5,'Exact complete typed leaf/presence counts')
    ids=[v for k,v in leaves if k=='bytes'];need(len(ids)==7 and all(len(v)==65 for v in ids),'Full fixed65 byte payloads')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=9,fixtureRecords=14,allTypedLeaves=len(leaves),
        u64Fields=sum(k=='u64' for k,_ in leaves),u32Fields=sum(k=='u32' for k,_ in leaves),enumFields=sum(k=='enum' for k,_ in leaves),boolFields=sum(k=='bool' for k,_ in leaves),
        fixedIdentityRecords=7,fixedIdentityBytes=sum(len(v) for v in ids),absentValues=absents,presentValues=presents,
        scope='Fourteen artificial stored identity/body records, all65 opaque bytes and full64 source ordinals; no binding acceptance, object hash measurement, numeric query, full Report/pump or JS/WASM/game connection.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
