import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson} from '../engine/strict-json.mjs';

const [fixtureFile,probeFile,directory]=process.argv.slice(2);
if(!fixtureFile||!probeFile||!directory)throw new Error('Usage: node scripts/verify-sphere-triangle-sdk.mjs native-fixtures.json native-sdk-probe output-directory');
const dir=path.resolve(directory);await mkdir(dir,{recursive:true});
const sha=x=>createHash('sha256').update(x).digest('hex'),view=new DataView(new ArrayBuffer(8));
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0).toString(16).padStart(16,'0');};
const signedJSON=x=>typeof x==='number'?(assert.ok(Number.isFinite(x)),Object.is(x,-0)?'-0':JSON.stringify(x)):Array.isArray(x)?'['+x.map(signedJSON).join(',')+']':x&&typeof x==='object'?'{'+Object.entries(x).map(([k,v])=>JSON.stringify(k)+':'+signedJSON(v)).join(',')+'}':JSON.stringify(x);
const text=await readFile(fixtureFile,'utf8'),source=parseStrictJson(text);assert.equal(source.schema,1);assert.equal(source.kind,'sphere-triangle-fixtures');assert.equal(source.fixtures.length,113);
const settingsKeys=['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared'];
const packet=q=>[...q.sphere.center,q.sphere.radius,q.triangle.id,...q.triangle.vertices.flat(),...settingsKeys.map(k=>q.settings[k]),0,0,0,0];
const rows='pikapika_sphere_triangle_sdk 1\ncases 113\n'+source.fixtures.map(f=>JSON.stringify(f.name)+' '+packet(f.input).map(signedJSON).join(' ')).join('\n')+'\n';
await writeFile(path.join(dir,'inputs.rows'),rows,{flag:'wx'});
const nativeBytes=execFileSync(path.resolve(probeFile),['--rows',path.join(dir,'inputs.rows')],{windowsHide:true,timeout:120000,maxBuffer:16*1024*1024});
await writeFile(path.join(dir,'native-packets.json'),nativeBytes,{flag:'wx'});const native=parseStrictJson(nativeBytes.toString());
assert.equal(native.schema,1);assert.equal(native.kind,'sphere-triangle-sdk-packets');assert.equal(native.accepted,111);assert.equal(native.hostRejected,2);assert.equal(native.fixtures.length,113);
const wasmBytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const raw=await loadSimulationRuntime({wasmBytes}),wrapper=await loadSimulationRuntime({wasmBytes});raw.check(raw.native._pp_sim_reset());
const statuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const reasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const features=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'],dispositions=['retained','outside_simplex','kkt_violated'],relations=['separated','penetrating','touching','boundary_unresolved'];
function project(r){return {...r,status:statuses.indexOf(r.status),reason:reasons.indexOf(r.reason),geometry:r.geometry?{...r.geometry,relation:relations.indexOf(r.geometry.relation)}:null,candidates:r.candidates.map(c=>({...c,feature:features.indexOf(c.feature),disposition:dispositions.indexOf(c.disposition)}))};}
let packetComparisons=0,modelComparisons=0,negativeZeros=0,completed=0,failures=0,hostRejected=0;
function compare(a,b,label,kind='model'){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);if(kind==='model')modelComparisons++;else packetComparisons++;if(Object.is(a,-0))negativeZeros++;}
 else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const key of Object.keys(a))compare(a[key],b[key],label+'.'+key,kind);}
 else assert.equal(a,b,label);
}
const outputs=[],replay=[];
for(let i=0;i<113;i++){
 const f=source.fixtures[i],n=native.fixtures[i],input=packet(f.input),before=raw.output(),label=f.name;assert.equal(n.name,label);assert.equal(input.length,24);compare(input,n.input,label+'.input','packet');assert.deepEqual(input.map(bits),n.inputBits);
 compare(before,n.outputBefore,label+'.before','packet');assert.deepEqual(before.map(bits),n.outputBeforeBits);
 raw.inputF64(input);const exchangeStatus=raw.native._pp_sim_sphere_triangle(24);assert.equal(exchangeStatus,n.exchangeStatus,label+'.exchange');
 let summary=null,candidates=[],result=null;
 if(exchangeStatus===0){
  summary=raw.output();assert.equal(summary.length,58);compare(summary,n.summary,label+'.summary','packet');assert.deepEqual(summary.map(bits),n.summaryBits);
  for(let j=0;j<summary[6];j++){raw.check(raw.native._pp_sim_sphere_triangle_candidate(j));const c=raw.output();assert.equal(c.length,13);compare(c,n.candidates[j],label+'.candidate'+j,'packet');assert.deepEqual(c.map(bits),n.candidateBits[j]);candidates.push(c);}
  assert.equal(candidates.length,n.candidates.length);assert.equal(n.hostFailurePreserved,null);
  const q=f.input,unchanged=signedJSON(q);result=project(wrapper.querySphereTriangle({position:q.sphere.center,radius:q.sphere.radius},q.triangle,q.settings));assert.equal(signedJSON(q),unchanged,label+'.source unchanged');
  compare(result,f.result,label+'.model');replay.push({name:label,input:q,result});if(result.status===0)completed++;else{failures++;assert.equal(result.geometry,null);}
 }else{
  hostRejected++;assert.equal(n.hostFailurePreserved,true);assert.equal(n.summary,null);assert.deepEqual(n.candidates,[]);assert.deepEqual(raw.output().map(bits),before.map(bits));
  const q=f.input;assert.throws(()=>wrapper.querySphereTriangle({position:q.sphere.center,radius:q.sphere.radius},q.triangle,q.settings),/ID requires/);
 }
 const after=raw.output();compare(after,n.outputAfter,label+'.after','packet');assert.deepEqual(after.map(bits),n.outputAfterBits);
 outputs.push({name:label,input,exchangeStatus,summary,candidates,result,outputBefore:before,outputAfter:after,summaryBits:summary?.map(bits)??null,candidateBits:candidates.map(c=>c.map(bits)),hostFailurePreserved:exchangeStatus?true:null});
}
assert.equal(completed,88);assert.equal(failures,23);assert.equal(hostRejected,2);assert.ok(negativeZeros>0);
const replayFile=path.join(dir,'wasm-fixtures.json');await writeFile(replayFile,signedJSON({schema:1,kind:'sphere-triangle-fixtures',fixtures:replay})+'\n',{flag:'wx'});
await writeFile(path.join(dir,'wasm-packets.json'),signedJSON({schema:1,kind:'sphere-triangle-sdk-packets',fixtures:outputs})+'\n',{flag:'wx'});
const python=process.env.PIKAPIKA_PYTHON??(process.platform==='win32'?'python':'python3');
const reference=JSON.parse(execFileSync(python,[fileURLToPath(new URL('./verify-sphere-triangle.py',import.meta.url)),replayFile],{windowsHide:true,encoding:'utf8',timeout:30000,maxBuffer:4*1024*1024}));
const negative=execFileSync(python,[fileURLToPath(new URL('../tests/sphere_triangle_reference_tests.py',import.meta.url)),replayFile,'--output',path.join(dir,'negative-controls')],{windowsHide:true,encoding:'utf8',timeout:60000,maxBuffer:4*1024*1024});
await writeFile(path.join(dir,'negative-controls.stdout.txt'),negative,{flag:'wx'});
const files={};for(const name of ['inputs.rows','native-packets.json','wasm-packets.json','wasm-fixtures.json','negative-controls.stdout.txt']){const data=await readFile(path.join(dir,name));files[name]={bytes:data.length,sha256:sha(data)};}
const report={schema:1,status:'PASS',modelFixtures:111,completed,expectedModelFailures:failures,hostRejected,packetNumericComparisons:packetComparisons,modelNumericComparisons:modelComparisons,negativeZeroComparisons:negativeZeros,reference,nativeFixturesSha256:sha(Buffer.from(text)),wasm:{bytes:wasmBytes.length,sha256:sha(wasmBytes)},files,scope:'All 113 frozen inputs, 111 model results and two explicit host ID rejections. Actual common C++ WASM and independent rational inclusion checks. No World, CCD, response or GPU claims.'};
await writeFile(path.join(dir,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));
