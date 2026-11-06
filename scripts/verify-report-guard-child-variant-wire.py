"""Independent Child variant specification with all three actual child branches."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
mesh=module('child_mesh','scripts/verify-report-guard-mesh-call-wire.py')
plane=module('child_plane','scripts/verify-report-guard-plane-calls-wire.py')
sphere=module('child_sphere','scripts/verify-report-guard-sphere-box-call-wire.py');wire=mesh.wire
def need(v,m):
 if not v:raise ValueError(m)
def expected():
 m=mesh.expected()[1][1];p=plane.expected()[1][1];s=sphere.expected()[1][1]
 return 0x52474348,('array',[('variant',(i,v)) for i,v in [(0,m[0]),(1,p[3]),(2,s[0]),(0,m[15]),(1,p[7]),(2,s[15])]])
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'All3 Child ordinals and full original nested values exact')
 need([v[1][0] for v in actual[1][1]]==[0,1,2,0,1,2],'All6 explicit ordered active children')
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
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=0,mappedFields=0,mappedVariants=1,fixtureRecords=6,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),present=present,absent=absent,totalVariantOccurrences=variants,leafKinds={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']},scope='Artificial6 active Child variants across all3 alternatives and full nested values. Legitimate valueless reachability measured separately; no model query/Pair/GuardResult/World Report/pump/game acceptance.')
def main():
 need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
