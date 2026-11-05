# Controlled tick GNU13 acceptance

The main-CMake integration adds one independent library TU and one test driver.
The unchanged core has 40 TUs. The driver links ten test/serializer TUs; its
private `PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY=1` does not change the old51 target.

The CI job builds three bounded targets: controlled tick tests, old advance
tests, and old advance full fixtures. `verify-gnu.py` reads actual compile
commands and link files, audits the old seven-source Vec3 leaves and their
strict-command contract, and recomputes the separate two-source controlled
configuration identity with an explicit upstream ID. That configuration is not
runtime artifact attestation or a proof of the complete controlled caller.

Normal Release must already exist. Fresh, separate Debug and O1 Release
ASan/UBSan builds never reconfigure normal. All 40 core TUs, the independent
controlled TU, and all 19 target-specific harness/serializer commands must be
instrumented for the sanitizer build. Four new/shared TUs also use Werror.
Compiler argument vectors are replayed directly with their original cwd;
`cmake -E chdir` must not reserialize quoted `-D` values.

Normal and instrumented runs each execute 94 directed groups, raw nonfinite
unit observations4, finite full88 (22 committed,29 not certified,37 invalid),
the actual independent checker and 26 self/144 rejection controls. All 64
actual child advances and59 returned guards remain in the full document.
The old9 groups/18 clocks/full51 and14 self/85 controls remain separate.

Same-GNU-ABI normal/instrumented whole documents may differ only in two
declared identity families at four exact paths: outer controlled build ID88,
outer upstream ID88, actual child build ID64, and actual guard build ID59.
All other keys, values, types, array order, signed-zero bits, sizeof/storage,
work and pointer observations must match. There is no cross-ABI layout
normalization or blanket removal of buildId fields. Raw unit4 and old clock18
have no normalization. Raw files and actual failed child diagnostics survive
in the job log receipt; unavailable ephemeral files are not claimed downloaded.

Debug tests explicit profile0 refusal with actual Debug core, not numerical
acceptance. Allocation/nonreturn/post-child fault injection, full clock/commit
machine proof, scheduler packet queues, SDK/WASM and game integration remain
outside this gate. Windows driver controls can check orchestration and copied
comparison rejection only; they never count as actual GNU or sanitizer runs.
