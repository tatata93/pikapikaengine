import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const enclosed=(a,x)=>assert.ok(a[0]<=x&&x<=a[1],`${x} outside ${a}`);
const disk=z=>({kind:'disk',center:[0,0,z],normal:[0,0,-1],apertureRadius:10});
const step=(z,nextIndex=1,branch='transmitted')=>({surface:disk(z),nextIndex,branch,maximumParameter:10});
const direct=[step(0,1.5),step(.25),step(1.25)],ray={origin:[0,0,-1],direction:[0,0,1],maximumParameter:10};
test('actual WASM explicit plate route encloses distance optical path and arbitrary-polarization power',()=>{
  const r=runtime.traceOpticalRoute(ray,direct);assert.equal(r.status,'completed');assert.equal(r.segments.length,3);assert.equal(r.completedSteps,3);
  enclosed(r.completion.totals.distance,2.25);enclosed(r.completion.totals.opticalPathLength,2.375);enclosed(r.completion.totals.throughput,.9216);
  assert.deepEqual(r.segments[1].incoming.origin,r.segments[0].outgoing.origin);assert.deepEqual(r.segments[1].incoming.direction,r.segments[0].outgoing.direction);
  assert.deepEqual(r.segments[0].incidentIndex,[1,1]);assert.deepEqual(r.segments[1].incidentIndex,[1.5,1.5]);
});
test('actual WASM prescribed two-reflection ghost retains additional length and Fresnel attenuation',()=>{
  const ghost=[step(0,1.5),step(.25,1,'reflected'),step(0,1,'reflected'),step(.25),step(1.25)];
  const r=runtime.traceOpticalRoute(ray,ghost);assert.equal(r.status,'completed');assert.equal(r.segments.length,5);
  enclosed(r.completion.totals.distance,2.75);enclosed(r.completion.totals.opticalPathLength,3.125);enclosed(r.completion.totals.throughput,.00147456);
  assert.deepEqual(r.segments[2].incidentIndex,[1.5,1.5]);assert.deepEqual(r.segments[3].incidentIndex,[1.5,1.5]);
});
test('actual WASM oblique rational route and full dispersion index intervals remain enclosed',()=>{
  const r=runtime.traceOpticalRoute({...ray,direction:[3,0,4]},[step(0,3),step(.25,4),step(1.25,4)],{index:4});assert.equal(r.status,'completed');
  enclosed(r.completion.ray.origin[0],11/6);enclosed(r.completion.totals.distance,35/12);enclosed(r.completion.totals.opticalPathLength,45/4);
  assert.ok(r.completion.totals.throughput[0]<=331776/390625&&r.completion.totals.throughput[1]>=1);
  const wavelength=2**-20,phase=runtime.queryDispersion({kind:'cauchy',coefficients:[1.5,2**-44,2**-88]},wavelength).values.phase;
  const p=runtime.traceOpticalRoute(ray,[step(0,phase),step(.25),step(1.25)],{vacuumWavelength:wavelength});assert.equal(p.status,'completed');
  assert.deepEqual(p.segments[0].otherIndex,phase);assert.deepEqual(p.segments[1].incidentIndex,phase);assert.equal(p.vacuumWavelength,wavelength);
});
test('actual WASM route failures and explicit zero hit never fabricate a final ray or hidden offset',()=>{
  const budget=runtime.traceOpticalRoute(ray,direct,{maximumSteps:2});assert.equal(budget.status,'budget_exceeded');assert.equal(budget.completion,null);assert.equal(budget.segments.length,0);
  const tir=runtime.traceOpticalRoute({...ray,direction:[4,0,3]},[step(0)],{index:1.5});assert.equal(tir.status,'branch_unavailable');assert.equal(tir.completion,null);assert.equal(tir.segments[0].interface.kind,'total_internal_reflection');
  const mixed=runtime.traceOpticalRoute({...ray,direction:[4,0,3]},[step(0)],{index:[1.2,1.3]});assert.equal(mixed.status,'interface_unresolved');assert.equal(mixed.completion,null);
  const zero=runtime.traceOpticalRoute({origin:[0,0,0],direction:[0,0,1]},[step(0)]);assert.equal(zero.status,'completed');enclosed(zero.completion.totals.distance,0);assert.ok(zero.segments[0].geometry.hit.parameter.every(x=>x===0));
  const straddle=runtime.traceOpticalRoute({origin:[0,0,[-1e-9,1e-9]],direction:[0,0,1]},[step(0)]);assert.equal(straddle.status,'geometry_unresolved');assert.equal(straddle.completion,null);
  const invalid=runtime.traceOpticalRoute(ray,[step(0)],{index:[0,1]});assert.equal(invalid.status,'invalid_input');assert.equal(invalid.completion,null);
  const later=runtime.traceOpticalRoute(ray,[...direct.slice(0,2),{...direct[2],nextIndex:[0,1]}]);assert.equal(later.status,'invalid_input');assert.equal(later.failedStep,2);assert.equal(later.segments.length,0);assert.equal(later.completion,null);
});
