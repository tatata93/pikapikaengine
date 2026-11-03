import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createDerivedGPUProfileCases} from '../tools/derived-gpu-cases.mjs';
import {encodeDerivedGPUExact} from '../tools/derived-gpu-lab.mjs';
import {verifyDerivedBrowserReports,verifyDerivedBrowserFiles,parseDerivedBrowserReport} from '../scripts/verify-derived-gpu-lab.mjs';

const sha=x=>createHash('sha256').update(x).digest('hex');
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const manifest=JSON.parse(await readFile(new URL('../assets/pikapika-simulation.build.json',import.meta.url),'utf8'));
const setup=createDerivedGPUProfileCases(runtime),captures=new Map();let captureQueries=0;
// Six actual C++ queries only, not sixty measured prepares. Every repeated trial
// below is explicitly synthetic telemetry, never evidence of browser speed/GPU.
for(const c of setup.cases)for(const readback of ['single','batch']){captures.set(c.name+'/'+readback,runtime.prepareDerivedMesh(c.input,{...c.settings,readback}));++captureQueries;}
const rawPaths=['derived-gpu-public-4.json','derived-gpu-public-64.json','derived-gpu-public-512.json','derived-gpu-public-retry-4.json'];
const rawBytes=await Promise.all(rawPaths.map(name=>readFile(new URL('../reports/'+name,import.meta.url))));
const historical=rawBytes.map(parseDerivedBrowserReport),rawHashes=rawBytes.map(sha);
const context={cases:setup.cases,authorSource:setup.sourcePreparation.authorSourceBefore,manifest,replayKind:'cached six actual Node WASM captures; synthetic telemetry test only',replay:(input,{readback})=>{
 const item=setup.cases.find(c=>encodeDerivedGPUExact(c.input).text===encodeDerivedGPUExact(input).text);assert.ok(item);return captures.get(item.name+'/'+readback);
}};
const cpuNames=['f64Exchange','u32Exchange','cppQuery','cppGetter','outputCopy'],gpuNames=['syncRender','validationWait','queueWait'];
function time(stages,calls){const out=Object.fromEntries(stages.map(name=>[name,{calls:calls[name],elapsedMs:calls[name]/1024}])),sum=Object.values(out).reduce((n,x)=>n+x.elapsedMs,0);return {elapsedMs:sum+1,stages:out,unassignedMs:1};}
const statistics=values=>{const s=[...values].sort((a,b)=>a-b),n=s.length;return {samples:n,medianMs:s[Math.floor(n/2)],p95Ms:s[Math.ceil(.95*n)-1],maxMs:s.at(-1)};};
function regenerateSummary(r){
 r.summary=[];for(const phase of ['initial','warmup','measure'])for(const kind of ['baseline','instrumented']){
  const selected=r.trials.filter(t=>t.phase===phase),add=(group,stage,get)=>r.summary.push({phase,kind,group,stage,expected:selected.length,valid:selected.length,unavailable:0,statistics:statistics(selected.map(get))});
  for(const stage of ['elapsedMs',...(kind==='instrumented'?[...cpuNames,'unassignedMs']:[])])add('cpu',stage,t=>stage==='elapsedMs'?t.cpu[kind].timing.elapsedMs:stage==='unassignedMs'?t.cpu[kind].timing.unassignedMs:t.cpu[kind].timing.stages[stage].elapsedMs);
  add('factory','elapsedMs',t=>t.draw[kind].factory.elapsedMs);
  for(const mode of ['fresh','cache'])for(const stage of ['elapsedMs',...(kind==='instrumented'?[...gpuNames,'unassignedMs']:[])])add(mode,stage,t=>stage==='elapsedMs'?t.draw[kind][mode].timing.elapsedMs:stage==='unassignedMs'?t.draw[kind][mode].timing.unassignedMs:t.draw[kind][mode].timing.stages[stage].elapsedMs);
 }
}
function makeSchema2(){
 const records=[],marker='0123456789abcdef';let ordinal=0;
 for(const [c,item]of setup.cases.entries())for(const readback of c%2?['batch','single']:['single','batch']){
  const r=structuredClone(historical[c]),actual=captures.get(item.name+'/'+readback),encoded=encodeDerivedGPUExact(actual),digest=sha(encoded.text),n=item.input.positions.length,t=item.input.triangles.length,counts=[n,t,t,t],calls=readback==='single'?counts:[Math.ceil(n/20),Math.ceil(t/20),Math.ceil(t/3),Math.ceil(t/2)],total=calls.reduce((a,b)=>a+b,0);
  Object.assign(r,{schema:2,kind:'derived-mesh-browser-profile',trialSchema:2,summarySchema:1,readback,sessionId:'synthetic-test-session',runtimeGeneration:1,runOrdinal:++ordinal,evidenceLabel:'Synthetic legal timings/GPU counters; exactly six actual C++ captures, not browser performance.'});
  r.settings={...item.settings,readback};r.input=structuredClone(item.input);r.manifest={status:'obtained',url:'https://example.test/assets/pikapika-simulation.build.json?build='+marker,data:structuredClone(manifest)};
  r.runtime={...r.runtime,wasmBytes:manifest.artifacts['assets/pikapika-simulation.wasm'].bytes,compiler:manifest.compiler,buildId:marker};r.environment={...r.environment,url:'https://example.test/tools/derived-gpu-lab.html',moduleURL:'https://example.test/tools/derived-gpu-lab.mjs?build='+marker,buildMarker:marker};
  r.firstPair={encoding:'tagged-exact-v1',baseline:structuredClone(encoded.encoded),instrumented:structuredClone(encoded.encoded)};r.verified.comparedNumericValues=5*(encoded.counts.numbers+encoded.counts.typedElements);
  for(const trial of r.trials)for(const kind of ['baseline','instrumented']){
   const cpu=trial.cpu[kind];cpu.digest={status:'obtained',sha256:digest,reason:null};cpu.comparedCounts=structuredClone(encoded.counts);
   cpu.timing=kind==='baseline'?{elapsedMs:1}:time(cpuNames,{f64Exchange:1,u32Exchange:1,cppQuery:1,cppGetter:total,outputCopy:1+total});
   if(kind==='instrumented')Object.assign(cpu.timing,{getterKinds:[...calls],getterRecords:[...counts]});
   trial.draw[kind].factory.elapsedMs=.125;
   for(const mode of ['fresh','cache'])trial.draw[kind][mode].timing=kind==='baseline'?{elapsedMs:2}:time(gpuNames,{syncRender:1,validationWait:1,queueWait:1});
  }
  regenerateSummary(r);records.push(r);
 }
 return records;
}
const current=makeSchema2();
function changed(edit,index=0){const records=current.slice();records[index]=structuredClone(current[index]);edit(records[index],records);return records;}
const audit=records=>verifyDerivedBrowserReports(records,context);

test('schema2 six records audit all actual per-mode captures and synthetic telemetry without measuring sixty queries',()=>{
 assert.equal(captureQueries,6);const before=current.map(r=>encodeDerivedGPUExact(r).text),result=audit(current);
 assert.equal(result.status,'PASS');assert.equal(result.schema,2);assert.equal(result.browserReports,6);assert.equal(result.draws,120);assert.equal(result.newUploads,60);assert.equal(result.cacheDraws,60);assert.equal(result.nodeReplay.queries,6);assert.match(result.nodeReplay.kind,/cached/);
 assert.deepEqual(result.cohort.recordedOrder.map(r=>r.runOrdinal),[1,2,3,4,5,6]);assert.deepEqual(result.cohort.ordinalGaps,[]);
 for(const r of result.records){assert.equal(r.getterRecordsTelemetry.presentTrials,5);assert.equal(r.getterRecordsTelemetry.absentTrials,0);assert.equal(r.summary.length,22);}
 assert.deepEqual(current.map(r=>encodeDerivedGPUExact(r).text),before);setup.verifySourceUnchanged();
});
test('schema2 accepts file order independent of ordinal and exposes allowed ordinal gaps',()=>{
 const records=current.map((r,j)=>({...r,runOrdinal:2*j+10})).reverse(),result=audit(records);assert.deepEqual(result.cohort.recordedOrder.map(x=>x.runOrdinal),[10,12,14,16,18,20]);assert.equal(result.cohort.ordinalGaps.length,5);
});
test('GPU feature sets ignore only enumeration order and retain strict status membership and other metadata',()=>{
 const records=current.map(r=>({...r,gpu:{...r.gpu,environment:structuredClone(r.gpu.environment)}}));
 // The actual device recorded one enabled feature. Add a clearly synthetic
 // two-member set only for the order-comparison test, never as hardware proof.
 for(const r of records)r.gpu.environment.deviceFeaturesEnabled.values=['synthetic-device-a','synthetic-device-b'];
 records[1].gpu.environment.adapterFeaturesAvailable.values.reverse();records[1].gpu.environment.deviceFeaturesEnabled.values.reverse();
 const before=records.map(r=>encodeDerivedGPUExact(r.gpu.environment).text);assert.equal(audit(records).status,'PASS');assert.deepEqual(records.map(r=>encodeDerivedGPUExact(r.gpu.environment).text),before);
 for(const name of ['adapterFeaturesAvailable','deviceFeaturesEnabled'])for(const edit of [
  feature=>feature.values.pop(),feature=>feature.values.push(feature.values[0]),feature=>feature.values[0]=null,feature=>feature.values[0]=1,feature=>feature.values[0]={name:'wrong'},feature=>feature.values=Array(feature.values.length),
  feature=>feature.status='unknown',feature=>feature.status='other',feature=>feature.values[0]='different-feature',feature=>delete feature.values,
 ]){const altered=records.slice();altered[1]={...records[1],gpu:{...records[1].gpu,environment:structuredClone(records[1].gpu.environment)}};edit(altered[1].gpu.environment[name]);assert.throws(()=>audit(altered));}
 for(const edit of [gpu=>delete gpu.adapterFeaturesAvailable,gpu=>delete gpu.deviceFeaturesEnabled,gpu=>gpu.adapterInfo.values.architecture='other',gpu=>gpu.deviceLimits.values.maxBufferSize++,gpu=>gpu.deviceFeaturesEnabled.reason='new reason']){
  const altered=records.slice();altered[1]={...records[1],gpu:{...records[1].gpu,environment:structuredClone(records[1].gpu.environment)}};edit(altered[1].gpu.environment);assert.throws(()=>audit(altered));
 }
});
test('historical schema1 four archived raws replay current actual SDK as numerical compatibility only',()=>{
 let calls=0;const result=verifyDerivedBrowserReports(historical,{...context,replayKind:'actual-node-wasm-historical-numerical-compatibility',replay:(input,settings)=>{++calls;assert.equal(settings.readback,'single');return runtime.prepareDerivedMesh(input,settings);}});
 assert.equal(calls,4);assert.equal(result.schema,1);assert.equal(result.classification,'historical numerical compatibility; not a same-SDK performance cohort');assert.equal(result.cohort,null);assert.equal(result.draws,80);assert.equal(result.numericComparisons,136460);
 for(const r of result.records){assert.equal(r.readback,'single');assert.equal(r.getterRecordsTelemetry.presentTrials,0);assert.equal(r.getterRecordsTelemetry.absentTrials,5);assert.match(r.getterRecordsTelemetry.note,/not fabricated/);}
 assert.notEqual(historical[0].manifest.data.artifacts['assets/pikapika-simulation.wasm'].sha256,manifest.artifacts['assets/pikapika-simulation.wasm'].sha256);
 assert.deepEqual(rawBytes.map(sha),rawHashes);
});
test('schema count mode and cohort controls reject missing duplicated mixed and unknown reports',()=>{
 const controls=[
  r=>r.schema=3,r=>r.kind='other',r=>r.trialSchema=1,r=>r.summarySchema=2,r=>r.readback='auto',r=>r.settings.readback='batch',
  r=>r.sessionId='other',r=>r.runtimeGeneration=2,r=>r.runOrdinal=0,r=>r.runOrdinal=2,
  (r,all)=>{all[0]=structuredClone(all[1]);},r=>r.settings.maxVertices=10,r=>r.input.positions[0][0]=1,
  r=>r.environment.dpr=2,r=>r.environment.viewport.width++,r=>r.environment.canvas.height++,r=>r.environment.buildMarker='ffffffffffffffff',
  r=>r.runtime.wasmBytes++,r=>r.runtime.startupMs++,r=>r.manifest.data.compiler='fake',r=>r.manifest.data.sourceSha256['core/src/core.cpp']='0'.repeat(64),r=>r.manifest.status='unknown',r=>r.manifest.url='https://example.test/old.json',
  r=>r.camera.eye[0]++,r=>r.model.scale[0]=2,r=>r.projection.farMetres=10,
 ];
 for(const edit of controls)assert.throws(()=>audit(changed(edit)));
 assert.throws(()=>audit(current.slice(1)));assert.throws(()=>audit([historical[0],...current.slice(1)]));assert.throws(()=>audit(historical.slice(0,3)));
 const legacy=historical.slice();legacy[0]={...legacy[0],readback:'single'};assert.throws(()=>verifyDerivedBrowserReports(legacy,context));
 const oldSDK=current.map(r=>({...r,manifest:{...r.manifest,data:historical[0].manifest.data}}));assert.throws(()=>audit(oldSDK));
});
test('summary controls reject unknown groups stages rows duplicated missing and false success fields',()=>{
 const controls=[r=>r.summary[0].group='unknown',r=>r.summary[0].stage='unknown',r=>r.summary[0].phase='later',r=>r.summary[0].kind='batch',r=>r.summary[0].extra=1,r=>r.summary[0].statistics.extra=0,r=>r.summary[0].statistics.medianMs++,r=>r.summary[0].valid=0,r=>r.summary[0].unavailable=1,r=>r.summary[0].expected=0,r=>r.summary[1]=structuredClone(r.summary[0]),r=>r.summary.pop(),r=>r.summary.push(structuredClone(r.summary[0]))];
 for(const edit of controls)assert.throws(()=>audit(changed(edit)));
});
test('trial timing counters status and dense telemetry mutations cannot be accepted as successful summaries',()=>{
 const controls=[r=>r.trials.pop(),r=>r.trials[0].phase='measure',r=>r.trials[0].pair=1,r=>r.trials[0].order.reverse(),r=>r.trials[0].cpu.extra={},r=>r.trials[0].skip=true,r=>r.trials[0].cpu.baseline.skip=true,r=>r.trials[0].draw.baseline.fresh.skip=true,
  r=>r.status='timing_invalid',r=>r.error={message:'hidden'},r=>r.timingInvalid=true,r=>r.clockError={},r=>r.startup.clockError={},r=>r.sourcePreparation.timingErrors.push({}),r=>r.sourcePreparation.sourceEvaluationMs=-1,
  r=>r.trials[0].cpu.baseline.state='failed',r=>r.trials[0].cpu.baseline.modelStatus='unresolved',r=>r.trials[0].cpu.baseline.clockError={},r=>r.trials[0].cpu.baseline.timing=null,
  r=>r.trials[0].cpu.instrumented.timing.getterKinds=Array(4),r=>r.trials[0].cpu.instrumented.timing.getterRecords=Array(4),r=>delete r.trials[0].cpu.instrumented.timing.getterRecords,r=>r.trials[0].cpu.instrumented.timing.getterKinds[0]++,r=>r.trials[0].cpu.instrumented.timing.getterRecords[0]++,
  r=>r.trials[0].cpu.instrumented.timing.stages.cppGetter.calls++,r=>r.trials[0].cpu.instrumented.timing.stages.outputCopy.calls++,r=>r.trials[0].cpu.instrumented.timing.stages.extra={calls:0,elapsedMs:0},r=>r.trials[0].cpu.instrumented.timing.unassignedMs++,r=>r.trials[0].cpu.instrumented.timing.elapsedMs=-1,
  r=>r.trials[0].draw.instrumented.fresh.timing.stages.queueWait.calls=0,r=>r.trials[0].draw.instrumented.fresh.timing.unassignedMs++,r=>r.trials[0].draw.baseline.factory.clockError={},r=>r.trials[0].draw.baseline.factory.metadata.vertexCount++,
 ];
 for(const edit of controls)assert.throws(()=>audit(changed(edit)));
});
test('GPU transfer retirement continuity disposal and skipped drawing mutations are rejected',()=>{
 const controls=[r=>r.gpu.status='ready',r=>r.gpu.events.push({message:'callback'}),r=>r.trials[0].draw.baseline.fresh.state='failed',r=>r.trials[0].draw.baseline.fresh.checkedResolved=false,r=>r.trials[0].draw.baseline.fresh.error={},r=>r.trials[0].draw.baseline.fresh.after.triangles++,r=>r.trials[0].draw.baseline.fresh.delta.uploadedMeshBytes++,r=>r.trials[0].draw.baseline.fresh.before.uploadedMeshBytes++,r=>r.trials[0].draw.baseline.cache.delta.uploadedMeshBytes=72,r=>r.trials[0].draw.baseline.cache.delta.destroyedMeshBuffers=1,r=>r.disposeErrors.push({}),r=>r.disposal.after.destroyedMeshBuffers=9,r=>r.disposal.delta.drawCalls=0,r=>r.disposal.deviceDestroyRequested=false,r=>r.execution.drawCompleted=19,r=>r.environment.visibilityAtStart='hidden',r=>r.visibilityAtFinish='hidden',r=>r.visibilityChanges.push('hidden'),r=>r.cancellation='hidden'];
 for(const edit of controls)assert.throws(()=>audit(changed(edit)));
});
test('all first DTO types/key order/bits/typed bytes and every digest are checked against independent mode captures',()=>{
 assert.throws(()=>audit(changed(r=>r.trials[3].cpu.baseline.digest.sha256='0'.repeat(64))));assert.throws(()=>audit(changed(r=>r.trials[1].cpu.instrumented.digest.status='unknown')));
 const altered=current.slice();for(const i of [0,1]){altered[i]=structuredClone(current[i]);for(const kind of ['baseline','instrumented']){
  const dto=altered[i].firstPair[kind];assert.equal(dto.type,'Object');dto.entries.reverse();
 }}assert.throws(()=>audit(altered));
 const poison=current.slice();for(const i of [0,1]){poison[i]=structuredClone(current[i]);for(const kind of ['baseline','instrumented'])poison[i].firstPair[kind]={type:'Object',entries:[]};}assert.throws(()=>audit(poison));
 function find(node,predicate){if(predicate(node))return node;if(node?.type==='Object')for(const [,value]of node.entries){const hit=find(value,predicate);if(hit)return hit;}if(node?.type==='Array')for(const value of node.items){const hit=find(value,predicate);if(hit)return hit;}return null;}
 // Alter both modes and both first outputs equally: cross-mode agreement alone
 // must not bypass the independent actual C++ per-mode result comparison.
 for(const mutate of [
  tree=>{const x=find(tree,x=>x?.type==='Float32Array');assert.ok(x);x.type='Uint32Array';},
  tree=>{const x=find(tree,x=>x?.type==='Float32Array');assert.ok(x);x.bytesHex=(x.bytesHex[0]==='0'?'1':'0')+x.bytesHex.slice(1);},
  tree=>{const x=find(tree,x=>x?.type==='number');assert.ok(x);x.bits=x.bits.slice(0,-1)+(x.bits.at(-1)==='0'?'1':'0');}
 ]){const records=current.slice();for(const i of [0,1]){records[i]=structuredClone(current[i]);for(const kind of ['baseline','instrumented'])mutate(records[i].firstPair[kind]);}assert.throws(()=>audit(records));}
});
test('strict raw parsing rejects duplicate keys malformed UTF8 nonfinite overflow underflow and truncation while preserving negative zero',()=>{
 assert.ok(Object.is(parseDerivedBrowserReport(Buffer.from('{"zero":-0}')).zero,-0));
 for(const value of ['{"schema":2,"schema":2}','{"v":1e999}','{"v":1e-999}','{"v":NaN}','{"a":','[] trailing'])assert.throws(()=>parseDerivedBrowserReport(Buffer.from(value)));
 assert.throws(()=>parseDerivedBrowserReport(Buffer.from([0xff])));assert.throws(()=>parseDerivedBrowserReport(Buffer.alloc(0)));
});
test('CLI branch rejects wrong arity and duplicate source paths before creating output; import performs no CLI run',async()=>{
 await assert.rejects(verifyDerivedBrowserFiles([]));await assert.rejects(verifyDerivedBrowserFiles(['same','same','a','b']));assert.equal(captureQueries,6);
});
