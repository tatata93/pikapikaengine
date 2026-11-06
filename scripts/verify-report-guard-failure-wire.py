"""Independent original-source and guard failure location oracle; no preflight or numeric calls."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def optional(v):return ('absent',None) if v is None else ('present',('u64',v))
    kinds=[0,1,2,3,4,5,2**31,2**32-1];locations=[]
    # Explicit independent source ordinals; null and zero remain distinct.
    indices=[None,0,None,2**64-1,None,2**53+1,None,42]
    faces=[None,None,2**64-1,0,None,None,2**53+1,2**64-2]
    for j in range(8):locations.append(obj(kind=('enum',kinds[j]),index=optional(indices[j]),face_index=optional(faces[j])))
    bodies=[None,None,0,2**53+1,None,None,2**64-1,1]
    pairs=[None,None,None,None,0,2**64-1,2**53+1,42]
    failures=[obj(preparation=('present',locations[j//2]) if j%2 else ('absent',None),body_ordinal=optional(bodies[j]),pair_ordinal=optional(pairs[j])) for j in range(8)]
    return 0x52474631,('array',locations+failures)
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every original-source kind/index/face and separate guard body/pair position')
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
    walk(actual[1]);need(len(leaves)==32 and absents==24 and presents==24,'Exact typed leaf/presence counts')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=2,mappedFields=6,fixtureRecords=16,allTypedLeaves=len(leaves),
        u64Fields=sum(k=='u64' for k,_ in leaves),enumFields=sum(k=='enum' for k,_ in leaves),absentValues=absents,presentValues=presents,
        locationPresenceMasks=4,guardPresenceMasks=8,knownObjectKinds=6,artificialUnknownObjectKinds=2,
        scope='Sixteen artificial failure records and four nested source locations; full64 source/body/pair positions and all optional masks retained. No actual preflight acceptance, numeric query, full Report/pump or JS/WASM/game connection.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
