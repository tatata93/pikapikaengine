import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';

const bytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:bytes});
// Frozen Native inputs and result fields are the reference. Enum spelling is
// projected here; no geometric/interval/kernel calculation is reproduced.
const corpus=JSON.parse(await readFile(new URL('../reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',import.meta.url),'utf8'));
const named=name=>{const f=corpus.fixtures.find(row=>row.name===name);assert.ok(f,'Missing original fixture '+name);return structuredClone(f.input);};
const flat=(id=37)=>({id,vertices:[[-0,0,0],[4,0,0],[0,0,4]]});
const base=()=>({start:[1,1,1],end:[1,1,1],radius:.25});
const prefix='_pp_sim_sphere_triangle_mesh_entry';
const names=[prefix+'_begin',prefix+'_append',prefix,prefix+'_record',prefix+'_last_mesh',prefix+'_candidate'];
const invoke=(r,input)=>r.querySphereTriangleMeshEntry({start:input.start,end:input.end,radius:input.radius},input.triangles,input.settings);
function wire(input){const s=input.settings,m=s.mesh,p=m.primitive;return [...input.start,...input.end,input.radius,m.maxSurfaces,
  p.maxCandidates,p.sqrtRefinements,p.maxTotalSqrtRefinements,p.maximumLocalWidth,p.maximumNormalWidth,p.minimumSineSquared,
  s.maxEvaluations,s.maxLeaves,s.maxDepth,s.enclosureSqrtRefinements,s.maxTotalSqrtRefinements,s.parameterTolerance,0,0,0,0];}
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const primitiveStatuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const primitiveReasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const features=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'];
const dispositions=['retained','outside_simplex','kkt_violated'];
function expected(fixture){
  const r=structuredClone(fixture.result);
  for(const a of r.audits){if(a.meshStatus!==null)a.meshStatus=meshStatuses[a.meshStatus];if(a.meshReason!==null)a.meshReason=meshReasons[a.meshReason];}
  if(r.lastMesh){const m=r.lastMesh;m.status=meshStatuses[m.status];m.reason=meshReasons[m.reason];
    for(const row of m.rows)if(row.query){const q=row.query;q.status=primitiveStatuses[q.status];q.reason=primitiveReasons[q.reason];
      if(q.geometry)q.geometry.relation=['separated','penetrating','touching','boundary_unresolved'][q.geometry.relation];
      for(const c of q.candidates){c.feature=features[c.feature];c.disposition=dispositions[c.disposition];}}
  }
  const input=structuredClone(fixture.input);
  r.originalInput={start:input.start,end:input.end,radius:input.radius,triangles:input.triangles,settings:input.settings,echo:wire(input)};
  return r;
}
const captures=new Map();
function capture(name='static-face'){
  if(captures.has(name))return structuredClone(captures.get(name));
  const input=named(name),expected=invoke(runtime,input),m=runtime.native;
  runtime.inputF64(wire(input));runtime.check(m[prefix](24));const header=runtime.output();
  const get=(kind,index=0)=>{runtime.check(m[prefix+'_record'](kind,index));return runtime.output();};
  const q={input,expected,header,echo:get(0),sources:input.triangles.map((_,i)=>get(1,i)),
    audits:Array.from({length:header[11]},(_,i)=>get(2,i)),leaves:Array.from({length:header[8]},(_,i)=>get(3,i)),
    partition:Array.from({length:header[9]},(_,i)=>get(4,i)),frontier:Array.from({length:header[10]},(_,i)=>get(5,i)),
    current:header[18]?get(6):null,initial:header[6]?get(7):null,bestWitness:header[15]?get(8):null,
    window:header[16]?get(9):null,candidateIds:Array.from({length:header[17]},(_,i)=>get(10,i)),lastHeader:null,rows:[]};
  if(header[19]){
    runtime.check(m[prefix+'_last_mesh'](0,0));q.lastHeader=runtime.output();
    for(let i=0;i<q.sources.length;++i){
      if(!q.sources[i][11]){q.rows.push(null);continue;}
      if(!q.sources[i][12]){q.rows.push({packet:null,candidates:[]});continue;}
      runtime.check(m[prefix+'_last_mesh'](1,i));const packet=runtime.output(),candidates=[];
      for(let j=0;j<packet[6];++j){runtime.check(m[prefix+'_candidate'](i,j));candidates.push(runtime.output());}
      q.rows.push({packet,candidates});
    }
  }
  captures.set(name,structuredClone(q));return q;
}
function replay(q){
  let packet=q.header;const calls={writes:0,begins:0,appends:0,queries:0,getters:0};
  const records=[q.echo,q.sources,q.audits,q.leaves,q.partition,q.frontier,q.current,q.initial,q.bestWitness,q.window,q.candidateIds];
  const native={_pp_sim_api_version:()=>1,
    [names[0]]:()=>{calls.begins++;return 0;},[names[1]]:()=>{calls.appends++;return 0;},
    [names[2]]:()=>{calls.queries++;packet=q.header;return 0;},
    [names[3]]:(kind,index)=>{calls.getters++;packet=[0,6,7,8,9].includes(kind)?records[kind]:records[kind]?.[index];return 0;},
    [names[4]]:(part,index)=>{calls.getters++;packet=part===0?q.lastHeader:q.rows[index]?.packet;return 0;},
    [names[5]]:(row,index)=>{calls.getters++;packet=q.rows[row]?.candidates[index];return 0;}};
  const r=new SimulationRuntime(native,{},0,0);
  r.inputF64=values=>{calls.writes++;return values.length;};r.output=()=>packet?.slice();
  for(const method of ['querySphereTriangle','querySphereTriangleMesh','querySphereTriangleMeshTrajectory'])r[method]=()=>assert.fail('No '+method+' fallback');
  return {r,calls,native};
}
function rejectsEdits(name,edits){for(const [label,edit] of edits){
  const q=capture(name),fake=replay(q),old=invoke(fake.r,q.input),saved=structuredClone(old);edit(q);
  assert.throws(()=>invoke(fake.r,q.input),undefined,label);assert.deepEqual(old,saved,'Rejected packet changed old JS DTO: '+label);
}}
const changed=(label,select,edit)=>[label,q=>edit(select(q))];
const zeroCalls={writes:0,begins:0,appends:0,queries:0,getters:0};

test('entry requires all six exports before accessing input, and an old80 runtime has no fallback',()=>{
  for(const missing of names){
    const native=Object.fromEntries(names.map(name=>[name,()=>assert.fail('Unavailable SDK called '+name)]));
    native._pp_sim_api_version=()=>1;delete native[missing];const r=new SimulationRuntime(native,{},0,0);
    r.inputF64=()=>assert.fail('Missing capability wrote input');
    const path=new Proxy({},{get(){assert.fail('Missing capability read input');}});
    assert.throws(()=>r.querySphereTriangleMeshEntry(path,null),/unavailable/i,missing);
  }
  const old=new SimulationRuntime({_pp_sim_api_version:()=>1,[names[0]]:()=>assert.fail('Old SDK began')},{},0,0);
  old.inputF64=()=>assert.fail('Old80 SDK wrote');assert.throws(()=>old.querySphereTriangleMeshEntry(base(),[flat()]),/unavailable/i);
});

test('all frozen65 sources execute62 actual C++ models and reject3 host inputs without rewriting expected geometry',()=>{
  assert.equal(corpus.fixtures.length,65);let models=0,hosts=0;
  const hostNames=new Set(['zero-source-id','unsafe-source-id','65-source-rejection']);
  for(const fixture of corpus.fixtures){const input=structuredClone(fixture.input),before=structuredClone(input);
    if(hostNames.has(fixture.name)){assert.throws(()=>invoke(runtime,input),undefined,fixture.name);hosts++;}
    else{const r=invoke(runtime,input),e=expected(fixture);assert.deepEqual(r,e,fixture.name);assert.deepEqual(Object.keys(r),Object.keys(e),fixture.name+' result keys');models++;}
    assert.deepEqual(input,before,fixture.name+' source mutation');
  }
  assert.deepEqual({models,hosts},{models:62,hosts:3});
});

test('finite malformed host inputs are rejected completely before stage or scratch writes',()=>{
  const badPaths=[null,{}, {...base(),start:[1,2]}, {...base(),end:[1,NaN,1]}, {...base(),radius:Infinity}, {...base(),radius:true}, {...base(),start:[1,,1]}];
  const badSources=[null,{},Array.from({length:65},(_,i)=>flat(i+1)),[flat(),flat(0)],[flat(),flat(2**53)],
    [flat(),,flat(2)],[flat(),flat(-1)],[flat(),flat(true)],[flat(),{id:2,vertices:[]}],
    [flat(),{id:2,vertices:[[0,0,0],[4,0,0],[0,0,Infinity]]}],[flat(),{id:2,vertices:[[0,,0],[4,0,0],[0,0,4]]}]];
  for(const length of [1.5,-1,NaN,Infinity,2**32,true])badSources.push(new Proxy([flat()],{get(t,k,r){return k==='length'?length:Reflect.get(t,k,r);}}));
  const badSettings=[null,{maxEvaluations:-1},{maxLeaves:.5},{maxDepth:2**32},{enclosureSqrtRefinements:NaN},
    {maxTotalSqrtRefinements:Infinity},{parameterTolerance:NaN},{parameterTolerance:'1'},
    {mesh:{maxSurfaces:-1}},{mesh:{primitive:{maxCandidates:.5}}},{mesh:{primitive:{sqrtRefinements:2**32}}},
    {mesh:{primitive:{maximumLocalWidth:NaN}}},{mesh:{primitive:{maximumNormalWidth:Infinity}}},{mesh:{primitive:{minimumSineSquared:true}}}];
  for(const [path,triangles,settings] of [...badPaths.map(p=>[p,[flat()],{}]),...badSources.map(s=>[base(),s,{}]),...badSettings.map(s=>[base(),[flat()],s])]){
    const fake=replay({});assert.throws(()=>fake.r.querySphereTriangleMeshEntry(path,triangles,settings));assert.deepEqual(fake.calls,zeroCalls);
  }
});

test('actual analytic quarter entry keeps closed positive prefix and negative witness distinct from contact time',()=>{
  const r=invoke(runtime,named('analytic-entry-quarter'));
  assert.equal(r.status,'entry_window');assert.equal(r.initialSeparationProven,true);assert.ok(r.initial.lowerGapCertificate[0]>0);
  assert.ok(r.window.parameter[0]<.25&&r.window.parameter[1]>.25);assert.ok(r.window.width[1]<=1e-6);
  assert.deepEqual(r.safePrefix,[0,r.window.parameter[0]]);assert.equal(r.bestWitness.parameter,r.window.parameter[1]);
  assert.ok(r.bestWitness.upperGapCertificate[1]<0);assert.equal(r.window.witnessAuditIndex,r.bestWitness.auditIndex);
  assert.equal('time' in r,false);assert.equal('normal' in r,false);assert.equal('surfaceId' in r,false);
  assert.ok(r.certifiedLeaves.some(l=>l.cell.parameter[0]>r.safePrefix[1]),'A later certified island must not extend the prefix');
  assert.ok(r.frontier.some(c=>c.parameter[0]>=r.bestWitness.parameter),'Unqueried tail is owned');
});

test('actual full256 audits128 leaves and breadth127 frontier include last entries without truncation',()=>{
  const r=invoke(runtime,named('actual-256-audits-128-leaves'));
  assert.equal(r.status,'separated');assert.equal(r.audits.length,256);assert.equal(r.audits[0].kind,'initial_point');
  assert.equal(r.certifiedLeaves.length,128);assert.equal(r.partition.length,128);assert.equal(r.certifiedLeaves.at(-1).auditIndex,255);
  assert.deepEqual(r.safePrefix,[0,1]);assert.equal(r.partition.at(-1).cell.parameter[1],1);assert.equal(r.work.meshQueries,256);
  const b=invoke(runtime,named('breadth-frontier-budget'));assert.equal(b.status,'not_certified');assert.equal(b.frontier.length,127);
  assert.equal(b.partition.length,128);assert.equal(b.audits.length,128);assert.equal(b.certifiedLeaves.length,0);assert.deepEqual(b.safePrefix,[0,0]);
  assert.equal(b.frontier.at(-1).parameter[1],1);assert.ok(b.current);assert.equal(b.partition.filter(p=>p.state==='current').length,1);
});

test('actual127 partition failure has126 certified leaves and no success prefix promotion',()=>{
  const r=invoke(runtime,named('127-leaf-budget-preserves-prefix'));assert.equal(r.status,'not_certified');assert.equal(r.reason,'leaf_budget');
  assert.equal(r.partitionLeaves,127);assert.equal(r.partition.length,127);assert.equal(r.certifiedLeaves.length,126);assert.equal(r.audits.length,254);
  assert.ok(r.safePrefix[1]>0&&r.safePrefix[1]<1);assert.equal(r.partition.at(-1).state,'unresolved');assert.equal(r.window,null);
  const e=invoke(runtime,named('255-evaluation-budget-includes-initial'));assert.equal(e.audits.length,255);assert.equal(e.certifiedLeaves.length,127);assert.ok(e.current);
});

test('actual64 sources and conservative window IDs retain complete rows candidates and input order',()=>{
  const input=named('actual-64-entry-all-conservative-ids'),r=invoke(runtime,input);
  assert.equal(r.status,'entry_window');assert.equal(r.candidateSurfaceIds.length,64);
  assert.deepEqual(r.candidateSurfaceIds,input.triangles.map(t=>t.id).sort((a,b)=>a-b));
  assert.equal(r.originalInput.triangles.length,64);assert.equal(r.lastMesh.rows.length,64);assert.equal(r.lastMesh.rows.at(-1).triangle.id,input.triangles.at(-1).id);
  assert.equal(r.lastMesh.rows.at(-1).query.candidates.length,7);assert.equal(r.lastMeshAuditIndex,r.audits.length-1);
  assert.ok(Object.is(r.lastMesh.rows.at(-1).query.candidates[0].kkt[0][0],-0));
});

test('initial negative boundary normal failure and untouched initial-point current are separate states',()=>{
  for(const name of ['initial-strict-negative','initial-backside-negative']){const r=invoke(runtime,named(name));
    assert.equal(r.status,'initial_penetration');assert.ok(r.initial.upperGapCertificate[1]<0);assert.equal(r.initialSeparationProven,false);
    assert.equal(r.bestWitness,null);assert.equal(r.window,null);assert.equal(r.safePrefix,null);assert.equal(r.audits.length,1);}
  const boundary=invoke(runtime,named('initial-exact-boundary'));assert.equal(boundary.reason,'initial_boundary');assert.ok(boundary.initial);assert.equal(boundary.window,null);
  const normal=invoke(runtime,named('initial-zero-distance-normal-failure'));assert.equal(normal.reason,'mesh_query_failed');assert.ok(normal.snapshot);assert.equal(normal.initial,null);
  const pre=invoke(runtime,named('sqrt-reservation-before-mesh'));assert.deepEqual(pre.current,{parameter:[0,0],depth:0});
  assert.equal(pre.lastMesh,null);assert.equal(pre.audits[0].meshQueried,false);assert.equal(pre.partition[0].cell.parameter[1],1);
  const firstOnly=invoke(runtime,named('initial-only-evaluation-budget'));assert.equal(firstOnly.audits.length,1);assert.deepEqual(firstOnly.safePrefix,[0,0]);
  assert.deepEqual(firstOnly.current,{parameter:[0,1],depth:0});assert.equal(firstOnly.partition[0].auditIndex,null);
});

test('recoverable failed ancestor and later successful rows remain diagnostics rather than invented proofs',()=>{
  const r=invoke(runtime,named('symmetric-midpoint-normal-failure'));assert.equal(r.status,'entry_window');
  assert.equal(r.audits[1].meshStatus,'row_failure');assert.equal(r.audits[1].outcome,'split');assert.equal(r.audits[1].clearanceCertificate,null);
  assert.ok(r.certifiedLeaves.every(l=>l.auditIndex!==1));assert.ok(r.bestWitness.auditIndex>1);
  const row=invoke(runtime,named('middle-degenerate-later-row-preserved'));assert.equal(row.lastMesh.status,'row_failure');
  assert.equal(row.lastMesh.rows[1].query.status,'degenerate');assert.equal(row.lastMesh.rows[2].query.status,'completed');assert.equal(row.initial,null);
  const wide=invoke(runtime,named('tight-tolerance-depth-budget'));assert.ok(wide.bestWitness);assert.equal(wide.window,null);assert.equal(wide.reason,'depth_budget');
});

test('actual caller originalInput snapshot lastMesh and later query own independent signed-zero copies',()=>{
  const input=named('signed-source-zero');input.settings.maxDepth=-0;
  const before=structuredClone(input),r=invoke(runtime,input),saved=structuredClone(r);assert.deepEqual(input,before);
  assert.ok(Object.is(r.originalInput.settings.maxDepth,-0));assert.ok(Object.is(r.originalInput.echo[16],-0));assert.ok(Object.is(r.snapshot.settings.maxDepth,0));
  assert.ok(Object.is(r.originalInput.triangles[0].vertices[0][0],-0));assert.ok(Object.is(r.snapshot.triangles[0].vertices[0][0],-0));
  input.start[0]=123;input.triangles[0].vertices[0][0]=123;input.settings.parameterTolerance=1;
  invoke(runtime,named('analytic-entry-quarter'));assert.deepEqual(r,saved);
  r.originalInput.start[0]=456;r.originalInput.triangles[0].vertices[0][0]=456;r.originalInput.settings.mesh.maxSurfaces=1;r.originalInput.echo[0]=456;
  assert.deepEqual(r.snapshot,saved.snapshot);assert.deepEqual(r.lastMesh,saved.lastMesh);
  r.snapshot.triangles[0].vertices[0][0]=789;assert.deepEqual(r.lastMesh,saved.lastMesh);
  r.audits[0].pathBounds[0][0]=789;r.lastMesh.rows[0].triangle.vertices[0][0]=789;
  assert.deepEqual(invoke(runtime,before),saved);
  const invalid=invoke(runtime,named('duplicate-source-id'));assert.equal(invalid.snapshot,null);assert.equal(invalid.originalInput.triangles.length,2);
});

test('preflight captures accessors lengths and numeric properties once and ignores caller iterators',()=>{
  const source=named('static-face'),counts=new Map();
  const count=label=>counts.set(label,(counts.get(label)??0)+1);
  const vector=(value,label)=>new Proxy(value,{get(target,key,receiver){if(key==='length'||['0','1','2'].includes(key))count(label+'.'+key);if(key===Symbol.iterator)return ()=>assert.fail('Caller iterator read');return Reflect.get(target,key,receiver);}});
  let idReads=0,verticesReads=0,lengthReads=0;
  const vertices=source.triangles[0].vertices.map((v,i)=>vector(v,'v'+i));
  const triangle={get id(){idReads++;return idReads===1?37:-1;},get vertices(){verticesReads++;return verticesReads===1?vertices:[];}};
  const triangles=new Proxy([triangle],{get(t,k,r){if(k==='length')lengthReads++;if(k===Symbol.iterator)return ()=>assert.fail('Source iterator read');return Reflect.get(t,k,r);}});
  const start=vector(source.start,'start'),end=vector(source.end,'end');let sr=0,er=0,rr=0;
  const path={get start(){sr++;return sr===1?start:null;},get end(){er++;return er===1?end:null;},get radius(){rr++;return rr===1?.25:NaN;}};
  const r=runtime.querySphereTriangleMeshEntry(path,triangles);assert.equal(r.status,'separated');
  assert.deepEqual({idReads,verticesReads,lengthReads,sr,er,rr},{idReads:1,verticesReads:1,lengthReads:1,sr:1,er:1,rr:1});
  for(const [label,n] of counts)assert.equal(n,1,label);
  let invalidReads=0;const fake=replay({});assert.throws(()=>fake.r.querySphereTriangleMeshEntry(base(),[{get id(){return ++invalidReads===1?0:37;},vertices:flat().vertices}]));
  assert.equal(invalidReads,1);assert.deepEqual(fake.calls,zeroCalls);
});

test('settings are captured once and complete owned input is fixed before the first Native call',()=>{
  const q=capture(),input=structuredClone(q.input),counts=new Map();
  const once=(o,label)=>new Proxy(o,{get(t,k,r){if(Object.hasOwn(t,k)){const key=label+'.'+k;counts.set(key,(counts.get(key)??0)+1);assert.equal(counts.get(key),1,key);}return Reflect.get(t,k,r);}});
  const p=once(input.settings.mesh.primitive,'primitive'),m=once({...input.settings.mesh,primitive:p},'mesh');
  const settings=once({...input.settings,mesh:m},'settings');const fake=replay(q),begin=fake.native[names[0]];
  fake.native[names[0]]=(...args)=>{input.start.fill(999);input.end.fill(999);input.radius=0;input.triangles[0].id=999;input.triangles[0].vertices[0].fill(999);input.settings.maxLeaves=0;return begin(...args);};
  const actual=fake.r.querySphereTriangleMeshEntry(input,input.triangles,settings);assert.deepEqual(actual,q.expected);
  for(const n of counts.values())assert.equal(n,1);
});

test('host preflight rejection preserves actual Native old output and stage, and loader rejection recovers',async()=>{
  invoke(runtime,named('static-face'));const m=runtime.native;runtime.check(m[prefix+'_record'](0,0));const old=runtime.output();
  for(const name of ['zero-source-id','unsafe-source-id','65-source-rejection']){assert.throws(()=>invoke(runtime,named(name)));assert.deepEqual(runtime.output(),old);}
  runtime.check(m[prefix](24));assert.equal(runtime.output()[0],1,'Host rejection must not replace original stage');
  await assert.rejects(loadSimulationRuntime({wasmBytes:[]}));await assert.rejects(loadSimulationRuntime({wasmBytes:new Uint8Array()}));
  assert.equal(invoke(runtime,named('analytic-entry-quarter')).status,'entry_window');
});

test('read-only entry keeps World clock loads and old single mesh trajectory records independent across reset',()=>{
  const world=runtime.createWorld({gravity:[0,-10,0]}),m=runtime.native;
  try{
    world.addBody({id:4,position:[0,10,0],force:[2,0,0],torque:[0,0,1]});world.step(1/120);const before={info:world.info(),body:world.getBody(4)};
    runtime.querySphereTriangle({position:[1,1,1],radius:.25},flat(777));runtime.check(m._pp_sim_sphere_triangle_candidate(0));const single=runtime.output();
    runtime.querySphereTriangleMesh({position:[1,1,1],radius:.25},[flat(555)]);runtime.check(m._pp_sim_sphere_triangle_mesh_source(0));const mesh=runtime.output();
    runtime.querySphereTriangleMeshTrajectory(base(),[flat(333)]);runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_record(0,0));const trajectory=runtime.output();
    invoke(runtime,named('analytic-entry-quarter'));invoke(runtime,named('zero-radius'));assert.deepEqual({info:world.info(),body:world.getBody(4)},before);
    runtime.check(m._pp_sim_sphere_triangle_candidate(0));assert.deepEqual(runtime.output(),single);runtime.check(m._pp_sim_sphere_triangle_mesh_source(0));assert.deepEqual(runtime.output(),mesh);
    runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_record(0,0));assert.deepEqual(runtime.output(),trajectory);
    runtime.check(m[prefix+'_record'](0,0));const echo=runtime.output();
    for(const call of [()=>m[prefix+'_record'](2,256),()=>m[prefix+'_last_mesh'](0,0),()=>m[prefix+'_candidate'](0,0)]){assert.notEqual(call(),0);assert.deepEqual(runtime.output(),echo);}
  }finally{world.dispose();}
  runtime.check(m._pp_sim_reset());assert.notEqual(m[prefix+'_record'](0,0),0);assert.equal(invoke(runtime,named('static-face')).status,'separated');
});

test('actual packet replay preserves all owned fields and remains usable after a decoder rejection',()=>{
  for(const name of ['static-face','analytic-entry-quarter','initial-strict-negative','initial-exact-boundary','initial-zero-distance-normal-failure',
    'initial-only-evaluation-budget','surface-budget-before-query','duplicate-source-id','middle-degenerate-later-row-preserved']){
    const q=capture(name);assert.deepEqual(invoke(replay(q).r,q.input),q.expected,name);
  }
  const q=capture(),fake=replay(q),old=invoke(fake.r,q.input),saved=structuredClone(old);q.header[35]=-0;
  assert.throws(()=>invoke(fake.r,q.input));assert.deepEqual(old,saved);q.header[35]=0;assert.deepEqual(invoke(fake.r,q.input),saved);
});

test('summary and echo reject exact length type flags counts enum padding and ownership corruption',()=>{
  const edits=[['short',a=>a.pop()],['tail',a=>a.push(0)],['nan',a=>a[0]=NaN],['boolean',a=>a[3]=true],['string',a=>a[0]='1'],
    ['status enum',a=>a[0]=7],['reason enum',a=>a[1]=18],['classification',a=>a[1]=1],['negative-zero enum',a=>a[0]=-0],
    ['source count',a=>a[2]++],['snapshot flag',a=>a[3]=2],['failed absent payload',a=>a[5]=1],['initial flag',a=>a[6]=0],['initialsep flag',a=>a[7]=2],
    ['leaf overflow',a=>a[8]=129],['partition overflow',a=>a[9]=129],['frontier overflow',a=>a[10]=129],['audit overflow',a=>a[11]=257],
    ['prefix loss',a=>a[12]=0],['fake witness',a=>a[15]=1],['fake window',a=>a[16]=1],['fake conservative IDs',a=>a[17]=1],
    ['mesh loss',a=>a[19]=0],['mesh link loss',a=>a[20]=0],['mesh link wrong',a=>a[21]=0],['partition count',a=>a[22]++],['depth',a=>a[23]++],
    ['work sum',a=>a[24]++],['work upper',a=>a[30]++],['exactflag',a=>a[34]=2],['padding sign',a=>a[35]=-0],['padding',a=>a[39]=1],['sparse',a=>delete a[0]]];
  rejectsEdits('static-face',edits.map(([label,edit])=>changed(label,q=>q.header,edit)));
  rejectsEdits('static-face',[changed('echo changed',q=>q.echo,a=>a[0]++),changed('echo tolerance',q=>q.echo,a=>a[19]=1),
    changed('reserved -0',q=>q.echo,a=>a[23]=-0),changed('echo short',q=>q.echo,a=>a.pop())]);
});

test('source rows reject mismatched input bits IDs flags and sparse data before publishing a DTO',()=>{
  rejectsEdits('static-face',[...[[0,1],[1,999],[2,1],[11,0],[12,0],[13,0],[13,2],[11,true],[1,-0]].map(([i,v])=>changed('source '+i,q=>q.sources[0],a=>a[i]=v)),
    changed('short',q=>q.sources[0],a=>a.pop()),changed('tail',q=>q.sources[0],a=>a.push(0)),changed('sparse',q=>q.sources[0],a=>delete a[3])]);
});

test('initial and regular audit packets validate kind parameter optional prefix work bounds and reserved signs',()=>{
  const edits=[['ordinal',a=>a[0]=1],['kind',a=>a[1]=2],['wrong kind',a=>a[1]=1],['depth',a=>a[4]=1],['parameter',a=>a[5]=.25],
    ['outcome',a=>a[6]=7],['outcome type',a=>a[6]=true],['path lost',a=>a[7]=0],['path interval',a=>{a[8]=2;a[9]=1;}],
    ['point lost',a=>a[14]=0],['anchor lost',a=>a[21]=0],['mesh queried',a=>a[25]=0],['mesh enum',a=>a[27]=6],['mesh reason',a=>a[29]=12],
    ['distance interval',a=>{a[31]=2;a[32]=1;}],['distance flag',a=>a[30]=0],['displacement root lost',a=>a[39]=0],['error root lost',a=>a[42]=0],
    ['clearance lost',a=>a[45]=0],['sqrt count',a=>a[54]++],['total work',a=>a[56]++],['exactflag',a=>a[61]=2],['reserved -0',a=>a[62]=-0],
    ['reserved',a=>a[63]=1],['short',a=>a.pop()],['tail',a=>a.push(0)],['nonfinite',a=>a[31]=Infinity],['sparse',a=>delete a[8]]];
  rejectsEdits('static-face',edits.map(([label,edit])=>changed(label,q=>q.audits[0],edit)));
  rejectsEdits('static-face',[changed('cell masquerading as initial',q=>q.audits[1],a=>a[1]=0),changed('cell parameter',q=>q.audits[1],a=>a[5]=0)]);
  rejectsEdits('symmetric-midpoint-normal-failure',[
    changed('completed split without returned proof',q=>q.audits[1],a=>{a[27]=0;a[29]=0;})]);
  rejectsEdits('sqrt-reservation-before-mesh',[changed('absent distance sign',q=>q.audits[0],a=>a[31]=-0),changed('invent mesh status',q=>q.audits[0],a=>a[26]=1)]);
});

test('partition leaves and frontier enforce closed cover ordinal audit state and blocked-reason consistency',()=>{
  rejectsEdits('static-face',[
    changed('leaf coverage hole',q=>q.leaves[0],a=>a[1]=.5),changed('leaf audit',q=>q.leaves[0],a=>a[5]=0),changed('leaf nonpositive',q=>q.leaves[0],a=>a[3]=0),
    changed('leaf short',q=>q.leaves[0],a=>a.pop()),changed('leaf bool',q=>q.leaves[0],a=>a[2]=false),
    changed('partition ordinal',q=>q.partition[0],a=>a[0]=1),changed('partition hole',q=>q.partition[0],a=>a[2]=.5),changed('partition state',q=>q.partition[0],a=>a[4]=0),
    changed('partition absent audit',q=>q.partition[0],a=>a[5]=0),changed('partition audit',q=>q.partition[0],a=>a[6]=0),changed('partition reason',q=>q.partition[0],a=>a[7]=10),
    changed('partition short',q=>q.partition[0],a=>a.pop())]);
  rejectsEdits('analytic-entry-quarter',[changed('frontier ordinal',q=>q.frontier[0],a=>a[0]=1),['frontier removed tail',q=>{q.frontier.pop();q.header[10]--;}],
    changed('frontier sparse',q=>q.frontier[0],a=>delete a[1]),changed('frontier depth',q=>q.frontier[0],a=>a[3]++)]);
  rejectsEdits('initial-only-evaluation-budget',[changed('current ordinal',q=>q.current,a=>a[0]=1),changed('current hole',q=>q.current,a=>a[1]=.5)]);
  rejectsEdits('sqrt-reservation-before-mesh',[changed('initial current not point',q=>q.current,a=>a[2]=1)]);
});

test('initial proof window best witness and all-source ID links reject fabricated success metadata',()=>{
  rejectsEdits('static-face',[changed('initial ordinal',q=>q.initial,a=>a[0]=1),changed('initial audit',q=>q.initial,a=>a[5]=1),
    changed('initial strictness',q=>q.initial,a=>a[1]=0),changed('initial short',q=>q.initial,a=>a.pop())]);
  rejectsEdits('analytic-entry-quarter',[
    changed('window ordinal',q=>q.window,a=>a[0]=1),changed('window L',q=>q.window,a=>a[1]=0),changed('window U',q=>q.window,a=>a[2]=1),
    changed('window too wide',q=>q.window,a=>a[4]=1),changed('window inverted',q=>q.window,a=>a[3]=a[4]+1),changed('window audit',q=>q.window,a=>a[5]=0),
    changed('witness ordinal',q=>q.bestWitness,a=>a[0]=1),changed('witness parameter',q=>q.bestWitness,a=>a[4]=2),
    changed('witness path',q=>q.bestWitness,a=>a[5]=123),changed('witness anchor',q=>q.bestWitness,a=>a[11]=123),changed('witness error',q=>q.bestWitness,a=>a[14]=-1),
    changed('witness nonstrict',q=>q.bestWitness,a=>a[16]=0),changed('witness audit',q=>q.bestWitness,a=>a[17]=0),changed('witness short',q=>q.bestWitness,a=>a.pop()),
    changed('ID ordinal',q=>q.candidateIds[0],a=>a[0]=1),changed('foreign ID',q=>q.candidateIds[0],a=>a[1]=999),changed('ID tail',q=>q.candidateIds[0],a=>a.push(0))]);
});

test('last mesh link rows candidates and scratch own all fields and preserve unused KKT negative zero',()=>{
  rejectsEdits('static-face',[
    changed('mesh count',q=>q.lastHeader,a=>a[3]++),changed('mesh padding',q=>q.lastHeader,a=>a[23]=-0),changed('mesh work',q=>q.lastHeader,a=>a[10]++),
    changed('wrong row ID',q=>q.rows[0].packet,a=>a[3]=999),changed('wrong row work',q=>q.rows[0].packet,a=>a[7]=6),changed('bad geometry',q=>q.rows[0].packet,a=>a[40]=2),
    changed('row interval sparse',q=>q.rows[0].packet,a=>delete a[12]),changed('row normal sparse',q=>q.rows[0].packet,a=>delete a[40]),
    ...[0,1,2,3,4,5,6,7,8,9,10,13].map(i=>changed('row metadata negative zero '+i,q=>q.rows[0].packet,a=>a[i]=-0)),
    changed('candidate ordinal',q=>q.rows[0].candidates[0],a=>a[0]=1),changed('unused KKT sign',q=>q.rows[0].candidates[0],a=>a[9]=0),
    ...[0,1,2].map(i=>changed('candidate metadata negative zero '+i,q=>q.rows[0].candidates[0],a=>a[i]=-0)),
    changed('candidate tail',q=>q.rows[0].candidates[0],a=>a.push(0)),changed('candidate nonfinite',q=>q.rows[0].candidates[0],a=>a[3]=NaN),
    changed('candidate barycentric sparse',q=>q.rows[0].candidates[0],a=>delete a[3]),changed('candidate used KKT sparse',q=>q.rows[0].candidates[1],a=>delete a[10])]);
  rejectsEdits('middle-degenerate-later-row-preserved',[
    changed('failed row absent geometry sparse',q=>q.rows[1].packet,a=>delete a[40]),
    ...[2,6,7,8,9,13].map(i=>changed('failed row metadata negative zero '+i,q=>q.rows[1].packet,a=>a[i]=-0))]);
  const q=capture(),r=invoke(replay(q).r,q.input),saved=structuredClone(r);
  q.echo.fill(0);q.sources[0].fill(0);q.audits[0].fill(0);q.partition[0].fill(0);q.initial.fill(0);q.rows[0].packet.fill(0);q.rows[0].candidates[0].fill(0);
  assert.deepEqual(r,saved);assert.ok(Object.is(r.lastMesh.rows[0].query.candidates[0].kkt[0][0],-0));
});

test('stage query and each getter rejection propagate without fallback or changing previously returned JS data',()=>{
  for(const name of names){const q=capture(),fake=replay(q),old=invoke(fake.r,q.input),saved=structuredClone(old),marker=new Error('Native phase rejected '+name);
    const previous=fake.native[name];fake.native[name]=()=>77;fake.r.check=status=>{if(status!==0)throw marker;};
    assert.throws(()=>invoke(fake.r,q.input),error=>error===marker,name);assert.deepEqual(old,saved,name);
    fake.native[name]=previous;assert.deepEqual(invoke(fake.r,q.input),saved,'Recovery after '+name);
  }
  const q=capture(),fake=replay(q);
  for(const name of names){const fn=fake.native[name];fake.native[name]=function(...args){assert.equal(this,fake.native,'Native receiver '+name);return Reflect.apply(fn,this,args);};}
  assert.deepEqual(invoke(fake.r,q.input),q.expected);
});

test('synthetic unreturned R sqrt keeps positive initial proof unknown work current and no entry window',()=>{
  // Artificial decoder packets only: no actual C++ allocation/root fault was injected.
  const q=capture('depth-budget-zero'),h=q.header,a=q.audits[1],initial=q.audits[0],primitive=a[54];
  h[0]=6;h[1]=14;h[18]=1;q.current=[0,0,1,0];
  q.partition[0]=[0,0,1,0,3,1,1,14];a[6]=6;
  for(const at of [39,42,45,48])a.fill(0,at,at+3);
  a[55]=0;a[56]=primitive;a[57]=primitive+512;a[59]=1;a[60]=0;a[61]=0;
  for(let i=0;i<10;++i)h[24+i]=initial[51+i]+a[51+i];h[34]=0;
  const r=invoke(replay(q).r,q.input);
  assert.equal(r.status,'numerical_failure');assert.equal(r.reason,'nonfinite_intermediate');assert.equal(r.work.workExact,false);
  assert.equal(r.work.sqrtRefinementsUpper,r.work.sqrtRefinements+512);assert.ok(r.initial);assert.equal(r.initialSeparationProven,true);
  assert.deepEqual(r.safePrefix,[0,0]);assert.deepEqual(r.certifiedLeaves,[]);assert.equal(r.window,null);assert.equal(r.bestWitness,null);
  assert.equal(r.audits[1].displacementRoot,null);assert.deepEqual(r.current,{parameter:[0,1],depth:0});assert.ok(r.lastMesh);
  for(const [label,edit] of [['pretend separated',p=>p.header[0]=1],['pretend exact',p=>p.header[34]=1],
    ['strip reservation',p=>p.header[30]=p.header[29]],['delta strip reservation',p=>p.audits[1][57]=primitive],
    ['consistent global and delta underreservation',p=>{p.header[30]=p.header[29];p.audits[1][57]=primitive;}]]){
    const modified=structuredClone(q);edit(modified);assert.throws(()=>invoke(replay(modified).r,modified.input),undefined,label);
  }
});

test('synthetic pre-initial-audit allocation failure retains source and point current without inventing work',()=>{
  // Decoder shape coverage, not a real allocator fault injection.
  const q=capture();q.header=Array(40).fill(0);
  for(const [i,v] of [[0,6],[1,15],[2,1],[3,1],[9,1],[10,1],[18,1],[22,1],[34,1]])q.header[i]=v;
  for(const source of q.sources)source.fill(0,11,14);
  q.audits=[];q.leaves=[];q.partition=[[0,0,1,0,0,0,0,0]];q.frontier=[[0,0,1,0]];q.current=[0,0,0,0];
  q.initial=null;q.bestWitness=null;q.window=null;q.candidateIds=[];q.lastHeader=null;q.rows=[];
  const r=invoke(replay(q).r,q.input);assert.equal(r.status,'numerical_failure');assert.equal(r.reason,'allocation_failure');
  assert.ok(r.snapshot);assert.equal(r.originalInput.triangles.length,1);assert.equal(r.initial,null);assert.equal(r.lastMesh,null);
  assert.deepEqual(r.current,{parameter:[0,0],depth:0});assert.deepEqual(r.audits,[]);assert.equal(r.work.meshQueries,0);assert.equal(r.work.workExact,true);
  assert.deepEqual(r.partition[0],{cell:{parameter:[0,1],depth:0},state:'unqueried',auditIndex:null,blockedReason:'none'});
  const inconsistent=structuredClone(q);inconsistent.header[1]=14;
  assert.throws(()=>invoke(replay(inconsistent).r,inconsistent.input),'Unaudited initial current is specific to the allocation stage');
});
