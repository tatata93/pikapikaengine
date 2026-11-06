"""Independent bounded typed-byte decoder and required diagnostic primitive fixture."""
import argparse, hashlib, json, struct
from pathlib import Path

def need(condition, message):
    if not condition: raise ValueError(message)

def decode(data):
    need(type(data) is bytes and len(data)<=1048576, 'Bounded immutable document')
    pos=0
    def take(n):
        nonlocal pos
        need(0<=n<=len(data)-pos, 'Truncated payload')
        result=data[pos:pos+n];pos+=n;return result
    def uint(n): return int.from_bytes(take(n),'little')
    need(take(4)==b'PPDR' and uint(4)==1, 'Magic and version')
    schema=uint(4);need(schema!=0, 'Nonzero schema')
    def value(depth=0):
        tag=uint(1)
        if tag==1:return ('null',None)
        if tag==2:
            n=uint(1);need(n in (0,1),'Boolean domain');return ('bool',bool(n))
        if tag in (3,4,5,6,8):
            n=uint(4 if tag in (3,8) else 8)
            if tag==5 and n>=2**63:n-=2**64
            return ({3:'u32',4:'u64',5:'i64',6:'f64bits',8:'enum'}[tag],n)
        if tag==7:return ('bytes',take(uint(8)))
        if tag==11:return ('absent',None)
        need(tag in (9,10,12,13) and depth<64,'Container tag/depth')
        if tag in (9,10):
            items=[]
            while True:
                need(pos<len(data),'Missing container end')
                if data[pos]==14:take(1);break
                if tag==9:
                    need(uint(1)==15,'Object key required');key=take(uint(8))
                    items.append((key,value(depth+1)))
                else:items.append(value(depth+1))
            return ('object' if tag==9 else 'array',items)
        ordinal=uint(4) if tag==13 else None
        child=value(depth+1);need(uint(1)==14,'Exactly one optional/variant child')
        return ('variant',(ordinal,child)) if tag==13 else ('present',child)
    result=value();need(uint(1)==0 and pos==len(data),'Explicit finish and exact EOF')
    return schema,result

def expected():
    floats=[int(s,16) for s in [
        '0','8000000000000000','1','8000000000000001','000fffffffffffff','0010000000000000',
        '3ff0000000000000','bff0000000000000','7fefffffffffffff','ffefffffffffffff',
        '7ff0000000000000','fff0000000000000','7ff8000000000042','fff8000000001234',
        '7ff0000000000001','fff0000000000001']]
    return 0x44544731,('object',[
        (b'bits',('array',[('f64bits',n) for n in floats])),
        (b'integers',('array',[('u32',0),('u32',2**32-1),('u64',0),('u64',2**64-1),('u64',2**53+1),
                              ('i64',-2**63),('i64',-1),('i64',2**63-1),('enum',2**32-1)])),
        (b'optional',('array',[('absent',None),('present',('null',None))])),
        (b'variant',('variant',(2**32-1,('object',[(b'',('bool',True)),(b'zero',('bool',False))])))),
        (b'bytes',('bytes',bytes(range(256))*3+b'\x00')),
        (b'\x00\xff\xc0',('bytes',b''))])

def typed_equal(a,b):
    if type(a)!=type(b):return False
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(typed_equal(x,y) for x,y in zip(a,b))
    return a==b

def verify(data):
    need(typed_equal(decode(data),expected()),'All exact typed values, order, keys and IEEE bits')
    header=b'PPDR'+struct.pack('<II',1,1)
    malformed=[header+b'\x02\x02\x00',header+b'\x0f'+bytes(8)+b'\x01\x00',header+b'\x09\x01\x0e\x00',
        header+b'\x09\x0f'+bytes(8)+b'\x0e\x00',header+b'\x0c\x0e\x00',header+b'\x0c\x01\x01\x0e\x00',
        header+b'\x0d'+bytes(4)+b'\x0e\x00',header+b'\x0a'*65+b'\x01'+b'\x0e'*65+b'\x00',
        header+b'\x07'+b'\xff'*8+b'\x00',data+b'\x00',data[:4]+struct.pack('<I',2)+data[8:],
        data[:8]+bytes(4)+data[12:],b'XXXX'+data[4:],header+b'\xff\x00']
    rejects=0
    for bad in [data[:n] for n in range(len(data))]+malformed:
        try:decode(bad)
        except ValueError:rejects+=1
        else:raise ValueError('Malformed/truncated document accepted')
    # Decoder distinguishes absent/null and integer/bool; a well-formed mutation
    # is still refused by the independent complete expected-value comparison.
    changed=bytearray(data);changed[27]^=1
    need(not typed_equal(decode(bytes(changed)),expected()),'Real typed payload mutation')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                floatBitPatterns=16,malformedAndTruncatedRejections=rejects,
                wellFormedPayloadMutationRefused=True,scope='Primitive v1 demonstration schema only; no full Report/pump/physical model acceptance.')

def main():
    need(__debug__,'Optimized Python is refused')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capture',type=Path);parser.add_argument('--hex',action='store_true');args=parser.parse_args()
    need(args.capture.stat().st_size<=2097154,'Bounded input file');data=args.capture.read_bytes()
    if args.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
