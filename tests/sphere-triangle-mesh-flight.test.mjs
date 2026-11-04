import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';

// Synthetic transport/ownership tests, not fresh C++/WASM or fault injection.
// Read each frozen file once, retaining only this bounded diagnostic subset.
const selected=new Set(['static-face','linear-entry-quarter','analytic-chord-false-safe','analytic-edge-quartic','analytic-vertex-quartic',
  'actual-256-audits-128-leaves','breadth-frontier-budget','actual-64-entry-all-conservative-ids','depth-budget-zero',
  'initial-strict-negative','initial-boundary','sqrt-reservation-before-mesh','middle-degenerate-later-row-preserved',
  'duplicate-source-id','surface-budget-before-query','signed-source-zero','safe-face-held-rotation','rotation-increment-failure',
  'invalid-body-inertia','invalid-body-quaternion','invalid-body-material','static-body-unsupported','inflated-radius-over-domain',
  'candidate-final-validation-failure','coarse-inflated-window-not-original-entry','non-dyadic-global-seconds']);
const key=(c,n)=>c+'/'+n;
const folder='../reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-final-002/native-exchange/';
const packets=new Map(JSON.parse(await readFile(new URL(folder+'packets.json',import.meta.url),'utf8')).fixtures
  .filter(f=>selected.has(f.name)||selected.has(f.name.replace(/^held-input-/,'')))
  .filter(f=>f.exchangeStatus===0).map(f=>[key(f.cohort,f.name),{mode:f.mode,input:f.input,summary:f.summary,
    packets:f.packets.map(p=>({kind:p.kind,index:p.index,values:p.values})),lastMeshSummary:f.lastMeshSummary,
    lastMeshRows:f.lastMeshRows.map(r=>({rowOrdinal:r.rowOrdinal,packet:r.packet,candidates:r.candidates}))}]));
const models=new Map(JSON.parse(await readFile(new URL(folder+'decoded-models.json',import.meta.url),'utf8')).fixtures
  .filter(f=>packets.has(key(f.cohort,f.name))).map(f=>[key(f.cohort,f.name),f]));
const prefix='_pp_sim_sphere_triangle_mesh_flight';
const names=['begin','append','query','record','last_mesh','candidate'].map(s=>prefix+'_'+s);
const clone=x=>structuredClone(x);
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const primitiveStatuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const primitiveReasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const ccdFailures=['none','invalid_input','initial_contact','query_unresolved','event_budget','segment_budget','query_budget','root_budget','geometric_guard','propagation_failure','solver_failure','sustained_contact_required','numerical_failure'];
function heldEnums(r){
  for(const a of r.audits){if(a.meshStatus!==null)a.meshStatus=meshStatuses[a.meshStatus];if(a.meshReason!==null)a.meshReason=meshReasons[a.meshReason];}
  if(r.lastMesh){const m=r.lastMesh;m.status=meshStatuses[m.status];m.reason=meshReasons[m.reason];
    for(const row of m.rows)if(row.query){const q=row.query;q.status=primitiveStatuses[q.status];q.reason=primitiveReasons[q.reason];
      if(q.geometry)q.geometry.relation=['separated','penetrating','touching','boundary_unresolved'][q.geometry.relation];
      for(const c of q.candidates){c.feature=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'][c.feature];c.disposition=['retained','outside_simplex','kkt_violated'][c.disposition];}}}
  return r;
}
function fixture(name='static-face',cohort='held'){
  const k=key(cohort,name),raw=clone(packets.get(k)),model=clone(models.get(k));assert.ok(raw&&model,'Frozen accepted fixture '+k);
  const result=model.mode===0?heldEnums(model.result):model.result;
  if(model.mode===1){if(result.inflated)heldEnums(result.inflated);if(result.flightFailure!==null)result.flightFailure=ccdFailures[result.flightFailure];}
  result.originalInput={...clone(model.input),echo:clone(raw.input)};
  return {raw,input:model.input,expected:result,mode:model.mode};
}
const invoke=(r,f)=>f.mode===0?r.querySphereTriangleMeshHeldLoad(f.input.sphere,f.input.triangles,f.input.horizon,f.input.settings)
  :r.querySphereTriangleMeshFreeFlightGuard(f.input.body,f.input.gravity,f.input.triangles,f.input.horizon,f.input.settings);
const rec=(f,kind,index=0)=>{const p=f.raw.packets.find(p=>p.kind===kind&&p.index===index);assert.ok(p,'Missing record '+kind+':'+index);return p.values;};
function replay(f,{memory=false,prototype=false}={}){
  let active=f,output=[],growths=0;
  const calls={writes:0,begins:0,appends:0,queries:0,getters:0};
  const mem=new WebAssembly.Memory({initial:2,maximum:64});
  const publish=values=>{assert.ok(values,'Mock requested absent packet');if(memory){mem.grow(1);growths++;native.HEAPU8=new Uint8Array(mem.buffer);native.HEAPF64=new Float64Array(mem.buffer);native.HEAPF64.set(values,512);}output=values;};
  const methods={_pp_sim_api_version(){assert.equal(this,native);return 1;},
    [names[0]](mode,n){assert.equal(this,native);assert.equal(mode,active.mode);assert.equal(n,active.input.triangles.length);calls.begins++;return 0;},
    [names[1]](){assert.equal(this,native);calls.appends++;return 0;},
    [names[2]](mode,count){assert.equal(this,native);assert.equal(mode,active.mode);assert.equal(count,mode?48:32);calls.queries++;publish(active.raw.summary);return 0;},
    [names[3]](mode,kind,index){assert.equal(this,native);assert.equal(mode,active.mode);calls.getters++;publish(rec(active,kind,index));return 0;},
    [names[4]](mode,part,index){assert.equal(this,native);assert.equal(mode,active.mode);calls.getters++;publish(part===0?active.raw.lastMeshSummary:active.raw.lastMeshRows.find(r=>r.rowOrdinal===index)?.packet);return 0;},
    [names[5]](mode,row,index){assert.equal(this,native);assert.equal(mode,active.mode);calls.getters++;publish(active.raw.lastMeshRows.find(r=>r.rowOrdinal===row)?.candidates[index]);return 0;},
    _pp_sim_input_f64_capacity(){assert.equal(this,native);return 64;},_pp_sim_input_f64_ptr(){assert.equal(this,native);return 0;},
    _pp_sim_output_f64_ptr(){assert.equal(this,native);return 4096;},_pp_sim_output_count(){assert.equal(this,native);return output.length;}};
  const native=prototype?Object.create(methods):{...methods};native.HEAPU8=new Uint8Array(mem.buffer);native.HEAPF64=new Float64Array(mem.buffer);
  const r=new SimulationRuntime(native,{},0,0);
  if(memory){const real=r.inputF64;r.inputF64=function(values){calls.writes++;return real.call(this,values);};}
  else{r.inputF64=values=>{calls.writes++;return values.length;};r.output=()=>output.slice();}
  for(const method of ['querySphereTriangle','querySphereTriangleMesh','querySphereTriangleMeshTrajectory','querySphereTriangleMeshEntry'])r[method]=()=>assert.fail('No '+method+' fallback');
  return {r,native,calls,activate(next){active=next;},get growths(){return growths;},get buffer(){return mem.buffer;},get output(){return output;}};
}
const zeros={writes:0,begins:0,appends:0,queries:0,getters:0};
function rejectEdits(name,edits,cohort='held'){
  for(const [label,edit] of edits){const f=fixture(name,cohort),fake=replay(f),old=invoke(fake.r,f),saved=clone(old);edit(f);
    assert.throws(()=>invoke(fake.r,f),undefined,label);assert.deepEqual(old,saved,'Prior owned DTO: '+label);}
}
const change=(label,kind,index,edit)=>[label,f=>edit(rec(f,kind,index))];

test('flight both methods require all six capabilities before any input accessor or scratch/stage write, including old86',()=>{
  for(const mode of [0,1])for(const missing of [...names,'all']){
    const native={_pp_sim_api_version:()=>1,...Object.fromEntries(names.map(n=>[n,()=>assert.fail('Missing capability called '+n)]))};
    if(missing==='all')for(const n of names)delete native[n];else delete native[missing];
    const r=new SimulationRuntime(native,{},0,0);r.inputF64=()=>assert.fail('Missing capability wrote input');
    const bad=new Proxy({},{get(){assert.fail('Missing capability read caller input');}});
    assert.throws(()=>mode?r.querySphereTriangleMeshFreeFlightGuard(bad,bad,bad,bad,bad):r.querySphereTriangleMeshHeldLoad(bad,bad,bad,bad),/unavailable/i);
  }
});

test('bounded frozen Native packet subset restores all DTO keys and enum values without geometric fallback',()=>{
  for(const [k] of packets){const at=k.indexOf('/'),f=fixture(k.slice(at+1),k.slice(0,at));assert.deepEqual(invoke(replay(f).r,f),f.expected,k);}
});

test('held global seconds, strict initial/prefix, negative witness, closed islands and unqueried tail remain distinct',()=>{
  const f=fixture('linear-entry-quarter'),r=invoke(replay(f).r,f);
  assert.equal(r.status,'entry_window');assert.ok(r.initial.lowerGapCertificate[0]>0);
  assert.ok(r.window.timeBounds[0]<f.input.horizon/4&&r.window.timeBounds[1]>f.input.horizon/4);
  assert.ok(r.window.timeWidth[1]<=f.input.settings.timeTolerance);assert.deepEqual(r.safePrefix,[0,r.window.timeBounds[0]]);
  assert.equal(r.bestWitness.time,r.window.timeBounds[1]);assert.ok(r.bestWitness.upperGapCertificate[1]<0);
  assert.ok(r.frontier.some(c=>c.timeBounds[0]>=r.bestWitness.time));assert.equal('parameter' in r.window,false);
  assert.equal('toi' in r,false);assert.equal('normal' in r,false);
});

test('both modes retain final256audit128leaf/partition127frontier64source/all448candidates without truncation',()=>{
  for(const [cohort,pre] of [['held',''],['guard','held-input-']]){
    let f=fixture(pre+'actual-256-audits-128-leaves',cohort),r=invoke(replay(f).r,f);if(r.inflated)r=r.inflated;
    assert.equal(r.audits.length,256);assert.equal(r.certifiedLeaves.length,128);assert.equal(r.partition.length,128);
    assert.equal(r.certifiedLeaves.at(-1).auditIndex,255);assert.equal(r.partition.at(-1).cell.timeBounds[1],f.input.horizon);
    f=fixture(pre+'breadth-frontier-budget',cohort);r=invoke(replay(f).r,f);if(r.inflated)r=r.inflated;assert.equal(r.frontier.length,127);assert.equal(r.partition.length,128);
    f=fixture(pre+'actual-64-entry-all-conservative-ids',cohort);r=invoke(replay(f).r,f);if(r.inflated)r=r.inflated;
    assert.equal(r.candidateSurfaceIds.length,64);assert.equal(r.lastMesh.rows.length,64);assert.equal(r.lastMesh.rows.reduce((n,row)=>n+row.query.candidates.length,0),448);
  }
});

test('guard original sphere radius, inflated radius, full candidate and failure-only nested window retain separate ownership',()=>{
  const f=fixture('safe-face-held-rotation','guard'),r=invoke(replay(f).r,f);
  assert.equal(r.status,'certified_separated');assert.equal(r.snapshot.body.radius,f.input.body.radius);
  assert.equal(r.inflated.snapshot.input.radius,r.tube.guardRadius);assert.ok(r.tube.guardRadius>=f.input.body.radius);
  assert.deepEqual(r.candidate.force,f.input.body.force);assert.deepEqual(r.candidate.torque,f.input.body.torque);
  const e=fixture('coarse-inflated-window-not-original-entry','supplemental'),q=invoke(replay(e).r,e);
  assert.equal(q.status,'not_certified');assert.equal(q.inflated.status,'entry_window');assert.equal(q.candidate,null);
});

test('invalid captured full body and static body remain model DTOs, while successful candidate validation stays separate',()=>{
  for(const name of ['invalid-body-inertia','invalid-body-quaternion','invalid-body-material','static-body-unsupported']){
    const f=fixture(name,'guard'),r=invoke(replay(f).r,f);assert.deepEqual(r.worldBody.body,f.input.body);assert.equal(r.candidate,null);
  }
});

test('finite invalid model settings and domains pass unchanged while host shape/type failures write nothing',()=>{
  for(const mode of [0,1]){
    const f=fixture(mode?'safe-face-held-rotation':'static-face',mode?'guard':'held');
    const bads=[x=>x.input.horizon=NaN,x=>x.input.horizon=true,x=>x.input.triangles=Array(65).fill(x.input.triangles[0]),
      x=>x.input.triangles[0].id=0,x=>x.input.triangles[0].id=2**53,x=>delete x.input.triangles[0].vertices[2][1],
      x=>x.input.triangles[0].vertices[2][1]=Infinity,x=>x.input.settings=null,
      x=>(mode?x.input.settings.heldLoad:x.input.settings).maxDepth=.5,
      x=>(mode?x.input.settings.heldLoad:x.input.settings).mesh.primitive.sqrtRefinements=2**32];
    if(mode)bads.push(x=>delete x.input.body.torque,x=>x.input.body.isStatic=0,x=>x.input.body.orientation=[0,0,1],x=>x.input.body.material.restitution='0');
    else bads.push(x=>x.input.sphere.position=new DataView(new ArrayBuffer(24)),x=>x.input.sphere.mass='1',x=>x.input.sphere.gravity=[0,,0]);
    for(const edit of bads){const x=clone(f),fake=replay(x);edit(x);assert.throws(()=>invoke(fake.r,x));assert.deepEqual(fake.calls,zeros);}
  }
});

test('undefined settings use explicit defaults but null numeric and nested settings are rejected before writes',()=>{
  for(const mode of [0,1]){
    const base=()=>fixture(mode?'safe-face-held-rotation':'static-face',mode?'guard':'held');
    for(const settings of [undefined,{},mode?{heldLoad:undefined,maxAngularIncrement:undefined}:{mesh:undefined,maxDepth:undefined}]){
      const f=base(),fake=replay(f);f.input.settings=settings;assert.deepEqual(invoke(fake.r,f),f.expected);
    }
    const edits=[x=>x.input.settings=null,x=>(mode?x.input.settings.heldLoad:x.input.settings).mesh=null,
      x=>(mode?x.input.settings.heldLoad:x.input.settings).mesh.primitive=null];
    for(const field of ['timeTolerance','maxEvaluations','maxLeaves','maxDepth','enclosureSqrtRefinements','maxTotalSqrtRefinements'])edits.push(x=>(mode?x.input.settings.heldLoad:x.input.settings)[field]=null);
    for(const field of ['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared'])edits.push(x=>(mode?x.input.settings.heldLoad:x.input.settings).mesh.primitive[field]=null);
    edits.push(x=>(mode?x.input.settings.heldLoad:x.input.settings).mesh.maxSurfaces=null);
    if(mode)edits.push(x=>x.input.settings.heldLoad=null,x=>x.input.settings.maxAngularIncrement=null);
    for(const edit of edits){const f=base(),fake=replay(f);edit(f);assert.throws(()=>invoke(fake.r,f));assert.deepEqual(fake.calls,zeros);}
  }
});

function onceTree(value,label,counts){
  if(value===null||typeof value!=='object')return value;
  const children=new Map(Object.keys(value).map(k=>[k,onceTree(value[k],label+'.'+k,counts)]));
  return new Proxy(value,{get(t,k,r){if(k===Symbol.iterator)return ()=>assert.fail('Caller iterator read '+label);
    if(k==='length'&&Array.isArray(t)||typeof k==='string'&&Object.hasOwn(t,k)){
      const at=label+'.'+String(k);counts.set(at,(counts.get(at)??0)+1);assert.equal(counts.get(at),1,'Repeated caller read '+at);
      return children.has(k)?children.get(k):Reflect.get(t,k,r);
    }return Reflect.get(t,k,r);}});
}
test('every input field hierarchy array length and numeric component is captured once before Native mutates caller state',()=>{
  for(const [cohort,name] of [['held','static-face'],['guard','safe-face-held-rotation']]){
    const f=fixture(name,cohort),plain=f.input,counts=new Map(),wrapped=onceTree(plain,'input',counts),fake=replay(f),begin=fake.native[names[0]];
    fake.native[names[0]]=function(...a){plain.triangles[0].id=999;plain.triangles[0].vertices[0].fill(999);if(plain.sphere)plain.sphere.position.fill(999);else plain.body.orientation.fill(999);return Reflect.apply(begin,this,a);};
    const g={...f,input:wrapped};assert.deepEqual(invoke(fake.r,g),f.expected);
    for(const [at,n] of counts)assert.equal(n,1,at);
    const expected=[];function visit(v,p){if(v&&typeof v==='object'){if(Array.isArray(v))expected.push(p+'.length');for(const k of Object.keys(v)){expected.push(p+'.'+k);visit(v[k],p+'.'+k);}}}visit(f.expected.originalInput,'input');
    for(const at of expected.filter(k=>!k.startsWith('input.echo')&&!['input.sphere','input.body','input.settings','input.gravity','input.triangles','input.horizon'].includes(k)))assert.equal(counts.get(at),1,at);
  }
});

test('bad-then-valid and valid-then-bad getters cannot change validated values between preflight and encoding',()=>{
  for(const mode of [0,1])for(const initialGood of [false,true]){
    const f=fixture(mode?'safe-face-held-rotation':'static-face',mode?'guard':'held'),fake=replay(f);let reads=0;
    Object.defineProperty(f.input.triangles[0],'id',{get(){return ++reads===1?(initialGood?37:0):(initialGood?0:37);}});
    if(initialGood)assert.deepEqual(invoke(fake.r,f),f.expected);else{assert.throws(()=>invoke(fake.r,f));assert.deepEqual(fake.calls,zeros);}assert.equal(reads,1);
  }
});

test('dense typed vectors accepted, sparse arrays/DataView/BigInt/toArray aliases and invalid Proxy lengths rejected prewrite',()=>{
  const f=fixture(),x=clone(f);x.input.sphere.position=new Float64Array(x.input.sphere.position);x.input.sphere.velocity=new Float32Array(x.input.sphere.velocity);
  assert.deepEqual(invoke(replay(x).r,x),f.expected);
  for(const value of [[1,,1],new DataView(new ArrayBuffer(24)),new BigInt64Array(3),{toArray(){assert.fail('Implicit toArray called');}}]){
    const q=fixture(),fake=replay(q);q.input.sphere.position=value;assert.throws(()=>invoke(fake.r,q));assert.deepEqual(fake.calls,zeros);
  }
  for(const length of [NaN,Infinity,-1,1.5,2**32,true]){const q=fixture(),fake=replay(q),v=q.input.sphere.position;
    q.input.sphere.position=new Proxy(v,{get(t,k,r){return k==='length'?length:Reflect.get(t,k,r);}});assert.throws(()=>invoke(fake.r,q));assert.deepEqual(fake.calls,zeros);}
});

test('caller, originalInput, snapshot, world body, inflated sphere, candidate, source row and prior/next DTO are separately owned',()=>{
  for(const [cohort,name] of [['held','static-face'],['guard','safe-face-held-rotation']]){
    const f=fixture(name,cohort),fake=replay(f),r=invoke(fake.r,f),saved=clone(r);f.input.triangles[0].vertices[0][0]=999;
    if(f.mode)f.input.body.position[0]=999;else f.input.sphere.position[0]=999;assert.deepEqual(r,saved);
    const next=fixture('linear-entry-quarter');fake.activate(next);invoke(fake.r,next);assert.deepEqual(r,saved);
    r.originalInput.triangles[0].vertices[0][0]=123;r.originalInput.echo[0]=123;assert.deepEqual(r.snapshot,saved.snapshot);
    if(f.mode){r.worldBody.body.position[0]=321;assert.deepEqual(r.snapshot,saved.snapshot);assert.deepEqual(r.candidate,saved.candidate);r.candidate.force[0]=123;assert.deepEqual(r.inflated,saved.inflated);}
    const h=f.mode?r.inflated:r,old=f.mode?saved.inflated:saved;h.snapshot.triangles[0].vertices[0][0]=789;assert.deepEqual(h.lastMesh,old.lastMesh);
    for(const p of f.raw.packets)p.values.fill(0);for(const row of f.raw.lastMeshRows){row.packet?.fill(0);row.candidates.forEach(c=>c.fill(0));}
    assert.deepEqual(h.audits,old.audits);assert.deepEqual(h.lastMesh,old.lastMesh);
  }
});

test('signed source and unused KKT zeros survive, integer setting negative zero remains original while snapshot is canonical',()=>{
  const f=fixture('depth-budget-zero');f.input.settings.maxDepth=-0;f.raw.input[26]=-0;rec(f,0)[26]=-0;
  const r=invoke(replay(f).r,f);assert.ok(Object.is(r.originalInput.settings.maxDepth,-0));assert.ok(Object.is(r.originalInput.echo[26],-0));assert.ok(Object.is(r.snapshot.settings.maxDepth,0));
  assert.ok(Object.is(r.originalInput.triangles[0].vertices[0][0],-0));assert.ok(Object.is(r.lastMesh.rows[0].query.candidates[0].kkt[0][0],-0));
});

test('prototype-defined Native methods keep their exact original receiver and runtime/native/prototype remain unchanged',()=>{
  const f=fixture('safe-face-held-rotation','guard'),fake=replay(f,{prototype:true}),native=fake.r.native,proto=Object.getPrototypeOf(native),runtimeProto=Object.getPrototypeOf(fake.r),methods=names.map(n=>native[n]);
  assert.deepEqual(invoke(fake.r,f),f.expected);assert.equal(fake.r.native,native);assert.equal(Object.getPrototypeOf(native),proto);assert.equal(Object.getPrototypeOf(fake.r),runtimeProto);
  assert.deepEqual(names.map(n=>native[n]),methods);
});

test('simulated memory growth forces fresh views and immediate owned packet copies without claiming actual allocator usage',()=>{
  const f=fixture('safe-face-held-rotation','guard'),fake=replay(f,{memory:true}),first=fake.buffer;
  const r=invoke(fake.r,f),saved=clone(r);assert.deepEqual(r,f.expected);assert.ok(fake.growths>10);assert.notEqual(fake.buffer,first);
  fake.native.HEAPF64.fill(999);assert.deepEqual(r,saved);
});

test('host stage/getter refusal and postcommit decoder throw preserve old JS DTO without retry or claimed Native rollback',()=>{
  for(const n of names){const f=fixture(),fake=replay(f),old=invoke(fake.r,f),saved=clone(old),marker=new Error('Host '+n),original=fake.native[n];
    fake.native[n]=()=>17;fake.r.check=code=>{if(code!==0)throw marker;};assert.throws(()=>invoke(fake.r,f),e=>e===marker);assert.deepEqual(old,saved);
    fake.native[n]=original;assert.deepEqual(invoke(fake.r,f),saved);
  }
  const f=fixture(),fake=replay(f),r=invoke(fake.r,f),saved=clone(r);f.raw.summary[23]=-0;const before=fake.calls.queries;
  assert.throws(()=>invoke(fake.r,f));assert.equal(fake.calls.queries,before+1);assert.deepEqual(r,saved);
});

test('loader sync accessor throw and rejected load remain distinct from synchronous decoder-aftercommit errors',async()=>{
  const marker=new Error('Loader accessor');assert.throws(()=>loadSimulationRuntime({get wasmBytes(){throw marker;}}),e=>e===marker);
  await assert.rejects(loadSimulationRuntime({wasmBytes:[]}));await assert.rejects(loadSimulationRuntime({wasmBytes:new Uint8Array()}));
  const f=fixture(),fake=replay(f);f.raw.summary[0]=2;assert.throws(()=>invoke(fake.r,f));assert.equal(fake.calls.queries,1);
});

test('summary24 mode/status/reason/count/optional and strict positive-zero metadata fail closed in both modes',()=>{
  for(const [cohort,name] of [['held','static-face'],['guard','safe-face-held-rotation']]){
    const edits=[['short',a=>a.pop()],['extra',a=>a.push(0)],['hole',a=>delete a[0]],['nan',a=>a[2]=NaN],['bool',a=>a[3]=true],['string',a=>a[1]='0'],
      ['mode',a=>a[0]=1-a[0]],['status',a=>a[1]=99],['reason',a=>a[2]=99],['sourceCount',a=>a[3]++],['snapshot',a=>a[4]=0],
      ['invalid flag',a=>a[5]=2],['absent failed payload',a=>a[6]=1],['invalid candidate flag',a=>a[14]=2],['held presence',a=>a[15]=0],
      ['padding',a=>a[23]=1],['signed padding',a=>a[16]=-0],['negativezero reason',a=>a[2]=-0]];
    if(cohort==='guard')edits.push(['missing captured body',a=>a[7]=0],['lost tube',a=>a[8]=0],['fake flight failure',a=>a[9]=1],['lost candidate evaluation',a=>a[11]=0],['lost endpoint',a=>a[12]=0],['lost inflated',a=>a[13]=0],['lost candidate',a=>a[14]=0],['negativezero completed status',a=>a[1]=-0]);
    else edits.push(['held fake body',a=>a[7]=1],['held fake tube',a=>a[8]=1],['held fake endpoint',a=>a[12]=1],['held fake candidate',a=>a[14]=1]);
    rejectEdits(name,edits.map(([l,e])=>[l,f=>e(f.raw.summary)]),cohort);
  }
});

test('echo/source/snapshot/body/input linking rejects ownership corruption and nested-radius substitution',()=>{
  rejectEdits('static-face',[
    change('echo',0,0,a=>a[0]++),change('reserved -0',0,0,a=>a[31]=-0),change('snapshot original sphere',2,0,a=>a[1]++),
    change('heldInput',4,0,a=>a[14]++),change('source ordinal',1,0,a=>a[0]=1),change('sourceID',1,0,a=>a[1]=999),
    change('sourcebits',1,0,a=>a[2]=0),change('source queriedflag',1,0,a=>a[12]=0),change('source metadata -0',1,0,a=>a[0]=-0),
    change('source sparse',1,0,a=>delete a[5]),change('source tail',1,0,a=>a.push(0))]);
  rejectEdits('safe-face-held-rotation',[
    change('captured body field',5,0,a=>a[20]++),change('capturedbody pad',5,0,a=>a[31]=-0),
    change('snapshot body',2,0,a=>a[7]++),change('original radius to nested',4,0,a=>a[14]=.25),
    change('nested horizon',4,0,a=>a[15]*=2),change('nested source count',3,0,a=>a[2]++),
    change('nested worldBodyflag forbidden',3,0,a=>a[6]=1),change('candidate pad',8,0,a=>a[28]=-0),
    change('candidate force',8,0,a=>a[20]++),change('staticflag metadata -0',5,0,a=>a[1]=-0)],'guard');
});

test('heldHeader48 counts flags prefix link and Work delta arithmetic are audited before return',()=>{
  const edits=[['status',a=>a[0]=99],['reason',a=>a[1]=99],['snapshot',a=>a[3]=0],['worldbody forbidden',a=>a[6]=1],
    ['initialproof lost',a=>a[10]=0],['initialseparation',a=>a[11]=0],['leaves overflow',a=>a[12]=129],['partition overflow',a=>a[13]=129],
    ['frontier overflow',a=>a[14]=129],['audits overflow',a=>a[15]=257],['prefix loss',a=>a[16]=0],['prefixseconds',a=>a[18]=1],
    ['fake witness',a=>a[19]=1],['fake window',a=>a[20]=1],['fake ID',a=>a[21]=1],['fake current',a=>a[22]=1],
    ['lastmesh link',a=>a[25]=0],['partitioncount',a=>a[26]++],['depth',a=>a[27]++],['meshwork',a=>a[28]++],['sqrt work',a=>a[33]++],
    ['upper work',a=>a[34]++],['exactflag',a=>a[38]=2],['padding -0',a=>a[47]=-0],['short',a=>a.pop()],['hole',a=>delete a[20]]];
  rejectEdits('static-face',edits.map(([l,e])=>change(l,3,0,e)));
});

test('all audit optional/bounds/seconds/kind/outcome/Work/padding metadata are checked including initial point',()=>{
  const edits=[['ordinal',a=>a[0]=1],['kind',a=>a[1]=2],['initialkind',a=>a[1]=1],['initialcell',a=>a[3]=.01],['time',a=>a[5]=.01],
    ['outcome',a=>a[6]=99],['path loss',a=>a[7]=0],['pathinterval',a=>{a[8]=2;a[9]=1;}],['point loss',a=>a[14]=0],['anchor loss',a=>a[21]=0],
    ['meshquery loss',a=>a[25]=0],['meshstatus',a=>a[27]=6],['meshreason',a=>a[29]=12],['distance loss',a=>a[30]=0],
    ['displacement root loss',a=>a[39]=0],['error root loss',a=>a[42]=0],['clearance loss',a=>a[45]=0],['primitivework',a=>a[54]++],
    ['totalwork',a=>a[56]++],['exactflag',a=>a[61]=2],['signedpad',a=>a[62]=-0],['padding',a=>a[63]=1],['short',a=>a.pop()],['sparse',a=>delete a[8]],['nonfinite',a=>a[31]=Infinity]];
  rejectEdits('static-face',edits.map(([l,e])=>change(l,12,0,e)));
  rejectEdits('static-face',[change('regular masquerades initial',12,1,a=>a[1]=0),change('regularseconds',12,1,a=>a[5]=1)]);
  rejectEdits('sqrt-reservation-before-mesh',[change('absent optional payload -0',12,0,a=>a[31]=-0),change('false meshstatus',12,0,a=>a[26]=1)]);
});

test('acceleration whole-path and whole-velocity8 records reject ordinal/padding signs, holes and reversed bounds',()=>{
  for(const kind of [9,10,11])rejectEdits('static-face',[
    change('bounds ordinal '+kind,kind,0,a=>a[0]=1),change('bounds signedordinal '+kind,kind,0,a=>a[0]=-0),
    change('bounds signedpad '+kind,kind,0,a=>a[7]=-0),change('bounds reversed '+kind,kind,0,a=>a[1]=a[2]+1),
    change('bounds hole '+kind,kind,0,a=>delete a[4]),change('bounds tail '+kind,kind,0,a=>a.push(0))]);
});

test('partition coverage, BFS ordinal/audit links, frontier/current and islands cannot fabricate a safe prefix',()=>{
  rejectEdits('static-face',[
    change('leafhole',13,0,a=>a[1]/=2),change('leaf audit',13,0,a=>a[5]=0),change('leaf nonstrict',13,0,a=>a[3]=0),
    change('partition ordinal',14,0,a=>a[0]=1),change('partition hole',14,0,a=>a[2]/=2),change('partitionstate',14,0,a=>a[4]=0),
    change('partition audit loss',14,0,a=>a[5]=0),change('partition audit index',14,0,a=>a[6]=0),change('partition blockedreason',14,0,a=>a[7]=10)]);
  rejectEdits('linear-entry-quarter',[
    change('frontierordinal',15,0,a=>a[0]=1),change('frontierdepth',15,0,a=>a[3]++),change('frontierhole',15,0,a=>a[1]+=.001),
    change('celltime outofH',12,2,a=>a[3]=1),['BFS swapped audits',f=>{const a=rec(f,12,2),b=rec(f,12,3);[a[2],b[2]]=[b[2],a[2]];}]]);
  rejectEdits('sqrt-reservation-before-mesh',[change('initial current to entirecell',16,0,a=>a[2]=.0625)]);
});

test('initial witness window seconds/spatial fields and conservative IDs must belong to the actual proof records',()=>{
  rejectEdits('static-face',[change('initialordinal',17,0,a=>a[0]=1),change('initialaudit',17,0,a=>a[5]=1),change('initialnonstrict',17,0,a=>a[1]=0)]);
  rejectEdits('linear-entry-quarter',[
    change('windowordinal',19,0,a=>a[0]=1),change('windowL',19,0,a=>a[1]=0),change('windowU',19,0,a=>a[2]=1),change('windowwidth',19,0,a=>a[4]=1),
    change('window reversed width',19,0,a=>a[3]=a[4]+1),change('window pathlost',19,0,a=>a[5]=123),change('window L1 reversed',19,0,a=>a[11]=a[12]+1),change('windowaudit',19,0,a=>a[13]=0),
    change('witnessordinal',18,0,a=>a[0]=1),change('witnesstime',18,0,a=>a[4]=1),change('witnessbox',18,0,a=>a[5]=123),change('witnessanchor',18,0,a=>a[11]=123),
    change('witnessE',18,0,a=>a[14]=-1),change('witnessnonstrict',18,0,a=>a[16]=0),change('witnessaudit',18,0,a=>a[17]=0),
    change('IDordinal',20,0,a=>a[0]=1),change('foreignID',20,0,a=>a[1]=999)]);
});

test('tube24 endpoint40 and full candidate/body packets reject invalid metadata and radius/force/rotation links',()=>{
  rejectEdits('safe-face-held-rotation',[
    change('tube interval',6,0,a=>a[3]=a[4]+1),change('tube Bnegative',6,0,a=>a[15]=-1),
    change('tube radius mismatch',6,0,a=>a[17]=.25),change('tube signedpad',6,0,a=>a[23]=-0),change('tube bool',6,0,a=>a[16]=false),
    change('endpoint interval',7,0,a=>a[0]=a[1]+1),change('endpointL1',7,0,a=>a[30]=a[31]+1),change('endpoint false nominal',7,0,a=>a[32]=0),
    change('endpoint falseexact',7,0,a=>a[33]=0),change('endpoint falseL1',7,0,a=>a[34]=0),change('endpoint signedflag',7,0,a=>a[32]=-0),change('endpoint signedpad',7,0,a=>a[39]=-0),
    change('candidateID',8,0,a=>a[0]++),change('candidate invalidmass',8,0,a=>a[2]=0),change('candidate invalidq',8,0,a=>a[13]=2),
    change('candidate changedtorque',8,0,a=>a[23]++),change('candidateposition outside endpoint',8,0,a=>a[7]+=100)],'guard');
});

test('nested lastMesh row58/candidate13 strict +0 metadata is checked before reusing the older mesh decoder',()=>{
  const edits=[['meshstatus negativezero',f=>f.raw.lastMeshSummary[0]=-0],['meshpad negativezero',f=>f.raw.lastMeshSummary[23]=-0],
    ['mesh count',f=>f.raw.lastMeshSummary[3]++],['mesh work',f=>f.raw.lastMeshSummary[10]++]];
  for(const at of [0,1,2,3,4,5,6,7,8,9,10,13])edits.push(['row metadata sign '+at,f=>f.raw.lastMeshRows[0].packet[at]=-0]);
  for(const at of [0,1,2])edits.push(['candidate metadata sign '+at,f=>f.raw.lastMeshRows[0].candidates[0][at]=-0]);
  edits.push(['unused KKTsign',f=>f.raw.lastMeshRows[0].candidates[0][9]=0],['candidate sparse',f=>delete f.raw.lastMeshRows[0].candidates[0][3]],
    ['row sparse',f=>delete f.raw.lastMeshRows[0].packet[40]],['candidate tail',f=>f.raw.lastMeshRows[0].candidates[0].push(0)]);
  rejectEdits('static-face',edits);
});

test('nonarray/toArray/nonnumeric/sparse decoder outputs never become a partial successful DTO',()=>{
  for(const value of [null,{toArray(){assert.fail('Decoder called toArray');}},Array(24),Array(24).fill('0'),new BigInt64Array(24)]){
    const f=fixture(),fake=replay(f);fake.r.output=()=>value;assert.throws(()=>invoke(fake.r,f));assert.equal(fake.calls.queries,1);
  }
});

test('synthetic unreturned R enclosure root retains exactfalse known work and +512 reservation, not an entry or separation proof',()=>{
  // Artificial decoder shape; no Native allocation/environment fault was caused.
  const f=fixture('depth-budget-zero'),h=rec(f,3),a=rec(f,12,1),initial=rec(f,12,0),primitive=a[54];
  f.raw.summary[1]=6;f.raw.summary[2]=14;h[0]=6;h[1]=14;h[22]=1;
  rec(f,14)[4]=3;rec(f,14)[7]=14;f.raw.packets.push({kind:16,index:0,values:[0,0,f.input.horizon,0]});a[6]=6;
  for(const at of [39,42,45,48])a.fill(0,at,at+3);
  a[55]=0;a[56]=primitive;a[57]=primitive+512;a[59]=1;a[60]=0;a[61]=0;
  for(let i=0;i<10;++i)h[28+i]=initial[51+i]+a[51+i];h[38]=0;
  const r=invoke(replay(f).r,f);assert.equal(r.status,'numerical_failure');assert.equal(r.work.workExact,false);assert.equal(r.work.sqrtRefinementsUpper,r.work.sqrtRefinements+512);
  assert.equal(r.audits[1].displacementRoot,null);assert.equal(r.window,null);assert.equal(r.bestWitness,null);assert.deepEqual(r.safePrefix,[0,0]);assert.ok(r.lastMesh);
  for(const [label,edit] of [['claimexact',q=>rec(q,3)[38]=1],['strip upper',q=>rec(q,3)[34]=rec(q,3)[33]],
    ['strip delta',q=>rec(q,12,1)[57]=primitive],['consistentstrip',q=>{rec(q,3)[34]=rec(q,3)[33];rec(q,12,1)[57]=primitive;}],
    ['claimseparated',q=>{q.raw.summary[1]=1;rec(q,3)[0]=1;}]]){
    const q=clone(f);edit(q);assert.throws(()=>invoke(replay(q).r,q),undefined,label);
  }
});

test('synthetic unknown mesh work reserves N*512 without invented status/nearest or successful proofs',()=>{
  const f=fixture('sqrt-reservation-before-mesh'),h=rec(f,3),a=rec(f,12),reserved=512*f.input.triangles.length;
  f.input.settings.maxTotalSqrtRefinements=1000000;f.raw.input[28]=1000000;
  for(const kind of [0,2,4])rec(f,kind)[28]=1000000;
  f.raw.summary[1]=6;f.raw.summary[2]=15;h[0]=6;h[1]=15;h[28]=1;h[34]=reserved;h[38]=0;
  a[25]=1;a[51]=1;a[57]=reserved;a[61]=0;
  const r=invoke(replay(f).r,f);assert.equal(r.reason,'allocation_failure');assert.equal(r.work.meshQueries,1);assert.equal(r.work.workExact,false);
  assert.equal(r.work.sqrtRefinements,0);assert.equal(r.work.sqrtRefinementsUpper,reserved);assert.equal(r.lastMesh,null);assert.equal(r.audits[0].meshStatus,null);assert.equal(r.initial,null);assert.equal(r.safePrefix,null);
  const bad=clone(f);rec(bad,3)[34]=0;rec(bad,12)[57]=0;assert.throws(()=>invoke(replay(bad).r,bad));
});

test('synthetic pre-audit allocation and unsupported environment remain explicit partial diagnostics, never fresh Native faults',()=>{
  const f=fixture('sqrt-reservation-before-mesh'),h=rec(f,3);f.raw.summary[1]=6;f.raw.summary[2]=15;h[0]=6;h[1]=15;h[15]=0;
  f.raw.packets=f.raw.packets.filter(p=>p.kind!==12);const r=invoke(replay(f).r,f);
  assert.equal(r.status,'numerical_failure');assert.equal(r.audits.length,0);assert.equal(r.work.workExact,true);assert.deepEqual(r.current,{timeBounds:[0,0],depth:0});assert.equal(r.initial,null);
  const e=fixture('duplicate-source-id');e.raw.summary[1]=5;e.raw.summary[2]=16;e.raw.summary[5]=0;e.raw.summary[6]=0;
  rec(e,3)[0]=5;rec(e,3)[1]=16;rec(e,3)[4]=0;rec(e,3)[5]=0;
  const q=invoke(replay(e).r,e);assert.equal(q.status,'unsupported_environment');assert.equal(q.reason,'environment');assert.equal(q.snapshot,null);assert.equal(q.originalInput.triangles.length,2);
});
