import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {RobotBackCover,COVER_ID,COVER_UPDATE_TICKS} from '../samples/back-cover.mjs';
import {RobotGame} from '../samples/robot.mjs';
import {Scene} from '../engine/scene.mjs';
import {FixedClock} from '../engine/time.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {copyDerivedMeshRenderVertices} from '../engine/derived-render.mjs';
import {Renderer} from '../engine/renderer.mjs';
import {createBoxMesh} from '../engine/mesh.mjs';

const source=await readFile(new URL('../assets/robot-back-cover.skin.json',import.meta.url),'utf8');
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const player={p:[4,6,8],previous:[2,4,6],yaw:Math.PI/2},camera={eye:[0,10,40],target:[0,4,0]},base=[{id:'level',type:'box'}];
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const flush=async()=>{await Promise.resolve();await Promise.resolve();await Promise.resolve();};
function mock(){
 const calls=[],cache=new Map(),checks=[];return {calls,cache,checks,maximum:128,
  dropMesh(id){return cache.delete(id);},validateBudget(items){if(items.length>this.maximum)throw new Error('budget');},
  render(items,camera,time){calls.push({items,camera,time,kind:'normal'});for(const item of items)if(item.id===COVER_ID)cache.set(item.id,item.mesh);},
  renderChecked(items,camera,time){this.render(items,camera,time);calls.at(-1).kind='checked';const d=deferred();checks.push(d);return d.promise;}
 };
}
async function ready(options={}){const renderer=mock(),cover=new RobotBackCover(renderer,options);await cover.load({loadRuntime:async()=>runtime,fetchSource:async()=>source});assert.equal(cover.state,'ready');return {renderer,cover};}
function draw(cover,options={}){return cover.render(base,camera,1,player,1,options);}

test('fixed drive distinguishes boost consumption and speed; reset and pause do not integrate wall time',async()=>{
 const {cover}=await ready();for(let i=0;i<120;i++)cover.step(1/120,{boostActive:true,horizontalSpeed:0});assert.equal(cover.u,0);
 for(let i=0;i<30;i++)cover.step(1/120,{horizontalSpeed:32});assert.equal(cover.u,.25);
 for(let i=0;i<30;i++)cover.step(1/120,{boostActive:true,horizontalSpeed:80});assert.equal(cover.u,1);
 for(let i=0;i<31;i++)cover.step(1/120,{});assert.equal(cover.u,0);
 assert.throws(()=>cover.step(1/60,{}));assert.throws(()=>cover.step(1/120,{horizontalSpeed:NaN}));
 cover.reset();assert.equal(cover.tick,0);assert.equal(cover.u,0);assert.equal(cover.previousU,0);assert.equal(COVER_UPDATE_TICKS,2);
});
test('full Source to derived token is mounted with player interpolation and yaw; one full frame checked once',async()=>{
 const {cover,renderer}=await ready();cover.step(1/120,{boostActive:true,horizontalSpeed:80});const items=cover.render(base,camera,1,player,.5);
 assert.equal(items.length,2);assert.strictEqual(items[0],base[0]);const item=items[1];assert.equal(item.id,COVER_ID);assert.equal(item.type,'derived-mesh');assert.equal(item.mesh.floatCount,72);assert.equal(copyDerivedMeshRenderVertices(item.mesh).byteLength,288);
 assert.ok(Math.abs(item.position[0]-(3-1.32))<1e-12);assert.equal(item.position[1],5+2.65);assert.equal(item.position[2],7);assert.equal(item.yaw,player.yaw);
 assert.equal(renderer.calls.length,1);assert.equal(renderer.calls[0].kind,'checked');assert.strictEqual(renderer.calls[0].items,items);assert.equal(cover.sampleClipSeconds,cover.u*.5);assert.equal(cover.records[0].state,'completed');
 renderer.checks[0].resolve();await flush();assert.equal(cover.counts.validated,1);
});
test('a pending validation never stops normal frames or accumulates new checks; latest scheduled state is explicit',async()=>{
 const {cover,renderer}=await ready();draw(cover);const first=cover.token;
 for(let i=0;i<24;i++){cover.step(1/120,{boostActive:true,horizontalSpeed:80});draw(cover);}
 assert.equal(renderer.calls.length,25);assert.equal(renderer.checks.length,1);assert.equal(cover.counts.queries,1);assert.equal(cover.token,first);assert.equal(cover.tick,24);assert.ok(Math.abs(cover.u-.8)<1e-15);assert.equal(cover.maximumTokenAgeSeconds,.2);
 renderer.checks[0].resolve();await flush();draw(cover);assert.equal(renderer.checks.length,2);assert.equal(cover.counts.queries,2);assert.equal(cover.sampleTick,24);assert.ok(cover.counts.omittedScheduled>0);assert.ok(cover.counts.deferredFrames>=24);
 renderer.checks[1].resolve();await flush();const count=cover.counts.queries;draw(cover,{paused:true});draw(cover,{paused:true});assert.equal(cover.counts.queries,count);
});
test('reset while pending retires the old token, prevents resurrection and waits for its one check slot',async()=>{
 const {cover,renderer}=await ready();draw(cover);const old=cover.token;cover.reset();assert.equal(renderer.cache.has(COVER_ID),false);
 draw(cover);assert.equal(renderer.checks.length,1);assert.equal(renderer.calls.at(-1).items.length,1);
 renderer.checks[0].reject(new Error('old play'));await flush();assert.equal(cover.failure,null);assert.equal(cover.token,null);draw(cover);assert.notEqual(cover.token,old);assert.equal(renderer.checks.length,2);
 renderer.checks[1].resolve();await flush();assert.equal(cover.state,'ready');
});
test('hidden invalidation keeps source and fixed drive, drops token and requires explicit resume',async()=>{
 const {cover,renderer}=await ready();draw(cover);renderer.checks[0].resolve();await flush();const original=cover.authorSource;
 cover.step(1/120,{boostActive:true,horizontalSpeed:80});const u=cover.u;cover.suspend();draw(cover);assert.equal(renderer.calls.at(-1).items.length,1);assert.equal(cover.token,null);assert.equal(cover.u,u);assert.equal(cover.authorSource,original);
 cover.resume();draw(cover);assert.equal(renderer.calls.at(-1).items.length,2);renderer.checks[1].resolve();await flush();
});
test('GPU rejection removes only cover and checks a complete base recovery; recovery failure is fatal',async()=>{
 const fatals=[],{cover,renderer}=await ready({onFatal:e=>fatals.push(e)});draw(cover);renderer.checks[0].reject(new Error('validation'));await flush();
 assert.equal(cover.failure.stage,'gpu');assert.equal(cover.token,null);assert.equal(renderer.cache.has(COVER_ID),false);draw(cover);
 assert.equal(renderer.calls.at(-1).kind,'checked');assert.deepEqual(renderer.calls.at(-1).items,base);renderer.checks[1].resolve();await flush();assert.equal(cover.counts.recoveries,1);assert.equal(cover.state,'failed');assert.equal(fatals.length,0);
 cover.reset();draw(cover);renderer.checks[2].reject(new Error('queue'));await flush();draw(cover);renderer.checks[3].reject(new Error('base lost'));await flush();assert.deepEqual(fatals,['base lost']);
});
test('numeric failure and conflicting or exhausted level budgets preserve the base frame without fallback',async()=>{
 const {cover,renderer}=await ready();draw(cover);renderer.checks[0].resolve();await flush();
 cover.runtime={sampleMotion:runtime.sampleMotion.bind(runtime),deformSkin:()=>({status:'numerical_failure'})};cover.step(1/120,{boostActive:true,horizontalSpeed:80});cover.step(1/120,{boostActive:true,horizontalSpeed:80});draw(cover);
 assert.equal(cover.failure.stage,'source');assert.equal(cover.token,null);assert.deepEqual(renderer.calls.at(-1).items,base);assert.equal(renderer.checks.length,1);
 cover.runtime=runtime;cover.reset();renderer.maximum=1;draw(cover);assert.equal(cover.failure.stage,'budget');assert.deepEqual(renderer.calls.at(-1).items,base);
 cover.reset();renderer.maximum=128;const conflicting=[{id:COVER_ID,type:'mesh'}];cover.render(conflicting,camera,1,player);assert.equal(cover.failure.stage,'budget');assert.deepEqual(renderer.calls.at(-1).items,conflicting);
 cover.reset();const level=Array.from({length:128},(_,i)=>({id:'level-'+i,type:'mesh',mesh:createBoxMesh()}));
 renderer.maxInstances=4096;renderer.maxMeshes=128;renderer.maxTriangles=262144;renderer.validateBudget=Renderer.prototype.validateBudget;
 assert.doesNotThrow(()=>renderer.validateBudget(level));cover.render(level,camera,1,player);assert.equal(cover.failure.stage,'budget');assert.strictEqual(renderer.calls.at(-1).items,level);assert.equal(level.length,128);
});
test('asset/runtime load errors are explicit; retry and superseded or disposed async loads cannot publish old source',async()=>{
 const renderer=mock(),cover=new RobotBackCover(renderer);await cover.load({loadRuntime:async()=>{throw new Error('missing SDK');}});assert.equal(cover.failure.stage,'runtime');draw(cover);assert.equal(renderer.calls.at(-1).items.length,1);
 await cover.load({loadRuntime:async()=>runtime,fetchSource:async()=>'{bad'});assert.equal(cover.failure.stage,'asset');
 const old=deferred(),pending=cover.load({loadRuntime:async()=>runtime,fetchSource:()=>old.promise});await flush();await cover.load({loadRuntime:async()=>runtime,fetchSource:async()=>source});old.resolve('{bad');await pending;assert.equal(cover.state,'ready');assert.equal(cover.failure,null);
 await cover.load({loadRuntime:async()=>runtime,fetchSource:async()=>'{bad'});cover.reset();draw(cover);assert.equal(cover.state,'failed');assert.equal(cover.failure.stage,'asset');assert.equal(cover.token,null);assert.deepEqual(renderer.calls.at(-1).items,base);
 const late=deferred(),loading=cover.load({loadRuntime:()=>late.promise,fetchSource:async()=>source});cover.dispose();late.resolve(runtime);await loading;assert.equal(cover.state,'disposed');assert.throws(()=>draw(cover),/disposed/);
});
test('invalid clocks fail explicitly and report snapshots cannot mutate live telemetry',async()=>{
 const {cover}=await ready();const original=cover.now;cover.now=()=>NaN;draw(cover);assert.equal(cover.failure.stage,'source');assert.equal(cover.records.at(-1).sourceMs,null);cover.now=original;
 const r=cover.report();r.counts.queries=999;r.errors[0].message='forged';assert.notEqual(cover.counts.queries,999);assert.notEqual(cover.errors[0].message,'forged');
});
test('render frequencies preserve full game state and fixed cover drive; drawing cannot advance physics',async()=>{
 const outcomes=[];
 for(const fps of [30,60,120,144]){
  const {cover,renderer}=await ready(),game=new RobotGame(new Scene()),reference=new RobotGame(new Scene()),clock=new FixedClock();game.state=reference.state='playing';
  for(let frame=0;frame<fps*2;frame++){
   const alpha=clock.advance(1/fps,(dt,tick)=>{const input={forward:tick<180,boost:tick<120,fire:true,yaw:.4};game.step(dt,input);reference.step(dt,input);cover.step(dt,game.drive);});
   cover.render(game.view(alpha),camera,game.time,game.player,alpha);renderer.checks.at(-1)?.resolve();await flush();
  }
  assert.deepEqual(game.player,reference.player);assert.deepEqual(game.enemies,reference.enemies);assert.deepEqual(game.projectiles,reference.projectiles);assert.equal(game.time,reference.time);
  outcomes.push({player:game.player,enemies:game.enemies,projectiles:game.projectiles,kills:game.kills,wave:game.wave,u:cover.u,tick:cover.tick,drive:game.drive});
  assert.equal(cover.authorSource,source.trim());assert.ok(cover.records.every(r=>r.state==='completed'));assert.equal(clock.droppedSeconds,0);
 }
 for(const value of outcomes)assert.deepEqual(value,outcomes[0]);
});
test('authored idle speed band settles at the exact rest clip and stops repeated skin queries',async()=>{
 const {cover,renderer}=await ready(),game=new RobotGame(new Scene());game.state='playing';
 for(let tick=0;tick<240;tick++){game.step(1/120,{forward:tick<30});cover.step(1/120,game.drive);cover.render(game.view(),camera,game.time,game.player);renderer.checks.at(-1)?.resolve();await flush();}
 assert.equal(cover.u,0);assert.equal(cover.sampleClipSeconds,0);const queries=cover.counts.queries;
 for(let tick=0;tick<60;tick++){game.step(1/120,{});cover.step(1/120,game.drive);cover.render(game.view(),camera,game.time,game.player);renderer.checks.at(-1)?.resolve();await flush();}
 assert.equal(cover.counts.queries,queries);assert.ok(cover.counts.reused>0);
});
