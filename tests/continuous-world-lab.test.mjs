import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {WORLD_CCD_DEFAULTS,WORLD_CCD_PRESETS,continuousWorldCase,ContinuousWorldExperiment,initializeContinuousWorldLab} from '../tools/continuous-world-lab.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const close=(a,b,tolerance=1e-12)=>assert.ok(Math.abs(a-b)<=tolerance,`${a} != ${b}`);
const parameters=name=>({...WORLD_CCD_DEFAULTS,...WORLD_CCD_PRESETS[name]});

test('actual C++ World completes three impacts with gravity, force and torque held throughout one tick',()=>{
  const e=new ContinuousWorldExperiment(runtime);try{
    assert.equal(runtime.diagnostics.backend,'C++ WebAssembly');const s=e.step();assert.equal(s.report.success,true);assert.equal(s.report.events.length,3);assert.equal(s.report.freeSegments,4);assert.equal(s.info.ticks,1);assert.equal(s.info.time,.06);
    close(s.current.position[0],0,1e-6);close(s.current.position[1],-.5*5.8*.06*.06);close(s.current.linearVelocity[0],-100);close(s.current.linearVelocity[1],-5.8*.06);
    close(s.current.angularMomentum[2],.2*.06);close(2*Math.atan2(s.current.orientation[2],s.current.orientation[3]),.5*(.2/.1)*.06*.06);
    assert.deepEqual(s.initial.force,[0,4,0]);assert.deepEqual(s.initial.torque,[0,0,.2]);assert.deepEqual(s.current.force,[0,0,0]);assert.deepEqual(s.current.torque,[0,0,0]);
    for(const [i,event]of s.report.events.entries()){assert.ok(event.entryBracket[0]<event.entryBracket[1]);assert.ok(event.maximumGap>0&&event.maximumGap<=1e-6);assert.ok(Math.abs(event.respondedAt-[.01,.03,.05][i])<1e-7);}
    assert.throws(()=>e.step(),/リセット/);assert.equal(e.snapshot().info.ticks,1);
  }finally{e.dispose();}
});

test('actual high-speed floor impact cannot tunnel and the full remaining time is retained',()=>{
  const e=new ContinuousWorldExperiment(runtime,parameters('floor'));try{
    const s=e.step();assert.equal(s.report.success,true);assert.equal(s.report.events.length,1);assert.equal(s.info.time,.001);
    const t=3/(10000+Math.sqrt(100000000+30)),v=-10000-10*t,tail=.001-t;
    close(s.current.position[1],.5-v*tail-5*tail*tail,3e-6);close(s.current.linearVelocity[1],-v-10*tail,1e-5);assert.ok(s.current.position[1]>8);
  }finally{e.dispose();}
});

test('event-budget failure rolls back every state and retries the SAME actual World with retained loads',()=>{
  const e=new ContinuousWorldExperiment(runtime,parameters('budget'));try{
    const handle=e.world.handle,initial=e.snapshot(),failed=e.step();assert.equal(failed.report.success,false);assert.equal(failed.report.failure,'event_budget');assert.equal(failed.report.advancedDt,0);assert.ok(failed.report.candidateTime>0);assert.equal(failed.report.events.length,1);
    assert.deepEqual(failed.current,initial.current);assert.deepEqual(failed.info,initial.info);assert.deepEqual(failed.current.force,[0,4,0]);assert.deepEqual(failed.current.torque,[0,0,.2]);
    assert.throws(()=>e.step({forceY:0}),/guardと予算/);const recovered=e.step({maxEventBatches:32});assert.equal(e.world.handle,handle);assert.equal(recovered.report.success,true);assert.equal(recovered.info.ticks,1);close(recovered.current.angularMomentum[2],.012);
  }finally{e.dispose();}
});

test('initial support and root-budget uncertainty remain failures without clock or state changes',()=>{
  const e=new ContinuousWorldExperiment(runtime,parameters('support'));try{
    const before=e.snapshot(),s=e.step();assert.equal(s.report.success,false);assert.equal(s.report.failure,'initial_contact');assert.equal(s.report.advancedDt,0);assert.equal(s.info.time,0);assert.equal(s.info.ticks,0);assert.deepEqual(s.current,before.current);
    e.reset({...parameters('corridor'),maxRootEvaluations:1});const r=e.step();assert.equal(r.report.success,false);assert.equal(r.report.failure,'root_budget');assert.equal(r.info.ticks,0);assert.deepEqual(r.current.force,[0,4,0]);
    assert.equal(e.step({maxRootEvaluations:1000000}).report.success,true);
  }finally{e.dispose();}
});

function harness(){
  const listeners=new Map(),elements=new Map(),context=new Proxy({}, {get:()=>()=>{},set:()=>true});
  const defaults={'world-mode':'corridor','initial-y':'0','initial-speed':'100','gravity-y':'-9.8','force-y':'4','torque-z':'.2','tick-dt':'.06','time-guard':'1e-7','space-guard':'1e-6','event-budget':'32','root-budget':'1000000','time-unit':'s'};
  const get=id=>{if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',hidden:false,disabled:true,width:900,height:360,getContext:()=>context,addEventListener(type,callback){listeners.set(`${id}:${type}`,callback);}});return elements.get(id);};
  return {doc:{getElementById:get},get,fire(id,type='click'){const fn=listeners.get(`${id}:${type}`);assert.ok(fn,`listener ${id}:${type}`);return fn();}};
}

test('UI uses actual WASM single ticks, s/ms conversion and both event bracket endpoints',async()=>{
  const ui=harness(),lab=await initializeContinuousWorldLab({doc:ui.doc,loadRuntime:async()=>runtime});try{
    assert.equal(lab.getState().report,null);assert.equal(ui.get('world-step').disabled,false);assert.equal(ui.get('world-controls').disabled,false);
    ui.get('time-unit').value='ms';ui.fire('time-unit','change');close(Number(ui.get('tick-dt').value),60);close(Number(ui.get('time-guard').value),.0001);assert.equal(lab.getState().input.dt,.06);assert.equal(ui.get('tick-dt').max,'100');
    ui.fire('world-step');const s=lab.getState();assert.equal(s.report.success,true);assert.equal(ui.get('world-step').disabled,true);assert.equal(ui.get('world-ticks').textContent,'1');assert.match(ui.get('world-time').textContent,/0.06 s/);
    for(const event of s.report.events)for(const end of event.entryBracket)assert.ok(ui.get('world-events').textContent.includes(String(end)));
    const record=JSON.parse(ui.get('world-json').textContent);assert.equal(record.diagnostics.backend,'C++ WebAssembly');assert.equal(record.report.events.length,3);assert.deepEqual(record.current.force,[0,0,0]);
    ui.fire('world-reset');assert.equal(lab.getState().info.ticks,0);assert.equal(ui.get('world-step').disabled,false);assert.deepEqual(lab.getState().current.torque,[0,0,.2]);
    ui.get('time-unit').value='s';ui.fire('time-unit','change');close(Number(ui.get('tick-dt').value),.06);close(Number(ui.get('time-guard').value),1e-7);
  }finally{lab.dispose();}
});

test('UI shows discarded candidate events and exposes same-World budget recovery without a reset',async()=>{
  const ui=harness(),lab=await initializeContinuousWorldLab({doc:ui.doc,loadRuntime:async()=>runtime});try{
    ui.fire('preset-budget');ui.fire('world-step');assert.equal(lab.getState().report.failure,'event_budget');assert.equal(ui.get('world-time').textContent,'0 s');assert.equal(ui.get('world-ticks').textContent,'0');assert.match(ui.get('world-events').textContent,/破棄した候補/);assert.equal(ui.get('world-budget-retry').hidden,false);
    ui.fire('world-budget-retry');assert.equal(lab.getState().report.success,true);assert.equal(ui.get('event-budget').value,'32');assert.equal(ui.get('world-budget-retry').hidden,true);close(lab.getState().current.angularMomentum[2],.012);
    ui.fire('preset-support');ui.fire('world-step');assert.equal(lab.getState().report.failure,'initial_contact');assert.match(ui.get('world-outcome').textContent,/初期境界/);assert.equal(ui.get('world-time').textContent,'0 s');
    ui.get('world-mode').value='floor';ui.fire('world-mode','change');assert.equal(ui.get('initial-y').value,'2');ui.fire('world-step');assert.equal(lab.getState().report.success,true);assert.ok(lab.getState().current.position[1]>8);
  }finally{lab.dispose();}
});

test('invalid input clears stale states, and runtime load failures provide no substitute physics',async()=>{
  const ui=harness();let attempts=0;const lab=await initializeContinuousWorldLab({doc:ui.doc,loadRuntime:async()=>{if(attempts++===0)throw new Error('WASM fixture load failure');return runtime;}});try{
    assert.equal(lab.getState(),null);assert.equal(ui.get('world-controls').disabled,true);assert.equal(ui.get('world-retry').disabled,false);assert.match(ui.get('world-error').textContent,/WASM fixture/);
    await lab.retry();ui.fire('world-step');assert.equal(lab.getState().report.success,true);
    ui.get('tick-dt').value='NaN';ui.fire('tick-dt','input');assert.equal(lab.getState(),null);assert.equal(ui.get('world-step').disabled,true);assert.equal(ui.get('world-position').textContent,'—');assert.equal(ui.get('world-events').textContent,'—');assert.equal(JSON.parse(ui.get('world-json').textContent).inputForm['tick-dt'],'NaN');
    ui.fire('preset-corridor');assert.equal(lab.getState().info.time,0);assert.equal(lab.getState().report,null);ui.fire('world-step');assert.equal(lab.getState().report.success,true);assert.equal(ui.get('world-error').hidden,true);
  }finally{lab.dispose();}
});

test('lab bounds and native API exceptions are explicit and recoverable',async()=>{
  for(const value of [{mode:'mesh'},{height:''},{speed:10001},{gravityY:Infinity},{dt:0},{dt:.11},{timeTolerance:1e-13},{spatialTolerance:.001},{maxEventBatches:33},{maxRootEvaluations:1.5}])assert.throws(()=>continuousWorldCase(value));
  const ui=harness();let reject=false,malformed=false;
  const wrapped={get diagnostics(){return runtime.diagnostics;},createWorld(options){const world=runtime.createWorld(options);return new Proxy(world,{get(target,key){if(key==='stepContinuous')return(...args)=>{if(reject){reject=false;throw new Error('native call fixture rejected');}const r=target.stepContinuous(...args);if(malformed){malformed=false;r.events[0].entryBracket.reverse();}return r;};const value=target[key];return typeof value==='function'?value.bind(target):value;}});}};
  const lab=await initializeContinuousWorldLab({doc:ui.doc,loadRuntime:async()=>wrapped});try{reject=true;ui.fire('world-step');assert.equal(lab.getState(),null);assert.match(ui.get('world-error').textContent,/native call fixture/);ui.fire('world-reset');malformed=true;ui.fire('world-step');assert.equal(lab.getState(),null);assert.match(ui.get('world-error').textContent,/bracket/);ui.fire('world-reset');ui.fire('world-step');assert.equal(lab.getState().report.success,true);}finally{lab.dispose();}
});

test('HTML and authored SVG preserve units, accessible links and the bounded W1 scope',async()=>{
  const url=new URL('../tools/continuous-world-lab.html',import.meta.url),html=await readFile(url,'utf8'),svg=await readFile(new URL('../docs/learn/diagrams/continuous-world.svg',import.meta.url),'utf8');
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);assert.equal(ids.length,new Set(ids).size);for(const name of Object.keys(WORLD_CCD_PRESETS))assert.ok(ids.includes(`preset-${name}`));
  for(const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)){const target=new URL(match[1],url);if(target.protocol==='file:'){const fragment=target.hash.slice(1);target.hash='';await access(target);if(fragment)assert.ok((await readFile(target,'utf8')).includes(`id="${fragment}"`));}}
  assert.match(html,/m\/s²/);assert.match(html,/N m/);assert.match(html,/kg m²\/s/);assert.match(html,/一点の厳密TOI/);assert.match(html,/未対応/);assert.match(html,/自動再生/);assert.match(html,/file:\/\//);assert.match(html,/<script type="module" src="continuous-world-lab\.mjs(?:\?[^"]*)?"><\/script>/);
  assert.match(svg,/<title id="title">/);assert.match(svg,/<desc id="desc">/);assert.match(svg,/拡大/);assert.match(svg,/原状保持/);assert.equal(continuousWorldCase().bodies[0].inertia[0],.1);
});
