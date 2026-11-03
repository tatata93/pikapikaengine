import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const oracleOptions=process.argv.slice(2).filter(a=>a.startsWith('--oracle='));assert.ok(oracleOptions.length<=1,'one oracle option');const args=process.argv.slice(2).filter(a=>!a.startsWith('--oracle='));const file=args[0];if(!file)throw new Error('usage: verify-optical-selection-wasm.mjs native-fixtures.json|native-executable [report.json] [wasm-outputs.json]');
const source=JSON.parse(file.endsWith('.json')?await readFile(file,'utf8'):execFileSync(path.resolve(file),['--fixtures'],{encoding:'utf8',timeout:60000,maxBuffer:8*1024*1024}));
assert.equal(source.version,1);assert.equal(source.model,'uniform static optical surface selection');assert.equal(source.fixtures.length,33);
const names=['two-planes','all-miss','empty','sphere-front','cap-second','self-zero','sphere-exit','tiny-neighbor','explicit-cutoff','order-swap','correlated-order','aperture-mixed','aperture-outside','coincident','tangent','rear-aperture-uncertain','prefix-disabled','rear-tangent-uncertain','query-budget','prefix-budget','surface-budget','total-sqrt-budget','primitive-refinement-budget','parameter-width','same-id','zero-id','invalid-later-shape','invalid-settings','empty-invalid-ray','empty-zero-direction','parallel-miss','upper-boundary','back-face'];
assert.deepEqual(source.fixtures.map(x=>x.name).sort(),names.sort());
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:wasm});
const statuses=['hit','miss','unresolved','invalid_input','budget_exceeded','numerical_failure'],gs=['hit','miss','unresolved'];
const reasons=['none','zero_direction','zero_normal','parallel_or_coplanar','no_real_roots','tangent_or_discriminant','parameter_boundary','aperture_boundary','cap_boundary','orientation','precision_limit','refinement_budget','incident_side','critical_angle','numerical_domain'];
const cs=['not_examined','accepted','rejected_parameter','rejected_aperture','rejected_cap','unresolved'];
const hit=h=>h?{parameter:h.parameter,physicalDistance:h.distance,position:h.position,geometricNormal:h.geometricNormal,incidentNormal:h.incidentNormal,frontFace:h.frontFace}:null;
const geometry=g=>g?{status:gs[g.status],reason:reasons[g.reason],rootCount:g.rootCount,consideredCount:g.consideredCount,sqrtRefinements:g.sqrtRefinements,refinementLimited:g.refinementLimited,discriminant:g.discriminant,candidates:g.candidates.slice(0,g.rootCount).map(c=>({parameter:c.parameter,state:cs[c.state],reason:reasons[c.reason]})),hit:hit(g.nearest)}:null;
const expected=r=>({status:statuses[r.status],surfaceCount:r.surfaces.length,geometryQueries:r.queries,prefixQueries:r.prefixQueries,sqrtRefinements:r.sqrtRefinements,refinementLimited:r.refinementLimited,nearest:r.nearest?{id:r.nearest.id,hit:hit(r.nearest.hit)}:null,surfaces:r.surfaces.map(d=>({id:d.id,geometry:geometry(d.geometry),prefix:geometry(d.prefix),excludedByPrefix:d.excludedByPrefix}))});
let values=0,bitEqual=0,maxAbsoluteError=0,oracleFamilies=0,oracleEndpointBits=0;
const bits=x=>{const b=new ArrayBuffer(8),d=new DataView(b);d.setFloat64(0,x);return d.getBigUint64(0).toString(16).padStart(16,'0');};
function compare(a,b,label){
  if(typeof b==='number'){assert.ok(Number.isFinite(a)&&Number.isFinite(b),label);++values;maxAbsoluteError=Math.max(maxAbsoluteError,Math.abs(a-b));if(bits(a)===bits(b))++bitEqual;else throw new Error(`${label} numeric endpoint/counter mismatch ${bits(a)} != ${bits(b)}`);return;}
  if(Array.isArray(b)){assert.ok(Array.isArray(a),label);assert.equal(a.length,b.length,label);b.forEach((x,j)=>compare(a[j],x,`${label}/${j}`));return;}
  if(b!==null&&typeof b==='object'){assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(b))compare(a[k],b[k],`${label}/${k}`);return;}
  assert.equal(a,b,label);
}
const outputs=[];let compared=0,rejected=0;
for(const fixture of source.fixtures){
  const {ray,settings:s,surfaces}=fixture.input;
  const records=surfaces.map(t=>({id:t.id,surface:t.kind===0?{kind:'disk',center:t.center,normal:t.axis,apertureRadius:t.aperture}:t.kind===1?{kind:'sphere',center:t.center,radius:t.radius}:{kind:'cap',vertex:t.center,axis:t.axis,signedRadius:t.radius,apertureRadius:t.aperture}}));
  const settings={maximumParameterWidth:s.maximumParameterWidth,maxSqrtRefinements:s.primitiveMaxSqrtRefinements,maximumSurfaces:s.maxSurfaces,maximumQueries:s.maxQueries,maximumTotalSqrtRefinements:s.maxSqrtRefinements,allowPrefixExclusion:s.allowPrefixExclusion};
  if(['zero-id','invalid-settings'].includes(fixture.name)){
    assert.equal(fixture.result.status,3);assert.throws(()=>runtime.queryNearestOpticalSurface(ray,records,settings));
    outputs.push({name:fixture.name,abiRejected:true,reason:'C/JS exchange requires exact positive safe IDs and strictly positive integer budget settings; Native core invalid_input remains covered independently.'});++rejected;continue;
  }
  const actual=runtime.queryNearestOpticalSurface(ray,records,settings);compare(actual,expected(fixture.result),fixture.name);++compared;
  const encoded=[...ray.origin.flat(),...ray.direction.flat(),ray.minimumParameter,ray.maximumParameter,s.maximumParameterWidth,s.primitiveMaxSqrtRefinements,s.maxSurfaces,s.maxQueries,s.maxSqrtRefinements,s.allowPrefixExclusion?1:0,surfaces.length,
    ...surfaces.flatMap(t=>[t.id,t.kind,...t.center,...(t.kind===1?[0,0,0]:t.axis),t.radius,t.aperture])];
  const n=runtime.inputF64(encoded);runtime.check(runtime.native._pp_sim_optical_selection(n));const summary=runtime.output(),raw=[];
  for(let j=0;j<summary[3];++j){runtime.check(runtime.native._pp_sim_optical_selection_surface(j,0));const original=runtime.output();runtime.check(runtime.native._pp_sim_optical_selection_surface(j,1));raw.push({original,prefix:runtime.output()});}
  outputs.push({name:fixture.name,result:actual,raw:{input:encoded,summary,surfaces:raw}});
}
const oracleOutputs=[];
if(oracleOptions.length){
  const csv=await readFile(oracleOptions[0].slice('--oracle='.length),'utf8'),lines=csv.trim().split(/\r?\n/);
  assert.equal(lines.shift(),'kind,k,originLo,originHi,directionLo,directionHi,target,selectedID,status,tLo,tHi,distanceLo,distanceHi,zLo,zHi');assert.equal(lines.length,192);
  const fromBits=h=>{assert.match(h,/^[0-9a-f]{16}$/);const d=new DataView(new ArrayBuffer(8));d.setBigUint64(0,BigInt('0x'+h));const n=d.getFloat64(0);assert.ok(Number.isFinite(n));return n;};
  const seen=new Set();
  for(const line of lines){const row=line.split(',');assert.equal(row.length,15);const [kind,k]=row;assert.ok(['P','S','C'].includes(kind)&&Number.isInteger(+k)&&+k>=1&&+k<=64);assert.ok(!seen.has(kind+k));seen.add(kind+k);
    const [lo,hi,dl,dh,target]=row.slice(2,7).map(fromBits),disk=z=>({kind:'disk',center:[0,0,z],normal:[0,0,-1],apertureRadius:10});
    const records=[{id:2,surface:disk(kind==='C'?-4:4)},{id:1,surface:kind==='P'?disk(target):kind==='S'?{kind:'sphere',center:[0,0,0],radius:-target}:{kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:2,apertureRadius:1}}];
    const input={origin:[0,0,[lo,hi]],direction:[0,0,[dl,dh]],minimumParameter:0,maximumParameter:100},r=runtime.queryNearestOpticalSurface(input,records);
    assert.equal(row[7],'1');assert.equal(row[8],'0');assert.equal(r.status,'hit');assert.equal(r.nearest.id,1);
    const endpoints=[...r.nearest.hit.parameter,...r.nearest.hit.physicalDistance,...r.nearest.hit.position[2]];
    assert.deepEqual(endpoints.map(bits),row.slice(9),`${kind}${k} shipped optical selection endpoints`);++oracleFamilies;oracleEndpointBits+=6;oracleOutputs.push({kind,k:+k,hit:r.nearest.hit});
  }
}
assert.equal(compared,31);assert.equal(rejected,2);assert.equal(bitEqual,values);
const report={status:'PASS',fixtures:33,comparedModelResults:compared,explicitExchangeRejections:rejected,numericalValues:values,bitEqualNumbers:bitEqual,maxAbsoluteError,oracleFamilies,oracleEndpointBits,wasmBytes:wasm.length,wasmSha256:createHash('sha256').update(wasm).digest('hex'),limits:'Complete Native core fixtures replayed through shipped JS/C ABI. Two invalid-domain cases intentionally rejected by stricter exchange before core. Geometry semantics are independently checked by the Fraction oracle; finite parity alone does not prove arbitrary inputs.'};
console.log(JSON.stringify(report,null,2));if(args[1])await writeFile(args[1],JSON.stringify(report,null,2)+'\n');if(args[2])await writeFile(args[2],JSON.stringify({version:1,model:source.model,outputs,oracleOutputs})+'\n');
