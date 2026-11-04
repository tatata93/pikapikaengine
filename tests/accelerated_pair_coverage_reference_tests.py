"""Exact polynomial self-tests and copied Native coverage negative controls."""
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
SCRIPT=ROOT/'scripts/verify-accelerated-pair-coverage.py'
spec=importlib.util.spec_from_file_location('coverage_reference',SCRIPT)
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


def sphere(center=(0,0,0),velocity=(0,0,0),acceleration=(0,0,0),radius=.25):
    return {'center':list(center),'velocity':list(velocity),'acceleration':list(acceleration),'radius':radius}


def pair_source():
    return {'input':{'kind':'sphere_pair','first':sphere(),'second':sphere((4,0,0))},
            'horizon':.0625,'settings':{'timeTolerance':1e-7,'maxEvaluations':255,'maxLeaves':128,'maxDepth':24}}


def plane_source(normal=(1,1,0),center=(1,1,0),radius=1):
    p=pair_source();p['input']={'kind':'sphere_plane','sphere':sphere(center,radius=radius),
                              'plane':{'normal':list(normal),'offset':0}}
    return p


class RationalCoverageTests(unittest.TestCase):
    def test_strict_loader_and_negative_zero(self):
        for text in ['{"x":1e999}','{"x":1e-999}','{"x":0,"x":1}','{"x":NaN}','"\\ud800"']:
            with self.assertRaises((AssertionError,ValueError,UnicodeError)):reference.loads(text)
        self.assertEqual(reference.bits(reference.loads('{"x":-0}')['x']),reference.bits(-0.))
        for value in [False,True,-0.,0.,1.]:
            with self.assertRaises(AssertionError):reference.uint(value,255,'metadata')

    def test_quadratic_extrema_include_stationary_and_closed_ends(self):
        self.assertEqual(reference.quadratic_range([1,-4,4],F(0),F(1)),(0,1))
        self.assertEqual(reference.quadratic_range([1,-4,4],F(0),F(1,4)),(F(1,4),1))
        self.assertEqual(reference.quadratic_range([0,0,-1],F(-1),F(1)),(-1,0))

    def test_bernstein_transform_and_half_partition_exact_identity(self):
        p=[F(3,7),-2,F(5,3),F(1,9),F(2,11)]
        b=reference.bernstein(p,F(-1,3),F(7,8));left,right=reference.bisect_bernstein(b)
        self.assertEqual(b[0],reference.evaluate(p,F(-1,3)))
        self.assertEqual(b[-1],reference.evaluate(p,F(7,8)))
        self.assertEqual(left[-1],right[0]);self.assertEqual(left[0],b[0]);self.assertEqual(right[-1],b[-1])
        midpoint=(F(-1,3)+F(7,8))/2
        self.assertEqual(left[-1],reference.evaluate(p,midpoint))
        for u in [F(0),F(1,3),F(1)]:
            # This finite identity cross-check tests exact coefficient algebra;
            # the proof itself uses nonnegative basis/partition unity, not samples.
            n=len(b)-1
            value=sum((b[i]*reference.comb(n,i)*u**i*(1-u)**(n-i) for i in range(n+1)),F(0))
            self.assertEqual(value,reference.evaluate(p,F(-1,3)+(F(7,8)+F(1,3))*u))

    def test_irrational_double_roots_are_removed_without_epsilon(self):
        p=[4,0,-4,0,1] # (t^2-2)^2, exact zeros at +/-sqrt(2).
        residual,removed=reference.odd_part(p)
        self.assertEqual(residual,[1]);self.assertEqual(removed,2)
        reference.nonnegative(p,F(0),F(2))
        with self.assertRaises(AssertionError):reference.nonnegative([-c for c in p],F(0),F(2))

    def test_multiplicity_and_leading_sign_preserved(self):
        self.assertEqual(reference.odd_part([0,0,0,0,7])[0],[7])
        reference.nonnegative([0,0,0,0,7],F(-2),F(3))
        with self.assertRaises(AssertionError):reference.nonnegative([0,0,0,0,-7],F(-2),F(3))
        # t^3(t-1) has odd-root residual t(t-1), negative on (0,1).
        with self.assertRaises(AssertionError):reference.nonnegative([0,0,0,-1,1],F(0),F(1))

    def test_endpoint_factors_zero_polynomial_and_single_point(self):
        reference.nonnegative([0],F(-7),F(11))
        reference.nonnegative([0,1,-1,1,-1],F(0),F(1)) # t(1-t)(1+t^2).
        reference.nonnegative([0,0,0,0,-1],F(0),F(0))

    def test_positive_quartic_and_irrational_stationary_are_certified(self):
        reference.nonnegative([2,-2,0,0,1],F(0),F(1)) # minimum at cuberoot(1/2).
        # The endpoints of t^4-2t+1 are nonnegative but an interior value is negative.
        with self.assertRaises(AssertionError):reference.nonnegative([1,-2,0,0,1],F(0),F(1))

    def test_finite_proof_budget_unresolved_is_not_success(self):
        p=reference.multiply([F(1,4),-1,1],[F(1,4),-1,1]);p[0]+=F(1,10000)
        self.assertLess(min(reference.bernstein(p,F(0),F(1))),0)
        saved=reference.MAX_PROOF_DEPTH
        try:
            reference.MAX_PROOF_DEPTH=0
            with self.assertRaisesRegex(AssertionError,'unresolved'):reference.nonnegative(p,F(0),F(1))
        finally:reference.MAX_PROOF_DEPTH=saved
        reference.nonnegative(p,F(0),F(1))

    def test_plane_irrational_support_sign_before_squaring(self):
        s=plane_source();cell={'timeBounds':[0,.0625]}
        reference.verify_range(s,cell,[.5,.75],reference.new_stats()) # 2-sqrt(2).
        with self.assertRaises(AssertionError):reference.verify_range(s,cell,[.75,1],reference.new_stats())
        s['input']['sphere']['center']=[-1,-2,0] # q=-3, value=-3-sqrt(2).
        reference.verify_range(s,cell,[-5,0],reference.new_stats())
        with self.assertRaises(AssertionError):reference.verify_range(s,cell,[0,4],reference.new_stats())

    def test_tiny_normal_has_nonzero_exact_norm(self):
        d=reference.next_up(0.)
        s=plane_source((d,d,0),(4,4,0),.25);cell={'timeBounds':[0,.0625]}
        reference.verify_range(s,cell,[6*d,9*d],reference.new_stats())
        with self.assertRaises(AssertionError):reference.verify_range(s,cell,[8*d,9*d],reference.new_stats())
        self.assertEqual(reference.preflight(s),(None,None))

    def test_pair_uses_exact_relative_input_difference_and_radius_sum(self):
        s=pair_source();s['input']['first']['center'][0]=1e12
        s['input']['second']['center'][0]=reference.next_up(0.)
        p=reference.sphere_polynomial(s)
        expected=(F(1e12)-F(reference.next_up(0.)))**2-F(1,4)
        self.assertEqual(p,[expected])
        self.assertNotEqual(p[0],F(1e24)-F(1,4))

    def test_width_metadata_zero_shortcut_outward_successor_and_subnormal(self):
        d=reference.next_up(0.)
        self.assertEqual(reference.width_upper({'timeBounds':[0,d]}),F(d))
        self.assertEqual(reference.width_upper({'timeBounds':[d,2*d]}),F(2*d))
        self.assertEqual(reference.next_up(-0.),d)
        self.assertEqual(reference.rn_positive(F(1)+F(1,2**53)),1.)
        self.assertEqual(reference.rn_positive(F(1)+F(3,2**53)),reference.next_up(reference.next_up(1.)))

    def test_settings_then_horizon_then_source_validation(self):
        s=plane_source((0,-0.,0));s['horizon']=-0.;s['settings']['maxEvaluations']=0
        self.assertEqual(reference.preflight(s),('settings',None))
        s['settings']['maxEvaluations']=255;self.assertEqual(reference.preflight(s),('horizon',None))
        s['horizon']=.0625;self.assertEqual(reference.preflight(s),('zero_normal',1))

    def test_input_fingerprint_types_order_and_labels(self):
        a=pair_source();b=plane_source();rows=[{'name':'a','input':a},{'name':'b','input':b}]
        swapped=[{'name':'x','input':b},{'name':'y','input':a}]
        self.assertEqual(reference.input_fingerprint(rows),reference.input_fingerprint(swapped))
        swapped=copy.deepcopy(swapped);swapped[1]['input']['input']['first']['center'][0]=-0.
        self.assertNotEqual(reference.input_fingerprint(rows),reference.input_fingerprint(swapped))


def controls(data):
    fixtures=data['fixtures'];records=[]
    find=lambda predicate:next(i for i,f in enumerate(fixtures) if predicate(f))
    maximum=find(lambda f:len(f['result']['audits'])==255 and f['input']['input']['kind']=='sphere_pair')
    budget=find(lambda f:len(f['result']['frontier'])==127)
    invalid=find(lambda f:f['result']['status']=='invalid_input' and f['result']['failedInput']==1)
    positive=find(lambda f:f['result']['status']=='certified' and f['input']['input']['kind']=='sphere_pair')
    plane=find(lambda f:f['result']['status']=='certified' and f['input']['input']['kind']=='sphere_plane')
    subdivided=find(lambda f:f['result']['status']=='certified' and len(f['result']['audits'])>1)
    negative=find(lambda f:f['result']['audits'] and f['result']['audits'][0]['value'][1]<0)
    pair_cross=find(lambda f:f['name']=='sphere-high-speed-interior-crossing')
    quartic=find(lambda f:f['name']=='sphere-quartic-nonrational-stationary')
    plane_cross=find(lambda f:f['name']=='plane-interior-crossing-safe-endpoints')
    irrational=find(lambda f:f['name']=='plane-irrational-normal')
    tiny=find(lambda f:f['name']=='plane-tiny-axis-normal-preserved')
    put=lambda o,k,v:o.__setitem__(k,v)
    r=lambda f:f['result']
    def add(name,index,mutate):
        fixture=copy.deepcopy(fixtures[index]);before=copy.deepcopy(fixture);mutate(fixture)
        # Mutation bookkeeping must distinguish integer metadata from 24.0;
        # source_equal deliberately compares numeric source values by F64 bits.
        if json.dumps(before,sort_keys=True)==json.dumps(fixture,sort_keys=True):
            raise AssertionError('control unchanged: '+name)
        try:reference.verify_fixture(fixture['input'],fixture['result'],reference.new_stats())
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:raise AssertionError('coverage corruption accepted: '+name)
    add('sphere endpoint-only interval misses interior crossing',pair_cross,lambda f:put(r(f)['audits'][0],'value',[15,16]))
    add('quartic endpoint-only interval excludes irrational stationary minimum',quartic,lambda f:put(r(f)['audits'][0],'value',[1.5,2.5]))
    add('plane endpoint-only interval misses quadratic interior minimum',plane_cross,lambda f:put(r(f)['audits'][0],'value',[.5,1]))
    add('pair uses sum of radius squares instead of squared radius sum',positive,lambda f:put(r(f)['audits'][0],'value',[15.8,15.9]))
    add('irrational normal silently treated as unit',irrational,lambda f:put(r(f)['audits'][0],'value',[3.7,3.8]))
    add('tiny nonzero plane normal rounded to zero support',tiny,lambda f:put(r(f)['audits'][0],'value',[4*reference.next_up(0.)]*2))
    add('returned interval tail endpoint omitted',positive,lambda f:r(f)['audits'][0]['value'].pop())
    add('returned interval reversed',positive,lambda f:r(f)['audits'][0]['value'].reverse())
    add('returned interval numeric boolean alias',positive,lambda f:put(r(f)['audits'][0]['value'],0,False))
    add('returned public value silently removed',positive,lambda f:put(r(f)['audits'][0],'value',None))
    add('positive outcome fabricated from negative value',negative,lambda f:put(r(f)['audits'][0],'outcome','positive'))
    add('final pending outcome fabricated',positive,lambda f:put(r(f)['audits'][0],'outcome','pending'))
    add('call attempt erased for a returned value',positive,lambda f:put(r(f)['audits'][0],'callAttempted',False))
    add('call attempt numeric alias',positive,lambda f:put(r(f)['audits'][0],'callAttempted',1))
    add('audit tail omitted',maximum,lambda f:r(f)['audits'].pop())
    add('audit BFS order reversed',subdivided,lambda f:r(f)['audits'].reverse())
    add('child parent audit erased',subdivided,lambda f:put(r(f)['audits'][1]['cell'],'parentAudit',None))
    add('parent ordinal boolean alias',subdivided,lambda f:put(r(f)['audits'][1]['cell'],'parentAudit',False))
    add('metadata depth negative zero alias',positive,lambda f:put(r(f)['audits'][0]['cell'],'depth',-0.))
    add('global seconds changed into normalized parameter',positive,lambda f:put(r(f)['audits'][0]['cell']['timeBounds'],1,1.))
    add('root pluszero metadata sign changed',positive,lambda f:put(r(f)['audits'][0]['cell']['timeBounds'],0,-0.))
    add('split boundary changed without matching children',subdivided,lambda f:put(r(f)['audits'][0],'splitTime',f['input']['horizon']/3))
    add('partition final leaf omitted',maximum,lambda f:r(f)['partition'].pop())
    add('partition duplicated first cell instead of tail',maximum,lambda f:put(r(f)['partition'],-1,copy.deepcopy(r(f)['partition'][0])))
    add('partition reordered',maximum,lambda f:r(f)['partition'].reverse())
    add('partition audit link changed',subdivided,lambda f:put(r(f)['partition'][0],'auditIndex',0))
    add('partition state promoted to certified',maximum,lambda f:put(r(f)['partition'][-1],'state','certified'))
    add('whole partition completeness false',positive,lambda f:put(r(f),'partitionComplete',False))
    add('current unknown cell dropped',budget,lambda f:put(r(f),'current',None))
    add('frontier unknown tail dropped',budget,lambda f:r(f)['frontier'].pop())
    add('frontier current wrongly included',budget,lambda f:r(f)['frontier'].insert(0,copy.deepcopy(r(f)['current'])))
    add('frontier order reversed',budget,lambda f:r(f)['frontier'].reverse())
    for key in sorted(reference.WORK_KEYS):
        index=plane if key.startswith('plane') else positive
        add('work '+key+' falsified',index,lambda f,k=key:put(r(f)['work'],k,r(f)['work'][k]+1))
    add('private plane loop upper misreported as actual zero',plane,lambda f:put(r(f)['work'],'planeNormLoopIterationsUpper',0))
    add('work count boolean alias',positive,lambda f:put(r(f)['work'],'valueCallsReturned',True))
    add('captured invalid input falsely validated',invalid,lambda f:put(r(f),'snapshotValidated',True))
    add('failed input boolean alias',invalid,lambda f:put(r(f),'failedInput',True))
    add('captured original omitted',positive,lambda f:put(r(f),'snapshot',None))
    add('captured original radius changed',positive,lambda f:put(r(f)['snapshot']['input']['first'],'radius',.5))
    add('captured original horizon converted to1',positive,lambda f:put(r(f)['snapshot'],'horizon',1.))
    add('source settings dropped',positive,lambda f:r(f)['snapshot'].pop('settings'))
    add('snapshot profile integer converted to float',positive,lambda f:put(r(f)['snapshot']['settings'],'maxDepth',24.))
    def erase_zero(f):
        value=r(f)['snapshot']['input']['first']['center']
        for i,x in enumerate(value):
            if reference.bits(x)==reference.bits(-0.):value[i]=0.;return
        raise AssertionError('actual source negative zero absent')
    add('source negative zero erased',positive,erase_zero)
    add('not-certified coverage promoted to entry window',maximum,lambda f:put(r(f),'status','entry_window'))
    add('coverage fabricates a World candidate',positive,lambda f:put(r(f),'candidate',{}))
    add('wrong first unresolved/global terminal reason',budget,lambda f:put(r(f),'reason','width_limit'))
    for name,mutate in [('whole fixture dropped',lambda p:p['fixtures'].pop()),
                        ('whole input duplicated with a different label',lambda p:put(p['fixtures'],-1,dict(copy.deepcopy(p['fixtures'][0]),name='different-label'))),
                        ('input field bit changed',lambda p:put(p['fixtures'][0]['input']['input']['first']['center'],0,.125))]:
        p=copy.deepcopy(data);mutate(p)
        try:reference.verify(p)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:raise AssertionError('whole-corpus corruption accepted: '+name)
    # Positive control: widening [~15.75,~15.75] to [15,16] is mathematically
    # valid and leaves the positive root/metadata unchanged. It is NOT claimed
    # to be the actual public function's exact interval; Native bit replay owns
    # that independent provenance question.
    widened=copy.deepcopy(fixtures[positive]);widened['result']['audits'][0]['value']=[15,16]
    reference.verify_fixture(widened['input'],widened['result'],reference.new_stats())
    # Also exercise a coherent artificial nonreturn record, without calling it
    # a natural Native value exception or an executed fault-injection experiment.
    nonreturn=copy.deepcopy(fixtures[positive]);result=nonreturn['result'];a=result['audits'][0]
    a.update(value=None,outcome='blocked',blockedReason='value_exception',splitTime=None)
    result.update(status='not_certified',reason='value_exception',current=copy.deepcopy(a['cell']))
    result['partition'][0].update(state='current',blockedReason='value_exception')
    result['work']['valueCallsReturned']=0
    reference.verify_fixture(nonreturn['input'],result,reference.new_stats())
    return records,{'mathematicallyValidWiderIntervalAccepted':True,'syntheticNonreturnedAttemptAccepted':True,
                    'scope':'Wider I is a mathematical positive control, not actual-public-value provenance. Nonreturn is copied artificial metadata, not a natural Native exception or actual fault injection.'}


def main():
    reference.need(__debug__,'run coverage reference tests without Python -O')
    parser=argparse.ArgumentParser();parser.add_argument('fixture',nargs='?');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output:args.output.mkdir(parents=True,exist_ok=False)
    stream=io.StringIO();run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RationalCoverageTests))
    if args.output:(args.output/'reference-self-tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    reference.need(run.wasSuccessful(),stream.getvalue())
    report={'status':'PASS','selfTestGroups':run.testsRun}
    if args.fixture:
        data=reference.load(args.fixture);baseline=reference.verify(data);records,positive_controls=controls(data)
        swapped=copy.deepcopy(data);swapped['fixtures'].reverse()
        for i,f in enumerate(swapped['fixtures']):f['name']='independent-coverage-'+str(i)
        reference.need(reference.verify(swapped)==baseline,'label/order-independent mathematical and metadata acceptance')
        command=[sys.executable,'-O',str(SCRIPT),args.fixture]
        optimized=subprocess.run(command,capture_output=True,text=True,timeout=120)
        reference.need(optimized.returncode!=0 and 'without Python -O' in optimized.stderr,'Python -O rejection')
        records.append({'name':'Python -O rejected','rejected':True,'diagnostic':optimized.stderr.strip().splitlines()[-1]})
        report.update(fixtures=baseline['fixtures'],baseline=baseline,rejectedControls=records,
                      labelAndOrderIndependent=True,positiveControls=positive_controls)
    if args.output:
        (args.output/'commands.json').write_text(json.dumps({'argv':sys.argv,'python':sys.version},indent=2)+'\n',encoding='utf-8')
        (args.output/'negative-controls.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        paths=[SCRIPT,Path(__file__)]+([Path(args.fixture)] if args.fixture else [])
        (args.output/'provenance.json').write_text(json.dumps([{'path':str(p.resolve()),'bytes':len(p.read_bytes()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],indent=2)+'\n',encoding='utf-8')
        if args.fixture:
            (args.output/'reference.json').write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
            (args.output/'optimized.stdout.txt').write_text(optimized.stdout,encoding='utf-8')
            (args.output/'optimized.stderr.txt').write_text(optimized.stderr,encoding='utf-8')
            (args.output/'optimized-command.json').write_text(json.dumps({'command':command,'exitCode':optimized.returncode},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'baseline','rejectedControls','positiveControls'}} |
                     ({'rejectedControls':len(records),'positiveControls':positive_controls} if args.fixture else {})))


if __name__=='__main__':main()
