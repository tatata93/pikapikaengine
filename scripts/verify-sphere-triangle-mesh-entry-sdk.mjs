// Original entry owned-decoder integration proof. Actual shared WASM is called
// through the public entry method; raw-wire and trajectory proofs stay separate.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';

const [fixtureFile,directory,...extra]=process.argv.slice(2);
if(!fixtureFile||!directory||extra.length)throw Error('Usage: node scripts/verify-sphere-triangle-mesh-entry-sdk.mjs pure-fixtures.json fresh-output-directory');
const budget={maxBytes:67108864,maxDepth:48,maxNodes:2000000};
const signed=value=>stringifyStrictJson(value,budget);
const own=value=>parseStrictJson(signed(value),budget);
const sha=value=>createHash('sha256').update(value).digest('hex');
const dir=path.resolve(directory);
await mkdir(path.dirname(dir),{recursive:true});await mkdir(dir);
const save=async(name,value)=>{
 const text=typeof value==='string'?value:signed(value)+'\n';
 assert.ok(Buffer.byteLength(text)<=budget.maxBytes,'saved stream byte budget includes final LF');
 return writeFile(path.join(dir,name),text,{flag:'wx'});
};
const sourceBytes=await readFile(fixtureFile);
assert.ok(sourceBytes.length<=budget.maxBytes,'source fixture byte budget');
const source=parseStrictJson(new TextDecoder('utf-8',{fatal:true}).decode(sourceBytes),budget);
await writeFile(path.join(dir,'source-fixtures.json'),sourceBytes,{flag:'wx'});
assert.deepEqual(Object.keys(source).sort(),['fixtures','kind','schema']);
assert.equal(source.schema,1);assert.equal(source.kind,'sphere-triangle-mesh-entry-fixtures');
assert.ok(Array.isArray(source.fixtures));assert.equal(source.fixtures.length,65);
const primitiveSettings=['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared'];
const guardSettings=['maxEvaluations','maxLeaves','maxDepth','enclosureSqrtRefinements','maxTotalSqrtRefinements'];
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const singleStatuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const singleReasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const features=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'];
const dispositions=['retained','outside_simplex','kkt_violated'];
const relations=['separated','penetrating','touching','boundary_unresolved'];
const view=new DataView(new ArrayBuffer(8));
function bits(value){assert.equal(typeof value,'number');assert.ok(Number.isFinite(value));view.setFloat64(0,value);return view.getBigUint64(0).toString(16).padStart(16,'0');}
function compare(actual,expected,label,counter){
 assert.equal(typeof actual,typeof expected,label);
 if(typeof expected==='number'){
  assert.equal(bits(actual),bits(expected),label);counter.numeric++;if(Object.is(actual,-0))counter.negativeZero++;
 }else if(expected!==null&&typeof expected==='object'){
  assert.ok(actual!==null,label);assert.equal(Array.isArray(actual),Array.isArray(expected),label);
  assert.deepEqual(Object.keys(actual).sort(),Object.keys(expected).sort(),label);
  for(const key of Object.keys(expected))compare(actual[key],expected[key],label+'.'+key,counter);
 }else assert.equal(actual,expected,label);
}
function ordinal(value,choices,label){assert.equal(typeof value,'string',label);const index=choices.indexOf(value);assert.ok(index>=0,label);return index;}
function projectSingle(result){
 return {...result,status:ordinal(result.status,singleStatuses,'single status'),reason:ordinal(result.reason,singleReasons,'single reason'),
  geometry:result.geometry===null?null:{...result.geometry,relation:ordinal(result.geometry.relation,relations,'relation')},
  candidates:result.candidates.map(c=>({...c,feature:ordinal(c.feature,features,'candidate feature'),disposition:ordinal(c.disposition,dispositions,'candidate disposition')}))};
}
function projectMesh(result){
 return {...result,status:ordinal(result.status,meshStatuses,'mesh status'),reason:ordinal(result.reason,meshReasons,'mesh reason'),
  rows:result.rows.map(row=>({...row,query:row.query===null?null:projectSingle(row.query)}))};
}
function project(result){
 assert.ok(result&&typeof result==='object'&&!Array.isArray(result));
 const {originalInput,...model}=result;
 assert.ok(originalInput&&typeof originalInput==='object');
 return {...model,audits:model.audits.map(a=>({...a,
  meshStatus:a.meshStatus===null?null:ordinal(a.meshStatus,meshStatuses,'audit mesh status'),
  meshReason:a.meshReason===null?null:ordinal(a.meshReason,meshReasons,'audit mesh reason')})),
  lastMesh:model.lastMesh===null?null:projectMesh(model.lastMesh)};
}
function echo(q){
 const s=q.settings,p=s.mesh.primitive;
 return [...q.start,...q.end,q.radius,s.mesh.maxSurfaces,...primitiveSettings.map(k=>p[k]),...guardSettings.map(k=>s[k]),s.parameterTolerance,0,0,0,0];
}
function expectedOriginal(q){return {...own(q),echo:echo(q)};}
function hostReason(q){
 if(q.triangles.length>64)return 'surface_count';
 for(const t of q.triangles)if(!Number.isSafeInteger(t.id)||t.id<=0)return 'surface_id';
 // No coordinate-domain/conditioning/zero-setting decisions are made here.
 // Finite model-invalid values belong to the actual C++ guard, not host logic.
 const integers=[q.settings.mesh.maxSurfaces,...primitiveSettings.slice(0,3).map(k=>q.settings.mesh.primitive[k]),...guardSettings.map(k=>q.settings[k])];
 if(integers.some(v=>!Number.isInteger(v)||v<0||v>0xffffffff))return 'integer_exchange';
 return null;
}
function mutateNumbers(value,replacement=9001){
 if(value===null||typeof value!=='object')return;
 for(const key of Object.keys(value))if(typeof value[key]==='number')value[key]=replacement;else mutateNumbers(value[key],replacement);
}
const wasmBytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes});
assert.equal(typeof runtime.querySphereTriangleMeshEntry,'function','public owned decoder required');
runtime.check(runtime.native._pp_sim_reset());
const counters={model:{numeric:0,negativeZero:0},originalInput:{numeric:0,negativeZero:0},hostOutput:{numeric:0,negativeZero:0},ownership:{numeric:0,negativeZero:0}};
const replay=[],mixed=[],origins=[],returned=[],hostFailures=[],retained=[];
let separated=0,entryWindows=0,initialPenetrations=0,expectedModelFailures=0,callerOwnershipChecks=0;
for(let index=0;index<source.fixtures.length;index++){
 const fixture=source.fixtures[index],q=own(fixture.input),label=`fixture[${index}]`;
 assert.equal(typeof fixture.name,'string');
 const before=signed(q),reason=hostReason(q),outputBefore=runtime.output();
 let actual,error;
 try{actual=runtime.querySphereTriangleMeshEntry({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings);}catch(caught){error=caught;}
 assert.equal(signed(q),before,label+' caller untouched by attempt');
 if(reason!==null){
  assert.ok(error instanceof Error,label+' host rejection required');assert.equal(actual,undefined);
  compare(runtime.output(),outputBefore,label+' host output retained',counters.hostOutput);
  hostFailures.push({index,name:fixture.name,reason,message:error.message});
  mixed.push(own(fixture));origins.push({index,name:fixture.name,origin:'pure-native-host-supplement',reason});continue;
 }
 if(error)throw error;
 const projected=project(actual);
 compare(projected,fixture.result,label+'.completeModel',counters.model);
 compare(actual.originalInput,expectedOriginal(fixture.input),label+'.originalInput',counters.originalInput);
 const preserved=signed(actual);mutateNumbers(q);assert.equal(signed(actual),preserved,label+' returned DTO owns caller source/settings');callerOwnershipChecks++;
 replay.push({name:fixture.name,input:own(fixture.input),result:own(projected)});
 mixed.push({name:fixture.name,input:own(fixture.input),result:own(projected)});
 origins.push({index,name:fixture.name,origin:'actual-wasm-owned-js-decoder'});
 returned.push({index,name:fixture.name,result:own(actual)});retained.push({index,result:actual,preserved});
 if(actual.status==='separated')separated++;else if(actual.status==='entry_window')entryWindows++;else if(actual.status==='initial_penetration')initialPenetrations++;else expectedModelFailures++;
}
assert.equal(replay.length+hostFailures.length,65);
for(const held of retained)assert.equal(signed(held.result),held.preserved,`fixture[${held.index}] prior DTO retained after all later attempts`);

// Extra ownership attempts are counted separately from the fixed 65-input
// corpus. Input, originalInput, snapshot, prior/next DTO, and scratch lifetimes
// are deliberately changed in different steps, never used as model fixtures.
const selected=source.fixtures.find(f=>hostReason(f.input)===null&&f.result.snapshot!==null&&f.result.lastMesh!==null);
assert.ok(selected,'an owned source snapshot is required');
const q1=own(selected.input),r1=runtime.querySphereTriangleMeshEntry({start:q1.start,end:q1.end,radius:q1.radius},q1.triangles,q1.settings);
const r1Saved=signed(r1);mutateNumbers(q1);assert.equal(signed(r1),r1Saved,'extra caller mutation leaves DTO owned');
const call=()=>{const q=own(selected.input);return runtime.querySphereTriangleMeshEntry({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings);};
const r2=call(),r2Saved=signed(r2);assert.equal(signed(r1),r1Saved,'subsequent Native snapshot leaves prior DTO owned');
compare(project(r2),selected.result,'ownership replay complete model',counters.ownership);
const meshSourcesBefore=signed(r1.lastMesh.rows.map(row=>row.triangle));
const snapshotBefore=signed(r1.snapshot);mutateNumbers(r1.originalInput);
assert.equal(signed(r1.snapshot),snapshotBefore,'originalInput and Native snapshot are separately owned');
assert.equal(signed(r1.lastMesh.rows.map(row=>row.triangle)),meshSourcesBefore,'originalInput and lastMesh row sources are separately owned');
const originalBefore=signed(r1.originalInput);mutateNumbers(r1.snapshot);
assert.equal(signed(r1.originalInput),originalBefore,'Native snapshot and originalInput are separately owned');
assert.equal(signed(r1.lastMesh.rows.map(row=>row.triangle)),meshSourcesBefore,'Native snapshot and lastMesh row sources are separately owned');
const changedSnapshotBefore=signed(r1.snapshot);
for(const row of r1.lastMesh.rows)mutateNumbers(row.triangle,9002);
assert.equal(signed(r1.snapshot),changedSnapshotBefore,'lastMesh source edits leave Native snapshot owned');
assert.equal(signed(r1.originalInput),originalBefore,'lastMesh source edits leave originalInput owned');
mutateNumbers(r1);assert.equal(signed(r2),r2Saved,'prior DTO edits leave subsequent DTO owned');
runtime.inputF64(Array(64).fill(9001));assert.equal(signed(r2),r2Saved,'exchange scratch edits leave returned DTO owned');
const outputCopy=runtime.output();outputCopy.fill(9002);
assert.equal(signed(r2),r2Saved,'public output copy edits leave returned DTO owned');
const r3=call();compare(project(r3),selected.result,'ownership retry complete model',counters.ownership);
for(const held of retained)assert.equal(signed(held.result),held.preserved,`fixture[${held.index}] corpus DTO retained after extra ownership attempts`);

await save('wasm-owned-fixtures.json',{schema:1,kind:source.kind,fixtures:replay});
await save('mixed-fixtures.json',{schema:1,kind:source.kind,fixtures:mixed});
await save('wasm-owned-dtos.json',{schema:1,kind:'sphere-triangle-mesh-entry-owned-sdk-dtos',fixtures:returned});
await save('origins.json',{schema:1,modelCount:replay.length,hostSupplementCount:hostFailures.length,fixtures:origins});
await save('host-rejections.json',{schema:1,fixtures:hostFailures});
const python=process.env.PIKAPIKA_PYTHON??(process.platform==='win32'?'python':'python3');
const commands=[];
async function runPython(name,script,args){
 const argv=['-X','utf8',fileURLToPath(new URL(script,import.meta.url)),...args];
 const run=spawnSync(python,argv,{windowsHide:true,encoding:'utf8',timeout:180000,maxBuffer:16777216});
 await save(name+'.stdout.txt',run.stdout??'');await save(name+'.stderr.txt',run.stderr??'');
 commands.push({executable:python,argv,exitCode:run.status,signal:run.signal,error:run.error?String(run.error):null});
 await writeFile(path.join(dir,'commands.json'),JSON.stringify(commands,null,2)+'\n');
 assert.ifError(run.error);assert.equal(run.status,0,name+'; see saved stdout/stderr');
 return parseStrictJson(run.stdout,budget);
}
const mixedFile=path.join(dir,'mixed-fixtures.json');
const reference=await runPython('reference','./verify-sphere-triangle-mesh-entry.py',[mixedFile]);
const negative=await runPython('negative-controls','../tests/sphere_triangle_mesh_entry_reference_tests.py',[mixedFile,'--output',path.join(dir,'negative-controls')]);
const files={};
for(const name of ['source-fixtures.json','wasm-owned-fixtures.json','mixed-fixtures.json','wasm-owned-dtos.json','origins.json','host-rejections.json','reference.stdout.txt','reference.stderr.txt','negative-controls.stdout.txt','negative-controls.stderr.txt','commands.json']){
 const bytes=await readFile(path.join(dir,name));files[name]={bytes:bytes.length,sha256:sha(bytes)};
}
const report={schema:1,status:'PASS',fixtureCount:source.fixtures.length,actualModelFixtures:replay.length,hostRejected:hostFailures.length,
 separated,entryWindows,initialPenetrations,expectedModelFailures,
 modelNumericComparisons:counters.model.numeric,modelNegativeZeroComparisons:counters.model.negativeZero,
 originalInputNumericComparisons:counters.originalInput.numeric,originalInputNegativeZeroComparisons:counters.originalInput.negativeZero,
 hostOutputNumericComparisons:counters.hostOutput.numeric,hostOutputNegativeZeroComparisons:counters.hostOutput.negativeZero,
 ownership:{callerMutationChecks:callerOwnershipChecks,corpusDtosRetained:retained.length,extraModelCalls:3,extraModelNumericComparisons:counters.ownership.numeric,extraModelNegativeZeroComparisons:counters.ownership.negativeZero,
  originalInputSnapshotSeparate:true,lastMeshRowSourcesSeparate:true,priorAndSubsequentDtosSeparate:true,exchangeScratchSeparate:true,publicOutputCopySeparate:true},
 reference,negativeControls:negative,
 mathematicalCorpus:{fixtures:mixed.length,actualOwnedWasmDecoderResults:replay.length,pureNativeHostSupplements:hostFailures.length,
  scope:'All model DTO fields first matched to pure Native bits. The 62 decoder-derived complete model DTOs are projected into the pinned 65-input mathematical corpus; the three exchange-rejected pure Native results are explicitly supplemented, never claimed as WASM model results. The 62-only file is an artifact, not falsely presented as accepted by the pinned checker.'},
 source:{bytes:sourceBytes.length,sha256:sha(sourceBytes)},wasm:{bytes:wasmBytes.length,sha256:sha(wasmBytes)},files,
 scope:'Actual shared WASM through the public owned JavaScript entry decoder. Counts are complete DTO comparisons, separate from earlier Native/raw-WASM wire counts. Read-only defined-segment guard; no UI, World, TOI, contact response, or allocation/unknown-work exception injection.'};
const dependencies={};
for(const relative of ['./verify-sphere-triangle-mesh-entry-sdk.mjs','../engine/simulation.mjs','../engine/sphere-triangle-mesh-entry.mjs','../engine/strict-json.mjs',
 './verify-sphere-triangle-mesh-entry.py','./verify-sphere-triangle-mesh-trajectory.py','./verify-sphere-triangle-mesh.py','./verify-sphere-triangle.py','../tests/sphere_triangle_mesh_entry_reference_tests.py']){
 const bytes=await readFile(new URL(relative,import.meta.url));dependencies[relative]={bytes:bytes.length,sha256:sha(bytes)};
}
report.dependencies=dependencies;
await save('report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
