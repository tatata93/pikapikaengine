import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const sphere=()=>({position:[1,1,1],radius:.5});
const flat=(id,y=0)=>({id,vertices:[[-0,y,0],[4,y,0],[0,y,4]]});
const names=['_pp_sim_sphere_triangle_mesh_begin','_pp_sim_sphere_triangle_mesh_append','_pp_sim_sphere_triangle_mesh',
  '_pp_sim_sphere_triangle_mesh_source','_pp_sim_sphere_triangle_mesh_row','_pp_sim_sphere_triangle_mesh_candidate'];
function capture(triangles=[flat(37),flat(5)],settings={}){
  const expected=runtime.querySphereTriangleMesh(sphere(),triangles,settings),m=runtime.native;
  runtime.check(m._pp_sim_sphere_triangle_mesh(14));const header=runtime.output(),sources=[],rows=[];
  for(let i=0;i<triangles.length;++i){
    runtime.check(m._pp_sim_sphere_triangle_mesh_source(i));const source=runtime.output();sources.push(source);
    if(!source[12]){rows.push(null);continue;}
    runtime.check(m._pp_sim_sphere_triangle_mesh_row(i));const packet=runtime.output(),candidates=[];
    for(let j=0;j<packet[6];++j){runtime.check(m._pp_sim_sphere_triangle_mesh_candidate(i,j));candidates.push(runtime.output());}
    rows.push({packet,candidates});
  }
  return {header,sources,rows,expected,triangles,settings};
}
function replay(snapshot){
  let packet=snapshot.header;const calls={begins:0,appends:0,inputs:0};
  const m={_pp_sim_api_version:()=>1,_pp_sim_sphere_triangle_mesh_begin:()=>{calls.begins++;return 0;},
    _pp_sim_sphere_triangle_mesh_append:()=>{calls.appends++;return 0;},_pp_sim_sphere_triangle_mesh:()=>{packet=snapshot.header;return 0;},
    _pp_sim_sphere_triangle_mesh_source:i=>{packet=snapshot.sources[i];return 0;},
    _pp_sim_sphere_triangle_mesh_row:i=>{packet=snapshot.rows[i].packet;return 0;},
    _pp_sim_sphere_triangle_mesh_candidate:(i,j)=>{packet=snapshot.rows[i].candidates[j];return 0;}};
  const r=new SimulationRuntime(m,{},0,0);r.inputF64=v=>{calls.inputs++;return v.length;};r.output=()=>[...packet];return {r,calls};
}

test('mesh bridge checks all six old SDK capabilities before reading or writing input',()=>{
  for(const missing of names){
    const m=Object.fromEntries(names.map(name=>[name,()=>assert.fail('old SDK called')]));m._pp_sim_api_version=()=>1;delete m[missing];
    const r=new SimulationRuntime(m,{},0,0);r.inputF64=()=>assert.fail('old scratch touched');
    assert.throws(()=>r.querySphereTriangleMesh(null,null),/mesh API unavailable/);
  }
});
test('mesh host validation owns and validates the full late source before beginning staging',()=>{
  for(const input of [[flat(1),{...flat(2),id:0}],Array.from({length:65},(_,i)=>flat(i+1)),[flat(1),{id:2,vertices:[]}],
    [flat(1),{...flat(2),vertices:[[0,0,0],[4,0,0],[0,0,Infinity]]}]]){
    const q=replay({});assert.throws(()=>q.r.querySphereTriangleMesh(sphere(),input));assert.deepEqual(q.calls,{begins:0,appends:0,inputs:0});
  }
  for(const settings of [{maxSurfaces:-1},{primitive:{maxCandidates:.5}},{primitive:{maximumLocalWidth:NaN}}]){
    const q=replay({});assert.throws(()=>q.r.querySphereTriangleMesh(sphere(),[flat(1)],settings));assert.equal(q.calls.begins,0);
  }
});
test('actual mesh WASM keeps all 64 original surfaces and exact ties across eleven chunks',()=>{
  const input=Array.from({length:64},(_,i)=>flat(64-i)),before=structuredClone(input),r=runtime.querySphereTriangleMesh(sphere(),input);
  assert.equal(r.status,'completed');assert.equal(r.reason,'none');assert.equal(r.queries,64);assert.equal(r.candidatesExamined,448);
  assert.equal(r.rows.length,64);assert.equal(r.rows.at(-1).triangle.id,1);assert.deepEqual(r.nearest.possibleSurfaceIds,Array.from({length:64},(_,i)=>i+1));
  assert.ok(r.nearest.distance[0]<=1&&r.nearest.distance[1]>=1);assert.deepEqual(input,before);assert.ok(Object.is(r.rows[0].triangle.vertices[0][0],-0));
  const saved=structuredClone(r);input[0].id=999;input[0].vertices[0][0]=9;runtime.querySphereTriangleMesh(sphere(),[flat(123)]);assert.deepEqual(r,saved);
  r.rows[0].query.geometry.closest[0][0]=999;assert.deepEqual(runtime.querySphereTriangleMesh(sphere(),before),saved);
});
test('bounded mesh input copies indexed components without invoking caller iterators',()=>{
  const surfaces=[flat(37)],s=sphere(),unexpected=()=>assert.fail('caller iterator invoked');
  surfaces[Symbol.iterator]=unexpected;surfaces[0].vertices[Symbol.iterator]=unexpected;
  surfaces[0].vertices.forEach(v=>v[Symbol.iterator]=unexpected);s.position[Symbol.iterator]=unexpected;
  const r=runtime.querySphereTriangleMesh(s,surfaces);assert.equal(r.status,'completed');assert.equal(r.rows.length,1);assert.equal(r.rows[0].triangle.id,37);
});
test('actual mesh preserves distinct opposing normals and excludes only proved dominance',()=>{
  const faces=[{id:99,vertices:[[-1,-2,-2],[-1,2,-2],[-1,0,2]]},{id:7,vertices:[[1,-2,-2],[1,2,-2],[1,0,2]]}];
  const r=runtime.querySphereTriangleMesh({position:[0,0,0],radius:.25},faces);
  assert.deepEqual(r.nearest.possibleSurfaceIds,[7,99]);assert.ok(r.rows[0].query.geometry.normal[0][0]>0);assert.ok(r.rows[1].query.geometry.normal[0][1]<0);
  assert.equal('normal' in r.nearest,false);assert.equal('closest' in r.nearest,false);
  const d=runtime.querySphereTriangleMesh(sphere(),[flat(37),flat(99,-4)]);assert.deepEqual(d.nearest.possibleSurfaceIds,[37]);
  const reversed=runtime.querySphereTriangleMesh(sphere(),[flat(99,-4),flat(37)]);assert.deepEqual(reversed.nearest,d.nearest);assert.equal(reversed.rows[0].triangle.id,99);
});
test('actual mesh failures retain all later diagnostics and recover from preflight and budgets',()=>{
  const bad={id:99,vertices:[[0,0,0],[4,0,0],[8,0,0]]};
  const r=runtime.querySphereTriangleMesh(sphere(),[flat(37),bad,flat(5,-4)]);
  assert.equal(r.status,'row_failure');assert.equal(r.reason,'row_failed');assert.equal(r.nearest,null);assert.equal(r.queries,3);assert.equal(r.firstFailedRow,1);assert.equal(r.failedRows,1);
  assert.equal(r.rows[1].query.status,'degenerate');assert.equal(r.rows[2].query.status,'completed');
  for(const [triangles,settings,status,reason] of [[[],{},'invalid_input','surface_count'],[[flat(37),flat(37)],{},'invalid_input','duplicate_id'],
    [[flat(37),flat(5)],{maxSurfaces:1},'budget_exceeded','surface_budget'],[[flat(1)],{primitive:{maxCandidates:0}},'invalid_input','settings']]){
    const result=runtime.querySphereTriangleMesh(sphere(),triangles,settings);assert.equal(result.status,status);assert.equal(result.reason,reason);assert.equal(result.nearest,null);assert.deepEqual(result.rows,[]);assert.equal(result.queries,0);
    assert.equal(runtime.querySphereTriangleMesh(sphere(),[flat(1)]).status,'completed');
  }
  const width=runtime.querySphereTriangleMesh(sphere(),[flat(1),flat(2)],{primitive:{maximumNormalWidth:1e-30}});
  assert.equal(width.status,'row_failure');assert.equal(width.failedRows,2);assert.equal(width.nearest,null);
});
test('mesh decoder checks every aggregate count interval flag and possible ID without stale geometry',()=>{
  const good=capture();assert.deepEqual(replay(good).r.querySphereTriangleMesh(sphere(),good.triangles),good.expected);
  const edits=[a=>a.pop(),a=>a.push(0),a=>a[0]=6,a=>a[1]=12,a=>a[1]=1,a=>a[2]=2,a=>a[2]=0,a=>a[3]=1,a=>a[4]=1,
    a=>a[5]=1,a=>a[7]=1,a=>a[9]=1,a=>a[10]++,a=>a[11]++,a=>a[12]++,a=>a[13]=1,a=>a[14]=1,a=>a[15]=0,a=>a[17]=-1,a=>a[19]=1e90,a=>a[21]=-0,a=>a[23]=Infinity];
  for(const edit of edits){const q=structuredClone(good);edit(q.header);assert.throws(()=>replay(q).r.querySphereTriangleMesh(sphere(),q.triangles),/C\+\+ sphere triangle mesh/);}
  for(const edit of [a=>a.pop(),a=>a.push(0),a=>a[0]=1,a=>a[1]=99,a=>a[2]=0,a=>a[3]=NaN,a=>a[11]=0,a=>a[12]=0,a=>a[13]=0,a=>a[13]=2]){
    const q=structuredClone(good);edit(q.sources[0]);assert.throws(()=>replay(q).r.querySphereTriangleMesh(sphere(),q.triangles),/C\+\+ sphere triangle mesh/);
  }
});
test('mesh row and candidate decoding cannot silently read the independent single snapshot',()=>{
  const good=capture();
  for(const edit of [p=>p.rows[0].packet[3]=999,p=>p.rows[0].packet[6]=6,p=>p.rows[0].packet[52]=0,p=>p.rows[0].packet[40]=2,
    p=>p.rows[0].candidates[0][0]=1,p=>p.rows[0].candidates[0][9]=0,p=>p.rows[0].candidates[0].push(0)]){
    const q=structuredClone(good);edit(q);assert.throws(()=>replay(q).r.querySphereTriangleMesh(sphere(),q.triangles),/C\+\+ sphere triangle/);
  }
  const result=replay(good).r.querySphereTriangleMesh(sphere(),good.triangles);good.sources.forEach(s=>s.fill(0));good.rows.forEach(r=>r.packet.fill(0));assert.equal(result.rows[0].triangle.id,37);assert.equal(result.rows[0].query.geometry.surfaceId,37);
});
test('preflight and model failure packets cannot publish a nearest or erase failed work',()=>{
  const invalid=capture([flat(37),flat(37)]),rowFailure=capture([flat(37),{id:99,vertices:[[0,0,0],[4,0,0],[8,0,0]]}]);
  for(const snapshot of [invalid,rowFailure]){
    assert.deepEqual(replay(snapshot).r.querySphereTriangleMesh(sphere(),snapshot.triangles),snapshot.expected);
    for(const edit of [a=>a[2]=1,a=>a[14]=1,a=>a[15]=-0,a=>a[19]=1]){
      const q=structuredClone(snapshot);edit(q.header);assert.throws(()=>replay(q).r.querySphereTriangleMesh(sphere(),q.triangles),/C\+\+ sphere triangle mesh/);
    }
  }
  for(const edit of [a=>a[13]=0,a=>a[7]=0,a=>a[8]=0]){
    const q=structuredClone(rowFailure);edit(q.header);assert.throws(()=>replay(q).r.querySphereTriangleMesh(sphere(),q.triangles),/C\+\+ sphere triangle mesh/);
  }
});
test('actual staging and query records remain independent of single queries and rejected operations',()=>{
  runtime.querySphereTriangleMesh(sphere(),[flat(37),flat(5)]);const m=runtime.native;
  runtime.check(m._pp_sim_sphere_triangle_mesh_source(1));const saved=runtime.output();
  runtime.check(m._pp_sim_sphere_triangle_mesh_begin(1));assert.deepEqual(runtime.output(),saved);
  for(const call of [()=>m._pp_sim_sphere_triangle_mesh_begin(65),()=>m._pp_sim_sphere_triangle_mesh_append(9),()=>m._pp_sim_sphere_triangle_mesh(14),
    ()=>m._pp_sim_sphere_triangle_mesh_source(2),()=>m._pp_sim_sphere_triangle_mesh_row(2),()=>m._pp_sim_sphere_triangle_mesh_candidate(0,7)]){
    assert.notEqual(call(),0);assert.deepEqual(runtime.output(),saved);
  }
  runtime.querySphereTriangle(sphere(),flat(777));runtime.check(m._pp_sim_sphere_triangle_mesh_source(1));assert.deepEqual(runtime.output(),saved);
  runtime.check(m._pp_sim_reset());assert.notEqual(m._pp_sim_sphere_triangle_mesh_source(0),0);assert.notEqual(m._pp_sim_sphere_triangle_mesh(14),0);
  assert.equal(runtime.querySphereTriangleMesh(sphere(),[flat(1)]).status,'completed');
});
