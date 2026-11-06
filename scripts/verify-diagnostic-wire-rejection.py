"""Independent exact v1 control fixture; explicit refusal itself emits zero bytes."""
from pathlib import Path
import argparse,hashlib,json,struct

def expected():
    # Literal v1 tags and little-endian fields, independent of the C++ writer.
    payload=bytes(i&255 for i in range(513));key=bytes((i*3)&255 for i in range(257))
    return (b'PPDR'+struct.pack('<II',1,0x524a4331)+b'\x0a\x03'+struct.pack('<I',0x12345678)
        +b'\x0c\x07'+struct.pack('<Q',len(payload))+payload+b'\x0e\x0d'+struct.pack('<I',1)
        +b'\x09\x0f'+struct.pack('<Q',len(key))+key+b'\x04'+struct.pack('<Q',2**64-1)+b'\x0e\x0e\x0e\x00')

def main():
    if not __debug__:raise RuntimeError('Optimized Python is refused')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    raw=bytes.fromhex(a.input.read_text()) if a.hex else a.input.read_bytes()
    if raw!=expected():raise ValueError('Whole independent v1 control fixture differs')
    print(json.dumps(dict(status='PASS',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),schema=0x524a4331,
        payloadBytes=513,keyBytes=257,scope='Control document only. Rejection zero-byte behavior is measured separately by the native harness.')))
if __name__=='__main__':main()
