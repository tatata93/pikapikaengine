import assert from 'node:assert/strict';
import {createHash,randomBytes} from 'node:crypto';
import {readFile,writeFile,mkdir,lstat,realpath} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
import os from 'node:os';
import {loadSimulationRuntime,SimulationRuntime} from '../../engine/simulation.mjs';
import {createDerivedGPUProfileCases} from '../../tools/derived-gpu-cases.mjs';
import {hashProfileDTO} from '../../scripts/profile-derived-mesh.mjs';

// Exploration only. No production method/prototype/module is modified. The sole
// override belongs to one fresh, isolated runtime and is removed in finally.
export function indexedCopy(view){const result=new Array(view.length);for(let i=0;i<view.length;++i)result[i]=view[i];return result;}
function indexedOutput(){const m=this.native,p=m._pp_sim_output_f64_ptr()/8;return indexedCopy(m.HEAPF64.subarray(p,p+m._pp_sim_output_count()));}
const ROOT=fileURLToPath(new URL('../../',import.meta.url)),BASE=fileURLToPath(new URL('./',import.meta.url));
const MAX_MS=30000,ITERATIONS=10000,PHASES=['initial','warmup','measure','measure','measure'];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const bits=value=>{const b=Buffer.alloc(8);b.writeDoubleBE(value);return b.toString('hex');};
function exact(value){
 if(value===null)return {type:'null'};
 if(typeof value==='number'){assert.ok(Number.isFinite(value));return {type:'number',bits:bits(value)};}
 if(ArrayBuffer.isView(value)&&!(value instanceof DataView))return {type:value.constructor.name,length:value.length,bytesHex:Buffer.from(value.buffer,value.byteOffset,value.byteLength).toString('hex')};
 if(Array.isArray(value)){for(let i=0;i<value.length;++i)assert.ok(i in value);return {type:'Array',items:value.map(exact)};}
 if(typeof value==='object')return {type:'Object',entries:Object.entries(value).map(([key,item])=>[key,exact(item)])};
 assert.ok(typeof value==='string'||typeof value==='boolean');return {type:typeof value,value};
}
function summary(values){const sorted=[...values].sort((a,b)=>a-b),n=sorted.length;return {samples:n,medianMs:n%2?sorted[Math.floor(n/2)]:sorted[n/2-1]/2+sorted[n/2]/2,p95Ms:sorted[Math.ceil(.95*n)-1],minMs:sorted[0],maxMs:sorted[n-1]};}
function exportsOf(runtime){return Object.fromEntries(Object.keys(runtime.native).filter(k=>k.startsWith('_pp_sim_')&&typeof runtime.native[k]==='function').map(k=>[k,runtime.native[k]]));}
function functionsUnchanged(runtime,prior){assert.deepEqual(Object.keys(exportsOf(runtime)),Object.keys(prior));for(const key of Object.keys(prior))assert.equal(runtime.native[key],prior[key],key);}
function equal(a,b){assert.deepStrictEqual(a,b);const old=hashProfileDTO(a),candidate=hashProfileDTO(b);assert.deepEqual(candidate,old);return old;}

async function execute(){
 const started=performance.now(),startedAt=new Date().toISOString(),deadline=started+MAX_MS;
 const guard=()=>assert.ok(performance.now()<deadline,'30 second pilot budget exceeded (incomplete experiment)');
 await mkdir(BASE,{recursive:true});assert.equal((await lstat(BASE)).isSymbolicLink(),false);assert.equal(await realpath(BASE),path.resolve(BASE));
 const destination=path.join(BASE,'run-'+Date.now()+'-'+randomBytes(4).toString('hex'));await mkdir(destination);
 let retainedBytes=0;const retained=[];
 async function save(name,value){const data=typeof value==='string'?value:JSON.stringify(value,null,2)+'\n';const count=Buffer.byteLength(data);assert.ok(retainedBytes+count<=10*1024*1024,'10 MiB output cap exceeded');await writeFile(path.join(destination,name),data,{flag:'wx'});retainedBytes+=count;retained.push({name,bytes:count,sha256:sha(data)});}
 const provenance={schema:1,startedAt,command:{executable:process.execPath,argv:process.argv,cwd:process.cwd()},limits:{wallBudgetMs:MAX_MS,prepareQueries:30,microCopies:5*PHASES.length*2*ITERATIONS,perMicroTrialIterations:ITERATIONS,maxRetainedBytes:10*1024*1024},environment:{node:process.version,versions:process.versions,platform:process.platform,arch:process.arch,os:os.type()+' '+os.release(),cpus:os.cpus().map(({model,speed})=>({model,speedMHz:speed})),memoryBytes:os.totalmem(),endianness:os.endianness()},scope:'Bounded exploratory Node comparison. No speed guarantee, Native/GPU timing, production replacement, overhead subtraction or general workload claim. Micro copy isolates Array.from(view) versus indexedCopy(view); full prepare includes C++/ABI/getters/decode. Initial means first measured pair after source setup, not a process-cold/JIT-cold claim. Alternating order does not remove GC/CPU/clock/own-method instrumentation perturbation.'};
 let candidate=null,old=null,proto=null,oldOutput=null,candidatePrior=null,refs=null,before=null,after=null;
 try{
  const manifestBytes=await readFile(path.join(ROOT,'assets/pikapika-simulation.build.json')),manifest=JSON.parse(manifestBytes);
  const names=[...Object.keys(manifest.sourceSha256),...Object.keys(manifest.licenses),...Object.keys(manifest.artifacts),'assets/pikapika-simulation.build.json','engine/simulation.mjs','engine/skin-binding.mjs','tools/derived-gpu-cases.mjs','scripts/profile-derived-mesh.mjs','build/derived-copy-pilot/run.mjs'];
  async function hashes(){const result={};for(const name of names){guard();const bytes=await readFile(path.join(ROOT,name));result[name]={bytes:bytes.length,sha256:sha(bytes)};}return result;}
  before=await hashes();for(const [name,expected]of Object.entries({...manifest.sourceSha256,...manifest.licenses}))assert.equal(before[name].sha256,expected,name);
  for(const [name,expected]of Object.entries(manifest.artifacts))assert.deepEqual(before[name],expected,name);
  assert.equal(Object.keys(manifest.sourceSha256).length,53);assert.equal(Object.keys(manifest.licenses).length,7);assert.equal(Object.keys(manifest.artifacts).length,2);
  provenance.before=before;await save('provenance-start.json',provenance);guard();
  const wasm=await readFile(path.join(ROOT,'assets/pikapika-simulation.wasm'));
  const init=performance.now();old=await loadSimulationRuntime({wasmBytes:new Uint8Array(wasm)});candidate=await loadSimulationRuntime({wasmBytes:new Uint8Array(wasm)});provenance.runtimePairInitializationMs=performance.now()-init;
  assert.notEqual(old,candidate);assert.notEqual(old.native,candidate.native);assert.notEqual(old.native.HEAPF64.buffer,candidate.native.HEAPF64.buffer);
  proto=SimulationRuntime.prototype.output;oldOutput=old.output;candidatePrior=candidate.output;assert.equal(proto,oldOutput);assert.equal(candidatePrior,proto);refs=[exportsOf(old),exportsOf(candidate)];
  assert.equal(Object.hasOwn(old,'output'),false);assert.equal(Object.hasOwn(candidate,'output'),false);candidate.output=indexedOutput;
  const oldSetup=createDerivedGPUProfileCases(old),newSetup=createDerivedGPUProfileCases(candidate);assert.equal(oldSetup.sourcePreparation.authorSourceBefore,newSetup.sourcePreparation.authorSourceBefore);
  assert.equal(oldSetup.verifySourceUnchanged(),true);assert.equal(newSetup.verifySourceUnchanged(),true);const caseInputs=equal(oldSetup.cases,newSetup.cases);
  await save('inputs.json',{schema:1,source:oldSetup.sourcePreparation.authorSourceBefore,cases:oldSetup.cases,casesExact:exact(oldSetup.cases),inputHash:caseInputs,note:'casesExact retains all signed-zero bits; ordinary JSON cases is a convenience projection.'});
  const trials=[],full=[];let comparedNumbers=0;
  for(let c=0;c<oldSetup.cases.length;++c){
   const oldCase=oldSetup.cases[c],newCase=newSetup.cases[c],inputHash=equal(oldCase,newCase),entry=[];
   for(let j=0;j<PHASES.length;++j){
    guard();const order=(j+c)%2?['candidate','old']:['old','candidate'],row={caseName:oldCase.name,pair:j,phase:PHASES[j],order,timing:{},hash:null},results={};
    for(const kind of order){const runtime=kind==='old'?old:candidate,input=kind==='old'?oldCase:newCase,t0=performance.now();results[kind]=runtime.prepareDerivedMesh(input.input,input.settings);const duration=performance.now()-t0;assert.ok(Number.isFinite(duration)&&duration>=0);row.timing[kind]={elapsedMs:duration};}
    assert.equal(results.old.status,'completed');row.hash=equal(results.old,results.candidate);comparedNumbers+=row.hash.counts.numbers+row.hash.counts.typedElements;
    assert.deepEqual(hashProfileDTO(oldCase),inputHash);assert.deepEqual(hashProfileDTO(newCase),inputHash);oldSetup.verifySourceUnchanged();newSetup.verifySourceUnchanged();
    if(j===0)full.push({caseName:oldCase.name,old:exact(results.old),candidate:exact(results.candidate)});
    entry.push(row);trials.push(row);guard();
   }
  }
  // Collect real getter packets only after timed prepare, avoiding an unreported
  // derived prepare prewarm. The capacity64 input below is synthetic pure-copy.
  const native=old.native,p=native._pp_sim_output_f64_ptr()/8,microRecords=[];
  for(const [kind,length]of [[0,3],[2,18],[3,26]]){old.check(native._pp_sim_derived_mesh_record(kind,0));assert.equal(native._pp_sim_output_count(),length);microRecords.push({name:'actual-record-'+length,origin:'Native derived getter '+kind,values:old.output()});}
  const final=oldSetup.cases[2];const n=old.inputF64([final.input.positions.length,final.input.triangles.length,2048,32768,128,0,0,0,...final.input.positions.flat()]);const u=old.inputU32(final.input.triangles.flat());old.check(native._pp_sim_derived_mesh(n,u));assert.equal(native._pp_sim_output_count(),20);microRecords.push({name:'actual-summary-20',origin:'Native derived summary',values:old.output()});
  const extremes=[0,-0,Number.MIN_VALUE,-Number.MIN_VALUE,Number.MAX_VALUE,-Number.MAX_VALUE,1,-1,1e-300,-1e-300];
  microRecords.push({name:'synthetic-capacity-64',origin:'Synthetic pure-copy values; not a Native output record',values:Array.from({length:64},(_,i)=>extremes[i%extremes.length])});
  let sink=0;const microTrials=[];
  for(let c=0;c<microRecords.length;++c){const record=microRecords[c];
   // Real packet values are restored to the isolated module's output scratch,
   // then both copy functions receive precisely the same HEAPF64.subarray. No
   // native operation/decoder is timed here. Synthetic capacity64 stays owned.
   const view=c===microRecords.length-1?new Float64Array(record.values):native.HEAPF64.subarray(p,p+record.values.length);
   if(c!==microRecords.length-1)view.set(record.values);const reference=Array.from(view);equal(reference,indexedCopy(view));
   for(let j=0;j<PHASES.length;++j){guard();const row={name:record.name,pair:j,phase:PHASES[j],iterations:ITERATIONS,order:(c+j)%2?['candidate','old']:['old','candidate'],timing:{}};
    for(const kind of row.order){const copy=kind==='old'?Array.from:indexedCopy,t0=performance.now();let last;for(let k=0;k<ITERATIONS;++k){last=copy(view);sink+=last.length;}const elapsedMs=performance.now()-t0;assert.ok(Number.isFinite(elapsedMs)&&elapsedMs>=0);row.timing[kind]={elapsedMs,perCopyMs:elapsedMs/ITERATIONS};equal(last,reference);}
    microTrials.push(row);guard();
   }
  }
  // Verify ownership, live replacement views and unchanged subarray clamping
  // independently of timing. This models view replacement, not real WASM growth.
  const ownership=[];
  for(const length of [0,3,18,20,26,64]){const memory=new Float64Array(extremes.slice(0,Math.min(length,extremes.length)).concat(Array(Math.max(0,length-extremes.length)).fill(-0))),mock={HEAPF64:memory,_pp_sim_output_f64_ptr:()=>0,_pp_sim_output_count:()=>length},fake={native:mock};
   const a=Reflect.apply(proto,fake,[]),b=Reflect.apply(indexedOutput,fake,[]),saved=exact(a);equal(a,b);assert.ok(Array.isArray(a)&&Array.isArray(b));assert.equal(Object.keys(b).length,length);
   if(length){a[0]=123;assert.notEqual(memory[0],123);b[0]=456;assert.notEqual(memory[0],456);}
   const held=Reflect.apply(indexedOutput,fake,[]),heldBefore=exact(held);mock.HEAPF64=new Float64Array(length).fill(7);assert.deepEqual(exact(held),heldBefore);equal(Reflect.apply(proto,fake,[]),Reflect.apply(indexedOutput,fake,[]));
   for(const [begin,end]of [[-3,undefined],[-99,999],[99,100],[0,undefined]]){const v=memory.subarray(begin,end);equal(Array.from(v),indexedCopy(v));}
   ownership.push({length,initial:saved,held:heldBefore,arrayDense:true,heapMutationIsolated:true,replacementViewObserved:true,subarrayClampingIdentical:true});
  }
  const rawRetained=[];for(const runtime of [old,candidate]){runtime.check(runtime.native._pp_sim_derived_mesh_record(2,0));const output=runtime.output(),prior=exact(output);runtime.check(runtime.native._pp_sim_derived_mesh_record(3,0));assert.deepEqual(exact(output),prior);assert.ok(Array.isArray(output));rawRetained.push(prior);}assert.deepEqual(rawRetained[0],rawRetained[1]);
  // Existing full copied DTOs must survive later queries in their own modules.
  const heldOld=old.prepareDerivedMesh(oldSetup.cases[0].input),heldCandidate=candidate.prepareDerivedMesh(newSetup.cases[0].input),heldHash=equal(heldOld,heldCandidate);
  old.prepareDerivedMesh(oldSetup.cases[1].input);candidate.prepareDerivedMesh(newSetup.cases[1].input);assert.deepEqual(hashProfileDTO(heldOld),heldHash);assert.deepEqual(hashProfileDTO(heldCandidate),heldHash);
  equal(oldSetup.cases,newSetup.cases);assert.deepEqual(hashProfileDTO(oldSetup.cases),caseInputs);oldSetup.verifySourceUnchanged();newSetup.verifySourceUnchanged();
  assert.equal(old.output,oldOutput);assert.equal(SimulationRuntime.prototype.output,proto);functionsUnchanged(old,refs[0]);functionsUnchanged(candidate,refs[1]);assert.equal(candidate.output,indexedOutput);
  delete candidate.output;assert.equal(candidate.output,candidatePrior);after=await hashes();assert.deepEqual(after,before);guard();
  const statistics=[];for(const [group,rows,key]of [['prepare',trials,'caseName'],['micro',microTrials,'name']])for(const name of [...new Set(rows.map(r=>r[key]))])for(const kind of ['old','candidate']){const values=rows.filter(r=>r[key]===name&&r.phase==='measure').map(r=>r.timing[kind].elapsedMs);statistics.push({group,name,kind,phase:'measure',...summary(values)});}
  await save('prepare-trials.json',{schema:1,trials,firstPairFullDTO:full});await save('micro-trials.json',{schema:1,records:microRecords.map(r=>({...r,values:exact(r.values)})),trials:microTrials,sink,scope:'10,000 copies per timed batch; only final value checked per batch. All iterations contribute to length sink. Actual packets use the identical HEAPF64.subarray after restoring captured values to isolated output scratch; pointer/count/getter work is excluded. JIT/GC/loop/sink overhead uncalibrated; max64 is synthetic, not a Native packet.'});await save('ownership.json',{schema:1,checks:ownership,realRawArraysAfterNextGetter:rawRetained,existingDTOUnchangedAfterLaterQueries:true,liveViewReplacement:'Simulated alternate HEAPF64; actual memory.grow not induced'});
  const elapsedMs=performance.now()-started;const report={schema:1,status:'PASS',runDirectory:path.relative(ROOT,destination).replaceAll('\\','/'),elapsedMs,timedPrepareQueries:trials.length*2,setupOrOwnershipQueries:5,comparedNumericValues:comparedNumbers,allDTOExact:true,sourceAndInputUnchanged:true,originalMethodsAndNativeExportsUnchanged:true,sdkInputsUnchanged:true,statistics,interpretation:provenance.scope};
  await save('report.json',report);await save('provenance.json',{...provenance,after,elapsedMs:performance.now()-started,retained,notes:'All measurements exploratory. Three measure samples only; p95 nearest rank is max. No subtraction of copy micro from prepare or claim of causation. No production optimization adopted.'});console.log(JSON.stringify(report,null,2));
 }catch(error){
  await save('failure.json',{schema:1,status:'FAIL',elapsedMs:performance.now()-started,error:{name:error.name,message:error.message,stack:error.stack},before,after});throw error;
 }finally{if(candidate&&candidatePrior){delete candidate.output;assert.equal(candidate.output,candidatePrior);}if(proto)assert.equal(SimulationRuntime.prototype.output,proto);if(oldOutput)assert.equal(old.output,oldOutput);}
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
 if(process.argv.length===3&&process.argv[2]==='--run')await execute();
 else if(process.argv.length===3&&process.argv[2]==='--help')console.log('node build/derived-copy-pilot/run.mjs --run (bounded exploratory comparison; creates a new ignored run directory)');
 else throw new Error('Explicit --run required; no measurements performed');
}
