"""Independent full GuardResult14: all root optional masks, enums, complete original records and message bytes."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
pair=module('root_pairs','scripts/verify-report-guard-pair-record-wire.py');preparation=module('root_prepare','scripts/verify-report-preparation-result-wire.py')
identity=module('root_identity','scripts/verify-report-guard-identity-body-wire.py');settings=module('root_settings','scripts/verify-report-settings-wire.py');ledger=module('root_ledger','scripts/verify-report-ledgers-wire.py');work=module('root_work','scripts/verify-report-work-wire.py');wire=pair.wire
def need(v,m):
 if not v:raise ValueError(m)
def expected():
 def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
 def optional(v):return ('absent',None) if v is None else ('present',v)
 ident=identity.expected()[1][1];ledgers=ledger.expected()[1][1];works=work.expected()[1][1];pairs=pair.expected()[1][1];prepared=preparation.expected()[1][1]
 failures=preparation.failure.expected()[1][1][8:];guard=settings.expected()[1][1][-1];body=preparation.owned.leaf.expected()[1][1][0]
 long=bytearray(b'g'*513);long[256]=long[511]=0;messages=[b'',b'guard\0result',b'\xff\x80\0\xfe',bytes(long)];unknown=[2**32-1,2**31,2**31-1,2**32-2];rows=[]
 for i in range(32):
  bodies=[] if i%3==0 else [ident[7+i%7]];children=[]
  if i==31:bodies=[ident[10],ident[8],ident[10]];children=pairs+[pairs[0]]
  candidates=None if not i&16 else [body] if i==30 else [body,body] if i==31 else []
  rows.append(obj(status=('enum',i%5 if i<28 else unknown[i-28]),reason=('enum',i%17 if i<28 else unknown[i-28]),binding=ident[i%7],original_settings=optional(guard if i&1 else None),failure=optional(failures[(i//2)%8] if i&2 else None),preparation=optional(prepared[7 if i==31 else 0] if i&4 else None),preparation_messages=ledgers[6],bodies=('array',bodies),pairs=('array',children),work=works[i%2],reservation=ledgers[4],initial_request=optional(ledgers[2] if i&8 else None),candidate_bodies=optional(('array',candidates) if candidates is not None else None),message=('bytes',messages[i%4])))
 return 0x52475253,('array',rows)
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every14 GuardResult members, full original arrays, all32 optional masks and byte messages exact');leaves=[];present=absent=variants=0
 def walk(v):
  nonlocal present,absent,variants
  kind,value=v
  if kind=='object':
   for _,x in value:walk(x)
  elif kind=='array':
   for x in value:walk(x)
  elif kind=='present':present+=1;walk(value)
  elif kind=='absent':absent+=1
  elif kind=='variant':variants+=1;walk(value[1])
  else:leaves.append(v)
 walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits']
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=1,mappedFields=14,mappedVariants=0,fixtureRecords=32,rootOptionalMasks=32,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),present=present,absent=absent,totalVariantOccurrences=variants,leafKinds={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']},scope='Artificial32 GuardResults; all17 Reasons/5 Statuses and4 unknown ordinals each, all32 root optional masks, full7 original Pair records including duplicate/unexamined tail. No query/World Report/pump/game acceptance.')
def main():
 need(__debug__,'Optimized Python refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
