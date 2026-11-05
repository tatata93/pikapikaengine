"""Independent rational binary64 clock reference for finite advance fixtures.

Uses integer quotient/remainder and ties-to-even, not native floating addition
to calculate expected sums/differences. Physics and artifact binding are separate.
"""
from fractions import Fraction
import json
from pathlib import Path
import re
import struct
import sys


def need(value, message):
    if not value:
        raise ValueError(message)


def number(bits):
    need(isinstance(bits, str) and re.fullmatch('[0-9a-f]{16}', bits), 'binary64 hex encoding')
    raw = int(bits, 16)
    need(((raw >> 52) & 2047) != 2047, 'finite binary64 required')
    return Fraction.from_float(struct.unpack('>d', bytes.fromhex(bits))[0])


def rn(value):
    """Nearest binary64 bits, ties even, for a finite rational of clock scale."""
    value = Fraction(value)
    sign = 1 << 63 if value < 0 else 0
    if value == 0:
        return '0000000000000000'
    value = abs(value)
    n, d = value.numerator, value.denominator
    e = n.bit_length() - d.bit_length()
    if (n < (d << e)) if e >= 0 else ((n << -e) < d):
        e -= 1
    shift = max(e - 52, -1074)
    if shift >= 0:
        quotient, remainder = divmod(n, d << shift)
        divisor = d << shift
    else:
        quotient, remainder = divmod(n << -shift, d)
        divisor = d
    if 2 * remainder > divisor or (2 * remainder == divisor and quotient % 2):
        quotient += 1
    if e < -1022:
        need(quotient <= (1 << 52), 'subnormal rounding range')
        raw = quotient
    else:
        if quotient == 1 << 53:
            quotient >>= 1
            e += 1
        need(-1022 <= e <= 1023 and (1 << 52) <= quotient < (1 << 53), 'normal rounding range')
        raw = ((e + 1023) << 52) | (quotient - (1 << 52))
    return f'{sign | raw:016x}'


def self_test():
    tests = [
        (Fraction(0), '0000000000000000'),
        (Fraction(1), '3ff0000000000000'),
        (Fraction(1) + Fraction(1, 1 << 53), '3ff0000000000000'),
        (Fraction(1) + Fraction(3, 1 << 53), '3ff0000000000002'),
        (Fraction(1, 1 << 1075), '0000000000000000'),
        (Fraction(3, 1 << 1075), '0000000000000002'),
        (Fraction(1, 1 << 1074), '0000000000000001'),
        (Fraction(1, 1 << 1022) - Fraction(1, 1 << 1075), '0010000000000000'),
        (-Fraction(1) - Fraction(1, 1 << 53), 'bff0000000000000'),
        (Fraction(10**9), '41cdcd6500000000'),
    ]
    for exact, expected in tests:
        need(rn(exact) == expected, 'integer rounding self-test')
    need(number('8000000000000000') == 0, 'real interpretation of negative zero')
    return len(tests) + 1


def enclosure(value, exact):
    need(isinstance(value, list) and len(value) == 2, 'two interval endpoints required')
    lo, hi = map(number, value)
    need(lo <= exact <= hi, 'exact real clock expression not enclosed')


def check_case(case):
    i, o = case['input'], case['output']
    t, h = number(i['timeBits']), number(i['horizonBits'])
    ticks = i['ticks']
    need(type(ticks) is int and 0 <= ticks <= (1 << 64) - 1, 'uint64 ticks')
    need(o['originalTimeBits'] == i['timeBits'] and type(o['originalTicks']) is int and
         o['originalTicks'] == ticks and o['requestedDtBits'] == i['horizonBits'], 'original clock/horizon provenance bits')
    need(o['advanceProfileChecked'] is True and o['advanceProfileMatches'] is True,
         'configured prototype profile gate; artifact audit remains separate')
    status, reason = 'invalid_input', 'none'
    next_bits = None
    if not (0 < h <= number('3fb999999999999a')):
        reason = 'horizon'
    elif not (0 <= t <= 10**9):
        reason = 'progress_time'
    elif ticks > (1 << 53) - 1:
        reason = 'progress_ticks'
    elif ticks == (1 << 53) - 1:
        reason = 'tick_limit'
    else:
        candidate = rn(t + h)
        if number(candidate) > 10**9:
            reason = 'time_limit'
        elif number(candidate) <= t:
            status, reason = 'not_certified', 'time_resolution'
        else:
            status, reason, next_bits = 'committed', 'none', candidate
    committed = next_bits is not None
    need(o['status'] == status and o['reason'] == reason, 'clock status/reason')
    need(type(o['committed']) is bool and o['committed'] == committed, 'commit flag')
    need(o['advancedDtBits'] == (i['horizonBits'] if committed else '0000000000000000'), 'requested/zero advancement')
    need(o['actualTimeBits'] == (next_bits if committed else i['timeBits']), 'actual time bits')
    need(type(o['actualTicks']) is int and o['actualTicks'] == ticks + int(committed), 'actual tick transition')
    need(o['proposedTimeBits'] == next_bits and
         ((type(o['proposedTicks']) is int and o['proposedTicks'] == ticks + 1) if committed else o['proposedTicks'] is None), 'clock proposal')
    for key, expected in [('guardQueriesAttempted', int(committed)), ('guardQueriesReturned', int(committed)),
                          ('bodyAssignments', 0), ('progressAssignments', int(committed))]:
        need(type(o[key]) is int and o[key] == expected, 'exact clock work/store counter: ' + key)
    if committed:
        clock = o['clock']
        proposed = number(next_bits)
        enclosure(clock['sum'], t + h)
        enclosure(clock['difference'], proposed - t)
        enclosure(clock['error'], proposed - (t + h))
        need(clock['representedDtBits'] == rn(proposed - t), 'rounded represented clock difference')
    else:
        need(o['clock'] is None, 'invalid/nonprogress clock has no completed diagnostics')
    return committed


def check_document(data):
    need(type(data['schema']) is int and data['schema'] == 1 and data['kind'] == 'world-static-mesh-flight-advance-clock-fixtures', 'clock fixture schema')
    cases = data['cases']
    need(isinstance(cases, list) and len(cases) > 0, 'nonempty clock fixture set')
    accepted = sum(check_case(c) for c in cases)
    return {'status': 'PASS', 'cases': len(cases), 'committed': accepted, 'rejected': len(cases) - accepted,
            'scope': 'Finite empty-World clock transitions, integer RN reference and rational interval inclusion only. No general physics, allocation faults or artifact audit.'}


if __name__ == '__main__':
    count = self_test()
    if sys.argv[1:] == ['--self-test']:
        print(json.dumps({'status': 'PASS', 'selfTests': count}))
    elif len(sys.argv) == 2:
        def unique_keys(items):
            result = {}
            for key, value in items:
                need(key not in result, 'duplicate fixture key')
                result[key] = value
            return result
        data = json.loads(Path(sys.argv[1]).read_text(encoding='utf8'), object_pairs_hook=unique_keys,
                          parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        result = check_document(data)
        result['selfTests'] = count
        print(json.dumps(result))
    else:
        raise SystemExit('usage: clock-reference.py --self-test | CLOCK_FIXTURES_JSON')
