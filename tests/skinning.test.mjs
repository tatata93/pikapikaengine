import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';
import {defaultMotionSource} from '../engine/motion.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const identity=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
const affine=(x=1,y=1,z=1,t=[0,0,0])=>{const m=identity();m[0]=x;m[5]=y;m[10]=z;m.splice(12,3,...t);return m;};
const rest=()=>[{id:7,matrix:identity()}];
const vertex=(position=[1,2,3],influences=[{id:7,weight:1}])=>({position,influences});
const basic=()=>({joints:runtime.bindSkin(rest()).joints,pose:rest(),vertices:[vertex()]});
const near=(a,b)=>assert.ok(Math.abs(a-b)<=256*Number.EPSILON*Math.max(1,Math.abs(b)),`${a} != ${b}`);
const bits=x=>{const d=new DataView(new ArrayBuffer(8));d.setFloat64(0,x);return d.getBigUint64(0);};

test('actual skin SDK inverse uses affine shear and retains authored matrices and copied snapshots',()=>{
 const matrix=affine(2,4,.5,[1,-2,3]);matrix[4]=.5;matrix[9]=.25;matrix[3]=-0;
 const source=[{id:19,matrix},{id:7,matrix:identity()}],before=structuredClone(source),r=runtime.bindSkin(source);
 assert.equal(r.status,'completed');assert.equal(r.positions,null);assert.deepEqual(r.weightResiduals,[]);assert.deepEqual(r.joints.map(j=>j.id),[19,7]);assert.deepEqual(r.joints[0].restWorld,matrix);
 const expected=[.5,0,0,0,-.0625,.25,0,0,.03125,-.125,2,0,-.71875,.875,-6,1];r.joints[0].inverseBind.forEach((v,i)=>near(v,expected[i]));assert.equal(bits(r.joints[0].restWorld[3]),bits(-0));assert.deepEqual(source,before);
 const saved=structuredClone(r);runtime.bindSkin(rest());assert.deepEqual(r,saved);r.joints[0].inverseBind[0]=99;assert.deepEqual(runtime.bindSkin(source),saved);
});

test('actual skin SDK exact authored ratios and stable IDs are independent of palette and influence order',()=>{
 const source=[{id:7,matrix:identity()},{id:19,matrix:identity()}],joints=runtime.bindSkin(source).joints;
 const input={joints,pose:[{id:19,matrix:affine(1,1,1,[4,0,0])},{id:7,matrix:identity()}],vertices:[vertex([1,2,3],[{id:19,weight:3},{id:7,weight:1}]),vertex([0,0,0],[{id:7,weight:1}])]};
 const before=structuredClone(input),a=runtime.deformSkin(input);assert.equal(a.status,'completed');assert.deepEqual(a.positions,[[4,2,3],[0,0,0]]);assert.equal(a.joints,null);assert.deepEqual(input,before);
 const copy=structuredClone(a);input.pose.reverse();input.joints.reverse();input.vertices[0].influences.reverse();const b=runtime.deformSkin(input);assert.deepEqual(b.positions,a.positions);assert.deepEqual(a,copy);b.positions[0][0]=999;assert.deepEqual(runtime.deformSkin(input).positions,a.positions);
});

test('actual skin SDK retains nonuniform scale/shear and applies inverse bind exactly once',()=>{
 const input=basic();input.pose[0].matrix=affine(2,3,.5);input.pose[0].matrix[4]=.5;input.pose[0].matrix[9]=.25;assert.deepEqual(runtime.deformSkin(input).positions,[[3,6.75,1.5]]);
 const matrix=affine(2,4,.5,[1,-2,3]);matrix[4]=.5;matrix[9]=.25;input.joints=runtime.bindSkin([{id:7,matrix}]).joints;input.pose=[{id:7,matrix}];assert.deepEqual(runtime.deformSkin(input).positions,[[1,2,3]]);
 input.pose[0].matrix=affine(0,1,-1);assert.equal(runtime.deformSkin(input).status,'completed','singular pose is permitted; rest inverse must be nonsingular');
});

test('actual skin SDK matrix blend avoids known cancellation and normalizes maximal/subnormal weights',()=>{
 const input=basic();input.joints.push({id:19,restWorld:identity(),inverseBind:identity()});input.pose=[{id:7,matrix:affine(1,1,1,[2**53,0,0])},{id:19,matrix:affine(1,1,1,[-(2**53),0,0])}];input.vertices=[vertex([1,0,0],[{id:7,weight:1},{id:19,weight:1}])];assert.deepEqual(runtime.deformSkin(input).positions,[[1,0,0]]);
 input.pose=[{id:7,matrix:identity()},{id:19,matrix:affine(1,1,1,[4,0,0])}];input.vertices=[vertex([1,2,3],[{id:7,weight:Number.MAX_VALUE},{id:19,weight:Number.MAX_VALUE}])];assert.deepEqual(runtime.deformSkin(input).positions,[[3,2,3]]);
 const tiny=basic();tiny.vertices[0].influences[0].weight=Number.MIN_VALUE;assert.deepEqual(runtime.deformSkin(tiny).positions,[[1,2,3]]);
});

test('actual skin SDK model failures replace results atomically and retain optional diagnostic failure prefixes',()=>{
 const good=basic(),baseline=runtime.deformSkin(good);
 for(const edit of [q=>q.vertices[0].influences[0].weight=-1,q=>q.pose=[],q=>q.joints.push(structuredClone(q.joints[0])),q=>q.vertices[0].influences.push({id:99,weight:0})]){const q=structuredClone(good);edit(q);const r=runtime.deformSkin(q);assert.equal(r.status,'invalid_input');assert.equal(r.positions,null);assert.equal(runtime.native._pp_sim_skin_deform_record(0,0)!==0,true);assert.deepEqual(runtime.deformSkin(good),baseline);}
 const under=structuredClone(good);under.joints.push({id:19,restWorld:identity(),inverseBind:identity()});under.pose.push({id:19,matrix:identity()});under.vertices[0].influences=[{id:7,weight:Number.MIN_VALUE},{id:19,weight:Number.MAX_VALUE}];const r=runtime.deformSkin(under);assert.equal(r.status,'numerical_failure');assert.equal(r.positions,null);assert.equal(under.vertices[0].influences[0].weight,Number.MIN_VALUE);
 const singular=runtime.bindSkin([{id:7,matrix:affine(1,0,1)}]);assert.equal(singular.status,'ill_conditioned');assert.equal(singular.joints,null);assert.equal(singular.diagnostics.length,1);assert.equal(singular.diagnostics[0].pivotFailure,true);assert.equal(singular.diagnostics[0].condition,null);assert.equal(singular.diagnostics[0].residual,null);
 assert.deepEqual(runtime.deformSkin(good),baseline);
});

test('actual skin SDK simultaneous 128 bones 2048 vertices 8192 influences and explicit one-over rejection',()=>{
 const source=Array.from({length:128},(_,j)=>({id:j+1,matrix:identity()})),joints=runtime.bindSkin(source).joints;
 const input={joints,pose:source,vertices:Array.from({length:2048},(_,j)=>vertex([j/4096,0,0],Array.from({length:4},(_,k)=>({id:k+1,weight:1}))))};
 const result=runtime.deformSkin(input);assert.equal(result.status,'completed');assert.equal(result.positions.length,2048);assert.deepEqual(result.positions,input.vertices.map(v=>v.position));assert.equal(result.diagnostics.length,128);assert.equal(result.weightResiduals.length,2048);
 assert.equal(runtime.deformSkin(input,{maximumVertices:65536,maximumInfluences:262144}).status,'completed');
 for(const settings of [{maximumBones:127},{maximumVertices:2047},{maximumInfluences:8191}]){const r=runtime.deformSkin(input,settings);assert.equal(r.status,'budget_exceeded');assert.equal(r.positions,null);}
 assert.throws(()=>runtime.bindSkin([...source,{id:129,matrix:identity()}]),/128 bones/);
 assert.throws(()=>runtime.deformSkin({...input,vertices:[...input.vertices,vertex()]}),/2048 vertices/);
 const excess=structuredClone(input);excess.vertices[0].influences.push({id:5,weight:1});assert.throws(()=>runtime.deformSkin(excess),/8192/);
 assert.equal(runtime.deformSkin(input).status,'completed');
});

test('actual skin SDK finite model domain differs from host exchange rejection and supports empty output',()=>{
 for(const settings of [{maximumCondition:.5},{maximumInverseResidual:1e-16}])assert.equal(runtime.bindSkin(rest(),settings).status,'invalid_input');
 const duplicate=[...rest(),...rest()];assert.equal(runtime.bindSkin(duplicate).status,'invalid_input');assert.equal(runtime.bindSkin([]).status,'invalid_input');
 const input=basic();input.vertices=[];const r=runtime.deformSkin(input);assert.equal(r.status,'completed');assert.deepEqual(r.positions,[]);
 const outside=basic();outside.pose[0].matrix[12]=1e100;assert.deepEqual(runtime.deformSkin(outside).positions,[[1e100,2,3]]);
 for(const source of [[{id:0,matrix:identity()}],[{id:2**53,matrix:identity()}],[{id:7,matrix:Array(16).fill(NaN)}],Array(1)])assert.throws(()=>runtime.bindSkin(source));
 const sparse=basic();sparse.vertices=Array(1);assert.throws(()=>runtime.deformSkin(sparse));
 assert.throws(()=>runtime.bindSkin(rest(),{maximumBones:0}));assert.equal(runtime.bindSkin(rest()).status,'completed');
});

test('actual skin SDK bad exchanges and getters retain output and both bind/deform records',()=>{
 const input=basic(),deform=runtime.deformSkin(input),bind=runtime.bindSkin(rest()),m=runtime.native;
 runtime.check(m._pp_sim_skin_deform_record(0,0));const savedPosition=runtime.output();
 runtime.check(m._pp_sim_skin_bind_record(0,0));const saved=runtime.output();
 for(const call of [()=>m._pp_sim_skin_bind_record(9,0),()=>m._pp_sim_skin_bind_record(0,1),()=>m._pp_sim_skin_deform_record(9,0),()=>m._pp_sim_skin_bind(1),()=>m._pp_sim_skin_deform(1)]){assert.notEqual(call(),0);assert.deepEqual(runtime.output(),saved);}
 const packet=[1,128,65536,262144,1e10,1e-10,0,0,7,...identity()];
 for(const change of [p=>p[6]=1,p=>p[8]=0,p=>p[2]=65537,p=>p[9]=Infinity]){const p=[...packet];change(p);const address=m._pp_sim_input_f64_ptr()/8;m.HEAPF64.set(p,address);assert.notEqual(m._pp_sim_skin_bind(p.length),0);assert.deepEqual(runtime.output(),saved);runtime.check(m._pp_sim_skin_bind_record(0,0));assert.deepEqual(runtime.output(),saved);}
 const deformPacket=[1,1,1,1,128,65536,262144,1e10,1e-10,0,0,0,7,...identity(),...identity(),7,...identity(),1,2,3,1,7,1];
 for(const change of [p=>p[9]=1,p=>p[3]=2,p=>p[65]=0,p=>p[66]=0,p=>p[2]=2049]){const p=[...deformPacket];change(p);m.HEAPF64.set(p,m._pp_sim_input_f64_ptr()/8);assert.notEqual(m._pp_sim_skin_deform(p.length),0);assert.deepEqual(runtime.output(),saved);runtime.check(m._pp_sim_skin_deform_record(0,0));assert.deepEqual(runtime.output(),savedPosition);runtime.check(m._pp_sim_skin_bind_record(0,0));assert.deepEqual(runtime.output(),saved);}
 assert.deepEqual(runtime.bindSkin(rest()),bind);assert.deepEqual(runtime.deformSkin(input),deform);
});

test('actual skin SDK leaves motion optics and World records independent; reset invalidates only live records',()=>{
 const m=runtime.native,source=defaultMotionSource(),pose=runtime.sampleMotion(source,1),world=runtime.createWorld(),before=world.info(),input=basic();
 runtime.check(m._pp_sim_motion_bone(3));const motion=runtime.output();const skin=runtime.deformSkin(input);const bind=runtime.bindSkin(rest());runtime.queryDielectricInterface();runtime.check(m._pp_sim_motion_bone(3));assert.deepEqual(runtime.output(),motion);assert.deepEqual(world.info(),before);assert.deepEqual(runtime.sampleMotion(source,1),pose);assert.deepEqual(runtime.deformSkin(input),skin);assert.deepEqual(runtime.bindSkin(rest()),bind);world.dispose();
 runtime.check(m._pp_sim_reset());for(const call of [()=>m._pp_sim_skin_bind_record(0,0),()=>m._pp_sim_skin_deform_record(0,0),()=>m._pp_sim_motion_bone(0)])assert.notEqual(call(),0);
 assert.deepEqual(runtime.bindSkin(rest()),bind);assert.deepEqual(runtime.deformSkin(input),skin);
});

test('skin bridge fails explicitly when shipped SDK lacks new exports',()=>{
 const old={_pp_sim_api_version:()=>1},stub=new SimulationRuntime(old,{},0,0);assert.throws(()=>stub.bindSkin(rest()),/API unavailable/);assert.throws(()=>stub.deformSkin({joints:[],pose:[],vertices:[]}),/API unavailable/);
});

test('skin bridge rejects corrupted summary and optional record flags without treating them as valid model data',()=>{
 const run=({summary=[0,1,1,1,0,0,0,0],joint=[7,...identity(),...identity()],diagnostic=[7,1,1,1,0,0]}={})=>{
  let current=summary;
  const native={_pp_sim_api_version:()=>1,_pp_sim_skin_bind:()=>0,_pp_sim_skin_deform:()=>0,
   _pp_sim_skin_bind_record:kind=>{current=kind===0?joint:diagnostic;return 0;},_pp_sim_skin_deform_record:()=>0};
  const bridge=new SimulationRuntime(native,{},0,0);bridge.inputF64=values=>values.length;bridge.output=()=>[...current];return bridge.bindSkin(rest());
 };
 assert.equal(run().status,'completed');
 for(const edit of [a=>a[0]=5,a=>a[1]=2,a=>a[1]=0,a=>a[2]=2,a=>a[3]=2,a=>a[4]=1,a=>a[5]=1,a=>a[0]=NaN]){const summary=[0,1,1,1,0,0,0,0];edit(summary);assert.throws(()=>run({summary}),/C\+\+ skin/);}
 assert.throws(()=>run({joint:[19,...identity(),...identity()]}),/stable ID/);assert.throws(()=>run({joint:Array(32).fill(0)}),/skin record/);
 for(const edit of [d=>d[1]=2,d=>d[3]=2,d=>d[5]=2,d=>d[1]=0,d=>d[2]=-1,d=>d[0]=19]){const diagnostic=[7,1,1,1,0,0];edit(diagnostic);assert.throws(()=>run({diagnostic}),/skin diagnostic/);}
});
