#ifndef PIKAPIKA_SIMULATION_API_H
#define PIKAPIKA_SIMULATION_API_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef uint32_t pp_sim_handle;
enum pp_sim_status_code {
    PP_SIM_OK=0, PP_SIM_INVALID_ARGUMENT=1, PP_SIM_INVALID_HANDLE=2,
    PP_SIM_BUDGET_EXCEEDED=3, PP_SIM_CORE_REJECTED=4,
    PP_SIM_ALLOCATION_FAILED=5, PP_SIM_INTERNAL_ERROR=6
};
enum pp_sim_limits {
    PP_SIM_API_VERSION=1,
    PP_SIM_MAX_WORLDS=16, PP_SIM_MAX_HULLS=32,
    PP_SIM_MAX_BODIES=128, PP_SIM_MAX_PLANES=8, PP_SIM_MAX_CONTACTS=8192,
    PP_SIM_MAX_HULL_VERTICES=16384, PP_SIM_MAX_HULL_TRIANGLES=32768,
    PP_SIM_MAX_TOTAL_VERTICES=65536, PP_SIM_MAX_TOTAL_TRIANGLES=131072,
    PP_SIM_MAX_STEPS=32, PP_SIM_ERROR_CAPACITY=256,
    PP_SIM_INPUT_F64_CAPACITY=49152, PP_SIM_INPUT_U32_CAPACITY=98304,
    PP_SIM_OUTPUT_F64_CAPACITY=64,
    PP_SIM_BODY_INPUT_COUNT=28, PP_SIM_BODY_OUTPUT_COUNT=34,
    PP_SIM_PLANE_INPUT_COUNT=8, PP_SIM_HYDRO_INPUT_COUNT=16,
    PP_SIM_HYDRO_OUTPUT_COUNT=14, PP_SIM_BUOYANCY_INPUT_COUNT=9,
    PP_SIM_STEP_OUTPUT_COUNT=22, PP_SIM_WORLD_INFO_COUNT=7,
    PP_SIM_TOI_INPUT_COUNT=15, PP_SIM_TOI_OUTPUT_COUNT=13,
    PP_SIM_ACCEL_PAIR_INPUT_COUNT=25, PP_SIM_ACCEL_PLANE_INPUT_COUNT=19,
    PP_SIM_ACCEL_OUTPUT_COUNT=21, PP_SIM_MAX_QUERY_EVALUATIONS=32768,
    PP_SIM_MAX_QUERY_FRONTIER=4096
};
enum pp_sim_optics_counts { PP_SIM_OPTICS_INPUT_COUNT=9, PP_SIM_OPTICS_OUTPUT_COUNT=31 };
enum pp_sim_reference_counts {
    PP_SIM_GEOMETRY_INPUT_COUNT=19, PP_SIM_GEOMETRY_OUTPUT_COUNT=52,
    PP_SIM_POLARIZATION_INPUT_COUNT=16, PP_SIM_POLARIZATION_OUTPUT_COUNT=57,
    PP_SIM_DISPERSION_INPUT_COUNT=27, PP_SIM_DISPERSION_OUTPUT_COUNT=14,
    PP_SIM_BOUNDED_GEOMETRY_INPUT_COUNT=25, PP_SIM_BOUNDED_GEOMETRY_OUTPUT_COUNT=41,
    PP_SIM_BOUNDED_INTERFACE_INPUT_COUNT=19, PP_SIM_BOUNDED_INTERFACE_OUTPUT_COUNT=59,
    PP_SIM_SUPPORT_SETTINGS_COUNT=10, PP_SIM_SUPPORT_OUTPUT_COUNT=21,
    PP_SIM_SUPPORT_CONSTRAINT_COUNT=24, PP_SIM_SUPPORT_BODY_COUNT=22,
    PP_SIM_ROUTE_HEADER_COUNT=21, PP_SIM_ROUTE_STEP_INPUT_COUNT=14,
    PP_SIM_ROUTE_OUTPUT_COUNT=31, PP_SIM_ROUTE_SEGMENT_COUNT=64,
    PP_SIM_SELECTION_HEADER_COUNT=21, PP_SIM_SELECTION_SURFACE_INPUT_COUNT=10,
    PP_SIM_SELECTION_OUTPUT_COUNT=31, PP_SIM_SELECTION_SURFACE_OUTPUT_COUNT=46,
    PP_SIM_POLARIZED_ROUTE_HEADER_COUNT=31, PP_SIM_POLARIZED_ROUTE_OUTPUT_COUNT=64,
    PP_SIM_POLARIZED_ROUTE_INITIAL_COUNT=40, PP_SIM_POLARIZED_ROUTE_SEGMENT_COUNT=35,
    PP_SIM_PACKET_HEADER_COUNT=23, PP_SIM_PACKET_INPUT_COUNT=21,
    PP_SIM_PACKET_OUTPUT_COUNT=24, PP_SIM_PACKET_RECORD_COUNT=12,
    PP_SIM_MOTION_HEADER_COUNT=10, PP_SIM_MOTION_OUTPUT_COUNT=10, PP_SIM_MOTION_BONE_COUNT=45,
    PP_SIM_SKIN_BIND_HEADER_COUNT=8, PP_SIM_SKIN_DEFORM_HEADER_COUNT=12,
    PP_SIM_SKIN_MATRIX_INPUT_COUNT=17, PP_SIM_SKIN_JOINT_COUNT=33,
    PP_SIM_SKIN_VERTEX_INPUT_COUNT=4, PP_SIM_SKIN_INFLUENCE_INPUT_COUNT=2,
    PP_SIM_SKIN_OUTPUT_COUNT=8, PP_SIM_SKIN_DIAGNOSTIC_COUNT=6,
    PP_SIM_SKIN_MAX_BONES=128, PP_SIM_SKIN_MAX_VERTICES=2048, PP_SIM_SKIN_MAX_INFLUENCES=8192,
    PP_SIM_DERIVED_HEADER_COUNT=8, PP_SIM_DERIVED_OUTPUT_COUNT=20,
    PP_SIM_DERIVED_AUDIT_COUNT=26, PP_SIM_DERIVED_MAX_VERTICES=2048,
    PP_SIM_DERIVED_MAX_TRIANGLES=32768,
    PP_SIM_LAUNCH_INPUT_COUNT=9, PP_SIM_LAUNCH_OUTPUT_COUNT=14,
    PP_SIM_SPOT_HEADER_COUNT=21, PP_SIM_SPOT_SAMPLE_INPUT_COUNT=15,
    PP_SIM_SPOT_OUTPUT_COUNT=32, PP_SIM_SPOT_ROUTE_OUTPUT_COUNT=34, PP_SIM_SPOT_SENSOR_OUTPUT_COUNT=46,
    PP_SIM_CCD_SETTINGS_COUNT=16, PP_SIM_CCD_OUTPUT_COUNT=21, PP_SIM_CCD_EVENT_COUNT=8,
    PP_SIM_SUPPORTED_SETTINGS_COUNT=33, PP_SIM_SUPPORTED_OUTPUT_COUNT=32, PP_SIM_SUPPORTED_EVENT_COUNT=12
};
enum pp_sim_optics_kind { PP_SIM_OPTICS_TRANSMISSION=0, PP_SIM_OPTICS_TIR=1, PP_SIM_OPTICS_UNCERTAIN=2 };
enum pp_sim_optics_uncertainty { PP_SIM_OPTICS_RESOLVED=0, PP_SIM_OPTICS_INCIDENT_SIDE=1,
    PP_SIM_OPTICS_CRITICAL_ANGLE=2, PP_SIM_OPTICS_NUMERICAL_OUTPUT=3 };
enum pp_sim_contact_kind {
    PP_SIM_TOI_NONE=0, PP_SIM_TOI_INITIAL_OVERLAP=1, PP_SIM_TOI_INITIAL_TOUCH=2,
    PP_SIM_TOI_IMPACT=3, PP_SIM_TOI_GRAZING=4, PP_SIM_TOI_UNCERTAIN=5
};
enum pp_sim_initial_motion {
    PP_SIM_TOI_STATIONARY=0, PP_SIM_TOI_APPROACHING=1,
    PP_SIM_TOI_SEPARATING=2, PP_SIM_TOI_TANGENTIAL=3
};
enum pp_sim_accel_kind {
    PP_SIM_ACCEL_NONE=0, PP_SIM_ACCEL_ENTRY_BRACKET=1, PP_SIM_ACCEL_UNRESOLVED=2
};
enum pp_sim_accel_reason {
    PP_SIM_ACCEL_REASON_NONE=0, PP_SIM_ACCEL_INITIAL_OVERLAP=1,
    PP_SIM_ACCEL_INITIAL_BOUNDARY=2, PP_SIM_ACCEL_EVALUATION_BUDGET=3,
    PP_SIM_ACCEL_FRONTIER_BUDGET=4, PP_SIM_ACCEL_DEPTH_LIMIT=5,
    PP_SIM_ACCEL_TIME_RESOLUTION=6, PP_SIM_ACCEL_NUMERICAL_UNCERTAINTY=7
};
// One module-owned exchange area. Never free these pointers. Refresh WASM
// TypedArray views after any call that can grow memory; reacquire pointer too.
// Calls are synchronous, not reentrant/thread-safe. No C++ object layout leaks.
uint32_t pp_sim_api_version(void);
double* pp_sim_input_f64_ptr(void);
uint32_t* pp_sim_input_u32_ptr(void);
const double* pp_sim_output_f64_ptr(void);
uint32_t pp_sim_input_f64_capacity(void);
uint32_t pp_sim_input_u32_capacity(void);
uint32_t pp_sim_output_f64_capacity(void);
uint32_t pp_sim_output_count(void);
int32_t pp_sim_last_status(void);
const char* pp_sim_error_ptr(void);
uint32_t pp_sim_error_length(void);
int32_t pp_sim_reset(void); // Frees resources; invalidates all live handles.

// Stateless linear-trajectory queries; no World/Hull handle or response.
// Sphere/sphere input: positionA3,velocityA3,radiusA,positionB3,velocityB3,radiusB,horizonSeconds.
// Sphere/plane input: position3,velocity3,radius,normal3,offset,planeVelocity3,horizonSeconds.
// Output: kind,motion,hasTime,time,normal3,normalValid,atHorizon,roundoffSensitive,
//         initialGap,initialNormalSpeed,normalSpeed. Absent time is encoded as 0.
// Sphere/sphere normal A->B; sphere/plane normal plane->sphere. See CONTINUOUS.md.
int32_t pp_sim_sphere_sphere_toi(uint32_t value_count);
int32_t pp_sim_sphere_plane_toi(uint32_t value_count);

// Stateless constant-acceleration, fixed-radius queries. No World step/response.
// Sphere record[10]: position3,velocity3,acceleration3,radius.
// Pair[25]: sphereA10,sphereB10,horizon,tolerance,maxEvaluations,maxFrontier,maxDepth.
// Plane[19]: sphere10,normal3,offset,horizon,tolerance,maxEvaluations,maxFrontier,maxDepth.
// Output[21]: kind,reason,initialSeparationProven,safeUntil,
// hasSafeValue,safeLo,safeHi,hasInitialValue,initialLo,initialHi,
// hasBracket,bracketLo,bracketHi,hasNegativeWitness,negativeTime,
// hasNegativeValue,negativeLo,negativeHi,evaluations,excludedIntervals,depthReached.
// Optional missing payloads are 0; check their flags. An entry bracket certifies
// a first zero within its bounds, not an exact impact time or contact normal.
// Unresolved preserves the proven safe prefix; never treat it as no collision.
int32_t pp_sim_accelerated_spheres(uint32_t value_count);
int32_t pp_sim_accelerated_plane(uint32_t value_count);

// Lossless nonmagnetic dielectric plane interface at the supplied vacuum
// wavelength. Input[9]: propagationTowardInterface3,normalIntoIncidentMedium3,
// indexIncident,indexTransmitted,vacuumWavelengthMetres. No material dispersion.
// Output[31]: kind,uncertainty,incidentUnit3,normalUnit3,reflected3,
// hasTransmitted,transmitted3,hasPower,Rs,Ts,Rp,Tp,R_unpolarized,T_unpolarized,
// cosineIncident,hasCosineTransmitted,cosineTransmitted,wavelengthMetres,
// discriminantLo,discriminantHi,incidentDotLo,incidentDotHi,exactGrazing.
// Power ratios are NORMAL flux, not amplitudes or radiance multipliers.
// Classification uses original-input intervals; direction/power are estimates.
int32_t pp_sim_dielectric_interface(uint32_t value_count);

// Geometry[19]: shape(0 disk/1 full sphere/2 vertex cap),origin3,direction3,
// tMin,tMax,centerOrVertex3,normalOrAxis3,signedRadius,aperture,tTolerance,maxSqrt.
// Sphere normal/axis and aperture reserved 0; disk signedRadius reserved 0.
// Output[52]: status,reason,hasHit,rootCount,considered,sqrtRefinements,limited,
// hasDiscriminant,Dlo,Dhi,candidate0(tLo,tHi,state,reason),candidate1(same),
// hit(tLo,tHi,distanceLo,distanceHi,positionBounds6,geometricNormalBounds6,
// incidentNormalBounds6,tEstimate,distanceEstimate,position3,geometricNormal3,
// incidentNormal3,frontFace). Check hasHit, no implicit self-hit offset.
int32_t pp_sim_optical_geometry(uint32_t value_count);
// Polarization[16]: interface9,transverseReference3,Stokes(I,Q,U,V).
// Output[57]: failure,interfaceKind,interfaceUncertainty,hasReflected,hasTransmitted,
// inputFrame9,reflectedBranch17,transmittedBranch17,Dlo,Dhi,dotLo,dotHi,
// cosIncident,hasCosTransmitted,cosTransmitted,exactGrazing,wavelengthMetres.
// Frame9=direction3,first3,second3. Branch17=frame9,Stokes4,ampS(real,imag),ampP(real,imag).
// Transmission amplitudes are POWER normalized. Stokes V=2Im(Cxy).
int32_t pp_sim_polarized_interface(uint32_t value_count);
// Dispersion[27]: kind(0 Cauchy/1 Sellmeier),lambdaLo,lambdaHi,validLo,validHi,
// maxPhaseWidth,maxSqrt,A,B,C,count,8*(oscillatorB,oscillatorC).
// Cauchy count/oscillators reserved 0; Sellmeier A/B/C and unused terms 0.
// Output[14]: status(0 resolved/1 nonphysical/2 unresolved),reason,hasValues,
// sqrtRefinements,hasSquaredPhase,qLo,qHi,nLo,nHi,dnLo,dnHi,ngLo,ngHi,
// wholePhaseWithinInterfaceDomain. Wavelength m, Cauchy B:m^2 C:m^4,
// Sellmeier C:m^2, derivative 1/m. Absolute index, vacuum wavelength.
int32_t pp_sim_dispersion(uint32_t value_count);
// Bounded geometry[25]: shape,originBounds6,directionBounds6,tMin,tMax,
// centerOrVertex3,normalOrAxis3,signedRadius,aperture,maxParameterWidth,maxSqrt.
// Output[41]: same as geometry output[0..39], then frontFace. No estimates.
int32_t pp_sim_bounded_geometry(uint32_t value_count);
// Bounded interface[19]: incidentBounds6,normalBounds6,niLoHi,ntLoHi,
// vacuumWavelength,maximumParameterWidth,maxSqrt. Independent index families.
// Output[59]: kind,reason,sqrtRefinements,limited,exactGrazing,wavelength,
// hasIncident,hasNormal,hasReflected,hasTransmitted,hasPower,hasCosI,hasCosT,hasD,
// incidentBounds6,normalBounds6,reflectedBounds6,transmittedBounds6,
// powerBounds12(Rs,Ts,Rp,Tp,Ravg,Tavg),cosI2,cosT2,D2,incidentDot2,reserved0.
int32_t pp_sim_bounded_interface(uint32_t value_count);
// Explicit optical itinerary, not automatic nearest-world/occlusion/path search.
// Input header[21]: originBounds6,directionBounds6,initialTMin,initialTMax,
// initialIndex2,vacuumWavelength,maxSteps,maxParameterWidth,maxSqrt,stepCount.
// Per-step[14]: shape,anchor3,axis3,radius,aperture,branch(0 reflect/1 transmit),
// otherIndex2,tMin,tMax. Reserved shape slots match bounded geometry. Each step
// supplies the incoming domain; initial domain remains on empty identity route.
// Summary[31]: status,completedSteps,failedStep,segmentCount,hasCompletion,
// geometryQueries,totalSqrtRefinements,limited,finalOriginBounds6,
// finalDirectionBounds6,finalIndex2,distance2,OPL2,throughput2,finalTMin,finalTMax,
// wavelength. Completion fields absent unless hasCompletion. Throughput bounds
// any polarization using per-interface s/p envelopes; no coherent interference.
int32_t pp_sim_optical_route(uint32_t value_count);
// Snapshot of last valid attempt, including failed-prefix diagnostics. Out[64]:
// branch,hasHit,geometryStatus,geometryReason,hasInterface,interfaceKind,
// interfaceReason,hasOutgoing,hasFactor,hasAccumulated,incomingOriginBounds6,
// incomingDirectionBounds6,incomingTMin,incomingTMax,incidentIndex2,otherIndex2,
// hitPosition6,parameter2,distance2,incidentNormal6,outgoingDirection6,factor2,
// accumulatedDistance2,accumulatedOPL2,accumulatedThroughput2,sqrtRefinements,
// limited,consideredRoots,rootCount,frontFace,reserved0.
int32_t pp_sim_optical_route_segment(uint32_t index);

// Nearest static optical surface for an entire bounded ray family. Input[21+10N]:
// originBounds6,directionBounds6,tMin,tMax,maxParameterWidth,primitiveSqrtLimit,
// maxSurfaces,maxQueries,totalSqrtLimit,allowPrefix(0/1),surfaceCount (0..1024).
// Each surface[10]: exact-safe-positive ID,kind(0 disk/1 sphere/2 cap),
// centerOrVertex3,normalOrAxis3,radius,aperture. Disk radius reserved0;
// sphere normal/axis/aperture reserved0. All provided values must be finite.
// Summary[31]: status,hasNearest,surfaceID,surfaceDiagnosticCount,queries,
// prefixQueries,sqrtRefinements,limited,parameter2,distance2,position6,
// geometricNormal6,incidentNormal6,frontFace. Hit fields absent unless hasNearest.
// Model failures are PP_SIM_OK data with no nearest. Bad exchange retains the
// previous output and attempt record. No automatic epsilon/source skip/medium.
int32_t pp_sim_optical_selection(uint32_t value_count);
// Last valid attempt snapshot, canonical increasing-ID order. prefix=0 original,
// prefix=1 closed-prefix query. Out[46]: ID,hasOriginal,hasPrefix,excludedByPrefix,
// hasRequestedPart,then unchanged bounded-geometry[41]. Absent part fields zero.
int32_t pp_sim_optical_selection_surface(uint32_t index,uint32_t prefix);


// Bounded polarized ray-tube POWER route. Input[31+14S]: original route header
// [0..20], transverseReference3,pointStokes(I,Q,U,V),powerSqrtLimit,totalSqrtLimit,
// reserved0; route steps unchanged. No per-interface unpolarized reset.
// Out[64]: status,powerFailure,hasGeometry,geometryStatus,geometryCompletedSteps,
// geometryFailedStep,geometrySegments,hasInitialFrame,hasInitialState,
// powerSegments,completedPowerSteps,failedPowerStep,geometryQueries,
// interfaceQueries,geometrySqrt,powerSqrt,limited,hasCompletion,geometryFinalOrigin6,
// geometryFinalDirection6,geometryFinalIndex2,finalPower2,finalCoherency18,geometryFinalTMin,geometryFinalTMax,
// wavelength,hasGeometryCompletion,distance2,OPL2,throughputEnvelope2,reserved0x2.
// Coherency18: diagonal(xx,yy,zz) intervals, then xy/xz/yz complex intervals
// (realLoHi,imagLoHi). A box enclosing true PSD/transverse matrices does not
// mean every independent member of that box is physical. Exact contract:
// docs/POLARIZED_ROUTE.md. Model failure is data; invalid exchange retains record.
int32_t pp_sim_polarized_route(uint32_t value_count);
// Initial snapshot[40]: hasFrame,hasState,direction6,first6,second6,power2,C18.
int32_t pp_sim_polarized_route_initial(void);
// Part0: existing route-segment[64], indexed into geometry.segments.
// Part1[35]: ordinal,branch,hasS,hasP,exactNormal,homogeneous,hasOutgoing,
// amplitudeS4,amplitudeP4,outgoingPower2,outgoingCoherency18.
int32_t pp_sim_polarized_route_segment(uint32_t index,uint32_t part);
// One prescribed itinerary for explicit noninterfering finite POWER packets (W).
// Header23 + steps14 + packets21; packet=ray14,Stokes4,reference3.
// Record parts:0 metadata12,1 polarized-route64,2 initial40,3 sensor41.
// Segment parts:0 geometry64,1 polarized-power35. All are copied snapshots.
// Model failure is data; bad exchange/getters retain prior record/output.
// Absolute-seconds authored motion/FK. Header10, bones12, tracks3 + keys11.
// Complete pose only. Getter45: IDs2,localTRS10,localMatrix16,worldMatrix16,rank.
// Snapshot independent of world/optical calls; malformed exchange/getters retain it.
int32_t pp_sim_motion(uint32_t value_count);
int32_t pp_sim_motion_bone(uint32_t index);
// Positions-only, point binary64 LBS. Bind header8: restCount,maxBones,
// maxVertices,maxInfluences,maximumCondition,maximumInverseResidual,0,0.
// Rest/pose item17: id,matrix16 column-major. Joint33: id,rest16,inverse16.
// Deform header12: jointCount,poseCount,vertexCount,influenceCount,Settings5,0,0,0;
// then all joints33, all poses17, all vertices4(position3,influenceCount),
// then flat influences2(id,authorWeight), in vertex order. The influence-count
// sum must equal the header. Native Settings maxima remain128/65536/262144;
// actual exchange maxima are128 bones/2048 vertices/8192 influences. No split.
// Every exchange value must be finite, IDs exact1..2^53-1, count/settings budgets
// integer. Finite matrix/weight/quality-model failures return PP_SIM_OK and a
// new core-status record; invalid exchange/getters preserve old record/output.
// Summary8: coreStatus,hasResult,itemCount,diagnosticCount,weightResidualCount,0,0,0.
// bind kind0=joint33,kind1=diagnostic6. deform kind0=position3,kind1=diagnostic6,
// kind2=weightResidual1. Diagnostic6=id,hasCondition,conditionOr0,
// hasResidual,residualOr0,pivotFailure. Failure diagnostics are a prefix only.
// Independent copied snapshots; global reset clears both. No normals/GPU proof.
int32_t pp_sim_skin_bind(uint32_t value_count);
int32_t pp_sim_skin_bind_record(uint32_t kind,uint32_t index);
int32_t pp_sim_skin_deform(uint32_t value_count);
int32_t pp_sim_skin_deform_record(uint32_t kind,uint32_t index);
// Pure local Float32 derived mesh. Header8: vertexCount,triangleCount,
// maxVertices,maxTriangles,sqrtRefinements,0,0,0; then vertex positions3.
// Separate U32 exchange contains triangle indices3. Exact lengths are required.
// Actual exchange maxima are2048 vertices/32768 triangles; no split/truncation.
// Empty arrays and all uint32 settings/indices pass to the unchanged core model.
// Nonfinite/noninteger/negative/oversize/length/reserved exchange errors retain
// the previous derived snapshot and output. Accepted model failure replaces it
// with a geometry-null record; audits are a diagnostic prefix, not render data.
// Summary20: status,reason,hasGeometry,outVertices,outTriangles,auditCount,
// floatCount,hasFailedVertex,failedVertexOr0,hasFailedFace,failedFaceOr0,
// sqrtTotal,limitedFaces,0,minimum3,maximum3. Bounds are zero without geometry.
// Getter kind0=vertex3,kind1=triangle3,kind2=expanded face18,kind3=audit26:
// face,cross6,Q2,hasNormalized,normalized6Or0,hasNormal,normal3Or0,
// hasError,error3Or0,sqrtCount,limited. Float32 values widen exactly to double.
// Invalid getter retains snapshot/output. Global reset clears this independent
// snapshot; World, skin, motion and optical records remain independent.
// This certifies quantized LOCAL geometry only, not world/GPU/raster operations.
int32_t pp_sim_derived_mesh(uint32_t f64_count,uint32_t u32_count);
int32_t pp_sim_derived_mesh_record(uint32_t kind,uint32_t index);
int32_t pp_sim_polarized_packet(uint32_t value_count);
int32_t pp_sim_polarized_packet_record(uint32_t index,uint32_t part);
int32_t pp_sim_polarized_packet_segment(uint32_t packet_index,uint32_t index,uint32_t part);

// Source launch[9]: kind(0 finite point/1 parallel),reference3,launchPoint3,tMin,tMax.
// Out[14]: originBounds6,directionBounds6,tMin,tMax. Finite D=P-O uses outward
// subtraction in C++; parallel D is the supplied vector. No normalization.
int32_t pp_sim_optical_launch_ray(uint32_t value_count);
// Prescribed-route finite geometric spot, not brightness/continuous-pupil PSF.
// Input[21+14S+15N]: N,S,index2,wavelength,sensorCenter3,sensorNormal3,
// sensorAperture,sensorTMin,sensorTMax,maxRouteSteps,parameterWidth,primitiveSqrt,
// maxSamples,maxEvaluations,totalSqrt,reserved0; then S route steps as above;
// N samples: originBounds6,directionBounds6,tMin,tMax,positive geometric weight.
// Out[32]: status,records,evaluations,accepted,routeMisses,branchUnavailable,
// sensorMisses,unknown,geometryQueries,interfaceQueries,sqrtRefinements,limited,
// hasStats,hasMoments,totalWeight2,acceptedWeight2,centroid6,MSR2,hull6.
// Unknown/unevaluated samples prohibit stats. Model failure is PP_SIM_OK data;
// invalid exchange retains previous output/record. Full contract: OPTICAL_SPOT.md.
int32_t pp_sim_optical_spot(uint32_t value_count);
// Snapshot part 0[34]: ordinal,weight,status,hasRoute,routeStatus,completedSteps,
// failedStep,geometryQueries,interfaceQueries,sqrtRefinements,limited,
// hasCompletion,origin6,direction6,tMin,tMax,index2,distance2,OPL2,throughput2.
// Part 1[46]: ordinal,weight,status,hasSensor,reserved0,boundedGeometry[41].
int32_t pp_sim_optical_spot_sample(uint32_t index,uint32_t part);

// Creation returns 0 on failure; inspect last_status/error. All other operations
// return a status. Failure preserves resource state and the prior output span.
pp_sim_handle pp_sim_world_create(void);
int32_t pp_sim_world_destroy(pp_sim_handle world);
int32_t pp_sim_world_reset(pp_sim_handle world); // Empty world, default gravity, time/tick zero.
int32_t pp_sim_world_set_gravity(pp_sim_handle world,uint32_t value_count); // Input F64[3].
int32_t pp_sim_world_info(pp_sim_handle world); // Output gravity3,bodyCount,planeCount,time,tick.
// Read-only normal support query, never advances/changes physical World/loads.
// Settings[10]: gapBand,velocityWidth,accelerationTol,complementarityTol,
// projectedForceTol,minScaledPivot,maxForce,maxIterations,maxContacts,maxPairs.
// Output[21]: success,failure,pairs,separated,resting,separating,iterations,
// maxGeometryOffset,maxVelocityWidth,minScaledPivot,negativeForce,
// negativeAcceleration,complementarity,projectedForce,maxAccelWidth,
// constraintCount,bodyCount,firstID,secondID,queryTime,queryTick.
// Model/budget failure is data with success=0. Bad ABI input retains prior output
// and prior record. Records are snapshots until next valid attempt/reset/destroy.
int32_t pp_sim_world_support(pp_sim_handle world,uint32_t value_count);
// Last support record: constraint[24] = IDs2,phase,guarded,normal3,
// normalLower3,normalUpper3,gap2,vn2,curvature2,freeAccel,lambda,normalAccel,
// accelBounds2. body[22] = ID,force3,normalTorque3,forceLower3,forceUpper3,
// acceleration3,accelerationLower3,accelerationUpper3. Failed candidates are NOT
// usable reaction solutions. Retrieval does not change the stored summary.
int32_t pp_sim_world_support_constraint(pp_sim_handle world,uint32_t index);
int32_t pp_sim_world_support_body(pp_sim_handle world,uint32_t index);

// Body input F64[28]: id,static(0/1),mass,radius,Ixyz,pXYZ,qXYZW,vXYZ,
// LXYZ,Fxyz,torqueXYZ,restitution,friction. IDs are exact integers 1..2^53-1.
// Output appends omegaXYZ,kineticEnergy,time,tick. No angular velocity setter:
// world angular momentum is the state used by the common C++ dynamics core.
int32_t pp_sim_world_body_add(pp_sim_handle world,uint32_t value_count);
int32_t pp_sim_world_body_set(pp_sim_handle world,uint32_t value_count);
int32_t pp_sim_world_body_get(pp_sim_handle world,double body_id);
// Plane F64[8]: id,normalXYZ,offset,restitution,friction,reserved(0).
int32_t pp_sim_world_plane_add(pp_sim_handle world,uint32_t value_count);
int32_t pp_sim_world_step(pp_sim_handle world,double dt,uint32_t steps);
// One transactional W1 tick, sphere proxies/static planes, no sustained support.
// Settings[16]: timeTol,spatialTol,minImpactSpeed,closingResidualTol,energyTol,
// maxEvents(<=32),maxSegments(<=65),maxPairs(<=100000),maxRoots(<=1000000),
// queryEvaluations(<=32768),queryFrontier(<=4096),queryDepth(<=128),
// solverIterations(<=128),maxContacts(<=8192),restitutionThreshold,maxAngularIncrement.
// Output[21]: success,failure,advancedDt,candidateTime,firstId,secondId,
// pairQueries,rootEvaluations,freeSegments,maxPropagationError,accPositionRoundoff,
// timeRoundoff,contacts,solverIterations,maxPenetration,normalImpulse,frictionImpulse,
// maxClosingResidual,eventCount,worldTime,worldTick.
// Valid queries returning success=0 use PP_SIM_OK: model/budget failure is data,
// world/loads/time/tick are retained. Invalid ABI calls retain prior output.
int32_t pp_sim_world_step_continuous(pp_sim_handle world,double dt,uint32_t value_count);
// Last continuous attempt's events, even if it later rolled back. Diagnostic
// candidate events are NOT committed motion on failure. Record persists until
// next continuous attempt/reset/destroy; other world edits do not rewrite it.
// Output[8]: respondedAt,entryLo,entryHi,maxGap,propagationError,firstId,secondId,contacts.
int32_t pp_sim_world_ccd_event(pp_sim_handle world,uint32_t index);

// Transactional W2 normal-only RATTLE/near-impact tick; explicit zero-friction
// materials required. All accepted DEFINED numerical dense paths are audited;
// this does not certify the continuous mechanical solution. Settings[33] and
// summary[32] layouts are documented in docs/SIMULATION_ABI.md. Finite model
// failure is data (PP_SIM_OK, success=0), retaining bodies/loads/time/tick.
int32_t pp_sim_world_step_supported(pp_sim_handle world,double dt,uint32_t value_count);
// Snapshot of last W2 attempt, including diagnostic events on rollback.
// Output[12]: kind,at,firstID,secondID,normal3,contacts,impulseSum,
// kineticBefore,kineticAfter,maximumGap. Other queries/edits do not rewrite it.
int32_t pp_sim_world_supported_event(pp_sim_handle world,uint32_t index);

// Hull consumes F64[3*vertex_count] positions and U32[3*triangle_count] indices.
// Both arrays start at exchange offset 0. Every shell must be closed/outward.
pp_sim_handle pp_sim_hull_create(uint32_t vertex_count,uint32_t triangle_count);
int32_t pp_sim_hull_replace(pp_sim_handle hull,uint32_t vertex_count,uint32_t triangle_count);
int32_t pp_sim_hull_destroy(pp_sim_handle hull);
// Hydro F64[16]: rho,g,waterLevel,positionXYZ,qXYZW,scaleXYZ,CoMXYZ.
// Output[14]: forceXYZ,torqueXYZ,wetArea,V,totalVolume,shells,hasCoB,CoBXYZ.
// Dry CoBXYZ are zero, hasCoB=0; wet hasCoB=1. No NaN null sentinel.
int32_t pp_sim_hydro_query(pp_sim_handle hull,uint32_t value_count);
// Buoyancy F64[9]: rho,g,waterLevel,hullOriginBodyXYZ,scaleXYZ. One dynamic
// body/no planes. Calls the existing C++ two-load midpoint coupling each step.
int32_t pp_sim_world_buoyancy_step(pp_sim_handle world,pp_sim_handle hull,double body_id,
                                  double dt,uint32_t steps,uint32_t value_count);
// Step output[22]: last midpoint hydro result[14] (zeros for plain world_step),
// maxContacts,maxVelocityIterations,maxPenetration,sumNormalImpulse,
// sumFrictionImpulse,maxClosingResidual,elapsedSeconds,totalTicks.

#ifdef __cplusplus
}
#endif
#endif
