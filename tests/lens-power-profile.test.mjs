import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createLensPowerProfile,serializeLensPowerProfile,parseLensPowerProfile,createLensPowerNodes,createLensPowerPaths,evaluateLensPowerProfile} from '../engine/polarized-camera.mjs';
const copy=x=>JSON.parse(JSON.stringify(x));
function exact(x){const data=new DataView(new ArrayBuffer(8));data.setFloat64(0,x);const bits=data.getBigUint64(0),sgn=bits>>63n?-1n:1n,e=Number(bits>>52n&2047n),m=(bits&((1n<<52n)-1n))+(e?1n<<52n:0n),shift=e?e-1023-52:-1074;return shift>=0?{n:sgn*(m<<BigInt(shift)),d:1n}:{n:sgn*m,d:1n<<BigInt(-shift)};}
const exactEqual=(a,b)=>assert.equal(a.n*b.d,b.n*a.d);
const encloses=(a,x)=>assert.ok(a[0]<=x&&x<=a[1],`${a} does not enclose ${x}`);

test('finite POWER profile roundtrip preserves source sensor material wavelengths and explicit settings without aliases',()=>{
  const p=createLensPowerProfile({powerWatts:.12345678912345678,source:{direction:[.125,-.25,2],transverseReference:[0,1,0]},sensor:{center:[.01,-.02,.073],apertureRadius:.003},wavelengths:[500e-9],settings:{maximumPacketEvaluations:7,maximumRouteSteps:4},material:{coefficients:[1.51,2e-15,0]}});
  assert.deepEqual(parseLensPowerProfile(serializeLensPowerProfile(p)),p);const q=createLensPowerProfile(p);q.source.direction[0]=99;q.sensor.center[0]=99;q.material.coefficients[0]=99;q.wavelengths[0]=99;assert.equal(p.source.direction[0],.125);assert.equal(p.sensor.center[0],.01);assert.equal(p.material.coefficients[0],1.51);assert.equal(p.wavelengths[0],500e-9);
  assert.equal(createLensPowerProfile().powerWatts,1);assert.equal(createLensPowerProfile().kind,'synthetic-biconvex-finite-power');
});

test('power-of-two packet division exactly preserves binary64 total watts and strict pure-state cones',()=>{
  for(const radialSamples of [1,2,4,8,16])for(const angularSamples of [4,8,16,32,64])for(const powerWatts of [1e-6,.12345678912345678,1,1e6]){
    const nodes=createLensPowerNodes({radialSamples,angularSamples,powerWatts}),n=nodes.length,packet=exact(nodes[0].power[0]);assert.equal(n,radialSamples*angularSamples);exactEqual({n:packet.n*BigInt(n),d:packet.d},exact(powerWatts));assert.ok(nodes.every(node=>node.power[0]===nodes[0].power[0]));
  }
  for(const stokes of ['unpolarized','q_plus','q_minus','u_plus','u_minus','v_plus','v_minus']){
    const nodes=createLensPowerNodes({stokes,powerWatts:123.456});for(const {power:[i,q,u,v]}of nodes){const squared=[i,q,u,v].map(x=>{const f=exact(x);return {n:f.n*f.n,d:f.d*f.d};});if(stokes!=='unpolarized'){const component=squared.slice(1).find(x=>x.n!==0n);exactEqual(squared[0],component);}else assert.deepEqual([q,u,v],[0,0,0]);}
  }
});

test('pupil coordinates are original paired rounded nodes and aperture changes do not invent source watts',()=>{
  const p=createLensPowerProfile(),nodes=createLensPowerNodes(p),n=nodes.length;assert.equal(n,64);
  for(let i=0;i<n;i+=2){assert.equal(nodes[i].position[0],-nodes[i+1].position[0]);assert.equal(nodes[i].position[1],-nodes[i+1].position[1]);assert.equal(nodes[i].position[2],-.01);}
  const meanR2=nodes.reduce((sum,node)=>sum+node.position[0]**2+node.position[1]**2,0)/n;assert.ok(Math.abs(meanR2-p.apertureRadius**2/2)<1e-19);
  const wider=createLensPowerNodes({...p,apertureRadius:.01});assert.deepEqual(wider.map(x=>x.power),nodes.map(x=>x.power));assert.notDeepEqual(wider.map(x=>x.position),nodes.map(x=>x.position));
});

test('unknown fields and incompatible source sample counts watt ranges sensor and budget values reject',()=>{
  for(const input of [{version:2},{kind:'other'},{unknown:1},{powerWatts:0},{powerWatts:1e7},{powerWatts:'1'},{radialSamples:3},{angularSamples:10},{radialSamples:32},{stokes:'angle'},{source:{kind:'finite'}},{source:{direction:[0,0,0]}},{source:{direction:[0,0,1],extra:1}},{sensor:{center:[0,0,.004]}},{sensor:{apertureRadius:0}},{material:{kind:'sellmeier'}},{wavelengths:[900e-9]},{wavelengths:[]},{settings:{maximumSteps:1}},{settings:{maximumRouteSteps:1.5}},{settings:{maximumTotalSqrtRefinements:0}},{settings:{powerMaxSqrtRefinements:257}},{settings:{maximumPackets:1025}}])assert.throws(()=>createLensPowerProfile(input),JSON.stringify(input));
  assert.throws(()=>parseLensPowerProfile('{invalid'));assert.throws(()=>createLensPowerPaths({},[0,1]));
});

test('explicit primary and first internal ghost itineraries preserve the full phase index and all self-root domains',()=>{
  const paths=createLensPowerPaths({},[1.49,1.51]);assert.deepEqual(paths.map(p=>p.id),['primary','ghost']);assert.deepEqual(paths[0].steps.map(s=>s.branch),['transmitted','transmitted']);assert.deepEqual(paths[1].steps.map(s=>s.branch),['transmitted','reflected','reflected','transmitted']);
  assert.deepEqual(paths[1].steps.map(s=>s.surface.vertex[2]),[0,.005,0,.005]);for(const path of paths){assert.deepEqual(path.steps[0].nextIndex,[1.49,1.51]);assert.ok(path.steps.slice(1).every(s=>s.nextIndex===1));assert.ok(path.steps.every(s=>s.minimumParameter===0&&s.maximumParameter===1e6));}
});

// Scripted runtime checks forwarding and scheduling, not optical physics.
function fixtureRuntime(){const launches=[],calls=[],dispersion=[];return {launches,calls,dispersion,diagnostics:{backend:'scripted fixture, not physics'},phase:[1.49,1.51],makeOpticalLaunchRay(source,position){launches.push(copy({source,position}));return {origin:position.map(x=>[x,x]),direction:source.direction.map(x=>[x,x]),minimumParameter:0,maximumParameter:1e6};},queryDispersion(model,wavelength,settings){dispersion.push(copy({model,wavelength,settings}));return this.phase?{status:'resolved',values:{withinInterfaceDomain:true,phase:[...this.phase]}}:{status:'unresolved',values:null};},queryPolarizedPacket(input,settings){calls.push(copy({input,settings}));return {status:'fixture_not_a_physical_result',records:[],stats:null};}};}

test('profile evaluation dispatches unchanged packet watts and phase intervals independently for each path and wavelength',async()=>{
  const r=fixtureRuntime(),p=createLensPowerProfile({powerWatts:2,radialSamples:2,angularSamples:8}),progress=[];let yields=0;
  const out=await evaluateLensPowerProfile(r,p,{onProgress:x=>progress.push(x),yieldControl:async()=>{++yields;}});assert.equal(r.launches.length,16);assert.equal(r.calls.length,6);assert.equal(r.dispersion.length,3);assert.equal(out.channels.length,3);assert.equal(progress.at(-1).completed,progress.at(-1).total);assert.ok(yields>=7);
  for(const call of r.calls){assert.deepEqual(call.input.packets.map(x=>x.power[0]),Array(16).fill(.125));assert.deepEqual(call.input.steps[0].nextIndex,[1.49,1.51]);assert.deepEqual(call.input.sensor.center,p.sensor.center);assert.equal(call.settings.maximumRouteSteps,64);assert.equal(call.settings.powerMaxSqrtRefinements,128);assert.equal(call.input.index,1);}
  assert.deepEqual(r.calls[0].input.packets,r.calls[5].input.packets);assert.equal(Object.hasOwn(out,'totalDetectedPower'),false);assert.equal(Object.hasOwn(out.channels[0],'totalDetectedPower'),false);assert.deepEqual(out.profile,p);
});

test('unresolved dispersion skips physical batches without creating zero tallies; missing API and cancellation do not fall back',async()=>{
  const r=fixtureRuntime();r.phase=null;const out=await evaluateLensPowerProfile(r,{});assert.equal(r.calls.length,0);for(const c of out.channels){assert.equal(c.index,null);assert.deepEqual(c.paths.map(p=>p.result),[null,null]);}
  await assert.rejects(evaluateLensPowerProfile({},{}),/API unavailable/);const aborter=new AbortController();aborter.abort();await assert.rejects(evaluateLensPowerProfile(fixtureRuntime(),{},{signal:aborter.signal}),{name:'AbortError'});
  const r2=fixtureRuntime(),controller=new AbortController();await assert.rejects(evaluateLensPowerProfile(r2,{},{signal:controller.signal,onProgress:()=>controller.abort()}),{name:'AbortError'});assert.equal(r2.calls.length,0);
});

let runtime;async function actual(){if(!runtime)runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});return runtime;}
test('actual WASM lens profile preserves explicit watts across independent primary and internal-ghost results',async()=>{
  const p=createLensPowerProfile({apertureRadius:.0001,radialSamples:1,angularSamples:4,wavelengths:[550e-9]}),out=await evaluateLensPowerProfile(await actual(),p),paths=out.channels[0].paths;
  assert.match(out.diagnostics.backend,/C\+\+ WebAssembly/);assert.deepEqual(paths.map(x=>x.id),['primary','ghost']);for(const path of paths){assert.equal(path.result.status,'completed');assert.ok(path.result.stats);encloses(path.result.stats.totalSourcePower,1);assert.ok(path.result.stats.detectedPower[0]>=0);assert.ok(path.result.stats.detectedPower[1]<=1);assert.equal(path.result.records.length,4);for(const record of path.result.records){assert.equal(record.power[0],.25);if(record.status==='accepted')assert.deepEqual(record.sensorPower,record.route.completion.state.power);}}
  assert.ok(paths[0].result.stats.detectedPower[0]>paths[1].result.stats.detectedPower[1]);assert.equal(Object.hasOwn(out,'detectedPower'),false);
});
test('actual WASM packet budgets retain original watts and prohibit an incomplete final tally',async()=>{
  const p=createLensPowerProfile({apertureRadius:.0001,radialSamples:1,angularSamples:4,wavelengths:[550e-9],settings:{maximumPacketEvaluations:1}}),out=await evaluateLensPowerProfile(await actual(),p);
  for(const path of out.channels[0].paths){assert.equal(path.result.status,'budget_exceeded');assert.equal(path.result.stats,null);assert.equal(path.result.records.length,4);assert.ok(path.result.records.filter(x=>x.status==='not_examined').length>=3);assert.ok(path.result.records.every(x=>x.power[0]===.25));}
});
