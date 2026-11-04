"""Analytic inventory checks and copied-output negative controls; no solver."""
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
SCRIPT = ROOT/'scripts/verify-world-static-mesh-preparation.py'
spec = importlib.util.spec_from_file_location('world_preparation_reference', SCRIPT)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def body(identifier, static=False):
    return {'id':identifier, 'isStatic':static, 'mass':1., 'inertiaDiagonal':[1.,1.,1.],
            'radius':.5, 'position':[0.,-0.,0.], 'velocity':[0.,0.,0.],
            'angularMomentum':[0.,0.,0.], 'orientation':[0.,0.,0.,1.],
            'force':[0.,-0.,0.], 'torque':[0.,0.,0.],
            'material':{'restitution':0.,'friction':0.}}


def plane(identifier):
    return {'id':identifier, 'normal':[0.,1.,-0.], 'offset':-0.,
            'material':{'restitution':0.,'friction':0.}}


def mesh(identifier, revision=1):
    return {'id':identifier, 'revision':revision,
            'triangles':[{'id':1, 'vertices':[[0.,-0.,0.],[1.,0.,0.],[0.,0.,1.]]}]}


def source():
    return {'bodies':[body(90,True),body(7),body(22)], 'planes':[plane(2),plane(61)],
            'meshes':[mesh(55,8),mesh(3,2)], 'gravity':[0.,-9.,-0.], 'horizon':.0625,
            'settings':dict(reference.SETTING_CAPS)}


def proposed_result(s):
    status,reason,failure,capture = reference.expected_preflight(s)
    return {'status':status, 'reason':reason, 'failure':failure, 'capture':capture,
            'snapshot':copy.deepcopy(s) if capture=='complete' else None,
            'inventory':reference.expected_inventory(s) if status=='ready' else None}


class IndependentPreparationTests(unittest.TestCase):
    def test_strict_loading_overflow_underflow_duplicates_and_signed_zero(self):
        for text in ('{"x":1e999}', '{"x":1e-999}', '{"x":0,"x":1}', '{"x":NaN}', '"\\ud800"'):
            with self.assertRaises((AssertionError,ValueError,UnicodeError)):
                reference.loads(text)
        self.assertEqual(reference.bits(reference.loads('{"x":-0}')['x']), reference.bits(-0.))
        self.assertEqual(reference.loads('{"x":0e-999}')['x'], 0.)

    def test_scalar_type_aliases_fail_closed(self):
        for value in (False,True,-0.,1.,-1,2**64):
            with self.assertRaises(AssertionError):
                reference.uint(value,2**64-1)
        self.assertEqual(reference.uint(0),0)
        with self.assertRaises(AssertionError):
            reference.source_equal(2**53,2**53+1)

    def test_independent_seven_collider_combination_enumeration(self):
        s=source(); inventory=reference.expected_inventory(s)
        self.assertEqual((inventory['dynamicBodies'],inventory['staticBodies'],inventory['allPairs']),(2,1,21))
        self.assertEqual(len(inventory['pairs']),11)
        self.assertEqual(inventory['excluded'],{'bodyBody':0,'bodyPlane':2,'bodyMesh':2,
                                               'planePlane':1,'planeMesh':4,'meshMesh':1,'total':10})
        actual={(p['kind'],p['first']['id'],p['second']['id']) for p in inventory['pairs']}
        expected={('body_body',7,90),('body_body',22,90),('body_body',7,22)}
        expected|={('body_plane',b,p) for b in (7,22) for p in (2,61)}
        expected|={('body_mesh',b,m) for b in (7,22) for m in (55,3)}
        self.assertEqual(actual,expected)
        first=inventory['pairs'][0]
        self.assertEqual(first,{'kind':'body_plane','first':{'kind':'body','id':7,'ordinal':1,'revision':0},
                               'second':{'kind':'plane','id':2,'ordinal':0,'revision':0}})

    def test_maximum_378_equals_188_plus_190(self):
        s=source();s['bodies']=[body(i+1) for i in range(8)]
        s['planes']=[plane(100+i) for i in range(16)]
        s['meshes']=[mesh(200+i) for i in range(4)]
        for m in s['meshes']:
            m['triangles']=[{'id':i+1,'vertices':[[0.,0.,0.],[1.,0.,0.],[0.,0.,1.]]} for i in range(16)]
        inventory=reference.expected_inventory(s)
        self.assertEqual((len(inventory['pairs']),inventory['excluded']['total'],inventory['allPairs']),(188,190,378))
        self.assertEqual(inventory['totalFaces'],64)
        self.assertEqual(reference.expected_preflight(s)[:2],('ready','none'))

    def test_six_exclusions_and_vacuous_are_not_nonoverlap(self):
        s=source();s['bodies'].append(body(91,True))
        inventory=reference.expected_inventory(s)
        self.assertTrue(all(inventory['excluded'].values()))
        for b in s['bodies']: b['isStatic']=True
        inventory=reference.expected_inventory(s)
        self.assertEqual(inventory['pairs'],[])
        self.assertEqual(inventory['allPairs'],inventory['excluded']['total'])

    def test_original_ordinals_and_mesh_revision_survive_reordering(self):
        s=source();a=reference.expected_inventory(s)
        for key in ('bodies','planes','meshes'):s[key].reverse()
        b=reference.expected_inventory(s)
        key=lambda p:(p['kind'],p['first']['id'],p['second']['id'])
        self.assertEqual([key(p) for p in a['pairs']],[key(p) for p in b['pairs']])
        self.assertNotEqual(a['pairs'][0]['second']['ordinal'],b['pairs'][0]['second']['ordinal'])
        ms=[p['second'] for p in b['pairs'] if p['kind']=='body_mesh']
        self.assertEqual({(m['id'],m['revision']) for m in ms},{(55,8),(3,2)})

    def test_face_namespace_is_local_and_geometry_is_not_queried(self):
        s=source()
        for m in s['meshes']:m['triangles'][0]['vertices']=[[0.,0.,0.]]*3
        self.assertEqual(reference.expected_preflight(s)[:2],('ready','none'))
        s['meshes'][0]['triangles'].append(copy.deepcopy(s['meshes'][0]['triangles'][0]))
        self.assertEqual(reference.expected_preflight(s)[1:3],('duplicate_face_id',reference.failure('face',0,1)))

    def test_hard_limit_precedes_capture_but_model_invalid_is_captured(self):
        s=source();s['bodies']=[body(i+1) for i in range(9)];s['settings']['maxPairs']=0
        self.assertEqual(reference.expected_preflight(s),('invalid_input','body_count',reference.failure('body',8),'none'))
        s=source();s['horizon']=-0.
        self.assertEqual(reference.expected_preflight(s),('invalid_input','horizon',reference.failure('world'),'complete'))

    def test_lower_profile_never_truncates_to_ready(self):
        for key,value,reason in [('maxBodies',2,'body_budget'),('maxPlanes',1,'plane_budget'),
                                  ('maxMeshes',1,'mesh_budget'),('maxTotalFaces',1,'face_budget'),('maxPairs',10,'pair_budget')]:
            s=source();s['settings'][key]=value
            self.assertEqual(reference.expected_preflight(s)[:2],('budget_exceeded',reason))
        s=source();s['settings']['maxPairs']=10;s['meshes'][0]['revision']=0
        self.assertEqual(reference.expected_preflight(s)[1],'mesh_revision')

    def test_raw_plane_and_all_body_zero_bits_are_source_data(self):
        s=source();r=proposed_result(s)
        reference.verify_fixture(s,r,reference.new_stats())
        for target in [('planes',0,'offset'),('bodies',0,'mass')]:
            changed=copy.deepcopy(r)
            changed['snapshot'][target[0]][target[1]][target[2]]=0.
            with self.assertRaises(AssertionError):reference.verify_fixture(s,changed,reference.new_stats())
        changed=copy.deepcopy(r);changed['snapshot']['bodies'][0]['force'][1]=0.
        with self.assertRaises(AssertionError):reference.verify_fixture(s,changed,reference.new_stats())

    def test_full_shape_is_required_and_no_numerical_candidate_is_allowed(self):
        s=source();r=proposed_result(s);r['candidateBodies']=copy.deepcopy(s['bodies'])
        with self.assertRaises(AssertionError):reference.verify_fixture(s,r,reference.new_stats())

    def test_whole_input_fingerprint_ignores_labels_and_fixture_order_only(self):
        s=source();t=copy.deepcopy(s);t['horizon']=.03125
        a=[{'name':'a','input':s},{'name':'b','input':t}]
        b=[{'name':'new0','input':t},{'name':'new1','input':s}]
        self.assertEqual(reference.input_fingerprint(a),reference.input_fingerprint(b))
        b[1]=copy.deepcopy(b[1]);b[1]['input']['bodies'][0]['force'][1]=0.
        self.assertNotEqual(reference.input_fingerprint(a),reference.input_fingerprint(b))


def controls(data):
    rows=data['fixtures'];records=[]
    find=lambda predicate:next(i for i,f in enumerate(rows) if predicate(f))
    ready=find(lambda f:f['result']['status']=='ready' and f['result']['inventory']['dynamicBodies'] and f['result']['inventory']['staticBodies'] and f['input']['planes'])
    maximum=find(lambda f:f['result']['status']=='ready' and len(f['result']['inventory']['pairs'])==188)
    invalid=find(lambda f:f['result']['capture']=='complete' and f['result']['status']=='invalid_input')
    budget=find(lambda f:f['result']['status']=='budget_exceeded')
    uncaptured=find(lambda f:f['result']['capture']=='none')
    zero=find(lambda f:f['result']['status']=='ready' and reference.count_numeric(f['input'])[1]>0)

    def add(name,index,mutate):
        fixture=copy.deepcopy(rows[index]);before=copy.deepcopy(fixture);mutate(fixture)
        try:reference.source_equal(before,fixture)
        except AssertionError:pass
        else:raise AssertionError('negative control made no change: '+name)
        try:reference.verify_fixture(fixture['input'],fixture['result'],reference.new_stats())
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:raise AssertionError('copied preparation corruption accepted: '+name)

    put=lambda obj,key,value:obj.__setitem__(key,value)
    r=lambda f:f['result'];inv=lambda f:r(f)['inventory']
    add('required final pair dropped',maximum,lambda f:inv(f)['pairs'].pop())
    add('pair duplicated instead of tail',maximum,lambda f:put(inv(f)['pairs'],-1,copy.deepcopy(inv(f)['pairs'][0])))
    add('stable pair ordering swapped',maximum,lambda f:inv(f)['pairs'].reverse())
    add('typed pair kind corrupted',maximum,lambda f:put(inv(f)['pairs'][-1],'kind','body_plane' if inv(f)['pairs'][-1]['kind']=='body_mesh' else 'body_mesh'))
    add('body source ordinal corrupted',maximum,lambda f:put(inv(f)['pairs'][-1]['first'],'ordinal',7-inv(f)['pairs'][-1]['first']['ordinal']))
    add('pair collider ID corrupted',maximum,lambda f:put(inv(f)['pairs'][-1]['second'],'id',999999))
    add('mesh revision erased',maximum,lambda f:put(next(p['second'] for p in inv(f)['pairs'] if p['kind']=='body_mesh'),'revision',0))
    add('nonmesh revision fabricated',maximum,lambda f:put(inv(f)['pairs'][0]['first'],'revision',1))
    add('ordinal boolean alias rejected',maximum,lambda f:put(inv(f)['pairs'][0]['first'],'ordinal',False))
    add('inventory count negative-zero alias rejected',maximum,lambda f:put(inv(f),'staticBodies',-0.))
    add('static flag numeric alias rejected',ready,lambda f:put(r(f)['snapshot']['bodies'][0],'isStatic',0))
    for key in sorted(reference.EXCLUDED_KEYS):
        add('excluded '+key+' undercount',ready,lambda f,k=key:put(inv(f)['excluded'],k,inv(f)['excluded'][k]+1))
    for key in ('dynamicBodies','staticBodies','totalFaces','colliders','allPairs'):
        add('inventory '+key+' corrupted',maximum,lambda f,k=key:put(inv(f),k,inv(f)[k]+1))
    add('required and excluded counts consistently delete a pair',maximum,lambda f:(inv(f)['pairs'].pop(),put(inv(f)['excluded'],'total',inv(f)['excluded']['total']+1)))
    add('original settings omitted',ready,lambda f:r(f)['snapshot'].pop('settings'))
    add('source body load changed',ready,lambda f:put(r(f)['snapshot']['bodies'][0]['force'],0,123.))
    add('source angular momentum changed',ready,lambda f:put(r(f)['snapshot']['bodies'][0]['angularMomentum'],2,123.))
    add('source body material omitted',ready,lambda f:r(f)['snapshot']['bodies'][0].pop('material'))
    add('source mesh face tail dropped',maximum,lambda f:r(f)['snapshot']['meshes'][-1]['triangles'].pop())
    add('source face vertices changed',maximum,lambda f:put(r(f)['snapshot']['meshes'][-1]['triangles'][-1]['vertices'][0],1,123.))
    add('source plane raw normal normalized',ready,lambda f:put(r(f)['snapshot']['planes'][0]['normal'],0,.123))
    add('whole source gravity omitted',ready,lambda f:r(f)['snapshot'].pop('gravity'))
    add('source horizon converted to normalized parameter',ready,lambda f:put(r(f)['snapshot'],'horizon',1.))
    def erase_zero(f):
        def visit(v):
            if type(v) is dict:
                for k,x in v.items():
                    if type(x) in (int,float) and reference.bits(x)==reference.bits(-0.):v[k]=0.;return True
                    if visit(x):return True
            elif type(v) is list:
                for k,x in enumerate(v):
                    if type(x) in (int,float) and reference.bits(x)==reference.bits(-0.):v[k]=0.;return True
                    if visit(x):return True
            return False
        reference.need(visit(r(f)['snapshot']),'signed-zero source control')
    add('source negative zero erased',zero,erase_zero)
    add('complete invalid snapshot claimed ready',invalid,lambda f:(put(r(f),'status','ready'),put(r(f),'reason','none')))
    add('budget failure publishes truncated inventory',budget,lambda f:put(r(f),'inventory',copy.deepcopy(rows[maximum]['result']['inventory'])))
    add('uncaptured hard failure fabricated complete snapshot',uncaptured,lambda f:(put(r(f),'capture','complete'),put(r(f),'snapshot',copy.deepcopy(f['input']))))
    add('ready source claims partial capture',ready,lambda f:put(r(f),'capture','partial'))
    add('ready source drops its complete snapshot',ready,lambda f:put(r(f),'snapshot',None))
    add('ready preparation promoted to numerical separation',ready,lambda f:put(r(f),'status','certified_separated'))
    add('ready preparation fabricates propagated candidate',ready,lambda f:put(r(f),'candidateBodies',copy.deepcopy(f['input']['bodies'])))
    for name,mutate in [('fixture omitted',lambda p:p['fixtures'].pop()),
                        ('duplicate input with new label',lambda p:put(p['fixtures'],-1,dict(copy.deepcopy(p['fixtures'][0]),name='new-label'))),
                        ('input sign bits changed',lambda p:put(p['fixtures'][zero]['input'],'horizon',.012345))]:
        packet=copy.deepcopy(data);mutate(packet)
        try:reference.verify(packet)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:
            records.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:raise AssertionError('whole-corpus corruption accepted: '+name)
    return records


def main():
    reference.need(__debug__,'run preparation reference tests without Python -O')
    parser=argparse.ArgumentParser();parser.add_argument('fixture',nargs='?');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output:args.output.mkdir(parents=True,exist_ok=False)
    stream=io.StringIO();run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentPreparationTests))
    if args.output:(args.output/'reference-self-tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    reference.need(run.wasSuccessful(),stream.getvalue())
    report={'status':'PASS','selfTestGroups':run.testsRun}
    if args.fixture:
        data=reference.load(args.fixture);baseline=reference.verify(data);rejected=controls(data)
        swapped=copy.deepcopy(data);swapped['fixtures'].reverse()
        for i,f in enumerate(swapped['fixtures']):f['name']='independent-preparation-'+str(i)
        reference.need(reference.verify(swapped)==baseline,'label/order independent whole-input audit')
        command=[sys.executable,'-O',str(SCRIPT),args.fixture]
        optimized=subprocess.run(command,capture_output=True,text=True,timeout=120)
        reference.need(optimized.returncode!=0 and 'without Python -O' in optimized.stderr,'Python -O fails closed')
        rejected.append({'name':'Python -O rejected','rejected':True,'diagnostic':optimized.stderr.strip().splitlines()[-1]})
        report.update(fixtures=baseline['fixtures'],baseline=baseline,rejectedControls=rejected,labelAndOrderIndependent=True)
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
    print(json.dumps({k:v for k,v in report.items() if k not in {'baseline','rejectedControls'}} |
                     ({'rejectedControls':len(rejected)} if args.fixture else {})))


if __name__=='__main__':
    main()
