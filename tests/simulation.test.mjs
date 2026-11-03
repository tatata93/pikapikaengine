import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createBoxMesh} from '../engine/mesh.mjs';
import {hydrostaticForces} from '../engine/hydrostatics.mjs';
import {loadSimulationRuntime,createFloatSimulation,SimulationError} from '../engine/simulation.mjs';
const wasmBytes=new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)));
const manifest=JSON.parse(await readFile(new URL('../assets/pikapika-simulation.build.json',import.meta.url),'utf8'));
const runtime=await loadSimulationRuntime({wasmBytes,manifest});
const near=(a,b,tolerance=1e-8)=>assert.ok(Math.abs(a-b)<=tolerance,`${a} versus ${b}`);

test('actual simulation WASM, authored sources and bundled notices match their recorded provenance',async()=>{
  assert.equal(runtime.native._pp_sim_api_version(),1);assert.equal(manifest.sdkVersion,'6.0.13');
  for(const [name,expected]of Object.entries({...manifest.sourceSha256,...Object.fromEntries(Object.entries(manifest.artifacts).map(([k,v])=>[k,v.sha256])),...manifest.licenses}))assert.equal(createHash('sha256').update(await readFile(new URL('../'+name,import.meta.url))).digest('hex'),expected,name);
  assert.equal(runtime.diagnostics.wasmBytes,wasmBytes.byteLength);assert.equal(runtime.diagnostics.memoryBytes,manifest.memory.initialBytes);
});
test('generic WASM worlds expose exact free fall and isolated elastic sphere impulses',()=>{
  const world=runtime.createWorld({gravity:[0,-10,0]});
  try{world.addBody({id:42,position:[0,100,0]});world.step(.01,32);const state=world.getBody(42);near(state.position[1],100-5*.32**2);near(state.linearVelocity[1],-3.2);assert.equal(state.ticks,32);
    for(const id of [42.9,NaN,Infinity,0,-1,Number.MAX_SAFE_INTEGER+1])assert.throws(()=>world.getBody(id),/Body ID/);
    assert.deepEqual(world.getBody(42),state);
    world.addBody({id:4294967338,position:[50,100,0]});assert.equal(world.getBody(4294967338).id,4294967338);
    assert.deepEqual(world.getBody(42),state);
    world.reset();world.setGravity([0,0,0]);
    world.addBody({id:1,radius:.5,position:[-.5,0,0],linearVelocity:[1,0,0],restitution:1,friction:0});world.addBody({id:2,radius:.5,position:[.5,0,0],linearVelocity:[-1,0,0],restitution:1,friction:0});
    assert.equal(world.step(.01).contacts,1);const a=world.getBody(1),b=world.getBody(2);near(a.linearVelocity[0],-1);near(b.linearVelocity[0],1);near(a.kineticEnergy+b.kineticEnergy,1);
  }finally{world.dispose();}
});
test('C++ exceptions cross the real WASM boundary as diagnostics and rejected batches preserve state',()=>{
  const world=runtime.createWorld({gravity:[0,0,0]});
  try{
    assert.throws(()=>world.addBody({id:1,mass:-1}),error=>error instanceof SimulationError&&error.code===4);
    assert.equal(world.info().bodies,0);world.addBody({id:1,inertia:[1,1,1],angularMomentum:[0,0,10],force:[2,0,0]});const before=world.getBody(1);
    assert.throws(()=>world.step(.1,2),SimulationError);assert.deepEqual(world.getBody(1),before);
    assert.throws(()=>world.step(.01,1.5),/complete ticks/);assert.deepEqual(world.getBody(1),before);
    world.step(.001);assert.equal(world.getBody(1).ticks,1);assert.deepEqual(world.getBody(1).force,[0,0,0]);
  }finally{world.dispose();}
});
test('prepared WASM hull queries match pressure integration and rejected replacement keeps geometry',()=>{
  const mesh=createBoxMesh([2,4,6]),hull=runtime.createHull(mesh),options={position:[1,.5,2],orientation:[0,0,Math.sin(.1),Math.cos(.1)],centerOfMass:[2,1,3],gravity:10};
  try{
    const actual=hull.query(options),expected=hydrostaticForces(mesh,options);
    for(const key of ['force','torque'])for(let i=0;i<3;i++)near(actual[key][i],expected[key][i]);near(actual.submergedVolume,expected.submergedVolume);
    const broken=structuredClone(mesh);broken.triangles.pop();assert.throws(()=>hull.replace(broken),SimulationError);assert.deepEqual(hull.query(options),actual);
    const copy=hull.source;copy.positions[0][0]=999;assert.deepEqual(hull.query(options),actual);
  }finally{hull.dispose();}
  assert.throws(()=>hull.query(),/disposed/);hull.dispose();
});
test('repeated WASM resource lifetime and copied snapshots remain reusable without stale aliases',async()=>{
  const initialMemory=runtime.diagnostics.memoryBytes;
  for(let i=0;i<256;i++){const world=runtime.createWorld();world.addBody({id:1});const copy=world.getBody(1);copy.position[0]=999;assert.equal(world.getBody(1).position[0],0);world.dispose();assert.throws(()=>world.info(),/disposed/);world.dispose();}
  assert.equal(runtime.diagnostics.memoryBytes,initialMemory,'this bounded workload fits the initial heap; memory shrink is not implied');
  const sim=await createFloatSimulation({wasmBytes});const before=sim.snapshot();assert.throws(()=>sim.reset('unknown'),/Unknown/);assert.deepEqual(sim.snapshot(),before);sim.dispose();assert.throws(()=>sim.step(),/disposed/);
});
