"""Independent typed oracle for all22 guard::Work members, including independent exact flags."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('diagnostic_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
    if not v:raise ValueError(m)
def expected():
    def u(v):return ('u64',v)
    def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
    def counter(k,h,e):return obj(known=u(k),upper=u(h),exact=('bool',e))
    def work(second):
        held=obj(mesh_queries=counter(0,2**64-1,False),primitive_queries=counter(2**53+1,0,True),candidates_examined=counter(2**64-1,1,False),
            primitive_sqrt_refinements=counter(17,19,True),enclosure_sqrt_refinements=counter(23,29,False),sqrt_refinements=counter(31,37,True),
            mesh_sqrt_limited_rows=counter(41,43,False),enclosure_sqrt_calls=counter(2**53+7 if second else 47,53,True),enclosure_sqrt_limited_calls=counter(59,61,False))
        return obj(child_calls_attempted=u(2**64-2 if second else 0),child_calls_returned=u(2**64-1),mesh_calls_attempted=u(2**53+1),mesh_calls_returned=u(2**63),
            plane_metric_calls_attempted=u(11),plane_metric_calls_returned=u(13),plane_box_calls_attempted=u(17),plane_box_calls_returned=u(19),
            sphere_box_calls_attempted=u(23),sphere_box_calls_returned=u(29),held=held,propagation_attempts=counter(0,2**64-1,not second),
            plane_metric_values=counter(37,41,False),box_values=counter(43,47,True),bridge_calls_upper=u(61),plane_norm_calls_upper=u(67),plane_norm_loop_iterations_upper=u(71),
            sphere_root_results_returned=u(73),sphere_root_limited_returns=u(79),sphere_sqrt_refinements=counter(83,89,True),sqrt_refinements=counter(97,101,second),exact=('bool',second))
    return 0x52574b31,('array',[work(False),work(True)])
def verify(data):
    actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every Work field, full-width integer, independent exact flag and record order')
    leaves=[]
    def walk(node):
        kind,value=node
        if kind=='object':
            for _,v in value:walk(v)
        elif kind=='array':
            for v in value:walk(v)
        else:leaves.append(node)
    walk(actual[1]);need(len(leaves)==116,'All nested Work scalar occurrences')
    return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedTypes=1,mappedFields=22,fixtureRecords=2,
        allTypedLeaves=len(leaves),u64Fields=sum(k=='u64' for k,_ in leaves),booleanFields=sum(k=='bool' for k,_ in leaves),
        scope='One guard Work structure only; records contain deliberately inconsistent diagnostic values. No numerical work measurement, full Report/pump or JS/WASM/game acceptance.')
def main():
    need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args()
    need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
    if a.hex:data=bytes.fromhex(data.decode('ascii'))
    print(json.dumps(verify(data)))
if __name__=='__main__':main()
