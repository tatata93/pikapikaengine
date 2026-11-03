import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {dispersionCase,evaluateDispersionCase,initializeDispersionLab} from '../tools/dispersion-lab.mjs';
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const htmlUrl=new URL('../tools/dispersion-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8');
test('actual WASM plotted bins cover the complete requested band with retained intervals',()=>{
  const r=evaluateDispersionCase(runtime);assert.equal(r.result.status,'resolved');assert.equal(r.bins.length,32);
  assert.equal(r.bins[0].wavelength[0],r.source.wavelength[0]);assert.equal(r.bins.at(-1).wavelength[1],r.source.wavelength[1]);
  for(let j=0;j<32;++j){const b=r.bins[j];assert.equal(b.result.status,'resolved');assert.ok(b.result.values.group[0]>b.result.values.phase[1]);if(j)assert.equal(r.bins[j-1].wavelength[1],b.wavelength[0]);}
  assert.ok(r.bins[0].result.values.phase[0]>r.bins.at(-1).result.values.phase[1]);
});
test('actual WASM pole model and full-band width preserve unresolved data',()=>{
  const pole=evaluateDispersionCase(runtime,{kind:'pole'});assert.equal(pole.result.reason,'pole_not_excluded');assert.equal(pole.result.values,null);
  assert.ok(pole.bins.some(b=>b.result.reason==='pole_not_excluded'));assert.ok(pole.bins.some(b=>b.result.status==='nonphysical'));
  const narrow=evaluateDispersionCase(runtime,{maximumPhaseWidth:.001});assert.equal(narrow.result.reason,'phase_width');assert.ok(narrow.bins.some(b=>b.result.status==='resolved'));
  assert.throws(()=>dispersionCase({minimumNm:800,maximumNm:400}));assert.throws(()=>dispersionCase({kind:'invalid'}));
});
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[];
  const defaults={'dispersion-kind':'cauchy','lambda-min':'400','lambda-max':'700','phase-width':'1','sqrt-budget':'128'};
  const ctx=new Proxy({}, {get:(_target,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const get=id=>{assert.ok(ids.has(id),'missing element '+id);if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',hidden:false,disabled:true,width:900,height:420,getContext:()=>ctx,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};
  return {get,draws,doc:{getElementById:get},fire:(id,type='change')=>listeners.get(id+':'+type)()};
}
test('UI shows actual interval results, handles poles and clears stale values on invalid input',async()=>{
  const ui=harness(),lab=await initializeDispersionLab({doc:ui.doc,loadRuntime:async()=>runtime});
  assert.equal(ui.get('dispersion-controls').disabled,false);assert.match(ui.get('phase-value').textContent,/\[/);assert.ok(ui.draws.some(d=>d[0]==='strokeRect'));
  ui.get('dispersion-kind').value='pole';ui.fire('dispersion-kind');assert.equal(lab.getState().result.reason,'pole_not_excluded');assert.equal(ui.get('phase-value').textContent,'—');
  ui.get('lambda-max').value='200';ui.fire('lambda-max','input');assert.equal(lab.getState(),null);assert.equal(ui.get('dispersion-json').textContent,'結果なし');assert.equal(ui.get('dispersion-error').hidden,false);
  ui.get('dispersion-kind').value='cauchy';ui.get('lambda-max').value='700';ui.fire('lambda-max');assert.equal(lab.getState().result.status,'resolved');
  ui.get('lambda-max').value='1000';ui.fire('lambda-max');assert.equal(lab.getState(),null);assert.equal(ui.get('phase-value').textContent,'—');
});
test('loader failure disables controls and retries the real runtime without a JS fallback',async()=>{
  const ui=harness();let fail=true;
  const lab=await initializeDispersionLab({doc:ui.doc,loadRuntime:async()=>{if(fail)throw new Error('offline');return runtime;}});
  assert.equal(lab.getState(),null);assert.equal(ui.get('dispersion-controls').disabled,true);assert.match(ui.get('dispersion-error').textContent,/offline/);
  fail=false;await lab.retry();assert.equal(lab.getState().result.status,'resolved');assert.equal(ui.get('dispersion-controls').disabled,false);
});
test('lab static content has unique IDs and available local documentation and diagram',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
  for(const match of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(match[1]))await access(new URL(match[1].split('?')[0],htmlUrl));
  assert.match(html,/実在するガラス/);assert.match(html,/真空中の波長/);assert.match(html,/10⁻²⁴/);
});
