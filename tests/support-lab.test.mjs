import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {supportCase,evaluateSupportCase,initializeSupportLab} from '../tools/support-lab.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const htmlUrl=new URL('../tools/support-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8');
const near=(a,b,e=1e-7)=>assert.ok(Math.abs(a-b)<=e,`${a} != ${b}`);
test('actual WASM support lab balances prescribed loads and preserves complete states at time zero',()=>{
  for(const preset of ['floor','stack','slope','curvature','detach','positive-gap']){
    const state=evaluateSupportCase(runtime,{preset});assert.equal(state.result.success,true,preset);assert.equal(state.worldUnchanged,true);assert.deepEqual(state.before,state.after);assert.equal(state.after.info.ticks,0);
    if(preset==='floor')near(state.result.constraints[0].lambda,10);
    if(preset==='stack')for(const [j,force]of [52,47,23].entries())near(state.result.constraints[j].lambda,force);
    if(preset==='curvature')near(state.result.constraints[0].lambda,6);
    if(preset==='detach')near(state.result.constraints[0].lambda,0);
    if(preset==='positive-gap')assert.ok(state.result.constraints[0].gap[0]>0);
  }
});
test('actual WASM support lab exposes impact and iteration failures without applying a candidate',()=>{
  const impact=evaluateSupportCase(runtime,{preset:'impact'});assert.equal(impact.result.failure,'impact_required');assert.deepEqual(impact.before,impact.after);
  const budget=evaluateSupportCase(runtime,{preset:'stack',maxIterations:1});assert.equal(budget.result.failure,'iteration_budget');assert.deepEqual(budget.before,budget.after);
  const loaded=evaluateSupportCase(runtime,{forceDeltaY:5});near(loaded.result.constraints[0].lambda,5);
  const separating=evaluateSupportCase(runtime,{normalVelocity:1e-20});assert.equal(separating.result.constraints[0].phase,'separating');near(separating.result.constraints[0].lambda,0);
  assert.throws(()=>supportCase({preset:'unknown'}));assert.throws(()=>supportCase({maxIterations:1.5}));
});
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[];
  const defaults={'support-preset':'floor','force-delta':'0','normal-velocity':'0','gap-band':'1e-8','support-iterations':'20000'};
  const ctx=new Proxy({}, {get:(_target,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const get=id=>{assert.ok(ids.has(id),'missing element '+id);if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',hidden:false,disabled:true,width:900,height:520,getContext:()=>ctx,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};
  return {get,draws,doc:{getElementById:get},fire:(id,type='change')=>listeners.get(id+':'+type)()};
}
test('UI uses real support outputs, separates candidate failure and clears stale values on bad inputs',async()=>{
  const ui=harness(),lab=await initializeSupportLab({doc:ui.doc,loadRuntime:async()=>runtime});assert.equal(ui.get('support-controls').disabled,false);assert.equal(lab.getState().result.success,true);assert.ok(ui.draws.some(d=>d[0]==='arc'));
  ui.get('support-preset').value='stack';ui.fire('support-preset');assert.match(ui.get('support-constraints').textContent,/52\.000000/);
  ui.get('support-iterations').value='1';ui.fire('support-iterations','input');assert.equal(lab.getState().result.failure,'iteration_budget');assert.match(ui.get('support-status').textContent,/適用しません/);assert.equal(JSON.parse(ui.get('support-json').textContent).worldUnchanged,true);
  ui.get('support-iterations').value='0';ui.fire('support-iterations','input');assert.equal(lab.getState(),null);assert.equal(ui.get('support-constraints').textContent,'—');assert.equal(ui.get('support-json').textContent,'結果なし');
  ui.get('support-iterations').value='20000';ui.fire('support-iterations');assert.equal(lab.getState().result.success,true);
});
test('UI load failure and recovery never substitute a JS support solver',async()=>{
  const ui=harness();let fail=true;const lab=await initializeSupportLab({doc:ui.doc,loadRuntime:async()=>{if(fail)throw new Error('offline');return runtime;}});
  assert.equal(lab.getState(),null);assert.equal(ui.get('support-controls').disabled,true);fail=false;await lab.retry();assert.equal(lab.getState().result.success,true);
});
test('support lab static links and original diagram exist with unique IDs',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
  for(const match of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(match[1]))await access(new URL(match[1].split('?')[0],htmlUrl));
  assert.match(html,/読み取り専用照会/);assert.match(html,/rω²/);assert.match(html,/相補/);
});
