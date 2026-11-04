"""Isolated, unconfigured advance prototype check; never accepts profile 1.

The existing local-accepted guard library/artifacts are only read. This checks
compilation and actual refusal of the new, default-unconfigured entry point.
It does not certify successful World advancement or a new audited build binding.
"""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if len(sys.argv) != 2:
    raise SystemExit("usage: check-default-prototype.py NEW_RUN_NAME")
name = sys.argv[1]
if not name or Path(name).name != name or name in {".", ".."}:
    raise SystemExit("run name must be one directory component")
out = ROOT / "reports/world-static-mesh-flight-advance-checks" / name
scratch = ROOT / "build/world-flight-advance-prototype" / name
out.mkdir(parents=True, exist_ok=False)
scratch.mkdir(parents=True, exist_ok=False)
sources = [
    "core/include/pikapika/world_static_mesh_flight_advance.hpp",
    "core/src/world_static_mesh_flight_advance.cpp",
    "tests/world_static_mesh_flight_advance_tests.cpp",
]
protected = [
    "build/native/Release/pikapika_core.lib",
    "build/native/Release/pikapika_world_static_mesh_flight_guard_tests.exe",
    "build/native/pikapika_core.dir/Release/core.obj",
    "build/native/Release/world-flight-guard.map",
    "build/native/world-flight-binding-Release.json",
]


def identity(path):
    data = (ROOT / path).read_bytes()
    return {"path": path, "bytes": len(data), "sha256": sha256(data).hexdigest()}


before = {p: identity(p) for p in sources + protected}
commands = []
record = {"schema": 1, "status": "RUNNING", "started": datetime.now(timezone.utc).isoformat(),
          "scope": "Unconfigured new translation unit linked to the existing read-only accepted library. Compilation and profile refusal only; no successful advance or new artifact acceptance.",
          "before": list(before.values()), "commands": commands}


def write():
    (out / "observation.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf8")


def run(label, argv):
    start = time.monotonic()
    completed = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    (out / (label + ".stdout.txt")).write_bytes(completed.stdout)
    (out / (label + ".stderr.txt")).write_bytes(completed.stderr)
    commands.append({"label": label, "argv": list(map(str, argv)), "exitCode": completed.returncode,
                     "elapsedSeconds": time.monotonic() - start,
                     "stdout": {"bytes": len(completed.stdout), "sha256": sha256(completed.stdout).hexdigest()},
                     "stderr": {"bytes": len(completed.stderr), "sha256": sha256(completed.stderr).hexdigest()}})
    write()
    if completed.returncode:
        raise RuntimeError(label + " failed; see raw command logs")


try:
    # Absolute CMake paths have no variable interpolation from user input.
    def cmake_path(path):
        return str(path).replace("\\", "/")
    driver = "\n".join([
        "cmake_minimum_required(VERSION 3.24)",
        "project(WorldFlightAdvanceDefaultPrototype LANGUAGES CXX)",
        "set(CMAKE_CXX_STANDARD 20)",
        "set(CMAKE_CXX_STANDARD_REQUIRED ON)",
        "set(CMAKE_CXX_EXTENSIONS OFF)",
        "add_executable(advance_default",
        '  "' + cmake_path(ROOT / sources[1]) + '"',
        '  "' + cmake_path(ROOT / sources[2]) + '")',
        'target_include_directories(advance_default PRIVATE "' + cmake_path(ROOT / "core/include") + '")',
        'target_link_libraries(advance_default PRIVATE "' + cmake_path(ROOT / protected[0]) + '")',
        "if(MSVC)",
        "  target_compile_options(advance_default PRIVATE /W4 /WX /permissive- /fp:strict)",
        "else()",
        '  message(FATAL_ERROR "This default-prototype recipe uses the existing MSVC library only.")',
        "endif()", "",
    ])
    (scratch / "CMakeLists.txt").write_text(driver, encoding="utf8")
    (out / "CMakeLists.txt").write_text(driver, encoding="utf8")
    write()
    run("configure", ["cmake", "-S", str(scratch), "-B", str(scratch / "build"), "-A", "x64"])
    run("build", ["cmake", "--build", str(scratch / "build"), "--config", "Release", "--target", "advance_default", "--parallel", "2"])
    executable = scratch / "build/Release/advance_default.exe"
    run("default-refusal", [str(executable), "--unsupported-profile"])
    record["executable"] = identity(executable.relative_to(ROOT).as_posix())
    after = {p: identity(p) for p in sources + protected}
    record["after"] = list(after.values())
    record["sourcesAndProtectedArtifactsUnchanged"] = before == after
    if before != after:
        raise RuntimeError("source/protected artifact changed during check")
    record["status"] = "PASS"
except Exception as error:
    record["status"] = "FAIL"
    record["failure"] = {"type": type(error).__name__, "message": str(error)}
    write()
    raise
record["finished"] = datetime.now(timezone.utc).isoformat()
write()
print(json.dumps({"status": record["status"], "report": str(out / "observation.json"),
                  "scope": record["scope"]}))
