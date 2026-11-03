import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createLensSpotProfile,createLensPupilSamples,serializeLensSpotProfile,parseLensSpotProfile,evaluateLensSpotProfile} from '../engine/optical-camera.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const encloses=(a,x)=>assert.ok(a[0]<=x&&x<=a[1],`${a} excludes ${x}`);

test('equal-area pupil quadrature has exact opposite pairs and analytic disk radial moment',()=>{
  for(const [radialSamples,angularSamples]of [[1,4],[4,16],[16,64]]){
    const p=createLensSpotProfile({radialSamples,angularSamples}),nodes=createLensPupilSamples(p);assert.equal(nodes.length,radialSamples*angularSamples);
    let moment=0,weight=0;for(let j=0;j<nodes.length;j+=2){const [a,b]=nodes.slice(j,j+2);assert.equal(a.position[0],-b.position[0]);assert.equal(a.position[1],-b.position[1]);assert.equal(a.weight,b.weight);}
    for(const n of nodes){moment+=n.weight*(n.position[0]**2+n.position[1]**2);weight+=n.weight;}
    assert.ok(Math.abs(weight-1)<1e-13);assert.ok(Math.abs(moment-p.apertureRadius**2/2)<1e-17);assert.deepEqual(nodes,createLensPupilSamples(p));
  }
});
test('profile save reload preserves explicit finite source dispersion wavelengths and budgets',()=>{
  const p=createLensSpotProfile({source:{kind:'finite',position:[.013,-.002,-2]},wavelengths:[477e-9,589e-9],material:{coefficients:[1.49,5.3e-15,1e-29],validBand:[450e-9,650e-9]},settings:{maximumParameterWidth:2e-8,maximumSampleEvaluations:17}});
  assert.deepEqual(parseLensSpotProfile(serializeLensSpotProfile(p)),p);assert.deepEqual(createLensPupilSamples(parseLensSpotProfile(serializeLensSpotProfile(p))),createLensPupilSamples(p));
  for(const invalid of [{source:{kind:'parallel',direction:[0,0,0]}},{source:{kind:'finite',position:[0,0,0]}},{angularSamples:7},{sensorZ:NaN},{wavelengths:[900e-9]},{material:{unknown:1}},{settings:{hiddenQuality:1}},{unknown:1}])assert.throws(()=>createLensSpotProfile(invalid));
});
test('actual WASM finite launch retains low term lost by ordinary binary64 subtraction',()=>{
  const origin=2**19,low=2**-40;assert.equal(low-origin,-origin);
  const r=runtime.makeOpticalLaunchRay({kind:'finite',position:[origin,0,-1]},[low,0,-.01]);assert.ok(r.direction[0][0]<=-origin&&r.direction[0][1]>-origin);
  const d=runtime.makeOpticalLaunchRay({kind:'parallel',direction:[.25,0,2]},[.1,0,-.01]).direction;for(let j=0;j<3;++j){encloses(d[j],[.25,0,2][j]);assert.equal(d[j][1]-d[j][0],0);}
});
test('actual WASM geometric spot uses independent weighted moments and rejects partial normalization',()=>{
  const input={samples:[{ray:{origin:[-1,0,-1],direction:[0,0,2]},weight:1},{ray:{origin:[1,0,-1],direction:[0,0,2]},weight:3}],sensor:{kind:'disk',center:[0,0,0],normal:[0,0,-1],apertureRadius:10}};
  const before=JSON.stringify(input),r=runtime.queryOpticalSpot(input);assert.equal(r.status,'completed');encloses(r.stats.moments.centroid[0],.5);encloses(r.stats.moments.meanSquaredRadius,.75);encloses(r.stats.totalWeight,4);encloses(r.records[0].sensor.hit.parameter,.5);encloses(r.records[0].sensor.hit.physicalDistance,1);
  const saved=JSON.stringify(r),partial=runtime.queryOpticalSpot(input,{maximumSampleEvaluations:1});assert.equal(partial.status,'budget_exceeded');assert.equal(partial.stats,null);assert.equal(partial.records[1].status,'not_examined');assert.equal(partial.counts.notExamined,1);
  assert.deepEqual(runtime.queryOpticalSpot(input),r);assert.equal(JSON.stringify(r),saved);assert.equal(JSON.stringify(input),before);
});
test('actual WASM synthetic lens preserves full dispersion phase and distinguishes point wavelengths',async()=>{
  const p=createLensSpotProfile({apertureRadius:.001,radialSamples:2,angularSamples:8}),before=JSON.stringify(p),out=await evaluateLensSpotProfile(runtime,p);
  assert.equal(JSON.stringify(p),before);assert.equal(out.channels.length,3);
  for(const c of out.channels){assert.equal(c.result.status,'completed');assert.deepEqual(c.index,c.dispersion.values.phase);assert.equal(c.result.counts.accepted,16);encloses(c.result.stats.moments.centroid[0],0);encloses(c.result.stats.moments.centroid[1],0);assert.ok(c.result.stats.moments.meanSquaredRadius[0]>=0);}
  assert.ok(out.channels[0].index[0]>out.channels[2].index[1]);assert.notDeepEqual(out.channels[0].result.stats.moments.meanSquaredRadius,out.channels[2].result.stats.moments.meanSquaredRadius);
});
test('cancellation and unresolved dispersion cannot silently produce a completed image',async()=>{
  const control=new AbortController();let yields=0;
  await assert.rejects(()=>evaluateLensSpotProfile(runtime,{}, {signal:control.signal,yieldControl:async()=>{if(++yields===1)control.abort();}}),{name:'AbortError'});
  const out=await evaluateLensSpotProfile(runtime,{radialSamples:1,angularSamples:4,material:{coefficients:[-1,0,0]}});assert.ok(out.channels.every(c=>c.result===null&&c.index===null&&c.dispersion.status!=='resolved'));
});
