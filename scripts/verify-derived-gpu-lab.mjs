import assert from 'node:assert/strict';
import {readFile,mkdir,mkdtemp,writeFile,lstat,realpath} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson} from '../engine/strict-json.mjs';
import {createDerivedGPUProfileCases} from '../tools/derived-gpu-cases.mjs';
import {encodeDerivedGPUExact} from '../tools/derived-gpu-lab.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const phases=['initial','warmup','measure','measure','measure'],kinds=['baseline','instrumented'];
const cpuStages=['f64Exchange','u32Exchange','cppQuery','cppGetter','outputCopy'],gpuStages=['syncRender','validationWait','queueWait'];
const caseNames=['actual-source-4','rational-normal-64','sheared-grid-512'];
const sha=value=>createHash('sha256').update(value).digest('hex');
const has=(value,key)=>Object.hasOwn(value,key);
const number=value=>assert.ok(Number.isFinite(value)&&value>=0,'Expected finite nonnegative value');
const integer=value=>assert.ok(Number.isSafeInteger(value)&&value>=0,'Expected nonnegative safe integer');
function keys(value,expected){assert.ok(value&&typeof value==='object'&&!Array.isArray(value));assert.deepEqual(Object.keys(value).sort(),[...expected].sort(),'Unexpected or missing object fields');}
function dense(value,length){assert.ok(Array.isArray(value));assert.equal(value.length,length);for(let j=0;j<length;++j)assert.ok(has(value,j),'Sparse array');}
function finiteTree(value){
 if(typeof value==='number'){assert.ok(Number.isFinite(value),'Nonfinite report value');return;}
 if(value===null||typeof value==='string'||typeof value==='boolean')return;
 assert.ok(value&&typeof value==='object','Unsupported report value');
 if(Array.isArray(value)){dense(value,value.length);for(const x of value)finiteTree(x);}
 else for(const x of Object.values(value))finiteTree(x);
}
export function parseDerivedBrowserReport(bytes){
 assert.ok(bytes instanceof Uint8Array);assert.ok(bytes.byteLength>0&&bytes.byteLength<16*1024*1024,'Browser report byte budget');
 return parseStrictJson(new TextDecoder('utf-8',{fatal:true}).decode(bytes),{maxBytes:16*1024*1024,maxDepth:64,maxNodes:2000000});
}
function timing(value,names=null,calls=null){
 assert.ok(value&&typeof value==='object');number(value.elapsedMs);
 if(names){keys(value.stages,names);let sum=0;for(const name of names){const stage=value.stages[name];keys(stage,['calls','elapsedMs']);integer(stage.calls);number(stage.elapsedMs);assert.equal(stage.calls,calls[name],'Stage call count');sum+=stage.elapsedMs;}
  assert.ok(Number.isFinite(sum)&&sum<=value.elapsedMs);number(value.unassignedMs);assert.equal(value.unassignedMs,value.elapsedMs-sum,'Direct exclusive timing residual');}
}
function statistics(values){assert.ok(values.length);for(const value of values)number(value);const s=[...values].sort((a,b)=>a-b),n=s.length;return {samples:n,medianMs:n%2?s[Math.floor(n/2)]:s[n/2-1]/2+s[n/2]/2,p95Ms:s[Math.ceil(.95*n)-1],maxMs:s[n-1]};}
const statKeys=['uploadedMeshBytes','destroyedMeshBuffers','drawCalls','triangles'];
function stats(value){keys(value,statKeys);for(const key of statKeys)integer(value[key]);}
function difference(before,after){return Object.fromEntries(statKeys.map(key=>[key,after[key]-before[key]]));}
function summaryRows(){
 const rows=[];for(const phase of ['initial','warmup','measure'])for(const kind of kinds){
  for(const stage of ['elapsedMs',...(kind==='instrumented'?[...cpuStages,'unassignedMs']:[])])rows.push({phase,kind,group:'cpu',stage});
  rows.push({phase,kind,group:'factory',stage:'elapsedMs'});
  for(const group of ['fresh','cache'])for(const stage of ['elapsedMs',...(kind==='instrumented'?[...gpuStages,'unassignedMs']:[])])rows.push({phase,kind,group,stage});
 }return rows;
}
function auditSummary(report){
 const expected=summaryRows();dense(report.summary,expected.length);const seen=new Set();
 for(const row of report.summary){keys(row,['phase','kind','group','stage','expected','valid','unavailable','statistics']);const tag=JSON.stringify([row.phase,row.kind,row.group,row.stage]);assert.ok(!seen.has(tag),'Duplicate summary row');seen.add(tag);
  assert.ok(expected.some(x=>x.phase===row.phase&&x.kind===row.kind&&x.group===row.group&&x.stage===row.stage),'Unknown summary row');
  const selected=report.trials.filter(t=>t.phase===row.phase),values=selected.map(t=>{if(row.group==='factory')return t.draw[row.kind].factory.elapsedMs;const record=row.group==='cpu'?t.cpu[row.kind]:t.draw[row.kind][row.group];assert.equal(record.state,'completed');assert.equal(record.error,null);assert.equal(record.clockError,null);return row.stage==='elapsedMs'?record.timing.elapsedMs:row.stage==='unassignedMs'?record.timing.unassignedMs:record.timing.stages[row.stage].elapsedMs;});
  assert.equal(row.expected,row.phase==='measure'?3:1);assert.equal(row.valid,row.expected);assert.equal(row.unavailable,0);keys(row.statistics,['samples','medianMs','p95Ms','maxMs']);assert.deepEqual(row.statistics,statistics(values));
 }
 assert.equal(seen.size,expected.length);
}
function exactEqual(a,b,message){assert.equal(encodeDerivedGPUExact(a).text,encodeDerivedGPUExact(b).text,message);}
function validString(value){assert.ok(typeof value==='string'&&value.length>0&&value.length<=1024&&!/[\x00-\x1f\x7f]/.test(value));}
function gpuMetadataForComparison(value){
 assert.ok(value&&typeof value==='object'&&!Array.isArray(value));const copy={...value};
 // GPUSupportedFeatures enumeration order is not a cohort distinction. Only
 // these two string sets are canonicalized; raw reports remain untouched and
 // status/reason/all other GPU metadata still compare exactly.
 for(const name of ['adapterFeaturesAvailable','deviceFeaturesEnabled']){
  const feature=value[name];keys(feature,['status','values',...(feature&&has(feature,'reason')?['reason']:[])]);
  assert.ok(feature.status==='obtained'||feature.status==='unknown','Invalid feature retrieval status');
  assert.ok(Array.isArray(feature.values));dense(feature.values,feature.values.length);for(const item of feature.values)validString(item);
  assert.equal(new Set(feature.values).size,feature.values.length,'Duplicate GPU feature');
  if(feature.status==='unknown')assert.equal(feature.values.length,0,'Unknown features cannot carry obtained values');
  if(has(feature,'reason'))validString(feature.reason);
  copy[name]={...feature,values:[...feature.values].sort()};
 }
 return copy;
}
function schema2Cohort(reports,manifest){
 assert.ok(manifest&&typeof manifest==='object','Current audited manifest required');
 const first=reports[0],seenPairs=new Set(),ordinals=new Set();validString(first.sessionId);
 const settingsWithoutMode=report=>Object.fromEntries(Object.entries(report.settings).filter(([key])=>key!=='readback'));
 const environment=first.environment,gpuMetadata=gpuMetadataForComparison(first.gpu.environment);
 validString(environment.userAgent);assert.notEqual(environment.userAgent,'unknown');validString(environment.platform);assert.notEqual(environment.platform,'unknown');assert.match(environment.buildMarker,/^[0-9a-f]{16}$/);
 for(const name of ['width','height']){integer(environment.viewport[name]);assert.ok(environment.viewport[name]>0);}number(environment.dpr);assert.ok(environment.dpr>0);
 for(const name of ['width','height','cssWidth','cssHeight']){number(environment.canvas[name]);assert.ok(environment.canvas[name]>0);}
 for(const report of reports){
  assert.equal(report.kind,'derived-mesh-browser-profile');assert.equal(report.trialSchema,2);assert.equal(report.summarySchema,1);assert.ok(['single','batch'].includes(report.readback));assert.equal(report.settings.readback,report.readback);
  validString(report.sessionId);assert.equal(report.sessionId,first.sessionId);integer(report.runtimeGeneration);assert.ok(report.runtimeGeneration>0);assert.equal(report.runtimeGeneration,first.runtimeGeneration);integer(report.runOrdinal);assert.ok(report.runOrdinal>0);assert.ok(!ordinals.has(report.runOrdinal),'Duplicate run ordinal');ordinals.add(report.runOrdinal);
  const pair=report.caseName+'/'+report.readback;assert.ok(!seenPairs.has(pair),'Duplicate case/transport');seenPairs.add(pair);
  assert.equal(report.manifest.status,'obtained');assert.deepEqual(report.manifest.data,manifest,'Browser SDK manifest differs from current audited SDK');
  assert.equal(report.runtime.apiVersion,1);assert.equal(report.runtime.wasmBytes,manifest.artifacts['assets/pikapika-simulation.wasm'].bytes);assert.equal(report.runtime.compiler,manifest.compiler);assert.equal(report.runtime.backend,'C++ WebAssembly');assert.equal(report.runtime.buildId,environment.buildMarker);
  assert.deepEqual(report.runtime,first.runtime,'Runtime diagnostics changed within cohort');
  assert.deepEqual(report.environment,environment,'Browser cohort environment/viewport/canvas changed');assert.deepEqual(gpuMetadataForComparison(report.gpu.environment),gpuMetadata,'GPU metadata changed within cohort');assert.deepEqual(report.projection,first.projection);
  const moduleURL=new URL(report.environment.moduleURL);assert.ok(['http:','https:'].includes(moduleURL.protocol));assert.equal(moduleURL.searchParams.get('build'),environment.buildMarker);assert.ok(moduleURL.pathname.endsWith('/tools/derived-gpu-lab.mjs'));assert.ok(['http:','https:'].includes(new URL(report.environment.url).protocol));
  const manifestURL=new URL(report.manifest.url);assert.equal(manifestURL.origin,moduleURL.origin);assert.equal(manifestURL.searchParams.get('build'),environment.buildMarker);assert.ok(manifestURL.pathname.endsWith('/assets/pikapika-simulation.build.json'));
 }
 for(const name of caseNames){const single=reports.find(r=>r.caseName===name&&r.readback==='single'),batch=reports.find(r=>r.caseName===name&&r.readback==='batch');assert.ok(single&&batch,'Missing case/transport');exactEqual(single.input,batch.input);exactEqual(settingsWithoutMode(single),settingsWithoutMode(batch));assert.equal(single.sourcePreparation.authorSourceBefore,batch.sourcePreparation.authorSourceBefore);assert.deepEqual(single.camera,batch.camera);assert.deepEqual(single.model,batch.model);assert.deepEqual(single.firstPair,batch.firstPair,'Cross-transport full encoded DTO differs');}
 const order=[...reports].sort((a,b)=>a.runOrdinal-b.runOrdinal).map(r=>({runOrdinal:r.runOrdinal,caseName:r.caseName,readback:r.readback}));
 return {sessionId:first.sessionId,runtimeGeneration:first.runtimeGeneration,recordedOrder:order,ordinalGaps:order.slice(1).flatMap((r,j)=>r.runOrdinal>order[j].runOrdinal+1?[{after:order[j].runOrdinal,before:r.runOrdinal}]:[]),scope:'Same recorded browser/runtime/build/viewport/GPU metadata; not hardware identity or clock authenticity proof. Ordinal gaps can include separately retained failures/cancellations.'};
}

// Pure audit entry. replay must execute the requested transport; it must not
// substitute a Native or single result for batch. Tests may explicitly label a
// cache of six actual-WASM captures; CLI always uses live actual Node queries.
export function verifyDerivedBrowserReports(reports,{cases,authorSource,manifest,replay,replayKind='actual-node-wasm'}={}){
 assert.ok(typeof replay==='function');dense(reports,reports.length);assert.ok([4,6].includes(reports.length));
 for(const report of reports)finiteTree(report);
 const schema=reports[0].schema;assert.ok(schema===1||schema===2,'Unknown browser schema');assert.ok(reports.every(r=>r.schema===schema),'Mixed browser schemas');assert.equal(reports.length,schema===1?4:6,'Schema/CLI branch count');
 const cohort=schema===2?schema2Cohort(reports,manifest):null,records=[];let numericComparisons=0,draws=0,uploads=0,replayQueries=0;
 const oldNames=[...caseNames,'actual-source-4'];
 for(const [fileIndex,r]of reports.entries()){
  const item=cases.find(c=>c.name===r.caseName);assert.ok(item,'Unknown case');const mode=schema===2?r.readback:'single';if(schema===1){assert.equal(r.caseName,oldNames[fileIndex]);assert.ok(!has(r,'readback')&&!has(r.settings,'readback'),'Historical schema1 cannot declare a new transport');}
  assert.equal(r.status,'completed');assert.ok(!has(r,'error')||r.error===null);assert.ok(!has(r,'timingInvalid')||r.timingInvalid===false);assert.equal(r.gpu.status,'completed');assert.deepEqual(r.gpu.events,[]);dense(r.trials,5);
  exactEqual(r.input,item.input,'Case input changed');exactEqual(r.settings,schema===2?{...item.settings,readback:mode}:item.settings,'Case settings changed');
  assert.deepEqual(r.camera,r.caseName==='rational-normal-64'?{eye:[4,2,9],target:[4,.1,0]}:{eye:[3,2,4],target:[1,.35,0]});assert.deepEqual(r.model,{position:[0,0,0],scale:[1,1,1],yaw:0});assert.deepEqual(r.projection,{fovDegrees:60,nearMetres:.2,farMetres:1600});
  const source=r.sourcePreparation;assert.equal(source.authorSourceBefore,authorSource);assert.equal(source.authorSourceAfter,authorSource);assert.equal(source.sourceUnchanged,true);assert.equal(source.deformationStatus,'completed');assert.equal(source.sampleSeconds,1);assert.equal(source.loop,false);assert.deepEqual(source.timingErrors,[]);number(source.sourceSetupMs);number(source.sourceEvaluationMs);assert.ok(!has(source,'clockError')||source.clockError===null);
  assert.equal(r.environment.visibilityAtStart,'visible');assert.equal(r.visibilityAtFinish,'visible');assert.deepEqual(r.visibilityChanges,[]);assert.deepEqual(r.disposeErrors,[]);assert.equal(r.clockError,null);assert.equal(r.cancellation,null);assert.equal(r.startup.clockError,null);number(r.startup.runtimeStartupMs);assert.equal(r.gpu.initialization.clockError,null);for(const key of ['totalMs','rendererCreateMs','initialQueueWaitMs'])number(r.gpu.initialization[key]);
  assert.deepEqual(r.planned,{pairs:5,prepareQueries:10,newUploads:10,cacheDraws:10,drawCalls:20});assert.deepEqual(r.execution,{prepareCompleted:10,freshCompleted:10,cacheCompleted:10,newUploads:10,drawCompleted:20});assert.equal(r.verified.fullDTOEqualPairs,5);assert.equal(r.verified.inputUnchanged,true);assert.equal(r.verified.sourceUnchanged,true);
  const actual=replay(item.input,{...item.settings,readback:mode});++replayQueries;assert.equal(actual.status,'completed');const exact=encodeDerivedGPUExact(actual),hash=sha(exact.text);keys(r.firstPair,['encoding','baseline','instrumented']);assert.equal(r.firstPair.encoding,'tagged-exact-v1');assert.deepEqual(r.firstPair.baseline,exact.encoded);assert.deepEqual(r.firstPair.instrumented,exact.encoded);
  const comparisons=5*(exact.counts.numbers+exact.counts.typedElements);assert.equal(r.verified.comparedNumericValues,comparisons);numericComparisons+=comparisons;
  const n=item.input.positions.length,t=item.input.triangles.length,expectedRecords=[n,t,t,t],expectedCalls=mode==='single'?expectedRecords:[Math.ceil(n/20),Math.ceil(t/20),Math.ceil(t/3),Math.ceil(t/2)],getterCalls=expectedCalls.reduce((a,b)=>a+b,0);let fresh=0,previousStats={uploadedMeshBytes:0,destroyedMeshBuffers:0,drawCalls:0,triangles:0},recordedRecords=0;
  for(let pair=0;pair<5;++pair){const trial=r.trials[pair];keys(trial,['pair','phase','order','cpu','draw']);assert.equal(trial.pair,pair);assert.equal(trial.phase,phases[pair]);assert.deepEqual(trial.order,pair%2?[...kinds].reverse():kinds);keys(trial.cpu,kinds);keys(trial.draw,kinds);
   for(const kind of trial.order){const cpu=trial.cpu[kind];keys(cpu,['state','modelStatus','timing','error','clockError','digest','comparedCounts']);assert.equal(cpu.state,'completed');assert.equal(cpu.modelStatus,'completed');assert.equal(cpu.error,null);assert.equal(cpu.clockError,null);keys(cpu.digest,['status','sha256','reason']);assert.equal(cpu.digest.status,'obtained');assert.equal(cpu.digest.reason,null);assert.equal(cpu.digest.sha256,hash);assert.deepEqual(cpu.comparedCounts,exact.counts);timing(cpu.timing);
    keys(cpu.timing,kind==='baseline'?['elapsedMs']:['elapsedMs','stages','getterKinds',...(has(cpu.timing,'getterRecords')?['getterRecords']:[]),'unassignedMs']);
    if(kind==='instrumented'){const x=cpu.timing;dense(x.getterKinds,4);for(let j=0;j<4;++j)assert.equal(x.getterKinds[j],expectedCalls[j]);
     if(schema===2||has(x,'getterRecords')){dense(x.getterRecords,4);for(let j=0;j<4;++j)assert.equal(x.getterRecords[j],expectedRecords[j]);++recordedRecords;}
     timing(x,cpuStages,{f64Exchange:1,u32Exchange:1,cppQuery:1,cppGetter:getterCalls,outputCopy:1+getterCalls});
    }
    const draw=trial.draw[kind];keys(draw,['factory','fresh','cache']);keys(draw.factory,['elapsedMs','clockError','metadata']);number(draw.factory.elapsedMs);assert.equal(draw.factory.clockError,null);assert.deepEqual(draw.factory.metadata,{vertexCount:n,triangleCount:t,floatCount:18*t});
    for(const update of ['fresh','cache']){const v=draw[update];keys(v,['state','timing','error','clockError','before','after','delta',...(has(v,'checkedResolved')?['checkedResolved']:[])]);assert.equal(v.state,'completed');assert.ok(!has(v,'checkedResolved')||v.checkedResolved===true);assert.equal(v.error,null);assert.equal(v.clockError,null);keys(v.timing,kind==='baseline'?['elapsedMs']:['elapsedMs','stages','unassignedMs']);timing(v.timing,kind==='instrumented'?gpuStages:null,kind==='instrumented'?{syncRender:1,validationWait:1,queueWait:1}:null);
     stats(v.before);stats(v.after);assert.deepEqual(v.before,previousStats,'GPU stats discontinuity');assert.deepEqual(v.delta,difference(v.before,v.after));assert.equal(v.after.drawCalls,1);assert.equal(v.after.triangles,t);assert.equal(v.delta.uploadedMeshBytes,update==='fresh'?72*t:0);assert.equal(v.delta.destroyedMeshBuffers,update==='fresh'&&fresh>0?1:0);if(update==='fresh')++fresh;++draws;previousStats=v.after;
    }
   }
  }
  assert.equal(fresh,10);uploads+=fresh;assert.equal(r.disposal.ownedDevice,true);assert.equal(r.disposal.deviceDestroyRequested,true);stats(r.disposal.before);stats(r.disposal.after);assert.deepEqual(r.disposal.before,previousStats);assert.deepEqual(r.disposal.delta,difference(r.disposal.before,r.disposal.after));assert.equal(r.disposal.before.uploadedMeshBytes,720*t);assert.equal(r.disposal.before.destroyedMeshBuffers,9);assert.deepEqual(r.disposal.after,{...r.disposal.before,destroyedMeshBuffers:10,drawCalls:0,triangles:0});auditSummary(r);
  records.push({caseName:r.caseName,readback:mode,transportClassification:schema===1?'historical implicit single':'explicit schema2 transport',runOrdinal:schema===2?r.runOrdinal:null,faces:t,numericComparisons:comparisons,exactResultSHA256:hash,execution:r.execution,getterCallsExpected:expectedCalls,recordCountsExpectedFromInput:expectedRecords,getterRecordsTelemetry:{presentTrials:recordedRecords,absentTrials:5-recordedRecords,note:recordedRecords===0?'Absent in original schema1; expected counts are theoretical, not fabricated measurements.':'Requested records as recorded; not success counters.'},summary:r.summary.filter(row=>row.phase==='measure'),recordedSDK:r.manifest?.data?.artifacts??null});
 }
 return {status:'PASS',schema,browserReports:reports.length,classification:schema===1?'historical numerical compatibility; not a same-SDK performance cohort':'recorded same-SDK browser transport cohort',cohort,numericComparisons,draws,newUploads:uploads,cacheDraws:draws-uploads,nodeReplay:{kind:replayKind,queries:replayQueries,scope:'Separate replay queries, never added to recorded browser prepare counts; each requested mode supplied independently.'},records};
}

export async function verifyDerivedBrowserFiles(files){
 assert.ok(Array.isArray(files)&&[4,6].includes(files.length),'Supply 4 schema1 raw files or 6 schema2 raw files');assert.equal(new Set(files.map(f=>path.resolve(f))).size,files.length,'Duplicate input path');
 const base=path.join(ROOT,'build/derived-gpu-verification');await mkdir(base,{recursive:true});assert.equal((await lstat(base)).isSymbolicLink(),false);assert.equal(await realpath(base),path.resolve(base));const run=await mkdtemp(path.join(base,'run-'));
 const command=[process.execPath,...process.execArgv,fileURLToPath(import.meta.url),...files];await writeFile(path.join(run,'command.json'),JSON.stringify({command,cwd:process.cwd()},null,2)+'\n',{flag:'wx'});
 try{
  const raw=await Promise.all(files.map(f=>readFile(f))),reports=raw.map(parseDerivedBrowserReport),manifest=parseStrictJson(await readFile(path.join(ROOT,'assets/pikapika-simulation.build.json'),'utf8'),{maxDepth:64});
  const wasm=await readFile(path.join(ROOT,'assets/pikapika-simulation.wasm')),sdkAudit={};
  if(reports.some(r=>r.schema===2)){for(const [name,expected]of Object.entries({...manifest.sourceSha256,...manifest.licenses})){const data=await readFile(path.join(ROOT,name));assert.equal(sha(data),expected,name);sdkAudit[name]={bytes:data.length,sha256:expected};}
   for(const [name,expected]of Object.entries(manifest.artifacts)){const data=await readFile(path.join(ROOT,name));assert.deepEqual({bytes:data.length,sha256:sha(data)},expected,name);sdkAudit[name]=expected;}
   assert.equal(Object.keys(manifest.sourceSha256).length,53);assert.equal(Object.keys(manifest.licenses).length,7);assert.equal(Object.keys(manifest.artifacts).length,2);
  }
  const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(wasm)}),setup=createDerivedGPUProfileCases(runtime),result=verifyDerivedBrowserReports(reports,{cases:setup.cases,authorSource:setup.sourcePreparation.authorSourceBefore,manifest,replay:(input,settings)=>runtime.prepareDerivedMesh(input,settings)});setup.verifySourceUnchanged();
  for(let j=0;j<files.length;++j)Object.assign(result.records[j],{path:files[j],bytes:raw[j].length,sha256:sha(raw[j])});
  const sourceHashes={};for(const name of ['scripts/verify-derived-gpu-lab.mjs','tools/derived-gpu-lab.mjs','tools/derived-gpu-profile.mjs','tools/derived-gpu-cases.mjs','engine/simulation.mjs','engine/renderer.mjs','engine/derived-render.mjs'])sourceHashes[name]=sha(await readFile(path.join(ROOT,name)));
  Object.assign(result,{wasm:{bytes:wasm.length,sha256:sha(wasm)},sdkAudit,sourceHashes,scope:'All recorded successful timings/statistics/counters checked; exact browser DTOs compared with actual Node WASM. No GPU readback, hardware identity, timing authenticity, GPU timestamp or display proof.',command,runDirectory:run});
  await writeFile(path.join(run,'verification.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});return result;
 }catch(error){await writeFile(path.join(run,'failure.json'),JSON.stringify({status:'FAIL',error:{name:error.name,message:error.message},command},null,2)+'\n',{flag:'wx'});throw error;}
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
 try{const result=await verifyDerivedBrowserFiles(process.argv.slice(2));console.log(JSON.stringify({status:result.status,schema:result.schema,browserReports:result.browserReports,numericComparisons:result.numericComparisons,draws:result.draws,newUploads:result.newUploads,runDirectory:result.runDirectory},null,2));}
 catch(error){console.error(error.message);process.exitCode=1;}
}
