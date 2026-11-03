import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';
import {defaultSkinBindingSource,createSkinBindingSource,evaluateSkinBinding,serializeSkinBindingSource} from '../engine/skin-binding.mjs';
import {defaultMotionSource} from '../engine/motion.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const mesh=()=>({positions:[[0,0,0],[1,0,0],[0,1,0]],triangles:[[0,1,2]]});
const identity=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];

test('derived mesh bridge explicitly rejects an older SDK without generating geometry',()=>{
 const old=new SimulationRuntime({_pp_sim_api_version:()=>1},{},0,0);assert.throws(()=>old.prepareDerivedMesh(mesh()),/API unavailable/);
});

function stub({summary=[0,0,1,3,1,1,18,0,0,0,0,0,0,0,0,0,0,1,1,0],audit=[0,0,0,0,0,1,1,1,1,1,0,0,0,0,1,1,1,0,0,1,1,0,0,0,0,0],position=[0,0,0],triangle=[0,1,2],face=[0,0,0,0,0,1,1,0,0,0,0,1,0,1,0,0,0,1]}={}){
 let current=summary;
 const native={_pp_sim_api_version:()=>1,_pp_sim_derived_mesh:()=>0,_pp_sim_derived_mesh_record:(kind,index)=>{current=kind===3?audit:kind===0?(index===0?position:index===1?[1,0,0]:[0,1,0]):kind===1?triangle:face;return 0;}};
 const r=new SimulationRuntime(native,{},0,0);r.inputF64=x=>x.length;r.inputU32=x=>x.length;r.output=()=>[...current];return r;
}
test('derived mesh bridge checks summary flags, reserved fields, counts and complete failure buffers',()=>{
 assert.equal(stub().prepareDerivedMesh(mesh()).status,'completed');
 for(const edit of [a=>a[0]=8,a=>a[0]=.5,a=>a[1]=17,a=>a[2]=2,a=>a[2]=0,a=>a[3]=2,a=>a[4]=0,a=>a[5]=0,a=>a[6]=17,a=>a[7]=2,a=>a[8]=1,a=>a[9]=1,a=>a[10]=1,a=>a[11]=1,a=>a[12]=1,a=>a[13]=1,a=>a[14]=NaN]){const summary=[0,0,1,3,1,1,18,0,0,0,0,0,0,0,0,0,0,1,1,0];edit(summary);assert.throws(()=>stub({summary}).prepareDerivedMesh(mesh()),/C\+\+ derived mesh/);}
 const failure=[1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];assert.equal(stub({summary:failure}).prepareDerivedMesh(mesh()).geometry,null);
 failure[14]=1;assert.throws(()=>stub({summary:failure}).prepareDerivedMesh(mesh()),/geometry counts/);
});
test('derived mesh bridge checks audit optionals, Float32 representation, triangle order and expanded buffers',()=>{
 for(const edit of [a=>a[0]=1,a=>a[9]=2,a=>a[16]=2,a=>a[20]=2,a=>a[25]=2,a=>a[24]=513,a=>a[2]=-1,a=>a[8]=0,a=>a[9]=0,a=>a[16]=0,a=>a[20]=0,a=>a[21]=-1,a=>a[21]=1e-5]){
  const audit=[0,0,0,0,0,1,1,1,1,1,0,0,0,0,1,1,1,0,0,1,1,0,0,0,0,0];edit(audit);assert.throws(()=>stub({audit}).prepareDerivedMesh(mesh()),/C\+\+ derived mesh/);
 }
 assert.throws(()=>stub({position:[.1,0,0]}).prepareDerivedMesh(mesh()),/non-Float32/);
 assert.throws(()=>stub({triangle:[0,2,1]}).prepareDerivedMesh(mesh()),/triangle index/);
 assert.throws(()=>stub({face:Array(18).fill(0)}).prepareDerivedMesh(mesh()),/expanded buffer/);
});

test('actual derived mesh SDK returns owned f32 local positions, oriented normals, exact source order and signed zero',()=>{
 const q={positions:[[-0,0,0],[1,0,0],[0,4,-3],[1+2**-24,0,0],[2**-149,0,0]],triangles:[[0,1,2]]},before=structuredClone(q),r=runtime.prepareDerivedMesh(q);
 assert.equal(r.status,'completed');assert.ok(r.geometry.positions.every(p=>p instanceof Float32Array));assert.ok(r.geometry.interleaved instanceof Float32Array);assert.ok(r.geometry.triangles[0] instanceof Uint32Array);
 assert.ok(Object.is(r.geometry.positions[0][0],-0));assert.equal(r.geometry.positions[3][0],1);assert.equal(r.geometry.positions[4][0],2**-149);assert.deepEqual(q,before);
 assert.deepEqual(Array.from(r.geometry.triangles[0]),[0,1,2]);assert.deepEqual(Array.from(r.geometry.minimum),[-0,0,-3]);
 assert.ok(Math.abs(r.audits[0].normal[1]-.6)<1e-6);assert.ok(Math.abs(r.audits[0].normal[2]-.8)<1e-6);
 const saved=structuredClone(r);runtime.prepareDerivedMesh(mesh());assert.deepEqual(r,saved);r.geometry.interleaved[0]=99;r.audits[0].cross[0][0]=99;assert.deepEqual(runtime.prepareDerivedMesh(q),saved);
 const reverse=runtime.prepareDerivedMesh({...q,triangles:[[0,2,1]]});assert.ok(reverse.audits[0].normal[1]<0);assert.ok(reverse.audits[0].normal[2]<0);
});
test('actual derived mesh SDK model failures commit no geometry and preserve failing diagnostic prefixes',()=>{
 for(const q of [{positions:[],triangles:[]},{positions:mesh().positions,triangles:[]},{...mesh(),triangles:[[0,0,2]]},{...mesh(),triangles:[[0,1,3]]},{...mesh(),positions:[[0,0,0],[1e300,0,0],[0,1,0]]}]){const r=runtime.prepareDerivedMesh(q);assert.equal(r.status,'invalid_input');assert.equal(r.geometry,null);assert.equal(runtime.prepareDerivedMesh(mesh()).status,'completed');}
 const r=runtime.prepareDerivedMesh({positions:[[0,0,0],[1,0,0],[0,1,0],[2,0,0]],triangles:[[0,1,2],[0,1,3]]});assert.equal(r.status,'degenerate');assert.equal(r.failedFace,1);assert.equal(r.audits.length,2);assert.equal(r.geometry,null);
 const uncertain=runtime.prepareDerivedMesh(mesh(),{sqrtRefinements:1});assert.equal(uncertain.status,'quality_unresolved');assert.equal(uncertain.reason,'normal_uncertain');assert.equal(uncertain.geometry,null);assert.equal(uncertain.audits[0].sqrtRefinementLimited,true);
 for(const options of [{maxVertices:0},{maxVertices:65537},{maxTriangles:0},{maxTriangles:131073},{sqrtRefinements:0},{sqrtRefinements:257}]){const r=runtime.prepareDerivedMesh(mesh(),options);assert.equal(r.status,'invalid_input');assert.equal(r.reason,'settings');}
 assert.equal(runtime.prepareDerivedMesh(mesh(),{maxVertices:3,maxTriangles:1}).status,'completed');
});
test('actual derived mesh SDK simultaneous 2048 vertices and 32768 faces; one-over and budgets remain explicit',()=>{
 const q={positions:[...mesh().positions,...Array.from({length:2045},()=>[0,0,0])],triangles:Array.from({length:32768},()=>[0,1,2])};
 const r=runtime.prepareDerivedMesh(q);assert.equal(r.status,'completed');assert.equal(r.geometry.positions.length,2048);assert.equal(r.geometry.triangles.length,32768);assert.equal(r.geometry.interleaved.length,589824);assert.equal(r.audits.length,32768);
 assert.deepEqual(Array.from(r.geometry.interleaved.slice(-6)),[0,1,0,0,0,1]);
 for(const options of [{maxVertices:2047},{maxTriangles:32767}]){const fail=runtime.prepareDerivedMesh(q,options);assert.equal(fail.status,'budget_exceeded');assert.equal(fail.geometry,null);}
 assert.throws(()=>runtime.prepareDerivedMesh({...q,positions:[...q.positions,[0,0,0]]}),/2048/);assert.throws(()=>runtime.prepareDerivedMesh({...q,triangles:[...q.triangles,[0,1,2]]}),/32768/);
});
test('actual derived mesh SDK host malformed exchanges/getters preserve the previous output and model record',()=>{
 const good=runtime.prepareDerivedMesh(mesh()),m=runtime.native;runtime.check(m._pp_sim_derived_mesh_record(2,0));const saved=runtime.output();
 for(const call of [()=>m._pp_sim_derived_mesh_record(4,0),()=>m._pp_sim_derived_mesh_record(0,3),()=>m._pp_sim_derived_mesh(1,3),()=>m._pp_sim_derived_mesh(17,2)]){assert.notEqual(call(),0);assert.deepEqual(runtime.output(),saved);}
 const packet=[3,1,2048,32768,128,0,0,0,...mesh().positions.flat()];
 for(const edit of [p=>p[5]=1,p=>p[0]=2049,p=>p[2]=-.5,p=>p[8]=NaN]){const p=[...packet];edit(p);m.HEAPF64.set(p,m._pp_sim_input_f64_ptr()/8);assert.notEqual(m._pp_sim_derived_mesh(p.length,3),0);assert.deepEqual(runtime.output(),saved);runtime.check(m._pp_sim_derived_mesh_record(2,0));assert.deepEqual(runtime.output(),saved);}
 for(const q of [{positions:Array(1),triangles:[]},{positions:[[NaN,0,0]],triangles:[]},{...mesh(),triangles:[[0,1,.5]]},{...mesh(),triangles:[[0,1,2**32]]}])assert.throws(()=>runtime.prepareDerivedMesh(q));
 assert.throws(()=>runtime.prepareDerivedMesh(mesh(),{maxVertices:Infinity}));assert.deepEqual(runtime.prepareDerivedMesh(mesh()),good);
});
test('actual derived mesh SDK leaves skin motion optical and World state independent and resets only records',()=>{
 const m=runtime.native,source=defaultMotionSource(),pose=runtime.sampleMotion(source,1),bind=runtime.bindSkin([{id:7,matrix:identity()}]);
 const skin=runtime.deformSkin({joints:bind.joints,pose:[{id:7,matrix:identity()}],vertices:[{position:[1,2,3],influences:[{id:7,weight:1}]}]});
 const packet=runtime.queryPolarizedPacket({packets:[{ray:{origin:[0,0,0],direction:[0,0,1]},power:[1,0,0,0]}],steps:[],sensor:{kind:'disk',center:[0,0,1],normal:[0,0,-1],apertureRadius:1}});assert.equal(packet.status,'completed');runtime.check(m._pp_sim_polarized_packet_record(0,0));const packetRecord=runtime.output();
 const world=runtime.createWorld(),before=world.info(),good=runtime.prepareDerivedMesh(mesh());runtime.queryDielectricInterface();runtime.check(m._pp_sim_derived_mesh_record(0,0));assert.deepEqual(runtime.output(),[0,0,0]);assert.deepEqual(world.info(),before);
 runtime.check(m._pp_sim_polarized_packet_record(0,0));assert.deepEqual(runtime.output(),packetRecord);
 runtime.check(m._pp_sim_motion_bone(0));assert.equal(runtime.output()[0],pose.bones[0].id);runtime.check(m._pp_sim_skin_bind_record(0,0));assert.equal(runtime.output()[0],7);runtime.check(m._pp_sim_skin_deform_record(0,0));assert.deepEqual(runtime.output(),skin.positions[0]);
 assert.deepEqual(runtime.prepareDerivedMesh(mesh()),good);world.dispose();runtime.check(m._pp_sim_reset());for(const kind of [0,1,2,3])assert.notEqual(m._pp_sim_derived_mesh_record(kind,0),0);assert.notEqual(m._pp_sim_polarized_packet_record(0,0),0);assert.deepEqual(runtime.prepareDerivedMesh(mesh()),good);
});
test('actual owned Source LBS feeds derived mesh at clamp and loop times while preserving serialized authorship',()=>{
 const source=defaultSkinBindingSource(runtime),before=serializeSkinBindingSource(source);
 let atOne;
 for(const [time,loop] of [[0,false],[.5,false],[1,false],[2,false],[3,true]]){const state=evaluateSkinBinding(runtime,source,time,{loop});assert.equal(state.deformation.status,'completed');const r=runtime.prepareDerivedMesh({positions:state.deformation.positions,triangles:source.mesh.triangles});assert.equal(r.status,'completed');assert.equal(r.geometry.positions.length,6);
  if(time===0||time===2)assert.deepEqual(state.deformation.positions,source.mesh.positions);
  if(time===1){atOne=state.deformation.positions;const exact=[[0,-.2,0],[1.1,-.1,0],[1.2,1,0],[0,.2,0],[.9,.1,0],[.8,1,0]];atOne.forEach((p,j)=>p.forEach((v,k)=>assert.ok(Math.abs(v-exact[j][k])<256*Number.EPSILON)));}
  if(time===3)assert.deepEqual(state.deformation.positions,atOne);
 }
 assert.equal(serializeSkinBindingSource(source),before);
 const collapsed=structuredClone(source);collapsed.influences=collapsed.influences.map(()=>[{boneId:7,weight:1},{boneId:19,weight:1}]);collapsed.motion.clip.tracks[0].keys[1].rotation=[0,0,1,0];
 const owned=createSkinBindingSource(collapsed),state=evaluateSkinBinding(runtime,owned,1);assert.equal(state.deformation.status,'completed');assert.deepEqual(state.deformation.positions,Array.from({length:6},()=>[1,0,0]));
 const r=runtime.prepareDerivedMesh({positions:state.deformation.positions,triangles:owned.mesh.triangles});assert.equal(r.status,'degenerate');assert.equal(r.geometry,null);assert.equal(serializeSkinBindingSource(source),before);
});
test('actual Source stage failures do not turn into successful derived geometry; the same runtime recovers',()=>{
 const source=defaultSkinBindingSource(runtime),before=serializeSkinBindingSource(source);
 const stale=structuredClone(source);stale.motion.bones[0].rest.position[0]=2;assert.throws(()=>evaluateSkinBinding(runtime,stale,0),/rest snapshot|Stale|rest/);
 const bad=structuredClone(source);bad.joints[0].inverseBind[0]=2;const failure=evaluateSkinBinding(runtime,bad,0);assert.notEqual(failure.deformation.status,'completed');assert.equal(failure.deformation.positions,null);
 const under=structuredClone(source);under.influences[0]=[{boneId:7,weight:Number.MIN_VALUE},{boneId:19,weight:Number.MAX_VALUE}];assert.equal(evaluateSkinBinding(runtime,under,0).deformation.status,'numerical_failure');
 assert.equal(runtime.prepareDerivedMesh({positions:evaluateSkinBinding(runtime,source,0).deformation.positions,triangles:source.mesh.triangles}).status,'completed');assert.equal(serializeSkinBindingSource(source),before);
});
