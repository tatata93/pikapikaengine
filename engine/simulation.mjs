import createModule from '../assets/pikapika-simulation.mjs';
import {validateMesh,createBoxMesh} from './mesh.mjs';
import {quaternionRotate,add} from './math.mjs';
import {querySphereTriangleMeshTrajectory} from './sphere-triangle-mesh-trajectory.mjs';
import {querySphereTriangleMeshEntry} from './sphere-triangle-mesh-entry.mjs';
import {querySphereTriangleMeshHeldLoad,querySphereTriangleMeshFreeFlightGuard} from './sphere-triangle-mesh-flight.mjs';

const bytesCache=new WeakMap();let defaultRuntime;
const asset=name=>{const url=new URL('../assets/'+name,import.meta.url),build=new URL(import.meta.url).searchParams.get('build');if(build)url.searchParams.set('build',build);return url;};
const finiteArray=(input,length,label)=>{
  if(!(Array.isArray(input)||ArrayBuffer.isView(input))||input.length!==length)throw new Error(`${label} requires ${length} components`);
  const values=Array.from(input);if(!values.every(Number.isFinite))throw new Error(`${label} requires finite numbers`);return values;
};
const stepCount=value=>{if(!Number.isInteger(value)||value<1||value>32)throw new Error('Simulation batch requires 1..32 complete ticks');return value;};
const validBodyId=value=>{if(!Number.isSafeInteger(value)||value<1)throw new Error('Body ID requires an integer in 1..9007199254740991');return value;};
const sphereTriangleStatuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const sphereTriangleReasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const sphereTriangleFeatures=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'];
const sphereTriangleDispositions=['retained','outside_simplex','kkt_violated'];
const sphereTriangleRelations=['separated','penetrating','touching','boundary_unresolved'];
function sphereTriangleResult(runtime,a,surfaceId,getCandidate=index=>runtime.native._pp_sim_sphere_triangle_candidate(index)){
  const fail=label=>{throw new Error('Invalid C++ sphere triangle '+label);},integer=(x,max)=>Number.isSafeInteger(x)&&x>=0&&x<=max,flag=x=>x===0||x===1;
  if(a.length!==58||!a.every(Number.isFinite)||!integer(a[0],7)||!integer(a[1],17)||!flag(a[2])||a[3]!==surfaceId||!integer(a[4],127)||!integer(a[5],3)||!integer(a[6],7)||!integer(a[7],7)||a[6]>a[7]||a[7]-a[6]>1||!integer(a[8],512)||!flag(a[9])||!flag(a[10])||!flag(a[13]))fail('summary');
  const reasonsByStatus=[[0],[1,2,3],[4],[6],[5,7,9,10,11,12,14],[8,13],[9,15,16],[17]];
  if(!reasonsByStatus[a[0]].includes(a[1])||Boolean(a[2])!==(a[0]===0)||a[13]>a[10])fail('classification');
  const zeroRange=(from,to)=>{if(a.slice(from,to).some(x=>!Object.is(x,0)))fail('absent-field padding');};
  const interval=(data,at)=>{if(data[at]>data[at+1])fail('interval');return data.slice(at,at+2);};
  const optional=(flagIndex,at)=>{if(a[flagIndex])return interval(a,at);zeroRange(at,at+2);return null;};
  const squaredCross=optional(10,11),sineSquared=optional(13,14);
  if(squaredCross&&squaredCross[0]<0||sineSquared&&(sineSquared[0]<0||sineSquared[1]>1))fail('geometric diagnostics');
  let geometry=null;
  if(a[2]){
    if(a[6]!==7||a[7]!==7||a[4]===0||!squaredCross||!sineSquared)fail('completed metadata');
    const vector=at=>[interval(a,at),interval(a,at+2),interval(a,at+4)];
    geometry={surfaceId:a[3],survivingFeatures:a[4],barycentric:vector(16),closestLocal:vector(22),closest:vector(28),delta:vector(34),normal:vector(40),spherePoint:vector(46),squaredDistance:interval(a,52),distance:interval(a,54),gap:interval(a,56),relation:sphereTriangleRelations[a[5]]};
    if(geometry.barycentric.some(b=>b[0]<0||b[1]>1)||geometry.normal.some(b=>b[0]<-1||b[1]>1)||geometry.squaredDistance[0]<=0||geometry.distance[0]<=0)fail('geometry domain');
    const [lo,hi]=geometry.gap,relation=lo>0?0:hi<0?1:lo===0&&hi===0?2:3;
    if(a[5]!==relation)fail('gap relation');
  }else{zeroRange(4,6);zeroRange(16,58);}
  const candidates=[];let retained=0;
  for(let index=0;index<a[6];++index){
    runtime.check(getCandidate(index));const c=runtime.output(),dimension=index===0?0:index<4?1:2;
    if(c.length!==13||!c.every(Number.isFinite)||c[0]!==index||!integer(c[1],2)||c[2]!==dimension)fail('candidate record');
    const barycentric=[interval(c,3),interval(c,5),interval(c,7)],kkt=[interval(c,9),interval(c,11)];
    for(let k=dimension;k<2;++k)if(!Object.is(kkt[k][0],-0)||!Object.is(kkt[k][1],0))fail('unused KKT padding');
    const outside=barycentric.some(b=>b[1]<0||b[0]>1),violated=kkt.slice(0,dimension).some(b=>b[0]>0);
    if(c[1]===0&&(outside||violated)||c[1]===1&&!outside||c[1]===2&&(outside||!violated))fail('candidate disposition');
    if(c[1]===0)retained|=1<<index;
    candidates.push({feature:sphereTriangleFeatures[index],disposition:sphereTriangleDispositions[c[1]],kktCount:dimension,barycentric,kkt});
  }
  if(geometry&&geometry.survivingFeatures!==retained)fail('retained feature mask');
  return {status:sphereTriangleStatuses[a[0]],reason:sphereTriangleReasons[a[1]],geometry,squaredCross,sineSquared,candidates,candidatesExamined:a[7],sqrtRefinements:a[8],sqrtRefinementLimited:Boolean(a[9])};
}
const sphereTriangleMeshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const sphereTriangleMeshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
function sphereTriangleMeshResult(runtime,a,source,getters){
  const fail=label=>{throw new Error('Invalid C++ sphere triangle mesh '+label);};
  const integer=(x,max)=>Number.isSafeInteger(x)&&!Object.is(x,-0)&&x>=0&&x<=max,flag=x=>Object.is(x,0)||x===1;
  if(a.length!==24||!a.every(Number.isFinite)||!integer(a[0],5)||!integer(a[1],11)||!flag(a[2])||!integer(a[3],64)||a[3]!==source.length||!integer(a[4],source.length)||!flag(a[5])||!flag(a[7])||!integer(a[9],64)||!integer(a[10],448)||!integer(a[11],32768)||!integer(a[12],a[9])||!integer(a[13],a[9])||!integer(a[14],source.length))fail('header');
  const reasons=[[0],[1,2,4,5,6],[3],[7],[8,9,10],[11]];
  if(!reasons[a[0]].includes(a[1])||Boolean(a[2])!==(a[0]===0)||a.slice(21).some(x=>!Object.is(x,0)))fail('classification or reserved fields');
  const optionalIndex=(has,index,max)=>{if(has){if(!integer(index,max-1))fail('failure index');return index;}if(!Object.is(index,0))fail('absent index padding');return null;};
  const failedIndex=optionalIndex(a[5],a[6],source.length),firstFailedRow=optionalIndex(a[7],a[8],a[4]);
  if(failedIndex!==null&&(a[0]!==1||![4,5,6].includes(a[1]))||a[0]===1&&[4,5].includes(a[1])&&failedIndex===null)fail('structural failure index');
  const preflight=[1,2,5].includes(a[0]);
  if(preflight&&(a[4]!==0||a.slice(9,15).some(x=>!Object.is(x,0))||firstFailedRow!==null))fail('preflight work');
  if(a[0]===0&&(!source.length||a[4]!==source.length||a[9]!==source.length||a[13]!==0||failedIndex!==null||firstFailedRow!==null))fail('completed work');
  if(a[0]===3&&(a[4]!==source.length||a[9]!==source.length||a[13]<1||failedIndex!==null||firstFailedRow===null))fail('failed-row work');
  if(!a[2]&&(a[14]!==0||a.slice(15,21).some(x=>!Object.is(x,0))))fail('absent nearest padding');
  const rows=[],possibleSurfaceIds=[];let queries=0,candidatesExamined=0,sqrtRefinements=0,sqrtLimitedRows=0,failedRows=0,firstFailure=null,unexamined=false;
  for(let index=0;index<source.length;++index){
    runtime.check(getters?getters.source(index):runtime.native._pp_sim_sphere_triangle_mesh_source(index));const s=runtime.output(),original=source[index];
    const expected=[index,original.id,...original.vertices.flat()];
    if(s.length!==14||!s.every(Number.isFinite)||expected.some((v,i)=>!Object.is(v,s[i]))||![11,12,13].every(i=>flag(s[i]))||s[11]!==Number(index<a[4])||s[12]>s[11]||s[13]>Number(Boolean(a[2])&&Boolean(s[12])))fail('owned source record');
    if(s[13])possibleSurfaceIds.push(s[1]);
    if(!s[11])continue;
    const triangle={id:s[1],vertices:[s.slice(2,5),s.slice(5,8),s.slice(8,11)]};let query=null;
    if(s[12]){
      if(unexamined)fail('non-prefix query work');
      runtime.check(getters?getters.row(index):runtime.native._pp_sim_sphere_triangle_mesh_row(index));
      query=sphereTriangleResult(runtime,runtime.output(),triangle.id,ordinal=>getters?getters.candidate(index,ordinal):runtime.native._pp_sim_sphere_triangle_mesh_candidate(index,ordinal));
      queries++;candidatesExamined+=query.candidatesExamined;sqrtRefinements+=query.sqrtRefinements;sqrtLimitedRows+=Number(query.sqrtRefinementLimited);
      if(query.status!=='completed'){failedRows++;if(firstFailure===null)firstFailure=index;}
    }else{unexamined=true;if(a[0]!==4)fail('unexamined ordinary row');}
    rows.push({triangle,query});
  }
  if(queries!==a[9]||candidatesExamined!==a[10]||sqrtRefinements!==a[11]||sqrtLimitedRows!==a[12]||failedRows!==a[13]||firstFailure!==firstFailedRow)fail('actual work sums');
  possibleSurfaceIds.sort((x,y)=>x-y);
  if(possibleSurfaceIds.length!==a[14]||new Set(possibleSurfaceIds).size!==possibleSurfaceIds.length)fail('possible surface IDs');
  let nearest=null;
  if(a[2]){
    if(rows.some(r=>!r.query?.geometry))fail('incomplete nearest');
    const values=['squaredDistance','distance','gap'];nearest={};
    for(let i=0;i<3;++i){
      const interval=a.slice(15+2*i,17+2*i),rowValues=rows.map(r=>r.query.geometry[values[i]]),expected=[Math.min(...rowValues.map(v=>v[0])),Math.min(...rowValues.map(v=>v[1]))];
      if(interval.some((v,k)=>!Object.is(v,expected[k])))fail('endpoint minimum');nearest[values[i]]=interval;
    }
    const expected=rows.filter(r=>r.query.geometry.squaredDistance[0]<=nearest.squaredDistance[1]).map(r=>r.triangle.id).sort((x,y)=>x-y);
    if(!expected.length||expected.length!==possibleSurfaceIds.length||expected.some((id,i)=>id!==possibleSurfaceIds[i]))fail('all interval-possible surfaces');
    nearest.possibleSurfaceIds=possibleSurfaceIds;
  }
  return {status:sphereTriangleMeshStatuses[a[0]],reason:sphereTriangleMeshReasons[a[1]],failedIndex,firstFailedRow,rows,nearest,queries,candidatesExamined,sqrtRefinements,sqrtLimitedRows,failedRows};
}
export class SimulationError extends Error {constructor(code,message){super(message);this.name='SimulationError';this.code=code;}}
export class SimulationRuntime {
  constructor(native,metadata,wasmBytes,startupMs){
    if(native._pp_sim_api_version()!==1)throw new Error('Unsupported C++ simulation ABI');
    this.native=native;this.metadata=metadata;this.wasmBytes=wasmBytes;this.startupMs=startupMs;
  }
  get diagnostics(){return {backend:'C++ WebAssembly',compiler:this.metadata.compiler??'Emscripten 6.0.13',buildId:new URL(import.meta.url).searchParams.get('build')??'local-unversioned',wasmBytes:this.wasmBytes,memoryBytes:this.native.HEAPU8.byteLength,startupMs:this.startupMs,apiVersion:1};}
  check(status){if(status!==0){const m=this.native,p=m._pp_sim_error_ptr(),n=m._pp_sim_error_length();throw new SimulationError(status,new TextDecoder().decode(m.HEAPU8.subarray(p,p+n)));}}
  handle(value){if(!value){this.check(this.native._pp_sim_last_status());throw new Error('C++ returned an empty simulation handle');}return value;}
  inputF64(values){
    const data=finiteArray(values,values.length,'Float64 exchange'),m=this.native;
    if(data.length>m._pp_sim_input_f64_capacity())throw new Error('Float64 exchange capacity exceeded');
    m.HEAPF64.set(data,m._pp_sim_input_f64_ptr()/8);return data.length;
  }
  inputU32(values){
    const data=Array.from(values),m=this.native;if(data.length>m._pp_sim_input_u32_capacity()||!data.every(x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff))throw new Error('Invalid triangle index exchange');
    m.HEAPU32.set(data,m._pp_sim_input_u32_ptr()/4);return data.length;
  }
  output(){const m=this.native,p=m._pp_sim_output_f64_ptr()/8;return Array.from(m.HEAPF64.subarray(p,p+m._pp_sim_output_count()));}
  createHull(source){return new SimulationHull(this,source);}
  createWorld({gravity=[0,-9.80665,0]}={}){const world=new SimulationWorld(this);try{world.setGravity(gravity);return world;}catch(error){world.dispose();throw error;}}
  querySphereSphere(a,b,horizon){
    const count=this.inputF64([...sphereQueryInput(a),...sphereQueryInput(b),horizon]);
    this.check(this.native._pp_sim_sphere_sphere_toi(count));return toiResult(this.output());
  }
  querySpherePlane(sphere,{normal=[0,1,0],offset=0,velocity=[0,0,0]}={},horizon){
    const count=this.inputF64([...sphereQueryInput(sphere),...finiteArray(normal,3,'Plane normal'),offset,...finiteArray(velocity,3,'Plane velocity'),horizon]);
    this.check(this.native._pp_sim_sphere_plane_toi(count));return toiResult(this.output());
  }
  querySphereTriangle({position,radius},{id,vertices},settings={}){
    const m=this.native;
    if(typeof m._pp_sim_sphere_triangle!=='function'||typeof m._pp_sim_sphere_triangle_candidate!=='function')throw new Error('C++ sphere triangle API unavailable; rebuild the common simulation SDK');
    if(!Array.isArray(vertices)||vertices.length!==3)throw new Error('Static triangle requires three vertices');
    const uint=(value,label)=>{if(!Number.isInteger(value)||value<0||value>0xffffffff)throw new Error(label+' requires a uint32 integer');return value;};
    const surfaceId=validBodyId(id),count=this.inputF64([...finiteArray(position,3,'Sphere position'),radius,surfaceId,
      ...vertices.flatMap(v=>finiteArray(v,3,'Triangle vertex')),
      uint(settings.maxCandidates??7,'maxCandidates'),uint(settings.sqrtRefinements??128,'sqrtRefinements'),uint(settings.maxTotalSqrtRefinements??1024,'maxTotalSqrtRefinements'),
      settings.maximumLocalWidth??1e-7,settings.maximumNormalWidth??1e-8,settings.minimumSineSquared??1e-12,0,0,0,0]);
    this.check(m._pp_sim_sphere_triangle(count));return sphereTriangleResult(this,this.output(),surfaceId);
  }
  querySphereTriangleMesh(sphere,triangles,settings={}){
    const m=this.native;
    for(const name of ['begin','append','source','row','candidate','query']){
      const symbol=name==='query'?'_pp_sim_sphere_triangle_mesh':'_pp_sim_sphere_triangle_mesh_'+name;
      if(typeof m[symbol]!=='function')throw new Error('C++ sphere triangle mesh API unavailable; rebuild the common simulation SDK');
    }
    if(!Array.isArray(triangles)||triangles.length>64)throw new Error('Static triangle mesh requires an array of at most 64 surfaces');
    const copyVector=(value,label)=>{
      if(!(Array.isArray(value)||ArrayBuffer.isView(value))||value.length!==3)throw new Error(label+' requires three components');
      const copy=[value[0],value[1],value[2]];if(!copy.every(Number.isFinite))throw new Error(label+' requires finite numbers');return copy;
    };
    const source=[],surfaceCount=triangles.length;
    for(let index=0;index<surfaceCount;++index){const t=triangles[index];
      if(!t||!Array.isArray(t.vertices)||t.vertices.length!==3)throw new Error('Static triangle requires three vertices');
      source.push({id:validBodyId(t.id),vertices:[copyVector(t.vertices[0],'Triangle vertex'),copyVector(t.vertices[1],'Triangle vertex'),copyVector(t.vertices[2],'Triangle vertex')]});
    }
    const uint=(value,label)=>{if(!Number.isInteger(value)||value<0||value>0xffffffff)throw new Error(label+' requires a uint32 integer');return value;},p=settings.primitive??{};
    const input=finiteArray([...copyVector(sphere.position,'Sphere position'),sphere.radius,uint(settings.maxSurfaces??64,'maxSurfaces'),
      uint(p.maxCandidates??7,'maxCandidates'),uint(p.sqrtRefinements??128,'sqrtRefinements'),uint(p.maxTotalSqrtRefinements??1024,'maxTotalSqrtRefinements'),
      p.maximumLocalWidth??1e-7,p.maximumNormalWidth??1e-8,p.minimumSineSquared??1e-12,0,0,0],14,'Sphere triangle mesh profile');
    this.check(m._pp_sim_sphere_triangle_mesh_begin(source.length));
    for(let offset=0;offset<source.length;offset+=6){
      const count=this.inputF64(source.slice(offset,offset+6).flatMap(t=>[t.id,...t.vertices.flat()]));this.check(m._pp_sim_sphere_triangle_mesh_append(count));
    }
    this.check(m._pp_sim_sphere_triangle_mesh(this.inputF64(input)));
    return sphereTriangleMeshResult(this,this.output(),source);
  }
  querySphereTriangleMeshTrajectory(path,triangles,settings={}){
    return querySphereTriangleMeshTrajectory(this,path,triangles,settings,sphereTriangleMeshResult);
  }
  querySphereTriangleMeshEntry(path,triangles,settings={}){
    return querySphereTriangleMeshEntry(this,path,triangles,settings,sphereTriangleMeshResult);
  }
  querySphereTriangleMeshHeldLoad(sphere,triangles,horizon,settings={}){
    return querySphereTriangleMeshHeldLoad(this,sphere,triangles,horizon,settings,sphereTriangleMeshResult);
  }
  querySphereTriangleMeshFreeFlightGuard(body,gravity,triangles,horizon,settings={}){
    return querySphereTriangleMeshFreeFlightGuard(this,body,gravity,triangles,horizon,settings,sphereTriangleMeshResult);
  }
  queryAcceleratedSpheres(a,b,horizon,settings={}){
    const count=this.inputF64([...acceleratedSphereInput(a),...acceleratedSphereInput(b),horizon,...acceleratedSettings(settings)]);
    this.check(this.native._pp_sim_accelerated_spheres(count));return acceleratedResult(this.output());
  }
  queryAcceleratedPlane(sphere,plane={},horizon,settings={}){
    const {normal=[0,1,0],offset=0}=plane;
    for(const field of ['velocity','acceleration'])if(plane[field]!==undefined&&finiteArray(plane[field],3,'Plane '+field).some(x=>x!==0))throw new Error('Accelerated query currently requires a static plane');
    const count=this.inputF64([...acceleratedSphereInput(sphere),...finiteArray(normal,3,'Plane normal'),offset,horizon,...acceleratedSettings(settings)]);
    this.check(this.native._pp_sim_accelerated_plane(count));return acceleratedResult(this.output());
  }
  queryDielectricInterface({incident=[0,-1,0],normal=[0,1,0],indexIncident=1,indexTransmitted=1.5,vacuumWavelength=550e-9}={}){
    const count=this.inputF64([...finiteArray(incident,3,'Incident propagation'),...finiteArray(normal,3,'Interface normal'),indexIncident,indexTransmitted,vacuumWavelength]);
    this.check(this.native._pp_sim_dielectric_interface(count));return opticsResult(this.output());
  }
  queryOpticalSurface({origin,direction,minimumParameter=0,maximumParameter=1e6},surface,{parameterTolerance=1e-8,maxSqrtRefinements=128}={}){
    const kinds={disk:0,sphere:1,cap:2},kind=kinds[surface.kind];
    if(kind===undefined)throw new Error('Optical surface kind requires disk, sphere or cap');
    const center=kind===2?surface.vertex:surface.center;
    const axis=kind===0?(surface.normal??[0,0,1]):kind===2?(surface.axis??[0,0,1]):[0,0,0];
    const radius=kind===0?0:kind===1?surface.radius:surface.signedRadius;
    const aperture=kind===1?0:surface.apertureRadius;
    const count=this.inputF64([kind,...finiteArray(origin,3,'Ray origin'),...finiteArray(direction,3,'Ray direction'),minimumParameter,maximumParameter,
      ...finiteArray(center,3,'Surface center/vertex'),...finiteArray(axis,3,'Surface normal/axis'),radius,aperture,parameterTolerance,maxSqrtRefinements]);
    this.check(this.native._pp_sim_optical_geometry(count));return geometryResult(this.output());
  }
  queryPolarizedInterface({incident=[0,-1,0],normal=[0,1,0],indexIncident=1,indexTransmitted=1.5,vacuumWavelength=550e-9,
    transverseReference=[1,0,0],power=[1,0,0,0]}={}){
    const count=this.inputF64([...finiteArray(incident,3,'Incident propagation'),...finiteArray(normal,3,'Interface normal'),indexIncident,indexTransmitted,vacuumWavelength,
      ...finiteArray(transverseReference,3,'Transverse reference'),...finiteArray(power,4,'Stokes power')]);
    this.check(this.native._pp_sim_polarized_interface(count));return polarizationResult(this.output());
  }
  queryDispersion(model,wavelength,{maximumPhaseWidth=1e6,maxSqrtRefinements=128}={}){
    const kinds={cauchy:0,sellmeier:1},kind=kinds[model.kind];
    if(kind===undefined)throw new Error('Dispersion model requires cauchy or sellmeier');
    const band=typeof wavelength==='number'?[wavelength,wavelength]:finiteArray(wavelength,2,'Vacuum wavelength band');
    const valid=finiteArray(model.validBand??[1e-12,1],2,'Declared wavelength band');
    const terms=kind===1?(model.terms??[]):[];
    if(!Array.isArray(terms)||terms.length>8)throw new Error('At most eight Sellmeier terms');
    const slots=Array(16).fill(0);for(let j=0;j<terms.length;++j)slots.splice(2*j,2,...finiteArray(terms[j],2,'Sellmeier B,C'));
    const c=kind===0?finiteArray(model.coefficients??[1,0,0],3,'Cauchy A,B,C'):[0,0,0];
    const count=this.inputF64([kind,...band,...valid,maximumPhaseWidth,maxSqrtRefinements,...c,terms.length,...slots]);
    this.check(this.native._pp_sim_dispersion(count));const a=this.output();
    const statuses=['resolved','nonphysical','unresolved'],reasons=['none','pole_not_excluded','nonpositive_phase','nonpositive_squared_phase','positivity_uncertain','refinement_budget','phase_width','numerical_range'];
    if(a.length!==14||a.some(Number.isNaN)||!statuses[a[0]]||!reasons[a[1]])throw new Error('Invalid C++ dispersion output');
    return {status:statuses[a[0]],reason:reasons[a[1]],sqrtRefinements:a[3],squaredPhase:a[4]?a.slice(5,7):null,
      values:a[2]?{phase:a.slice(7,9),derivative:a.slice(9,11),group:a.slice(11,13),withinInterfaceDomain:Boolean(a[13])}:null};
  }
  queryBoundedSurface({origin,direction,minimumParameter=0,maximumParameter=1e6},surface,{maximumParameterWidth=1e6,maxSqrtRefinements=128}={}){
    const kinds={disk:0,sphere:1,cap:2},kind=kinds[surface.kind];if(kind===undefined)throw new Error('Bounded optical surface kind requires disk, sphere or cap');
    const center=kind===2?surface.vertex:surface.center,axis=kind===0?(surface.normal??[0,0,1]):kind===2?(surface.axis??[0,0,1]):[0,0,0];
    const radius=kind===0?0:kind===1?surface.radius:surface.signedRadius,aperture=kind===1?0:surface.apertureRadius;
    const count=this.inputF64([kind,...boundsVectorInput(origin,'Ray origin'),...boundsVectorInput(direction,'Ray direction'),minimumParameter,maximumParameter,
      ...finiteArray(center,3,'Surface center/vertex'),...finiteArray(axis,3,'Surface normal/axis'),radius,aperture,maximumParameterWidth,maxSqrtRefinements]);
    this.check(this.native._pp_sim_bounded_geometry(count));return boundedGeometryResult(this.output());
  }
  queryBoundedInterface({incident=[0,-1,0],normal=[0,1,0],indexIncident=1,indexTransmitted=1.5,vacuumWavelength=550e-9}={},
    {maximumParameterWidth=1e6,maxSqrtRefinements=128}={}){
    const count=this.inputF64([...boundsVectorInput(incident,'Incident propagation'),...boundsVectorInput(normal,'Incident-side normal'),
      ...intervalInput(indexIncident,'Incident index'),...intervalInput(indexTransmitted,'Transmitted index'),vacuumWavelength,maximumParameterWidth,maxSqrtRefinements]);
    this.check(this.native._pp_sim_bounded_interface(count));return boundedInterfaceResult(this.output());
  }
  makeOpticalLaunchRay(source,launchPoint,{minimumParameter=0,maximumParameter=1e6}={}){
    const kinds={finite:0,parallel:1};if(!source||!Object.hasOwn(kinds,source.kind))throw new Error('Optical source requires finite or parallel');
    if(typeof this.native._pp_sim_optical_launch_ray!=='function')throw new Error('Optical launch WASM API unavailable; rebuild the common C++ runtime');
    const reference=source.kind==='finite'?source.position:source.direction;
    const n=this.inputF64([kinds[source.kind],...finiteArray(reference,3,'Source reference'),...finiteArray(launchPoint,3,'Launch point'),minimumParameter,maximumParameter]);
    this.check(this.native._pp_sim_optical_launch_ray(n));const a=this.output();
    if(a.length!==14||!a.every(Number.isFinite))throw new Error('Invalid C++ optical launch output');
    return {origin:vectorBounds(a,0),direction:vectorBounds(a,6),minimumParameter:a[12],maximumParameter:a[13]};
  }
  bindSkin(rest,settings={}){
    skinApi(this.native);
    const encoded=skinMatrices(rest,'Skin rest'),limits=skinSettings(settings);
    const count=this.inputF64([rest.length,...limits,0,0,...encoded]);
    this.check(this.native._pp_sim_skin_bind(count));
    return skinResult(this,'bind',rest.map(b=>b.id),0);
  }
  prepareDerivedMesh({positions,triangles},{maxVertices=2048,maxTriangles=32768,sqrtRefinements=128,readback='single'}={}){
    if(readback!=='single'&&readback!=='batch')throw new Error('Derived mesh readback must be single or batch');
    for(const name of ['_pp_sim_derived_mesh',readback==='batch'?'_pp_sim_derived_mesh_records':'_pp_sim_derived_mesh_record'])if(typeof this.native[name]!=='function')throw new Error('Derived mesh WASM API unavailable; rebuild the common C++ runtime');
    if(!Array.isArray(positions)||positions.length>2048||!Array.isArray(triangles)||triangles.length>32768)throw new Error('Derived mesh SDK allows at most 2048 vertices and 32768 triangles; inputs are not split or truncated');
    const uint=value=>{if(!Number.isInteger(value)||value<0||value>0xffffffff)throw new Error('Derived mesh exchange requires uint32 settings and indices');return value;};
    const p=Array.from(positions,v=>finiteArray(v,3,'Derived mesh position'));
    const t=Array.from(triangles,v=>finiteArray(v,3,'Derived mesh triangle').map(uint));
    const n=this.inputF64([p.length,t.length,uint(maxVertices),uint(maxTriangles),uint(sqrtRefinements),0,0,0,...p.flat()]);
    const nt=this.inputU32(t.flat());this.check(this.native._pp_sim_derived_mesh(n,nt));
    return derivedMeshResult(this,p.length,t,readback);
  }
  deformSkin({joints,pose,vertices},settings={}){
    skinApi(this.native);
    if(!Array.isArray(joints)||joints.length>128||!Array.isArray(vertices)||vertices.length>2048)throw new Error('Skin SDK requires at most 128 joints and 2048 vertices; inputs are not split or truncated');
    const encodedJoints=Array.from(joints,b=>[validBodyId(b.id),...finiteArray(b.restWorld,16,'Skin rest world'),...finiteArray(b.inverseBind,16,'Skin inverse bind')]).flat();
    const encodedPose=skinMatrices(pose,'Skin pose'),encodedVertices=[],influences=[];
    for(const v of vertices){
      if(!v||!Array.isArray(v.influences)||v.influences.length>8192||influences.length/2+v.influences.length>8192)throw new Error('Skin SDK total influence limit is 8192; inputs are not split or truncated');
      encodedVertices.push(...finiteArray(v.position,3,'Skin vertex position'),v.influences.length);
      for(const w of v.influences)influences.push(validBodyId(w.id),w.weight);
    }
    const count=this.inputF64([joints.length,pose.length,vertices.length,influences.length/2,...skinSettings(settings),0,0,0,...encodedJoints,...encodedPose,...encodedVertices,...influences]);
    this.check(this.native._pp_sim_skin_deform(count));
    return skinResult(this,'deform',joints.map(b=>b.id),vertices.length);
  }
  sampleMotion({bones,clip},seconds,{loop=false,maximumBones=128,maximumTracks=128,maximumKeys=4096}={}){
    if(typeof loop!=='boolean'||!Array.isArray(bones)||bones.length>128||!clip||!Array.isArray(clip.tracks)||clip.tracks.length>128)throw new Error('Motion requires bones, clip tracks and explicit loop boolean');
    for(const name of ['_pp_sim_motion','_pp_sim_motion_bone'])if(typeof this.native[name]!=='function')throw new Error('Motion WASM API unavailable; rebuild the common C++ runtime');
    const trs=p=>[...finiteArray(p.position,3,'Motion position'),...finiteArray(p.rotation,4,'Motion quaternion'),...finiteArray(p.scale,3,'Motion scale')];
    let keyCount=0;const tracks=[];for(const t of clip.tracks){if(!Array.isArray(t.keys)||!['linear','step'].includes(t.interpolation))throw new Error('Motion track requires keys and linear/step interpolation');keyCount+=t.keys.length;if(keyCount>4096)throw new Error('Motion total key budget exceeded');tracks.push(validBodyId(t.boneId),t.interpolation==='step'?1:0,t.keys.length);for(const k of t.keys)tracks.push(k.time,...trs(k));}
    const encodedBones=bones.flatMap(b=>[validBodyId(b.id),b.parentId===0?0:validBodyId(b.parentId),...trs(b.rest)]);
    const count=this.inputF64([bones.length,clip.tracks.length,keyCount,clip.duration,seconds,loop?1:0,maximumBones,maximumTracks,maximumKeys,0,...encodedBones,...tracks]);this.check(this.native._pp_sim_motion(count));const a=this.output(),statuses=['completed','invalid_input','budget_exceeded','numerical_failure'];
    if(a.length!==10||!a.every(Number.isFinite)||!statuses[a[0]]||!Number.isInteger(a[2])||a[2]<0||a[2]>bones.length||a[9]!==0||Boolean(a[1])!==(a[0]===0))throw new Error('Invalid C++ motion summary');
    const result={status:statuses[a[0]],requestedTime:a[3],sampledTime:a[1]?a[4]:null,playback:a[6]?'loop':'clamp',duration:a[5],bones:[],evaluationOrder:[]};
    for(let j=0;j<a[2];++j){this.check(this.native._pp_sim_motion_bone(j));const b=this.output();if(b.length!==45||!b.every(Number.isFinite)||b[0]!==bones[j].id||b[1]!==bones[j].parentId||!Number.isInteger(b[44])||b[44]<0||b[44]>=a[2])throw new Error('Invalid C++ motion bone');result.bones.push({id:b[0],parentId:b[1],local:{position:b.slice(2,5),rotation:b.slice(5,9),scale:b.slice(9,12)},localMatrix:b.slice(12,28),worldMatrix:b.slice(28,44),worldPosition:b.slice(40,43),evaluationRank:b[44]});}
    if(result.bones.length){const ordered=[...result.bones].sort((x,y)=>x.evaluationRank-y.evaluationRank);if(ordered.some((b,j)=>b.evaluationRank!==j))throw new Error('Duplicate C++ motion rank');result.evaluationOrder=ordered.map(b=>b.id);}
    return result;
  }
  queryPolarizedPacket({packets,steps=[],sensor,index=1,vacuumWavelength=550e-9,sensorMinimumParameter=0,sensorMaximumParameter=1e6},
    {maximumRouteSteps=64,maximumParameterWidth=1e6,maxSqrtRefinements=128,powerMaxSqrtRefinements=128,maximumPackets=1024,maximumPacketEvaluations=1024,maximumTotalSqrtRefinements=1000000,maximumRouteSqrtRefinements=maximumTotalSqrtRefinements}={}){
    if(!Array.isArray(packets)||packets.length>1024||!Array.isArray(steps)||steps.length>64)throw new Error('Polarized packet query requires at most 1024 packets and 64 steps');
    if(!sensor||sensor.kind!=='disk')throw new Error('Polarized packet sensor requires disk geometry');
    for(const name of ['_pp_sim_polarized_packet','_pp_sim_polarized_packet_record','_pp_sim_polarized_packet_segment'])if(typeof this.native[name]!=='function')throw new Error('Polarized packet WASM API unavailable; rebuild the common C++ runtime');
    const encoded=[];
    for(const step of steps){const surface=step.surface,kinds={disk:0,sphere:1,cap:2},branches={reflected:0,transmitted:1};
      if(!surface||!Object.hasOwn(kinds,surface.kind)||!Object.hasOwn(branches,step.branch??'transmitted'))throw new Error('Invalid packet route surface or branch');
      const kind=kinds[surface.kind],center=kind===2?surface.vertex:surface.center,axis=kind===0?(surface.normal??[0,0,1]):kind===2?(surface.axis??[0,0,1]):[0,0,0];
      encoded.push(kind,...finiteArray(center,3,'Packet route anchor'),...finiteArray(axis,3,'Packet route axis'),kind===0?0:kind===1?surface.radius:surface.signedRadius,kind===1?0:surface.apertureRadius,
        branches[step.branch??'transmitted'],...intervalInput(step.nextIndex??1,'Packet route next index'),step.minimumParameter??0,step.maximumParameter??1e6);
    }
    const rays=packets.flatMap(packet=>[...boundsVectorInput(packet.ray.origin,'Packet origin'),...boundsVectorInput(packet.ray.direction,'Packet direction'),packet.ray.minimumParameter??0,packet.ray.maximumParameter??1e6,
      ...finiteArray(packet.power,4,'Packet Stokes watts'),...finiteArray(packet.transverseReference??[1,0,0],3,'Packet transverse reference')]);
    const n=this.inputF64([packets.length,steps.length,...intervalInput(index,'Packet initial index'),vacuumWavelength,...finiteArray(sensor.center,3,'Sensor center'),...finiteArray(sensor.normal??[0,0,-1],3,'Sensor normal'),sensor.apertureRadius,
      sensorMinimumParameter,sensorMaximumParameter,maximumRouteSteps,maximumParameterWidth,maxSqrtRefinements,maximumPackets,maximumPacketEvaluations,maximumTotalSqrtRefinements,powerMaxSqrtRefinements,maximumRouteSqrtRefinements,0,...encoded,...rays]);
    this.check(this.native._pp_sim_polarized_packet(n));const a=this.output(),statuses=['completed','unresolved','invalid_input','budget_exceeded','numerical_failure'];
    if(a.length!==24||!a.every(Number.isFinite)||!statuses[a[0]]||!Number.isInteger(a[1])||a[1]<0||a[1]>packets.length||a[23]!==0)throw new Error('Invalid C++ polarized packet summary');
    for(let j=1;j<=13;++j)if(!Number.isInteger(a[j])||a[j]<0)throw new Error('Invalid C++ packet counter');
    const result={status:statuses[a[0]],records:[],counts:{accepted:a[3],routeMiss:a[4],branchUnavailable:a[5],sensorMiss:a[6],unknown:a[7],notExamined:0},evaluations:a[2],geometryQueries:a[8],interfaceQueries:a[9],sensorQueries:a[10],
      geometrySqrtRefinements:a[11],powerSqrtRefinements:a[12],sensorSqrtRefinements:a[13],refinementLimited:Boolean(a[14]),stats:a[15]?{totalSourcePower:a.slice(16,18),acceptedSourcePower:a.slice(18,20),detectedPower:a.slice(20,22)}:null};
    const get=(j,part)=>{this.check(this.native._pp_sim_polarized_packet_record(j,part));return this.output();};
    for(let j=0;j<a[1];++j){const b=get(j,0),packetStatuses=['not_examined','accepted','route_miss','branch_unavailable','sensor_miss','route_unresolved','power_unresolved','sensor_unresolved','invalid_input','budget_exceeded','numerical_failure'];
      if(b.length!==12||!b.every(Number.isFinite)||b[0]!==j||!packetStatuses[b[1]]||b[11]!==0)throw new Error('Invalid C++ packet snapshot');
      const record={packetIndex:j,power:b.slice(2,6),status:packetStatuses[b[1]],route:null,sensor:b[7]?boundedGeometryResult(get(j,3)):null,sensorPower:b[8]?b.slice(9,11):null};
      if(b[6])record.route=polarizedRouteResult(get(j,1),()=>get(j,2),(k,part)=>{this.check(this.native._pp_sim_polarized_packet_segment(j,k,part));return this.output();});
      if(record.status==='not_examined')++result.counts.notExamined;result.records.push(record);
    }
    if(result.stats&&(result.status!=='completed'||result.counts.unknown!==0))throw new Error('C++ packet tally contains unresolved records');
    return result;
  }
  queryOpticalSpot({samples,steps=[],sensor,index=1,vacuumWavelength=550e-9,sensorMinimumParameter=0,sensorMaximumParameter=1e6},
    {maximumRouteSteps=64,maximumParameterWidth=1e6,maxSqrtRefinements=128,maximumSamples=1024,maximumSampleEvaluations=1024,maximumTotalSqrtRefinements=1000000}={}){
    if(!Array.isArray(samples)||samples.length>1024||!Array.isArray(steps)||steps.length>64)throw new Error('Optical spot requires at most 1024 samples and 64 steps');
    if(!sensor||sensor.kind!=='disk')throw new Error('Optical spot sensor requires disk geometry');
    if(typeof this.native._pp_sim_optical_spot!=='function'||typeof this.native._pp_sim_optical_spot_sample!=='function')throw new Error('Optical spot WASM API unavailable; rebuild the common C++ runtime');
    const route=[];
    for(const step of steps){
      const surface=step.surface,kinds={disk:0,sphere:1,cap:2},branches={reflected:0,transmitted:1};
      if(!surface||!Object.hasOwn(kinds,surface.kind)||!Object.hasOwn(branches,step.branch??'transmitted'))throw new Error('Invalid spot route surface or branch');
      const kind=kinds[surface.kind],center=kind===2?surface.vertex:surface.center,axis=kind===0?(surface.normal??[0,0,1]):kind===2?(surface.axis??[0,0,1]):[0,0,0];
      route.push(kind,...finiteArray(center,3,'Spot route anchor'),...finiteArray(axis,3,'Spot route axis'),kind===0?0:kind===1?surface.radius:surface.signedRadius,
        kind===1?0:surface.apertureRadius,branches[step.branch??'transmitted'],...intervalInput(step.nextIndex??1,'Spot next index'),step.minimumParameter??0,step.maximumParameter??1e6);
    }
    const rays=samples.flatMap(sample=>[...boundsVectorInput(sample.ray.origin,'Spot origin'),...boundsVectorInput(sample.ray.direction,'Spot direction'),sample.ray.minimumParameter??0,sample.ray.maximumParameter??1e6,sample.weight??1]);
    const n=this.inputF64([samples.length,steps.length,...intervalInput(index,'Spot initial index'),vacuumWavelength,...finiteArray(sensor.center,3,'Sensor center'),...finiteArray(sensor.normal??[0,0,-1],3,'Sensor normal'),sensor.apertureRadius,
      sensorMinimumParameter,sensorMaximumParameter,maximumRouteSteps,maximumParameterWidth,maxSqrtRefinements,maximumSamples,maximumSampleEvaluations,maximumTotalSqrtRefinements,0,...route,...rays]);
    this.check(this.native._pp_sim_optical_spot(n));const a=this.output(),statuses=['completed','unresolved','invalid_input','budget_exceeded','numerical_failure'];
    if(a.length!==32||!a.every(Number.isFinite)||!statuses[a[0]]||!Number.isInteger(a[1])||a[1]<0||a[1]>samples.length)throw new Error('Invalid C++ optical spot summary');
    const result={status:statuses[a[0]],records:[],counts:{accepted:a[3],routeMiss:a[4],branchUnavailable:a[5],sensorMiss:a[6],unknown:a[7],notExamined:0},evaluations:a[2],geometryQueries:a[8],interfaceQueries:a[9],sqrtRefinements:a[10],refinementLimited:Boolean(a[11]),
      stats:a[12]?{totalWeight:a.slice(14,16),acceptedWeight:a.slice(16,18),moments:a[13]?{centroid:vectorBounds(a,18),meanSquaredRadius:a.slice(24,26),hull:vectorBounds(a,26)}:null}:null};
    for(let j=0;j<a[1];++j){
      this.check(this.native._pp_sim_optical_spot_sample(j,0));const b=this.output(),statuses=['not_examined','accepted','route_miss','branch_unavailable','sensor_miss','route_unresolved','sensor_unresolved','budget_exceeded','invalid_input','numerical_failure'];
      if(b.length!==34||!b.every(Number.isFinite)||b[0]!==j||!statuses[b[2]]||(b[3]&&!routeStatuses[b[4]]))throw new Error('Invalid C++ optical spot sample');
      const record={sampleIndex:j,weight:b[1],status:statuses[b[2]],route:b[3]?{status:routeStatuses[b[4]],completedSteps:b[5],failedStep:b[6],geometryQueries:b[7],interfaceQueries:b[8],sqrtRefinements:b[9],refinementLimited:Boolean(b[10]),
        completion:b[11]?{ray:{origin:vectorBounds(b,12),direction:vectorBounds(b,18),minimumParameter:b[24],maximumParameter:b[25]},index:b.slice(26,28),totals:{distance:b.slice(28,30),opticalPathLength:b.slice(30,32),throughput:b.slice(32,34)}}:null}:null,sensor:null};
      this.check(this.native._pp_sim_optical_spot_sample(j,1));const c=this.output();
      if(c.length!==46||!c.every(Number.isFinite)||c[0]!==j||c[1]!==b[1]||c[2]!==b[2]||c[4]!==0)throw new Error('Inconsistent C++ optical spot sensor snapshot');
      if(c[3])record.sensor=boundedGeometryResult(c.slice(5));if(record.status==='not_examined')++result.counts.notExamined;result.records.push(record);
    }
    return result;
  }
  queryNearestOpticalSurface({origin,direction,minimumParameter=0,maximumParameter=1e6},surfaces,
    {maximumParameterWidth=1e6,maxSqrtRefinements=128,maximumSurfaces=128,maximumQueries=512,maximumTotalSqrtRefinements=16384,allowPrefixExclusion=true}={}){
    if(!Array.isArray(surfaces)||surfaces.length>1024)throw new Error('Nearest optical selection requires at most 1024 surfaces');
    if(typeof allowPrefixExclusion!=='boolean')throw new Error('Prefix exclusion must be a boolean');
    if(typeof this.native._pp_sim_optical_selection!=='function'||typeof this.native._pp_sim_optical_selection_surface!=='function')throw new Error('Optical selection WASM API unavailable; rebuild the common C++ runtime');
    const encoded=[];
    for(const record of surfaces){
      const id=validBodyId(record.id),surface=record.surface,kinds={disk:0,sphere:1,cap:2};
      if(!surface||!Object.hasOwn(kinds,surface.kind))throw new Error('Selection surface kind requires disk, sphere or cap');
      const kind=kinds[surface.kind],center=kind===2?surface.vertex:surface.center;
      const axis=kind===0?(surface.normal??[0,0,1]):kind===2?(surface.axis??[0,0,1]):[0,0,0];
      const radius=kind===0?0:kind===1?surface.radius:surface.signedRadius,aperture=kind===1?0:surface.apertureRadius;
      encoded.push(id,kind,...finiteArray(center,3,'Selection center/vertex'),...finiteArray(axis,3,'Selection normal/axis'),radius,aperture);
    }
    const n=this.inputF64([...boundsVectorInput(origin,'Selection ray origin'),...boundsVectorInput(direction,'Selection ray direction'),minimumParameter,maximumParameter,
      maximumParameterWidth,maxSqrtRefinements,maximumSurfaces,maximumQueries,maximumTotalSqrtRefinements,allowPrefixExclusion?1:0,surfaces.length,...encoded]);
    this.check(this.native._pp_sim_optical_selection(n));const r=opticalSelectionResult(this.output());r.surfaces=[];
    for(let j=0;j<r.surfaceCount;++j){
      this.check(this.native._pp_sim_optical_selection_surface(j,0));const a=this.output(),d=opticalSelectionSurface(a);
      if(a[2]){this.check(this.native._pp_sim_optical_selection_surface(j,1));const b=this.output(),p=opticalSelectionSurface(b);if(p.id!==d.id||!b[4])throw new Error('Inconsistent C++ optical prefix snapshot');d.prefix=p.geometry;}
      if(j&&d.id<=r.surfaces[j-1].id)throw new Error('C++ selection diagnostics are not canonical');r.surfaces.push(d);
    }
    if(r.nearest&&!r.surfaces.some(d=>d.id===r.nearest.id))throw new Error('C++ selection winner has no diagnostic');
    return r;
  }
  tracePolarizedRoute({origin,direction,minimumParameter=0,maximumParameter=1e6},steps,
    {index=1,vacuumWavelength=550e-9,transverseReference=[1,0,0],power=[1,0,0,0],maximumSteps=64,maximumParameterWidth=1e6,maxSqrtRefinements=128,powerMaxSqrtRefinements=128,maximumTotalSqrtRefinements=1000000}={}){
    if(!Array.isArray(steps)||steps.length>64)throw new Error('Polarized route requires at most 64 steps');
    for(const name of ['_pp_sim_polarized_route','_pp_sim_polarized_route_initial','_pp_sim_polarized_route_segment'])if(typeof this.native[name]!=='function')throw new Error('Polarized route WASM API unavailable; rebuild the common C++ runtime');
    const encoded=[];
    for(const step of steps){const surface=step.surface,kinds={disk:0,sphere:1,cap:2},branches={reflected:0,transmitted:1};
      if(!surface||!Object.hasOwn(kinds,surface.kind)||!Object.hasOwn(branches,step.branch??'transmitted'))throw new Error('Invalid polarized route surface or branch');
      const kind=kinds[surface.kind],center=kind===2?surface.vertex:surface.center,axis=kind===0?(surface.normal??[0,0,1]):kind===2?(surface.axis??[0,0,1]):[0,0,0];
      encoded.push(kind,...finiteArray(center,3,'Polarized route anchor'),...finiteArray(axis,3,'Polarized route axis'),kind===0?0:kind===1?surface.radius:surface.signedRadius,kind===1?0:surface.apertureRadius,
        branches[step.branch??'transmitted'],...intervalInput(step.nextIndex??1,'Polarized route next index'),step.minimumParameter??0,step.maximumParameter??1e6);
    }
    const n=this.inputF64([...boundsVectorInput(origin,'Polarized route origin'),...boundsVectorInput(direction,'Polarized route direction'),minimumParameter,maximumParameter,...intervalInput(index,'Initial polarized route index'),vacuumWavelength,
      maximumSteps,maximumParameterWidth,maxSqrtRefinements,steps.length,...finiteArray(transverseReference,3,'Transverse reference'),...finiteArray(power,4,'Point Stokes power'),powerMaxSqrtRefinements,maximumTotalSqrtRefinements,0,...encoded]);
    this.check(this.native._pp_sim_polarized_route(n));return polarizedRouteResult(this.output(),()=>{this.check(this.native._pp_sim_polarized_route_initial());return this.output();},(j,part)=>{this.check(this.native._pp_sim_polarized_route_segment(j,part));return this.output();});
  }
  traceOpticalRoute({origin,direction,minimumParameter=0,maximumParameter=1e6},steps,
    {index=1,vacuumWavelength=550e-9,maximumSteps=64,maximumParameterWidth=1e6,maxSqrtRefinements=128}={}){
    if(!Array.isArray(steps)||steps.length>64)throw new Error('Explicit optical route requires at most 64 steps');
    const encoded=[];
    for(const step of steps){
      const surface=step.surface,kinds={disk:0,sphere:1,cap:2},kind=kinds[surface?.kind];if(kind===undefined)throw new Error('Route surface kind requires disk, sphere or cap');
      const branches={reflected:0,transmitted:1},branch=branches[step.branch??'transmitted'];if(branch===undefined)throw new Error('Route branch requires reflected or transmitted');
      const center=kind===2?surface.vertex:surface.center,axis=kind===0?(surface.normal??[0,0,1]):kind===2?(surface.axis??[0,0,1]):[0,0,0];
      const radius=kind===0?0:kind===1?surface.radius:surface.signedRadius,aperture=kind===1?0:surface.apertureRadius;
      encoded.push(kind,...finiteArray(center,3,'Route center/vertex'),...finiteArray(axis,3,'Route normal/axis'),radius,aperture,branch,
        ...intervalInput(step.nextIndex??1,'Route other-side index'),step.minimumParameter??0,step.maximumParameter??1e6);
    }
    const n=this.inputF64([...boundsVectorInput(origin,'Route origin'),...boundsVectorInput(direction,'Route direction'),minimumParameter,maximumParameter,
      ...intervalInput(index,'Initial route index'),vacuumWavelength,maximumSteps,maximumParameterWidth,maxSqrtRefinements,steps.length,...encoded]);
    this.check(this.native._pp_sim_optical_route(n));const result=routeResult(this.output());result.segments=[];
    for(let j=0;j<result.segmentCount;++j){this.check(this.native._pp_sim_optical_route_segment(j));result.segments.push(routeSegmentResult(this.output()));}
    return result;
  }
}
function intervalInput(value,label){
  const a=typeof value==='number'?[value,value]:finiteArray(value,2,label);
  if(!a.every(Number.isFinite)||a[0]>a[1])throw new Error(label+' requires an ordered finite interval');return a;
}
function boundsVectorInput(value,label){
  const a=Array.from(value??[]);if(a.length!==3)throw new Error(label+' requires three components or bounds');
  return a.flatMap(component=>intervalInput(component,label));
}
const boundedReasons=['none','zero_direction','zero_normal','parallel_or_coplanar','no_real_roots','tangent_or_discriminant','parameter_boundary','aperture_boundary','cap_boundary','orientation','precision_limit','refinement_budget','incident_side','critical_angle','numerical_domain'];
const vectorBounds=(a,o)=>[a.slice(o,o+2),a.slice(o+2,o+4),a.slice(o+4,o+6)];
function boundedGeometryResult(a){
  if(a.length!==41||!a.every(Number.isFinite)||!geometryStatuses[a[0]]||!boundedReasons[a[1]])throw new Error('Invalid C++ bounded geometry output');
  const candidates=[10,14].slice(0,a[3]).map(o=>({parameter:a.slice(o,o+2),state:geometryCandidateStates[a[o+2]],reason:boundedReasons[a[o+3]]}));
  if(candidates.some(c=>!c.state||!c.reason))throw new Error('Invalid C++ bounded candidate tags');
  return {status:geometryStatuses[a[0]],reason:boundedReasons[a[1]],rootCount:a[3],consideredCount:a[4],sqrtRefinements:a[5],refinementLimited:Boolean(a[6]),
    discriminant:a[7]?a.slice(8,10):null,candidates,hit:a[2]?{parameter:a.slice(18,20),physicalDistance:a.slice(20,22),position:vectorBounds(a,22),geometricNormal:vectorBounds(a,28),incidentNormal:vectorBounds(a,34),frontFace:Boolean(a[40])}:null};
}
function boundedInterfaceResult(a){
  const kinds=['transmission','total_internal_reflection','unresolved'];
  if(a.length!==59||!a.every(Number.isFinite)||!kinds[a[0]]||!boundedReasons[a[1]]||a[58]!==0)throw new Error('Invalid C++ bounded interface output');
  return {kind:kinds[a[0]],reason:boundedReasons[a[1]],sqrtRefinements:a[2],refinementLimited:Boolean(a[3]),exactGrazing:Boolean(a[4]),vacuumWavelength:a[5],
    incidentUnit:a[6]?vectorBounds(a,14):null,normalUnit:a[7]?vectorBounds(a,20):null,reflected:a[8]?vectorBounds(a,26):null,transmitted:a[9]?vectorBounds(a,32):null,
    power:a[10]?{reflectanceS:a.slice(38,40),transmittanceS:a.slice(40,42),reflectanceP:a.slice(42,44),transmittanceP:a.slice(44,46),reflectanceUnpolarized:a.slice(46,48),transmittanceUnpolarized:a.slice(48,50)}:null,
    cosineIncident:a[11]?a.slice(50,52):null,cosineTransmitted:a[12]?a.slice(52,54):null,discriminant:a[13]?a.slice(54,56):null,incidentDot:a.slice(56,58)};
}
const opticalSelectionStatuses=['hit','miss','unresolved','invalid_input','budget_exceeded','numerical_failure'];
function opticalSelectionResult(a){
  if(a.length!==31||!a.every(Number.isFinite)||!opticalSelectionStatuses[a[0]]||![0,1].includes(a[1])||Boolean(a[1])!==(a[0]===0))throw new Error('Invalid C++ optical selection summary');
  for(const j of [2,3,4,5,6])if(!Number.isSafeInteger(a[j])||a[j]<0)throw new Error('Invalid C++ optical selection counter/ID');
  if(a[3]>1024||(a[1]&&a[2]<1))throw new Error('Invalid C++ optical selection winner/size');
  return {status:opticalSelectionStatuses[a[0]],surfaceCount:a[3],geometryQueries:a[4],prefixQueries:a[5],sqrtRefinements:a[6],refinementLimited:Boolean(a[7]),
    nearest:a[1]?{id:a[2],hit:{parameter:a.slice(8,10),physicalDistance:a.slice(10,12),position:vectorBounds(a,12),geometricNormal:vectorBounds(a,18),incidentNormal:vectorBounds(a,24),frontFace:Boolean(a[30])}}:null};
}
function opticalSelectionSurface(a){
  if(a.length!==46||!a.every(Number.isFinite)||!Number.isSafeInteger(a[0])||a[0]<1||a.slice(1,5).some(x=>x!==0&&x!==1))throw new Error('Invalid C++ optical selection surface');
  return {id:a[0],geometry:a[4]?boundedGeometryResult(a.slice(5)):null,prefix:null,excludedByPrefix:Boolean(a[3])};
}
const complexBoundsResult=(a,o)=>({real:a.slice(o,o+2),imag:a.slice(o+2,o+4)});
function coherencyResult(a,o){return {diagonal:[a.slice(o,o+2),a.slice(o+2,o+4),a.slice(o+4,o+6)],upper:[complexBoundsResult(a,o+6),complexBoundsResult(a,o+10),complexBoundsResult(a,o+14)]};}
const routeStatuses=['completed','geometry_miss','geometry_unresolved','interface_unresolved','branch_unavailable','invalid_input','budget_exceeded','numerical_failure'];
function routeResult(a){
  if(a.length!==31||!a.every(Number.isFinite)||!routeStatuses[a[0]])throw new Error('Invalid C++ optical route summary');
  return {status:routeStatuses[a[0]],completedSteps:a[1],failedStep:a[2],segmentCount:a[3],geometryQueries:a[5],sqrtRefinements:a[6],refinementLimited:Boolean(a[7]),vacuumWavelength:a[30],
    completion:a[4]?{ray:{origin:vectorBounds(a,8),direction:vectorBounds(a,14),minimumParameter:a[28],maximumParameter:a[29]},index:a.slice(20,22),totals:{distance:a.slice(22,24),opticalPathLength:a.slice(24,26),throughput:a.slice(26,28)}}:null};
}
function routeSegmentResult(a){
  const branches=['reflected','transmitted'],kinds=['transmission','total_internal_reflection','unresolved'];
  if(a.length!==64||!a.every(Number.isFinite)||!branches[a[0]]||!geometryStatuses[a[2]]||!boundedReasons[a[3]]||a[63]!==0)throw new Error('Invalid C++ optical route segment');
  if(a[4]&&(!kinds[a[5]]||!boundedReasons[a[6]]))throw new Error('Invalid C++ optical route interface tags');
  if(a[7]&&!a[1])throw new Error('C++ optical outgoing ray has no hit position');
  return {branch:branches[a[0]],incoming:{origin:vectorBounds(a,10),direction:vectorBounds(a,16),minimumParameter:a[22],maximumParameter:a[23]},incidentIndex:a.slice(24,26),otherIndex:a.slice(26,28),
    geometry:{status:geometryStatuses[a[2]],reason:boundedReasons[a[3]],consideredCount:a[60],rootCount:a[61],hit:a[1]?{position:vectorBounds(a,28),parameter:a.slice(34,36),physicalDistance:a.slice(36,38),incidentNormal:vectorBounds(a,38),frontFace:Boolean(a[62])}:null},
    interface:a[4]?{kind:kinds[a[5]],reason:boundedReasons[a[6]]}:null,outgoing:a[7]?{origin:vectorBounds(a,28),direction:vectorBounds(a,44),minimumParameter:0,maximumParameter:1e6}:null,
    factor:a[8]?a.slice(50,52):null,accumulated:a[9]?{distance:a.slice(52,54),opticalPathLength:a.slice(54,56),throughput:a.slice(56,58)}:null,sqrtRefinements:a[58],refinementLimited:Boolean(a[59])};
}
const supportFailures=['none','invalid_input','geometry_incompatible','geometry_uncertain','impact_required','velocity_uncertain','static_constraint','pair_budget','contact_budget','ill_conditioned','iteration_budget','numerical_uncertainty','numerical_failure'];
function supportSettings({gapTolerance=1e-8,velocityIntervalTolerance=1e-9,accelerationTolerance=1e-8,complementarityTolerance=1e-7,projectedForceTolerance=1e-8,
  minimumScaledPivot=1e-10,maximumForce=1e24,maxIterations=20000,maxContacts=128,maxPairQueries=100000}={}){
  return [gapTolerance,velocityIntervalTolerance,accelerationTolerance,complementarityTolerance,projectedForceTolerance,minimumScaledPivot,maximumForce,maxIterations,maxContacts,maxPairQueries];
}
function supportResult(a){
  if(a.length!==21||!a.every(Number.isFinite)||!supportFailures[a[1]])throw new Error('Invalid C++ support summary');
  return {success:Boolean(a[0]),failure:supportFailures[a[1]],pairQueries:a[2],separatedPairs:a[3],restingConstraints:a[4],separatingConstraints:a[5],iterations:a[6],
    maximumGeometryOffset:a[7],maximumVelocityIntervalWidth:a[8],minimumScaledPivot:a[9],residuals:{negativeForce:a[10],negativeAcceleration:a[11],complementarity:a[12],projectedForce:a[13],maximumAccelerationIntervalWidth:a[14]},
    constraintCount:a[15],bodyCount:a[16],firstId:a[17],secondId:a[18],queryTime:a[19],queryTicks:a[20]};
}
const supportedFailures=['none','invalid_input','initial_geometry','pair_budget','contact_budget','attempt_budget','segment_budget','event_budget','minimum_step','constraint_failure','trajectory_failure','impulse_failure','energy_failure','numerical_failure','guard_budget'];
const constraintFailures=['none','invalid_input','initial_geometry','initial_velocity','static_constraint','ill_conditioned','newton_budget','linear_budget','line_search','normal_rotation','release_required','residual','numerical_failure','contact_budget'];
const trajectoryFailures=['none','invalid_input','penetration_witness','pair_budget','evaluation_budget','depth_budget','numerical_uncertainty','numerical_failure'];
function supportedSettings({maximumSubstep=1/240,minimumSubstep=1e-10,spatialTolerance=1e-7,contactBand=5e-8,velocityTolerance=1e-9,
  positionErrorTolerance=1e-6,velocityErrorTolerance=1e-5,orientationErrorTolerance=1e-5,relativeImpactEnergyTolerance=1e-10,
  maxAttempts=16384,maxSegments=4096,maxEvents=512,maxPairQueries=1000000,maxGuardEvaluations=4000000,
  maxNewtonIterations=32,maxLinearSolves=64,maxLineSearchSteps=16,maxContacts=128,minimumScaledPivot=1e-10,
  positionTolerance=1e-10,normalVelocityTolerance=1e-10,maximumNormalRotation=.5,maximumAngularIncrement=.5,
  guardMaxDepth=48,guardEvaluationsPerSegment=1000000,impulseIterations=128,guardPairsPerSegment=100000,maximumImpulse=1e24,
  initialGapTolerance=1e-7,initialVelocityTolerance=1e-8,positionEquationTolerance=1e-10,velocityEquationTolerance=1e-10}={}){
  return [maximumSubstep,minimumSubstep,spatialTolerance,contactBand,velocityTolerance,positionErrorTolerance,velocityErrorTolerance,orientationErrorTolerance,relativeImpactEnergyTolerance,
    maxAttempts,maxSegments,maxEvents,maxPairQueries,maxGuardEvaluations,maxNewtonIterations,maxLinearSolves,maxLineSearchSteps,maxContacts,minimumScaledPivot,positionTolerance,normalVelocityTolerance,
    maximumNormalRotation,maximumAngularIncrement,guardMaxDepth,guardEvaluationsPerSegment,impulseIterations,guardPairsPerSegment,maximumImpulse,initialGapTolerance,initialVelocityTolerance,positionEquationTolerance,velocityEquationTolerance,0];
}
function supportedResult(a){
  if(a.length!==32||!a.every(Number.isFinite)||!supportedFailures[a[1]]||!constraintFailures[a[25]]||!trajectoryFailures[a[26]])throw new Error('Invalid C++ supported World summary');
  return {success:Boolean(a[0]),failure:supportedFailures[a[1]],advancedDt:a[2],candidateTime:a[3],attempts:a[4],acceptedSegments:a[5],rejectedAttempts:a[6],constraintSolves:a[7],
    pairQueries:a[8],guardEvaluations:a[9],certifiedIntervals:a[10],minimumAcceptedSubstep:a[11],maximumGapResidual:a[12],maximumVelocityResidual:a[13],maximumPositionErrorEstimate:a[14],maximumVelocityErrorEstimate:a[15],maximumOrientationErrorEstimate:a[16],
    supportImpulseSum:a[17],impactImpulseSum:a[18],maximumNearContactGap:a[19],initialMechanicalEnergy:a[20],finalMechanicalEnergy:a[21],heldForceWork:a[22],mechanicalEnergyChange:a[23],timeRoundoff:a[24],
    lastConstraintFailure:constraintFailures[a[25]],lastGuardFailure:trajectoryFailures[a[26]],eventCount:a[27],firstId:a[28],secondId:a[29],time:a[30],ticks:a[31]};
}
const geometryStatuses=['hit','miss','unresolved'];
const geometryReasons=['none','no_real_roots','parallel','filtered_roots','parallel_or_coplanar','tangent_or_discriminant','parameter_boundary','aperture_boundary','cap_boundary','orientation','precision_limit','refinement_budget','numerical_output'];
const geometryCandidateStates=['not_examined','accepted','rejected_parameter','rejected_aperture','rejected_cap','unresolved'];
function geometryResult(a){
  if(a.length!==52||!a.every(Number.isFinite)||!geometryStatuses[a[0]]||!geometryReasons[a[1]])throw new Error('Invalid C++ optical geometry output');
  const bounds=o=>[a.slice(o,o+2),a.slice(o+2,o+4),a.slice(o+4,o+6)];
  const candidates=[10,14].map(o=>({parameter:a.slice(o,o+2),state:geometryCandidateStates[a[o+2]],reason:geometryReasons[a[o+3]]}));
  if(candidates.some(c=>!c.state||!c.reason))throw new Error('Invalid C++ optical candidate tags');
  return {status:geometryStatuses[a[0]],reason:geometryReasons[a[1]],rootCount:a[3],consideredCount:a[4],sqrtRefinements:a[5],refinementLimited:Boolean(a[6]),
    discriminant:a[7]?a.slice(8,10):null,candidates:candidates.slice(0,a[3]),hit:a[2]?{parameter:a.slice(18,20),physicalDistance:a.slice(20,22),
      position:bounds(22),geometricNormal:bounds(28),incidentNormal:bounds(34),parameterEstimate:a[40],physicalDistanceEstimate:a[41],
      positionEstimate:a.slice(42,45),geometricNormalEstimate:a.slice(45,48),incidentNormalEstimate:a.slice(48,51),frontFace:Boolean(a[51])}:null};
}
const polarizationFailures=['none','interface_uncertain','incidence_plane_uncertain','numerical_output'];
function frameResult(a,o){return {direction:a.slice(o,o+3),first:a.slice(o+3,o+6),second:a.slice(o+6,o+9)};}
function polarizationResult(a){
  const kinds=['transmission','total_internal_reflection','uncertain'],uncertainties=['none','incident_side','critical_angle','numerical_output'];
  if(a.length!==57||!a.every(Number.isFinite)||!polarizationFailures[a[0]]||!kinds[a[1]]||!uncertainties[a[2]])throw new Error('Invalid C++ polarization output');
  const branch=o=>({frame:frameResult(a,o),power:a.slice(o+9,o+13),amplitudeS:a.slice(o+13,o+15),amplitudeP:a.slice(o+15,o+17)});
  return {failure:polarizationFailures[a[0]],interfaceKind:kinds[a[1]],interfaceUncertainty:uncertainties[a[2]],inputFrame:frameResult(a,5),
    reflected:a[3]?branch(14):null,transmitted:a[4]?branch(31):null,discriminant:a.slice(48,50),incidentDot:a.slice(50,52),cosineIncident:a[52],
    cosineTransmitted:a[53]?a[54]:null,exactGrazing:Boolean(a[55]),vacuumWavelength:a[56]};
}
const ccdFailures=['none','invalid_input','initial_contact','query_unresolved','event_budget','segment_budget','query_budget','root_budget','geometric_guard','propagation_failure','solver_failure','sustained_contact_required','numerical_failure'];
function ccdSettings({timeTolerance=1e-7,spatialTolerance=1e-6,minimumImpactSpeed=1e-6,closingResidualTolerance=1e-7,relativeEnergyTolerance=1e-10,
  maxEventBatches=32,maxFreeSegments=65,maxPairQueries=100000,maxRootEvaluations=1000000,queryEvaluations=32768,queryFrontier=4096,queryDepth=64,
  velocityIterations=16,maxContacts=8192,restitutionVelocityThreshold=0,maxAngularIncrement=.5}={}){
  return [timeTolerance,spatialTolerance,minimumImpactSpeed,closingResidualTolerance,relativeEnergyTolerance,maxEventBatches,maxFreeSegments,maxPairQueries,
    maxRootEvaluations,queryEvaluations,queryFrontier,queryDepth,velocityIterations,maxContacts,restitutionVelocityThreshold,maxAngularIncrement];
}
function ccdResult(a){
  if(a.length!==21||!a.every(Number.isFinite)||!ccdFailures[a[1]])throw new Error('Invalid C++ continuous World output');
  return {success:Boolean(a[0]),failure:ccdFailures[a[1]],advancedDt:a[2],candidateTime:a[3],firstId:a[4],secondId:a[5],pairQueries:a[6],rootEvaluations:a[7],
    freeSegments:a[8],maximumPropagationError:a[9],accumulatedPositionRoundoff:a[10],timeRoundoff:a[11],contacts:a[12],velocityIterations:a[13],
    maxPenetration:a[14],normalImpulse:a[15],frictionImpulse:a[16],maxClosingResidual:a[17],eventCount:a[18],time:a[19],ticks:a[20]};
}
function sphereQueryInput({position,velocity=[0,0,0],radius}){
  return [...finiteArray(position,3,'Sphere position'),...finiteArray(velocity,3,'Sphere velocity'),radius];
}
function acceleratedSphereInput({position,velocity=[0,0,0],acceleration=[0,0,0],radius}){
  return [...finiteArray(position,3,'Sphere position'),...finiteArray(velocity,3,'Sphere velocity'),...finiteArray(acceleration,3,'Sphere acceleration'),radius];
}
function acceleratedSettings({timeTolerance=1e-8,maxEvaluations=32768,maxFrontier=4096,maxDepth=64}){
  return [timeTolerance,maxEvaluations,maxFrontier,maxDepth];
}
const acceleratedKinds=['none','entry_bracket','unresolved'];
const acceleratedReasons=['none','initial_overlap','initial_boundary','evaluation_budget','frontier_budget','depth_limit','time_resolution','numerical_uncertainty'];
function acceleratedResult(a){
  if(a.length!==21||!acceleratedKinds[a[0]]||!acceleratedReasons[a[1]]||!a.every(Number.isFinite))throw new Error('Invalid C++ accelerated-query output');
  const range=i=>a[i]?a.slice(i+1,i+3):null;
  return {kind:acceleratedKinds[a[0]],reason:acceleratedReasons[a[1]],initialSeparationProven:Boolean(a[2]),safeUntil:a[3],
    valueAtSafe:range(4),initialValue:range(7),bracket:range(10),negativeWitness:a[13]?a[14]:null,negativeValue:range(15),
    evaluations:a[18],excludedIntervals:a[19],depthReached:a[20]};
}
function opticsResult(a){
  const kinds=['transmission','total_internal_reflection','uncertain'],reasons=['none','incident_side','critical_angle','numerical_output'];
  if(a.length!==31||!kinds[a[0]]||!reasons[a[1]]||!a.every(Number.isFinite))throw new Error('Invalid C++ optical-interface output');
  return {kind:kinds[a[0]],uncertainty:reasons[a[1]],incidentUnit:a.slice(2,5),normalUnit:a.slice(5,8),reflected:a.slice(8,11),transmitted:a[11]?a.slice(12,15):null,
    power:a[15]?{reflectanceS:a[16],transmittanceS:a[17],reflectanceP:a[18],transmittanceP:a[19],reflectanceUnpolarized:a[20],transmittanceUnpolarized:a[21]}:null,
    cosineIncident:a[22],cosineTransmitted:a[23]?a[24]:null,vacuumWavelength:a[25],discriminant:a.slice(26,28),incidentDot:a.slice(28,30),exactGrazing:Boolean(a[30])};
}
const toiKinds=['none','initial_overlap','initial_touch','impact','grazing','uncertain'];
const toiMotions=['stationary','approaching','separating','tangential'];
function toiResult(values){
  if(values.length!==13||!toiKinds[values[0]]||!toiMotions[values[1]])throw new Error('Invalid C++ continuous-query output');
  return {kind:toiKinds[values[0]],initialMotion:toiMotions[values[1]],time:values[2]?values[3]:null,
    normal:values.slice(4,7),normalValid:Boolean(values[7]),atHorizon:Boolean(values[8]),roundoffSensitive:Boolean(values[9]),
    initialGap:values[10],initialNormalSpeed:values[11],normalSpeed:values[12]};
}
async function initialize({wasmBytes,manifest}={}){
  const start=performance.now();let bytes=wasmBytes,metadata=manifest??{};
  if(bytes===undefined){
    const [binary,record]=await Promise.all([fetch(asset('pikapika-simulation.wasm')),fetch(asset('pikapika-simulation.build.json'))]);
    if(!binary.ok||!record.ok)throw new Error('数値コアの配信ファイルを読み込めません');
    bytes=new Uint8Array(await binary.arrayBuffer());metadata=await record.json();
    const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',bytes));
    const hash=Array.from(digest,x=>x.toString(16).padStart(2,'0')).join('');
    if(hash!==metadata.artifacts?.['assets/pikapika-simulation.wasm']?.sha256)throw new Error('数値コアのWASMと来歴が一致しません');
  }
  if(!(bytes instanceof Uint8Array)||bytes.byteLength===0)throw new Error('Simulation requires nonempty WebAssembly bytes');
  const native=await createModule({wasmBinary:bytes,print:()=>{},printErr:message=>console.error(message)});
  return new SimulationRuntime(native,metadata,bytes.byteLength,performance.now()-start);
}
export function loadSimulationRuntime(options={}){
  if(options.wasmBytes!==undefined){
    if(!(options.wasmBytes instanceof Uint8Array))return Promise.reject(new Error('wasmBytes must be Uint8Array'));
    let promise=bytesCache.get(options.wasmBytes);if(!promise){promise=initialize(options);bytesCache.set(options.wasmBytes,promise);promise.catch(()=>bytesCache.delete(options.wasmBytes));}return promise;
  }
  if(!defaultRuntime){defaultRuntime=initialize(options);defaultRuntime.catch(()=>{defaultRuntime=undefined;});}return defaultRuntime;
}
function uploadHull(runtime,source){
  const mesh=validateMesh(source);
  if(mesh.positions.length>16384||mesh.triangles.length>32768)throw new Error('WASM hull profile: at most 16384 vertices / 32768 triangles');
  runtime.inputF64(mesh.positions.flat());runtime.inputU32(mesh.triangles.flat());return mesh;
}
const hydroResult=a=>({force:a.slice(0,3),torque:a.slice(3,6),wetArea:a[6],submergedVolume:a[7],totalVolume:a[8],shells:a[9],centerOfBuoyancy:a[10]?a.slice(11,14):null});
class SimulationHull {
  #source;
  constructor(runtime,source){this.runtime=runtime;const mesh=uploadHull(runtime,source);this.handle=runtime.handle(runtime.native._pp_sim_hull_create(mesh.positions.length,mesh.triangles.length));this.#source=mesh;}
  get source(){return structuredClone(this.#source);}
  requireLive(){if(!this.handle)throw new Error('Hull is disposed');}
  replace(source){this.requireLive();const mesh=uploadHull(this.runtime,source);this.runtime.check(this.runtime.native._pp_sim_hull_replace(this.handle,mesh.positions.length,mesh.triangles.length));this.#source=mesh;}
  query({density=1000,gravity=9.80665,waterLevel=0,position=[0,0,0],orientation=[0,0,0,1],scale=[1,1,1],centerOfMass=position}={}){
    this.requireLive();const r=this.runtime,n=r.inputF64([density,gravity,waterLevel,...finiteArray(position,3,'Position'),...finiteArray(orientation,4,'Orientation'),...finiteArray(scale,3,'Scale'),...finiteArray(centerOfMass,3,'Center of mass')]);
    r.check(r.native._pp_sim_hydro_query(this.handle,n));return hydroResult(r.output());
  }
  dispose(){if(this.handle){this.runtime.check(this.runtime.native._pp_sim_hull_destroy(this.handle));this.handle=0;}}
}
function bodyInput(body){
  const {id,isStatic=false,mass=1,radius=1,inertia=[.4*mass*radius*radius,.4*mass*radius*radius,.4*mass*radius*radius],position=[0,0,0],orientation=[0,0,0,1],linearVelocity=[0,0,0],angularMomentum=[0,0,0],force=[0,0,0],torque=[0,0,0],restitution=0,friction=.6}=body;
  if(typeof isStatic!=='boolean')throw new Error('isStatic requires a boolean');
  return [id,Number(isStatic),mass,radius,...finiteArray(inertia,3,'Inertia'),...finiteArray(position,3,'Position'),...finiteArray(orientation,4,'Orientation'),...finiteArray(linearVelocity,3,'Velocity'),...finiteArray(angularMomentum,3,'Angular momentum'),...finiteArray(force,3,'Force'),...finiteArray(torque,3,'Torque'),restitution,friction];
}
const bodyResult=a=>({id:a[0],isStatic:Boolean(a[1]),mass:a[2],radius:a[3],inertia:a.slice(4,7),position:a.slice(7,10),orientation:a.slice(10,14),linearVelocity:a.slice(14,17),angularMomentum:a.slice(17,20),force:a.slice(20,23),torque:a.slice(23,26),restitution:a[26],friction:a[27],angularVelocity:a.slice(28,31),kineticEnergy:a[31],time:a[32],ticks:a[33]});
const stepResult=a=>({midpointHydro:hydroResult(a),contacts:a[14],velocityIterations:a[15],maxPenetration:a[16],normalImpulse:a[17],frictionImpulse:a[18],closingResidual:a[19],time:a[20],ticks:a[21]});
class SimulationWorld {
  constructor(runtime){this.runtime=runtime;this.handle=runtime.handle(runtime.native._pp_sim_world_create());}
  requireLive(){if(!this.handle)throw new Error('World is disposed');}
  setGravity(gravity){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_set_gravity(this.handle,r.inputF64(finiteArray(gravity,3,'Gravity'))));}
  reset(){this.requireLive();this.runtime.check(this.runtime.native._pp_sim_world_reset(this.handle));}
  info(){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_info(this.handle));const a=r.output();return {gravity:a.slice(0,3),bodies:a[3],planes:a[4],time:a[5],ticks:a[6]};}
  addBody(body){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_body_add(this.handle,r.inputF64(bodyInput(body))));}
  setBody(body){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_body_set(this.handle,r.inputF64(bodyInput(body))));}
  getBody(id){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_body_get(this.handle,validBodyId(id)));return bodyResult(r.output());}
  addPlane({id,normal=[0,1,0],offset=0,restitution=0,friction=.6}){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_plane_add(this.handle,r.inputF64([id,...finiteArray(normal,3,'Plane normal'),offset,restitution,friction,0])));}
  step(dt,steps=1){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_step(this.handle,dt,stepCount(steps)));return stepResult(r.output());}
  stepContinuous(dt,settings={}){
    this.requireLive();const r=this.runtime,n=r.inputF64(ccdSettings(settings));r.check(r.native._pp_sim_world_step_continuous(this.handle,dt,n));
    const result=ccdResult(r.output());result.events=[];
    for(let i=0;i<result.eventCount;++i){r.check(r.native._pp_sim_world_ccd_event(this.handle,i));const a=r.output();
      if(a.length!==8||!a.every(Number.isFinite))throw new Error('Invalid C++ continuous event output');
      result.events.push({respondedAt:a[0],entryBracket:a.slice(1,3),maximumGap:a[3],propagationError:a[4],firstId:a[5],secondId:a[6],contacts:a[7]});}
    return result;
  }
  stepSupported(dt,settings={}){
    this.requireLive();const r=this.runtime,n=r.inputF64(supportedSettings(settings));r.check(r.native._pp_sim_world_step_supported(this.handle,dt,n));
    const result=supportedResult(r.output());result.events=[];
    for(let j=0;j<result.eventCount;++j){r.check(r.native._pp_sim_world_supported_event(this.handle,j));const a=r.output(),kinds=['impact','velocity_repair','release'];
      if(a.length!==12||!a.every(Number.isFinite)||!kinds[a[0]])throw new Error('Invalid C++ supported event');
      result.events.push({kind:kinds[a[0]],at:a[1],firstId:a[2],secondId:a[3],normal:a.slice(4,7),contacts:a[7],impulseSum:a[8],kineticBefore:a[9],kineticAfter:a[10],maximumGap:a[11]});}
    return result;
  }
  querySupport(settings={}){
    this.requireLive();const r=this.runtime,n=r.inputF64(supportSettings(settings));r.check(r.native._pp_sim_world_support(this.handle,n));
    const result=supportResult(r.output());result.constraints=[];result.bodies=[];
    for(let j=0;j<result.constraintCount;++j){r.check(r.native._pp_sim_world_support_constraint(this.handle,j));const a=r.output();
      if(a.length!==24||!a.every(Number.isFinite)||!(a[2]===0||a[2]===1))throw new Error('Invalid C++ support constraint');
      result.constraints.push({firstId:a[0],secondId:a[1],phase:a[2]===0?'resting':'separating',guardedGeometry:Boolean(a[3]),normal:a.slice(4,7),normalBounds:[0,1,2].map(k=>[a[7+k],a[10+k]]),
        gap:a.slice(13,15),normalVelocity:a.slice(15,17),curvature:a.slice(17,19),freeNormalAcceleration:a[19],lambda:a[20],normalAcceleration:a[21],accelerationBounds:a.slice(22,24)});
    }
    for(let j=0;j<result.bodyCount;++j){r.check(r.native._pp_sim_world_support_body(this.handle,j));const a=r.output();
      if(a.length!==22||!a.every(Number.isFinite))throw new Error('Invalid C++ support body');
      result.bodies.push({id:a[0],force:a.slice(1,4),normalTorque:a.slice(4,7),forceBounds:[0,1,2].map(k=>[a[7+k],a[10+k]]),
        acceleration:a.slice(13,16),accelerationBounds:[0,1,2].map(k=>[a[16+k],a[19+k]])});
    }
    return result;
  }
  buoyancyStep(hull,{bodyId=1,dt=1/120,steps=1,density=1000,gravity=9.80665,waterLevel=0,hullOriginBody=[0,0,0],scale=[1,1,1]}={}){
    this.requireLive();if(!(hull instanceof SimulationHull)||hull.runtime!==this.runtime)throw new Error('Hull and World must belong to the same WASM runtime');hull.requireLive();
    const r=this.runtime,n=r.inputF64([density,gravity,waterLevel,...finiteArray(hullOriginBody,3,'Hull origin'),...finiteArray(scale,3,'Scale')]);
    validBodyId(bodyId);
    r.check(r.native._pp_sim_world_buoyancy_step(this.handle,hull.handle,bodyId,dt,stepCount(steps),n));return stepResult(r.output());
  }
  dispose(){if(this.handle){this.runtime.check(this.runtime.native._pp_sim_world_destroy(this.handle));this.handle=0;}}
}
export async function createFloatSimulation({mode='heave',wasmBytes,manifest}={}){
  const runtime=await loadSimulationRuntime({wasmBytes,manifest}),hull=runtime.createHull(createBoxMesh([4,2,4]));
  let world,currentMode,origin,initialEnergy=0,contacts=0,disposed=false;
  function snapshot(){
    if(disposed)throw new Error('Float simulation is disposed');
    const body=world.getBody(1),hullPosition=add(body.position,quaternionRotate(origin,body.orientation));
    const hydro=hull.query({density:1000,gravity:10,position:hullPosition,orientation:body.orientation,centerOfMass:body.position});
    const potentialEnergy=currentMode==='heave'?.5*160000*body.position[1]**2:320000*(.5-quaternionRotate(origin,body.orientation)[1]);
    const totalEnergy=body.kineticEnergy+potentialEnergy;
    return {...body,mode:currentMode,hullPosition,hullSize:[4,2,4],hullOriginBody:[...origin],potentialEnergy,totalEnergy,initialEnergy,relativeEnergyError:initialEnergy?(totalEnergy-initialEnergy)/initialEnergy:0,submergedVolume:hydro.submergedVolume,buoyantForce:hydro.force,buoyantTorque:hydro.torque,contacts};
  }
  function reset(nextMode=currentMode){
    if(disposed)throw new Error('Float simulation is disposed');if(!['heave','roll'].includes(nextMode))throw new Error('Unknown floating reference mode');
    const candidate=runtime.createWorld({gravity:[0,-10,0]});
    try{candidate.addBody({id:1,mass:nextMode==='heave'?16000:32000,radius:.25,inertia:nextMode==='heave'?[16000*20/12,16000*32/12,16000*20/12]:[24000,48000,40000],position:nextMode==='heave'?[0,.1,0]:[0,-4,0],orientation:nextMode==='heave'?[0,0,0,1]:[0,0,Math.sin(.075),Math.cos(.075)]});}
    catch(error){candidate.dispose();throw error;}
    world?.dispose();world=candidate;currentMode=nextMode;origin=nextMode==='heave'?[0,0,0]:[0,.5,0];contacts=0;initialEnergy=0;initialEnergy=snapshot().totalEnergy;return snapshot();
  }
  try{reset(mode);}catch(error){world?.dispose();hull.dispose();throw error;}
  return {get diagnostics(){return runtime.diagnostics;},snapshot,reset,
    step(dt=1/120){if(disposed)throw new Error('Float simulation is disposed');contacts=world.buoyancyStep(hull,{dt,gravity:10,hullOriginBody:origin}).contacts;return snapshot();},
    dispose(){if(!disposed){world.dispose();hull.dispose();disposed=true;}}};
}

const derivedStatuses=['completed','invalid_input','budget_exceeded','degenerate','quality_rejected','quality_unresolved','numerical_failure','unsupported_environment'];
const derivedReasons=['none','settings','vertex_count','triangle_count','position_domain','index_range','duplicate_index','vertex_budget','triangle_budget','zero_cross','below_area_floor','cross_uncertain','area_uncertain','normal_uncertain','nonfinite_intermediate','allocation_failure','environment'];
function derivedMeshResult(runtime,vertexCount,triangles,readback){
  const a=runtime.output(),bad=message=>{throw new Error('Invalid C++ derived mesh '+message);};
  const integer=(x,max)=>Number.isSafeInteger(x)&&x>=0&&x<=max;
  const flag=x=>x===0||x===1;
  const f32=values=>{if(values.some(x=>!Number.isFinite(x)||!Object.is(Math.fround(x),x)))bad('non-Float32 component');return new Float32Array(values);};
  const bounds=values=>{const out=[];for(let j=0;j<values.length;j+=2){if(values[j]>values[j+1])bad('reversed bounds');out.push(values.slice(j,j+2));}return out;};
  if(a.length!==20||!a.every(Number.isFinite)||!integer(a[0],derivedStatuses.length-1)||!integer(a[1],derivedReasons.length-1)||![2,7,9].every(j=>flag(a[j]))||a[13]!==0)bad('summary');
  for(const j of [3,4,5,6,8,10,11,12])if(!integer(a[j],Number.MAX_SAFE_INTEGER))bad('count');
  if(Boolean(a[2])!==(a[0]===0)||(a[0]===0?a[1]!==0:a[1]===0)||a[5]>triangles.length||a[12]>a[5]||(a[7]?a[8]>=vertexCount:a[8]!==0)||(a[9]?a[10]>=triangles.length:a[10]!==0))bad('metadata');
  if(a[2]?(vertexCount<3||triangles.length<1||a[3]!==vertexCount||a[4]!==triangles.length||a[5]!==triangles.length||a[6]!==18*triangles.length||a[7]||a[9]):(a[3]!==0||a[4]!==0||a[6]!==0||a.slice(14).some(x=>x!==0)))bad('geometry counts');
  if([3,4,5].includes(a[0])&&(!a[9]||a[7]||a[5]!==a[10]+1))bad('failing audit prefix');
  // Own one bounded output packet per kind. Triangle and face requests are
  // interleaved below; separate caches avoid discarding the other kind's tail.
  const cache=[null,null,null,null],limits=[20,20,3,2],strides=[3,3,18,26],available=[a[3],a[4],a[4],a[5]];
  const get=(kind,index,size)=>{
    if(readback==='single'){runtime.check(runtime.native._pp_sim_derived_mesh_record(kind,index));const b=runtime.output();if(b.length!==size||!b.every(Number.isFinite))bad('record');return b;}
    let packet=cache[kind];
    if(!packet||index<packet.first||index>=packet.first+packet.count){
      const count=Math.min(limits[kind],available[kind]-index);
      runtime.check(runtime.native._pp_sim_derived_mesh_records(kind,index,count));
      const b=runtime.output();
      if(size!==strides[kind]||count<1||b.length!==4+count*size||!Array.from(b).every(Number.isFinite)||b[0]!==kind||b[1]!==index||b[2]!==count||b[3]!==size)bad('batch packet');
      packet={first:index,count,payload:b.slice(4)};cache[kind]=packet;
    }
    const offset=(index-packet.first)*size;return packet.payload.slice(offset,offset+size);
  };
  const result={status:derivedStatuses[a[0]],reason:derivedReasons[a[1]],failedVertex:a[7]?a[8]:null,failedFace:a[9]?a[10]:null,geometry:null,audits:[],sqrtRefinements:a[11],sqrtLimitedFaces:a[12]};
  for(let j=0;j<a[5];++j){
    const b=get(3,j,26);if(b[0]!==j||![9,16,20,25].every(k=>flag(b[k]))||!integer(b[24],512)||b[8]<0)bad('audit flags/count');
    for(const [flagIndex,start,end] of [[9,10,16],[16,17,20],[20,21,24]])if(!b[flagIndex]&&b.slice(start,end).some(x=>x!==0))bad('absent audit payload');
    if(b[20]&&(!b[9]||!b[16]||b.slice(21,24).some(x=>x<0)))bad('normal error evidence');
    const audit={face:j,cross:bounds(b.slice(1,7)),squaredCross:bounds(b.slice(7,9))[0],normalized:b[9]?bounds(b.slice(10,16)):null,normal:b[16]?f32(b.slice(17,20)):null,normalError:b[20]?b.slice(21,24):null,sqrtRefinements:b[24],sqrtRefinementLimited:Boolean(b[25])};
    if(a[2]&&(!audit.normalized||!audit.normal||!audit.normalError||audit.normalError.some(e=>e>1e-6)||audit.squaredCross[0]<=1e-24||!audit.cross.some(([lo,hi])=>lo>0||hi<0)))bad('completed normal evidence');
    result.audits.push(audit);
  }
  if(result.audits.reduce((s,b)=>s+b.sqrtRefinements,0)!==a[11]||result.audits.filter(b=>b.sqrtRefinementLimited).length!==a[12])bad('audit totals');
  if(a[2]){
    const geometry={positions:[],triangles:[],interleaved:new Float32Array(a[6]),minimum:f32(a.slice(14,17)),maximum:f32(a.slice(17,20))};
    for(let axis=0;axis<3;++axis)if(geometry.minimum[axis]>geometry.maximum[axis])bad('bounds');
    for(let j=0;j<a[3];++j)geometry.positions.push(f32(get(0,j,3)));
    for(let j=0;j<a[4];++j){const t=get(1,j,3);if(t.some((x,k)=>!integer(x,vertexCount-1)||x!==triangles[j][k]))bad('triangle index/order');geometry.triangles.push(new Uint32Array(t));
      const face=f32(get(2,j,18));for(let corner=0;corner<3;++corner)for(let axis=0;axis<3;++axis){if(!Object.is(face[6*corner+axis],geometry.positions[t[corner]][axis])||!Object.is(face[6*corner+3+axis],result.audits[j].normal[axis]))bad('expanded buffer/order');}geometry.interleaved.set(face,18*j);
    }
    result.geometry=geometry;
  }
  return result;
}

function skinApi(native){
  for(const name of ['_pp_sim_skin_bind','_pp_sim_skin_bind_record','_pp_sim_skin_deform','_pp_sim_skin_deform_record'])if(typeof native[name]!=='function')throw new Error('Skinning WASM API unavailable; rebuild the common C++ runtime');
}
function skinMatrices(records,label){
  if(!Array.isArray(records)||records.length>128)throw new Error('Skin SDK requires at most 128 bones; inputs are not split or truncated');
  return Array.from(records,b=>[validBodyId(b.id),...finiteArray(b.matrix,16,label+' matrix')]).flat();
}
function skinSettings({maximumBones=128,maximumVertices=65536,maximumInfluences=262144,maximumCondition=1e10,maximumInverseResidual=1e-10}={}){
  return [maximumBones,maximumVertices,maximumInfluences,maximumCondition,maximumInverseResidual];
}
function skinResult(runtime,operation,ids,vertexCount){
  const a=runtime.output(),statuses=['completed','invalid_input','budget_exceeded','ill_conditioned','numerical_failure'];
  const itemLimit=operation==='bind'?ids.length:vertexCount;
  if(a.length!==8||!a.every(Number.isFinite)||!statuses[a[0]]||![0,1].includes(a[1])||Boolean(a[1])!==(a[0]===0)||a.slice(5).some(x=>x!==0))throw new Error('Invalid C++ skin summary');
  for(const j of [2,3,4])if(!Number.isInteger(a[j])||a[j]<0)throw new Error('Invalid C++ skin count');
  if(a[2]>(a[1]?itemLimit:0)||(a[1]&&a[2]!==itemLimit)||a[3]>ids.length||a[4]>vertexCount||(operation==='bind'&&a[4]!==0)||(operation==='deform'&&a[1]&&a[4]!==vertexCount))throw new Error('Inconsistent C++ skin summary');
  const get=(kind,index,length)=>{
    runtime.check(runtime.native[operation==='bind'?'_pp_sim_skin_bind_record':'_pp_sim_skin_deform_record'](kind,index));
    const b=runtime.output();if(b.length!==length||!b.every(Number.isFinite))throw new Error('Invalid C++ skin record');return b;
  };
  const result={status:statuses[a[0]],joints:operation==='bind'&&a[1]?[]:null,positions:operation==='deform'&&a[1]?[]:null,diagnostics:[],weightResiduals:[]};
  for(let j=0;j<a[2];++j){
    if(operation==='bind'){
      const b=get(0,j,33);if(b[0]!==ids[j])throw new Error('C++ skin bind changed stable ID/order');
      result.joints.push({id:b[0],restWorld:b.slice(1,17),inverseBind:b.slice(17,33)});
    }else result.positions.push(get(0,j,3));
  }
  for(let j=0;j<a[3];++j){
    const b=get(1,j,6);
    if(b[0]!==ids[j]||![0,1].includes(b[1])||![0,1].includes(b[3])||![0,1].includes(b[5])||b[2]<0||b[4]<0||(!b[1]&&b[2]!==0)||(!b[3]&&b[4]!==0))throw new Error('Invalid C++ skin diagnostic flags/ID');
    result.diagnostics.push({id:b[0],condition:b[1]?b[2]:null,residual:b[3]?b[4]:null,pivotFailure:Boolean(b[5])});
  }
  for(let j=0;j<a[4];++j){const b=get(2,j,1);if(b[0]<0||b[0]>32*Number.EPSILON)throw new Error('Invalid C++ skin weight residual');result.weightResiduals.push(b[0]);}
  return result;
}

function polarizedRouteResult(a,initial,segment){
const statuses=['completed','geometry_failed','power_unresolved','invalid_input','budget_exceeded','numerical_failure'],failures=['none','initial_state_uncertain','initial_frame_uncertain','incidence_frame_uncertain','amplitude_uncertain','numerical_domain'];
    if(a.length!==64||!a.every(Number.isFinite)||!statuses[a[0]]||!failures[a[1]]||(a[2]&&!routeStatuses[a[3]])||a[62]!==0||a[63]!==0)throw new Error('Invalid C++ polarized route summary');
    for(const j of [4,5,6,9,10,11,12,13,14,15])if(!Number.isInteger(a[j])||a[j]<0)throw new Error('Invalid C++ polarized route counter');
    if(a[6]>64||a[9]>64||(a[17]&&!a[55]))throw new Error('Inconsistent C++ polarized route completion');
    const ray=()=>({origin:vectorBounds(a,18),direction:vectorBounds(a,24),minimumParameter:a[52],maximumParameter:a[53]});
    const result={status:statuses[a[0]],powerFailure:failures[a[1]],geometry:a[2]?{status:routeStatuses[a[3]],completedSteps:a[4],failedStep:a[5],segments:[],completion:a[55]?{ray:ray(),index:a.slice(30,32),totals:{distance:a.slice(56,58),opticalPathLength:a.slice(58,60),throughput:a.slice(60,62)}}:null}:null,
      initialFrame:null,initialState:null,segments:[],completedPowerSteps:a[10],failedPowerStep:a[11],completion:a[17]?{state:{power:a.slice(32,34),coherency:coherencyResult(a,34)},ray:ray(),index:a.slice(30,32)}:null,
      geometryQueries:a[12],interfaceQueries:a[13],geometrySqrtRefinements:a[14],powerSqrtRefinements:a[15],refinementLimited:Boolean(a[16])};
    const b=initial();
    if(b.length!==40||!b.every(Number.isFinite)||b[0]!==a[7]||b[1]!==a[8])throw new Error('Invalid C++ polarized initial snapshot');
    if(b[0])result.initialFrame={direction:vectorBounds(b,2),first:vectorBounds(b,8),second:vectorBounds(b,14)};
    if(b[1])result.initialState={power:b.slice(20,22),coherency:coherencyResult(b,22)};
    for(let j=0;j<a[6];++j){result.geometry.segments.push(routeSegmentResult(segment(j,0)));}
    for(let j=0;j<a[9];++j){const c=segment(j,1);
      if(c.length!==35||!c.every(Number.isFinite)||c[0]!==j||![0,1].includes(c[1]))throw new Error('Invalid C++ polarized power segment');
      result.segments.push({ordinal:j,branch:c[1]?'transmitted':'reflected',amplitudeS:c[2]?complexBoundsResult(c,7):null,amplitudeP:c[3]?complexBoundsResult(c,11):null,exactNormal:Boolean(c[4]),homogeneous:Boolean(c[5]),outgoing:c[6]?{power:c.slice(15,17),coherency:coherencyResult(c,17)}:null});}
    return result;
}
