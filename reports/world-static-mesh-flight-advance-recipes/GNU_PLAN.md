# Native advance GNU13 CI driver: prepared, Linux execution pending

This is the plan for `verify-gnu.py` in this directory. It does not modify CMake,
the workflow, production kernels, SDK artifacts, the current artifact auditor,
or prior receipts. It is a proposed later workflow gate, not a GNU success record.
The existing local MSVC result is separate evidence.

Example future invocation, after a real all-target Release build:

```text
python3 reports/world-static-mesh-flight-advance-recipes/verify-gnu.py --normal build/ci --output build/ci/advance-gnu-verification --sanbuild build/wfa-san --debugbuild build/wfa-debug --parallel 2 --command-timeout 600
```

The normal directory must already be a Release Unix Makefiles build with exported
compile commands, both advance/guard executables and their linker maps. The driver
does not configure or build this normal directory. It checks the complete normal
core object set, library, two binaries/maps, cache, profile and link/compile records
before and after the subsequent work. Sources, available old accepted Native
artifacts and SDK bytes are also protected. Output must be fresh. Separate Debug
and sanitizer directories must be fresh and must not overlap normal or output.
Every path must resolve into a repository `build` child; repository/build roots,
aliases and escaping paths are refused. No recursive cleanup or network step exists.

## Gates to be executed on Linux

1. Require actual Linux, GNU13, x86-64, Release/profile1, and the explicit
   `world-static-mesh-flight-advance-v1` discriminator with exactly seven current
   source/header hashes. Missing/old/unknown source sets have no fallback. The
   current real auditor checks profile flags. Actual compiler version/target
   commands are also retained; the profile alone is insufficient evidence.
2. Run the actual current object/linked audit on the normal core object, advance
   executable and map. Preserve the existing Vec3 leaf/caller and actual compiler
   command scope. Verify `advanceScope` still says clock instructions, commit
   path and complete World advance acceptance are false. No compiler identity
   flag or runtime `ready` result turns that into a full proof.
3. Compile the new advance TU and its self-contained test separately with GNU13
   C++20, strict FP/no contraction/no LTO and `-Wall -Wextra -Wpedantic -Werror`.
   These warning objects are diagnostics and are not substituted for the normal
   linked object used by the artifact gate.
4. Execute actual `--run` (nine internal directed assertion groups), then
   `--clock-fixtures` (18 cases). Run the unchanged independent integer clock
   reference on these actual fixture bytes. These are fresh GNU measurements;
   MSVC or earlier isolated prototype outputs cannot supply missing results.
5. Produce the normal guard51 corpus and run its independent Fraction checker
   and controls. This is dependency mathematics for the owned guard calls, not
   a full serialization of the new advance API.
6. Configure a separate Debug tree with the same actual compiler; build both
   harnesses and execute their `--unsupported-profile` modes. Require the actual
   profile0 refusal, without a caller boolean or runtime unlock.
7. Configure a separate Release tree with O1, `-g`, ASan/UBSan, nonrecovering UB
   and frame pointers, replacing Release optimization flags with `-O1 -DNDEBUG`.
   Build the complete core library and both harnesses. Check actual compile DB
   and object hashes: every normal core TU must be present and instrumented, and
   all nine distinct linked harness/fixture TUs must also be instrumented at O1.
   This is full dependency instrumentation, not API-only instrumentation.
8. Require a distinct seven-source sanitizer configuration identity. Execute the
   same nine assertion groups and 18 clock fixtures under sanitizers, and run the
   independent clock reference. Compare nine-group stdout raw and complete clock
   JSON key order, scalar types, array order and binary64 signed-zero bits, with
   **no normalization**. Repeat guard51 and its independent Fraction/negative
   controls; compare the full normal/sanitized guard JSON allowing only each outer
   `fixtures[*].result.binding.buildId` to differ.

The unchanged guard recipe supplies `Commands`, strict JSON loading, compile DB
inspection, exact tree and guard fixture comparison. In this GNU driver, its
normal/sanitized terms really mean normal versus instrumented configurations.
This differs from the earlier same-MSVC old-five/new-seven regression wrapper.
Failure stdout and stderr are printed into the CI log in full by `Commands`, as
well as saved raw with argv, exit and timing, so a hash-only failure is not enough.
All commands have bounded timeouts (default 600 seconds, configurable 30–1200),
parallelism is bounded to 1–4, and directory reuse is refused. Overall CI duration
and resource use have not been measured; a workflow timeout must be chosen from
actual runs. No fit-to-existing-job-time claim is made.

## Scope that remains incomplete

The prototype plan's minimum finite acceptance proposed saving complete World
and Progress before/after, the complete owned guard, candidates, failed-path
diagnostics and ownership relations as fixtures. The present harness does **not**
provide that complete serializer. Its nine directed groups check these properties
internally; the separately emitted 18-case JSON covers empty-World clock
transitions only. Comparing that clock JSON does not reconstruct missing body,
guard, pointer/alias or commit transcripts. A later complete advance acceptance
must close this explicit fixture/independent-reference gap rather than label the
nine/18 subset as the full proposed corpus.

ASan/UBSan gives numerical and memory-development evidence for instrumented code.
It does not establish normal-artifact binding; the driver deliberately does not
run the normal machine graph audit on the instrumented binary or infer that proof
from its configured profile1. Full clock graph, EH/no-throw commit boundary,
alias/store proof, all targets/compiler attestation and natural allocation or
nonreturn fault injection remain unproved. World response/TOI/FixedClock, new
SDK/browser APIs and public acceptance are outside this driver. Existing 47CTest
and 684Node runs are not repeated here.

## Local preparation evidence

On Windows, only syntax, `--help`, output-boundary/freshness refusals and actual
non-Linux refusal may be exercised. Such an expected-refusal receipt must retain
`actualGNUExecuted:false` and must not become a Linux PASS receipt. No Linux
compiler, Debug target, sanitizer build, numerical fixture or artifact audit has
been executed by authoring this driver. Fresh local smoke output is separate from
all accepted receipts. Internal sources read: the current guard GNU driver and
artifact auditor, advance test harness, clock reference, and applied seven-source
CMake binding. No external source, dependency, material or license was added.
