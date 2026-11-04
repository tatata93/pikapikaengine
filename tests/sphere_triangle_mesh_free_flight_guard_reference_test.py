"""Independent integer RN/ULP proof self-tests and finite-corpus controls."""
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

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/check-sphere-triangle-mesh-free-flight-guard.py'
spec=importlib.util.spec_from_file_location('free_guard_reference',SCRIPT)
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


def body(**kwargs):
    result={'id':7,'isStatic':False,'mass':1,'radius':.25,'position':[1,2,1],
            'velocity':[8,0,0],'force':[0,0,0]}
    result.update(kwargs)
    return result


class OperationReferenceTests(unittest.TestCase):
    def test_nearest_ties_even_at_one(self):
        self.assertEqual(reference.raw_bits(reference.rn(1+F(1,2**53))),reference.raw_bits(1.))
        self.assertEqual(reference.raw_bits(reference.rn(1+3*F(1,2**53))),reference.raw_bits(1.)+2)
        self.assertEqual(reference.rn(-1-F(1,2**53)),-1.)

    def test_subnormal_boundary_and_half_underflow(self):
        self.assertEqual(reference.raw_bits(reference.rn(F(1,2**1075))),0)
        self.assertEqual(reference.raw_bits(reference.rn(3*F(1,2**1075))),2)
        self.assertEqual(reference.raw_bits(reference.rn(-F(1,2**1075))),1<<63)
        self.assertEqual(reference.raw_bits(reference.rn(F(1,2**1022)-F(1,2**1075))),1<<52)

    def test_integer_rn_all_exponents_independent_bits(self):
        for exponent in [-1074,-1022,-512,-1,0,1,52,500,1023]:
            exact=F(2)**exponent
            self.assertEqual(F(reference.rn(exact)),exact)
            for sign in [-1,1]:
                # Python conversion is only a cross-check of this INTEGER RN,
                # never used to calculate the proof or expected Native packet.
                value=sign*(exact+exact/F(2**54))
                self.assertEqual(reference.raw_bits(reference.rn(value)),reference.raw_bits(float(value)))

    def test_signed_zero_operation_graph(self):
        self.assertEqual(reference.raw_bits(reference.rn_add(-0.,-0.)),1<<63)
        self.assertEqual(reference.raw_bits(reference.rn_add(-0.,0.)),0)
        self.assertEqual(reference.raw_bits(reference.rn_add(1.,-1.)),0)
        self.assertEqual(reference.raw_bits(reference.rn_mul(-0.,2.)),1<<63)
        self.assertEqual(reference.raw_bits(reference.rn_div(-0.,2.)),1<<63)

    def test_ceil_and_spacing_at_binade(self):
        self.assertEqual(reference.spacing_bound(1),F(1,2**52))
        self.assertEqual(reference.spacing_bound(1-F(1,2**54)),F(1,2**52))
        self.assertEqual(reference.spacing_bound(0),F(1,2**1074))
        self.assertGreaterEqual(F(reference.ceil_binary64(F(1,3))),F(1,3))

    def test_f_over_m_nominal_and_real_differ(self):
        b=body(mass=3,force=[0,-1,0],velocity=[0,0,0],position=[0,2.**-64,0])
        r=reference.all_duration_reference(b,[0,1/3,0],.0625)
        self.assertEqual(r['nominalAcceleration'][1],0.)
        self.assertEqual(r['exactAcceleration'][1],-F(1,3*2**54))
        self.assertEqual(r['coefficient'],F(1,3*2**63))
        self.assertGreater(r['total'],r['roundoff'])

    def test_graph_reassociation_is_observable(self):
        b=body(position=[-2.**53,0,0],velocity=[2.**57,0,0],force=[512,0,0])
        # At H=1/16 p+vH cancels FIRST, then adds a*(.5H^2)=1.
        self.assertEqual(reference.nominal_position(b,[0,0,0],.0625)[0],1.)
        reassociated=reference.rn_add(b['position'][0],reference.rn_add(2.**53,1.))
        self.assertEqual(reassociated,0.)

    def test_fma_contraction_changes_declared_in_domain_graph(self):
        b=body(position=[-1,0,0],velocity=[16+2.**-23,0,0])
        t=float((1-F(1,2**27))/16)
        self.assertEqual(reference.nominal_position(b,[0,0,0],t)[0],0.)
        fused=reference.rn(F(b['position'][0])+F(b['velocity'][0])*F(t))
        self.assertEqual(fused,-2.**-54)

    def test_q_s_multiply_underflow_is_preserved(self):
        b=body(position=[0,0,0],velocity=[0,0,0],force=[1,0,0])
        self.assertEqual(reference.nominal_position(b,[0,0,0],2.**-1074),(0.,0.,0.))
        r=reference.all_duration_reference(b,[0,0,0],2.**-1074)
        self.assertGreater(r['roundoff'],0)

    def test_recurrence_all_duration_bound_and_finite_samples(self):
        for b,g in [(body(),[0,-9.80665,0]),
                    (body(mass=3,position=[2.**35,-2.**35,1],force=[1,-1,3]),[0,1/3,0]),
                    (body(position=[0,-0.,0],velocity=[2.**-1022,0,0],force=[2.**-1000,0,0]),[0,0,0])]:
            result=reference.all_duration_reference(b,g,.0625)
            self.assertGreaterEqual(result['total'],result['coefficient'])
            for t in [0.,2.**-1074,.0625/64,.0625/3,.0625]:
                actual=reference.nominal_position(b,g,t)
                exact=reference.held.add(reference.vector(b['position']),reference.held.add(
                    reference.held.scale(reference.vector(b['velocity']),F(t)),
                    reference.held.scale(result['exactAcceleration'],F(t)**2/2)))
                error=sum(abs(F(x)-y) for x,y in zip(actual,exact))
                self.assertLessEqual(error,result['total'])

    def test_rn_avoids_fma_and_nonfinite(self):
        with self.assertRaises(AssertionError): reference.rn(F(2)**1024)
        with self.assertRaises(AssertionError): reference.rn_div(1,0)
        with self.assertRaises(AssertionError): reference.spacing_bound(-1)

    def test_whole_input_fingerprint_preserves_bool_and_zero_sign(self):
        def fingerprint(x):return reference.input_fingerprint([{'input':x}])
        self.assertNotEqual(fingerprint({'x':False}),fingerprint({'x':0}))
        self.assertNotEqual(fingerprint({'x':-0.}),fingerprint({'x':0.}))
        self.assertEqual(fingerprint({'b':True,'a':1}),fingerprint({'a':1,'b':True}))


def controls(data,baseline):
    fixtures=data['fixtures'];records=[]
    def find(predicate):
        for index,f in enumerate(fixtures):
            if predicate(f):return index
        raise AssertionError('required actual guard corruption target missing')
    def r(f):return f['result']
    def put(obj,key,value):obj[key]=value
    success=find(lambda f:r(f)['status']=='certified_separated')
    invalid=find(lambda f:r(f)['status']=='invalid_input')
    inflated_failure=find(lambda f:r(f)['inflated'] is not None and r(f)['inflated']['status']=='entry_window')
    coeff=find(lambda f:r(f)['tube'] is not None and
        reference.all_duration_reference(f['input']['body'],f['input']['gravity'],f['input']['horizon'])['coefficient']>reference.fraction(r(f)['tube']['roundoff']))
    def add(name,index,mutate):
        fixture=copy.deepcopy(fixtures[index]);mutate(fixture)
        reference.need(json.dumps(fixture,sort_keys=True)!=json.dumps(fixtures[index],sort_keys=True),
                       'control must actually change its packet: '+name)
        stats={k:0 for k,v in baseline.items() if type(v) is int};stats['held']=reference.held_stats()
        try:reference.verify_fixture(fixture['input'],fixture['result'],stats)
        except (AssertionError,ValueError,KeyError,TypeError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:raise AssertionError('guard corruption accepted: '+name)
    add('total B erased',success,lambda f:put(r(f)['tube'],'positionError',0.))
    add('roundoff recurrence erased',success,lambda f:put(r(f)['tube'],'roundoff',0.))
    add('F over m coefficient error deleted from B',coeff,lambda f:put(r(f)['tube'],'positionError',r(f)['tube']['roundoff']))
    add('exact acceleration replaced by nominal point',coeff,lambda f:put(r(f)['tube'],'exactAcceleration',[[x,x] for x in r(f)['tube']['nominalAcceleration']]))
    add('acceleration discrepancy erased',coeff,lambda f:put(r(f)['tube'],'accelerationDifference',[[0,0]]*3))
    add('nominal acceleration replaced by wrong graph',success,lambda f:put(r(f)['tube']['nominalAcceleration'],0,123.))
    add('guard radius uses original radius',success,lambda f:put(r(f)['tube'],'guardRadius',f['input']['body']['radius']))
    floor_case=find(lambda f:r(f)['tube'] is not None and
        reference.fraction(reference.rn(reference.fraction(f['input']['body']['radius'])+reference.fraction(r(f)['tube']['positionError'])))<
        reference.fraction(f['input']['body']['radius'])+reference.fraction(r(f)['tube']['positionError']))
    add('radius plus B rounded downward',floor_case,lambda f:put(r(f)['tube'],'guardRadius',reference.rn(
        reference.fraction(f['input']['body']['radius'])+reference.fraction(r(f)['tube']['positionError']))))
    add('published candidate position changed one ULP',success,lambda f:put(r(f)['candidate']['position'],0,
        reference.float_from_bits(reference.raw_bits(r(f)['candidate']['position'][0])+1)))
    add('candidate endpoint incorrectly uses real acceleration',coeff,lambda f:put(r(f)['endpoint'],'nominalPosition',[[999,999]]*3))
    add('candidate velocity changed',success,lambda f:put(r(f)['candidate']['velocity'],0,999.))
    add('candidate angular momentum changed',success,lambda f:put(r(f)['candidate']['angularMomentum'],0,999.))
    forced=find(lambda f:r(f)['candidate'] is not None and any(f['input']['body']['force']))
    torqued=find(lambda f:r(f)['candidate'] is not None and any(f['input']['body']['torque']))
    add('candidate held force consumed',forced,lambda f:put(r(f)['candidate'],'force',[0,0,0]))
    add('candidate held torque consumed',torqued,lambda f:put(r(f)['candidate'],'torque',[0,0,0]))
    add('candidate material changed',success,lambda f:put(r(f)['candidate']['material'],'friction',9.))
    add('candidate inertia changed',success,lambda f:put(r(f)['candidate']['inertiaDiagonal'],0,1.5))
    add('candidate quaternion invalid',success,lambda f:put(r(f)['candidate']['orientation'],3,4.))
    add('nominal allowed tube shrunk to endpoint',success,lambda f:put(r(f)['endpoint'],'nominalAllowed',copy.deepcopy(r(f)['endpoint']['nominalPosition'])))
    add('exact allowed tube shrunk to endpoint',success,lambda f:put(r(f)['endpoint'],'exactAllowed',copy.deepcopy(r(f)['endpoint']['exactPosition'])))
    discrepancy=find(lambda f:r(f)['endpoint'] is not None and any(
        reference.fraction(p)!=x for p,x in zip(reference.nominal_position(f['input']['body'],f['input']['gravity'],f['input']['horizon']),
            reference.held.path_point(reference.held_source(f['input']),reference.fraction(f['input']['horizon'])))))
    add('actual minus real endpoint discrepancy erased',discrepancy,lambda f:put(r(f)['endpoint'],'exactDifference',[[0,0]]*3))
    add('endpoint L1 upper erased',discrepancy,lambda f:put(r(f)['endpoint'],'l1ErrorBound',[0,0]))
    add('endpoint flag boolean replaced by integer',success,lambda f:put(r(f)['endpoint'],'nominalContained',1))
    add('endpoint true containment flag set false',success,lambda f:put(r(f)['endpoint'],'exactContained',False))
    add('candidate attempt flag erased',success,lambda f:put(r(f),'candidateEvaluated',False))
    add('candidate attempt flag integer alias',success,lambda f:put(r(f),'candidateEvaluated',1))
    add('original body position mutated without snapshot',success,lambda f:put(f['input']['body']['position'],0,999.))
    add('captured World body force mutated',success,lambda f:put(r(f)['worldBody']['body']['force'],0,999.))
    add('captured gravity mutated',success,lambda f:put(r(f)['worldBody']['gravity'],1,999.))
    add('original settings mutated',success,lambda f:put(r(f)['snapshot']['settings'],'maxAngularIncrement',.25))
    add('original full body field omitted',success,lambda f:r(f)['snapshot']['body'].pop('torque'))
    add('original radius replaced with inflated radius',success,lambda f:put(r(f)['snapshot']['body'],'radius',r(f)['tube']['guardRadius']))
    add('inflated held source wrongly keeps original radius',success,lambda f:put(r(f)['inflated']['snapshot']['input'],'radius',f['input']['body']['radius']))
    add('inflated source triangle dropped',success,lambda f:r(f)['inflated']['snapshot']['triangles'].pop())
    add('inflated final audit omitted',success,lambda f:r(f)['inflated']['audits'].pop())
    add('inflated partition tail omitted',success,lambda f:r(f)['inflated']['partition'].pop())
    add('inflated last mesh source corrupted',success,lambda f:put(r(f)['inflated']['lastMesh']['rows'][-1]['triangle'],'id',999))
    add('inflated entry promoted to original safe guard',inflated_failure,lambda f:(put(r(f),'status','certified_separated'),
        put(r(f),'reason','none'),put(r(f),'candidate',copy.deepcopy(fixtures[success]['result']['candidate']))))
    add('failed inflated entry still publishes candidate',inflated_failure,lambda f:put(r(f),'candidate',copy.deepcopy(fixtures[success]['result']['candidate'])))
    no_endpoint=find(lambda f:r(f)['reason']=='propagation_failure')
    add('failed rotation claims endpoint and held query executed',no_endpoint,lambda f:put(r(f),'inflated',copy.deepcopy(fixtures[success]['result']['inflated'])))
    add('preflight claims tube execution',invalid,lambda f:put(r(f),'tube',copy.deepcopy(fixtures[success]['result']['tube'])))
    add('preflight fabricates candidate attempt',invalid,lambda f:put(r(f),'candidateEvaluated',True))
    for name,mutate in [('whole fixture omitted',lambda p:p['fixtures'].pop()),
                        ('duplicate source with new label',lambda p:p['fixtures'].__setitem__(-1,copy.deepcopy(p['fixtures'][0]))),
                        ('fixed input source bits changed',lambda p:put(p['fixtures'][0]['input']['body']['velocity'],0,.125))]:
        packet=copy.deepcopy(data);mutate(packet)
        try:reference.verify(packet)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:raise AssertionError('whole guard corruption accepted: '+name)
    return records


def supplemental_controls(data):
    records=[]
    coarse=next(i for i,f in enumerate(data['fixtures']) if f['result']['status']=='not_certified')
    success=next(i for i,f in enumerate(data['fixtures']) if f['result']['status']=='certified_separated'
                 and f['input']['body']['position'][0]!=2.**39)
    def put(obj,key,value):obj[key]=value
    for name,mutate in [
        ('supplemental binade centre source bit changed',lambda p:put(p['fixtures'][success]['input']['body']['position'],0,2.**39)),
        ('supplemental accepted inflated entry promoted to safe',lambda p:put(p['fixtures'][coarse]['result'],'status','certified_separated')),
        ('supplemental coarse time tolerance silently defaulted',lambda p:put(p['fixtures'][coarse]['input']['settings']['heldLoad'],'timeTolerance',1e-7)),
        ('supplemental original radius replaced by inflated radius',lambda p:put(p['fixtures'][coarse]['input']['body'],'radius',p['fixtures'][coarse]['result']['tube']['guardRadius'])),
        ('supplemental final source dropped',lambda p:p['fixtures'].pop())]:
        packet=copy.deepcopy(data);mutate(packet)
        reference.need(json.dumps(packet,sort_keys=True)!=json.dumps(data,sort_keys=True),'supplemental control must change input/result: '+name)
        try:reference.verify_supplemental(packet)
        except (AssertionError,ValueError,KeyError,TypeError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:raise AssertionError('supplemental corruption accepted: '+name)
    return records


def main():
    reference.need(__debug__,'run free-flight reference tests without Python -O')
    parser=argparse.ArgumentParser();parser.add_argument('fixture',nargs='?');parser.add_argument('--output',type=Path);parser.add_argument('--supplemental',type=Path)
    args=parser.parse_args()
    stream=io.StringIO();run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OperationReferenceTests))
    reference.need(run.wasSuccessful(),stream.getvalue())
    report={'status':'PASS','selfTestGroups':run.testsRun}
    if args.fixture:
        data=reference.load(args.fixture);baseline=reference.verify(data);records=controls(data,baseline)
        swapped=copy.deepcopy(data);swapped['fixtures'].reverse()
        for index,f in enumerate(swapped['fixtures']):f['name']='independent-guard-'+str(index)
        reference.need(reference.verify(swapped)==baseline,'label/order independence')
        command=[sys.executable,'-O',str(SCRIPT),args.fixture]
        optimized=subprocess.run(command,capture_output=True,text=True,timeout=120)
        reference.need(optimized.returncode!=0 and 'without Python -O' in optimized.stderr,'optimized checker fails closed')
        records.append({'name':'Python -O rejected','rejected':True,'diagnostic':optimized.stderr.strip().splitlines()[-1]})
        report.update(baseline=baseline,rejectedControls=records,labelAndOrderIndependent=True)
    if args.supplemental:
        reference.need(args.fixture is not None,'supplemental controls accompany the independent fixed100 corpus')
        supplemental_data=reference.load(args.supplemental)
        supplemental=reference.verify_supplemental(supplemental_data)
        records.extend(supplemental_controls(supplemental_data))
        renamed=copy.deepcopy(supplemental_data);renamed['fixtures'].reverse()
        for index,f in enumerate(renamed['fixtures']):f['name']='independent-supplement-'+str(index)
        reference.need(reference.verify_supplemental(renamed)==supplemental,'supplemental label/order independence')
        report['supplemental']=supplemental
    if args.output:
        args.output.mkdir(parents=True,exist_ok=False)
        (args.output/'reference-self-tests.txt').write_text(stream.getvalue(),encoding='utf-8')
        (args.output/'commands.json').write_text(json.dumps({'argv':sys.argv,'python':sys.version},indent=2)+'\n',encoding='utf-8')
        (args.output/'negative-controls.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        paths=[SCRIPT,Path(__file__),ROOT/'scripts/check-sphere-triangle-mesh-held-load.py',ROOT/'scripts/verify-sphere-triangle-mesh-trajectory.py',ROOT/'scripts/verify-sphere-triangle-mesh.py',ROOT/'scripts/verify-sphere-triangle.py']
        if args.fixture:paths.append(Path(args.fixture))
        if args.supplemental:paths.append(args.supplemental)
        (args.output/'provenance.json').write_text(json.dumps([{'path':str(p.resolve()),'bytes':len(p.read_bytes()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],indent=2)+'\n',encoding='utf-8')
        if args.fixture:
            (args.output/'reference.json').write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
            (args.output/'optimized.stdout.txt').write_text(optimized.stdout,encoding='utf-8')
            (args.output/'optimized.stderr.txt').write_text(optimized.stderr,encoding='utf-8')
            (args.output/'optimized-command.json').write_text(json.dumps({'command':command,'exitCode':optimized.returncode},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'baseline','rejectedControls'}} |
        ({'fixtures':baseline['fixtures'],'rejectedControls':len(records)} if args.fixture else {})))


if __name__=='__main__': main()
