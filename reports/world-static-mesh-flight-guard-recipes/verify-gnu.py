"""GNU 13 CI orchestration. Never substitutes an instrumented binding for normal.

Run after the existing Release build/ci has been configured with Unix Makefiles
and CMAKE_EXPORT_COMPILE_COMMANDS=ON. Every output directory must be fresh.
This recipe does not alter CMake, production sources, SDK artifacts or flags in
the existing normal build. ASan/UBSan and Debug use separate CMake directories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TARGET = "pikapika_world_static_mesh_flight_guard_tests"
CHECKER = ROOT / "scripts/verify-world-static-mesh-flight-guard.py"
CONTROLS = ROOT / "tests/world_static_mesh_flight_guard_reference_tests.py"
AUDITOR = Path(__file__).with_name("audit-binding.py")
STRICT = ["-fno-fast-math", "-ffp-contract=off", "-frounding-math",
          "-fexcess-precision=standard", "-mfpmath=sse", "-msse2", "-fno-lto"]
SANITIZERS = ["-fsanitize=address,undefined", "-fno-sanitize-recover=undefined", "-fno-omit-frame-pointer"]
WARN_SOURCES = ["core/src/world_static_mesh_flight_guard.cpp",
                "tests/world_static_mesh_flight_guard_tests.cpp",
                "tests/world_static_mesh_flight_guard_fixtures.cpp"]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": digest(raw)}


def write(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def load(path):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, "Duplicate JSON key: " + key)
            value[key] = item
        return value
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_int=lambda text: -0.0 if text == "-0" else int(text),
                      parse_constant=lambda text: (_ for _ in ()).throw(ValueError(text)))


def source_stamps():
    paths = {ROOT / "CMakeLists.txt", AUDITOR, Path(__file__)}
    for folder, suffixes in (("core", {".cpp", ".hpp", ".h"}),
                             ("tests", {".cpp", ".hpp", ".h", ".py"}),
                             ("scripts", {".py"}), ("cmake", {".cmake"})):
        paths.update(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in suffixes)
    return [stamp(p) for p in sorted(paths, key=lambda x: str(x))]


class Commands:
    def __init__(self, output, timeout):
        self.output, self.timeout, self.items = output, timeout, []

    def run(self, name, argv, *, env=None, timeout=None):
        argv = list(map(str, argv))
        record = {"name": name, "argv": argv, "cwd": str(ROOT), "environmentOverrides": env or {}}
        start = time.monotonic()
        try:
            actual_env = os.environ.copy()
            actual_env.update(env or {})
            done = subprocess.run(argv, cwd=ROOT, env=actual_env, capture_output=True,
                                  timeout=timeout or self.timeout)
            record["exitCode"], stdout, stderr = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as error:
            record.update(exitCode=None, exception="TimeoutExpired: " + str(error))
            stdout, stderr = error.stdout or b"", (error.stderr or b"") + str(error).encode()
        except BaseException as error:
            record.update(exitCode=None, exception=type(error).__name__ + ": " + str(error))
            stdout, stderr = b"", str(error).encode()
        record["elapsedSeconds"] = time.monotonic() - start
        for key, raw in (("stdout", stdout), ("stderr", stderr)):
            path = self.output / (name + "." + key + ".txt")
            path.write_bytes(raw)
            record[key] = stamp(path)
        self.items.append(record)
        write(self.output / (name + ".command.json"), record)
        if record["exitCode"] != 0:
            # GitHub logs must retain the actual failed child's diagnostic;
            # local-only files/hashes disappear with the hosted runner.
            print(json.dumps({"failedCommand": name, "exitCode": record["exitCode"],
                              "stdout": stdout.decode("utf-8", errors="replace"),
                              "stderr": stderr.decode("utf-8", errors="replace")},
                             ensure_ascii=False), flush=True)
        need(record["exitCode"] == 0, "Command failed: " + name)
        return stdout


def cache(build):
    path = build / "CMakeCache.txt"
    need(path.is_file(), "Existing CMake build required: " + str(build))
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([^#/:][^:]*):[^=]+=(.*)$", line)
        if match:
            result[match[1]] = match[2]
    return result


def compilation(build, target="pikapika_core"):
    need(isinstance(target, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.+-]*", target), "Compile target component")
    object_root = build.resolve() / "CMakeFiles" / (target + ".dir")
    entries = load(build / "compile_commands.json")
    need(isinstance(entries, list), "Compile database list")
    result = {}
    for entry in entries:
        source = Path(entry["file"])
        if not source.is_absolute():
            source = Path(entry["directory"]) / source
        source = source.resolve()
        if ROOT / "core/src" not in source.parents:
            continue
        argv = entry.get("arguments") or shlex.split(entry["command"])
        need(isinstance(argv, list) and all(isinstance(x, str) for x in argv), "Compile argv")
        need("-o" in argv and argv.index("-o") + 1 < len(argv), "Object output argument")
        path = Path(argv[argv.index("-o") + 1])
        if not path.is_absolute():
            path = Path(entry["directory"]) / path
        path = path.resolve()
        if object_root not in path.parents:
            continue
        need(source not in result, "Duplicate core source compile entry")
        result[source] = {"argv": argv, "directory": entry["directory"], "object": path}
    need(result, "Nonempty library source set")
    return result


def check_sanitized_compilation(build, expected):
    rows = compilation(build)
    need(set(rows) == set(expected), "All core library translation units retained in sanitizer build")
    observations = []
    for source, item in sorted(rows.items(), key=lambda x: str(x[0])):
        args = item["argv"]
        need(set(SANITIZERS) <= set(args), "All dependency sources must carry sanitizer flags: " + str(source))
        optimizations = [x for x in args if re.fullmatch(r"-O(?:[0-3sgz]|fast)", x)]
        need(optimizations and all(x == "-O1" for x in optimizations), "Only O1 in actual sanitized compile command")
        need("-DNDEBUG" in args, "Sanitized numerical comparator keeps Release NDEBUG")
        need(not any(re.match(r"-flto(?:=|$)", x) for x in args), "No sanitizer LTO")
        observations.append({"source": str(source), "argv": args, "object": stamp(item["object"])})
    return observations


def profile(build, expected_configuration):
    data = load(build / ("world-flight-binding-" + expected_configuration + ".json"))
    need(data.get("schema") == 1 and data.get("configuration") == expected_configuration, "Configured profile schema/configuration")
    need(data.get("compiler", {}).get("id") == "GNU" and re.match(r"^13(?:\.|$)", data["compiler"]["version"]), "GNU 13 only")
    need(re.fullmatch(r"[0-9a-f]{64}", data.get("buildId", "")), "Configuration identity")
    need(data.get("profile") == (1 if expected_configuration == "Release" else 0), "Configured or unconfigured profile expected")
    for row in data["sources"]:
        need(stamp(ROOT / row["path"])["sha256"] == row["sha256"], "Profile source identity")
    return data


def run_fixture(commands, name, binary, output, env=None):
    raw = commands.run(name, [binary, "--fixtures"], env=env)
    path = output / (name + ".json")
    path.write_bytes(raw)
    data = load(path)
    need(data.get("schema") == 1 and data.get("kind") == "world-static-mesh-flight-guard-fixtures", "Actual fixture envelope")
    need(isinstance(data.get("fixtures"), list) and len(data["fixtures"]) == 51, "Exact current 51 actual inputs")
    return path, data


def exact_tree(value):
    """Preserve key/array order, scalar type and signed-zero binary64 bits."""
    if isinstance(value, dict):
        return ["object", [[k, exact_tree(v)] for k, v in value.items()]]
    if isinstance(value, list):
        return ["array", [exact_tree(x) for x in value]]
    if type(value) is float:
        return ["float64", struct.pack(">d", value).hex()]
    if type(value) is int:
        return ["integer", str(value)]
    if type(value) is bool:
        return ["boolean", value]
    if value is None:
        return ["null"]
    need(type(value) is str, "Unexpected JSON scalar")
    return ["string", value]


def compare_fixtures(normal, sanitized, normal_id, sanitized_id):
    need(normal_id != sanitized_id, "Sanitizer configuration must have a distinct identity")
    # Only this exact field in every outer binding may differ. No other string,
    # message, optional, child interval, counter or sizeof field is normalized.
    for data, identity in ((normal, normal_id), (sanitized, sanitized_id)):
        need(len(data["fixtures"]) == 51, "Whole current corpus")
        for fixture in data["fixtures"]:
            binding = fixture["result"]["binding"]
            need(binding["buildId"] == identity, "Whole corpus binding identity")
            binding["buildId"] = "<sole-configured-buildId-difference>"
    left, right = exact_tree(normal), exact_tree(sanitized)
    need(left == right, "Normal/sanitized whole JSON differs beyond outer binding.buildId")
    raw = json.dumps(left, ensure_ascii=False, separators=(",", ":")).encode()
    return {"status": "PASS", "fixtures": 51, "normalizedPaths": "fixtures[*].result.binding.buildId ONLY",
            "normalBuildId": normal_id, "sanitizedBuildId": sanitized_id,
            "comparison": "Complete key order, JSON scalar types, array order and IEEE64 signed-zero bits",
            "normalizedTreeSha256": digest(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal", type=Path, default=ROOT / "build/ci")
    parser.add_argument("--output", type=Path, default=ROOT / "build/ci/world-flight-guard-audit")
    parser.add_argument("--sanbuild", type=Path, default=ROOT / "build/world-flight-guard-sanitized")
    parser.add_argument("--debugbuild", type=Path, default=ROOT / "build/world-flight-guard-unconfigured")
    parser.add_argument("--parallel", type=int, default=2)
    parser.add_argument("--command-timeout", type=int, default=600)
    args = parser.parse_args()
    need(1 <= args.parallel <= 4 and 30 <= args.command_timeout <= 1200, "Bounded command settings")
    need(len({p.resolve() for p in (args.normal, args.output, args.sanbuild, args.debugbuild)}) == 4, "Distinct directories")
    need(not args.sanbuild.exists() and not args.debugbuild.exists(), "Fresh sanitizer/Debug directories required")
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "recipe.py.txt").write_bytes(Path(__file__).read_bytes())
    write(args.output / "invocation.json", {"argv": sys.argv, "cwd": str(Path.cwd())})
    before = source_stamps()
    write(args.output / "sources-before.json", before)
    commands, result = Commands(args.output, args.command_timeout), {"schema": 1, "status": "FAIL"}
    try:
        need(sys.platform.startswith("linux"), "This recipe requires actual Linux GNU tooling")
        c = cache(args.normal)
        need(c.get("CMAKE_BUILD_TYPE") == "Release" and c.get("CMAKE_GENERATOR") == "Unix Makefiles", "Existing Release Unix Makefiles build")
        need(c.get("CMAKE_EXPORT_COMPILE_COMMANDS") in ("ON", "TRUE", "1"), "Root must configure actual compile database ON")
        need(c.get("CMAKE_HOME_DIRECTORY") == str(ROOT), "Existing source directory identity")
        commands.run("normal-target-build", ["cmake", "--build", args.normal, "--target", TARGET, "--parallel", args.parallel, "--verbose"])
        normal_profile = profile(args.normal, "Release")
        normal_compilation = compilation(args.normal)
        object_path = normal_compilation[(ROOT / "core/src/core.cpp").resolve()]["object"]
        binary = args.normal / TARGET
        linkmap = args.normal / "world-flight-guard.map"
        need(linkmap.is_file(), "Root must add actual GNU target linker map")
        audit_raw = commands.run("normal-artifact-audit", [sys.executable, AUDITOR,
            "--profile", args.normal / "world-flight-binding-Release.json", "--object", object_path,
            "--binary", binary, "--map", linkmap, "--build-directory", args.normal,
            "--output", args.output / "normal-binding"])
        audit = json.loads(audit_raw)
        need(audit.get("status") == "PASS" and audit.get("binaryExecuted") is False, "Normal actual artifact audit")
        warning_dir = args.output / "warning-objects"
        warning_dir.mkdir()
        for i, source in enumerate(WARN_SOURCES):
            argv = [normal_profile["compiler"]["path"], "-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror", *STRICT,
                    "-I" + str(ROOT / "core/include"), "-I" + str(ROOT / "tests"),
                    "-DPIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1",
                    '-DPIKAPIKA_WORLD_FLIGHT_BUILD_ID="' + normal_profile["buildId"] + '"',
                    "-c", ROOT / source, "-o", warning_dir / (str(i) + ".o")]
            commands.run("warning-" + str(i), argv)
        commands.run("normal-tests", [binary])
        normal_path, normal = run_fixture(commands, "normal-fixtures", binary, args.output)
        commands.run("normal-storage", [binary, "--storage"])
        commands.run("normal-independent-math", [sys.executable, CHECKER, normal_path])
        commands.run("normal-independent-controls", [sys.executable, CONTROLS, normal_path, "--output", args.output / "normal-reference"])
        common_config = ["-G", "Unix Makefiles", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
                         "-DCMAKE_CXX_COMPILER=" + normal_profile["compiler"]["path"], "-DBUILD_TESTING=ON"]
        commands.run("debug-configure", ["cmake", "-S", ROOT, "-B", args.debugbuild, *common_config, "-DCMAKE_BUILD_TYPE=Debug"])
        commands.run("debug-build", ["cmake", "--build", args.debugbuild, "--target", TARGET, "--parallel", args.parallel, "--verbose"])
        debug_profile = profile(args.debugbuild, "Debug")
        debug_raw = commands.run("debug-unconfigured-actual-guard", [args.debugbuild / TARGET, "--unsupported-profile"])
        need(b"unsupported build profile refusal PASS" in debug_raw and b"child calls0" in debug_raw, "Actual unconfigured fallback refusal")
        flags = " ".join(["-O1", "-g", *SANITIZERS])
        commands.run("sanitizer-configure", ["cmake", "-S", ROOT, "-B", args.sanbuild, *common_config,
            "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_CXX_FLAGS=" + flags,
            "-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG", "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined"])
        commands.run("sanitizer-build-all-dependencies", ["cmake", "--build", args.sanbuild, "--target", TARGET,
            "--parallel", args.parallel, "--verbose"])
        san_profile = profile(args.sanbuild, "Release")
        instrumented = check_sanitized_compilation(args.sanbuild, normal_compilation)
        write(args.output / "sanitized-translation-units.json", instrumented)
        env = {"ASAN_OPTIONS": "detect_leaks=1:halt_on_error=1", "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"}
        commands.run("sanitizer-tests", [args.sanbuild / TARGET], env=env)
        san_path, sanitized = run_fixture(commands, "sanitizer-fixtures", args.sanbuild / TARGET, args.output, env)
        commands.run("sanitizer-independent-math", [sys.executable, CHECKER, san_path])
        commands.run("sanitizer-independent-controls", [sys.executable, CONTROLS, san_path, "--output", args.output / "sanitizer-reference"])
        comparison = compare_fixtures(normal, sanitized, normal_profile["buildId"], san_profile["buildId"])
        write(args.output / "normal-sanitized-comparison.json", comparison)
        result.update(status="PASS", normalBindingAudit=stamp(args.output / "normal-binding/audit.json"),
                      normalProfile=normal_profile, sanitizedProfile=san_profile, debugProfile=debug_profile,
                      finiteFixtures=51, comparison=comparison, instrumentedLibraryTranslationUnits=len(instrumented),
                      normalFixtures=stamp(normal_path), sanitizedFixtures=stamp(san_path),
                      scope={"normal": "Actual source/configuration, compiler-command and object/link leaf binding gate, then numerical tests and independent Fraction verification",
                             "callerAssociation": "Plane dot-offset/threshold/comparison and left-associated radii+margin are source-literal plus actual strict non-LTO compiler-contract inferences. Only three leaf graphs and caller target/fused-x87 checks are machine-dataflow audited; the entire caller comparison graph is not symbolically proved.",
                             "sanitizer": "All core library dependency translation units and test target compiled O1 with ASan/UBSan. Numerical and memory-development evidence only; instrumented code is NOT a normal-artifact machine-binding audit.",
                             "fallback": "Actual separate Debug guard profile0 refuses before numerical child calls, without caller boolean or runtime unlock",
                             "limits": "No new Native/WASM API, World advance, response, all-platform certification or natural allocation/nonreturn fault injection."})
    except BaseException as error:
        result.update(error=type(error).__name__ + ": " + str(error))
    finally:
        after = source_stamps()
        write(args.output / "sources-after.json", after)
        result["sourceStable"] = before == after
        if not result["sourceStable"]:
            result.update(status="FAIL", sourceError="Sources changed during orchestration")
        result["commands"] = commands.items
        result["recipe"] = stamp(Path(__file__))
        write(args.output / "verification.json", result)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
