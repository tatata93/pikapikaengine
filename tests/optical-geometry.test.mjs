import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const near=(a,b,e=1e-12)=>assert.ok(Math.abs(a-b)<=e,`${a} != ${b}`);
const contains=(bounds,x)=>assert.ok(bounds[0]<=x&&bounds[1]>=x,`${x} outside ${bounds}`);
const ray={origin:[0,0,-3],direction:[0,0,2],maximumParameter:10};

test('actual WASM optical disk retains parameter physical distance and enclosed normals',()=>{
  const r=runtime.queryOpticalSurface(ray,{kind:'disk',center:[0,0,0],normal:[0,0,-1],apertureRadius:1});
  assert.equal(r.status,'hit');assert.equal(r.rootCount,1);assert.equal(r.hit.frontFace,true);
  contains(r.hit.parameter,1.5);contains(r.hit.physicalDistance,3);contains(r.hit.position[2],0);contains(r.hit.geometricNormal[2],-1);
  near(r.hit.parameterEstimate,1.5);near(r.hit.physicalDistanceEstimate,3);assert.equal(r.candidates[0].state,'accepted');
  const outside=runtime.queryOpticalSurface({...ray,origin:[2,0,-3]},{kind:'disk',center:[0,0,0],apertureRadius:1});
  assert.equal(outside.status,'miss');assert.equal(outside.hit,null);assert.equal(outside.candidates[0].state,'rejected_aperture');
});

test('actual WASM cap excludes opposite hemisphere before selecting the second true root',()=>{
  const r=runtime.queryOpticalSurface({origin:[0,0,3],direction:[0,0,-1],maximumParameter:10},
    {kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:1,apertureRadius:.5});
  assert.equal(r.status,'hit');assert.equal(r.rootCount,2);assert.equal(r.consideredCount,2);
  assert.equal(r.candidates[0].state,'rejected_cap');assert.equal(r.candidates[1].state,'accepted');contains(r.hit.parameter,3);
  const sphere=runtime.queryOpticalSurface(ray,{kind:'sphere',center:[0,0,0],radius:1});
  assert.equal(sphere.status,'hit');contains(sphere.hit.parameter,1);contains(sphere.hit.physicalDistance,2);
});

test('actual WASM tangent aperture boundary and explicit self-hit cutoff remain distinct',()=>{
  const tangent=runtime.queryOpticalSurface({origin:[-2,1,0],direction:[1,0,0],maximumParameter:5},{kind:'sphere',center:[0,0,0],radius:1});
  assert.equal(tangent.status,'unresolved');assert.equal(tangent.reason,'tangent_or_discriminant');assert.equal(tangent.hit,null);
  const boundary=runtime.queryOpticalSurface({...ray,origin:[1,0,-3]},{kind:'disk',center:[0,0,0],apertureRadius:1});
  assert.equal(boundary.status,'unresolved');assert.equal(boundary.reason,'aperture_boundary');
  const surface={kind:'disk',center:[0,0,0],apertureRadius:1};
  const self=runtime.queryOpticalSurface({origin:[0,0,0],direction:[0,0,1],maximumParameter:5},surface);
  assert.equal(self.status,'hit');contains(self.hit.parameter,0);
  const cutoff=runtime.queryOpticalSurface({origin:[0,0,0],direction:[0,0,1],minimumParameter:.001,maximumParameter:5},surface);
  assert.equal(cutoff.status,'miss');assert.equal(cutoff.candidates[0].state,'rejected_parameter');
});

test('optical geometry rejection retains output and existing world state',()=>{
  const world=runtime.createWorld();try{
    world.addBody({id:91,position:[3,4,5],force:[1,2,3]});const before=world.getBody(91);
    runtime.queryOpticalSurface(ray,{kind:'sphere',center:[0,0,0],radius:1});const packet=runtime.output();
    assert.throws(()=>runtime.queryOpticalSurface(ray,{kind:'sphere',center:[0,0,0],radius:0}),SimulationError);assert.deepEqual(runtime.output(),packet);
    assert.notEqual(runtime.native._pp_sim_optical_geometry(18),0);assert.deepEqual(runtime.output(),packet);
    assert.deepEqual(world.getBody(91),before);
  }finally{world.dispose();}
});
