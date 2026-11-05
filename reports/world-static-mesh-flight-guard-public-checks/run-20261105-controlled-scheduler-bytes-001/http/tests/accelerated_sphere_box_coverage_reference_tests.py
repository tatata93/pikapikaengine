"""Independent exact sphere-box self proofs and copied-packet negative controls.

Artificial packets exercise the verifier only; they are not Native fault injection.
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

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/verify-accelerated-sphere-box-coverage.py'
spec=importlib.util.spec_from_file_location('sphere_box_reference',SCRIPT)
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


def source():
    sphere=lambda x:{'center':[x,0,0],'velocity':[0,0,0],'acceleration':[0,0,0],'radius':.5}
    return {'input':{'first':sphere(0),'second':sphere(4),'firstPositionError':0.,'secondPositionError':0.,'contactMargin':0.},
            'horizon':.0625,'settings':{'timeTolerance':1e-7,'maxEvaluations':255,'maxLeaves':128,'maxDepth':24,'sqrtRefinements':128}}


def simple_fixture():
    s=source();cell={'timeBounds':[0.,s['horizon']],'depth':0,'parentAudit':None}
    e={'firstCoordinates':[[0,0],[0,0],[0,0]],'secondCoordinates':[[4,4],[0,0],[0,0]],
       'delta':[[4,4],[0,0],[0,0]],'rawSquaredDistance':[16,16],'nonnegativeSquaredDistance':[16,16],
       'root':{'value':[4,4],'refinements':0,'refinementLimited':False},'distance':[4,4],'threshold':[1,1],'gap':[3,3]}
    result={'status':'certified','reason':'none','snapshot':copy.deepcopy(s),'snapshotValidated':True,'failedInput':None,
            'partitionComplete':True,'audits':[{'cell':copy.deepcopy(cell),'callAttempted':True,'evaluation':e,
              'outcome':'positive','blockedReason':'none','splitTime':None}],
            'partition':[{'cell':copy.deepcopy(cell),'state':'certified','auditIndex':0,'blockedReason':'none'}],
            'frontier':[],'current':None,'work':dict(reference.empty_work(),valueCallsAttempted=1,valueCallsReturned=1,sqrtResultsReturned=1)}
    return {'name':'artificial-static-reference','input':s,'result':result}


def assert_fixture(f):
    reference.verify_fixture(f['input'],f['result'],reference.new_stats())


def artificial_nonreturn(f):
    r=f['result'];a=r['audits'][0]
    a.update(evaluation=None,outcome='blocked',blockedReason='value_exception',splitTime=None)
    r.update(status='not_certified',reason='value_exception',current=copy.deepcopy(a['cell']))
    r['partition'][0].update(state='current',blockedReason='value_exception')
    r['work']=dict(reference.empty_work(),valueCallsAttempted=1,sqrtRefinementsUpper=2*f['input']['settings']['sqrtRefinements'],exact=False)


class SphereBoxTests(unittest.TestCase):
    def test_strict_loader_and_metadata(self):
        for text in ['{"x":1e999}','{"x":1e-999}','{"x":0,"x":1}','{"x":NaN}','"\\ud800"']:
            with self.assertRaises((AssertionError,ValueError,UnicodeError)):reference.loads(text)
        self.assertEqual(reference.bits(reference.loads('{"x":-0}')['x']),reference.bits(-0.))
        for value in [False,True,-0.,0.,1.]:
            with self.assertRaises(AssertionError):reference.uint(value,255,'metadata')

    def test_integer_RN_normal_subnormal_ties(self):
        d=F(1,2**1074)
        for value,expected in [(1+F(1,2**53),1),(1+F(3,2**53),1+F(1,2**51)),
                               (d/2,0),(3*d/2,2*d),(-d/2,0),(F(1,2**1022)-d/2,F(1,2**1022))]:
            self.assertEqual(reference.integer_rn(value),expected)
        with self.assertRaises(AssertionError):reference.integer_rn(F(2**1024))

    def test_exact_quadratic_internal_extremum(self):
        self.assertEqual(reference.quadratic_range([1,-4,4],0,1),(0,1))
        self.assertEqual(reference.quadratic_range([0,0,-1],-1,1),(-1,0))
        d=F(1,2**1074)
        self.assertEqual(reference.quadratic_range([0,0,d/2],0,F(1,16)),(0,d/512))

    def test_analytic_margin_is_not_metric_gap(self):
        distance=F(17,32);r=F(1,4)
        self.assertGreater(distance-2*r,0)
        threshold=reference.threshold_choices(r,r,F(1,16))
        self.assertEqual(threshold,{F(9,16)})
        self.assertLess(distance-min(threshold),0)

    def test_analytic_rounded_delta_can_remove_separation(self):
        e=F(1,2**53)
        values=reference.node_choices('sub',{F(1)},{-e})
        self.assertEqual(values,{F(1),1+e})
        self.assertGreater((1+e)**2,1)

    def test_analytic_rounded_dot_can_remove_separation(self):
        e=F(1,2**27)
        q=reference.extrema_choices('add',(1,1),reference.square_range((e,e)))
        self.assertEqual(q,(1,1+e*e))
        self.assertEqual(reference.integer_rn(1+e*e),1)

    def test_analytic_sqrt_rounding_is_distinct_from_dot(self):
        e=F(1,2**26);q=1+e*e;midpoint=1+F(1,2**53)
        self.assertEqual(reference.integer_rn(q),q)
        self.assertGreater(q,1);self.assertLess(q,midpoint*midpoint)
        # sqrt(q) lies strictly between 1 and its nearest-even midpoint.
        # Thus correct RN sqrt is 1, without evaluating a floating sqrt.
        upper=1+F(1,2**52)
        self.assertGreaterEqual(upper*upper,q)

    def test_analytic_threshold_association_changes_RN(self):
        e=F(1,2**53)
        left=reference.integer_rn(reference.integer_rn(1+e)+e)
        right=reference.integer_rn(1+reference.integer_rn(e+e))
        self.assertEqual(left,1);self.assertEqual(right,1+2*e)
        self.assertIn(1+2*e,reference.threshold_choices(1,e,e))

    def test_square_box_crossing_zero_includes_interior_minimum(self):
        self.assertEqual(reference.square_range((F(-2),F(3))),(0,9))
        self.assertEqual(reference.square_range((F(-3),F(-2))),(4,9))
        d=F(1,2**1074)
        self.assertEqual(reference.square_range((d,d)),(0,d*d))

    def test_left_associated_Q_and_exact_FMA_nodes(self):
        e=F(1,2**27)
        product=reference.node_choices('mul',{1+e},{1-e})
        self.assertEqual(product,{1,1-e*e})
        self.assertIn(-e*e,reference.node_choices('sub',product,{F(1)}))

    def test_complete_synthetic_success_and_limited_valid_root(self):
        f=simple_fixture();assert_fixture(f)
        e=f['result']['audits'][0]['evaluation']
        e.update(root={'value':[3,6],'refinements':2,'refinementLimited':True},distance=[3,6],gap=[2,5])
        f['result']['work'].update(sqrtLimitedReturns=1,sqrtRefinementsReturned=2,sqrtRefinementsUpper=2)
        assert_fixture(f) # limited is not failure when full enclosure and gap>0.

    def test_root_enclosure_and_distance_bits_mandatory(self):
        for mutate in [lambda e:e['root'].__setitem__('value',[4.1,4.1]),
                       lambda e:e.__setitem__('distance',[4,5]),
                       lambda e:e.__setitem__('nonnegativeSquaredDistance',[0,16]),
                       lambda e:e['root'].__setitem__('refinements',True)]:
            f=simple_fixture();mutate(f['result']['audits'][0]['evaluation'])
            with self.assertRaises(AssertionError):assert_fixture(f)

    def test_nonreturn_unknown_root_reservation(self):
        wide=simple_fixture();we=wide['result']['audits'][0]['evaluation'];we.update(root={'value':[4,5],'refinements':0,'refinementLimited':False},distance=[4,5],gap=[3,4]);assert_fixture(wide)
        f=simple_fixture();artificial_nonreturn(f);assert_fixture(f)
        for key,value in [('sqrtRefinementsUpper',0),('exact',True),('sqrtResultsReturned',1)]:
            bad=copy.deepcopy(f);bad['result']['work'][key]=value
            with self.assertRaises(AssertionError):assert_fixture(bad)

    def test_validation_priority_and_both_B_source_signs(self):
        s=source();s['settings']['sqrtRefinements']=0;s['horizon']=-0.;s['input']['first']['radius']=0
        self.assertEqual(reference.preflight(s),('settings',None));s['settings']['sqrtRefinements']=128
        self.assertEqual(reference.preflight(s),('horizon',None));s['horizon']=.0625
        self.assertEqual(reference.preflight(s),('input_domain',0));s['input']['first']['radius']=1
        s['input']['secondPositionError']=-1
        self.assertEqual(reference.preflight(s),('position_error',3));s['input']['firstPositionError']=-1
        self.assertEqual(reference.preflight(s),('position_error',2));s['input']['firstPositionError']=-0.
        s['input']['secondPositionError']=-0.;s['input']['contactMargin']=-1
        self.assertEqual(reference.preflight(s),('contact_margin',4))
        t=copy.deepcopy(s);t['input']['firstPositionError']=0.
        with self.assertRaises(AssertionError):reference.source_equal(s,t)

    def test_width_successor_and_whole_input_fingerprint(self):
        d=reference.next_up(0.);self.assertEqual(reference.next_up(-0.),d)
        self.assertEqual(reference.width_upper({'timeBounds':[d,2*d]}),F(2*d))
        a=source();b=copy.deepcopy(a);b['input']['second']['center'][0]=5
        rows=[{'input':a},{'input':b}]
        self.assertEqual(reference.input_fingerprint(rows),reference.input_fingerprint(rows[::-1]))
        b['settings']['maxDepth']=24.
        self.assertNotEqual(reference.input_fingerprint([{'input':a}]),reference.input_fingerprint([{'input':dict(a,settings=dict(a['settings'],maxDepth=24.))}]))

    def test_bounded_AST_fail_closed(self):
        saved=reference.MAX_AST_CHOICES
        try:
            reference.MAX_AST_CHOICES=1
            with self.assertRaisesRegex(AssertionError,'budget'):reference.node_choices('mul',{1+F(1,2**27)},{1-F(1,2**27)})
        finally:reference.MAX_AST_CHOICES=saved


def controls(data):
    fixtures=data['fixtures'];records=[]
    find=lambda p:next(i for i,f in enumerate(fixtures) if p(f))
    positive=find(lambda f:f['result']['status']=='certified' and len(f['result']['audits'])==1)
    maximum=find(lambda f:len(f['result']['audits'])==255)
    frontier=find(lambda f:len(f['result']['frontier'])==127)
    divided=find(lambda f:f['result']['status']=='certified' and len(f['result']['audits'])>1)
    invalid=find(lambda f:f['result']['failedInput'] is not None)
    put=lambda o,k,v:o.__setitem__(k,v)
    r=lambda f:f['result'];e=lambda f:r(f)['audits'][0]['evaluation']
    def add(name,index,mutate):
        f=copy.deepcopy(fixtures[index]);before=json.dumps(f,sort_keys=True);mutate(f)
        reference.need(before!=json.dumps(f,sort_keys=True),'control changed '+name)
        try:assert_fixture(f)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as failure:
            records.append({'name':name,'rejected':True,'diagnostic':str(failure)})
        else:raise AssertionError('sphere-box corruption accepted: '+name)
    for key in ['firstCoordinates','secondCoordinates','delta']:
        for axis in range(3):
            add(key+' axis '+str(axis)+' corrupted',positive,lambda f,k=key,a=axis:put(e(f)[k],a,[1e30,1e30]))
        add(key+' axis omitted',positive,lambda f,k=key:e(f)[k].pop())
    for key in ['rawSquaredDistance','nonnegativeSquaredDistance','distance','threshold','gap']:
        add(key+' replaced',positive,lambda f,k=key:put(e(f),k,[1e30,1e30]))
        add(key+' endpoint omitted',positive,lambda f,k=key:e(f)[k].pop())
        add(key+' bool endpoint',positive,lambda f,k=key:put(e(f)[k],0,False))
    named=lambda name:find(lambda f:f['name']==name)
    add('explicit margin omitted from threshold',named('margin-contact-counterexample'),lambda f:put(e(f),'threshold',[.5,.5]))
    add('rounded-only delta erases exact subtraction',named('subtraction-rounds-away-real-gap'),lambda f:put(e(f)['delta'],0,[1,1]))
    add('rounded-only dot erases exact square sum',named('dot-rounds-away-real-gap'),lambda f:put(e(f),'rawSquaredDistance',[1,1]))
    def false_root(f):
        e(f)['root']['value']=[1,1];e(f)['distance']=[1,1]
    add('rounded-only sqrt erases full exact root inclusion',named('sqrt-rounds-away-real-gap'),false_root)
    add('rounded-only threshold erases original fixed AST choices',named('left-associated-threshold-counterexample'),lambda f:put(e(f),'threshold',[1,1]))
    add('subnormal unrounded half acceleration omitted',named('subnormal-half-acceleration-preserved'),lambda f:put(e(f)['firstCoordinates'],1,[0,0]))
    add('interior quadratic extremum omitted',named('safe-parabolic-subdivision'),lambda f:put(e(f)['secondCoordinates'],1,[1.625,1.875]))
    for key,name in [('firstCoordinates','first-b-omission-would-certify'),('secondCoordinates','second-b-omission-would-certify')]:
        add('declared '+key+' B omitted',named(name),lambda f,k=key:put(e(f)[k],0,[0,0]))
    crossing=named('maximum-first-b')
    def corners_only(f):
        # Forgery intentionally computes only endpoint square minima; the
        # reference must retain the zero attained inside a delta interval.
        box=[reference.interval(v) for v in e(f)['delta']]
        minimum=sum(min(a*a,b*b) for a,b in box)
        reference.need(minimum>0,'counterexample has strict endpoint-only lower')
        e(f)['rawSquaredDistance'][0]=float(reference.integer_rn(minimum))
    add('corners-only squares omit zero crossing minimum',crossing,corners_only)
    add('clamp upper silently changed to zero',positive,lambda f:put(e(f)['nonnegativeSquaredDistance'],1,0))
    add('root square lower too high',positive,lambda f:put(e(f)['root'],'value',[1e30,1e30]))
    add('root lower negative',positive,lambda f:put(e(f)['root']['value'],0,-1))
    add('root returned ref overflow',positive,lambda f:put(e(f)['root'],'refinements',513))
    add('root ref bool alias',positive,lambda f:put(e(f)['root'],'refinements',False))
    add('root limited numeric alias',positive,lambda f:put(e(f)['root'],'refinementLimited',0))
    add('root field omitted',positive,lambda f:e(f)['root'].pop('refinementLimited'))
    for key in ['valueCallsAttempted','valueCallsReturned','sqrtResultsReturned','sqrtRefinementsReturned','sqrtLimitedReturns','sqrtRefinementsUpper']:
        add(key+' inconsistent',positive,lambda f,k=key:put(r(f)['work'],k,r(f)['work'][k]+1))
    add('root exact numeric alias',positive,lambda f:put(r(f)['work'],'exact',1))
    add('root exact false without unknown call',positive,lambda f:put(r(f)['work'],'exact',False))
    add('returned record erased',positive,lambda f:put(r(f)['audits'][0],'evaluation',None))
    add('whole record field omitted',positive,lambda f:e(f).pop('threshold'))
    add('audit attempt erased',positive,lambda f:put(r(f)['audits'][0],'callAttempted',False))
    add('audit pending retained',positive,lambda f:put(r(f)['audits'][0],'outcome','pending'))
    add('last audit omitted',maximum,lambda f:r(f)['audits'].pop())
    add('BFS order reversed',divided,lambda f:r(f)['audits'].reverse())
    add('split endpoint differs from children',divided,lambda f:put(r(f)['audits'][0],'splitTime',0.))
    add('parent link omitted',divided,lambda f:put(r(f)['audits'][1]['cell'],'parentAudit',None))
    add('parent link bool alias',divided,lambda f:put(r(f)['audits'][1]['cell'],'parentAudit',False))
    add('depth negativezero alias',positive,lambda f:put(r(f)['audits'][0]['cell'],'depth',-0.))
    add('root metadata zero sign erased',positive,lambda f:put(r(f)['audits'][0]['cell']['timeBounds'],0,-0.))
    add('seconds normalized into parameter',positive,lambda f:put(r(f)['audits'][0]['cell']['timeBounds'],1,1.))
    add('partition tail omitted',maximum,lambda f:r(f)['partition'].pop())
    add('partition order reversed',maximum,lambda f:r(f)['partition'].reverse())
    add('partition falsely certified',maximum,lambda f:put(next(l for l in r(f)['partition'] if l['state']!='certified'),'state','certified'))
    add('frontier tail omitted',frontier,lambda f:r(f)['frontier'].pop())
    add('frontier current duplicated',frontier,lambda f:r(f)['frontier'].append(copy.deepcopy(r(f)['current'])))
    add('halt reason skips evaluation budget',frontier,lambda f:put(r(f),'reason','width_limit'))
    add('current erased',frontier,lambda f:put(r(f),'current',None))
    add('partition complete erased',positive,lambda f:put(r(f),'partitionComplete',False))
    add('snapshot absent',positive,lambda f:put(r(f),'snapshot',None))
    add('snapshot firstB changed',positive,lambda f:put(r(f)['snapshot']['input'],'firstPositionError',1e12))
    add('snapshot secondB changed',positive,lambda f:put(r(f)['snapshot']['input'],'secondPositionError',1e12))
    add('snapshot margin changed',positive,lambda f:put(r(f)['snapshot']['input'],'contactMargin',.1))
    add('snapshot integer setting float alias',positive,lambda f:put(r(f)['snapshot']['settings'],'sqrtRefinements',float(f['input']['settings']['sqrtRefinements'])))
    add('failed ordinal bool alias',invalid,lambda f:put(r(f),'failedInput',False))
    add('invalid source falsely validated',invalid,lambda f:put(r(f),'snapshotValidated',True))
    add('fabricated World candidate',positive,lambda f:put(r(f),'candidate',{}))
    add('coverage promoted to entry window',maximum,lambda f:put(r(f),'status','entry_window'))
    def zero_path(value,path=()):
        if type(value) is float and reference.bits(value)==reference.bits(-0.):return path
        if type(value) in (dict,list):
            for k,v in (value.items() if type(value) is dict else enumerate(value)):
                found=zero_path(v,path+(k,))
                if found is not None:return found
        return None
    zero=find(lambda f:zero_path(r(f)['snapshot']) is not None)
    def erase_zero(f):
        path=zero_path(r(f)['snapshot']);o=r(f)['snapshot']
        for key in path[:-1]:o=o[key]
        o[path[-1]]=0.
    add('original negative zero erased',zero,erase_zero)
    for name,mutate in [('fixture omitted',lambda p:p['fixtures'].pop()),
                        ('duplicate input under different label',lambda p:put(p['fixtures'],-1,dict(copy.deepcopy(p['fixtures'][0]),name='newlabel'))),
                        ('source firstB bits changed',lambda p:put(p['fixtures'][0]['input']['input'],'firstPositionError',.125))]:
        packet=copy.deepcopy(data);mutate(packet)
        try:reference.verify(packet)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as failure:
            records.append({'name':name,'rejected':True,'diagnostic':str(failure)})
        else:raise AssertionError('whole sphere corpus corruption accepted: '+name)
    wide=simple_fixture();we=wide['result']['audits'][0]['evaluation'];we.update(root={'value':[4,5],'refinements':0,'refinementLimited':False},distance=[4,5],gap=[3,4]);assert_fixture(wide)
    f=simple_fixture();artificial_nonreturn(f);assert_fixture(f)
    for key,value in [('sqrtRefinementsUpper',0),('exact',True),('sqrtResultsReturned',1)]:
        bad=copy.deepcopy(f);bad['result']['work'][key]=value
        try:assert_fixture(bad)
        except AssertionError as failure:records.append({'name':'artificial nonreturn '+key+' corrupt','rejected':True,'diagnostic':str(failure)})
        else:raise AssertionError('unknown root work accepted')
    return records,{'syntheticNonreturnedValueReservationAccepted':True,'limitedValidRootSelfTestAccepted':True,'mathematicallyValidWiderRootAccepted':True,
                    'scope':'Artificial copied metadata only, not natural C++ allocation/value/root fault injection; Native actual value bits are a separate gate.'}


def main():
    reference.need(__debug__,'run sphere box coverage reference tests without Python -O')
    parser=argparse.ArgumentParser();parser.add_argument('fixture',nargs='?');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output:args.output.mkdir(parents=True,exist_ok=False)
    stream=io.StringIO();run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SphereBoxTests))
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
