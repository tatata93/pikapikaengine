// Original correctness replay for the observational profiler, not a benchmark.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createDerivedMeshProfiler} from '../tools/derived-profile.mjs';
import {parseSkinBindingPortable,serializeSkinBindingPortable,evaluateSkinBinding} from '../engine/skin-binding.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';

const [nativeFile,sourceFile,...extra]=process.argv.slice(2);
if(!nativeFile||!sourceFile||extra.length)throw new Error('Usage: node scripts/verify-derived-profile.mjs native40.json source11.json');
const root=fileURLToPath(new URL('../',import.meta.url));
const base=path.join(root,'build/derived-profile-verification');await mkdir(base,{recursive:true});
const out=await mkdtemp(path.join(base,'run-'));
const sha=b=>createHash('sha256').update(b).digest('hex');
const nativeRaw=await readFile(nativeFile),sourceRaw=await readFile(sourceFile);
const fixed=parseStrictJson(nativeRaw.toString('utf8')),sources=parseStrictJson(sourceRaw.toString('utf8'));
assert.equal(fixed.schema,1);assert.equal(fixed.fixtures.length,40);assert.equal(sources.schema,1);assert.equal(sources.fixtures.length,11);
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)),runtime=await loadSimulationRuntime({wasmBytes:wasm});
const originals={native:runtime.native,prepare:runtime.prepareDerivedMesh,query:runtime.native._pp_sim_derived_mesh,getter:runtime.native._pp_sim_derived_mesh_record};
const profiler=createDerivedMeshProfiler(runtime);
const statuses=['completed','invalid_input','budget_exceeded','degenerate','quality_rejected','quality_unresolved','numerical_failure','unsupported_environment'];
const reasons=['none','settings','vertex_count','triangle_count','position_domain','index_range','duplicate_index','vertex_budget','triangle_budget','zero_cross','below_area_floor','cross_uncertain','area_uncertain','normal_uncertain','nonfinite_intermediate','allocation_failure','environment'];
const f32Bits=v=>Array.from(new Uint32Array(v.buffer,v.byteOffset,v.length));
function project(r){const g=r.geometry;return {status:statuses.indexOf(r.status),reason:reasons.indexOf(r.reason),failedVertex:r.failedVertex,failedFace:r.failedFace,
 positionsBits:g?g.positions.map(f32Bits):null,triangles:g?g.triangles.map(t=>Array.from(t)):null,interleavedBits:g?f32Bits(g.interleaved):null,minimumBits:g?f32Bits(g.minimum):null,maximumBits:g?f32Bits(g.maximum):null,
 audits:r.audits.map(a=>({face:a.face,cross:a.cross,squaredCross:a.squaredCross,normalized:a.normalized,normalBits:a.normal?f32Bits(a.normal):null,normalError:a.normalError,sqrtRefinements:a.sqrtRefinements,sqrtRefinementLimited:a.sqrtRefinementLimited})),sqrtRefinements:r.sqrtRefinements,sqrtLimitedFaces:r.sqrtLimitedFaces};}
let numericComparisons=0;
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.ok(Number.isFinite(a)&&Number.isFinite(b));assert.ok(Object.is(a,b),label);++numericComparisons;}
 else if(a&&typeof a==='object'){assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const key of Object.keys(a))compare(a[key],b[key],label+'.'+key);}
 else assert.equal(a,b,label);
}
const timings=[],replay=[],sourceReplay=[];
function run(name,input,settings){
 const before=stringifyStrictJson(input),baseline=runtime.prepareDerivedMesh(input,settings),observed=profiler.prepare(input,settings);
 assert.equal(observed.error,null,name);assert.equal(observed.clockError,null,name);assert.ok(observed.timing,name);assert.deepEqual(observed.result,baseline,name+': complete DTO bit/type parity');
 assert.equal(stringifyStrictJson(input),before,name+': input unchanged');
 const r=observed.result,t=observed.timing,n=r.geometry?.positions.length??0,faces=r.geometry?.triangles.length??0,expected=[n,faces,faces,r.audits.length];
 assert.equal(t.stages.cppQuery.calls,1,name);assert.deepEqual(t.getterKinds,expected,name);assert.equal(t.stages.cppGetter.calls,expected.reduce((a,b)=>a+b,0),name);assert.equal(t.stages.outputCopy.calls,1+t.stages.cppGetter.calls,name);
 let sum=0;for(const stage of Object.values(t.stages)){assert.ok(Number.isFinite(stage.elapsedMs)&&stage.elapsedMs>=0);sum+=stage.elapsedMs;}
 assert.ok(Number.isFinite(t.elapsedMs)&&t.elapsedMs>=sum);assert.equal(t.unassignedMs,t.elapsedMs-sum);
 timings.push({name,classification:r.status==='completed'?'completed model':'expected model failure',timing:t});return r;
}
for(const f of fixed.fixtures){const q=f.input,settings={maxVertices:q.settings[0],maxTriangles:q.settings[1],sqrtRefinements:q.settings[2]},r=run(f.name,q,settings),p=project(r);compare(p,f.result,f.name);replay.push({name:f.name,input:q,result:p});}
const fixedNumericComparisons=numericComparisons;
for(const f of sources.fixtures){
 const q=f.input;let source,state,sourceError=null,before;
 try{source=parseSkinBindingPortable(q.portable);before=serializeSkinBindingPortable(source);state=evaluateSkinBinding(runtime,source,q.seconds,{loop:q.loop});}catch(error){sourceError=String(error.message);}
 assert.equal(sourceError!==null,f.sourceError!==null,f.name+': original upstream failure stage');
 if(source)assert.equal(serializeSkinBindingPortable(source),before,f.name+': source unchanged');
 let derived=null;
 if(state){assert.equal(['completed','invalid_input','budget_exceeded','ill_conditioned','numerical_failure'].indexOf(state.deformation.status),f.deformation.status,f.name);
  if(state.deformation.status==='completed')derived=project(run(f.name,{positions:state.deformation.positions,triangles:source.mesh.triangles},{maxVertices:q.settings[0],maxTriangles:q.settings[1],sqrtRefinements:q.settings[2]}));
 }
 compare(derived,f.derived,f.name+'.derived');sourceReplay.push({name:f.name,sourceError,profileInvoked:derived!==null,derived});
}
assert.equal(runtime.native,originals.native);assert.equal(runtime.prepareDerivedMesh,originals.prepare);assert.equal(runtime.native._pp_sim_derived_mesh,originals.query);assert.equal(runtime.native._pp_sim_derived_mesh_record,originals.getter);
assert.equal(timings.length,48);assert.equal(sourceReplay.filter(x=>!x.profileInvoked).length,3);
const packet=path.join(out,'profiled-wasm40.json');await writeFile(packet,stringifyStrictJson({schema:1,fixtures:replay})+'\n',{flag:'wx'});
const python=process.env.PIKAPIKA_PYTHON??(process.platform==='win32'?'python':'python3'),checker=fileURLToPath(new URL('./verify-derived-mesh.py',import.meta.url));
const argv=[checker,packet,'--backend','main-wasm'];let reference;
try{const stdout=execFileSync(python,argv,{encoding:'utf8',windowsHide:true,maxBuffer:4*1024*1024});await writeFile(path.join(out,'reference.stdout.txt'),stdout,{flag:'wx'});reference=JSON.parse(stdout);}
catch(error){await writeFile(path.join(out,'reference.stderr.txt'),error.stderr??String(error),{flag:'wx'});throw error;}
await writeFile(path.join(out,'timings.json'),JSON.stringify({timings,sourceReplay},null,2)+'\n',{flag:'wx'});
const controlScript=fileURLToPath(new URL('../tests/derived_mesh_reference_tests.py',import.meta.url));
const controlArgs=[controlScript,packet,'--backend','main-wasm','--output',path.join(root,'build/derived-mesh-reference-profile')];let referenceControls;
try{const stdout=execFileSync(python,controlArgs,{encoding:'utf8',windowsHide:true,maxBuffer:4*1024*1024});await writeFile(path.join(out,'controls.stdout.txt'),stdout,{flag:'wx'});referenceControls=JSON.parse(stdout);}
catch(error){await writeFile(path.join(out,'controls.stderr.txt'),error.stderr??String(error),{flag:'wx'});throw error;}
const sourceHashes={};for(const p of ['tools/derived-profile.mjs','engine/simulation.mjs','scripts/verify-derived-profile.mjs','scripts/verify-derived-mesh.py','tests/derived_mesh_reference_tests.py'])sourceHashes[p]=sha(await readFile(path.join(root,p)));
const report={status:'PASS',fixedCases:40,sourceCases:11,admittedProfiledSourceCases:8,upstreamCasesWithoutDerivedQuery:3,profiledQueries:48,nativeNumericBitComparisons:numericComparisons,fixedNumericBitComparisons:fixedNumericComparisons,sourceDerivedNumericBitComparisons:numericComparisons-fixedNumericComparisons,reference,referenceControls,sourceHashes,
 wasm:{bytes:wasm.length,sha256:sha(wasm)},inputs:[{path:nativeFile,sha256:sha(nativeRaw)},{path:sourceFile,sha256:sha(sourceRaw)}],referenceCommand:[python,...argv],controlsCommand:[python,...controlArgs],outputDirectory:out,scope:'Correctness replay only: all DTO fields equal uninstrumented actual WASM; profiled actual outputs independently checked. Instrumentation timings are not calibrated performance or GPU/Native timings.'};
await writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));
