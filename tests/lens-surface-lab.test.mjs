import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {SURFACE_DEFAULTS,surfacePreset,surfaceCase,evaluateSurfaceCase,initializeSurfaceLab} from '../tools/lens-surface-lab.mjs';
const wasmBytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes});
const htmlUrl=new URL('../tools/lens-surface-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8');
const encloses=(a,value)=>assert.ok(a[0]<=value&&value<=a[1],JSON.stringify(a)+' does not enclose '+value);
const near=(a,b,tolerance=1e-12)=>assert.ok(Math.abs(a-b)<=tolerance,a+' != '+b);

test('actual C++ WASM cap front encloses analytic position parameter distance and normal',()=>{
  assert.equal(runtime.diagnostics.backend,'C++ WebAssembly');
  const {source,result:r}=evaluateSurfaceCase(runtime,SURFACE_DEFAULTS);
  assert.deepEqual(source.ray.direction,[0,0,1]);assert.equal(r.status,'hit');assert.equal(r.reason,'none');
  assert.equal(r.rootCount,2);assert.equal(r.candidates[0].state,'accepted');assert.equal(r.candidates[1].state,'not_examined');
  encloses(r.hit.parameter,3);encloses(r.hit.physicalDistance,3);
  for(const bounds of r.hit.position)encloses(bounds,0);
  encloses(r.hit.geometricNormal[2],-1);assert.equal(r.hit.frontFace,true);
});
test('same physical hit retains metres while scaled direction changes ray parameter',()=>{
  const a=evaluateSurfaceCase(runtime,{directionScale:1}).result,b=evaluateSurfaceCase(runtime,{directionScale:2}).result;
  encloses(a.hit.parameter,3);encloses(b.hit.parameter,1.5);encloses(b.hit.physicalDistance,3);
  near(a.hit.positionEstimate[2],b.hit.positionEstimate[2]);
  const plane=evaluateSurfaceCase(runtime,{kind:'disk',directionScale:2}).result;
  assert.equal(plane.status,'hit');assert.equal(plane.discriminant,null);encloses(plane.hit.parameter,1.5);encloses(plane.hit.physicalDistance,3);
});
test('full sphere and vertex cap select different nearest roots from the backside',()=>{
  const p=surfacePreset('back'),cap=evaluateSurfaceCase(runtime,p).result,sphere=evaluateSurfaceCase(runtime,{...p,kind:'sphere'}).result;
  assert.deepEqual(surfaceCase(p).ray.direction,[0,0,-1],'axis preset avoids sin(pi) roundoff');
  assert.equal(cap.status,'hit');assert.equal(cap.candidates[0].state,'rejected_cap');assert.equal(cap.candidates[1].state,'accepted');
  encloses(cap.hit.parameter,5);assert.equal(cap.hit.frontFace,false);encloses(cap.hit.incidentNormal[2],1);
  encloses(sphere.hit.parameter,1);assert.equal(sphere.candidates[0].state,'accepted');
});
test('tangent aperture boundary and original self-hit preserve unresolved instead of false miss',()=>{
  for(const [name,reason]of [['tangent','tangent_or_discriminant'],['aperture','aperture_boundary'],['self','parameter_boundary']]) {
    const r=evaluateSurfaceCase(runtime,surfacePreset(name)).result;
    assert.equal(r.status,'unresolved');assert.equal(r.reason,reason);assert.equal(r.hit,null);
  }
  const self=evaluateSurfaceCase(runtime,surfacePreset('self')).result;
  encloses(self.candidates[0].parameter,0);assert.equal(self.candidates[1].state,'not_examined');
  const cutoff=evaluateSurfaceCase(runtime,surfacePreset('cutoff')).result;
  assert.equal(cutoff.status,'hit');assert.equal(cutoff.candidates[0].state,'rejected_parameter');encloses(cutoff.hit.parameter,4);
});
test('aperture rejection, finite window miss, negative radius and invalid edits remain distinct',()=>{
  const outside=evaluateSurfaceCase(runtime,{kind:'disk',originX:1.2}).result;
  assert.equal(outside.status,'miss');assert.equal(outside.candidates[0].state,'rejected_aperture');
  const finiteWindow=evaluateSurfaceCase(runtime,{maximumParameter:1}).result;
  assert.equal(finiteWindow.status,'miss');assert.equal(finiteWindow.hit,null);
  const reverse=evaluateSurfaceCase(runtime,{radius:-2,originZ:3,angleDegrees:180}).result;
  assert.equal(reverse.status,'hit');encloses(reverse.hit.parameter,3);encloses(reverse.hit.geometricNormal[2],1);
  for(const p of [{radius:0},{aperture:3},{minimumParameter:5,maximumParameter:2},{originX:'NaN'},{kind:'other'}])assert.throws(()=>surfaceCase(p));
  assert.throws(()=>surfacePreset('invalid'));
});
function harness() {
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),calls=[];
  const context=new Proxy({}, {get(target,key){return key in target?target[key]:(...args)=>calls.push({method:key,args});},set(target,key,value){target[key]=value;return true;}});
  const defaults={'surface-kind':'cap','origin-z':'-3','origin-x':'0','ray-angle':'0','direction-scale':'1',radius:'2',aperture:'1','parameter-min':'0','parameter-max':'10'};
  function get(id) {
    assert.ok(ids.has(id),'missing HTML element '+id);
    if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',hidden:false,disabled:true,width:900,height:500,setAttribute(name,value){this[name]=value;},getContext(){return context;},addEventListener(type,fn){listeners.set(id+':'+type,fn);}});
    return elements.get(id);
  }
  return {doc:{getElementById:get},get,calls,fire(id,type='click'){const callback=listeners.get(id+':'+type);assert.ok(callback,'missing listener '+id+':'+type);return callback();}};
}
test('UI submits actual surface queries and exposes intervals, estimates, candidate ordering and mode edits',async()=>{
  const ui=harness(),submitted=[];
  const instrumented={get diagnostics(){return runtime.diagnostics;},queryOpticalSurface(...args){submitted.push(structuredClone(args));return runtime.queryOpticalSurface(...args);}};
  const lab=await initializeSurfaceLab({doc:ui.doc,loadRuntime:async()=>instrumented});
  assert.equal(ui.get('surface-controls').disabled,false);assert.equal(submitted.length,1);assert.equal(lab.getState().result.status,'hit');
  assert.match(ui.get('result-parameter').textContent,/2\.999/);assert.match(ui.get('result-position').textContent,/X: \[0, 0\]/);
  assert.ok(ui.calls.some(c=>c.method==='strokeRect'),'C++ position enclosure is drawn separately');
  assert.match(ui.get('surface-view')['aria-label'],/物理距離区間/);
  ui.fire('preset-back');assert.equal(lab.getState().result.hit.frontFace,false);assert.match(ui.get('candidate-0-state').textContent,/頂点側半球の外/);
  ui.get('surface-kind').value='sphere';ui.fire('surface-kind','change');encloses(lab.getState().result.hit.parameter,1);
  ui.fire('preset-tangent');assert.equal(lab.getState().result.status,'unresolved');assert.equal(ui.get('result-estimate').textContent,'—');
  assert.match(ui.get('result-explanation').textContent,/置き換えません/);assert.equal(JSON.parse(ui.get('surface-json').textContent).result.hit,null);
  ui.fire('preset-aperture');assert.match(ui.get('result-reason').textContent,/開口の境界/);
  ui.fire('preset-self');assert.match(ui.get('candidate-1-state').textContent,/未調査/);
  ui.fire('preset-cutoff');assert.equal(lab.getState().result.status,'hit');encloses(lab.getState().result.hit.parameter,4);
  ui.fire('preset-front');ui.get('direction-scale').value='2';ui.fire('direction-scale','input');encloses(lab.getState().result.hit.parameter,1.5);encloses(lab.getState().result.hit.physicalDistance,3);
  assert.deepEqual(submitted.at(-1)[0].direction,[0,0,2]);assert.equal(ui.get('direction-scale-value').textContent,'2');
  ui.get('surface-kind').value='disk';ui.fire('surface-kind','change');ui.get('origin-x').value='1.2';ui.fire('origin-x','input');
  assert.match(ui.get('result-status').textContent,/指定範囲では交差なし/);assert.equal(ui.get('result-parameter').textContent,'—');assert.match(ui.get('result-explanation').textContent,/指定した面/);
});
test('UI clears stale hit on bad input and real C++ rejection and can recover without reload',async()=>{
  const ui=harness();let count=0,rejectNext=false;
  const instrumented={get diagnostics(){return runtime.diagnostics;},queryOpticalSurface(ray,surface,settings){count++;return runtime.queryOpticalSurface(ray,rejectNext?(rejectNext=false,{...surface,signedRadius:0}):surface,settings);}};
  const lab=await initializeSurfaceLab({doc:ui.doc,loadRuntime:async()=>instrumented});
  ui.get('radius').value='0';ui.fire('radius','input');assert.equal(count,1);assert.equal(lab.getState(),null);assert.equal(ui.get('result-position').textContent,'—');assert.match(ui.get('surface-error').textContent,/半径/);
  ui.fire('preset-front');assert.equal(lab.getState().result.status,'hit');assert.equal(ui.get('surface-error').hidden,true);
  rejectNext=true;lab.recalculate();assert.equal(lab.getState(),null);assert.equal(ui.get('result-status').textContent,'—');assert.match(ui.get('surface-view')['aria-label'],/表示していません/);
  ui.fire('preset-front');assert.equal(lab.getState().result.status,'hit');
});
test('initialization failure has no JS intersection fallback and retry calls actual WASM',async()=>{
  const ui=harness();let attempts=0;
  const lab=await initializeSurfaceLab({doc:ui.doc,loadRuntime:async()=>{if(attempts++===0)throw new Error('fixture load failed');return runtime;}});
  assert.equal(lab.getState(),null);assert.equal(ui.get('surface-controls').disabled,true);assert.equal(ui.get('result-parameter').textContent,'—');
  assert.match(ui.get('surface-error').textContent,/fixture load failed/);assert.equal(ui.get('surface-retry').disabled,false);
  await ui.fire('surface-retry');assert.equal(lab.getState().result.status,'hit');assert.equal(ui.get('surface-controls').disabled,false);
});
test('static learning assets and local links exist independently of module startup',async()=>{
  assert.match(html,/<html lang="ja">/);assert.match(html,/file:\/\/でも読め/);assert.match(html,/type="module" src="lens-surface-lab\.mjs(?:\?[^"]*)?"/);
  for(const match of html.matchAll(/(?:href|src)="([^"#]+)"/g)) {
    if(/^(?:https?:|data:)/.test(match[1]))continue;
    await access(new URL(match[1].split('?')[0],htmlUrl));
  }
  const svg=await readFile(new URL('../docs/learn/diagrams/lens-surface.svg',import.meta.url),'utf8');
  assert.match(svg,/<title/);assert.doesNotMatch(svg,/<(?:script|image|foreignObject)\b|(?:href|xlink:href)="https?:/);
});
