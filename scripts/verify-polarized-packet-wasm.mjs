import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const [file,reportFile,outputsFile,oracleFile]=process.argv.slice(2);
if(!file)throw new Error('Usage: node scripts/verify-polarized-packet-wasm.mjs fixtures.json [report.json] [outputs.json] [oracle.csv]');
const source=JSON.parse(await readFile(file,'utf8'));assert.equal(source.schema,1);assert.ok(Array.isArray(source.fixtures)&&source.fixtures.length>=36);
const bytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:bytes});
const statuses=['completed','geometry_failed','power_unresolved','invalid_input','budget_exceeded','numerical_failure'];
const failures=['none','initial_state_uncertain','initial_frame_uncertain','incidence_frame_uncertain','amplitude_uncertain','numerical_domain'];
const geometryStatuses=['completed','geometry_miss','geometry_unresolved','interface_unresolved','branch_unavailable','invalid_input','budget_exceeded','numerical_failure'];
const state=s=>s?{power:s.power,diagonal:s.coherency.diagonal,upper:s.coherency.upper.map(c=>[c.real,c.imag])}:null;
const complex=c=>c?[c.real,c.imag]:null;
function routeProjected(r){return {status:statuses.indexOf(r.status),powerFailure:failures.indexOf(r.powerFailure),geometryStatus:r.geometry?geometryStatuses.indexOf(r.geometry.status):-1,completedPowerSteps:r.completedPowerSteps,failedPowerStep:r.failedPowerStep,counters:[r.geometryQueries,r.interfaceQueries,r.geometrySqrtRefinements,r.powerSqrtRefinements],limited:r.refinementLimited,initial:state(r.initialState),segments:r.segments.map(s=>({ordinal:s.ordinal,branch:s.branch==='transmitted'?1:0,exactNormal:s.exactNormal,homogeneous:s.homogeneous,s:complex(s.amplitudeS),p:complex(s.amplitudeP),state:state(s.outgoing)})),completion:r.completion?{state:state(r.completion.state),origin:r.completion.ray.origin,direction:r.completion.ray.direction,index:r.completion.index}:null};}

const batchStatuses=['completed','unresolved','invalid_input','budget_exceeded','numerical_failure'];
const packetStatuses=['not_examined','accepted','route_miss','branch_unavailable','sensor_miss','route_unresolved','power_unresolved','sensor_unresolved','invalid_input','budget_exceeded','numerical_failure'];
const reasons=['none','zero_direction','zero_normal','parallel_or_coplanar','no_real_roots','tangent_or_discriminant','parameter_boundary','aperture_boundary','cap_boundary','orientation','precision_limit','refinement_budget','incident_side','critical_angle','numerical_domain'];
function sensorProjected(s){return s?{status:['hit','miss','unresolved'].indexOf(s.status),reason:reasons.indexOf(s.reason),rootCount:s.rootCount,consideredCount:s.consideredCount,sqrt:s.sqrtRefinements,limited:s.refinementLimited,discriminant:s.discriminant,nearest:s.hit?{parameter:s.hit.parameter,distance:s.hit.physicalDistance,position:s.hit.position,normal:s.hit.geometricNormal,incidentNormal:s.hit.incidentNormal,frontFace:s.hit.frontFace}:null}:null;}
function projected(r){return {status:batchStatuses.indexOf(r.status),counts:[r.evaluations,r.counts.accepted,r.counts.routeMiss,r.counts.branchUnavailable,r.counts.sensorMiss,r.counts.unknown],queries:[r.geometryQueries,r.interfaceQueries,r.sensorQueries],sqrt:[r.geometrySqrtRefinements,r.powerSqrtRefinements,r.sensorSqrtRefinements],limited:r.refinementLimited,stats:r.stats?{totalSource:r.stats.totalSourcePower,acceptedSource:r.stats.acceptedSourcePower,detected:r.stats.detectedPower}:null,records:r.records.map(p=>({ordinal:p.packetIndex,power:p.power,status:packetStatuses.indexOf(p.status),sensorPower:p.sensorPower,route:p.route?routeProjected(p.route):null,sensor:sensorProjected(p.sensor)}))};}
const bits=n=>{assert.ok(Number.isFinite(n));const d=new DataView(new ArrayBuffer(8));d.setFloat64(0,n);return d.getBigUint64(0).toString(16).padStart(16,'0');};let numericalValues=0;
function compare(a,b,label){assert.equal(typeof a,typeof b,label);if(typeof a==='number'){assert.equal(bits(a),bits(b),label);++numericalValues;}else if(a&&typeof a==='object'){assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}else assert.equal(a,b,label);}
const shape=t=>t.kind===0?{kind:'disk',center:t.center,normal:t.normal,apertureRadius:t.aperture}:t.kind===1?{kind:'sphere',center:t.center,radius:t.radius}:{kind:'cap',vertex:t.vertex,axis:t.axis,signedRadius:t.radius,apertureRadius:t.aperture};
const outputs=[];
for(const f of source.fixtures){const x=f.input,s=x.settings;
 const input={packets:x.packets.map(p=>({ray:{origin:p.origin,direction:p.direction,minimumParameter:p.domain[0],maximumParameter:p.domain[1]},power:p.power,transverseReference:p.reference})),steps:x.steps.map(t=>({surface:shape(t),branch:t.branch?'transmitted':'reflected',nextIndex:t.nextIndex,minimumParameter:t.domain[0],maximumParameter:t.domain[1]})),index:x.index,vacuumWavelength:x.wavelength,sensor:{kind:'disk',center:x.sensor.center,normal:x.sensor.normal,apertureRadius:x.sensor.aperture},sensorMinimumParameter:x.sensor.domain[0],sensorMaximumParameter:x.sensor.domain[1]};
 const settings={maximumParameterWidth:s[0],maxSqrtRefinements:s[1],maximumRouteSteps:s[2],powerMaxSqrtRefinements:s[3],maximumRouteSqrtRefinements:s[4],maximumPackets:s[5],maximumPacketEvaluations:s[6],maximumTotalSqrtRefinements:s[7]};
 const result=runtime.queryPolarizedPacket(input,settings);compare(projected(result),f.result,f.name);outputs.push({name:f.name,input,settings,result});
}
let oracleRows=0,oracleEndpointBits=0;const oracleOutputs=[];
if(oracleFile){const lines=(await readFile(oracleFile,'utf8')).trim().split(/\r?\n/);assert.equal(lines.shift(),'id,kind,I,Q,U,V,totalLo,totalHi,acceptedLo,acceptedHi,detectedLo,detectedHi');assert.equal(lines.length,128);
 const hex=t=>{const m=/^(-?)0x([01])(?:\.([0-9a-f]+))?p([+-]?\d+)$/.exec(t);assert.ok(m,'canonical hex float');const f=m[3]??'',e=+m[4];assert.ok(e>=-1022&&e<=1023);return (m[1]?-1:1)*(Number.parseInt(m[2]+f,16)*2**(-4*f.length))*2**e;};
 const disk=(z,normal)=>({kind:'disk',center:[0,0,z],normal,apertureRadius:100}),front={surface:disk(0,[0,0,-1]),nextIndex:1.5},back={surface:disk(.25,[0,0,1]),nextIndex:1};
 for(const [j,line]of lines.entries()){const a=line.split(',');assert.equal(a.length,12);assert.equal(a[0],String(j));assert.equal(a[1],String(j%3));const power=a.slice(2,6).map(hex);assert.deepEqual(power,[1+j/128,0,0,1+j/128]);
  const steps=j%3===0?[]:j%3===1?[front,back]:[front,{...back,branch:'reflected'},{surface:front.surface,nextIndex:1,branch:'reflected'},back];
  const result=runtime.queryPolarizedPacket({packets:[{ray:{origin:[0,0,-1],direction:[0,0,1]},power}],steps,sensor:disk(1.25,[0,0,-1])});assert.equal(result.status,'completed');const actual=[...result.stats.totalSourcePower,...result.stats.acceptedSourcePower,...result.stats.detectedPower];assert.deepEqual(actual.map(bits),a.slice(6).map(t=>bits(hex(t))),'oracle '+j);++oracleRows;oracleEndpointBits+=actual.length;oracleOutputs.push({id:j,result});
 }
}
const report={status:'PASS',fixtures:source.fixtures.length,numericalValues,bitEqualNumbers:numericalValues,oracleRows,oracleEndpointBits,wasmBytes:bytes.length,wasmSha256:createHash('sha256').update(bytes).digest('hex'),limits:'Finite prescribed-route noninterfering explicit-watt packet measure; no continuous source integration bound, sensor irradiance image, coherent path recombination or automatic visibility proof.'};
console.log(JSON.stringify(report,null,2));if(reportFile)await writeFile(reportFile,JSON.stringify(report,null,2)+'\n');if(outputsFile)await writeFile(outputsFile,JSON.stringify({schema:1,outputs,oracleOutputs})+'\n');
