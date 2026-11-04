"""Independent held-load reference self-tests and captured-packet controls.

No production query, compiled kernel, or sampled trajectory is an oracle here.
All test invocations and later corpus controls can be archived by --output.
"""
from fractions import Fraction as F
import argparse
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check-sphere-triangle-mesh-held-load.py'
spec = importlib.util.spec_from_file_location('held_load_reference', SCRIPT)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
TRIANGLE = {'id': 37, 'vertices': [[0,0,0],[4,0,0],[0,0,4]]}


def source(position=(1,1,1), linear=(0,0,0), quadratic=(0,0,0), radius=F(1,4), horizon=F(1,16)):
    """Exact power-of-two conversion from tau to SI seconds, no fitted chord."""
    return {'sphere': {'id':7, 'position':list(position),
                       'velocity':[float(F(v)/horizon) for v in linear], 'mass':1,
                       'force':[float(2*F(q)/(horizon*horizon)) for q in quadratic],
                       'gravity':[0,0,0], 'radius':float(radius)},
            'horizon':float(horizon), 'triangles':[copy.deepcopy(TRIANGLE)]}


class MathematicalReferenceTests(unittest.TestCase):
    def test_full_quadratic_range_has_interior_extrema(self):
        self.assertEqual(reference.quadratic_range(1,-4,4,0,1),(0,1))
        self.assertEqual(reference.quadratic_range(0,4,-4,0,1),(0,1))
        self.assertEqual(reference.quadratic_range(1,2,0,F(1,4),F(1,2)),(F(3,2),2))

    def test_original_f_over_m_never_pointified(self):
        s=source(position=(0,2.**-64,0),radius=F(1,2**65))
        s['sphere'].update(mass=3,force=[0,-1,0],gravity=[0,1/3,0])
        self.assertEqual(reference.acceleration(s)[1],-F(1,3*2**54))
        self.assertEqual(1/3 + (-1)*(1/3),0)
        y=reference.path_point(s,F(1,16))[1]
        self.assertTrue(0<y<F(1,2**65))
        self.assertEqual(2*(F(1,2**64)-F(1,2**65))/(-reference.acceleration(s)[1]),F(3,1024))

    def test_chord_false_safe_has_quarter_entry(self):
        s=source((1,1,1),(0,-4,0),(0,4,0))
        self.assertEqual(reference.path_point(s,0),reference.path_point(s,F(1,16)))
        self.assertEqual(reference.path_range(s,0,F(1,16))[1],(0,1))
        for t in [F(1,64),F(3,64)]:
            self.assertEqual(reference.mesh_point_squared(reference.path_point(s,t),s['triangles']),F(1,16))
        self.assertEqual(reference.mesh_point_squared(reference.path_point(s,F(1,32)),s['triangles']),0)

    def test_chord_false_collision_quadratic_safely_detours(self):
        s=source((-2,F(1,8),1),(8,4,0),(0,-4,0))
        h=F(1,16)
        self.assertLessEqual(reference.path_range(s,0,h/8)[0][1],-1)
        self.assertGreaterEqual(reference.path_range(s,h/8,7*h/8)[1][0],F(9,16))
        self.assertGreaterEqual(reference.path_range(s,7*h/8,h)[0][0],5)
        self.assertLess(reference.point_triangle_squared((1,F(1,8),1),TRIANGLE['vertices']),F(1,16))

    def test_face_feasible_and_three_clamped_edges(self):
        cases=[((1,2,1),4),((1,2,-1),5),((-1,2,-1),6),((5,2,0),5),((2,2,2),4)]
        for p,d2 in cases:
            self.assertEqual(reference.point_triangle_squared(p,TRIANGLE['vertices']),d2)
        collapsed=[[1,0,0],[1,0,0],[1,0,0]]
        self.assertEqual(reference.point_triangle_squared((2,2,3),collapsed),14)

    def test_edge_quartic_has_quarter_entry(self):
        s=source((1,F(3,4),-F(1,4)),(0,-3,0),(0,3,0),F(5,16))
        for u in [F(0),F(1,4),F(1,2),F(3,4),F(1)]:
            value=reference.mesh_point_squared(reference.path_point(s,u/16),s['triangles'])
            self.assertEqual(value,9*(u-F(1,2))**4+F(1,16))
        self.assertEqual(reference.mesh_point_squared(reference.path_point(s,F(1,64)),s['triangles']),F(25,256))

    def test_vertex_quartic_has_quarter_entry(self):
        s=source((-F(3,16),3,-F(1,4)),(0,-12,0),(0,12,0),F(13,16))
        for u in [F(0),F(1,4),F(1,2),F(3,4),F(1)]:
            value=reference.mesh_point_squared(reference.path_point(s,u/16),s['triangles'])
            self.assertEqual(value,144*(u-F(1,2))**4+F(25,256))
        self.assertEqual(reference.mesh_point_squared(reference.path_point(s,F(1,64)),s['triangles']),F(169,256))

    def test_tangent_is_never_strictly_negative(self):
        s=source((1,F(1,2),1),(0,-1,0),(0,1,0))
        self.assertEqual(reference.path_range(s,0,F(1,16))[1][0],F(1,4))
        self.assertEqual(reference.mesh_point_squared(reference.path_point(s,F(1,32)),s['triangles']),F(1,16))

    def test_irreducible_cubic_stationary_minimum_nonvacuity(self):
        # f(u)=u^4-2u+9/4; f'=4u^3-2; alpha^3=1/2.
        # alpha<5/6 since (5/6)^3>1/2, hence f(alpha)=9/4-3alpha/2>1.
        self.assertGreater(F(5,6)**3,F(1,2))
        self.assertEqual(F(9,4)-F(3,2)*F(5,6),1)
        s=source((-1,-F(1,2),-1),(1,0,0),(0,1,0),F(17,16))
        self.assertEqual(reference.mesh_point_squared(reference.path_point(s,F(3,64)),s['triangles']),F(273,256))
        self.assertLess(F(273,256),F(17,16)**2)
        for t in [0,F(1,16)]:
            self.assertGreater(reference.mesh_point_squared(reference.path_point(s,t),s['triangles']),F(17,16)**2)

    def test_global_seconds_not_normalized_parameter(self):
        s=source((1,1,1),(0,-4,0),(0,4,0))
        self.assertEqual(reference.path_point(s,F(1,64))[1],F(1,4))
        self.assertNotEqual(reference.path_point(s,F(1,4))[1],F(1,4))
        reference.verify_width([.015625,.015625],0,F(1,64),F(1,32))
        with self.assertRaises(AssertionError):
            reference.verify_width([.25,.25],0,F(1,64),F(1,32))

    def test_path_box_rejects_endpoint_chord_and_missing_extremum(self):
        s=source((1,1,1),(0,-4,0),(0,4,0))
        reference.verify_path_box(s,[[1,1],[0,1],[1,1]],0,F(1,16))
        with self.assertRaises(AssertionError):
            reference.verify_path_box(s,[[1,1],[1,1],[1,1]],0,F(1,16))

    def test_r_e_root_proof_does_not_use_libm(self):
        reference.trajectory.verify_root([1,2],[1,2],(F(1),F(2)))
        with self.assertRaises(AssertionError):
            reference.trajectory.verify_root([1,2],[1,1],(F(1),F(2)))
        # A small negative outward squared LOWER is legitimate.
        reference.trajectory.verify_root([-2.**-1074,0],[0,0],(F(0),F(0)))

    def test_space_l1_is_stored_box_width_sum_not_time(self):
        s=source((0,2,0),(1,0,0),(0,0,0))
        w={'timeBounds':[0,.0625],'pathBounds':[[0,1],[2,2],[0,0]],'l1DiameterBound':[1,1]}
        stats={'windowSpatialReferences':0}
        reference.verify_window_space(s,w,stats)
        w['l1DiameterBound']=[.0625,.0625]
        with self.assertRaises(AssertionError): reference.verify_window_space(s,w,stats)

    def test_large_common_translation_keeps_exact_reference(self):
        p=(F(1,8),F(3,4),-F(1,4))
        offset=2**35
        d=reference.point_triangle_squared(p,TRIANGLE['vertices'])
        shifted=[[v+offset for v in x] for x in TRIANGLE['vertices']]
        self.assertEqual(reference.point_triangle_squared([v+offset for v in p],shifted),d)

    def test_strict_json_duplicate_nonfinite_underflow_and_signed_zero(self):
        for text in ['{"a":0,"a":1}','{"a":1e999}','{"a":1e-999}','{"a":NaN}']:
            with self.assertRaises((AssertionError,ValueError)): reference.loads(text)
        self.assertEqual(reference.bits(reference.loads('-0')),reference.bits(-0.0))
        self.assertNotEqual(reference.bits(-0.0),reference.bits(0.0))

    def test_integer_and_boolean_metadata_cannot_alias(self):
        for value in [False,True,-0.0,1.0]:
            with self.assertRaises(AssertionError): reference.uint(value,256,'strict integer')


def controls(data,baseline):
    fixtures=data['fixtures']
    records=[]
    def find(predicate):
        for index,f in enumerate(fixtures):
            if predicate(f): return index
        raise AssertionError('actual corpus lacks a planned control target')
    window=find(lambda f:f['result']['status']=='entry_window')
    separated=find(lambda f:f['result']['status']=='separated')
    invalid=find(lambda f:f['result']['status']=='invalid_input')
    tail=find(lambda f:len(f['result']['frontier'])>0 and len(f['result']['audits'])>1)
    queried=find(lambda f:f['result']['lastMesh'] is not None and f['result']['lastMesh']['rows'])
    def add(name,index,mutate):
        fixture=copy.deepcopy(fixtures[index]);mutate(fixture)
        stats={k:0 for k,v in baseline.items() if type(v) is int}
        try:
            reference.verify_fixture(fixture['input'],fixture['result'],stats)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:
            raise AssertionError('corruption accepted: '+name)
    def r(f): return f['result']
    def a(f):
        return next(v for v in r(f)['audits'] if v['kind']=='cell' and v['pathBounds'] is not None)
    def put(obj,key,value): obj[key]=value
    add('source position changed without snapshot',window,lambda f:put(f['input']['sphere']['position'],0,123.))
    add('source force changed without snapshot',window,lambda f:put(f['input']['sphere']['force'],1,123.))
    add('source horizon changed without snapshot',window,lambda f:put(f['input'],'horizon',.03125))
    add('sphere ID boolean alias',window,lambda f:put(f['input']['sphere'],'id',True))
    add('snapshot source signed zero lost',window,lambda f:put(r(f)['snapshot']['input']['force'],0,
        -0.0 if reference.bits(f['input']['sphere']['force'][0])==reference.bits(0.0) else 0.0))
    accel=find(lambda f: f['result']['acceleration'] is not None and any(x!=0 for x in reference.acceleration(f['input'])))
    add('acceleration replaced by zero',accel,lambda f:put(r(f),'acceleration',[[0,0]]*3))
    cancellation=find(lambda f:not reference.input_faults(f['input']) and f['input']['sphere']['mass']==3
                      and f['input']['sphere']['gravity'][1]==1/3 and f['input']['sphere']['force'][1]==-1)
    add('rounded F over m cancellation erases exact A',cancellation,lambda f:put(r(f),'acceleration',[[0,0]]*3))
    interior=find(lambda f:any(v['kind']=='cell' and v['pathBounds'] is not None
                    and any(lo<hi and min(reference.path_point(f['input'],reference.fraction(v['cell']['timeBounds'][0]))[i],
                                         reference.path_point(f['input'],reference.fraction(v['cell']['timeBounds'][1]))[i])>lo
                            for i,(lo,hi) in enumerate(reference.path_range(f['input'],*map(reference.fraction,v['cell']['timeBounds']))))
                    for v in f['result']['audits']))
    def chord(f):
        audit=next(v for v in r(f)['audits'] if v['kind']=='cell' and v['pathBounds'] is not None and
                   any(min(reference.path_point(f['input'],reference.fraction(v['cell']['timeBounds'][0]))[i],
                           reference.path_point(f['input'],reference.fraction(v['cell']['timeBounds'][1]))[i])>lo
                       for i,(lo,hi) in enumerate(reference.path_range(f['input'],*map(reference.fraction,v['cell']['timeBounds'])))))
        lo,hi=map(reference.fraction,audit['cell']['timeBounds'])
        endpoints=[reference.path_point(f['input'],lo),reference.path_point(f['input'],hi)]
        audit['pathBounds']=[[float(min(p[i] for p in endpoints)),float(max(p[i] for p in endpoints))] for i in range(3)]
    add('endpoint chord deletes quadratic interior extremum',interior,chord)
    add('point box replaced by arbitrary anchor',window,lambda f:put(a(f),'pointBounds',[[999,999]]*3))
    add('path box collapsed to selected point',window,lambda f:put(a(f),'pathBounds',copy.deepcopy(a(f)['pointBounds'])))
    add('whole velocity enclosure missing',window,lambda f:put(r(f),'wholeVelocityBounds',None))
    add('whole path enclosure false point',window,lambda f:put(r(f),'wholePathBounds',[[999,999]]*3))
    add('unjustified derived domain refusal',separated,lambda f:put(r(f),'reason','derived_domain'))
    add('normalised parameter instead of seconds',window,lambda f:put(a(f),'time',.5))
    add('cell time endpoints scaled to unit horizon',window,lambda f:put(a(f)['cell'],'timeBounds',[0,1]))
    add('cell depth boolean alias',window,lambda f:put(a(f)['cell'],'depth',False))
    add('cell work status boolean alias',window,lambda f:put(a(f),'meshStatus',False))
    add('cell work count float negative zero',window,lambda f:put(a(f)['work'],'meshQueries',-0.0))
    add('cell work certainty integer alias',window,lambda f:put(a(f)['work'],'workExact',1))
    add('total work erased',window,lambda f:put(r(f)['work'],'meshQueries',0))
    add('unreturned reservation erased',window,lambda f:put(a(f)['work'],'sqrtRefinementsUpper',0))
    add('R root below full squared bound',window,lambda f:put(a(f),'displacementRoot',[0,0]))
    add('R squared bound below path box',window,lambda f:put(a(f),'displacementSquaredBound',[0,0]))
    add('certificate pretends negative root bound',window,lambda f:put(a(f),'errorRoot',[-1,-1]))
    error_target=find(lambda f:any(v['errorRoot'] is not None and v['errorRoot'][1]>0 and
                  v['anchor'] is not None and reference.path_point(f['input'],reference.fraction(v['time']))!=reference.vector(v['anchor'])
                  for v in f['result']['audits']))
    def erased_e(f):
        audit=next(v for v in r(f)['audits'] if v['errorRoot'] is not None and v['errorRoot'][1]>0 and
                   reference.path_point(f['input'],reference.fraction(v['time']))!=reference.vector(v['anchor']))
        audit['errorSquaredBound']=[0,0];audit['errorRoot']=[0,0]
    add('anchor error correction E erased consistently',error_target,erased_e)
    add('clearance certificate fabricated',window,lambda f:put(a(f),'clearanceCertificate',[999,999]))
    add('penetration certificate fabricated',window,lambda f:put(a(f),'penetrationCertificate',[-999,-999]))
    add('prefix jumps over unresolved cells',window,lambda f:put(r(f),'safePrefix',[0,f['input']['horizon']]))
    add('window proof missing initial strict positive',window,lambda f:put(r(f),'initialSeparationProven',False))
    add('negative witness alone fabricates prefix',window,lambda f:put(r(f),'safePrefix',[0,r(f)['bestWitness']['time']]))
    add('window width is normalised time',window,lambda f:put(r(f)['window'],'timeWidth',[1,1]))
    add('window extends before safe prefix',window,lambda f:put(r(f)['window']['timeBounds'],0,-1.))
    add('window path bounds replaced by point',window,lambda f:put(r(f)['window'],'pathBounds',[[999,999]]*3))
    add('time width substituted for metre diameter',window,lambda f:put(r(f)['window'],'l1DiameterBound',copy.deepcopy(r(f)['window']['timeWidth'])))
    add('window witness audit alias boolean',window,lambda f:put(r(f)['window'],'witnessAuditIndex',False))
    add('conservative IDs tail removed',window,lambda f:r(f)['candidateSurfaceIds'].pop())
    add('conservative IDs narrowed to one invented ID',window,lambda f:put(r(f),'candidateSurfaceIds',[999999]))
    add('witness point no longer at exact seconds',window,lambda f:put(r(f)['bestWitness'],'time',0.))
    add('witness owner changed',window,lambda f:put(r(f)['bestWitness'],'auditIndex',0))
    add('safe separated status replaces real entry',window,lambda f:put(r(f),'status','separated'))
    add('certified island removed',window,lambda f:r(f)['certifiedLeaves'].pop())
    add('partition tail removed',tail,lambda f:r(f)['partition'].pop())
    add('frontier tail removed',tail,lambda f:r(f)['frontier'].pop())
    add('partition owner boolean alias',window,lambda f:put(r(f)['partition'][0],'auditIndex',False))
    add('partition closed coverage hole',window,lambda f:put(r(f)['partition'][0]['cell']['timeBounds'],0,.001))
    island=find(lambda f:f['result']['safePrefix'] is not None and any(
        v['cell']['timeBounds'][0]>f['result']['safePrefix'][1] for v in f['result']['certifiedLeaves']))
    def promote_island(f):
        leaf=next(v for v in r(f)['certifiedLeaves'] if v['cell']['timeBounds'][0]>r(f)['safePrefix'][1])
        r(f)['safePrefix']=[0,leaf['cell']['timeBounds'][1]]
    add('later positive island promoted over earlier unknown',island,promote_island)
    add('last mesh belongs to initial instead of real audit',window,lambda f:put(r(f),'lastMeshAuditIndex',0))
    add('last mesh source changed',queried,lambda f:put(r(f)['lastMesh']['rows'][0]['triangle'],'id',999))
    add('last mesh row omitted',queried,lambda f:r(f)['lastMesh']['rows'].pop())
    add('last mesh candidate omitted',queried,lambda f:r(f)['lastMesh']['rows'][0]['query']['candidates'].pop())
    add('last mesh status boolean alias',queried,lambda f:put(r(f)['lastMesh'],'status',False))
    add('invalid preflight invents acceleration',invalid,lambda f:put(r(f),'acceleration',[[0,0]]*3))
    add('invalid preflight invents prefix',invalid,lambda f:put(r(f),'safePrefix',[0,0]))
    add('maximum depth float negative zero',window,lambda f:put(r(f),'maximumDepth',-0.0))
    full=find(lambda f:len(f['result']['audits'])==256 and len(f['result']['certifiedLeaves'])==128)
    add('capacity audit256 tail time corrupted',full,lambda f:put(r(f)['audits'][-1],'time',0.))
    add('capacity certified leaf128 certificate corrupted',full,lambda f:put(r(f)['certifiedLeaves'][-1],'lowerGapCertificate',[999,999]))
    all_ids=find(lambda f:len(f['result']['candidateSurfaceIds'])==64)
    add('capacity candidate ID64 tail removed',all_ids,lambda f:r(f)['candidateSurfaceIds'].pop())
    add('capacity last mesh row64 surface ID corrupted',all_ids,lambda f:put(r(f)['lastMesh']['rows'][-1]['query']['geometry'],'surfaceId',999))
    reservation=find(lambda f:f['result']['reason']=='sqrt_budget' and any(a['meshQueried'] for a in f['result']['audits']))
    def unjustified_budget(f):
        f['input']['settings']['maxTotalSqrtRefinements']=1000000
        r(f)['snapshot']['settings']['maxTotalSqrtRefinements']=1000000
    add('norm reservation stop with available R and E capacity',reservation,unjustified_budget)
    for name,mutate in [('fixture omitted',lambda p:p['fixtures'].pop()),
                        ('fixture duplicated',lambda p:p['fixtures'].__setitem__(-1,copy.deepcopy(p['fixtures'][0]))),
                        ('source bit change fixed corpus',lambda p:put(p['fixtures'][0]['input']['sphere']['force'],0,.125))]:
        packet=copy.deepcopy(data);mutate(packet)
        try: reference.verify(packet)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else: raise AssertionError('whole corpus corruption accepted: '+name)
    return records


def main():
    if not __debug__:
        raise AssertionError('run reference tests without Python -O')
    parser=argparse.ArgumentParser()
    parser.add_argument('fixture',nargs='?')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MathematicalReferenceTests))
    reference.need(result.wasSuccessful(),stream.getvalue())
    report={'status':'PASS','selfTestGroups':result.testsRun}
    if args.fixture:
        data=reference.load(args.fixture)
        baseline=reference.verify(data)
        records=controls(data,baseline)
        independent=copy.deepcopy(data)
        independent['fixtures'].reverse()
        for index,f in enumerate(independent['fixtures']): f['name']='independent-name-'+str(index)
        reference.need(reference.verify(independent)==baseline,'no label/order dependence')
        command=[sys.executable,'-O',str(SCRIPT),args.fixture]
        optimized=subprocess.run(command,capture_output=True,text=True,timeout=120)
        reference.need(optimized.returncode!=0 and 'without Python -O' in optimized.stderr,'optimized Python must fail closed')
        records.append({'name':'Python -O rejected','rejected':True,'diagnostic':optimized.stderr.strip().splitlines()[-1]})
        report.update(baseline=baseline,rejectedControls=records,labelAndOrderIndependent=True)
    if args.output:
        args.output.mkdir(parents=True,exist_ok=False)
        paths=[SCRIPT,Path(__file__),ROOT/'scripts/verify-sphere-triangle-mesh-trajectory.py',ROOT/'scripts/verify-sphere-triangle-mesh.py',ROOT/'scripts/verify-sphere-triangle.py']
        if args.fixture: paths.append(Path(args.fixture))
        provenance=[{'path':str(p.resolve()),'bytes':len(p.read_bytes()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
        (args.output/'negative-controls.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        (args.output/'reference-self-tests.txt').write_text(stream.getvalue(),encoding='utf-8')
        (args.output/'commands.json').write_text(json.dumps({'argv':sys.argv,'python':sys.version},indent=2)+'\n',encoding='utf-8')
        (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
        if args.fixture:
            (args.output/'reference.json').write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
            (args.output/'optimized.stdout.txt').write_text(optimized.stdout,encoding='utf-8')
            (args.output/'optimized.stderr.txt').write_text(optimized.stderr,encoding='utf-8')
            (args.output/'optimized-command.json').write_text(json.dumps({'command':command,'exitCode':optimized.returncode},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'rejectedControls','baseline'}} |
                     ({'fixtures':baseline['fixtures'],'rejectedControls':len(records)} if args.fixture else {})))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
