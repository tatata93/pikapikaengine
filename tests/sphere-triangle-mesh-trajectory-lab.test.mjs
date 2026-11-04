import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime,SimulationError} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {trajectoryLabPresets,trajectoryLabPreset,parseTrajectoryLabInput,evaluateTrajectoryLab,
  serializeTrajectoryLab,trajectoryProjection,initializeSphereTriangleMeshTrajectoryLab} from '../tools/sphere-triangle-mesh-trajectory-lab.mjs';

let actual;
const runtime=async()=>actual??=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const clone=structuredClone,encode=stringifyStrictJson;
const names=['static-face','parallel-near-miss','reverse-parallel-near-miss','shared-edge-path','shared-vertex-static',
  'different-closest-two-surfaces','source-order-reversed','huge-common-offset-in-domain','endpoints-outside-interior-penetration',
  'anchor-on-face-normal-unresolved','exact-contact-not-separation','terminal-contact-with-prefix','evaluation-budget',
  'sqrt-reservation-before-mesh','primitive-candidate-budget','middle-degenerate-later-row-preserved','surface-budget-before-query',
  'duplicate-source-id','empty-source','signed-source-zero','inside-rounded-anchor-no-false-witness','actual-64-surfaces',
  'actual-128-leaf-partition','127-leaf-budget-preserves-prefix','65-source-rejection'];
const nativeCorpus=JSON.parse(await readFile(new URL('../reports/sphere-triangle-mesh-trajectory-checks/run-20261104-root/final-accepted/native-final-fixtures.json',import.meta.url),'utf8'));
const original=name=>{const f=nativeCorpus.fixtures.find(f=>f.name===name);assert.ok(f);return clone(f);};
const call=(r,s)=>r.querySphereTriangleMeshTrajectory({start:s.start,end:s.end,radius:s.radius},s.triangles,s.settings);
const inside=(b,n)=>assert.ok(b[0]<=n&&n<=b[1],`${b} excludes ${n}`);
const page=await readFile(new URL('../tools/sphere-triangle-mesh-trajectory-lab.html',import.meta.url),'utf8');
const pageIds=[...page.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);

test('twenty-five original presets have frozen labels exact accepted sources and independent arrays',()=>{
  assert.deepEqual(trajectoryLabPresets.map(p=>p.name),names);assert.ok(Object.isFrozen(trajectoryLabPresets));
  assert.ok(trajectoryLabPresets.every(p=>Object.isFrozen(p)&&typeof p.label==='string'&&p.label.length));
  assert.equal(new Set(pageIds).size,pageIds.length,'Actual HTML IDs are unique');
  for(const id of ids)assert.ok(pageIds.includes('traj-'+id),'Actual HTML control '+id);
  const options=page.match(/<select id="traj-preset">([\s\S]*?)<\/select>/)[1];
  const staticOptions=[...options.matchAll(/<option value="([^"]+)"/g)].map(m=>m[1]);
  // HTML may contain only the initial choice; initialization must expose all 25.
  assert.deepEqual(staticOptions,staticOptions.length===1?[names[0]]:names);
  for(const name of names){
    const a=trajectoryLabPreset(name),b=trajectoryLabPreset(name);assert.deepEqual(a,original(name).input,name);assert.deepEqual(a,b);
    assert.deepEqual(Object.keys(a),['start','end','radius','triangles','settings']);assert.equal(Object.keys(a.settings.mesh.primitive).length,6);
    a.start[0]=9;a.settings.mesh.primitive.maxCandidates=0;if(a.triangles.length)a.triangles[0].vertices[0][0]=9;
    assert.deepEqual(trajectoryLabPreset(name),b);
  }
  assert.deepEqual(trajectoryLabPreset(),trajectoryLabPreset('static-face'));assert.throws(()=>trajectoryLabPreset('unknown'));
});

test('strict source parser enforces shape budgets duplicates finite decimals and complete default settings',()=>{
  const source=trajectoryLabPreset(),defaults=clone(source.settings);source.settings={};
  assert.deepEqual(parseTrajectoryLabInput(encode(source)).settings,defaults);assert.deepEqual(source.settings,{});
  const base=trajectoryLabPreset(),bad=[];
  for(const key of ['start','end','radius','triangles','settings']){const q=clone(base);delete q[key];bad.push(q);}
  bad.push({...base,unknown:1},{...base,start:[0,0]},{...base,end:[0,'1',0]},{...base,radius:null},
    {...base,triangles:[{...base.triangles[0],unknown:1}]},{...base,triangles:[{id:1,vertices:[[0,0,0]]}]},
    {...base,triangles:Array(66).fill(base.triangles[0])},{...base,settings:null},{...base,settings:[]},
    {...base,settings:{unknown:1}},{...base,settings:{mesh:null}},{...base,settings:{mesh:{primitive:null}}},
    {...base,settings:{mesh:{primitive:{unknown:1}}}},{...base,settings:{maxLeaves:null}});
  for(const value of bad)assert.throws(()=>parseTrajectoryLabInput(encode(value)));
  const text=encode(base);
  for(const invalid of [text.slice(0,-1)+',"start":[0,0,0]}',text.replace('"radius":0.25','"radius":NaN'),
    text.replace('"radius":0.25','"radius":1e999'),text.replace('"radius":0.25','"radius":1e-999'),
    text+' trailing',' '.repeat(65537)+text,text.replace('"start"','"\\ud800"')])assert.throws(()=>parseTrajectoryLabInput(invalid));
  const sparse=clone(base);sparse.start=Array(3);assert.throws(()=>evaluateTrajectoryLab({},sparse));
  const finiteModel=clone(base);finiteModel.radius=0;finiteModel.settings.maxLeaves=0;
  assert.deepEqual(parseTrajectoryLabInput(encode(finiteModel)),finiteModel,'Finite model-invalid inputs are not silently repaired');
  assert.equal(parseTrajectoryLabInput(encode(trajectoryLabPreset('65-source-rejection'))).triangles.length,65);
});

test('all presets use the real C++ owned trajectory method exactly once and retain full input diagnostics',async()=>{
  const real=await runtime(),counts={};
  for(const name of names){
    const source=trajectoryLabPreset(name),before=clone(source);
    if(name==='65-source-rejection'){assert.throws(()=>evaluateTrajectoryLab(real,source),/64/);assert.deepEqual(source,before);continue;}
    const p=evaluateTrajectoryLab(real,source),expected=original(name).result;
    assert.equal(p.schema,1);assert.equal(p.kind,'sphere-triangle-mesh-trajectory-lab');assert.equal(p.diagnostics.backend,'C++ WebAssembly');
    assert.deepEqual(p.input,source);assert.deepEqual(source,before);assert.equal(p.result.status,expected.status,name);assert.equal(p.result.reason,expected.reason,name);
    assert.deepEqual(p.result,call(real,source));counts[p.result.status]=(counts[p.result.status]??0)+1;
    assert.equal(p.result.witness!==null,p.result.status==='penetration_witness');
  }
  assert.deepEqual(counts,{separated:11,penetration_witness:1,not_certified:10,invalid_input:2});
});

test('independent static gap interior witness and false-anchor examples keep their distinct mathematical claims',async()=>{
  const real=await runtime(),safe=evaluateTrajectoryLab(real,trajectoryLabPreset()),r=safe.result;
  assert.deepEqual(r.safePrefix,[0,1]);assert.ok(r.certifiedLeaves[0].lowerGapCertificate[0]>0);inside(r.lastMesh.rows[0].query.geometry.gap,.75);
  const crossing=evaluateTrajectoryLab(real,trajectoryLabPreset('endpoints-outside-interior-penetration'));
  assert.ok(Math.abs(crossing.input.start[1])>crossing.input.radius&&Math.abs(crossing.input.end[1])>crossing.input.radius);
  assert.ok(crossing.result.witness.parameter>0&&crossing.result.witness.parameter<1);assert.ok(crossing.result.witness.upperGapCertificate[1]<0);
  const lost=evaluateTrajectoryLab(real,trajectoryLabPreset('inside-rounded-anchor-no-false-witness')),a=lost.result.audits[0];
  assert.equal(lost.result.status,'not_certified');assert.equal(lost.result.witness,null);assert.ok(a.distance[1]<lost.input.radius);assert.ok(a.errorRoot[1]>=2**-14);assert.ok(a.penetrationCertificate[1]>0);
});

test('saved capacity includes all255 audits all128 leaves final audit254 and failed127-prefix remainder',async()=>{
  const full=evaluateTrajectoryLab(await runtime(),trajectoryLabPreset('actual-128-leaf-partition')),before=clone(full);
  const saved=parseStrictJson(serializeTrajectoryLab(full,'yz',254,0),{maxBytes:8388608,maxDepth:32,maxNodes:1000000});
  assert.equal(saved.inspectedAudit,254);assert.equal(saved.inspectedOrdinal,0);assert.equal(saved.inspectedSurfaceId,37);assert.equal(saved.projection,'yz');
  assert.equal(saved.result.audits.length,255);assert.equal(saved.result.certifiedLeaves.length,128);assert.equal(saved.result.certifiedLeaves[127].auditIndex,254);
  assert.deepEqual(saved.result.certifiedLeaves[127].cell.parameter,[127/128,1]);assert.deepEqual(saved.result,full.result);assert.deepEqual(full,before);
  const limited=evaluateTrajectoryLab(await runtime(),trajectoryLabPreset('127-leaf-budget-preserves-prefix'));
  assert.equal(limited.result.status,'not_certified');assert.equal(limited.result.partitionLeaves,127);assert.equal(limited.result.certifiedLeaves.length,126);
  assert.equal(limited.result.audits.length,253);assert.ok(limited.result.safePrefix[1]>0&&limited.result.safePrefix[1]<1);
  assert.deepEqual(limited.result.current.parameter,[limited.result.safePrefix[1],1]);assert.equal(limited.result.frontier.length,0);
  assert.throws(()=>serializeTrajectoryLab(full,'xy',255,0));assert.throws(()=>serializeTrajectoryLab(full,'xy',254,1));assert.throws(()=>serializeTrajectoryLab(full,'bad'));
});

test('all64 original sources final seven candidates and unused negative-zero KKT survive strict save',async()=>{
  const p=evaluateTrajectoryLab(await runtime(),trajectoryLabPreset('actual-64-surfaces'));
  const s=parseStrictJson(serializeTrajectoryLab(p,'xz',p.result.lastMeshAuditIndex,63),{maxBytes:8388608,maxDepth:32,maxNodes:1000000});
  assert.equal(s.input.triangles.length,64);assert.equal(s.result.originalInput.triangles.length,64);assert.equal(s.result.lastMesh.rows.length,64);
  assert.equal(s.inspectedSurfaceId,s.input.triangles[63].id);assert.equal(s.result.lastMesh.rows[63].query.candidates.length,7);assert.equal(s.result.lastMesh.rows[63].query.candidates[6].feature,'vertex_c');
  assert.equal(s.result.lastMesh.nearest.possibleSurfaceIds.length,64);assert.deepEqual(s.result,p.result);
  assert.deepEqual(s.input,p.input);assert.ok(Object.is(s.result.lastMesh.rows[63].query.candidates[0].kkt[0][0],-0));
  const negative=evaluateTrajectoryLab(await runtime(),trajectoryLabPreset('signed-source-zero')),negativeSaved=parseStrictJson(serializeTrajectoryLab(negative));
  assert.ok(Object.is(negativeSaved.input.start[0],-0));assert.ok(Object.is(negativeSaved.input.triangles[0].vertices[0][0],-0));
  assert.ok(Object.is(negativeSaved.result.originalInput.triangles[0].vertices[0][0],-0));assert.deepEqual(negativeSaved.result,negative.result);
  const empty=evaluateTrajectoryLab(await runtime(),trajectoryLabPreset('empty-source')),saved=parseStrictJson(serializeTrajectoryLab(empty));
  assert.equal(saved.inspectedAudit,null);assert.equal(saved.inspectedOrdinal,null);assert.equal(saved.inspectedSurfaceId,null);assert.equal(saved.result.snapshot,null);assert.ok(saved.result.originalInput);
  assert.equal(parseStrictJson(serializeTrajectoryLab(empty,'xy',null,null)).inspectedAudit,null);
  assert.throws(()=>serializeTrajectoryLab(empty,'xy',1,0));assert.throws(()=>serializeTrajectoryLab(empty,'xy',0,1));assert.throws(()=>serializeTrajectoryLab(null));
});

test('evaluate owns input result and diagnostics and forwards one query without single-mesh fallback',async()=>{
  const real=await runtime(),source=trajectoryLabPreset(),answer=call(real,source),saved=clone(answer),diagnostics={backend:'Captured actual C++ DTO',nested:{owned:true}},calls=[];
  const facade={diagnostics,querySphereTriangleMeshTrajectory(path,triangles,settings){calls.push(clone({path,triangles,settings}));return answer;},querySphereTriangleMesh(){assert.fail('No mesh fallback');}};
  const p=evaluateTrajectoryLab(facade,source),before=clone(p);assert.equal(calls.length,1);
  assert.deepEqual(calls[0],{path:{start:source.start,end:source.end,radius:source.radius},triangles:source.triangles,settings:source.settings});
  source.start[0]=999;source.triangles[0].id=999;answer.audits[0].anchor[0]=999;diagnostics.nested.owned=false;assert.deepEqual(p,before);assert.deepEqual(p.result,saved);
  const failure=new SimulationError(1,'Captured host refusal');assert.throws(()=>evaluateTrajectoryLab({querySphereTriangleMeshTrajectory(){throw failure;}},trajectoryLabPreset()),e=>e===failure);
  assert.throws(()=>evaluateTrajectoryLab({querySphereTriangleMesh(){assert.fail('fallback');}},trajectoryLabPreset()));
});

test('strict export accounts for its final newline at the complete eight-MiB byte boundary',async()=>{
  const packet=evaluateTrajectoryLab(await runtime(),trajectoryLabPreset()),limit=8388608;
  packet.diagnostics.padding='';const overhead=Buffer.byteLength(serializeTrajectoryLab(packet),'utf8');
  packet.diagnostics.padding='x'.repeat(limit-overhead);
  const text=serializeTrajectoryLab(packet);assert.equal(Buffer.byteLength(text,'utf8'),limit);assert.ok(text.endsWith('\n'));
  packet.diagnostics.padding+='x';assert.throws(()=>serializeTrajectoryLab(packet),/byte|budget|size/i);
});

test('projection uses only selected audit boxes and never relabels the last mesh as an earlier query',async()=>{
  const p=evaluateTrajectoryLab(await runtime(),trajectoryLabPreset('actual-128-leaf-partition')),before=clone(p),last=p.result.lastMeshAuditIndex;
  assert.equal(last,254);
  for(const projection of ['xy','xz','yz']){
    const earlier=trajectoryProjection(p.input,p.result,projection,0,0),actualLast=trajectoryProjection(p.input,p.result,projection,last,0);
    assert.equal(earlier.available,true);assert.equal(earlier.inspectedAudit,0);assert.equal(earlier.lastMeshAuditIndex,last);
    assert.equal(earlier.geometryBelongsToSelectedAudit,false);assert.equal(earlier.closest,null);assert.ok(earlier.pathBox);assert.ok(earlier.pointBox);assert.ok(earlier.anchor);
    assert.equal(actualLast.geometryBelongsToSelectedAudit,true);assert.ok(actualLast.closest);assert.equal(actualLast.triangles.length,1);
    earlier.triangles[0].vertices[0][0]=999;assert.deepEqual(p,before);
  }
  const unqueried=evaluateTrajectoryLab(await runtime(),trajectoryLabPreset('sqrt-reservation-before-mesh'));
  const view=trajectoryProjection(unqueried.input,unqueried.result,'xy',0,0);assert.equal(view.closest,null);assert.equal(view.geometryBelongsToSelectedAudit,false);
  const huge=trajectoryLabPreset();huge.start=[1e308,0,0];huge.end=[-1e308,0,0];huge.radius=1e308;
  const invalid=evaluateTrajectoryLab(await runtime(),huge);assert.equal(invalid.result.status,'invalid_input');
  assert.equal(trajectoryProjection(invalid.input,invalid.result).available,false);assert.equal(invalid.result.status,'invalid_input');
  assert.throws(()=>trajectoryProjection(p.input,p.result,'bad'));assert.throws(()=>trajectoryProjection(p.input,p.result,'xy',255,0));
});

const ids=['status','error','retry','controls','preset','source','projection','inspect','audit','query','reset','save',
  'runtime','note','view','summary','rows','geometry','candidates','json','leaves','partition','timeline'];
function harness(){
  const elements=new Map();
  function get(name){
    const id=name.startsWith('traj-')?name:'traj-'+name;assert.ok(ids.includes(id.slice(5)),'Contract DOM ID '+id);
    if(!elements.has(id)){
      const listeners=new Map(),attributes=new Map();
      elements.set(id,{id,value:'',textContent:'',innerHTML:'',disabled:false,hidden:false,listeners,
        addEventListener(event,fn){if(!listeners.has(event))listeners.set(event,new Set());listeners.get(event).add(fn);},
        removeEventListener(event,fn){listeners.get(event)?.delete(fn);},
        setAttribute(k,v){attributes.set(k,String(v));},getAttribute(k){return attributes.get(k)??null;}});
    }
    return elements.get(id);
  }
  return {get,doc:{getElementById:get},fire(name,event='click'){const e=get(name);let out;for(const fn of [...(e.listeners.get(event)??[])])out=fn({target:e,currentTarget:e});return out;},
    listeners(){let n=0;for(const e of elements.values())for(const a of e.listeners.values())n+=a.size;return n;}};
}
function counted(real){
  let failure=null;const calls=[];
  return {calls,get diagnostics(){return real.diagnostics;},set failure(error){failure=error;},
    querySphereTriangleMeshTrajectory(path,triangles,settings){calls.push(clone({path,triangles,settings}));if(failure)throw failure;return real.querySphereTriangleMeshTrajectory(path,triangles,settings);},
    querySphereTriangleMesh(){assert.fail('No mesh fallback');}};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const flush=async()=>{await Promise.resolve();await Promise.resolve();};
function cleared(ui,lab){
  assert.equal(lab.getState(),null);assert.equal(ui.get('save').disabled,true);
  for(const name of ['inspect','audit']){assert.equal(ui.get(name).disabled,true);assert.equal(ui.get(name).innerHTML,'');}
  for(const name of ['rows','leaves','timeline','view'])assert.equal(ui.get(name).innerHTML,'');
  for(const name of ['summary','partition','geometry','candidates'])assert.equal(ui.get(name).textContent,'—');
  assert.equal(ui.get('json').textContent,'');
}

test('actual UI discloses every preset classification and full capacity tables without hidden rows',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:async()=>r});
  assert.equal(r.calls.length,1);assert.equal((ui.get('preset').innerHTML.match(/<option /g)??[]).length,25);
  for(const name of names){
    ui.get('preset').value=name;ui.fire('preset','change');
    if(name==='65-source-rejection'){cleared(ui,lab);assert.equal(ui.get('error').hidden,false);assert.match(ui.get('error').textContent,/SDK交換/);continue;}
    const p=lab.getState();assert.deepEqual(p.input,trajectoryLabPreset(name));assert.equal(p.result.status,original(name).result.status,name);
    assert.deepEqual(parseStrictJson(ui.get('json').textContent,{maxBytes:8388608,maxDepth:32,maxNodes:1000000}).result,p.result);
    assert.equal((ui.get('rows').innerHTML.match(/<tr>/g)??[]).length,p.input.triangles.length);
    assert.equal((ui.get('rows').innerHTML.match(/<td>/g)??[]).length,p.input.triangles.length*5);
    assert.equal((ui.get('leaves').innerHTML.match(/<tr>/g)??[]).length,p.result.certifiedLeaves.length);
    assert.equal((ui.get('audit').innerHTML.match(/<option /g)??[]).length,p.result.audits.length);
    assert.equal(ui.get('error').hidden,true,'Model result is distinct from a thrown host/parse refusal');
    if(p.result.status==='separated')assert.match(ui.get('status').textContent,/strict非接触/);
    else if(p.result.status==='penetration_witness')assert.match(ui.get('status').textContent,/witness.*TOI/);
    else if(p.result.status==='not_certified')assert.match(ui.get('status').textContent,/未認証/);
    else assert.match(ui.get('status').textContent,/モデル入力を拒否/);
    if(name==='actual-128-leaf-partition'){
      ui.get('audit').value='254';ui.fire('audit','change');const g=parseStrictJson(ui.get('geometry').textContent);
      assert.equal(g.selectedAudit,254);assert.deepEqual(g.audit,p.result.audits[254]);assert.equal(g.lastMeshAuditIndex,254);
      assert.equal(g.lastMeshBelongsToSelectedAudit,true);assert.match(ui.get('leaves').innerHTML,/<td>127<\/td>/);
    }
    if(name==='actual-64-surfaces'){
      ui.get('inspect').value='63';ui.fire('inspect','change');const g=parseStrictJson(ui.get('geometry').textContent);
      assert.equal(g.surfaceId,p.input.triangles[63].id);assert.equal(g.rowQuery.candidatesExamined,7);assert.match(ui.get('candidates').textContent,/vertex_c/);
    }
  }
  lab.dispose();
});

test('editing input immediately clears leaves witness lastMesh JSON export and both drawings until explicit query',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:async()=>r});
  ui.get('preset').value='endpoints-outside-interior-penetration';ui.fire('preset','change');assert.ok(lab.getState().result.witness);
  const count=r.calls.length,source=trajectoryLabPreset();source.end[0]=1.125;
  ui.get('source').value=encode(source);ui.fire('source','input');cleared(ui,lab);assert.equal(r.calls.length,count);
  ui.fire('query');assert.deepEqual(lab.getState().input,source);assert.equal(r.calls.length,count+1);
  const saved=lab.getState(),copy=lab.getState();copy.result.audits[0].anchor[0]=999;assert.deepEqual(lab.getState(),saved);
  ui.fire('reset');assert.deepEqual(lab.getState().input,trajectoryLabPreset('endpoints-outside-interior-penetration'));lab.dispose();
});

test('audit source and projection browsing never queries physics and saved strict bytes equal displayed full JSON',async()=>{
  const ui=harness(),r=counted(await runtime()),saves=[],lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:async()=>r,saveFile:value=>saves.push(value)});
  ui.get('preset').value='actual-128-leaf-partition';ui.fire('preset','change');const before=lab.getState(),count=r.calls.length;
  ui.get('audit').value='0';ui.fire('audit','change');assert.equal(parseStrictJson(ui.get('geometry').textContent).lastMeshBelongsToSelectedAudit,false);
  assert.match(ui.get('note').textContent,/属さないlastMesh/);
  ui.get('audit').value='254';ui.fire('audit','change');ui.get('projection').value='yz';ui.fire('projection','change');ui.fire('save');
  assert.equal(r.calls.length,count);assert.deepEqual(lab.getState(),before);assert.equal(saves.length,1);assert.equal(saves[0].mime,'application/json');
  assert.equal(saves[0].text,ui.get('json').textContent);const p=parseStrictJson(saves[0].text,{maxBytes:8388608,maxDepth:32,maxNodes:1000000});
  assert.equal(p.projection,'yz');assert.equal(p.inspectedAudit,254);assert.deepEqual(p.result,before.result);
  ui.get('preset').value='signed-source-zero';ui.fire('preset','change');const negativeCount=r.calls.length;ui.fire('save');
  const negative=parseStrictJson(saves[1].text);assert.ok(Object.is(negative.input.start[0],-0));assert.ok(Object.is(negative.result.originalInput.start[0],-0));
  assert.equal(r.calls.length,negativeCount);assert.equal(saves[1].text,ui.get('json').textContent);lab.dispose();
});

test('failed mesh and later rows remain inspectable without attaching lastMesh to an unqueried audit',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:async()=>r});
  ui.get('preset').value='middle-degenerate-later-row-preserved';ui.fire('preset','change');assert.equal(lab.getState().result.status,'not_certified');
  ui.get('inspect').value='1';ui.fire('inspect','change');assert.equal(parseStrictJson(ui.get('geometry').textContent).rowQuery.status,'degenerate');
  ui.get('inspect').value='2';ui.fire('inspect','change');assert.equal(parseStrictJson(ui.get('geometry').textContent).rowQuery.status,'completed');
  ui.get('preset').value='sqrt-reservation-before-mesh';ui.fire('preset','change');const g=parseStrictJson(ui.get('geometry').textContent);
  assert.equal(g.audit.meshQueried,false);assert.equal(g.lastMesh,null);assert.equal(g.rowQuery,null);assert.match(ui.get('rows').innerHTML,/未照会/);
  assert.match(ui.get('candidates').textContent,/候補を生成していません/);assert.equal(lab.getState().result.safePrefix,null);lab.dispose();
});

test('synthetic workExact false display keeps known counts and upper reservation distinct without claiming fault injection',async()=>{
  const real=await runtime(),source=trajectoryLabPreset(),result=call(real,source),a=result.audits[0];
  result.status='numerical_failure';result.reason='nonfinite_intermediate';result.certifiedLeaves=[];result.safePrefix=null;result.current=clone(a.cell);a.outcome='not_certified';
  for(const key of ['displacementRoot','errorRoot','clearanceCertificate','penetrationCertificate'])a[key]=null;
  for(const w of [result.work,a.work]){w.enclosureSqrtRefinements=0;w.sqrtRefinements=w.primitiveSqrtRefinements;w.sqrtRefinementsUpper=w.sqrtRefinements+512;w.enclosureSqrtCalls=1;w.enclosureSqrtLimitedCalls=0;w.workExact=false;}
  const ui=harness(),facade={diagnostics:{backend:'Synthetic unreturned-sqrt wire DTO display; not a C++ fault injection'},querySphereTriangleMeshTrajectory(){return result;}};
  const lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:async()=>facade}),summary=parseStrictJson(ui.get('summary').textContent);
  assert.equal(summary.work.workExact,false);assert.equal(summary.work.sqrtRefinementsUpper,summary.work.sqrtRefinements+512);
  assert.equal(lab.getState().result.status,'numerical_failure');assert.equal(lab.getState().result.witness,null);assert.equal(summary.safePrefix,null);
  assert.equal(parseStrictJson(ui.get('json').textContent).result.work.workExact,false);assert.match(ui.get('status').textContent,/数値計算失敗/);lab.dispose();
});

test('parse and host refusals clear all stale results and recover without changing the source or falling back',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:async()=>r});
  const count=r.calls.length;ui.get('source').value='{bad';ui.fire('source','input');lab.run();cleared(ui,lab);assert.match(ui.get('error').textContent,/入力JSON/);assert.equal(r.calls.length,count);
  ui.get('source').value=encode(trajectoryLabPreset('65-source-rejection'));lab.run();cleared(ui,lab);assert.match(ui.get('error').textContent,/SDK交換/);
  assert.equal(parseTrajectoryLabInput(ui.get('source').value).triangles.length,65);
  r.failure=new SimulationError(1,'Injected host refusal');ui.get('source').value=encode(trajectoryLabPreset());lab.run();cleared(ui,lab);
  r.failure=null;lab.run();assert.equal(lab.getState().result.status,'separated');lab.dispose();
});

test('deferred initial load plus source edit cannot automatically query the newly edited input',async()=>{
  const ui=harness(),r=counted(await runtime()),wait=deferred(),pending=initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:()=>wait.promise});
  await flush();ui.get('source').value=encode(trajectoryLabPreset('endpoints-outside-interior-penetration'));ui.fire('source','input');wait.resolve(r);
  const lab=await pending;assert.equal(r.calls.length,0);cleared(ui,lab);assert.match(ui.get('status').textContent,/現在の入力/);
  lab.run();assert.equal(r.calls.length,1);assert.equal(lab.getState().result.status,'penetration_witness');lab.dispose();
});

test('sync loader throw old SDK and coalesced retry block the old runtime and allow recovery',async()=>{
  const ui=harness(),r=counted(await runtime());let loads=0,next=r;
  const lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:()=>{loads++;if(loads===1)throw new Error('Synchronous load failure');return next;}});
  cleared(ui,lab);assert.match(ui.get('error').textContent,/SDK初期化/);await lab.retry();assert.equal(r.calls.length,1);
  const wait=deferred();next=wait.promise;const one=lab.retry(),two=lab.retry();assert.strictEqual(one,two);await flush();
  const count=r.calls.length;cleared(ui,lab);assert.equal(ui.get('runtime').textContent,'SDK未初期化');assert.equal(lab.run(),null);assert.equal(r.calls.length,count);assert.equal(loads,3);
  wait.resolve(r);await Promise.all([one,two]);assert.equal(r.calls.length,count+1);
  const edited=deferred();next=edited.promise;const loadingEdit=lab.retry();await flush();
  const beforeEdit=r.calls.length;ui.get('source').value=encode(trajectoryLabPreset('endpoints-outside-interior-penetration'));ui.fire('source','input');
  edited.resolve(r);await loadingEdit;assert.equal(r.calls.length,beforeEdit);cleared(ui,lab);lab.run();assert.equal(lab.getState().result.status,'penetration_witness');
  next={diagnostics:{backend:'Old 74-export SDK'},querySphereTriangleMesh(){assert.fail('No fallback');}};
  await lab.retry();cleared(ui,lab);assert.match(ui.get('error').textContent,/80-export/);
  next=r;await lab.retry();assert.equal(lab.getState().result.status,'penetration_witness');lab.dispose();
});

test('retry rejection clears old runtime and completed tables while disposal blocks late success and every handler',async()=>{
  const ui=harness(),r=counted(await runtime());let next=r;
  const lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:()=>next});
  ui.get('preset').value='actual-128-leaf-partition';ui.fire('preset','change');assert.ok(ui.get('leaves').innerHTML);
  const fail=deferred();next=fail.promise;const retry=lab.retry();await flush();cleared(ui,lab);assert.equal(ui.get('runtime').textContent,'SDK未初期化');
  fail.reject(new Error('Deferred retry failed'));await retry;cleared(ui,lab);assert.equal(ui.get('controls').disabled,true);assert.equal(ui.get('retry').disabled,false);
  next=r;await lab.retry();assert.equal(lab.getState().result.status,'separated');
  const late=deferred();next=late.promise;const pending=lab.retry();await flush();lab.dispose();const count=r.calls.length;assert.equal(ui.listeners(),0);
  late.resolve(r);await pending;cleared(ui,lab);assert.equal(r.calls.length,count);assert.equal(ui.get('runtime').textContent,'SDK未初期化');
  assert.equal(ui.get('controls').disabled,true);assert.equal(ui.get('retry').disabled,true);assert.equal(lab.run(),null);assert.equal(await lab.retry(),null);assert.equal(ui.fire('query'),undefined);
});

test('disposed generation ignores late loader rejection and never resurrects metadata or saved results',async()=>{
  const ui=harness(),r=counted(await runtime());let next=r;
  const lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:()=>next}),wait=deferred();next=wait.promise;
  const retry=lab.retry();await flush();lab.dispose();const status=ui.get('status').textContent;wait.reject(new Error('Late rejection'));await retry;
  cleared(ui,lab);assert.equal(ui.get('status').textContent,status);assert.equal(ui.listeners(),0);assert.equal(ui.get('retry').disabled,true);
});

test('save and projection errors clear prior success and retain explicit-query recovery',async()=>{
  const ui=harness(),r=counted(await runtime()),lab=await initializeSphereTriangleMeshTrajectoryLab({doc:ui.doc,loadRuntime:async()=>r,saveFile(){throw new Error('Save refused');}});
  const count=r.calls.length;ui.fire('save');cleared(ui,lab);assert.match(ui.get('error').textContent,/保存/);
  lab.run();assert.equal(r.calls.length,count+1);ui.get('projection').value='unknown';ui.fire('projection','change');cleared(ui,lab);assert.match(ui.get('error').textContent,/表示/);
  assert.equal(r.calls.length,count+1);ui.get('projection').value='xy';lab.run();assert.equal(lab.getState().result.status,'separated');lab.dispose();
});
