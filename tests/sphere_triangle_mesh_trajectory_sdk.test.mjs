import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
// The frozen corpus supplies original inputs, not decoder-generated mathematical expectations.
// Its complete 62-case/independent Fraction acceptance belongs to the separate wire runner.
const corpus=JSON.parse(await readFile(new URL('../reports/sphere-triangle-mesh-trajectory-checks/run-20261104-root/final-accepted/native-final-fixtures.json',import.meta.url),'utf8'));
const named=name=>{const f=corpus.fixtures.find(f=>f.name===name);assert.ok(f,'Missing original fixture '+name);return structuredClone(f.input);};
const flat=(id=37)=>({id,vertices:[[-0,0,0],[4,0,0],[0,0,4]]});
const base=()=>({start:[1,1,1],end:[1,1,1],radius:.25});
const names=['_pp_sim_sphere_triangle_mesh_trajectory_begin','_pp_sim_sphere_triangle_mesh_trajectory_append',
  '_pp_sim_sphere_triangle_mesh_trajectory','_pp_sim_sphere_triangle_mesh_trajectory_record',
  '_pp_sim_sphere_triangle_mesh_trajectory_last_mesh','_pp_sim_sphere_triangle_mesh_trajectory_candidate'];
const invoke=(r,input)=>r.querySphereTriangleMeshTrajectory({start:input.start,end:input.end,radius:input.radius},input.triangles,input.settings);
function wire(input){const s=input.settings,m=s.mesh,p=m.primitive;return [...input.start,...input.end,input.radius,m.maxSurfaces,p.maxCandidates,p.sqrtRefinements,p.maxTotalSqrtRefinements,p.maximumLocalWidth,p.maximumNormalWidth,p.minimumSineSquared,s.maxEvaluations,s.maxLeaves,s.maxDepth,s.enclosureSqrtRefinements,s.maxTotalSqrtRefinements,0,0,0,0,0];}
const captures=new Map();
function capture(name='static-face'){
  if(captures.has(name))return structuredClone(captures.get(name));
  const input=named(name),expected=invoke(runtime,input),m=runtime.native;
  runtime.inputF64(wire(input));runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory(24));const header=runtime.output();
  const get=(kind,index=0)=>{runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_record(kind,index));return runtime.output();};
  const q={input,expected,header,echo:get(0),sources:input.triangles.map((_,i)=>get(1,i)),
    audits:Array.from({length:header[8]},(_,i)=>get(2,i)),leaves:Array.from({length:header[6]},(_,i)=>get(3,i)),
    frontier:Array.from({length:header[7]},(_,i)=>get(4,i)),current:header[13]?get(5):null,witness:header[12]?get(6):null,lastHeader:null,rows:[]};
  if(header[14]){
    runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_last_mesh(0,0));q.lastHeader=runtime.output();
    for(let i=0;i<q.sources.length;++i){
      if(!q.sources[i][11]){q.rows.push(null);continue;}
      if(!q.sources[i][12]){q.rows.push({packet:null,candidates:[]});continue;}
      runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_last_mesh(1,i));const packet=runtime.output(),candidates=[];
      for(let j=0;j<packet[6];++j){runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_candidate(i,j));candidates.push(runtime.output());}
      q.rows.push({packet,candidates});
    }
  }
  captures.set(name,structuredClone(q));return q;
}
function replay(q){
  let packet=q.header;const calls={writes:0,begins:0,appends:0,queries:0,getters:0};
  const native={_pp_sim_api_version:()=>1,
    [names[0]]:()=>{calls.begins++;return 0;},[names[1]]:()=>{calls.appends++;return 0;},
    [names[2]]:()=>{calls.queries++;packet=q.header;return 0;},
    [names[3]]:(kind,index)=>{calls.getters++;packet=kind===0?q.echo:kind===1?q.sources[index]:kind===2?q.audits[index]:kind===3?q.leaves[index]:kind===4?q.frontier[index]:kind===5?q.current:q.witness;return 0;},
    [names[4]]:(part,index)=>{calls.getters++;packet=part===0?q.lastHeader:q.rows[index].packet;return 0;},
    [names[5]]:(row,index)=>{calls.getters++;packet=q.rows[row].candidates[index];return 0;}};
  const r=new SimulationRuntime(native,{},0,0);
  r.inputF64=values=>{calls.writes++;return values.length;};
  r.output=()=>packet?.slice();
  r.querySphereTriangleMesh=()=>assert.fail('No mesh fallback');r.querySphereTriangle=()=>assert.fail('No single fallback');
  return {r,calls,native};
}
function rejectsEdits(name,edits){for(const [label,edit] of edits){
  const q=capture(name),fake=replay(q),old=invoke(fake.r,q.input),saved=structuredClone(old);edit(q);
  assert.throws(()=>invoke(fake.r,q.input),undefined,label);assert.deepEqual(old,saved,'Rejected packet mutated old JS DTO: '+label);
}}
const changed=(label,select,edit)=>[label,q=>edit(select(q))];

test('trajectory bridge requires all six real SDK exports before reading or writing any input',()=>{
  for(const missing of names){
    const native=Object.fromEntries(names.map(name=>[name,()=>assert.fail('Unavailable SDK called '+name)]));
    native._pp_sim_api_version=()=>1;delete native[missing];const r=new SimulationRuntime(native,{},0,0);
    r.inputF64=()=>assert.fail('Unavailable SDK wrote input');r.querySphereTriangleMesh=()=>assert.fail('No mesh fallback');
    assert.throws(()=>r.querySphereTriangleMeshTrajectory(null,null),/unavailable/i,missing);
  }
  const old=new SimulationRuntime({_pp_sim_api_version:()=>1}, {},0,0);old.inputF64=()=>assert.fail('Old 74-export SDK wrote input');
  assert.throws(()=>old.querySphereTriangleMeshTrajectory(base(),[flat()]),/unavailable/i);
});

test('trajectory host rejects every malformed late input before staging or scratch writes',()=>{
  const badPaths=[null,{}, {...base(),start:[1,2]}, {...base(),end:[1,NaN,1]}, {...base(),radius:Infinity}, {...base(),radius:true}, {...base(),start:[1,,1]}];
  const badSources=[null,{},Array.from({length:65},(_,i)=>flat(i+1)),[flat(),flat(0)],[flat(),flat(2**53)],
    [flat(),,{...flat(2)}],[flat(),flat(-1)],[flat(),flat(true)],[flat(),{id:2,vertices:[]}],
    [flat(),{id:2,vertices:[[0,0,0],[4,0,0],[0,0,Infinity]]}],[flat(),{id:2,vertices:[[0,,0],[4,0,0],[0,0,4]]}]];
  const badSettings=[null,{maxEvaluations:-1},{maxLeaves:.5},{maxDepth:2**32},{enclosureSqrtRefinements:NaN},
    {maxTotalSqrtRefinements:Infinity},{mesh:{maxSurfaces:-1}},{mesh:{primitive:{maxCandidates:.5}}},
    {mesh:{primitive:{sqrtRefinements:2**32}}},{mesh:{primitive:{maximumLocalWidth:NaN}}},
    {mesh:{primitive:{maximumNormalWidth:Infinity}}},{mesh:{primitive:{minimumSineSquared:'1'}}}];
  for(const [path,triangles,settings] of [...badPaths.map(p=>[p,[flat()],{}]),...badSources.map(s=>[base(),s,{}]),...badSettings.map(s=>[base(),[flat()],s])]){
    const fake=replay({});assert.throws(()=>fake.r.querySphereTriangleMeshTrajectory(path,triangles,settings));
    assert.deepEqual(fake.calls,{writes:0,begins:0,appends:0,queries:0,getters:0});
  }
});

test('actual static separated path encloses the analytic 3/4m gap without a fake TOI or response',()=>{
  const r=runtime.querySphereTriangleMeshTrajectory(base(),[flat()]);
  assert.equal(r.status,'separated');assert.equal(r.reason,'none');assert.deepEqual(r.safePrefix,[0,1]);assert.equal(r.witness,null);assert.equal(r.current,null);
  assert.equal(r.certifiedLeaves.length,1);assert.deepEqual(r.certifiedLeaves[0].cell.parameter,[0,1]);assert.ok(r.certifiedLeaves[0].lowerGapCertificate[0]>0);
  const gap=r.lastMesh.rows[0].query.geometry.gap;assert.ok(gap[0]<=.75&&gap[1]>=.75);assert.equal(r.work.meshQueries,1);assert.equal(r.work.workExact,true);
  assert.equal('time' in r,false);assert.equal('normal' in r,false);
});

test('actual four strict witnesses include interior crossing despite both endpoints outside',()=>{
  for(const name of ['endpoints-outside-interior-penetration','reverse-interior-penetration','static-strict-penetration','edge-strict-penetration']){
    const input=named(name),before=structuredClone(input),r=invoke(runtime,input);
    assert.equal(r.status,'penetration_witness',name);assert.equal(r.reason,'none');assert.ok(r.witness.upperGapCertificate[1]<0);
    assert.ok(r.witness.parameter>=r.witness.cell.parameter[0]&&r.witness.parameter<=r.witness.cell.parameter[1]);
    assert.equal(r.audits[r.witness.auditIndex].outcome,'penetration_witness');assert.deepEqual(input,before);
    if(name.includes('interior')){assert.ok(Math.abs(input.start[1])>input.radius&&Math.abs(input.end[1])>input.radius);assert.ok(r.witness.parameter>0&&r.witness.parameter<1);}
  }
});

test('actual model failures preserve unknown cells, primitive diagnostics and successful later rows',()=>{
  const cases=[['evaluation-budget','evaluation_budget'],['leaf-budget','leaf_budget'],['depth-zero-budget','depth_budget'],
    ['sqrt-reservation-before-mesh','sqrt_budget'],['sqrt-reservation-before-displacement','sqrt_budget'],['sqrt-reservation-before-error','sqrt_budget'],
    ['primitive-candidate-budget','mesh_query_failed'],['primitive-normal-width','mesh_query_failed'],
    ['middle-degenerate-later-row-preserved','mesh_query_failed'],['surface-budget-before-query','surface_budget']];
  for(const [name,reason] of cases){const r=invoke(runtime,named(name));assert.equal(r.status,'not_certified',name);assert.equal(r.reason,reason,name);assert.equal(r.witness,null);assert.notDeepEqual(r.safePrefix,[0,1]);}
  const failed=invoke(runtime,named('middle-degenerate-later-row-preserved'));
  assert.equal(failed.lastMesh.status,'row_failure');assert.equal(failed.lastMesh.rows[1].query.status,'degenerate');assert.equal(failed.lastMesh.rows[2].query.status,'completed');
  const unqueried=invoke(runtime,named('sqrt-reservation-before-mesh'));assert.equal(unqueried.lastMesh,null);assert.deepEqual(unqueried.audits[0].work.meshQueries,0);
  assert.equal(runtime.querySphereTriangleMeshTrajectory(base(),[flat()]).status,'separated');
});

test('actual finite domain and uint32-invalid models reach C++ while unsafe IDs stay host errors',()=>{
  for(const [name,reason] of [['empty-source','surface_count'],['duplicate-source-id','duplicate_id'],['endpoint-domain-2pow40','input_domain'],
    ['last-vertex-outside-domain','input_domain'],['zero-radius','input_domain'],['invalid-evaluation-setting','settings'],
    ['invalid-leaf-setting','settings'],['invalid-depth-setting','settings'],['invalid-enclosure-sqrt-setting','settings'],['invalid-primitive-setting','settings']]){
    const r=invoke(runtime,named(name));assert.equal(r.status,'invalid_input',name);assert.equal(r.reason,reason);assert.equal(r.snapshot,null);assert.deepEqual(r.audits,[]);assert.ok(r.originalInput);
  }
  for(const name of ['zero-source-id','unsafe-source-id','65-source-rejection'])assert.throws(()=>invoke(runtime,named(name)),undefined,name);
});

test('actual host rejection leaves the prior committed echo and output bits intact',()=>{
  const m=runtime.native;runtime.querySphereTriangleMeshTrajectory(base(),[flat()]);
  runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_record(0,0));const saved=runtime.output();
  for(const input of [named('zero-source-id'),named('unsafe-source-id'),named('65-source-rejection'),
    {...named('static-face'),end:[1,Infinity,1]}, {...named('static-face'),settings:{maxLeaves:.5}}]){
    assert.throws(()=>invoke(runtime,input));assert.deepEqual(runtime.output(),saved);
    runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_record(0,0));assert.deepEqual(runtime.output(),saved);
  }
});

test('actual full 255 audits, 128 leaves, and 127-leaf failed prefix are neither truncated nor promoted',()=>{
  const full=invoke(runtime,named('actual-128-leaf-partition'));assert.equal(full.status,'separated');assert.equal(full.audits.length,255);assert.equal(full.work.meshQueries,255);
  assert.equal(full.certifiedLeaves.length,128);assert.equal(full.certifiedLeaves.at(-1).auditIndex,254);assert.equal(full.certifiedLeaves.at(-1).cell.parameter[1],1);assert.equal(full.partitionLeaves,128);
  const fail=invoke(runtime,named('127-leaf-budget-preserves-prefix'));assert.equal(fail.status,'not_certified');assert.equal(fail.reason,'leaf_budget');
  assert.equal(fail.partitionLeaves,127);assert.ok(fail.safePrefix[1]>0&&fail.safePrefix[1]<1);assert.ok(fail.current);
  assert.deepEqual(fail.current.parameter,[fail.safePrefix[1],1]);assert.deepEqual(fail.frontier,[]);assert.equal(fail.witness,null);
});

test('actual all 64 surfaces, final row and seven candidates remain owned across all chunks',()=>{
  const input=named('actual-64-surfaces'),r=invoke(runtime,input);assert.equal(r.status,'separated');assert.equal(r.originalInput.triangles.length,64);
  assert.equal(r.lastMesh.rows.length,64);assert.equal(r.lastMesh.rows.at(-1).query.candidates.length,7);assert.equal(r.lastMesh.rows.at(-1).triangle.id,input.triangles.at(-1).id);
  assert.equal(r.lastMesh.nearest.possibleSurfaceIds.length,64);assert.deepEqual(r.lastMesh.nearest.possibleSurfaceIds,[...input.triangles.map(t=>t.id)].sort((a,b)=>a-b));
});

test('actual ownership separates caller, original echo, normalized snapshot, old DTO and future calls',()=>{
  const input=named('signed-source-zero');input.settings.maxDepth=-0;
  const before=structuredClone(input),r=invoke(runtime,input),saved=structuredClone(r);assert.deepEqual(input,before);
  assert.ok(Object.is(r.originalInput.triangles[0].vertices[0][0],-0));assert.ok(Object.is(r.snapshot.triangles[0].vertices[0][0],-0));
  assert.ok(Object.is(r.originalInput.settings.maxDepth,-0));assert.ok(Object.is(r.originalInput.echo[16],-0));assert.ok(Object.is(r.snapshot.settings.maxDepth,0));
  input.start[0]=99;input.triangles[0].vertices[0][0]=99;input.settings.mesh.primitive.maximumLocalWidth=1;runtime.querySphereTriangleMeshTrajectory(base(),[flat(99)]);assert.deepEqual(r,saved);
  r.originalInput.start[0]=123;r.originalInput.triangles[0].vertices[0][0]=123;r.originalInput.settings.mesh.maxSurfaces=123;
  assert.deepEqual(r.snapshot,saved.snapshot);r.snapshot.start[0]=456;r.audits[0].pathBounds[0][0]=456;
  assert.deepEqual(invoke(runtime,before),saved);
});

test('indexed input copying does not invoke caller array iterators during complete preflight',()=>{
  const input=named('static-face'),unexpected=()=>assert.fail('Caller iterator invoked');
  input.start[Symbol.iterator]=unexpected;input.end[Symbol.iterator]=unexpected;input.triangles[Symbol.iterator]=unexpected;
  input.triangles[0].vertices[Symbol.iterator]=unexpected;input.triangles[0].vertices.forEach(v=>v[Symbol.iterator]=unexpected);
  const r=invoke(runtime,input);assert.equal(r.status,'separated');assert.equal(r.originalInput.triangles[0].id,37);
});

test('actual rounded inside anchor cannot become a false exact-path point witness',()=>{
  const r=invoke(runtime,named('inside-rounded-anchor-no-false-witness')),a=r.audits[0];
  assert.equal(r.status,'not_certified');assert.equal(r.witness,null);assert.ok(a.distance[1]<r.originalInput.radius);
  assert.ok(a.errorRoot[1]>=2**-14);assert.ok(a.penetrationCertificate[1]>0);assert.notDeepEqual(r.safePrefix,[0,1]);
});

test('actual read-only trajectory leaves World clock loads and old single/mesh records independent',()=>{
  const world=runtime.createWorld({gravity:[0,-10,0]});
  try{
    world.addBody({id:4,position:[0,10,0],force:[2,0,0],torque:[0,0,1]});world.step(1/120);
    const before={info:world.info(),body:world.getBody(4)},m=runtime.native;
    runtime.querySphereTriangle({position:[1,1,1],radius:.25},flat(777));runtime.check(m._pp_sim_sphere_triangle_candidate(0));const single=runtime.output();
    runtime.querySphereTriangleMesh({position:[1,1,1],radius:.25},[flat(555)]);runtime.check(m._pp_sim_sphere_triangle_mesh_source(0));const mesh=runtime.output();
    invoke(runtime,named('endpoints-outside-interior-penetration'));invoke(runtime,named('zero-radius'));
    assert.deepEqual({info:world.info(),body:world.getBody(4)},before);
    runtime.check(m._pp_sim_sphere_triangle_candidate(0));assert.deepEqual(runtime.output(),single);
    runtime.check(m._pp_sim_sphere_triangle_mesh_source(0));assert.deepEqual(runtime.output(),mesh);
    runtime.check(m._pp_sim_sphere_triangle_mesh_trajectory_record(0,0));const echo=runtime.output();
    for(const call of [()=>m._pp_sim_sphere_triangle_mesh_trajectory_record(2,255),()=>m._pp_sim_sphere_triangle_mesh_trajectory_last_mesh(0,0),()=>m._pp_sim_sphere_triangle_mesh_trajectory_candidate(0,0)]){assert.notEqual(call(),0);assert.deepEqual(runtime.output(),echo);}
  }finally{world.dispose();}
  runtime.check(runtime.native._pp_sim_reset());assert.notEqual(runtime.native._pp_sim_sphere_triangle_mesh_trajectory_record(0,0),0);
  assert.equal(runtime.querySphereTriangleMeshTrajectory(base(),[flat()]).status,'separated');
});

test('real packet replay preserves complete DTO keys, types, signs and failure shapes',()=>{
  for(const name of ['static-face','evaluation-budget','sqrt-reservation-before-mesh','middle-degenerate-later-row-preserved',
    'endpoints-outside-interior-penetration','duplicate-source-id','surface-budget-before-query']){
    const q=capture(name);assert.deepEqual(invoke(replay(q).r,q.input),q.expected,name);
  }
  const q=capture(),fake=replay(q),old=invoke(fake.r,q.input),saved=structuredClone(old);
  q.header[30]=-0;assert.throws(()=>invoke(fake.r,q.input));assert.deepEqual(old,saved);
  q.header[30]=0;assert.deepEqual(invoke(fake.r,q.input),saved,'Same runtime must recover after rejected packet');
});

test('preflight owns every endpoint setting and late triangle before the first native call',()=>{
  const q=capture(),input=structuredClone(q.input),fake=replay(q),begin=fake.native[names[0]];
  fake.native[names[0]]=(...args)=>{
    input.start[0]=999;input.end[2]=999;input.radius=0;input.settings.maxLeaves=0;input.settings.mesh.primitive.maximumLocalWidth=1;
    input.triangles[0].id=999;input.triangles[0].vertices[2][2]=999;
    return begin(...args);
  };
  assert.deepEqual(invoke(fake.r,input),q.expected);
});

test('preflight captures getter-backed IDs vertices and array length exactly once',()=>{
  let ids=0,vertices=0,lengths=0;
  const triangle={get id(){return ++ids===1?37:-1;},get vertices(){vertices++;return vertices===1?flat().vertices:[];}};
  const source=new Proxy([triangle],{get(target,key,receiver){if(key==='length')lengths++;return Reflect.get(target,key,receiver);}});
  const r=runtime.querySphereTriangleMeshTrajectory(base(),source);
  assert.equal(r.status,'separated');assert.equal(r.originalInput.triangles[0].id,37);
  assert.deepEqual({ids,vertices,lengths},{ids:1,vertices:1,lengths:1});
  let invalidReads=0;const fake=replay({});
  assert.throws(()=>fake.r.querySphereTriangleMeshTrajectory(base(),[{get id(){return ++invalidReads===1?0:37;},vertices:flat().vertices}]));
  assert.equal(invalidReads,1);assert.deepEqual(fake.calls,{writes:0,begins:0,appends:0,queries:0,getters:0});
});

test('header and original echo reject lengths finite types flags enums padding and mismatched ownership',()=>{
  const select=q=>q.header;
  const edits=[['short',a=>a.pop()],['tail',a=>a.push(0)],['nan',a=>a[0]=NaN],['boolean',a=>a[3]=true],['string',a=>a[0]='0'],
    ['status enum',a=>a[0]=6],['reason enum',a=>a[1]=17],['invalid pair',a=>a[1]=1],['negative-zero enum',a=>a[0]=-0],
    ['source count',a=>a[2]++],['flag',a=>a[3]=2],['failed index absent',a=>a[5]=1],['leaf overflow',a=>a[6]=129],
    ['frontier overflow',a=>a[7]=34],['audit overflow',a=>a[8]=256],['lost prefix',a=>a[9]=0],['fake current',a=>a[13]=1],
    ['lost mesh',a=>a[14]=0],['lost mesh link',a=>a[15]=0],['wrong mesh link',a=>a[16]=1],['partition',a=>a[17]++],['depth',a=>a[18]++],
    ['work sum',a=>a[19]++],['work upper',a=>a[25]++],['exact flag',a=>a[29]=2],['padding -0',a=>a[30]=-0],['padding nonzero',a=>a[31]=1],
    ['sparse',a=>delete a[0]]];
  rejectsEdits('static-face',edits.map(([label,edit])=>changed(label,select,edit)));
  rejectsEdits('static-face',[changed('echo changed',q=>q.echo,a=>a[0]++),changed('echo reserved',q=>q.echo,a=>a[23]=-0),changed('echo short',q=>q.echo,a=>a.pop())]);
});

test('source packets reject changed bits, late IDs, flags, and sparse components instead of borrowing input',()=>{
  rejectsEdits('static-face',[...[[0,1],[1,999],[2,1],[11,0],[12,0],[13,0],[13,2],[11,true],[1,-0]].map(([i,v])=>changed('source field '+i,q=>q.sources[0],a=>a[i]=v)),
    changed('source short',q=>q.sources[0],a=>a.pop()),changed('source tail',q=>q.sources[0],a=>a.push(0)),changed('source sparse',q=>q.sources[0],a=>delete a[3])]);
});

test('audit packet validation covers optional bounds links outcomes padding and exact delta work',()=>{
  const edits=[['ordinal',a=>a[0]=1],['depth',a=>a[3]=1],['midpoint',a=>a[4]=.25],['outcome',a=>a[5]=5],['outcome type',a=>a[5]=true],
    ['path flag',a=>a[6]=0],['path interval',a=>{a[7]=2;a[8]=1;}],
    ['point flag',a=>a[13]=0],['anchor flag',a=>a[20]=0],['mesh queried',a=>a[24]=0],['mesh enum',a=>a[26]=6],
    ['mesh reason',a=>a[28]=12],['distance interval',a=>{a[30]=2;a[31]=1;}],['distance flag',a=>a[29]=0],
    ['displacement root lost',a=>a[38]=0],['error root lost',a=>a[41]=0],['clearance lost',a=>a[44]=0],
    ['sqrt work',a=>a[53]++],['total work',a=>a[55]++],['exact flag',a=>a[60]=2],['padding sign',a=>a[61]=-0],['padding',a=>a[63]=1],
    ['short',a=>a.pop()],['tail',a=>a.push(0)],['nonfinite',a=>a[30]=Infinity],['sparse',a=>delete a[7]]];
  rejectsEdits('static-face',edits.map(([label,edit])=>changed(label,q=>q.audits[0],edit)));
  rejectsEdits('sqrt-reservation-before-mesh',[changed('absent distance -0',q=>q.audits[0],a=>a[30]=-0),changed('fake mesh status',q=>q.audits[0],a=>a[25]=1)]);
});

test('leaf current frontier and witness require full cover left prefix strict certificate and valid audit links',()=>{
  rejectsEdits('static-face',[
    changed('leaf coverage hole',q=>q.leaves[0],a=>a[1]=.5),changed('leaf audit',q=>q.leaves[0],a=>a[5]=1),changed('leaf nonpositive',q=>q.leaves[0],a=>a[3]=0),
    changed('leaf short',q=>q.leaves[0],a=>a.pop()),changed('leaf integer type',q=>q.leaves[0],a=>a[2]=false)]);
  rejectsEdits('evaluation-budget',[
    changed('current ordinal',q=>q.current,a=>a[0]=1),changed('current hole',q=>q.current,a=>a[1]=.25),
    changed('frontier ordinal',q=>q.frontier[0],a=>a[0]=1),changed('frontier hole',q=>q.frontier[0],a=>a[1]=.75),
    changed('frontier tail',q=>q.frontier[0],a=>a.push(0))]);
  rejectsEdits('endpoints-outside-interior-penetration',[
    changed('witness ordinal',q=>q.witness,a=>a[0]=1),changed('witness outside cell',q=>q.witness,a=>a[4]=2),
    changed('witness point',q=>q.witness,a=>a[5]=123),changed('witness anchor',q=>q.witness,a=>a[11]=123),
    changed('witness error',q=>q.witness,a=>a[14]=-1),changed('witness not strict',q=>q.witness,a=>a[16]=0),
    changed('witness audit',q=>q.witness,a=>a[17]=255),changed('witness short',q=>q.witness,a=>a.pop())]);
});

test('last mesh and candidate decoder use only the linked trajectory snapshot and preserve KKT signs',()=>{
  rejectsEdits('static-face',[
    changed('mesh count',q=>q.lastHeader,a=>a[3]++),changed('mesh padding',q=>q.lastHeader,a=>a[23]=-0),
    changed('mesh work',q=>q.lastHeader,a=>a[10]++),changed('wrong row ID',q=>q.rows[0].packet,a=>a[3]=999),
    changed('wrong row work',q=>q.rows[0].packet,a=>a[7]=6),changed('bad geometry',q=>q.rows[0].packet,a=>a[40]=2),
    changed('candidate ordinal',q=>q.rows[0].candidates[0],a=>a[0]=1),changed('candidate unused -0 lost',q=>q.rows[0].candidates[0],a=>a[9]=0),
    changed('candidate tail',q=>q.rows[0].candidates[0],a=>a.push(0)),changed('candidate nonfinite',q=>q.rows[0].candidates[0],a=>a[3]=NaN)]);
  const q=capture(),r=invoke(replay(q).r,q.input),saved=structuredClone(r);q.sources[0].fill(0);q.audits[0].fill(0);q.rows[0].packet.fill(0);q.rows[0].candidates[0].fill(0);assert.deepEqual(r,saved);
  assert.ok(Object.is(r.lastMesh.rows[0].query.candidates[0].kkt[0][0],-0));
});

test('synthetic unreturned sqrt work retains failure DTO and conservative reservation without inventing geometry',()=>{
  // This is an artificial wire packet, not an executed C++ allocation/sqrt exception.
  const q=capture(),h=q.header,a=q.audits[0],primitive=a[53];
  h[0]=5;h[1]=13;h[6]=0;h[9]=0;h[10]=0;h[11]=0;h[13]=1;
  q.leaves=[];q.current=[0,0,1,0];a[5]=4;
  for(const at of [38,41,44,47])a.fill(0,at,at+3);
  for(const [packet,start] of [[a,50],[h,19]]){
    packet[start+4]=0;packet[start+5]=primitive;packet[start+6]=primitive+512;
    packet[start+8]=1;packet[start+9]=0;packet[start+10]=0;
  }
  const r=invoke(replay(q).r,q.input);assert.equal(r.status,'numerical_failure');assert.equal(r.reason,'nonfinite_intermediate');
  assert.equal(r.work.workExact,false);assert.equal(r.work.sqrtRefinementsUpper,r.work.sqrtRefinements+512);
  assert.equal(r.witness,null);assert.equal(r.safePrefix,null);assert.equal(r.audits[0].displacementRoot,null);assert.ok(r.lastMesh);
  assert.deepEqual(r.current,{parameter:[0,1],depth:0});assert.deepEqual(r.certifiedLeaves,[]);
  // Unknown work cannot be relabelled separated, made exact or stripped of its reservation.
  for(const edit of [p=>p.header[0]=0,p=>p.header[29]=1,p=>p.header[25]=primitive,p=>p.audits[0][56]=primitive]){
    const altered=structuredClone(q);edit(altered);assert.throws(()=>invoke(replay(altered).r,altered.input));
  }
});
