import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {createMotionSource,defaultMotionSource,serializeMotionSource} from '../engine/motion.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {initializeMotionLab,validateMotionPose} from '../tools/motion-lab.mjs';
const htmlUrl=new URL('../tools/motion-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8'),copy=x=>JSON.parse(JSON.stringify(x));
const close=(a,b,tol=2e-12)=>assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);
// Scripted pose DTO fixture, not FK or interpolation. Deliberate shear and
// time-labelled positions test display/scheduling without a mirror solver.
function fixturePose(source,time,{loop=false}={}){
  const sampledTime=loop?time%source.clip.duration:Math.min(time,source.clip.duration);
  return {status:'completed',requestedTime:time,sampledTime,playback:loop?'loop':'clamp',duration:source.clip.duration,bones:source.bones.map((bone,i)=>({id:bone.id,parentId:bone.parentId,local:copy(bone.rest),localMatrix:[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],worldMatrix:[1,0,0,0,.375,1,0,0,0,0,1,0,i,sampledTime,0,1],worldPosition:[i,sampledTime,0],evaluationRank:i})),evaluationOrder:source.bones.map(b=>b.id)};
}
function fixtureRuntime(){const calls=[];return {calls,diagnostics:{backend:'scripted pose fixture, not FK'},respond:fixturePose,sampleMotion(source,time,options){calls.push(copy({source,time,options}));return copy(this.respond(source,time,options));}};}
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[],frames=new Map(),saves=[];let nextId=1;
  const ctx=new Proxy({}, {get:(_t,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const create=tag=>({tag,value:'',textContent:'',children:[],appendChild(c){this.children.push(c);},replaceChildren(...c){this.children=c;}});
  const get=id=>{assert.ok(ids.has(id),'missing element '+id);if(!elements.has(id))elements.set(id,{...create(id),checked:false,hidden:false,disabled:false,width:800,height:390,files:[],getContext:()=>ctx,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};
  const doc={hidden:false,getElementById:get,createElement:create,addEventListener:(type,fn)=>listeners.set('document:'+type,fn)};
  return {get,doc,draws,frames,saves,saveJson:(name,text)=>saves.push({name,text}),requestFrame:fn=>{const id=nextId++;frames.set(id,fn);return id;},cancelFrame:id=>frames.delete(id),frame:timestamp=>{const first=frames.entries().next().value;assert.ok(first,'no scheduled frame');frames.delete(first[0]);first[1](timestamp);},fire:(id,type='input')=>{const fn=listeners.get(id+':'+type);assert.ok(fn,'missing listener '+id+':'+type);return fn();}};
}
const initialize=(ui,runtime=fixtureRuntime(),extra={})=>initializeMotionLab({doc:ui.doc,loadRuntime:async()=>runtime,requestFrame:ui.requestFrame,cancelFrame:ui.cancelFrame,saveJson:ui.saveJson,...extra});

test('initial paused pose uses the common sampler and preserves original matrices and all source IDs',async()=>{
  const ui=harness(),runtime=fixtureRuntime(),lab=await initialize(ui,runtime);assert.equal(lab.getState().playing,false);assert.equal(ui.frames.size,0);assert.equal(runtime.calls.length,1);assert.equal(runtime.calls[0].time,0);assert.equal(ui.get('mo-bones').children.length,4);
  assert.equal(lab.getState().pose.bones[2].worldMatrix[4],.375);assert.equal(JSON.parse(ui.get('mo-pose-json').textContent).bones[2].worldMatrix[4],.375);assert.equal(ui.saves.length,0);assert.ok(ui.draws.some(d=>d[0]==='arc'));
  const bad=fixturePose(defaultMotionSource(),0);bad.bones[0].worldMatrix[4]=NaN;assert.throws(()=>validateMotionPose(defaultMotionSource(),bad),/原出力/);
});

test('key edit applies via source API with hidden bone tracks preserved; Undo Redo and save reload retain all originals',async()=>{
  const ui=harness(),r=fixtureRuntime(),lab=await initialize(ui,r),source=defaultMotionSource();source.bones.push({id:99,parentId:1,name:'未選択の保持用',rest:{position:[0,0,1],rotation:[0,0,0,-2],scale:[1,2,1]}});source.clip.tracks.push({boneId:99,interpolation:'step',keys:[{time:0,position:[0,0,1],rotation:[0,0,0,-2],scale:[1,2,1]}]});await lab.loadSource(serializeMotionSource(source));
  const before=lab.getState().source;ui.get('mo-px').value='2';ui.fire('mo-px');assert.equal(lab.getState().pose,null);assert.equal(lab.getState().pendingEdit,true);assert.equal(ui.get('mo-playback').disabled,true);ui.fire('mo-apply','click');const after=lab.getState().source;
  assert.equal(after.clip.tracks.find(t=>t.boneId===2).keys[0].position[0],2);assert.deepEqual(after.bones.find(b=>b.id===99),before.bones.find(b=>b.id===99));assert.deepEqual(after.clip.tracks.find(t=>t.boneId===99),before.clip.tracks.find(t=>t.boneId===99));assert.equal(r.calls.at(-1).source.clip.tracks.find(t=>t.boneId===2).keys[0].position[0],2);
  lab.undo();assert.deepEqual(lab.getState().source,before);lab.redo();assert.deepEqual(lab.getState().source,after);assert.equal(lab.getState().playing,false);ui.fire('mo-save','click');assert.equal(ui.saves.length,1);await lab.loadSource(ui.saves[0].text);assert.deepEqual(lab.getState().source,after);assert.equal(lab.getState().playing,false);
});

test('add and remove key operations preserve IDs and remove the last track back to rest with Undo',async()=>{
  const ui=harness(),lab=await initialize(ui);ui.get('mo-bone').value='4';ui.fire('mo-bone','change');assert.equal(ui.get('mo-key').value,'rest');ui.get('mo-key-time').value='1.25';ui.fire('mo-key-time');ui.get('mo-pz').value='.5';ui.fire('mo-pz');lab.apply();assert.equal(lab.getState().source.clip.tracks.find(t=>t.boneId===4).keys[0].time,1.25);
  lab.remove();assert.equal(lab.getState().source.clip.tracks.some(t=>t.boneId===4),false);assert.deepEqual(lab.getState().source.bones.map(b=>b.id),[1,2,3,4]);lab.undo();assert.equal(lab.getState().source.clip.tracks.find(t=>t.boneId===4).keys[0].position[2],.5);
});

test('playback samples absolute timestamps equally at 30 60 and 120Hz and stops on hiding or clamp end',async()=>{
  const poses=[];for(const hz of [30,60,120]){const ui=harness(),runtime=fixtureRuntime(),lab=await initialize(ui,runtime);assert.equal(lab.play(),true);ui.frame(100);for(let j=1;j<=hz;++j)ui.frame(100+j*1000/hz);poses.push(lab.getState().pose);assert.equal(runtime.calls.at(-1).time,1);assert.equal(lab.getState().playing,true);ui.doc.hidden=true;ui.fire('document','visibilitychange');assert.equal(lab.getState().playing,false);assert.equal(ui.frames.size,0);}
  assert.deepEqual(poses[0],poses[1]);assert.deepEqual(poses[1],poses[2]);
  const ui=harness(),lab=await initialize(ui);lab.play();ui.frame(0);ui.frame(2500);assert.equal(lab.getState().playing,false);assert.equal(lab.getState().pose.sampledTime,2);assert.equal(ui.frames.size,0);
});

test('scrub loop step and source changes pause playback; key selection uses original quaternion rather than pose decomposition',async()=>{
  const ui=harness(),r=fixtureRuntime(),lab=await initialize(ui,r);lab.play();ui.frame(0);ui.get('mo-time').value='1';ui.fire('mo-time');assert.equal(lab.getState().playing,false);assert.equal(r.calls.at(-1).time,1);ui.get('mo-loop').checked=true;ui.fire('mo-loop','change');ui.get('mo-time').value='2.5';ui.fire('mo-time');assert.equal(lab.getState().pose.sampledTime,.5);assert.equal(r.calls.at(-1).options.loop,true);
  ui.fire('mo-step','click');close(r.calls.at(-1).time,2.5+1/120);ui.get('mo-key').value='1';ui.fire('mo-key','change');assert.equal(ui.get('mo-qz').value,'1');assert.equal(ui.get('mo-qw').value,'1');assert.equal(ui.get('mo-key-time').value,'1');
});

test('invalid editor time scale quaternion or source clears stale pose without changing the committed source',async()=>{
  const ui=harness(),r=fixtureRuntime(),lab=await initialize(ui,r),before=lab.getState().source;ui.get('mo-sx').value='0';ui.fire('mo-sx');assert.equal(lab.getState().pose,null);assert.equal(lab.apply(),null);assert.deepEqual(lab.getState().source,before);assert.equal(lab.play(),false);assert.equal(ui.get('mo-pose-json').textContent,'姿勢なし');
  ui.fire('mo-cancel-edit','click');assert.ok(lab.getState().pose);ui.get('mo-key-time').value='';ui.fire('mo-key-time');assert.equal(lab.apply(),null);assert.equal(lab.getState().pose,null);ui.fire('mo-cancel-edit','click');
  for(const id of ['mo-qx','mo-qy','mo-qz','mo-qw']){ui.get(id).value='0';ui.fire(id);}assert.equal(lab.apply(),null);assert.deepEqual(lab.getState().source,before);ui.fire('mo-cancel-edit','click');
  assert.equal(await lab.loadSource('{broken'),false);assert.equal(lab.getState().pose,null);assert.deepEqual(lab.getState().source,before);assert.equal(ui.saves.length,0);ui.get('mo-time').value='';ui.fire('mo-time');assert.equal(lab.getState().pose,null);
});

test('runtime failure and legacy motion API leave source editable and retry restores a stopped pose',async()=>{
  const ui=harness(),r=fixtureRuntime();let fail=true;const lab=await initialize(ui,r,{loadRuntime:async()=>{if(fail)throw new Error('offline');return r;}});assert.equal(lab.getState().pose,null);assert.equal(ui.get('mo-editor').disabled,false);assert.equal(ui.get('mo-playback').disabled,true);
  fail=false;await lab.retry();assert.ok(lab.getState().pose);r.respond=()=>{throw new Error('Motion WASM API unavailable; rebuild');};lab.resample(.5);assert.equal(lab.getState().pose,null);assert.match(ui.get('mo-error').textContent,/同梱WASM/);r.respond=fixturePose;await lab.retry();assert.ok(lab.getState().pose);assert.equal(lab.getState().playing,false);
});

test('file load is explicit paused and size limited; history branches clear Redo and retain only 32 changes',async()=>{
  const ui=harness(),lab=await initialize(ui),source=defaultMotionSource();source.name='読込原本';lab.play();ui.get('mo-load').files=[{size:100,text:async()=>serializeMotionSource(source)}];await ui.fire('mo-load','change');assert.equal(lab.getState().source.name,'読込原本');assert.equal(lab.getState().playing,false);assert.equal(ui.saves.length,0);
  ui.get('mo-load').files=[{size:9*1024*1024,text:async()=>{throw new Error('must not read');}}];await ui.fire('mo-load','change');assert.equal(lab.getState().pose,null);
  for(let j=0;j<34;++j){ui.get('mo-px').value=String(j+.25);ui.fire('mo-px');lab.apply();}assert.equal(lab.getState().undo,32);lab.undo();assert.equal(lab.getState().redo,1);ui.get('mo-px').value='100';ui.fire('mo-px');lab.apply();assert.equal(lab.getState().redo,0);
});

test('static Japanese lesson original SVG and one entry tuple keep animation scope and readable tables',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(m[1]))await access(new URL(m[1],htmlUrl));for(const term of ['NLERP','定速SLERPではありません','shear','物理Worldを進めません','HTTP/HTTPS','Undo/Redo','glTF入出力互換'])assert.ok(html.includes(term),term);
  assert.match(html,/overflow-x:auto/);assert.match(html,/src="motion-lab\.mjs(?:\?[^\"]*)?"/);const index=await readFile(new URL('../docs/learn/index.html',import.meta.url),'utf8');assert.equal([...index.matchAll(/<article\s/g)].length,26);assert.match(index,/id="motion"/);const build=await readFile(new URL('../scripts/build-web.mjs',import.meta.url),'utf8');assert.equal((build.match(/\['tools\/motion-lab.html','\.\.\/','motion-lab.mjs'\]/g)??[]).length,1);const svg=await readFile(new URL('../docs/learn/diagrams/motion.svg',import.meta.url),'utf8');assert.match(svg,/<svg /);assert.doesNotMatch(svg,/<image|https?:\/\/(?!www.w3.org)/);
});

let runtime;async function actual(){if(!runtime)runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});return runtime;}
test('actual WASM source key edit sample Undo Redo save and reload changes the selected joint analytically',async()=>{
  const ui=harness(),lab=await initialize(ui,await actual());close(lab.getState().pose.bones.find(b=>b.id===4).worldPosition[0],2);ui.get('mo-px').value='2';ui.fire('mo-px');lab.apply();close(lab.getState().pose.bones.find(b=>b.id===4).worldPosition[0],4);lab.undo();close(lab.getState().pose.bones.find(b=>b.id===4).worldPosition[0],2);lab.redo();close(lab.getState().pose.bones.find(b=>b.id===4).worldPosition[0],4);ui.fire('mo-save','click');const saved=lab.getState().source;await lab.loadSource(ui.saves[0].text);assert.deepEqual(lab.getState().source,saved);close(lab.getState().pose.bones.find(b=>b.id===4).worldPosition[0],4);
  const pose=lab.resample(1);const tip=pose.bones.find(b=>b.id===4);close(tip.worldPosition[0],1);close(tip.worldPosition[1],2); // Exact middle key overrides the edited time-0 key.
});

test('actual WASM loop clamp step and antipodal keys keep the defined discrete source semantics',async()=>{
  const ui=harness(),r=await actual(),lab=await initialize(ui,r),source=defaultMotionSource();source.clip.tracks=[{boneId:2,interpolation:'step',keys:[{time:0,position:[0,1,0],rotation:[0,0,0,1],scale:[1,1,1]},{time:1,position:[0,2,0],rotation:[0,0,0,-2],scale:[1,1,1]}]}];await lab.loadSource(serializeMotionSource(source));close(lab.resample(.75).bones.find(b=>b.id===2).worldPosition[1],1);close(lab.resample(1).bones.find(b=>b.id===2).worldPosition[1],2);
  source.clip.tracks[0].interpolation='linear';source.clip.tracks[0].keys[1].position=[0,1,0];await lab.loadSource(serializeMotionSource(source));const half=lab.resample(.5);close(half.bones.find(b=>b.id===4).worldPosition[0],2);close(half.bones.find(b=>b.id===4).worldPosition[1],1);ui.get('mo-loop').checked=true;ui.fire('mo-loop','change');assert.equal(lab.resample(2).sampledTime,0);ui.get('mo-loop').checked=false;ui.fire('mo-loop','change');assert.equal(lab.resample(3).sampledTime,2);
  const poses=[];for(const hz of [30,60,120]){await lab.loadSource(serializeMotionSource(defaultMotionSource()));lab.resample(0);lab.play();ui.frame(0);for(let j=1;j<=hz;++j)ui.frame(j*1000/hz);poses.push(lab.getState().pose);lab.pause();}assert.deepEqual(poses[0],poses[1]);assert.deepEqual(poses[1],poses[2]);assert.equal(poses[0].sampledTime,1);
});

test('actual WASM nonuniform parent scale and rotated child retain shear in original world matrix values',async()=>{
  const source=defaultMotionSource();source.clip.tracks=[];source.bones[0].rest.scale=[2,1,1];source.bones[1].rest.rotation=[0,0,1,2];const ui=harness(),lab=await initialize(ui,await actual());await lab.loadSource(serializeMotionSource(createMotionSource(source)));const m=lab.getState().pose.bones.find(b=>b.id===2).worldMatrix;
  close(m[0],6/5);close(m[1],4/5);close(m[4],-8/5);close(m[5],3/5);close(m[0]*m[4]+m[1]*m[5],-36/25);assert.deepEqual(JSON.parse(ui.get('mo-pose-json').textContent).bones.find(b=>b.id===2).worldMatrix,m);
});
