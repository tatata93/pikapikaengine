import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const near=(a,b,e=1e-12)=>assert.ok(Math.abs(a-b)<=e,`${a} != ${b}`);

test('actual WASM interface returns known normal-incidence and 3-4-5 Snell directions',()=>{
  const normal=runtime.queryDielectricInterface();assert.equal(normal.kind,'transmission');assert.ok(normal.discriminant[0]>0&&normal.incidentDot[1]<0);
  for(const k of ['reflectanceS','reflectanceP','reflectanceUnpolarized'])near(normal.power[k],.04);
  for(const k of ['transmittanceS','transmittanceP','transmittanceUnpolarized'])near(normal.power[k],.96);
  assert.deepEqual(normal.reflected,[0,1,0]);assert.deepEqual(normal.transmitted,[0,-1,0]);near(normal.vacuumWavelength,550e-9);
  const r=runtime.queryDielectricInterface({incident:[3,-4,0]});near(r.reflected[0],.6);near(r.reflected[1],.8);near(r.transmitted[0],.4);near(r.transmitted[1],-Math.sqrt(.84));
});

test('actual WASM Brewster and reciprocal paths agree with independent Fresnel cases',()=>{
  const r=runtime.queryDielectricInterface({incident:[1.5,-1,0]});near(r.power.reflectanceP,0,1e-28);near(r.power.reflectanceS,25/169);near(r.power.transmittanceS,144/169);
  const f=runtime.queryDielectricInterface({incident:[3,-4,0]});
  const back=runtime.queryDielectricInterface({incident:f.transmitted.map(x=>-x),normal:[0,-1,0],indexIncident:1.5,indexTransmitted:1});
  back.transmitted.forEach((x,i)=>near(x,-f.incidentUnit[i]));near(back.power.reflectanceS,f.power.reflectanceS);near(back.power.reflectanceP,f.power.reflectanceP);
  const wavelength=runtime.queryDielectricInterface({incident:[3,-4,0],vacuumWavelength:450e-9});assert.deepEqual(wavelength.power,f.power);assert.deepEqual(wavelength.transmitted,f.transmitted);near(wavelength.vacuumWavelength,450e-9);
});

test('actual WASM critical certificates keep uncertain output distinct from total reflection',()=>{
  const tir=runtime.queryDielectricInterface({incident:[4,-3,0],indexIncident:1.5,indexTransmitted:1});
  assert.equal(tir.kind,'total_internal_reflection');assert.ok(tir.discriminant[1]<0);assert.equal(tir.transmitted,null);assert.equal(tir.cosineTransmitted,null);near(tir.power.reflectanceS,1);near(tir.power.transmittanceS,0);
  const critical=runtime.queryDielectricInterface({incident:[3,-4,0],indexIncident:5,indexTransmitted:3});
  assert.equal(critical.kind,'uncertain');assert.equal(critical.uncertainty,'critical_angle');assert.ok(critical.discriminant[0]<=0&&critical.discriminant[1]>=0);
  assert.equal(critical.transmitted,null);assert.equal(critical.power,null);assert.equal(critical.cosineTransmitted,null);
  const side=runtime.queryDielectricInterface({incident:[1,1,0],normal:[1,-1,0],indexIncident:1,indexTransmitted:1});
  assert.equal(side.kind,'uncertain');assert.equal(side.uncertainty,'incident_side');assert.equal(side.power,null);
  const homogeneous=runtime.queryDielectricInterface({incident:[3,-4,0],indexIncident:1,indexTransmitted:1});near(homogeneous.power.transmittanceS,1);assert.deepEqual(homogeneous.transmitted,homogeneous.incidentUnit);
  const grazing=runtime.queryDielectricInterface({incident:[1,0,0],indexIncident:1,indexTransmitted:1});
  assert.equal(grazing.exactGrazing,true);assert.notEqual(grazing.cosineTransmitted,null);near(grazing.cosineTransmitted,0);near(grazing.power.transmittanceP,1);
});

test('optical input rejection retains prior output and never changes a world',()=>{
  const world=runtime.createWorld();
  try{
    world.addBody({id:77,position:[3,4,5]});const before=world.getBody(77),r=runtime.queryDielectricInterface(),packet=runtime.output();
    assert.throws(()=>runtime.queryDielectricInterface({incident:[0,1,0]}),SimulationError);assert.deepEqual(runtime.output(),packet);
    assert.throws(()=>runtime.queryDielectricInterface({indexIncident:0}),SimulationError);assert.deepEqual(runtime.output(),packet);
    assert.throws(()=>runtime.queryDielectricInterface({normal:[0,NaN,0]}),/finite/);assert.deepEqual(runtime.output(),packet);
    assert.notEqual(runtime.native._pp_sim_dielectric_interface(8),0);assert.deepEqual(runtime.output(),packet);
    assert.deepEqual(runtime.queryDielectricInterface(),r);assert.deepEqual(world.getBody(77),before);
    r.power.reflectanceS=99;near(runtime.queryDielectricInterface().power.reflectanceS,.04);
  }finally{world.dispose();}
});
