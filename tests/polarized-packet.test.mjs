import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const disk=(z,r=10,normal=[0,0,-1])=>({kind:'disk',center:[0,0,z],normal,apertureRadius:r});
const packet=(i=.25,x=0)=>({ray:{origin:[x,0,0],direction:[0,0,1],maximumParameter:100},power:[i,0,0,i],transverseReference:[1,0,0]});
const plate=[{surface:disk(1),nextIndex:1.5},{surface:disk(2),nextIndex:1}];
const input=(packets=[packet(),packet(.75)],steps=plate,sensor=disk(3))=>({packets,steps,sensor});
function fraction(x){const d=new DataView(new ArrayBuffer(8));d.setFloat64(0,x);const b=d.getBigUint64(0),s=b>>63n?-1n:1n;let e=Number((b>>52n)&2047n),m=b&((1n<<52n)-1n);assert.notEqual(e,2047);if(e){m+=1n<<52n;e-=1075;}else e=-1074;return e>=0?[s*m*(1n<<BigInt(e)),1n]:[s*m,1n<<BigInt(-e)];}
function contains(a,n,d=1n){const [l,ld]=fraction(a[0]),[h,hd]=fraction(a[1]);assert.ok(l*d<=n*ld&&h*d>=n*hd,`${a} excludes ${n}/${d}`);}

test('actual WASM finite packet POWER tally preserves watts, circular phase and complete old route snapshots',()=>{
 const x=input(),before=structuredClone(x),r=runtime.queryPolarizedPacket(x);assert.equal(r.status,'completed');assert.deepEqual(x,before);assert.equal(r.counts.accepted,2);
 contains(r.stats.totalSourcePower,1n);contains(r.stats.acceptedSourcePower,1n);contains(r.stats.detectedPower,576n,625n);
 for(const [j,record] of r.records.entries()){
  const p=x.packets[j];assert.deepEqual(record.power,p.power);contains(record.sensorPower,BigInt(j?432:144),625n);
  const old=runtime.tracePolarizedRoute(p.ray,plate,{power:p.power,transverseReference:p.transverseReference});assert.deepEqual(record.route,old);assert.equal(record.sensor.status,'hit');
 }
});
test('actual WASM ideal power counter does not double-apply sensor cosine or interface transmission',()=>{
 const r=runtime.queryPolarizedPacket(input(undefined,plate,disk(3,10,[3,0,-4])));assert.equal(r.status,'completed');contains(r.stats.detectedPower,576n,625n);
 assert.equal(r.interfaceQueries,4);assert.equal(r.sensorQueries,2);
});
test('actual WASM known sensor omissions retain total and accepted source powers separately',()=>{
 const r=runtime.queryPolarizedPacket(input([packet(.25),packet(.75,2)],[],disk(3,1)));assert.equal(r.status,'completed');assert.equal(r.counts.accepted,1);assert.equal(r.counts.sensorMiss,1);
 contains(r.stats.totalSourcePower,1n);contains(r.stats.acceptedSourcePower,1n,4n);contains(r.stats.detectedPower,1n,4n);assert.equal(r.records[1].sensorPower,null);assert.deepEqual(r.records[1].power,[.75,0,0,.75]);
});
test('actual WASM sensor boundary uncertainty and zero-power unknown packets never become a final black tally',()=>{
 for(const watts of [0,1]){const p=packet(watts);p.ray.origin=[[.9,1.1],0,0];const r=runtime.queryPolarizedPacket(input([p],[],disk(3,1)));assert.equal(r.status,'unresolved');assert.equal(r.stats,null);assert.equal(r.counts.unknown,1);assert.equal(r.records[0].status,'sensor_unresolved');assert.equal(r.records[0].sensorPower,null);}
});
test('actual WASM packet budget retains accepted prefix and not-examined original power, then recovers',()=>{
 const x=input(),r=runtime.queryPolarizedPacket(x,{maximumPacketEvaluations:1});assert.equal(r.status,'budget_exceeded');assert.equal(r.stats,null);assert.equal(r.evaluations,1);assert.equal(r.counts.notExamined,1);assert.equal(r.records[0].status,'accepted');assert.equal(r.records[1].route,null);assert.deepEqual(r.records[1].power,[.75,0,0,.75]);
 const total=runtime.queryPolarizedPacket(x,{maximumTotalSqrtRefinements:1});assert.equal(total.status,'budget_exceeded');assert.equal(total.stats,null);assert.equal(runtime.queryPolarizedPacket(x).status,'completed');
});
test('actual WASM finite packet preflight rejects bad later source before attempting an earlier one',()=>{
 const x=input();x.packets[1].power=[1,2,0,0];const r=runtime.queryPolarizedPacket(x);assert.equal(r.status,'invalid_input');assert.equal(r.stats,null);assert.equal(r.evaluations,0);assert.equal(r.records.length,0);
 const empty=runtime.queryPolarizedPacket(input([],[]));assert.equal(empty.status,'completed');for(const bounds of Object.values(empty.stats))assert.ok(bounds.every(x=>x===0));
});
test('actual WASM subnormal packet power survives ideal sensor transport without midpoint arithmetic',()=>{
 const p=packet(Number.MIN_VALUE),r=runtime.queryPolarizedPacket(input([p],[]));assert.equal(r.status,'completed');contains(r.stats.detectedPower,1n,1n<<1074n);contains(r.records[0].route.initialState.coherency.upper[0].imag,1n,1n<<1075n);
});
test('actual WASM new getters retain packet snapshots across unrelated queries and reject invalid exchange atomically',()=>{
 runtime.queryPolarizedPacket(input());const n=runtime.native,out=()=>runtime.output();runtime.check(n._pp_sim_polarized_packet_record(0,1));const before=out();
 assert.notEqual(n._pp_sim_polarized_packet_record(1024,0),0);assert.deepEqual(out(),before);assert.notEqual(n._pp_sim_polarized_packet_record(0,4),0);assert.deepEqual(out(),before);
 assert.notEqual(n._pp_sim_polarized_packet_segment(0,64,1),0);assert.deepEqual(out(),before);
 const values=new Float64Array(n.HEAPU8.buffer,n._pp_sim_input_f64_ptr(),23);values.fill(0);values[0]=1025;assert.notEqual(n._pp_sim_polarized_packet(23),0);assert.deepEqual(out(),before);
 runtime.tracePolarizedRoute(packet().ray,plate);runtime.check(n._pp_sim_polarized_packet_record(0,1));assert.deepEqual(out(),before);runtime.check(n._pp_sim_reset());assert.notEqual(n._pp_sim_polarized_packet_record(0,0),0);
});
