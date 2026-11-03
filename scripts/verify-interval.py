"""Independent exact-rational containment checker; no reference float arithmetic.

Usage: verify-interval.py native.csv [wasm.csv]
Generate the corpus with pikapika_interval_tests --oracle. All reference values
are exact Fractions decoded from IEEE bits, including subnormal inputs. Infinite
OUTPUT bounds denote unbounded enclosures; input endpoints here are all finite.
This verifies containment, not tightness or a formal compiler proof.
"""
from fractions import Fraction
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError('Run the verifier without Python optimization: assertions are required')

def decode(text):
    bits = int(text, 16)
    sign = -1 if bits >> 63 else 1
    exponent = (bits >> 52) & 0x7ff
    mantissa = bits & ((1 << 52) - 1)
    if exponent == 0x7ff:
        assert mantissa == 0, 'NaN endpoint'
        return '-inf' if sign < 0 else '+inf'
    if exponent:
        mantissa += 1 << 52
        power = exponent - 1023 - 52
    else:
        power = -1074
    return sign * Fraction(mantissa * (1 << max(power, 0)), 1 << max(-power, 0))

def verify(path):
    count = 0
    for line_number, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        op, *encoded = line.split(',')
        al, ah, bl, bh, lo, hi = map(decode, encoded)
        assert all(isinstance(x, Fraction) for x in (al, ah, bl, bh)), (path, line_number, 'finite inputs')
        assert al <= ah and bl <= bh, (path, line_number, 'input order')
        if op == 's':
            lower = 0 if al <= 0 <= ah else min(al*al, ah*ah)
            upper = max(al*al, ah*ah)
        else:
            if op == '/':
                assert not bl <= 0 <= bh, (path, line_number, 'zero divisor')
            operation = {'+': lambda a,b:a+b, '-': lambda a,b:a-b,
                         '*': lambda a,b:a*b, '/': lambda a,b:a/b}[op]
            exact = [operation(a,b) for a in (al,ah) for b in (bl,bh)]
            lower, upper = min(exact), max(exact)
        assert lo == '-inf' or isinstance(lo, Fraction) and lo <= lower, (path, line_number, op, 'lower fails')
        assert hi == '+inf' or isinstance(hi, Fraction) and hi >= upper, (path, line_number, op, 'upper fails')
        count += 1
    assert count == 6829, ('oracle corpus changed or was truncated', count)
    print(f'EXACT FRACTION PASS {count} enclosures: {path}')
    return count

if __name__ == '__main__':
    assert len(sys.argv) > 1, 'usage: verify-interval.py native.csv [wasm.csv]'
    for input_path in sys.argv[1:]:
        verify(input_path)
    if len(sys.argv) == 3:
        a,b = (Path(p).read_text(encoding='utf-8-sig').splitlines() for p in sys.argv[1:])
        assert a == b, 'native/WASM output bits differ'
        print(f'NATIVE/WASM BIT PARITY PASS {len(a)} rows, {len(a)*2} endpoint values')
