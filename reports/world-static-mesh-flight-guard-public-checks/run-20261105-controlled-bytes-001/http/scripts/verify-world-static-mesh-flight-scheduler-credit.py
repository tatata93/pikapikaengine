"""Independent integer-RN check of selected Native scheduler observations.

Does not rerun production or verify missing nested AdvanceReport/child physics.
Unknown environment/allocator outcomes remain Native observations, never derived
from elapsed time alone. Credit/progress math and all-or-none failure snapshots
are checked on the actual supplied transcript.
"""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'reports/world-static-mesh-flight-advance-recipes/clock-reference.py'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('scheduler_credit_integer_rn', REFERENCE)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
number, rn, enclosure = reference.number, reference.rn, reference.enclosure


def need(value, message):
    if not value:
        raise ValueError(message)


def integer(value, limit=(1 << 64) - 1):
    need(type(value) is int and 0 <= value <= limit, 'Nonnegative bounded integer')
    return value


def boolean(value):
    need(type(value) is bool, 'Boolean field')
    return value


def rawbits(value):
    need(type(value) is str and re.fullmatch('[0-9a-f]{16}', value), 'Binary64/uint64 bits')
    return int(value, 16)


def finite(value):
    return ((rawbits(value) >> 52) & 2047) != 2047


def snapshot(value):
    h, b = number(value['stepBits']), number(value['backlogBits'])
    need(number('3eb0000000000000') <= h <= number('3fb999999999999a'), 'Immutable step domain')
    need(0 <= b <= 1 and not rawbits(value['backlogBits']) >> 63, 'Represented positive backlog domain')
    n = integer(value['maxAttempts'], 8)
    need(n > 0 and value['busy'] is False, 'Snapshot attempts/nonbusy observation')
    integer(value['sequence'])
    return h, b, n


def check_trace(trace):
    r = trace['report']
    h, before, cap = snapshot(r['before'])
    after_h, after, after_cap = snapshot(r['after'])
    need(h == after_h and cap == after_cap and r['before']['stepBits'] == r['after']['stepBits'], 'Immutable exact settings')
    accepted = boolean(r['accepted'])
    planned, attempts, committed = [integer(r[k], 8) for k in ['planned', 'attempts', 'committed']]
    need(committed <= attempts <= planned <= cap, 'Attempt/prefix bounds')
    need(len(r['queue']) == planned and len(r['ticks']) == attempts, 'Dense observed slots')
    need(r['dropBits'] == '0000000000000000', 'Retain-only drop +0')
    for key in ['worldBeforeBits', 'worldAfterBits', 'sourceBeforeBits', 'sourceAfterBits']:
        need(type(trace[key]) is list, 'Snapshot list')
        for bits in trace[key]:
            rawbits(bits)
    need(trace['sourceBeforeBits'] == trace['sourceAfterBits'], 'All source/settings snapshot bits preserved')
    p0, p1 = trace['progressBefore'], trace['progressAfter']
    time = number(p0['timeBits'])
    ticks = integer(p0['ticks'])
    integer(p1['ticks'])
    status, reason = integer(r['status'], 6), integer(r['reason'], 11)
    if not accepted:
        need(r['before'] == r['after'] and p0 == p1 and trace['worldBeforeBits'] == trace['worldAfterBits'], 'Unaccepted input preserves all observed state')
        need(attempts == committed == 0, 'No attempts before admission')
        if reason == 3:
            need(status == 3 and (not finite(r['elapsedBits']) or not 0 <= number(r['elapsedBits']) <= 1), 'Actual invalid elapsed')
        elif reason == 4:
            need(status == 3 and finite(r['elapsedBits']) and 0 <= number(r['elapsedBits']) <= 1 and
                 number(rn(before + number(r['elapsedBits']))) > 1, 'Actual admission cap overflow')
        elif reason == 5:
            need(status == 3 and r['before']['sequence'] == (1 << 64) - 1, 'Actual sequence cap')
        else:
            need((status, reason) in {(4, 1), (4, 2), (5, 6), (3, 7), (5, 8), (5, 9), (6, 10)}, 'Observed external/environment preflight refusal class')
        return {'accepted': 0, 'attempts': 0, 'committed': 0, 'externalRefusal': int(reason not in {3, 4, 5})}
    need(finite(r['elapsedBits']), 'Accepted elapsed finite')
    elapsed = number(r['elapsedBits'])
    need(0 <= elapsed <= 1 and r['before']['sequence'] < (1 << 64) - 1, 'Admitted input domains')
    credit_bits = rn(before + elapsed)
    credit = number(credit_bits)
    need(credit <= 1 and r['admittedCreditBits'] == credit_bits, 'Independent integer RN admission')
    enclosure(r['admissionErrorBits'], credit - (before + elapsed))
    need(r['after']['sequence'] == r['before']['sequence'] + 1, 'Input admitted exactly once')
    queue = []
    while credit >= h and len(queue) < cap:
        nxt = rn(credit - h)
        need(0 <= number(nxt) < credit, 'Queue numeric progress')
        queue.append((credit_bits, nxt, number(nxt) - (credit - h)))
        credit_bits, credit = nxt, number(nxt)
    need(len(queue) == planned, 'Complete independent due plan; no epsilon')
    for q, (before_bits, next_bits, error) in zip(r['queue'], queue):
        need(q['beforeBits'] == before_bits and q['proposedBits'] == next_bits, 'Full integer-RN queue bits')
        enclosure(q['errorBits'], error)
    need(attempts == planned or (attempts > 0 and not r['ticks'][-1]['consumed']), 'Only first actual rejection stops a due plan')
    seen = 0
    body_count = rawbits(trace['worldBeforeBits'][0])
    need(body_count <= 8, 'Actual bounded body inventory')
    for i, t in enumerate(r['ticks']):
        need(integer(t['queueIndex'], 7) == i, 'Actual attempt ordinal')
        consumed = boolean(t['consumed'])
        for key in ['bodyStores', 'progressStores', 'guardAttempts', 'guardReturns']:
            integer(t[key])
        boolean(t['guardPresent'])
        need(consumed == (integer(t['status'], 4) == 0), 'Actual advance commit flag/status')
        if consumed:
            need(0 <= time <= 10**9 and ticks < (1 << 53) - 1, 'Committed clock domain')
            new_time = rn(time + h)
            need(time < number(new_time) <= 10**9, 'Committed clock integer RN progress')
            time, ticks = number(new_time), ticks + 1
            need(t['progressStores'] == 1 and t['bodyStores'] == body_count, 'Whole actual successful store counts')
            seen += 1
        else:
            need(i + 1 == attempts and status == 2 and reason == 11 and
                 t['bodyStores'] == t['progressStores'] == 0, 'Rejected tick no stores and stops prefix')
    need(seen == committed, 'Exact observed successful prefix')
    expected_after = r['admittedCreditBits'] if committed == 0 else queue[committed - 1][1]
    need(r['after']['backlogBits'] == expected_after, 'Only successful tick credit consumed')
    need(p1['timeBits'] == (p0['timeBits'] if committed == 0 else rn(time)) and p1['ticks'] == ticks, 'All actual Progress bits/count')
    if committed == 0:
        need(trace['worldBeforeBits'] == trace['worldAfterBits'], 'All World bits preserved without commit')
    if attempts == committed:
        need(reason == 0 and status == (1 if after >= h else 0), 'Waiting/budget status and no implicit drop')
    return {'accepted': 1, 'attempts': attempts, 'committed': committed, 'externalRefusal': 0}


def check(data):
    need(type(data['schema']) is int and data['schema'] == 1 and data['kind'] == 'world-flight-scheduler-prototype-observations', 'Selected observation schema')
    need(type(data['traces']) is list and data['traces'], 'Nonempty actual trace list')
    total = dict(accepted=0, attempts=0, committed=0, externalRefusal=0)
    for trace in data['traces']:
        for key, value in check_trace(trace).items():
            total[key] += value
    return {'status': 'PASS', 'traces': len(data['traces']), **total,
            'scope': 'Selected actual credit/queue/Progress transcript: integer/Fraction RN and enclosure, due cap, admission/prefix consumption, raw source and no-commit World preservation. Missing nested AdvanceReport/child mathematics and successful full World correspondence remain separate Native assertions/unexecuted independent gates. External environment/allocator refusal classification is a Native observation, not independently recreated.'}


if __name__ == '__main__':
    try:
        need(not sys.flags.optimize, 'Checker requires active assertions/normal interpreter')
        need(len(sys.argv) == 2, 'Expected actual observation JSON path')
        def unique(items):
            out = {}
            for key, value in items:
                need(key not in out, 'Duplicate JSON key')
                out[key] = value
            return out
        path = Path(sys.argv[1])
        need(path.stat().st_size <= 32 * 1024 * 1024, 'Bounded selected transcript')
        data = json.loads(path.read_text(encoding='utf8'), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON token')))
        result = check(data)
        result['integerReferenceSelfTests'] = reference.self_test()
        print(json.dumps(result))
    except Exception as error:
        print(json.dumps({'status': 'FAIL', 'error': type(error).__name__ + ': ' + str(error)}))
        raise SystemExit(1)
