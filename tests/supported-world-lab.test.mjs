import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {SUPPORTED_DT,SUPPORTED_DEFAULTS,SUPPORTED_PRESETS,SUPPORTED_SETTINGS,supportedWorldCase,SupportedWorldExperiment,initializeSupportedWorldLab} from '../tools/supported-world-lab.mjs';

const htmlUrl=new URL('../tools/supported-world-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8');
const clone=x=>JSON.parse(JSON.stringify(x));
const near=(a,b,e=1e-12)=>assert.ok(Math.abs(a-b)<=e,`${a} != ${b}`);
test('presets define original frictionless coupled cases with explicit SI loads',()=>{
  assert.equal(Object.keys(SUPPORTED_PRESETS).length,7);assert.equal(Object.keys(SUPPORTED_SETTINGS).length,32);
  for(const preset of Object.keys(SUPPORTED_PRESETS)){
    const source=supportedWorldCase({preset});assert.equal(source.dt,1/120);assert.equal(source.settings.maximumSubstep,1/240);
    for(const b of source.bodies){assert.equal(b.friction,0);assert.equal(b.radius,.5);assert.equal(b.force.length,3);assert.equal(b.torque.length,3);}
    for(const p of source.planes)assert.equal(p.friction,0);
  }
  const floor=supportedWorldCase();assert.deepEqual(floor.bodies[0].force,[2,0,0]);assert.deepEqual(floor.bodies[0].torque,[0,0,.2]);
  const stack=supportedWorldCase({preset:'stack'});assert.deepEqual(stack.bodies.map(b=>b.mass),[1,2,3]);assert.ok(stack.bodies.every(b=>b.force[0]/b.mass===2));
  const wedge=supportedWorldCase({preset:'wedge'});assert.deepEqual(wedge.planes.map(p=>p.normal),[[0,1,0],[.6,.8,0]]);assert.deepEqual(wedge.bodies[0].force,[-6,0,0]);
  const fast=supportedWorldCase({preset:'fast'});assert.deepEqual(fast.bodies.map(b=>b.linearVelocity[0]),[1000,-1000]);assert.ok(fast.bodies.every(b=>b.restitution===1));
  const curve=supportedWorldCase({preset:'curved'});assert.deepEqual(curve.gravity,[0,-4,0]);assert.equal(curve.bodies[1].isStatic,true);
});
test('parameters reject blank nonfinite and fractional budgets without rounding into defaults',()=>{
  for(const input of [{preset:'unknown'},{maxSegments:''},{maxSegments:1.2},{maxSegments:100001},{maximumSubstep:NaN},{maximumSubstep:0},{maximumSubstep:.2}])assert.throws(()=>supportedWorldCase(input));
  assert.equal(supportedWorldCase({maxSegments:'1'}).settings.maxSegments,1);
});

// Scripted API fixture tests UI contracts only. It is never imported by the lab,
// and is not evidence for numerical physics (the actual-WASM tests follow later).
function fixtureRuntime({mutateFailure=false}={}){
  let next=0;const worlds=[],runtime={diagnostics:{backend:'fixture API (not physics)',wasmBytes:0,buildId:'UI-only'},worlds};
  runtime.createWorld=({gravity})=>{
    let time=0,ticks=0;const bodies=new Map(),planes=[],calls=[];
    const info=()=>({gravity:gravity.slice(),bodies:bodies.size,planes:planes.length,time,ticks});
    const world={handle:++next,calls,disposed:false,info,
      addBody(b){bodies.set(b.id,{inertia:[.1,.1,.1],...clone(b)});},addPlane(p){planes.push(clone(p));},
      getBody(id){const b=clone(bodies.get(id));return {...b,angularVelocity:[0,0,0],kineticEnergy:0,time,ticks};},
      setBody(b){bodies.set(b.id,clone(b));},dispose(){this.disposed=true;},
      stepSupported(dt,settings){
        calls.push({dt,settings:clone(settings),loads:[...bodies.values()].map(b=>({id:b.id,force:b.force.slice(),torque:b.torque.slice()}))});
        const success=settings.maxSegments!==1;
        if(success){++ticks;time+=dt;for(const b of bodies.values()){if(!b.isStatic)b.position[0]+=.125;b.force=[0,0,0];b.torque=[0,0,0];}}
        else if(mutateFailure)bodies.values().next().value.position[0]+=1;
        const report={success,failure:success?'none':'segment_budget',advancedDt:success?dt:0,candidateTime:dt/2,attempts:2,acceptedSegments:success?2:1,rejectedAttempts:0,constraintSolves:3,pairQueries:6,guardEvaluations:9,certifiedIntervals:3,minimumAcceptedSubstep:dt/2,maximumGapResidual:1e-12,maximumVelocityResidual:1e-12,maximumPositionErrorEstimate:1e-9,maximumVelocityErrorEstimate:1e-9,maximumOrientationErrorEstimate:0,supportImpulseSum:.1,impactImpulseSum:0,maximumNearContactGap:1e-12,initialMechanicalEnergy:5,finalMechanicalEnergy:5,heldForceWork:0,mechanicalEnergyChange:0,timeRoundoff:0,lastConstraintFailure:'none',lastGuardFailure:'none',eventCount:0,events:[],time,ticks,firstId:0,secondId:0};
        return report;
      }
    };worlds.push(world);return world;
  };return runtime;
}
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[];
  const defaults={'supported-preset':'floor','maximum-substep':String(1000/240),'segment-budget':'4096'};
  const ctx=new Proxy({}, {get:(_t,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const get=id=>{assert.ok(ids.has(id),'missing ID '+id);if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',disabled:false,hidden:false,width:900,height:520,getContext:()=>ctx,addEventListener:(kind,fn)=>listeners.set(id+':'+kind,fn)});return elements.get(id);};
  return {get,draws,doc:{getElementById:get},fire:(id,kind='click')=>{const fn=listeners.get(id+':'+kind);assert.ok(fn,`missing listener ${id}:${kind}`);return fn();}};
}
test('experiment reuses the same World and replaces held loads before every tick',()=>{
  const runtime=fixtureRuntime(),e=new SupportedWorldExperiment(runtime);try{
    assert.equal(e.snapshot().current.info.ticks,0);const handle=e.world.handle;
    for(let i=0;i<3;++i){const s=e.step();assert.equal(s.report.success,true);assert.deepEqual(s.lastRecord.before.bodies[0].force,[2,0,0]);assert.deepEqual(s.lastRecord.after.bodies[0].force,[0,0,0]);assert.deepEqual(s.lastRecord.before.bodies[0].torque,[0,0,.2]);}
    assert.equal(e.world.handle,handle);assert.equal(e.snapshot().current.info.ticks,3);assert.equal(e.world.calls.length,3);assert.ok(e.world.calls.every(c=>c.loads[0].force[0]===2));
    const snap=e.snapshot();snap.current.bodies[0].position[0]=999;assert.notEqual(e.snapshot().current.bodies[0].position[0],999);
  }finally{e.dispose();}
});
test('failure preserves full states and clocks and budget retry does not recreate World',()=>{
  const runtime=fixtureRuntime(),e=new SupportedWorldExperiment(runtime,{maxSegments:1});try{
    const handle=e.world.handle,failed=e.step();assert.equal(failed.report.success,false);assert.equal(failed.lastRecord.worldUnchanged,true);assert.deepEqual(failed.lastRecord.before,failed.lastRecord.after);assert.equal(failed.current.info.time,0);
    const success=e.step({maxSegments:4096});assert.equal(success.report.success,true);assert.equal(e.world.handle,handle);assert.equal(runtime.worlds.length,1);assert.equal(success.current.info.ticks,1);
    assert.throws(()=>e.step({force:[0,0,0]}));
  }finally{e.dispose();}
});
test('a backend that modifies state on reported failure is explicitly rejected',()=>{
  const e=new SupportedWorldExperiment(fixtureRuntime({mutateFailure:true}),{maxSegments:1});try{assert.throws(()=>e.step(),/保持されません/);}finally{e.dispose();}
});
test('manual UI never starts itself, yields each four ticks, and stores full before/after JSON',async()=>{
  const ui=harness(),runtime=fixtureRuntime();let yields=0;
  const lab=await initializeSupportedWorldLab({doc:ui.doc,loadRuntime:async()=>runtime,yieldFrame:async()=>{++yields;}});try{
    assert.equal(runtime.worlds[0].calls.length,0);assert.equal(lab.getState().current.info.ticks,0);assert.ok(ui.draws.some(d=>d[0]==='arc'));
    await ui.fire('supported-step-12');assert.equal(lab.getState().current.info.ticks,12);assert.equal(yields,2);near(lab.getState().current.info.time,.1);
    const json=JSON.parse(ui.get('supported-json').textContent);assert.equal(json.records.length,12);assert.equal(json.batch.completed,12);assert.deepEqual(json.lastRecord.before.bodies[0].force,[2,0,0]);assert.equal(json.droppedTime,0);assert.match(ui.get('supported-clock').textContent,/実時間同期なし/);
    ui.fire('supported-reset');assert.equal(lab.getState().current.info.ticks,0);assert.equal(runtime.worlds[0].disposed,true);
  }finally{lab.dispose();}
});
test('UI stops a failed batch and recovers by raising budget on the same World',async()=>{
  const ui=harness(),runtime=fixtureRuntime(),lab=await initializeSupportedWorldLab({doc:ui.doc,loadRuntime:async()=>runtime});try{
    const world=lab.getExperiment().world;ui.get('segment-budget').value='1';await ui.fire('supported-step-96');assert.equal(world.calls.length,1);assert.equal(lab.getState().batch.completed,0);assert.equal(lab.getState().lastRecord.worldUnchanged,true);assert.match(ui.get('supported-invariant').textContent,/完全一致/);
    await ui.fire('supported-budget-retry');assert.equal(lab.getExperiment().world,world);assert.equal(lab.getState().report.success,true);assert.equal(ui.get('segment-budget').value,'4096');
    ui.get('maximum-substep').value='';await lab.run(1);assert.equal(lab.getState(),null);assert.equal(ui.get('supported-bodies').textContent,'—');
    ui.get('maximum-substep').value=String(1000/240);await lab.run(1);assert.equal(lab.getState().current.info.ticks,2);
  }finally{lab.dispose();}
});
test('load failure clears output, retry recovers, and missing kernel API is never replaced',async()=>{
  const ui=harness(),runtime=fixtureRuntime();let fail=true;
  const lab=await initializeSupportedWorldLab({doc:ui.doc,loadRuntime:async()=>{if(fail)throw new Error('offline WASM');return runtime;}});try{
    assert.equal(lab.getState(),null);assert.equal(ui.get('supported-controls').disabled,true);assert.equal(runtime.worlds.length,0);
    fail=false;await lab.retry();assert.equal(lab.getState().current.info.ticks,0);assert.equal(runtime.worlds[0].calls.length,0);
    ui.get('supported-preset').value='stack';ui.fire('supported-preset','change');assert.equal(lab.getState().current.bodies.length,3);
  }finally{lab.dispose();}
  assert.throws(()=>new SupportedWorldExperiment({createWorld:()=>({dispose(){}})}),/支持時間積分API/);
});
test('static lab and lesson have unique IDs and local original diagram links',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
  for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(m[1]))await access(new URL(m[1],htmlUrl));
  const index=await readFile(new URL('../docs/learn/index.html',import.meta.url),'utf8');assert.equal([...index.matchAll(/<article\s/g)].length,20);assert.match(index,/id="supported-world"/);assert.match(html,/摩擦係数0/);assert.match(html,/真の連続運動/);assert.match(html,/src="supported-world-lab\.mjs(?:\?[^\"]*)?"/);
});

let actual;
async function actualRuntime(){
  if(!actual){const {loadSimulationRuntime}=await import('../engine/simulation.mjs');actual=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});}
  assert.equal(actual.diagnostics.backend,'C++ WebAssembly');return actual;
}
function ticks(e,n){let s;for(let j=0;j<n;++j){s=e.step();assert.equal(s.report.success,true,`${e.source.parameters.preset} tick ${j}: ${JSON.stringify(s.report)}`);}return s;}
test('actual WASM floor and loaded unequal stack follow independent ax=2 motion while holding height',async()=>{
  const runtime=await actualRuntime();for(const preset of ['floor','stack']){
    const e=new SupportedWorldExperiment(runtime,{preset});try{const s=ticks(e,12);near(s.current.info.time,.1);assert.equal(s.current.info.ticks,12);
      for(const b of s.current.bodies){near(b.position[0],.01,2e-7);near(b.linearVelocity[0],.2,2e-7);near(b.position[1],preset==='floor'?.5:b.id-.5,2e-7);near(b.linearVelocity[1],0,2e-7);assert.deepEqual(b.force,[0,0,0]);assert.deepEqual(b.torque,[0,0,0]);}
      if(preset==='floor'){near(s.current.bodies[0].angularMomentum[2],.02,2e-9);near(2*Math.atan2(s.current.bodies[0].orientation[2],s.current.bodies[0].orientation[3]),.01,2e-7);}
    }finally{e.dispose();}
  }
});
test('actual WASM nonorthogonal wedge stays balanced and a separating body returns to inelastic support',async()=>{
  const runtime=await actualRuntime();const wedge=new SupportedWorldExperiment(runtime,{preset:'wedge'});try{const s=ticks(wedge,12);for(const x of s.current.bodies[0].position)near(x,0,2e-7);for(const v of s.current.bodies[0].linearVelocity)near(v,0,2e-7);}finally{wedge.dispose();}
  const returning=new SupportedWorldExperiment(runtime,{preset:'return'});try{const s=ticks(returning,12);near(s.current.bodies[0].position[1],.5,2e-7);near(s.current.bodies[0].linearVelocity[1],0,2e-6);assert.ok(s.events.some(e=>e.kind==='impact'));}finally{returning.dispose();}
});
test('actual WASM support and pair impact retain held acceleration and high speed cannot tunnel',async()=>{
  const runtime=await actualRuntime();const e=new SupportedWorldExperiment(runtime,{preset:'collision'});try{const s=ticks(e,12);
    for(const [i,b]of s.current.bodies.entries()){near(b.position[0],[1.01,3.01][i],3e-6);near(b.linearVelocity[0],[.2,20.2][i],3e-6);near(b.position[1],.5,2e-7);}assert.ok(s.events.some(e=>e.kind==='impact'));
  }finally{e.dispose();}
  const fast=new SupportedWorldExperiment(runtime,{preset:'fast'});try{const s=ticks(fast,1);near(s.current.bodies[0].position[0],1-1000*SUPPORTED_DT,3e-6);near(s.current.bodies[1].position[0],1000*SUPPORTED_DT-1,3e-6);near(s.current.bodies[0].linearVelocity[0],-1000,2e-6);near(s.current.bodies[1].linearVelocity[0],1000,2e-6);assert.ok(s.events.some(e=>e.kind==='impact'));}finally{fast.dispose();}
});
test('actual WASM curved support changes normal and releases without exceeding the discrete geometry band',async()=>{
  const e=new SupportedWorldExperiment(await actualRuntime(),{preset:'curved'});try{const s=ticks(e,96),b=s.current.bodies[0];assert.ok(b.position[0]>.5&&b.position[1]<.9);assert.ok(Math.hypot(...b.position)>=1-2e-7);assert.ok(s.events.some(e=>e.kind==='release'));near(b.kineticEnergy+4*b.position[1],4.5,2e-3);
    for(const record of s.records){assert.ok(record.report.maximumGapResidual<=1e-7);assert.equal(record.report.lastGuardFailure,'none');}
  }finally{e.dispose();}
});
test('actual WASM segment failure preserves every value and UI retries on the same handle with loads intact',async()=>{
  const runtime=await actualRuntime(),ui=harness(),lab=await initializeSupportedWorldLab({doc:ui.doc,loadRuntime:async()=>runtime});try{
    const handle=lab.getExperiment().world.handle;ui.get('segment-budget').value='1';await lab.run(12);const failed=lab.getState();assert.equal(failed.report.failure,'segment_budget');assert.equal(failed.current.info.ticks,0);assert.deepEqual(failed.lastRecord.before,failed.lastRecord.after);assert.equal(failed.lastRecord.worldUnchanged,true);
    await ui.fire('supported-budget-retry');const s=lab.getState();assert.equal(lab.getExperiment().world.handle,handle);assert.equal(s.current.info.ticks,1);assert.equal(s.report.success,true);near(s.current.bodies[0].position[0],SUPPORTED_DT**2,2e-9);near(s.current.bodies[0].angularMomentum[2],.2*SUPPORTED_DT,2e-9);assert.deepEqual(s.current.bodies[0].force,[0,0,0]);
  }finally{lab.dispose();}
});
