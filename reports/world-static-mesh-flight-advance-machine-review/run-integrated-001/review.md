# Integrated Release advance: exploratory machine review

The build owner declared `build/wfa2` Release ALL complete before collection.
This review reads its existing artifacts; it does not rebuild or execute them.
The earlier long-path MSBuild failure is separate build history, not a C++
semantic failure and not an input to this machine review.

Six dumpbin commands completed with exit 0. They retain raw symbols,
disassembly, relocations, PE headers and unwind information with command,
stdout/stderr and hash records. `before.json` / `after.json` cover 289 inputs,
including all 149 frozen prototype files and the integrated object/executable,
map, profile and available command tlogs. All were unchanged during collection;
`final-input-check.json` repeats that check after analysis. No old prototype or
previous review evidence was modified.

This is **not formal clock-graph proof or commit compiler attestation**. The
profile's seven requested source identities/flags and actual strict-command
acceptance are the core auditor's separate gate. Its recorded build ID is
`4dc5fea0a751f469137271421800e282b3a257ddf56d6ac6498182bd0bff061f`.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| world_static_mesh_flight_advance.obj | 460299 | bdbfe8611a77fa2ce3661c297af995e4a812363da0aa697a4a1a3a09e3199296 |
| pikapika_world_static_mesh_flight_advance_tests.exe | 1038848 | 6788aa7bf74061a519102413c304af7b6628c773b8ba561924aacaee93a67e1d |
| world-flight-advance.map | 3410847 | 884564d78a93f56b1970b3fd35b79cf499ca42b6b6ed782e512fb8d498e34fbd |
| world-flight-binding-Release.json | 1898 | 6a003adf059dd2abe24178bed5f4d95db78e6a6405351572ad7da004092e82db |

## Object, executable and map correspondence

`byte-map-correlation.json` compares every non-relocation byte of each complete
COFF function section against the executable, then requires the exact decorated
symbol's map address to match that unique executable location. All six selected
functions agree. Relocation bytes are masked and listed explicitly: their
semantics are not certified by this section-byte comparison. Each excerpt
retains the original full dump's line numbers.

| Function | Object bytes | Compared non-relocation bytes | Executable VA | Map line |
| --- | ---: | ---: | --- | ---: |
| advance | 3216 | 3088 | 0x14004D220 | 3126 |
| clock_preflight | 1277 | 1097 | 0x14004E130 | 8640 |
| commit | 327 | 327 | 0x14004E630 | 8641 |
| prepare_commit | 1791 | 1763 | 0x140051140 | 8650 |
| validate_commit | 234 | 230 | 0x140051DF0 | 8658 |
| origin_preflight | 2238 | 2158 | 0x140050880 | 8649 |

Unlike the earlier configured prototype, this image retains the standalone
`commit` section. The integration link options request `/OPT:NOREF /OPT:NOICF`.
That section's presence still does not identify the path used by `advance`:
there is no direct call from the matched `advance` body to standalone `commit`.
The body-copy/Progress-store loop is inlined in `advance` itself.

## Actual clock instructions

In the matched helper, +0x1A loads requested H from report +0x10 into xmm7;
+0x7A reloads original time from report +0x20 into xmm0. The source/field
interpretation is corroborated by the surrounding code, not a completed alias
or field-layout proof.

- +0xC3, VA **0x14004E1F3**: `addsd xmm6,xmm0`, after copying H to xmm6. It is a
  scalar SSE addition in this image, not a fused expression.
- Result finite/cap/progress checks appear before +0xEE, where VA 0x14004E21E
  stores the proposed time into report +0x30. Proposed tick `lea rax,[rbx+1]`
  and store to report +0x38 follow; the optional flag is report +0x40. These are
  report writes, not the caller's Progress assignment.
- +0x10D, VA **0x14004E23D**: `subsd xmm9,[rdi+20h]`, the separate represented
  difference. Point/add/sub/contains and CRT classification calls remain in the
  helper; map labels for observed call targets are retained in `observations.json`.
- The three Interval diagnostics and represented_dt are written to the report
  only after the subsequent validation code. Observing those instructions does
  not prove every input, call edge, exception edge or FP-control state.

The exact machine instructions depend on the active SSE rounding/denormal
control state. The environment/profile preflight and the core auditor's scope
are distinct evidence; a visible `addsd` alone is not nearest-even attestation.
The actual finite clock tests/independent Fraction clock checks were run by the
build owner and are not rerun or substituted by this read-only collection.

## Actual commit store path

The matched `advance` calls clock at +0x787, guard at +0x839, first origin check
at +0x8B1, preparation at +0x8CC, validation at +0x8E4, and second origin check
at +0x912. Proposal/clock engagement and count comparisons precede its success
branch. These visible sites support later control-flow work but do not alone
establish that every failure edge avoids stores.

The local GuardResult temporary destructor call at +0xA05 precedes the inlined
commit block. For each body, the block obtains a prepared destination pointer,
loads 0xE0 bytes from the private body buffer, and writes fourteen 16-byte chunks:

- first body destination store: +0xAA5, **VA 0x14004DCC5**;
- remaining body stores: offsets +0xAA8 through +0xAEC, covering destination
  byte offsets 0x10 through 0xD0;
- loop back edge: +0xAFA to +0xA20; zero body count skips this loop;
- final Progress write: +0xB04, **VA 0x14004DD24**, a 16-byte `movups` from the
  proposed Progress to the original Progress pointer.

There are zero call instructions between the first body store and the Progress
store in this observed block. On the normal epilogue, +0xB1D / VA 0x14004DD3D
calls the map-labelled `__security_check_cookie`, then restores registers and
returns. `observations.json` retains the actual call/map records. The raw unwind
dump is preserved but has not been decoded into a proof of exception dominance.

The standalone `commit` also has fourteen body stores and one Progress store,
with no call instruction. It is supplementary evidence; auditing only that
symbol would miss the inlined path actually visible in `advance`.

## Conditions still needed for formal acceptance

1. Bind all production compile/link/profile inputs to the exact object/map/PE,
   and resolve every relevant relocation/callee. The core auditor's seven-source
   strict-command proof is separate from this new clock/store exploration.
2. Bind clock field layout/constants, active FP controls and their preservation,
   Interval/CRT call behavior, overflow/progress branches and diagnostics. Keep
   requested H distinct from represented clock difference. This review is not a
   complete universal clock operation-graph proof.
3. Construct actual normal and exception control-flow graphs including outlined
   catches, unwind states and destructors. Prove the guard, candidate validation,
   both origin passes and final consistency checks dominate World/Progress
   stores, while all failure exits bypass them.
4. Track all aliases of mutable World bodies, prepared destination pointers and
   Progress through callees. Distinguish local/report writes from simulation
   writes, prove bounds/distinct destinations, and retain the caller's synchronous
   no-concurrent-mutation condition. This collection does not close that graph.
5. Audit all code after the first store, including runtime checks and generated
   helpers in the actual compiler configuration. The no-throw/no-allocation C++
   commit design does not promise CPU-transactional, process-crash or access-fault
   atomicity. Multiple body stores can be partially visible under excluded faults
   or concurrent observation.
6. Keep independent numerical guards, finite commit/clock tests and existing
   leaf artifact proofs separate. Any reused leaf proof needs exact image/call
   correspondence; this review does not broaden its original acceptance scope.

All six requested symbols were found and map-correlated in this image. Complete
call closure, EH/alias/store-dominance proof and compiler attestation remain
explicitly absent. No missing proof is filled from source expectations.
