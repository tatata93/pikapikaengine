import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {flightLabPresetData,flightLabPresetProvenance} from '../tools/sphere-triangle-mesh-flight-presets.mjs';
import {flightLabPresets,flightLabPreset,parseFlightLabInput,evaluateFlightLab,serializeFlightLab,
  flightProjection,initializeSphereTriangleMeshFlightLab} from '../tools/sphere-triangle-mesh-flight-lab.mjs';

const inputBudget={maxBytes:131072,maxDepth:16,maxNodes:24000},budget={maxBytes:8388608,maxDepth:32,maxNodes:1000000};
const corpusBudget={maxBytes:67108864,maxDepth:64,maxNodes:4000000};
const clone=structuredClone,encode=q=>stringifyStrictJson(q,corpusBudget),id=n=>'flight-'+n;
let actual;const runtime=async()=>actual??=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const corpus={};for(const [cohort,info] of Object.entries(flightLabPresetProvenance.sourceFiles)){
  const bytes=await readFile(new URL('../'+info.path,import.meta.url));assert.equal(bytes.length,info.bytes);assert.equal(createHash('sha256').update(bytes).digest('hex'),info.sha256);
  corpus[cohort]=parseStrictJson(bytes.toString('utf8'),corpusBudget);
}
const receipt=await readFile(new URL('../'+flightLabPresetProvenance.receipt.path,import.meta.url));
assert.equal(receipt.length,flightLabPresetProvenance.receipt.bytes);assert.equal(createHash('sha256').update(receipt).digest('hex'),flightLabPresetProvenance.receipt.sha256);
const canonical=parseStrictJson(await readFile(new URL('../reports/sphere-triangle-mesh-flight-js-checks/run-20261104-final/owned/wasm-owned-dtos.json',import.meta.url),'utf8'),corpusBudget);
const raw=parseStrictJson(await readFile(new URL('../reports/sphere-triangle-mesh-flight-sdk-checks/run-20261104-final-002/native-exchange/packets.json',import.meta.url),'utf8'),corpusBudget);
const named=(cohort,name)=>cohort+'-'+name;
const H=n=>named('held',n),G=n=>named('guard',n),S=n=>named('supplemental',n);
const source=p=>{const f=corpus[p.cohort].fixtures.find(f=>f.name===p.fixtureName);assert.ok(f,p.name);return f;};
const original=p=>canonical.fixtures.find(f=>f.cohort===p.cohort&&f.name===p.fixtureName);
const chosen=name=>flightLabPresets.find(p=>p.name===name);
const call=(r,q)=>q.mode==='held'?r.querySphereTriangleMeshHeldLoad(q.sphere,q.triangles,q.horizon,q.settings):r.querySphereTriangleMeshFreeFlightGuard(q.body,q.gravity,q.triangles,q.horizon,q.settings);
const held=p=>p.mode==='held'?p.result:p.result.inflated;
const settings=s=>{const m=s.mesh,p=m.primitive;return [m.maxSurfaces,p.maxCandidates,p.sqrtRefinements,p.maxTotalSqrtRefinements,p.maximumLocalWidth,p.maximumNormalWidth,p.minimumSineSquared,s.timeTolerance,s.maxEvaluations,s.maxLeaves,s.maxDepth,s.enclosureSqrtRefinements,s.maxTotalSqrtRefinements];};
const echo=q=>q.mode==='held'?[q.sphere.id,...q.sphere.position,...q.sphere.velocity,q.sphere.mass,...q.sphere.force,...q.sphere.gravity,q.sphere.radius,q.horizon,...settings(q.settings),0,0,0]:
  [q.body.id,q.body.isStatic?1:0,q.body.mass,q.body.radius,...q.body.inertiaDiagonal,...q.body.position,...q.body.orientation,...q.body.velocity,...q.body.angularMomentum,...q.body.force,...q.body.torque,q.body.material.restitution,q.body.material.friction,...q.gravity,q.horizon,...settings(q.settings.heldLoad),q.settings.maxAngularIncrement,0,0];
const bits=n=>{const v=new DataView(new ArrayBuffer(8));v.setFloat64(0,n);return v.getBigUint64(0).toString(16).padStart(16,'0');};
const page=await readFile(new URL('../tools/sphere-triangle-mesh-flight-lab.html',import.meta.url),'utf8');
const ids=['status','error','retry','controls','mode','preset','source','query','reset','save','save-input','projection','audit','inspect','runtime','note','view','timeline','summary','initial','window','tube','endpoint','body','partition','geometry','candidates','json','rows','audits','leaves'];
function harness(){const nodes=new Map(),windowListeners=new Map();
  class LabWindow extends EventTarget{
    addEventListener(type,fn,options){super.addEventListener(type,fn,options);if(!windowListeners.has(type))windowListeners.set(type,new Set());windowListeners.get(type).add(fn);}
    removeEventListener(type,fn,options){super.removeEventListener(type,fn,options);windowListeners.get(type)?.delete(fn);}
  }
  const defaultView=new LabWindow();const doc={defaultView,getElementById(name){const suffix=name.replace(/^flight-/,'');assert.ok(ids.includes(suffix),'DOM contract '+name);
  if(!nodes.has(suffix)){const listeners=new Map(),attributes=new Map();nodes.set(suffix,{id:id(suffix),value:'',textContent:'',innerHTML:'',disabled:false,hidden:false,dataset:{},listeners,
    addEventListener(event,fn){if(!listeners.has(event))listeners.set(event,new Set());listeners.get(event).add(fn);},removeEventListener(event,fn){listeners.get(event)?.delete(fn);},
    setAttribute(k,v){attributes.set(k,String(v));},getAttribute(k){return attributes.get(k)??null;}});}return nodes.get(suffix);}};
  return {doc,get:name=>doc.getElementById(id(name)),fire(name,event='click'){const e=doc.getElementById(id(name));let value;for(const fn of [...(e.listeners.get(event)??[])])value=fn({target:e,currentTarget:e});return value;},
    pagehide(){const event=new Event('pagehide');Object.defineProperty(event,'persisted',{value:true});return defaultView.dispatchEvent(event);},
    windowListeners:type=>windowListeners.get(type)?.size??0,
    listeners(){let n=0;for(const e of nodes.values())for(const group of e.listeners.values())n+=group.size;for(const group of windowListeners.values())n+=group.size;return n;}};
}
function counted(real){const calls=[];let failure=null;return {calls,get diagnostics(){return real.diagnostics;},set failure(e){failure=e;},
  querySphereTriangleMeshHeldLoad(sphere,triangles,horizon,settings){calls.push(clone({mode:'held',sphere,triangles,horizon,settings}));if(failure)throw failure;return real.querySphereTriangleMeshHeldLoad(sphere,triangles,horizon,settings);},
  querySphereTriangleMeshFreeFlightGuard(body,gravity,triangles,horizon,settings){calls.push(clone({mode:'guard',body,gravity,triangles,horizon,settings}));if(failure)throw failure;return real.querySphereTriangleMeshFreeFlightGuard(body,gravity,triangles,horizon,settings);},
  querySphereTriangleMeshEntry(){assert.fail('No entry fallback');},querySphereTriangleMesh(){assert.fail('No instantaneous mesh fallback');}};}
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {resolve,reject,promise};};
const flush=async()=>{await Promise.resolve();await Promise.resolve();};
const select=(ui,name,value)=>{ui.get(name).value=String(value);return ui.fire(name,'change');};
function cleared(ui,lab){assert.equal(lab.getState(),null);assert.equal(ui.get('save').disabled,true);
  for(const name of ['audit','inspect']){assert.equal(ui.get(name).disabled,true);assert.equal(ui.get(name).innerHTML,'');}
  for(const name of ['rows','audits','leaves','timeline','view'])assert.equal(ui.get(name).innerHTML,'',name);
  for(const name of ['summary','initial','window','tube','endpoint','body','partition','geometry','candidates'])assert.equal(ui.get(name).textContent,'—',name);
  assert.equal(ui.get('json').textContent,'');}

test('thirty original preset sources preserve all input bits, modes/cohorts, source hashes and immutable metadata',()=>{
  assert.equal(flightLabPresets.length,30);assert.ok(Object.isFrozen(flightLabPresets));assert.equal(new Set(flightLabPresets.map(p=>p.name)).size,30);
  assert.equal(flightLabPresetProvenance.completeInputFingerprint,'4149030bf7278b5a91db1f2739c55491c82f57fc733254ee384153867f19ca54');
  for(const p of flightLabPresets){assert.ok(Object.isFrozen(p));assert.equal(typeof p.label,'string');assert.ok(p.label.length);
    const q=flightLabPreset(p.name),f=source(p);assert.deepEqual(q,{mode:p.mode,...f.input});
    const r=raw.fixtures.find(f=>f.cohort===p.cohort&&f.name===p.fixtureName);assert.deepEqual(echo(q).map(bits),r.inputBits,p.name+' Native input32/48');
    const data=flightLabPresetData.find(f=>f.name===p.name);assert.ok(Object.isFrozen(data)&&Object.isFrozen(data.input)&&Object.isFrozen(data.input.triangles));
    q.triangles[0].vertices[0][0]=999;assert.deepEqual(flightLabPreset(p.name),{mode:p.mode,...f.input});
  }
  assert.throws(()=>flightLabPreset('unknown'));const htmlIds=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(htmlIds).size,htmlIds.length);for(const name of ids)assert.ok(htmlIds.includes(id(name)),name);
});

test('all presets call the actual owned92 API exactly once and match complete canonical owned DTOs, with host kept separate',async()=>{
  const real=counted(await runtime());let models=0,hosts=0;
  for(const p of flightLabPresets){const q=flightLabPreset(p.name),saved=clone(q),before=real.calls.length,reference=original(p);assert.ok(reference,p.name);
    if(reference.result===null){assert.throws(()=>evaluateFlightLab(real,q));hosts++;}
    else{const packet=evaluateFlightLab(real,q);assert.equal(packet.mode,q.mode);assert.deepEqual(packet.input,q);assert.deepEqual(packet.result,reference.result,p.name);assert.deepEqual(parseStrictJson(serializeFlightLab(packet),budget).result,reference.result);models++;}
    assert.equal(real.calls.length,before+1,p.name+' one actual method');assert.deepEqual(q,saved);
  }assert.deepEqual({models,hosts},{models:29,hosts:1});
});

test('tagged input rejects duplicate/unknown/missing keys, null defaults, mixed body modes and strict JSON corruption',()=>{
  for(const text of ['{"mode":"held","mode":"guard"}','{"mode":"held","x":1}', '{"mode":"held","horizon":1e999}','{"mode":"held","x":"\\ud800"}','{bad'])assert.throws(()=>parseFlightLabInput(text));
  for(const name of [H('static-face'),G('safe-face-held-rotation')]){
    const original=flightLabPreset(name),bads=[q=>q.mode='other',q=>q.extra=1,q=>delete q.horizon,q=>q.settings=null,
      q=>(q.mode==='held'?q.settings:q.settings.heldLoad).mesh=null,q=>(q.mode==='held'?q.settings:q.settings.heldLoad).timeTolerance=null,
      q=>(q.mode==='held'?q.settings:q.settings.heldLoad).mesh.primitive=null,q=>q.triangles[0].extra=1,q=>q.triangles[0].vertices[0]=[1,2],q=>q.horizon='1'];
    if(original.mode==='held')bads.push(q=>q.body={},q=>delete q.sphere.force,q=>q.sphere.extra=1);else bads.push(q=>q.sphere={},q=>delete q.body.torque,q=>q.body.inertia=[1,1,1],q=>q.body.isStatic=0,q=>q.settings.heldLoad=null,q=>q.settings.maxAngularIncrement=null);
    for(const edit of bads){const q=clone(original);edit(q);assert.throws(()=>parseFlightLabInput(encode(q)));}
    const q=clone(original);q.settings={};const parsed=parseFlightLabInput(encode(q));assert.deepEqual(parsed,original);
  }
  const host=parseFlightLabInput(encode(flightLabPreset(H('65-source-rejection'))));assert.equal(host.triangles.length,65);
  assert.throws(()=>parseFlightLabInput(' '.repeat(inputBudget.maxBytes)+'{}'),/byte|budget|size/i);
});

test('both full mode packets own input, actual result and nested diagnostics independently of callers/runtime',async()=>{
  const real=await runtime();for(const name of [H('static-face'),G('safe-face-held-rotation')]){
    const q=flightLabPreset(name),answer=call(real,q),diagnostics={backend:'Captured actual owned DTO',nested:{owned:true}},facade={diagnostics,
      querySphereTriangleMeshHeldLoad(){return answer;},querySphereTriangleMeshFreeFlightGuard(){return answer;}};
    const packet=evaluateFlightLab(facade,q),saved=clone(packet);q.triangles[0].vertices[0][0]=999;diagnostics.nested.owned=false;answer.originalInput.triangles[0].id=999;
    assert.deepEqual(packet,saved);packet.input.triangles[0].id=777;assert.deepEqual(packet.result,saved.result);
  }
});

test('strict full export includes final LF, negative zero and exact8MiB bound while rejecting cycles/nonfinite/overflow',async()=>{
  const p=evaluateFlightLab(await runtime(),flightLabPreset(H('signed-source-zero'))),saved=clone(p);
  const text=serializeFlightLab(p,'yz',0,0),read=parseStrictJson(text,budget);assert.ok(text.endsWith('\n'));assert.deepEqual(read.result,p.result);assert.ok(Object.is(read.input.triangles[0].vertices[0][0],-0));
  assert.equal(read.projection,'yz');assert.equal(read.inspectedSurfaceId,p.input.triangles[0].id);assert.deepEqual(p,saved);
  p.diagnostics.padding='';const overhead=Buffer.byteLength(serializeFlightLab(p));p.diagnostics.padding='x'.repeat(budget.maxBytes-overhead);
  assert.equal(Buffer.byteLength(serializeFlightLab(p)),budget.maxBytes);p.diagnostics.padding+='x';assert.throws(()=>serializeFlightLab(p),/byte|budget|size/i);
  const bad=evaluateFlightLab(await runtime(),flightLabPreset());bad.diagnostics.bad=Infinity;assert.throws(()=>serializeFlightLab(bad));delete bad.diagnostics.bad;bad.diagnostics.cycle=bad;assert.throws(()=>serializeFlightLab(bad));
});

test('maximum256audits128leaves/partition127frontier and64source448candidates survive saved JSON and final selections',async()=>{
  const real=await runtime(),full=evaluateFlightLab(real,flightLabPreset(H('actual-256-audits-128-leaves')));
  const s=parseStrictJson(serializeFlightLab(full,'xz',255,0),budget);assert.equal(s.inspectedAudit,255);assert.equal(s.result.audits.length,256);assert.equal(s.result.certifiedLeaves.length,128);assert.equal(s.result.partition.length,128);assert.equal(s.result.certifiedLeaves[127].auditIndex,255);
  const b=held(evaluateFlightLab(real,flightLabPreset(H('breadth-frontier-budget'))));assert.equal(b.frontier.length,127);assert.equal(b.frontier[126].timeBounds[1],full.input.horizon);
  const p=evaluateFlightLab(real,flightLabPreset(H('actual-64-entry-all-conservative-ids'))),saved=parseStrictJson(serializeFlightLab(p,'xy',p.result.lastMeshAuditIndex,63),budget);
  assert.equal(saved.result.candidateSurfaceIds.length,64);assert.equal(saved.result.lastMesh.rows.length,64);assert.equal(saved.result.lastMesh.rows.reduce((n,r)=>n+r.query.candidates.length,0),448);assert.equal(saved.inspectedSurfaceId,p.input.triangles[63].id);
  assert.throws(()=>serializeFlightLab(full,'xy',256,0));assert.throws(()=>serializeFlightLab(full,'xy',255,1));assert.throws(()=>serializeFlightLab(full,'bad'));
});

test('guard radius/tube/candidate and nested entry never become original contact or previous successful state',async()=>{
  const real=await runtime(),safe=evaluateFlightLab(real,flightLabPreset(G('safe-face-held-rotation'))),failed=evaluateFlightLab(real,flightLabPreset(S('coarse-inflated-window-not-original-entry')));
  assert.equal(safe.result.status,'certified_separated');assert.equal(safe.result.inflated.snapshot.input.radius,safe.result.tube.guardRadius);assert.equal(safe.result.snapshot.body.radius,safe.input.body.radius);
  assert.deepEqual(safe.result.candidate.force,safe.input.body.force);assert.deepEqual(safe.result.candidate.torque,safe.input.body.torque);
  assert.equal(failed.result.status,'not_certified');assert.equal(failed.result.inflated.status,'entry_window');assert.equal(failed.result.candidate,null);
  const r=parseStrictJson(serializeFlightLab(failed),budget).result;assert.equal(r.candidate,null);assert.equal(r.inflated.window.timeWidth[1]<=failed.input.settings.heldLoad.timeTolerance,true);
});

test('projection uses only chosen owned boxes and lastMesh membership; viewing never issues more API queries',async()=>{
  const r=counted(await runtime()),p=evaluateFlightLab(r,flightLabPreset(H('actual-256-audits-128-leaves'))),saved=clone(p),count=r.calls.length;
  for(const projection of ['xy','xz','yz']){
    const earlier=flightProjection(p.input,p.result,projection,0,0),last=flightProjection(p.input,p.result,projection,255,0);
    assert.equal(earlier.available,true);assert.equal(earlier.geometryBelongsToSelectedAudit,false);assert.equal(earlier.closest,null);assert.ok(earlier.pathBox);assert.ok(earlier.pointBox);assert.ok(earlier.anchor);
    assert.equal(last.geometryBelongsToSelectedAudit,true);assert.ok(last.closest);earlier.triangles[0].vertices[0][0]=999;assert.deepEqual(p,saved);
  }assert.equal(r.calls.length,count);
  const g=evaluateFlightLab(r,flightLabPreset(G('rotation-increment-failure')));assert.equal(g.result.inflated,null);assert.equal(flightProjection(g.input,g.result).closest,null);
  assert.throws(()=>flightProjection(p.input,p.result,'bad'));assert.throws(()=>flightProjection(p.input,p.result,'xy',256,0));
});

test('finite oversized drawing is rejected independently while the actual invalid model and strict full JSON remain intact',async()=>{
  const real=await runtime(),q=flightLabPreset();q.sphere.position=[1e308,0,0];q.sphere.radius=1e308;
  const packet=evaluateFlightLab(real,q),saved=clone(packet);assert.equal(packet.result.status,'invalid_input');
  assert.equal(flightProjection(packet.input,packet.result).available,false);assert.deepEqual(packet,saved);assert.deepEqual(parseStrictJson(serializeFlightLab(packet),budget).result,packet.result);
});

test('controller renders all30 real classifications and full audit/source/leaf tables without hidden truncation',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r});
  assert.equal(r.calls.length,1);assert.equal((ui.get('preset').innerHTML.match(/<option /g)??[]).length,30);
  for(const preset of flightLabPresets){select(ui,'preset',preset.name);const expected=original(preset);
    if(expected.result===null){cleared(ui,lab);assert.equal(ui.get('error').hidden,false);continue;}
    const packet=lab.getState(),h=held(packet);assert.deepEqual(packet.input,flightLabPreset(preset.name));assert.deepEqual(packet.result,expected.result,preset.name);
    assert.deepEqual(parseStrictJson(ui.get('json').textContent,budget).result,packet.result);assert.equal(ui.get('error').hidden,true);
    assert.equal((ui.get('rows').innerHTML.match(/<tr>/g)??[]).length,packet.input.triangles.length);
    assert.equal((ui.get('audits').innerHTML.match(/<tr>/g)??[]).length,h?.audits.length??0);assert.equal((ui.get('leaves').innerHTML.match(/<tr>/g)??[]).length,h?.certifiedLeaves.length??0);
    assert.equal((ui.get('audit').innerHTML.match(/<option /g)??[]).length,h?.audits.length??0);
    if(preset.name===H('actual-256-audits-128-leaves')){select(ui,'audit',255);assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).selectedAudit,255);assert.match(ui.get('leaves').innerHTML,/<td>127<\/td>/);}
    if(preset.name===H('actual-64-entry-all-conservative-ids')){select(ui,'inspect',63);assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).rowQuery.candidates.length,7);}
  }assert.equal(r.calls.length,31);lab.dispose();
});

test('held wholePathBounds and wholeVelocityBounds show every owned component in the dedicated panel and projection',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r}),packet=lab.getState();
  const panel=parseStrictJson(ui.get('tube').textContent,budget);assert.deepEqual(panel.wholePathBounds,packet.result.wholePathBounds);assert.deepEqual(panel.wholeVelocityBounds,packet.result.wholeVelocityBounds);
  assert.equal(panel.wholePathBounds.flat().length,6);assert.equal(panel.wholeVelocityBounds.flat().length,6);
  const projection=flightProjection(packet.input,packet.result);assert.ok(projection.wholePathBox);lab.dispose();
});

test('editing clears all previous held/guard panels, geometry, tables, timeline, JSON and save immediately',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r});select(ui,'preset',G('safe-face-held-rotation'));
  const count=r.calls.length,q=flightLabPreset(G('safe-vertex'));ui.get('source').value=encode(q);ui.fire('source','input');cleared(ui,lab);assert.equal(r.calls.length,count);
  lab.run();assert.deepEqual(lab.getState().input,q);assert.equal(r.calls.length,count+1);const state=lab.getState(),copy=lab.getState();copy.result.worldBody.body.position[0]=999;assert.deepEqual(lab.getState(),state);
  ui.fire('reset');assert.deepEqual(lab.getState().input,flightLabPreset(G('safe-face-held-rotation')));lab.dispose();
});

test('mode change selects an explicit owned preset and clears without querying or converting body/sphere fields',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r}),before=r.calls.length;
  select(ui,'mode','guard');cleared(ui,lab);assert.equal(r.calls.length,before);
  const q=parseFlightLabInput(ui.get('source').value);assert.equal(q.mode,'guard');assert.ok(q.body);assert.equal('sphere' in q,false);
  assert.deepEqual(q,flightLabPreset(flightLabPresets.find(p=>p.mode==='guard').name));lab.run();assert.equal(r.calls.length,before+1);
  select(ui,'mode','held');cleared(ui,lab);assert.equal(r.calls.length,before+1);assert.ok(parseFlightLabInput(ui.get('source').value).sphere);lab.dispose();
});

test('view selection and save callbacks use the same complete packet and never query; callbacks are not actual downloads',async()=>{
  const ui=harness(),r=counted(await runtime()),saves=[],lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r,saveFile:value=>saves.push(value)});
  select(ui,'preset',H('actual-256-audits-128-leaves'));const count=r.calls.length,before=lab.getState();select(ui,'audit',0);
  assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).lastMeshBelongsToSelectedAudit,false);select(ui,'audit',255);
  for(const projection of ['xy','xz','yz'])select(ui,'projection',projection);ui.fire('save');
  assert.equal(r.calls.length,count);assert.equal(saves.length,1);assert.equal(saves[0].text,ui.get('json').textContent);assert.equal(saves[0].mime,'application/json');assert.deepEqual(lab.getState(),before);
  const packet=parseStrictJson(saves[0].text,budget);assert.equal(packet.inspectedAudit,255);assert.equal(packet.projection,'yz');assert.deepEqual(packet.result,before.result);
  select(ui,'preset',S('coarse-inflated-window-not-original-entry'));ui.fire('save');assert.equal(parseStrictJson(saves[1].text,budget).result.status,'not_certified');
  assert.equal(parseStrictJson(saves[1].text,budget).result.inflated.status,'entry_window');lab.dispose();
});

test('separate input-save callback contains the completed input only with signed zero and LF, not a fake model',async()=>{
  const ui=harness(),r=counted(await runtime()),saves=[],lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r,saveFile:value=>saves.push(value)});
  select(ui,'preset',H('signed-source-zero'));const before=lab.getState(),count=r.calls.length;ui.fire('save-input');assert.equal(r.calls.length,count);
  assert.equal(saves.length,1);assert.ok(saves[0].text.endsWith('\n'));assert.deepEqual(parseStrictJson(saves[0].text,inputBudget),before.input);assert.ok(Object.is(parseStrictJson(saves[0].text,inputBudget).triangles[0].vertices[0][0],-0));
  ui.fire('source','input');cleared(ui,lab);assert.equal(ui.get('save-input').disabled,true);lab.dispose();
});

test('initial witness/guard/missing-inflated and failed later rows never borrow old geometry or candidate',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r});
  select(ui,'preset',H('initial-strict-negative'));assert.equal(lab.getState().result.status,'initial_penetration');assert.equal(lab.getState().result.window,null);
  select(ui,'preset',H('middle-degenerate-later-row-preserved'));select(ui,'inspect',1);assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).rowQuery.status,'degenerate');select(ui,'inspect',2);assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).rowQuery.status,'completed');
  select(ui,'preset',G('safe-face-held-rotation'));assert.ok(lab.getState().result.candidate);select(ui,'preset',G('rotation-increment-failure'));assert.equal(lab.getState().result.inflated,null);assert.equal(lab.getState().result.candidate,null);
  assert.equal(ui.get('audit').disabled,true);assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).rowQuery,null);lab.dispose();
});

test('parse/host/capability refusals clear stale results and recover without rewriting the65-source input',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r}),count=r.calls.length;
  ui.get('source').value='{bad';ui.fire('source','input');lab.run();cleared(ui,lab);assert.equal(r.calls.length,count);assert.match(ui.get('error').textContent,/入力JSON/);
  ui.get('source').value=encode(flightLabPreset(H('65-source-rejection')));lab.run();cleared(ui,lab);assert.equal(parseFlightLabInput(ui.get('source').value).triangles.length,65);
  r.failure=new SimulationError(1,'Synthetic host refusal');ui.get('source').value=encode(flightLabPreset());lab.run();cleared(ui,lab);r.failure=null;lab.run();assert.ok(lab.getState());lab.dispose();
});

test('loading an edited generation performs no automatic query until explicit run',async()=>{
  const ui=harness(),r=counted(await runtime()),wait=deferred(),pending=initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:()=>wait.promise});await flush();
  select(ui,'mode','guard');const input=flightLabPreset(G('safe-face-held-rotation'));ui.get('source').value=encode(input);ui.fire('source','input');wait.resolve(r);const lab=await pending;
  assert.equal(r.calls.length,0);cleared(ui,lab);lab.run();assert.equal(r.calls.length,1);assert.deepEqual(lab.getState().input,input);lab.dispose();
});

test('sync loader error, Promise rejection, coalesced double retry and missing methods recover with current clean generation',async()=>{
  const ui=harness(),r=counted(await runtime());let next=r,loads=0;
  const lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:()=>{loads++;if(loads===1)throw Error('Sync loader failure');return next;}});cleared(ui,lab);
  await lab.retry();assert.equal(r.calls.length,1);const wait=deferred();next=wait.promise;const one=lab.retry(),two=lab.retry();assert.strictEqual(one,two);await flush();cleared(ui,lab);assert.equal(lab.run(),null);wait.resolve(r);await one;assert.equal(r.calls.length,2);
  next={diagnostics:{backend:'Old92 API unavailable'},querySphereTriangleMeshEntry(){assert.fail('No old fallback');}};await lab.retry();cleared(ui,lab);assert.equal(ui.get('error').hidden,false);
  next=r;await lab.retry();assert.ok(lab.getState());lab.dispose();
});

test('retry rejects old runtime, load-time edits suppress auto query, disposal removes handlers and late callbacks',async()=>{
  const ui=harness(),r=counted(await runtime());let next=r;const lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:()=>next});
  const edit=deferred();next=edit.promise;const pending=lab.retry();await flush();cleared(ui,lab);const count=r.calls.length;
  select(ui,'mode','guard');ui.get('source').value=encode(flightLabPreset(G('safe-edge')));ui.fire('source','input');edit.resolve(r);await pending;assert.equal(r.calls.length,count);cleared(ui,lab);lab.run();assert.equal(lab.getState().mode,'guard');
  const fail=deferred();next=fail.promise;const bad=lab.retry();await flush();fail.reject(Error('Retry failure'));await bad;cleared(ui,lab);
  next=r;await lab.retry();const late=deferred();next=late.promise;const loading=lab.retry();await flush();lab.dispose();const before=r.calls.length;late.resolve(r);await loading;
  cleared(ui,lab);assert.equal(ui.listeners(),0);assert.equal(r.calls.length,before);assert.equal(lab.run(),null);assert.equal(await lab.retry(),null);
});

test('disposed late rejection never resurrects runtime/status; save and projection failures require explicit recovery',async()=>{
  const ui=harness(),r=counted(await runtime());let next=r;const lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:()=>next,saveFile(){throw Error('Save failed');}}),count=r.calls.length;
  ui.fire('save');cleared(ui,lab);lab.run();assert.equal(r.calls.length,count+1);select(ui,'projection','invalid');cleared(ui,lab);ui.get('projection').value='xy';lab.run();
  const wait=deferred();next=wait.promise;const pending=lab.retry();await flush();lab.dispose();const status=ui.get('status').textContent;wait.reject(Error('Late rejection'));await pending;
  cleared(ui,lab);assert.equal(ui.get('status').textContent,status);assert.equal(ui.listeners(),0);
});

test('actual pagehide event invalidates initial/retry loader generations before late resolve or rejection',async()=>{
  const real=await runtime();
  for(const phase of ['initial','retry'])for(const completion of ['resolve','reject']){
    const ui=harness(),r=counted(real),saves=[],wait=deferred();let next=phase==='initial'?wait.promise:r,lab;
    const first=initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:()=>next,saveFile:value=>saves.push(value)});
    let pending=first;if(phase==='retry'){lab=await first;next=wait.promise;pending=lab.retry();}
    await flush();assert.equal(ui.windowListeners('pagehide'),1);const count=r.calls.length;
    ui.pagehide();assert.equal(ui.windowListeners('pagehide'),0);assert.equal(ui.listeners(),0);
    if(completion==='resolve')wait.resolve(r);else wait.reject(Error('Late loader rejection after actual pagehide'));
    const result=await pending;if(phase==='initial')lab=result;
    cleared(ui,lab);assert.equal(r.calls.length,count,phase+'/'+completion);assert.equal(saves.length,0);assert.equal(lab.run(),null);assert.equal(await lab.retry(),null);
    const status=ui.get('status').textContent;lab.dispose();lab.dispose();ui.pagehide();assert.equal(ui.get('status').textContent,status);
    assert.equal(ui.get('retry').disabled,true);assert.equal(ui.get('save-input').disabled,true);assert.equal(ui.listeners(),0);
  }
});

test('pagehide clears displayed full results and blocks queued old callbacks, saving and queries with idempotent disposal',async()=>{
  const ui=harness(),r=counted(await runtime()),saves=[],lab=await initializeSphereTriangleMeshFlightLab({doc:ui.doc,loadRuntime:async()=>r,saveFile:value=>saves.push(value)});
  select(ui,'preset',G('safe-face-held-rotation'));assert.ok(lab.getState().result.candidate);
  const queued=[];for(const name of ['query','retry','reset','save','save-input','source','mode','preset','projection','audit','inspect']){
    const element=ui.get(name);for(const handlers of element.listeners.values())for(const handler of handlers)queued.push(()=>handler({target:element,currentTarget:element}));
  }
  const count=r.calls.length;assert.equal(ui.windowListeners('pagehide'),1);ui.pagehide();cleared(ui,lab);assert.equal(ui.listeners(),0);
  const status=ui.get('status').textContent;for(const callback of queued)await callback();await flush();
  assert.equal(r.calls.length,count);assert.equal(saves.length,0);cleared(ui,lab);assert.equal(ui.get('status').textContent,status);
  lab.dispose();lab.dispose();ui.pagehide();assert.equal(ui.listeners(),0);assert.equal(lab.run(),null);assert.equal(await lab.retry(),null);
});
