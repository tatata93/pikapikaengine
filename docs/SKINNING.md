# Position skinning kernel

`pikapika::skinning` is an original, pure C++20 positions-only linear blend
skinning (LBS) kernel. It consumes matrices from the existing motion sampler
without changing `motion::Pose`, `core::Transform`, source vertices or author
weights. The Native/standalone WASM kernel is now connected to the common
63-export simulation SDK. A small Canvas XY/XZ operation lab uses actual C++
results. Game-renderer/GPU skinning and persistent binding assets are later work;
local SDK verification is distinguished from final public CI/Pages acceptance.

## Coordinates and formula

The first supported binding uses **mesh-local = skeleton space**, SI metres and
column vectors. `Mat4` is column-major, with translation at elements 12–14.
For stable bone ID `j`, rest-world matrix `R_j`, pose-world matrix `G_j` and
inverse bind `I_j = inverse(R_j)`, the position calculation is

```
B  = sum_j normalizedWeight_j * (G_j * I_j).affine3x4
p' = B * [p,1]
```

An object/world transform belongs after this calculation and must be applied
once by a future scene adapter. No implicit bind-shape transform or coordinate
conversion is applied. Full affine matrices retain shear from a nonuniformly
scaled parent and rotated child; there is no TRS decomposition of `G_j * I_j`.

`BoneMatrix` stores a stable ID and matrix. `bind(rest, settings)` builds
`JointBind {bone_id, rest_world, inverse_bind}` in the original rest order.
`deform(vertices, joints, pose, settings)` accepts explicit inverse binds and
returns positions in source vertex order. Bone, binding and pose order may
differ: lookups use IDs. Their binding/pose ID sets must agree exactly. Vertex
indices are positions in this input span, not newly introduced persistent mesh
vertex IDs. Source wrappers and mesh identity are a later integration layer.

## Domain and budgets

| Item | Contract |
| --- | --- |
| Bone IDs | Unique integers in `1..2^53-1`; binding must be nonempty |
| Matrices | All elements finite, absolute value at most `1e150`; exact final row `[0,0,0,1]` |
| Rest inverse | Constructed inverse must also satisfy that matrix domain |
| Source position | Each component finite and within `[-1e6,1e6]` metres |
| Output position | Finite binary64; source bounds and Float32 representability are not output guarantees |
| Vertex influences | 1–4 distinct known IDs, including IDs with a zero weight |
| Author weights | Finite, nonnegative, at least one positive per vertex |
| `max_bones` | Default/hard maximum 128, setting minimum 1 |
| `max_vertices` | Default/hard maximum 65536, setting minimum 1; actual empty vertex input is valid |
| `max_influences` | Default/hard maximum 262144 total, setting minimum 1 |
| `maximum_condition` | Default `1e10`, setting range `[1,1e12]` |
| `maximum_inverse_residual` | Default `1e-10`, setting range `[1e-15,1e-3]` |

Count admission may reject an oversized span before inspecting its elements.
After admission, all source matrices, IDs, positions and author weights are
validated before inverse-quality work, normalization or deformation begins.
No successful output is returned on failure, including a failure after several
valid bones or vertices. Diagnostic vectors may contain an inspected prefix.
Calls retain no mutable kernel state and can be retried after a failed call.

## Inverse and weight acceptance

The inverse implementation is original scaled 3×3 Gauss–Jordan elimination.
It divides the linear block by its largest absolute entry, chooses a pivot by
the entry/initial-row-maximum ratio, and rejects a pivot score at or below
`64 * binary64 epsilon`. It then divides the inverse block by the original
scale and computes inverse translation. It does not compute a determinant.
This avoids rejecting a well-conditioned `diag(1e-150)` merely because its
determinant would underflow, and also accepts `diag(1e150)`. Conversely, a
translation that requires an inverse entry of `1e300` is outside the explicit
matrix domain and returns `numerical_failure` without a binding.

For each inverse, including imported explicit inverses, acceptance audits

```
condition = normInfinity(R.linear3x3) * normInfinity(I.linear3x3)
residual  = max(normInfinity(R*I - identity), normInfinity(I*R - identity))
```

These are **point binary64 diagnostics**, not certified interval condition or
error bounds. The linear condition avoids mixing metre translation with the
dimensionless 3×3 block. The affine residual uses a declared one-metre reference
for translation, so its numerical threshold audits that component in metres as
well. Both thresholds are inclusive. Passing a chosen residual threshold permits
that finite inverse discrepancy; an imported inverse is never silently rebuilt.
The independent oracle checks inverses against exact rational affine algebra,
rather than taking these self-product residuals as an independent answer.

Each vertex's working influence list is sorted by stable ID. We divide author
weights by their maximum, sum these ratios, then divide by this sum. The author
numbers stay unchanged. Max scaling permits weights near `DBL_MAX` without an
overflowing raw sum. If a positive author weight becomes zero in either division
stage, the result is `numerical_failure`; it is not silently discarded. The
accepted point sum residual is at most `32 * binary64 epsilon`. Zero influences
still require known, nonduplicate IDs. Underflow in subsequent ordinary position
arithmetic is subject to the point-computation limits below.

## Failure and precision limits

The status order is `completed=0`, `invalid_input=1`, `budget_exceeded=2`,
`ill_conditioned=3`, `numerical_failure=4`. Invalid raw domains and settings are
input failures; count quotas are budget failures; singular/scaled-pivot or
condition/residual rejection is `ill_conditioned`. A constructed inverse outside
the supported range, positive weight loss, nonfinite intermediate or failed
post-validation numerical operation is `numerical_failure`. `joints` and
`positions` are optional and present only for `completed`. Diagnostic allocation
failure can escape if even recording the error cannot allocate memory.

Build without fast math or floating-point contraction. The tested configurations
use MSVC `/fp:strict`, or Emscripten `-fno-fast-math -ffp-contract=off`. Binary64
point rounding, underflow and cancellation remain. There is no uniform absolute
or relative error promise for every finite input in this wide domain. The 3×4
palette matrices are blended before transforming each vertex once. This avoids
losing a small vertex offset separately in two huge translated points: equal
influences with identity binds, `p.x=1` and translations `+2^53`/`-2^53` return
the exact result `x=1` in the regression. This operation order does not provide
a general cancellation error bound. A caller needing tight geometric accuracy must
choose a suitably scaled local coordinate representation and audit its results.

LBS itself can collapse, invert or lose volume even with valid affine inputs.
Pose matrices may be singular or reflected; that alone is not rejected for this
position-only calculation. No triangle validity, normal/tangent transformation,
FP32 GPU conversion, rasterization or collision deformation is implemented here.
There is no IK, event/control graph or contact-aware animation in this API.

## Validation and reproduction

`tests/skinning_tests.cpp` runs 68 groups on Native and real standalone WASM.
They include known affine/shear inverses, one/two/four influences, arbitrary
matrix and influence order, weight scaling, positive underflow at both stages,
subnormal single weights, imported residual thresholds, singular/near-dependent
rest matrices, tiny/huge uniform matrices, inverse translation range rejection,
input and count failures, empty vertices, unchanged author input, failed-call
reuse, direct NaN/infinity checks, finite large products, the explicit cancellation
regression and an actual `motion::sample` two-bone deformation with nonuniform scale.

The executable supports `--fixtures` (65 finite, named, complete-input JSON
cases) and `--oracle` (128 complete-input affine/LBS CSV rows). JSON schema 1 uses
`input.operation = bind | deform`, explicit `rest`, `joints`, `pose`, `vertices`
and five settings. Result fields are status, optional joints/positions,
diagnostics and weight residuals. No NaN/Infinity JSON is emitted. CSV columns
are `id`, `r0_0..15`, `r1_0..15`, `g0_0..15`, `g1_0..15`, `px,py,pz,w0,w1`,
`i0_0..15`, `i1_0..15`, `x,y,z`. Every numeric value except the row ID is an exact
binary64 hexadecimal float spelling. Matrices are column-major throughout.

Ignored raw evidence is under `build/skinning-proof/`: Native/WASM test logs,
both fixture files and oracle files, build/run recipes, hashes and provenance.
The same sources produced bit-identical Native/WASM fixture numeric values
(5248) and oracle numeric values (13312), including signed zero: 18560 compared
binary64 values, maximum difference zero. This is observed cross-build parity,
not a promise that every compiler or future optimization is bit-identical.

Native reproduction from the repository root, in a VS x64 developer shell:

```
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include core/src/skinning.cpp core/src/motion.cpp tests/skinning_tests.cpp /Febuild/skinning-proof/skinning-native.exe /Fobuild/skinning-proof/ /link /INCREMENTAL:NO
build\skinning-proof\skinning-native.exe
python build/skinning-proof/capture.py
node build/skinning-proof/build-wasm.mjs
python build/skinning-proof/capture-wasm.py
```

The standalone build reuses the previously fixed Emscripten 6.0.13 toolchain.
It does not install dependencies, replace the public SDK or change the frozen
motion implementation.

`scripts/verify-skinning.py` independently reconstructs each input binary64 as
an exact rational, uses a separately written 4×4 rational inverse, and evaluates
the authored-weight ratio and supplied-inverse LBS formula. It verifies 304
fixture point quantities plus 4480 quantities in the 128-row affine corpus per
runtime (4784 each). The fixed comparison threshold is
`256 * epsilon * max(1, abs(exactReference))`; this is a corpus acceptance rule,
not a domain-wide error theorem. Maximum observed scaled error is
`2.555909121439209e-16`. In the ordinary 128-row corpus the maximum absolute
error is `1.7763568394002505e-15`. The extreme finite product fixture, with
positions around `1e306`, has absolute error `1.0038015193053828e290` despite
scaled error near `1e-16`; a small relative discrepancy is not a small metre
discrepancy. The huge-translation cancellation regression has exact and computed
`x=1`, error zero. It receives the ordinary threshold, with no special exemption.

The checker rejects 26 data/control mutations, including truncated or changed
inputs, invalid schema, signed-zero changes, output corruption, nonfinite JSON
and Python `-O`. It also rejects the obsolete `0.5` cancellation output. Full
acceptance, negative-case logs and checker provenance are retained under
`build/skinning-reference/`, with byte copies in `build/skinning-proof/`.

```
python scripts/verify-skinning.py build/skinning-proof/native.json build/skinning-proof/wasm.json --oracle build/skinning-proof/native-oracle.csv --wasm-oracle build/skinning-proof/wasm-oracle.csv
```

These tests establish this finite point corpus and cross-build observations.
They do not certify all intermediate floating-point error for arbitrary input
matrices or provide bounds on a continuous deforming surface.

## Common simulation SDK and operation lab

The common SDK adds four C exports, `pp_sim_skin_bind`,
`pp_sim_skin_bind_record`, `pp_sim_skin_deform`, and
`pp_sim_skin_deform_record`, while retaining ABI version 1 and output capacity
64. The actual exchange is capped at **128 bones, 2048 vertices and 8192 total
influences per query**. Native Settings still accept maxima 128/65536/262144;
this does not enlarge the exchange or split/truncate a mesh. Lower Settings
budgets remain effective. Header/layout and getter-kind definitions are in
`core/include/pikapika/simulation_api.h`; the completed milestone and next
acceptance are recorded in [SKINNING_SDK_PLAN.md](SKINNING_SDK_PLAN.md).

`SimulationRuntime.bindSkin(rest, settings)` takes `{id,matrix}` records.
`deformSkin({joints,pose,vertices}, settings)` takes explicit
`{id,restWorld,inverseBind}` joints, `{id,matrix}` poses and
`{position,influences:[{id,weight}]}` vertices. Both return copied snapshots:

```
{status, joints, positions, diagnostics, weightResiduals}
```

Status strings match the five kernel statuses. Only a completed bind has a
`joints` array, only a completed deformation has a `positions` array; inactive
or failed fields are null. Diagnostic entries are
`{id,condition:null|number,residual:null|number,pivotFailure:boolean}`.
Author order, weights, matrices and duplicate/missing IDs are passed through;
the JS bridge implements no inverse, LBS or FK alternative. Integer Settings,
exact positive IDs, finiteness, exchange counts and reserved slots are admission
conditions. Bad exchanges/getters retain prior output and records. An admitted
model failure publishes a new no-result record with its diagnostic prefix.
Global reset clears both skin records. Motion, optical records and World clock
remain independent.

[`tools/skinning-lab.html`](../tools/skinning-lab.html) shows the original and
C++-deformed vertices of an authored two-bone strip, nonuniform-scale/shear,
translation cancellation and positive-weight underflow examples. Time/weight
edits clear stale positions; calculation is explicit. JSON export records the
query and diagnostics, not a reloadable skin asset. HTTP/HTTPS is required for
the ESM/WASM operation, while the text and original SVG remain readable through
file URLs. Lines and point projections do not validate normals, triangles,
FP32 conversion, GPU deformation or physical collision/damage.

The final local main module is 583708 bytes, glue 49388 bytes, 63 exports, with
source/artifact/license provenance in `assets/pikapika-simulation.build.json`.
Native integration passes 651 groups/28 CTest targets; all Node tests pass
322/322, skip 0. New skin SDK tests pass 11/11; the related skin/motion/optics/
World selection passes 36/36. The existing regression suite also remains a
separate acceptance from public deployment.

`scripts/verify-skinning-wasm.mjs` replays the 65 finite Native fixtures:
**60 actual C++ model results and five explicitly classified host exchange
rejections**, not 65 accepted model queries. The five are zero/unsafe IDs and
three integer Settings failures. None of these fixtures exceeds the actual SDK
vertex/influence cap. Separate tests exercise the simultaneous 128/2048/8192
boundary and one-over rejection. The 128 oracle rows execute actual bind and
deform calls. Model results, diagnostic optionals, residuals and retry outputs
match 5288 numeric binary64 bit patterns. Saved JSON preserves negative zero,
and a separate full hex tree records every result bit.

The unchanged independent Fraction checker verifies the generated main replay
with the same 304 fixture and 4480 oracle point comparisons per runtime. The
replay's five normalized host-failure rows have no C++ model output and are
identified in its sidecar report. Evidence, complete snapshots, input/output
hashes and commands are retained in ignored `build/skinning-sdk-js/`:

```
node scripts/verify-skinning-wasm.mjs build/skinning-proof/native.json build/skinning-proof/native-oracle.csv build/skinning-sdk-js/report.json build/skinning-sdk-js/outputs.json build/skinning-sdk-js/replay.json build/skinning-sdk-js/replay-oracle.csv
```

Persistent binding JSON/portable codecs, stable scene/mesh fingerprint checking,
Native CLI round trips, mesh topology edits, renderer integration and original
robot sample updates remain subsequent acceptance work.

## Read primary references

The [Khronos glTF 2.0 specification, skins and skinned mesh attributes](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#skins)
was read for the inverse-bind/weighted affine model and coordinate-space
ordering. This milestone implements its own engine contract and does not parse
glTF, adopt its indexed-joint storage or claim format compatibility.
The [LAPACK DGECON purpose documentation](https://netlib.org/lapack/explore-html/d4/daf/group__gecon_ga4f9b830e19e12c7f082ddb497a57af18.html)
was read for the norm-of-matrix times norm-of-inverse condition-number definition.
The implementation does not call or reproduce LAPACK code; its small scaled
elimination, explicit inverse and diagnostics are independently written.
