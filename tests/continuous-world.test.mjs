import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const near=(a,b,e=1e-10)=>assert.ok(Math.abs(a-b)<=e,`${a} != ${b}`);
function corridor(){
  const w=runtime.createWorld({gravity:[0,-9.8,0]});
  w.addBody({id:1,mass:1,radius:.5,position:[0,0,0],linearVelocity:[100,0,0],force:[0,4,0],torque:[0,0,1],inertia:[1,1,1],restitution:1,friction:0});
  w.addPlane({id:100,normal:[1,0,0],offset:-1.5,restitution:1,friction:0});w.addPlane({id:101,normal:[-1,0,0],offset:-1.5,restitution:1,friction:0});return w;
}

test('actual WASM continuous World consumes an entire multi impact tick under held loads',()=>{
  const w=corridor();try{
    const r=w.stepContinuous(.06);assert.equal(r.success,true);assert.equal(r.failure,'none');assert.equal(r.events.length,3);near(r.advancedDt,.06);near(r.time,.06);assert.equal(r.ticks,1);
    const expected=[.01,.03,.05];r.events.forEach((e,i)=>{assert.ok(Math.abs(e.respondedAt-expected[i])<1e-7);assert.ok(e.entryBracket[0]<=expected[i]+1e-7&&e.entryBracket[1]>=expected[i]-1e-7);assert.ok(e.maximumGap>0&&e.maximumGap<=1e-6);});
    const b=w.getBody(1);near(b.position[0],0,4e-6);near(b.position[1],-.01044);near(b.linearVelocity[0],-100);near(b.angularMomentum[2],.06);
    assert.deepEqual(b.force,[0,0,0]);assert.deepEqual(b.torque,[0,0,0]);
  }finally{w.dispose();}
});

test('actual WASM failed continuous tick retains complete state while exposing candidate events',()=>{
  const w=corridor();try{
    const before=w.getBody(1),info=w.info(),r=w.stepContinuous(.06,{maxEventBatches:1});
    assert.equal(r.success,false);assert.equal(r.failure,'event_budget');assert.equal(r.advancedDt,0);assert.equal(r.events.length,1);assert.ok(r.candidateTime>0);
    assert.deepEqual(w.getBody(1),before);assert.deepEqual(w.info(),info);
    const packet=runtime.output();assert.throws(()=>w.stepContinuous(.06,{queryEvaluations:32769}),SimulationError);assert.deepEqual(runtime.output(),packet);
    assert.deepEqual(w.getBody(1),before);assert.equal(w.stepContinuous(.06).success,true);
  }finally{w.dispose();}
});

test('actual WASM different external force per mass collides along an accelerated relative trajectory',()=>{
  const w=runtime.createWorld({gravity:[0,-9.8,0]});try{
    w.addBody({id:1,mass:1,radius:.5,position:[-2,0,0],force:[400,0,0],restitution:1,friction:0});
    w.addBody({id:2,mass:2,radius:.5,position:[2,0,0],force:[-800,0,0],restitution:1,friction:0});
    const r=w.stepContinuous(.1);assert.equal(r.success,true);assert.equal(r.events.length,1);
    const t=Math.sqrt(3/400),tail=.1-t,u=400*t,v=-400*t;
    near(w.getBody(1).linearVelocity[0],(-u+4*v)/3+400*tail,1e-5);
    near(w.getBody(2).linearVelocity[0],(2*u+v)/3-400*tail,1e-5);near(w.getBody(1).position[1],-.049);
  }finally{w.dispose();}
});

test('actual WASM continuous boundary/support is an explicit unsupported failure with no fallback step',()=>{
  const w=runtime.createWorld({gravity:[0,-10,0]});try{
    w.addBody({id:1,radius:.5,position:[0,.5,0],force:[0,1,0]});w.addPlane({id:100,friction:0});
    const before=w.getBody(1),r=w.stepContinuous(1/120);assert.equal(r.success,false);assert.equal(r.failure,'initial_contact');assert.equal(r.events.length,0);
    assert.deepEqual(w.getBody(1),before);assert.equal(w.info().ticks,0);w.reset();assert.throws(()=>runtime.check(runtime.native._pp_sim_world_ccd_event(w.handle,0)),SimulationError);
  }finally{w.dispose();}
});
