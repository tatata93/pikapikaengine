import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {Renderer} from '../engine/renderer.mjs';
import {createDerivedMeshRenderData,copyDerivedMeshRenderVertices} from '../engine/derived-render.mjs';
import {createDerivedGPUProfiler} from '../tools/derived-gpu-profile.mjs';
import {createDerivedGPUProfileCases} from '../tools/derived-gpu-cases.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const camera={eye:[3,3,5],target:[0,0,0]};
const token=()=>createDerivedMeshRenderData(runtime.prepareDerivedMesh({positions:[[-0,0,0],[1,0,0],[0,1,0],[0,0,1]],triangles:[[0,1,2],[0,3,1],[0,2,3],[1,3,2]]}));
const item=(mesh=token())=>({id:'derived',type:'derived-mesh',mesh,position:[0,0,0],scale:[1,1,1],color:[.2,.5,.8]});
const bytes=value=>Buffer.from(value.buffer,value.byteOffset,value.byteLength);
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const ticking=()=>{let time=0;return ()=>time++;};
Object.defineProperty(globalThis,'GPUBufferUsage',{configurable:true,value:{VERTEX:1,COPY_DST:2,UNIFORM:4}});
Object.defineProperty(globalThis,'GPUTextureUsage',{configurable:true,value:{RENDER_ATTACHMENT:1}});
Object.defineProperty(globalThis,'devicePixelRatio',{configurable:true,value:1});
function mock(){
  const log=[],buffers=[],textures=[],passes=[],lost=deferred();
  const context={configure(){},unconfigure(){log.push('unconfigure');},getCurrentTexture(){return {createView:()=>({})};}};
  const canvas={width:300,height:150,clientWidth:640,clientHeight:480,getContext:()=>context};
  const device={log,buffers,textures,passes,lost:lost.promise,scopeDepth:0,popValues:[],
    addEventListener(){},removeEventListener(){},createShaderModule(){return {};},createRenderPipeline(){return {getBindGroupLayout:()=>({})};},createBindGroup(){return {};},
    createBuffer(options){const buffer={...options,data:new Uint8Array(options.size),destroyed:0,destroy(){++this.destroyed;}};buffers.push(buffer);return buffer;},
    createTexture(){const texture={destroyed:0,destroy(){++this.destroyed;},createView:()=>({})};textures.push(texture);return texture;},
    createCommandEncoder(){return {beginRenderPass(){const pass={draws:[],setPipeline(){},setBindGroup(){},setVertexBuffer(){},draw(...args){this.draws.push(args);},end(){}};passes.push(pass);return pass;},finish:()=>({})};},
    pushErrorScope(kind){assert.equal(this,device);assert.equal(kind,'validation');++this.scopeDepth;log.push('push');},
    popErrorScope(){assert.equal(this,device);assert.ok(this.scopeDepth>0);--this.scopeDepth;log.push('pop');const value=this.popValues.shift();if(value instanceof Error)throw value;return Promise.resolve(value??null);},
    destroy(){log.push('device-destroy');}
  };
  const queue={
    writeBuffer(buffer,offset,data,dataOffset=0,size){assert.equal(this,queue);if(device.writeError)throw device.writeError;const bpe=data.BYTES_PER_ELEMENT??1;buffer.data.set(new Uint8Array(data.buffer,data.byteOffset+dataOffset*bpe,size===undefined?data.byteLength-dataOffset*bpe:size*bpe),offset);},
    submit(){assert.equal(this,queue);log.push('submit');if(device.submitError)throw device.submitError;},
    onSubmittedWorkDone(){assert.equal(this,queue);log.push('done');return device.work??Promise.resolve();}
  };
  device.queue=queue;
  Object.defineProperty(globalThis,'navigator',{configurable:true,value:{gpu:{getPreferredCanvasFormat:()=> 'bgra8unorm'}}});
  const renderer=new Renderer(canvas,device,{});
  return {renderer,device,queue,log,buffers,textures,passes,lost};
}
function accounting(result,counts=[1,1,1]){
  assert.equal(result.clockError,null);assert.ok(result.timing);const {elapsedMs,stages,unassignedMs}=result.timing;
  assert.deepEqual(Object.keys(stages),['syncRender','validationWait','queueWait']);
  let sum=0;for(const [i,value]of Object.values(stages).entries()){assert.equal(value.calls,counts[i]);assert.ok(Number.isFinite(value.elapsedMs)&&value.elapsedMs>=0);sum+=value.elapsedMs;}
  assert.ok(Number.isFinite(elapsedMs)&&elapsedMs>=0);assert.ok(sum<=elapsedMs);assert.equal(unassignedMs,elapsedMs-sum);
}

test('GPU profiler uses actual checked renderer, all bytes and trailing normal, with exclusive accounting',async()=>{
  const m=mock(),mesh=token(),expected=copyDerivedMeshRenderVertices(mesh),profile=createDerivedGPUProfiler(m.renderer,{now:ticking()});
  const result=await profile.renderChecked([item(mesh)],camera,2);
  assert.equal(result.completed,true);assert.equal(result.error,null);accounting(result);assert.equal(result.timing.elapsedMs,7);assert.equal(result.timing.unassignedMs,4);
  assert.deepEqual(m.log.slice(-4),['push','submit','pop','done']);assert.equal(m.device.scopeDepth,0);
  assert.deepEqual(Buffer.from(m.renderer.meshBuffers.get('derived').buffer.data),bytes(expected));
  assert.deepEqual(Buffer.from(m.renderer.meshBuffers.get('derived').buffer.data.slice(-24)),bytes(expected).subarray(-24));
  assert.deepEqual(m.passes.at(-1).draws,[[12,1,0,0]]);assert.equal(m.renderer.stats.uploadedMeshBytes,288);m.renderer.dispose();
});
test('GPU profiler preserves all original methods and branded this, including frozen source methods',async()=>{
  const m=mock(),r=m.renderer,original=[r.render,r.renderChecked,m.device.pushErrorScope,m.device.popErrorScope,m.queue.onSubmittedWorkDone,m.queue.writeBuffer,m.queue.submit];
  for(const [object,key]of [[m.device,'popErrorScope'],[m.queue,'onSubmittedWorkDone']])Object.defineProperty(object,key,{value:object[key],writable:false,configurable:false});
  const profile=createDerivedGPUProfiler(r,{now:ticking()});assert.ok(Object.isFrozen(profile));assert.equal((await profile.renderChecked([item()],camera)).completed,true);
  assert.deepEqual([r.render,r.renderChecked,m.device.pushErrorScope,m.device.popErrorScope,m.queue.onSubmittedWorkDone,m.queue.writeBuffer,m.queue.submit],original);r.dispose();
});
test('GPU profiler cache redraw, new token replacement and empty render keep production resource behavior',async()=>{
  const m=mock(),r=m.renderer,profile=createDerivedGPUProfiler(r,{now:ticking()}),first=item();
  await profile.renderChecked([first],camera);const old=r.meshBuffers.get('derived').buffer,count=m.buffers.length,uploaded=r.stats.uploadedMeshBytes;
  accounting(await profile.renderChecked([first],camera));assert.equal(m.buffers.length,count);assert.equal(r.stats.uploadedMeshBytes,uploaded);
  await profile.renderChecked([item()],camera);const next=r.meshBuffers.get('derived').buffer;assert.equal(old.destroyed,1);assert.notEqual(next,old);assert.equal(r.stats.uploadedMeshBytes,576);
  accounting(await profile.renderChecked([],camera));assert.equal(next.destroyed,1);assert.equal(r.meshBuffers.size,0);assert.deepEqual(m.passes.at(-1).draws,[]);
  r.dispose();assert.ok(m.buffers.every(b=>b.destroyed===1));assert.ok(m.textures.every(t=>t.destroyed===1));assert.ok(!m.log.includes('device-destroy'));
});
test('GPU profiler awaits deferred validation before invoking deferred queue completion',async()=>{
  const m=mock(),validation=deferred(),work=deferred();m.device.popValues.push(validation.promise);m.device.work=work.promise;
  const pending=createDerivedGPUProfiler(m.renderer,{now:ticking()}).renderChecked([item()],camera);
  assert.deepEqual(m.log.slice(-3),['push','submit','pop']);assert.equal(m.device.scopeDepth,0);let settled=false;pending.then(()=>settled=true);
  await Promise.resolve();assert.equal(settled,false);assert.ok(!m.log.includes('done'));
  validation.resolve(null);for(let i=0;i<4&&!m.log.includes('done');++i)await Promise.resolve();assert.equal(m.log.at(-1),'done');assert.equal(settled,false);
  work.resolve();const result=await pending;assert.equal(result.completed,true);accounting(result);m.renderer.dispose();
});
test('GPU profiler attributes independent deferred CPU waits without overlapping stages',async()=>{
  const m=mock(),validation=deferred(),work=deferred();let observedTime=0;
  const submit=m.queue.submit;m.queue.submit=function(...args){Reflect.apply(submit,this,args);observedTime=5;};
  m.device.popValues.push(validation.promise);m.device.work=work.promise;
  const pending=createDerivedGPUProfiler(m.renderer,{now:()=>observedTime}).renderChecked([item()],camera);
  observedTime=15;validation.resolve(null);for(let i=0;i<5&&!m.log.includes('done');++i)await Promise.resolve();assert.equal(m.log.at(-1),'done');
  observedTime=40;work.resolve();const result=await pending;accounting(result);
  assert.deepEqual(result.timing,{elapsedMs:40,stages:{syncRender:{calls:1,elapsedMs:5},validationWait:{calls:1,elapsedMs:10},queueWait:{calls:1,elapsedMs:25}},unassignedMs:0});m.renderer.dispose();
});
test('GPU profiler synchronous invalid model and write failure retain errors, balance scope, and recover',async()=>{
  const m=mock(),r=m.renderer,profile=createDerivedGPUProfiler(r,{now:ticking()});
  await profile.renderChecked([item()],camera);
  const invalid=await profile.renderChecked([{...item(),mesh:null}],camera);assert.equal(invalid.completed,false);assert.match(invalid.error.message,/opaque/);accounting(invalid,[1,1,0]);assert.equal(r.meshBuffers.size,0);assert.equal(m.device.scopeDepth,0);
  const failure=new Error('injected write failure');m.device.writeError=failure;const failed=await profile.renderChecked([item()],camera);assert.equal(failed.error,failure);assert.equal(failed.completed,false);accounting(failed,[1,1,0]);assert.equal(m.device.scopeDepth,0);assert.ok(m.buffers.slice(3).every(b=>b.destroyed===1));
  delete m.device.writeError;assert.equal((await profile.renderChecked([item()],camera)).completed,true);r.dispose();
});
test('GPU profiler validation and queue rejections preserve checked cleanup and allow retry',async()=>{
  for(const kind of ['validation','pop','queue']){
    const m=mock(),r=m.renderer,profile=createDerivedGPUProfiler(r,{now:ticking()}),failure=new Error(`${kind} failure`);
    if(kind==='validation')m.device.popValues.push({message:failure.message});
    if(kind==='pop')m.device.popValues.push(failure);
    if(kind==='queue'){const pending=deferred();m.device.work=pending.promise;pending.reject(failure);}
    const result=await profile.renderChecked([item()],camera);assert.equal(result.completed,false);assert.match(result.error.message,/failure/);if(kind!=='validation')assert.equal(result.error,failure);
    accounting(result,kind==='queue'?[1,1,1]:[1,1,0]);assert.equal(m.device.scopeDepth,0);assert.equal(r.meshBuffers.size,0);assert.equal(r.stats.drawCalls,0);
    delete m.device.work;assert.equal((await profile.renderChecked([item()],camera)).completed,true);r.dispose();
  }
});
test('GPU profiler disposed/lost during queue wait remains failure without reviving resources',async()=>{
  for(const lost of [false,true]){
    const m=mock(),work=deferred();m.device.work=work.promise;const pending=createDerivedGPUProfiler(m.renderer,{now:ticking()}).renderChecked([item()],camera);
    for(let i=0;i<5&&!m.log.includes('done');++i)await Promise.resolve();assert.equal(m.log.at(-1),'done');
    if(lost){m.lost.resolve({message:'stub device loss'});await Promise.resolve();}else m.renderer.dispose();
    work.resolve();const result=await pending;assert.equal(result.completed,false);assert.match(result.error.message,/disposed|lost/);accounting(result);assert.equal(m.renderer.meshBuffers.size,0);assert.ok(m.buffers.every(b=>b.destroyed===1));
  }
});
test('GPU profiler clock throws, nonfinite, backwards or duration overflow do not abort real rendering',async()=>{
  const clockFailure=new Error('clock failed');
  for(const now of [()=>{throw clockFailure;},()=>NaN,()=>Infinity,(()=>{let i=0;return ()=>i++?0:1;})(),(()=>{let i=0;return ()=>i++?-Number.MAX_VALUE/(-1):-Number.MAX_VALUE;})()]){
    const m=mock(),result=await createDerivedGPUProfiler(m.renderer,{now}).renderChecked([item()],camera);
    assert.equal(result.completed,true);assert.ok(result.clockError instanceof Error);assert.equal(result.error,result.clockError);assert.equal(result.timing,null);assert.equal(m.log.at(-1),'done');assert.equal(m.renderer.stats.triangles,4);m.renderer.dispose();
  }
});
test('GPU profiler clock failure at every observation preserves GPU completion and permits next call',async()=>{
  for(let bad=0;bad<8;++bad){
    const m=mock(),failure=new Error('one bad observation');let enabled=true;
    let index=0;const p=createDerivedGPUProfiler(m.renderer,{now:()=>{const n=index++;if(enabled&&n===bad)throw failure;return n;}});
    const result=await p.renderChecked([item()],camera);assert.equal(result.completed,true);assert.equal(result.clockError,failure);assert.equal(result.timing,null);enabled=false;
    const retry=await p.renderChecked([item()],camera);assert.equal(retry.completed,true);accounting(retry);m.renderer.dispose();
  }
});
test('GPU profiler retains actual GPU error together with independent clock error',async()=>{
  const m=mock(),renderError=new Error('write'),clockError=new Error('clock');m.device.writeError=renderError;
  const result=await createDerivedGPUProfiler(m.renderer,{now:()=>{throw clockError;}}).renderChecked([item()],camera);
  assert.equal(result.completed,false);assert.equal(result.error,renderError);assert.equal(result.clockError,clockError);assert.equal(result.timing,null);assert.equal(m.device.scopeDepth,0);m.renderer.dispose();
});
test('GPU profiler rejects reentry across instances without touching current scope and releases lock',async()=>{
  const m=mock(),validation=deferred();m.device.popValues.push(validation.promise);
  const first=createDerivedGPUProfiler(m.renderer,{now:ticking()}),second=createDerivedGPUProfiler(m.renderer,{now:ticking()});
  const pending=first.renderChecked([item()],camera),log=m.log.slice();
  for(const profile of [first,second]){const rejected=await profile.renderChecked([item()],camera);assert.equal(rejected.completed,false);assert.match(rejected.error.message,/already active/);assert.equal(rejected.timing,null);assert.deepEqual(m.log,log);}
  validation.resolve(null);assert.equal((await pending).completed,true);assert.equal((await second.renderChecked([item()],camera)).completed,true);m.renderer.dispose();
});
test('GPU profiler clock callback cannot reenter its renderer through another profiler',async()=>{
  const m=mock();let nested,triggered=false,other;
  const first=createDerivedGPUProfiler(m.renderer,{now:()=>{if(!triggered){triggered=true;nested=other.renderChecked([item()],camera);}return 0;}});other=createDerivedGPUProfiler(m.renderer,{now:ticking()});
  const result=await first.renderChecked([item()],camera);assert.equal(result.completed,true);accounting(result);assert.match((await nested).error.message,/already active/);assert.equal(m.log.filter(x=>x==='submit').length,1);m.renderer.dispose();
});
test('GPU profiler constructor validates dependencies without GPU calls',()=>{
  for(const renderer of [null,{}, {render(){},renderChecked(){},device:{queue:{}}}])assert.throws(()=>createDerivedGPUProfiler(renderer),TypeError);
  const m=mock();assert.throws(()=>createDerivedGPUProfiler(m.renderer,{now:null}),TypeError);assert.deepEqual(m.log,[]);m.renderer.dispose();
});
test('GPU profiler preserves pre-render scope failure and disposed renderer errors without fictitious stages',async()=>{
  const m=mock(),failure=new Error('scope push failure'),push=m.device.pushErrorScope;
  m.device.pushErrorScope=function(){assert.equal(this,m.device);throw failure;};
  const profile=createDerivedGPUProfiler(m.renderer,{now:ticking()}),failed=await profile.renderChecked([item()],camera);
  assert.equal(failed.completed,false);assert.equal(failed.error,failure);accounting(failed,[0,0,0]);assert.equal(m.device.scopeDepth,0);assert.deepEqual(m.log,[]);
  m.device.pushErrorScope=push;assert.equal((await profile.renderChecked([item()],camera)).completed,true);m.renderer.dispose();
  const disposed=await profile.renderChecked([item()],camera);assert.equal(disposed.completed,false);assert.match(disposed.error.message,/disposed/);accounting(disposed,[0,0,0]);
});
test('GPU profiler uploads every lab case byte, caches without upload and retires preceding case buffers',async()=>{
  const {cases,verifySourceUnchanged}=createDerivedGPUProfileCases(runtime,{now:ticking()});
  assert.deepEqual(cases.map(c=>[c.name,c.input.triangles.length]),[['actual-source-4',4],['rational-normal-64',64],['sheared-grid-512',512]]);
  const m=mock(),r=m.renderer,profile=createDerivedGPUProfiler(r,{now:ticking()});let previous=null;
  for(const example of cases){
    const sourceBefore=structuredClone(example.input),result=runtime.prepareDerivedMesh(example.input,example.settings);
    assert.equal(result.status,'completed');const mesh=createDerivedMeshRenderData(result),entry=item(mesh),before=r.stats.uploadedMeshBytes;
    const uploaded=await profile.renderChecked([entry],camera);assert.equal(uploaded.completed,true);assert.equal(uploaded.error,null);accounting(uploaded);
    const buffer=r.meshBuffers.get('derived').buffer,expected=bytes(result.geometry.interleaved);
    assert.equal(expected.length,example.input.triangles.length*18*4);assert.equal(buffer.size,expected.length);
    assert.deepEqual(Buffer.from(buffer.data),expected);assert.deepEqual(Buffer.from(buffer.data.slice(-72)),expected.subarray(-72));
    assert.equal(r.stats.uploadedMeshBytes-before,expected.length);assert.deepEqual(m.passes.at(-1).draws,[[3*example.input.triangles.length,1,0,0]]);
    if(previous)assert.equal(previous.destroyed,1);assert.equal(buffer.destroyed,0);
    const cachedBytes=r.stats.uploadedMeshBytes,bufferCount=m.buffers.length,cached=await profile.renderChecked([entry],camera);
    assert.equal(cached.completed,true);assert.equal(cached.error,null);accounting(cached);
    assert.equal(r.stats.uploadedMeshBytes-cachedBytes,0);assert.equal(m.buffers.length,bufferCount);assert.equal(r.meshBuffers.get('derived').buffer,buffer);
    assert.deepEqual(example.input,sourceBefore);assert.equal(verifySourceUnchanged(),true);previous=buffer;
  }
  r.dispose();assert.equal(previous.destroyed,1);assert.ok(m.buffers.every(buffer=>buffer.destroyed===1));
});
