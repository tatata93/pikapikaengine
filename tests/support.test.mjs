import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const near=(a,b,e=1e-7)=>assert.ok(Math.abs(a-b)<=e,`${a} != ${b}`);
function ground(){const w=runtime.createWorld({gravity:[0,-10,0]});w.addPlane({id:100});w.addBody({id:1,radius:.5,mass:2,position:[0,.5,0],linearVelocity:[3,0,0],angularMomentum:[0,0,-.6],force:[0,2,0],torque:[1,2,3]});return w;}
test('actual WASM normal support returns 18N without consuming loads changing spin or advancing time',()=>{
  const w=ground();try{const before=w.getBody(1),info=w.info(),r=w.querySupport();assert.equal(r.success,true);assert.equal(r.constraints.length,1);near(r.constraints[0].lambda,18);
    assert.equal(r.constraints[0].guardedGeometry,true);assert.deepEqual(r.bodies[0].normalTorque,[0,0,0]);near(r.bodies[0].acceleration[1],0);
    assert.deepEqual(w.getBody(1),before);assert.deepEqual(w.info(),info);assert.equal(r.queryTime,0);assert.equal(r.queryTicks,0);
  }finally{w.dispose();}
});
test('actual WASM loaded stack solves coupled normal reaction and bounded iteration failure can retry',()=>{
  const w=runtime.createWorld({gravity:[0,-10,0]});try{w.addPlane({id:100});for(const [id,mass,force]of [[1,1,5],[2,2,-4],[3,3,7]])w.addBody({id,mass,radius:.5,position:[0,id-.5,0],force:[0,force,0]});
    const before=[1,2,3].map(id=>w.getBody(id));const fail=w.querySupport({maxIterations:1});assert.equal(fail.success,false);assert.equal(fail.failure,'iteration_budget');assert.deepEqual([1,2,3].map(id=>w.getBody(id)),before);
    const r=w.querySupport();assert.equal(r.success,true);assert.equal(r.constraints.length,3);for(const [j,force]of [52,47,23].entries())near(r.constraints[j].lambda,force);
    assert.ok(r.residuals.complementarity<=1e-7);assert.deepEqual([1,2,3].map(id=>w.getBody(id)),before);
  }finally{w.dispose();}
});
test('actual WASM tiny impact and separating contact are distinct from resting support',()=>{
  const w=ground();try{const b=w.getBody(1);w.setBody({...b,linearVelocity:[0,-1e-20,0]});const before=w.getBody(1),fail=w.querySupport();assert.equal(fail.success,false);assert.equal(fail.failure,'impact_required');assert.deepEqual(w.getBody(1),before);
    w.setBody({...b,linearVelocity:[0,1e-20,0]});const r=w.querySupport();assert.equal(r.success,true);assert.equal(r.constraints[0].phase,'separating');near(r.constraints[0].lambda,0);near(r.constraints[0].normalAcceleration,-9);
    assert.throws(()=>w.querySupport({maxContacts:257}),SimulationError);
  }finally{w.dispose();}
});
test('actual WASM guarded positive gap and singular duplicate are explicit',()=>{
  const w=ground();try{const b=w.getBody(1);w.setBody({...b,position:[0,.5+1e-9,0]});const r=w.querySupport();assert.equal(r.success,true);assert.ok(r.constraints[0].gap[0]>0);assert.ok(r.maximumGeometryOffset>0);near(r.constraints[0].lambda,18);
    w.addPlane({id:101});const fail=w.querySupport();assert.equal(fail.success,false);assert.equal(fail.failure,'ill_conditioned');
  }finally{w.dispose();}
});
