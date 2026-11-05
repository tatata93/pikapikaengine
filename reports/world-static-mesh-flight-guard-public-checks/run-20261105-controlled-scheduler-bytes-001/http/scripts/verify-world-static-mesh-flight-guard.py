"""Independent owned World guard composition/accounting; no production query.
Existing protected Fraction references audit child mathematics. This layer
reconstructs original typed sources, seed identities, reservations, execution
order, settled known/upper work and all-or-none candidate composition.
"""
import copy,hashlib,importlib.util,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def reference(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
prep=reference('world_preparation_reference','verify-world-static-mesh-preparation.py')
flight=reference('world_flight_reference','check-sphere-triangle-mesh-free-flight-guard.py')
metric=reference('world_metric_reference','verify-accelerated-pair-coverage.py')
plane=reference('world_plane_box_reference','verify-accelerated-plane-box-coverage.py')
sphere=reference('world_sphere_box_reference','verify-accelerated-sphere-box-coverage.py')
need,fields,uint=prep.need,prep.fields,prep.uint
bits,source_equal=prep.bits,prep.source_equal
fraction=plane.fraction
load,loads=plane.load,plane.loads
EXPECTED_FIXTURE_COUNT=51
EXPECTED_INPUT_FINGERPRINT='7a2804d8791140722a9ffb7cba3ab42d0274cfa2947789d1c9a5e1fbe2256e37'
LAYOUT_KEYS={'guardResult','bodyRecord','rigidBody','plane','staticMeshSource','pairRecord','preparationPair','staticTriangle','heldAudit','heldCertifiedLeaf','heldPartitionLeaf','heldCell','meshRow','uint64','primitiveCandidateAudit','metricAudit','metricPartitionLeaf','metricCell','planeBoxAudit','planeBoxPartitionLeaf','planeBoxCell','sphereBoxAudit','sphereBoxPartitionLeaf','sphereBoxCell'}
LIMIT_CAPS={'bodyRecords':8,'pairRecords':256,'heldAudits':1024,'heldCertifiedLeaves':1024,'heldPartition':1024,'heldFrontier':1024,'primitiveAudits':1024,'primitivePartition':1024,'primitiveFrontier':1024,'lastMeshRows':512,'primitiveCandidates':3584,'retainedFaces':1600,'meshQueries':1024,'primitiveQueries':65536,'candidatesExamined':458752,'sqrtRefinements':16777216,'planeMetricValues':1048576,'boxValues':1048576,'propagations':32,'logicalPayloadBytes':16777216}
RETAINED_KEYS={'bodyRecords','pairRecords','heldAudits','heldCertifiedLeaves','heldPartition','heldFrontier','primitiveAudits','primitivePartition','primitiveFrontier','lastMeshRows','primitiveCandidates','retainedFaces','logicalPayloadBytes'}
GRANT_KEYS={'meshQueries','primitiveQueries','candidatesExamined','sqrtRefinements','propagations','planeMetricValues','boxValues','planeNormLoopIterationsUpper','bridgeCallsUpper'}
HELD_COUNTERS={'meshQueries','primitiveQueries','candidatesExamined','primitiveSqrtRefinements','enclosureSqrtRefinements','sqrtRefinements','meshSqrtLimitedRows','enclosureSqrtCalls','enclosureSqrtLimitedCalls'}
COUNTERS={'propagationAttempts','planeMetricValues','boxValues','sphereSqrtRefinements','sqrtRefinements'}
WRAPPER_KEYS={k+'Calls'+e for k in ['child','mesh','planeMetric','planeBox','sphereBox'] for e in ['Attempted','Returned']}
SCALAR_WORK={'bridgeCallsUpper','planeNormCallsUpper','planeNormLoopIterationsUpper','sphereRootResultsReturned','sphereRootLimitedReturns'}
WORK_KEYS=WRAPPER_KEYS|COUNTERS|SCALAR_WORK|{'held','exact'}
RESULT_KEYS={'status','reason','binding','originalSettings','failure','preparation','preparationMessages','bodies','pairs','work','reservation','initialRequest','candidateBodies'}
SETTINGS_KEYS={'preparation','mesh','planeMetric','planeBox','sphereBox','contactMargin','limits'}
REASONS={'none','preparation_failed','settings','storage_budget','work_budget','seed_failed','dependency_failed','mesh_not_separated','metric_not_separated','box_not_separated','binding_unsupported','child_environment','unknown_work','child_exception','metadata_inconsistent','allocation_failure','environment'}

def equal(a,b,label):
 try:source_equal(a,b)
 except AssertionError as e:raise AssertionError(label+': '+str(e)) from e

def zero(keys):return {k:0 for k in keys}
def counter(known=0,upper=None,exact=True):return {'known':known,'upper':known if upper is None else upper,'exact':exact}
def empty_work():return {**zero(WRAPPER_KEYS|SCALAR_WORK),**{k:counter() for k in COUNTERS},'held':{k:counter() for k in HELD_COUNTERS},'exact':True}
def plus(a,b):return {k:a[k]+b[k] for k in a}
def add_counter(a,known,upper=None,exact=True):
 upper=known if upper is None else upper;need(0<=known<=upper and (not exact or known==upper),'valid known/upper/exact increment')
 a['known']+=known;a['upper']+=upper;a['exact']=a['exact'] and exact

def sync(w):
 w['sqrtRefinements']=copy.deepcopy(w['held']['sqrtRefinements']);b=w['sphereSqrtRefinements'];add_counter(w['sqrtRefinements'],b['known'],b['upper'],b['exact'])
 w['exact']=w['exact'] and all(w['held'][k]['exact'] for k in ['meshQueries','primitiveQueries','candidatesExamined','sqrtRefinements']) and all(w[k]['exact'] for k in COUNTERS)

def counter_shape(v):
 fields(v,{'known','upper','exact'},'Counter');uint(v['known'],2**64-1,'known');uint(v['upper'],2**64-1,'upper')
 need(type(v['exact']) is bool and v['known']<=v['upper'] and (not v['exact'] or v['known']==v['upper']),'counter consistency')

def work_shape(v):
 fields(v,WORK_KEYS,'all outer Work');fields(v['held'],HELD_COUNTERS,'held ledger')
 for k in WRAPPER_KEYS|SCALAR_WORK:uint(v[k],2**64-1,k)
 for k in COUNTERS:counter_shape(v[k])
 for item in v['held'].values():counter_shape(item)
 need(type(v['exact']) is bool,'outer exact boolean')

def settings_shape(s):
 fields(s,SETTINGS_KEYS,'full guard profile');fields(s['limits'],LIMIT_CAPS,'full global limits')
 for k,v in s['limits'].items():uint(v,2**64-1,k)
 dummy={'center':[0,0,0],'velocity':[0,0,0],'acceleration':[0,0,0],'radius':1}
 for k,m in [('planeMetric',metric),('planeBox',plane),('sphereBox',sphere)]:
  d={'kind':'sphere_plane','sphere':dummy,'plane':{'normal':[0,1,0],'offset':0}} if k=='planeMetric' else ({'sphere':dummy,'plane':{'normal':[0,1,0],'offset':0},'positionError':0,'contactMargin':0} if k=='planeBox' else {'first':dummy,'second':dummy,'firstPositionError':0,'secondPositionError':0,'contactMargin':0})
  m.source_shape({'input':d,'horizon':.0625,'settings':s[k]})
 m=s['mesh'];fields(m,{'heldLoad','maxAngularIncrement'},'mesh profile');h=m['heldLoad']
 fields(h,{'mesh','timeTolerance','maxEvaluations','maxLeaves','maxDepth','enclosureSqrtRefinements','maxTotalSqrtRefinements'},'held profile')
 fields(h['mesh'],{'maxSurfaces','primitive'},'mesh subprofile');p=h['mesh']['primitive']
 fields(p,{'maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared'},'primitive profile')
 for k in ['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements']:uint(p[k],2**64-1,k)
 for k in ['maximumLocalWidth','maximumNormalWidth','minimumSineSquared']:fraction(p[k])
 uint(h['mesh']['maxSurfaces'],2**64-1,'maxSurfaces')
 for k in ['maxEvaluations','maxLeaves','maxDepth','enclosureSqrtRefinements','maxTotalSqrtRefinements']:uint(h[k],2**64-1,k)
 fraction(h['timeTolerance']);fraction(m['maxAngularIncrement']);fraction(s['contactMargin'])

def settings_valid(s):
 h=s['mesh']['heldLoad'];p=h['mesh']['primitive']
 mv=(1<=h['mesh']['maxSurfaces']<=64 and 1<=p['maxCandidates']<=7 and 1<=p['sqrtRefinements']<=256 and 1<=p['maxTotalSqrtRefinements']<=1024 and 0<fraction(p['maximumLocalWidth'])<=10**6 and 0<fraction(p['maximumNormalWidth'])<=2 and 0<fraction(p['minimumSineSquared'])<=1 and 0<fraction(h['timeTolerance'])<=fraction(.1) and 1<=h['maxEvaluations']<=256 and 1<=h['maxLeaves']<=128 and h['maxDepth']<=32 and 1<=h['enclosureSqrtRefinements']<=256 and 1<=h['maxTotalSqrtRefinements']<=16777216 and 0<fraction(s['mesh']['maxAngularIncrement'])<=fraction(float.fromhex('0x1.921fb54442d18p+1')))
 def coverage(c,root=False):return 0<fraction(c['timeTolerance'])<=fraction(.1) and 1<=c['maxEvaluations']<=255 and 1<=c['maxLeaves']<=128 and c['maxDepth']<=32 and (not root or 1<=c['sqrtRefinements']<=256)
 return mv and coverage(s['planeMetric']) and coverage(s['planeBox']) and coverage(s['sphereBox'],True) and all(1<=s['limits'][k]<=cap for k,cap in LIMIT_CAPS.items()) and 0<=fraction(s['contactMargin'])<=fraction(.1)

def source_shape(s):
 fields(s,{'bodies','planes','gravity','meshes','horizon','settings'},'full caller World/source');settings_shape(s['settings']);prep.input_shape({**s,'settings':s['settings']['preparation']})

def input_fingerprint(fixtures):
 def encode(v):
  if type(v) is dict:return '{'+','.join(json.dumps(k)+':'+encode(v[k]) for k in sorted(v))+'}'
  if type(v) is list:return '['+','.join(encode(x) for x in v)+']'
  if type(v) is bool:return 'bool:'+str(v)
  if type(v) is int:return 'int:'+str(v)
  if type(v) is float:return 'binary64:'+bits(v).hex()
  need(False,'whole input scalar type')
 return hashlib.sha256(('\n'.join(sorted(encode(f['input']) for f in fixtures))+'\n').encode()).hexdigest()

def layout_shape(z):
 fields(z,LAYOUT_KEYS,'same-run observed public sizeof')
 for k,v in z.items():uint(v,1048576,'sizeof '+k);need(v>0,'positive sizeof')
 need(z['uint64']==8,'uint64 representation')

def initial_request(s,inv,z):
 r=zero(RETAINED_KEYS);b=len(s['bodies']);p=len(s['planes']);m=len(s['meshes']);n=len(inv['pairs']);t=inv['totalFaces']
 r.update(bodyRecords=b,pairRecords=n,retainedFaces=t,logicalPayloadBytes=z['guardResult']+b*(z['bodyRecord']+2*z['rigidBody'])+p*z['plane']+m*z['staticMeshSource']+n*(z['pairRecord']+z['preparationPair'])+t*z['staticTriangle']);return r

def make_grant(kind,used,n,z):
 r=zero(RETAINED_KEYS);w=zero(GRANT_KEYS)
 if kind=='mesh':
  h=used['heldLoad'];e=h['maxEvaluations'];l=h['maxLeaves'];r.update(heldAudits=e,heldCertifiedLeaves=l,heldPartition=l,heldFrontier=l,lastMeshRows=n,primitiveCandidates=7*n,retainedFaces=3*n)
  r['logicalPayloadBytes']=e*z['heldAudit']+l*(z['heldCertifiedLeaf']+z['heldPartitionLeaf']+z['heldCell'])+n*(z['meshRow']+2*z['staticTriangle']+2*z['uint64'])+7*n*z['primitiveCandidateAudit']
  w.update(meshQueries=e,primitiveQueries=e*n,candidatesExamined=e*n*7,sqrtRefinements=min(h['maxTotalSqrtRefinements'],e*(512*n+1024)),propagations=1,bridgeCallsUpper=1)
 else:
  e=used['maxEvaluations'];l=used['maxLeaves'];p={'metric':'metric','box':'planeBox','sphere':'sphereBox'}[kind];r.update(primitiveAudits=e,primitivePartition=l,primitiveFrontier=l);r['logicalPayloadBytes']=e*z[p+'Audit']+l*(z[p+'PartitionLeaf']+z[p+'Cell'])
  if kind=='metric':w.update(planeMetricValues=e,planeNormLoopIterationsUpper=64*e)
  else:w['boxValues']=e
  if kind=='sphere':w['sqrtRefinements']=2*e*used['sqrtRefinements']
 return {'retained':r,'work':w}

def omission(v,count):
 fields(v,{'fields','nonemptyFields','bytes','omitted'},'message omission')
 for k in ['fields','nonemptyFields','bytes']:uint(v[k],64*1024*1024,'message '+k)
 need(v['fields']==count and v['nonemptyFields']<=count and type(v['omitted']) is bool,'visited message field count')
 need(v['omitted']==(v['nonemptyFields']>0) and (v['bytes']==0)==(v['nonemptyFields']==0) and v['bytes']>=v['nonemptyFields'],'message consistency; exact text bytes provenance remains Native')

def message_fields(kind,r):
 if r is None:return 0
 if kind!='mesh':return 1
 n=1;h=r['inflated']
 if h is not None:
  n+=1;last=h['lastMesh']
  if last is not None:n+=1+sum(row['query'] is not None for row in last['rows'])
 return n

def call_shape(c):
 fields(c,{'state','attemptOrdinal','requestedSettings','usedSettings','granted','grant','result','messages'},'complete Call')
 need(type(c['state']) is str and c['state'] in {'unexamined','returned','nonreturned'} and type(c['granted']) is bool,'Call states/flags')
 if c['attemptOrdinal'] is not None:uint(c['attemptOrdinal'],1023,'call ordinal')
 fields(c['grant'],{'retained','work'},'full Grant')
 for k,keys in [('retained',RETAINED_KEYS),('work',GRANT_KEYS)]:
  fields(c['grant'][k],keys,'grant '+k)
  for v in c['grant'][k].values():uint(v,2**64-1,'grant count')

def profile_integer_fields(v):
 """Metadata counts remain integers even on unqueried/denied call records."""
 for k,x in v.items():
  if type(x) is dict:profile_integer_fields(x)
  elif k in {'maxSurfaces','maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maxEvaluations','maxLeaves','maxDepth','enclosureSqrtRefinements'}:uint(x,2**64-1,'profile '+k)

def fits_retained(r,l):return all(r[k]<=l[k] for k in RETAINED_KEYS)
def fits_work(w,l):return all(w[k]<=l[k] for k in GRANT_KEYS-{'planeNormLoopIterationsUpper','bridgeCallsUpper'}) and w['planeNormLoopIterationsUpper']<=64*l['planeMetricValues'] and w['bridgeCallsUpper']<=32

def new_stats(count=0):
 return {'fixtures':count,'certifiedSeparated':0,'notCertified':0,'invalidInputs':0,'unsupported':0,'prepared':0,'childCalls':0,'meshCalls':0,'metricCalls':0,'planeBoxCalls':0,'sphereCalls':0,'candidateBodies':0,'maximumPairs':0,'maximumAllPairs':0,'reducedPrimitiveGrants':0,'knownRootRefinements':0,'mathematicalChildrenVerified':zero({'flight','metric','planeBox','sphereBox'}),'preparation':prep.new_stats(),'flight':flight.new_stats(0),'metric':metric.new_stats(),'planeBox':plane.new_stats(),'sphereBox':sphere.new_stats()}

def verify_fixture(s,r,z,stats):
 source_shape(s);layout_shape(z);fields(r,RESULT_KEYS,'whole World guard result')
 need(type(r['status']) is str and r['status'] in {'certified_separated','not_certified','invalid_input','unsupported_environment','numerical_failure'},'guard status')
 need(type(r['reason']) is str and r['reason'] in REASONS,'guard reason')
 b=r['binding'];fields(b,{'mode','state','checked','profile','buildId'},'binding configuration identity')
 need(b['mode']=='source_enforced' and type(b['checked']) is bool and type(b['state']) is str and b['state'] in {'unconfigured','unsupported_target','identity_mismatch','environment_unsupported','ready'},'binding metadata')
 uint(b['profile'],1,'binding profile');need(type(b['buildId']) is str and (b['buildId']=='' or re.fullmatch('[0-9a-f]{64}',b['buildId'])),'owned configuration identity')
 work_shape(r['work']);fields(r['reservation'],{'retained','granted','charged'},'Reservation')
 if r['failure'] is not None:
  fields(r['failure'],{'preparation','bodyOrdinal','pairOrdinal'},'typed outer failure')
  for key,cap in [('bodyOrdinal',7),('pairOrdinal',255)]:
   if r['failure'][key] is not None:uint(r['failure'][key],cap,'failure '+key)
 if r['initialRequest'] is not None:
  fields(r['initialRequest'],RETAINED_KEYS,'complete initial request')
  for v in r['initialRequest'].values():uint(v,2**64-1,'initial requested count')
 for k,keys in [('retained',RETAINED_KEYS),('granted',GRANT_KEYS),('charged',GRANT_KEYS)]:
  fields(r['reservation'][k],keys,'reservation '+k)
  for v in r['reservation'][k].values():uint(v,2**64-1,'reservation count')
 need(type(r['bodies']) is list and len(r['bodies'])<=8 and type(r['pairs']) is list and len(r['pairs'])<=256,'bounded complete record arrays')
 empty={'retained':zero(RETAINED_KEYS),'granted':zero(GRANT_KEYS),'charged':zero(GRANT_KEYS)}
 if b['state']!='ready':
  need(r['status']=='unsupported_environment' and r['reason'] in {'binding_unsupported','environment'},'unconfigured is not a numerical certificate')
  need(all(r[k] is None for k in ['originalSettings','failure','preparation','initialRequest','candidateBodies']) and r['bodies']==r['pairs']==[],'refusal before capture/preparation/children')
  equal(empty_work(),r['work'],'early zero work');equal(empty,r['reservation'],'early zero charge');omission(r['preparationMessages'],0);stats['unsupported']+=1;return
 need(b['checked'] and b['profile']==1 and re.fullmatch('[0-9a-f]{64}',b['buildId']),'ready profile metadata; machine artifact audit remains external')
 source_shape({**s,'settings':r['originalSettings']})
 equal(s['settings'],r['originalSettings'],'owned original profile')
 ps={**s,'settings':s['settings']['preparation']};need(r['preparation'] is not None,'ready binding performs preparation')
 prep.verify_fixture(ps,r['preparation'],stats['preparation']);omission(r['preparationMessages'],1)
 if r['preparation']['status']!='ready':
  expected={'invalid_input':'invalid_input','budget_exceeded':'not_certified','unsupported_environment':'unsupported_environment','numerical_failure':'numerical_failure'}[r['preparation']['status']]
  need(r['status']==expected and r['reason']=='preparation_failed','preparation refusal mapping')
  equal({'preparation':r['preparation']['failure'],'bodyOrdinal':None,'pairOrdinal':None},r['failure'],'typed failure ownership')
  need(r['initialRequest'] is r['candidateBodies'] is None and r['bodies']==r['pairs']==[],'no record prefix before preparation ready')
  equal(empty_work(),r['work'],'preparation zero work');equal(empty,r['reservation'],'preparation zero charge');stats['invalidInputs' if expected=='invalid_input' else 'notCertified']+=1;return
 stats['prepared']+=1
 if not settings_valid(s['settings']):
  need(r['status']=='invalid_input' and r['reason']=='settings' and r['failure'] is None,'full settings validation follows preparation')
  need(r['initialRequest'] is r['candidateBodies'] is None and r['bodies']==r['pairs']==[],'invalid profile has no numerical calls/records')
  equal(empty_work(),r['work'],'profile zero work');equal(empty,r['reservation'],'profile zero charge');stats['invalidInputs']+=1;return
 inv=prep.expected_inventory(ps);initial=initial_request(s,inv,z)
 stats['maximumPairs']=max(stats['maximumPairs'],len(inv['pairs']));stats['maximumAllPairs']=max(stats['maximumAllPairs'],inv['allPairs'])
 equal(initial,r['initialRequest'],'complete initial requested capacity')
 if not fits_retained(initial,s['settings']['limits']):
  need(r['status']=='not_certified' and r['reason']=='storage_budget' and r['failure'] is None,'initial quota refusal precedes record installation')
  need(r['candidateBodies'] is None and r['bodies']==r['pairs']==[],'whole preparation retained without partial records')
  equal(empty_work(),r['work'],'initial zero work');equal(empty,r['reservation'],'initial zero charge');stats['notCertified']+=1;return
 Replay(s,r,z,stats,inv,initial).run()

class Halt(Exception):
 def __init__(self,status,reason):self.status=status;self.reason=reason

class Replay:
 """Reconstruct finite metadata, never a geometry/interval evaluator."""
 def __init__(self,s,r,z,stats,inv,initial):
  self.s=s;self.r=r;self.z=z;self.stats=stats;self.keys=inv['pairs'];self.settings=s['settings'];self.limits=self.settings['limits'];self.work=empty_work()
  self.res={'retained':initial.copy(),'granted':zero(GRANT_KEYS),'charged':zero(GRANT_KEYS)}
  need(len(r['pairs'])==len(self.keys) and len(r['bodies'])==len(s['bodies']),'no missing complete prepared body/pair tail')
  minimum=min(range(len(s['meshes'])),key=lambda i:s['meshes'][i]['id']);self.bodies=[];self.pairs=[];self.calls={};self.active=None
  for i,body in enumerate(s['bodies']):
   seed=None if body['isStatic'] else next(j for j,p in enumerate(self.keys) if p['kind']=='body_mesh' and p['first']['ordinal']==i and p['second']['ordinal']==minimum)
   self.bodies.append({'bodyOrdinal':i,'isStatic':body['isStatic'],'state':'static_copy' if body['isStatic'] else 'unexamined','seedPairOrdinal':seed})
  for i,key in enumerate(self.keys):
   a=r['pairs'][i];fields(a,{'pairOrdinal','state','reason','executionOrdinal','child'},'whole PairRecord');uint(a['pairOrdinal'],255,'pair ordinal');need(a['pairOrdinal']==i,'full original pair ordinal')
   need(type(a['state']) is str and a['state'] in {'unexamined','certified','not_certified','dependency_failed'} and type(a['reason']) is str and a['reason'] in REASONS,'pair metadata enums')
   if a['executionOrdinal'] is not None:uint(a['executionOrdinal'],1023,'execution ordinal')
   child=a['child'];kind={'body_mesh':'mesh','body_plane':'plane','body_body':'sphere'}[key['kind']]
   fields(child,{'kind','metric','box'} if kind=='plane' else {'kind',kind},'typed child variant');need(child['kind']==kind,'same typed prepared pair')
   self.pairs.append({'pairOrdinal':i,'state':'unexamined','reason':'none','executionOrdinal':None})
   for name in ['metric','box'] if kind=='plane' else [kind]:
    c=child[name];call_shape(c);profile=self.settings[{'mesh':'mesh','metric':'planeMetric','box':'planeBox','sphere':'sphereBox'}[name]]
    profile_integer_fields(c['requestedSettings']);profile_integer_fields(c['usedSettings'])
    equal(profile,c['requestedSettings'],'original requested profile')
    self.calls[(i,name)]={'actual':c,'used':copy.deepcopy(profile),'grant':{'retained':zero(RETAINED_KEYS),'work':zero(GRANT_KEYS)},'granted':False,'ordinal':None,'state':'unexamined'}

 def charge(self,g):
  retained=plus(self.res['retained'],g['retained']);charged=plus(self.res['charged'],g['work'])
  if not fits_retained(retained,self.limits):raise Halt('not_certified','storage_budget')
  if not fits_work(charged,self.limits):raise Halt('not_certified','work_budget')
  self.res['retained']=retained;self.res['charged']=charged;self.res['granted']=plus(self.res['granted'],g['work'])

 def settle(self,g,actual):
  for k in GRANT_KEYS:
   need(actual[k]<=g[k] and self.res['charged'][k]>=g[k],'returned work within reserved grant');self.res['charged'][k]+=actual[k]-g[k]

 def ready(self,i):return self.bodies[i]['state'] in {'ready','static_copy'}

 def motion(self,i,metric_radius=False):
  original=self.s['bodies'][i]
  if original['isStatic']:return {'center':original['position'],'velocity':[0.,0.,0.],'acceleration':[0.,0.,0.],'radius':original['radius']},0.
  need(self.bodies[i]['state']=='ready','primitive has a ready dynamic seed')
  seed=self.calls[(self.bodies[i]['seedPairOrdinal'],'mesh')]['actual']['result']
  return {'center':original['position'],'velocity':original['velocity'],'acceleration':seed['tube']['nominalAcceleration'],'radius':seed['tube']['guardRadius'] if metric_radius else original['radius']},seed['tube']['positionError']

 def execute(self,i,kind):
  self.active=i;c=self.calls[(i,kind)];a=c['actual'];key=self.keys[i];used=c['used']
  if kind!='mesh':
   val='planeMetricValues' if kind=='metric' else 'boxValues'
   e=min(used['maxEvaluations'],self.limits['primitiveAudits']-self.res['retained']['primitiveAudits'],self.limits[val]-self.res['charged'][val])
   if kind=='sphere':e=min(e,(self.limits['sqrtRefinements']-self.res['charged']['sqrtRefinements'])//(2*used['sqrtRefinements']))
   used['maxEvaluations']=e
   if e==0:raise Halt('not_certified','storage_budget' if self.res['retained']['primitiveAudits']==self.limits['primitiveAudits'] else 'work_budget')
  n=len(self.s['meshes'][key['second']['ordinal']]['triangles']) if kind=='mesh' else 0
  g=make_grant(kind,used,n,self.z);c['grant']=g;self.charge(g);c['granted']=True
  ordinal=self.work['childCallsAttempted'];c['ordinal']=ordinal;c['state']=a['state']
  if self.pairs[i]['executionOrdinal'] is None:self.pairs[i]['executionOrdinal']=ordinal
  prefix={'mesh':'mesh','metric':'planeMetric','box':'planeBox','sphere':'sphereBox'}[kind]
  self.work['childCallsAttempted']+=1;self.work[prefix+'CallsAttempted']+=1
  need(a['state'] in {'returned','nonreturned'},'granted call has actual returned/nonreturned state')
  r=a['result'];returned=a['state']=='returned';need(returned==(r is not None),'full result iff returned')
  if returned:self.work['childCallsReturned']+=1;self.work[prefix+'CallsReturned']+=1
  omission(a['messages'],message_fields(kind,r))
  self.stats['childCalls']+=1;self.stats[{'mesh':'meshCalls','metric':'metricCalls','box':'planeBoxCalls','sphere':'sphereCalls'}[kind]]+=1
  if kind=='mesh':self.mesh_result(i,r,g,returned)
  else:self.primitive_result(i,kind,r,g,returned)
  return r

 def mesh_result(self,i,r,grant,returned):
  w=r['inflated']['work'] if returned and r['inflated'] is not None else None;exact=returned and (w is None or w['workExact'])
  g=grant['work'];e=grant['retained']['heldAudits'];n=grant['retained']['lastMeshRows'];known=lambda k:0 if w is None else w[k]
  sr=known('sqrtRefinements');su=(0 if w is None else w['sqrtRefinementsUpper']) if returned else g['sqrtRefinements']
  bounds={'meshQueries':g['meshQueries'],'primitiveQueries':g['primitiveQueries'],'candidatesExamined':g['candidatesExamined'],'primitiveSqrtRefinements':min(g['sqrtRefinements'],e*n*512),'enclosureSqrtRefinements':min(g['sqrtRefinements'],e*1024),'meshSqrtLimitedRows':e*n,'enclosureSqrtCalls':2*e,'enclosureSqrtLimitedCalls':2*e}
  for k in HELD_COUNTERS:
   lower=known(k);upper=su if k=='sqrtRefinements' else lower if exact else bounds[k];add_counter(self.work['held'][k],lower,upper,exact)
  need(known('primitiveSqrtRefinements')+known('enclosureSqrtRefinements')==sr,'held known root decomposition')
  prop=int(returned and r['candidateEvaluated']);add_counter(self.work['propagationAttempts'],prop,prop if returned else 1,returned);self.work['bridgeCallsUpper']+=1
  actual=g.copy();actual.update(meshQueries=known('meshQueries') if exact else g['meshQueries'],primitiveQueries=known('primitiveQueries') if exact else g['primitiveQueries'],candidatesExamined=known('candidatesExamined') if exact else g['candidatesExamined'],sqrtRefinements=su,propagations=prop if returned else 1)
  self.settle(g,actual);sync(self.work)
  if not returned:self.work['exact']=False;raise Halt('not_certified','child_exception')
  key=self.keys[i];src={'body':self.s['bodies'][key['first']['ordinal']],'gravity':self.s['gravity'],'triangles':self.s['meshes'][key['second']['ordinal']]['triangles'],'horizon':self.s['horizon'],'settings':self.calls[(i,'mesh')]['used']}
  flight.verify_fixture(src,r,self.stats['flight'])
  self.stats['mathematicalChildrenVerified']['flight']+=1
  if not self.work['exact']:raise Halt('not_certified','unknown_work')
  if r['status']=='numerical_failure':raise Halt('numerical_failure','mesh_not_separated')
  safe=r['status']=='certified_separated';self.pairs[i].update(state='certified' if safe else 'not_certified',reason='none' if safe else 'mesh_not_separated')

 def primitive_result(self,i,kind,r,grant,returned):
  g=grant['work'];actual=g.copy()
  if not returned:
   if kind=='metric':
    add_counter(self.work['planeMetricValues'],0,g['planeMetricValues'],False);self.work['planeNormCallsUpper']+=self.calls[(i,kind)]['used']['maxEvaluations'];self.work['planeNormLoopIterationsUpper']+=g['planeNormLoopIterationsUpper']
   else:add_counter(self.work['boxValues'],0,g['boxValues'],False)
   if kind=='sphere':add_counter(self.work['sphereSqrtRefinements'],0,g['sqrtRefinements'],False)
   self.work['exact']=False;sync(self.work);raise Halt('not_certified','child_exception')
  w=r['work'];key=self.keys[i];used=self.calls[(i,kind)]['used'];a,ba=self.motion(key['first']['ordinal'],kind=='metric')
  if kind=='metric':
   p=self.s['planes'][key['second']['ordinal']];inp={'kind':'sphere_plane','sphere':a,'plane':{'normal':p['normal'],'offset':p['offset']}};module=metric
  elif kind=='box':
   p=self.s['planes'][key['second']['ordinal']];inp={'sphere':a,'plane':{'normal':p['normal'],'offset':p['offset']},'positionError':ba,'contactMargin':self.settings['contactMargin']};module=plane
  else:
   b,bb=self.motion(key['second']['ordinal']);inp={'first':a,'second':b,'firstPositionError':ba,'secondPositionError':bb,'contactMargin':self.settings['contactMargin']};module=sphere
  module.verify_fixture({'input':inp,'horizon':self.s['horizon'],'settings':used},r,self.stats[{'metric':'metric','box':'planeBox','sphere':'sphereBox'}[kind]])
  self.stats['mathematicalChildrenVerified'][{'metric':'metric','box':'planeBox','sphere':'sphereBox'}[kind]]+=1
  if kind=='metric':
   actual['planeMetricValues']=w['valueCallsAttempted'];add_counter(self.work['planeMetricValues'],actual['planeMetricValues']);self.work['planeNormCallsUpper']+=w['planeNormCallsUpper'];self.work['planeNormLoopIterationsUpper']+=w['planeNormLoopIterationsUpper']
  else:actual['boxValues']=w['valueCallsAttempted'];add_counter(self.work['boxValues'],actual['boxValues'])
  if kind=='sphere':
   actual['sqrtRefinements']=w['sqrtRefinementsUpper'];add_counter(self.work['sphereSqrtRefinements'],w['sqrtRefinementsReturned'],w['sqrtRefinementsUpper'],w['exact']);self.work['sphereRootResultsReturned']+=w['sqrtResultsReturned'];self.work['sphereRootLimitedReturns']+=w['sqrtLimitedReturns']
  self.settle(g,actual);sync(self.work)
  if kind=='sphere' and not w['exact']:raise Halt('not_certified','unknown_work')
  if w['valueCallsAttempted']!=w['valueCallsReturned']:self.work['exact']=False;raise Halt('not_certified','child_exception')
  if kind=='sphere':self.pairs[i].update(state='certified' if r['status']=='certified' else 'not_certified',reason='none' if r['status']=='certified' else 'box_not_separated')

 def run(self):
  status=reason=None;failure=None
  try:
   for i in sorted((j for j,b in enumerate(self.s['bodies']) if not b['isStatic']),key=lambda j:self.s['bodies'][j]['id']):
    self.bodies[i]['state']='pending';seed=self.bodies[i]['seedPairOrdinal'];self.execute(seed,'mesh');self.bodies[i]['state']='ready' if self.pairs[seed]['state']=='certified' else 'failed'
   for i,k in enumerate(self.keys):
    if k['kind']!='body_mesh' or self.calls[(i,'mesh')]['state']!='unexamined':continue
    r=self.execute(i,'mesh');body=k['first']['ordinal']
    if self.pairs[i]['state']=='certified' and self.bodies[body]['state']=='ready':
     seed=self.calls[(self.bodies[body]['seedPairOrdinal'],'mesh')]['actual']['result']
     for key in ['tube','endpoint','candidate']:equal(seed[key],r[key],'same-body flight bits across independent meshes: '+key)
   for i,k in enumerate(self.keys):
    if k['kind']=='body_mesh':continue
    self.active=i
    if not self.ready(k['first']['ordinal']) or (k['kind']=='body_body' and not self.ready(k['second']['ordinal'])):
     self.pairs[i].update(state='dependency_failed',reason='dependency_failed');continue
    if k['kind']=='body_body':self.execute(i,'sphere')
    else:
     m=self.execute(i,'metric');b=self.execute(i,'box');safe=m['status']==b['status']=='certified'
     self.pairs[i].update(state='certified' if safe else 'not_certified',reason='metric_not_separated' if m['status']!='certified' else 'box_not_separated' if b['status']!='certified' else 'none')
   self.active=None;sync(self.work)
   all_safe=self.work['exact'] and all(p['state']=='certified' for p in self.pairs) and all(b['state'] in {'ready','static_copy'} for b in self.bodies)
   status='certified_separated' if all_safe else 'not_certified';reason='none' if all_safe else next((p['reason'] for p in self.pairs if p['state']!='certified'),'seed_failed')
  except Halt as stop:
   status,reason=stop.status,stop.reason
   if self.active is not None:
    p=self.pairs[self.active];p['reason']=reason
    if p['executionOrdinal'] is not None:p['state']='not_certified'
    failure={'preparation':None,'bodyOrdinal':None,'pairOrdinal':self.active}
   for body in self.bodies:
    if body['state']=='pending':body['state']='unexamined' if self.calls[(body['seedPairOrdinal'],'mesh')]['state']=='unexamined' else 'failed'
   for i,p in enumerate(self.pairs):
    k=self.keys[i]
    if p['state']=='unexamined' and k['kind']!='body_mesh' and (self.bodies[k['first']['ordinal']]['state']=='failed' or (k['kind']=='body_body' and self.bodies[k['second']['ordinal']]['state']=='failed')):p.update(state='dependency_failed',reason='dependency_failed')
  need((self.r['status'],self.r['reason'])==(status,reason),'terminal status/reason from complete ordered transcript')
  equal(failure,self.r['failure'],'active typed-pair failure')
  for body in self.r['bodies']:
   fields(body,{'bodyOrdinal','isStatic','state','seedPairOrdinal'},'BodyRecord');uint(body['bodyOrdinal'],7,'body ordinal');need(type(body['isStatic']) is bool and type(body['state']) is str,'seed field types')
   if body['seedPairOrdinal'] is not None:uint(body['seedPairOrdinal'],255,'seed pair')
  equal(self.bodies,self.r['bodies'],'original body seed states/ownership')
  for i,p in enumerate(self.pairs):equal(p,{k:self.r['pairs'][i][k] for k in p},'whole stable typed pair metadata')
  for (i,kind),c in self.calls.items():
   a=c['actual'];equal(c['used'],a['usedSettings'],'only visible primitive E may differ');equal(c['grant'],a['grant'],'full computed Grant')
   equal(c['granted'],a['granted'],'accepted grant');equal(c['ordinal'],a['attemptOrdinal'],'global attempt order');equal(c['state'],a['state'],'all call states')
   if c['state']=='unexamined':need(a['result'] is None,'unqueried payload never filled');omission(a['messages'],0)
  equal(self.res,self.r['reservation'],'retained request/no-refund and cumulative/settled work');equal(self.work,self.r['work'],'whole observed/unknown ledger')
  if status=='certified_separated':
   candidates=[copy.deepcopy(b) if b['isStatic'] else self.calls[(self.bodies[i]['seedPairOrdinal'],'mesh')]['actual']['result']['candidate'] for i,b in enumerate(self.s['bodies'])]
   equal(candidates,self.r['candidateBodies'],'all-or-none owned candidates in original order with static/load bits preserved');self.stats['candidateBodies']+=len(candidates);self.stats['certifiedSeparated']+=1
  else:need(self.r['candidateBodies'] is None,'no partial candidate on failure');self.stats['notCertified']+=1
  self.stats['reducedPrimitiveGrants']+=sum(c['granted'] and c['used'].get('maxEvaluations',0)<c['actual']['requestedSettings'].get('maxEvaluations',0) for (_,k),c in self.calls.items() if k!='mesh')
  self.stats['knownRootRefinements']+=self.work['sqrtRefinements']['known']

def verify(data):
 fields(data,{'schema','kind','layoutSizes','fixtures'},'World guard fixture envelope')
 need(type(data['schema']) is int and data['schema']==1 and data['kind']=='world-static-mesh-flight-guard-fixtures','schema/kind');layout_shape(data['layoutSizes'])
 need(EXPECTED_FIXTURE_COUNT is not None and EXPECTED_INPUT_FINGERPRINT is not None,'actual complete World corpus not frozen')
 need(type(data['fixtures']) is list and len(data['fixtures'])==EXPECTED_FIXTURE_COUNT,'whole fixed input corpus')
 fp=input_fingerprint(data['fixtures']);need(fp==EXPECTED_INPUT_FINGERPRINT,'full input type/bits/array order, label-independent multiset')
 stats=new_stats(len(data['fixtures']));names=set();identities=set()
 for f in data['fixtures']:
  fields(f,{'name','input','result'},'full fixture');need(type(f['name']) is str and f['name'] and f['name'] not in names,'unique labels');names.add(f['name'])
  verify_fixture(f['input'],f['result'],data['layoutSizes'],stats);identities.add(f['result']['binding']['buildId'])
 need(len(identities)==1,'one observed bound configuration per actual corpus, not executable hash')
 return {'status':'PASS',**stats,'inputFingerprint':fp,'scope':'Independent owned preparation, complete typed inputs/seeds/radius/B identity, execution order, requested capacity/no-storage-refund, settled known/upper work and whole candidate composition. Protected independent Fraction references validate real child results: six box coordinates use exact quadratic extrema+B; downstream recorded-box integer-RN/root enclosure is separate. Message byte provenance/actual public value bits and actual CPU instruction/compiler binding are separate Native/artifact gates. Same-run sizeof metadata is observational, not heap/stack/allocator bound. No World advance/response, actual fault injection or cross-compiler whole-output bit parity.'}

if __name__=='__main__':
 need(__debug__,'run World guard reference without Python -O')
 need(len(sys.argv)==2,'Usage: verify-world-static-mesh-flight-guard.py native-fixtures.json')
 print(json.dumps(verify(load(sys.argv[1]))))
