"""Independent integer/Fraction checks; no native floating-point reference math."""
import csv
import hashlib
import json
import sys
from fractions import Fraction as Q
from pathlib import Path

if not __debug__:
    raise RuntimeError('Run without Python optimization: assertions are required')
if len(sys.argv) != 2:
    raise SystemExit('usage: verify-accelerated.py oracle.csv')

def binary64(text):
    bits = int(text, 16)
    sign = -1 if bits >> 63 else 1
    exponent = (bits >> 52) & 2047
    fraction = bits & ((1 << 52) - 1)
    if exponent == 2047:
        raise AssertionError('this bounded corpus must have finite endpoints')
    mantissa = fraction if exponent == 0 else fraction + (1 << 52)
    power = -1074 if exponent == 0 else exponent - 1023 - 52
    return sign * Q(mantissa * (1 << max(0, power)), 1 << max(0, -power))

def trajectory(s, t):
    return [s[i] + s[3+i]*t + s[6+i]*t*t/2 for i in range(3)]

def quadratic_range(c, b, a, lo, hi):
    ts = [lo, hi]
    if a and lo < -b/(2*a) < hi:
        ts.append(-b/(2*a))
    values = [c + b*t + a*t*t for t in ts]
    return min(values), max(values)

def radical_lower(bound, centre, radius, norm_squared):
    # bound <= centre - radius*sqrt(norm_squared)
    d = (centre-bound)/radius
    return d >= 0 and d*d >= norm_squared

def radical_upper(bound, centre, radius, norm_squared):
    d = (centre-bound)/radius
    return d <= 0 or d*d <= norm_squared

source = Path(sys.argv[1])
counts = dict(rows=0, point_rows=0, nonzero_time_interval_rows=0,
              exact_rational_time_checks=0, whole_plane_intervals=0,
              whole_one_axis_pair_intervals=0, sampled_3d_pair_intervals=0)
for row in csv.reader(source.read_text(encoding='ascii').splitlines()):
    kind = row[0]
    values = [binary64(x) for x in row[1:]]
    lo, hi, lower, upper = values[-4:]
    assert lo <= hi and lower <= upper
    counts['rows'] += 1
    counts['point_rows' if lo == hi else 'nonzero_time_interval_rows'] += 1
    times = [lo] if lo == hi else [lo + (hi-lo)*Q(k,8) for k in range(9)]
    if kind == 'S':
        a, b = values[:10], values[10:20]
        radius2 = (a[9]+b[9])**2
        for t in times:
            pa, pb = trajectory(a,t), trajectory(b,t)
            exact = sum((y-x)**2 for x,y in zip(pa,pb)) - radius2
            assert lower <= exact <= upper, ('pair sample', counts['rows'], t)
        moving = [i for i in range(3) if a[3+i] != b[3+i] or a[6+i] != b[6+i]]
        if len(moving) <= 1:
            axis = moving[0] if moving else 0
            rmin, rmax = quadratic_range(b[axis]-a[axis], b[3+axis]-a[3+axis], (b[6+axis]-a[6+axis])/2,lo,hi)
            constant = sum((b[i]-a[i])**2 for i in range(3) if i != axis) - radius2
            minimum = 0 if rmin <= 0 <= rmax else min(rmin*rmin,rmax*rmax)
            maximum = max(rmin*rmin,rmax*rmax)
            assert lower <= minimum+constant and maximum+constant <= upper, ('pair full range',counts['rows'])
            if lo != hi: counts['whole_one_axis_pair_intervals'] += 1
        elif lo != hi:
            counts['sampled_3d_pair_intervals'] += 1
    elif kind == 'P':
        s, n, offset = values[:10], values[10:13], values[13]
        norm2 = sum(x*x for x in n)
        for t in times:
            centre = sum(x*y for x,y in zip(n,trajectory(s,t))) - offset
            assert radical_lower(lower,centre,s[9],norm2) and radical_upper(upper,centre,s[9],norm2), ('plane sample',counts['rows'],t)
        c = sum(n[i]*s[i] for i in range(3)) - offset
        b = sum(n[i]*s[3+i] for i in range(3))
        a = sum(n[i]*s[6+i] for i in range(3))/2
        vmin,vmax = quadratic_range(c,b,a,lo,hi)
        assert radical_lower(lower,vmin,s[9],norm2) and radical_upper(upper,vmax,s[9],norm2), ('plane full range',counts['rows'])
        if lo != hi: counts['whole_plane_intervals'] += 1
    else:
        raise AssertionError(kind)
    counts['exact_rational_time_checks'] += len(times)

assert counts == dict(rows=485, point_rows=240, nonzero_time_interval_rows=245,
    exact_rational_time_checks=2445, whole_plane_intervals=202,
    whole_one_axis_pair_intervals=2, sampled_3d_pair_intervals=41), ('truncated/changed corpus',counts)
print(json.dumps(dict(result='PASS', csv_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), **counts,
    limits='General 3D quartic intervals use finite samples, not a proof of their whole range. Plane quadratic and one-axis pair extrema are independently bounded exactly.'),indent=2))
