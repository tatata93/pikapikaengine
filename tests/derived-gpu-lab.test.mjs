import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createDerivedGPUProfileCases} from '../tools/derived-gpu-cases.mjs';
import {createDerivedMeshProfiler} from '../tools/derived-profile.mjs';
import {createDerivedGPUProfiler} from '../tools/derived-gpu-profile.mjs';
import {initializeDerivedGPULab,encodeDerivedGPUExact,derivedGPUStatistics} from '../tools/derived-gpu-lab.mjs';
const html=await readFile(new URL('../tools/derived-gpu-lab.html',import.meta.url),'utf8'),ids=new Set([...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]));
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
function harness(){
 const elements=new Map(),events=new Map(),saves=[];
 const make=()=>({value:'',textContent:'',hidden:false,disabled:false,children:[],width:960,height:480,clientWidth:960,clientHeight:340,appendChild(x){this.children.push(x);},replaceChildren(){this.children=[];}});
 const get=id=>{assert.ok(ids.has('dg-'+id),id);if(!elements.has(id))elements.set(id,{...make(),addEventListener:(type,fn)=>events.set(id+':'+type,fn)});return elements.get(id);};
 const doc={visibilityState:'visible',location:{href:'https://example.test/tools/derived-gpu-lab.html'},getElementById:id=>get(id.slice(3)),createElement:make,addEventListener:(type,fn)=>events.set('doc:'+type,fn),defaultView:{navigator:{userAgent:'test',platform:'test'},devicePixelRatio:2,innerWidth:1000,innerHeight:700,addEventListener:(type,fn)=>events.set('window:'+type,fn)}};
 return {get,doc,saves,saveFile:(name,text,type)=>saves.push({name,text,type}),fire:(id,type='click')=>events.get(id+':'+type)?.()};
}
function gpuHarness(){
 const instances=[],options={};
 const createRenderer=async(canvas,onError)=>{
  if(options.createFailure)throw new Error('GPU unavailable');
  const r={onError,stats:{drawCalls:0,triangles:0,uploadedMeshBytes:0,destroyedMeshBuffers:0},disposed:false,disposeCalls:0,destroyCalls:0,draws:0,queueCalls:0,buffer:null,adapter:{info:{description:'stub only',isFallbackAdapter:false},features:new Set(['available-feature']),limits:{maxBufferSize:1024}},device:{features:new Set(),limits:{maxBufferSize:512}},
   render(items){assert.equal(this.disposed,false);const token=items[0].mesh;if(this.buffer!==token){if(this.buffer)this.stats.destroyedMeshBuffers++;this.stats.uploadedMeshBytes+=token.floatCount*4;this.buffer=token;}this.stats.drawCalls=1;this.stats.triangles=token.triangleCount;this.draws++;if(options.badStats)this.stats.uploadedMeshBytes++;},
   async renderChecked(items,camera,time){this.render(items,camera,time);await this.device.popErrorScope();await this.device.queue.onSubmittedWorkDone();},
   dispose(){this.disposeCalls++;this.disposed=true;if(this.buffer){this.stats.destroyedMeshBuffers++;this.buffer=null;}this.stats.drawCalls=0;this.stats.triangles=0;if(options.disposeFailure)throw new Error('dispose failed');}
  };
  r.device.popErrorScope=async()=>{if(options.validationFailure)throw new Error('validation failed');return null;};
  r.device.queue={onSubmittedWorkDone:async()=>{r.queueCalls++;if(r.queueCalls===1&&options.initWait)await options.initWait.promise;if(options.queueFailure&&r.queueCalls>1)throw new Error('queue failed');}};
  r.device.destroy=()=>{r.destroyCalls++;};instances.push(r);if(options.createWait)await options.createWait.promise;return {renderer:r,ownsDevice:options.ownsDevice??true};
 };
 return {instances,options,createRenderer};
}
async function init(ui,gpu,extra={}){let t=0;return initializeDerivedGPULab({doc:ui.doc,loadRuntime:async()=>runtime,createRenderer:gpu.createRenderer,now:()=>++t/100,loadManifest:async()=>({status:'obtained',data:{exportedFunctions:65,sourceFiles:53}}),hashEncoded:async()=>({status:'unknown',sha256:null,reason:'test capture avoids digest; full comparison remains'}),saveFile:ui.saveFile,...extra});}
function assertComplete(report,r){
 assert.equal(report.status,'completed',JSON.stringify(report.error));assert.equal(report.gpu.status,'completed');assert.equal(report.verified.fullDTOEqualPairs,5);assert.ok(report.verified.comparedNumericValues>0);assert.equal(report.verified.sourceUnchanged,true);assert.equal(report.verified.inputUnchanged,true);
 assert.deepEqual(report.execution,{prepareCompleted:10,freshCompleted:10,cacheCompleted:10,newUploads:10,drawCompleted:20});assert.equal(r.draws,20);assert.equal(r.queueCalls,21);assert.equal(r.disposeCalls,1);assert.equal(r.destroyCalls,1);assert.equal(report.disposal.delta.destroyedMeshBuffers,1);
 assert.ok(report.summary.every(row=>row.valid===row.expected));assert.ok(report.summary.filter(row=>row.phase==='measure').every(row=>row.expected===3));
 let fresh=0;for(const trial of report.trials){assert.deepEqual(trial.order,trial.pair%2?['instrumented','baseline']:['baseline','instrumented']);for(const kind of trial.order){const draw=trial.draw[kind];assert.equal(draw.fresh.delta.uploadedMeshBytes,report.input.triangles.length*18*4);assert.equal(draw.fresh.delta.destroyedMeshBuffers,fresh++===0?0:1);assert.equal(draw.cache.delta.uploadedMeshBytes,0);assert.equal(draw.cache.delta.destroyedMeshBuffers,0);}}
}

test('GPU lab static scope and exact browser encoding preserve typed bytes, signed zero and key order',()=>{
 assert.match(html,/SDK全体 \[ms\]/);assert.match(html,/新buffer転送/);assert.match(html,/再描画転送/);assert.match(html,/GPU単独/);assert.match(html,/max-width:100%;overflow:auto/);assert.match(html,/src="derived-gpu-lab.mjs"/);
 assert.notEqual(encodeDerivedGPUExact(-0).text,encodeDerivedGPUExact(0).text);assert.notEqual(encodeDerivedGPUExact(new Float32Array([1])).text,encodeDerivedGPUExact(new Uint32Array([0x3f800000])).text);assert.notEqual(encodeDerivedGPUExact({a:1,b:2}).text,encodeDerivedGPUExact({b:2,a:1}).text);assert.throws(()=>encodeDerivedGPUExact(Array(1)));assert.throws(()=>encodeDerivedGPUExact(NaN));assert.deepEqual(derivedGPUStatistics([4,1,3,2]),{samples:4,medianMs:2.5,p95Ms:4,maxMs:4});
});

test('real SDK all three finite geometries compare every DTO and execute 20 checked stub draws per case',async()=>{
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu);assert.equal(ui.get('canvas').hidden,true);assert.equal(lab.getState().report,null);assert.equal(gpu.instances.length,0);
 for(const name of ['actual-source-4','rational-normal-64','sheared-grid-512']){ui.get('case').value=name;const report=await lab.run();assertComplete(report,gpu.instances.at(-1));assert.equal(report.gpu.environment.classification,'unknown');assert.deepEqual(report.gpu.environment.deviceFeaturesEnabled.values,[]);assert.deepEqual(report.gpu.environment.adapterFeaturesAvailable.values,['available-feature']);assert.equal(ui.get('canvas').hidden,true);assert.equal(report.environment.dpr,2);}
 ui.fire('export');ui.fire('source');assert.equal(ui.saves.length,2);assert.ok(JSON.parse(ui.saves[0].text).firstPair.baseline);assert.equal(ui.saves[1].text,lab.getState().source);assert.ok(ui.get('report').textContent.includes('"firstPair"'));lab.dispose();
});

test('GPU unavailable keeps actual CPU comparisons and Source, then explicit rerun recovers',async()=>{
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu);gpu.options.createFailure=true;const report=await lab.run();assert.equal(report.status,'cpu_completed_gpu_incomplete');assert.equal(report.execution.prepareCompleted,10);assert.equal(report.execution.drawCompleted,0);assert.ok(report.summary.filter(r=>r.group==='fresh').every(r=>r.valid===0&&r.expected>0));assert.equal(ui.get('source').disabled,false);assert.equal(report.verified.sourceUnchanged,true);gpu.options.createFailure=false;assertComplete(await lab.run(),gpu.instances.at(-1));
});

test('initial queue callback followed by resolution never revives disposed GPU or falsely completes',async()=>{
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu);gpu.options.initWait=deferred();const pending=lab.run();await tick();const r=gpu.instances[0];r.onError('device lost during initial queue');gpu.options.initWait.resolve();const report=await pending;assert.equal(report.status,'cpu_completed_gpu_incomplete');assert.equal(report.gpu.status,'renderer_error');assert.equal(report.execution.drawCompleted,0);assert.equal(r.disposeCalls,1);assert.equal(r.destroyCalls,1);assert.equal(report.execution.prepareCompleted,10);assert.equal(ui.get('canvas').hidden,true);gpu.options.initWait=null;assertComplete(await lab.run(),gpu.instances.at(-1));
});

test('draw validation and queue failures release resources and preserve all CPU pairs',async()=>{
 for(const property of ['validationFailure','queueFailure']){const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu);gpu.options[property]=true;const report=await lab.run();assert.equal(report.gpu.status,'draw_failure');assert.equal(report.status,'cpu_completed_gpu_incomplete');assert.equal(report.execution.prepareCompleted,10);assert.equal(report.execution.drawCompleted,0);assert.equal(gpu.instances[0].disposeCalls,1);assert.ok(report.trials[0].draw.baseline.fresh.error);assert.ok(report.summary.filter(x=>x.group==='fresh').every(x=>x.valid===0));gpu.options[property]=false;assertComplete(await lab.run(),gpu.instances.at(-1));}
});

test('NaN, backward, thrown and overflowing clocks retain execution and exclude invalid timings',async()=>{
 for(const mode of ['nan','backward','throw','overflow']){let count=0;const now=()=>{count++;if(mode==='nan')return NaN;if(mode==='throw')throw new Error('clock throw');if(mode==='backward')return -count;return count===1?-Number.MAX_VALUE:Number.MAX_VALUE;};const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu,{now});if(mode==='overflow')count=0;const report=await lab.run();assert.equal(report.status,'timing_invalid',mode);assert.equal(report.execution.prepareCompleted,10);assert.equal(report.execution.drawCompleted,20);assert.ok(report.startup.clockError);assert.equal(report.sourcePreparation.sourceSetupMs,null);assert.equal(report.sourcePreparation.sourceEvaluationMs,null);assert.ok(report.sourcePreparation.timingErrors.length===2);assert.ok(report.summary.filter(x=>x.group==='cpu'&&x.kind==='instrumented').every(x=>x.valid===0));assert.equal(report.verified.sourceUnchanged,true);}
});

test('helper-local clock error is measurement failure even when the outer clock and real draw succeed',async()=>{
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu,{createGPUProfiler:(r,options)=>{const helper=createDerivedGPUProfiler(r,options);return {async renderChecked(...args){const value=await helper.renderChecked(...args),error=new Error('helper-local accounting');return {...value,timing:null,error,clockError:error};}};}});const report=await lab.run();assert.equal(report.status,'timing_invalid');assert.equal(report.execution.drawCompleted,20);assert.ok(report.summary.filter(x=>x.kind==='instrumented'&&['fresh','cache'].includes(x.group)).every(x=>x.valid===0));assert.equal(report.startup.clockError,null);
});

test('profiler constructor and dispose errors cannot leave running stuck or claim resources released',async()=>{
 const ui=harness(),gpu=gpuHarness();let fail=true;const lab=await init(ui,gpu,{createCPUProfiler:(...args)=>{if(fail)throw new Error('constructor failed');return createDerivedMeshProfiler(...args);}});const failed=await lab.run();assert.equal(failed.status,'failed');assert.equal(lab.getState().running,false);assert.equal(failed.summary.find(x=>x.phase==='measure').expected,3);fail=false;gpu.options.disposeFailure=true;const report=await lab.run();assert.equal(report.status,'disposal_failure');assert.equal(report.disposeErrors.length,1);assert.equal(gpu.instances[0].destroyCalls,1);assert.doesNotMatch(ui.get('status').textContent,/資源を解放しました/);gpu.options.disposeFailure=false;assertComplete(await lab.run(),gpu.instances.at(-1));
});

test('cancel during asynchronous create, initial queue and drawing is terminal; old callbacks cannot affect rerun',async()=>{
 for(const stage of ['create','queue','draw']){const ui=harness(),gpu=gpuHarness(),gate=deferred();if(stage==='create')gpu.options.createWait=gate;if(stage==='queue')gpu.options.initWait=gate;const lab=await init(ui,gpu,{...(stage==='draw'?{createGPUProfiler:(r,opts)=>{const helper=createDerivedGPUProfiler(r,opts);return {async renderChecked(...args){await gate.promise;return helper.renderChecked(...args);}};}}:{})});const pending=lab.run();await tick();assert.equal(await lab.run(),false);ui.fire('window','pagehide');gate.resolve();const report=await pending;assert.equal(report.status,'cancelled',stage);assert.equal(ui.get('canvas').hidden,true);assert.equal(gpu.instances[0].disposeCalls,1);assert.equal(lab.getState().running,false);gpu.options.createWait=null;gpu.options.initWait=null;const next=await lab.run();assertComplete(next,gpu.instances.at(-1));gpu.instances[0].onError('late old generation');assert.equal(lab.getState().report.status,'completed');}
});

test('load retry and pagehide during load cannot restore stale Source or auto-run GPU',async()=>{
 const ui=harness(),gpu=gpuHarness();let fail=true;const lab=await init(ui,gpu,{loadRuntime:async()=>{if(fail)throw new Error('unavailable WASM');return runtime;}});assert.equal(lab.getState().available,false);fail=false;assert.equal(await lab.retry(),true);assert.equal(gpu.instances.length,0);
 const gate=deferred();let block=false;const other=await init(ui,gpu,{loadRuntime:async()=>{if(block)await gate.promise;return runtime;}});block=true;const pending=other.retry();ui.fire('window','pagehide');gate.resolve();assert.equal(await pending,false);assert.equal(other.getState().available,false);assert.equal(other.getState().loading,false);
});

test('malformed GPU stats and mismatched numerical DTO are explicit failed audits with immutable captured inputs',async()=>{
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu);gpu.options.badStats=true;const statsFailure=await lab.run();assert.equal(statsFailure.status,'failed');assert.match(statsFailure.error.message,/byte/);assert.equal(gpu.instances[0].disposeCalls,1);assert.equal(statsFailure.execution.freshCompleted,0);assert.equal(statsFailure.trials[0].draw.baseline.fresh.state,'failed');assert.equal(statsFailure.trials[0].draw.baseline.fresh.checkedResolved,true);assert.ok(statsFailure.summary.filter(row=>row.group==='fresh').every(row=>row.valid===0));
 for(const mutateInput of [false,true]){const ui2=harness(),gpu2=gpuHarness();let setup;const other=await init(ui2,gpu2,{createCases:(...args)=>(setup=createDerivedGPUProfileCases(...args)),createCPUProfiler:(...args)=>{const helper=createDerivedMeshProfiler(...args);return {prepare(...params){const value=helper.prepare(...params);value.result.audits[0].normalError[0]=.01;if(mutateInput)setup.cases[0].input.positions[0][0]=99;return value;}};}});const report=await other.run();assert.equal(report.status,'failed');assert.match(report.error.message,mutateInput?/入力/:/数値結果/);assert.equal(report.input.positions[0][0],0);assert.equal(report.verified.inputUnchanged,!mutateInput);assert.equal(gpu2.instances[0].disposeCalls,1);assert.ok(report.summary.filter(x=>['cpu','fresh'].includes(x.group)).every(x=>x.valid===0));}

});

test('raw Source preparation times are independently validated and nonowned devices are never destroyed',async()=>{
 const ui=harness(),gpu=gpuHarness();gpu.options.ownsDevice=false;const lab=await init(ui,gpu,{createCases:(...args)=>{const setup=createDerivedGPUProfileCases(...args);setup.sourcePreparation.sourceSetupMs=Infinity;setup.sourcePreparation.sourceEvaluationMs=-1;return setup;}});const report=await lab.run();assert.equal(report.status,'timing_invalid');assert.equal(report.sourcePreparation.sourceSetupMs,null);assert.equal(report.sourcePreparation.sourceEvaluationMs,null);assert.equal(report.sourcePreparation.timingErrors.length,2);assert.equal(report.execution.drawCompleted,20);assert.equal(gpu.instances[0].destroyCalls,0);assert.equal(report.disposal.ownedDevice,false);
});


test('callback during checked draw rejects that observation even if the checked promise resolves',async()=>{
 const ui=harness(),gpu=gpuHarness(),create=gpu.createRenderer;
 // Delay an original baseline checked call after its submission while retaining
 // the actual SDK CPU queries; this is GPU observation failure injection only.
 let r,resolveDraw,ready;const started=new Promise(resolve=>{ready=resolve;});
 const other=await init(ui,gpu,{createRenderer:async(...args)=>{const handle=await create(...args);r=handle.renderer;const original=r.renderChecked;r.renderChecked=async function(...values){await Reflect.apply(original,this,values);await new Promise(resolve=>{resolveDraw=resolve;ready();});};return handle;}});
 const pending=other.run();await started;r.onError('uncaptured during draw');resolveDraw();const report=await pending;
 assert.equal(report.status,'cpu_completed_gpu_incomplete');assert.equal(report.execution.prepareCompleted,10);assert.equal(report.execution.drawCompleted,0);const draw=report.trials[0].draw.baseline.fresh;assert.equal(draw.state,'failed');assert.equal(draw.checkedResolved,true);assert.match(draw.error.message,/uncaptured/);assert.ok(report.summary.filter(row=>row.group==='fresh').every(row=>row.valid===0));assert.equal(r.disposeCalls,1);other.dispose();
});


test('sparse injected getter telemetry is rejected instead of silently skipping its holes',async()=>{
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu,{createCPUProfiler:(...args)=>{const helper=createDerivedMeshProfiler(...args);return {prepare(...values){const outcome=helper.prepare(...values);outcome.timing.getterKinds=Array(4);return outcome;}};}});const report=await lab.run();assert.equal(report.status,'failed');assert.match(report.error.message,/getter/);assert.equal(report.execution.drawCompleted,0);assert.equal(gpu.instances[0].disposeCalls,1);assert.equal(lab.getState().running,false);
});
