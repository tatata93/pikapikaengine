"""Exact box/AST self-tests and copied Native coverage negative controls."""
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
SCRIPT=ROOT/'scripts/verify-accelerated-plane-box-coverage.py'
spec=importlib.util.spec_from_file_location('coverage_reference',SCRIPT)
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


def source(center=(4,0,0),normal=(1,0,0),error=0.,margin=0.):
    return {'input':{'sphere':{'center':list(center),'velocity':[0,0,0],'acceleration':[0,0,0],'radius':1},
                     'plane':{'normal':list(normal),'offset':0},'positionError':error,'contactMargin':margin},
            'horizon':.0625,'settings':{'timeTolerance':1e-7,'maxEvaluations':255,'maxLeaves':128,'maxDepth':24}}


def simple_fixture():
    s=source();cell={'timeBounds':[0.,s['horizon']],'depth':0,'parentAudit':None}
    evaluation={'tubeCoordinates':[[4,4],[0,0],[0,0]],'distance':[4,4],'threshold':[1,1],'gap':[3,3]}
    result={'status':'certified','reason':'none','snapshot':copy.deepcopy(s),'snapshotValidated':True,'failedInput':None,
            'partitionComplete':True,'audits':[{'cell':copy.deepcopy(cell),'callAttempted':True,'evaluation':evaluation,
              'outcome':'positive','blockedReason':'none','splitTime':None}],
            'partition':[{'cell':copy.deepcopy(cell),'state':'certified','auditIndex':0,'blockedReason':'none'}],
            'frontier':[],'current':None,'work':{'valueCallsAttempted':1,'valueCallsReturned':1}}
    return {'name':'artificial-static-reference','input':s,'result':result}


class RationalBoxTests(unittest.TestCase):
    def test_strict_loader_and_scalar_types(self):
        for text in ['{"x":1e999}','{"x":1e-999}','{"x":0,"x":1}','{"x":NaN}','"\\ud800"']:
            with self.assertRaises((AssertionError,ValueError,UnicodeError)):reference.loads(text)
        self.assertEqual(reference.bits(reference.loads('{"x":-0}')['x']),reference.bits(-0.))
        for value in [False,True,-0.,0.,1.]:
            with self.assertRaises(AssertionError):reference.uint(value,255,'metadata')

    def test_exact_quadratic_stationary_and_closed_endpoints(self):
        self.assertEqual(reference.quadratic_range([1,-4,4],F(0),F(1)),(0,1))
        self.assertEqual(reference.quadratic_range([1,-4,4],F(0),F(1,4)),(F(1,4),1))
        self.assertEqual(reference.quadratic_range([0,0,-1],F(-1),F(1)),(-1,0))
        self.assertEqual(reference.quadratic_range([1,3,0],F(2),F(2)),(7,7))

    def test_integer_nearest_even_normal_ties_and_binade(self):
        self.assertEqual(reference.integer_rn(1+F(1,2**53)),1)
        self.assertEqual(reference.integer_rn(1+F(3,2**53)),1+F(1,2**51))
        self.assertEqual(reference.integer_rn(2-F(1,2**53)),2)
        self.assertEqual(reference.integer_rn(-(1+F(3,2**53))),-(1+F(1,2**51)))
        self.assertEqual(reference.integer_rn(F(2**53+1)),F(2**53))

    def test_integer_nearest_even_subnormal_zero_and_normal_boundary(self):
        d=F(1,2**1074)
        self.assertEqual(reference.integer_rn(d/2),0)
        self.assertEqual(reference.integer_rn(3*d/2),2*d)
        self.assertEqual(reference.integer_rn(-d/2),0)
        self.assertEqual(reference.integer_rn(F(1,2**1022)-d/2),F(1,2**1022))
        self.assertEqual(reference.integer_rn(d),d)

    def test_integer_nearest_even_extreme_finite_and_overflow_reject(self):
        maximum=F((2**53-1)*2**971)
        self.assertEqual(reference.integer_rn(maximum),maximum)
        with self.assertRaises(AssertionError):reference.integer_rn(F(2**1024))

    def test_exact_product_is_not_erased_by_underflow(self):
        d=F(1,2**1074)
        self.assertEqual(reference.node_choices('mul',{d},{d}),frozenset([0,d*d]))

    def test_fma_and_separate_rounding_both_in_fixed_ast_family(self):
        e=F(1,2**27)
        choices=reference.fixed_ast([1+e,-1,0],[1-e,1,0],0,1,0)
        self.assertIn(-e*e,choices['distance'])
        self.assertIn(F(0),choices['distance'])
        self.assertIn(-1-e*e,choices['gap'])
        self.assertIn(F(-1),choices['gap'])

    def test_threshold_rounded_sum_is_not_two_sequential_subtractions(self):
        margin=F(1,2**54)
        choices=reference.fixed_ast([1,0,0],[1,0,0],0,1,margin)
        self.assertEqual(choices['threshold'],frozenset([1,1+margin]))
        self.assertEqual(choices['gap'],frozenset([-margin,0]))

    def test_fixed_association_must_not_be_reassociated(self):
        big=F(2**54)
        fixed=reference.fixed_ast([1,1,1],[big,-big,1],0,1,0)['distance']
        right=reference.node_choices('add',{big},reference.node_choices('add',{-big},{F(1)}))
        self.assertEqual(fixed,frozenset([1]))
        self.assertIn(F(0),right)

    def test_corner_monotonicity_with_mixed_normal_signs(self):
        n=[F(-2),F(3),F(-1,2)];box=[(F(-1),F(2)),(F(-3),F(4)),(F(0),F(1))]
        minimum=[pair[0] if a>=0 else pair[1] for a,pair in zip(n,box)]
        maximum=[pair[1] if a>=0 else pair[0] for a,pair in zip(n,box)]
        low=min(reference.fixed_ast(n,minimum,0,1,F(1,16))['gap'])
        high=max(reference.fixed_ast(n,maximum,0,1,F(1,16))['gap'])
        for x in box[0]:
            for y in box[1]:
                for z in box[2]:
                    values=reference.fixed_ast(n,[x,y,z],0,1,F(1,16))['gap']
                    self.assertTrue(low<=min(values)<=max(values)<=high)
        # Endpoints test the exact corner algebra, not a finite-time proof.

    def test_coordinate_tube_requires_internal_extremum_and_full_B(self):
        s=source(error=.25);s['input']['sphere']['center']=[0,0,0]
        s['input']['sphere']['velocity']=[-4,0,0];s['input']['sphere']['acceleration']=[8,0,0]
        cell={'timeBounds':[0,1]}
        e={'tubeCoordinates':[[-1.25,.25],[-.25,.25],[-.25,.25]],
           'distance':[-2,1],'threshold':[1,1],'gap':[-3,0]}
        reference.verify_evaluation(s,cell,e,reference.new_stats())
        wrong=copy.deepcopy(e);wrong['tubeCoordinates'][0]=[-.25,.25]
        with self.assertRaisesRegex(AssertionError,'quadratic extrema'):reference.verify_evaluation(s,cell,wrong,reference.new_stats())
        wrong=copy.deepcopy(e);wrong['tubeCoordinates'][1]=[0,0]
        with self.assertRaisesRegex(AssertionError,'declared B'):reference.verify_evaluation(s,cell,wrong,reference.new_stats())

    def test_subnormal_half_acceleration_is_not_scalar_prerounded(self):
        s=source(center=(0,0,0));d=reference.next_up(0.)
        s['input']['sphere']['acceleration']=[d,0,0]
        e={'tubeCoordinates':[[0,0],[0,0],[0,0]],'distance':[0,0],'threshold':[1,1],'gap':[-1,-1]}
        with self.assertRaisesRegex(AssertionError,'quadratic extrema'):reference.verify_evaluation(s,{'timeBounds':[0,.0625]},e,reference.new_stats())

    def test_whole_returned_record_and_synthetic_nonreturn_metadata(self):
        fixture=simple_fixture();reference.verify_fixture(fixture['input'],fixture['result'],reference.new_stats())
        r=fixture['result'];a=r['audits'][0]
        a.update(evaluation=None,outcome='blocked',blockedReason='value_exception')
        r.update(status='not_certified',reason='value_exception',current=copy.deepcopy(a['cell']))
        r['partition'][0].update(state='current',blockedReason='value_exception')
        r['work']['valueCallsReturned']=0
        reference.verify_fixture(fixture['input'],r,reference.new_stats())
        r['work']['valueCallsReturned']=1
        with self.assertRaises(AssertionError):reference.verify_fixture(fixture['input'],r,reference.new_stats())

    def test_validation_priority_B_margin_zero_normal_and_source_bits(self):
        s=source(normal=(0,-0.,0),error=-1,margin=-1);s['horizon']=-0.;s['settings']['maxEvaluations']=0
        self.assertEqual(reference.preflight(s),('settings',None));s['settings']['maxEvaluations']=255
        self.assertEqual(reference.preflight(s),('horizon',None));s['horizon']=.0625
        self.assertEqual(reference.preflight(s),('zero_normal',1));s['input']['plane']['normal'][0]=1
        self.assertEqual(reference.preflight(s),('position_error',2));s['input']['positionError']=-0.
        self.assertEqual(reference.preflight(s),('contact_margin',3));s['input']['contactMargin']=-0.
        self.assertEqual(reference.preflight(s),(None,None))
        a=source();b=copy.deepcopy(a);b['input']['positionError']=-0.
        with self.assertRaises(AssertionError):reference.source_equal(a,b)

    def test_width_RN_and_type_bit_fingerprint(self):
        d=reference.next_up(0.)
        self.assertEqual(reference.next_up(-0.),d)
        self.assertEqual(reference.width_upper({'timeBounds':[0,d]}),F(d))
        self.assertEqual(reference.width_upper({'timeBounds':[d,2*d]}),F(2*d))
        a=source();b=source(center=(5,0,0));rows=[{'name':'a','input':a},{'name':'b','input':b}]
        swapped=[{'name':'x','input':b},{'name':'y','input':a}]
        self.assertEqual(reference.input_fingerprint(rows),reference.input_fingerprint(swapped))
        swapped=copy.deepcopy(swapped);swapped[0]['input']['settings']['maxDepth']=24.
        self.assertNotEqual(reference.input_fingerprint(rows),reference.input_fingerprint(swapped))

    def test_finite_AST_budget_fails_closed(self):
        saved=reference.MAX_AST_CHOICES
        try:
            reference.MAX_AST_CHOICES=1
            with self.assertRaisesRegex(AssertionError,'budget'):reference.node_choices('mul',{1+F(1,2**27)},{1-F(1,2**27)})
        finally:reference.MAX_AST_CHOICES=saved


def controls(data):
    fixtures=data['fixtures'];records=[]
    find=lambda predicate:next(i for i,f in enumerate(fixtures) if predicate(f))
    positive=find(lambda f:f['result']['status']=='certified' and len(f['result']['audits'])==1)
    maximum=find(lambda f:len(f['result']['audits'])==255)
    frontier=find(lambda f:len(f['result']['frontier'])==127)
    divided=find(lambda f:f['result']['status']=='certified' and len(f['result']['audits'])>1)
    negative=find(lambda f:f['result']['audits'] and f['result']['audits'][0]['evaluation']['gap'][1]<0)
    error=find(lambda f:f['result']['reason']=='position_error')
    margin=find(lambda f:f['result']['reason']=='contact_margin')
    bounded=find(lambda f:f['result']['audits'] and f['input']['input']['positionError']>0 and f['result']['snapshotValidated'])
    invalid=find(lambda f:f['result']['status']=='invalid_input' and f['result']['failedInput'] is not None)
    put=lambda o,k,v:o.__setitem__(k,v)
    r=lambda f:f['result']
    e=lambda f:r(f)['audits'][0]['evaluation']
    def add(name,index,mutate):
        fixture=copy.deepcopy(fixtures[index]);before=json.dumps(fixture,sort_keys=True);mutate(fixture)
        reference.need(before!=json.dumps(fixture,sort_keys=True),'control changed '+name)
        try:reference.verify_fixture(fixture['input'],fixture['result'],reference.new_stats())
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as failure:
            records.append({'name':name,'rejected':True,'diagnostic':str(failure)})
        else:raise AssertionError('box corruption accepted: '+name)
    for key in ['distance','threshold','gap']:
        add(key+' replaced by unrelated point',positive,lambda f,k=key:put(e(f),k,[1e30,1e30]))
        add(key+' interval endpoint omitted',positive,lambda f,k=key:e(f)[k].pop())
        add(key+' boolean endpoint alias',positive,lambda f,k=key:put(e(f)[k],0,False))
    for k in range(3):
        add('coordinate tube axis '+str(k)+' replaced',positive,lambda f,k=k:put(e(f)['tubeCoordinates'],k,[1e30,1e30]))
    fma=find(lambda f:f['name']=='fma-and-separate-products-differ')
    threshold=find(lambda f:f['name']=='threshold-maximum-radius-positive-margin')
    interior=find(lambda f:f['name']=='safe-parabolic-subdivision')
    subnormal=find(lambda f:f['name']=='subnormal-half-acceleration-preserved')
    add('unrounded product / FMA distance choice erased',fma,lambda f:put(e(f),'distance',[0,0]))
    def rounded_threshold(f):
        d=f['input']['input'];value=reference.integer_rn(reference.fraction(d['sphere']['radius'])+reference.fraction(d['contactMargin']))
        # Conversion only serializes an already proven-representable integer-RN
        # result into a forged packet; it supplies no reference arithmetic.
        put(e(f),'threshold',[float(value),float(value)])
    add('rounded-only threshold erases exact-node choice',threshold,rounded_threshold)
    add('tube retains only endpoints and loses interior extremum',interior,
        lambda f:put(e(f)['tubeCoordinates'],1,[1.625,1.875]))
    add('scalar-prerounded subnormal half acceleration erased',subnormal,
        lambda f:put(e(f)['tubeCoordinates'],1,[0,0]))
    add('coordinate tube axis omitted',positive,lambda f:e(f)['tubeCoordinates'].pop())
    add('coordinate declared B erased',bounded,lambda f:put(e(f)['tubeCoordinates'],0,[0,0]))
    add('whole returned evaluation omitted',positive,lambda f:put(r(f)['audits'][0],'evaluation',None))
    add('partial returned record instead of whole evaluation',positive,lambda f:e(f).pop('threshold'))
    add('threshold scalar instead of interval',positive,lambda f:put(e(f),'threshold',f['input']['input']['sphere']['radius']))
    add('positive outcome from negative gap',negative,lambda f:put(r(f)['audits'][0],'outcome','positive'))
    add('final pending outcome retained',positive,lambda f:put(r(f)['audits'][0],'outcome','pending'))
    add('returned call attempt erased',positive,lambda f:put(r(f)['audits'][0],'callAttempted',False))
    add('attempt boolean replaced by numeric alias',positive,lambda f:put(r(f)['audits'][0],'callAttempted',1))
    add('last audit dropped',maximum,lambda f:r(f)['audits'].pop())
    add('BFS audit order reversed',divided,lambda f:r(f)['audits'].reverse())
    add('child parent link removed',divided,lambda f:put(r(f)['audits'][1]['cell'],'parentAudit',None))
    add('parent ordinal false alias',divided,lambda f:put(r(f)['audits'][1]['cell'],'parentAudit',False))
    add('depth negative-zero alias',positive,lambda f:put(r(f)['audits'][0]['cell'],'depth',-0.))
    add('seconds changed into normalized parameter',positive,lambda f:put(r(f)['audits'][0]['cell']['timeBounds'],1,1.))
    add('root zero metadata sign changed',positive,lambda f:put(r(f)['audits'][0]['cell']['timeBounds'],0,-0.))
    add('split boundary differs from actual children',divided,lambda f:put(r(f)['audits'][0],'splitTime',f['input']['horizon']/3))
    add('partition tail omitted',maximum,lambda f:r(f)['partition'].pop())
    add('partition duplicate first instead of tail',maximum,lambda f:put(r(f)['partition'],-1,copy.deepcopy(r(f)['partition'][0])))
    add('partition order reversed',maximum,lambda f:r(f)['partition'].reverse())
    add('partition audit link falsified',divided,lambda f:put(r(f)['partition'][0],'auditIndex',0))
    add('unresolved leaf promoted to certified',maximum,
        lambda f:put(next(leaf for leaf in r(f)['partition'] if leaf['state']!='certified'),'state','certified'))
    add('complete partition flag erased',positive,lambda f:put(r(f),'partitionComplete',False))
    add('halted current cell omitted',frontier,lambda f:put(r(f),'current',None))
    add('unqueried frontier tail omitted',frontier,lambda f:r(f)['frontier'].pop())
    add('frontier includes current',frontier,lambda f:r(f)['frontier'].insert(0,copy.deepcopy(r(f)['current'])))
    add('frontier order reversed',frontier,lambda f:r(f)['frontier'].reverse())
    for key in sorted(reference.WORK_KEYS):
        add(key+' counter falsified',positive,lambda f,k=key:put(r(f)['work'],k,r(f)['work'][k]+1))
    add('work false alias',positive,lambda f:put(r(f)['work'],'valueCallsReturned',True))
    add('nonexistent sqrt work invented',positive,lambda f:put(r(f)['work'],'sqrtRefinements',0))
    add('invalid captured original falsely validated',invalid,lambda f:put(r(f),'snapshotValidated',True))
    add('failed input boolean alias',invalid,lambda f:put(r(f),'failedInput',False))
    add('original snapshot absent',positive,lambda f:put(r(f),'snapshot',None))
    add('snapshot original B changed',positive,lambda f:put(r(f)['snapshot']['input'],'positionError',1e12))
    add('snapshot original margin changed',positive,lambda f:put(r(f)['snapshot']['input'],'contactMargin',.1))
    add('snapshot original normal changed',positive,lambda f:put(r(f)['snapshot']['input']['plane']['normal'],0,1e12))
    add('snapshot source setting omitted',positive,lambda f:r(f)['snapshot'].pop('settings'))
    add('snapshot metadata integer converted to float',positive,lambda f:put(r(f)['snapshot']['settings'],'maxDepth',float(f['input']['settings']['maxDepth'])))
    add('B rejection wrong source ordinal',error,lambda f:put(r(f),'failedInput',3))
    add('margin rejection wrong reason',margin,lambda f:put(r(f),'reason','position_error'))
    def zero_path(value,path=()):
        if type(value) is float and reference.bits(value)==reference.bits(-0.):return path
        if type(value) is list:
            for i,v in enumerate(value):
                found=zero_path(v,path+(i,))
                if found is not None:return found
        if type(value) is dict:
            for k,v in value.items():
                found=zero_path(v,path+(k,))
                if found is not None:return found
        return None
    zero=find(lambda f:zero_path(f['result']['snapshot']) is not None)
    def erase_zero(f):
        path=zero_path(r(f)['snapshot']);owner=r(f)['snapshot']
        for key in path[:-1]:owner=owner[key]
        owner[path[-1]]=0.
    add('original negative zero erased',zero,erase_zero)
    add('coverage fabricates World candidate',positive,lambda f:put(r(f),'candidate',{}))
    add('window fabricated from coverage',maximum,lambda f:put(r(f),'status','entry_window'))
    add('earlier unknown terminal reason replaced',frontier,lambda f:put(r(f),'reason','width_limit'))
    for name,mutate in [('whole fixture omitted',lambda p:p['fixtures'].pop()),
                        ('whole input replaced by duplicated label',lambda p:put(p['fixtures'],-1,dict(copy.deepcopy(p['fixtures'][0]),name='different-label'))),
                        ('input B scalar bits changed',lambda p:put(p['fixtures'][0]['input']['input'],'positionError',.125))]:
        p=copy.deepcopy(data);mutate(p)
        try:reference.verify(p)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as failure:
            records.append({'name':name,'rejected':True,'diagnostic':str(failure)})
        else:raise AssertionError('whole-corpus corruption accepted: '+name)
    widened=copy.deepcopy(fixtures[positive]);widened['result']['audits'][0]['evaluation']['distance']=[-1e30,1e30]
    reference.verify_fixture(widened['input'],widened['result'],reference.new_stats())
    nonreturn=copy.deepcopy(fixtures[positive]);result=nonreturn['result'];audit=result['audits'][0]
    audit.update(evaluation=None,outcome='blocked',blockedReason='value_exception',splitTime=None)
    result.update(status='not_certified',reason='value_exception',current=copy.deepcopy(audit['cell']))
    result['partition'][0].update(state='current',blockedReason='value_exception');result['work']['valueCallsReturned']=0
    reference.verify_fixture(nonreturn['input'],result,reference.new_stats())
    return records,{'mathematicallyValidWiderDistanceAccepted':True,'syntheticNonreturnedAttemptAccepted':True,
                    'scope':'Wider distance is not actual public-value provenance. Nonreturn is artificial copied metadata, not natural failure or actual C++ fault injection.'}


def main():
    reference.need(__debug__,'run box coverage reference tests without Python -O')
    parser=argparse.ArgumentParser();parser.add_argument('fixture',nargs='?');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output:args.output.mkdir(parents=True,exist_ok=False)
    stream=io.StringIO();run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RationalBoxTests))
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
