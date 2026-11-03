import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const near=(a,b,e=1e-12)=>assert.ok(Math.abs(a-b)<=e,`${a} != ${b}`);

test('actual WASM polarized normal reflection retains signed amplitudes and frame reversal',()=>{
  const r=runtime.queryPolarizedInterface({power:[1,0,1,0]});assert.equal(r.failure,'none');
  near(r.reflected.power[0],.04);near(r.reflected.power[2],-.04);near(r.transmitted.power[0],.96);near(r.transmitted.power[2],.96);
  near(r.reflected.amplitudeS[0],-.2);near(r.reflected.amplitudeP[0],.2);
  near(r.inputFrame.second[2],1);near(r.reflected.frame.second[2],-1);near(r.vacuumWavelength,550e-9);
});

test('actual WASM TIR retains exact-reference relative phase without a propagating transmitted branch',()=>{
  const r=runtime.queryPolarizedInterface({incident:[.8,-.6,0],indexIncident:1.5,indexTransmitted:1,transverseReference:[0,0,-1],power:[1,0,1,0]});
  assert.equal(r.interfaceKind,'total_internal_reflection');assert.equal(r.failure,'none');assert.equal(r.transmitted,null);
  near(r.reflected.power[0],1);near(r.reflected.power[2],53/75);near(r.reflected.power[3],16*Math.sqrt(11)/75);
  near(r.reflected.amplitudeS[0],37/125);near(r.reflected.amplitudeP[0],-7/15);assert.ok(r.discriminant[1]<0);
});

test('actual WASM repeated Brewster reflections preserve generated polarization',()=>{
  const input={incident:[1.5,-1,0],transverseReference:[0,0,-1]};const first=runtime.queryPolarizedInterface(input),beam=first.reflected;
  const ci=1/Math.sqrt(3.25),si=1.5*ci,d=beam.frame.direction,p=beam.frame.second;
  const normal=d.map((x,i)=>-ci*x+si*p[i]);
  const second=runtime.queryPolarizedInterface({incident:d,normal,transverseReference:beam.frame.first,power:beam.power});
  assert.equal(second.failure,'none');near(second.reflected.power[0],(25/169)**2/2);
  const crossed=d.map((x,i)=>-ci*x+si*beam.frame.first[i]);
  const extinguished=runtime.queryPolarizedInterface({incident:d,normal:crossed,transverseReference:beam.frame.first,power:beam.power});
  assert.equal(extinguished.failure,'none');assert.ok(extinguished.reflected.power[0]<1e-28);
});

test('polarized uncertainty and invalid states retain explicit absent outputs',()=>{
  const r=runtime.queryPolarizedInterface({incident:[3,-4,0],indexIncident:5,indexTransmitted:3});
  assert.equal(r.failure,'interface_uncertain');assert.equal(r.reflected,null);assert.equal(r.transmitted,null);assert.equal(r.interfaceUncertainty,'critical_angle');
  const plane=runtime.queryPolarizedInterface({incident:[1e-10,-1,0]});
  assert.equal(plane.failure,'incidence_plane_uncertain');assert.equal(plane.reflected,null);assert.equal(plane.transmitted,null);
  const packet=runtime.output();assert.throws(()=>runtime.queryPolarizedInterface({power:[1,2,0,0]}),SimulationError);assert.deepEqual(runtime.output(),packet);
  assert.notEqual(runtime.native._pp_sim_polarized_interface(15),0);assert.deepEqual(runtime.output(),packet);
});
