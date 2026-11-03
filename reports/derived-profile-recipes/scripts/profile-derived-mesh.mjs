import assert from 'node:assert/strict';
import {createHash,randomBytes} from 'node:crypto';
import {readFile,writeFile,mkdir,lstat,realpath} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createDerivedMeshRenderData} from '../engine/derived-render.mjs';
import {createDerivedProfileCases} from './derived-profile-cases.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const stageNames=['f64Exchange','u32Exchange','cppQuery','cppGetter','outputCopy'];
const MAX_QUERIES=260,MAX_OUTPUT_BYTES=10*1024*1024;
const usage='Usage: node scripts/profile-derived-mesh.mjs --output build/derived-profile[-label] [--quick] [--repeats 1..9] [--warmup 0..3]';
export function parseProfileArgs(argv){
 if(argv.length===1&&argv[0]==='--help')return {help:true};
 const result={quick:false,repeats:3,warmup:1,output:null},seen=new Set();
 for(let j=0;j<argv.length;++j){const key=argv[j];if(!['--output','--quick','--repeats','--warmup'].includes(key))throw new Error('Unknown argument: '+key);
  if(seen.has(key))throw new Error('Duplicate argument: '+key);seen.add(key);
  if(key==='--quick'){result.quick=true;continue;}
  const value=argv[++j];if(value===undefined||value.startsWith('--'))throw new Error('Missing value for '+key);
  if(key==='--output'){result.output=value;continue;}
  if(!/^(0|[1-9][0-9]*)$/.test(value))throw new Error('Integer value required for '+key);
  const n=Number(value),min=key==='--repeats'?1:0,max=key==='--repeats'?9:3;
  if(!Number.isSafeInteger(n)||n<min||n>max)throw new Error('Out of range '+key);result[key.slice(2)]=n;
 }
 if(!result.output)throw new Error('--output is required');
 result.totalQueries=(result.quick?8:10)*2*(1+result.warmup+result.repeats);
 if(result.totalQueries>MAX_QUERIES)throw new Error('Total query budget exceeded');return result;
}
function signedJSON(x){
 if(typeof x==='number'){if(!Number.isFinite(x))throw new Error('Cannot retain nonfinite report number');return Object.is(x,-0)?'-0':JSON.stringify(x);}
 if(Array.isArray(x))return '['+Array.from(x,signedJSON).join(',')+']';
 if(x&&typeof x==='object')return '{'+Object.entries(x).map(([k,v])=>JSON.stringify(k)+':'+signedJSON(v)).join(',')+'}';
 if(x===null||typeof x==='string'||typeof x==='boolean')return JSON.stringify(x);
 throw new Error('Unsupported report value '+typeof x);
}
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const f64=new DataView(new ArrayBuffer(8));
function numberBits(x){assert.ok(Number.isFinite(x));f64.setFloat64(0,x);return f64.getBigUint64(0).toString(16).padStart(16,'0');}
// Original, self-delimiting typed encoding. It retains ordered object keys,
// binary64 signs/payload bits and the exact host-endian bytes of typed arrays.
export function hashProfileDTO(value){
 const h=createHash('sha256');let pending='',counts={numbers:0,typedArrays:0,typedElements:0,typedBytes:0,arrays:0,objects:0,keys:0};
 const flush=()=>{if(pending){h.update(pending);pending='';}};
 const text=s=>{pending+=s;if(pending.length>=32768)flush();};
 function walk(x){
  if(x===null){text('z;');return;}
  if(typeof x==='number'){++counts.numbers;text('n'+numberBits(x)+';');return;}
  if(typeof x==='string'){text('s'+Buffer.byteLength(x)+':'+x);return;}
  if(typeof x==='boolean'){text(x?'b1;':'b0;');return;}
  if(ArrayBuffer.isView(x)&&!(x instanceof DataView)){const bytes=Buffer.from(x.buffer,x.byteOffset,x.byteLength);++counts.typedArrays;counts.typedElements+=x.length;counts.typedBytes+=bytes.length;text('t'+x.constructor.name+':'+x.length+':'+bytes.length+':');flush();h.update(bytes);return;}
  if(Array.isArray(x)){++counts.arrays;text('a'+x.length+':');for(let j=0;j<x.length;++j){assert.ok(j in x,'Sparse DTO array');walk(x[j]);}return;}
  if(typeof x==='object'){const keys=Object.keys(x);++counts.objects;counts.keys+=keys.length;text('o'+keys.length+':');for(const key of keys){walk(key);walk(x[key]);}return;}
  throw new Error('Unsupported DTO value '+typeof x);
 }
 walk(value);flush();return {sha256:h.digest('hex'),counts};
}
function exactDTO(x){
 if(x===null)return {type:'null'};
 if(typeof x==='number')return {type:'number',bits:numberBits(x)};
 if(ArrayBuffer.isView(x))return {type:x.constructor.name,length:x.length,bytesHex:Buffer.from(x.buffer,x.byteOffset,x.byteLength).toString('hex')};
 if(Array.isArray(x))return {type:'Array',items:x.map(exactDTO)};
 if(typeof x==='object')return {type:'Object',entries:Object.entries(x).map(([k,v])=>[k,exactDTO(v)])};
 return {type:typeof x,value:x};
}
function preview(result){
 if(result===null)return null;
 const g=result.geometry,indices=n=>Array.from(new Set([...Array.from({length:Math.min(3,n)},(_,j)=>j),...Array.from({length:Math.min(3,n)},(_,j)=>n-Math.min(3,n)+j)]));
 return {status:result.status,reason:result.reason,failedVertex:result.failedVertex,failedFace:result.failedFace,sqrtRefinements:result.sqrtRefinements,sqrtLimitedFaces:result.sqrtLimitedFaces,
  geometry:g?{vertices:g.positions.length,triangles:g.triangles.length,floats:g.interleaved.length,minimum:exactDTO(g.minimum),maximum:exactDTO(g.maximum),positions:indices(g.positions.length).map(j=>({index:j,data:exactDTO(g.positions[j])})),faces:indices(g.triangles.length).map(j=>({index:j,triangle:exactDTO(g.triangles[j]),interleaved:exactDTO(g.interleaved.slice(j*18,(j+1)*18))}))}:null,
  auditCount:result.audits.length,audits:indices(result.audits.length).map(j=>({index:j,data:exactDTO(result.audits[j])})),scope:'Explicit first/tail diagnostic preview only; never a partial successful render buffer.'};
}
const errorData=e=>e?{name:e.name??'Error',message:e.message??String(e),code:e.code??null,stack:e.stack??null}:null;
function accept(outcome,expectation,name){
 assert.equal(outcome.clockError,null,name+': clock failure is not a model/host result');
 if(expectation.kind==='host_rejection'){assert.ok(outcome.error instanceof Error,name+': explicit host rejection required');assert.equal(outcome.result,null);return;}
 assert.equal(outcome.error,null,name+': unexpected query error');assert.equal(outcome.result.status,expectation.status,name);assert.equal(outcome.result.reason,expectation.reason,name);
 if(expectation.kind!=='completed')assert.equal(outcome.result.geometry,null,name+': failure must not expose geometry');
}
function validateTiming(t,result,expectation){
 assert.ok(t&&Number.isFinite(t.elapsedMs)&&t.elapsedMs>=0&&Number.isFinite(t.unassignedMs)&&t.unassignedMs>=0,'Valid profiling clock required');
 assert.deepEqual(Object.keys(t.stages),stageNames);
 for(const s of Object.values(t.stages)){assert.ok(Number.isSafeInteger(s.calls)&&s.calls>=0);assert.ok(Number.isFinite(s.elapsedMs)&&s.elapsedMs>=0);}
 assert.equal(t.getterKinds.length,4);assert.ok(t.getterKinds.every(n=>Number.isSafeInteger(n)&&n>=0));
 const sum=stageNames.reduce((total,name)=>total+t.stages[name].elapsedMs,0);assert.ok(sum<=t.elapsedMs,'Stages must not exceed total elapsed');assert.equal(t.unassignedMs,t.elapsedMs-sum,'Residual must equal the directly defined subtraction');
 if(expectation.kind==='host_rejection'){
  assert.deepEqual(t.getterKinds,[0,0,0,0]);for(const stage of Object.values(t.stages)){assert.equal(stage.calls,0);assert.equal(stage.elapsedMs,0);}return;
 }
 const g=result.geometry,kinds=[g?g.positions.length:0,g?g.triangles.length:0,g?g.triangles.length:0,result.audits.length],getters=kinds.reduce((a,b)=>a+b,0);
 assert.deepEqual(t.getterKinds,kinds,'Getter kind counts must describe this complete result');
 for(const name of ['f64Exchange','u32Exchange','cppQuery'])assert.equal(t.stages[name].calls,1);
 assert.equal(t.stages.cppGetter.calls,getters);assert.equal(t.stages.outputCopy.calls,1+getters);
}
export function profileStatistics(values){
 assert.ok(values.length>0);assert.ok(values.every(x=>Number.isFinite(x)&&x>=0));
 const sorted=[...values].sort((a,b)=>a-b),n=sorted.length,mid=Math.floor(n/2);
 return {samples:n,medianMs:n%2?sorted[mid]:sorted[mid-1]/2+sorted[mid]/2,p95Ms:sorted[Math.ceil(.95*n)-1],maxMs:sorted.at(-1)};
}
function measuredSummary(trials,expectation){
 const samples=trials.filter(t=>t.phase==='measure'),factory=kind=>expectation.kind==='completed'?profileStatistics(samples.map(t=>t[kind].renderDataFactory.elapsedMs)):null;
 return {classification:expectation,sampleCount:samples.length,baseline:{elapsed:profileStatistics(samples.map(t=>t.baseline.timing.elapsedMs)),renderDataFactory:factory('baseline')},
  instrumented:{elapsed:profileStatistics(samples.map(t=>t.instrumented.timing.elapsedMs)),stages:Object.fromEntries(stageNames.map(name=>[name,profileStatistics(samples.map(t=>t.instrumented.timing.stages[name].elapsedMs))])),unassigned:profileStatistics(samples.map(t=>t.instrumented.timing.unassignedMs)),renderDataFactory:factory('instrumented')},
  policy:'Measure phase only. Initial and warmup samples remain raw and are excluded here. Expected model failures and host rejections remain separate labelled cases; their render factory was not run. p95 uses nearest rank ceil(.95*N), median averages the middle pair when N is even.'};
}
async function outputDirectory(value){
 const base=path.resolve(value),build=path.join(ROOT,'build'),relative=path.relative(build,base);
 if(path.dirname(base)!==path.resolve(build)||!/^derived-profile[A-Za-z0-9_-]*$/.test(relative))throw new Error('Output must be a direct build/derived-profile[-label] directory');
 await mkdir(build,{recursive:true});if(await realpath(build)!==path.resolve(build))throw new Error('Symlinked build directory is not supported');
 try{const stat=await lstat(base);if(stat.isSymbolicLink()||!stat.isDirectory())throw new Error('Output root must be a real directory');}catch(error){if(error.code!=='ENOENT')throw error;await mkdir(base);}
 const run=path.join(base,'run-'+new Date().toISOString().replace(/[^0-9]/g,'')+'-'+randomBytes(5).toString('hex'));await mkdir(run);return run;
}
async function environment(){
 const manifestPath=path.join(ROOT,'assets/pikapika-simulation.build.json'),manifestBytes=await readFile(manifestPath),manifest=JSON.parse(manifestBytes),files=[];
 for(const [name,expected] of Object.entries(manifest.sourceSha256)){const data=await readFile(path.join(ROOT,name)),actual=sha(data);assert.equal(actual,expected,'SDK source hash '+name);files.push({path:name,bytes:data.length,sha256:actual});}
 const artifacts=[];for(const [name,expected] of Object.entries(manifest.artifacts)){const bytes=await readFile(path.join(ROOT,name));assert.equal(sha(bytes),expected.sha256,name);assert.equal(bytes.length,expected.bytes,name);artifacts.push({path:name,...expected});}
 const notices=[];for(const [name,expected] of Object.entries(manifest.licenses)){const bytes=await readFile(path.join(ROOT,name));assert.equal(sha(bytes),expected,name);notices.push({path:name,bytes:bytes.length,sha256:expected});}
 const authored=[];for(const name of ['scripts/profile-derived-mesh.mjs','scripts/derived-profile-cases.mjs','tools/derived-profile.mjs','engine/simulation.mjs','engine/derived-render.mjs','engine/skin-binding.mjs','engine/motion.mjs','engine/strict-json.mjs']){const bytes=await readFile(path.join(ROOT,name));authored.push({path:name,bytes:bytes.length,sha256:sha(bytes)});}
 return {node:process.version,versions:process.versions,platform:process.platform,arch:process.arch,osRelease:os.release(),endianness:os.endianness(),cpuModel:os.cpus()[0]?.model??null,logicalCPUs:os.cpus().length,
  sdkManifest:manifest,sdkManifestSHA256:sha(manifestBytes),sdkSourceHashes:files,sdkArtifacts:artifacts,runtimeNotices:notices,authoredSourceHashes:authored};
}
async function runDerivedMeshProfile(options,{argv=[]}={}){
 const runDirectory=await outputDirectory(options.output),runStart=performance.now();let retainedBytes=0;
 async function retain(name,value,raw=false){const bytes=Buffer.from(raw?value:signedJSON(value)+'\n');if(retainedBytes+bytes.length>MAX_OUTPUT_BYTES)throw new Error('Profile output byte budget exceeded');await writeFile(path.join(runDirectory,name),bytes,{flag:'wx'});retainedBytes+=bytes.length;return {path:name,bytes:bytes.length,sha256:sha(bytes)};}
 try{
  const env=await environment(),command=[process.execPath,...process.execArgv,fileURLToPath(import.meta.url),...argv];
  await retain('environment.json',env);await retain('command.json',{command,cwd:process.cwd(),options,maxQueries:MAX_QUERIES,maxOutputBytes:MAX_OUTPUT_BYTES});
  const bytes=await readFile(path.join(ROOT,'assets/pikapika-simulation.wasm')),start=performance.now(),runtime=await loadSimulationRuntime({wasmBytes:bytes}),startupMs=performance.now()-start;
  const originalNative=runtime.native,exports=new Map(Object.entries(originalNative).filter(([key,value])=>key.startsWith('_pp_sim_')&&typeof value==='function'));
  const methods=new Map(['prepareDerivedMesh','inputF64','inputU32','output','check'].map(key=>[key,runtime[key]]));
  const unchanged=()=>{assert.equal(runtime.native,originalNative);for(const [key,value] of exports)assert.equal(originalNative[key],value,'Native export mutated '+key);for(const [key,value] of methods)assert.equal(runtime[key],value,'Runtime method mutated '+key);};
  const setup=createDerivedProfileCases(runtime,{quick:options.quick});unchanged();
  const sourceFile=await retain('author-source.json',setup.sourcePreparation.authorSourceBefore,true);
  const prep={...setup.sourcePreparation,sourceFile};delete prep.authorSourceBefore;delete prep.authorSourceAfter;
  const inputFile=await retain('case-inputs.json',{schema:1,cases:setup.cases,sourcePreparation:prep});
  const {createDerivedMeshProfiler}=await import('../tools/derived-profile.mjs');const profiler=createDerivedMeshProfiler(runtime);unchanged();
  const cases=[];let queryCount=0,totalComparedBits=0;
  for(const item of setup.cases){
   const inputSnapshot=structuredClone(item.input),settingsSnapshot=structuredClone(item.settings),trials=[];let initialPair=null;
   const phases=['initial',...Array(options.warmup).fill('warmup'),...Array(options.repeats).fill('measure')];
   for(let pair=0;pair<phases.length;++pair){
    const order=pair%2===0?['baseline','instrumented']:['instrumented','baseline'],outcomes={},records={};
    for(const kind of order){
     ++queryCount;assert.ok(queryCount<=MAX_QUERIES);let outcome;
     if(kind==='baseline'){let result=null,error=null;const start=performance.now();try{result=runtime.prepareDerivedMesh(item.input,item.settings);}catch(cause){error=cause;}outcome={result,error,clockError:null,timing:{elapsedMs:performance.now()-start}};}
     else outcome=profiler.prepare(item.input,item.settings);
     accept(outcome,item.expectation,item.name);
     if(kind==='instrumented')validateTiming(outcome.timing,outcome.result,item.expectation);else assert.ok(Number.isFinite(outcome.timing.elapsedMs)&&outcome.timing.elapsedMs>=0,'Valid baseline clock required');
     assert.deepStrictEqual(item.input,inputSnapshot,'Source positions/triangles changed');assert.deepStrictEqual(item.settings,settingsSnapshot);unchanged();
     const verifyStart=performance.now(),hash=hashProfileDTO(outcome.result);let factory=null;
     if(outcome.result?.status==='completed'){const begin=performance.now(),token=createDerivedMeshRenderData(outcome.result),elapsedMs=performance.now()-begin;factory={calls:1,elapsedMs,metadata:{...token}};assert.deepEqual(hashProfileDTO(outcome.result),hash,'Render factory changed the result');}
     outcomes[kind]=outcome;records[kind]={resultHash:hash,error:errorData(outcome.error),clockError:null,timing:outcome.timing,renderDataFactory:factory,verificationAndFactoryMs:performance.now()-verifyStart};
    }
    const compareStart=performance.now();assert.deepStrictEqual(outcomes.baseline.result,outcomes.instrumented.result,item.name+': full result DTO mismatch');
    assert.equal(Boolean(outcomes.baseline.error),Boolean(outcomes.instrumented.error));
    if(outcomes.baseline.error){assert.equal(outcomes.baseline.error.name,outcomes.instrumented.error.name);assert.equal(outcomes.baseline.error.message,outcomes.instrumented.error.message);assert.equal(outcomes.baseline.error.code,outcomes.instrumented.error.code);}
    assert.deepEqual(records.baseline.resultHash,records.instrumented.resultHash,item.name+': exact typed hash mismatch');
    const comparedBits=records.baseline.resultHash.counts.numbers+records.baseline.resultHash.counts.typedElements;totalComparedBits+=comparedBits;
    trials.push({phase:phases[pair],pair,order,baseline:records.baseline,instrumented:records.instrumented,comparedNumericValues:comparedBits,fullDTOComparisonMs:performance.now()-compareStart});
    if(pair===0)initialPair=item.input.triangles.length<=512?{encoding:'tagged-exact-v1',baseline:exactDTO(outcomes.baseline.result),instrumented:exactDTO(outcomes.instrumented.result)}:{encoding:'first-tail-preview-v1',baseline:preview(outcomes.baseline.result),instrumented:preview(outcomes.instrumented.result)};
   }
   const snapshotFile=await retain(item.name+'-initial.json',initialPair);cases.push({name:item.name,recipe:item.recipe,expectation:item.expectation,vertices:item.input.positions.length,triangles:item.input.triangles.length,inputHash:hashProfileDTO({input:item.input,settings:item.settings}),initialSnapshot:snapshotFile,trials,measureSummary:measuredSummary(trials,item.expectation)});
  }
  setup.verifySourceUnchanged();unchanged();assert.equal(queryCount,options.totalQueries);
  const report={schema:1,status:'PASS',runDirectory,mode:options.quick?'quick':'standard',repeats:options.repeats,warmup:options.warmup,queryCount,totalComparedNumericValues:totalComparedBits,startupMs,runtime:runtime.diagnostics,nativeExportCount:exports.size,nativeExportsUnchanged:true,sourceUnchanged:true,inputFile,sourcePreparation:prep,cases,
   elapsedIncludingVerificationMs:performance.now()-runStart,retainedBytesBeforeReport:retainedBytes,
   scope:'Node only. No GPU upload/draw, Native executable, real-time animation or continuous performance guarantee measured.',
   timingContract:'Instrumentation overhead is uncalibrated. Baseline/instrumented differences do not identify pure stage costs. cppQuery includes ABI validation/core/commit; cppGetter includes ABI packet copy; outputCopy is JS output() only. unassignedMs includes encoding, decoding, validation, instrumentation and other residual work; it is not pure JavaScript time.',
   retention:'Every trial compared full DTOs with deepStrictEqual and typed/key/binary64-bit/typed-byte hashes. Only the first pair of cases <=512 faces is fully retained; large cases retain explicit first/tail diagnostic previews, never partial successful geometry. Warmups and all measurements are retained without filtering.',
   orderPolicy:'Each case begins with an uninstrumented first query then an instrumented query; subsequent paired order alternates. Hashing, comparison and factory work occurs outside query timing and can perturb later measurements.'};
  await retain('report.json',report);console.log(JSON.stringify({status:'PASS',runDirectory,queryCount,cases:cases.length,totalComparedNumericValues:totalComparedBits,retainedBytes},null,2));return report;
 }catch(error){await retain('failure.json',{status:'FAIL',error:errorData(error),runDirectory,elapsedMs:performance.now()-runStart});throw error;}
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
 try{const options=parseProfileArgs(process.argv.slice(2));if(options.help)console.log(usage);else await runDerivedMeshProfile(options,{argv:process.argv.slice(2)});}
 catch(error){console.error(error.message);process.exitCode=1;}
}
