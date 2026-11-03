import {readFile,writeFile,mkdtemp} from 'node:fs/promises';
import {performance} from 'node:perf_hooks';
import {createHash} from 'node:crypto';
import os from 'node:os';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {createDerivedMeshRenderData} from '../../engine/derived-render.mjs';
const dir=await mkdtemp('build/derived-render-root/timing-');
const bytes=await readFile('assets/pikapika-simulation.wasm'),start=performance.now();
const runtime=await loadSimulationRuntime({wasmBytes:bytes});
const report={scope:'Exploratory Node end-to-end SDK + separate opaque-copy timing. Repeated single XY triangle, not representative animated character or GPU performance. No FPS claim.',node:process.version,platform:process.platform,cpu:os.cpus()[0].model,wasmSha256:createHash('sha256').update(bytes).digest('hex'),startupMs:performance.now()-start,warmupPerCase:2,measuredPerCase:5,cases:[]};
for(const faces of [4,64,512,4096,32768]){
 const positions=Array.from({length:faces===32768?2048:3},(_,i)=>i===1?[1,0,0]:i===2?[0,1,0]:[0,0,0]),triangles=Array.from({length:faces},()=>[0,1,2]),input={positions,triangles},before=JSON.stringify(input),times=[];let expected;
 for(let i=-2;i<5;i++){
  const a=performance.now(),result=runtime.prepareDerivedMesh(input),b=performance.now(),token=createDerivedMeshRenderData(result),c=performance.now();
  if(result.status!=='completed'||token.floatCount!==faces*18)throw Error('timing model failed');
  const data=result.geometry.interleaved,hash=createHash('sha256').update(new Uint8Array(data.buffer,data.byteOffset,data.byteLength)).digest('hex');
  if(expected&&hash!==expected)throw Error('timing bytes changed');expected=hash;
  if(JSON.stringify(input)!==before)throw Error('timing input mutated');
  if(i>=0)times.push({sdkMs:b-a,copyMs:c-b});
 }
 const metrics=key=>{const sorted=times.map(x=>x[key]).sort((a,b)=>a-b);return {median:sorted[2],nearestRankP95:sorted[4],maximum:sorted[4]};};
 report.cases.push({vertices:positions.length,faces,settings:{sqrtRefinements:128},byteLength:faces*18*4,interleavedSha256:expected,times,sdkMs:metrics('sdkMs'),copyMs:metrics('copyMs')});
 await writeFile(dir+'/pilot.json',JSON.stringify(report,null,2)+'\n');console.log(faces,'faces complete');
}
await writeFile('build/derived-render-root/timing-latest.json',JSON.stringify({runDirectory:dir},null,2)+'\n');console.log(dir);
