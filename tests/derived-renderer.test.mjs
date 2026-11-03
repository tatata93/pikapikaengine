import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createBoxMesh} from '../engine/mesh.mjs';
import {Renderer} from '../engine/renderer.mjs';
import {createDerivedMeshRenderData,derivedMeshRenderInfo,copyDerivedMeshRenderVertices} from '../engine/derived-render.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const dto=()=>runtime.prepareDerivedMesh({positions:[[-0,0,0],[1,0,0],[0,1,0]],triangles:[[0,1,2]]});
const token=()=>createDerivedMeshRenderData(dto());
const camera={eye:[3,3,5],target:[0,0,0]};
const item=(mesh=token(),id='derived')=>({id,type:'derived-mesh',mesh,position:[0,0,0],scale:[1,1,1],color:[.2,.5,.8]});
const bytes=x=>Buffer.from(x.buffer,x.byteOffset,x.byteLength);
Object.defineProperty(globalThis,'GPUBufferUsage',{configurable:true,value:{VERTEX:1,COPY_DST:2,UNIFORM:4}});
Object.defineProperty(globalThis,'GPUTextureUsage',{configurable:true,value:{RENDER_ATTACHMENT:1}});
Object.defineProperty(globalThis,'devicePixelRatio',{configurable:true,value:1});
function mock(){
  const log=[],buffers=[],textures=[],passes=[],listeners=new Map();let resolveLost;
  const context={configure(){log.push('configure');},unconfigure(){log.push('unconfigure');},getCurrentTexture(){if(device.failTextureView)throw new Error('texture view failure');return {createView:()=>({})};}};
  const canvas={width:300,height:150,clientWidth:640,clientHeight:480,getContext:()=>context};
  const device={buffers,textures,passes,log,popErrors:[],scopeDepth:0,
    lost:new Promise(resolve=>{resolveLost=resolve;}),
    addEventListener(name,fn){listeners.set(name,fn);},removeEventListener(name,fn){if(listeners.get(name)===fn)listeners.delete(name);},
    emitError(message){listeners.get('uncapturederror')?.({error:{message}});},
    createShaderModule(){return {};},createRenderPipeline(){if(this.failPipeline)throw new Error('pipeline failure');return {getBindGroupLayout:()=>({})};},createBindGroup(){return {};},
    createBuffer(options){if(this.failCreateBuffer?.(options))throw new Error('buffer creation failure');const b={...options,destroyed:0,data:new Uint8Array(options.size),destroy(){++this.destroyed;}};buffers.push(b);return b;},
    createTexture(options){if(this.failDepth)throw new Error('depth creation failure');const t={...options,destroyed:0,destroy(){++this.destroyed;},createView:()=>({})};textures.push(t);return t;},
    createCommandEncoder(){return {beginRenderPass(){const p={draws:[],bindings:new Map(),setPipeline(){},setBindGroup(){},setVertexBuffer(slot,b){this.bindings.set(slot,b);},draw(...args){this.draws.push({args,buffer:this.bindings.get(0)});},end(){}};passes.push(p);return p;},finish:()=>({})};},
    pushErrorScope(kind){assert.equal(kind,'validation');++this.scopeDepth;log.push('push');},
    popErrorScope(){assert.ok(this.scopeDepth>0);--this.scopeDepth;log.push('pop');const value=this.popErrors.shift();return value instanceof Error?Promise.reject(value):Promise.resolve(value??null);},
    destroy(){log.push('device-destroy');},
    queue:{writeBuffer(buffer,offset,data,dataOffset=0,size){if(device.failWrite?.(buffer))throw new Error('write failure');const bpe=data.BYTES_PER_ELEMENT??1;const view=new Uint8Array(data.buffer,data.byteOffset+dataOffset*bpe,size===undefined?data.byteLength-dataOffset*bpe:size*bpe);buffer.data.set(view,offset);},
      submit(){if(device.failSubmit)throw new Error('submit failure');log.push('submit');},onSubmittedWorkDone(){log.push('done');return device.workPromise??Promise.resolve();}}
  };
  const adapter={requestDevice:async()=>device};
  Object.defineProperty(globalThis,'navigator',{configurable:true,value:{gpu:{getPreferredCanvasFormat:()=> 'bgra8unorm',requestAdapter:async()=>adapter}}});
  return {device,canvas,context,adapter,resolveLost,make:onError=>new Renderer(canvas,device,adapter,onError)};
}

test('derived render token copies actual SDK bytes and exposes frozen metadata only',()=>{
  const result=dto(),expected=new Float32Array(result.geometry.interleaved),descriptor=createDerivedMeshRenderData(result);
  assert.deepEqual(Object.keys(descriptor),['vertexCount','triangleCount','floatCount']);assert.deepEqual(descriptor,{vertexCount:3,triangleCount:1,floatCount:18});assert.ok(Object.isFrozen(descriptor));
  result.geometry.interleaved.fill(99);result.geometry.positions[0][0]=99;result.audits[0].normal.fill(99);
  assert.deepEqual(bytes(copyDerivedMeshRenderVertices(descriptor)),bytes(expected));const copy=copyDerivedMeshRenderVertices(descriptor);copy.fill(-1);assert.deepEqual(bytes(copyDerivedMeshRenderVertices(descriptor)),bytes(expected));
  assert.equal(derivedMeshRenderInfo(descriptor),descriptor);assert.throws(()=>derivedMeshRenderInfo(Object.freeze({...descriptor})),/opaque/);assert.throws(()=>copyDerivedMeshRenderVertices(null),/opaque/);
});
test('derived render boundary rejects failed empty malformed typed geometry and audit DTOs',()=>{
  for(const value of [null,{status:'degenerate',geometry:null},{...dto(),geometry:null}])assert.throws(()=>createDerivedMeshRenderData(value));
  const edits=[r=>r.status='quality_unresolved',r=>r.reason='normal_uncertain',r=>r.failedFace=0,r=>r.geometry.positions=[],r=>r.geometry.triangles=[],r=>r.geometry.interleaved=new Float32Array(17),r=>r.geometry.interleaved=Array.from(r.geometry.interleaved),r=>r.geometry.positions[0]=[0,0,0],r=>r.geometry.positions[0][0]=NaN,r=>r.geometry.triangles[0]=[0,1,2],r=>r.geometry.triangles[0][2]=3,r=>r.geometry.triangles[0][2]=1,r=>r.geometry.maximum[0]=-1,r=>r.geometry.minimum[0]=2,r=>r.audits.pop(),r=>r.audits[0].face=1,r=>r.audits[0].cross[2]=[0,0],r=>r.audits[0].squaredCross=[0,1],r=>r.audits[0].normalized=null,r=>r.audits[0].normalError[0]=1e-5,r=>r.audits[0].normal[2]=0,r=>r.audits[0].sqrtRefinements=513,r=>r.sqrtRefinements++,r=>r.sqrtLimitedFaces++];
  for(const edit of edits){const r=dto();edit(r);assert.throws(()=>createDerivedMeshRenderData(r));}
});
test('derived render boundary preserves signed zero and rejects changed expanded positions or normals',()=>{
  const r=dto();assert.ok(Object.is(copyDerivedMeshRenderVertices(createDerivedMeshRenderData(r))[0],-0));
  r.geometry.interleaved[0]=0;assert.throws(()=>createDerivedMeshRenderData(r),/expanded position/);
  const n=dto();n.geometry.interleaved[5]=-1;assert.throws(()=>createDerivedMeshRenderData(n),/flat normal/);
});
test('derived render boundary rejects sparse holes in every audit bounds and error shape',()=>{
  for(const edit of [r=>r.audits[0].cross=Array(3),r=>r.audits[0].cross[0]=Array(2),r=>r.audits[0].squaredCross=Array(2),r=>r.audits[0].normalized=Array(3),r=>r.audits[0].normalized[0]=Array(2),r=>r.audits[0].normalError=Array(3)]){
    const r=dto();edit(r);assert.throws(()=>createDerivedMeshRenderData(r));
  }
  assert.deepEqual(createDerivedMeshRenderData(dto()),{vertexCount:3,triangleCount:1,floatCount:18});
});
test('mock GPU uploads all exact derived bytes and draws every expanded corner without compileMesh',()=>{
  const m=mock(),r=m.make(),descriptor=token(),expected=copyDerivedMeshRenderVertices(descriptor);assert.equal(descriptor.triangles,undefined);
  r.render([item(descriptor)],camera);const resource=r.meshBuffers.get('derived');assert.deepEqual(Buffer.from(resource.buffer.data),bytes(expected));assert.deepEqual(Buffer.from(resource.buffer.data.slice(-24)),bytes(expected).subarray(-24));
  assert.deepEqual(m.device.passes.at(-1).draws[0].args,[3,1,0,0]);assert.equal(r.stats.uploadedMeshBytes,72);assert.equal(r.stats.triangles,1);assert.equal(r.stats.drawCalls,1);r.dispose();
});
test('mock GPU cache replacement and render empty destroy old mesh resources and clear draws',()=>{
  const m=mock(),r=m.make(),a=item();r.render([a],camera);const old=r.meshBuffers.get(a.id).buffer,count=m.device.buffers.length;r.render([a],camera);assert.equal(m.device.buffers.length,count);
  r.render([item(token())],camera);const next=r.meshBuffers.get(a.id).buffer;assert.equal(old.destroyed,1);assert.equal(next.destroyed,0);
  r.render([],camera);assert.equal(next.destroyed,1);assert.equal(r.meshBuffers.size,0);assert.deepEqual(m.device.passes.at(-1).draws,[]);assert.equal(r.stats.drawCalls,0);assert.equal(r.stats.triangles,0);r.dispose();
});
test('mock GPU legacy editable mesh and box share budgets and instance order with derived mesh',()=>{
  const m=mock(),r=m.make(),legacy={...item(createBoxMesh(),'editable'),type:'mesh'},box={...item(undefined,'box'),type:'box'};r.render([item(),box,legacy],camera);
  assert.deepEqual(m.device.passes.at(-1).draws.map(x=>x.args),[[36,1],[3,1,0,1],[36,1,0,2]]);assert.equal(r.stats.triangles,25);
  assert.throws(()=>r.render([item(),{...legacy,id:'derived'}],camera),/unique/);assert.throws(()=>r.render([{...item(),mesh:dto()}],camera),/opaque/);assert.throws(()=>r.render([{...item(),mesh:null}],camera),/opaque/);r.dispose();
});
test('mock GPU capacity covers full SDK-sized bytes and aggregate limits explicitly',()=>{
  // Repeat an actual SDK face DTO to exercise the structural/upload capacity;
  // this does not replace the independent C++ maximum-capacity kernel test.
  const data=dto(),g=data.geometry,a=data.audits[0];g.positions.push(...Array.from({length:2045},()=>new Float32Array(3)));
  g.triangles=Array.from({length:32768},()=>new Uint32Array([0,1,2]));g.interleaved=new Float32Array(32768*18);
  for(let i=0;i<32768;++i)g.interleaved.set(dtoFace,18*i);
  data.audits=Array.from({length:32768},(_,face)=>({...a,face}));data.sqrtRefinements=a.sqrtRefinements*32768;data.sqrtLimitedFaces=a.sqrtRefinementLimited?32768:0;
  const descriptor=createDerivedMeshRenderData(data),m=mock(),r=m.make();r.render([item(descriptor)],camera);
  assert.equal(r.meshBuffers.get('derived').buffer.size,2359296);assert.deepEqual(m.device.passes.at(-1).draws[0].args,[98304,1,0,0]);assert.deepEqual(Buffer.from(r.meshBuffers.get('derived').buffer.data.slice(-72)),bytes(dtoFace));
  const eight=Array.from({length:8},(_,i)=>item(descriptor,String(i)));assert.equal(r.validateBudget(eight).triangles,262144);assert.throws(()=>r.validateBudget([...eight,{type:'box'}]),/triangle budget/);
  assert.throws(()=>r.validateBudget(Array.from({length:129},(_,i)=>item(descriptor,String(i)))),/draw budget/);assert.throws(()=>r.validateBudget(Array(4097).fill({type:'box'})),/instance budget/);r.dispose();
  data.geometry.positions.push(new Float32Array(3));assert.throws(()=>createDerivedMeshRenderData(data),/2048/);
});
const dtoFace=new Float32Array(dto().geometry.interleaved);
test('mock GPU failed writes and later buffer creation discard all candidates and preserve old snapshots',()=>{
  for(const failure of ['write','create']){
    const m=mock(),r=m.make();r.render([item(token(),'a'),item(token(),'b')],camera);const old=[...r.meshBuffers.values()].map(x=>x.buffer);const before=m.device.buffers.length;let attempts=0;
    if(failure==='write')m.device.failWrite=b=>b!==r.uniform&&b!==r.instances&&++attempts===2;else m.device.failCreateBuffer=()=>++attempts===2;
    assert.throws(()=>r.render([item(token(),'a'),item(token(),'b')],camera),/failure/);for(const b of m.device.buffers.slice(before))assert.equal(b.destroyed,1);assert.ok(old.every(b=>b.destroyed===0));assert.deepEqual([...r.meshBuffers.values()].map(x=>x.buffer),old);
    m.device.failWrite=undefined;m.device.failCreateBuffer=undefined;r.render([item(token(),'a'),item(token(),'b')],camera);assert.ok(old.every(b=>b.destroyed===1));r.dispose();
  }
});
test('mock GPU submit failure releases new candidates and keeps the previous committed mesh',()=>{
  const m=mock(),r=m.make();r.render([item()],camera);const old=r.meshBuffers.get('derived').buffer,before=m.device.buffers.length;m.device.failSubmit=true;
  assert.throws(()=>r.render([item()],camera),/submit/);assert.equal(m.device.buffers[before].destroyed,1);assert.equal(old.destroyed,0);assert.equal(r.meshBuffers.get('derived').buffer,old);m.device.failSubmit=false;r.render([],camera);assert.equal(old.destroyed,1);r.dispose();
});
test('mock GPU explicit empty scene destroys old geometry even when the clearing frame fails',()=>{
  const m=mock(),r=m.make();r.render([item()],camera);const previous=r.meshBuffers.get('derived').buffer;m.device.failTextureView=true;
  assert.throws(()=>r.render([],camera),/texture view/);assert.equal(previous.destroyed,1);assert.equal(r.meshBuffers.size,0);assert.equal(r.stats.drawCalls,0);r.dispose();
});
test('mock GPU resize and idempotent disposal release every owned buffer depth and context but not device',()=>{
  const m=mock(),r=m.make();r.render([item()],camera);const oldDepth=r.depth;m.canvas.clientWidth=800;m.device.failDepth=true;assert.throws(()=>r.resize(),/depth/);assert.equal(oldDepth.destroyed,0);assert.equal(r.depth,oldDepth);m.device.failDepth=false;r.resize();assert.equal(oldDepth.destroyed,1);
  r.dispose();r.dispose();assert.ok(m.device.buffers.every(b=>b.destroyed===1));assert.ok(m.device.textures.every(t=>t.destroyed===1));assert.equal(m.device.log.filter(x=>x==='unconfigure').length,1);assert.ok(!m.device.log.includes('device-destroy'));assert.throws(()=>r.render([],camera),/disposed/);
});
test('mock GPU device loss releases resources and callbacks after disposal have no effect',async()=>{
  const m=mock(),errors=[],r=m.make(x=>errors.push(x));r.render([item()],camera);m.resolveLost({message:'test loss'});await Promise.resolve();assert.equal(r.disposed,true);assert.equal(r.lost,true);assert.equal(r.meshBuffers.size,0);assert.ok(m.device.buffers.every(b=>b.destroyed===1));assert.equal(errors.length,1);m.device.emitError('late');assert.equal(errors.length,1);
  const n=mock(),late=[],disposed=n.make(x=>late.push(x));disposed.dispose();n.resolveLost({message:'ignored'});await Promise.resolve();assert.deepEqual(late,[]);
});
test('mock GPU checked rendering balances scopes for success synchronous and asynchronous errors',async()=>{
  const m=mock(),r=m.make();await r.renderChecked([item()],camera);assert.equal(m.device.scopeDepth,0);assert.deepEqual(m.device.log.slice(-4),['push','submit','pop','done']);
  await assert.rejects(r.renderChecked([{...item(),mesh:null}],camera),/opaque/);assert.equal(m.device.scopeDepth,0);assert.equal(r.meshBuffers.size,0);
  m.device.popErrors.push({message:'validation test'});await assert.rejects(r.renderChecked([item()],camera),/validation test/);assert.equal(r.meshBuffers.size,0);assert.equal(m.device.scopeDepth,0);
  m.device.workPromise=Promise.reject(new Error('work failure'));await assert.rejects(r.renderChecked([item()],camera),/work failure/);assert.equal(r.meshBuffers.size,0);assert.equal(m.device.scopeDepth,0);r.dispose();
});
test('mock GPU checked rendering cannot revive a renderer disposed during completion wait',async()=>{
  const m=mock(),r=m.make();let complete;m.device.workPromise=new Promise(resolve=>{complete=resolve;});const pending=r.renderChecked([item()],camera);await Promise.resolve();r.dispose();complete();await assert.rejects(pending,/disposed/);assert.equal(r.meshBuffers.size,0);
});
test('mock GPU an older asynchronous validation failure cannot discard newer frame resources',async()=>{
  const m=mock(),r=m.make();let resolveOld;m.device.popErrors.push(new Promise(resolve=>{resolveOld=resolve;}));
  const older=r.renderChecked([item(token(),'old')],camera);await r.renderChecked([item(token(),'new')],camera);
  const latest=r.meshBuffers.get('new').buffer;resolveOld({message:'old validation failure'});await assert.rejects(older,/old validation/);
  assert.equal(r.meshBuffers.get('new').buffer,latest);assert.equal(latest.destroyed,0);assert.equal(r.stats.drawCalls,1);r.dispose();
});
test('mock GPU Renderer.create cleans partial construction and validation/pop failures with balanced scopes',async()=>{
  for(const failure of ['constructor','partial','validation','pop']){
    const m=mock();if(failure==='constructor')m.device.failPipeline=true;
    if(failure==='partial'){let calls=0;m.device.failCreateBuffer=()=>++calls===3;}
    if(failure==='validation')m.device.popErrors.push({message:'create validation'});if(failure==='pop')m.device.popErrors.push(new Error('create pop failure'));
    await assert.rejects(Renderer.create(m.canvas),/failure|validation/);assert.equal(m.device.scopeDepth,0);assert.equal(m.device.log.filter(x=>x==='pop').length,1);assert.ok(m.device.buffers.every(b=>b.destroyed===1));assert.equal(m.device.log.filter(x=>x==='unconfigure').length,1);m.resolveLost({message:'late'});await Promise.resolve();
  }
});
test('mock GPU Renderer.create rejects device loss during its validation wait',async()=>{
  const m=mock();let validation;m.device.popErrors.push(new Promise(resolve=>{validation=resolve;}));const pending=Renderer.create(m.canvas);await Promise.resolve();await Promise.resolve();
  m.resolveLost({message:'lost while creating'});await Promise.resolve();validation(null);await assert.rejects(pending,/disposed|lost/);
  assert.equal(m.device.scopeDepth,0);assert.ok(m.device.buffers.every(b=>b.destroyed===1));
});


const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const settle=()=>new Promise(resolve=>setImmediate(resolve));
const fourFaceToken=()=>createDerivedMeshRenderData(runtime.prepareDerivedMesh({positions:[[0,0,0],[1,0,0],[0,1,0],[0,0,1]],triangles:[[0,1,2],[0,3,1],[0,2,3],[1,3,2]]}));
const worldItem=(id='world')=>({...item(createBoxMesh(),id),type:'mesh'});

test('dropMesh retires exactly one owned derived or plain mesh and preserves submitted stats and other caches',()=>{
 const m=mock(),r=m.make(),cover=item(fourFaceToken(),'cover'),world=worldItem(),box={...item(undefined,'body'),type:'box'},source=copyDerivedMeshRenderVertices(cover.mesh);r.render([box,cover,world],camera);
 const coverBuffer=r.meshBuffers.get('cover').buffer,worldBuffer=r.meshBuffers.get('world').buffer,previous={...r.stats},epoch=r.renderEpoch,submitted=m.device.log.filter(x=>x==='submit').length;
 assert.equal(coverBuffer.size,288);assert.deepEqual(Buffer.from(coverBuffer.data),bytes(source));assert.deepEqual(Buffer.from(coverBuffer.data.slice(-24)),bytes(source).subarray(-24));assert.equal(r.stats.drawCalls,3);assert.equal(r.stats.triangles,28);
 assert.equal(r.dropMesh('missing'),false);assert.equal(r.renderEpoch,epoch);assert.deepEqual(r.stats,previous);assert.equal(r.dropMesh('cover'),true);assert.equal(r.renderEpoch,epoch+1);assert.equal(coverBuffer.destroyed,1);assert.equal(worldBuffer.destroyed,0);assert.equal(r.meshBuffers.get('world').buffer,worldBuffer);assert.equal(r.meshBuffers.has('cover'),false);
 assert.equal(r.stats.uploadedMeshBytes,previous.uploadedMeshBytes);assert.equal(r.stats.drawCalls,previous.drawCalls);assert.equal(r.stats.triangles,previous.triangles);assert.equal(r.stats.destroyedMeshBuffers,previous.destroyedMeshBuffers+1);assert.equal(m.device.log.filter(x=>x==='submit').length,submitted);assert.equal(r.dropMesh('cover'),false);assert.equal(coverBuffer.destroyed,1);assert.equal(r.renderEpoch,epoch+1);
 r.render([box,world],camera);assert.equal(r.stats.uploadedMeshBytes,previous.uploadedMeshBytes);assert.equal(worldBuffer.destroyed,0);assert.equal(r.stats.drawCalls,2);assert.equal(r.dropMesh('world'),true);assert.equal(worldBuffer.destroyed,1);const retiredUploads=r.stats.uploadedMeshBytes;r.render([cover,world],camera);const readded=r.meshBuffers.get('cover').buffer;assert.notEqual(readded,coverBuffer);assert.deepEqual(Buffer.from(readded.data),bytes(source));assert.equal(r.stats.uploadedMeshBytes,retiredUploads+288+864);assert.equal(coverBuffer.destroyed,1);r.dispose();assert.equal(readded.destroyed,1);assert.equal(r.dropMesh('world'),false);assert.equal(r.dropMesh('cover'),false);assert.ok(!m.device.log.includes('device-destroy'));
 // Match existing Map/Set identity semantics rather than adding a string-only
 // ID restriction to one operation while render still accepts numeric IDs.
 const n=mock(),numeric=n.make();numeric.render([item(token(),7)],camera);assert.equal(numeric.dropMesh('7'),false);assert.equal(numeric.dropMesh(7),true);numeric.dispose();
});

test('pending checked full frame pops its scope synchronously and queues completion only after validation',async()=>{
 for(const completion of ['success','failure']){const m=mock(),r=m.make(),validation=deferred(),work=deferred(),cover=item(fourFaceToken(),'cover'),world=worldItem(),body={...item(undefined,'body'),type:'box'};m.device.popErrors.push(validation.promise);m.device.workPromise=work.promise;
 const checked=r.renderChecked([world,body,cover],camera,0);assert.equal(m.device.scopeDepth,0);assert.deepEqual(m.device.log.slice(-3),['push','submit','pop']);assert.equal(m.device.log.includes('done'),false);assert.equal(m.device.log.filter(x=>x==='submit').length,1);
 const held=r.meshBuffers.get('cover').buffer,uploaded=r.stats.uploadedMeshBytes;r.render([world,{...body,position:[1,0,0]},{...cover,position:[1,0,0]}],camera,.1);assert.equal(m.device.log.filter(x=>x==='submit').length,2);assert.equal(r.stats.uploadedMeshBytes,uploaded);assert.equal(r.meshBuffers.get('cover').buffer,held);assert.equal(held.destroyed,0);assert.equal(m.device.log.includes('done'),false);
 validation.resolve(null);await settle();assert.equal(m.device.log.filter(x=>x==='done').length,1);assert.equal(m.device.log.filter(x=>x==='submit').length,2);
 const replacement=item(fourFaceToken(),'cover');r.render([world,body,replacement],camera,.2);const latest=r.meshBuffers.get('cover').buffer;assert.notEqual(latest,held);assert.equal(held.destroyed,1);assert.equal(r.stats.uploadedMeshBytes,uploaded+288);assert.equal(m.device.log.filter(x=>x==='submit').length,3);
 if(completion==='success'){work.resolve();await checked;}else{work.reject(new Error('older queue failure'));await assert.rejects(checked,/older queue/);}assert.equal(latest.destroyed,0);assert.equal(r.meshBuffers.get('cover').buffer,latest);assert.equal(r.meshBuffers.get('world').buffer.destroyed,0);assert.equal(r.stats.drawCalls,3);assert.equal(m.device.scopeDepth,0);r.dispose();}
});

test('real drop during pending validation invalidates old failure cleanup but unknown drop preserves same-epoch policy',async()=>{
 for(const actualDrop of [false,true]){const m=mock(),r=m.make(),validation=deferred(),cover=item(fourFaceToken(),'cover'),world=worldItem();m.device.popErrors.push(validation.promise);const checked=r.renderChecked([cover,world],camera),epoch=r.renderEpoch,coverBuffer=r.meshBuffers.get('cover').buffer,worldBuffer=r.meshBuffers.get('world').buffer;
  assert.equal(r.dropMesh(actualDrop?'cover':'missing'),actualDrop);assert.equal(r.renderEpoch,epoch+(actualDrop?1:0));validation.resolve({message:'pending validation failure'});await assert.rejects(checked,/pending validation/);assert.equal(m.device.log.includes('done'),false);assert.equal(coverBuffer.destroyed,1);
  if(actualDrop){assert.equal(worldBuffer.destroyed,0);assert.equal(r.meshBuffers.size,1);assert.equal(r.meshBuffers.get('world').buffer,worldBuffer);assert.equal(r.stats.drawCalls,2);const uploads=r.stats.uploadedMeshBytes;r.render([world],camera);assert.equal(r.stats.uploadedMeshBytes,uploads);assert.equal(worldBuffer.destroyed,0);}
  else{assert.equal(worldBuffer.destroyed,1);assert.equal(r.meshBuffers.size,0);assert.equal(r.stats.drawCalls,0);assert.equal(r.stats.triangles,0);}
  assert.equal(m.device.scopeDepth,0);r.dispose();assert.equal(coverBuffer.destroyed,1);assert.equal(worldBuffer.destroyed,1);
 }
});

test('drop clear reset-equivalent replacement and dispose while queue is pending cannot double-destroy or revive caches',async()=>{
 for(const action of ['drop','clear','dispose']){const m=mock(),r=m.make(),work=deferred(),cover=item(fourFaceToken(),'cover'),world=worldItem();m.device.workPromise=work.promise;const checked=r.renderChecked([cover,world],camera);await settle();const oldCover=r.meshBuffers.get('cover').buffer,oldWorld=r.meshBuffers.get('world').buffer;
  if(action==='drop')assert.equal(r.dropMesh('cover'),true);else if(action==='clear')r.render([],camera);else r.dispose();
  if(action!=='dispose'){const replacement=worldItem('new-scene');r.render([replacement],camera);const current=r.meshBuffers.get('new-scene').buffer;work.reject(new Error('old scene queue rejection'));await assert.rejects(checked,/old scene/);assert.equal(r.meshBuffers.get('new-scene').buffer,current);assert.equal(current.destroyed,0);assert.equal(r.meshBuffers.has('cover'),false);r.dispose();assert.equal(current.destroyed,1);}
  else{work.resolve();await assert.rejects(checked,/disposed/);assert.equal(r.meshBuffers.size,0);assert.equal(r.dropMesh('cover'),false);r.dispose();}
  assert.equal(oldCover.destroyed,1);assert.equal(oldWorld.destroyed,1);assert.ok(m.device.buffers.every(b=>b.destroyed===1));assert.ok(!m.device.log.includes('device-destroy'));assert.equal(m.device.scopeDepth,0);
 }
});

test('same-epoch queue failure clears all caches while later-frame and dropped epochs retain unrelated resources',async()=>{
 for(const boundary of ['same','later','drop']){const m=mock(),r=m.make(),work=deferred(),cover=item(fourFaceToken(),'cover'),world=worldItem();m.device.workPromise=work.promise;const checked=r.renderChecked([cover,world],camera);await settle();const oldCover=r.meshBuffers.get('cover').buffer,oldWorld=r.meshBuffers.get('world').buffer;
  let latest=null;if(boundary==='later'){r.render([item(token(),'new-scene')],camera);latest=r.meshBuffers.get('new-scene').buffer;}else if(boundary==='drop')r.dropMesh('cover');work.reject(new Error('queue failure boundary'));await assert.rejects(checked,/queue failure/);
  if(boundary==='same'){assert.equal(r.meshBuffers.size,0);assert.equal(r.stats.drawCalls,0);assert.equal(oldWorld.destroyed,1);}else if(boundary==='later'){assert.equal(r.meshBuffers.get('new-scene').buffer,latest);assert.equal(latest.destroyed,0);}else{assert.equal(r.meshBuffers.size,1);assert.equal(r.meshBuffers.get('world').buffer,oldWorld);assert.equal(oldWorld.destroyed,0);}
  assert.equal(oldCover.destroyed,1);r.dispose();assert.equal(oldWorld.destroyed,1);if(latest)assert.equal(latest.destroyed,1);assert.equal(m.device.scopeDepth,0);
 }
});

test('checked synchronous pop failure balances scope and later normal frames do not stack inside a pending scope',async()=>{
 const m=mock(),r=m.make();m.device.popErrorScope=function(){assert.equal(this.scopeDepth,1);--this.scopeDepth;this.log.push('pop-sync-throw');throw new Error('pop synchronous failure');};const pending=r.renderChecked([item(fourFaceToken(),'cover'),worldItem()],camera);assert.equal(m.device.scopeDepth,0);await assert.rejects(pending,/pop synchronous/);assert.equal(m.device.log.includes('done'),false);assert.equal(r.meshBuffers.size,0);assert.ok(m.device.buffers.slice(3).every(b=>b.destroyed===1));r.dispose();
 const n=mock(),other=n.make(),validation=deferred();n.device.popErrors.push(validation.promise);const bad=other.renderChecked([{...item(),mesh:null}],camera);assert.equal(n.device.scopeDepth,0);other.render([worldItem('new')],camera);const current=other.meshBuffers.get('new').buffer;validation.resolve(null);await assert.rejects(bad,/opaque/);assert.equal(other.meshBuffers.get('new').buffer,current);assert.equal(current.destroyed,0);assert.equal(n.device.log.filter(x=>x==='submit').length,1);assert.equal(n.device.log.includes('done'),false);other.dispose();
});
