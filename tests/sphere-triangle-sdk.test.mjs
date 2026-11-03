import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const sphere=()=>({position:[.25,.25,2],radius:.5});
const triangle=()=>({id:53,vertices:[[0,0,0],[1,0,0],[0,1,0]]});
function capture(){
 const expected=runtime.querySphereTriangle(sphere(),triangle());
 // Re-issue to retain the summary before ordinal getters replace the output.
 runtime.check(runtime.native._pp_sim_sphere_triangle(24));const summary=runtime.output();
 const candidates=Array.from({length:summary[6]},(_,i)=>{runtime.check(runtime.native._pp_sim_sphere_triangle_candidate(i));return runtime.output();});
 return {expected,summary,candidates};
}
function replay(snapshot){
 let packet=snapshot.summary;const calls={inputs:0,queries:0,getters:[]};
 const m={_pp_sim_api_version:()=>1,_pp_sim_sphere_triangle:()=>{calls.queries++;packet=snapshot.summary;return 0;},_pp_sim_sphere_triangle_candidate:i=>{calls.getters.push(i);packet=snapshot.candidates[i];return 0;}};
 const r=new SimulationRuntime(m,{},0,0);r.inputF64=v=>{calls.inputs++;return v.length;};r.output=()=>[...packet];return {r,calls};
}
test('sphere triangle bridge refuses old SDK capabilities before touching exchange scratch',()=>{
 for(const missing of ['_pp_sim_sphere_triangle','_pp_sim_sphere_triangle_candidate']){
  const native={_pp_sim_api_version:()=>1,_pp_sim_sphere_triangle:()=>0,_pp_sim_sphere_triangle_candidate:()=>0};delete native[missing];
  const r=new SimulationRuntime(native,{},0,0);r.inputF64=()=>assert.fail('old SDK input touched');assert.throws(()=>r.querySphereTriangle(sphere(),triangle()),/API unavailable/);
 }
});
test('actual main WASM encloses analytic face edge vertex and backside contacts with owned input/output',()=>{
 const example=runtime.querySphereTriangle({position:[2,3,-4],radius:4},{id:17,vertices:[[0,0,0],[4,0,0],[0,0,4]]});
 assert.equal(example.status,'completed');
 for(const [interval,value]of [[example.geometry.distance,5],[example.geometry.gap,1],...example.geometry.normal.map((v,i)=>[v,[0,.6,-.8][i]])])assert.ok(interval[0]<=value&&value<=interval[1]);
 const cases=[[[.25,.25,2],[.25,.25,0],'face'],[[.5,-1,2],[.5,0,0],'edge_ab'],[[-1,-1,2],[0,0,0],'vertex_a'],[[.25,.25,-2],[.25,.25,0],'face']];
 for(const [position,closest,feature]of cases){
  const s={position,radius:.5},t=triangle(),before=structuredClone({s,t}),r=runtime.querySphereTriangle(s,t);
  assert.equal(r.status,'completed');assert.equal(r.reason,'none');assert.equal(r.geometry.relation,'separated');assert.equal(r.geometry.surfaceId,53);assert.equal(r.candidatesExamined,7);assert.equal(r.candidates.length,7);
  closest.forEach((v,i)=>assert.ok(r.geometry.closest[i][0]<=v&&v<=r.geometry.closest[i][1]));assert.ok(r.candidates.some(c=>c.feature===feature&&c.disposition==='retained'));
  assert.deepEqual({s,t},before);const saved=structuredClone(r);runtime.querySphereTriangle(sphere(),triangle());assert.deepEqual(r,saved);
  r.geometry.closest[0][0]=999;r.candidates[0].barycentric[0][0]=999;assert.deepEqual(runtime.querySphereTriangle(s,t),saved);
 }
});
test('actual WASM separates model failure from host rejection and recovers without fabricated geometry',()=>{
 const cases=[{s:{...sphere(),radius:0},status:'invalid_input',reason:'input_domain'},
  {t:{...triangle(),vertices:[[0,0,0],[1,0,0],[2,0,0]]},status:'degenerate',reason:'zero_cross'},
  {settings:{maxCandidates:1},status:'budget_exceeded',reason:'candidate_budget'},
  {settings:{maximumNormalWidth:1e-30},status:'quality_unresolved',reason:'normal_width'}];
 for(const q of cases){const r=runtime.querySphereTriangle(q.s??sphere(),q.t??triangle(),q.settings);assert.equal(r.status,q.status);assert.equal(r.reason,q.reason);assert.equal(r.geometry,null);assert.equal(runtime.querySphereTriangle(sphere(),triangle()).status,'completed');}
 for(const settings of [{maxCandidates:0},{sqrtRefinements:257},{maxTotalSqrtRefinements:0},{minimumSineSquared:2}])assert.equal(runtime.querySphereTriangle(sphere(),triangle(),settings).reason,'settings');
 for(const settings of [{maxCandidates:-1},{sqrtRefinements:.5},{maxTotalSqrtRefinements:2**32},{maximumLocalWidth:Infinity}])assert.throws(()=>runtime.querySphereTriangle(sphere(),triangle(),settings));
 for(const id of [0,2**53,.5,NaN])assert.throws(()=>runtime.querySphereTriangle(sphere(),{...triangle(),id}));
 assert.throws(()=>runtime.querySphereTriangle({...sphere(),position:[NaN,0,0]},triangle()));
 assert.throws(()=>runtime.querySphereTriangle(sphere(),{...triangle(),vertices:[]}));
});
test('all 58 summary fields and candidate records are owned, ordered and checked before return',()=>{
 const snapshot=capture();assert.deepEqual(replay(snapshot).r.querySphereTriangle(sphere(),triangle()),snapshot.expected);
 const edits=[a=>a.pop(),a=>a.push(0),a=>a[0]=.5,a=>a[0]=8,a=>a[1]=18,a=>a[1]=1,a=>a[2]=2,a=>a[2]=0,a=>a[3]=54,a=>a[4]=0,a=>a[4]=128,a=>a[5]=1,a=>a[6]=6,a=>a[7]=6,a=>a[8]=.5,a=>a[8]=513,a=>a[9]=2,a=>a[10]=0,a=>a[13]=0,a=>a[11]=-1,a=>a[14]=2,a=>a[16]=2,a=>a[40]=-2,a=>a[52]=0,a=>a[54]=0,a=>a[28]=NaN,a=>a[56]=Infinity];
 for(const edit of edits){const bad=structuredClone(snapshot);edit(bad.summary);assert.throws(()=>replay(bad).r.querySphereTriangle(sphere(),triangle()),/C\+\+ sphere triangle/);}
 for(const edit of [a=>a.pop(),a=>a.push(0),a=>a[0]=1,a=>a[1]=3,a=>a[1]=.5,a=>a[2]=1,a=>a[3]=Infinity,a=>a[3]=a[4]+1,a=>a[9]=0,a=>a[10]=-0]){
  const bad=structuredClone(snapshot);edit(bad.candidates[0]);assert.throws(()=>replay(bad).r.querySphereTriangle(sphere(),triangle()),/C\+\+ sphere triangle/);
 }
 const r=replay(snapshot).r.querySphereTriangle(sphere(),triangle());assert.ok(Object.is(r.candidates[0].kkt[0][0],-0));assert.ok(Object.is(r.candidates[0].kkt[0][1],0));
 snapshot.summary.fill(0);snapshot.candidates.forEach(c=>c.fill(0));assert.ok(Object.is(r.candidates[0].kkt[0][0],-0));assert.equal(r.geometry.surfaceId,53);
});
test('failure packet padding and optional diagnostics cannot masquerade as completed geometry',()=>{
 const s=capture(),failure=Array(58).fill(0);failure[0]=1;failure[1]=1;failure[3]=53;s.summary=failure;s.candidates=[];
 assert.equal(replay(s).r.querySphereTriangle(sphere(),triangle()).geometry,null);
 for(const edit of [a=>a[4]=1,a=>a[5]=1,a=>a[11]=1,a=>a[14]=-0,a=>a[16]=-0,a=>a[57]=1,a=>a[13]=1,a=>a[2]=1,a=>a[7]=8,a=>a[7]=7]){const q=structuredClone(s);edit(q.summary);assert.throws(()=>replay(q).r.querySphereTriangle(sphere(),triangle()),/C\+\+ sphere triangle/);}
});
test('actual rejected exchanges and getters retain previous output bits and independent triangle snapshot',()=>{
 const good=capture(),m=runtime.native;runtime.check(m._pp_sim_sphere_triangle_candidate(0));const saved=runtime.output();
 for(const call of [()=>m._pp_sim_sphere_triangle(23),()=>m._pp_sim_sphere_triangle_candidate(7)]){assert.notEqual(call(),0);assert.deepEqual(runtime.output(),saved);}
 const p=m._pp_sim_input_f64_ptr()/8,source=Array.from(m.HEAPF64.subarray(p,p+24));
 for(const edit of [v=>v[4]=0,v=>v[14]=.5,v=>v[20]=1,v=>v[0]=NaN]){const bad=[...source];edit(bad);m.HEAPF64.set(bad,p);assert.notEqual(m._pp_sim_sphere_triangle(24),0);assert.deepEqual(runtime.output(),saved);runtime.check(m._pp_sim_sphere_triangle_candidate(0));assert.deepEqual(runtime.output(),saved);}
 m.HEAPF64.set(source,p);runtime.queryDielectricInterface();runtime.check(m._pp_sim_sphere_triangle_candidate(0));assert.deepEqual(runtime.output(),good.candidates[0]);
 runtime.check(m._pp_sim_reset());assert.notEqual(m._pp_sim_sphere_triangle_candidate(0),0);assert.equal(runtime.querySphereTriangle(sphere(),triangle()).status,'completed');
});
