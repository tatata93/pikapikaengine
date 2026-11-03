# Simulation C ABI v1: shared physics and optical queries

The interface in `core/include/pikapika/simulation_api.h` calls the existing C++
`dynamics::World`, `hydrostatics::Hull`, static pressure integration and isolated
two-load midpoint buoyancy integrator. It does not reimplement those equations in
JavaScript. The existing 650-byte freestanding scalar ABI is unchanged and remains
a separate artifact. This interface is a first shared simulation subset, not
Windows/Web game parity, a complete physics engine, CFD, or a 60fps result.

## Ownership and lifetime

World and Hull are opaque `uint32_t` handles. Zero is never a valid handle.
Creating a resource returns its handle or zero; read `pp_sim_last_status()` and
the error text when creation returns zero. Other resource operations return a
status directly. A Hull is independent of a World: a buoyancy step receives both
handles, and does not transfer ownership. Destroy both resources when finished.

Handles encode a type, slot and 23-bit generation. Destroy advances the generation;
stale handles, wrong types and a second destroy fail. A slot reaching generation
8388607 is permanently retired rather than wrapping to a previous identity.
`pp_sim_reset()` does not unretire such slots. Resource exhaustion is an explicit
failure; a stale handle is never deliberately made valid again in that module.

`pp_sim_world_reset(world)` preserves the World handle but clears bodies/planes,
restores default gravity `[0,-9.80665,0]`, and resets elapsed seconds/ticks to zero.
It does not affect Hulls or other Worlds. Re-add initial body state and set the
desired gravity after resetting. `pp_sim_hull_replace` atomically rebuilds a Hull
under its current handle; there is no physically meaningful empty Hull state.
`pp_sim_reset()` is a module-wide teardown and invalidates **all** live handles;
ordinary application reset should use `world_reset`, not global reset.

Calls use one shared exchange area and are synchronous, non-reentrant and not
thread-safe. Use serialized access to one module instance. Host writes into
arbitrary linear memory, native pointer misuse and concurrent scratch-buffer
mutation are outside this interface's validation contract.

## Counted exchange buffers

The module owns these arrays for its entire lifetime. Callers never `malloc` or
`free` them, and never infer a C++ class/struct layout.

| Getter | Element type and capacity |
|---|---|
| `pp_sim_input_f64_ptr()` | Float64 input, 49152 elements |
| `pp_sim_input_u32_ptr()` | Uint32 input, 98304 elements |
| `pp_sim_output_f64_ptr()` | Float64 output, 64 elements; read-only contract |
| `pp_sim_output_count()` | Number of currently valid output elements |
| `pp_sim_*_capacity()` | Runtime capacity check matching the header constants |

Each input begins at element zero of its buffer. Counts are **elements**, not
bytes. Mesh calls take vertex and triangle counts, each implying three elements.
The fixed scratch buffers consume approximately 0.75 MiB in total, plus the small
output/error arrays. Resource objects and core temporary work allocate additional
bounded-by-profile data; that is not a proof of their exact peak heap usage.

An operation may allocate and grow WebAssembly memory. A JS TypedArray retained
from before growth can become detached or refer to an old buffer. Reacquire the
module memory/heap views and the pointer getters after calls that may allocate.
Copy the returned output span before another operation overwrites it. Do not
keep the shared output view as persistent game state. A successful non-output
operation sets `output_count` to zero; old bytes then have no valid output span.

Native code receives real pointers; WASM exports expose numeric byte addresses.
Float64 element offsets divide byte addresses by 8; Uint32 offsets divide by 4.
The JS adapter must validate JS integer/count types before WASM's i32 coercion.
Handles should be treated as unsigned 32-bit values, not signed IDs. Body and
plane IDs are Float64 integers in `1..9007199254740991`; they are not truncated to
32 bits. All physical values use Float64 SI units and right-handed coordinates.

## Exact array layouts

Body input to `world_body_add/set` requires exactly **28** Float64 values.

| Offset | Values |
|---|---|
| 0 | stable ID |
| 1 | static flag, exactly 0 or 1 |
| 2, 3 | mass kg, sphere proxy radius m |
| 4..6 | principal body inertia XYZ, kg m² |
| 7..9 | world CoM position XYZ, m |
| 10..13 | body-to-world quaternion XYZW |
| 14..16 | world linear velocity XYZ, m/s |
| 17..19 | world angular momentum XYZ, kg m²/s |
| 20..22 | accumulated held force XYZ, N |
| 23..25 | accumulated held torque XYZ, N m |
| 26, 27 | restitution, Coulomb friction coefficient |

`world_body_add` rejects duplicate IDs, including collisions with plane IDs.
`world_body_set` updates an existing ID after complete validation; it does not
create a missing body. `world_body_get(world,id)` returns those 28 values plus
omegaXYZ at 28..30, kinetic energy J at 31, elapsed seconds at 32 and total ticks
at 33, for **34** outputs. Angular momentum remains the angular state; angular
velocity is derived through the common world inertia implementation.

Plane input is **8** Float64 values: ID, unit normalXYZ, offset m, restitution,
friction, reserved zero. Its legal half-space follows the existing static-plane
model. `world_info` outputs **7** values: gravityXYZ, body count, plane count,
elapsed seconds and ticks. Setting gravity requires exactly **3** input values.

Hull create/replace consumes packed Float64 positions `[x0,y0,z0,...]` and packed
Uint32 triangle indices `[i0,j0,k0,...]`. The vertex and triangle counts must fit
the limits below. The common Mesh/Hull validators reject nonfinite coordinates,
bad indices, degenerate/Float32-collapsing faces, open/inconsistent/nonmanifold
edges and nonpositive per-shell volume. They do not establish absence of
self-intersections, intersecting shells or unsupported nested cavities.

Static hydro input is exactly **16** Float64 values:

| Offset | Values |
|---|---|
| 0..2 | density kg/m³, positive gravity magnitude m/s², water level m |
| 3..5 | mesh origin world position XYZ |
| 6..9 | mesh orientation quaternion XYZW |
| 10..12 | positive scaleXYZ |
| 13..15 | world CoMXYZ for pressure torque |

Hydro output is **14** values: forceXYZ 0..2, CoM torqueXYZ 3..5, wet area m² at 6,
submerged volume m³ at 7, total volume m³ at 8, shell count at 9, has-CoB flag at
10, and world CoBXYZ 11..13. Dry output has flag zero and zero centroid elements;
there is no NaN/null sentinel. Only read the centroid when flag is one.

Buoyancy input is exactly **9** values: density, gravity magnitude, water level,
body-frame hull-origin offsetXYZ and positive scaleXYZ. `world_buoyancy_step`
requires one dynamic body, no planes, matching -Y gravity, and calls the existing
isolated two-load midpoint integrator each tick. It does not use the collision
sphere to calculate displacement or replace the hull with a box. Body mass,
inertia and CoM are supplied separately; modifying a Hull does not recalculate
them. The proxy/hull differences and physical assumptions remain those in
[BUOYANCY.md](BUOYANCY.md).

Both step operations return **22** values. For a buoyancy call, 0..13 are the
**last inner tick's midpoint hydro load**. Plain `world_step` puts zeros there.
Offsets 14..21 are max contacts, max velocity iterations, max penetration,
sum normal impulse, sum friction impulse, max closing residual, final elapsed
seconds and total ticks. Maxima/sums cover the entire requested batch. A batch's
output is not an array of every inner tick; call one tick at a time for raw traces.

## Budgets, errors and transactional failure

| Scope | C ABI profile limit |
|---|---|
| Live resource handles | 16 Worlds, 32 Hulls |
| Per World | 128 bodies, 8 static planes, 8192 generated contacts per inner step |
| Per Hull | 3..16384 vertices, 1..32768 triangles |
| All live Hulls | 65536 vertices, 131072 triangles |
| Per step call | 1..32 ticks, each `0 < dt <= 0.1` seconds |
| Counters | elapsed seconds <=1e9, ticks <=2^53−1 |
| Error buffer | 256 bytes including terminating zero |

This is an explicit transport/runtime profile narrower than the full native
authoring quotas. Exceeding it fails; geometry, collisions and ticks are never
silently removed. Core mass/inertia, quaternion, coordinate and angular-step
guards remain active. The 0.5-radian default angular increment can reject a step
and require a smaller dt. Successful core ticks consume held force/torque; in a
multi-tick plain batch an initial held load is consumed by its first tick.

Status codes are 0 OK, 1 invalid ABI argument/count/ID, 2 invalid/stale handle,
3 explicit budget exceeded, 4 common core validation/numerical rejection,
5 allocation failure and 6 unknown internal exception. The boundary catches
C++ exceptions and uses bounded, zero-terminated diagnostic text. Pointer,
capacity, output-count and diagnostic getters do not clear an error. Other
successful operations clear it; capture text before issuing another operation.

A failed operation retains the prior valid output span and resource state.
Hull replacement builds a candidate before swapping. Stepping runs the entire
batch against a candidate World and commits only after all ticks succeed, so a
later failed tick also rolls back earlier candidate ticks and consumed loads.
Global lifecycle counters/quota accounting are changed only at commit. Scratch
input is caller-owned content in module storage; it is not rolled back.

The allocation catch is present, but quota tests are not an exhaustive forced-OOM
test of every native/WASM runtime configuration. Toolchain memory-growth/abort
behaviour and final heap limits require the separate WASM build verification.

## Native verification and parity probe

```powershell
./scripts/build-native.ps1
./build/native/Release/pikapika_simulation_api_tests.exe
./build/native/Release/pikapika-simulation-probe.exe --fixtures
```

Native Release CTest passed 4/4, including 16 C ABI groups. Cases cover independent
Archimedes displacement/eccentric moment, dry centroid flags, analytic free fall
and force acceleration, actual sphere-plane impulse/restitution, equilibrium,
second-order heave convergence, rollback after a later batch tick fails, invalid
counts/IDs/NaNs, failed Hull replacement and reuse, every handle-count boundary,
body/plane limits, an exact-capacity 16384-vertex upload, the total live vertex
quota and 512 create/destroy cycles with stale-handle checks. Generation exhaustion
at millions of cycles is prevented by explicit retirement logic, not exercised
by that short lifecycle test.

`tools/simulation_probe.cpp` emits JSON through this C ABI. It includes the exact
mesh, four static hydro input/output fixtures, and five buoyancy traces:
equilibrium (120 ticks), heave at 30/60/120 Hz (two seconds each), and ballasted
roll (240 ticks). Each trace includes gravity, exact initial body input, buoyancy
input, dt and every Float64 body output including the initial state. A separate
`worldTraces` entry contains 100 ticks of free fall with a first-tick held force
and torque. Nothing is a prerecorded renderer substitute: these are reproducible
comparison outputs for the actual exported operations.

Native raw output is retained at
`build/native/simulation-proof/probe.json` and `test-output.txt`. The final generic
trace has y≈95m, vy≈−10m/s, Lz=0.08kg m²/s, omegaZ=0.024rad/s, time≈1s and tick100;
the initial held loads have been consumed. `node scripts/verify-simulation.mjs`
executes the committed WASM against this probe, including source/artifact/notice
hash verification. All 30180 values passed on Windows MSVC and Linux GNU native
builds; [results and public proof](../reports/2026-11-03-wasm-simulation.md).
Parity checks
implementation sharing, not independent physical ground truth or unconditional
cross-backend bit identity. No ABI-only test proves visible presentation cadence,
gameplay completeness or a production precision/60fps profile.

## Browser API

Serve the project over HTTP/HTTPS; the engine loads the local generated ES
module, WASM and build manifest. No CDN or remote calculation service is used.

```js
import {loadSimulationRuntime} from './engine/simulation.mjs';
const runtime = await loadSimulationRuntime();
const world = runtime.createWorld({gravity: [0, -9.80665, 0]});
try {
  world.addBody({id: 1, mass: 10, radius: 0.5, position: [0, 10, 0]});
  world.addPlane({id: 2, normal: [0, 1, 0], offset: 0});
  world.step(1 / 120);
  console.log(world.getBody(1)); // Copies pose/velocity/momentum/time/tick.
} finally {
  world.dispose();
}
```

`runtime.createHull(sourceMesh)` returns a reusable, validated displacement hull;
its `query()` computes static hydrostatic loads and `world.buoyancyStep(hull, …)`
advances the isolated one-body reference. See `engine/simulation.mjs` for the
specific options and `tools/float-lab.mjs` for the actual fixed-clock sample.
The JS adapter returns copied snapshots and re-reads module memory views after
calls. Body IDs retain the exact 1..2^53−1 range; they are not 32-bit handles.
World/Hull are explicit resources: dispose them after use. This API has discrete
sphere/plane contact, not complete CCD or arbitrary mesh collision.

## Stateless linear contact-time queries (additive v1 exports)

`pp_sim_sphere_sphere_toi(15)` and `pp_sim_sphere_plane_toi(15)` use the same module
exchange arrays. They allocate no World/Hull and do not advance, mutate or resolve
an existing world. Input is exactly 15 Float64 values:

| Query | Input offsets |
|---|---|
| sphere/sphere | A position0..2, A velocity3..5, A radius6, B position7..9, B velocity10..12, B radius13, horizonSeconds14 |
| sphere/plane | sphere position0..2, velocity3..5, radius6, plane normal7..9, offset10, plane velocity11..13, horizonSeconds14 |

Output13: `kind,motion,hasTime,time,normalX,normalY,normalZ,normalValid,atHorizon,roundoffSensitive,initialGap,initialNormalSpeed,normalSpeed`.
Kind codes are none0, initial_overlap1, initial_touch2, impact3, grazing4, uncertain5.
Motion codes are stationary0, approaching1, separating2, tangential3. An absent
time is encoded with hasTime0/time0, distinct from an initial event at time0.
Normals point A→B for spheres and plane→sphere for the plane query; coincident
sphere centres do not have a unique normal. Time is seconds, gaps metres and
normal speeds metres/second. At coincident centres, normalValid is false,
initialNormalSpeed stores the right derivative of separation (relative speed),
and normalSpeed0 is an invalid-normal placeholder, not a physical zero normal
velocity. Consumers must check normalValid. Domain errors are caught as CORE_REJECTED and leave
prior output intact; invalid value counts are INVALID_ARGUMENT.

The JavaScript adapter translates codes into strings and absent time into null:

```js
const hit = runtime.querySphereSphere(
  {position: [-3, 0, 0], velocity: [1000, 0, 0], radius: 0.5},
  {position: [0, 0, 0], velocity: [0, 0, 0], radius: 0.5},
  1 / 120
);
console.log(hit.kind, hit.time); // impact, approximately 0.002 seconds
```

The trajectories are linear with fixed radii/plane normal. These functions do
not include acceleration, gravity, rotation, impulse response, event ordering
or remaining-time advancement. `uncertain` is a candidate around a numerical
boundary; `roundoffSensitive` is a diagnostic guard, not a rigorous interval
certificate. See [CONTINUOUS.md](CONTINUOUS.md) for the declared domain, independent
analytical tests and limitations. The existing World step remains discrete.

## Constant-acceleration enclosure queries (additive v1 exports)

`pp_sim_accelerated_spheres(25)` and `pp_sim_accelerated_plane(19)` are stateless
queries. A sphere record is ten values: positionXYZ, velocityXYZ,
accelerationXYZ, radius. Pair input is two records, horizonSeconds, then four
settings: timeToleranceSeconds, maxEvaluations, maxFrontier, maxDepth.
Plane input is one sphere record, normalXYZ, offset, horizonSeconds, then the
same settings. This plane is static; its arbitrary nonzero normal is interpreted
with an enclosed real length. It is not rounded into an exact unit vector.

The transport profile caps evaluations at 32768, frontier at 4096, and depth at
128. Integer settings must be exact nonnegative integers (evaluations/frontier
at least one). Count/setting transport violations fail and retain prior output.
Exhausting a valid exploration budget is instead a successful query carrying
an **unresolved** physical result. See [ACCELERATED.md](ACCELERATED.md) for the
finite input domain, enclosure assumptions and root-search acceptance.

| Output offset | Values |
|---|---|
| 0, 1 | kind (none0 / entry_bracket1 / unresolved2), reason |
| 2, 3 | initialSeparationProven, safeUntil seconds |
| 4..6 | hasSafeValue, safe lower/upper bounds |
| 7..9 | hasInitialValue, initial lower/upper bounds |
| 10..12 | hasBracket, first-entry bracket lower/upper seconds |
| 13, 14 | hasNegativeWitness, negative witness seconds |
| 15..17 | hasNegativeValue, negative lower/upper bounds |
| 18..20 | evaluations, excludedIntervals, depthReached |

Reason codes are none0, initial_overlap1, initial_boundary2, evaluation_budget3,
frontier_budget4, depth_limit5, time_resolution6, numerical_uncertainty7. Missing
optional payloads are zero with flag zero. The JS adapter returns null for them.
If initialSeparationProven is true, the closed continuous prefix `[0,safeUntil]`
is strictly outside. A negative witness alone does not isolate the first entry.
An entry bracket requires that prefix, a negative point and the specified time
width. The returned function bounds have different dimensions for plane and
sphere-pair queries; do not treat both as distance errors in metres.

```js
const proof = runtime.queryAcceleratedPlane(
  {position:[0,3,0], acceleration:[0,-4,0], radius:1}, {}, 2,
  {timeTolerance:1e-7, maxEvaluations:32768}
);
console.log(proof.kind, proof.bracket); // first entry is enclosed near 1 second
```

`queryAcceleratedSpheres(a,b,horizon,settings)` uses the same sphere/options
schema. Optional velocity/acceleration default to zero. The plane wrapper
rejects nonzero plane velocity/acceleration. These queries do not mutate a World,
consume loads, respond to an impact, or solve persistent contact. In particular,
an initially touching or tangential trajectory can remain unresolved.

## Lossless dielectric interface (additive v1 export)

`pp_sim_dielectric_interface(9)` consumes propagationTowardInterfaceXYZ,
normalIntoIncidentMediumXYZ, indexIncident, indexTransmitted,
vacuumWavelengthMetres. It models a single flat nonabsorbing isotropic interface
with equal magnetic permeability. The two supplied positive real indices apply
at that wavelength; no dispersion data are evaluated automatically.

| Output offset | Values |
|---|---|
| 0, 1 | kind (transmission0 / total_internal_reflection1 / uncertain2), reason |
| 2..10 | approximate incidentUnitXYZ, normalUnitXYZ, reflectedXYZ |
| 11..14 | hasTransmitted, approximate transmittedXYZ |
| 15..21 | hasPower, Rs, Ts, Rp, Tp, R_unpolarized, T_unpolarized |
| 22..24 | approximate cosineIncident, hasCosineTransmitted, cosineTransmitted |
| 25 | supplied vacuum wavelength metres |
| 26..29 | original-input discriminant lower/upper, incident dot lower/upper |
| 30 | exactGrazing flag |

Reason codes: none0, incident_side1, critical_angle2, numerical_output3. Uncertain
returns neither power nor transmitted direction/cosine. TIR has power R1/T0
and no propagating transmitted direction. The exact-grazing result is a
one-sided limit. Check all flags; zero-filled absent data are not a physical
zero result. Returned powers are normal flux ratios, not field amplitudes or
radiance multipliers. Only the classification uses certified input intervals;
directions and power are ordinary numerical estimates. Physical assumptions,
normalization error, rounding clamps and limitations are in
[OPTICS_INTERFACE.md](OPTICS_INTERFACE.md).

```js
const interfaceResult = runtime.queryDielectricInterface({
  incident:[3,-4,0], normal:[0,1,0],
  indexIncident:1, indexTransmitted:1.5, vacuumWavelength:550e-9
});
```

The interface now has 36 additive v1 exports. A multi-surface lens, ghosts,
aberration, diffraction and renderer connection remain separate work.

## Surface geometry and polarized branches (additive v1)

`pp_sim_optical_geometry(count)` takes 19 doubles: shape (0 disk, 1 full sphere,
2 vertex cap), origin3, direction3, tMin, tMax, center-or-vertex3, normal-or-axis3,
signed radius, aperture radius, parameter tolerance, sqrt refinement budget.
Disk radius is reserved zero; full-sphere normal/axis and aperture are reserved
zero. Settings/domains are in [OPTICAL_GEOMETRY.md](OPTICAL_GEOMETRY.md).
The closed parameter interval is in metres; physical distance is t*|direction|.

| Output offsets | Meaning |
|---|---|
| 0..9 | status, reason, hasHit, rootCount, consideredCount, sqrtRefinements, refinementLimited, hasDiscriminant, Dlo, Dhi |
| 10..13 / 14..17 | Each candidate: tLo, tHi, state, reason |
| 18..21 | Accepted tLo,tHi, physicalDistanceLo,physicalDistanceHi |
| 22..27 / 28..33 / 34..39 | Position / geometric normal / incident-side normal: xLo,xHi,yLo,yHi,zLo,zHi |
| 40..41 / 42..44 / 45..47 / 48..50 / 51 | Parameter estimate, distance estimate / position estimate / geometric normal estimate / incident normal estimate / frontFace |

Status codes are hit=0, miss=1, unresolved=2. Reasons 0..12 are none,
no_real_roots, parallel, filtered_roots, parallel_or_coplanar,
tangent_or_discriminant, parameter_boundary, aperture_boundary, cap_boundary,
orientation, precision_limit, refinement_budget, numerical_output. Candidate
states 0..5 are not_examined, accepted, rejected_parameter, rejected_aperture,
rejected_cap, unresolved. Check flags: unused payloads are zero placeholders.
No implicit self-hit offset is added. A miss applies only to the requested domain.

`pp_sim_polarized_interface(count)` takes 16 doubles: the existing interface9,
transverse reference3, then Stokes I,Q,U,V. The frame is right-handed with
first×second=direction; V=2Im(Cxy), time convention exp(i k.x-i omega t).
See [POLARIZATION.md](POLARIZATION.md) for physical/range/conditioning limits.

| Output offsets | Meaning |
|---|---|
| 0..4 | failure, interfaceKind, interfaceUncertainty, hasReflected, hasTransmitted |
| 5..13 | Input frame: direction3,first3,second3 |
| 14..30 / 31..47 | Reflected / transmitted branch: frame9,Stokes4,amplitudeS(real,imag),amplitudeP(real,imag) |
| 48..51 | Original-input discriminantLo,Hi, incidentDotLo,Hi |
| 52..56 | cosineIncident,hasCosineTransmitted,cosineTransmitted,exactGrazing,wavelengthMetres |

Failure codes 0..3 are none, interface_uncertain, incidence_plane_uncertain,
numerical_output. Interface codes match the primitive interface. Uncertainty
supplies no branches. TIR supplies complex reflection phases and no propagating
transmission. Transmission amplitudes are power normalized, **not electric t**.
Stokes, frames and complex coefficients are numerical estimates, not intervals.
No separate-path coherence or wave-optical image integration is implied.

```js
const surface = runtime.queryOpticalSurface(
  {origin:[0,0,-3], direction:[0,0,2], maximumParameter:10},
  {kind:'cap', vertex:[0,0,0], axis:[0,0,1], signedRadius:2, apertureRadius:1}
);
const polarized = runtime.queryPolarizedInterface({
  incident:[.8,-.6,0], indexIncident:1.5, indexTransmitted:1,
  transverseReference:[0,0,-1], power:[1,0,1,0]
});
```

## Transactional W1 World step (additive v1)

`pp_sim_world_step_continuous(world,dt,count)` advances one requested tick.
It accepts 16 settings: timeTol, spatialTol, minimumImpactSpeed,
closingResidualTol, relativeEnergyTol, maxEvents, maxFreeSegments, maxPairQueries,
maxRootEvaluations, queryEvaluations, queryFrontier, queryDepth,
solverVelocityIterations, maxContacts, restitutionVelocityThreshold,
maxAngularIncrement. The bounded ABI profile caps counts at
32/65/100000/1000000/32768/4096/128/128/8192 respectively. Numeric model domains
and the unsupported sustained-support cases are in [CONTINUOUS_WORLD.md](CONTINUOUS_WORLD.md).
Position projection is disabled. Forces/torques are held over all subintervals.

Output21 is success, failure, advancedDt, candidateTime, firstId, secondId,
pairQueries, rootEvaluations, freeSegments, maximumPropagationError,
accumulatedPositionRoundoff, timeRoundoff, contacts, velocityIterations,
maxPenetration, normalImpulse, frictionImpulse, maxClosingResidual, eventCount,
worldTime, worldTick. Failure codes 0..12 are none, invalid_input, initial_contact,
query_unresolved, event_budget, segment_budget, query_budget, root_budget,
geometric_guard, propagation_failure, solver_failure, sustained_contact_required,
numerical_failure.

A well-formed call with a model/solver/budget failure returns **PP_SIM_OK and
success=0**. This is a diagnostic result: all World state/loads/clocks are retained,
advancedDt=0, and candidateTime/events do not represent committed motion.
Invalid handles/counts/ABI budgets retain the prior output and report a C error.
Successful calls commit the whole tick and consume loads exactly once.

`pp_sim_world_ccd_event(world,index)` returns 8 doubles from the last continuous
attempt: respondedAt, entryLo, entryHi, maximumGap, propagationError, firstId,
secondId, contacts. Times are relative to that attempt, not cumulative World time.
The bracket encloses the hypothetical unresponded free-trajectory entry from a
proved separated response time to a real-held-load negative witness; it is not
an exact impulse time. The record includes candidate events on failure and persists
until the next valid continuous attempt/reset/destroy. Other World edits do not
rewrite this historical diagnostic. Index errors retain the prior output.

JS `world.stepContinuous(dt, settings)` copies the summary and all events before
returning. It does not fall back to the discrete step on unsupported support.
