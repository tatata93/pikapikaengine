"""Exact Fraction minima and negative-witness checks for the 640-row corpus.

Binary64 hex is decoded with integers/Fraction. Row identity is the implicit
(type, ordinal) emitted by the Native --oracle CLI; no sampling proves safety.
"""
import argparse
import csv
from fractions import Fraction as F
import json
from pathlib import Path
import struct

if not __debug__:
    raise SystemExit("Python -O is rejected: proof checks must not be disabled")

HEADER = "type,x0,y0,x1,y1,vx,vy,dt,r1,r2,tol,status,witness,predicateLo,predicateHi".split(",")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def decode(text):
    require(len(text) == 16 and all(c in "0123456789abcdef" for c in text), "expected exactly 16 lowercase binary64 hex digits")
    bits = int(text, 16)
    sign = -1 if bits >> 63 else 1
    exponent, mantissa = (bits >> 52) & 2047, bits & ((1 << 52) - 1)
    require(exponent != 2047, "nonfinite binary64 input/output")
    if exponent:
        mantissa |= 1 << 52
    return sign * F(mantissa) * F(2)**(exponent - 1023 - 52 if exponent else -1074)


def encode(value):
    return struct.pack(">d", value).hex()


def expected_inputs(kind, k):
    # Match the original binary64 experiment inputs, not rounded polynomial
    # coefficients. All geometry recipes are dyadic except the given dt/divide.
    dt = 1 / 120 if kind != "C" and k % 3 == 0 else 1 / 64
    tolerance, good = 1 / 1024, k % 2 == 0
    target = 1 + (k + 1) / 512 if good else .5 + (k + 1) / 2048
    start = k / 256 + 1
    if kind in {"P", "Q"}:
        values = [0., target + start, 0., target + start, 0., -4 * start / dt]
    elif kind == "L":
        values = [-start, target, start, target, 2 * start / dt, 0.]
    else:
        b = (k // 2 + 1) / 1024
        b2 = b * b
        b4 = b2 * b2
        c = b2 / 2 + b4 / 8
        tolerance = b4 / 4 if good else b4 / 128
        values = [0., 1., b, 1 - c, b / dt, 0.]
    return [encode(x) for x in values + [dt, 1. if kind == "P" else .5, 0. if kind == "P" else .5, tolerance]]


def value(poly, parameter):
    a, b, c = poly
    return a + parameter * (b + parameter * c)


def minimum_quadratic(poly):
    a, b, c = poly
    result = min(a, a + b + c)
    if c > 0:
        parameter = -b / (2 * c)
        if 0 < parameter < 1:
            result = min(result, value(poly, parameter))
    return result


def verify(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        packet = list(csv.reader(stream, strict=True))
    require(len(packet) == 641, "expected one header plus exactly 640 rows")
    require(packet[0] == HEADER, "oracle header mismatch")
    counts = {"safe": 0, "witness": 0}
    identities = set()
    for ordinal, row in enumerate(packet[1:]):
        require(len(row) == len(HEADER), "row length mismatch at " + str(ordinal))
        kind, k = "PLQC"[ordinal // 160], ordinal % 160
        require(row[0] == kind, "type/block identity mismatch at " + str(ordinal))
        require(row[1:11] == expected_inputs(kind, k), "input/implicit ordinal identity mismatch at " + str(ordinal))
        identity = tuple(row[:11])
        require(identity not in identities, "duplicate corpus input identity")
        identities.add(identity)
        x0, y0, x1, y1, vx, vy, dt, r1, r2, tolerance = map(decode, row[1:11])
        witness, lower, upper = map(decode, row[12:15])
        require(lower <= upper, "reversed predicate bounds")
        require(0 <= witness <= 1, "witness parameter outside [0,1]")
        require(0 < dt <= F(1, 10) and r1 > 0 and r2 >= 0 and 0 <= tolerance < r1, "invalid oracle domain")
        x = (x0, dt * vx, x1 - x0 - dt * vx)
        y = (y0, dt * vy, y1 - y0 - dt * vy)
        radius = r1 + r2 - tolerance
        require(radius > 0, "nonpositive clearance radius")
        if kind == "P":
            require(x == (0, 0, 0) and r1 == 1 and r2 == 0, "plane corpus shape")
            exact_minimum = minimum_quadratic(y) - radius
        elif kind == "Q":
            require(x == (0, 0, 0), "axial sphere corpus shape")
            minimum_y = minimum_quadratic(y)
            require(minimum_y > 0, "axial positive-side proof unavailable")
            exact_minimum = minimum_y**2 - radius**2
        elif kind == "L":
            require(x[0] < 0 and sum(x) > 0 and y[1] == y[2] == 0, "crossing corpus shape")
            # x=0 exists by continuity. Constant y makes this the true minimum,
            # even when rounded dt*v makes x(s) slightly quadratic.
            exact_minimum = y[0]**2 - radius**2
        else:
            require(x[0] == x[2] == y[1] == 0, "curved corpus shape")
            # Squared distance is quadratic in z=s^2, which covers [0,1].
            exact_minimum = minimum_quadratic((y[0]**2 - radius**2,
                x[1]**2 + 2 * y[0] * y[2], y[2]**2))
        expected = "safe" if exact_minimum >= 0 else "witness"
        require(row[11] == expected, "exact classification mismatch at " + str(ordinal))
        counts[expected] += 1
        if expected == "witness":
            actual = value(x, witness)**2 + value(y, witness)**2 - radius**2
            if kind == "P":
                require(value(y, witness) >= 0, "plane squared witness lacks positive-side proof")
            require(lower <= actual <= upper < 0, "negative witness enclosure mismatch at " + str(ordinal))
        else:
            require(row[12:] == ["0000000000000000"] * 3, "safe diagnostic fields must be cleared")
    require(counts == {"safe": 320, "witness": 320}, "corpus classification totals")
    return {"status": "PASS", "cases": 640, "uniqueInputIdentities": len(identities),
            "classifications": counts, "negativeWitnessEnclosures": 320,
            "limits": "Exact minima for this fixed 2D-section binary64 corpus, not arbitrary mechanical continuous-flow enclosures."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", help="trajectory_guard --oracle CSV")
    parser.add_argument("wasm", nargs="?", help="optional standalone WASM oracle CSV; independently checked too")
    args = parser.parse_args()
    report = verify(args.native)
    if args.wasm:
        report["wasm"] = verify(args.wasm)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, OverflowError, csv.Error) as error:
        raise SystemExit("FAIL trajectory guard verification: " + str(error)) from error
