# Full scheduler GNU13 driver — prepared, not executed on Linux

`verify-gnu.py` is a read-only driver for the already built normal main-CMake
configuration. Windows preparation/smoke checks do not establish GNU, sanitizer,
runtime instruction, or public acceptance. The frozen MSVC finite results remain
separate evidence. No production, CMake, workflow, SDK or old verifier is edited
by this recipe.

Configure normal Release GNU13/x86-64/Unix Makefiles with exported compile commands
and build these four targets **before** calling the recipe:

```text
pikapika_world_static_mesh_flight_scheduler_tests
pikapika_world_static_mesh_flight_scheduler_fixtures
pikapika_world_static_mesh_flight_advance_tests
pikapika_world_static_mesh_flight_advance_fixtures
```

```text
python3 reports/world-static-mesh-flight-scheduler-recipes/verify-gnu.py --normal build/ci-world-scheduler --output build/public-checks/scheduler-gnu --sanbuild build/wfs-san --debugbuild build/wfs-debug --parallel 2 --command-timeout 600
```

The driver never configures or builds normal. Output must be a fresh child of
`build/public-checks`; sanitizer and Debug builds are distinct fresh repository
build children, nonoverlapping with normal/output/each other. Reuse, escapes,
parallelism outside1–4 and child timeouts outside30–1200 seconds are refused.
There is no cleanup, network request, Git revision substitution or normal object
replacement. Actual argv, raw stdout/stderr (including failed children), elapsed
time, recipe/source and before/after object/library/exe/map/cache/compile/link
hashes are retained. SDK and available old accepted artifacts are watched too.

## Required actual Linux gates

1. Require actual Linux GNU13 compiler version/target, main Release configuration
   and the original seven-source `world-flight-binding-Release.json`. Validate
   the separate `world-flight-scheduler-binding-Release.json` from the formal
   helper: exact JSON identity material/hash, two original source hashes, helper
   hash, actual compiler/cache flags, explicit upstream seven-source ID, profile1,
   and the actual scheduler TU's macro/ID/strict/Werror command. Never replace it
   with the earlier imported-library prototype ID. Configured identity is not an
   object attestation; `artifactAuditComplete` remains false.
2. Invoke the unchanged current seven-source object/link/compiler-command auditor
   on normal core object, advance executable and `world-flight-advance.map`.
   Preserve its declared incomplete clock/commit/World acceptance scope. Capture
   four actual new/shared TU Werror compilations to independent diagnostic objects:
   scheduler CPP, scheduler test, scheduler full main, shared advance writer.
   Replay their actual compile-database working directory/options/definitions.
   The seven old child writers retain their existing diagnostic policy.
3. Require actual scheduler13 assertion groups and1382 selected observations, then
   run the existing selected integer-credit reference. Separately capture all28
   full frames, including actual43 owned advance attempts/41 actual returned
   guards, and run the frozen full checker plus16self/146negative controls,
   label/order independence and an actual optimized-Python refusal. No fabricated
   intermediate WorldAfter/pointer observation or replacement guard is supplied.
4. Repeat old advance9 groups, clock18 plus integer/Fraction reference, and fresh
   complete old transaction51 plus14self/85negative controls. The selected1382
   observations are a separate limited ledger, not a substitute for full28. No
   additional old guard-only executable is required by this job: the old51
   transaction checker audits each actually returned guard in its own scope.
5. Configure a fresh full Debug main-CMake build with the same GNU compiler. Build
   scheduler/advance tests and require each actual profile0 refusal. Validate both
   generated Debug profiles and actual scheduler compile command. Do not run the
   configured-only full serializer or label this Release-imported Debug.
6. Configure a fresh full Release sanitizer build with
   `CMAKE_CXX_FLAGS=-O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer`,
   `CMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG` and sanitizer linker flags. Main CMake builds
   all four targets and their full dependency chain. Require the exact normal
   core40 and independent scheduler1 source sets separately: the target-aware
   old guard helper checks only `pikapika_core.dir`40; this driver separately
   checks `pikapika_world_static_mesh_flight_scheduler.dir`1 with its actual strict,
   sanitizer/Werror command. Combine41 only for normal artifact protection and
   reporting, never feed unbuilt independent objects to old core-only jobs.
   Require every instrumented object and every one of the19
   target-specific harness/serializer commands (11 distinct source TUs), including
   shared writers in both full targets. Enforce O1/NDEBUG/sanitizers/no LTO for
   every dependency; source2 strict actual command and new/shared Werror remain
   mandatory. No API-only or normal-library link can stand in for this build.
7. Require distinct normal/sanitized seven-source and scheduler IDs. Actually
   repeat scheduler13/selected1382/full28/16self146negative plus old9/clock18/
   transaction51/14self85negative under ASan/UBSan. Full old clock18 compares with
   **no normalization**. Old51 compares through its existing precisely two-path
   helper. Full28 permits only these three identity patterns in private copies:

   - `fixtures[*].report.binding.buildId`: scheduler family,28 leaves.
   - `fixtures[*].report.tickReports[*].report.binding.buildId`: upstream family,
     actual43 nonnull attempt leaves.
   - `fixtures[*].report.tickReports[*].report.guard.binding.buildId`: same
     upstream family, actual41 nonnull guard leaves.

   Validate actual identities before replacing these112 leaves per side. Compare
   every other key/order/array/scalar type/bool/null/string/layout/storage/interval/
   counter/observation and IEEE64 signed-zero bit. No generic text substitution,
   missing-tail allowance, sizeof exception or normalization of source/clock/work
   is permitted. Both selected1382 datasets are independently checked and their
   whole selected trees compare with no normalization (that selected schema has
   no build-ID fields). The full28 gate separately checks the complete reports.

## Scope left open

The finite original full28 corpus exercises24 actual mathematical child calls
(8flight,8metric,8plane-box); it contains no sphere-box child call. Protected
references preserve exact quadratic+B coordinate versus recorded-box downstream
RN/root scopes. Outer pointers and sizeof remain Native observations; no measured
intermediate World snapshots are invented. Unknown/missing results are not made
successful, artificial JSON controls are not C++ allocator/CPU fault injection,
and full clock/commit/scheduler machine/EH/alias proof remains incomplete.
GNU finite/sanitizer output will only be called successful after actual CI runs.
