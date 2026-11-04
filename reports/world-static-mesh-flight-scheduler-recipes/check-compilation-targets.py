"""Synthetic compilation-database target-scope controls; no compiler is run.

Uses both saved historical and actual current driver functions. Paths are native
host paths, with Unix Makefiles command/arguments shapes, not a GNU execution.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "reports/world-static-mesh-flight-guard-recipes/verify-gnu.py"
DEFAULT_BASELINE = ROOT / "reports/world-static-mesh-flight-scheduler-compilation-checks/before-001/verify-gnu-before.py"


def need(value, message):
    if not value:
        raise ValueError(message)


def stamp(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def split_function(raw):
    text = raw.decode("utf-8")
    nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "compilation"]
    need(len(nodes) == 1, "Exactly one compilation definition")
    node = nodes[0]
    lines = text.splitlines(keepends=True)
    return "".join(lines[:node.lineno - 1]), "".join(lines[node.lineno - 1:node.end_lineno]), "".join(lines[node.end_lineno:])


def module(raw, filename, root):
    result = types.ModuleType("isolated_compdb_driver")
    result.__file__ = str(filename)
    exec(compile(raw, str(filename), "exec"), result.__dict__)
    result.ROOT = root
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    need(ROOT in out.parents, "Fresh output must stay inside repository")
    out.mkdir(parents=True, exist_ok=False)
    before = {"driver": stamp(DRIVER), "baseline": stamp(args.baseline), "recipe": stamp(Path(__file__))}
    write(out / "invocation.json", {"argv": sys.argv, "cwd": str(Path.cwd()), "python": sys.version, "platform": sys.platform})
    old_raw, new_raw = args.baseline.read_bytes(), DRIVER.read_bytes()
    old_parts, new_parts = split_function(old_raw), split_function(new_raw)
    need(old_parts[0] == new_parts[0] and old_parts[2] == new_parts[2], "Only compilation function may change, including outside-function newlines")
    (out / "verify-gnu-before.py.txt").write_bytes(old_raw)
    (out / "verify-gnu-after.py.txt").write_bytes(new_raw)
    patch = "".join(difflib.unified_diff(old_raw.decode().splitlines(keepends=True), new_raw.decode().splitlines(keepends=True), fromfile="verify-gnu-before.py", tofile="verify-gnu.py"))
    (out / "compilation.patch").write_text(patch, encoding="utf-8", newline="")
    repo = out / "synthetic-repository"
    build = repo / "build with space"
    build.mkdir(parents=True)
    old, current = module(old_raw, args.baseline, repo), module(new_raw, DRIVER, repo)
    other = "pikapika_world_static_mesh_flight_scheduler"
    results = []

    def entry(name, target="pikapika_core", *, command=False, source=None, output=None):
        source = source if source is not None else "../core/src/" + name + ".cpp"
        output = output if output is not None else "CMakeFiles/" + target + ".dir/core/src/" + name + ".cpp.o"
        argv = ["/usr/bin/c++", "-DPIKAPIKA_TEST=1", "-I" + (repo / "include path").as_posix(), "-O3", "-DNDEBUG", "-o", output, "-c", source]
        value = {"directory": str(build), "file": source}
        if command:
            value["command"] = shlex.join(argv)
        else:
            value["arguments"] = argv
        return value

    def case(name, entries, *, target=None, expected=None, error=None, legacy=False, validate=None):
        write(out / (name + ".json"), entries)
        (build / "compile_commands.json").write_text(json.dumps(entries), encoding="utf-8")
        driver = old if legacy else current
        try:
            observed = driver.compilation(build) if target is None else driver.compilation(build, target)
        except (ValueError, KeyError, TypeError) as failure:
            need(error is not None and error in str(failure), name + " unexpected rejection: " + repr(failure))
            results.append({"name": name, "status": "PASS", "rejected": True, "error": str(failure), "legacy": legacy})
            return
        need(error is None, name + " unexpectedly accepted")
        need(len(observed) == expected, name + " source count")
        if validate:
            validate(observed)
        results.append({"name": name, "status": "PASS", "rejected": False, "sources": len(observed), "objects": [str(v["object"]) for v in observed.values()], "legacy": legacy})

    core = [entry("unit%02d" % i, command=i % 2 == 0) for i in range(40)]
    scheduler = entry("world_static_mesh_flight_scheduler", other, command=True)
    combined = core + [scheduler]
    case("old-extra-source-reproduction", combined, expected=41, legacy=True)
    case("default-core-40", combined, expected=40,
         validate=lambda rows: need(all("pikapika_core.dir" in v["object"].parts for v in rows.values()), "Default target object namespace"))
    case("explicit-core-40", combined, target="pikapika_core", expected=40)
    case("independent-scheduler-1", combined, target=other, expected=1)
    duplicate_other = entry("unit00", other)
    case("old-cross-target-duplicate-reproduction", [core[0], duplicate_other], legacy=True, error="Duplicate core source")
    case("cross-target-duplicate-after", [duplicate_other, core[0]], expected=1)
    case("same-target-duplicate", [core[0], core[0]], error="Duplicate core source")
    case("absent-target", core, target=other, error="Nonempty library")
    case("empty-database", [], error="Nonempty library")
    case("source-outside-core", [entry("outside", source="../tests/outside.cpp"), core[0]], expected=1)
    case("source-sibling-prefix", [entry("outside", source="../core/src-extra/outside.cpp")], error="Nonempty library")
    case("source-parent-escape", [entry("outside", source="../core/src/../../outside.cpp")], error="Nonempty library")
    case("relative-command-shape", [entry("relative", command=True)], expected=1)
    absolute = entry("absolute", source=str(repo / "core/src/absolute.cpp"), output=str(build / "CMakeFiles/pikapika_core.dir/absolute.o"))
    case("absolute-paths", [absolute], expected=1)
    relative_directory = entry("relative-directory")
    relative_directory["directory"] = os.path.relpath(build, Path.cwd())
    case("relative-directory", [relative_directory], expected=1)
    case("object-normalized-within-target", [entry("normalized", output="CMakeFiles/pikapika_core.dir/sub/../normalized.o")], expected=1)
    for name, output in [
        ("escaped-object", "CMakeFiles/pikapika_core.dir/../../outside.o"),
        ("object-target-prefix", "CMakeFiles/pikapika_core.dir-other/x.o"),
        ("object-is-target-directory", "CMakeFiles/pikapika_core.dir"),
        ("object-parent", "CMakeFiles/x.o"),
        ("outside-absolute-object", str(out / "outside.o")),
    ]:
        row = entry(name, output=output)
        case(name + "-empty", [row], error="Nonempty library")
        case(name + "-ignored-with-valid", [row, core[0]], expected=1)
    for suffix, argv in [("missing", ["/usr/bin/c++", "-c", "x.cpp"]), ("trailing", ["/usr/bin/c++", "-o"])]:
        row = entry("bad-output")
        row["arguments"] = argv
        case("output-" + suffix, [row], error="Object output argument")
    row = entry("outside-no-argv", source="../tests/outside.cpp")
    del row["arguments"]
    case("outside-source-not-parsed", [row, core[0]], expected=1)
    row = entry("malformed-argv")
    row["arguments"] = ["c++", 1]
    case("argv-nonstring", [row], error="Compile argv")
    for i, target in enumerate(["", ".", "..", "../x", "x/y", "x\\y", "/absolute", "C:escape", "has space", "has\nnewline", None, 1, [], {}]):
        # None normally selects default in the case helper; direct call is needed.
        try:
            current.compilation(build, target)
        except ValueError as failure:
            need("Compile target component" in str(failure), "Invalid target diagnostic")
            results.append({"name": "invalid-target-%02d" % i, "status": "PASS", "rejected": True, "target": target, "error": str(failure)})
        else:
            raise ValueError("Invalid target accepted: " + repr(target))
    after = {"driver": stamp(DRIVER), "baseline": stamp(args.baseline), "recipe": stamp(Path(__file__))}
    need(before == after, "Actual source bytes stable during synthetic controls")
    extra_object = build / ("CMakeFiles/" + other + ".dir/core/src/world_static_mesh_flight_scheduler.cpp.o")
    need(not extra_object.exists(), "Synthetic unbuilt extra object remains absent")
    write(out / "result.json", {
        "schema": 1, "status": "PASS", "signature": "compilation(build, target='pikapika_core')",
        "tests": len(results), "acceptedControls": sum(not r["rejected"] for r in results),
        "rejectedControls": sum(r["rejected"] for r in results), "results": results,
        "oldSelectedSources": 41, "currentCoreSources": 40, "independentSchedulerSources": 1,
        "extraObjectExists": extra_object.is_file(),
        "sourceBefore": before, "sourceAfter": after, "onlyCompilationFunctionChanged": True,
        "compilerInvocations": 0, "nativeExecutions": 0, "actualGnuBuildVerified": False,
        "scope": "Synthetic metadata unit controls using actual imported driver functions; host-native path resolution and Unix Makefiles argv/command syntax. No compiler, linker, sanitizer or Native/GNU job is executed. The historical parser selects 41 synthetic core/src entries; the target-scoped default selects 40 and the independent scheduler target one. Escaped/nonmatching object paths are excluded before duplicate detection; empty selected sets and missing -o reject."
    })
    print(json.dumps({"status": "PASS", "tests": len(results), "old": 41, "core": 40, "scheduler": 1, "output": str(out)}))


if __name__ == "__main__":
    main()
