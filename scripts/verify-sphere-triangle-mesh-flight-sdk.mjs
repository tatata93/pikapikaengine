// Actual owned flight methods, complete source/DTO/getter bits, separate Fraction audit.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';

const [heldFile,guardFile,supplementalFile,nativeFile,directory,...extra]=process.argv.slice(2);
if(!heldFile||!guardFile||!supplementalFile||!nativeFile||!directory||extra.length)
  throw Error('Usage: node verify-sphere-triangle-mesh-flight-sdk.mjs HELD79 GUARD100 SUPPLEMENTAL4 NATIVE-PACKETS fresh-output');
const dir=path.resolve(directory);await mkdir(path.dirname(dir),{recursive:true});await mkdir(dir);
const budget={maxBytes:67108864,maxDepth:64,maxNodes:4000000};
const signed=x=>stringifyStrictJson(x,budget);
const own=x=>parseStrictJson(signed(x),budget);
const sha=x=>createHash('sha256').update(x).digest('hex');
const info=x=>({bytes:x.length,sha256:sha(x)});
async function save(name,value){const text=typeof value==='string'?value:signed(value)+'\n';assert.ok(Buffer.byteLength(text)<=budget.maxBytes);await writeFile(path.join(dir,name),text,{flag:'wx'});}
const dependencies=['./verify-sphere-triangle-mesh-flight-sdk.mjs','./verify-sphere-triangle-mesh-flight-owned.py',
  './verify-sphere-triangle-mesh-flight-native-sdk.py','./check-sphere-triangle-mesh-held-load.py','./check-sphere-triangle-mesh-free-flight-guard.py',
  '../engine/simulation.mjs','../engine/sphere-triangle-mesh-flight.mjs','../engine/strict-json.mjs',
  '../assets/pikapika-simulation.wasm','../assets/pikapika-simulation.mjs','../assets/pikapika-simulation.build.json'];
async function dependencyHashes(){const result={};for(const name of dependencies)result[name]=info(await readFile(new URL(name,import.meta.url)));return result;}
const before=await dependencyHashes();await save('source-before.json',before);
const commands=[];
const bitView=new DataView(new ArrayBuffer(8));
function bits(x){assert.equal(typeof x,'number');assert.ok(Number.isFinite(x));bitView.setFloat64(0,x);return bitView.getBigUint64(0).toString(16).padStart(16,'0');}
const count=()=>({numeric:0,negativeZero:0});
function compare(a,b,label,c){
  assert.equal(typeof a,typeof b,label);
  if(typeof b==='number'){assert.equal(bits(a),bits(b),label);c.numeric++;if(Object.is(a,-0))c.negativeZero++;}
  else if(b!==null&&typeof b==='object'){
    assert.ok(a!==null,label);assert.equal(Array.isArray(a),Array.isArray(b),label);
    assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);
    for(const key of Object.keys(b))compare(a[key],b[key],label+'.'+key,c);
  }else assert.equal(a,b,label);
}
const meshStatus=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReason=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const singleStatus=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const singleReason=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const features=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'],dispositions=['retained','outside_simplex','kkt_violated'];
const relations=['separated','penetrating','touching','boundary_unresolved'];
const ccd=['none','invalid_input','initial_contact','query_unresolved','event_budget','segment_budget','query_budget','root_budget','geometric_guard','propagation_failure','solver_failure','sustained_contact_required','numerical_failure'];
const ordinal=(value,choices)=>{assert.equal(typeof value,'string');const n=choices.indexOf(value);assert.ok(n>=0,'known enum');return n;};
function meshProjection(q){
  return {...q,status:ordinal(q.status,meshStatus),reason:ordinal(q.reason,meshReason),rows:q.rows.map(row=>({...row,query:row.query===null?null:{...row.query,
    status:ordinal(row.query.status,singleStatus),reason:ordinal(row.query.reason,singleReason),
    geometry:row.query.geometry===null?null:{...row.query.geometry,relation:ordinal(row.query.geometry.relation,relations)},
    candidates:row.query.candidates.map(c=>({...c,feature:ordinal(c.feature,features),disposition:ordinal(c.disposition,dispositions)}))}}))};
}
function heldProjection(q){return {...q,audits:q.audits.map(a=>({...a,meshStatus:a.meshStatus===null?null:ordinal(a.meshStatus,meshStatus),meshReason:a.meshReason===null?null:ordinal(a.meshReason,meshReason)})),lastMesh:q.lastMesh===null?null:meshProjection(q.lastMesh)};}
function projection(q,mode){const {originalInput,...model}=q;assert.ok(originalInput&&typeof originalInput==='object');return mode===0?heldProjection(model):{...model,flightFailure:model.flightFailure===null?null:ordinal(model.flightFailure,ccd),inflated:model.inflated===null?null:heldProjection(model.inflated)};}
const primitiveKeys=['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared'];
function settingsValues(s){return [s.mesh.maxSurfaces,...primitiveKeys.map(k=>s.mesh.primitive[k]),...['timeTolerance','maxEvaluations','maxLeaves','maxDepth','enclosureSqrtRefinements','maxTotalSqrtRefinements'].map(k=>s[k])];}
function bodyValues(b){return [b.id,Number(b.isStatic),b.mass,b.radius,...b.inertiaDiagonal,...b.position,...b.orientation,...b.velocity,...b.angularMomentum,...b.force,...b.torque,b.material.restitution,b.material.friction];}
function echo(q,mode){
  if(mode===0){const b=q.sphere;return [b.id,...b.position,...b.velocity,b.mass,...b.force,...b.gravity,b.radius,q.horizon,...settingsValues(q.settings),0,0,0];}
  return [...bodyValues(q.body),...q.gravity,q.horizon,...settingsValues(q.settings.heldLoad),q.settings.maxAngularIncrement,0,0];
}
function hostReason(q,mode){
  if(q.triangles.length>64)return 'surface_count';
  if(q.triangles.some(t=>!Number.isSafeInteger(t.id)||t.id<=0))return 'surface_id';
  const v=echo(q,mode),offset=mode===0?16:32;
  if(!Number.isSafeInteger(v[0])||v[0]<=0)return 'body_id';
  if([0,1,2,3,8,9,10,11,12].some(i=>!Number.isInteger(v[offset+i])||v[offset+i]<0||v[offset+i]>0xffffffff))return 'integer_exchange';
  return null;
}
function getterPlan(result,mode,sourceCount){
  const h=mode===0?result:result.inflated;
  const present=x=>Number(x!==null);
  const counts=[1,sourceCount,present(result.snapshot),present(h),h?present(h.snapshot):0,present(result.worldBody),
    mode===1?present(result.tube):0,mode===1?present(result.endpoint):0,mode===1?present(result.candidate):0,
    h?present(h.acceleration):0,h?present(h.wholePathBounds):0,h?present(h.wholeVelocityBounds):0,
    h?h.audits.length:0,h?h.certifiedLeaves.length:0,h?h.partition.length:0,h?h.frontier.length:0,
    h?present(h.current):0,h?present(h.initial):0,h?present(h.bestWitness):0,h?present(h.window):0,h?h.candidateSurfaceIds.length:0];
  const lengths=[mode===0?32:48,14,mode===0?32:48,48,32,32,24,40,32,8,8,8,64,6,8,4,4,6,18,14,2];
  return counts.flatMap((n,kind)=>Array.from({length:n},(_,index)=>({kind,index,length:lengths[kind]})));
}
const mutate=value=>{if(value===null||typeof value!=='object')return;for(const k of Object.keys(value))if(typeof value[k]==='number')value[k]=9001;else mutate(value[k]);};
let world=null;
try{
  const sourceBytes=await Promise.all([heldFile,guardFile,supplementalFile].map(x=>readFile(x)));
  const datasets=sourceBytes.map(x=>parseStrictJson(new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(x),budget));
  for(const [i,size] of [79,100,4].entries())assert.equal(datasets[i].fixtures.length,size);
  const corpus=datasets.flatMap((set,i)=>set.fixtures.map(f=>({cohort:['held','guard','supplemental'][i],mode:i===0?0:1,fixture:f})));
  const nativeBytes=await readFile(nativeFile),native=parseStrictJson(nativeBytes.toString('utf8'),budget);
  assert.equal(native.kind,'sphere-triangle-mesh-flight-sdk-packets');assert.equal(native.fixtures.length,183);
  for(let i=0;i<3;i++)await writeFile(path.join(dir,['source-held.json','source-guard.json','source-supplemental.json'][i]),sourceBytes[i],{flag:'wx'});
  const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
  const runtime=await loadSimulationRuntime({wasmBytes:wasm}),m=runtime.native;
  for(const name of ['querySphereTriangleMeshHeldLoad','querySphereTriangleMeshFreeFlightGuard'])assert.equal(typeof runtime[name],'function','new public owned method required');
  const prefix='_pp_sim_sphere_triangle_mesh_flight';
  for(const suffix of ['_begin','_append','_query','_record','_last_mesh','_candidate'])assert.equal(typeof m[prefix+suffix],'function');
  const nativeFunctions=Object.fromEntries(Object.entries(Object.getOwnPropertyDescriptors(m)).filter(([,d])=>typeof d.value==='function').map(([k,d])=>[k,d.value]));
  const nativePrototype=Object.getPrototypeOf(m),runtimePrototype=Object.getPrototypeOf(runtime);
  runtime.check(m._pp_sim_reset());
  const counters={model:count(),originalInput:count(),rawGetters:count(),hostOutput:count(),ownership:count()};
  const memory={initialCapacityBytes:m.HEAPU8.byteLength,maximumCapacityBytes:m.HEAPU8.byteLength,finalCapacityBytes:null,bufferChanges:0,viewChecks:0,
    usedHeapBytes:null,stackHighWaterBytes:null,memoryGrowthExercised:false,scope:'Capacity/view observations only; no allocator-use or stack-highwater export is present.'};
  let buffer=m.HEAPU8.buffer;
  function observe(){assert.equal(m.HEAPF64.buffer,m.HEAPU8.buffer);assert.equal(m.HEAPU32.buffer,m.HEAPU8.buffer);memory.viewChecks++;memory.maximumCapacityBytes=Math.max(memory.maximumCapacityBytes,m.HEAPU8.byteLength);if(buffer!==m.HEAPU8.buffer){memory.bufferChanges++;buffer=m.HEAPU8.buffer;}}
  const output=()=>Array.from(runtime.output());
  function getter(suffix,...args){runtime.check(m[prefix+suffix](...args));observe();const v=output();v.forEach(bits);return v;}
  const invoke=(q,mode)=>mode===0?runtime.querySphereTriangleMeshHeldLoad(q.sphere,q.triangles,q.horizon,q.settings):runtime.querySphereTriangleMeshFreeFlightGuard(q.body,q.gravity,q.triangles,q.horizon,q.settings);
  world=runtime.createWorld({gravity:[0,-10,0]});world.addBody({id:710,position:[0,10,0],force:[2,0,0],torque:[0,0,1]});world.step(1/120);
  const worldBefore=own({info:world.info(),body:world.getBody(710)});
  const oldSource=parseStrictJson(await readFile(new URL('../reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',import.meta.url),'utf8'),budget);
  const oldQ=oldSource.fixtures.find(f=>f.result.status==='separated'&&f.input.triangles.length<=64).input;
  const oldEntry=runtime.querySphereTriangleMeshEntry({start:oldQ.start,end:oldQ.end,radius:oldQ.radius},oldQ.triangles,oldQ.settings),oldEntryBefore=signed(oldEntry);
  runtime.check(m._pp_sim_sphere_triangle_mesh_entry_record(0,0));const oldEcho=output();
  const rows=[],rawRows=[],retained=[],hosts=[],cohorts={held:{models:0,hostRejected:0},guard:{models:0,hostRejected:0},supplemental:{models:0,hostRejected:0}};
  for(let index=0;index<corpus.length;index++){
    const {cohort,mode,fixture}=corpus[index],q=own(fixture.input),label=cohort+'/'+fixture.name,expectedRaw=native.fixtures[index];
    assert.equal(expectedRaw.cohort,cohort);assert.equal(expectedRaw.name,fixture.name);assert.equal(expectedRaw.mode,mode);
    compare(echo(q,mode),expectedRaw.input,label+'.completeInputEcho',counters.originalInput);
    const beforeCaller=signed(q),beforeOutput=output(),reason=hostReason(q,mode);let result,error;
    try{result=invoke(q,mode);}catch(e){error=e;}observe();assert.equal(signed(q),beforeCaller,label+' caller unchanged');
    if(reason!==null){
      assert.ok(error instanceof Error,label+' explicit host refusal');assert.equal(result,undefined);
      compare(output(),beforeOutput,label+' host output/count retained',counters.hostOutput);cohorts[cohort].hostRejected++;
      rows.push({cohort,name:fixture.name,mode,input:own(fixture.input),result:null,hostError:error.message});hosts.push({cohort,name:fixture.name,reason,message:error.message});continue;
    }
    if(error)throw error;
    compare(projection(result,mode),fixture.result,label+'.fullModel',counters.model);
    compare(result.originalInput,{...own(fixture.input),echo:echo(fixture.input,mode)},label+'.originalInput',counters.originalInput);
    rows.push({cohort,name:fixture.name,mode,input:own(fixture.input),result:own(result),hostError:null});cohorts[cohort].models++;
    const saved=signed(result);mutate(q);assert.equal(signed(result),saved,label+' input ownership');retained.push({result,saved});
    const raw={cohort,name:fixture.name,mode,summary:null,summaryUnavailable:'Consumed by owned decoder; no intercept, export replacement, or extra query.',packets:[],lastMeshSummary:null,lastMeshSummaryBits:null,lastMeshRows:[]};
    const plan=getterPlan(result,mode,fixture.input.triangles.length);
    assert.equal(expectedRaw.packets.length,plan.length,label+' all getter records, no omitted tail');
    for(let p=0;p<plan.length;p++){const spec=plan[p],expected=expectedRaw.packets[p];assert.equal(expected.kind,spec.kind);assert.equal(expected.index,spec.index);
      const values=getter('_record',mode,spec.kind,spec.index);assert.equal(values.length,spec.length);compare(values,expected.values,label+'.kind'+spec.kind+'.'+spec.index,counters.rawGetters);raw.packets.push({kind:spec.kind,index:spec.index,values,bits:values.map(bits)});}
    const lastMesh=(mode===0?result:result.inflated)?.lastMesh??null;
    assert.equal(expectedRaw.lastMeshSummary===null,lastMesh===null);
    assert.equal(expectedRaw.lastMeshRows.length,lastMesh?.rows.length??0);
    if(expectedRaw.lastMeshSummary!==null){raw.lastMeshSummary=getter('_last_mesh',mode,0,0);raw.lastMeshSummaryBits=raw.lastMeshSummary.map(bits);compare(raw.lastMeshSummary,expectedRaw.lastMeshSummary,label+'.lastMeshSummary',counters.rawGetters);}
    for(const expected of expectedRaw.lastMeshRows){
      const query=lastMesh.rows[expected.rowOrdinal].query;assert.equal(expected.packet===null,query===null);assert.equal(expected.candidates.length,query?.candidates.length??0);
      const row={rowOrdinal:expected.rowOrdinal,packet:null,bits:null,candidates:[],candidateBits:[]};
      if(expected.packet!==null){row.packet=getter('_last_mesh',mode,1,expected.rowOrdinal);row.bits=row.packet.map(bits);compare(row.packet,expected.packet,label+'.row'+expected.rowOrdinal,counters.rawGetters);}
      for(let c=0;c<expected.candidates.length;c++){const value=getter('_candidate',mode,expected.rowOrdinal,c);compare(value,expected.candidates[c],label+'.candidate'+expected.rowOrdinal+'.'+c,counters.rawGetters);row.candidates.push(value);row.candidateBits.push(value.map(bits));}
      raw.lastMeshRows.push(row);
    }
    rawRows.push(raw);
  }
  assert.equal(rows.length,183);assert.equal(retained.length+hosts.length,183);
  for(const r of retained)assert.equal(signed(r.result),r.saved,'every prior DTO retained after all later modes and getters');
  const ownership={corpusDtosRetained:retained.length,extraCalls:0};
  // Independently mutate each owned branch; no mutation enters the fixed corpus.
  for(const mode of [0,1]){
    const chosen=corpus.find(c=>c.mode===mode&&hostReason(c.fixture.input,mode)===null&&c.fixture.result.snapshot!==null&&(mode===0?c.fixture.result.lastMesh!==null:c.fixture.result.candidate!==null));
    assert.ok(chosen);const q=own(chosen.fixture.input),a=invoke(q,mode),b=invoke(own(chosen.fixture.input),mode);ownership.extraCalls+=2;
    compare(projection(b,mode),chosen.fixture.result,'extra owned replay',counters.ownership);
    const savedB=signed(b),snapshot=signed(a.snapshot),original=signed(a.originalInput);
    const held=mode===0?a:a.inflated,heldSnapshot=held?.snapshot===null?null:signed(held?.snapshot),lastMesh=held?.lastMesh===null?null:signed(held?.lastMesh);
    mutate(q);assert.equal(signed(a.snapshot),snapshot);assert.equal(signed(a.originalInput),original);
    mutate(a.originalInput);assert.equal(signed(a.snapshot),snapshot);if(held?.lastMesh)assert.equal(signed(held.lastMesh),lastMesh);
    const changedOriginal=signed(a.originalInput);mutate(a.snapshot);assert.equal(signed(a.originalInput),changedOriginal);
    if(mode===1){if(held?.snapshot)assert.equal(signed(held.snapshot),heldSnapshot);const body=signed(a.worldBody),candidate=signed(a.candidate);mutate(a.worldBody);assert.equal(signed(a.candidate),candidate);mutate(a.candidate);assert.notEqual(signed(a.worldBody),body);}
    mutate(a);assert.equal(signed(b),savedB);runtime.inputF64(Array(64).fill(9001));const copiedOutput=output();copiedOutput.fill(9002);assert.equal(signed(b),savedB);
  }
  for(const r of retained)assert.equal(signed(r.result),r.saved,'fixed corpus DTOs survive separate ownership mutations');
  compare({info:world.info(),body:world.getBody(710)},worldBefore,'World clock/body/load unchanged',counters.ownership);
  assert.equal(signed(oldEntry),oldEntryBefore,'old entry JS DTO unchanged');runtime.check(m._pp_sim_sphere_triangle_mesh_entry_record(0,0));compare(output(),oldEcho,'old entry Native snapshot unchanged',counters.ownership);
  for(const [name,fn] of Object.entries(nativeFunctions))assert.equal(Object.getOwnPropertyDescriptor(m,name).value,fn,'original export unchanged '+name);
  assert.equal(Object.getPrototypeOf(m),nativePrototype);assert.equal(Object.getPrototypeOf(runtime),runtimePrototype);
  memory.finalCapacityBytes=m.HEAPU8.byteLength;memory.memoryGrowthExercised=memory.bufferChanges>0;
  await save('wasm-owned-dtos.json',{schema:1,kind:'sphere-triangle-mesh-flight-owned-sdk-dtos',fixtures:rows});
  await save('actual-getter-packets.json',{schema:1,kind:'sphere-triangle-mesh-flight-owned-getters',fixtures:rawRows});
  await save('host-rejections.json',{schema:1,fixtures:hosts});
  const python=process.env.PIKAPIKA_PYTHON??(process.platform==='win32'?'python':'python3');
  const argv=['-X','utf8',fileURLToPath(new URL('./verify-sphere-triangle-mesh-flight-owned.py',import.meta.url)),heldFile,guardFile,supplementalFile,path.join(dir,'wasm-owned-dtos.json'),path.join(dir,'independent')];
  const processResult=spawnSync(python,argv,{windowsHide:true,encoding:'utf8',timeout:240000,maxBuffer:16777216});
  await save('reference.stdout.txt',processResult.stdout??'');await save('reference.stderr.txt',processResult.stderr??'');
  commands.push({executable:python,argv,exitCode:processResult.status,signal:processResult.signal,error:processResult.error?String(processResult.error):null});await save('commands.json',commands);
  assert.ifError(processResult.error);assert.equal(processResult.status,0,'independent verifier; raw child output retained');
  const reference=parseStrictJson(processResult.stdout,budget);
  const after=await dependencyHashes();await save('source-after.json',after);assert.deepEqual(after,before,'all frozen dependencies unchanged throughout run');
  world.dispose();world=null;
  const files={};for(const name of ['wasm-owned-dtos.json','actual-getter-packets.json','host-rejections.json','commands.json','reference.stdout.txt','reference.stderr.txt','source-before.json','source-after.json'])files[name]=info(await readFile(path.join(dir,name)));
  const maximums={};for(const [kind,key] of [[1,'sources'],[12,'audits'],[13,'leaves'],[14,'partition'],[15,'frontier'],[20,'candidateIds']])maximums[key]=Math.max(...rawRows.map(r=>r.packets.filter(p=>p.kind===kind).length));
  maximums.lastMeshRows=Math.max(...rawRows.map(r=>r.lastMeshRows.length));maximums.lastMeshCandidates=Math.max(...rawRows.map(r=>r.lastMeshRows.reduce((n,row)=>n+row.candidates.length,0)));
  const report={schema:1,status:'PASS',fixtures:rows.length,actualModels:retained.length,hostRejected:hosts.length,cohorts,counters,ownership,maximums,
    reference,memory,files,sourcesBefore:before,sourcesAfter:after,sourceStable:true,nativePackets:info(nativeBytes),wasm:info(wasm),
    originalExportsAndPrototypesUnchanged:true,oldEntryAndWorldUnchanged:true,
    scope:'Actual public owned JS flight methods on frozen WASM. All accepted DTO fields/explicit originalInput and every accessible current getter packet compared to Native. Query summary24 is consumed before return and is explicitly unavailable here, not filled or re-queried; prior raw proof and separate synthetic decoder tests cover it. Hosts remain null. Capacity is not used heap/stack. No public UI, response, or allocation/environment fault injection.'};
  await save('report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}catch(error){
  await save('failure.json',{status:'FAIL',name:error.name,message:error.message,stack:error.stack,commands}).catch(()=>{});
  const after=await dependencyHashes().catch(e=>({captureError:String(e)}));await save('failure-source-after.json',after).catch(()=>{});
  throw error;
}finally{world?.dispose();}
