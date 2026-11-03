import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const enclosed=(interval,x)=>assert.ok(interval[0]<=x&&interval[1]>=x,`${x} outside ${interval}`);
const cauchy={kind:'cauchy',coefficients:[1.5,2**-44,2**-88]};

test('actual WASM Cauchy phase derivative group have SI units',()=>{
  const r=runtime.queryDispersion(cauchy,2**-20);assert.equal(r.status,'resolved');
  enclosed(r.values.phase,401/256);enclosed(r.values.derivative,-147456);enclosed(r.values.group,437/256);
  assert.equal(r.values.withinInterfaceDomain,true);
});
test('actual WASM Sellmeier index and group differ',()=>{
  const r=runtime.queryDispersion({kind:'sellmeier',terms:[[2.25,2**-42]]},2**-20);
  assert.equal(r.status,'resolved');enclosed(r.values.phase,2);enclosed(r.values.derivative,-(2**19));enclosed(r.values.group,2.5);enclosed(r.squaredPhase,4);
});
test('actual WASM full wavelength band retains physical variation',()=>{
  const r=runtime.queryDispersion({kind:'cauchy',coefficients:[1.5,2**-44,0]},[2**-20,2**-19]);
  assert.equal(r.status,'resolved');enclosed(r.values.phase,25/16);enclosed(r.values.phase,97/64);
  const tight=runtime.queryDispersion({kind:'cauchy',coefficients:[1.5,2**-44,0]},[2**-20,2**-19],{maximumPhaseWidth:1e-4});
  assert.equal(tight.reason,'phase_width');assert.equal(tight.values,null);
});
test('actual WASM pole budgets and declared domains fail without stale values',()=>{
  const model={kind:'sellmeier',terms:[[.75,2**-42]]};
  assert.equal(runtime.queryDispersion(model,2**-21).reason,'pole_not_excluded');
  assert.equal(runtime.queryDispersion(model,2**-20,{maxSqrtRefinements:1}).reason,'refinement_budget');
  assert.throws(()=>runtime.queryDispersion({...cauchy,validBand:[400e-9,700e-9]},800e-9),SimulationError);
  assert.throws(()=>runtime.queryDispersion({kind:'sellmeier',terms:Array(9).fill([1,1])},550e-9),/eight/);
  assert.equal(runtime.queryDispersion({kind:'cauchy',coefficients:[-1,0,0]},550e-9).values,null);
});
