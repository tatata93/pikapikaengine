# Native rigid-body foundation: first verified subset

The native library now integrates six degrees of freedom and solves contact
impulses between spheres and static planes, and between pairs of static/dynamic
spheres. This is a reusable numerical foundation. It is not a complete physics
engine, vehicle model, flight model, railway model, or claim of DCS/Forza/Train Sim
World accuracy. No third-party physics library is linked. Browser integration is
a later step; the existing portable WASM ABI remains unchanged.

## State and public operations

Include `pikapika/dynamics.hpp`; the namespace is `pikapika::dynamics`.

| API/state | Meaning and units |
| --- | --- |
| `RigidBody::id` | Stable positive integer ID, shared uniqueness with planes |
| `mass` | kg; static bodies retain descriptive mass but have zero inverse mass |
| `inertia_diagonal` | Principal body-frame moments in kg m² |
| `position`, `velocity` | Centre of mass in world metres and m/s |
| `orientation` | Normalized body-to-world quaternion, `(x,y,z,w)` |
| `angular_momentum` | **World-frame** angular momentum in kg m²/s |
| `force`, `torque` | Accumulated world-frame N and N m, held constant during one step |
| `radius` | Sphere collision proxy radius in metres |
| `World::apply_force(id,F,point)` | Adds force and the corresponding `(point-position) × F` torque |
| `apply_torque`, `apply_impulse` | Direct torque, or point impulse including angular momentum change |
| `World::step(dt,settings)` | Transactional integration/contact solve; returns diagnostics |

`make_sphere` gives a uniform solid sphere its analytic principal moments
`I = 2 m r² / 5`. An explicitly supplied diagonal inertia can instead describe a
body whose collision sphere is a proxy. The principal axes must be the authored
body axes, and moments must be positive and satisfy the inertia triangle
inequalities. This stage does not compute mesh mass properties or infer material
density from appearance.

The frame is right-handed, with +Y up by default. Gravity is an editable world
acceleration; the default is `[0,-9.80665,0]` m/s². Static bodies cannot carry
nonzero velocity or angular momentum. Applying forces/impulses to a static body
is a documented no-op. Kinematic bodies are not implemented.

## Integration and gyroscopic behaviour

For held world force/torque, translation uses the constant-acceleration update
`p_next = p + v dt + (g + F/m) dt²/2`, `v_next = v + (g + F/m) dt`.
World angular momentum advances with `L_next = L + torque dt`.
Angular velocity is evaluated as

```text
omega(q,L) = R(q) diag(1/Ix,1/Iy,1/Iz) transpose(R(q)) L
```

Orientation uses an explicit midpoint rotation update: estimate a half-step
orientation using the initial angular velocity, evaluate angular velocity there
using half-step momentum, and left-multiply the initial quaternion by the
full-step rotation quaternion from that midpoint velocity. Quaternion products
are normalized. This is a second-order rotation approximation, not an exact
general rigid-body solution or a claim of exact rotational-energy conservation.

World L is the state, so zero applied torque keeps it unchanged while an
anisotropic body's angular velocity evolves with orientation. The gyroscopic
term has not been silently removed. A test also compares the numerical initial
body-frame angular acceleration against Euler's torque-free equation
`I domega/dt = -omega × (I omega)`.

Successful steps consume force and torque. Callers reapply continuous loads each
fixed tick. A step accepts `0 < dt <= 0.1` seconds. The default maximum angular
increment is 0.5 rad per step; an unresolved larger rotation fails and asks the
caller to reduce dt. Nothing silently clamps angular speed or discards elapsed
simulation time. Smaller dt improves rotational accuracy; the translation formula
is exact only for the held-acceleration assumption.

## Contacts, friction and stabilisation

The current step first predicts poses/momenta, generates discrete contacts, then
iterates velocity impulses and finally applies a separate positional correction.
Planes are static infinite half-spaces, defined by unit normal `n` and offset
`n dot x = offset`. Their positive-normal side is the legal region. Sphere pairs
have a single common contact point. Perfectly coincident centres use a fixed X
normal because their geometric separation direction is undefined.

Point velocity includes `v + omega × r`. Impulses update both linear velocity and
world angular momentum; effective masses include the point-torque response
through world inverse inertia. Each contact accumulates a nonnegative normal
impulse during the bounded sequential solve. Tangential impulses solve a 2-by-2
effective-mass quadratic constrained to a circular Coulomb disk. When the free
minimum is outside that disk, a bounded 48-iteration scalar bisection finds its
constrained minimum; it does not radially clamp an anisotropic mass matrix.

The coefficient mix is an explicit modelling choice: friction is the geometric
mean of the two coefficients; restitution is their maximum. These are not
measured universal material-combination laws. Restitution is the normal relative
speed ratio, bounded to 0..1, and is suppressed for approach speeds below the
default 0.5 m/s threshold to reduce resting jitter. One Coulomb coefficient is
used for both sticking and sliding. Rolling resistance, contact compliance,
adhesion, tire brush models and rail creep are absent.

Default velocity iterations are 16, bounded to 1..128. The solver accumulates
impulses within a step but does not yet warm start across steps. Geometry is
corrected separately by 80% of penetration beyond 0.00001 m, capped at 0.2 m per
contact/step. This correction does not directly change velocity. It is a
numerical stabiliser, not a physical force: gravitational potential energy and
orbital angular momentum are not claimed to be conserved by that projection.
Conservation tests for isolated pairs disable it when checking total angular
momentum. Finite iterations leave a reported residual; exact global contact
complementarity or an energy theorem for arbitrary simultaneous impacts is not
claimed.

## Bounded domain and current gaps

The current world permits at most 1024 bodies and 64 planes. The default contact
budget is 16384, configurable up to 65536. Overflow fails the entire step instead
of omitting contacts. Candidate state is committed only after successful
integration and solving; an invalid step leaves bodies and accumulated loads
unchanged. Stable-ID ordering fixes processing order in the same environment;
cross-CPU/compiler bit identity is not established.

Input guards limit mass and principal moments to `[1e-12,1e18]`, radius to at most
1e9 m, position components to ±1e12 m, linear velocity to ±1e9 m/s, and L/force/
torque components to ±1e24 in their respective units. These are overflow guards,
**not validated accuracy ranges**. The solver additionally rejects ill-conditioned
tangent effective masses. Friction coefficients are limited to 0..10.

Collision search is currently quadratic in body count. There is no continuous
time-of-impact solve in this pipeline: fast spheres can pass between discrete
samples, and impacts can temporarily penetrate. The engine's existing swept
sphere helper is separate and has not been connected here. There are no boxes,
convex hulls, concave meshes, contact manifolds, joints, suspension, tires,
deformables, terrain contact, wheel-rail contact, aerodynamics or control systems
in this module. The existing browser action controller and its bounding-box
collision path remain separate. These boundaries must be extended and tested
before claiming vehicle, aircraft, or railway simulation capability.

## Reproduce the verification

```powershell
./scripts/build-native.ps1
./build/native/Release/pikapika_dynamics_tests.exe
New-Item -ItemType Directory -Force ./build/native/dynamics-proof
./build/native/Release/pikapika-dynamics.exe --steps 1200 --csv ./build/native/dynamics-proof/steps.csv
```

The tests compare free fall, force/torque acceleration, constant-axis rotation,
isolated elastic/inelastic impacts, integrated weight support, and rolling down
an incline against independent analytic values. They check frictional spin,
Coulomb bounds and no kinetic-energy increase in specified isolated cases,
world-L conservation, the Euler gyroscopic derivative, a small resting stack,
and transactional error handling.

An anisotropic free-rotation convergence test integrates four seconds at dt
1/30, 1/60 and 1/120 s. Basis-vector orientation errors versus a fine 1/15360 s
numerical reference were respectively 0.000223214459152, 0.0000555889184492 and
0.0000138698177533. The first ratio was 4.01545, consistent with second order.
That reference shares the integrator and demonstrates self-convergence only;
it is not an independent physical ground truth. Independent analytic rotation
and Euler-equation tests address different correctness questions.

The CLI benchmark uses 64 sphere proxies, a static plane, 1200 fixed 1/120 s
steps and 16 velocity iterations. The recorded run had 79903 generated
contacts, maximum 75 in one step, maximum penetration 0.03583125 m, and maximum
closing-speed residual 0.000967745 m/s. Those finite-step errors remain visible.
CPU physics-step time was p50 0.7236 ms, p95 1.3869 ms, p99 3.2099 ms and maximum
3.7209 ms on the current workstation, while other development work was active.
No CPU physics step exceeded its 8.33333 ms tick budget in that run.
Raw steps are retained under `build/native/dynamics-proof/`; timings exclude CSV
output, rendering, audio, application scheduling and presentation. This is not a
60fps product result or a defined vehicle workload. Re-run on the intended
profile before using these values for a budget decision.

The report timestamp is 2026-11-03 02:50:44 JST
(`2026-11-02T17:50:44Z`). The build used MSVC 19.51.36247.0 in Release mode, with
revision base `2d6af6dea2cad9cb7406ed31e6cb4f1114be3da3` and a dirty working tree.
The benchmark JSON embeds that provenance and SHA256 values for dynamics source,
public header, benchmark source, shared core source and core header; all five
were compared with the current files and matched. The base commit alone is not
the exact uncommitted source. Full solver configuration is embedded alongside
results, including contact budget, tolerances, material mix inputs, angular-step
limit and friction bisection count. Raw CSV contains all 1200 steps without
post-hoc removal. The previously recorded native hardware profile identifies
the workstation as an i5-6500 with approximately 15.94 GiB RAM on Windows
10.0.19045; this CPU benchmark does not use the GPU for physics.

## Primary references checked on 2026-11-03 JST

- David Baraff, 1997, [Rigid Body Simulation I—Unconstrained Rigid Body
  Dynamics](https://www.cs.cmu.edu/~baraff/sigcourse/notesd1.pdf): world momentum,
  body/world inertia and quaternion dynamics. The state representation follows
  these physical relationships; the explicit midpoint implementation is our own.
- David Baraff, 1997, [Rigid Body Simulation II—Nonpenetration
  Constraints](https://www.cs.cmu.edu/~baraff/sigcourse/notesd2.pdf): collision
  impulse response and the distinction between impact and resting contact. This
  implementation remains a limited discrete iterative approximation.
- Erin Catto, 2006, [Fast and Simple Physics using Sequential
  Impulses](https://box2d.org/files/ErinCatto_SequentialImpulses_GDC2006.pdf):
  accumulated contact impulses, point-velocity effective mass and bounded
  sequential iteration. The slides also discuss simplifications that are not
  adopted here: in particular, their gyroscopic omission is not used. The
  3D tangent-disk solve, integration and data structures here are authored code.

Only references were consulted. Their PDFs, figures and example code are not
copied into the product or repository. No additional runtime dependency was
introduced.

## Internal split for later continuous stepping, 2026-11-03

Free propagation now preserves candidate force/torque; contact response can run
at the current poses without advancing time. The public discrete step retains
its original load-consumption, validation and commit order. The internal calls
require validated candidates and do not themselves promise candidate rollback.
With projection disabled, contact response changes velocity/momentum only.
Ten direct test groups and a frozen eight-case baseline check the split;
see [the implementation record](CONTINUOUS_WORLD_PLAN.md#実施r0-ccdの前提となる内部分離)
and [raw verification](../reports/2026-11-03-interval-foundation.md).
The old performance measurements above have not been rerun for this source;
the refactor does not establish a new timing result or complete World CCD.
