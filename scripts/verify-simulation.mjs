import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';

const root=fileURLToPath(new URL('../',import.meta.url));
const executable=process.argv[2]??(process.platform==='win32'?'build/native/Release/pikapika-simulation-probe.exe':'build/ci/pikapika-simulation-probe');
const manifest=JSON.parse(await readFile(path.join(root,'assets/pikapika-simulation.build.json'),'utf8'));
for(const [name,expected]of Object.entries({...manifest.sourceSha256,...Object.fromEntries(Object.entries(manifest.artifacts).map(([k,v])=>[k,v.sha256])),...manifest.licenses}))assert.equal(createHash('sha256').update(await readFile(path.join(root,name))).digest('hex'),expected,`${name} provenance`);
const probe=JSON.parse(execFileSync(path.resolve(root,executable),['--fixtures'],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:30000}));
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(path.join(root,'assets/pikapika-simulation.wasm'))),manifest}),m=runtime.native;
assert.equal(probe.apiVersion,m._pp_sim_api_version());
let values=0,maxAbsoluteError=0,maxNormalizedError=0;
function compare(actual,expected,label){
  assert.equal(actual.length,expected.length,label);
  actual.forEach((value,i)=>{assert.ok(Number.isFinite(value)&&Number.isFinite(expected[i]),label);const error=Math.abs(value-expected[i]),scale=Math.max(Math.abs(value),Math.abs(expected[i]));maxAbsoluteError=Math.max(maxAbsoluteError,error);maxNormalizedError=Math.max(maxNormalizedError,error/Math.max(1,scale));values++;assert.ok(error<=1e-8+1e-10*scale,`${label}[${i}] WASM ${value} native ${expected[i]}`);});
}
const hull=runtime.createHull(probe.mesh);
for(const [i,fixture]of probe.hydroFixtures.entries()){runtime.inputF64(fixture.input);runtime.check(m._pp_sim_hydro_query(hull.handle,16));compare(runtime.output(),fixture.output,'hydro '+i);}
const traces=[...probe.traces,...(probe.worldTraces??[])];
for(const trace of traces){
  const world=runtime.createWorld({gravity:trace.gravity});runtime.inputF64(trace.initialBody);runtime.check(m._pp_sim_world_body_add(world.handle,28));
  for(let tick=0;tick<=trace.ticks;tick++){
    runtime.check(m._pp_sim_world_body_get(world.handle,trace.initialBody[0]));compare(runtime.output(),trace.states[tick],`${trace.name} tick ${tick}`);
    if(tick===trace.ticks)break;
    if(trace.buoyancyInput){runtime.inputF64(trace.buoyancyInput);runtime.check(m._pp_sim_world_buoyancy_step(world.handle,hull.handle,trace.initialBody[0],trace.dt,1,9));}
    else runtime.check(m._pp_sim_world_step(world.handle,trace.dt,1));
  }
  world.dispose();
}
hull.dispose();
assert.ok(probe.toiFixtures?.length>=12,'Native probe must include linear continuous-query fixtures');
for(const fixture of probe.toiFixtures){
  runtime.inputF64(fixture.input);runtime.check(fixture.type==='sphere_plane'?m._pp_sim_sphere_plane_toi(15):m._pp_sim_sphere_sphere_toi(15));
  const actual=runtime.output();compare(actual,fixture.output,'TOI '+fixture.name);
  for(const i of [0,1,2,7,8,9])assert.equal(actual[i],fixture.output[i],`TOI ${fixture.name} exact tag ${i}`);
}
const report={verification:'Common C++ native-WebAssembly parity',compiler:manifest.compiler,wasmBytes:runtime.wasmBytes,staticCases:probe.hydroFixtures.length,traces:traces.map(t=>({name:t.name,ticks:t.ticks,dt:t.dt})),toiCases:probe.toiFixtures.map(t=>t.name),numericalValues:values,maxAbsoluteError,maxNormalizedError,tolerance:'abs 1e-8 + relative 1e-10; TOI enum/flags exact; analytical correctness is tested separately',memoryBytes:runtime.diagnostics.memoryBytes};
if(process.argv[3])await writeFile(path.resolve(root,process.argv[3]),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
