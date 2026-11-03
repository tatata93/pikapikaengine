import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {evaluateLensSpotProfile} from '../engine/optical-camera.mjs';
const wasm=await readFile('assets/pikapika-simulation.wasm'),runtime=await loadSimulationRuntime({wasmBytes:wasm});
const cases=[];for(const [radialSamples,angularSamples]of [[2,8],[4,16],[8,32],[16,64]]){
 const out=await evaluateLensSpotProfile(runtime,{radialSamples,angularSamples,settings:{maximumTotalSqrtRefinements:4000000}});assert.ok(out.channels.every(c=>c.result.status==='completed'&&c.result.counts.accepted===radialSamples*angularSamples));cases.push({label:'area-quadrature-refinement',output:out});}
for(const [label,p]of [['maximum-samples-default-budget',{radialSamples:16,angularSamples:64}],['small-pupil',{apertureRadius:.001}],['defocus',{apertureRadius:.001,sensorZ:.06}],['finite-source',{apertureRadius:.001,source:{kind:'finite',position:[0,0,-1]}}],['budget',{settings:{maximumSampleEvaluations:1}}]]){const out=await evaluateLensSpotProfile(runtime,p);if(label==='budget')assert.ok(out.channels.every(c=>c.result.status==='budget_exceeded'&&c.result.stats===null));cases.push({label,output:out});}
const summary={status:'PASS',wasmSha256:createHash('sha256').update(wasm).digest('hex'),cases:cases.map(({label,output:o})=>({label,profile:o.profile,milliseconds:o.timing.totalMilliseconds,channels:o.channels.map(c=>({wavelength:c.wavelength,index:c.index,status:c.result?.status,counts:c.result?.counts,stats:c.result?.stats}))})),limits:'Finite equal-area midpoint quadrature observations, not an enclosure of continuous pupil integration error. Timings are individual Node operations on this host, not realtime/game performance guarantees.'};
await writeFile(process.argv[2]??'build/optical-spot-profile-observations.json',JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary.cases.map(c=>({label:c.label,samples:c.profile.radialSamples*c.profile.angularSamples,milliseconds:c.milliseconds,msr550:c.channels[1]?.stats?.moments?.meanSquaredRadius}))));
