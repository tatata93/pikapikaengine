import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const enclosed=(bound,x)=>assert.ok(bound[0]<=x&&x<=bound[1],`${x} outside ${bound}`);
const disk=(z,normal=[0,0,-1])=>({kind:'disk',center:[0,0,z],normal,apertureRadius:10});
test('actual WASM bounded ray retains nonzero origin and direction families at a plane',()=>{
  const r=runtime.queryBoundedSurface({origin:[0,0,[-3.1,-2.9]],direction:[0,0,[1,2]]},disk(0));
  assert.equal(r.status,'hit');enclosed(r.hit.parameter,1.45);enclosed(r.hit.parameter,3.1);assert.ok(r.hit.position[2].every(x=>x===0),'signed-zero endpoints both represent the exact plane');
  assert.equal('positionEstimate' in r.hit,false);enclosed(r.hit.incidentNormal[2],-1);
  const bad=runtime.queryBoundedSurface({origin:[0,0,-3],direction:[0,0,[-1,1]]},disk(0));assert.equal(bad.status,'unresolved');assert.equal(bad.hit,null);
});
test('actual WASM independent index families enclose normal Fresnel without same-band shortcut',()=>{
  const r=runtime.queryBoundedInterface({incident:[0,0,[1,2]],normal:[0,0,-1],indexIncident:1,indexTransmitted:[1.4,1.6]});
  assert.equal(r.kind,'transmission');enclosed(r.power.reflectanceS,1/36);enclosed(r.power.reflectanceS,9/169);
  enclosed(r.transmitted[2],1);enclosed(r.reflected[2],-1);
  const sameBands=runtime.queryBoundedInterface({incident:[0,0,1],normal:[0,0,-1],indexIncident:[1,2],indexTransmitted:[1,2]});
  assert.ok(sameBands.power===null||sameBands.power.reflectanceS[1]>0,'equal independent intervals are not identical media');
});
test('actual WASM geometry and Snell carry complete boxes into a second surface',()=>{
  const first=runtime.queryBoundedSurface({origin:[[.1,.2],0,[-3.1,-2.9]],direction:[0,0,[1,2]]},disk(0));assert.equal(first.status,'hit');
  const bend=runtime.queryBoundedInterface({incident:[0,0,[1,2]],normal:first.hit.incidentNormal,indexIncident:1,indexTransmitted:[1.4,1.6]});assert.equal(bend.kind,'transmission');
  const next=runtime.queryBoundedSurface({origin:first.hit.position,direction:bend.transmitted},disk(2));assert.equal(next.status,'hit');
  enclosed(next.hit.position[0],.1);enclosed(next.hit.position[0],.2);assert.deepEqual(next.hit.position[2],[2,2]);
});
test('actual WASM phase-index enclosure is passed whole into refraction and critical families fail',()=>{
  const dispersion=runtime.queryDispersion({kind:'cauchy',coefficients:[1.5,2**-44,0]},2**-20);assert.equal(dispersion.status,'resolved');
  const r=runtime.queryBoundedInterface({indexTransmitted:dispersion.values.phase,vacuumWavelength:2**-20});assert.equal(r.kind,'transmission');assert.equal(r.vacuumWavelength,2**-20);
  enclosed(r.power.reflectanceS,(9/41)**2);
  const critical=runtime.queryBoundedInterface({incident:[4,0,3],normal:[0,0,-1],indexIncident:[1.2,1.3],indexTransmitted:1});
  assert.equal(critical.kind,'unresolved');assert.equal(critical.reason,'critical_angle');assert.equal(critical.reflected,null);assert.equal(critical.transmitted,null);assert.equal(critical.power,null);
  assert.throws(()=>runtime.queryBoundedInterface({indexIncident:[0,1]}),SimulationError);
  assert.throws(()=>runtime.queryBoundedSurface({origin:[0,0,0],direction:[0,0,[2,1]]},disk(2)),/ordered/);
});
