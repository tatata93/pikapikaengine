# No-history CI MOVHPD command check

The exact planned command ran in fresh short physical export `build/mhp`:

```
python reports/world-static-mesh-flight-guard-recipes/check-movhpd.py --production --output build/ci-movhpd
```

Its PRODUCTION path contained the pinned 51764-byte five-source candidate
`b46e181bfe427bdc85e27c00042ce31a5ce3f4e2ec9c17fd9aeba45a69f658cf`.
The current seven-source production auditor was watched but not replaced.

Seven original files were sufficient: the candidate at PRODUCTION, checker,
patch, operand checker, saved actual failure, historical comparator and pinned
baseline copy. The export initially contained exactly seven files and no `.git`.
GIT_CEILING_DIRECTORIES was the physical parent `build`; inherited explicit Git
directory/worktree/object overrides were removed. Both real-root discovery and
old-commit `git show` actually failed with exit 128 and `not a git repository`.
The production-mode checker itself then succeeded without a history lookup.

All 96 finite checks passed: one replay of the saved eleven-instruction record,
73 operand regressions, two historical rejection observations and 20 new MOVHPD
controls. The two historical controls execute their named historical comparators;
they are not represented as exercising the new candidate. The saved actual
record replay reuses instruction records, not the original object/link graph.
Other lane/operand inputs use explicitly synthetic placeholder instruction bytes.

Reusing the same output directory actually failed with FileExistsError. Every
byte of the complete successful/export tree was unchanged by that attempt.
Appending an explicit synthetic marker to the exported baseline alone caused a
fresh production invocation to fail with `Pinned five-source Git auditor
identity`; the previous successful output stayed unchanged. The export baseline
was restored, and all seven exported inputs again matched their originals.
This is an artificial copy-corruption control, not a Native/CPU fault injection.

All five subprocess attempts have exact argv/cwd/environment, exit, raw stdout
and stderr records. The successful tree and later rejection output, restored
inputs and derived candidate are archived as 127 flat data files with the exact
original export-relative mapping in `flat-copy-map.json`. `source-before.json`
and `source-after.json` agree for all 159 watched original/evidence paths,
including the frozen 149-file prototype record and this new recipe.

No compiler, binary execution, full object/link audit, complete GNU release
acceptance, clock graph proof or commit attestation occurred in this check.
