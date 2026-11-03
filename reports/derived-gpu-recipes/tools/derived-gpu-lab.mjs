import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {Renderer} from '../engine/renderer.mjs';
import {createDerivedMeshRenderData} from '../engine/derived-render.mjs';
import {createDerivedMeshProfiler} from './derived-profile.mjs';
import {createDerivedGPUProfiler} from './derived-gpu-profile.mjs';
import {createDerivedGPUProfileCases} from './derived-gpu-cases.mjs';

const check=(ok,message)=>{if(!ok)throw new Error(message);};
const errorView=e=>e?{name:e.name??'Error',message:e.message??String(e),code:e.code??null}:null;
const phases=['initial','warmup','measure','measure','measure'];
const phaseNames={initial:'初回',warmup:'ウォームアップ',measure:'計測'};
const kinds={baseline:'通常',instrumented:'計器付き'};
function clock(now){
 let last=null,error=null;
 const read=()=>{if(error)throw error;try{const value=now();check(Number.isFinite(value),'時計が非有限です');check(last===null||value>=last,'時計が後退しました');last=value;return value;}catch(e){error=e instanceof Error?e:new Error(String(e));throw error;}};
 return {read,get error(){return error;},safe(){try{return read();}catch{return last??0;}},start(){try{return read();}catch{return null;}},end(begin){let end;try{end=read();}catch{return null;}if(begin===null)return null;const duration=end-begin;if(!Number.isFinite(duration)||duration<0){error=new RangeError('時計の差が表現できません');return null;}return duration;}};
}
export function encodeDerivedGPUExact(value){
 const view=new DataView(new ArrayBuffer(8)),counts={numbers:0,typedElements:0,typedBytes:0};
 function encode(x){
  if(x===null)return {type:'null'};
  if(typeof x==='number'){check(Number.isFinite(x),'数値結果に非有限値があります');++counts.numbers;view.setFloat64(0,x);return {type:'number',bits:view.getBigUint64(0).toString(16).padStart(16,'0')};}
  if(ArrayBuffer.isView(x)&&!(x instanceof DataView)){const bytes=new Uint8Array(x.buffer,x.byteOffset,x.byteLength);counts.typedElements+=x.length;counts.typedBytes+=bytes.length;return {type:x.constructor.name,length:x.length,bytesHex:Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')};}
  if(Array.isArray(x)){for(let j=0;j<x.length;++j)check(j in x,'数値結果の配列が欠損しています');return {type:'Array',items:x.map(encode)};}
  if(typeof x==='object')return {type:'Object',entries:Object.keys(x).map(key=>[key,encode(x[key])])};
  check(typeof x==='string'||typeof x==='boolean','数値結果の型を保存できません');return {type:typeof x,value:x};
 }
 const encoded=encode(value);return {encoded,text:JSON.stringify(encoded),counts};
}
function signedJSON(x){
 if(typeof x==='number'){check(Number.isFinite(x),'記録に非有限値があります');return Object.is(x,-0)?'-0':JSON.stringify(x);}
 if(Array.isArray(x))return '['+x.map(signedJSON).join(',')+']';
 if(x&&typeof x==='object')return '{'+Object.entries(x).map(([k,v])=>JSON.stringify(k)+':'+signedJSON(v)).join(',')+'}';
 check(x===null||typeof x==='string'||typeof x==='boolean','記録の型が不正です');return JSON.stringify(x);
}
async function digest(text){
 if(!globalThis.crypto?.subtle)return {status:'unknown',sha256:null,reason:'crypto.subtle unavailable'};
 try{const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));return {status:'obtained',sha256:Array.from(new Uint8Array(bytes),x=>x.toString(16).padStart(2,'0')).join(''),reason:null};}
 catch(e){return {status:'unknown',sha256:null,reason:e?.message??String(e)};}
}
function properties(object){
 if(!object)return {status:'unknown',values:{},errors:[]};const names=new Set(),values={},errors=[];
 for(let p=object;p&&p!==Object.prototype;p=Object.getPrototypeOf(p))for(const name of Object.getOwnPropertyNames(p))if(name!=='constructor')names.add(name);
 for(const name of names)try{const value=object[name];if(['string','boolean'].includes(typeof value)||(typeof value==='number'&&Number.isFinite(value)))values[name]=value;}catch(e){errors.push({name,message:e?.message??String(e)});}
 return {status:Object.keys(values).length?'obtained':'unknown',values,errors};
}
const featureList=value=>{try{return value?{status:'obtained',values:Array.from(value)}:{status:'unknown',values:[]};}catch(e){return {status:'unknown',values:[],reason:e?.message??String(e)};}};
function gpuEnvironment(renderer){return {classification:'unknown',adapterInfo:properties(renderer.adapter?.info),adapterFeaturesAvailable:featureList(renderer.adapter?.features),adapterLimitsAvailable:properties(renderer.adapter?.limits),deviceFeaturesEnabled:featureList(renderer.device?.features),deviceLimits:properties(renderer.device?.limits),note:'Obtained descriptors/features do not prove hardware execution. Available adapter features are separate from device features actually enabled.'};}
const stats=renderer=>{const s=renderer.stats;for(const key of ['uploadedMeshBytes','destroyedMeshBuffers','drawCalls','triangles'])check(Number.isSafeInteger(s?.[key])&&s[key]>=0,'描画統計が不正です: '+key);return {...s};};
const delta=(a,b)=>Object.fromEntries(['uploadedMeshBytes','destroyedMeshBuffers','drawCalls','triangles'].map(key=>[key,b[key]-a[key]]));
export function derivedGPUStatistics(values){if(!values.length)return null;check(values.every(x=>Number.isFinite(x)&&x>=0),'集計値が不正です');const sorted=[...values].sort((a,b)=>a-b),n=sorted.length,m=Math.floor(n/2);return {samples:n,medianMs:n%2?sorted[m]:sorted[m-1]/2+sorted[m]/2,p95Ms:sorted[Math.ceil(.95*n)-1],maxMs:sorted.at(-1)};}
function summarize(trials){
 const rows=[];
 for(const phase of ['initial','warmup','measure'])for(const kind of ['baseline','instrumented']){
  const selected=trials.filter(t=>t.phase===phase),expected=phase==='measure'?3:1,add=(group,stage,values)=>rows.push({phase,kind,group,stage,expected,valid:values.length,unavailable:expected-values.length,statistics:derivedGPUStatistics(values)});
  for(const stage of ['elapsedMs',...(kind==='instrumented'?['f64Exchange','u32Exchange','cppQuery','cppGetter','outputCopy','unassignedMs']:[])])add('cpu',stage,selected.flatMap(t=>{if(t.cpu?.[kind]?.state!=='completed')return [];const timing=t.cpu?.[kind]?.timing,value=stage==='elapsedMs'?timing?.elapsedMs:stage==='unassignedMs'?timing?.unassignedMs:timing?.stages?.[stage]?.elapsedMs;return Number.isFinite(value)&&value>=0?[value]:[];}));
  add('factory','elapsedMs',selected.flatMap(t=>Number.isFinite(t.draw?.[kind]?.factory?.elapsedMs)?[t.draw[kind].factory.elapsedMs]:[]));
  for(const group of ['fresh','cache'])for(const stage of ['elapsedMs',...(kind==='instrumented'?['syncRender','validationWait','queueWait','unassignedMs']:[])])add(group,stage,selected.flatMap(t=>{const record=t.draw?.[kind]?.[group];if(record?.state!=='completed'||!record.timing)return [];const value=stage==='elapsedMs'?record.timing.elapsedMs:stage==='unassignedMs'?record.timing.unassignedMs:record.timing.stages?.[stage]?.elapsedMs;return Number.isFinite(value)&&value>=0?[value]:[];}));
 }
 return rows;
}
const cameraFor=name=>name==='rational-normal-64'?{eye:[4,2,9],target:[4,.1,0]}:{eye:[3,2,4],target:[1,.35,0]};
async function ownedRenderer(canvas,onError){const renderer=await Renderer.create(canvas,onError);return {renderer,ownsDevice:true};}
async function manifest(){try{const url=new URL('../assets/pikapika-simulation.build.json',import.meta.url),build=new URL(import.meta.url).searchParams.get('build');if(build)url.searchParams.set('build',build);const response=await fetch(url);if(!response.ok)throw new Error('HTTP '+response.status);return {status:'obtained',url:url.href,data:await response.json()};}catch(e){return {status:'unknown',url:new URL('../assets/pikapika-simulation.build.json',import.meta.url).href,error:errorView(e)};}}

export async function initializeDerivedGPULab({doc=globalThis.document,loadRuntime=loadSimulationRuntime,createCases=createDerivedGPUProfileCases,createRenderer=ownedRenderer,createCPUProfiler=createDerivedMeshProfiler,createGPUProfiler=createDerivedGPUProfiler,now=()=>performance.now(),hashEncoded=digest,loadManifest=manifest,saveFile}={}){
 const get=id=>doc.getElementById('dg-'+id),ui=Object.fromEntries(['case','run','retry','export','source','status','error','cpu','gpu','canvas','rows','summary','report','author','runtime'].map(id=>[id,get(id)]));
 let runtime=null,setup=null,loading=false,running=false,epoch=0,active=null,lastReport=null,startup=null,manifestInfo=null;
 const save=saveFile??((name,text,type)=>{const a=doc.createElement('a'),url=URL.createObjectURL(new Blob([text],{type}));a.href=url;a.download=name;doc.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),0);});
 const buttons=()=>{ui.run.disabled=loading||running||!setup;ui.retry.disabled=loading||running;ui.case.disabled=loading||running||!setup;ui.export.disabled=!lastReport||running;ui.source.disabled=!setup;};
 const current=run=>active===run&&epoch===run.epoch&&!run.cancelled;
 function disposeGPU(run){
  if(!run.handle||run.disposed)return;run.disposed=true;
  const {renderer,ownsDevice}=run.handle;let before=null,after=null;
  try{before=stats(renderer);}catch{}
  try{renderer.dispose();}catch(e){run.report.disposeErrors.push(errorView(e));}
  try{after=stats(renderer);}catch{}
  if(ownsDevice)try{renderer.device?.destroy?.();}catch(e){run.report.disposeErrors.push(errorView(e));}
  run.report.disposal={ownedDevice:ownsDevice,deviceDestroyRequested:ownsDevice,before,after,delta:before&&after?delta(before,after):null};
  ui.canvas.hidden=true;
 }
 function cancel(reason){++epoch;if(active){active.cancelled=true;active.report.cancellation=reason;disposeGPU(active);}ui.canvas.hidden=true;}
 function displayReport(report){
  lastReport=report;ui.report.textContent=signedJSON(report);ui.summary.replaceChildren();
  const stageNames={elapsedMs:'全体',f64Exchange:'位置の交換',u32Exchange:'面の交換',cppQuery:'C ABI照会',cppGetter:'結果の読出し',outputCopy:'結果のコピー',unassignedMs:'その他・観測負荷',syncRender:'同期の描画呼出し',validationWait:'検証待ち',queueWait:'queue待ち'};
  const groupNames={cpu:'数値監査',factory:'描画データ作成',fresh:'新buffer',cache:'同じbufferの再描画'};
  for(const row of report.summary){const tr=doc.createElement('tr'),s=row.statistics;for(const text of [phaseNames[row.phase],kinds[row.kind]+' / '+groupNames[row.group],stageNames[row.stage],row.valid+' / '+row.expected,s?s.medianMs.toFixed(4):'—',s?s.p95Ms.toFixed(4):'—',s?s.maxMs.toFixed(4):'—']){const td=doc.createElement('td');td.textContent=text;tr.appendChild(td);}ui.summary.appendChild(tr);}
  buttons();
 }
 function addTrialRows(trial){for(const kind of trial.order){const row=doc.createElement('tr'),d=trial.draw?.[kind],cpu=trial.cpu?.[kind],ms=t=>t&&Number.isFinite(t.elapsedMs)?t.elapsedMs.toFixed(4):'—';for(const text of [phaseNames[trial.phase]+' '+(trial.pair+1),kinds[kind],ms(cpu?.timing),d?.factory?.elapsedMs===null?'—':d?.factory?d.factory.elapsedMs.toFixed(4):'—',ms(d?.fresh?.timing),ms(d?.cache?.timing),d?.fresh?.delta?.uploadedMeshBytes===undefined?'—':String(d.fresh.delta.uploadedMeshBytes),d?.cache?.delta?.uploadedMeshBytes===undefined?'—':String(d.cache.delta.uploadedMeshBytes),d?.fresh?.state??'未実行']){const td=doc.createElement('td');td.textContent=text;row.appendChild(td);}ui.rows.appendChild(row);}}
 function browserEnvironment(){const nav=doc.defaultView?.navigator??globalThis.navigator??{},win=doc.defaultView??globalThis;return {userAgent:nav.userAgent??'unknown',platform:nav.userAgentData?.platform??nav.platform??'unknown',language:nav.language??'unknown',hardwareConcurrency:nav.hardwareConcurrency??'unknown',deviceMemoryGB:nav.deviceMemory??'unknown',url:doc.location?.href??'unknown',moduleURL:import.meta.url,buildMarker:new URL(import.meta.url).searchParams.get('build')??'unversioned',dpr:win.devicePixelRatio??globalThis.devicePixelRatio??'unknown',viewport:{width:win.innerWidth??null,height:win.innerHeight??null},visibilityAtStart:doc.visibilityState??'unknown'};}
 async function run(){
  if(running||loading||!setup||!runtime)return false;
  const item=setup.cases.find(c=>c.name===ui.case.value);if(!item)return false;
  running=true;const own={epoch:++epoch,cancelled:false,handle:null,disposed:false,gpuReady:false,freshCount:0,gpuEvents:[],report:null};active=own;lastReport=null;ui.rows.replaceChildren();ui.summary.replaceChildren();ui.report.textContent='計測中…';ui.error.hidden=true;ui.error.textContent='';ui.canvas.hidden=true;buttons();
  const time=clock(now);let inputBefore=null;
  const report=own.report={schema:1,status:'running',caseName:item.name,recipe:item.recipe,input:structuredClone(item.input),settings:structuredClone(item.settings),sourcePreparation:structuredClone(setup.sourcePreparation),startup,manifest:manifestInfo,runtime:runtime.diagnostics??{},environment:browserEnvironment(),camera:cameraFor(item.name),model:{position:[0,0,0],scale:[1,1,1],yaw:0},projection:{fovDegrees:60,nearMetres:.2,farMetres:1600},trials:[],firstPair:null,summary:[],gpu:{status:'not_initialized',environment:null,initialization:null,events:own.gpuEvents},disposeErrors:[],disposal:null,cancellation:null,planned:{pairs:5,prepareQueries:10,newUploads:10,cacheDraws:10,drawCalls:20},verified:{fullDTOEqualPairs:0,comparedNumericValues:0,inputUnchanged:false,sourceUnchanged:false},visibilityChanges:[],scope:'Browser small local meshes only. Queue wait is CPU-observed completion through the call point, not GPU timestamps or display presentation. No Native performance, game/robot integration or realtime guarantee.',observation:'Instrumentation overhead/timer resolution are uncalibrated. Exact comparison, digest and JSON encoding are outside query/draw timing but perturb later observations. Baseline/helper differences are not pure wrapper cost. GPU classification remains unknown.'};
  let profiler=null,gpuProfiler=null;
  function live(){check(current(own),'計測は新しい操作で中止されました');}
  function drawState(state,extra={}){return {state,timing:null,error:null,clockError:null,...extra};}
  function gpuLive(r){live();check(!own.disposed&&!own.gpuEvents.length&&!r.disposed&&!r.lost,'初期化中にGPUが無効になりました');}
  function auditTiming(outcome,names,expectedCalls=null){
   if(outcome.clockError){report.timingInvalid=true;outcome.timing=null;return;}
   if(!outcome.timing){report.timingInvalid=true;return;}
   try{const t=outcome.timing;check(Number.isFinite(t.elapsedMs)&&t.elapsedMs>=0,'全体時間が不正です');if(names){let sum=0;for(const name of names){const stage=t.stages?.[name];check(Number.isSafeInteger(stage?.calls)&&stage.calls>=0&&Number.isFinite(stage.elapsedMs)&&stage.elapsedMs>=0,'段階時間が不正です');if(expectedCalls)check(stage.calls===expectedCalls[name],'段階呼出し数が不正です');sum+=stage.elapsedMs;}check(Number.isFinite(sum)&&sum<=t.elapsedMs&&Number.isFinite(t.unassignedMs)&&t.unassignedMs>=0&&t.unassignedMs===t.elapsedMs-sum,'時間の会計が一致しません');}}catch(e){outcome.clockError=e;outcome.timing=null;report.timingInvalid=true;}
  }
  try{
   inputBefore=encodeDerivedGPUExact({input:item.input,settings:item.settings}).text;profiler=createCPUProfiler(runtime,{now:()=>time.read()});ui.cpu.textContent='数値照会を準備中…';ui.gpu.textContent='GPUの準備中…';
   ui.status.textContent='GPUの準備と初期queueの完了を確認中…';const initStart=time.start();let createMs=null,queueMs=null;
   try{
    ui.canvas.hidden=false;const begin=time.start();own.handle=await createRenderer(ui.canvas,message=>{if(!current(own))return;own.gpuEvents.push({kind:'unknown',message:String(message)});own.gpuReady=false;report.gpu.status='renderer_error';disposeGPU(own);ui.gpu.textContent='GPUのエラーで表示を終了しました。数値照会は保持します。';});createMs=time.end(begin);live();
    check(own.handle&&typeof own.handle.ownsDevice==='boolean'&&own.handle.renderer,'専用rendererの所有情報がありません');
    const r=own.handle.renderer;check(typeof r.renderChecked==='function'&&typeof r.dispose==='function','rendererの契約が不正です');report.gpu.environment=gpuEnvironment(r);check(!own.gpuEvents.length,'初期化中にGPUエラーが届きました');
    const wait=time.start();await r.device.queue.onSubmittedWorkDone();queueMs=time.end(wait);gpuLive(r);
    gpuProfiler=await createGPUProfiler(r,{now:()=>time.read()});gpuLive(r);report.gpu.environment=gpuEnvironment(r);own.gpuReady=true;report.gpu.status='ready';ui.gpu.textContent='GPUを準備しました。転送と再描画を別々に測ります。';
   }catch(e){if(!current(own))throw e;report.gpu.status=own.gpuEvents.length?'renderer_error':'unavailable_or_initialization_failure';report.gpu.error=errorView(e);disposeGPU(own);ui.gpu.textContent='GPUの準備に失敗しました。C++の数値照会を続けます。';}
   report.gpu.initialization={totalMs:time.end(initStart),rendererCreateMs:createMs,initialQueueWaitMs:queueMs,clockError:errorView(time.error),scope:'Dedicated renderer creation/pipeline validation and constructor queue completion before measured draws. No GPU-only timing.'};
   for(let pair=0;pair<5;++pair){live();const trial={pair,phase:phases[pair],order:pair%2===0?['baseline','instrumented']:['instrumented','baseline'],cpu:{},draw:{}},results={},encoded={};report.trials.push(trial);ui.status.textContent=`${phaseNames[trial.phase]} (${pair+1}/5): 数値照会を比較中…`;
    for(const kind of trial.order){let outcome;if(kind==='baseline'){let result=null,error=null;const start=time.start();try{result=runtime.prepareDerivedMesh(item.input,item.settings);}catch(e){error=e;}const elapsedMs=time.end(start);outcome={result,error,clockError:time.error,timing:elapsedMs===null?null:{elapsedMs}};}else outcome=profiler.prepare(item.input,item.settings);
     const g=outcome.result?.geometry,audits=outcome.result?.audits??[],getters=g?[g.positions.length,g.triangles.length,g.triangles.length,audits.length]:[0,0,0,audits.length],getterCount=getters.reduce((a,b)=>a+b,0);
     if(kind==='instrumented'&&outcome.result?.status==='completed'){check(outcome.timing===null||getters.every((n,i)=>outcome.timing.getterKinds?.[i]===n)&&outcome.timing.getterKinds?.length===4,'getter種別の件数が一致しません');}
     auditTiming(outcome,kind==='instrumented'?['f64Exchange','u32Exchange','cppQuery','cppGetter','outputCopy']:null,kind==='instrumented'?{f64Exchange:1,u32Exchange:1,cppQuery:1,cppGetter:getterCount,outputCopy:1+getterCount}:null);
     results[kind]=outcome.result;trial.cpu[kind]={state:outcome.result?.status==='completed'?'pending_audit':'failed',modelStatus:outcome.result?.status??null,timing:outcome.timing,error:errorView(outcome.error),clockError:errorView(outcome.clockError)};
     check(outcome.result?.status==='completed','C++の数値監査が完了していません');check(!outcome.error||outcome.error===outcome.clockError,'C++照会に失敗しました');encoded[kind]=encodeDerivedGPUExact(outcome.result);check(encodeDerivedGPUExact({input:item.input,settings:item.settings}).text===inputBefore,'照会入力が変更されました');
    }
    check(encoded.baseline.text===encoded.instrumented.text,'通常と計器付きの全数値結果が一致しません');setup.verifySourceUnchanged();for(const kind of trial.order)trial.cpu[kind].state='completed';report.verified.sourceUnchanged=true;report.verified.inputUnchanged=true;++report.verified.fullDTOEqualPairs;report.verified.comparedNumericValues+=encoded.baseline.counts.numbers+encoded.baseline.counts.typedElements;
    if(pair===0)report.firstPair={encoding:'tagged-exact-v1',baseline:encoded.baseline.encoded,instrumented:encoded.instrumented.encoded};
    for(const kind of trial.order){trial.cpu[kind].digest=await hashEncoded(encoded[kind].text);live();trial.cpu[kind].comparedCounts=encoded[kind].counts;
     const start=time.start(),token=createDerivedMeshRenderData(results[kind]),factoryMs=time.end(start),items=[{id:'derived-profile-view',type:'derived-mesh',mesh:token,position:[0,0,0],scale:[1,1,1],color:[.20,.78,.67]}];
     const record=trial.draw[kind]={factory:{elapsedMs:factoryMs,clockError:errorView(time.error),metadata:{...token}},fresh:drawState('not_examined'),cache:drawState('not_examined')};
     for(const mode of ['fresh','cache']){
      if(!own.gpuReady||own.disposed)continue;live();const r=own.handle.renderer,before=stats(r);let draw;
      if(kind==='baseline'){let error=null;const begin=time.start();try{await r.renderChecked(items,report.camera);}catch(e){error=e;}const elapsedMs=time.end(begin);draw={completed:!error,error,clockError:time.error,timing:elapsedMs===null?null:{elapsedMs}};}
      else draw=await gpuProfiler.renderChecked(items,report.camera);
      live();auditTiming(draw,kind==='instrumented'?['syncRender','validationWait','queueWait']:null,draw.completed?{syncRender:1,validationWait:1,queueWait:1}:null);const after=stats(r),d=delta(before,after);record[mode]=drawState(draw.completed?'pending_audit':'failed',{timing:draw.timing,error:errorView(draw.error),clockError:errorView(draw.clockError),before,after,delta:d});
      if(!draw.completed||own.disposed||own.gpuEvents.length){record[mode].state='failed';record[mode].checkedResolved=draw.completed;record[mode].error??={name:'Error',message:own.gpuEvents.at(-1)?.message??'GPUが描画の待機中に無効になりました',code:null};own.gpuReady=false;report.gpu.status='draw_failure';disposeGPU(own);ui.gpu.textContent='GPU描画を終了しました。数値照会の結果を保持します。';continue;}
      try{check(!draw.error||draw.error===draw.clockError,'描画の完了状態が不整合です');check(after.drawCalls===1&&after.triangles===token.triangleCount,'描画数が入力と一致しません');
      check(d.uploadedMeshBytes===(mode==='fresh'?token.floatCount*4:0),'転送byte数が一致しません');check(d.destroyedMeshBuffers===(mode==='fresh'&&own.freshCount>0?1:0),'旧bufferの退役数が一致しません');if(mode==='fresh')++own.freshCount;}catch(e){record[mode].state='failed';record[mode].checkedResolved=draw.completed;record[mode].error=errorView(e);throw e;}record[mode].state='completed';
      report.environment.canvas={width:ui.canvas.width,height:ui.canvas.height,cssWidth:ui.canvas.clientWidth??null,cssHeight:ui.canvas.clientHeight??null,pixelRatio:r.pixelRatio??'renderer default min(DPR,1.5)'};
     }
    }
    live();setup.verifySourceUnchanged();report.verified.sourceUnchanged=true;report.verified.inputUnchanged=true;ui.cpu.textContent=`${item.input.triangles.length}面: 全数値の一致 ${pair+1}/5組、原本・入力は不変です。`;addTrialRows(trial);
   }
   if(own.gpuReady){const records=report.trials.flatMap(t=>Object.values(t.draw)),fresh=records.filter(r=>r.fresh.state==='completed').length,cache=records.filter(r=>r.cache.state==='completed').length;check(fresh===10&&cache===10&&own.freshCount===10,'実描画の完了件数が予定と一致しません');report.gpu.status='completed';}report.status=time.error||startup?.clockError||setup.sourcePreparation.timingErrors?.length||report.timingInvalid?'timing_invalid':report.gpu.status==='completed'?'completed':'cpu_completed_gpu_incomplete';
  }catch(e){report.status=own.cancelled||!current(own)?'cancelled':'failed';report.error=errorView(e);if(current(own)){ui.error.textContent=e?.message??String(e);ui.error.hidden=false;}}
  finally{
   disposeGPU(own);report.execution={prepareCompleted:Object.values(report.trials).reduce((n,t)=>n+Object.values(t.cpu).filter(c=>c.state==='completed').length,0),freshCompleted:report.trials.reduce((n,t)=>n+Object.values(t.draw).filter(d=>d.fresh.state==='completed').length,0),cacheCompleted:report.trials.reduce((n,t)=>n+Object.values(t.draw).filter(d=>d.cache.state==='completed').length,0),newUploads:own.freshCount};report.execution.drawCompleted=report.execution.freshCompleted+report.execution.cacheCompleted;try{setup.verifySourceUnchanged();report.verified.sourceUnchanged=true;report.verified.inputUnchanged=inputBefore!==null&&encodeDerivedGPUExact({input:item.input,settings:item.settings}).text===inputBefore;}catch(e){report.status='failed';report.error=errorView(e);}if(report.disposeErrors.length){report.status='disposal_failure';report.error=report.disposeErrors[0];}report.visibilityAtFinish=doc.visibilityState??'unknown';report.summary=summarize(report.trials);report.clockError=errorView(time.error);
   if(report.disposal?.delta&&own.freshCount>0&&report.gpu.status==='completed'&&report.disposal.delta.destroyedMeshBuffers!==1){report.status='failed';report.error={name:'Error',message:'最後のmesh bufferの破棄数が一致しません',code:null};}
   if(active===own){running=false;active=null;displayReport(report);ui.status.textContent=report.status==='completed'?'有限計測を完了し、GPU資源を解放しました。':report.status==='timing_invalid'?'実行結果を保持しました。時計が無効な時間は集計していません。':report.status==='cancelled'?'計測を中止し、途中の記録を保持しました。':'記録を保持しました。数値・GPUの状態を個別に確認してください。';ui.canvas.hidden=true;buttons();}
  }
  return report;
 }
 async function retry(){
  if(loading||running)return false;loading=true;cancel('runtime reload');lastReport=null;ui.report.textContent='未実行';ui.error.hidden=true;ui.status.textContent='計算核と原本を準備中…';buttons();const requestEpoch=epoch,time=clock(now),start=time.start();const fresh=()=>check(epoch===requestEpoch,'古い読込みは中止されました');
  try{const loaded=await loadRuntime();fresh();runtime=loaded;const elapsedMs=time.end(start);setup=createCases(runtime,{now:()=>time.safe()});check(setup.cases.length===3&&setup.cases.map(c=>c.input.triangles.length).sort((a,b)=>a-b).join(',')==='4,64,512'&&setup.cases.every(c=>c.input.positions.length<=2048),'有限な3例が必要です');check(setup.sourcePreparation.authorSourceBefore===setup.sourcePreparation.authorSourceAfter,'原本が変更されています');setup.verifySourceUnchanged();
   startup={runtimeStartupMs:elapsedMs,clockError:errorView(time.error)};const timingErrors=[];for(const key of ['sourceSetupMs','sourceEvaluationMs']){const value=setup.sourcePreparation[key];if(time.error||!Number.isFinite(value)||value<0){timingErrors.push({field:key,reason:time.error?.message??'時間が有限の非負値ではありません'});setup.sourcePreparation[key]=null;}}setup.sourcePreparation.timingErrors=timingErrors;
   manifestInfo=await loadManifest();fresh();ui.case.replaceChildren();for(const item of setup.cases){const option=doc.createElement('option');option.value=item.name;option.textContent=item.input.triangles.length+'面 / '+({'actual-source-4':'帯の原本','rational-normal-64':'斜めの法線','sheared-grid-512':'曲面の格子'}[item.name]??item.name);ui.case.appendChild(option);}ui.case.value=setup.cases[0].name;ui.author.textContent=setup.sourcePreparation.authorSourceBefore;ui.runtime.textContent=signedJSON({runtime:runtime.diagnostics??{},startup,manifest:manifestInfo});ui.status.textContent='例を選び、計測ボタンで開始してください。';ui.cpu.textContent='C++の数値照会は実行ボタンで行います。';return true;
  }catch(e){runtime=null;setup=null;if(epoch!==requestEpoch)return false;ui.error.textContent=e?.message??String(e);ui.error.hidden=false;ui.status.textContent='計算核を準備できません。再読込できます。';return false;}
  finally{loading=false;buttons();}
 }
 ui.run.addEventListener('click',run);ui.retry.addEventListener('click',retry);ui.case.addEventListener('change',()=>{cancel('case changed');if(!running){ui.rows.replaceChildren();ui.summary.replaceChildren();lastReport=null;ui.report.textContent='条件が変わりました。計測ボタンで実行してください。';ui.status.textContent='選んだ例はまだ計測していません。';}buttons();});
 ui.export.addEventListener('click',()=>{if(lastReport&&!running)save('pikapika-derived-gpu-profile.json',signedJSON(lastReport),'application/json');});ui.source.addEventListener('click',()=>{if(setup)save('pikapika-derived-profile-source.json',setup.sourcePreparation.authorSourceBefore,'application/json');});
 doc.addEventListener?.('visibilitychange',()=>{if(active){active.report.visibilityChanges.push(doc.visibilityState??'unknown');if(doc.visibilityState==='hidden')cancel('document hidden');}});doc.defaultView?.addEventListener?.('pagehide',()=>cancel('pagehide'));
 await retry();return {run,retry,dispose:()=>cancel('disposed'),getState:()=>({running,loading,available:Boolean(runtime&&setup),report:lastReport?structuredClone(lastReport):null,source:setup?.sourcePreparation.authorSourceBefore??null})};
}
if(typeof document!=='undefined'&&document.getElementById('dg-run'))initializeDerivedGPULab();
