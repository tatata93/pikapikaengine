import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const ray={origin:[0,0,0],direction:[0,0,1],maximumParameter:10};
const disk=(id,z,apertureRadius=10)=>({id,surface:{kind:'disk',center:[0,0,z],normal:[0,0,-1],apertureRadius}});
const encloses=(a,x)=>assert.ok(a[0]<=x&&a[1]>=x,`${a} excludes ${x}`);
test('actual WASM nearest selection chooses geometry ahead of ID order and retains all vector bounds',()=>{
  const source={...ray,direction:[0,0,2]},surfaces=[disk(20,2),disk(10,4)],before=JSON.stringify({source,surfaces});
  const a=runtime.queryNearestOpticalSurface(source,surfaces),b=runtime.queryNearestOpticalSurface(source,[...surfaces].reverse());
  assert.deepEqual(a,b);assert.equal(a.status,'hit');assert.equal(a.nearest.id,20);encloses(a.nearest.hit.parameter,1);encloses(a.nearest.hit.physicalDistance,2);encloses(a.nearest.hit.position[2],2);
  assert.deepEqual(a.surfaces.map(s=>s.id),[10,20]);assert.equal(JSON.stringify({source,surfaces}),before);assert.equal(a.nearest.hit.frontFace,true);
});
test('actual WASM nearest selection cannot ignore partial aperture or simultaneous competitors',()=>{
  for(const [r,s]of [[{...ray,origin:[[.9,1.1],0,0]},[disk(1,1,1),disk(2,2)]],[ray,[disk(1,1),disk(2,1)]]]){
    const a=runtime.queryNearestOpticalSurface(r,s);assert.equal(a.status,'unresolved');assert.equal(a.nearest,null);assert.ok(a.surfaces.length===2);
  }
});
test('actual WASM nearest selection keeps genuine family width and correlated-order uncertainty',()=>{
  const a=runtime.queryNearestOpticalSurface({...ray,direction:[0,0,[1,2]]},[disk(1,2),disk(2,3)]);
  assert.equal(a.status,'unresolved');assert.equal(a.nearest,null);encloses(a.surfaces[0].geometry.hit.parameter,1);encloses(a.surfaces[0].geometry.hit.parameter,2);
});
test('actual WASM nearest prefix exclusion certifies rear aperture uncertainty and can be disabled',()=>{
  const source={...ray,origin:[[.9,1.1],0,0]},surfaces=[disk(1,1),disk(2,2,1)];
  const a=runtime.queryNearestOpticalSurface(source,surfaces);assert.equal(a.status,'hit');assert.equal(a.nearest.id,1);assert.equal(a.surfaces[1].geometry.status,'unresolved');assert.equal(a.surfaces[1].prefix.status,'miss');assert.equal(a.surfaces[1].excludedByPrefix,true);assert.equal(a.geometryQueries,3);assert.equal(a.prefixQueries,1);
  const b=runtime.queryNearestOpticalSurface(source,surfaces,{allowPrefixExclusion:false});assert.equal(b.status,'unresolved');assert.equal(b.nearest,null);
  const c=runtime.queryNearestOpticalSurface(source,surfaces,{maximumQueries:2});assert.equal(c.status,'budget_exceeded');assert.equal(c.nearest,null);assert.equal(c.geometryQueries,2);
});
test('actual WASM nearest self and explicit cutoff retain distinct domains without source skip',()=>{
  const zero=runtime.queryNearestOpticalSurface(ray,[disk(1,0),disk(2,1e-8)]);assert.equal(zero.status,'hit');assert.equal(zero.nearest.id,1);encloses(zero.nearest.hit.parameter,0);
  const tiny=runtime.queryNearestOpticalSurface({...ray,minimumParameter:1e-9},[disk(1,0),disk(2,1e-8)]);assert.equal(tiny.status,'hit');assert.equal(tiny.nearest.id,2);encloses(tiny.nearest.hit.parameter,1e-8);
  const sphere=[{id:3,surface:{kind:'sphere',center:[0,0,0],radius:1}}],inside={origin:[0,0,1],direction:[0,0,-1],maximumParameter:10};
  const self=runtime.queryNearestOpticalSurface(inside,sphere);assert.equal(self.status,'unresolved');assert.equal(self.nearest,null);
  const exit=runtime.queryNearestOpticalSurface({...inside,minimumParameter:.1},sphere);assert.equal(exit.status,'hit');encloses(exit.nearest.hit.parameter,2);
});
test('actual WASM nearest rejected candidates do not lose the second valid spherical-cap root',()=>{
  const a=runtime.queryNearestOpticalSurface({origin:[0,0,5],direction:[0,0,-1],maximumParameter:10},[{id:4,surface:{kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:2,apertureRadius:1}},disk(5,-1)]);
  assert.equal(a.status,'hit');assert.equal(a.nearest.id,4);encloses(a.nearest.hit.parameter,5);assert.equal(a.surfaces[0].geometry.candidates[0].state,'rejected_cap');
});
test('actual WASM nearest budgets and invalid model inputs have no stale winner and can recover',()=>{
  const s=[disk(1,1),disk(2,2)];assert.equal(runtime.queryNearestOpticalSurface(ray,s).status,'hit');
  const budget=runtime.queryNearestOpticalSurface(ray,s,{maximumQueries:1});assert.equal(budget.status,'budget_exceeded');assert.equal(budget.nearest,null);assert.equal(budget.surfaces[1].geometry,null);
  for(const input of [[disk(1,1),disk(1,2)],[disk(3,2,0)]]){const r=runtime.queryNearestOpticalSurface(ray,input);assert.equal(r.status,'invalid_input');assert.equal(r.nearest,null);}
  assert.equal(runtime.queryNearestOpticalSurface(ray,[]).status,'miss');assert.equal(runtime.queryNearestOpticalSurface({...ray,direction:[0,0,0]},[]).status,'unresolved');
  assert.throws(()=>runtime.queryNearestOpticalSurface(ray,s,{allowPrefixExclusion:1}),/boolean/);assert.throws(()=>runtime.queryNearestOpticalSurface(ray,[disk(9007199254740992,1)]),/integer/);
  assert.equal(runtime.queryNearestOpticalSurface(ray,s).nearest.id,1);
});
test('actual WASM nearest results are independent copied snapshots',()=>{
  const r=runtime.queryNearestOpticalSurface(ray,[disk(1,1),disk(2,2)]),before=JSON.stringify(r);
  runtime.queryNearestOpticalSurface(ray,[disk(4,4)]);runtime.queryBoundedSurface(ray,disk(1,3).surface);assert.equal(JSON.stringify(r),before);
});
