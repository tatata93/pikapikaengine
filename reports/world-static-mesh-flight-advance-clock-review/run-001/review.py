"""Saved fresh replay of the prior unsaved clock RN review (not Native acceptance).

The selected cases and Voronoi/tie checks reproduce the earlier transient tool
snippet. This replay additionally checks every used binary64 endpoint against an
integer-only decoder. All arithmetic in expected rounding cells is Fraction or
integer arithmetic, never production floating addition/subtraction.
"""
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TARGET = ROOT / 'reports/world-static-mesh-flight-advance-recipes/clock-reference.py'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def decode_integer(raw):
    need(type(raw) is int and 0 <= raw < (1 << 64), 'binary64 encoding')
    sign = -1 if raw >> 63 else 1
    exponent = (raw >> 52) & 2047
    mantissa = raw & ((1 << 52) - 1)
    need(exponent != 2047, 'finite reference endpoint')
    if exponent:
        mantissa |= 1 << 52
        power = exponent - 1023 - 52
    else:
        power = -1074
    return sign * (F(mantissa << power) if power >= 0 else F(mantissa, 1 << -power))


def main():
    before = TARGET.read_bytes()
    (OUT / 'clock-reference.before.py').write_bytes(before)
    spec = importlib.util.spec_from_file_location('clock_reference_review', TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    endpoint_encodings = set()

    def q(raw):
        endpoint_encodings.add(raw)
        # Original review used this exact finite decoding, which performs no
        # arithmetic on floats. Independently verify it here from integer bits.
        original = module.number(f'{raw:016x}')
        independent = decode_integer(raw)
        need(original == independent, 'finite decoder differs from integer bits')
        return independent

    def nearest_cell(exact):
        bits = module.rn(exact)
        need(isinstance(bits, str) and len(bits) == 16, 'RN encoding length')
        raw = int(bits, 16)
        positive = raw & ((1 << 63) - 1)
        need(raw >> 63 == int(exact < 0), 'RN sign, including negative underflow')
        absolute = abs(exact)
        current = q(positive)
        if positive:
            left = (q(positive - 1) + current) / 2
            need(absolute > left or (absolute == left and positive % 2 == 0),
                 'nearest-even left midpoint boundary')
        right = (current + q(positive + 1)) / 2
        need(absolute < right or (absolute == right and positive % 2 == 0),
             'nearest-even right midpoint boundary')

    words = [0, 1, 2, (1 << 52) - 2, (1 << 52) - 1, 1 << 52, (1 << 52) + 1]
    for exponent_field in range(1, 1053):
        word = exponent_field << 52
        words.extend([word - 1, word, word + 1, word + 2])
    checks = 0
    exact_inputs = set()
    for word in words:
        midpoint = (q(word) + q(word + 1)) / 2
        epsilon = (q(word + 1) - q(word)) / 8
        for exact in [q(word), midpoint - epsilon, midpoint,
                      midpoint + epsilon, q(word + 1)]:
            nearest_cell(exact)
            exact_inputs.add(exact)
            checks += 1
            if exact:
                nearest_cell(-exact)
                exact_inputs.add(-exact)
                checks += 1
    self_tests = module.self_test()
    need(checks == 42149 and self_tests == 11, 'replayed test counts')
    need(module.number('8000000000000000') == 0, 'negative-zero real interpretation')
    after = TARGET.read_bytes()
    (OUT / 'clock-reference.after.py').write_bytes(after)
    need(before == after, 'reviewed source changed during execution')
    report = {
        'schema': 1, 'status': 'PASS', 'runKind': 'saved fresh replay',
        'priorAttempt': 'Earlier transient REPL/tool run reported 42149 checks; no raw streams were saved then. This is a separate replay, not its original raw evidence.',
        'target': TARGET.relative_to(ROOT).as_posix(),
        'sourceBefore': digest(before), 'sourceAfter': digest(after), 'sourceStable': True,
        'recipe': digest(Path(__file__).read_bytes()),
        'roundingChecks': checks, 'uniqueExactInputs': len(exact_inputs),
        'targetSelfTests': self_tests, 'seedEntriesWithRepetitions': len(words),
        'uniqueSeedEncodings': len(set(words)),
        'distinctDecodedEndpointEncodings': len(endpoint_encodings),
        'selection': {
            'initialPositiveBitWords': [f'{word:016x}' for word in words[:7]],
            'normalExponentFieldsInclusive': [1, 1052],
            'perExponentBitWords': '(e<<52)-1, e<<52, (e<<52)+1, (e<<52)+2',
            'perSeedRationals': 'value(w), midpoint(w,w+1)-spacing/8, midpoint, midpoint+spacing/8, value(w+1)',
            'signs': 'Each selected nonnegative exact rational and its negative if nonzero. Rational zero is tested once per selected occurrence as +0; negative nonzero underflow checks -0.',
            'minimumSeedBits': f'{min(words):016x}',
            'maximumSeedBits': f'{max(words):016x}',
            'notExhaustive': 'Selected bit words around exponent transitions, not every finite encoding or every rational; repetitions are included in 42149 calls. General overflow/Inf conversion is outside the clock reference domain.',
        },
        'oracle': 'Decode adjacent binary64 endpoints with integer significand/power-of-two arithmetic. Use exact Fraction midpoint cells and even raw LSB at ties. No native floating sum/subtraction is an expected-value oracle.',
        'scope': 'RN(value) and exact finite endpoint decoding only, plus the target 11 self-tests. No check_case Native corpus execution, World advance, physics, allocation faults, external arithmetic/artifact binding or interval endpoint-bit provenance acceptance.',
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    (OUT / 'result.json').write_text(text, encoding='utf-8', newline='\n')
    print(text, end='')


if __name__ == '__main__':
    main()
