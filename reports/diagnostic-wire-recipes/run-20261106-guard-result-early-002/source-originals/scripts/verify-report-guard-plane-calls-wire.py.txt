"""Independent PlaneCalls composition of original metric and box child specifications."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
metric=module('plane_calls_metric','scripts/verify-report-guard-plane-metric-call-wire.py')
box=module('plane_calls_box','scripts/verify-report-guard-plane-box-call-wire.py');wire=metric.wire
def need(v,m):
 if not v:raise ValueError(m)
def fields(v):return dict(v[1])
def expected():
 m=metric.expected()[1][1];b=box.expected()[1][1];indices=[0,1,2,3,4,5,14,15]
 return 0x52475043,('array',[('object',[(b'metric',m[n]),(b'box',b[indices[7-i]])]) for i,n in enumerate(indices)])
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Both full original child calls in declaration order')
 need(len(actual[1][1])==8 and all([k for k,_ in v[1]]==[b'metric',b'box'] for v in actual[1][1]),'All8 roots and exactly2 ordered fields')
 leaves=[];present=absent=variants=0
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
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=1,mappedFields=2,fixtureRecords=8,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),present=present,absent=absent,nestedVariants=variants,leafKinds={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']},scope='Artificial8 PlaneCalls,16 complete crossed metric/box calls. Original optional results, attempt positions, settings,grants,Input variants and all tail retained. No model query or World Report/pump/game acceptance.')
def main():
 need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
