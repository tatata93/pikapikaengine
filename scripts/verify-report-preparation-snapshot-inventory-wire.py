"""Independent owned Snapshot6/Inventory7 values from original leaf and typed-pair specifications."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
leaf=module('snapshot_leaf','scripts/verify-report-values-wire.py');pairs=module('snapshot_pair','scripts/verify-report-preparation-pair-values-wire.py');wire=leaf.wire
def need(v,m):
 if not v:raise ValueError(m)
def expected():
 def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
 def arr(v):return ('array',v)
 def alter(v,**changes):return ('object',[(k,changes.get(k.decode(),x)) for k,x in v[1]])
 base=leaf.expected()[1][1];p=pairs.expected()[1][1];body,plane,mesh,empty=base[0],base[1],base[3],base[12]
 bits=[int(x,16) for x in ['0','8000000000000000','1','8000000000000001','fffffffffffff','10000000000000','3ff0000000000000','bff0000000000000','7fefffffffffffff','ffefffffffffffff','7ff0000000000000','fff0000000000000','7ff8000000000042','fff8000000001234','7ff0000000000001','fff0000000000001']]
 counts=[0,2**64-1,2**53+1,2**63,17];snapshots=[];inventories=[]
 bodies=[[],[body,alter(body,id=('u64',0),is_static=('bool',False))],[alter(body,id=('u64',2**53+1),mass=('f64bits',2**63))],[]]
 planes=[[],[plane,alter(plane,id=('u64',0))],[],[alter(plane,normal=base[9])]]
 meshes=[[],[mesh,empty],[empty,mesh,empty],[]];pair_rows=[[],[p[11],p[6],p[11]],[p[10],p[8]],[p[9],p[8],p[7],p[6]]]
 for i in range(4):
  f=lambda j:('f64bits',bits[4*i+j]);settings=obj(**{k:('u64',counts[(i+j)%5]) for j,k in enumerate(['max_bodies','max_planes','max_meshes','max_total_faces','max_pairs'])})
  snapshots.append(obj(gravity=obj(x=f(0),y=f(1),z=f(2)),horizon=f(3),settings=settings,bodies=arr(bodies[i]),planes=arr(planes[i]),meshes=arr(meshes[i])))
  inventories.append(obj(**{k:('u64',counts[(i+j)%5]) for j,k in enumerate(['dynamic_bodies','static_bodies','total_faces','colliders','all_pairs'])},excluded=p[12+i],pairs=arr(pair_rows[i])))
 return 0x52505349,arr(snapshots+inventories)
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'All owned snapshot arrays, original bit values and inventory order/counts exact');leaves=[]
 def walk(v):
  kind,value=v
  if kind=='object':
   for _,x in value:walk(x)
  elif kind=='array':
   for x in value:walk(x)
  else:leaves.append(v)
 walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits']
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=2,mappedFields=13,mappedVariants=0,fixtureRecords=8,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),present=0,absent=0,totalVariantOccurrences=0,leafKinds={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']},scope='Artificial4 owned Snapshots and4 complete Inventories. Invalid/duplicate/original array values preserved; no prepare invocation/numerical/Result/World Report/pump/game acceptance.')
def main():
 need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
