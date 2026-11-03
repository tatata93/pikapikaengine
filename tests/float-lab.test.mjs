import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {FloatLabController,floatRenderItems,initializeFloatLab,rollAngle} from '../tools/float-lab.mjs';

const close=(actual,expected,tolerance=1e-9)=>assert.ok(Math.abs(actual-expected)<=tolerance,`${actual} != ${expected}`);
let sharedBytes;
async function simulation(mode='heave') {
  sharedBytes??=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
  const {createFloatSimulation}=await import('../engine/simulation.mjs');
  return createFloatSimulation({mode,wasmBytes:sharedBytes});
}

test('float controller operates the actual C++ WASM state and converges to the independent heave reference',async t=>{
  const sim=await simulation();t.after(()=>sim.dispose());const controller=new FloatLabController(sim);
  assert.equal(sim.diagnostics.backend,'C++ WebAssembly');assert.equal(controller.running,false);
  close(controller.current.position[1],0.1);close(controller.current.time,0);close(controller.current.initialEnergy,800,1e-6);
  controller.step();close(controller.current.time,1/120);assert.notEqual(controller.current.position[1],0.1);
  controller.reset('heave');controller.running=true;for(let frame=0;frame<120;frame++)controller.advance(1/60);
  close(controller.current.time,2,1e-12);assert.equal(controller.totalTicks,240);assert.equal(controller.current.contacts,0);
  close(controller.current.position[1],0.1*Math.cos(Math.sqrt(10)*2),2e-5);
  close(controller.current.linearVelocity[1],-0.1*Math.sqrt(10)*Math.sin(Math.sqrt(10)*2),1e-4);
  assert.ok(controller.maxEnergyError<0.001);assert.equal(controller.clock.droppedSeconds,0);
});

test('rendered 30/60/120fps share the same WASM trajectory and overload records dropped time',async t=>{
  const results=[];
  for(const fps of [30,60,120]) {
    const sim=await simulation();t.after(()=>sim.dispose());const controller=new FloatLabController(sim);controller.running=true;
    for(let frame=0;frame<fps*2;frame++)controller.advance(1/fps);
    results.push(controller.current);
  }
  for(const state of results.slice(1)){assert.deepEqual(state.position,results[0].position);assert.deepEqual(state.orientation,results[0].orientation);assert.deepEqual(state.linearVelocity,results[0].linearVelocity);}
  const sim=await simulation();t.after(()=>sim.dispose());const overloaded=new FloatLabController(sim);overloaded.running=true;overloaded.advance(1);
  assert.equal(overloaded.totalTicks,24);close(overloaded.current.time,0.2);close(overloaded.clock.droppedSeconds,0.8);
});

test('roll state is integrated in WASM and rendered from shortest quaternion interpolation with a body offset',async t=>{
  const sim=await simulation('roll');t.after(()=>sim.dispose());const controller=new FloatLabController(sim);controller.reset('roll');
  close(controller.current.position[1],-4);close(rollAngle(controller.current.orientation),0.15);close(controller.current.mass,32000);
  const initialAngle=rollAngle(controller.current.orientation),initialEnergy=controller.current.totalEnergy;
  controller.step();assert.ok(rollAngle(controller.current.orientation)<initialAngle);
  const pose=controller.pose(0.5);close(Math.hypot(...pose.orientation),1,1e-12);
  close(pose.hullPosition[0]-pose.position[0],-0.5*Math.sin(rollAngle(pose.orientation)),1e-12);
  close(pose.hullPosition[1]-pose.position[1],0.5*Math.cos(rollAngle(pose.orientation)),1e-12);
  const body=floatRenderItems(controller,0.5).at(-2);assert.deepEqual(body.orientation,pose.orientation);assert.deepEqual(body.position,pose.hullPosition);
  controller.running=true;for(let frame=1;frame<240;frame++)controller.advance(1/120);
  close(controller.current.time,2,1e-12);assert.ok(Math.abs(controller.current.totalEnergy-initialEnergy)/initialEnergy<0.001);assert.equal(controller.current.contacts,0);
});

function documentHarness() {
  const listeners=new Map(),elements=new Map(),ctx=new Proxy({}, {get:()=>()=>{},set:()=>true});
  function get(id){if(!elements.has(id))elements.set(id,{value:id==='float-mode'?'heave':'',textContent:'',disabled:true,hidden:false,width:850,height:220,dataset:{},
    setAttribute(name,value){this[name]=value;},getContext(){return ctx;},addEventListener(type,callback){listeners.set(`${id}:${type}`,callback);}});return elements.get(id);}
  const doc={hidden:false,getElementById:get,addEventListener(type,callback){listeners.set(`document:${type}`,callback);}};
  return {doc,get,fire:(id,type='click')=>listeners.get(`${id}:${type}`)()};
}

test('real WASM UI controls run, pause, step, switch mode, preserve telemetry and pause on hidden tabs',async t=>{
  const ui=documentHarness(),frames=[],renders=[],sim=await simulation();
  const renderer={render(items,camera,time){renders.push({items,camera,time});}};
  const mounted=await initializeFloatLab({doc:ui.doc,requestFrame:callback=>frames.push(callback),createSimulation:async()=>sim,createRenderer:async()=>renderer});
  assert.ok(mounted);t.after(()=>mounted.dispose());assert.equal(ui.get('float-run').disabled,false);assert.match(ui.get('float-status').textContent,/停止中/);
  frames.shift()(0);ui.fire('float-run');frames.shift()(1000/60);assert.equal(mounted.controller.totalTicks,2);assert.ok(renders.length>=2);
  ui.fire('float-run');const pausedTime=mounted.controller.current.time;frames.shift()(1000/30);close(mounted.controller.current.time,pausedTime);
  ui.fire('float-step');close(mounted.controller.current.time,pausedTime+1/120);assert.equal(mounted.controller.running,false);
  ui.get('float-mode').value='roll';ui.fire('float-mode','change');close(mounted.controller.current.time,0);close(rollAngle(mounted.controller.current.orientation),0.15);assert.match(ui.get('mode-description').textContent,/32000/);
  ui.fire('float-run');ui.doc.hidden=true;ui.fire('document','visibilitychange');assert.equal(mounted.controller.running,false);
  frames.shift()(5000);close(mounted.controller.current.time,0);
  const report=mounted.report();assert.equal(report.simulation.diagnostics.backend,'C++ WebAssembly');assert.ok(report.events.some(event=>event.type==='visibility-pause'));
  assert.equal(report.render.gpuMs,null);assert.ok(report.render.samples.length>0);assert.equal(report.simulation.current.contacts,0);
  ui.fire('float-inspect');const summary=JSON.parse(ui.get('float-report').value);
  assert.equal(summary.simulation.ticks,undefined);assert.equal(summary.render.samples,undefined);
  assert.ok(ui.get('float-report').value.length<10000);assert.ok(ui.get('float-report-link').href.startsWith('blob:'));
  ui.fire('float-reset');close(mounted.controller.current.time,0);assert.equal(mounted.controller.mode,'roll');
});

test('failed WASM initialization stays unavailable and never substitutes generated motion',async()=>{
  const ui=documentHarness(),frames=[];
  const mounted=await initializeFloatLab({doc:ui.doc,requestFrame:callback=>frames.push(callback),createSimulation:async()=>{throw new Error('WASM fixture cannot be loaded');},createRenderer:async()=>{throw new Error('should not create GPU');}});
  assert.equal(mounted,null);assert.equal(ui.get('float-run').disabled,true);assert.equal(frames.length,0);assert.match(ui.get('float-error').textContent,/WASM fixture/);
});

test('float lab keeps real controls, readable limits and valid module entry',async()=>{
  const html=await readFile(new URL('../tools/float-lab.html',import.meta.url),'utf8');
  for(const id of ['float-mode','float-run','float-step','float-reset','float-download','float-time','float-energy-error','float-dropped'])assert.ok(html.includes(`id="${id}"`));
  assert.match(html,/<script type="module" src="float-lab\.mjs(?:\?[^"]*)?"><\/script>/);assert.match(html,/CFD/);assert.match(html,/接触なし/);
});
