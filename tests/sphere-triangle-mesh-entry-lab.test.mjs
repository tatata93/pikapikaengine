import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {entryLabPresets,entryLabPreset,parseEntryLabInput,evaluateEntryLab,serializeEntryLab,
  entryProjection,initializeSphereTriangleMeshEntryLab} from '../tools/sphere-triangle-mesh-entry-lab.mjs';

let actual;
const runtime=async()=>actual??=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const clone=structuredClone,encode=stringifyStrictJson;
const budget={maxBytes:8388608,maxDepth:32,maxNodes:1000000};
const names=['static-face','actual-256-audits-128-leaves','actual-64-entry-all-conservative-ids','breadth-frontier-budget',
  '127-leaf-budget-preserves-prefix','255-evaluation-budget-includes-initial','analytic-entry-quarter','symmetric-midpoint-normal-failure',
  'multiple-entries-first-quarter','wide-tolerance-is-still-proof','tight-tolerance-depth-budget','initial-strict-negative',
  'initial-exact-boundary','initial-zero-distance-normal-failure','exact-vertex-tangency-no-negative','middle-degenerate-later-row-preserved',
  'surface-budget-before-query','sqrt-reservation-before-mesh','sqrt-reservation-before-enclosure','duplicate-source-id','empty-source',
  'endpoint-outside-domain','invalid-tolerance-zero','65-source-rejection','inside-rounded-anchor-no-false-witness'];
const corpus=JSON.parse(await readFile(new URL('../reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',import.meta.url),'utf8'));
const original=name=>{const f=corpus.fixtures.find(f=>f.name===name);assert.ok(f,name);return clone(f);};
const call=(r,q)=>r.querySphereTriangleMeshEntry({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings);
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const singleStatuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const singleReasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
function nativeModel(result){
  // Enum-only projection of the frozen reference; no geometry/interval solver.
  const r=clone(result);delete r.originalInput;
  for(const a of r.audits){if(a.meshStatus!==null)a.meshStatus=meshStatuses.indexOf(a.meshStatus);if(a.meshReason!==null)a.meshReason=meshReasons.indexOf(a.meshReason);}
  if(r.lastMesh){const m=r.lastMesh;m.status=meshStatuses.indexOf(m.status);m.reason=meshReasons.indexOf(m.reason);
    for(const row of m.rows)if(row.query){const q=row.query;q.status=singleStatuses.indexOf(q.status);q.reason=singleReasons.indexOf(q.reason);
      if(q.geometry)q.geometry.relation=['separated','penetrating','touching','boundary_unresolved'].indexOf(q.geometry.relation);
      for(const c of q.candidates){c.feature=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'].indexOf(c.feature);c.disposition=['retained','outside_simplex','kkt_violated'].indexOf(c.disposition);}}
  }return r;
}
const page=await readFile(new URL('../tools/sphere-triangle-mesh-entry-lab.html',import.meta.url),'utf8');
const pageIds=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
const ids=['status','error','retry','controls','preset','source','projection','inspect','audit','query','reset','save','runtime','note','view',
  'summary','initial','window','rows','audits','geometry','candidates','json','leaves','partition','timeline'];
function harness(){
  const elements=new Map();
  function get(name){const id=name.startsWith('entry-')?name:'entry-'+name;assert.ok(ids.includes(id.slice(6)),'Contract DOM ID '+id);
    if(!elements.has(id)){const listeners=new Map(),attributes=new Map();elements.set(id,{id,value:'',textContent:'',innerHTML:'',disabled:false,hidden:false,listeners,
      addEventListener(event,fn){if(!listeners.has(event))listeners.set(event,new Set());listeners.get(event).add(fn);},
      removeEventListener(event,fn){listeners.get(event)?.delete(fn);},setAttribute(k,v){attributes.set(k,String(v));},getAttribute(k){return attributes.get(k)??null;}});}
    return elements.get(id);
  }
  return {get,doc:{getElementById:get},fire(name,event='click'){const e=get(name);let out;for(const fn of [...(e.listeners.get(event)??[])])out=fn({target:e,currentTarget:e});return out;},
    listeners(){let n=0;for(const e of elements.values())for(const a of e.listeners.values())n+=a.size;return n;}};
}
function counted(real){let failure=null;const calls=[];return {calls,get diagnostics(){return real.diagnostics;},set failure(error){failure=error;},
  querySphereTriangleMeshEntry(path,triangles,settings){calls.push(clone({path,triangles,settings}));if(failure)throw failure;return real.querySphereTriangleMeshEntry(path,triangles,settings);},
  querySphereTriangleMesh(){assert.fail('No mesh fallback');},querySphereTriangleMeshTrajectory(){assert.fail('No old guard fallback');}};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const flush=async()=>{await Promise.resolve();await Promise.resolve();};
function cleared(ui,lab){
  assert.equal(lab.getState(),null);assert.equal(ui.get('save').disabled,true);
  for(const name of ['inspect','audit']){assert.equal(ui.get(name).disabled,true);assert.equal(ui.get(name).innerHTML,'');}
  for(const name of ['rows','audits','leaves','timeline','view'])assert.equal(ui.get(name).innerHTML,'',name);
  for(const name of ['summary','initial','window','partition','geometry','candidates'])assert.equal(ui.get(name).textContent,'—',name);
  assert.equal(ui.get('json').textContent,'');
}
const select=(ui,name,value)=>{ui.get(name).value=String(value);return ui.fire(name,'change');};

test('exact25 frozen preset sources labels and real HTML controls remain independently owned',()=>{
  assert.deepEqual(entryLabPresets.map(p=>p.name),names);assert.ok(Object.isFrozen(entryLabPresets));
  assert.ok(entryLabPresets.every(p=>Object.isFrozen(p)&&p.fixtureName===p.name&&typeof p.label==='string'&&p.label.length));
  assert.equal(new Set(pageIds).size,pageIds.length);for(const id of ids)assert.ok(pageIds.includes('entry-'+id),'Actual HTML '+id);
  const options=page.match(/<select id="entry-preset">([\s\S]*?)<\/select>/)[1];
  const staticOptions=[...options.matchAll(/<option value="([^"]+)"/g)].map(m=>m[1]);assert.deepEqual(staticOptions,staticOptions.length===1?[names[0]]:names);
  for(const name of names){const a=entryLabPreset(name),b=entryLabPreset(name);assert.deepEqual(a,original(name).input,name);assert.deepEqual(a,b);
    a.start[0]=9;a.settings.parameterTolerance=1;if(a.triangles.length)a.triangles[0].vertices[0][0]=9;assert.deepEqual(entryLabPreset(name),b);}
  assert.deepEqual(entryLabPreset(),entryLabPreset('static-face'));assert.throws(()=>entryLabPreset('unknown'));
});

test('strict parser preserves signed zero and model-invalid finite inputs while enforcing shape and budgets',()=>{
  const q=entryLabPreset(),defaults=clone(q.settings);q.settings={};assert.deepEqual(parseEntryLabInput(encode(q)).settings,defaults);assert.deepEqual(q.settings,{});
  assert.equal(defaults.parameterTolerance,1e-6);assert.equal(defaults.maxDepth,24);
  const base=entryLabPreset(),bad=[];for(const key of ['start','end','radius','triangles','settings']){const q=clone(base);delete q[key];bad.push(q);}
  bad.push({...base,unknown:1},{...base,start:[0,0]},{...base,end:[0,'1',0]},{...base,radius:null},
    {...base,triangles:[{...base.triangles[0],unknown:1}]},{...base,triangles:[{id:1,vertices:[[0,0,0]]}]},
    {...base,triangles:Array(66).fill(base.triangles[0])},{...base,settings:null},{...base,settings:[]},{...base,settings:{unknown:1}},
    {...base,settings:{mesh:null}},{...base,settings:{mesh:{primitive:null}}},{...base,settings:{mesh:{primitive:{unknown:1}}}},{...base,settings:{maxLeaves:null}});
  for(const value of bad)assert.throws(()=>parseEntryLabInput(encode(value)));
  const text=encode(base);for(const invalid of [text.slice(0,-1)+',"start":[0,0,0]}',text.replace('"radius":0.25','"radius":NaN'),
    text.replace('"radius":0.25','"radius":1e999'),text.replace('"radius":0.25','"radius":1e-999'),text+' trailing',' '.repeat(65537)+text,
    text.replace('"start"','"\\ud800"')])assert.throws(()=>parseEntryLabInput(invalid));
  const sparse=clone(base);sparse.start=Array(3);assert.throws(()=>evaluateEntryLab({},sparse));
  const finite=clone(base);finite.radius=0;finite.settings.parameterTolerance=0;finite.settings.maxLeaves=0;
  assert.deepEqual(parseEntryLabInput(encode(finite)),finite);assert.equal(parseEntryLabInput(encode(entryLabPreset('65-source-rejection'))).triangles.length,65);
  const signed=original('signed-source-zero').input;assert.deepEqual(parseEntryLabInput(encode(signed)),signed);
});

test('all25 presets make exactly one actual entry call and match24 full Native model DTOs with one host refusal',async()=>{
  const real=await runtime(),r=counted(real),counts={};
  for(const name of names){const source=entryLabPreset(name),before=clone(source),n=r.calls.length;
    if(name==='65-source-rejection'){assert.throws(()=>evaluateEntryLab(r,source),/64/);assert.equal(r.calls.length,n+1);continue;}
    const p=evaluateEntryLab(r,source);assert.equal(r.calls.length,n+1);assert.equal(p.schema,1);assert.equal(p.kind,'sphere-triangle-mesh-entry-lab');
    assert.deepEqual(p.input,source);assert.deepEqual(source,before);assert.equal(p.diagnostics.backend,'C++ WebAssembly');
    assert.deepEqual(nativeModel(p.result),original(name).result,name+' complete Native model');assert.deepEqual(p.result,call(real,source));
    counts[p.result.status]=(counts[p.result.status]??0)+1;
    const saved=parseStrictJson(serializeEntryLab(p),budget);assert.deepEqual(saved.input,p.input);assert.deepEqual(saved.result,p.result);
  }
  assert.deepEqual(counts,{separated:2,entry_window:5,not_certified:12,initial_penetration:1,invalid_input:4});assert.equal(r.calls.length,25);
});

test('entry initial prefix witness width conservative IDs and later proof islands keep their separate meaning',async()=>{
  const real=await runtime(),p=evaluateEntryLab(real,entryLabPreset('analytic-entry-quarter')),r=p.result;
  assert.ok(r.initial.lowerGapCertificate[0]>0);assert.equal(r.initialSeparationProven,true);assert.ok(r.window.parameter[0]<.25&&r.window.parameter[1]>.25);
  assert.ok(r.window.width[1]<=p.input.settings.parameterTolerance);assert.deepEqual(r.safePrefix,[0,r.window.parameter[0]]);
  assert.ok(r.bestWitness.upperGapCertificate[1]<0);assert.equal(r.bestWitness.parameter,r.window.parameter[1]);assert.equal(r.window.witnessAuditIndex,r.bestWitness.auditIndex);
  assert.ok(r.certifiedLeaves.some(l=>l.cell.parameter[0]>r.safePrefix[1]));assert.equal('time' in r,false);
  const multi=evaluateEntryLab(real,entryLabPreset('multiple-entries-first-quarter')).result;
  assert.deepEqual(multi.candidateSurfaceIds,[5,37]);assert.deepEqual(multi.lastMesh.nearest.possibleSurfaceIds,[37]);
  const wide=evaluateEntryLab(real,entryLabPreset('wide-tolerance-is-still-proof')).result;assert.deepEqual(wide.safePrefix,[0,0]);assert.deepEqual(wide.window.parameter,[0,.375]);
  assert.ok(wide.certifiedLeaves.some(l=>l.cell.parameter[0]===.5&&l.cell.parameter[1]===1));
  const failedAncestor=evaluateEntryLab(real,entryLabPreset('symmetric-midpoint-normal-failure')).result;
  assert.equal(failedAncestor.status,'entry_window');assert.equal(failedAncestor.audits[1].meshStatus,'row_failure');assert.equal(failedAncestor.audits[1].outcome,'split');
  assert.equal(failedAncestor.audits[1].clearanceCertificate,null);assert.ok(failedAncestor.bestWitness.auditIndex>1);
  const limited=evaluateEntryLab(real,entryLabPreset('tight-tolerance-depth-budget')).result;assert.ok(limited.bestWitness);assert.equal(limited.window,null);
});

test('full256 audits128 leaves and partition tails plus127 frontier and127-leaf failure survive strict export',async()=>{
  const real=await runtime(),full=evaluateEntryLab(real,entryLabPreset('actual-256-audits-128-leaves')),before=clone(full);
  const saved=parseStrictJson(serializeEntryLab(full,'yz',255,0),budget);
  assert.equal(saved.inspectedAudit,255);assert.equal(saved.inspectedOrdinal,0);assert.equal(saved.inspectedSurfaceId,37);assert.equal(saved.projection,'yz');
  assert.equal(saved.result.audits.length,256);assert.equal(saved.result.certifiedLeaves.length,128);assert.equal(saved.result.partition.length,128);
  assert.equal(saved.result.certifiedLeaves[127].auditIndex,255);assert.deepEqual(saved.result.partition[127].cell.parameter,[127/128,1]);assert.deepEqual(saved.result,full.result);assert.deepEqual(full,before);
  const breadth=evaluateEntryLab(real,entryLabPreset('breadth-frontier-budget')).result;assert.equal(breadth.frontier.length,127);assert.equal(breadth.frontier[126].parameter[1],1);assert.equal(breadth.partition.length,128);
  const limited=evaluateEntryLab(real,entryLabPreset('127-leaf-budget-preserves-prefix')).result;
  assert.equal(limited.status,'not_certified');assert.equal(limited.partitionLeaves,127);assert.equal(limited.certifiedLeaves.length,126);assert.equal(limited.audits.length,254);assert.equal(limited.window,null);
  const evaluated=evaluateEntryLab(real,entryLabPreset('255-evaluation-budget-includes-initial')).result;assert.equal(evaluated.audits.length,255);assert.equal(evaluated.certifiedLeaves.length,127);assert.ok(evaluated.current);
  assert.throws(()=>serializeEntryLab(full,'xy',256,0));assert.throws(()=>serializeEntryLab(full,'xy',255,1));assert.throws(()=>serializeEntryLab(full,'bad'));
});

test('all64 source IDs final448 candidate set and signed-zero source/KKT remain owned and saved',async()=>{
  const real=await runtime(),p=evaluateEntryLab(real,entryLabPreset('actual-64-entry-all-conservative-ids'));
  const s=parseStrictJson(serializeEntryLab(p,'xz',p.result.lastMeshAuditIndex,63),budget);
  assert.equal(s.result.candidateSurfaceIds.length,64);assert.deepEqual(s.result.candidateSurfaceIds,Array.from({length:64},(_,i)=>i+1));
  assert.equal(s.input.triangles.length,64);assert.equal(s.result.originalInput.triangles.length,64);assert.equal(s.result.lastMesh.rows.length,64);
  assert.equal(s.inspectedSurfaceId,s.input.triangles[63].id);assert.equal(s.result.lastMesh.rows[63].query.candidates[6].feature,'vertex_c');
  assert.equal(s.result.lastMesh.rows.reduce((n,row)=>n+row.query.candidates.length,0),448);assert.deepEqual(s.result,p.result);
  assert.ok(Object.is(s.result.lastMesh.rows[63].query.candidates[0].kkt[0][0],-0));
  const negative=evaluateEntryLab(real,original('signed-source-zero').input),parsed=parseStrictJson(serializeEntryLab(negative),budget);
  assert.ok(Object.is(parsed.input.start[0],-0));assert.ok(Object.is(parsed.result.originalInput.triangles[0].vertices[0][0],-0));assert.deepEqual(parsed.result,negative.result);
  const empty=evaluateEntryLab(real,entryLabPreset('empty-source')),e=parseStrictJson(serializeEntryLab(empty),budget);
  assert.equal(e.inspectedAudit,null);assert.equal(e.inspectedOrdinal,null);assert.equal(e.inspectedSurfaceId,null);assert.equal(e.result.snapshot,null);assert.ok(e.result.originalInput);
  assert.throws(()=>serializeEntryLab(empty,'xy',1,0));assert.throws(()=>serializeEntryLab(empty,'xy',0,1));assert.throws(()=>serializeEntryLab(null));
});

test('evaluate separately owns input result diagnostics and preserves actual host and capability failures',async()=>{
  const real=await runtime(),source=entryLabPreset(),answer=call(real,source),saved=clone(answer),diagnostics={backend:'Captured actual DTO',nested:{owned:true}},calls=[];
  const facade={diagnostics,querySphereTriangleMeshEntry(path,triangles,settings){calls.push(clone({path,triangles,settings}));return answer;},querySphereTriangleMesh(){assert.fail('No mesh fallback');}};
  const p=evaluateEntryLab(facade,source),before=clone(p);assert.equal(calls.length,1);assert.deepEqual(calls[0],{path:{start:source.start,end:source.end,radius:source.radius},triangles:source.triangles,settings:source.settings});
  source.start[0]=999;answer.audits[0].anchor[0]=999;diagnostics.nested.owned=false;assert.deepEqual(p,before);assert.deepEqual(p.result,saved);
  const failure=new SimulationError(1,'Captured host refusal');assert.throws(()=>evaluateEntryLab({querySphereTriangleMeshEntry(){throw failure;}},entryLabPreset()),e=>e===failure);
  assert.throws(()=>evaluateEntryLab({querySphereTriangleMeshTrajectory(){assert.fail('No old guard fallback');}},entryLabPreset()));
});

test('strict complete export accounts for its final LF at the exact eight-MiB boundary',async()=>{
  const p=evaluateEntryLab(await runtime(),entryLabPreset()),limit=8388608;p.diagnostics.padding='';const overhead=Buffer.byteLength(serializeEntryLab(p),'utf8');
  p.diagnostics.padding='x'.repeat(limit-overhead);const text=serializeEntryLab(p);assert.equal(Buffer.byteLength(text,'utf8'),limit);assert.ok(text.endsWith('\n'));
  p.diagnostics.padding+='x';assert.throws(()=>serializeEntryLab(p),/byte|budget|size/i);
});

test('projection reads selected owned audit boxes and never attaches last mesh to earlier or unqueried points',async()=>{
  const real=await runtime(),p=evaluateEntryLab(real,entryLabPreset('actual-256-audits-128-leaves')),before=clone(p),last=p.result.lastMeshAuditIndex;assert.equal(last,255);
  for(const projection of ['xy','xz','yz']){const earlier=entryProjection(p.input,p.result,projection,0,0),actualLast=entryProjection(p.input,p.result,projection,last,0);
    assert.equal(earlier.available,true);assert.equal(earlier.inspectedAudit,0);assert.equal(earlier.lastMeshAuditIndex,last);assert.equal(earlier.geometryBelongsToSelectedAudit,false);assert.equal(earlier.closest,null);
    assert.ok(earlier.pathBox);assert.ok(earlier.pointBox);assert.ok(earlier.anchor);assert.equal(actualLast.geometryBelongsToSelectedAudit,true);assert.ok(actualLast.closest);
    earlier.triangles[0].vertices[0][0]=999;assert.deepEqual(p,before);}
  const unqueried=evaluateEntryLab(real,entryLabPreset('sqrt-reservation-before-mesh')),v=entryProjection(unqueried.input,unqueried.result,'xy',0,0);
  assert.equal(v.closest,null);assert.equal(v.geometryBelongsToSelectedAudit,false);assert.deepEqual(unqueried.result.current,{parameter:[0,0],depth:0});
  const huge=entryLabPreset();huge.start=[1e308,0,0];huge.end=[-1e308,0,0];huge.radius=1e308;const invalid=evaluateEntryLab(real,huge);
  assert.equal(invalid.result.status,'invalid_input');assert.equal(entryProjection(invalid.input,invalid.result).available,false);assert.equal(invalid.result.status,'invalid_input');
  assert.throws(()=>entryProjection(p.input,p.result,'bad'));assert.throws(()=>entryProjection(p.input,p.result,'xy',256,0));
});

test('actual UI renders all25 classifications and complete max tables without hidden rows or success relabelling',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:async()=>r});assert.equal(r.calls.length,1);
  assert.equal((ui.get('preset').innerHTML.match(/<option /g)??[]).length,25);
  for(const name of names){select(ui,'preset',name);
    if(name==='65-source-rejection'){cleared(ui,lab);assert.equal(ui.get('error').hidden,false);assert.match(ui.get('error').textContent,/SDK交換/);continue;}
    const p=lab.getState();assert.deepEqual(p.input,entryLabPreset(name));assert.equal(p.result.status,original(name).result.status,name);
    assert.deepEqual(parseStrictJson(ui.get('json').textContent,budget).result,p.result);assert.equal((ui.get('rows').innerHTML.match(/<tr>/g)??[]).length,p.input.triangles.length);
    assert.equal((ui.get('leaves').innerHTML.match(/<tr>/g)??[]).length,p.result.certifiedLeaves.length);assert.equal((ui.get('audits').innerHTML.match(/<tr>/g)??[]).length,p.result.audits.length);
    assert.equal((ui.get('audit').innerHTML.match(/<option /g)??[]).length,p.result.audits.length);assert.equal(ui.get('error').hidden,true);
    const labels={separated:/strict非接触/,entry_window:/開始窓/,initial_penetration:/初期.*貫通/,not_certified:/未認証/,invalid_input:/モデル入力を拒否/};assert.match(ui.get('status').textContent,labels[p.result.status]);
    if(name==='actual-256-audits-128-leaves'){select(ui,'audit',255);const g=parseStrictJson(ui.get('geometry').textContent,budget);assert.equal(g.selectedAudit,255);assert.deepEqual(g.audit,p.result.audits[255]);assert.equal(g.lastMeshBelongsToSelectedAudit,true);assert.match(ui.get('leaves').innerHTML,/<td>127<\/td>/);}
    if(name==='actual-64-entry-all-conservative-ids'){select(ui,'inspect',63);const g=parseStrictJson(ui.get('geometry').textContent,budget);assert.equal(g.surfaceId,p.input.triangles[63].id);assert.equal(g.rowQuery.candidatesExamined,7);assert.match(ui.get('candidates').textContent,/vertex_c/);}
  }
  assert.equal(r.calls.length,26);lab.dispose();
});

test('input edits immediately clear initial window audit tables partition drawing JSON and save until explicit query',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:async()=>r});select(ui,'preset','analytic-entry-quarter');assert.ok(lab.getState().result.window);
  const count=r.calls.length,source=entryLabPreset();source.end[0]=1.125;ui.get('source').value=encode(source);ui.fire('source','input');cleared(ui,lab);assert.equal(r.calls.length,count);
  ui.fire('query');assert.deepEqual(lab.getState().input,source);assert.equal(r.calls.length,count+1);
  const saved=lab.getState(),copy=lab.getState();copy.result.audits[0].anchor[0]=999;assert.deepEqual(lab.getState(),saved);
  ui.fire('reset');assert.deepEqual(lab.getState().input,entryLabPreset('analytic-entry-quarter'));lab.dispose();
});

test('all browsing and actual Blob save preserve complete strict signed-zero bytes without another query',async()=>{
  const ui=harness(),r=counted(await runtime()),saves=[],blobs=[],lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:async()=>r,
    saveFile:value=>{saves.push(value);blobs.push(new Blob([value.text],{type:value.mime}));}});
  select(ui,'preset','actual-256-audits-128-leaves');const before=lab.getState(),count=r.calls.length;
  select(ui,'audit',0);assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).lastMeshBelongsToSelectedAudit,false);assert.match(ui.get('note').textContent,/属さないlastMesh/);
  select(ui,'audit',255);for(const projection of ['xy','xz','yz'])select(ui,'projection',projection);ui.fire('save');
  assert.equal(r.calls.length,count);assert.deepEqual(lab.getState(),before);assert.equal(saves[0].text,ui.get('json').textContent);assert.ok(saves[0].text.endsWith('\n'));
  assert.equal(blobs[0].type,'application/json');assert.equal(await blobs[0].text(),saves[0].text);const p=parseStrictJson(await blobs[0].text(),budget);
  assert.equal(p.inspectedAudit,255);assert.equal(p.projection,'yz');assert.deepEqual(p.result,before.result);
  ui.get('source').value=encode(original('signed-source-zero').input);ui.fire('source','input');lab.run();const signedCount=r.calls.length;ui.fire('save');
  const negative=parseStrictJson(await blobs[1].text(),budget);assert.ok(Object.is(negative.input.start[0],-0));assert.ok(Object.is(negative.result.originalInput.start[0],-0));assert.equal(r.calls.length,signedCount);
  lab.dispose();
});

test('initial/window panels and selected geometry keep initial proof and last mesh membership separate',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:async()=>r});
  select(ui,'preset','initial-strict-negative');assert.equal(lab.getState().result.status,'initial_penetration');assert.equal(lab.getState().result.window,null);assert.ok(ui.get('initial').textContent.includes('upperGapCertificate'));
  select(ui,'preset','initial-exact-boundary');assert.equal(lab.getState().result.reason,'initial_boundary');assert.equal(lab.getState().result.safePrefix,null);
  select(ui,'preset','symmetric-midpoint-normal-failure');const count=r.calls.length;select(ui,'audit',1);const ancestor=parseStrictJson(ui.get('geometry').textContent,budget);
  assert.equal(ancestor.audit.meshStatus,'row_failure');assert.equal(ancestor.audit.outcome,'split');assert.equal(ancestor.lastMeshBelongsToSelectedAudit,false);assert.equal(lab.getState().result.status,'entry_window');
  select(ui,'preset','middle-degenerate-later-row-preserved');select(ui,'inspect',1);assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).rowQuery.status,'degenerate');
  select(ui,'inspect',2);assert.equal(parseStrictJson(ui.get('geometry').textContent,budget).rowQuery.status,'completed');
  select(ui,'preset','sqrt-reservation-before-mesh');const g=parseStrictJson(ui.get('geometry').textContent,budget);
  assert.equal(g.audit.kind,'initial_point');assert.equal(g.audit.meshQueried,false);assert.equal(g.lastMesh,null);assert.equal(g.rowQuery,null);assert.match(ui.get('rows').innerHTML,/未照会/);
  assert.match(ui.get('candidates').textContent,/候補を生成していません/);assert.equal(lab.getState().result.initial,null);assert.equal(lab.getState().result.safePrefix,null);assert.equal(r.calls.length,count+2);
  lab.dispose();
});

test('synthetic unknown-work display keeps positive initial proof and conservative reservation without claiming a natural fault',async()=>{
  const real=await runtime(),q=entryLabPreset(),result=call(real,q),a=result.audits[1],initial=result.audits[0];
  result.status='numerical_failure';result.reason='nonfinite_intermediate';result.certifiedLeaves=[];result.safePrefix=[0,0];result.current=clone(a.cell);a.outcome='unresolved';
  result.partition=[{cell:clone(a.cell),state:'current',auditIndex:1,blockedReason:'nonfinite_intermediate'}];result.frontier=[];
  for(const key of ['displacementRoot','errorRoot','clearanceCertificate','penetrationCertificate'])a[key]=null;
  a.work.enclosureSqrtRefinements=0;a.work.sqrtRefinements=a.work.primitiveSqrtRefinements;a.work.sqrtRefinementsUpper=a.work.sqrtRefinements+512;a.work.enclosureSqrtCalls=1;a.work.enclosureSqrtLimitedCalls=0;a.work.workExact=false;
  for(const key of Object.keys(result.work))result.work[key]=key==='workExact'?false:initial.work[key]+a.work[key];
  const ui=harness(),facade={diagnostics:{backend:'Artificial DTO display; no Native fault injection'},querySphereTriangleMeshEntry(){return result;}};
  const lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:async()=>facade}),summary=parseStrictJson(ui.get('summary').textContent,budget);
  assert.equal(summary.work.workExact,false);assert.equal(summary.work.sqrtRefinementsUpper,summary.work.sqrtRefinements+512);assert.deepEqual(summary.safePrefix,[0,0]);
  assert.equal(lab.getState().result.window,null);assert.equal(parseStrictJson(ui.get('json').textContent,budget).result.work.workExact,false);assert.match(ui.get('status').textContent,/数値計算失敗/);lab.dispose();
});

test('artificial environment and pre-initial-allocation DTOs keep missing proof separate and permit ordinary recovery',async()=>{
  // Display-only fabricated failure shapes; no actual FP-mode or allocation fault.
  const real=await runtime(),source=entryLabPreset(),valid=call(real,source),failure=clone(valid);
  failure.status='unsupported_environment';failure.reason='environment';failure.snapshot=null;failure.initial=null;failure.initialSeparationProven=false;
  failure.certifiedLeaves=[];failure.safePrefix=null;failure.bestWitness=null;failure.window=null;failure.candidateSurfaceIds=[];
  failure.partition=[];failure.frontier=[];failure.current=null;failure.audits=[];failure.lastMesh=null;failure.lastMeshAuditIndex=null;failure.partitionLeaves=0;failure.maximumDepth=0;
  for(const key of Object.keys(failure.work))failure.work[key]=key==='workExact'?true:0;
  let next=failure;const ui=harness(),facade={diagnostics:{backend:'Artificial failure DTOs; no Native fault injection'},querySphereTriangleMeshEntry(){return clone(next);}};
  const lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:async()=>facade});
  assert.match(ui.get('status').textContent,/環境/);assert.equal(ui.get('error').hidden,true);assert.equal(lab.getState().result.snapshot,null);
  assert.equal(lab.getState().result.initial,null);assert.equal(parseStrictJson(ui.get('json').textContent,budget).result.status,'unsupported_environment');
  next=clone(failure);next.status='numerical_failure';next.reason='allocation_failure';next.snapshot=clone(valid.snapshot);next.current={parameter:[0,0],depth:0};
  next.partition=[{cell:{parameter:[0,1],depth:0},state:'unqueried',auditIndex:null,blockedReason:'none'}];next.frontier=[{parameter:[0,1],depth:0}];next.partitionLeaves=1;
  lab.run();assert.match(ui.get('status').textContent,/数値計算失敗/);assert.deepEqual(lab.getState().result.current,{parameter:[0,0],depth:0});
  assert.equal(lab.getState().result.audits.length,0);assert.equal(lab.getState().result.initial,null);assert.equal(lab.getState().result.work.meshQueries,0);
  const saved=parseStrictJson(ui.get('json').textContent,budget);assert.equal(saved.inspectedAudit,null);assert.equal(saved.result.work.workExact,true);
  next=valid;lab.run();assert.equal(lab.getState().result.status,'separated');assert.deepEqual(lab.getState().input,source);lab.dispose();
});

test('parse and host refusals clear stale success and recover without source repair or solver fallback',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:async()=>r});const count=r.calls.length;
  ui.get('source').value='{bad';ui.fire('source','input');lab.run();cleared(ui,lab);assert.match(ui.get('error').textContent,/入力JSON/);assert.equal(r.calls.length,count);
  ui.get('source').value=encode(entryLabPreset('65-source-rejection'));lab.run();cleared(ui,lab);assert.match(ui.get('error').textContent,/SDK交換/);assert.equal(parseEntryLabInput(ui.get('source').value).triangles.length,65);
  r.failure=new SimulationError(1,'Synthetic host refusal');ui.get('source').value=encode(entryLabPreset());lab.run();cleared(ui,lab);r.failure=null;lab.run();assert.equal(lab.getState().result.status,'separated');lab.dispose();
});

test('deferred first load does not query an edited generation until explicit execution',async()=>{
  const ui=harness(),r=counted(await runtime()),wait=deferred(),pending=initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:()=>wait.promise});await flush();
  ui.get('source').value=encode(entryLabPreset('analytic-entry-quarter'));ui.fire('source','input');wait.resolve(r);const lab=await pending;
  assert.equal(r.calls.length,0);cleared(ui,lab);assert.match(ui.get('status').textContent,/現在の入力/);lab.run();assert.equal(r.calls.length,1);assert.equal(lab.getState().result.status,'entry_window');lab.dispose();
});

test('sync loader throws coalesced retry and missing old80 API refuse old runtime then recover',async()=>{
  const ui=harness(),r=counted(await runtime());let loads=0,next=r;
  const lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:()=>{loads++;if(loads===1)throw new Error('Sync loader failure');return next;}});
  cleared(ui,lab);assert.match(ui.get('error').textContent,/SDK初期化/);await lab.retry();assert.equal(r.calls.length,1);
  const wait=deferred();next=wait.promise;const one=lab.retry(),two=lab.retry();assert.strictEqual(one,two);await flush();const count=r.calls.length;
  cleared(ui,lab);assert.equal(ui.get('runtime').textContent,'SDK未初期化');assert.equal(lab.run(),null);assert.equal(r.calls.length,count);assert.equal(loads,3);wait.resolve(r);await one;assert.equal(r.calls.length,count+1);
  const edit=deferred();next=edit.promise;const pending=lab.retry();await flush();const before=r.calls.length;ui.get('source').value=encode(entryLabPreset('analytic-entry-quarter'));ui.fire('source','input');edit.resolve(r);await pending;
  assert.equal(r.calls.length,before);cleared(ui,lab);lab.run();assert.equal(lab.getState().result.status,'entry_window');
  next={diagnostics:{backend:'Old80 SDK'},querySphereTriangleMeshTrajectory(){assert.fail('No old guard fallback');}};await lab.retry();cleared(ui,lab);assert.match(ui.get('error').textContent,/86-export/);
  next=r;await lab.retry();assert.equal(lab.getState().result.status,'entry_window');lab.dispose();
});

test('retry rejection clears every result panel and disposal blocks late success and all old handlers',async()=>{
  const ui=harness(),r=counted(await runtime());let next=r;const lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:()=>next});select(ui,'preset','actual-256-audits-128-leaves');
  const fail=deferred();next=fail.promise;const pending=lab.retry();await flush();cleared(ui,lab);assert.equal(ui.get('runtime').textContent,'SDK未初期化');
  fail.reject(new Error('Retry failure'));await pending;cleared(ui,lab);assert.equal(ui.get('controls').disabled,true);assert.equal(ui.get('retry').disabled,false);
  next=r;await lab.retry();assert.equal(lab.getState().result.status,'separated');
  const late=deferred();next=late.promise;const loading=lab.retry();await flush();lab.dispose();const count=r.calls.length;assert.equal(ui.listeners(),0);late.resolve(r);await loading;
  cleared(ui,lab);assert.equal(r.calls.length,count);assert.equal(ui.get('runtime').textContent,'SDK未初期化');assert.equal(ui.get('retry').disabled,true);
  assert.equal(lab.run(),null);assert.equal(await lab.retry(),null);assert.equal(ui.fire('query'),undefined);
});

test('disposed generation ignores late loader rejection and cannot resurrect runtime or exports',async()=>{
  const ui=harness(),r=counted(await runtime());let next=r;const lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:()=>next});
  const wait=deferred();next=wait.promise;const pending=lab.retry();await flush();lab.dispose();const status=ui.get('status').textContent;wait.reject(new Error('Late rejection'));await pending;
  cleared(ui,lab);assert.equal(ui.get('status').textContent,status);assert.equal(ui.listeners(),0);assert.equal(ui.get('retry').disabled,true);
});

test('save and invalid projection errors remove prior success and recover only by explicit query',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshEntryLab({doc:ui.doc,loadRuntime:async()=>r,saveFile(){throw new Error('Save refused');}}),count=r.calls.length;
  ui.fire('save');cleared(ui,lab);assert.match(ui.get('error').textContent,/保存/);lab.run();assert.equal(r.calls.length,count+1);
  select(ui,'projection','unknown');cleared(ui,lab);assert.match(ui.get('error').textContent,/表示/);assert.equal(r.calls.length,count+1);
  ui.get('projection').value='xy';lab.run();assert.equal(lab.getState().result.status,'separated');lab.dispose();
});
