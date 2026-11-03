import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';
import {defaultSkinBindingSource,createSkinBindingSource,evaluateSkinBinding,serializeSkinBindingSource,parseSkinBindingPortable,serializeSkinBindingPortable} from '../engine/skin-binding.mjs';
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
 const hasBatch=typeof runtime.native._pp_sim_derived_mesh_records==='function',r=runtime.prepareDerivedMesh(q,{readback:hasBatch?'batch':'single'});assert.equal(r.status,'completed');assert.equal(r.geometry.positions.length,2048);assert.equal(r.geometry.triangles.length,32768);assert.equal(r.geometry.interleaved.length,589824);assert.equal(r.audits.length,32768);
 assert.deepEqual(Array.from(r.geometry.interleaved.slice(-6)),[0,1,0,0,0,1]);
 if(hasBatch){for(const [kind,index,expected]of [[0,2047,Array.from(r.geometry.positions[2047])],[1,32767,Array.from(r.geometry.triangles[32767])],[2,32767,Array.from(r.geometry.interleaved.slice(-18))]]){runtime.check(runtime.native._pp_sim_derived_mesh_record(kind,index));assert.deepEqual(runtime.output(),expected);}runtime.check(runtime.native._pp_sim_derived_mesh_records(3,32766,2));const tail=runtime.output();assert.deepEqual(tail.slice(0,4),[3,32766,2,26]);assert.equal(tail[4],32766);assert.equal(tail[30],32767);}
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

// Protocol tests replay complete packets captured from the actual C++ decoder
// source. They test transport/ownership, not an independent numerical oracle.
function captureDerivedPackets(input,settings={}){
 const expected=runtime.prepareDerivedMesh(input,settings),p=[input.positions.length,input.triangles.length,settings.maxVertices??2048,settings.maxTriangles??32768,settings.sqrtRefinements??128,0,0,0,...input.positions.flat()];
 const count=runtime.inputF64(p),indices=runtime.inputU32(input.triangles.flat());runtime.check(runtime.native._pp_sim_derived_mesh(count,indices));const summary=runtime.output(),counts=[summary[3],summary[4],summary[4],summary[5]],records=counts.map((n,kind)=>Array.from({length:n},(_,index)=>{runtime.check(runtime.native._pp_sim_derived_mesh_record(kind,index));return runtime.output();}));return {summary,records,expected};
}
function packetRuntime(snapshot,{edit,missingBatch=false,batchError=false}={}){
 const calls={f64:0,u32:0,query:0,single:[],batch:[],heaps:[]};let length=0;
 const native={_pp_sim_api_version:()=>1,_pp_sim_output_f64_ptr:()=>0,_pp_sim_output_count:()=>length,HEAPF64:new Float64Array(64)};
 const publish=values=>{const data=Array.from(values);native.HEAPF64=new Float64Array(Math.max(64,data.length));native.HEAPF64.set(data);calls.heaps.push(native.HEAPF64);length=data.length;};
 native._pp_sim_derived_mesh=()=>{calls.query++;publish(snapshot.summary);return 0;};
 native._pp_sim_derived_mesh_record=(kind,index)=>{calls.single.push([kind,index]);publish(snapshot.records[kind][index]);return 0;};
 if(!missingBatch)native._pp_sim_derived_mesh_records=(kind,first,count)=>{calls.batch.push([kind,first,count]);if(batchError)return 1;const strides=[3,3,18,26],packet=[kind,first,count,strides[kind],...snapshot.records[kind].slice(first,first+count).flat()];if(edit)edit(packet,kind,first,count);publish(packet);return 0;};
 const host=new SimulationRuntime(native,{},0,0);host.inputF64=data=>{calls.f64++;return data.length;};host.inputU32=data=>{calls.u32++;return data.length;};host.check=status=>{if(status)throw new Error('Rejected batch ABI packet');};return {host,calls,publish,native};
}
function exactDerived(value){
 if(typeof value==='number'){const bytes=new ArrayBuffer(8),view=new DataView(bytes);view.setFloat64(0,value);return ['number',view.getBigUint64(0).toString(16)];}
 if(ArrayBuffer.isView(value))return [value.constructor.name,Buffer.from(value.buffer,value.byteOffset,value.byteLength).toString('hex')];
 if(Array.isArray(value))return ['Array',value.map(exactDerived)];
 if(value&&typeof value==='object')return ['Object',Object.keys(value).map(key=>[key,exactDerived(value[key])])];return [typeof value,value];
}
const chunkMesh=()=>({positions:[[-0,0,0],[1,0,0],[0,1,0],...Array.from({length:38},(_,j)=>[j/8,j%2,2**-149])],triangles:Array.from({length:23},(_,j)=>j===22?[0,2,1]:[0,1,2])});

test('derived readback selection rejects invalid modes and unavailable batch before exchanging inputs',()=>{
 const snapshot=captureDerivedPackets(mesh()),{host,calls}=packetRuntime(snapshot,{missingBatch:true});
 for(const readback of ['auto','',null,0,{},'Batch'])assert.throws(()=>host.prepareDerivedMesh(mesh(),{readback}),/readback/);
 assert.throws(()=>host.prepareDerivedMesh(mesh(),{readback:'batch'}),/API unavailable/);assert.equal(calls.f64,0);assert.equal(calls.u32,0);assert.equal(calls.query,0);assert.deepEqual(calls.single,[]);
 assert.deepEqual(exactDerived(host.prepareDerivedMesh(mesh())),exactDerived(snapshot.expected));assert.deepEqual(exactDerived(host.prepareDerivedMesh(mesh(),{readback:'single'})),exactDerived(snapshot.expected));assert.equal(calls.batch.length,0);
});

test('batch packet caches retain independent kinds and exact ordered DTO types, bits, tails and ownership',()=>{
 const input=chunkMesh(),before=structuredClone(input),snapshot=captureDerivedPackets(input),{host,calls,publish}=packetRuntime(snapshot),result=host.prepareDerivedMesh(input,{readback:'batch'});
 assert.deepEqual(exactDerived(result),exactDerived(snapshot.expected));assert.deepEqual(input,before);assert.deepEqual(calls.single,[]);assert.equal(calls.query,1);assert.equal(calls.f64,1);assert.equal(calls.u32,1);
 for(const [kind,max,count]of [[0,20,41],[1,20,23],[2,3,23],[3,2,23]]){const expected=Array.from({length:Math.ceil(count/max)},(_,j)=>[kind,j*max,Math.min(max,count-j*max)]);assert.deepEqual(calls.batch.filter(call=>call[0]===kind),expected);}
 assert.ok(Object.is(result.geometry.positions[0][0],-0));assert.equal(result.geometry.positions.at(-1)[2],2**-149);assert.equal(result.audits.at(-1).normal[2],-1);assert.deepEqual(Array.from(result.geometry.interleaved.slice(-3)),[0,0,-1]);
 const saved=structuredClone(result);for(const heap of calls.heaps)heap.fill(99);publish([42]);assert.deepEqual(exactDerived(result),exactDerived(saved));result.geometry.positions[0][0]=42;result.audits[0].cross[0][0]=42;
 assert.deepEqual(exactDerived(host.prepareDerivedMesh(input,{readback:'batch'})),exactDerived(saved));assert.deepEqual(exactDerived(host.prepareDerivedMesh(input)),exactDerived(saved));
});

test('hostile batch headers and payloads fail closed without single fallback or partial geometry',()=>{
 const snapshot=captureDerivedPackets(mesh());
 const mutations=[
  (b)=>b.splice(0,b.length,0,0,0),b=>b.push(0),b=>b.pop(),b=>b[0]=4,b=>b[1]++,b=>b[2]=0,b=>b[2]=21,b=>b[3]++,b=>b[4]=NaN,b=>b[4]=Infinity,
  (b,k)=>{if(k===3)b[4]=1;},(b,k)=>{if(k===3)b[13]=2;},(b,k)=>{if(k===3){b[13]=0;b[14]=1;}},(b,k)=>{if(k===3)b[25]=1e-5;},(b,k)=>{if(k===3)b[21]=.1;},
  (b,k)=>{if(k===0)b[4]=.1;},(b,k)=>{if(k===1)[b[5],b[6]]=[b[6],b[5]];},(b,k)=>{if(k===2)b[4]=-0;}
 ];
 for(const edit of mutations){const {host,calls}=packetRuntime(snapshot,{edit});assert.throws(()=>host.prepareDerivedMesh(mesh(),{readback:'batch'}),/C\+\+ derived mesh/);assert.deepEqual(calls.single,[]);assert.equal(calls.query,1);}
 const {host,calls}=packetRuntime(snapshot,{batchError:true});assert.throws(()=>host.prepareDerivedMesh(mesh(),{readback:'batch'}),/Rejected batch/);assert.deepEqual(calls.single,[]);
});

test('batch failure prefixes retain optional diagnostic records while geometry remains null',()=>{
 const input={positions:[[0,0,0],[1,0,0],[0,1,0],[2,0,0]],triangles:[[0,1,2],[0,1,3]]},snapshot=captureDerivedPackets(input),{host,calls}=packetRuntime(snapshot),result=host.prepareDerivedMesh(input,{readback:'batch'});
 assert.equal(result.status,'degenerate');assert.equal(result.geometry,null);assert.equal(result.audits.length,2);assert.equal(result.audits[0].normal!==null,true);assert.equal(result.audits[1].normal,null);assert.deepEqual(exactDerived(result),exactDerived(snapshot.expected));assert.deepEqual(calls.batch,[[3,0,2]]);assert.deepEqual(calls.single,[]);
 for(const edit of [(b)=>b[30]=0,b=>b[30+9]=2,b=>{b[30+9]=0;b[30+10]=1;},b=>b[30+8]=-1]){const corrupt=packetRuntime(snapshot,{edit});assert.throws(()=>corrupt.host.prepareDerivedMesh(input,{readback:'batch'}),/C\+\+ derived mesh/);assert.deepEqual(corrupt.calls.single,[]);}
 const empty=captureDerivedPackets({positions:[],triangles:[]}),other=packetRuntime(empty);assert.deepEqual(exactDerived(other.host.prepareDerivedMesh({positions:[],triangles:[]},{readback:'batch'})),exactDerived(empty.expected));assert.deepEqual(other.calls.batch,[]);
});


function projectDerived(result){
 const bits=v=>Array.from(new Uint32Array(v.buffer,v.byteOffset,v.length)),g=result.geometry;
 return {status:['completed','invalid_input','budget_exceeded','degenerate','quality_rejected','quality_unresolved','numerical_failure','unsupported_environment'].indexOf(result.status),reason:['none','settings','vertex_count','triangle_count','position_domain','index_range','duplicate_index','vertex_budget','triangle_budget','zero_cross','below_area_floor','cross_uncertain','area_uncertain','normal_uncertain','nonfinite_intermediate','allocation_failure','environment'].indexOf(result.reason),failedVertex:result.failedVertex,failedFace:result.failedFace,positionsBits:g?g.positions.map(bits):null,triangles:g?g.triangles.map(t=>Array.from(t)):null,interleavedBits:g?bits(g.interleaved):null,minimumBits:g?bits(g.minimum):null,maximumBits:g?bits(g.maximum):null,audits:result.audits.map(a=>({face:a.face,cross:a.cross,squaredCross:a.squaredCross,normalized:a.normalized,normalBits:a.normal?bits(a.normal):null,normalError:a.normalError,sqrtRefinements:a.sqrtRefinements,sqrtRefinementLimited:a.sqrtRefinementLimited})),sqrtRefinements:result.sqrtRefinements,sqrtLimitedFaces:result.sqrtLimitedFaces};
}

test('actual batch SDK replays all fixed 40 Native models with identical ordered typed DTO bits',async()=>{
 assert.equal(typeof runtime.native._pp_sim_derived_mesh_records,'function','Actual batch SDK export is required; protocol replay is not a substitute');
 const text=await readFile(new URL('../reports/derived-mesh-sdk-js-native-fixtures.json',import.meta.url),'utf8');assert.equal(createHash('sha256').update(text).digest('hex'),'a9bd09a6c4b726a63bba681952dd97fd52b98e3d30fac5dd670ddfeb1e9d6dcf');const corpus=JSON.parse(text);assert.equal(corpus.fixtures.length,40);let completed=0,failures=0;
 for(const fixture of corpus.fixtures){const q=fixture.input,before=exactDerived(q),settings={maxVertices:q.settings[0],maxTriangles:q.settings[1],sqrtRefinements:q.settings[2]},single=runtime.prepareDerivedMesh(q,settings),batch=runtime.prepareDerivedMesh(q,{...settings,readback:'batch'});assert.deepEqual(exactDerived(batch),exactDerived(single),fixture.name);assert.deepEqual(exactDerived(projectDerived(batch)),exactDerived(fixture.result),fixture.name+' Native');assert.deepEqual(exactDerived(q),before);if(batch.status==='completed')completed++;else failures++;}
 assert.equal(completed,16);assert.equal(failures,24);
 const input=chunkMesh(),single=runtime.prepareDerivedMesh(input),batch=runtime.prepareDerivedMesh(input,{readback:'batch'});assert.deepEqual(exactDerived(batch),exactDerived(single));
});

test('actual batch SDK Source11 retains stage failures and scalar/typed snapshot ownership',async()=>{
 assert.equal(typeof runtime.native._pp_sim_derived_mesh_records,'function','Actual batch SDK export is required');const text=await readFile(new URL('../reports/derived-mesh-sdk-js-native-source-probes.json',import.meta.url),'utf8');assert.equal(createHash('sha256').update(text).digest('hex'),'b658f0687cda518dfde3032625331c6c597d582a715c09a2afe363a5153a1e19');const corpus=JSON.parse(text);assert.equal(corpus.fixtures.length,11);let derivedCount=0;
 for(const fixture of corpus.fixtures){const q=fixture.input,source=parseSkinBindingPortable(q.portable),before=serializeSkinBindingPortable(source);let state,error=null;try{state=evaluateSkinBinding(runtime,source,q.seconds,{loop:q.loop});}catch(e){error=e;}assert.equal(Boolean(error),fixture.sourceError!==null,fixture.name);assert.equal(serializeSkinBindingPortable(source),before);
  if(state?.deformation.status==='completed'){const input={positions:state.deformation.positions,triangles:source.mesh.triangles},settings={maxVertices:q.settings[0],maxTriangles:q.settings[1],sqrtRefinements:q.settings[2]},single=runtime.prepareDerivedMesh(input,settings),batch=runtime.prepareDerivedMesh(input,{...settings,readback:'batch'});assert.deepEqual(exactDerived(batch),exactDerived(single),fixture.name);assert.deepEqual(exactDerived(projectDerived(batch)),exactDerived(fixture.derived),fixture.name);const saved=structuredClone(batch);runtime.prepareDerivedMesh(mesh());assert.deepEqual(exactDerived(batch),exactDerived(saved));derivedCount++;}
  else assert.equal(fixture.derived,null);
 }assert.equal(derivedCount,8);
 const good=runtime.prepareDerivedMesh(mesh(),{readback:'batch'}),saved=structuredClone(good);runtime.queryDielectricInterface();runtime.check(runtime.native._pp_sim_derived_mesh_records(0,0,3));assert.deepEqual(runtime.output().slice(0,4),[0,0,3,3]);assert.deepEqual(exactDerived(good),exactDerived(saved));runtime.check(runtime.native._pp_sim_reset());assert.notEqual(runtime.native._pp_sim_derived_mesh_records(0,0,1),0);assert.deepEqual(exactDerived(runtime.prepareDerivedMesh(mesh(),{readback:'batch'})),exactDerived(saved));
});
