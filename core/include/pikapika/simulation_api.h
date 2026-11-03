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

// Creation returns 0 on failure; inspect last_status/error. All other operations
// return a status. Failure preserves resource state and the prior output span.
pp_sim_handle pp_sim_world_create(void);
int32_t pp_sim_world_destroy(pp_sim_handle world);
int32_t pp_sim_world_reset(pp_sim_handle world); // Empty world, default gravity, time/tick zero.
int32_t pp_sim_world_set_gravity(pp_sim_handle world,uint32_t value_count); // Input F64[3].
int32_t pp_sim_world_info(pp_sim_handle world); // Output gravity3,bodyCount,planeCount,time,tick.

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
