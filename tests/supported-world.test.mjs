import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
test('supported JS API rolls back a failed tick including held loads and retries on the same World',()=>{
  const w=runtime.createWorld({gravity:[0,-10,0]});try{
    w.addBody({id:1,mass:1,radius:.5,position:[0,.5,0],force:[2,0,0],torque:[0,0,1],friction:0});w.addPlane({id:100,friction:0});
    const before={info:w.info(),body:w.getBody(1)};const fail=w.stepSupported(.1,{maxSegments:1});assert.equal(fail.success,false);assert.equal(fail.failure,'segment_budget');assert.equal(fail.advancedDt,0);assert.deepEqual({info:w.info(),body:w.getBody(1)},before);
    const pass=w.stepSupported(.1);assert.equal(pass.success,true);assert.equal(pass.ticks,1);assert.ok(Math.abs(w.getBody(1).position[0]-.01)<1e-9);assert.deepEqual(w.getBody(1).force,[0,0,0]);assert.deepEqual(w.getBody(1).torque,[0,0,0]);assert.equal(fail.success,false,'returned failed snapshot remains owned');
  }finally{w.dispose();}
});
test('supported event arrays are copied snapshots and reset clears the native record',()=>{
  const w=runtime.createWorld({gravity:[0,0,0]});try{
    w.addBody({id:1,mass:1,radius:.5,position:[-2,0,0],linearVelocity:[1000,0,0],restitution:1,friction:0});w.addBody({id:2,mass:1,radius:.5,position:[2,0,0],linearVelocity:[-1000,0,0],restitution:1,friction:0});
    const r=w.stepSupported(1/120);assert.equal(r.success,true);const copy=structuredClone(r);assert.ok(r.events.some(x=>x.kind==='impact'&&Math.abs(x.at-.0015)<2e-9));w.getBody(1);w.querySupport();assert.deepEqual(r,copy);
    assert.throws(()=>w.stepSupported(.01,{maximumSubstep:NaN}),/finite/);assert.deepEqual(r,copy);runtime.check(runtime.native._pp_sim_world_supported_event(w.handle,0));assert.equal(runtime.output()[0],0);
    w.reset();assert.notEqual(runtime.native._pp_sim_world_supported_event(w.handle,0),0);assert.deepEqual(r,copy);
  }finally{w.dispose();}
});
test('supported normal-only profile rejects nonzero friction without advancing the World',()=>{
  const w=runtime.createWorld();try{w.addBody({id:1,position:[0,2,0],friction:.5});const before=w.getBody(1);const r=w.stepSupported(1/120);assert.equal(r.failure,'invalid_input');assert.equal(r.success,false);assert.equal(w.info().ticks,0);assert.deepEqual(w.getBody(1),before);}finally{w.dispose();}
});
test('supported cold input tiny closing speed retains Newton restitution without a magnitude threshold',()=>{
  const w=runtime.createWorld({gravity:[0,0,0]});try{
    w.addBody({id:1,mass:1,radius:.5,position:[0,.5,0],linearVelocity:[0,-1e-20,0],restitution:1,friction:0});w.addPlane({id:100,restitution:1,friction:0});
    const r=w.stepSupported(1/120);assert.equal(r.success,true);assert.ok(Math.abs(w.getBody(1).linearVelocity[1]-1e-20)<1e-30);assert.equal(r.events[0].kind,'velocity_repair');
  }finally{w.dispose();}
});
