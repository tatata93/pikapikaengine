import assert from 'node:assert/strict';
import {createHash,randomBytes} from 'node:crypto';
import {readFile,writeFile,mkdir,lstat,realpath} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {loadSimulationRuntime,SimulationRuntime} from '../engine/simulation.mjs';
import {createDerivedMeshProfiler} from '../tools/derived-profile.mjs';
import {createDerivedGPUProfileCases} from '../tools/derived-gpu-cases.mjs';
import {hashProfileDTO,profileStatistics} from './profile-derived-mesh.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url)),MAX_BYTES=10*1024*1024,MAX_QUERIES=60,DEADLINE_MS=30000;
const stages=['f64Exchange','u32Exchange','cppQuery','cppGetter','outputCopy'];
const paths=['singleBaseline','singleInstrumented','batchBaseline','batchInstrumented'];
const phases=['initial','warmup','measure','measure','measure'];
const usage='Usage: node scripts/profile-derived-readback.mjs --output build/derived-readback[-label]';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const errorData=error=>({name:error?.name??'Error',message:error?.message??String(error),code:error?.code??null,stack:error?.stack??null});
export function parseReadbackArgs(argv){
 if(argv.length===1&&argv[0]==='--help')return {help:true};
 if(argv.length!==2||argv[0]!=='--output'||!argv[1]||argv[1].startsWith('--'))throw new Error(usage);
 return {output:argv[1],totalQueries:MAX_QUERIES};
}
export function exactReadbackDTO(value){
 if(value===null)return {type:'null'};
 if(typeof value==='number'){assert.ok(Number.isFinite(value));const data=new DataView(new ArrayBuffer(8));data.setFloat64(0,value);return {type:'number',bits:data.getBigUint64(0).toString(16).padStart(16,'0')};}
 if(ArrayBuffer.isView(value)&&!(value instanceof DataView))return {type:value.constructor.name,length:value.length,bytesHex:Buffer.from(value.buffer,value.byteOffset,value.byteLength).toString('hex')};
 if(ArrayBuffer.isView(value))throw new Error('Unsupported DataView DTO');
 if(Array.isArray(value)){assert.equal(Object.keys(value).length,value.length,'Sparse arrays are unsupported');return {type:'Array',items:value.map(exactReadbackDTO)};}
 if(typeof value==='object')return {type:'Object',entries:Object.entries(value).map(([key,item])=>[key,exactReadbackDTO(item)])};
 if(['string','boolean'].includes(typeof value))return {type:typeof value,value};
 throw new Error('Unsupported exact DTO value');
}
function signedJSON(value){
 if(typeof value==='number'){assert.ok(Number.isFinite(value));return Object.is(value,-0)?'-0':JSON.stringify(value);}
 if(value===null||typeof value==='string'||typeof value==='boolean')return JSON.stringify(value);
 if(Array.isArray(value))return '['+Array.from(value,signedJSON).join(',')+']';
 if(typeof value==='object')return '{'+Object.entries(value).map(([key,item])=>JSON.stringify(key)+':'+signedJSON(item)).join(',')+'}';
 throw new Error('Unsupported report value');
}
async function outputDirectory(value){
 const build=path.resolve(ROOT,'build'),base=path.resolve(value),relative=path.relative(build,base);
 if(path.dirname(base)!==build||!/^derived-readback(?:-[A-Za-z0-9_-]+)?$/.test(relative))throw new Error('Output must be a direct build/derived-readback[-label] directory');
 await mkdir(build,{recursive:true});if(await realpath(build)!==build)throw new Error('Symlinked build directory is unsupported');
 try{const stat=await lstat(base);if(!stat.isDirectory()||stat.isSymbolicLink())throw new Error('Output root must be a real directory');}catch(error){if(error.code!=='ENOENT')throw error;await mkdir(base);}
 if(await realpath(base)!==base)throw new Error('Symlinked output directory is unsupported');
 const run=path.join(base,'run-'+Date.now()+'-'+randomBytes(6).toString('hex'));await mkdir(run);return run;
}
async function environment(){
 const manifestBytes=await readFile(path.join(ROOT,'assets/pikapika-simulation.build.json')),manifest=JSON.parse(manifestBytes),files=[];
 for(const [name,expected]of Object.entries(manifest.sourceSha256)){const bytes=await readFile(path.join(ROOT,name));assert.equal(sha(bytes),expected,'SDK source '+name);files.push({path:name,bytes:bytes.length,sha256:expected});}
 const artifacts=[];for(const [name,expected]of Object.entries(manifest.artifacts)){const bytes=await readFile(path.join(ROOT,name));assert.equal(sha(bytes),expected.sha256,name);assert.equal(bytes.length,expected.bytes,name);artifacts.push({path:name,...expected});}
 const notices=[];for(const [name,expected]of Object.entries(manifest.licenses)){const bytes=await readFile(path.join(ROOT,name));assert.equal(sha(bytes),expected,name);notices.push({path:name,bytes:bytes.length,sha256:expected});}
 const authored=[];for(const name of ['scripts/profile-derived-readback.mjs','tools/derived-profile.mjs','tools/derived-gpu-cases.mjs','scripts/profile-derived-mesh.mjs','engine/simulation.mjs','engine/skin-binding.mjs','engine/motion.mjs','engine/strict-json.mjs']){const bytes=await readFile(path.join(ROOT,name));authored.push({path:name,bytes:bytes.length,sha256:sha(bytes)});}
 return {node:process.version,versions:process.versions,platform:process.platform,arch:process.arch,osRelease:os.release(),endianness:os.endianness(),cpuModel:os.cpus()[0]?.model??null,logicalCPUs:os.cpus().length,sdkManifest:manifest,sdkManifestSHA256:sha(manifestBytes),sdkSourceHashes:files,sdkArtifacts:artifacts,runtimeNotices:notices,authoredSourceHashes:authored};
}
function identities(runtime){
 const native=runtime.native,exports=new Map(Object.entries(native).filter(([key,value])=>key.startsWith('_pp_sim_')&&typeof value==='function'));
 const methods=new Map(['prepareDerivedMesh','inputF64','inputU32','output','check'].map(key=>[key,runtime[key]]));
 const prototype=new Map(Object.getOwnPropertyNames(SimulationRuntime.prototype).map(key=>[key,Object.getOwnPropertyDescriptor(SimulationRuntime.prototype,key)]));
 return {exportNames:[...exports.keys()],check(){assert.equal(runtime.native,native);for(const [key,value]of exports)assert.equal(native[key],value,'Export changed '+key);for(const [key,value]of methods)assert.equal(runtime[key],value,'Method changed '+key);for(const [key,value]of prototype)assert.deepEqual(Object.getOwnPropertyDescriptor(SimulationRuntime.prototype,key),value,'Prototype changed '+key);}};
}
export function expectedReadbackCounts(result,mode){
 assert.ok(mode==='single'||mode==='batch');const geometry=result.geometry,records=[geometry?geometry.positions.length:0,geometry?geometry.triangles.length:0,geometry?geometry.triangles.length:0,result.audits.length];
 const max=[20,20,3,2],calls=records.map((count,kind)=>mode==='single'?count:Math.ceil(count/max[kind]));return {records,calls,getters:calls.reduce((a,b)=>a+b,0)};
}
function validateTiming(timing,result,mode){
 assert.ok(timing&&Number.isFinite(timing.elapsedMs)&&timing.elapsedMs>=0,'Invalid instrumented clock');assert.deepEqual(Object.keys(timing.stages),stages);
 const expected=expectedReadbackCounts(result,mode);assert.deepEqual(timing.getterKinds,expected.calls);assert.deepEqual(timing.getterRecords,expected.records);
 for(const stage of Object.values(timing.stages)){assert.ok(Number.isSafeInteger(stage.calls)&&stage.calls>=0);assert.ok(Number.isFinite(stage.elapsedMs)&&stage.elapsedMs>=0);}
 for(const name of ['f64Exchange','u32Exchange','cppQuery'])assert.equal(timing.stages[name].calls,1);
 assert.equal(timing.stages.cppGetter.calls,expected.getters);assert.equal(timing.stages.outputCopy.calls,expected.getters+1);
 const sum=stages.reduce((total,name)=>total+timing.stages[name].elapsedMs,0);assert.equal(timing.unassignedMs,timing.elapsedMs-sum);assert.ok(Number.isFinite(timing.unassignedMs)&&timing.unassignedMs>=0);
}
function summary(trials){
 const measured=trials.filter(trial=>trial.phase==='measure');return Object.fromEntries(paths.map(key=>[key,{elapsed:profileStatistics(measured.map(trial=>trial.outcomes[key].timing.elapsedMs)),...(key.endsWith('Instrumented')?{stages:Object.fromEntries(stages.map(stage=>[stage,profileStatistics(measured.map(trial=>trial.outcomes[key].timing.stages[stage].elapsedMs))])),unassigned:profileStatistics(measured.map(trial=>trial.outcomes[key].timing.unassignedMs))}:{})}]));
}
async function run(options,argv){
 const runDirectory=await outputDirectory(options.output),start=performance.now();let retainedBytes=0,queryCount=0,totalComparedNumericValues=0,currentAttempt=null;const files=[],recent=new Map();
 const deadline=()=>{if(performance.now()-start>DEADLINE_MS)throw new Error('30-second cooperative run deadline exceeded; launch under a separate 30-second process watchdog to bound a synchronous WASM call');};
 async function retain(name,value,raw=false){const bytes=Buffer.from(raw?value:signedJSON(value)+'\n');if(retainedBytes+bytes.length>MAX_BYTES-65536)throw new Error('Readback output budget exceeded');await writeFile(path.join(runDirectory,name),bytes,{flag:'wx'});retainedBytes+=bytes.length;const entry={path:name,bytes:bytes.length,sha256:sha(bytes)};files.push(entry);return entry;}
 try{
  await retain('command.json',{command:[process.execPath,...process.execArgv,fileURLToPath(import.meta.url),...argv],cwd:process.cwd(),options,maxQueries:MAX_QUERIES,maxOutputBytes:MAX_BYTES,cooperativeDeadlineMs:DEADLINE_MS,externalWatchdogRequired:true});
  const env=await environment();await retain('environment.json',env);const wasmBytes=await readFile(path.join(ROOT,'assets/pikapika-simulation.wasm')),runtimes={},guards={},profilers={},startup={};
  // Runtime loading caches by the byte object's identity. Each clone therefore
  // intentionally has a different object identity, while retaining identical
  // WASM bytes; otherwise four labels would silently share one module.
  for(const key of paths){deadline();const independentBytes=Uint8Array.from(wasmBytes);assert.equal(sha(independentBytes),sha(wasmBytes));const begin=performance.now();runtimes[key]=await loadSimulationRuntime({wasmBytes:independentBytes});startup[key]=performance.now()-begin;guards[key]=identities(runtimes[key]);if(typeof runtimes[key].native._pp_sim_derived_mesh_records!=='function')throw new Error('This SDK lacks pp_sim_derived_mesh_records; explicit batch comparison cannot run and will not fall back to single');}
  assert.equal(new Set(paths.map(key=>runtimes[key].native)).size,4,'Separate actual WASM modules are required');
  for(const key of paths.filter(key=>key.endsWith('Instrumented')))profilers[key]=createDerivedMeshProfiler(runtimes[key]);
  const setup=createDerivedGPUProfileCases(runtimes.singleBaseline),sourceFile=await retain('author-source.json',setup.sourcePreparation.authorSourceBefore,true),prep={...setup.sourcePreparation,sourceFile};delete prep.authorSourceBefore;delete prep.authorSourceAfter;
  await retain('case-inputs.json',{schema:1,cases:setup.cases,sourcePreparation:prep});const cases=[],owned=[];
  const invariant=()=>{for(const key of paths)guards[key].check();setup.verifySourceUnchanged();for(const previous of owned)assert.deepEqual(hashProfileDTO(previous.result),previous.hash,'A previously returned owned DTO changed after another query');};
  for(const item of setup.cases){
   const before=hashProfileDTO({input:item.input,settings:item.settings}),trials=[];let initialSnapshot=null,initialHash=null;
   for(let pair=0;pair<phases.length;++pair){
    const order=pair%2===0?[...paths]:[...paths].reverse(),outcomes={},dto={};
    for(const key of order){
     deadline();assert.ok(++queryCount<=MAX_QUERIES);const mode=key.startsWith('single')?'single':'batch',settings={...item.settings,readback:mode};let result=null,error=null,clockError=null,timing=null;
     if(key.endsWith('Instrumented'))({result,error,clockError,timing}=profilers[key].prepare(item.input,settings));
     else{const begin=performance.now();try{result=runtimes[key].prepareDerivedMesh(item.input,settings);}catch(cause){error=cause;}const elapsedMs=performance.now()-begin;if(!Number.isFinite(elapsedMs)||elapsedMs<0)clockError=new Error('Invalid baseline clock');else timing={elapsedMs};}
     outcomes[key]={mode,instrumented:key.endsWith('Instrumented'),error:error?errorData(error):null,clockError:clockError?errorData(clockError):null,timing,resultHash:result?hashProfileDTO(result):null};dto[key]=result;recent.set(key,result);currentAttempt={case:item.name,phase:phases[pair],pair,order,outcomes};
     if(error||clockError){await retain(item.name+'-pair-'+pair+'-failed.json',{phase:phases[pair],pair,order,outcomes});throw error??clockError;}
     assert.equal(result.status,'completed');assert.ok(result.geometry);if(key.endsWith('Instrumented'))validateTiming(timing,result,mode);
     assert.deepEqual(hashProfileDTO({input:item.input,settings:item.settings}),before,'Input/settings changed');assert.deepEqual(settings,{...item.settings,readback:mode},'Settings changed');invariant();
    }
    const expected=outcomes.singleBaseline.resultHash;if(pair===0)initialHash=expected;else assert.deepEqual(expected,initialHash,'The same unchanged case produced a different DTO in a later pair');for(const key of paths.slice(1)){assert.deepStrictEqual(dto[key],dto.singleBaseline,'Full four-path DTO mismatch');assert.deepEqual(outcomes[key].resultHash,expected,'Typed/ordered/bits exact hash mismatch');}
    // Three independent equality comparisons against singleBaseline per pair.
    const comparedNumericValues=3*(expected.counts.numbers+expected.counts.typedElements);totalComparedNumericValues+=comparedNumericValues;
    const trial={phase:phases[pair],pair,order,outcomes,comparedNumericValues};trials.push(trial);await retain(item.name+'-pair-'+pair+'.json',trial);
    if(pair===0){initialSnapshot=await retain(item.name+'-initial.json',{encoding:'tagged-exact-v1',...Object.fromEntries(paths.map(key=>[key,exactReadbackDTO(dto[key])]))});for(const key of paths)owned.push({result:dto[key],hash:outcomes[key].resultHash});}
    invariant();
   }
   cases.push({name:item.name,recipe:item.recipe,vertices:item.input.positions.length,triangles:item.input.triangles.length,settings:item.settings,inputHash:before,initialSnapshot,trials,measureSummary:summary(trials)});
  }
  invariant();assert.equal(queryCount,MAX_QUERIES);deadline();
  const otherHashes=new Map([...recent].map(([key,value])=>[key,hashProfileDTO(value)])),old=owned[0].result.geometry.positions[0],saved=old[0];
  try{old[0]=saved+1;assert.notEqual(old[0],saved);for(const [key,value]of recent)assert.deepEqual(hashProfileDTO(value),otherHashes.get(key),'Mutating a previous owned DTO changed a later result');setup.verifySourceUnchanged();for(const item of setup.cases)assert.deepEqual(hashProfileDTO({input:item.input,settings:item.settings}),cases.find(record=>record.name===item.name).inputHash,'DTO mutation changed an input');}finally{old[0]=saved;}
  invariant();const finalEnvironment=await environment();assert.deepEqual(finalEnvironment,env,'SDK/authored source or environment changed during the run');
  const report={schema:1,status:'PASS',runDirectory,queryCount,totalComparedNumericValues,phases,startupMs:startup,sourcePreparation:prep,cases,files:[...files],nativeExports:Object.fromEntries(paths.map(key=>[key,guards[key].exportNames])),nativeExportsUnchanged:true,runtimeMethodsUnchanged:true,prototypeUnchanged:true,separateNativeModules:4,sourceUnchanged:true,inputsUnchanged:true,ownedSnapshotsUnchanged:owned.length,oldDTOMutationSeparatedFromLaterDTOsAndInputs:true,retainedBytesBeforeReport:retainedBytes,elapsedIncludingVerificationMs:performance.now()-start,
   scope:'Node only. No GPU, Native executable, real-time animation, general FPS or kernel-only time measured. No performance adoption decision is made by this tool.',
   timingContract:'Clock failures are explicit failures. Instrumentation is uncalibrated. cppQuery includes ABI/core/snapshot commit; cppGetter includes ABI packet copy; outputCopy is JS output() only. unassignedMs is the direct residual, not pure JavaScript or C++ time. Medians of separate stages are not additive.',
   orderPolicy:'Four separate actual modules of the same SDK. initial/warmup/three measure pairs, path order alternates forward/reverse. No queries added for ownership; initial DTO hashes are rechecked after later queries. Verification/file writes outside timed calls can perturb later measurements.',
   statisticsPolicy:'Only three measure samples; initial and warmup remain raw. Median, nearest-rank p95 and maximum are retained for each path and each instrumented stage. No filtering.',
   retention:'Every pair compares full DTOs and exact typed/ordered/binary64-bit hashes across all four paths. First pair full DTOs and every subsequent digest/count/timing retained. Source/inputs retain signed zero. Native export, method, prototype and all SDK source/notice/artifact bytes checked before/after.'};
  await retain('report.json',report);console.log(JSON.stringify({status:'PASS',runDirectory,queryCount,totalComparedNumericValues,retainedBytes},null,2));
 }catch(error){const bytes=Buffer.from(JSON.stringify({status:'FAIL',runDirectory,queryCount,elapsedMs:performance.now()-start,error:errorData(error),currentAttempt})+'\n');if(retainedBytes+bytes.length<=MAX_BYTES)await writeFile(path.join(runDirectory,'failure.json'),bytes,{flag:'wx'});console.error(JSON.stringify({status:'FAIL',runDirectory,error:errorData(error)}));throw error;}
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){try{const options=parseReadbackArgs(process.argv.slice(2));if(options.help)console.log(usage);else await run(options,process.argv.slice(2));}catch(error){console.error(error.message);process.exitCode=1;}}
