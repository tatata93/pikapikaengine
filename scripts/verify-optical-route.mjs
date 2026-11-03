import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import assert from 'node:assert/strict';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const input=process.argv[2];if(!input)throw new Error('usage: verify-optical-route.mjs native-executable-or-fixtures.json [report.json]');
const source=JSON.parse(input.endsWith('.json')?await readFile(input,'utf8'):execFileSync(path.resolve(input),['--fixtures'],{encoding:'utf8'}));
assert.equal(source.fixtures.length,15);assert.equal(new Set(source.fixtures.map(f=>f.name)).size,15);
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const statuses=['completed','geometry_miss','geometry_unresolved','interface_unresolved','branch_unavailable','invalid_input','budget_exceeded','numerical_failure'];
const reasons=['none','zero_direction','zero_normal','parallel_or_coplanar','no_real_roots','tangent_or_discriminant','parameter_boundary','aperture_boundary','cap_boundary','orientation','precision_limit','refinement_budget','incident_side','critical_angle','numerical_domain'];
let numericalValues=0,maxAbsoluteError=0,maxNormalizedError=0;const cases=[];
function compare(a,b,label){
  if(Array.isArray(a)){assert.equal(a.length,b.length,label);a.forEach((x,j)=>compare(x,b[j],label+'/'+j));return;}
  assert.ok(Number.isFinite(a)&&Number.isFinite(b),label);const error=Math.abs(a-b),scale=Math.max(1,Math.abs(a),Math.abs(b));++numericalValues;
  maxAbsoluteError=Math.max(maxAbsoluteError,error);maxNormalizedError=Math.max(maxNormalizedError,error/scale);assert.ok(error<=1e-8+1e-10*scale,`${label}: ${a} != ${b}`);
}
function ray(r){return {origin:r.origin,direction:r.direction,minimumParameter:r.tMin,maximumParameter:r.tMax};}
function totals(a,b,label){for(const key of ['distance','opticalPathLength','throughput'])compare(a[key],b[key],label+'/'+key);}
for(const f of source.fixtures){
  const steps=f.input.steps.map(s=>({surface:{...s.shape,kind:['disk','sphere','cap'][s.type]},branch:s.branch===0?'reflected':'transmitted',nextIndex:s.nextIndex,minimumParameter:s.tMin,maximumParameter:s.tMax}));
  const r=runtime.traceOpticalRoute(ray(f.input.ray),steps,{...f.input.settings,index:f.input.index,vacuumWavelength:f.input.wavelength}),n=f.result;
  assert.equal(r.status,statuses[n.status],f.name);assert.equal(r.completedSteps,n.completedSteps);assert.equal(r.failedStep,n.failedStep);assert.equal(r.segments.length,n.segments.length);
  assert.equal(Boolean(r.completion),Boolean(n.completion));
  if(r.completion){const a=r.completion,b=n.completion;compare(a.ray.origin,b.ray.origin,f.name+'/finalOrigin');compare(a.ray.direction,b.ray.direction,f.name+'/finalDirection');compare(a.index,b.index,f.name+'/index');totals(a.totals,b.totals,f.name+'/totals');}
  r.segments.forEach((a,j)=>{const b=n.segments[j],label=f.name+'/segment'+j;
    assert.equal(a.branch,b.branch===0?'reflected':'transmitted');assert.equal(a.geometry.status,['hit','miss','unresolved'][b.geometryStatus]);assert.equal(a.geometry.reason,reasons[b.geometryReason]);
    for(const key of ['incidentIndex','otherIndex'])compare(a[key],b[key],label+'/'+key);
    compare(a.incoming.origin,b.incoming.origin,label+'/origin');compare(a.incoming.direction,b.incoming.direction,label+'/direction');
    compare(a.incoming.minimumParameter,b.incoming.tMin,label+'/tmin');compare(a.incoming.maximumParameter,b.incoming.tMax,label+'/tmax');
    assert.equal(Boolean(a.geometry.hit),Boolean(b.hit));if(a.geometry.hit){compare(a.geometry.hit.position,b.hit,label+'/hit');compare(a.geometry.hit.parameter,b.parameter,label+'/parameter');compare(a.geometry.hit.physicalDistance,b.distance,label+'/distance');compare(a.geometry.hit.incidentNormal,b.normal,label+'/normal');}
    assert.equal(Boolean(a.interface),b.interfaceKind!==undefined);if(a.interface){assert.equal(a.interface.kind,['transmission','total_internal_reflection','unresolved'][b.interfaceKind]);assert.equal(a.interface.reason,reasons[b.interfaceReason]);}
    assert.equal(Boolean(a.outgoing),Boolean(b.outgoing));if(a.outgoing){compare(a.outgoing.origin,b.outgoing.origin,label+'/spawnOrigin');compare(a.outgoing.direction,b.outgoing.direction,label+'/spawnDirection');}
    assert.equal(Boolean(a.factor),Boolean(b.factor));if(a.factor)compare(a.factor,b.factor,label+'/factor');
    assert.equal(Boolean(a.accumulated),Boolean(b.accumulated));if(a.accumulated)totals(a.accumulated,b.accumulated,label+'/prefix');
    assert.ok(a.sqrtRefinements<=32768,'bounded primitive work');
  });
  cases.push({name:f.name,status:r.status,completedSteps:r.completedSteps,segments:r.segments.length});
}
const report={verification:'Original Native optical-route fixture inputs replayed through shipped shared C++ WASM API',fixtures:15,numericalValues,maxAbsoluteError,maxNormalizedError,cases,
  limits:'Compares exposed snapshot fields, not every internal primitive field. Explicit itineraries only; analytic correctness is checked independently.'};
if(process.argv[3])await writeFile(process.argv[3],JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
