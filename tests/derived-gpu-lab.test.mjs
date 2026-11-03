import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';
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
async function init(ui,gpu,extra={}){let t=0;return initializeDerivedGPULab({doc:ui.doc,loadRuntime:async()=>runtime,createRenderer:gpu.createRenderer,now:()=>++t/100,loadManifest:async()=>({status:'obtained',data:{exportedFunctions:66,sourceFiles:53}}),hashEncoded:async()=>({status:'unknown',sha256:null,reason:'test capture avoids digest; full comparison remains'}),saveFile:ui.saveFile,...extra});}
function assertComplete(report,r){
 assert.equal(report.status,'completed',JSON.stringify(report.error));assert.equal(report.schema,2);assert.equal(report.kind,'derived-mesh-browser-profile');assert.equal(report.trialSchema,2);assert.equal(report.summarySchema,1);assert.equal(report.settings.readback,report.readback);assert.ok(typeof report.sessionId==='string'&&report.sessionId.length>0);assert.ok(Number.isInteger(report.runtimeGeneration)&&report.runtimeGeneration>0);assert.ok(Number.isInteger(report.runOrdinal)&&report.runOrdinal>0);assert.equal(report.gpu.status,'completed');assert.equal(report.verified.fullDTOEqualPairs,5);assert.ok(report.verified.comparedNumericValues>0);assert.equal(report.verified.sourceUnchanged,true);assert.equal(report.verified.inputUnchanged,true);
 assert.deepEqual(report.execution,{prepareCompleted:10,freshCompleted:10,cacheCompleted:10,newUploads:10,drawCompleted:20});assert.equal(r.draws,20);assert.equal(r.queueCalls,21);assert.equal(r.disposeCalls,1);assert.equal(r.destroyCalls,1);assert.equal(report.disposal.delta.destroyedMeshBuffers,1);
 const n=report.input.positions.length,t=report.input.triangles.length,records=[n,t,t,t],calls=report.readback==='batch'?records.map((v,j)=>Math.ceil(v/[20,20,3,2][j])):records;for(const trial of report.trials){const timing=trial.cpu.instrumented.timing;assert.deepEqual(timing.getterKinds,calls);assert.deepEqual(timing.getterRecords,records);assert.equal(timing.stages.cppGetter.calls,calls.reduce((a,b)=>a+b,0));assert.equal(timing.stages.outputCopy.calls,1+calls.reduce((a,b)=>a+b,0));}
 assert.ok(report.summary.every(row=>row.valid===row.expected));assert.ok(report.summary.filter(row=>row.phase==='measure').every(row=>row.expected===3));
 let fresh=0;for(const trial of report.trials){assert.deepEqual(trial.order,trial.pair%2?['instrumented','baseline']:['baseline','instrumented']);for(const kind of trial.order){const draw=trial.draw[kind];assert.equal(draw.fresh.delta.uploadedMeshBytes,report.input.triangles.length*18*4);assert.equal(draw.fresh.delta.destroyedMeshBuffers,fresh++===0?0:1);assert.equal(draw.cache.delta.uploadedMeshBytes,0);assert.equal(draw.cache.delta.destroyedMeshBuffers,0);}}
}

test('GPU lab static scope and exact browser encoding preserve typed bytes, signed zero and key order',()=>{
 assert.match(html,/SDK全体 \[ms\]/);assert.match(html,/新buffer転送/);assert.match(html,/再描画転送/);assert.match(html,/GPU単独/);assert.match(html,/max-width:100%;overflow:auto/);assert.match(html,/src="derived-gpu-lab\.mjs(?:\?build=[a-f0-9]{16})?"/);
 assert.notEqual(encodeDerivedGPUExact(-0).text,encodeDerivedGPUExact(0).text);assert.notEqual(encodeDerivedGPUExact(new Float32Array([1])).text,encodeDerivedGPUExact(new Uint32Array([0x3f800000])).text);assert.notEqual(encodeDerivedGPUExact({a:1,b:2}).text,encodeDerivedGPUExact({b:2,a:1}).text);assert.throws(()=>encodeDerivedGPUExact(Array(1)));assert.throws(()=>encodeDerivedGPUExact(NaN));assert.deepEqual(derivedGPUStatistics([4,1,3,2]),{samples:4,medianMs:2.5,p95Ms:4,maxMs:4});
});

test('real SDK all three geometries in both modes compare every DTO and execute 20 checked stub draws per run',async()=>{
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu);assert.equal(ui.get('canvas').hidden,true);assert.equal(lab.getState().report,null);assert.equal(gpu.instances.length,0);
 let ordinal=0,session=null,generation=null;assert.equal(ui.get('readback').value,'single');
 for(const name of ['actual-source-4','rational-normal-64','sheared-grid-512']){let previous=null;for(const readback of ['single','batch']){ui.get('case').value=name;ui.get('readback').value=readback;const report=await lab.run();assertComplete(report,gpu.instances.at(-1));assert.equal(report.readback,readback);assert.equal(report.runOrdinal,++ordinal);session??=report.sessionId;generation??=report.runtimeGeneration;assert.equal(report.sessionId,session);assert.equal(report.runtimeGeneration,generation);if(previous){assert.deepEqual(report.firstPair,previous.firstPair);assert.deepEqual(report.input,previous.input);assert.equal(report.sourcePreparation.authorSourceBefore,previous.sourcePreparation.authorSourceBefore);const {readback:ignored,...settings}=report.settings;const {readback:other,...oldSettings}=previous.settings;assert.deepEqual(settings,oldSettings);}previous=report;assert.equal(report.gpu.environment.classification,'unknown');assert.deepEqual(report.gpu.environment.deviceFeaturesEnabled.values,[]);assert.deepEqual(report.gpu.environment.adapterFeaturesAvailable.values,['available-feature']);assert.equal(ui.get('canvas').hidden,true);assert.equal(report.environment.dpr,2);}}
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
 const completed=await lab.run();assertComplete(completed,gpu.instances.at(-1));assert.ok(ui.get('rows').children.length>0);assert.ok(ui.get('summary').children.length>0);assert.equal(await lab.retry(),true);assert.equal(ui.get('rows').children.length,0);assert.equal(ui.get('summary').children.length,0);assert.equal(ui.get('export').disabled,true);assert.equal(ui.get('canvas').hidden,true);assert.equal(lab.getState().report,null);assert.equal(gpu.instances.length,1);assert.doesNotMatch(ui.get('cpu').textContent,/全数値の一致/);
 const next=await lab.run();assertComplete(next,gpu.instances.at(-1));assert.equal(next.runtimeGeneration,completed.runtimeGeneration+1);fail=true;const failedReload=lab.retry();assert.equal(ui.get('rows').children.length,0);assert.equal(ui.get('summary').children.length,0);assert.equal(ui.get('export').disabled,true);assert.match(ui.get('runtime').textContent,/読込み中/);assert.equal(await failedReload,false);assert.match(ui.get('runtime').textContent,/未取得/);assert.equal(ui.get('rows').children.length,0);assert.equal(ui.get('summary').children.length,0);assert.equal(lab.getState().report,null);assert.equal(lab.getState().available,false);assert.doesNotMatch(ui.get('gpu').textContent,/完了|転送と再描画/);
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


test('dense validation rejects sparse or confused calls and record telemetry in both modes',async()=>{
 for(const mode of ['single','batch'])for(const field of ['getterKinds','getterRecords']){const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu,{createCPUProfiler:(...args)=>{const helper=createDerivedMeshProfiler(...args);return {prepare(...values){const outcome=helper.prepare(...values);outcome.timing[field]=Array(4);return outcome;}};}});ui.get('readback').value=mode;const report=await lab.run();assert.equal(report.status,'failed');assert.match(report.error.message,/getter/);assert.equal(report.execution.drawCompleted,0);assert.equal(gpu.instances[0].disposeCalls,1);assert.equal(lab.getState().running,false);}
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu,{createCPUProfiler:(...args)=>{const helper=createDerivedMeshProfiler(...args);return {prepare(...values){const outcome=helper.prepare(...values);outcome.timing.getterKinds=[...outcome.timing.getterRecords];return outcome;}};}});ui.get('readback').value='batch';assert.equal((await lab.run()).status,'failed');
});

function runtimeFacade(transform){
 const forwarded=new Map(),native=new Proxy(Object.create(null),{get(_target,key){const value=runtime.native[key];const changed=transform(key,value);if(changed!==value)return changed;if(typeof value!=='function')return value;if(!forwarded.has(key))forwarded.set(key,(...args)=>Reflect.apply(value,runtime.native,args));return forwarded.get(key);}});
 return new SimulationRuntime(native,runtime.metadata,runtime.wasmBytes,runtime.startupMs);
}

test('invalid mode and legacy batch capability fail before GPU or native exchange and preserve explicit single compatibility',async()=>{
 const counts={query:0,single:0,batch:0,exchange:0},legacy=runtimeFacade((key,value)=>{if(key==='_pp_sim_derived_mesh_records')return undefined;if(['_pp_sim_derived_mesh','_pp_sim_derived_mesh_record','_pp_sim_input_f64_ptr','_pp_sim_input_u32_ptr'].includes(key))return (...args)=>{if(key==='_pp_sim_derived_mesh')counts.query++;else if(key==='_pp_sim_derived_mesh_record')counts.single++;else counts.exchange++;return Reflect.apply(value,runtime.native,args);};return value;});
 const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu,{loadRuntime:async()=>legacy});const before={...counts};
 for(const mode of ['auto','batch']){ui.get('readback').value=mode;const report=await lab.run();assert.equal(report.status,'host_rejected');assert.equal(report.rejection,mode==='batch'?'batch_unavailable':'invalid_readback');assert.deepEqual(counts,before);assert.equal(gpu.instances.length,0);assert.equal(report.execution.prepareCompleted,0);assert.equal(report.execution.drawCompleted,0);assert.equal(ui.get('source').disabled,false);assert.equal(ui.get('canvas').hidden,true);}
 ui.get('readback').value='single';ui.fire('readback','change');assert.equal(lab.getState().report,null);assert.equal(ui.get('export').disabled,true);const success=await lab.run();assertComplete(success,gpu.instances.at(-1));assert.equal(success.readback,'single');assert.equal(success.runOrdinal,3);assert.ok(counts.query>0&&counts.single>0);
});

test('actual batch packet and ABI failures never fall back and a later explicit run recovers',async()=>{
 for(const failure of ['packet','abi'])for(const failureAt of [1,2]){let enabled=true,singleCalls=0,queryCount=0;const wrapped=runtimeFacade((key,value)=>{if(key==='_pp_sim_derived_mesh')return (...args)=>{queryCount++;return Reflect.apply(value,runtime.native,args);};if(key==='_pp_sim_derived_mesh_record')return (...args)=>{singleCalls++;return Reflect.apply(value,runtime.native,args);};if(key==='_pp_sim_derived_mesh_records')return (...args)=>{if(enabled&&queryCount>=failureAt&&failure==='abi')return 1;const code=Reflect.apply(value,runtime.native,args);if(enabled&&queryCount>=failureAt&&code===0){const pointer=runtime.native._pp_sim_output_f64_ptr()/8;runtime.native.HEAPF64[pointer+3]=99;}return code;};return value;});
  const ui=harness(),gpu=gpuHarness(),lab=await init(ui,gpu,{loadRuntime:async()=>wrapped});ui.get('readback').value='batch';const failed=await lab.run();assert.equal(failed.status,'failed');assert.equal(failed.execution.prepareCompleted,0);assert.equal(failed.execution.drawCompleted,0);assert.equal(singleCalls,0);assert.equal(gpu.instances[0].disposeCalls,1);assert.equal(failed.firstPair,null);assert.equal(failed.trials[0].cpu[failureAt===1?'baseline':'instrumented'].clockError,null);assert.equal(failed.verified.sourceUnchanged,true);enabled=false;assertComplete(await lab.run(),gpu.instances.at(-1));assert.equal(singleCalls,0);ui.get('readback').value='single';assertComplete(await lab.run(),gpu.instances.at(-1));assert.ok(singleCalls>0);
 }
});

test('mode change clears stale results and pending create queue or checked promises cannot restore the old run',async()=>{
 for(const stage of ['create','queue','draw']){const ui=harness(),gpu=gpuHarness(),gate=deferred();if(stage==='create')gpu.options.createWait=gate;if(stage==='queue')gpu.options.initWait=gate;
  const lab=await init(ui,gpu,{...(stage==='draw'?{createGPUProfiler:(r,options)=>{const helper=createDerivedGPUProfiler(r,options);return {async renderChecked(...args){await gate.promise;return helper.renderChecked(...args);}};}}:{})});
  const pending=lab.run();await tick();assert.equal(ui.get('readback').disabled,true);assert.equal(ui.get('case').disabled,true);ui.get('readback').value='batch';ui.fire('readback','change');assert.equal(lab.getState().report,null);assert.equal(ui.get('rows').children.length,0);assert.equal(ui.get('summary').children.length,0);assert.equal(ui.get('export').disabled,true);gate.resolve();const cancelled=await pending;assert.equal(cancelled.status,'cancelled');assert.equal(cancelled.readback,'single');assert.equal(lab.getState().report,null);assert.equal(ui.get('canvas').hidden,true);assert.equal(gpu.instances[0].disposeCalls,1);gpu.options.createWait=null;gpu.options.initWait=null;
  const next=await lab.run();assertComplete(next,gpu.instances.at(-1));assert.equal(next.readback,'batch');assert.equal(next.runOrdinal,cancelled.runOrdinal+1);assert.equal(next.runtimeGeneration,cancelled.runtimeGeneration);assert.equal(next.sessionId,cancelled.sessionId);gpu.instances[0].onError('late old mode');assert.equal(lab.getState().report.readback,'batch');
 }
});

test('a run owns its mode and settings; selection clears exports and reload starts a new runtime generation',async()=>{
 const ui=harness(),gpu=gpuHarness();let setup;const gate=deferred();gpu.options.createWait=gate;const lab=await init(ui,gpu,{createCases:(...args)=>{setup=createDerivedGPUProfileCases(...args);for(const item of setup.cases)Object.freeze(item.settings);return setup;}});const originalSettings=setup.cases.map(item=>structuredClone(item.settings));
 const pending=lab.run();await tick();ui.get('readback').value='batch';gate.resolve();const single=await pending;assertComplete(single,gpu.instances.at(-1));assert.equal(single.readback,'single');assert.equal(single.settings.readback,'single');assert.deepEqual(setup.cases.map(item=>item.settings),originalSettings);
 ui.fire('readback','change');assert.equal(lab.getState().report,null);assert.equal(ui.get('rows').children.length,0);assert.equal(ui.get('export').disabled,true);assert.match(ui.get('report').textContent,/条件が変わり/);gpu.options.createWait=null;ui.get('case').value='rational-normal-64';const batch=await lab.run();assertComplete(batch,gpu.instances.at(-1));ui.fire('export');assert.match(ui.saves[0].text,/,-0,/);assert.equal(JSON.parse(ui.saves[0].text).readback,'batch');assert.equal(Object.is(batch.input.positions[0][1],-0),true);
 assert.equal(await lab.retry(),true);const reloaded=await lab.run();assertComplete(reloaded,gpu.instances.at(-1));assert.equal(reloaded.runtimeGeneration,batch.runtimeGeneration+1);assert.equal(reloaded.sessionId,batch.sessionId);assert.equal(reloaded.runOrdinal,batch.runOrdinal+1);assert.equal(reloaded.readback,'batch');
});

test('batch keeps GPU failure CPU-only recovery and clock cancellation boundaries independent',async()=>{
 for(const fault of ['unavailable','validation','clock','hidden']){const ui=harness(),gpu=gpuHarness();let invalid=false,t=0;const lab=await init(ui,gpu,{now:()=>invalid?NaN:++t/100});ui.get('readback').value='batch';if(fault==='unavailable')gpu.options.createFailure=true;if(fault==='validation')gpu.options.validationFailure=true;if(fault==='clock')invalid=true;
  if(fault==='hidden'){gpu.options.initWait=deferred();const pending=lab.run();await tick();ui.doc.visibilityState='hidden';ui.fire('doc','visibilitychange');gpu.options.initWait.resolve();const report=await pending;assert.equal(report.status,'cancelled');assert.equal(report.readback,'batch');assert.equal(gpu.instances[0].disposeCalls,1);ui.doc.visibilityState='visible';gpu.options.initWait=null;}
  else{const report=await lab.run();assert.equal(report.status,fault==='clock'?'timing_invalid':'cpu_completed_gpu_incomplete');assert.equal(report.readback,'batch');assert.equal(report.execution.prepareCompleted,10);assert.equal(report.execution.drawCompleted,fault==='clock'?20:0);assert.equal(report.verified.inputUnchanged,true);assert.equal(report.verified.sourceUnchanged,true);if(fault==='clock')assert.ok(report.summary.every(row=>row.valid===0));}
  gpu.options.createFailure=false;gpu.options.validationFailure=false;invalid=false;assertComplete(await lab.run(),gpu.instances.at(-1));
 }
});
