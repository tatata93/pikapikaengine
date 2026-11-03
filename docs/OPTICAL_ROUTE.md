# Prescribed optical route enclosure

`pikapika::optical_route::trace_route` composes the existing bounded geometry
and bounded-index dielectric kernels. It evaluates a **specified sequence of
surfaces and reflection/transmission choices**. It does not search a world for
the nearest surface, test visibility against unlisted surfaces, select a medium
from solid topology, enumerate ghost paths, or make a complete optical renderer.
The caller supplies the itinerary and the medium on each side consistently.

## API and units

The public header is `core/include/pikapika/optical_route.hpp`.

```cpp
using namespace pikapika;
optical_route::Step steps[] = {
    {optical_geometry::PlaneDisk{{0,0,0},{0,0,1},10},
     optical_route::Branch::transmitted, interval::Interval::point(1.5), 0,100}
};
auto result = optical_route::trace_route({
    optical_bounds::enclose_ray({{0,0,-1},{0,0,1},0,100}),
    interval::Interval::point(1), 550e-9, steps
});
```

`Input` contains an entire `BoundedRay` family, initial absolute index interval,
one point vacuum wavelength in metres, and a span of `Step`s. Each step contains
a variant of `PlaneDisk`, `FullSphere`, or `SphericalCap`, a chosen branch, an
other-side index **interval**, and an explicit closed parameter domain. Surface
shape values are binary64 point parameters, interpreted as exact real values;
the incident ray and refractive indices retain their full interval families.

Positions, distances and optical path lengths are metres. Direction is
dimensionless. For `P(t)=O+tD`, `t` is a metre-valued parameter and physical
distance is `t |D|`; a nonunit initial direction is supported. The step domain
overrides the incoming ray's domain for that intersection. The original input
ray domain is also validated. The final spawned ray uses the explicit default
continuation domain `[0,1e6]`; a subsequent step has its own domain.

The other-side index is used for Fresnel coefficients on **both** branches.
Reflection preserves the current index. Transmission assigns the entire
other-side interval as the current index. This is a lossless, isotropic,
equal-permeability, geometrical-optics model at that specified wavelength.
There is no absorption, scattering, coating, spectral integration, phase,
interference, delay or sensor response in this function.

## Composition and error retention

Each segment first calls `optical_bounds::intersect`. Only a certified whole-family
hit permits the dielectric calculation. `hit.incident_normal` points toward
the incident medium; `dielectric_interface_bounds` receives this entire normal
box, the incoming direction box, and both entire index intervals. A successful
requested branch is continued by `spawn_ray`, copying **every endpoint** of the
hit-position and outgoing-direction boxes. There is no midpoint replacement,
origin offset, implicit positive `tMin`, or automatic source-surface skip.

An exact source-plane hit at `t=0` can therefore be a valid explicitly requested
step. A position family that straddles that boundary is unresolved. A nonzero
caller-supplied `tMin` restricts the requested route, and proves nothing about
the excluded segment. Even an identity-index step still tests the surface and
its boundary; zero-power reflection is a defined branch with zero throughput.

The enclosure argument is induction: the initial box contains each admitted
ray; a completed geometry query encloses the prescribed accepted root for all
of it; the interface encloses that entire set's outgoing vectors and powers;
the copied boxes therefore contain every continued physical ray. Cartesian
boxes lose correlation and may grow. Failure to certify a larger box remains
an explicit failure, even when a narrower correlated representation could
succeed. Sampling is not used to choose a direction or certify a route.

For each successful segment, interval arithmetic encloses

```
distance += physical_distance
optical_path_length += current_index * physical_distance
```

The latter defines the piecewise homogeneous phase-index OPL, `sum n ds`, not
group delay. Reusing an index interval loses correlation conservatively; equal
nonpoint index intervals are not silently treated as an exactly equal medium.
Point-wavelength Cauchy/Sellmeier phase output can be supplied intact, including
all arithmetic uncertainty. The caller must check dispersion status and the
whole `within_interface_domain` flag. No median index is substituted.

## Arbitrary-polarization throughput bound

Multiplying each interface's unpolarized mean would assume a fresh unpolarized
state at every encounter. Reflection/transmission generally changes polarization,
so that is not used. Instead each selected branch supplies an envelope

```
factor = [min(Fs.lower,Fp.lower), max(Fs.upper,Fp.upper)]
throughput *= factor
```

Here `Fs,Fp` are its s/p **normal power-flux ratios**, not field amplitudes or
radiance factors. In a local orthogonal s/p basis an arbitrary incident
polarization's nonzero power ratio is `ws Fs + wp Fp`, where `ws,wp>=0` and
`ws+wp=1`. It lies between the two coefficients. Whatever the changed basis,
relative phase or polarization after a previous segment, the next ratio lies
in its own envelope; interval multiplication of nonnegative factors encloses
the product. A zero-power prefix stays within the resulting nonnegative bound.
Intersection with `[0,1]` uses the known lossless branch-power range.

This can be loose. It bounds any polarization on this path but does **not**
compute Jones/Stokes state, phase, interference between paths, or an exact
unpolarized route total. It makes no guarantee that both bounds are attained
by one initial polarization across all segments.

## Completion, failure, and budgets

Only `Status::completed` has `completion`: final ray, final medium interval and
final distance/OPL/throughput. `Segment` diagnostics retain incoming ray,
incident/other index, full geometry and interface results, and, on successful
steps, outgoing ray, selected factor and accumulated prefix totals.
`completed_steps` counts fully completed segments. `failed_step` is the next
attempted index or, on completion, the itinerary length. A failed attempted
segment may be present without outgoing data or accumulated totals. Prefix
totals are not a final route result.

| Status | Meaning |
|---|---|
| `completed` | Every prescribed step was certified. Empty itineraries are validated identity routes. |
| `geometry_miss` | Entire family misses the requested surface within its stated domain. |
| `geometry_unresolved` | Geometry did not certify uniform hit/miss, e.g. boundary or width. |
| `interface_unresolved` | Side, normal, critical or numerical interface test was inconclusive. |
| `branch_unavailable` | For example, transmission requested during certified total internal reflection. |
| `invalid_input` | Invalid scalar/vector/shape/domain/branch/profile. |
| `budget_exceeded` | Too many prescribed steps, or an unresolved primitive reports its refinement budget. |
| `numerical_failure` | Interval/environment or other caught numerical/library failure. |

The function is read-only: no external state, ray, surface or index is mutated,
including after failure. C++ exceptions from processing are converted to the
above status and diagnostic text. Allocation failure can still propagate if
the diagnostic itself cannot allocate; external objects remain unchanged.

`maximum_steps` must be `1..64`; an oversized itinerary fails before geometric
work. `primitive.max_sqrt_refinements` is `1..256` **per square-root endpoint**;
`maximum_parameter_width` is `(0,1e6]`. These are finite work limits, not an
accuracy promise. A primitive can exhaust refinement yet still prove its
necessary conditions with a coarse enclosure; such a certified result remains
usable and its limited flag is retained. Otherwise the route refuses to finish.
At most 64 surface and 64 interface calls occur. The current primitive code has
at most three square roots for a cap hit and five for an interface, each with
at most two endpoints, hence at most 262,144 scalar refinement iterations for
64 steps at the maximum setting. There is no adaptive path recursion.

All endpoint/vector/domain/shape constraints and the strict binary64 environment
in [OPTICAL_BOUNDS.md](OPTICAL_BOUNDS.md) and [INTERVAL.md](INTERVAL.md) apply:
finite ray component endpoints within `+-1e6`, index intervals wholly within
`[1e-6,1e6]`, parameter domain within `[0,1e9]`, positive finite point wavelength,
and bounded supported shape parameters. Empty identity itineraries validate
the stored component/domain bounds but do not require a geometry-normalization
certificate; no propagation is performed. Compile the route, bounded optics,
dispersion and interval sources with strict floating point and no contraction.
If a valid hit lies outside the bounded-ray continuation position profile,
the route returns `numerical_failure`; it retains the hit diagnostics and does
not clip, displace or substitute the origin to produce a successful final ray.

## Independent reference cases and evidence

The reference plate has front `z=0`, back `z=1/4`, sensor `z=5/4`, initial
origin `(0,0,-1)`, and sufficiently wide disks.

| Itinerary | Exact physical distance | Exact OPL | Exact or bounded throughput |
|---|---:|---:|---:|
| Normal `T(1.5),T(1),T(1)` from index 1 | `9/4` | `19/8` | `(24/25)^2=576/625` |
| Normal `front T,back R,front R,back T,sensor T` | `11/4` | `25/8` | `(24/25)^2(1/25)^2=576/390625` |
| Incident `(3,0,4)`, index `4 -> 3 -> 4 -> 4` | `35/12` | `45/4` | contains `[331776/390625,1]` for arbitrary polarization |

For the rational oblique case, inside unit direction is `(4/5,0,3/5)`, final
direction `(3/5,0,4/5)`, final `x=11/6`. At each plate face `Rp=0`, `Rs=49/625`;
the pure s and pure p route products are `(576/625)^2` and `1`. These independent
rational results test direction, distance, medium accounting and the arbitrary
polarization envelope, without relying on another floating-point tracer.

`tests/optical_route_tests.cpp` also exercises sphere/cap reflection, full ray
and index families, intact Cauchy/Sellmeier output, TIR branch rejection,
aperture miss/uncertainty, exact and uncertain `t=0`, critical angle, closed
domain boundaries, partial prefixes, budgets, invalid inputs, reuse after
failure and 64 steps. Its `--fixtures` mode emits all route input fields and
segment output boxes as JSON for Native/WASM and independent rational checks.
Build commands and raw evidence are in ignored `build/optical-route-proof/`;
the parent integration records distributable evidence separately.

Standalone verification on 2026-11-03: Native MSVC x64 and the fixed Emscripten
6.0.13 real WebAssembly module each pass **23 groups**. The 15 JSON fixtures have
2,595 numeric values, all equal at binary64 bit level between those runs.
`compare.py` independently checks 67 exact `fractions.Fraction` inclusions for
the rational examples, normal index-family endpoint/interior members and
failure classifications. After the final preflight diagnostic fix, the
standalone WASM is 245,348 bytes. The script is
an independent finite reference check; neither bit agreement nor these finite
samples alone prove whole-family correctness. That rests on the interval
composition argument and the underlying kernels' stated contract.

Reproduce from the repository root with the saved proof commands:

```
cmd /c build\optical-route-proof\build.cmd
build\optical-route-proof\route-tests.exe
build\optical-route-proof\route-tests.exe --fixtures
node build/optical-route-proof/build-wasm.mjs
node build/optical-route-proof/run-wasm.mjs
node build/optical-route-proof/run-wasm.mjs --fixtures
python build/optical-route-proof/compare.py
```

`compare.py` reads the saved `native-fixtures.json` and `wasm-fixtures.json`;
capture the respective `--fixtures` outputs to those names before comparison.
`provenance.json` records source/artifact SHA-256, exact base revision, compiler
versions and flags. This standalone module is a test artifact, not an assertion
that the common engine ABI or browser distribution already exports the route.

## Sources and implementation provenance

The transport wrapper and tests are original project code; no external physics
library or copied source is included. Existing own intersection/interface code
is reused, rather than replaced with a JS approximation.

- [PBRT 4e, Specular Reflection and Transmission](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission): dielectric geometric optics, Fresnel and polarization background. The route envelope proof above is this implementation's conservative composition argument, not a claim that PBRT implements this interval route API.
- [PBRT 4e, Managing Rounding Error](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error): why intersection and continuation error matter. This prescribed-route API deliberately retains the full origin box without PBRT's production ray-origin offset; it consequently exposes source-boundary uncertainty.

These sources were consulted as references; testing validates the listed finite
cases. The enclosure contract depends on the interval construction and build
assumptions, not on sampled rays or the visual appearance of a route.


## Common ABI and final diagnostics

The route is now exposed through `pp_sim_optical_route`, its segment snapshot
getter, and JS `traceOpticalRoute`. This supersedes the standalone-only scope
of the original proof section above. Final source/artifact/proof hashes are in
`reports/route-support-verification.json`.
An invalid scalar field on a later step reports that step's zero-based
`failed_step`, with zero completed prefix because preflight runs before work.
Global input and preflight step-budget failures report index zero.
The regression checks the invalid third index and absence of a final ray.
The committed `scripts/verify-optical-route.py` and the Linux workflow provide
the reproducible rational checks from `--fixtures`; the ignored proof folder
above describes the local standalone build history. Published raw input/results
are in `reports/optical-route-native-fixtures.json`.

The lab joins two curved caps and synthetic Cauchy phase enclosures at a point
wavelength. Sensor-X enclosures at 450nm and 650nm are distinct in this finite
example; this is a bounded ray result, not a calibrated image or lens design.
Displayed interval endpoints retain 17 significant digits for binary64 roundtrip.
