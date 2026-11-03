import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const near=(a,b,tolerance=1e-12)=>assert.ok(Math.abs(a-b)<=tolerance,`${a} != ${b}`);
const a={position:[-3,0,0],velocity:[1000,0,0],radius:.5},b={position:[0,0,0],velocity:[0,0,0],radius:.5};

test('actual C++ WASM finds an intermediate impact when endpoint sphere overlap misses it',()=>{
  const horizon=1/120,hit=runtime.querySphereSphere(a,b,horizon);
  assert.equal(hit.kind,'impact');near(hit.time,.002);assert.equal(hit.initialMotion,'approaching');
  assert.deepEqual(hit.normal,[1,0,0]);assert.equal(hit.normalValid,true);near(hit.initialGap,2);near(hit.initialNormalSpeed,-1000);
  assert.ok(Math.abs(a.position[0]+a.velocity[0]*horizon-b.position[0])>a.radius+b.radius);
  const short=runtime.querySphereSphere(a,b,.001);assert.equal(short.kind,'none');assert.equal(short.time,null);
  const end=runtime.querySphereSphere(a,b,.002);near(end.time,.002);assert.equal(end.atHorizon,true);
});

test('oblique contact agrees with a 3-4-5 chord and is invariant under swapping and common velocity',()=>{
  const left={...a,position:[-4,0,0]},right={...b,position:[0,.6,0]},hit=runtime.querySphereSphere(left,right,.01);
  near(hit.time,.0032);near(hit.normal[0],.8);near(hit.normal[1],.6);near(hit.normalSpeed,-800);
  const swapped=runtime.querySphereSphere(right,left,.01);near(swapped.time,hit.time);hit.normal.forEach((x,i)=>near(swapped.normal[i],-x));
  const shift=s=>({...s,position:s.position.map((x,i)=>x+[1e6,-2e6,3e6][i]),velocity:s.velocity.map((x,i)=>x+[30,-20,5][i])});
  const moving=runtime.querySphereSphere(shift(left),shift(right),.01);near(moving.time,hit.time,1e-12);moving.normal.forEach((x,i)=>near(x,hit.normal[i],1e-9));
});

test('moving plane includes plane velocity and an arbitrary unit normal',()=>{
  const sphere={position:[0,4.8,6.4],velocity:[0,-60,-80],radius:2},plane={normal:[0,.6,.8],offset:0,velocity:[0,6,8]};
  const hit=runtime.querySpherePlane(sphere,plane,.1);assert.equal(hit.kind,'impact');near(hit.time,6/110);
  hit.normal.forEach((x,i)=>near(x,plane.normal[i]));near(hit.initialGap,6);near(hit.initialNormalSpeed,-110);
  assert.equal(runtime.querySpherePlane(sphere,plane,.01).time,null);
});

test('initial events, tangency and roundoff sensitivity are explicit rather than invented contact normals',()=>{
  const overlap=runtime.querySphereSphere({...a,position:[0,0,0],velocity:[0,0,0]},b,0);
  assert.equal(overlap.kind,'initial_overlap');assert.equal(overlap.time,0);assert.equal(overlap.normalValid,false);assert.deepEqual(overlap.normal,[0,0,0]);
  const departing=runtime.querySphereSphere({...a,position:[-1,0,0],velocity:[-1,0,0]},b,1);
  assert.equal(departing.kind,'initial_touch');assert.equal(departing.initialMotion,'separating');assert.equal(departing.time,0);
  const tangent=runtime.querySphereSphere({...a,position:[-2,0,0]},{...b,position:[0,1,0]},.01);
  assert.equal(tangent.kind,'grazing');near(tangent.time,.002);assert.equal(tangent.roundoffSensitive,true);
  const ambiguous=runtime.querySphereSphere({...a,position:[-2,0,0]},{...b,position:[0,1+Number.EPSILON,0]},.01);
  assert.equal(ambiguous.kind,'uncertain');assert.equal(ambiguous.roundoffSensitive,true);
  near(ambiguous.time,.002);assert.ok(ambiguous.normal.every(Number.isFinite));
});

test('real WASM query rejection preserves outputs and world state, then permits a corrected query',()=>{
  const world=runtime.createWorld({gravity:[0,0,0]});
  try {
    world.addBody({id:77,position:[4,5,6]});const body=world.getBody(77),hit=runtime.querySphereSphere(a,b,.01),output=runtime.output();
    for(const invalid of [{...a,radius:0},{...a,radius:1e13}]){
      assert.throws(()=>runtime.querySphereSphere(invalid,b,.01),error=>error instanceof SimulationError&&error.code===4);
      assert.deepEqual(runtime.output(),output);
    }
    assert.throws(()=>runtime.querySphereSphere(a,b,-1),SimulationError);assert.deepEqual(runtime.output(),output);
    assert.throws(()=>runtime.querySphereSphere({...a,position:[0,NaN,0]},b,.01),/finite/);
    assert.deepEqual(runtime.querySphereSphere(a,b,.01),hit);assert.deepEqual(world.getBody(77),body);
    const clone=runtime.querySphereSphere(a,b,.01);clone.normal[0]=99;assert.equal(runtime.querySphereSphere(a,b,.01).normal[0],1);
  } finally {world.dispose();}
});
