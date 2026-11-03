import assert from 'node:assert/strict';
import {readFile,mkdir,mkdtemp,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createDerivedGPUProfileCases} from '../tools/derived-gpu-cases.mjs';
import {encodeDerivedGPUExact} from '../tools/derived-gpu-lab.mjs';

const files=process.argv.slice(2);assert.equal(files.length,4,'Supply 4 browser report files: 4, 64, 512 faces and retry 4');
const root=fileURLToPath(new URL('../',import.meta.url)),base=path.join(root,'build/derived-gpu-verification');await mkdir(base,{recursive:true});const run=await mkdtemp(path.join(base,'run-'));
const sha=b=>createHash('sha256').update(b).digest('hex'),wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)),runtime=await loadSimulationRuntime({wasmBytes:wasm}),setup=createDerivedGPUProfileCases(runtime);
const records=[];let numericComparisons=0,draws=0,uploads=0;
function timing(t,names=null){assert.ok(t&&Number.isFinite(t.elapsedMs)&&t.elapsedMs>=0);if(names){let sum=0;for(const n of names){assert.equal(t.stages[n].calls,1);assert.ok(Number.isFinite(t.stages[n].elapsedMs)&&t.stages[n].elapsedMs>=0);sum+=t.stages[n].elapsedMs;}assert.ok(sum<=t.elapsedMs);assert.equal(t.unassignedMs,t.elapsedMs-sum);}}
function statistics(values){const s=[...values].sort((a,b)=>a-b),n=s.length;return {samples:n,medianMs:s[Math.floor(n/2)],p95Ms:s[Math.ceil(.95*n)-1],maxMs:s[n-1]};}
const expectedNames=['actual-source-4','rational-normal-64','sheared-grid-512','actual-source-4'];
for(let fileIndex=0;fileIndex<files.length;++fileIndex){
 const name=files[fileIndex],raw=await readFile(name);assert.ok(raw.length<16*1024*1024);const r=JSON.parse(raw),item=setup.cases.find(c=>c.name===r.caseName);assert.ok(item);assert.equal(r.caseName,expectedNames[fileIndex]);assert.equal(r.status,'completed');assert.equal(r.gpu.status,'completed');assert.equal(r.trials.length,5);
 assert.deepEqual(r.input,item.input);assert.deepEqual(r.settings,item.settings);assert.equal(r.sourcePreparation.authorSourceBefore,setup.sourcePreparation.authorSourceBefore);assert.equal(r.sourcePreparation.authorSourceAfter,setup.sourcePreparation.authorSourceBefore);
 assert.equal(r.environment.visibilityAtStart,'visible');assert.equal(r.visibilityAtFinish,'visible');assert.deepEqual(r.visibilityChanges,[]);assert.deepEqual(r.disposeErrors,[]);assert.equal(r.clockError,null);assert.equal(r.cancellation,null);
 assert.deepEqual(r.execution,{prepareCompleted:10,freshCompleted:10,cacheCompleted:10,newUploads:10,drawCompleted:20});assert.equal(r.verified.fullDTOEqualPairs,5);assert.equal(r.verified.inputUnchanged,true);assert.equal(r.verified.sourceUnchanged,true);
 const actual=runtime.prepareDerivedMesh(item.input,item.settings),exact=encodeDerivedGPUExact(actual),hash=sha(exact.text);assert.equal(actual.status,'completed');assert.deepEqual(r.firstPair.baseline,exact.encoded);assert.deepEqual(r.firstPair.instrumented,exact.encoded);
 const comparisons=5*(exact.counts.numbers+exact.counts.typedElements);assert.equal(r.verified.comparedNumericValues,comparisons);numericComparisons+=comparisons;
 let fresh=0;
 for(let pair=0;pair<5;++pair){const t=r.trials[pair];assert.equal(t.pair,pair);assert.equal(t.phase,['initial','warmup','measure','measure','measure'][pair]);assert.deepEqual(t.order,pair%2?['instrumented','baseline']:['baseline','instrumented']);
  for(const kind of t.order){const cpu=t.cpu[kind];assert.equal(cpu.state,'completed');assert.equal(cpu.modelStatus,'completed');assert.equal(cpu.error,null);assert.equal(cpu.clockError,null);assert.equal(cpu.digest.status,'obtained');assert.equal(cpu.digest.sha256,hash);assert.deepEqual(cpu.comparedCounts,exact.counts);timing(cpu.timing);
   if(kind==='instrumented'){const x=cpu.timing;assert.deepEqual(x.getterKinds,[item.input.positions.length,item.input.triangles.length,item.input.triangles.length,item.input.triangles.length]);let sum=0;for(const stage of Object.values(x.stages)){assert.ok(Number.isFinite(stage.elapsedMs)&&stage.elapsedMs>=0);sum+=stage.elapsedMs;}assert.ok(sum<=x.elapsedMs);assert.equal(x.unassignedMs,x.elapsedMs-sum);}
   const d=t.draw[kind];assert.ok(Number.isFinite(d.factory.elapsedMs)&&d.factory.elapsedMs>=0);assert.equal(d.factory.clockError,null);assert.equal(d.factory.metadata.triangleCount,item.input.triangles.length);assert.equal(d.factory.metadata.floatCount,18*item.input.triangles.length);
   for(const mode of ['fresh','cache']){const v=d[mode];assert.equal(v.state,'completed');assert.equal(v.error,null);assert.equal(v.clockError,null);timing(v.timing,kind==='instrumented'?['syncRender','validationWait','queueWait']:null);assert.equal(v.after.drawCalls,1);assert.equal(v.after.triangles,item.input.triangles.length);assert.equal(v.delta.uploadedMeshBytes,mode==='fresh'?72*item.input.triangles.length:0);assert.equal(v.delta.destroyedMeshBuffers,mode==='fresh'&&fresh>0?1:0);if(mode==='fresh')++fresh;++draws;}
  }
 }
 assert.equal(fresh,10);uploads+=fresh;assert.equal(r.disposal.ownedDevice,true);assert.equal(r.disposal.deviceDestroyRequested,true);assert.equal(r.disposal.before.uploadedMeshBytes,720*item.input.triangles.length);assert.equal(r.disposal.before.destroyedMeshBuffers,9);assert.equal(r.disposal.after.destroyedMeshBuffers,10);assert.equal(r.disposal.after.drawCalls,0);assert.equal(r.disposal.delta.destroyedMeshBuffers,1);
 for(const row of r.summary){const selected=r.trials.filter(t=>t.phase===row.phase),values=selected.map(t=>{let record;if(row.group==='cpu')record=t.cpu[row.kind];else if(row.group==='factory')return t.draw[row.kind].factory.elapsedMs;else record=t.draw[row.kind][row.group];return row.stage==='elapsedMs'?record.timing.elapsedMs:row.stage==='unassignedMs'?record.timing.unassignedMs:record.timing.stages[row.stage].elapsedMs;});assert.equal(row.expected,row.phase==='measure'?3:1);assert.equal(row.valid,row.expected);assert.equal(row.unavailable,0);assert.deepEqual(row.statistics,statistics(values));}
 records.push({path:name,bytes:raw.length,sha256:sha(raw),caseName:r.caseName,faces:item.input.triangles.length,numericComparisons:comparisons,exactResultSHA256:hash,execution:r.execution,sourceUnchanged:true,summary:r.summary.filter(x=>x.phase==='measure')});
}
setup.verifySourceUnchanged();const sourceHashes={};for(const p of ['scripts/verify-derived-gpu-lab.mjs','tools/derived-gpu-lab.mjs','tools/derived-gpu-profile.mjs','tools/derived-gpu-cases.mjs','engine/simulation.mjs','engine/renderer.mjs','engine/derived-render.mjs'])sourceHashes[p]=sha(await readFile(path.join(root,p)));
const result={status:'PASS',browserReports:4,numericComparisons,draws,newUploads:uploads,cacheDraws:draws-uploads,records,wasm:{bytes:wasm.length,sha256:sha(wasm)},sourceHashes,scope:'Recorded browser DTO/type/bits/digests compared with actual Node WASM; all raw timing/statistics/retirement counts audited. Actual GPU bytes are not read back here. CPU wall waits are not GPU timestamps or presentation proof.',command:[process.execPath,...process.execArgv,fileURLToPath(import.meta.url),...files],runDirectory:run};
await writeFile(path.join(run,'verification.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:result.status,browserReports:4,numericComparisons,draws,newUploads:uploads,runDirectory:run},null,2));
