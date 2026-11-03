import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const ray={origin:[0,0,0],direction:[0,0,1],maximumParameter:100},disk=(center,normal)=>({kind:'disk',center,normal,apertureRadius:100});
const plate=[{surface:disk([0,0,1],[0,0,-1]),nextIndex:1.5},{surface:disk([0,0,2],[0,0,-1]),nextIndex:1}];
const rational=[{surface:disk([0,0,1],[3,0,-4]),nextIndex:39,branch:'reflected'},{surface:disk([24,0,-6],[-543,300,-76]),nextIndex:39,branch:'reflected'}];
const encloses=(a,x)=>assert.ok(a[0]<=x&&x<=a[1],`${a} excludes ${x}`);
function fraction(x){const d=new DataView(new ArrayBuffer(8));d.setFloat64(0,x);const b=d.getBigUint64(0),sgn=b>>63n?-1n:1n;let e=Number((b>>52n)&2047n),m=b&((1n<<52n)-1n);assert.notEqual(e,2047);if(e){m+=1n<<52n;e-=1075;}else e=-1074;return e>=0?[sgn*m*(1n<<BigInt(e)),1n]:[sgn*m,1n<<BigInt(-e)];}
function containsFraction(a,n,d){const [l,ld]=fraction(a[0]),[h,hd]=fraction(a[1]);assert.ok(l*d<=n*ld&&h*d>=n*hd,`${a} excludes exact fraction`);}

test('actual WASM normal transmission and reflection retain world circular coherency sign',()=>{
  const r=runtime.tracePolarizedRoute(ray,plate,{power:[1,0,0,1]});assert.equal(r.status,'completed');containsFraction(r.completion.state.power,576n,625n);containsFraction(r.completion.state.coherency.upper[0].imag,288n,625n);assert.equal(r.completedPowerSteps,2);
  const reflected=runtime.tracePolarizedRoute(ray,[{...plate[0],branch:'reflected'}],{power:[1,0,0,1]});assert.equal(reflected.status,'completed');containsFraction(reflected.completion.state.coherency.upper[0].imag,1n,50n);
});
test('actual WASM noncoplanar route excludes resetting polarization and preserves old geometry packets',()=>{
  const options={index:25,transverseReference:[0,-1,0]},source=JSON.stringify({ray,rational,options}),r=runtime.tracePolarizedRoute(ray,rational,options);assert.equal(r.status,'completed');containsFraction(r.completion.state.power,42544n,17294403n);assert.ok(r.completion.state.power[1]<1263376/466948881);
  const old=runtime.traceOpticalRoute(ray,rational,options);assert.deepEqual(r.geometry.segments,old.segments);assert.deepEqual(r.geometry.completion,old.completion);assert.equal(JSON.stringify({ray,rational,options}),source);
  const u=runtime.tracePolarizedRoute(ray,rational,{...options,power:[1,0,1,0]});containsFraction(u.completion.state.power,322768n,259416045n);
});
test('actual WASM source and incidence frame uncertainty do not publish a stale final tensor',()=>{
  assert.equal(runtime.tracePolarizedRoute(ray,plate).status,'completed');
  const frame=runtime.tracePolarizedRoute(ray,plate,{transverseReference:[0,0,1]});assert.equal(frame.status,'power_unresolved');assert.equal(frame.powerFailure,'initial_frame_uncertain');assert.equal(frame.completion,null);assert.equal(frame.geometry.status,'completed');assert.ok(frame.geometry.completion);
  const outside=runtime.tracePolarizedRoute(ray,plate,{power:[1,2,0,0]});assert.equal(outside.status,'invalid_input');assert.equal(outside.completion,null);
  const uncertain=runtime.tracePolarizedRoute(ray,plate,{power:[1,1,2**-54,0]});assert.notEqual(uncertain.status,'completed');assert.equal(uncertain.completion,null);
  const near=runtime.tracePolarizedRoute({...ray,direction:[[-1e-8,1e-8],0,1]},plate.slice(0,1));assert.equal(near.status,'power_unresolved');assert.equal(near.powerFailure,'incidence_frame_uncertain');assert.equal(near.completion,null);
});
test('actual WASM geometry and total budget failures remain distinct and retry deterministically',()=>{
  const options={index:25,transverseReference:[0,-1,0]},good=runtime.tracePolarizedRoute(ray,rational,options),saved=JSON.stringify(good);
  const limited=runtime.tracePolarizedRoute(ray,rational,{...options,maximumTotalSqrtRefinements:1});assert.equal(limited.status,'budget_exceeded');assert.equal(limited.completion,null);assert.ok(limited.geometry);
  const miss=runtime.tracePolarizedRoute(ray,[{surface:disk([0,0,-1],[0,0,-1]),nextIndex:1.5}]);assert.equal(miss.status,'geometry_failed');assert.equal(miss.geometry.status,'geometry_miss');assert.equal(miss.completion,null);
  assert.deepEqual(runtime.tracePolarizedRoute(ray,rational,options),good);assert.equal(JSON.stringify(good),saved);
});
test('actual WASM retains subnormal half-power components that ordinary division loses',()=>{
  const tiny=Number.MIN_VALUE;assert.equal(tiny/2,0);
  const identity=runtime.tracePolarizedRoute(ray,[],{power:[tiny,0,0,tiny]});assert.equal(identity.status,'completed');containsFraction(identity.completion.state.coherency.upper[0].imag,1n,1n<<1075n);
  const transmitted=runtime.tracePolarizedRoute(ray,plate.slice(0,1),{power:[tiny,0,0,tiny]});assert.equal(transmitted.status,'completed');containsFraction(transmitted.completion.state.coherency.upper[0].imag,12n,25n*(1n<<1074n));containsFraction(transmitted.completion.state.power,24n,25n*(1n<<1074n));
});
test('actual WASM polarized snapshot getters preserve output on bad exchange and global reset clears records',()=>{
  runtime.tracePolarizedRoute(ray,plate);const m=runtime.native;runtime.check(m._pp_sim_polarized_route_segment(0,1));const saved=runtime.output();assert.notEqual(m._pp_sim_polarized_route_segment(999,1),0);assert.deepEqual(runtime.output(),saved);assert.notEqual(m._pp_sim_polarized_route_segment(0,2),0);assert.deepEqual(runtime.output(),saved);
  const n=runtime.inputF64(Array(31).fill(0));assert.notEqual(m._pp_sim_polarized_route(n-1),0);assert.deepEqual(runtime.output(),saved);runtime.check(m._pp_sim_polarized_route_segment(0,1));assert.deepEqual(runtime.output(),saved);
  runtime.check(m._pp_sim_reset());assert.notEqual(m._pp_sim_polarized_route_initial(),0);assert.equal(runtime.tracePolarizedRoute(ray,plate).status,'completed');
});
