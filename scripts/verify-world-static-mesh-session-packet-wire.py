"""Independent integer grammar and exact Native packet field/bit reference."""
from pathlib import Path
import argparse,hashlib,json,sys
EXPECTED_INPUT_FINGERPRINT='e81c7b5dd04bee50d51f76f0c06d669d06b01edaa9955c2bb1c0bf243a570475'
def need(v,m):
    if not v:raise ValueError(m)
def expected(f,w):
    def fail(status,packet=None,row=None,component=None):return dict(status=status,packet=packet,row=row,component=component,packets=None)
    if not w or len(w)>161:return fail(1)
    count=w[0]
    if count>8:return fail(2)
    records=[];remaining=w[1:]
    for ordinal in range(count):
        if len(remaining)<4:return fail(1,ordinal)
        mode,tick_low,tick_high,n=remaining[:4];remaining=remaining[4:]
        if n>8:return fail(3,ordinal)
        if len(remaining)<2*n:return fail(1,ordinal)
        ids=[remaining[2*i]+2**32*remaining[2*i+1] for i in range(n)];remaining=remaining[2*n:]
        records.append((mode,tick_low+2**32*tick_high,ids))
    if remaining:return fail(1)
    if len(f)!=sum(len(ids)*6 for _,_,ids in records):return fail(4)
    cursor=0;packets=[]
    for i,(mode,tick,ids) in enumerate(records):
        loads=[]
        for j,body in enumerate(ids):
            values=f[cursor:cursor+6];cursor+=6
            for k,b in enumerate(values):
                if (b>>52)&0x7ff==0x7ff:return fail(5,i,j,k)
            loads.append(dict(bodyId=body,forceBits=values[:3],torqueBits=values[3:]))
        packets.append(dict(mode=mode,expectedTick=tick,loads=loads))
    return dict(status=0,packet=None,row=None,component=None,packets=packets)
def typed_equal(a,b):
    if type(a)!=type(b):return False
    if type(a)==dict:return set(a)==set(b) and all(typed_equal(a[k],b[k]) for k in a)
    if type(a)==list:return len(a)==len(b) and all(typed_equal(x,y) for x,y in zip(a,b))
    return a==b
def verify(d,allow_unpinned=False):
    need(type(d)==dict and set(d)=={'schema','kind','version','rows','actualRows'},'Exact complete envelope')
    need(type(d['schema'])==int and d['schema']==1 and type(d['version'])==int and d['version']==1 and d['kind']=='session-packet-wire-fixtures','Actual packet wire version')
    need(type(d['actualRows'])==int and d['actualRows']==24 and type(d['rows'])==list and len(d['rows'])==24,'All24 actual rows')
    inputs=[];admitted=refused=mapped=negative=packets=loads=0;environments=set()
    for r in d['rows']:
        need(type(r)==dict and set(r)=={'name','floatBits','words','actualEnvironment','status','packet','row','component','packets'},'Exact row fields')
        need(type(r['name'])==str and r['actualEnvironment'] in {'nearest','upward','downward','toward-zero'},'Observed environment/name')
        f,w=r['floatBits'],r['words'];need(type(f)==list and len(f)<=1024 and all(type(v)==int and 0<=v<2**64 for v in f),'Typed binary64 bit input');need(type(w)==list and len(w)<=1024 and all(type(v)==int and 0<=v<2**32 for v in w),'Typed U32 input')
        inputs.append(json.dumps(dict(floatBits=f,words=w,actualEnvironment=r['actualEnvironment']),sort_keys=True,separators=(',',':')));environments.add(r['actualEnvironment'])
        e=expected(f,w);need(typed_equal({k:r[k] for k in e},e),'Independent full admission/diagnostic/packet fields')
        if e['status']==0:
            admitted+=1;mapped+=len(f);negative+=f.count(1<<63);packets+=len(e['packets']);loads+=sum(len(p['loads']) for p in e['packets'])
        else:refused+=1
    fingerprint=hashlib.sha256(json.dumps(sorted(inputs),separators=(',',':')).encode()).hexdigest()
    if not allow_unpinned:need(EXPECTED_INPUT_FINGERPRINT!='TO_BE_PINNED' and fingerprint==EXPECTED_INPUT_FINGERPRINT,'Exact independently-name/order input corpus')
    need(environments=={'nearest','upward','downward','toward-zero'},'Actual four observed rounding modes')
    return dict(status='UNPINNED_INPUT_REFERENCE_ONLY_PASS' if allow_unpinned else 'PASS',rows=24,admitted=admitted,refused=refused,packets=packets,loads=loads,mappedFloatBitValues=mapped,negativeZeroOccurrences=negative,inputFingerprint=fingerprint,allMappedFieldsAndBits=True,scope='Owned Native packet-data grammar/fields only. Raw mode/full64 IDs/ticks are not model validation. No model call, FP instruction/whole environment certificate, allocator fault, C ABI/pump/JS/WASM/game acceptance.')
def main():
    need(__debug__,'Use normal Python; optimized execution is refused')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--allow-unpinned',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=1024*1024,'Bounded capture')
    print(json.dumps(verify(json.loads(a.capture.read_bytes()),a.allow_unpinned),allow_nan=False))
if __name__=='__main__':main()
