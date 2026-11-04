import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson} from '../engine/strict-json.mjs';

const [fixtureFile,probeFile,directory]=process.argv.slice(2);
if(!fixtureFile||!probeFile||!directory)throw new Error('Usage: node scripts/verify-sphere-triangle-mesh-sdk.mjs native-fixtures.json native-sdk-probe fresh-output-directory');
const dir=path.resolve(directory);await mkdir(dir,{recursive:true});
const sha=x=>createHash('sha256').update(x).digest('hex'),view=new DataView(new ArrayBuffer(8));
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0).toString(16).padStart(16,'0');};
const signedJSON=x=>typeof x==='number'?(assert.ok(Number.isFinite(x)),Object.is(x,-0)?'-0':JSON.stringify(x)):Array.isArray(x)?'['+x.map(signedJSON).join(',')+']':x&&typeof x==='object'?'{'+Object.entries(x).map(([k,v])=>JSON.stringify(k)+':'+signedJSON(v)).join(',')+'}':JSON.stringify(x);
const text=await readFile(fixtureFile,'utf8'),source=parseStrictJson(text);
assert.equal(source.schema,1);assert.equal(source.kind,'sphere-triangle-mesh-fixtures');assert.equal(source.fixtures.length,48);
const settingsKeys=['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared'];
const input=q=>[...q.sphere.center,q.sphere.radius,q.settings.maxSurfaces,...settingsKeys.map(k=>q.settings.primitive[k]),0,0,0];
const triangles=q=>q.triangles.map(t=>[t.id,...t.vertices.flat()]);
const rows='pikapika_sphere_triangle_mesh_sdk 1\ncases 48\n'+source.fixtures.map(f=>JSON.stringify(f.name)+' '+f.input.triangles.length+' '+input(f.input).map(signedJSON).join(' ')+'\n'+triangles(f.input).map(t=>t.map(signedJSON).join(' ')).join('\n')).join('\n')+'\n';
// Empty sources have no triangle line; avoid an empty line between case records.
const lines=rows.split('\n').filter(Boolean).join('\n')+'\n';
await writeFile(path.join(dir,'inputs.rows'),lines,{flag:'wx'});
const nativeBytes=execFileSync(path.resolve(probeFile),['--rows',path.join(dir,'inputs.rows')],{windowsHide:true,timeout:120000,maxBuffer:32*1024*1024});
await writeFile(path.join(dir,'native-packets.json'),nativeBytes,{flag:'wx'});const native=parseStrictJson(nativeBytes.toString());
assert.equal(native.schema,1);assert.equal(native.kind,'sphere-triangle-mesh-sdk-packets');assert.equal(native.fixtures.length,48);
const wasmBytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const raw=await loadSimulationRuntime({wasmBytes}),wrapper=await loadSimulationRuntime({wasmBytes});raw.check(raw.native._pp_sim_reset());
const statuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const reasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const features=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'],dispositions=['retained','outside_simplex','kkt_violated'],relations=['separated','penetrating','touching','boundary_unresolved'];
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
function projectPrimitive(r){return {...r,status:statuses.indexOf(r.status),reason:reasons.indexOf(r.reason),geometry:r.geometry?{...r.geometry,relation:relations.indexOf(r.geometry.relation)}:null,candidates:r.candidates.map(c=>({...c,feature:features.indexOf(c.feature),disposition:dispositions.indexOf(c.disposition)}))};}
function project(r){return {...r,status:meshStatuses.indexOf(r.status),reason:meshReasons.indexOf(r.reason),rows:r.rows.map(row=>({...row,query:row.query?projectPrimitive(row.query):null}))};}
let packetComparisons=0,modelComparisons=0,negativeZeros=0,completed=0,failures=0,hostRejected=0;
function compare(a,b,label,kind='model'){
  assert.equal(typeof a,typeof b,label);
  if(typeof a==='number'){assert.equal(bits(a),bits(b),label);if(kind==='model')modelComparisons++;else packetComparisons++;if(Object.is(a,-0))negativeZeros++;}
  else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const key of Object.keys(a))compare(a[key],b[key],label+'.'+key,kind);}
  else assert.equal(a,b,label);
}
const outputs=[],replay=[];
for(let i=0;i<source.fixtures.length;i++){
  const f=source.fixtures[i],n=native.fixtures[i],values=input(f.input),surfaces=triangles(f.input),before=raw.output(),label=f.name,m=raw.native;
  assert.equal(n.name,label);compare(values,n.input,label+'.input','packet');assert.deepEqual(values.map(bits),n.inputBits);compare(surfaces,n.triangles,label+'.triangles','packet');assert.deepEqual(surfaces.map(t=>t.map(bits)),n.triangleBits);
  compare(before,n.outputBefore,label+'.before','packet');assert.deepEqual(before.map(bits),n.outputBeforeBits);
  const beginStatus=m._pp_sim_sphere_triangle_mesh_begin(surfaces.length),appendStatuses=[];assert.equal(beginStatus,n.beginStatus);
  let exchangeStatus=beginStatus,failedPhase=beginStatus?'begin':null;
  if(!exchangeStatus){
    for(let offset=0;offset<surfaces.length;offset+=6){
      const count=raw.inputF64(surfaces.slice(offset,offset+6).flat()),status=m._pp_sim_sphere_triangle_mesh_append(count);appendStatuses.push(status);
      if(status){exchangeStatus=status;failedPhase='append';break;}
    }
    if(!exchangeStatus){exchangeStatus=m._pp_sim_sphere_triangle_mesh(raw.inputF64(values));if(exchangeStatus)failedPhase='query';}
  }
  assert.deepEqual(appendStatuses,n.appendStatuses);assert.equal(exchangeStatus,n.exchangeStatus);assert.equal(failedPhase,n.failedPhase);
  let summary=null,sources=[],rows=[],result=null;
  if(!exchangeStatus){
    summary=raw.output();assert.equal(summary.length,24);compare(summary,n.summary,label+'.summary','packet');assert.deepEqual(summary.map(bits),n.summaryBits);
    for(let ordinal=0;ordinal<surfaces.length;++ordinal){
      raw.check(m._pp_sim_sphere_triangle_mesh_source(ordinal));const s=raw.output();assert.equal(s.length,14);compare(s,n.sources[ordinal],label+'.source'+ordinal,'packet');assert.deepEqual(s.map(bits),n.sourceBits[ordinal]);sources.push(s);
      if(s[12]){
        raw.check(m._pp_sim_sphere_triangle_mesh_row(ordinal));const packet=raw.output();assert.equal(packet.length,58);
        const nr=n.rows[rows.length];assert.equal(nr.rowOrdinal,ordinal);compare(packet,nr.packet,label+'.row'+ordinal,'packet');assert.deepEqual(packet.map(bits),nr.bits);
        const candidates=[];
        for(let c=0;c<packet[6];++c){raw.check(m._pp_sim_sphere_triangle_mesh_candidate(ordinal,c));const candidate=raw.output();assert.equal(candidate.length,13);compare(candidate,nr.candidates[c],label+'.candidate'+ordinal+'/'+c,'packet');assert.deepEqual(candidate.map(bits),nr.candidateBits[c]);candidates.push(candidate);}
        assert.equal(candidates.length,nr.candidates.length);rows.push({rowOrdinal:ordinal,packet,candidates});
      }
    }
    assert.equal(rows.length,n.rows.length);assert.equal(sources.length,n.sources.length);assert.equal(n.hostFailurePreserved,null);
    const q=f.input,unchanged=signedJSON(q);result=project(wrapper.querySphereTriangleMesh({position:q.sphere.center,radius:q.sphere.radius},q.triangles,q.settings));assert.equal(signedJSON(q),unchanged,label+'.source unchanged');
    compare(result,f.result,label+'.model');replay.push({name:label,input:q,result});if(result.status===0)completed++;else{failures++;assert.equal(result.nearest,null);}
  }else{
    hostRejected++;assert.equal(n.hostFailurePreserved,true);assert.equal(n.summary,null);assert.deepEqual(n.sources,[]);assert.deepEqual(n.rows,[]);assert.deepEqual(raw.output().map(bits),before.map(bits));
    const q=f.input;assert.throws(()=>wrapper.querySphereTriangleMesh({position:q.sphere.center,radius:q.sphere.radius},q.triangles,q.settings));
  }
  const after=raw.output();compare(after,n.outputAfter,label+'.after','packet');assert.deepEqual(after.map(bits),n.outputAfterBits);
  outputs.push({name:label,input:values,triangles:surfaces,beginStatus,appendStatuses,exchangeStatus,failedPhase,summary,sources,rows,result,outputBefore:before,outputAfter:after});
}
assert.equal(completed+failures,native.accepted);assert.equal(hostRejected,native.hostRejected);assert.equal(completed+failures+hostRejected,48);assert.ok(completed>=12&&hostRejected>0&&negativeZeros>0);
const replayFile=path.join(dir,'wasm-fixtures.json');await writeFile(replayFile,signedJSON({schema:1,kind:'sphere-triangle-mesh-fixtures',fixtures:replay})+'\n',{flag:'wx'});
await writeFile(path.join(dir,'wasm-packets.json'),signedJSON({schema:1,kind:'sphere-triangle-mesh-sdk-packets',fixtures:outputs})+'\n',{flag:'wx'});
const python=process.env.PIKAPIKA_PYTHON??(process.platform==='win32'?'python':'python3');
const reference=JSON.parse(execFileSync(python,[fileURLToPath(new URL('./verify-sphere-triangle-mesh.py',import.meta.url)),replayFile],{windowsHide:true,encoding:'utf8',timeout:30000,maxBuffer:4*1024*1024}));
const negative=execFileSync(python,[fileURLToPath(new URL('../tests/sphere_triangle_mesh_reference_tests.py',import.meta.url)),replayFile,'--output',path.join(dir,'negative-controls')],{windowsHide:true,encoding:'utf8',timeout:60000,maxBuffer:4*1024*1024});
await writeFile(path.join(dir,'negative-controls.stdout.txt'),negative,{flag:'wx'});
const files={};for(const name of ['inputs.rows','native-packets.json','wasm-packets.json','wasm-fixtures.json','negative-controls.stdout.txt']){const data=await readFile(path.join(dir,name));files[name]={bytes:data.length,sha256:sha(data)};}
const report={schema:1,status:'PASS',modelFixtures:completed+failures,completed,expectedModelFailures:failures,hostRejected,packetNumericComparisons:packetComparisons,modelNumericComparisons:modelComparisons,negativeZeroComparisons:negativeZeros,reference,nativeFixturesSha256:sha(Buffer.from(text)),wasm:{bytes:wasmBytes.length,sha256:sha(wasmBytes)},files,scope:'All 48 frozen inputs classified as actual model attempts or host exchange rejections; actual common WASM and independent rational inclusion. No World/CCD/game mesh response.'};
await writeFile(path.join(dir,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));
