import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {evaluateLensPowerProfile} from '../engine/polarized-camera.mjs';
const bytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:bytes});
const observations=[];
for(const [radialSamples,angularSamples,totalBudget] of [[1,4,1000000],[2,8,1000000],[4,16,1000000],[8,32,1000000],[16,64,1000000],[16,64,4000000]]){
 const result=await evaluateLensPowerProfile(runtime,{radialSamples,angularSamples,wavelengths:[550e-9],settings:{maximumTotalSqrtRefinements:totalBudget}});
 observations.push({profile:result.profile,packetCount:result.packets.length,timing:result.timing,paths:result.channels[0].paths.map(({id,result:r})=>({id,status:r?.status,counts:r?.counts,stats:r?.stats,evaluations:r?.evaluations,sqrt:[r?.geometrySqrtRefinements,r?.powerSqrtRefinements,r?.sensorSqrtRefinements],firstStatus:r?.records[0]?.status,lastStatus:r?.records.at(-1)?.status}))});
}
const report={wasmBytes:bytes.length,wasmSha256:createHash('sha256').update(bytes).digest('hex'),node:process.version,observations,limits:'Measured finite prescribed packet experiments, each with the same explicit 1W source. Different rounded pupil nodes define different finite measures; no continuous pupil quadrature error bound, source irradiance, combined paths, or 60fps performance claim.'};
await writeFile(process.argv[2]??'reports/polarized-packet-profile-observations.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(observations.map(o=>({packets:o.packetCount,budget:o.profile.settings.maximumTotalSqrtRefinements,milliseconds:o.timing.totalMilliseconds,paths:o.paths.map(p=>({id:p.id,status:p.status,detected:p.stats?.detectedPower,unknown:p.counts?.unknown}))})),null,2));
