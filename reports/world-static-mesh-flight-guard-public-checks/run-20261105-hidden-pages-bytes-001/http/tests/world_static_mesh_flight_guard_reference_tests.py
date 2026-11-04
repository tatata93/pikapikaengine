"""World guard independent composition self-tests and copied-record controls.
Synthetic binding/nonreturn records test metadata only, not actual CPU/faults.
"""
import argparse,copy,hashlib,importlib.util,io,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/verify-world-static-mesh-flight-guard.py'
spec=importlib.util.spec_from_file_location('world_guard_reference',SCRIPT);reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


def source():
 def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
 f=read('reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-initial/native-fixtures.json')['fixtures'][0]['input']
 # Defaults are source data, never imported expected child outputs.
 sphere=read('reports/accelerated-sphere-box-coverage-native-development/run-001/native-fixtures.json')['fixtures'][0]['input']['settings']
 box={k:v for k,v in sphere.items() if k!='sqrtRefinements'}
 return {'bodies':[],'planes':[],'gravity':[0.,-1.,-0.],
  'meshes':[{'id':301,'revision':7,'triangles':copy.deepcopy(f['triangles'])}],
  'horizon':.0625,'settings':{'preparation':{'maxBodies':8,'maxPlanes':16,'maxMeshes':4,'maxTotalFaces':64,'maxPairs':256},
   'mesh':copy.deepcopy(f['settings']),'planeMetric':copy.deepcopy(box),'planeBox':copy.deepcopy(box),'sphereBox':copy.deepcopy(sphere),
   'contactMargin':-0.,'limits':reference.LIMIT_CAPS.copy()}}


def layout():return {key:8 if key=='uint64' else 512 for key in reference.LAYOUT_KEYS}


def synthetic_vacuous():
 s=source();z=layout();ps={**s,'settings':s['settings']['preparation']};inv=reference.prep.expected_inventory(ps)
 prep={'status':'ready','reason':'none','failure':None,'capture':'complete','snapshot':copy.deepcopy(ps),'inventory':inv}
 initial=reference.initial_request(s,inv,z)
 r={'status':'certified_separated','reason':'none','binding':{'mode':'source_enforced','state':'ready','checked':True,'profile':1,'buildId':'a'*64},
  'originalSettings':copy.deepcopy(s['settings']),'failure':None,'preparation':prep,
  'preparationMessages':{'fields':1,'nonemptyFields':0,'bytes':0,'omitted':False},'bodies':[],'pairs':[],
  'work':reference.empty_work(),'reservation':{'retained':initial,'granted':reference.zero(reference.GRANT_KEYS),'charged':reference.zero(reference.GRANT_KEYS)},
  'initialRequest':copy.deepcopy(initial),'candidateBodies':[]}
 return s,r,z


def synthetic_unconfigured():
 s=source();r={'status':'unsupported_environment','reason':'binding_unsupported',
  'binding':{'mode':'source_enforced','state':'unconfigured','checked':True,'profile':0,'buildId':''},
  'originalSettings':None,'failure':None,'preparation':None,'preparationMessages':{'fields':0,'nonemptyFields':0,'bytes':0,'omitted':False},
  'bodies':[],'pairs':[],'work':reference.empty_work(),'reservation':{'retained':reference.zero(reference.RETAINED_KEYS),
  'granted':reference.zero(reference.GRANT_KEYS),'charged':reference.zero(reference.GRANT_KEYS)},'initialRequest':None,'candidateBodies':None}
 return s,r,layout()


def check(s,r,z):reference.verify_fixture(s,r,z,reference.new_stats())


class CompositionTests(unittest.TestCase):
 def test_strict_loader(self):
  for text in ['{"x":1e999}','{"x":1e-999}','{"x":1,"x":2}','{"x":NaN}','"\\ud800"']:
   with self.assertRaises((AssertionError,ValueError,UnicodeError)):reference.loads(text)
  self.assertEqual(reference.bits(reference.loads('-0')),reference.bits(-0.))

 def test_unconfigured_no_capture_no_candidates(self):
  s,r,z=synthetic_unconfigured();check(s,r,z)
  r['originalSettings']=copy.deepcopy(s['settings'])
  with self.assertRaises(AssertionError):check(s,r,z)

 def test_binding_refusal_precedes_invalid_margin(self):
  s,r,z=synthetic_unconfigured();s['settings']['contactMargin']=-1;check(s,r,z)
  r['candidateBodies']=[]
  with self.assertRaises(AssertionError):check(s,r,z)

 def test_vacuous_success_is_no_static_overlap_proof(self):
  s,r,z=synthetic_vacuous();check(s,r,z)
  self.assertEqual(r['candidateBodies'],[]);self.assertEqual(r['work']['childCallsAttempted'],0)

 def test_full_snapshot_source_negative_zero(self):
  s,r,z=synthetic_vacuous();r['originalSettings']['contactMargin']=0.
  with self.assertRaises(AssertionError):check(s,r,z)

 def test_initial_layout_size_is_observation_not_heap_bound(self):
  s,r,z=synthetic_vacuous();expected=z['guardResult']+len(s['meshes'])*z['staticMeshSource']+sum(len(m['triangles']) for m in s['meshes'])*z['staticTriangle']
  self.assertEqual(r['initialRequest']['logicalPayloadBytes'],expected)
  r['reservation']['retained']['logicalPayloadBytes']-=1
  with self.assertRaises(AssertionError):check(s,r,z)

 def test_layout_fields_and_integer_types(self):
  z=layout();reference.layout_shape(z)
  for value in [False,-0.,8.]:
   bad=z.copy();bad['uint64']=value
   with self.assertRaises(AssertionError):reference.layout_shape(bad)
  s,r,z=synthetic_vacuous();r['initialRequest']['bodyRecords']=0.
  with self.assertRaises(AssertionError):check(s,r,z)
  for value in [False,-0.,1.]:
   with self.assertRaises(AssertionError):reference.profile_integer_fields({'heldLoad':{'maxEvaluations':value}})

 def test_requested_mesh_capacity_and_work_formula(self):
  s=source();z=layout();g=reference.make_grant('mesh',s['settings']['mesh'],2,z);h=s['settings']['mesh']['heldLoad'];e=h['maxEvaluations'];l=h['maxLeaves']
  self.assertEqual(g['retained']['heldAudits'],e);self.assertEqual(g['retained']['retainedFaces'],6)
  self.assertEqual(g['work']['primitiveQueries'],2*e);self.assertEqual(g['work']['candidatesExamined'],14*e)
  self.assertEqual(g['work']['sqrtRefinements'],min(h['maxTotalSqrtRefinements'],e*(2*512+1024)))
  self.assertEqual(g['retained']['logicalPayloadBytes'],e*z['heldAudit']+l*(z['heldCertifiedLeaf']+z['heldPartitionLeaf']+z['heldCell'])+2*(z['meshRow']+2*z['staticTriangle']+2*z['uint64'])+14*z['primitiveCandidateAudit'])

 def test_primitive_grant_root_norm_units_differ(self):
  s=source();z=layout()
  a=reference.make_grant('metric',s['settings']['planeMetric'],0,z);b=reference.make_grant('box',s['settings']['planeBox'],0,z);c=reference.make_grant('sphere',s['settings']['sphereBox'],0,z)
  self.assertEqual(a['work']['planeNormLoopIterationsUpper'],64*s['settings']['planeMetric']['maxEvaluations'])
  self.assertEqual(a['work']['sqrtRefinements'],0);self.assertEqual(b['work']['sqrtRefinements'],0)
  self.assertEqual(c['work']['sqrtRefinements'],2*s['settings']['sphereBox']['sqrtRefinements']*s['settings']['sphereBox']['maxEvaluations'])

 def test_unknown_counter_is_not_known_zero_work(self):
  w=reference.empty_work();reference.add_counter(w['sphereSqrtRefinements'],0,512,False);reference.sync(w)
  self.assertFalse(w['exact']);self.assertEqual(w['sqrtRefinements'],{'known':0,'upper':512,'exact':False})
  with self.assertRaises(AssertionError):reference.counter_shape({'known':0,'upper':512,'exact':True})

 def test_message_field_visits_and_omission(self):
  reference.omission({'fields':1,'nonemptyFields':1,'bytes':3,'omitted':True},1)
  for record in [{'fields':0,'nonemptyFields':0,'bytes':0,'omitted':False},{'fields':1,'nonemptyFields':0,'bytes':4,'omitted':False}]:
   with self.assertRaises(AssertionError):reference.omission(record,1)

 def test_fingerprint_types_bits_order_not_labels(self):
  a=source();b=copy.deepcopy(a);b['settings']['contactMargin']=.0625
  rows=[{'name':'a','input':a},{'name':'b','input':b}]
  self.assertEqual(reference.input_fingerprint(rows),reference.input_fingerprint(rows[::-1]))
  c=copy.deepcopy(a);c['settings']['contactMargin']=0.
  self.assertNotEqual(reference.input_fingerprint([{'input':a}]),reference.input_fingerprint([{'input':c}]))


def artificial_nonreturn(f,z):
 r=f['result'];first=min(((p['pairOrdinal'],c['attemptOrdinal']) for p in r['pairs'] if p['child']['kind']=='mesh' for c in [p['child']['mesh']] if c['attemptOrdinal'] is not None),key=lambda x:x[1])[0]
 for p in r['pairs']:
  p.update(state='unexamined',reason='none',executionOrdinal=None)
  for name in ['metric','box'] if p['child']['kind']=='plane' else [p['child']['kind']]:
   c=p['child'][name];c.update(state='unexamined',attemptOrdinal=None,usedSettings=copy.deepcopy(c['requestedSettings']),granted=False,grant={'retained':reference.zero(reference.RETAINED_KEYS),'work':reference.zero(reference.GRANT_KEYS)},result=None,messages={'fields':0,'nonemptyFields':0,'bytes':0,'omitted':False})
 for b in r['bodies']:b['state']='static_copy' if b['isStatic'] else 'unexamined'
 key=r['preparation']['inventory']['pairs'][first];body=key['first']['ordinal'];r['bodies'][body]['state']='failed'
 pair=r['pairs'][first];c=pair['child']['mesh'];faces=len(f['input']['meshes'][key['second']['ordinal']]['triangles']);g=reference.make_grant('mesh',c['usedSettings'],faces,z)
 pair.update(state='not_certified',reason='child_exception',executionOrdinal=0);c.update(state='nonreturned',attemptOrdinal=0,granted=True,grant=g)
 for p in r['pairs']:
  key=r['preparation']['inventory']['pairs'][p['pairOrdinal']]
  if key['kind']!='body_mesh' and (key['first']['ordinal']==body or (key['kind']=='body_body' and key['second']['ordinal']==body)):p.update(state='dependency_failed',reason='dependency_failed')
 w=reference.empty_work();w.update(childCallsAttempted=1,meshCallsAttempted=1,bridgeCallsUpper=1,exact=False)
 e=g['retained']['heldAudits'];n=faces;gw=g['work'];bounds={'meshQueries':gw['meshQueries'],'primitiveQueries':gw['primitiveQueries'],'candidatesExamined':gw['candidatesExamined'],'sqrtRefinements':gw['sqrtRefinements'],'primitiveSqrtRefinements':min(gw['sqrtRefinements'],e*n*512),'enclosureSqrtRefinements':min(gw['sqrtRefinements'],e*1024),'meshSqrtLimitedRows':e*n,'enclosureSqrtCalls':2*e,'enclosureSqrtLimitedCalls':2*e}
 for k,v in bounds.items():w['held'][k]=reference.counter(0,v,False)
 w['propagationAttempts']=reference.counter(0,1,False);reference.sync(w)
 r.update(status='not_certified',reason='child_exception',failure={'preparation':None,'bodyOrdinal':None,'pairOrdinal':first},work=w,candidateBodies=None)
 r['reservation']={'retained':reference.plus(r['initialRequest'],g['retained']),'granted':gw.copy(),'charged':gw.copy()}
 return f


def controls(data):
 fixtures=data['fixtures'];z=data['layoutSizes'];records=[]
 find=lambda p:next(i for i,f in enumerate(fixtures) if p(f))
 pos=find(lambda f:f['result']['status']=='certified_separated' and any(p['child']['kind']=='sphere' for p in f['result']['pairs']))
 maximum=find(lambda f:len(f['result']['pairs'])==188)
 static=find(lambda f:f['result']['status']=='certified_separated' and any(b['isStatic'] for b in f['input']['bodies']) and f['result']['candidateBodies'])
 put=lambda o,k,v:o.__setitem__(k,v)
 r=lambda f:f['result']
 pair=lambda f,kind:next(p for p in r(f)['pairs'] if p['child']['kind']==kind)
 c=lambda f,kind:pair(f,'plane' if kind in ['metric','box'] else kind)['child'][kind]
 def add(name,index,mutate):
  f=copy.deepcopy(fixtures[index]);before=json.dumps(f,sort_keys=True);mutate(f)
  reference.need(before!=json.dumps(f,sort_keys=True),'control changed '+name)
  try:check(f['input'],f['result'],z)
  except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:records.append({'name':name,'rejected':True,'diagnostic':str(error)})
  else:raise AssertionError('World composition corruption accepted: '+name)
 for key in sorted(reference.RESULT_KEYS):add('whole result field omitted '+key,pos,lambda f,k=key:r(f).pop(k))
 add('binding profile bool alias',pos,lambda f:put(r(f)['binding'],'profile',True))
 add('binding ready unchecked',pos,lambda f:put(r(f)['binding'],'checked',False))
 add('binding identity malformed',pos,lambda f:put(r(f)['binding'],'buildId','not-a-hash'))
 add('full original margin changed',pos,lambda f:put(r(f)['originalSettings'],'contactMargin',.1))
 add('preparation whole snapshot omitted',pos,lambda f:put(r(f)['preparation'],'snapshot',None))
 add('original source revision changed',pos,lambda f:put(r(f)['preparation']['snapshot']['meshes'][0],'revision',999))
 add('original body load changed',pos,lambda f:put(r(f)['preparation']['snapshot']['bodies'][0]['force'],0,99))
 add('prepared pair tail omitted',maximum,lambda f:r(f)['preparation']['inventory']['pairs'].pop())
 add('retained pair tail omitted',maximum,lambda f:r(f)['pairs'].pop())
 add('retained pair order reversed',pos,lambda f:r(f)['pairs'].reverse())
 add('pair ordinal bool alias',pos,lambda f:put(r(f)['pairs'][0],'pairOrdinal',False))
 add('pair type changed',pos,lambda f:put(pair(f,'mesh')['child'],'kind','sphere'))
 add('pair first actual execution ordinal changed',pos,lambda f:put(pair(f,'mesh'),'executionOrdinal',999))
 add('initial requested integer float alias',pos,lambda f:put(r(f)['initialRequest'],'bodyRecords',float(r(f)['initialRequest']['bodyRecords'])))
 add('unqueried requested integer float alias',maximum,lambda f:put(next(p['child']['mesh'] for p in r(f)['pairs'] if p['child']['kind']=='mesh' and p['child']['mesh']['state']=='unexamined')['requestedSettings']['heldLoad'],'maxEvaluations',256.))
 add('body seed index omitted',pos,lambda f:put(r(f)['bodies'][0],'seedPairOrdinal',None))
 add('body seed references wrong pair',pos,lambda f:put(r(f)['bodies'][0],'seedPairOrdinal',0))
 add('body seed state unexamined',pos,lambda f:put(r(f)['bodies'][0],'state','unexamined'))
 add('body isStatic bool alias',pos,lambda f:put(r(f)['bodies'][0],'isStatic',0))
 for kind in ['mesh','metric','box','sphere']:
  add(kind+' returned result omitted',pos,lambda f,k=kind:put(c(f,k),'result',None))
  add(kind+' actual attempt ordinal changed',pos,lambda f,k=kind:put(c(f,k),'attemptOrdinal',999))
  add(kind+' grant flag bool alias',pos,lambda f,k=kind:put(c(f,k),'granted',1))
  add(kind+' full grant field omitted',pos,lambda f,k=kind:c(f,k)['grant'].pop('retained'))
  add(kind+' requested profile changed',pos,lambda f,k=kind:put(c(f,k)['requestedSettings'],'unrecognized',1))
  add(kind+' used profile hidden setting changed',pos,lambda f,k=kind:put(c(f,k)['usedSettings'],'unrecognized',1))
  add(kind+' message visited field erased',pos,lambda f,k=kind:put(c(f,k)['messages'],'fields',0))
 add('mesh snapshot source ownership changed',pos,lambda f:put(c(f,'mesh')['result']['snapshot']['triangles'][0],'id',999))
 add('mesh original radius replaced by inflated radius',pos,lambda f:put(c(f,'mesh')['result']['snapshot']['body'],'radius',c(f,'mesh')['result']['tube']['guardRadius']))
 add('mesh source identity id changed',pos,lambda f:put(c(f,'mesh')['result']['worldBody']['body'],'id',999))
 add('mesh inflated certified gap forged',pos,lambda f:put(c(f,'mesh')['result']['inflated']['certifiedLeaves'][0],'lowerGapCertificate',[1e12,1e12]))
 add('metric returned containment forged',pos,lambda f:put(c(f,'metric')['result']['audits'][0],'value',[1e12,1e12]))
 add('plane box returned gap forged',pos,lambda f:put(c(f,'box')['result']['audits'][0]['evaluation'],'gap',[1e12,1e12]))
 def corrupt_sphere_root(f):
  e=c(f,'sphere')['result']['audits'][0]['evaluation'];e['root']['value']=e['distance']=[1e12,1e12]
 add('sphere root and distance coherently forged',pos,corrupt_sphere_root)
 for kind in ['metric','box','sphere']:add(kind+' complete coverage tail omitted',pos,lambda f,k=kind:c(f,k)['result']['partition'].pop())
 add('plane metric normal changed',pos,lambda f:put(c(f,'metric')['result']['snapshot']['input']['plane']['normal'],1,.5))
 add('plane box B erased',pos,lambda f:put(c(f,'box')['result']['snapshot']['input'],'positionError',0.))
 add('plane box radius replaced by guard radius',pos,lambda f:put(c(f,'box')['result']['snapshot']['input']['sphere'],'radius',c(f,'metric')['result']['snapshot']['input']['sphere']['radius']))
 add('sphere first B erased',pos,lambda f:put(c(f,'sphere')['result']['snapshot']['input'],'firstPositionError',0.))
 add('sphere second B erased',pos,lambda f:put(c(f,'sphere')['result']['snapshot']['input'],'secondPositionError',0.))
 add('sphere original radius inflated again',pos,lambda f:put(c(f,'sphere')['result']['snapshot']['input']['first'],'radius',c(f,'metric')['result']['snapshot']['input']['sphere']['radius']))
 add('sphere explicit margin erased',pos,lambda f:put(c(f,'sphere')['result']['snapshot']['input'],'contactMargin',0.))
 add('whole candidate tail omitted',pos,lambda f:r(f)['candidateBodies'].pop())
 add('candidate source order reversed',pos,lambda f:r(f)['candidateBodies'].reverse())
 add('static candidate load cleared',static,lambda f:put(next(b for b in r(f)['candidateBodies'] if b['isStatic'])['force'],1,0.))
 add('outer candidate load changed',pos,lambda f:put(r(f)['candidateBodies'][0]['torque'],0,99))
 for key in sorted(reference.WRAPPER_KEYS|reference.SCALAR_WORK):add('outer '+key+' changed',pos,lambda f,k=key:put(r(f)['work'],k,r(f)['work'][k]+1))
 for key in sorted(reference.COUNTERS):add('Counter '+key+' upper changed',pos,lambda f,k=key:put(r(f)['work'][k],'upper',r(f)['work'][k]['upper']+1))
 for key in sorted(reference.RETAINED_KEYS):add('retained no-refund '+key+' changed',pos,lambda f,k=key:put(r(f)['reservation']['retained'],k,r(f)['reservation']['retained'][k]+1))
 for key in sorted(reference.GRANT_KEYS):
  add('cumulative grant '+key+' changed',pos,lambda f,k=key:put(r(f)['reservation']['granted'],k,r(f)['reservation']['granted'][k]+1))
  add('settled charge '+key+' changed',pos,lambda f,k=key:put(r(f)['reservation']['charged'],k,r(f)['reservation']['charged'][k]+1))
 fake=artificial_nonreturn(copy.deepcopy(fixtures[pos]),z);check(fake['input'],fake['result'],z)
 for name,mutate in [('unknown upper refunded',lambda f:put(r(f)['work']['sqrtRefinements'],'upper',0)),('unknown block marked exact',lambda f:put(r(f)['work'],'exact',True)),('nonreturn publishes candidate',lambda f:put(r(f),'candidateBodies',[]))]:
  bad=copy.deepcopy(fake);mutate(bad)
  try:check(bad['input'],bad['result'],z)
  except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:records.append({'name':name,'rejected':True,'diagnostic':str(error)})
  else:raise AssertionError('artificial nonreturn metadata accepted')
 for name,mutate in [('complete fixture omitted',lambda d:d['fixtures'].pop()),('full source margin changed',lambda d:put(d['fixtures'][pos]['input']['settings'],'contactMargin',.1))]:
  bad=copy.deepcopy(data);mutate(bad)
  try:reference.verify(bad)
  except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:records.append({'name':name,'rejected':True,'diagnostic':str(error)})
  else:raise AssertionError('whole source pin corruption accepted')
 return records


def main():
 reference.need(__debug__,'run World guard reference tests without Python -O')
 parser=argparse.ArgumentParser();parser.add_argument('fixture',nargs='?');parser.add_argument('--output',type=Path);a=parser.parse_args()
 if a.output:a.output.mkdir(parents=True,exist_ok=False)
 stream=io.StringIO();run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CompositionTests))
 if a.output:(a.output/'reference-self-tests.txt').write_text(stream.getvalue(),encoding='utf-8')
 reference.need(run.wasSuccessful(),stream.getvalue());report={'status':'PASS','selfTestGroups':run.testsRun}
 if a.fixture:
  data=reference.load(a.fixture);baseline=reference.verify(data);records=controls(data)
  swapped=copy.deepcopy(data);swapped['fixtures'].reverse()
  for i,f in enumerate(swapped['fixtures']):f['name']='independent-world-'+str(i)
  reference.need(reference.verify(swapped)==baseline,'label/order independent proof and metadata')
  command=[sys.executable,'-O',str(SCRIPT),a.fixture];optimized=subprocess.run(command,capture_output=True,text=True,timeout=120)
  reference.need(optimized.returncode!=0 and 'without Python -O' in optimized.stderr,'optimized reference rejected')
  records.append({'name':'Python -O rejected','rejected':True,'diagnostic':optimized.stderr.strip().splitlines()[-1]})
  report.update(fixtures=baseline['fixtures'],baseline=baseline,rejectedControls=records,labelAndOrderIndependent=True)
 if a.output:
  (a.output/'commands.json').write_text(json.dumps({'argv':sys.argv,'python':sys.version},indent=2)+'\n',encoding='utf-8')
  (a.output/'negative-controls.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
  paths=[SCRIPT,Path(__file__)]+([Path(a.fixture)] if a.fixture else [])
  (a.output/'provenance.json').write_text(json.dumps([{'path':str(p.resolve()),'bytes':len(p.read_bytes()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],indent=2)+'\n',encoding='utf-8')
  if a.fixture:
   (a.output/'reference.json').write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8');(a.output/'optimized.stdout.txt').write_text(optimized.stdout,encoding='utf-8');(a.output/'optimized.stderr.txt').write_text(optimized.stderr,encoding='utf-8');(a.output/'optimized-command.json').write_text(json.dumps({'command':command,'exitCode':optimized.returncode},indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in {'baseline','rejectedControls'}}|({'rejectedControls':len(records)} if a.fixture else {})))


if __name__=='__main__':main()
