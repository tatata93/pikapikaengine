"""Independent exact-rational optical-route fixture checks.

JSON numbers are decoded as binary64 (including integer-spelled endpoints),
then converted with Fraction.from_float. Decimal source spelling is not an
exact-real endpoint. Finite reference cases and optional parity are not a
whole-family proof of the interval kernel.
"""
import argparse
import json
import math
from pathlib import Path
import struct
import sys
from fractions import Fraction as F

if not __debug__:
    raise SystemExit("Python -O is rejected: proof checks must not be disabled")

NAMES = {"direct", "ghost", "brewster", "index-family", "miss",
         "sphere-reflection", "cap-reflection", "dispersion", "TIR-unavailable",
         "self-boundary", "step-budget", "continuation-range", "critical",
         "uncertain-source", "sqrt-budget"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, required, optional=()):
    require(isinstance(value, dict), "expected object")
    require(set(required) <= value.keys() <= set(required) | set(optional),
            "missing/unknown keys: " + str(set(value) ^ set(required)))


def number(value):
    require(type(value) is float and math.isfinite(value), "finite binary64 number required")
    return value


def integer(value, lo, hi):
    number(value)
    require(value.is_integer() and lo <= value <= hi, "integer outside schema range")
    return int(value)


def array(value, size):
    require(isinstance(value, list) and len(value) == size, "incorrect array length")


def interval(value, lo=-math.inf, hi=math.inf):
    array(value, 2)
    a, b = map(number, value)
    require(lo <= a <= b <= hi, "invalid interval endpoints")


def vector(value):
    array(value, 3)
    for x in value:
        number(x)


def bounds3(value, limit=math.inf):
    array(value, 3)
    for x in value:
        interval(x, -limit, limit)


def ray(value):
    keys(value, {"origin", "direction", "tMin", "tMax"})
    bounds3(value["origin"], 1e6)
    bounds3(value["direction"], 1e6)
    require(0 <= number(value["tMin"]) <= number(value["tMax"]) <= 1e9,
            "invalid closed parameter domain")


def totals(value):
    keys(value, {"distance", "opticalPathLength", "throughput"})
    interval(value["distance"], 0)
    interval(value["opticalPathLength"], 0)
    interval(value["throughput"], 0, 1)


def step(value):
    keys(value, {"type", "shape", "branch", "nextIndex", "tMin", "tMax"})
    kind = integer(value["type"], 0, 2)
    integer(value["branch"], 0, 1)
    interval(value["nextIndex"], 1e-6, 1e6)
    require(0 <= number(value["tMin"]) <= number(value["tMax"]) <= 1e9,
            "invalid step parameter domain")
    shape = value["shape"]
    if kind == 0:
        keys(shape, {"center", "normal", "apertureRadius"})
        vector(shape["center"])
        vector(shape["normal"])
        require(1e-6 <= number(shape["apertureRadius"]) <= 1e6, "invalid aperture")
    elif kind == 1:
        keys(shape, {"center", "radius"})
        vector(shape["center"])
        require(1e-6 <= number(shape["radius"]) <= 1e6, "invalid sphere radius")
    else:
        keys(shape, {"vertex", "axis", "signedRadius", "apertureRadius"})
        vector(shape["vertex"])
        vector(shape["axis"])
        require(1e-6 <= number(shape["apertureRadius"]) <= abs(number(shape["signedRadius"])) <= 1e6,
                "invalid cap radius/aperture")


def same(actual, expected, label):
    require(actual == expected, "fixture identity mismatch: " + label)


def disk(z, branch=1, index=1, aperture=10, x=0):
    return {"type": 0, "shape": {"center": [x, 0, z], "normal": [0, 0, 1], "apertureRadius": aperture},
            "branch": branch, "nextIndex": [index, index], "tMin": 0, "tMax": 100}


def identity(name, value):
    """Fix the physical experiment assumed by each independent formula."""
    origin, direction, index, wavelength = [[0, 0], [0, 0], [-1, -1]], [0, 0, 1], 1, 550e-9
    settings = {"maximumSteps": 64, "maximumParameterWidth": 1e6, "maxSqrtRefinements": 128}
    steps = [disk(0, index=1.5), disk(.25), disk(1.25)]
    if name == "ghost":
        steps = [disk(0, index=1.5), disk(.25, 0), disk(0, 0), disk(.25), disk(1.25)]
    elif name == "brewster":
        direction, index = [3, 0, 4], 4
        steps = [disk(0, index=3), disk(.25, index=4), disk(1.25, index=4)]
    elif name == "index-family":
        steps[0]["nextIndex"] = [1.4, 1.6]
    elif name == "dispersion":
        wavelength = 2**-20
        phase = value["steps"][0]["nextIndex"]
        require(F.from_float(phase[0]) <= F(401, 256) <= F.from_float(phase[1]), "Cauchy phase lost")
        require(0 < phase[1] - phase[0] < 1e-12, "Cauchy enclosure replaced or excessively wide")
        steps[0]["nextIndex"] = phase
    elif name == "miss":
        steps[0] = disk(0, index=1.5, aperture=1, x=100)
    elif name in {"sphere-reflection", "cap-reflection", "sqrt-budget"}:
        shape = {"center": [0, 0, 1], "radius": 1}
        kind = 1
        if name == "cap-reflection":
            kind, shape = 2, {"vertex": [0, 0, 0], "axis": [0, 0, 1], "signedRadius": 1, "apertureRadius": .5}
        first = {"type": kind, "shape": shape, "branch": 0, "nextIndex": [1.5, 1.5], "tMin": 0, "tMax": 100}
        steps = [first, disk(-2)]
        if name == "sqrt-budget":
            direction, steps = [.125, 0, 1], [first]
            settings.update(maximumParameterWidth=1e-14, maxSqrtRefinements=1)
    elif name == "TIR-unavailable":
        direction, index, steps = [4, 0, 3], 1.5, [disk(0)]
    elif name == "self-boundary":
        steps = [disk(0), disk(0)]
    elif name == "step-budget":
        settings["maximumSteps"] = 1
    elif name == "continuation-range":
        origin, direction = [[1e6, 1e6], [0, 0], [0, 0]], [1, 0, 0]
        steps = [{"type": 1, "shape": {"center": [1e6, 0, 0], "radius": 1},
                  "branch": 1, "nextIndex": [1, 1], "tMin": 0, "tMax": 100}]
    elif name == "critical":
        direction, index, steps = [3, 0, 4], 5, [disk(0, index=3)]
    elif name == "uncertain-source":
        origin[2], steps = [-1e-12, 1e-12], [disk(0)]
    same(value, {"ray": {"origin": origin, "direction": [[x, x] for x in direction], "tMin": 0, "tMax": 100},
                 "index": [index, index], "wavelength": wavelength, "settings": settings, "steps": steps}, name)


def schema(fixture):
    keys(fixture, {"name", "input", "result"})
    require(type(fixture["name"]) is str and fixture["name"] in NAMES, "unknown fixture name")
    inp, result = fixture["input"], fixture["result"]
    keys(inp, {"ray", "index", "wavelength", "settings", "steps"})
    ray(inp["ray"])
    interval(inp["index"], 1e-6, 1e6)
    require(number(inp["wavelength"]) > 0, "invalid wavelength")
    keys(inp["settings"], {"maximumSteps", "maximumParameterWidth", "maxSqrtRefinements"})
    integer(inp["settings"]["maximumSteps"], 1, 64)
    integer(inp["settings"]["maxSqrtRefinements"], 1, 256)
    require(0 < number(inp["settings"]["maximumParameterWidth"]) <= 1e6, "invalid width budget")
    require(isinstance(inp["steps"], list) and 1 <= len(inp["steps"]) <= 64, "invalid fixture itinerary length")
    for s in inp["steps"]:
        step(s)
    identity(fixture["name"], inp)
    keys(result, {"status", "completedSteps", "failedStep", "segments"}, {"completion"})
    status = integer(result["status"], 0, 7)
    completed = integer(result["completedSteps"], 0, len(inp["steps"]))
    cursor = integer(result["failedStep"], 0, len(inp["steps"]))
    require(isinstance(result["segments"], list), "segments array required")
    require(completed <= len(result["segments"]) <= min(completed + 1, len(inp["steps"])), "invalid prefix size")
    same(cursor, completed, "fixture completion cursor")
    current, incoming = inp["index"], inp["ray"]
    for j, segment in enumerate(result["segments"]):
        keys(segment, {"incoming", "incidentIndex", "otherIndex", "branch", "geometryStatus", "geometryReason", "sqrtRefinements"},
             {"parameter", "distance", "hit", "normal", "interfaceKind", "interfaceReason", "interfaceSqrtRefinements", "outgoing", "factor", "accumulated"})
        s = inp["steps"][j]
        ray(segment["incoming"])
        same(segment["incoming"], {**incoming, "tMin": s["tMin"], "tMax": s["tMax"]}, "incoming ray")
        interval(segment["incidentIndex"], 1e-6, 1e6)
        interval(segment["otherIndex"], 1e-6, 1e6)
        same(segment["incidentIndex"], current, "current medium")
        same(segment["otherIndex"], s["nextIndex"], "other medium")
        same(integer(segment["branch"], 0, 1), int(s["branch"]), "branch")
        geometry = integer(segment["geometryStatus"], 0, 2)
        integer(segment["geometryReason"], 0, 14)
        integer(segment["sqrtRefinements"], 0, 32768)
        hit_keys = {"parameter", "distance", "hit", "normal"}
        require((hit_keys <= segment.keys()) if geometry == 0 else hit_keys.isdisjoint(segment), "inconsistent geometry hit fields")
        if geometry == 0:
            interval(segment["parameter"], 0, 1e9)
            interval(segment["distance"], 0)
            bounds3(segment["hit"])
            bounds3(segment["normal"])
        iface_keys = {"interfaceKind", "interfaceReason", "interfaceSqrtRefinements"}
        require(iface_keys <= segment.keys() or iface_keys.isdisjoint(segment), "partial interface schema")
        if "interfaceKind" in segment:
            require(geometry == 0, "interface without geometry hit")
            integer(segment["interfaceKind"], 0, 2)
            integer(segment["interfaceReason"], 0, 14)
            integer(segment["interfaceSqrtRefinements"], 0, 32768)
        if "factor" in segment:
            require("interfaceKind" in segment and segment["interfaceKind"] != 2, "power without resolved interface")
            interval(segment["factor"], 0, 1)
        if "outgoing" in segment:
            ray(segment["outgoing"])
            require("factor" in segment and geometry == 0, "outgoing without resolved hit/power")
            same(segment["outgoing"]["origin"], segment["hit"], "spawn box retention")
        require(("accumulated" in segment) == (j < completed), "failed step leaks completed totals")
        if j < completed:
            require("outgoing" in segment, "completed segment lacks outgoing ray")
            totals(segment["accumulated"])
            incoming = segment["outgoing"]
            if s["branch"] == 1:
                current = s["nextIndex"]
    require(("completion" in result) == (status == 0), "final data on failed route or absent on completion")
    if status == 0:
        same(completed, len(inp["steps"]), "completed itinerary length")
        keys(result["completion"], {"ray", "index", "totals"})
        ray(result["completion"]["ray"])
        interval(result["completion"]["index"], 1e-6, 1e6)
        totals(result["completion"]["totals"])
        same(result["completion"]["ray"], incoming, "final ray")
        same(result["completion"]["index"], current, "final medium")
        same(result["completion"]["totals"], result["segments"][-1]["accumulated"], "final totals")


def no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "duplicate JSON object key: " + key)
        obj[key] = value
    return obj


def load(path):
    def invalid_constant(value):
        raise ValueError("nonstandard JSON constant: " + value)
    with Path(path).open(encoding="utf-8-sig") as stream:
        packet = json.load(stream, parse_int=float, parse_float=float,
                           parse_constant=invalid_constant, object_pairs_hook=no_duplicates)
    keys(packet, {"fixtures"})
    require(isinstance(packet["fixtures"], list) and len(packet["fixtures"]) == 15, "exactly 15 fixtures required")
    names = [f.get("name") if isinstance(f, dict) else None for f in packet["fixtures"]]
    require(all(type(x) is str for x in names), "fixture name must be a string")
    require(len(set(names)) == 15 and set(names) == NAMES, "fixture names must be complete and unique")
    for fixture in packet["fixtures"]:
        schema(fixture)
    return packet


def analytic(packet):
    count = 0

    def bound(bounds, value):
        nonlocal count
        count += 1
        require(F.from_float(bounds[0]) <= value <= F.from_float(bounds[1]),
                "rational value outside enclosure: " + str(value) + " in " + str(bounds))

    def box(bounds, values):
        for endpoint, value in zip(bounds, values):
            bound(endpoint, F(value))

    def total(fixture, ds, opl, low, high=None):
        completion = fixture["result"]["completion"]
        t = completion["totals"]
        bound(t["distance"], F(ds))
        bound(t["opticalPathLength"], F(opl))
        bound(t["throughput"], F(low))
        if high is not None:
            bound(t["throughput"], F(high))
        return completion

    cases = {f["name"]: f for f in packet["fixtures"]}
    c = total(cases["direct"], F(9, 4), F(19, 8), F(576, 625))
    box(c["ray"]["origin"], [0, 0, F(5, 4)])
    box(c["ray"]["direction"], [0, 0, 1])
    c = total(cases["ghost"], F(11, 4), F(25, 8), F(576, 390625))
    box(c["ray"]["origin"], [0, 0, F(5, 4)])
    c = total(cases["brewster"], F(35, 12), F(45, 4), F(331776, 390625), F(1))
    box(c["ray"]["origin"], [F(11, 6), 0, F(5, 4)])
    box(c["ray"]["direction"], [F(3, 5), 0, F(4, 5)])
    segments = cases["brewster"]["result"]["segments"]
    box(segments[0]["outgoing"]["direction"], [F(4, 5), 0, F(3, 5)])
    box(segments[1]["hit"], [F(13, 12), 0, F(1, 4)])
    for j, (ds, opl) in enumerate([(F(5, 4), F(5)), (F(5, 3), F(25, 4)), (F(35, 12), F(45, 4))]):
        bound(segments[j]["accumulated"]["distance"], ds)
        bound(segments[j]["accumulated"]["opticalPathLength"], opl)
    for name in ["index-family", "dispersion"]:
        fixture = cases[name]
        n = fixture["input"]["steps"][0]["nextIndex"]
        ns = [F.from_float(n[0]), F.from_float(n[1]), (F.from_float(n[0]) + F.from_float(n[1])) / 2]
        if name == "dispersion":
            ns.append(F(401, 256))
        for n in ns:
            total(fixture, F(9, 4), F(2) + n / 4, F(16) * n * n / (1 + n)**4)
    for name in ["sphere-reflection", "cap-reflection"]:
        total(cases[name], F(3), F(3), F(1, 25))
    for name, status in [("miss", 1), ("TIR-unavailable", 4), ("step-budget", 6),
                         ("continuation-range", 7), ("critical", 3), ("uncertain-source", 2), ("sqrt-budget", 6)]:
        same(cases[name]["result"]["status"], status, name + " failure classification")
        require("completion" not in cases[name]["result"], "failure leaks final totals")
    total(cases["self-boundary"], F(1), F(1), F(1))
    same(cases["self-boundary"]["result"]["segments"][1]["parameter"], [0, 0], "explicit source t=0")
    return count


def parity(native, wasm):
    numeric = 0

    def compare(a, b, path=""):
        nonlocal numeric
        require(type(a) is type(b), "parity type mismatch " + path)
        if isinstance(a, dict):
            same(a.keys(), b.keys(), "parity keys " + path)
            for key in a:
                compare(a[key], b[key], path + "/" + key)
        elif isinstance(a, list):
            same(len(a), len(b), "parity array " + path)
            for j, (x, y) in enumerate(zip(a, b)):
                compare(x, y, path + "/" + str(j))
        elif type(a) is float:
            numeric += 1
            require(struct.pack(">d", a) == struct.pack(">d", b), "binary64 parity mismatch " + path)
        else:
            same(a, b, "parity value " + path)
    # Fixture order is not physical identity. Match the independently fixed names.
    compare({f["name"]: f for f in native["fixtures"]}, {f["name"]: f for f in wasm["fixtures"]})
    return numeric


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", help="Native --fixtures JSON (required)")
    parser.add_argument("wasm", nargs="?", help="optional standalone WASM --fixtures JSON; exact binary64 comparison")
    args = parser.parse_args()
    native = load(args.native)
    report = {"fixtures": 15, "nativeRationalInclusions": analytic(native), "status": "PASS",
              "limits": "Independent finite rational reference cases; not a whole-family proof or automatic-world optical trace."}
    if args.wasm:
        wasm = load(args.wasm)
        report["wasmRationalInclusions"] = analytic(wasm)
        report["binary64ParityNumbers"] = parity(native, wasm)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, KeyError, IndexError, OSError, OverflowError) as error:
        raise SystemExit("FAIL optical route verification: " + str(error)) from error
