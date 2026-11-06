"""Independent prepare Result enum, optional, original owned values and message-byte specification."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
owned=module('result_owned','scripts/verify-report-preparation-snapshot-inventory-wire.py');failure=module('result_failure','scripts/verify-report-guard-failure-wire.py');wire=owned.wire
def need(v,m):
 if not v:raise ValueError(m)
def expected():
 def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
 def optional(v):return ('absent',None) if v is None else ('present',v)
 original=owned.expected()[1][1];locations=failure.expected()[1][1][:8];rows=[]
 long=bytearray(b'q'*513);long[256]=long[511]=0;messages=[b'',b'prepare\0diagnostic',b'\xff\x80\0\xfe',bytes(long)];unknown=[2**32-1,2**31,2**31-1,2**32-2]
 for i in range(30):
  mask=i%8 if i<16 else 0
  location=locations[i//2] if mask&1 else None
  snapshot=original[[0,0,0,1,0,0,2,3][mask]] if mask&2 else None
  inventory=original[4+mask-4] if mask&4 else None
  rows.append(obj(status=('enum',i%5 if i<26 else unknown[i-26]),reason=('enum',i if i<26 else unknown[i-26]),failure=optional(location),capture=('enum',i%3 if i<26 else unknown[i-26]),snapshot=optional(snapshot),inventory=optional(inventory),message=('bytes',messages[i%4])))
 return 0x52505253,('array',rows)
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'All Result enums, independent presence, owned bit values and original message bytes exact');leaves=[];present=absent=0
 def walk(v):
  nonlocal present,absent
  kind,value=v
  if kind=='object':
   for _,x in value:walk(x)
  elif kind=='array':
   for x in value:walk(x)
  elif kind=='present':present+=1;walk(value)
  elif kind=='absent':absent+=1
  else:leaves.append(v)
 walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits']
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=1,mappedFields=7,mappedVariants=0,fixtureRecords=30,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),present=present,absent=absent,totalVariantOccurrences=0,leafKinds={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']},scope='Artificial30 Results: all26 known Reasons,5 Statuses,3 CaptureStates,4 unknown ordinals per enum,all8 optional masks twice,original owned values and byte messages. No prepare invocation/numerical/World Report/pump/game acceptance.')
def main():
 need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
