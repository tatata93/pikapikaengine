"""Isolated MSVC configured advance experiment, NOT a new artifact acceptance.

Creates only fresh scratch/report directories. It compiles a separate library
from ALL current core CPPs, including advance, and a self-contained new harness.
The identity covers the expanded sources/compiler/full configuration rather
than reusing the accepted guard's five-source identity. Actual instruction audit,
formal integration, public acceptance and natural fault injection remain absent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ADVANCE = "core/src/world_static_mesh_flight_advance.cpp"
TEST = "tests/world_static_mesh_flight_advance_tests.cpp"
CLOCK = Path(__file__).with_name("clock-reference.py")
PROFILE_SOURCES = ["core/src/core.cpp", "core/src/world_static_mesh_flight_guard.cpp", ADVANCE]
PROTECTED = ["build/native/Release/pikapika_core.lib",
             "build/native/Release/pikapika_world_static_mesh_flight_guard_tests.exe",
             "build/native/pikapika_core.dir/Release/core.obj",
             "build/native/Release/world-flight-guard.map",
             "build/native/world-flight-binding-Release.json"]
COMMON_OPTIONS = ["/fp:strict", "/GL-"]
NEW_OPTIONS = ["/W4", "/WX", "/permissive-"]
LINK_OPTIONS = ["/LTCG:OFF"]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def stamp(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def external_stamp(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def cmake_quote(value):
    need("\n" not in value and "\r" not in value, "CMake value contains newline")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$") + '"'


def cmake_path(path):
    return cmake_quote(Path(path).resolve().as_posix())


FACTS = r'''
if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "MSVC" OR NOT MSVC_VERSION EQUAL 1951)
  message(FATAL_ERROR "This experiment supports genuine MSVC 19.51 only.")
endif()
if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8 OR NOT CMAKE_GENERATOR_PLATFORM STREQUAL "x64" OR CMAKE_CROSSCOMPILING)
  message(FATAL_ERROR "This experiment requires native MSVC x64, not ARM64EC/cross compilation.")
endif()
function(proto_json_quote output input)
  string(REPLACE "\\" "\\\\" escaped "${input}")
  string(REPLACE "\"" "\\\"" escaped "${escaped}")
  string(REPLACE "\n" "\\n" escaped "${escaped}")
  string(REPLACE "\r" "\\r" escaped "${escaped}")
  set(${output} "\"${escaped}\"" PARENT_SCOPE)
endfunction()
set(proto_json "{\n")
foreach(key IN ITEMS CMAKE_VERSION CMAKE_CXX_COMPILER_ID CMAKE_CXX_COMPILER_VERSION CMAKE_CXX_COMPILER
    MSVC_VERSION MSVC_CXX_ARCHITECTURE_ID CMAKE_SIZEOF_VOID_P CMAKE_SYSTEM_NAME
    CMAKE_SYSTEM_PROCESSOR CMAKE_GENERATOR CMAKE_GENERATOR_PLATFORM CMAKE_GENERATOR_TOOLSET
    CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_RELEASE CMAKE_MSVC_RUNTIME_LIBRARY)
  proto_json_quote(encoded "${${key}}")
  string(APPEND proto_json "  \"${key}\":${encoded},\n")
endforeach()
string(APPEND proto_json "  \"configuration\":\"Release\"\n}\n")
file(WRITE "${CMAKE_BINARY_DIR}/compiler-facts.json" "${proto_json}")
'''


def preamble(project):
    return "\n".join(["cmake_minimum_required(VERSION 3.24)",
                       "project(" + project + " LANGUAGES CXX)",
                       "set(CMAKE_CXX_STANDARD 20)", "set(CMAKE_CXX_STANDARD_REQUIRED ON)",
                       "set(CMAKE_CXX_EXTENSIONS OFF)",
                       "set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)", FACTS])


class Commands:
    def __init__(self, output, source_paths):
        self.output, self.source_paths, self.items = output, source_paths, []

    def identities(self):
        return {path.relative_to(ROOT).as_posix(): stamp(path) if path.is_file() else None for path in self.source_paths}

    def run(self, name, argv, timeout=600):
        record = {"name": name, "argv": list(map(str, argv)), "cwd": str(ROOT), "before": self.identities()}
        started = time.monotonic()
        try:
            done = subprocess.run(record["argv"], cwd=ROOT, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=timeout)
            code, stdout, stderr = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as error:
            code, stdout = None, error.stdout or b""
            stderr = (error.stderr or b"") + str(error).encode()
            record["exception"] = "TimeoutExpired: " + str(error)
        except BaseException as error:
            code, stdout, stderr = None, b"", str(error).encode()
            record["exception"] = type(error).__name__ + ": " + str(error)
        record.update(exitCode=code, elapsedSeconds=time.monotonic() - started)
        for kind, raw in (("stdout", stdout), ("stderr", stderr)):
            path = self.output / (name + "." + kind + ".txt")
            path.write_bytes(raw)
            record[kind] = stamp(path)
        record["after"] = self.identities()
        record["sourceAndAcceptedArtifactsStable"] = record["before"] == record["after"]
        self.items.append(record)
        write(self.output / (name + ".command.json"), record)
        need(code == 0, "Command failed: " + name)
        need(record["sourceAndAcceptedArtifactsStable"], "Source/accepted artifact changed: " + name)
        return stdout


def compiler_facts(path):
    facts = json.loads(path.read_text(encoding="utf-8"))
    need(facts["CMAKE_CXX_COMPILER_ID"] == "MSVC" and re.match(r"^19\.51(?:\.|$)", facts["CMAKE_CXX_COMPILER_VERSION"]), "MSVC 19.51 only")
    need(facts["MSVC_VERSION"] == "1951" and facts["CMAKE_GENERATOR_PLATFORM"] == "x64" and
         facts["CMAKE_SIZEOF_VOID_P"] == "8" and facts["CMAKE_SYSTEM_NAME"] == "Windows" and
         facts["CMAKE_SYSTEM_PROCESSOR"].lower() in {"amd64", "x86_64"}, "Native Windows x64 only")
    for key in ("CMAKE_CXX_FLAGS", "CMAKE_CXX_FLAGS_RELEASE"):
        value = facts[key]
        need(not re.search(r"(?:^|\s)/(?:GL|LTCG)(?=\s|:|$)", value, re.I), "No inherited LTO")
        need(not re.search(r"(?:^|\s)/fp:(?:fast|precise)(?=\s|$)", value, re.I), "No contradictory inherited FP mode")
    return facts


def identity_material(facts, sources):
    return {"schema": 1, "kind": "isolated-configured-World-flight-advance-prototype-v1",
            "sources": [stamp(path) for path in sources], "compilerFacts": facts,
            "compilerBinary": external_stamp(facts["CMAKE_CXX_COMPILER"]),
            "configuration": {"standard": "c++20", "extensions": False, "configuration": "Release",
                              "allLibraryAndHarnessOptions": COMMON_OPTIONS,
                              "newAdvanceAndHarnessAdditionalOptions": NEW_OPTIONS,
                              "linkOptions": LINK_OPTIONS, "IPO": False,
                              "profile": 1, "identityMacro": "SHA256 of this complete canonical material",
                              "profiledLibrarySources": PROFILE_SOURCES,
                              "harnessProfile": True},
            "scope": "Declared experimental source/compiler/flags identity only. Not self-measured machine-code proof or public artifact acceptance."}


def project(cpps, identity):
    lines = [preamble("WorldFlightAdvanceConfiguredPrototype"), "add_library(advance_prototype_core STATIC"]
    lines.extend("  " + cmake_path(path) for path in cpps)
    lines += [")", "target_include_directories(advance_prototype_core PUBLIC " + cmake_path(ROOT / "core/include") + ")",
              "target_compile_options(advance_prototype_core PRIVATE " + " ".join(COMMON_OPTIONS) + ")",
              "set_property(TARGET advance_prototype_core PROPERTY INTERPROCEDURAL_OPTIMIZATION FALSE)"]
    definitions = 'PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1;PIKAPIKA_WORLD_FLIGHT_BUILD_ID="' + identity + '"'
    lines += ["set_source_files_properties("]
    lines.extend("  " + cmake_path(ROOT / path) for path in PROFILE_SOURCES)
    lines += ["  PROPERTIES COMPILE_DEFINITIONS " + cmake_quote(definitions) + ")",
              "set_source_files_properties(" + cmake_path(ROOT / ADVANCE) + " PROPERTIES COMPILE_OPTIONS " + cmake_quote(";".join(NEW_OPTIONS)) + ")",
              "add_executable(advance_configured " + cmake_path(ROOT / TEST) + ")",
              "target_link_libraries(advance_configured PRIVATE advance_prototype_core)",
              "target_compile_options(advance_configured PRIVATE " + " ".join(COMMON_OPTIONS + NEW_OPTIONS) + ")",
              "target_compile_definitions(advance_configured PRIVATE " + cmake_quote(definitions) + ")",
              "target_link_options(advance_configured PRIVATE " + " ".join(LINK_OPTIONS) + ")",
              "set_property(TARGET advance_configured PROPERTY INTERPROCEDURAL_OPTIMIZATION FALSE)", ""]
    return "\n".join(lines)


def command_provenance(build, sources, identity, output):
    copies, observed = [], {}
    for path in sorted(build.rglob("CL.command.1.tlog")):
        relative = path.relative_to(build).as_posix()
        destination = output / ("compile-" + str(len(copies)) + ".tlog.txt")
        destination.write_bytes(path.read_bytes())
        copies.append({"original": stamp(path), "copy": stamp(destination)})
        lines = path.read_bytes().decode("utf-16").splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("^"):
                continue
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("^")), len(lines))
            command = " ".join(lines[i + 1:end])
            for key in line[1:].split("|"):
                key = key.replace("/", "\\").casefold()
                need(key not in observed, "Unique actual source compilation expected")
                observed[key] = {"command": command, "tlog": relative}
    results = []
    for path in sources:
        key = str(path.resolve()).replace("/", "\\").casefold()
        need(key in observed, "Missing actual compiler command: " + str(path))
        row = observed[key]
        command = row["command"]
        fp = re.findall(r"(?:^|\s)/fp:([a-z]+)(?=\s|$)", command, re.I)
        need(fp and all(x.lower() == "strict" for x in fp), "All library/harness sources must actually be strict")
        need(not re.search(r"(?:^|\s)/GL(?=\s|$)", command, re.I), "Actual source enables LTO")
        need(re.search(r"(?:^|\s)/GL-(?=\s|$)", command, re.I), "Actual source must explicitly disable LTO")
        relative = path.relative_to(ROOT).as_posix()
        if relative in {ADVANCE, TEST}:
            need(re.search(r"(?:^|\s)/W4(?=\s|$)", command, re.I) and re.search(r"(?:^|\s)/WX(?=\s|$)", command, re.I)
                 and re.search(r"(?:^|\s)/permissive-(?=\s|$)", command, re.I), "New advance/harness strict warnings")
        if relative in PROFILE_SOURCES or relative == TEST:
            need("PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1" in command and identity in command, "Actual expanded configuration definitions")
        results.append({"source": relative, **row})
    for path in sorted(build.glob("*.vcxproj")):
        destination = output / path.name
        destination.write_bytes(path.read_bytes())
        copies.append({"original": stamp(path), "copy": stamp(destination)})
        ET.fromstring(path.read_bytes())
    links = [path for path in build.rglob("link.command.1.tlog")
             if "advance_configured.dir" in path.relative_to(build).parts]
    need(len(links) == 1, "One actual experimental executable link")
    raw = links[0].read_bytes()
    link = raw.decode("utf-16")
    need(not re.search(r"(?:^|\s)/LTCG(?!:OFF)(?=\s|:|$)", link, re.I), "No actual link LTO")
    destination = output / "link-command.tlog.txt"
    destination.write_bytes(raw)
    copies.append({"original": stamp(links[0]), "copy": stamp(destination)})
    return {"sourceCommands": results, "copies": copies,
            "scope": "Captured actual MSBuild project/tlogs, not compiler attestation or instruction audit."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="New one-component scratch/report run name")
    parser.add_argument("--parallel", type=int, default=2)
    args = parser.parse_args()
    need(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}", args.name) and args.name not in {".", ".."}, "One safe new directory component")
    need(1 <= args.parallel <= 4, "Bounded build parallelism")
    output = ROOT / "reports/world-static-mesh-flight-advance-checks" / args.name
    scratch = ROOT / "build/world-flight-advance-prototype" / args.name
    need(not output.exists() and not scratch.exists(), "Fresh run directories required")
    output.mkdir(parents=True, exist_ok=False)
    scratch.mkdir(parents=True, exist_ok=False)
    (output / "recipe.py.txt").write_bytes(Path(__file__).read_bytes())
    write(output / "invocation.json", {"argv": sys.argv, "cwd": str(Path.cwd())})
    cpps = sorted((ROOT / "core/src").glob("*.cpp"))
    headers = sorted(p for p in (ROOT / "core").rglob("*") if p.is_file() and p.suffix in {".hpp", ".h"})
    source_paths = sorted(set(cpps + headers + [ROOT / TEST, CLOCK, Path(__file__)]))
    monitored = sorted(set(source_paths + [ROOT / p for p in PROTECTED]))
    commands = Commands(output, monitored)
    record = {"schema": 1, "status": "FAIL", "started": datetime.now(timezone.utc).isoformat(),
              "scope": "Experimental expanded-source MSVC19.51x64 configuration finite behavior/clock tests only. No new actual-instruction artifact audit, formal integration, public acceptance, World response or natural fault injection is claimed."}
    before = {}
    try:
        need(sys.platform == "win32", "MSVC Windows experiment only")
        need(ROOT / ADVANCE in cpps and len(cpps) == len(set(cpps)), "New advance exactly once in all-current-core list")
        need(all(path.is_file() for path in monitored), "All sources/harness/clock reference/accepted artifacts required before run")
        before = commands.identities()
        write(output / "before.json", before)
        probe = scratch / "probe"
        probe.mkdir()
        probe_driver = preamble("WorldFlightAdvanceCompilerProbe") + "\n"
        (probe / "CMakeLists.txt").write_text(probe_driver, encoding="utf-8", newline="\n")
        (output / "probe-CMakeLists.txt").write_text(probe_driver, encoding="utf-8", newline="\n")
        commands.run("probe-configure", ["cmake", "-S", probe, "-B", scratch / "probe-build", "-A", "x64"])
        facts = compiler_facts(scratch / "probe-build/compiler-facts.json")
        material = identity_material(facts, source_paths)
        canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        identity = hashlib.sha256(canonical).hexdigest()
        old = json.loads((ROOT / PROTECTED[-1]).read_text(encoding="utf-8"))
        need(identity != old["buildId"], "Never reuse the accepted five-source identity")
        write(output / "identity-material.json", material)
        (output / "identity-material.canonical.txt").write_bytes(canonical)
        write(output / "experimental-profile.json", {"schema": 1, "profile": 1, "buildId": identity,
              "oldAcceptedBuildId": old["buildId"], "sourceCount": len(source_paths), "coreTranslationUnits": len(cpps),
              "identityMaterialSha256": identity, "artifactAuditComplete": False,
              "scope": "Experimental configuration identity; runtime ready is NOT external artifact acceptance."})
        project_dir = scratch / "project"
        project_dir.mkdir()
        driver = project(cpps, identity)
        (project_dir / "CMakeLists.txt").write_text(driver, encoding="utf-8", newline="\n")
        (output / "CMakeLists.txt").write_text(driver, encoding="utf-8", newline="\n")
        build = scratch / "build"
        argv = ["cmake", "-S", project_dir, "-B", build, "-G", facts["CMAKE_GENERATOR"], "-A", "x64",
                "-DCMAKE_CXX_COMPILER=" + facts["CMAKE_CXX_COMPILER"],
                "-DCMAKE_CXX_FLAGS=" + facts["CMAKE_CXX_FLAGS"], "-DCMAKE_CXX_FLAGS_RELEASE=" + facts["CMAKE_CXX_FLAGS_RELEASE"]]
        if facts["CMAKE_GENERATOR_TOOLSET"]:
            argv.extend(["-T", facts["CMAKE_GENERATOR_TOOLSET"]])
        if facts["CMAKE_MSVC_RUNTIME_LIBRARY"]:
            argv.append("-DCMAKE_MSVC_RUNTIME_LIBRARY=" + facts["CMAKE_MSVC_RUNTIME_LIBRARY"])
        commands.run("configure", argv)
        need(compiler_facts(build / "compiler-facts.json") == facts, "Actual library/harness compiler configuration changed after identity creation")
        commands.run("build", ["cmake", "--build", build, "--config", "Release", "--target", "advance_configured", "--parallel", args.parallel, "--verbose"])
        compilation = command_provenance(build, cpps + [ROOT / TEST], identity, output)
        write(output / "compile-provenance.json", compilation)
        executable = build / "Release/advance_configured.exe"
        library = build / "Release/advance_prototype_core.lib"
        record["experimentalArtifacts"] = [stamp(executable), stamp(library)]
        commands.run("configured-tests", [executable, "--run"])
        raw = commands.run("clock-fixtures", [executable, "--clock-fixtures"])
        clock_path = output / "clock-fixtures.json"
        clock_path.write_bytes(raw)
        commands.run("independent-clock-reference", [sys.executable, CLOCK, clock_path])
        record.update(status="PASS", buildId=identity, coreTranslationUnits=len(cpps), sources=len(source_paths),
                      experimentalProfile=stamp(output / "experimental-profile.json"),
                      compileProvenance=stamp(output / "compile-provenance.json"), clockFixtures=stamp(clock_path),
                      formalArtifactAuditComplete=False, executedCases="See preserved harness and independent clock stdout; no invented count")
    except BaseException as error:
        record["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        after = {p.relative_to(ROOT).as_posix(): stamp(p) for p in monitored if p.is_file()}
        record["sourcesAndAcceptedArtifactsUnchanged"] = bool(before) and before == after
        if not record["sourcesAndAcceptedArtifactsUnchanged"]:
            record["status"] = "FAIL"
        write(output / "after.json", after)
        record["commands"] = commands.items
        record["finished"] = datetime.now(timezone.utc).isoformat()
        record["recipe"] = stamp(Path(__file__))
        write(output / "observation.json", record)
        print(json.dumps({"status": record["status"], "report": str(output / "observation.json"),
                          "scope": record["scope"], "failure": record.get("failure")}, ensure_ascii=False))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
