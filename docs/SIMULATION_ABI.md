# Simulation C ABI v1: shared native dynamics and hydrostatics

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
