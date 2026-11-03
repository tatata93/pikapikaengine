import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {opticalRouteCase,evaluateOpticalRouteCase,initializeOpticalRouteLab} from '../tools/optical-route-lab.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const htmlUrl=new URL('../tools/optical-route-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8');
const enclosed=(a,x)=>assert.ok(a[0]<=x&&x<=a[1],`${x} outside ${a}`);
test('actual WASM route lab directly computes prescribed primary and two-reflection branches',()=>{
  const direct=evaluateOpticalRouteCase(runtime),ghost=evaluateOpticalRouteCase(runtime,{preset:'ghost'});
  assert.equal(direct.result.status,'completed');enclosed(direct.result.completion.totals.distance,2.25);enclosed(direct.result.completion.totals.throughput,.9216);
  assert.equal(ghost.result.status,'completed');enclosed(ghost.result.completion.totals.opticalPathLength,3.125);enclosed(ghost.result.completion.totals.throughput,.00147456);
  const brewster=evaluateOpticalRouteCase(runtime,{preset:'brewster'});enclosed(brewster.result.completion.ray.origin[0],11/6);
});
test('actual WASM curved lens uses the complete phase interval at the same wavelength',()=>{
  const blue=evaluateOpticalRouteCase(runtime,{preset:'dispersion',wavelengthNm:450}),red=evaluateOpticalRouteCase(runtime,{preset:'dispersion',wavelengthNm:650});
  for(const state of [blue,red]){assert.equal(state.result.status,'completed');assert.deepEqual(state.result.segments[0].otherIndex,state.source.dispersion.values.phase);assert.deepEqual(state.result.segments[1].incidentIndex,state.source.dispersion.values.phase);assert.equal(state.result.vacuumWavelength,state.source.settings.vacuumWavelength);}
  assert.ok(blue.result.completion.ray.origin[0][1]<red.result.completion.ray.origin[0][0],'wavelength-specific sensor X enclosures are separated');
  assert.throws(()=>evaluateOpticalRouteCase(runtime,{preset:'dispersion',wavelengthNm:1000}));
  assert.throws(()=>opticalRouteCase({preset:'lens',thickness:.1}),/面が交差しない/);
});
test('actual WASM lab retains family variation and unmet budgets without a final completion',()=>{
  const family=evaluateOpticalRouteCase(runtime,{preset:'family'});assert.equal(family.result.status,'geometry_unresolved');assert.equal(family.result.completion,null);
  const admitted=evaluateOpticalRouteCase(runtime,{preset:'family',maximumParameterWidth:1});assert.equal(admitted.result.status,'completed');enclosed(admitted.result.completion.ray.origin[0],-.02);enclosed(admitted.result.completion.ray.origin[0],.02);
  const critical=evaluateOpticalRouteCase(runtime,{preset:'critical'});assert.equal(critical.result.status,'interface_unresolved');assert.equal(critical.result.completion,null);
  assert.equal(evaluateOpticalRouteCase(runtime,{maximumSteps:2}).result.status,'budget_exceeded');
  assert.throws(()=>opticalRouteCase({preset:'invalid'}));assert.throws(()=>opticalRouteCase({thickness:0}));
});
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[];
  const defaults={'route-preset':'plate','plate-thickness':'.25','route-wavelength':'550','route-step-budget':'64','route-width':'1e-6','route-sqrt-budget':'128'};
  const ctx=new Proxy({}, {get:(_target,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const get=id=>{assert.ok(ids.has(id),'missing element '+id);if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',hidden:false,disabled:true,width:1000,height:520,getContext:()=>ctx,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};
  return {get,draws,doc:{getElementById:get},fire:(id,type='change')=>listeners.get(id+':'+type)()};
}
test('UI presents real bounds, absent completion and recovery while loader failure has no fallback',async()=>{
  const ui=harness();let fail=true;const lab=await initializeOpticalRouteLab({doc:ui.doc,loadRuntime:async()=>{if(fail)throw new Error('offline');return runtime;}});
  assert.equal(lab.getState(),null);assert.equal(ui.get('route-controls').disabled,true);fail=false;await lab.retry();assert.equal(lab.getState().result.status,'completed');assert.ok(ui.draws.some(d=>d[0]==='strokeRect'));
  ui.get('route-preset').value='ghost';ui.fire('route-preset');assert.match(ui.get('route-power').textContent,/0\.0014745/);
  ui.get('route-step-budget').value='2';ui.fire('route-step-budget','input');assert.equal(lab.getState().result.completion,null);assert.equal(ui.get('route-length').textContent,'—');assert.match(ui.get('route-status').textContent,/最終光線なし/);
  ui.get('plate-thickness').value='0';ui.fire('plate-thickness','input');assert.equal(lab.getState(),null);assert.equal(ui.get('route-json').textContent,'結果なし');
  ui.get('plate-thickness').value='.25';ui.get('route-step-budget').value='64';ui.fire('route-step-budget');assert.equal(lab.getState().result.status,'completed');
});
test('route lab static links original diagram and declared scope are present',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
  for(const match of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(match[1]))await access(new URL(match[1].split('?')[0],htmlUrl));
  assert.match(html,/指定した面列と分岐/);assert.match(html,/中央値/);assert.match(html,/無偏光/);assert.match(html,/撮像/);
});
