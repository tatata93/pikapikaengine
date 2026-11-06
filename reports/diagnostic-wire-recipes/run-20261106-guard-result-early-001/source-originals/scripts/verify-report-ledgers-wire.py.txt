"""Independent exact typed oracle for seven guard ledger value structures."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('diagnostic_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)

def need(v,m):
    if not v:raise ValueError(m)

def expected():
    def u(v):return ('u64',v)
    def b(v):return ('bool',v)
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def counter(k,h,e):return obj(known=u(k),upper=u(h),exact=b(e))
    def retained():return obj(body_records=u(0),pair_records=u(2**64-1),held_audits=u(2**53+1),held_certified_leaves=u(2**63),
        held_partition=u(5),held_frontier=u(7),primitive_audits=u(11),primitive_partition=u(13),primitive_frontier=u(17),
        last_mesh_rows=u(19),primitive_candidates=u(23),retained_faces=u(29),logical_payload_bytes=u(31))
    def work(v):
        need(len(v)==9,'Nine distinct work values')
        return obj(mesh_queries=u(v[0]),primitive_queries=u(v[1]),candidates_examined=u(v[2]),sqrt_refinements=u(v[3]),
            propagations=u(v[4]),plane_metric_values=u(v[5]),box_values=u(v[6]),plane_norm_loop_iterations_upper=u(v[7]),bridge_calls_upper=u(v[8]))
    c=counter(0,2**64-1,False)
    held=obj(mesh_queries=counter(0,2**64-1,False),primitive_queries=counter(2**53+1,0,True),candidates_examined=counter(2**64-1,1,False),
        primitive_sqrt_refinements=counter(17,19,True),enclosure_sqrt_refinements=counter(23,29,False),sqrt_refinements=counter(31,37,True),
        mesh_sqrt_limited_rows=counter(41,43,False),enclosure_sqrt_calls=counter(47,53,True),enclosure_sqrt_limited_calls=counter(59,61,False))
    grant=work([2**64-1,2**53+1,0,2**63,37,41,43,47,53])
    reservation=obj(retained=retained(),granted=grant,charged=work([0,1,2,3,5,8,13,21,34]))
    request=obj(retained=retained(),work=work([55,89,144,233,377,610,987,1597,2584]))
    omission=obj(fields=u(2**64-1),nonempty_fields=u(0),bytes=u(2**53+1),omitted=b(True))
    return 0x524c4431,('array',[c,held,retained(),grant,reservation,request,omission])

def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every ledger key, type, value, order and nesting')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);need(len(leaves)==109,'All nested ledger scalar occurrences')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=7,mappedFields=43,fixtureRecords=7,
        allTypedLeaves=len(leaves),u64Fields=sum(k=='u64' for k,_ in leaves),booleanFields=sum(k=='bool' for k,_ in leaves),
        scope='Seven ledger value structures only; no numerical success, complete Report, pump, JS/WASM or game acceptance.')

def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
