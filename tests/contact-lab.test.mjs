import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {CONTACT_DEFAULTS,contactCase,contactPose,evaluateContactCase,initializeContactLab} from '../tools/contact-lab.mjs';

const wasmBytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes});
const close=(actual,expected,tolerance=1e-12)=>assert.ok(Math.abs(actual-expected)<=tolerance,`${actual} != ${expected}`);

test('real C++ WASM detects the high-speed impact missed by an endpoint-only query',()=>{
  assert.equal(runtime.diagnostics.backend,'C++ WebAssembly');
  const state=evaluateContactCase(runtime);
  assert.equal(state.result.kind,'impact');close(state.result.time,0.002);assert.deepEqual(state.result.normal,[1,0,0]);
  close(state.result.initialGap,2);close(state.result.initialNormalSpeed,-1000);assert.equal(state.endpoint.kind,'none');close(state.endpoint.initialGap,13/3);
  const sample=contactPose(state.source,state.result.time);close(sample.a.position[0],-1);close(sample.b.position[0],0);
});

test('moving targets, no relative motion, tangency and initial contact remain distinct real query results',()=>{
  close(evaluateContactCase(runtime,{targetSpeed:500}).result.time,0.004);
  assert.equal(evaluateContactCase(runtime,{speed:500,targetSpeed:500}).result.initialMotion,'stationary');
  assert.equal(evaluateContactCase(runtime,{speed:-100}).result.kind,'none');
  const tangent=evaluateContactCase(runtime,{lateral:1});assert.equal(tangent.result.kind,'grazing');close(tangent.result.time,0.003);assert.deepEqual(tangent.result.normal,[0,-1,0]);assert.equal(tangent.result.roundoffSensitive,true);
  const initial=evaluateContactCase(runtime,{gap:0,speed:0,verticalSpeed:100});assert.equal(initial.result.kind,'initial_touch');assert.equal(initial.result.initialMotion,'tangential');close(initial.result.time,0);
  const apart=evaluateContactCase(runtime,{gap:0,speed:-100});assert.equal(apart.result.kind,'initial_touch');assert.equal(apart.result.initialMotion,'separating');
  const overlap=evaluateContactCase(runtime,{gap:-1,speed:100});assert.equal(overlap.result.kind,'initial_overlap');assert.equal(overlap.result.normalValid,false);
});

test('sphere-plane uses its solid half-space and moves its endpoint offset consistently',()=>{
  const state=evaluateContactCase(runtime,{mode:'plane'});assert.equal(state.result.kind,'impact');close(state.result.time,0.002);assert.deepEqual(state.result.normal,[-1,0,0]);assert.equal(state.endpoint.kind,'initial_overlap');
  const moving=evaluateContactCase(runtime,{mode:'plane',targetSpeed:500});close(moving.result.time,0.004);
  const pose=contactPose(moving.source,moving.source.horizonSeconds);close(pose.plane.offset,-500/120);
  close(moving.endpoint.initialGap,-13/6);
  const lateral=evaluateContactCase(runtime,{mode:'plane',verticalSpeed:500,lateral:2});close(lateral.result.time,state.result.time);
});

test('horizon endpoints and numerical uncertainty are preserved instead of becoming no contact',()=>{
  const before=evaluateContactCase(runtime,{horizonSeconds:0.001});assert.equal(before.result.kind,'none');assert.equal(before.result.time,null);
  const endpoint=evaluateContactCase(runtime,{horizonSeconds:0.002});assert.equal(endpoint.result.kind,'impact');assert.equal(endpoint.result.atHorizon,true);assert.equal(endpoint.endpoint.kind,'initial_touch');
  const uncertain=evaluateContactCase(runtime,{horizonSeconds:0.002-1e-18});assert.equal(uncertain.result.kind,'uncertain');assert.equal(uncertain.result.roundoffSensitive,true);assert.equal(uncertain.result.atHorizon,true);
  assert.equal(evaluateContactCase(runtime,{horizonSeconds:0}).result.kind,'none');
});

function documentHarness(){
  const listeners=new Map(),elements=new Map(),context=new Proxy({}, {get:()=>()=>{},set:()=>true});
  const defaults={'contact-mode':'spheres',gap:'2',speed:'1000','vertical-speed':'0','target-speed':'0',lateral:'0',horizon:String(1000/120),'horizon-unit':'ms',preview:'100'};
  function get(id){if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',hidden:false,disabled:true,width:900,height:440,
    setAttribute(name,value){this[name]=value;},getContext(){return context;},addEventListener(type,callback){listeners.set(`${id}:${type}`,callback);}});return elements.get(id);}
  return {doc:{getElementById:get},get,fire:(id,type='click')=>listeners.get(`${id}:${type}`)()};
}

test('UI calls the real interval and endpoint APIs on input, preserves units and recovers from rejected input',async()=>{
  const ui=documentHarness();let sphereCalls=0,planeCalls=0;
  const instrumented={get diagnostics(){return runtime.diagnostics;},querySphereSphere(...args){sphereCalls++;return runtime.querySphereSphere(...args);},querySpherePlane(...args){planeCalls++;return runtime.querySpherePlane(...args);}};
  const lab=await initializeContactLab({doc:ui.doc,loadRuntime:async()=>instrumented});
  assert.equal(ui.get('contact-controls').disabled,false);assert.equal(sphereCalls,2);close(lab.getState().result.time,0.002);assert.match(ui.get('comparison').textContent,/見落と/);
  const horizon=lab.getState().source.horizonSeconds;ui.get('horizon-unit').value='s';ui.fire('horizon-unit','change');close(lab.getState().source.horizonSeconds,horizon);assert.equal(ui.get('horizon').max,'0.02');
  ui.get('horizon-unit').value='ms';ui.fire('horizon-unit','change');close(lab.getState().source.horizonSeconds,horizon);
  ui.get('contact-mode').value='plane';ui.fire('contact-mode','change');assert.equal(planeCalls,2);assert.match(ui.get('endpoint-kind').textContent,/重なり/);
  ui.fire('preset-tangent');assert.equal(lab.getState().source.parameters.mode,'plane');assert.equal(lab.getState().result.initialMotion,'tangential');
  ui.fire('preset-fast');assert.equal(lab.getState().source.parameters.mode,'spheres');
  ui.get('horizon').value=String((0.002-1e-18)*1000);ui.fire('horizon','input');assert.equal(lab.getState().result.kind,'uncertain');assert.match(ui.get('comparison').textContent,/不確か/);assert.match(ui.get('roundoff').textContent,/区間証明/);
  ui.get('gap').value='NaN';ui.fire('gap','input');assert.equal(lab.getState(),null);assert.equal(ui.get('result-time').textContent,'—');assert.match(ui.get('contact-error').textContent,/照会できません/);
  ui.fire('preset-grazing');assert.equal(lab.getState().result.kind,'grazing');assert.equal(ui.get('contact-error').hidden,true);
  ui.get('preview').value='50';ui.fire('preview','input');close(lab.getState().source.parameters.preview,0.5);assert.match(ui.get('preview-time').textContent,/4\.166667/);
  ui.fire('preset-away');assert.equal(lab.getState().result.initialMotion,'separating');assert.match(ui.get('comparison').textContent,/開始時点.*離反/);
  ui.fire('preset-overlap');assert.equal(lab.getState().result.kind,'initial_overlap');assert.match(ui.get('comparison').textContent,/退出する時刻ではありません/);assert.ok(sphereCalls>10);
});

test('initialization failure never substitutes calculations and retry restores actual WASM queries',async()=>{
  const ui=documentHarness();let attempt=0;
  const lab=await initializeContactLab({doc:ui.doc,loadRuntime:async()=>{if(attempt++===0)throw new Error('fixture load failure');return runtime;}});
  assert.equal(lab.getState(),null);assert.equal(ui.get('contact-controls').disabled,true);assert.match(ui.get('contact-error').textContent,/fixture load failure/);
  await lab.retry();assert.equal(lab.getState().result.kind,'impact');assert.equal(ui.get('contact-controls').disabled,false);assert.equal(ui.get('contact-error').hidden,true);
});

test('lab HTML links and unique IDs are valid; source defaults match the real input case',async()=>{
  const url=new URL('../tools/contact-lab.html',import.meta.url),html=await readFile(url,'utf8');
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);assert.equal(new Set(ids).size,ids.length);
  for(const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)){const target=new URL(match[1],url);if(target.protocol==='file:'){const fragment=target.hash.slice(1);target.hash='';await access(target);if(fragment)assert.ok((await readFile(target,'utf8')).includes(`id="${fragment}"`));}}
  assert.match(html,/<script type="module" src="contact-lab\.mjs(?:\?[^"]*)?"><\/script>/);assert.match(html,/World全体のCCD/);assert.match(html,/file:\/\//);
  const source=contactCase(CONTACT_DEFAULTS);assert.deepEqual(source.a.position,[-3,0,0]);assert.equal(source.horizonSeconds,1/120);
  for(const input of [{gap:NaN},{speed:Infinity},{horizonSeconds:-1},{horizonSeconds:0.1},{preview:2},{mode:'mesh'}])assert.throws(()=>contactCase(input));
});
