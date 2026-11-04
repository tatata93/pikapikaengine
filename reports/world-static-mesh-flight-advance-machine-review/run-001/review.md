# configured-001 advance: exploratory machine review

This is a read-only examination of the existing isolated MSVC19.51 x64
configured prototype. It does not extend the accepted guard leaf audit, accept
this new executable, prove the complete clock graph, or integrate advance.
No source, object, library or executable was rebuilt or executed for this review.

`collection.json` records five successful dumpbin commands and unchanged input
hashes. `before.json` / `after.json` include the configured collection's original
source/accepted-artifact inventory, the advance object, prototype library and
executable. `final-input-check.json` checks that inventory again after analysis.
The exact command lines, stdout, stderr and exit codes are retained. Initial
path discovery over the broad build tree encountered old inaccessible private
directories; subsequent collection used only explicit configured-001 paths.

The examined executable is 359936 bytes, SHA256
`da26f0a804561b44cba95446b38ea325598aeb2600279c356a99ebbf0021d5e2`.
Its experimental source identity is
`f9444505eb353f9864773d49bf99d0bda04125d12424ebc8675295fa035f9f3b`.
That identity is not an actual-instruction audit result. The retained compiler
commands use `/O2 /Ob2 /fp:strict /GL-`; the link command uses `/LTCG:OFF`.

## What remains visible

The raw COFF symbols retain `advance`, `clock_preflight`, `commit`,
`prepare_commit`, `validate_commit` and `origin_preflight`. `byte-correlation.json`
matches every non-relocation byte of each relevant function section against the
PE executable. Relocation bytes are masked, not semantically certified. Each of
the five functions other than `commit` has one executable match. Exact PE virtual
addresses below are specific to this unchanged executable.

| Function | Object section | Executable VA | Observation |
| --- | --- | --- | --- |
| advance | 0x2DC | 0x140023B20 | Calls clock helper and contains the inlined commit stores |
| clock_preflight | 0x2EB | 0x140024920 | Scalar SSE addition and subtraction remain separate |
| prepare_commit | 0x31B | 0x1400275B0 | Separate function survives |
| validate_commit | 0x330 | 0x140028000 | Separate function survives |
| origin_preflight | See correlation JSON | 0x140026CF0 | Separate function survives; advance calls it twice |
| commit | 0x2EC | No section-byte match | Object body exists; no corresponding standalone section was located in the executable |

The last row is a real limitation, not an absent-store claim. Advance already
contains an inlined copy loop. Searching for a `commit` call would miss the
executed store boundary. No symbol information from a new map/PDB was generated.

`clock_preflight-object-excerpt.txt` retains original dumpbin line numbers;
the corresponding executable excerpt contains resolved instruction addresses:

- helper +0xC3 / VA 0x1400249E3: `addsd xmm6,xmm0`, after loading the requested H
  and original time. This is the represented `t+H` operation in the examined
  scalar path; it has not been replaced by a fused multiply-add.
- helper +0xD8 and +0xE3 compare the result against the time cap and original
  time; +0xEE stores proposed time into the report, followed by proposed ticks
  and the optional engagement flag. These are report writes, not Progress.
- helper +0x10D / VA 0x140024A2D: `subsd xmm9,[rdi+20h]` computes the represented
  difference separately. The report's +0x20 field is original time, corroborated
  by source and the surrounding loads. Full machine field-layout binding remains
  a later gate.
- separate calls construct Interval points, add, subtract twice, check finite
  endpoints and call `contains`. Their call targets/implementations and CRT
  `_dclass` are not closed by this review. Observing `addsd` alone does not prove
  nearest-even control state, subnormal behavior, or the Interval diagnostics.

In `advance`, the matched object/executable byte sequences show clock call
+0x787, guard call +0x839, first origin check +0x8B1, preparation +0x8CC,
validation +0x8E4, and second origin check +0x912. Later comparisons test
proposal/clock engagement and the preparation work counts before the success
branch. A local temporary GuardResult destructor call appears at +0xA05,
before the inlined destination copies.

## Observed store boundary

The advance body copies each 0xE0-byte RigidBody using fourteen 16-byte `movups`
loads/stores. Destination pointers come from the prepared local pointer array.
The first body destination write is advance +0xAA5 / VA 0x1400245C5;
subsequent stores cover offsets 0x10 through 0xD0. The loop advances and branches
back at +0xAFA. With zero candidates the body loop is skipped.

After that loop, +0xB00 loads the 16-byte proposed Progress from the report and
+0xB04 / VA 0x140024624 writes it through the original Progress pointer. There
is no call instruction between the first body destination store and this
Progress store in the observed block. The epilogue subsequently calls
`__security_check_cookie` at +0xB1D. Neither multiple 16-byte body writes nor this
Progress write establish CPU-transactional or crash atomicity. Hardware faults,
corrupt stacks, concurrent mutation and asynchronous observers are not proved
safe by the no-throw C++ commit design.

The standalone object `commit` has a similar copy loop, but is not the matched
executed implementation. Its nonappearance in the PE byte search is recorded;
the likely dead-section/inlining explanation is not used as an acceptance gate.

## Minimum conditions for a later formal artifact audit

1. Bind exact production source, compiler commands, profile identity, object,
   library selection, link options and executable hashes. Regenerate the audit
   for every different image; this configured prototype cannot authorize a later
   CMake/CI image. Retain symbol/map or equivalent byte/range mapping even when
   helpers inline or COMDAT folding removes standalone bodies.
2. Resolve clock operands, field offsets, constant bit patterns, each relevant
   branch/target and the Interval/CRT call closure. Check the runtime rounding and
   denormal control preflight and preservation over all intervening calls. Match
   `t+H`, `next-t`, ticks and the three diagnostic expressions individually;
   finite fixtures remain an independent check, not a universal graph proof.
3. Build normal and exception control-flow graphs from the actual image and EH
   tables. Establish that clock/preparation/validation/origin-check failures
   cannot reach World/Progress stores, and that successful guard evidence and
   both origin passes dominate them. Merely observing source try/catch boundaries
   or one straight-line success path is insufficient.
4. Track aliases of World bodies, destination pointers and Progress through all
   callees, not just the named commit helper. Bind the full body layout, candidate
   count/capacity bound, distinct resolved destinations, prepared load clearing
   and last Progress copy. Classify report/stack writes separately from mutable
   simulation state. Explicitly retain the synchronous, no-concurrent-mutation
   caller condition.
5. Audit the entire post-first-store region, including epilogue/destructors and
   possible helper replacements (`memcpy`, runtime checks or compiler-generated
   calls in another build). State the actual C++ exception/no-allocation scope;
   do not promise rollback on hardware/access faults or process termination.
6. Keep the existing mathematical guard proof, requested-H vs represented clock
   distinction, finite commit/clock tests and independent Fraction clock checks
   as separate gates. Reuse of an old leaf audit needs its own exact image/target
   correspondence; no such reuse is certified here.

No missing symbol or unresolved relocation is filled from source expectations.
This collection found useful concrete audit anchors and the important inlined
commit case. Complete branch, alias, EH and dependency closure is still absent.
