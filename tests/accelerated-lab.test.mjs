import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {ACCELERATED_DEFAULTS,ACCELERATED_PRESETS,acceleratedCase,acceleratedPose,evaluateAcceleratedCase,initializeAcceleratedLab} from '../tools/accelerated-lab.mjs';

const wasmBytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes});
const close=(a,b,tolerance=1e-12)=>assert.ok(Math.abs(a-b)<=tolerance,`${a} != ${b}`);
function entry(result,time,tolerance){assert.equal(result.kind,'entry_bracket');assert.ok(result.bracket[0]<=time&&time<=result.bracket[1]);assert.ok(result.bracket[1]-result.bracket[0]<=tolerance);assert.equal(result.safeUntil,result.bracket[0]);assert.ok(result.valueAtSafe[0]>0&&result.negativeValue[1]<0);}

test('real C++ WASM encloses the default accelerated plane entry and reports endpoint overlap',()=>{
  assert.equal(runtime.diagnostics.backend,'C++ WebAssembly');const state=evaluateAcceleratedCase(runtime);
  assert.deepEqual(state.source.a.acceleration,[0,-4,0]);assert.equal(state.source.a.radius,1);entry(state.result,1,state.source.settings.timeTolerance);
  assert.equal(state.endpoint.kind,'unresolved');assert.equal(state.endpoint.reason,'initial_overlap');
  assert.deepEqual(state.endpointInput.a.position,[0,-5,0]);assert.equal(state.endpointInput.horizonSeconds,0);
  const point=acceleratedPose(state.source,1);assert.deepEqual(point.a.position,[0,1,0]);assert.deepEqual(point.a.velocity,[0,-4,0]);
});

test('real accelerated pair query detects an entry despite separated endpoint and uses relative acceleration',()=>{
  const state=evaluateAcceleratedCase(runtime,{mode:'spheres'});entry(state.result,1,state.source.settings.timeTolerance);
  assert.equal(state.source.a.radius,0.5);assert.equal(state.source.b.radius,0.5);assert.equal(state.endpoint.kind,'none');
  const common=evaluateAcceleratedCase(runtime,{mode:'spheres',targetAccelerationY:-4});assert.equal(common.result.kind,'none');assert.equal(common.result.safeUntil,2);
  const before=evaluateAcceleratedCase(runtime,{horizonSeconds:0.5});assert.equal(before.result.kind,'none');assert.equal(before.result.safeUntil,0.5);
});

test('real C++ preserves initial-boundary, budget and repeated-root uncertainty',()=>{
  const boundary=evaluateAcceleratedCase(runtime,ACCELERATED_PRESETS.boundary);assert.equal(boundary.result.kind,'unresolved');assert.equal(boundary.result.reason,'initial_boundary');assert.equal(boundary.result.initialSeparationProven,false);assert.equal(boundary.result.bracket,null);
  const budget=evaluateAcceleratedCase(runtime,ACCELERATED_PRESETS.budget);assert.equal(budget.result.kind,'unresolved');assert.equal(budget.result.reason,'evaluation_budget');assert.equal(budget.result.evaluations,1);assert.equal(budget.result.safeUntil,0);
  const tangent=evaluateAcceleratedCase(runtime,ACCELERATED_PRESETS.tangent);assert.equal(tangent.result.kind,'unresolved');assert.equal(tangent.result.bracket,null);assert.equal(tangent.result.negativeWitness,null);
  const endpoint=evaluateAcceleratedCase(runtime,ACCELERATED_PRESETS.endpoint);assert.equal(endpoint.result.kind,'unresolved');assert.equal(endpoint.result.negativeWitness,null);
  const outside=evaluateAcceleratedCase(runtime,ACCELERATED_PRESETS.outside);assert.equal(outside.result.kind,'none');assert.equal(outside.result.safeUntil,2);
  assert.equal(evaluateAcceleratedCase(runtime,{horizonSeconds:0}).result.kind,'none');
});

function documentHarness(){
  const listeners=new Map(),elements=new Map(),context=new Proxy({}, {get:()=>()=>{},set:()=>true});
  const defaults={'accelerated-mode':'plane','initial-height':'3','initial-velocity':'0',acceleration:'-4','target-velocity':'0','target-acceleration':'0',horizon:'2',tolerance:'0.000001','evaluation-budget':'32768','time-unit':'s',preview:'100'};
  const get=id=>{if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',hidden:false,disabled:true,width:900,height:440,setAttribute(name,value){this[name]=value;},getContext(){return context;},addEventListener(type,callback){listeners.set(`${id}:${type}`,callback);}});return elements.get(id);};
  return {doc:{getElementById:get},get,fire:(id,type='click')=>{const listener=listeners.get(`${id}:${type}`);assert.ok(listener,`listener ${id}:${type}`);return listener();}};
}

test('UI queries actual WASM, preserves s/ms inputs and shows both distinct bracket endpoints',async()=>{
  const ui=documentHarness();let calls=0;const actual={get diagnostics(){return runtime.diagnostics;},queryAcceleratedPlane(...args){calls++;return runtime.queryAcceleratedPlane(...args);},queryAcceleratedSpheres(...args){calls++;return runtime.queryAcceleratedSpheres(...args);}};
  const lab=await initializeAcceleratedLab({doc:ui.doc,loadRuntime:async()=>actual});assert.equal(calls,2);assert.equal(ui.get('accelerated-controls').disabled,false);
  const first=lab.getState();entry(first.result,1,1e-6);assert.match(ui.get('result-bracket').textContent,new RegExp(String(first.result.bracket[0]).replaceAll('.','\\.')));assert.ok(ui.get('result-bracket').textContent.includes(String(first.result.bracket[1])));
  ui.get('time-unit').value='ms';ui.fire('time-unit','change');close(Number(ui.get('horizon').value),2000);close(Number(ui.get('tolerance').value),0.001);close(lab.getState().source.horizonSeconds,2);close(lab.getState().source.settings.timeTolerance,1e-6);assert.equal(ui.get('horizon').max,'6000');
  ui.get('time-unit').value='s';ui.fire('time-unit','change');close(Number(ui.get('horizon').value),2);close(Number(ui.get('tolerance').value),1e-6);assert.equal(ui.get('horizon').max,'6');
  ui.get('accelerated-mode').value='spheres';ui.fire('accelerated-mode','change');assert.equal(ui.get('target-controls').hidden,false);assert.match(ui.get('result-explanation').textContent,/終点では離れ/);assert.equal(ui.get('equation-unit').textContent,'m²');
  const beforePreview=calls,result=lab.getState().result;ui.get('preview').value='50';ui.fire('preview','input');assert.equal(calls,beforePreview);assert.equal(lab.getState().result,result);assert.match(ui.get('preview-time').textContent,/1 s/);
  const record=JSON.parse(ui.get('accelerated-json').textContent);assert.equal(record.diagnostics.backend,'C++ WebAssembly');assert.deepEqual(record.endpointInput.a.position,[0,-5,0]);assert.equal(record.input.parameters.preview,0.5);
  ui.get('horizon').value='0';ui.fire('horizon','input');assert.equal(lab.getState().result.kind,'none');assert.match(ui.get('result-prefix').textContent,/初期点のみ/);
});

test('UI presets keep proven prefix, entry and unresolved separate, including witness without bracket',async()=>{
  const ui=documentHarness(),lab=await initializeAcceleratedLab({doc:ui.doc,loadRuntime:async()=>runtime});
  ui.fire('preset-boundary');assert.equal(lab.getState().result.reason,'initial_boundary');assert.match(ui.get('result-prefix').textContent,/証明なし/);assert.match(ui.get('result-bracket').textContent,/なし/);
  ui.fire('preset-budget');assert.equal(lab.getState().result.reason,'evaluation_budget');assert.match(ui.get('result-prefix').textContent,/初期点のみ/);assert.match(ui.get('result-kind').textContent,/未解決/);
  let witnessBudget=null;for(let n=2;n<=20;n++){const r=evaluateAcceleratedCase(runtime,{maxEvaluations:n}).result;if(r.kind==='unresolved'&&r.negativeWitness!==null){witnessBudget=n;break;}}assert.notEqual(witnessBudget,null);
  ui.get('evaluation-budget').value=String(witnessBudget);ui.fire('evaluation-budget','input');assert.equal(lab.getState().result.kind,'unresolved');assert.match(ui.get('result-explanation').textContent,/負の点があっても/);assert.equal(lab.getState().result.bracket,null);
  ui.fire('preset-outside');assert.equal(lab.getState().result.kind,'none');assert.match(ui.get('result-prefix').textContent,/\[0, 2\] s/);
  ui.fire('preset-tangent');assert.equal(lab.getState().result.kind,'unresolved');ui.fire('preset-endpoint');assert.equal(lab.getState().result.kind,'unresolved');
  ui.fire('preset-pass');entry(lab.getState().result,1,1e-6);assert.match(ui.get('result-endpoint').textContent,/分離を証明/);
});

test('invalid UI input removes stale proofs and recovery calls actual WASM again',async()=>{
  const ui=documentHarness();let calls=0,rejectNext=false,malformedNext=false;
  const actual={get diagnostics(){return runtime.diagnostics;},queryAcceleratedPlane(...args){calls++;if(rejectNext){rejectNext=false;throw new Error('native query rejected fixture');}const result=runtime.queryAcceleratedPlane(...args);if(malformedNext){malformedNext=false;return {...result,valueAtSafe:null};}return result;},queryAcceleratedSpheres(...args){calls++;return runtime.queryAcceleratedSpheres(...args);}};
  const lab=await initializeAcceleratedLab({doc:ui.doc,loadRuntime:async()=>actual}),before=calls;
  ui.get('initial-height').value='NaN';ui.fire('initial-height','input');assert.equal(lab.getState(),null);assert.equal(calls,before);assert.equal(ui.get('result-bracket').textContent,'—');assert.equal(ui.get('preview-time').textContent,'図示時刻: —');assert.match(ui.get('accelerated-error').textContent,/照会できません/);assert.equal(JSON.parse(ui.get('accelerated-json').textContent).inputForm['initial-height'],'NaN');
  ui.fire('preset-plane');assert.equal(lab.getState().result.kind,'entry_bracket');assert.equal(ui.get('accelerated-error').hidden,true);
  rejectNext=true;lab.recalculate();assert.equal(lab.getState(),null);assert.match(ui.get('accelerated-error').textContent,/native query rejected/);lab.recalculate();entry(lab.getState().result,1,1e-6);
  malformedNext=true;lab.recalculate();assert.equal(lab.getState(),null);assert.match(ui.get('accelerated-error').textContent,/正値の証拠がありません/);lab.recalculate();entry(lab.getState().result,1,1e-6);
});

test('failed runtime initialization uses no substitute and retry restores real calculations',async()=>{
  const ui=documentHarness();let attempts=0;const lab=await initializeAcceleratedLab({doc:ui.doc,loadRuntime:async()=>{if(attempts++===0)throw new Error('wasm load fixture');return runtime;}});
  assert.equal(lab.getState(),null);assert.equal(ui.get('accelerated-controls').disabled,true);assert.equal(ui.get('accelerated-retry').disabled,false);assert.match(ui.get('accelerated-error').textContent,/wasm load fixture/);
  await lab.retry();entry(lab.getState().result,1,1e-6);assert.equal(ui.get('accelerated-controls').disabled,false);assert.equal(ui.get('accelerated-error').hidden,true);
});

test('lab input bounds and unavailable API are explicit rather than synthetic results',async()=>{
  for(const value of [{height:''},{velocityY:Infinity},{accelerationY:31},{horizonSeconds:7},{timeTolerance:0},{timeTolerance:1e-13},{maxEvaluations:1.5},{maxEvaluations:32769},{preview:2},{mode:'mesh'}])assert.throws(()=>acceleratedCase(value));
  const ui=documentHarness(),lab=await initializeAcceleratedLab({doc:ui.doc,loadRuntime:async()=>({diagnostics:{backend:'unavailable'}})});assert.equal(lab.getState(),null);assert.match(ui.get('accelerated-error').textContent,/APIがありません/);assert.equal(ui.get('accelerated-controls').disabled,true);
});

test('authored HTML/SVG have valid links, unique IDs, unit labels and bounded educational scope',async()=>{
  const url=new URL('../tools/accelerated-lab.html',import.meta.url),html=await readFile(url,'utf8'),svg=await readFile(new URL('../docs/learn/diagrams/accelerated.svg',import.meta.url),'utf8');
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);assert.equal(ids.length,new Set(ids).size);
  for(const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)){const target=new URL(match[1],url);if(target.protocol==='file:'){const fragment=target.hash.slice(1);target.hash='';await access(target);if(fragment)assert.ok((await readFile(target,'utf8')).includes(`id="${fragment}"`));}}
  for(const preset of Object.keys(ACCELERATED_PRESETS))assert.ok(ids.includes(`preset-${preset}`));
  assert.match(html,/<script type="module" src="accelerated-lab\.mjs(?:\?[^"]*)?"><\/script>/);assert.match(html,/m\/s²/);assert.match(html,/一点の厳密時刻/);assert.match(html,/持続接触/);assert.match(html,/file:\/\//);
  assert.match(svg,/<title id="title">/);assert.match(svg,/<desc id="desc">/);assert.match(svg,/拡大/);assert.equal(acceleratedCase(ACCELERATED_DEFAULTS).horizonSeconds,2);
});
