import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const settings={timeTolerance:1e-7};
function entry(r,time){
  assert.equal(r.kind,'entry_bracket');assert.equal(r.reason,'none');assert.ok(r.initialSeparationProven);
  assert.ok(r.bracket[0]<=time&&time<=r.bracket[1]);assert.ok(r.bracket[1]-r.bracket[0]<=settings.timeTolerance);
  assert.equal(r.safeUntil,r.bracket[0]);assert.equal(r.negativeWitness,r.bracket[1]);
  assert.ok(r.valueAtSafe[0]>0&&r.negativeValue[1]<0&&r.initialValue[0]>0);
}

test('actual WASM encloses accelerated plane contact with positive and negative certificates',()=>{
  const sphere={position:[0,11,0],acceleration:[0,-10,0],radius:1};
  const r=runtime.queryAcceleratedPlane(sphere,{},2,settings);entry(r,Math.SQRT2);
  const tilted=runtime.queryAcceleratedPlane({position:[0,6,8],acceleration:[0,-6,-8],radius:1},{normal:[0,3,4],offset:5.9375},2,settings);
  entry(tilted,1.25);
  const scaled=runtime.queryAcceleratedPlane({position:[0,6,8],acceleration:[0,-6,-8],radius:1},{normal:[0,24,32],offset:47.5},2,settings);
  entry(scaled,1.25);
});

test('actual WASM quartic query includes different accelerations and first entry before later exit',()=>{
  const a={position:[0,0,0],acceleration:[1,0,0],radius:1},b={position:[10,0,0],velocity:[-1,0,0],acceleration:[-1,0,0],radius:1};
  const time=(Math.sqrt(33)-1)/2;
  entry(runtime.queryAcceleratedSpheres(a,b,4,settings),time);
  entry(runtime.queryAcceleratedSpheres(b,a,4,settings),time);
  const common=s=>({...s,position:s.position.map((x,i)=>x+[100,-20,30][i]),velocity:(s.velocity??[0,0,0]).map((x,i)=>x+[7,9,-4][i]),acceleration:s.acceleration.map((x,i)=>x+[3,4,-5][i])});
  entry(runtime.queryAcceleratedSpheres(common(a),common(b),4,settings),time);
});

test('unresolved boundary, tangency and budget remain distinct from whole-horizon exclusion',()=>{
  const sphere={position:[0,3,0],acceleration:[0,-4,0],radius:1};
  const none=runtime.queryAcceleratedPlane(sphere,{},.5,settings);assert.equal(none.kind,'none');assert.equal(none.safeUntil,.5);assert.equal(none.bracket,null);
  const budget=runtime.queryAcceleratedPlane(sphere,{},2,{...settings,maxEvaluations:1});
  assert.equal(budget.kind,'unresolved');assert.equal(budget.reason,'evaluation_budget');assert.equal(budget.bracket,null);assert.equal(budget.evaluations,1);
  const boundary=runtime.queryAcceleratedPlane({...sphere,position:[0,1,0]}, {},2,settings);
  assert.equal(boundary.kind,'unresolved');assert.equal(boundary.reason,'initial_boundary');assert.equal(boundary.initialSeparationProven,false);
  const tangent=runtime.queryAcceleratedPlane({position:[0,2,0],velocity:[0,-2,0],acceleration:[0,2,0],radius:1},{},2,{...settings,maxDepth:24});
  assert.equal(tangent.kind,'unresolved');assert.equal(tangent.bracket,null);assert.equal(tangent.negativeWitness,null);
});

test('accelerated ABI failures retain prior proof and world state and allow correction',()=>{
  const world=runtime.createWorld({gravity:[0,-10,0]});
  try{
    world.addBody({id:77,position:[4,5,6]});const before=world.getBody(77),sphere={position:[0,3,0],acceleration:[0,-4,0],radius:1};
    const r=runtime.queryAcceleratedPlane(sphere,{},2,settings),packet=runtime.output();
    assert.throws(()=>runtime.queryAcceleratedPlane({...sphere,radius:0},{},2,settings),SimulationError);assert.deepEqual(runtime.output(),packet);
    assert.throws(()=>runtime.queryAcceleratedPlane(sphere,{},2,{maxEvaluations:32769}),e=>e instanceof SimulationError&&e.code===1);assert.deepEqual(runtime.output(),packet);
    assert.throws(()=>runtime.queryAcceleratedPlane({...sphere,acceleration:[0,NaN,0]},{},2),/finite/);assert.deepEqual(runtime.output(),packet);
    assert.throws(()=>runtime.queryAcceleratedPlane(sphere,{velocity:[0,1,0]},2),/static plane/);assert.deepEqual(runtime.output(),packet);
    assert.throws(()=>runtime.check(runtime.native._pp_sim_accelerated_plane(18)),SimulationError);assert.deepEqual(runtime.output(),packet);assert.equal(runtime.native._pp_sim_output_count(),21);
    const copy=runtime.queryAcceleratedPlane(sphere,{},2,settings);copy.bracket[0]=99;
    assert.deepEqual(runtime.queryAcceleratedPlane(sphere,{},2,settings),r);assert.deepEqual(world.getBody(77),before);
  }finally{world.dispose();}
});
