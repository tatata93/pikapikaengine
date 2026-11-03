import createModule from '../assets/pikapika-simulation.mjs';
import {validateMesh,createBoxMesh} from './mesh.mjs';
import {quaternionRotate,add} from './math.mjs';

const bytesCache=new WeakMap();let defaultRuntime;
const asset=name=>{const url=new URL('../assets/'+name,import.meta.url),build=new URL(import.meta.url).searchParams.get('build');if(build)url.searchParams.set('build',build);return url;};
const finiteArray=(input,length,label)=>{
  if(!(Array.isArray(input)||ArrayBuffer.isView(input))||input.length!==length)throw new Error(`${label} requires ${length} components`);
  const values=Array.from(input);if(!values.every(Number.isFinite))throw new Error(`${label} requires finite numbers`);return values;
};
const stepCount=value=>{if(!Number.isInteger(value)||value<1||value>32)throw new Error('Simulation batch requires 1..32 complete ticks');return value;};
const validBodyId=value=>{if(!Number.isSafeInteger(value)||value<1)throw new Error('Body ID requires an integer in 1..9007199254740991');return value;};
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
