import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {meshLabPresets,meshLabPreset,parseMeshLabInput,evaluateMeshLab,serializeMeshLab,meshProjection,initializeSphereTriangleMeshLab} from '../tools/sphere-triangle-mesh-lab.mjs';

let actual;
const runtime=async()=>actual??=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const names=['singleton','back','dominance','shared_edge','shared_vertex','separate_tie','reversed','uncertain_order','huge_offset','capacity64','middle_degenerate','far_degenerate','candidate_budget','normal_precision','duplicate_id','empty','capacity65'];
const clone=structuredClone;
const inside=(bounds,value)=>assert.ok(bounds[0]<=value&&value<=bounds[1],`${bounds} excludes ${value}`);
const encode=stringifyStrictJson;
const page=await readFile(new URL('../tools/sphere-triangle-mesh-lab.html',import.meta.url),'utf8');
const pageIds=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);

test('seventeen source presets expose stable names labels complete settings and independent arrays',()=>{
 assert.deepEqual(meshLabPresets.map(p=>p.name),names);assert.ok(Object.isFrozen(meshLabPresets));assert.ok(meshLabPresets.every(p=>Object.isFrozen(p)&&typeof p.label==='string'&&p.label.length));
 assert.equal(new Set(pageIds).size,pageIds.length,'actual HTML has unique IDs');
 for(const id of ids)assert.ok(pageIds.includes('mesh-'+id),'actual HTML control '+id);
 const options=page.match(/<select id="mesh-preset">([\s\S]*?)<\/select>/)[1];assert.deepEqual([...options.matchAll(/<option value="([^"]+)"/g)].map(m=>m[1]),names,'actual HTML exposes all presets');
 for(const name of names){const a=meshLabPreset(name),b=meshLabPreset(name);assert.deepEqual(a,b);assert.deepEqual(Object.keys(a),['sphere','triangles','settings']);assert.equal(Object.keys(a.settings.primitive).length,6);a.sphere.position[0]=9;a.settings.primitive.maxCandidates=9;if(a.triangles.length)a.triangles[0].vertices[0][0]=9;assert.deepEqual(meshLabPreset(name),b);}
 assert.equal(meshLabPreset('capacity64').triangles.length,64);assert.equal(meshLabPreset('capacity65').triangles.length,65);assert.throws(()=>meshLabPreset('unknown'));
});
test('strict source shape budgets finite values unknown keys duplicates and null settings fail closed',()=>{
 const q=meshLabPreset(),before=clone(q);q.settings={};const parsed=parseMeshLabInput(encode(q));assert.deepEqual(parsed.settings,before.settings);assert.deepEqual(q.settings,{});
 const bad=[];for(const key of ['sphere','triangles','settings']){const v=clone(before);delete v[key];bad.push(v);}
 bad.push({...before,unknown:1},{...before,sphere:{...before.sphere,velocity:[0,0,0]}},{...before,triangles:[{...before.triangles[0],extra:1}]},{...before,settings:{unknown:0}},{...before,settings:{primitive:{unknown:0}}},{...before,settings:{maxSurfaces:null}},{...before,settings:{primitive:null}},{...before,settings:[]},{...before,triangles:[{id:1,vertices:[[0,0,0]]}]},{...before,sphere:{position:[0,0],radius:1}},{...before,triangles:Array(66).fill(before.triangles[0])});
 for(const value of bad)assert.throws(()=>parseMeshLabInput(encode(value)));
 const text=encode(before);for(const value of [text.slice(0,-1)+',"sphere":'+encode(before.sphere)+'}',text.replace('"radius":0.5','"radius":NaN'),text.replace('"radius":0.5','"radius":1e400'),text.replace('"radius":0.5','"radius":1e-9999'),text+' trailing',' '.repeat(65537)+text])assert.throws(()=>parseMeshLabInput(value));
 const sparse=clone(before);sparse.triangles[0].vertices[0]=Array(3);assert.throws(()=>evaluateMeshLab({},sparse));
});
test('all finite presets use the actual common C++ mesh API and preserve every source and diagnostic',async()=>{
 const r=await runtime();const expected={middle_degenerate:'row_failure',far_degenerate:'row_failure',candidate_budget:'row_failure',normal_precision:'row_failure',duplicate_id:'invalid_input',empty:'invalid_input'};
 for(const name of names){const source=meshLabPreset(name),before=clone(source);if(name==='capacity65'){assert.throws(()=>evaluateMeshLab(r,source),e=>e instanceof Error&&/64 surfaces/.test(e.message));assert.deepEqual(source,before);continue;}
  const p=evaluateMeshLab(r,source);assert.equal(p.schema,1);assert.equal(p.kind,'sphere-triangle-mesh-lab');assert.equal(p.diagnostics.backend,'C++ WebAssembly');assert.deepEqual(p.input,source);assert.deepEqual(source,before);assert.equal(p.result.status,expected[name]??'completed',name);assert.deepEqual(p.result,r.querySphereTriangleMesh(source.sphere,source.triangles,source.settings));
  assert.equal(p.result.nearest!==null,p.result.status==='completed');if(p.result.status==='row_failure')assert.equal(p.result.rows.length,source.triangles.length);
 }
});
test('independent simple distances and distinct closest ties remain per row with every possible ID',async()=>{
 const r=await runtime();for(const name of ['singleton','back','dominance','reversed','shared_edge','shared_vertex','separate_tie','capacity64']){const p=evaluateMeshLab(r,meshLabPreset(name));inside(p.result.nearest.squaredDistance,1);inside(p.result.nearest.distance,1);assert.ok(!Object.hasOwn(p.result.nearest,'normal'));
  if(['dominance','reversed'].includes(name))assert.deepEqual(p.result.nearest.possibleSurfaceIds,[37]);
 }
 for(const name of ['shared_edge','shared_vertex'])assert.deepEqual(evaluateMeshLab(r,meshLabPreset(name)).result.nearest.possibleSurfaceIds,[11,37]);
 const tie=evaluateMeshLab(r,meshLabPreset('separate_tie')).result;assert.deepEqual(tie.nearest.possibleSurfaceIds,[7,99]);inside(tie.rows[0].query.geometry.closest[0],-1);inside(tie.rows[1].query.geometry.closest[0],1);inside(tie.rows[0].query.geometry.normal[0],1);inside(tie.rows[1].query.geometry.normal[0],-1);
 assert.deepEqual(evaluateMeshLab(r,meshLabPreset('uncertain_order')).result.nearest.possibleSurfaceIds,[5,37]);
});
test('actual capacity64 retains all source rows all possible IDs and last seven candidate audits in saved JSON',async()=>{
 const source=meshLabPreset('capacity64'),p=evaluateMeshLab(await runtime(),source),before=clone(p),text=serializeMeshLab(p,'yz',63),saved=parseStrictJson(text);
 assert.equal(saved.input.triangles.length,64);assert.equal(saved.result.rows.length,64);assert.deepEqual(saved.result.nearest.possibleSurfaceIds,Array.from({length:64},(_,i)=>i+1));assert.equal(saved.result.queries,64);assert.equal(saved.result.candidatesExamined,448);assert.equal(saved.result.rows[63].triangle.id,64);assert.equal(saved.result.rows[63].query.candidates.length,7);assert.equal(saved.result.rows[63].query.candidates[6].feature,'vertex_c');
 assert.equal(saved.inspectedOrdinal,63);assert.equal(saved.inspectedSurfaceId,64);assert.equal(saved.projection,'yz');assert.deepEqual(saved.result,p.result);assert.deepEqual(p,before);assert.ok(Object.is(saved.input.triangles[63].vertices[0][0],-0));assert.ok(Object.is(saved.result.rows[63].query.candidates[0].kkt[0][0],-0));
 const empty=evaluateMeshLab(await runtime(),meshLabPreset('empty'));assert.equal(parseStrictJson(serializeMeshLab(empty)).inspectedSurfaceId,null);assert.throws(()=>serializeMeshLab(p,'bad'));assert.throws(()=>serializeMeshLab(p,'xz',64));
});
test('evaluation owns source result diagnostics and forwards one actual query without fallback',async()=>{
 const real=await runtime(),source=meshLabPreset('dominance'),answer=real.querySphereTriangleMesh(source.sphere,source.triangles,source.settings),saved=clone(answer),diagnostics={backend:'captured actual result',nested:{owned:true}},calls=[];
 const facade={diagnostics,querySphereTriangleMesh(s,t,settings){calls.push(clone({s,t,settings}));return answer;},querySphereTriangle(){assert.fail('No per-triangle JS fallback');}};
 const p=evaluateMeshLab(facade,source),before=clone(p);assert.equal(calls.length,1);assert.deepEqual(calls[0],{s:source.sphere,t:source.triangles,settings:source.settings});source.triangles[0].id=999;answer.rows[0].query.geometry.closest[0][0]=999;diagnostics.nested.owned=false;assert.deepEqual(p,before);assert.deepEqual(p.result,saved);
 const error=new SimulationError(1,'actual host error');assert.throws(()=>evaluateMeshLab({diagnostics:{},querySphereTriangleMesh(){throw error;}},meshLabPreset()),e=>e===error);assert.throws(()=>evaluateMeshLab({querySphereTriangle(){assert.fail('fallback');}},meshLabPreset()));
});
test('projection is display-only and selects actual row diagnostics without inventing aggregate nearest',async()=>{
 const p=evaluateMeshLab(await runtime(),meshLabPreset('middle_degenerate')),before=clone(p);assert.equal(p.result.nearest,null);
 for(const projection of ['xy','xz','yz']){const a=meshProjection(p.input,p.result,projection,0);assert.equal(a.available,true);assert.equal(a.triangles.length,3);assert.ok(a.closest);assert.equal(a.aggregateStatus,'row_failure');assert.equal(a.rowStatus,'completed');assert.equal(meshProjection(p.input,p.result,projection,1).closest,null);a.triangles[0].vertices[0][0]=999;assert.deepEqual(p,before);}
 const duplicate=evaluateMeshLab(await runtime(),meshLabPreset('duplicate_id'));assert.equal(meshProjection(duplicate.input,duplicate.result,'xz',1).rowStatus,'unexamined');assert.equal(meshProjection(duplicate.input,duplicate.result,'xz',1).closest,null);
 const giant=meshLabPreset();giant.sphere={position:[1e308,0,0],radius:1e308};const g=evaluateMeshLab(await runtime(),giant);assert.equal(g.result.status,'invalid_input');assert.equal(meshProjection(g.input,g.result,'xy').available,false);assert.equal(g.result.nearest,null);assert.throws(()=>meshProjection(p.input,p.result,'bad'));
});

const ids=['status','error','retry','controls','preset','source','projection','inspect','run','reset','save','runtime','note','view','summary','rows','geometry','candidates','json'];
function harness(){const elements=new Map();function get(name){const id=name.startsWith('mesh-')?name:'mesh-'+name;assert.ok(ids.includes(id.slice(5)),id);if(!elements.has(id)){const listeners=new Map(),attributes=new Map();elements.set(id,{id,value:'',textContent:'',innerHTML:'',disabled:false,hidden:false,listeners,addEventListener(e,f){if(!listeners.has(e))listeners.set(e,new Set());listeners.get(e).add(f);},removeEventListener(e,f){listeners.get(e)?.delete(f);},setAttribute(k,v){attributes.set(k,String(v));},getAttribute(k){return attributes.get(k)??null;}});}return elements.get(id);}
 return {get,doc:{getElementById:get},fire(name,event='click'){const e=get(name);let out;for(const fn of [...(e.listeners.get(event)??[])])out=fn({target:e,currentTarget:e});return out;},listeners(){let n=0;for(const e of elements.values())for(const a of e.listeners.values())n+=a.size;return n;}};
}
function counted(real){let failure=null;const calls=[];return {calls,get diagnostics(){return real.diagnostics;},set failure(e){failure=e;},querySphereTriangleMesh(s,t,settings){calls.push(clone({sphere:s,triangles:t,settings}));if(failure)throw failure;return real.querySphereTriangleMesh(s,t,settings);}};}
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const flush=async()=>{await Promise.resolve();await Promise.resolve();};
function cleared(ui,lab){assert.equal(lab.getState(),null);assert.equal(ui.get('save').disabled,true);assert.equal(ui.get('inspect').disabled,true);for(const name of ['rows','view'])assert.equal(ui.get(name).innerHTML,'');for(const name of ['geometry','candidates','summary'])assert.equal(ui.get(name).textContent,'—');assert.equal(ui.get('json').textContent,'');}

test('actual UI presets disclose model failures host refusals all64 rows and last inspected audits',async()=>{
 const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:async()=>r});assert.equal(r.calls.length,1);
 for(const name of names){ui.get('preset').value=name;ui.fire('preset','change');if(name==='capacity65'){cleared(ui,lab);assert.equal(ui.get('error').hidden,false);assert.match(ui.get('error').textContent,/SDK交換/);continue;}
  const p=lab.getState();assert.deepEqual(p.input,meshLabPreset(name));assert.deepEqual(parseStrictJson(ui.get('json').textContent).result,p.result);assert.equal((ui.get('rows').innerHTML.match(/<tr>/g)??[]).length,p.input.triangles.length);assert.equal((ui.get('rows').innerHTML.match(/<td>/g)??[]).length,p.input.triangles.length*5);
  if(p.result.nearest)assert.match(ui.get('status').textContent,/集合成功/);else assert.match(ui.get('status').textContent,/集合モデル失敗/);
  if(name==='capacity64'){ui.get('inspect').value='63';ui.fire('inspect','change');const g=parseStrictJson(ui.get('geometry').textContent);assert.equal(g.surfaceId,64);assert.equal(g.candidateCount,7);assert.equal(g.candidatesExamined,7);assert.equal(g.sqrtRefinementLimited,p.result.rows[63].query.sqrtRefinementLimited);assert.deepEqual(g.squaredCross,p.result.rows[63].query.squaredCross);assert.match(ui.get('candidates').textContent,/vertex_c/);assert.equal(parseStrictJson(ui.get('json').textContent).result.rows[63].query.candidates.length,7);}
  if(name==='duplicate_id')assert.match(ui.get('rows').innerHTML,/事前拒否で未照会/);
 }
 lab.dispose();
});
test('edits instantly clear all old display export and save until explicit query; reset uses selected preset',async()=>{
 const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:async()=>r});const packet=lab.getState(),copy=lab.getState();copy.result.rows[0].query.geometry.closest[0][0]=99;assert.deepEqual(lab.getState(),packet);
 ui.get('preset').value='shared_edge';ui.fire('preset','change');const count=r.calls.length;const source=meshLabPreset('shared_edge');source.sphere.position[1]=2;ui.get('source').value=encode(source);ui.fire('source','input');cleared(ui,lab);assert.equal(r.calls.length,count);lab.run();assert.deepEqual(lab.getState().input,source);ui.fire('reset');assert.deepEqual(lab.getState().input,meshLabPreset('shared_edge'));lab.dispose();
});
test('projection inspection and signed-zero save use owned full packet without new physics query',async()=>{
 const ui=harness(),r=counted(await runtime()),saves=[],lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:async()=>r,saveFile:value=>saves.push(value)});ui.get('preset').value='capacity64';ui.fire('preset','change');const before=lab.getState(),count=r.calls.length;
 ui.get('inspect').value='63';ui.fire('inspect','change');ui.get('projection').value='yz';ui.fire('projection','change');await ui.fire('save');assert.equal(r.calls.length,count);assert.deepEqual(lab.getState(),before);assert.equal(saves.length,1);assert.equal(saves[0].text,ui.get('json').textContent);const saved=parseStrictJson(saves[0].text);assert.equal(saved.projection,'yz');assert.equal(saved.inspectedSurfaceId,64);assert.deepEqual(saved.result,before.result);assert.ok(Object.is(saved.input.triangles[0].vertices[0][0],-0));assert.equal(saves[0].mime,'application/json');lab.dispose();
});
test('row failure remains aggregate failure while successful and failed row diagnostics remain inspectable',async()=>{
 const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:async()=>r});ui.get('preset').value='middle_degenerate';ui.fire('preset','change');assert.equal(lab.getState().result.nearest,null);assert.match(ui.get('status').textContent,/集合モデル失敗/);assert.match(ui.get('view').getAttribute('aria-label'),/当該行の診断/);
 ui.get('inspect').value='1';ui.fire('inspect','change');assert.equal(parseStrictJson(ui.get('geometry').textContent).status,'degenerate');assert.doesNotMatch(ui.get('view').innerHTML,/fill="#fff"/);ui.get('inspect').value='2';ui.fire('inspect','change');assert.equal(parseStrictJson(ui.get('geometry').textContent).surfaceId,5);assert.equal(lab.getState().result.status,'row_failure');assert.match(ui.get('note').textContent,/集合nearestはありません/);lab.dispose();
});
test('synthetic fatal unexamined rows remain diagnostic nulls rather than misses or generated candidates',async()=>{
 const real=await runtime(),source=meshLabPreset('dominance'),result=real.querySphereTriangleMesh(source.sphere,source.triangles,source.settings);Object.assign(result,{status:'numerical_failure',reason:'allocation_failure',failedIndex:null,firstFailedRow:null,nearest:null,queries:0,candidatesExamined:0,sqrtRefinements:0,sqrtLimitedRows:0,failedRows:0});for(const row of result.rows)row.query=null;
 const ui=harness(),facade={diagnostics:{backend:'Synthetic fatal DTO display test, not allocation fault injection'},querySphereTriangleMesh(){return result;}},lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:async()=>facade});
 assert.match(ui.get('rows').innerHTML,/未照会 \/ fatal/);assert.match(ui.get('geometry').textContent,/未照会/);assert.match(ui.get('candidates').textContent,/候補は生成していません/);assert.equal(parseStrictJson(ui.get('json').textContent).result.rows[0].query,null);assert.doesNotMatch(ui.get('view').innerHTML,/fill="#fff"/);assert.equal(lab.getState().result.nearest,null);lab.dispose();
});
test('host and parse refusals clear stale result and recover without fallback or automatic source changes',async()=>{
 const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:async()=>r});ui.get('source').value='{bad';ui.fire('source','input');lab.run();cleared(ui,lab);assert.match(ui.get('error').textContent,/入力JSON/);
 ui.get('source').value=encode(meshLabPreset('capacity65'));lab.run();cleared(ui,lab);assert.match(ui.get('error').textContent,/SDK交換/);assert.equal(parseMeshLabInput(ui.get('source').value).triangles.length,65);
 r.failure=new SimulationError(1,'injected host refusal');ui.get('source').value=encode(meshLabPreset());lab.run();cleared(ui,lab);r.failure=null;lab.run();assert.equal(lab.getState().result.status,'completed');lab.dispose();
});
test('initial deferred loading plus input change never automatically queries a different source',async()=>{
 const ui=harness(),r=counted(await runtime()),wait=deferred(),initial=initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:()=>wait.promise});await flush();ui.get('source').value=encode(meshLabPreset('separate_tie'));ui.fire('source','input');wait.resolve(r);const lab=await initial;assert.equal(r.calls.length,0);cleared(ui,lab);assert.match(ui.get('status').textContent,/現在の入力を照会/);lab.run();assert.equal(r.calls.length,1);assert.deepEqual(lab.getState().result.nearest.possibleSurfaceIds,[7,99]);lab.dispose();
});
test('synchronous load failure and old SDK refusal can retry; reload blocks old runtime and coalesces',async()=>{
 const ui=harness(),r=counted(await runtime());let loads=0,next=null;const lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:()=>{loads++;if(loads===1)throw new Error('synchronous loader error');return next??r;}});cleared(ui,lab);assert.match(ui.get('error').textContent,/SDK初期化/);await lab.retry();assert.equal(r.calls.length,1);
 const wait=deferred();next=wait.promise;const one=lab.retry(),two=lab.retry();await flush();const count=r.calls.length;assert.equal(lab.run(),null);cleared(ui,lab);assert.equal(r.calls.length,count);assert.equal(loads,3);wait.resolve(r);await Promise.all([one,two]);assert.equal(r.calls.length,count+1);
 next={diagnostics:{backend:'old SDK'},querySphereTriangle(){assert.fail('No fallback');}};await lab.retry();cleared(ui,lab);assert.match(ui.get('error').textContent,/74-export/);next=r;await lab.retry();assert.equal(lab.getState().result.status,'completed');lab.dispose();
});
test('retry rejection and disposal prevent stale metadata geometry save and late resurrection',async()=>{
 const ui=harness(),r=counted(await runtime());let next=r;const lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:()=>next});const fail=deferred();next=fail.promise;const retry=lab.retry();await flush();assert.equal(ui.get('runtime').textContent,'SDK未初期化');fail.reject(new Error('delayed retry failed'));await retry;cleared(ui,lab);assert.equal(ui.get('controls').disabled,true);assert.equal(ui.get('retry').disabled,false);
 next=r;await lab.retry();const late=deferred();next=late.promise;const pending=lab.retry();await flush();lab.dispose();assert.equal(ui.listeners(),0);late.resolve(r);await pending;cleared(ui,lab);assert.equal(ui.get('controls').disabled,true);assert.equal(ui.get('retry').disabled,true);assert.equal(lab.run(),null);assert.equal(await lab.retry(),null);assert.equal(ui.fire('run'),undefined);
});
test('disposed retry ignores a late loader rejection and leaves no live event handlers',async()=>{
 const ui=harness(),r=counted(await runtime());let next=r;const lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:()=>next});const wait=deferred();next=wait.promise;const retry=lab.retry();await flush();lab.dispose();const status=ui.get('status').textContent;wait.reject(new Error('late disposal rejection'));await retry;cleared(ui,lab);assert.equal(ui.get('status').textContent,status);assert.equal(ui.listeners(),0);assert.equal(ui.get('runtime').textContent,'SDK未初期化');assert.equal(ui.get('retry').disabled,true);
});
test('save and display errors clear stale successful UI without replacing numerical results by a fallback',async()=>{
 const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshLab({doc:ui.doc,loadRuntime:async()=>r,saveFile(){throw new Error('save rejected');}});const count=r.calls.length;ui.fire('save');cleared(ui,lab);assert.match(ui.get('error').textContent,/保存/);lab.run();ui.get('projection').value='unknown';ui.fire('projection','change');cleared(ui,lab);assert.match(ui.get('error').textContent,/表示/);assert.equal(r.calls.length,count+1);lab.dispose();
});
