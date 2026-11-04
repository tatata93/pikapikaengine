"""Read-only feature/evidence inventory; never stages, commits, pushes or deletes.

Default mode prints/writes an inventory only. --emit-manifest is a separate,
explicit operator action after the parent authorizes final publication prep.
It emits fresh JSON and NUL pathspec data, not a Git mutation. Identical raw
files are reported as duplicates but are NEVER deduplicated or omitted.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "reports/world-static-mesh-flight-guard-baseline.json"
PREFIX = "world-static-mesh-flight-guard-"
SOURCE_PATHS = {
    "core/include/pikapika/world_static_mesh_flight_guard.hpp",
    "core/src/world_static_mesh_flight_guard.cpp",
    "tests/world_static_mesh_flight_guard_tests.cpp",
    "tests/world_static_mesh_flight_guard_fixtures.cpp",
    "tests/world_static_mesh_flight_guard_test_support.hpp",
    "scripts/verify-world-static-mesh-flight-guard.py",
    "tests/world_static_mesh_flight_guard_reference_tests.py",
    "cmake/WorldFlightBinding.cmake",
}
DOC_PATHS = {
    "docs/WORLD_STATIC_MESH_FLIGHT_GUARD.md",
    "docs/WORLD_STATIC_MESH_FLIGHT_NATIVE_CONTRACT.md",
    "docs/WORLD_STATIC_MESH_FLIGHT_PLAN.md",
    "docs/WORLD_PREDICATE_FLOATING_POINT_AUDIT.md",
    "docs/learn/diagrams/world-static-mesh-flight-guard.svg",
    "docs/learn/index.html", "docs/RESEARCH.md", "docs/PLAN.md",
    "docs/legal/ASSETS.md", "docs/legal/REFERENCES.md",
    "reports/2026-11-05-world-static-mesh-flight-guard.md",
}
COMPILED_SUFFIXES = {".exe", ".obj", ".o", ".a", ".lib", ".dll", ".so", ".dylib",
                     ".pdb", ".ilk", ".exp", ".pyc", ".pyo", ".class", ".wasm"}
SKIP_PARTS = {"__pycache__", ".git", ".aws", ".codex", "node_modules", ".venv", "venv"}
SECRET_NAMES = {".env", ".npmrc", ".pypirc", "credentials", "credentials.json", "secrets.json",
                "id_rsa", "id_ed25519", "authorized_keys"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore"}
SECRET_PATTERNS = [re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
                   re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
                   re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
                   re.compile(rb"\bAKIA[0-9A-Z]{16}\b")]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def info(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write("\n")


def git(*args, raw=None):
    command = ["git", *args]
    done = subprocess.run(command, cwd=ROOT, input=raw, capture_output=True)
    need(done.returncode == 0, "Read-only git command failed: " + repr(command) + ": " + done.stderr.decode(errors="replace"))
    return done.stdout


def statuses():
    raw = git("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=no")
    records, out, i = raw.split(b"\0"), {}, 0
    while i < len(records):
        item = records[i]
        i += 1
        if not item:
            continue
        text = item.decode("utf-8")
        need(len(text) >= 4 and text[2] == " ", "Git status record shape")
        status, path = text[:2], text[3:]
        need(path not in out, "Duplicate Git status path")
        out[path] = status
        if "R" in status or "C" in status:
            need(i < len(records), "Git rename/copy source missing")
            out[records[i].decode("utf-8")] = "rename/copy source"
            i += 1
    return out


def ignored(paths):
    if not paths:
        return set()
    done = subprocess.run(["git", "check-ignore", "--stdin", "-z"], cwd=ROOT,
                          input=b"\0".join(p.encode("utf-8") for p in paths) + b"\0", capture_output=True)
    need(done.returncode in (0, 1), "Read-only check-ignore failed")
    return {p.decode("utf-8") for p in done.stdout.split(b"\0") if p}


def is_inside(path, directory):
    return path == directory or directory in path.parents


def classify(path, literal_sources, generated):
    if path in literal_sources:
        return "source-or-integration"
    if path in generated:
        return "generated-html"
    if path in DOC_PATHS:
        return "documentation"
    return "World-stage-original-evidence"


def available(baseline, output):
    literal_sources = SOURCE_PATHS | set(baseline["permittedOldSources"])
    planned = literal_sources | DOC_PATHS | set(baseline["generatedEntries"])
    paths = {ROOT / p for p in planned if (ROOT / p).is_file()}
    reports = ROOT / "reports"
    for path in reports.iterdir():
        if path.name.startswith(PREFIX):
            if path.is_file():
                paths.add(path)
            elif path.is_dir():
                paths.update(p for p in path.rglob("*") if p.is_file())
    # Manifest outputs cannot recursively include/hash themselves. Older
    # inventory attempts remain ordinary evidence in subsequent inventories.
    paths = {p for p in paths if (output is None or not is_inside(p.resolve(), output))
             and not any(part.lower() in SKIP_PARTS for part in p.relative_to(ROOT).parts)}
    return sorted(paths, key=lambda p: p.relative_to(ROOT).as_posix()), planned, literal_sources


def exclusion(path, relative, raw, old_allowed):
    if any(part.lower() in SKIP_PARTS for part in path.relative_to(ROOT).parts):
        return "cache/VCS/environment directory"
    if not is_inside(path.resolve(), ROOT):
        return "symlink/junction outside workspace"
    name = path.name.lower()
    if name in SECRET_NAMES or name.startswith(".env.") or path.suffix.lower() in SECRET_SUFFIXES:
        return "credential/key filename"
    # The intentionally distributed SDK WASM is authorized and is not an
    # accidental native proof executable. All report-prefix code is excluded.
    if relative == "assets/pikapika-simulation.wasm" and relative in old_allowed:
        return None
    if path.suffix.lower() in COMPILED_SUFFIXES:
        return "compiled artifact suffix"
    if raw.startswith((b"MZ", b"\x7fELF", b"\0asm", b"!<arch>\n")):
        return "compiled artifact magic"
    if any(pattern.search(raw) for pattern in SECRET_PATTERNS):
        return "high-confidence credential/private-key content; manual review required"
    return None


def failures(entries):
    records = []
    for item in entries:
        path = item["path"]
        if not path.endswith(".json") or item["bytes"] > 2 * 1024 * 1024:
            continue
        name = Path(path).name.lower()
        if not any(token in name for token in ("command", "audit", "report", "capture", "provenance", "acceptance", "verification", "failure")):
            continue
        try:
            data = json.loads((ROOT / path).read_text(encoding="utf-8"))
        except (ValueError, UnicodeError):
            continue
        if isinstance(data, dict):
            exit_code = next((data[k] for k in ("exitCode", "returncode", "returnCode") if k in data), 0)
            if data.get("status") in ("FAIL", "FAILED") or (exit_code is not None and exit_code != 0) or ("exitCode" in data and exit_code is None):
                records.append({"path": path, "status": data.get("status"), "exitCode": exit_code,
                                "error": data.get("error", data.get("exception")), "sha256": item["sha256"]})
    return {"scope": "Metadata index only; all selected evidence retained regardless of status. Not a deduplicated count of logical product failures or all nested command attempts.",
            "topLevelFailureRecordFiles": records}


def inventory(baseline, output):
    changed = statuses()
    paths, planned, literal_sources = available(baseline, output)
    included, excluded, unchanged = [], [], []
    allowed = set(baseline["permittedOldSources"])
    protected_changes, protected_ok = [], []
    for relative, expected in baseline["protected"].items():
        path = ROOT / relative
        need(is_inside(path.resolve(), ROOT), "Protected path escapes workspace")
        actual = info(path.read_bytes()) if path.is_file() else None
        if actual == expected:
            protected_ok.append(relative)
        else:
            protected_changes.append({"path": relative, "declaredOldException": relative in allowed,
                                      "before": expected, "current": actual})
    unexpected = [x for x in protected_changes if not x["declaredOldException"]]
    need(len(baseline["protected"]) == 383 and len(allowed) == 8, "Exact current baseline 383/8")
    need(not unexpected, "Protected source changes outside declared old exceptions: " + repr(unexpected))
    all_relatives = [path.relative_to(ROOT).as_posix() for path in paths]
    ignores = ignored(all_relatives)
    for path, relative in zip(paths, all_relatives):
        need(is_inside(path.resolve(), ROOT), "Candidate symlink/junction escapes workspace: " + relative)
        raw = path.read_bytes()
        record = {"path": relative, **info(raw), "gitStatus": changed.get(relative),
                  "ignored": relative in ignores,
                  "category": classify(relative, literal_sources, baseline["generatedEntries"])}
        reason = exclusion(path, relative, raw, allowed)
        if reason:
            excluded.append({**record, "reason": reason})
        elif relative in changed or relative in ignores:
            included.append(record)
        else:
            unchanged.append(record)
    sha_groups = defaultdict(list)
    for item in included:
        sha_groups[item["sha256"]].append(item)
    duplicate_groups = [{"sha256": key, "bytesPerFile": items[0]["bytes"], "copies": len(items),
                         "duplicateBytesBeyondFirst": (len(items) - 1) * items[0]["bytes"],
                         "paths": [x["path"] for x in items]}
                        for key, items in sorted(sha_groups.items()) if len(items) > 1]
    missing = sorted(p for p in planned if not (ROOT / p).is_file())
    selected = {x["path"] for x in included}
    undeclared = {p: status for p, status in changed.items()
                  if p not in selected and p not in {x["path"] for x in excluded}
                  and p not in planned and not p.startswith("reports/" + PREFIX)}
    largest = sorted(included, key=lambda x: (-x["bytes"], x["path"]))[:20]
    for item in included + unchanged + excluded:
        need(info((ROOT / item["path"]).read_bytes()) == {k: item[k] for k in ("bytes", "sha256")}, "File changed during inventory: " + item["path"])
    after_paths, _, _ = available(baseline, output)
    need(paths == after_paths, "Evidence file set changed during inventory; added=" +
         repr([p.relative_to(ROOT).as_posix() for p in after_paths if p not in paths]) +
         "; removed=" + repr([p.relative_to(ROOT).as_posix() for p in paths if p not in after_paths]))
    return {"schema": 1, "status": "INVENTORY_ONLY", "baseline": info(BASELINE.read_bytes()),
            "baseCommit": baseline["baseCommit"], "head": git("rev-parse", "HEAD").decode().strip(),
            "protected": {"count": 383, "unchanged": len(protected_ok), "declaredOldPaths": sorted(allowed),
                          "permittedChanged": protected_changes, "unexpectedChanged": unexpected},
            "candidateFiles": len(included), "candidateBytes": sum(x["bytes"] for x in included),
            "maxFile": largest[0] if largest else None, "largestFiles": largest,
            "duplicateGroups": duplicate_groups, "duplicateBytesBeyondFirst": sum(x["duplicateBytesBeyondFirst"] for x in duplicate_groups),
            "ignoredRawRequiresExplicitForceStage": [x["path"] for x in included if x["ignored"]],
            "plannedMissing": missing, "plannedOrEvidenceUnchanged": unchanged,
            "excluded": excluded, "unrelatedGitChangesNotSelected": undeclared,
            "failureHistoryIndex": failures(included), "files": included,
            "scope": "Proposed exact feature paths and original raw histories only. Duplicates are included; no Git index/repository mutation or numerical/public acceptance is inferred."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Fresh metadata evidence directory; no overwrite")
    parser.add_argument("--emit-manifest", action="store_true", help="Use only after explicit parent authorization; emits fresh JSON + NUL pathspec")
    args = parser.parse_args()
    output = args.output.resolve() if args.output else None
    need(not args.emit_manifest or output is not None, "Manifest requires a fresh output directory")
    if args.emit_manifest:
        need(output.parent == ROOT / "reports/world-static-mesh-flight-guard-checks" and output.name.startswith("publication"), "Final manifest destination must be checks/publication*")
    if output:
        need(is_inside(output, ROOT), "Output must stay in workspace")
        output.mkdir(parents=True, exist_ok=False)
        (output / "recipe.py.txt").write_bytes(Path(__file__).read_bytes())
        write(output / "invocation.json", {"argv": sys.argv, "cwd": str(Path.cwd()), "gitMutation": False})
    try:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        result = inventory(baseline, output)
        result["recipe"] = {"path": Path(__file__).relative_to(ROOT).as_posix(), **info(Path(__file__).read_bytes())}
        if output:
            write(output / "inventory.json", result)
        if args.emit_manifest:
            need(not result["plannedMissing"], "Missing planned feature paths")
            secret = [x for x in result["excluded"] if "credential" in x["reason"] or "key" in x["reason"]]
            need(not secret, "Credential/key exclusions require review before manifest")
            manifest = {"schema": 1, "status": "PROPOSED_NOT_STAGED", "inventory": info((output / "inventory.json").read_bytes()),
                        "files": result["files"], "gitMutation": False,
                        "forceStagePaths": result["ignoredRawRequiresExplicitForceStage"]}
            write(output / "manifest.json", manifest)
            with (output / "manifest.paths0").open("xb") as stream:
                stream.write(b"\0".join(x["path"].encode("utf-8") for x in result["files"]) + b"\0")
        print(json.dumps({k: result[k] for k in ("status", "candidateFiles", "candidateBytes", "maxFile", "duplicateBytesBeyondFirst", "protected", "plannedMissing", "unrelatedGitChangesNotSelected")}
                         | {"excludedFiles": len(result["excluded"]), "duplicateGroups": len(result["duplicateGroups"]),
                            "failureRecordFiles": len(result["failureHistoryIndex"]["topLevelFailureRecordFiles"]),
                            "ignoredRawFiles": len(result["ignoredRawRequiresExplicitForceStage"]), "output": str(output) if output else None,
                            "manifestEmitted": args.emit_manifest, "gitMutation": False}, ensure_ascii=False))
        return 0
    except BaseException as error:
        failure = {"status": "FAIL", "error": type(error).__name__ + ": " + str(error), "gitMutation": False}
        if output:
            write(output / "failure.json", failure)
        print(json.dumps(failure))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
