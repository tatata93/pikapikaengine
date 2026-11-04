// Actual manual-lab preset acceptance. No solver or fabricated host model.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {flightLabPresetProvenance} from '../tools/sphere-triangle-mesh-flight-presets.mjs';
import {flightLabPresets,flightLabPreset,evaluateFlightLab,serializeFlightLab} from '../tools/sphere-triangle-mesh-flight-lab.mjs';

const [directory,...extra]=process.argv.slice(2);assert.ok(directory&&!extra.length,'Usage: node verify-sphere-triangle-mesh-flight-lab.mjs FRESH_OUTPUT_DIRECTORY');
const root=fileURLToPath(new URL('../',import.meta.url)),out=path.resolve(directory);
await mkdir(path.dirname(out),{recursive:true});await mkdir(out);
const budget={maxBytes:67108864,maxDepth:64,maxNodes:4000000},saveBudget={maxBytes:8388608,maxDepth:32,maxNodes:1000000};
const info=raw=>({bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});
const save=async(name,value)=>{const text=typeof value==='string'?value:stringifyStrictJson(value,budget)+'\n';await writeFile(path.join(out,name),text,{flag:'wx'});};
const dependencies=['engine/simulation.mjs','engine/sphere-triangle-mesh-flight.mjs','tools/sphere-triangle-mesh-flight-presets.mjs','tools/sphere-triangle-mesh-flight-lab.mjs',
  'tools/sphere-triangle-mesh-flight-lab.html','tests/sphere-triangle-mesh-flight-lab.test.mjs','scripts/verify-sphere-triangle-mesh-flight-lab.mjs',
  'assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json'];
async function hashes(){const result={};for(const p of dependencies)result[p]=info(await readFile(path.join(root,p)));return result;}
const before=await hashes();await save('source-before.json',before);
const bitView=new DataView(new ArrayBuffer(8));const bits=n=>{assert.equal(typeof n,'number');assert.ok(Number.isFinite(n));bitView.setFloat64(0,n);return bitView.getBigUint64(0).toString(16).padStart(16,'0');};
const counters={source:{numeric:0,negativeZero:0},model:{numeric:0,negativeZero:0},saved:{numeric:0,negativeZero:0}};
function compare(actual,expected,label,count){assert.equal(typeof actual,typeof expected,label);
  if(typeof expected==='number'){assert.equal(bits(actual),bits(expected),label);count.numeric++;if(Object.is(actual,-0))count.negativeZero++;}
  else if(expected!==null&&typeof expected==='object'){
    if(Array.isArray(expected)){assert.ok(Array.isArray(actual),label);assert.equal(actual.length,expected.length,label);for(let i=0;i<expected.length;i++)compare(actual[i],expected[i],label+'['+i+']',count);}
    else{assert.ok(actual!==null&&!Array.isArray(actual),label);assert.deepEqual(Object.keys(actual).sort(),Object.keys(expected).sort(),label);for(const k of Object.keys(expected))compare(actual[k],expected[k],label+'.'+k,count);}
  }else assert.equal(actual,expected,label);
}
try{
  const source={};for(const [cohort,record] of Object.entries(flightLabPresetProvenance.sourceFiles)){
    const raw=await readFile(path.join(root,record.path));assert.deepEqual(info(raw),{bytes:record.bytes,sha256:record.sha256});source[cohort]=parseStrictJson(raw.toString('utf8'),budget);
  }
  const originalFile='reports/sphere-triangle-mesh-flight-js-checks/run-20261104-final/owned/wasm-owned-dtos.json';
  const referenceBytes=await readFile(path.join(root,originalFile)),reference=parseStrictJson(referenceBytes.toString('utf8'),budget);
  const wasm=await readFile(path.join(root,'assets/pikapika-simulation.wasm')),real=await loadSimulationRuntime({wasmBytes:wasm});
  let calls=0;const runtime={get diagnostics(){return real.diagnostics;},
    querySphereTriangleMeshHeldLoad(...a){calls++;return real.querySphereTriangleMeshHeldLoad(...a);},
    querySphereTriangleMeshFreeFlightGuard(...a){calls++;return real.querySphereTriangleMeshFreeFlightGuard(...a);},
    querySphereTriangleMeshEntry(){assert.fail('No older method fallback');}};
  const rows=[],retained=[],counts={held:{},guard:{}},maximums={audits:0,leaves:0,partition:0,frontier:0,sources:0,candidateIds:0,lastMeshRows:0,lastMeshCandidates:0};
  for(const preset of flightLabPresets){const input=flightLabPreset(preset.name),f=source[preset.cohort].fixtures.find(f=>f.name===preset.fixtureName),expected=reference.fixtures.find(f=>f.cohort===preset.cohort&&f.name===preset.fixtureName);
    assert.ok(f&&expected);compare(input,{mode:preset.mode,...f.input},preset.name+'.source',counters.source);
    const original=stringifyStrictJson(input,budget),beforeCalls=calls;let packet,error;
    try{packet=evaluateFlightLab(runtime,input);}catch(e){error=e;}
    assert.equal(calls,beforeCalls+1,preset.name+' exactly one real owned method');assert.equal(stringifyStrictJson(input,budget),original);
    if(expected.result===null){assert.ok(error instanceof Error&&packet===undefined);const row={name:preset.name,cohort:preset.cohort,fixtureName:preset.fixtureName,mode:preset.mode,input,packet:null,hostError:error.message};rows.push(row);await save(preset.name+'.host.json',row);continue;}
    assert.ifError(error);compare(packet.result,expected.result,preset.name+'.fullOwnedModel',counters.model);compare(packet.input,input,preset.name+'.ownedSource',counters.source);
    const h=preset.mode==='held'?packet.result:packet.result.inflated;
    const selectedAudit=h?.audits.length?h.audits.length-1:0,selectedSource=input.triangles.length?input.triangles.length-1:0;
    const text=serializeFlightLab(packet,'yz',selectedAudit,selectedSource);assert.ok(text.endsWith('\n'));assert.ok(Buffer.byteLength(text)<=saveBudget.maxBytes);
    const parsed=parseStrictJson(text,saveBudget);compare(parsed.result,packet.result,preset.name+'.savedFullResult',counters.saved);compare(parsed.input,input,preset.name+'.savedInput',counters.saved);
    assert.equal(parsed.projection,'yz');assert.equal(parsed.inspectedAudit,h?.audits.length?selectedAudit:null);assert.equal(parsed.inspectedOrdinal,input.triangles.length?selectedSource:null);
    assert.equal(parsed.inspectedSurfaceId,input.triangles.length?input.triangles[selectedSource].id:null);
    await save(preset.name+'.json',text);retained.push({packet,serialized:stringifyStrictJson(packet,budget)});
    counts[preset.mode][packet.result.status]=(counts[preset.mode][packet.result.status]??0)+1;
    for(const [key,n] of Object.entries({audits:h?.audits.length??0,leaves:h?.certifiedLeaves.length??0,partition:h?.partition.length??0,frontier:h?.frontier.length??0,sources:input.triangles.length,
      candidateIds:h?.candidateSurfaceIds.length??0,lastMeshRows:h?.lastMesh?.rows.length??0,lastMeshCandidates:h?.lastMesh?.rows.reduce((n,r)=>n+(r.query?.candidates.length??0),0)??0}))maximums[key]=Math.max(maximums[key],n);
    rows.push({name:preset.name,cohort:preset.cohort,fixtureName:preset.fixtureName,mode:preset.mode,hostError:null,status:packet.result.status,file:preset.name+'.json'});
  }
  for(const item of retained)assert.equal(stringifyStrictJson(item.packet,budget),item.serialized,'Prior full packets retained across all later modes');
  assert.equal(rows.length,30);assert.equal(retained.length,29);assert.equal(rows.filter(r=>r.hostError!==null).length,1);
  const after=await hashes();await save('source-after.json',after);assert.deepEqual(after,before);
  await save('presets.json',{schema:1,kind:'sphere-triangle-mesh-flight-lab-acceptance',rows});
  const files={};for(const name of ['source-before.json','source-after.json','presets.json',...rows.map(r=>r.hostError===null?r.file:r.name+'.host.json')])files[name]=info(await readFile(path.join(out,name)));
  const report={schema:1,status:'PASS',presets:rows.length,actualModelPresets:retained.length,hostRejected:rows.length-retained.length,actualOwnedMethodCalls:calls,counts,maximums,counters,
    provenance:flightLabPresetProvenance,reference:{path:originalFile,...info(referenceBytes)},wasm:info(wasm),sourceBefore:before,sourceAfter:after,sourceStable:true,files,
    scope:'Actual92-export owned methods evaluate every selected original input once. Complete lab DTOs and saved JSON compare to canonical actual-owned173-model proof; host packet remains absent. No browser Blob/download or UI-generation/rendering assertion is inferred from this Node verifier; those have separate dedicated tests and actual browser evidence.'};
  await save('report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}catch(error){await save('failure.json',{status:'FAIL',name:error.name,message:error.message,stack:error.stack});await save('failure-source-after.json',await hashes());throw error;}
