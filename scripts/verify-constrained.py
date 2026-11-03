"""Fail-closed validation of the 14 explicit normal RATTLE experiments.

Native --fixtures JSON is required; optional standalone WASM JSON is checked
independently and compared. JSON numbers have binary64 semantics. The 39 finite
analytic/convergence references do not prove a continuous-solution enclosure.
"""
import argparse
import json
import math
from pathlib import Path
import struct

if not __debug__:
    raise SystemExit("Python -O is rejected: proof checks must not be disabled")

NAMES = {"floor", "stack", "wedge", "curve", "unequal", "release", "singular",
         "newton-budget", "linear-budget", "empty-active", "moving-coupled",
         "contact-budget", "normal-rotation", "equation-residual"}
FAILURES = {"release": 10, "singular": 5, "newton-budget": 6, "linear-budget": 7,
            "contact-budget": 13, "normal-rotation": 9, "equation-residual": 11}


def require(ok, text):
    if not ok:
        raise ValueError(text)


def keys(value, required):
    require(isinstance(value, dict) and value.keys() == set(required), "missing/unknown object keys")


def number(value):
    require(type(value) is float and math.isfinite(value), "finite binary64 number required")
    return value


def integer(value, lo, hi):
    number(value)
    require(value.is_integer() and lo <= value <= hi, "integer outside schema range")
    return int(value)


def vector(value, size=3, limit=math.inf):
    require(isinstance(value, list) and len(value) == size, "vector length")
    for x in value:
        require(abs(number(x)) <= limit, "vector domain")


def bounds(value):
    vector(value, 2)
    require(value[0] <= value[1], "reversed interval")


def same(a, b, text):
    require(a == b, "identity/consistency mismatch: " + text)


def physical_identity(actual, expected, path="input"):
    """Reject bool-as-number and preserve the specified binary64 input bits."""
    if isinstance(expected, dict):
        keys(actual, expected)
        for key in expected:
            physical_identity(actual[key], expected[key], path + "/" + key)
    elif isinstance(expected, list):
        require(type(actual) is list and len(actual) == len(expected), "input array schema " + path)
        for j, (a, b) in enumerate(zip(actual, expected)):
            physical_identity(a, b, path + "/" + str(j))
    elif type(expected) is bool:
        require(type(actual) is bool and actual == expected, "input boolean identity " + path)
    else:
        number(actual)
        require(struct.pack(">d", actual) == struct.pack(">d", float(expected)), "binary64 physical input identity " + path)


def sphere(identifier, position=(0, 0, 0), mass=1, static=False, velocity=(0, 0, 0), force=(0, 0, 0), torque=(0, 0, 0)):
    inertia = .4 * mass * .5 * .5
    return {"id": identifier, "isStatic": static, "mass": mass, "radius": .5,
            "inertia": [inertia] * 3, "position": list(position), "velocity": list(velocity),
            "angularMomentum": [0, 0, 0], "orientation": [0, 0, 0, 1],
            "force": list(force), "torque": list(torque), "material": {"restitution": 0, "friction": .6}}


def plane(identifier=100, normal=(0, 1, 0), offset=0):
    return {"id": identifier, "normal": list(normal), "offset": offset, "material": {"restitution": 0, "friction": .6}}


def experiment(name):
    settings = {"initialGapTolerance": 1e-8, "initialVelocityTolerance": 1e-8,
                "positionTolerance": 1e-10, "velocityTolerance": 1e-10,
                "positionEquationTolerance": 1e-10, "velocityEquationTolerance": 1e-10,
                "minimumScaledPivot": 1e-10, "maximumNormalRotation": .5,
                "maximumImpulse": 1e24, "maximumAngularIncrement": .5,
                "maxNewtonIterations": 32, "maxLinearSolves": 64,
                "maxLineSearchSteps": 16, "maxContacts": 128}
    world = {"gravity": [0, -10, 0], "bodies": [sphere(1, (0, .5, 0), force=(2, 0, 0), torque=(0, 0, 2))], "planes": [plane()]}
    dt, active = .02, [[100, 1]]
    if name in {"floor", "equation-residual"}:
        dt = .05
    if name == "stack":
        world["bodies"] = [sphere(j + 1, (0, .5 + j, 0), j + 1,
             force=(2 * (j + 1), [5, -4, 7][j], 0)) for j in range(3)]
        active = [[100, 1], [1, 2], [2, 3]]
    elif name in {"wedge", "contact-budget"}:
        world["bodies"] = [sphere(1, force=(-6, 0, 0))]
        world["planes"] = [plane(offset=-.5), plane(101, (.6, .8, 0), -.5)]
        active = [[100, 1], [101, 1]]
    elif name in {"curve", "newton-budget", "normal-rotation"}:
        world = {"gravity": [0, -4, 0], "bodies": [sphere(1, (0, 1, 0), velocity=(1, 0, 0)), sphere(2, static=True)], "planes": []}
        active, dt = [[1, 2]], .1 if name == "newton-budget" else .05
    elif name == "unequal":
        world = {"gravity": [0, -4, 0], "bodies": [sphere(1, velocity=(-2 / 3, 0, 0), force=(0, 2, 0)), sphere(2, (0, 1, 0), 2, velocity=(1 / 3, 0, 0), force=(0, -2, 0))], "planes": []}
        dt, active = .05, [[1, 2]]
    elif name == "release":
        world["bodies"][0]["force"] = [0, 12, 0]
    elif name == "singular":
        world["planes"].append(plane(101))
        active = [[100, 1], [101, 1]]
    elif name == "empty-active":
        active = []
    elif name == "moving-coupled":
        world = {"gravity": [0, 0, 0], "bodies": [sphere(1, force=(0, 2, 0)), sphere(2, (1, 0, 0), velocity=(0, 1, 0), force=(-4, 0, 0)), sphere(3, (0, 1, 0), static=True)], "planes": []}
        dt, active = .05, [[1, 2], [1, 3]]
    if name == "newton-budget":
        settings["maxNewtonIterations"] = 1
    elif name == "linear-budget":
        settings["maxLinearSolves"] = 1
    elif name == "contact-budget":
        settings["maxContacts"] = 1
    elif name == "normal-rotation":
        settings["maximumNormalRotation"] = .001
    elif name == "equation-residual":
        settings["positionEquationTolerance"] = 1e-25
    return {"world": world, "dt": dt, "active": active, "settings": settings}


BODY_KEYS = set(sphere(1))
RESIDUAL_KEYS = {"initialGap", "initialNormalVelocity", "finalGap", "finalNormalVelocity", "positionEquation", "velocityEquation", "maximumNormalRotation", "minimumScaledPivot"}


def body(value):
    keys(value, BODY_KEYS)
    integer(value["id"], 1, 2**53 - 1)
    require(type(value["isStatic"]) is bool, "static flag must be boolean")
    require(1e-12 <= number(value["mass"]) <= 1e18 and 0 < number(value["radius"]) <= 1e9, "mass/radius domain")
    for name in ["inertia", "position", "velocity", "angularMomentum", "force", "torque"]:
        vector(value[name])
    vector(value["orientation"], 4)
    require(abs(sum(x * x for x in value["orientation"]) - 1) < 1e-8, "quaternion norm")
    keys(value["material"], {"restitution", "friction"})
    require(0 <= number(value["material"]["restitution"]) <= 1 and 0 <= number(value["material"]["friction"]) <= 10, "material domain")


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def discrete_consistency(inp, result):
    """Check all translational DOFs against the nominal discrete equations.

    This float recomputation is a consistency check, not the C++ interval audit
    or an independent continuous-solution proof.
    """
    h, gravity, settings = inp["dt"], inp["world"]["gravity"], inp["settings"]
    initial = {b["id"]: b for b in inp["world"]["bodies"]}
    end = {b["id"]: b for b in result["candidateBodies"]}
    impulses = {identifier: [[0.] * 3, [0.] * 3] for identifier in initial}
    for c in result["constraints"]:
        for stage, normal, impulse in [(0, c["normal0"], c["P0"]), (1, c["normal1"], c["P1"])]:
            for identifier, sign in [(c["firstId"], -1), (c["secondId"], 1)]:
                if identifier in impulses:
                    for k in range(3):
                        impulses[identifier][stage][k] += sign * normal[k] * impulse
    for identifier, a in initial.items():
        z = end[identifier]
        for key in ["id", "isStatic", "mass", "radius", "inertia", "force", "torque", "material"]:
            same(z[key], a[key], "retained body metadata/load")
        if a["isStatic"]:
            same(z, a, "static candidate unchanged")
            continue
        for k in range(3):
            acc = gravity[k] + a["force"][k] / a["mass"]
            half = a["velocity"][k] + h * .5 * acc + impulses[identifier][0][k] / a["mass"]
            q = a["position"][k] + h * half
            v = half + h * .5 * acc + impulses[identifier][1][k] / a["mass"]
            require(abs(z["position"][k] - q) <= settings["positionEquationTolerance"] + 1e-12 * max(1, abs(q)), "candidate position equation")
            require(abs(z["velocity"][k] - v) <= settings["velocityEquationTolerance"] + 1e-12 * max(1, abs(v)), "candidate velocity equation")
            expected_l = a["angularMomentum"][k] + h * a["torque"][k]
            require(abs(z["angularMomentum"][k] - expected_l) <= 1e-12 * max(1, abs(expected_l)), "held torque equation")


def schema(fixture):
    keys(fixture, {"name", "input", "result", "worldUnchanged"})
    name = fixture["name"]
    require(type(name) is str and name in NAMES, "unknown fixture name")
    require(fixture["worldUnchanged"] is True, "read-only result flag")
    physical_identity(fixture["input"], experiment(name), name + "/input")
    inp, r = fixture["input"], fixture["result"]
    for b in inp["world"]["bodies"]:
        body(b)
    keys(r, {"success", "failure", "message", "newtonIterations", "linearSolves", "lineSearchTrials", "geometryEvaluations", "residuals", "constraints", "releasePairs", "candidateBodies"})
    require(type(r["success"]) is bool and type(r["message"]) is str and len(r["message"]) <= 1024, "result flag/message schema")
    expected = FAILURES.get(name, 0)
    same(integer(r["failure"], 0, 13), expected, name + " failure classification")
    same(r["success"], expected == 0, name + " success classification")
    s = inp["settings"]
    newton = integer(r["newtonIterations"], 0, int(s["maxNewtonIterations"]))
    integer(r["linearSolves"], 0, int(s["maxLinearSolves"]))
    line = integer(r["lineSearchTrials"], 0, newton * int(s["maxLineSearchSteps"]))
    integer(r["geometryEvaluations"], 0, len(inp["active"]) * (3 + line))
    keys(r["residuals"], RESIDUAL_KEYS)
    for value in r["residuals"].values():
        require(number(value) >= 0, "negative residual")
    require(r["residuals"]["minimumScaledPivot"] <= 1, "scaled pivot report range")
    for key in ["constraints", "releasePairs", "candidateBodies"]:
        require(isinstance(r[key], list), "result array schema")
    require(len(r["constraints"]) in {0, len(inp["active"])}, "partial constraint diagnostics")
    for j, constraint in enumerate(r["constraints"]):
        keys(constraint, {"firstId", "secondId", "normal0", "normal1", "gap0", "gap1", "vn0", "vn1", "P0", "P1"})
        same([constraint["firstId"], constraint["secondId"]], inp["active"][j], "constraint pair/order")
        for key in ["firstId", "secondId"]:
            integer(constraint[key], 1, 2**53 - 1)
        for key in ["normal0", "normal1"]:
            vector(constraint[key])
            require(abs(dot(constraint[key], constraint[key]) - 1) < 1e-8, "nominal normal norm")
        for key in ["gap0", "gap1", "vn0", "vn1"]:
            bounds(constraint[key])
        for key in ["P0", "P1"]:
            require(abs(number(constraint[key])) <= s["maximumImpulse"], "stage impulse domain")
    releases = set()
    for pair in r["releasePairs"]:
        vector(pair, 2)
        require(pair in inp["active"] and tuple(pair) not in releases, "invalid/duplicate release ID")
        releases.add(tuple(pair))
    if expected == 10:
        negatives = {(c["firstId"], c["secondId"]) for c in r["constraints"] if min(c["P0"], c["P1"]) < 0}
        require(bool(negatives) and releases == negatives, "missing negative signed multiplier/release pair")
    else:
        require(not releases, "unexpected release IDs")
    if r["success"]:
        same(len(r["constraints"]), len(inp["active"]), "successful constraint count")
        same(len(r["candidateBodies"]), len(inp["world"]["bodies"]), "candidate count")
        require(all(c["P0"] >= 0 and c["P1"] >= 0 for c in r["constraints"]), "successful tensile stage")
        for metric, limit in [("finalGap", "positionTolerance"), ("finalNormalVelocity", "velocityTolerance"), ("positionEquation", "positionEquationTolerance"), ("velocityEquation", "velocityEquationTolerance")]:
            require(r["residuals"][metric] <= s[limit], "successful residual budget")
        for b in r["candidateBodies"]:
            body(b)
        same([b["id"] for b in r["candidateBodies"]], [b["id"] for b in inp["world"]["bodies"]], "candidate IDs/order")
        discrete_consistency(inp, r)
    else:
        require(not r["candidateBodies"], "failure leaks candidate state")


def unique_keys(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "duplicate JSON key: " + key)
        obj[key] = value
    return obj


def load(path):
    def constant(value):
        raise ValueError("nonstandard JSON constant: " + value)
    with Path(path).open(encoding="utf-8-sig") as stream:
        packet = json.load(stream, parse_int=float, parse_float=float, parse_constant=constant, object_pairs_hook=unique_keys)
    keys(packet, {"version", "model", "fixtures", "convergence"})
    same(integer(packet["version"], 1, 1), 1, "version")
    same(packet["model"], "normal-only RATTLE candidate segment; explicit active set", "model")
    require(isinstance(packet["fixtures"], list) and len(packet["fixtures"]) == 14, "exactly 14 fixtures required")
    names = [f.get("name") if isinstance(f, dict) else None for f in packet["fixtures"]]
    require(all(type(n) is str for n in names) and set(names) == NAMES and len(set(names)) == 14, "complete unique fixture identities required")
    for f in packet["fixtures"]:
        schema(f)
    require(isinstance(packet["convergence"], list) and len(packet["convergence"]) == 3, "three refinement levels required")
    for j, metric in enumerate(packet["convergence"]):
        keys(metric, {"steps", "h", "positionError", "velocityError", "maximumEnergyError", "angularBalance", "maximumGap", "maximumNormalVelocity"})
        same(integer(metric["steps"], 1, 1000), 10 << j, "refinement identity")
        same(number(metric["h"]), .4 / (10 << j), "refinement time step")
        for key in set(metric) - {"steps", "h"}:
            require(number(metric[key]) >= 0, "negative convergence metric")
        require(metric["angularBalance"] < 1e-12 and metric["maximumGap"] < 1e-10 and metric["maximumNormalVelocity"] < 1e-10, "curved constraint/angular residual")
        require(0 < metric["positionError"] < 5e-4 and 0 < metric["velocityError"] < 7e-4 and 0 < metric["maximumEnergyError"] < 6e-4, "curved absolute reference error")
    return packet


def analytic(packet):
    cases = {f["name"]: f for f in packet["fixtures"]}
    checks = 0
    def near(actual, expected, tolerance=1e-9):
        nonlocal checks
        checks += 1
        require(abs(actual - expected) <= tolerance, "independent reference mismatch: " + str((actual, expected)))
    r = cases["floor"]["result"]
    b = r["candidateBodies"][0]
    for actual, expected in [(b["position"][0], .0025), (b["position"][1], .5), (b["velocity"][0], .1), (b["angularMomentum"][2], .1)]:
        near(actual, expected)
    near(b["orientation"][2], math.sin(.0125), 1e-12)
    near(r["constraints"][0]["P0"], .25)
    near(r["constraints"][0]["P1"], .25)
    for j, force in enumerate([52, 47, 23]):
        r = cases["stack"]["result"]
        near(r["constraints"][j]["P0"], force * .01)
        near(r["constraints"][j]["P1"], force * .01)
        near(r["candidateBodies"][j]["position"][1], .5 + j)
        near(r["candidateBodies"][j]["velocity"][0], .04)
    for j, force in enumerate([2, 10]):
        near(cases["wedge"]["result"]["constraints"][j]["P0"], force * .01)
        near(cases["wedge"]["result"]["constraints"][j]["P1"], force * .01)
    h = cases["curve"]["input"]["dt"]
    y = math.sqrt(1 - h * h)
    p0 = h * (2 - 1 / (1 + y))
    p1 = h * (4 * y - 1) - y * p0
    r = cases["curve"]["result"]
    near(r["constraints"][0]["P0"], p0, 1e-10)
    near(r["constraints"][0]["P1"], p1, 1e-10)
    near(r["candidateBodies"][0]["position"][0], h)
    near(r["candidateBodies"][0]["position"][1], y)
    a, b = cases["unequal"]["result"]["candidateBodies"]
    h = cases["unequal"]["input"]["dt"]
    for k, reference in enumerate([0, 2 / 3 - 2 * h * h, 0]):
        near((a["position"][k] + 2 * b["position"][k]) / 3, reference)
    for k, reference in enumerate([0, -12 * h, 0]):
        near(a["velocity"][k] + 2 * b["velocity"][k], reference)
    for key in ["positionError", "velocityError", "maximumEnergyError"]:
        values = [level[key] for level in packet["convergence"]]
        for a, b in zip(values, values[1:]):
            checks += 1
            require(3.7 < a / b < 4.3, "second-order refinement trend: " + key)
    same(checks, 39, "independent reference coverage")
    return checks


def compare(native, wasm):
    counters = {"failure", "newtonIterations", "linearSolves", "lineSearchTrials", "geometryEvaluations", "id", "firstId", "secondId", "steps", "version"}
    numbers = bits = exact = 0
    maximum = normalized = 0.
    def visit(a, b, path=""):
        nonlocal numbers, bits, exact, maximum, normalized
        require(type(a) is type(b), "parity type mismatch " + path)
        if isinstance(a, dict):
            same(a.keys(), b.keys(), "parity keys " + path)
            for key in a:
                visit(a[key], b[key], path + "/" + key)
        elif isinstance(a, list):
            same(len(a), len(b), "parity length " + path)
            for j, (x, y) in enumerate(zip(a, b)):
                visit(x, y, path + "/" + str(j))
        elif type(a) is float:
            numbers += 1
            bits += struct.pack(">d", a) == struct.pack(">d", b)
            error, scale = abs(a - b), max(1, abs(a), abs(b))
            maximum, normalized = max(maximum, error), max(normalized, error / scale)
            if path.split("/")[-1] in counters:
                same(a, b, "parity counter/enum " + path)
                exact += 1
            else:
                require(error <= 1e-11 + 1e-10 * scale, "numeric parity mismatch " + path)
        else:
            same(a, b, "parity value " + path)
    a, b = dict(native), dict(wasm)
    a["fixtures"] = {f["name"]: f for f in native["fixtures"]}
    b["fixtures"] = {f["name"]: f for f in wasm["fixtures"]}
    visit(a, b)
    return {"numericValues": numbers, "bitEqualNumbers": bits, "exactCountersAndIds": exact,
            "maxAbsoluteError": maximum, "maxNormalizedError": normalized}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", help="Native constrained --fixtures JSON")
    parser.add_argument("wasm", nargs="?", help="optional standalone WASM --fixtures JSON")
    args = parser.parse_args()
    native = load(args.native)
    report = {"status": "PASS", "fixtures": 14, "nativeIndependentReferenceChecks": analytic(native),
              "limits": "Finite reference cases and consistency checks; no continuous-flow enclosure, inactive CCD or automatic unilateral driver proof."}
    if args.wasm:
        wasm = load(args.wasm)
        report["wasmIndependentReferenceChecks"] = analytic(wasm)
        report["comparison"] = compare(native, wasm)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, KeyError, IndexError, OSError, OverflowError, ZeroDivisionError) as error:
        raise SystemExit("FAIL constrained verification: " + str(error)) from error
