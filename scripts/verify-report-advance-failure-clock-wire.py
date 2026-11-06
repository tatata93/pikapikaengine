"""Independent advance Failure2/ClockAudit4 values; no clock reconstruction or advance call."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
failure=module('advance_failure_locations','scripts/verify-report-guard-failure-wire.py');intervals=module('advance_stored_intervals','scripts/verify-report-intervals-wire.py');wire=failure.wire
def need(v,m):
 if not v:raise ValueError(m)
def expected():
 def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
 original=failure.expected()[1][1][:8];bounds=intervals.expected()[1][1][:9];unknown=[2**32-1,2**31,2**31-1,2**32-2]
 bits=[int(x,16) for x in ['0','8000000000000000','1','8000000000000001','fffffffffffff','10000000000000','3ff0000000000000','bff0000000000000','7fefffffffffffff','ffefffffffffffff','7ff0000000000000','fff0000000000000','7ff8000000000042','fff8000000001234','7ff0000000000001','fff0000000000001']]
 failures=[obj(stage=('enum',i%6 if i<12 else unknown[i-12]),object=('present',original[i//2]) if i%2 else ('absent',None)) for i in range(16)]
 clocks=[obj(time_sum=bounds[i%9],represented_difference=bounds[(i+3)%9],sum_rounding_error=bounds[(i+6)%9],represented_dt=('f64bits',bits[i])) for i in range(16)]
 return 0x5241434b,('array',failures+clocks)
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'All Stage ordinals, original object locations, stored endpoint bits and represented_dt bits exact');leaves=[];present=absent=0
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
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=2,mappedFields=6,mappedVariants=0,fixtureRecords=32,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),present=present,absent=absent,totalVariantOccurrences=0,leafKinds={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']},scope='Artificial16 Failure values (all6 Stage/4 unknown ordinals and all8 original locations) plus16 ClockAudits (9 legally constructed intervals and all16 represented_dt bit patterns). No sqrt call, clock arithmetic/reconstruction, advance/World Report/pump/game acceptance.')
def main():
 need(__debug__,'Optimized Python refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
