import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';
import {defaultMotionSource} from '../engine/motion.mjs';
import {createDerivedMeshProfiler} from '../tools/derived-profile.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const input=()=>({positions:[[-0,0,0],[1,0,0],[0,1,0],[1,1,0]],triangles:[[0,1,2],[1,3,2]]});
const stageNames=['f64Exchange','u32Exchange','cppQuery','cppGetter','outputCopy'];
function bits(value){
  if(typeof value==='number'){const b=Buffer.alloc(8);b.writeDoubleBE(value);return b.toString('hex');}
  if(ArrayBuffer.isView(value))return {type:value.constructor.name,bytes:Buffer.from(value.buffer,value.byteOffset,value.byteLength).toString('hex')};
  if(Array.isArray(value))return value.map(bits);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,bits(v)]));return value;
}
function accounting(timing){
  assert.ok(Number.isFinite(timing.elapsedMs)&&timing.elapsedMs>=0);assert.ok(Number.isFinite(timing.unassignedMs)&&timing.unassignedMs>=0);
  assert.equal(timing.elapsedMs,Object.values(timing.stages).reduce((n,s)=>n+s.elapsedMs,0)+timing.unassignedMs);
  for(const value of Object.values(timing.stages)){assert.ok(Number.isSafeInteger(value.calls)&&value.calls>=0);assert.ok(Number.isFinite(value.elapsedMs)&&value.elapsedMs>=0);}
}
const clock=()=>{let n=0;return ()=>n++;};
const identity=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];

test('actual profiler preserves all SDK DTO bits and measures disjoint transfer query getter and output stages',()=>{
  const q=input(),before=bits(q),baseline=runtime.prepareDerivedMesh(q),profile=createDerivedMeshProfiler(runtime,{now:clock()});
  const {result,error,timing,clockError}=profile.prepare(q);assert.equal(error,null);assert.equal(clockError,null);assert.deepEqual(result,baseline);assert.deepEqual(bits(result),bits(baseline));assert.deepEqual(bits(q),before);
  assert.deepEqual(timing.getterKinds,[4,2,2,2]);assert.deepEqual(Object.fromEntries(stageNames.map(k=>[k,timing.stages[k].calls])),{f64Exchange:1,u32Exchange:1,cppQuery:1,cppGetter:10,outputCopy:11});
  assert.deepEqual(Object.fromEntries(stageNames.map(k=>[k,timing.stages[k].elapsedMs])),{f64Exchange:1,u32Exchange:1,cppQuery:1,cppGetter:10,outputCopy:11});assert.equal(timing.elapsedMs,49);assert.equal(timing.unassignedMs,25);accounting(timing);
});
test('actual profiler leaves the original runtime methods and every module export function identical',()=>{
  const native=runtime.native,methods=Object.fromEntries(['prepareDerivedMesh','inputF64','inputU32','output'].map(k=>[k,runtime[k]])),exports=Object.entries(native).filter(([,value])=>typeof value==='function');
  const profile=createDerivedMeshProfiler(runtime);assert.equal(profile.prepare(input()).error,null);assert.equal(runtime.native,native);
  for(const [key,value]of Object.entries(methods))assert.equal(runtime[key],value);for(const [key,value]of exports)assert.equal(native[key],value);
});
test('actual profiler returns model failures as DTOs with their real getter and output counts',()=>{
  const profile=createDerivedMeshProfiler(runtime,{now:clock()});
  const empty={positions:[],triangles:[]},r=profile.prepare(empty);assert.equal(r.error,null);assert.equal(r.result.status,'invalid_input');assert.deepEqual(r.timing.getterKinds,[0,0,0,0]);assert.equal(r.timing.stages.cppQuery.calls,1);assert.equal(r.timing.stages.outputCopy.calls,1);accounting(r.timing);
  const q={positions:[[0,0,0],[1,0,0],[0,1,0],[2,0,0]],triangles:[[0,1,2],[0,1,3]]},failure=profile.prepare(q);assert.equal(failure.error,null);assert.equal(failure.result.status,'degenerate');assert.equal(failure.result.geometry,null);assert.deepEqual(failure.timing.getterKinds,[0,0,0,2]);assert.equal(failure.timing.stages.outputCopy.calls,3);accounting(failure.timing);
  const settings=profile.prepare(input(),{sqrtRefinements:0});assert.equal(settings.result.status,'invalid_input');assert.equal(settings.error,null);assert.equal(settings.timing.stages.cppQuery.calls,1);
});
test('actual profiler captures host validation errors without touching old native output and then recovers',()=>{
  runtime.prepareDerivedMesh(input());runtime.check(runtime.native._pp_sim_derived_mesh_record(2,0));const before=bits(runtime.output()),profile=createDerivedMeshProfiler(runtime,{now:clock()});
  const r=profile.prepare({positions:[[NaN,0,0]],triangles:[]});assert.equal(r.result,null);assert.ok(r.error instanceof Error);assert.equal(r.clockError,null);assert.deepEqual(bits(runtime.output()),before);
  assert.ok(stageNames.every(k=>r.timing.stages[k].calls===0));assert.equal(r.timing.elapsedMs,1);accounting(r.timing);
  const retry=profile.prepare(input());assert.equal(retry.error,null);assert.equal(retry.result.status,'completed');assert.equal(retry.timing.stages.cppQuery.calls,1);
});
test('actual profiler measurements and result snapshots do not change during a later invocation',()=>{
  const profile=createDerivedMeshProfiler(runtime,{now:clock()}),first=profile.prepare(input()),saved=structuredClone(first);
  profile.prepare({positions:[],triangles:[]});assert.deepEqual(first,saved);first.timing.stages.cppQuery.calls=999;first.result.geometry.interleaved.fill(99);
  const next=profile.prepare(input());assert.equal(next.timing.stages.cppQuery.calls,1);assert.equal(next.result.geometry.interleaved[1],0);
});
test('actual profiler preserves World clocks and independent skin and motion snapshots',()=>{
  const bind=runtime.bindSkin([{id:7,matrix:identity()}]);runtime.check(runtime.native._pp_sim_skin_bind_record(0,0));const savedBind=bits(runtime.output());
  runtime.deformSkin({joints:bind.joints,pose:[{id:7,matrix:identity()}],vertices:[{position:[1,2,3],influences:[{id:7,weight:1}]}]});runtime.check(runtime.native._pp_sim_skin_deform_record(0,0));const savedDeform=bits(runtime.output());
  runtime.sampleMotion(defaultMotionSource(),.5);runtime.check(runtime.native._pp_sim_motion_bone(0));const savedMotion=bits(runtime.output());
  const world=runtime.createWorld(),before=world.info();try{
    const profile=createDerivedMeshProfiler(runtime,{now:clock()});assert.equal(profile.prepare(input()).error,null);assert.deepEqual(world.info(),before);
    runtime.check(runtime.native._pp_sim_skin_bind_record(0,0));assert.deepEqual(bits(runtime.output()),savedBind);runtime.check(runtime.native._pp_sim_skin_deform_record(0,0));assert.deepEqual(bits(runtime.output()),savedDeform);runtime.check(runtime.native._pp_sim_motion_bone(0));assert.deepEqual(bits(runtime.output()),savedMotion);
  }finally{world.dispose();}
});
test('actual profiler retains completed DTOs when the clock throws and resets state for the next measurement',()=>{
  const failure=new Error('clock test'),baseline=runtime.prepareDerivedMesh(input());let fail=true,n=0;
  const profile=createDerivedMeshProfiler(runtime,{now:()=>{if(fail)throw failure;return n++;}}),r=profile.prepare(input());
  assert.deepEqual(bits(r.result),bits(baseline));assert.equal(r.error,failure);assert.equal(r.clockError,failure);assert.equal(r.timing,null);
  fail=false;const next=profile.prepare(input());assert.equal(next.error,null);assert.equal(next.clockError,null);assert.equal(next.timing.stages.cppQuery.calls,1);accounting(next.timing);
});
test('actual profiler rejects nonfinite backward or unrepresentable clock metrics without aborting computation',()=>{
  const clocks=[()=>NaN,()=>Infinity,()=> '1',()=>Promise.resolve(1),(()=>{let n=0;return ()=>[0,5,4][n++]??10;})(),(()=>{let n=0;return ()=>n++===0?-1e308:1e308;})()];
  for(const now of clocks){const r=createDerivedMeshProfiler(runtime,{now}).prepare(input());assert.equal(r.result.status,'completed');assert.ok(r.error instanceof Error);assert.equal(r.error,r.clockError);assert.equal(r.timing,null);}
  const zero=createDerivedMeshProfiler(runtime,{now:()=>-5}).prepare(input());assert.equal(zero.error,null);assert.equal(zero.timing.elapsedMs,0);assert.equal(zero.timing.unassignedMs,0);accounting(zero.timing);
});
test('profiler native forwarding preserves original this live HEAP access and frozen exports',()=>{
  const module=runtime.native,facade={},calls=[];let heapReads=0;
  for(const key of Object.keys(module))if(typeof module[key]==='function')Object.defineProperty(facade,key,{value:function(...args){assert.equal(this,facade);calls.push(key);return Reflect.apply(module[key],module,args);},enumerable:true});
  for(const key of ['HEAPF64','HEAPU32','HEAPU8'])Object.defineProperty(facade,key,{get(){++heapReads;return module[key];},enumerable:true});Object.freeze(facade);
  const original=new SimulationRuntime(facade,runtime.metadata,runtime.wasmBytes,runtime.startupMs),profile=createDerivedMeshProfiler(original,{now:clock()});
  const first=profile.prepare(input());assert.equal(first.error,null);const reads=heapReads;assert.ok(reads>0);const second=profile.prepare(input());assert.equal(second.error,null);assert.ok(heapReads>reads);assert.ok(calls.includes('_pp_sim_derived_mesh_record'));assert.deepEqual(bits(first.result),bits(second.result));assert.equal(original.native,facade);
});
test('profiler preserves the real operation Error alongside an independent clock Error',()=>{
  const operationError=new Error('native operation failed'),clockError=new Error('clock also failed'),module=runtime.native;
  const facade=new Proxy(Object.create(null),{get(_t,key){if(key==='_pp_sim_derived_mesh')return ()=>{throw operationError;};const value=module[key];return typeof value==='function'?value.bind(module):value;}});
  const original=new SimulationRuntime(facade,runtime.metadata,runtime.wasmBytes,runtime.startupMs);let n=0;
  const profile=createDerivedMeshProfiler(original,{now:()=>{if(++n===7)throw clockError;return n;}}),r=profile.prepare(input());
  assert.equal(r.result,null);assert.equal(r.error,operationError);assert.equal(r.clockError,clockError);assert.equal(r.timing,null);
  const validClock=createDerivedMeshProfiler(original,{now:clock()}).prepare(input());assert.equal(validClock.error,operationError);assert.equal(validClock.clockError,null);assert.equal(validClock.timing.stages.cppQuery.calls,1);assert.equal(validClock.timing.stages.cppGetter.calls,0);accounting(validClock.timing);
});
test('profiler rejects reentrant same-profiler prepare without corrupting the outer or next measurement',()=>{
  let profile,n=0,nested,tried=false;profile=createDerivedMeshProfiler(runtime,{now:()=>{if(!tried){tried=true;nested=profile.prepare(input());}return n++;}});
  const outer=profile.prepare(input());assert.ok(nested.error instanceof Error);assert.match(nested.error.message,/reentered/);assert.equal(nested.result,null);assert.equal(nested.timing,null);assert.equal(nested.clockError,null);
  assert.equal(outer.error,null);assert.equal(outer.result.status,'completed');assert.equal(outer.timing.stages.cppQuery.calls,1);accounting(outer.timing);
  const next=profile.prepare(input());assert.equal(next.error,null);assert.equal(next.timing.stages.cppQuery.calls,1);accounting(next.timing);
});
test('profiler validates construction arguments without altering the supplied runtime',()=>{
  assert.throws(()=>createDerivedMeshProfiler(null),TypeError);assert.throws(()=>createDerivedMeshProfiler(runtime,{now:1}),TypeError);assert.equal(runtime.prepareDerivedMesh(input()).status,'completed');
});
