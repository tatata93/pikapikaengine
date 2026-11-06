"""Independent artificial typed prepare-pair/StaticOnlyCounts specification; no model query."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_values_wire',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
 if not v:raise ValueError(m)
def expected():
 def obj(**v):return ('object',[(key.encode(),value) for key,value in v.items()])
 kinds=[0,1,2,3,2**31,2**32-1];counts=[0,2**64-1,2**53+1,2**63];totals=[0,2**64-1,2**53+1,2**63,17,42,2**64-2]
 refs=[obj(kind=('enum',kinds[i]),id=('u64',counts[i%4]),ordinal=('u64',counts[(i+1)%4]),revision=('u64',counts[(i+2)%4])) for i in range(6)]
 pairs=[obj(kind=('enum',kinds[i]),first=refs[i],second=refs[5-i]) for i in range(6)]
 names=['body_body','body_plane','body_mesh','plane_plane','plane_mesh','mesh_mesh','total']
 excluded=[obj(**{key:('u64',totals[(i+j)%7]) for j,key in enumerate(names)}) for i in range(4)]
 return 0x52505056,('array',refs+pairs+excluded)
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every original typed reference, pair order and excluded count exact')
 leaves=[]
 def walk(v):
  kind,value=v
  if kind=='object':
   for _,item in value:walk(item)
  elif kind=='array':
   for item in value:walk(item)
  else:leaves.append(v)
 walk(actual[1]);need(len(leaves)==106,'All106 typed integer/enum leaves')
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=3,mappedFields=14,mappedVariants=0,fixtureRecords=16,allTypedLeaves=len(leaves),present=0,absent=0,totalVariantOccurrences=0,leafKinds={k:sum(kind==k for kind,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']},scope='Artificial6 ColliderRef,6 ordered Pair and4 independent StaticOnlyCounts. Not prepare/GuardResult/World Report/numerical/game acceptance.')
def main():
 need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
