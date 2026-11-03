import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {defaultMotionSource,sampleMotion} from '../engine/motion.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const near=(a,b)=>assert.ok(Math.abs(a-b)<2e-12,`${a} != ${b}`);
const pose=(position=[0,0,0],rotation=[0,0,0,1],scale=[1,1,1])=>({position,rotation,scale});

test('actual motion WASM known FK keeps authored source and copied snapshots independent',()=>{
 const source=defaultMotionSource(),before=JSON.stringify(source),r=sampleMotion(runtime,source,1),tip=r.bones.find(b=>b.id===4);assert.equal(r.status,'completed');near(tip.worldPosition[0],1);near(tip.worldPosition[1],2);assert.deepEqual(r.evaluationOrder,[1,2,3,4]);assert.equal(JSON.stringify(source),before);
 const snapshot=structuredClone(r);sampleMotion(runtime,source,.25);assert.deepEqual(r,snapshot);tip.worldPosition[0]=999;assert.notEqual(tip.worldMatrix[12],999);assert.deepEqual(sampleMotion(runtime,source,1),snapshot);
});

test('actual motion WASM arbitrary source order retains full shear and ready-ID topological ordering',()=>{
 const source=defaultMotionSource();source.clip.tracks=[];source.bones[0].rest.scale=[2,1,1];source.bones[1].rest.rotation=[0,0,1,2];source.bones.reverse();const r=runtime.sampleMotion(source,0),m=r.bones.find(b=>b.id===2).worldMatrix;assert.deepEqual(r.bones.map(b=>b.id),[4,3,2,1]);assert.deepEqual(r.evaluationOrder,[1,2,3,4]);near(m[0]*m[4]+m[1]*m[5],-36/25);
 const branches={bones:[{id:40,parentId:20,rest:pose()},{id:30,parentId:10,rest:pose()},{id:10,parentId:0,rest:pose()},{id:20,parentId:10,rest:pose()}],clip:{duration:1,tracks:[]}};assert.deepEqual(runtime.sampleMotion(branches,0).evaluationOrder,[10,20,30,40]);
});

test('actual motion WASM clamp and loop have explicit endpoint and huge-clock semantics',()=>{
 const source=defaultMotionSource();assert.equal(runtime.sampleMotion(source,3).sampledTime,2);assert.equal(runtime.sampleMotion(source,2,{loop:true}).sampledTime,0);assert.equal(runtime.sampleMotion(source,6,{loop:true}).sampledTime,0);assert.equal(runtime.sampleMotion(source,2.5,{loop:true}).sampledTime,.5);assert.equal(runtime.sampleMotion(source,1e300,{loop:true}).sampledTime,1e300%2);
});

test('actual motion WASM normalized shortest-path NLERP and step preserve source key values',()=>{
 const source=defaultMotionSource();source.clip.tracks=[{boneId:2,interpolation:'linear',keys:[{time:.25,...pose([0,1,0],[0,0,1,2])},{time:1,...pose([0,3,0],[0,0,-2,-4])}]}];const before=JSON.stringify(source),a=runtime.sampleMotion(source,.625).bones.find(b=>b.id===2).local;near(a.position[1],2);near(a.rotation[2],1/Math.sqrt(5));near(a.rotation[3],2/Math.sqrt(5));assert.equal(JSON.stringify(source),before);
 source.clip.tracks[0].interpolation='step';near(runtime.sampleMotion(source,.999).bones.find(b=>b.id===2).local.position[1],1);near(runtime.sampleMotion(source,1).bones.find(b=>b.id===2).local.position[1],3);near(runtime.sampleMotion(source,0).bones.find(b=>b.id===2).local.position[1],1);
});

test('actual motion WASM handles subnormal and huge quaternion norms without norm overflow',()=>{
 const source=defaultMotionSource();source.clip.tracks=[];for(const magnitude of [Number.MIN_VALUE,1e300]){source.bones[0].rest.rotation=[magnitude,-magnitude,magnitude,-magnitude];const r=runtime.sampleMotion(source,0);assert.equal(r.status,'completed');assert.deepEqual(r.bones[0].local.rotation,[.5,-.5,.5,-.5]);}
 source.clip.duration=2*Number.MIN_VALUE;source.clip.tracks=[{boneId:1,interpolation:'linear',keys:[{time:0,...pose()},{time:2*Number.MIN_VALUE,...pose([2,0,0])}]}];near(runtime.sampleMotion(source,Number.MIN_VALUE).bones[0].local.position[0],1);
});

test('actual motion WASM model failures return no partial pose and allow deterministic retry',()=>{
 const good=defaultMotionSource(),baseline=runtime.sampleMotion(good,1);
 for(const change of [s=>s.bones[2].parentId=999,s=>s.bones[2].parentId=3,s=>s.bones[1].rest.rotation=[0,0,0,0],s=>s.clip.tracks[0].keys[2].time=0]){const source=structuredClone(good);change(source);const r=runtime.sampleMotion(source,1);assert.equal(r.status,'invalid_input');assert.equal(r.sampledTime,null);assert.deepEqual(r.bones,[]);}
 for(const budget of [{maximumBones:3},{maximumTracks:1},{maximumKeys:5}]){const r=runtime.sampleMotion(good,1,budget);assert.equal(r.status,'budget_exceeded');assert.deepEqual(r.bones,[]);}
 const overflow={bones:Array.from({length:54},(_,j)=>({id:j+1,parentId:j,rest:pose([1,0,0],[0,0,0,1],[1e6,1e6,1e6])})),clip:{duration:1,tracks:[]}};assert.equal(runtime.sampleMotion(overflow,0).status,'numerical_failure');assert.equal(runtime.sampleMotion(good,-1).status,'invalid_input');assert.deepEqual(runtime.sampleMotion(good,1),baseline);
});

test('actual motion WASM exchanges simultaneous 128 bones 128 tracks and 4096 keys',()=>{
 const source={bones:Array.from({length:128},(_,j)=>({id:j+1,parentId:j,rest:pose([0,1,0])})),clip:{duration:2,tracks:Array.from({length:128},(_,j)=>({boneId:j+1,interpolation:'linear',keys:Array.from({length:32},(_,k)=>({time:k/16,...pose([0,1,0])}))}))}};
 const r=runtime.sampleMotion(source,1);assert.equal(r.status,'completed');assert.equal(r.bones.length,128);assert.deepEqual(r.evaluationOrder,source.bones.map(b=>b.id));near(r.bones[127].worldPosition[1],128);source.clip.tracks[0].keys.push({time:2,...pose()});assert.throws(()=>runtime.sampleMotion(source,1),/key budget/);
});

test('actual motion WASM bad exchange and getters retain records; unrelated optics do not advance World',()=>{
 const source=defaultMotionSource(),baseline=runtime.sampleMotion(source,1),m=runtime.native;runtime.check(m._pp_sim_motion_bone(3));const saved=runtime.output();assert.notEqual(m._pp_sim_motion_bone(999),0);assert.deepEqual(runtime.output(),saved);assert.notEqual(m._pp_sim_motion(1),0);assert.deepEqual(runtime.output(),saved);runtime.check(m._pp_sim_motion_bone(3));assert.deepEqual(runtime.output(),saved);
 for(const options of [{loop:1},{maximumBones:0}])assert.throws(()=>runtime.sampleMotion(source,0,options));const unsafe=structuredClone(source);unsafe.bones[0].id=2**53;assert.throws(()=>runtime.sampleMotion(unsafe,0));
 const world=runtime.createWorld(),before=world.info();runtime.queryDielectricInterface();runtime.check(m._pp_sim_motion_bone(3));assert.deepEqual(runtime.output(),saved);assert.deepEqual(world.info(),before);world.dispose();assert.deepEqual(runtime.sampleMotion(source,1),baseline);runtime.check(m._pp_sim_reset());assert.notEqual(m._pp_sim_motion_bone(0),0);assert.deepEqual(runtime.sampleMotion(source,1),baseline);
});
