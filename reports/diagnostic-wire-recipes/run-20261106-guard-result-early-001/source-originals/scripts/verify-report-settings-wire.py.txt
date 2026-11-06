"""Independent typed oracle for all ten report setting structures."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('diagnostic_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    floating=[int(x,16) for x in ['0','8000000000000000','1','8000000000000001','fffffffffffff','10000000000000',
        '3ff0000000000000','bff0000000000000','7fefffffffffffff','ffefffffffffffff','7ff0000000000000','fff0000000000000',
        '7ff8000000000042','fff8000000001234','7ff0000000000001','fff0000000000001']]
    nf,nu,nc=9,0,0
    def f():
        nonlocal nf
        value=('f64bits',floating[nf%16]);nf+=1;return value
    def u():
        nonlocal nu
        n=nu;nu+=1;return ('u32',0 if n==0 else 2**32-1 if n==1 else 0x80000002 if n==2 else 2**32-1-17*n)
    def count():
        nonlocal nc
        n=nc;nc+=1;return ('u64',0 if n==0 else 2**64-1 if n==1 else 2**53+1 if n==2 else 2**63 if n==3 else 2**64-1-17*n)
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    primitive=obj(max_candidates=u(),sqrt_refinements=u(),max_total_sqrt_refinements=u(),maximum_local_width=f(),maximum_normal_width=f(),minimum_sine_squared=f())
    mesh=obj(max_surfaces=count(),primitive=primitive)
    held=obj(mesh=mesh,time_tolerance=f(),max_evaluations=count(),max_leaves=count(),max_depth=u(),enclosure_sqrt_refinements=u(),max_total_sqrt_refinements=count())
    free=obj(held_load=held,max_angular_increment=f())
    metric=obj(time_tolerance=f(),max_evaluations=count(),max_leaves=count(),max_depth=u())
    plane=obj(time_tolerance=f(),max_evaluations=count(),max_leaves=count(),max_depth=u())
    sphere=obj(time_tolerance=f(),max_evaluations=count(),max_leaves=count(),max_depth=u(),sqrt_refinements=u())
    preparation=obj(max_bodies=count(),max_planes=count(),max_meshes=count(),max_total_faces=count(),max_pairs=count())
    keys=['body_records','pair_records','held_audits','held_certified_leaves','held_partition','held_frontier',
        'primitive_audits','primitive_partition','primitive_frontier','last_mesh_rows','primitive_candidates','retained_faces',
        'mesh_queries','primitive_queries','candidates_examined','sqrt_refinements','plane_metric_values','box_values','propagations','logical_payload_bytes']
    limits=obj(**{k:count() for k in keys})
    guard=obj(preparation=preparation,mesh=free,plane_metric=metric,plane_box=plane,sphere_box=sphere,contact_margin=f(),limits=limits)
    need((nf,nu,nc)==(18,9,35),'Independent field generator counts')
    return 0x52535431,('array',[primitive,mesh,held,free,metric,plane,sphere,preparation,limits,guard])
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every typed setting field, raw bit and order')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits'];need(len(floats)==27,'All27 float field occurrences')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=10,mappedFields=62,fixtureRecords=10,
        mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),allTypedLeaves=len(leaves),u32Fields=sum(k=='u32' for k,_ in leaves),u64Fields=sum(k=='u64' for k,_ in leaves),
        scope='Ten setting value structures only. Invalid settings remain diagnostic data; no model admission, complete Report/pump or JS/WASM/game acceptance.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
