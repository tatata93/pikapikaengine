import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {triangleLabPreset,parseTriangleLabInput,evaluateTriangleLab,serializeTriangleLab,triangleProjection,initializeSphereTriangleLab} from '../tools/sphere-triangle-lab.mjs';

const presetNames=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c','back','coincident','degenerate','thin','budget','normal_precision'];
const defaultSettings={maxCandidates:7,sqrtRefinements:128,maxTotalSqrtRefinements:1024,maximumLocalWidth:1e-7,maximumNormalWidth:1e-8,minimumSineSquared:1e-12};
let actual;
async function runtime(){return actual??=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});}
const clone=x=>structuredClone(x);
const inside=(bounds,value)=>assert.ok(bounds[0]<=value&&value<=bounds[1],`${bounds} excludes independent value ${value}`);

test('all thirteen original presets have complete owned sphere triangle and six-setting sources',()=>{
 for(const name of presetNames){
  const a=triangleLabPreset(name),b=triangleLabPreset(name);assert.deepEqual(a,b,name);assert.deepEqual(Object.keys(a).sort(),['settings','sphere','triangle']);
  assert.deepEqual(Object.keys(a.sphere).sort(),['position','radius']);assert.deepEqual(Object.keys(a.triangle).sort(),['id','vertices']);assert.deepEqual(Object.keys(a.settings).sort(),Object.keys(defaultSettings).sort());
  assert.equal(a.sphere.position.length,3);assert.equal(a.triangle.vertices.length,3);a.triangle.vertices.forEach(v=>assert.equal(v.length,3));
  a.sphere.position[0]=999;a.triangle.vertices[0][0]=888;a.settings.maxCandidates=123;assert.deepEqual(triangleLabPreset(name),b,'preset has no mutable shared arrays');
 }
 assert.deepEqual(triangleLabPreset('face').settings,defaultSettings);assert.throws(()=>triangleLabPreset('missing'));
});

test('strict source parser fills only missing settings and refuses unknown missing duplicate and nonfinite input',()=>{
 const a=triangleLabPreset('face'),before=clone(a),partial={...a,settings:{sqrtRefinements:64}},parsed=parseTriangleLabInput(stringifyStrictJson(partial));
 assert.deepEqual(parsed.settings,{...defaultSettings,sqrtRefinements:64});assert.deepEqual(a,before);assert.deepEqual(parseTriangleLabInput(stringifyStrictJson(a)),a);
 const bad=[];
 for(const key of ['extra','__proto__'])bad.push({...a,[key]:true});
 for(const key of ['sphere','triangle','settings']){const q=clone(a);delete q[key];bad.push(q);}
 for(const key of ['position','radius']){const q=clone(a);delete q.sphere[key];bad.push(q);}
 for(const key of ['id','vertices']){const q=clone(a);delete q.triangle[key];bad.push(q);}
 bad.push({...a,sphere:{...a.sphere,velocity:[0,0,0]}},{...a,triangle:{...a.triangle,normal:[0,1,0]}},{...a,settings:{...a.settings,friction:.5}},
  {...a,sphere:{...a.sphere,position:[0,0]}},{...a,triangle:{...a.triangle,vertices:a.triangle.vertices.slice(0,2)}},null,[],{...a,settings:[]});
 for(const q of bad)assert.throws(()=>parseTriangleLabInput(stringifyStrictJson(q)),'invalid strict source');
 const source=stringifyStrictJson(a);
 for(const text of [source.slice(0,-1)+',"sphere":'+stringifyStrictJson(a.sphere)+'}',source.replace('"radius":'+a.sphere.radius,'"radius":NaN'),source.replace('"radius":'+a.sphere.radius,'"radius":1e400'),source.replace('"radius":'+a.sphere.radius,'"radius":1e-9999'),source+' trailing'])assert.throws(()=>parseTriangleLabInput(text));
});

test('actual common C++ WASM evaluates all thirteen presets with full candidates and explicit failed geometry',async()=>{
 const r=await runtime();
 const expected={face:'completed',edge_ab:'completed',edge_bc:'completed',edge_ca:'completed',vertex_a:'completed',vertex_b:'completed',vertex_c:'completed',back:'completed',coincident:'quality_unresolved',degenerate:'degenerate',thin:'ill_conditioned',budget:'budget_exceeded',normal_precision:'quality_unresolved'};
 for(const name of presetNames){
  const source=triangleLabPreset(name),before=clone(source),packet=evaluateTriangleLab(r,source);assert.deepEqual(source,before,name+' source changed');
  assert.equal(packet.schema,1);assert.equal(packet.kind,'sphere-triangle-lab');assert.deepEqual(packet.input,source);assert.equal(packet.result.status,expected[name],name);assert.equal(packet.diagnostics.backend,'C++ WebAssembly');
  assert.deepEqual(packet.result,r.querySphereTriangle(source.sphere,source.triangle,source.settings),name+' is actual API output');
  if(packet.result.status==='completed'){
   assert.ok(packet.result.geometry);assert.equal(packet.result.candidates.length,7);assert.equal(packet.result.candidatesExamined,7);assert.equal(packet.result.geometry.surfaceId,source.triangle.id);
   const feature=name==='back'?'face':name;assert.ok(packet.result.candidates.some(c=>c.feature===feature&&c.disposition==='retained'),name+' expected feature missing');
  }else assert.equal(packet.result.geometry,null,name+' fabricated partial geometry');
 }
});

test('evaluation owns source result and diagnostics and dispatches original coordinates once without fallback',async()=>{
 const real=await runtime(),source=triangleLabPreset('face'),before=clone(source),answer=real.querySphereTriangle(source.sphere,source.triangle,source.settings),savedAnswer=clone(answer),diagnostics={backend:'captured actual C++ result',nested:{tag:'owned'}};
 const calls=[];const facade={diagnostics,querySphereTriangle(s,t,six){calls.push(clone({s,t,six}));return answer;},querySpherePlane(){assert.fail('no plane fallback');},querySphereSphere(){assert.fail('no sphere fallback');}};
 const packet=evaluateTriangleLab(facade,source);assert.equal(calls.length,1);assert.deepEqual(calls[0],{s:source.sphere,t:source.triangle,six:source.settings});assert.deepEqual(source,before);assert.deepEqual(packet.result,savedAnswer);
 source.sphere.position[0]=123;answer.geometry.closest[0][0]=456;diagnostics.nested.tag='changed';assert.deepEqual(packet.input,before);assert.deepEqual(packet.result,savedAnswer);assert.equal(packet.diagnostics.nested.tag,'owned');
 const shared=clone(packet);packet.input.triangle.vertices[0][0]=789;packet.result.candidates[0].barycentric[0][0]=999;assert.deepEqual(savedAnswer,shared.result);
 const error=new SimulationError(1,'intentional exchange rejection');assert.throws(()=>evaluateTriangleLab({diagnostics:{},querySphereTriangle(){throw error;}},triangleLabPreset('face')),e=>e===error);
 assert.throws(()=>evaluateTriangleLab({querySpherePlane(){assert.fail('no alternative geometry');}},triangleLabPreset('face')));
});

test('signed zero full result JSON saves and reloads without source result or projection mutation',async()=>{
 const r=await runtime(),source=triangleLabPreset('face');source.triangle.vertices[0][0]=-0;const before=clone(source),packet=evaluateTriangleLab(r,source),saved=clone(packet),text=serializeTriangleLab(packet,'xz'),decoded=parseStrictJson(text);
 assert.equal(decoded.projection,'xz');assert.equal(decoded.schema,1);assert.equal(decoded.kind,'sphere-triangle-lab');assert.ok(Object.is(decoded.input.triangle.vertices[0][0],-0));
 assert.ok(Object.is(decoded.result.candidates[0].kkt[0][0],-0));assert.ok(Object.is(decoded.result.candidates[0].kkt[0][1],0));assert.deepEqual(decoded.result,packet.result);
 assert.deepEqual(parseTriangleLabInput(stringifyStrictJson(decoded.input)),before);assert.deepEqual(packet,saved);assert.deepEqual(source,before);
 for(const projection of ['','bad',0])assert.throws(()=>serializeTriangleLab(packet,projection));
 const bad=clone(packet);bad.result.geometry.closest[0][0]=NaN;assert.throws(()=>serializeTriangleLab(bad));
});

test('actual presets and edited rational contacts enclose independent closest delta and squared-distance references',async()=>{
 const r=await runtime();
 const known={face:[[1,0,1],[0,2,0],4],edge_ab:[[2,0,0],[0,2,-1],5],edge_bc:[[2,0,2],[1,2,1],6],edge_ca:[[0,0,2],[-1,2,0],5],vertex_a:[[0,0,0],[-1,2,-1],6],vertex_b:[[4,0,0],[1,2,-1],6],vertex_c:[[0,0,4],[-1,2,1],6],back:[[1,0,1],[0,-2,0],4]};
 for(const [name,[closest,delta,squared]]of Object.entries(known)){
  const {result}=evaluateTriangleLab(r,triangleLabPreset(name));assert.equal(result.status,'completed');closest.forEach((v,k)=>inside(result.geometry.closest[k],v));delta.forEach((v,k)=>inside(result.geometry.delta[k],v));inside(result.geometry.squaredDistance,squared);
 }
 for(const [position,closest,normal]of [[[2,3,-4],[2,0,0],[0,.6,-.8]],[[-3,4,0],[0,0,0],[-.6,.8,0]]]){
  const source=triangleLabPreset('face');source.sphere={position,radius:5};const {result}=evaluateTriangleLab(r,parseTriangleLabInput(stringifyStrictJson(source)));assert.equal(result.status,'completed');
  closest.forEach((v,k)=>inside(result.geometry.closest[k],v));normal.forEach((v,k)=>inside(result.geometry.normal[k],v));inside(result.geometry.distance,5);inside(result.geometry.squaredDistance,25);inside(result.geometry.gap,0);
 }
});

test('projection owns drawing coordinates and interval rectangles without changing physics or inventing failed geometry',async()=>{
 const r=await runtime(),source=triangleLabPreset('face'),{result}=evaluateTriangleLab(r,source),before=clone({source,result});
 for(const projection of ['xy','xz','yz']){
  const view=triangleProjection(source,result,projection);assert.equal(view.available,true);assert.equal(view.projection,projection);assert.equal(view.triangle.length,3);view.triangle.forEach(p=>assert.equal(p.length,2));
  assert.ok(view.closest);assert.ok(view.closest.width>=0&&view.closest.height>=0);assert.ok([view.scale,view.radius,...view.sphereCenter,...view.triangle.flat(),...Object.values(view.closest)].every(Number.isFinite));
  view.triangle[0][0]=123;assert.deepEqual({source,result},before);
 }
 const failure=evaluateTriangleLab(r,triangleLabPreset('coincident')),view=triangleProjection(failure.input,failure.result,'xz');assert.equal(view.closest,null);assert.equal(failure.result.geometry,null);
 assert.throws(()=>triangleProjection(source,result,'bad'));
 const giant=triangleLabPreset('face');giant.sphere.position=[1e308,0,0];giant.sphere.radius=1e308;const packet=evaluateTriangleLab(r,giant);assert.equal(packet.result.status,'invalid_input');const unavailable=triangleProjection(packet.input,packet.result,'xy');assert.equal(unavailable.available,false);assert.equal(typeof unavailable.reason,'string');assert.equal(packet.result.geometry,null);
});

const html=await readFile(new URL('../tools/sphere-triangle-lab.html',import.meta.url),'utf8');
function harness(){
 const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map();
 function get(id){
  assert.ok(ids.has(id),'Actual lab element missing: '+id);
  if(!elements.has(id)){
   const listeners=new Map(),attributes=new Map();
   elements.set(id,{id,value:'',textContent:'',innerHTML:'',disabled:false,hidden:false,attributes,listeners,
    addEventListener(type,fn){if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);},
    removeEventListener(type,fn){listeners.get(type)?.delete(fn);},setAttribute(name,value){attributes.set(name,String(value));},getAttribute(name){return attributes.get(name)??null;}});
  }
  return elements.get(id);
 }
 return {get,doc:{getElementById:get},fire(id,event='click'){
  const e=get(id),listeners=[...(e.listeners.get(event)??[])];assert.ok(listeners.length,'Missing event '+id+':'+event);let result;
  for(const fn of listeners)result=fn({target:e,currentTarget:e});return result;
 },listenerCount(){let total=0;for(const e of elements.values())for(const callbacks of e.listeners.values())total+=callbacks.size;return total;}};
}
function counted(real){
 const calls=[];let failure=null;
 return {calls,get diagnostics(){return real.diagnostics;},set failure(error){failure=error;},querySphereTriangle(s,t,settings){calls.push(clone({sphere:s,triangle:t,settings}));if(failure)throw failure;return real.querySphereTriangle(s,t,settings);},querySpherePlane(){assert.fail('No alternate plane calculation');}};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const flush=async()=>{await Promise.resolve();await Promise.resolve();};
function cleared(ui,lab){
 assert.equal(lab.getState(),null);assert.equal(ui.get('triangle-save').disabled,true);assert.equal(ui.get('triangle-json').textContent,'');assert.equal(ui.get('triangle-view').innerHTML,'');assert.equal(ui.get('triangle-geometry').textContent,'—');assert.equal(ui.get('triangle-candidates').textContent,'—');
}

test('UI uses actual SDK for every preset and exposes complete geometry or failed candidate prefix',async()=>{
 const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleLab({doc:ui.doc,loadRuntime:async()=>r});
 assert.equal(r.calls.length,1);assert.equal(lab.getState().result.status,'completed');assert.equal(ui.get('triangle-controls').disabled,false);assert.equal(ui.get('triangle-save').disabled,false);
 for(const name of presetNames){
  const count=r.calls.length;ui.get('triangle-preset').value=name;ui.fire('triangle-preset','change');assert.equal(r.calls.length,count+1,name);
  const packet=lab.getState();assert.deepEqual(packet.input,triangleLabPreset(name));assert.deepEqual(parseStrictJson(ui.get('triangle-json').textContent).result,packet.result);
  if(packet.result.geometry){assert.deepEqual(parseStrictJson(ui.get('triangle-geometry').textContent),packet.result.geometry);assert.match(ui.get('triangle-view').getAttribute('aria-label'),/completed/);}
  else{assert.match(ui.get('triangle-geometry').textContent,/null/);assert.match(ui.get('triangle-status').textContent,/モデル失敗/);assert.doesNotMatch(ui.get('triangle-view').innerHTML,/fill="#fff"/);}
  for(const candidate of packet.result.candidates)assert.match(ui.get('triangle-candidates').textContent,new RegExp(candidate.feature));
 }
 lab.dispose();
});

test('input edits clear old geometry candidates export and save until explicit query; getState is owned',async()=>{
 const ui=harness(),r=counted(await runtime()),saved=[],lab=await initializeSphereTriangleLab({doc:ui.doc,loadRuntime:async()=>r,saveFile:value=>saved.push(value)});
 const first=lab.getState(),copy=lab.getState();copy.input.sphere.position[0]=100;copy.result.geometry.closest[0][0]=999;assert.deepEqual(lab.getState(),first);
 const next=triangleLabPreset('edge_bc');ui.get('triangle-source').value=stringifyStrictJson(next);const oldCalls=r.calls.length;ui.fire('triangle-source','input');cleared(ui,lab);assert.equal(r.calls.length,oldCalls);
 ui.fire('triangle-save');assert.equal(saved.length,0);ui.fire('triangle-run');assert.equal(r.calls.length,oldCalls+1);assert.deepEqual(lab.getState().input,next);
 ui.fire('triangle-save');assert.equal(saved.length,1);assert.equal(saved[0].mime,'application/json');assert.match(saved[0].filename,/\.json$/);assert.deepEqual(parseStrictJson(saved[0].text).input,next);
 ui.get('triangle-source').value='{"sphere":';ui.fire('triangle-source','input');ui.fire('triangle-run');cleared(ui,lab);assert.match(ui.get('triangle-error').textContent,/入力JSON/);assert.equal(r.calls.length,oldCalls+1);
 ui.get('triangle-source').value=stringifyStrictJson(next);ui.fire('triangle-run');assert.equal(lab.getState().result.status,'completed');lab.dispose();
});

test('projection changes redraw and update saved display condition with zero extra C++ queries',async()=>{
 const ui=harness(),r=counted(await runtime()),saved=[],lab=await initializeSphereTriangleLab({doc:ui.doc,loadRuntime:async()=>r,saveFile:value=>saved.push(value)}),state=lab.getState(),source=ui.get('triangle-source').value;
 for(const projection of ['xy','yz','xz']){const calls=r.calls.length;ui.get('triangle-projection').value=projection;ui.fire('triangle-projection','change');assert.equal(r.calls.length,calls);assert.deepEqual(lab.getState(),state);assert.equal(ui.get('triangle-source').value,source);assert.equal(parseStrictJson(ui.get('triangle-json').textContent).projection,projection);ui.fire('triangle-save');assert.equal(parseStrictJson(saved.at(-1).text).projection,projection);}
 ui.get('triangle-projection').value='unknown';ui.fire('triangle-projection','change');cleared(ui,lab);assert.match(ui.get('triangle-error').textContent,/表示/);lab.dispose();
});

test('host exchange and save rejection clear success, and reset restores the currently selected preset',async()=>{
 const ui=harness(),r=counted(await runtime());let saveFails=false;
 const lab=await initializeSphereTriangleLab({doc:ui.doc,loadRuntime:async()=>r,saveFile(){if(saveFails)throw new Error('save failure');}});
 const invalid=triangleLabPreset('face');invalid.triangle.id=0;ui.get('triangle-source').value=stringifyStrictJson(invalid);ui.fire('triangle-source','input');ui.fire('triangle-run');cleared(ui,lab);assert.match(ui.get('triangle-error').textContent,/SDK交換/);
 ui.get('triangle-preset').value='vertex_c';ui.fire('triangle-preset','change');assert.equal(lab.getState().result.status,'completed');const edited=triangleLabPreset('vertex_c');edited.sphere.radius=.75;ui.get('triangle-source').value=stringifyStrictJson(edited);ui.fire('triangle-source','input');ui.fire('triangle-run');assert.equal(lab.getState().input.sphere.radius,.75);
 ui.fire('triangle-reset');assert.deepEqual(lab.getState().input,triangleLabPreset('vertex_c'));assert.equal(ui.get('triangle-preset').value,'vertex_c');
 r.failure=new SimulationError(1,'scripted actual exchange rejection');ui.fire('triangle-run');cleared(ui,lab);assert.match(ui.get('triangle-error').textContent,/SDK交換/);r.failure=null;ui.fire('triangle-run');assert.equal(lab.getState().result.status,'completed');
 saveFails=true;ui.fire('triangle-save');cleared(ui,lab);assert.match(ui.get('triangle-error').textContent,/保存/);saveFails=false;ui.fire('triangle-run');assert.ok(lab.getState().result.geometry);lab.dispose();
});

test('editing during initial delayed load preserves current source and prevents stale automatic query',async()=>{
 const ui=harness(),r=counted(await runtime()),pending=deferred(),initializing=initializeSphereTriangleLab({doc:ui.doc,loadRuntime:()=>pending.promise});await flush();
 const next=triangleLabPreset('edge_ca');ui.get('triangle-source').value=stringifyStrictJson(next);ui.fire('triangle-source','input');pending.resolve(r);const lab=await initializing;
 assert.equal(r.calls.length,0);cleared(ui,lab);assert.equal(ui.get('triangle-controls').disabled,false);assert.deepEqual(parseTriangleLabInput(ui.get('triangle-source').value),next);
 ui.fire('triangle-run');assert.equal(r.calls.length,1);assert.deepEqual(lab.getState().input,next);lab.dispose();
});

test('synchronous loader throw recovers, concurrent retry coalesces, and run cannot use old runtime during reload',async()=>{
 const ui=harness(),r=counted(await runtime()),pending=deferred();let calls=0,mode='sync-throw';
 const loadRuntime=()=>{++calls;if(mode==='sync-throw')throw new Error('sync offline');if(mode==='pending')return pending.promise;return r;};
 const lab=await initializeSphereTriangleLab({doc:ui.doc,loadRuntime});assert.equal(calls,1);cleared(ui,lab);assert.equal(ui.get('triangle-controls').disabled,true);assert.match(ui.get('triangle-error').textContent,/SDK初期化/);
 mode='ready';await lab.retry();assert.equal(calls,2);assert.equal(lab.getState().result.status,'completed');const previousQueries=r.calls.length;
 mode='pending';const a=lab.retry(),b=lab.retry();await flush();assert.equal(calls,3);cleared(ui,lab);assert.equal(lab.run(),null);assert.equal(r.calls.length,previousQueries);pending.resolve(r);await Promise.all([a,b]);assert.equal(calls,3);assert.equal(r.calls.length,previousQueries+1);assert.equal(lab.getState().result.status,'completed');lab.dispose();
});

test('dispose removes handlers and late retry fulfillment or rejection cannot resurrect result controls or export',async()=>{
 for(const outcome of ['resolve','reject']){
  const ui=harness(),r=counted(await runtime()),pending=deferred();let delay=false;
  const lab=await initializeSphereTriangleLab({doc:ui.doc,loadRuntime:()=>delay?pending.promise:r});delay=true;const retry=lab.retry();await flush();const calls=r.calls.length;assert.ok(ui.listenerCount()>0);lab.dispose();lab.dispose();
  assert.equal(ui.listenerCount(),0);cleared(ui,lab);assert.equal(ui.get('triangle-controls').disabled,true);assert.equal(ui.get('triangle-retry').disabled,true);const text=ui.get('triangle-status').textContent;
  if(outcome==='resolve')pending.resolve(r);else pending.reject(new Error('late offline'));await retry;
  assert.equal(lab.run(),null);assert.equal(await lab.retry(),null);assert.equal(r.calls.length,calls);cleared(ui,lab);assert.equal(ui.get('triangle-status').textContent,text);assert.equal(ui.get('triangle-controls').disabled,true);assert.equal(ui.get('triangle-retry').disabled,true);
 }
});
