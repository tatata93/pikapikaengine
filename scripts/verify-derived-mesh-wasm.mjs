import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseSkinBindingPortable,serializeSkinBindingPortable,serializeSkinBindingSource,evaluateSkinBinding} from '../engine/skin-binding.mjs';
import {parseStrictJson} from '../engine/strict-json.mjs';

const [nativeFile,reportFile,outputFile,replayFile,probeFile]=process.argv.slice(2);
if(![nativeFile,reportFile,outputFile,replayFile].every(Boolean))throw new Error('Usage: node scripts/verify-derived-mesh-wasm.mjs native-fixtures.json report.json outputs.json wasm-fixtures.json [native-source-probes.json]');
const python=process.env.PIKAPIKA_PYTHON??(process.platform==='win32'?'python':'python3');
const checker=fileURLToPath(new URL('./verify-derived-mesh.py',import.meta.url));
const reference=(path,backend)=>JSON.parse(execFileSync(python,[checker,path,'--backend',backend],{encoding:'utf8',windowsHide:true,timeout:30000,maxBuffer:4*1024*1024}));
const nativeReference=reference(nativeFile,'native');
const nativeText=await readFile(nativeFile,'utf8'),source=JSON.parse(nativeText.replace(/^\uFEFF/,''));
const wasmBytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes});
const statuses=['completed','invalid_input','budget_exceeded','degenerate','quality_rejected','quality_unresolved','numerical_failure','unsupported_environment'];
const reasons=['none','settings','vertex_count','triangle_count','position_domain','index_range','duplicate_index','vertex_budget','triangle_budget','zero_cross','below_area_floor','cross_uncertain','area_uncertain','normal_uncertain','nonfinite_intermediate','allocation_failure','environment'];
const f32Bits=values=>Array.from(new Uint32Array(values.buffer,values.byteOffset,values.length));
const view=new DataView(new ArrayBuffer(8));
const bits=n=>{assert.ok(Number.isFinite(n));view.setFloat64(0,n);return view.getBigUint64(0).toString(16).padStart(16,'0');};
const hexTree=x=>typeof x==='number'?bits(x):Array.isArray(x)?x.map(hexTree):x&&typeof x==='object'?Object.fromEntries(Object.entries(x).map(([k,v])=>[k,hexTree(v)])):x;
function signedJSON(x){
 if(typeof x==='number'){assert.ok(Number.isFinite(x));return Object.is(x,-0)?'-0':JSON.stringify(x);}
 if(ArrayBuffer.isView(x))return signedJSON(Array.from(x));
 if(Array.isArray(x))return '['+x.map(signedJSON).join(',')+']';
 if(x&&typeof x==='object')return '{'+Object.entries(x).map(([k,v])=>JSON.stringify(k)+':'+signedJSON(v)).join(',')+'}';
 return JSON.stringify(x);
}
function project(r){
 const g=r.geometry;
 return {status:statuses.indexOf(r.status),reason:reasons.indexOf(r.reason),failedVertex:r.failedVertex,failedFace:r.failedFace,
  positionsBits:g?g.positions.map(f32Bits):null,triangles:g?g.triangles.map(t=>Array.from(t)):null,
  interleavedBits:g?f32Bits(g.interleaved):null,minimumBits:g?f32Bits(g.minimum):null,maximumBits:g?f32Bits(g.maximum):null,
  audits:r.audits.map(a=>({face:a.face,cross:a.cross,squaredCross:a.squaredCross,normalized:a.normalized,normalBits:a.normal?f32Bits(a.normal):null,normalError:a.normalError,sqrtRefinements:a.sqrtRefinements,sqrtRefinementLimited:a.sqrtRefinementLimited})),
  sqrtRefinements:r.sqrtRefinements,sqrtLimitedFaces:r.sqrtLimitedFaces};
}
let numericComparisons=0,completed=0,failures=0;
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);++numericComparisons;}
 else if(a&&typeof a==='object'){assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}
 else assert.equal(a,b,label);
}
const replay=[],outputs=[];
for(const fixture of source.fixtures){
 const q=fixture.input,before=signedJSON(q);
 const result=runtime.prepareDerivedMesh(q,{maxVertices:q.settings[0],maxTriangles:q.settings[1],sqrtRefinements:q.settings[2]});
 assert.equal(signedJSON(q),before,'source input unchanged');
 const actual=project(result);compare(actual,fixture.result,fixture.name);
 replay.push({name:fixture.name,input:q,result:actual});
 outputs.push({name:fixture.name,classification:'actual C++ WebAssembly model result',input:q,result,projected:actual,binary64:hexTree(actual)});
 if(result.status==='completed')++completed;else ++failures;
}
assert.equal(replay.length,40);assert.equal(completed,16);assert.equal(failures,24);
const fixtureNumericComparisons=numericComparisons;
// All result fields here come from the main WASM query. Native results are
// compared above, never copied into this replay or used as a fallback.
await writeFile(replayFile,signedJSON({schema:1,fixtures:replay})+'\n',{flag:'wx'});
const wasmReference=reference(replayFile,'main-wasm');
const probeOutputs=[];let probeNumericComparisons=0,probeInputSHA256=null,probeNativeSHA256=null;
if(probeFile){
 const probeText=await readFile(probeFile,'utf8'),nativeProbes=parseStrictJson(probeText);
 probeNativeSHA256=createHash('sha256').update(probeText).digest('hex');
 const names=['default-t0','default-t0.5','default-t1','default-t2','default-loop-t3','actual-lbs-half-turn-collapse','derived-face-budget','derived-normal-budget','source-weight-underflow','source-inverse-quality','source-stale-rest'];
 assert.equal(nativeProbes.schema,1);assert.deepEqual(nativeProbes.fixtures.map(f=>f.name),names);
 const inputPacket=nativeProbes.fixtures.map(f=>({name:f.name,input:{source:serializeSkinBindingSource(parseSkinBindingPortable(f.input.portable)),seconds:f.input.seconds,loop:f.input.loop,settings:f.input.settings}}));
 probeInputSHA256=createHash('sha256').update(JSON.stringify(inputPacket)).digest('hex');
 assert.equal(probeInputSHA256,'ad5b677a30500e73fef7979abdee88a87c52b02f859eec432e8dd4329e450ee7','fixed authored Source probe inputs');
 const beforeCount=numericComparisons;
 for(const fixture of nativeProbes.fixtures){
  assert.equal(fixture.sourceSavedUnchanged,true,fixture.name+': Native authorship');
  const q=fixture.input;let owned,state,sourceError=null,sourceBefore=null,sourceAfter=null;
  try{owned=parseSkinBindingPortable(q.portable);sourceBefore=serializeSkinBindingPortable(owned);state=evaluateSkinBinding(runtime,owned,q.seconds,{loop:q.loop});}
  catch(error){sourceError=String(error.message);}
  if(owned){sourceAfter=serializeSkinBindingPortable(owned);assert.equal(sourceAfter,sourceBefore,fixture.name+': Web authorship');}
  assert.equal(sourceError!==null,fixture.sourceError!==null,fixture.name+': source failure stage');
  let deformation=null,derivedInput=null,derived=null;
  if(state){const d=state.deformation;deformation={status:['completed','invalid_input','budget_exceeded','ill_conditioned','numerical_failure'].indexOf(d.status),positions:d.positions,diagnostics:d.diagnostics,weightResiduals:d.weightResiduals};
   if(d.status==='completed'){derivedInput={positions:d.positions,triangles:owned.mesh.triangles,settings:q.settings};derived=project(runtime.prepareDerivedMesh(derivedInput,{maxVertices:q.settings[0],maxTriangles:q.settings[1],sqrtRefinements:q.settings[2]}));}
  }
  compare(deformation,fixture.deformation,fixture.name+'.deformation');compare(derivedInput,fixture.derivedInput,fixture.name+'.derivedInput');compare(derived,fixture.derived,fixture.name+'.derived');
  probeOutputs.push({name:fixture.name,input:q,sourceError,sourceBefore,sourceAfter,deformation,derivedInput,derived,binary64:hexTree({deformation,derivedInput,derived})});
 }
 probeNumericComparisons=numericComparisons-beforeCount;
}
await writeFile(outputFile,signedJSON({schema:1,classification:'main WASM actual results',outputs,probeOutputs})+'\n',{flag:'wx'});
const manifest=JSON.parse(await readFile(new URL('../assets/pikapika-simulation.build.json',import.meta.url),'utf8'));
const files=[];for(const url of [new URL('../engine/simulation.mjs',import.meta.url),new URL(import.meta.url),new URL('./verify-derived-mesh.py',import.meta.url),new URL('../engine/skin-binding.mjs',import.meta.url),new URL('../engine/motion.mjs',import.meta.url),new URL('../engine/strict-json.mjs',import.meta.url)]){const data=await readFile(url);files.push({path:fileURLToPath(url),bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')});}
const report={status:'PASS',modelFixtures:40,completed,expectedFailures:failures,hostClassifications:0,numericComparisons,fixtureNumericComparisons,sourceProbeCases:probeOutputs.length,probeNumericComparisons,probeInputSHA256,probeNativeSHA256,nativeReference,wasmReference,
 nativeSHA256:createHash('sha256').update(nativeText).digest('hex'),wasmSHA256:createHash('sha256').update(wasmBytes).digest('hex'),wasmBytes:wasmBytes.length,manifest,files,
 scope:'Fixed 40 local-mesh cases; actual main WASM only. Expected model failures are not valid geometry. No GPU/world-space proof or performance claim.'};
await writeFile(reportFile,signedJSON(report)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));
