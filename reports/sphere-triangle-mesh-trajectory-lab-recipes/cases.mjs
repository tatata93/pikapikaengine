// Exercise the real controller/public SDK and identify proven fixture origins by
// complete input values (including signed zero), independently of preset labels.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../../engine/strict-json.mjs';
import {trajectoryLabPresets,trajectoryLabPreset,evaluateTrajectoryLab,serializeTrajectoryLab} from '../../tools/sphere-triangle-mesh-trajectory-lab.mjs';
const root=new URL('../../',import.meta.url),out=new URL(process.argv[2].replaceAll('\\','/').replace(/\/$/,'')+'/',root);
await mkdir(out,{recursive:true});
const budget={maxBytes:16777216,maxDepth:32,maxNodes:1000000};
const corpus=parseStrictJson(await readFile(new URL('reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root/native-fixtures.json',root),'utf8'),budget);
const hostNames=new Set(['zero-source-id','unsafe-source-id','65-source-rejection']);
const sorted=value=>Array.isArray(value)?value.map(sorted):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,sorted(value[key])])):value;
const signature=value=>stringifyStrictJson(sorted(value),budget);
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('assets/pikapika-simulation.wasm',root))});
const cases=[],summary=[];
for(const preset of trajectoryLabPresets){
 const input=trajectoryLabPreset(preset.name),sig=signature(input),origins=corpus.fixtures.filter(row=>signature(row.input)===sig).map(row=>row.name);
 let packet=null,error=null;
 try{
  packet=evaluateTrajectoryLab(runtime,input);
  const direct=runtime.querySphereTriangleMeshTrajectory({start:input.start,end:input.end,radius:input.radius},input.triangles,input.settings);
  assert.equal(signature(packet.result),signature(direct),preset.name+' public method/controller complete result differs');
  const saved=parseStrictJson(serializeTrajectoryLab(packet),budget);
  assert.equal(signature(saved.input),sig);assert.equal(signature(saved.result),signature(packet.result));
 }catch(e){if(packet)throw e;error={name:e.name,message:e.message};}
 assert.ok(origins.length,preset.name+' is not bitwise equal to a declared previous exact-rational fixture');
 assert.equal(packet===null,origins.some(name=>hostNames.has(name)),preset.name+' unexpected host/model classification');
 cases.push({name:preset.name,label:preset.label,origins,input,packet,error});
 summary.push({name:preset.name,origins,status:packet?.result.status??'host_rejected',reason:packet?.result.reason??null,audits:packet?.result.audits.length??0,leaves:packet?.result.certifiedLeaves.length??0,sourceCount:input.triangles.length});
}
const text=stringifyStrictJson({schema:1,cases},budget)+'\n';await writeFile(new URL('cases.json',out),text);
const report={schema:1,status:'PASS',presets:cases.length,modelResults:cases.filter(row=>row.packet).length,hostRejected:cases.filter(row=>!row.packet).length,
 separated:cases.filter(row=>row.packet?.result.status==='separated').length,witness:cases.filter(row=>row.packet?.result.status==='penetration_witness').length,
 cases:summary,artifact:{bytes:Buffer.byteLength(text),sha256:createHash('sha256').update(text).digest('hex')},
 scope:'Every controller input exactly matches an already accepted pinned Native fixture including negative zero. All real model outputs match the actual public owned method; every host rejection remains separate. No new independent mathematical solver or broader model claim.'};
await writeFile(new URL('report.json',out),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
