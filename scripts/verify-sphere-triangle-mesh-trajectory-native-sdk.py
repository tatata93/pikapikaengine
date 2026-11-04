"""Independent frozen Native-DTO / C ABI packet conformance runner.

The production guard, C ABI, and probe are not imported as an encoder. Expected
wire values are assembled here from the separately produced pure Native DTOs.
The rational whole-path checker is run on its full, pinned 62-input corpus;
this is explicitly distinct from the 59 exchange-accepted model comparisons.
--packets uses the same path for externally captured raw C ABI packets (e.g.
WASM), without pretending that a JavaScript owned wrapper has been exercised.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'trajectory_sdk_exact_reference', HERE / 'verify-sphere-triangle-mesh-trajectory.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
need = reference.need

STATUSES = ['separated', 'penetration_witness', 'not_certified', 'invalid_input',
            'unsupported_environment', 'numerical_failure']
REASONS = ['none', 'settings', 'surface_count', 'surface_id', 'duplicate_id',
           'input_domain', 'surface_budget', 'mesh_query_failed', 'evaluation_budget',
           'leaf_budget', 'depth_budget', 'sqrt_budget', 'parameter_resolution',
           'nonfinite_intermediate', 'allocation_failure', 'environment',
           'coverage_inconsistent']
OUTCOMES = ['pending', 'separated', 'split', 'penetration_witness', 'not_certified']
WORK = ['meshQueries', 'primitiveQueries', 'candidatesExamined',
        'primitiveSqrtRefinements', 'enclosureSqrtRefinements', 'sqrtRefinements',
        'sqrtRefinementsUpper', 'meshSqrtLimitedRows', 'enclosureSqrtCalls',
        'enclosureSqrtLimitedCalls', 'workExact']
PRIMITIVE_SETTINGS = ['maxCandidates', 'sqrtRefinements', 'maxTotalSqrtRefinements',
                      'maximumLocalWidth', 'maximumNormalWidth', 'minimumSineSquared']
GUARD_SETTINGS = ['maxEvaluations', 'maxLeaves', 'maxDepth',
                  'enclosureSqrtRefinements', 'maxTotalSqrtRefinements']
INTERVALS = ['distance', 'displacementSquaredBound', 'errorSquaredBound',
             'displacementRoot', 'errorRoot', 'clearanceCertificate',
             'penetrationCertificate']


def numeric(value):
    need(type(value) in (int, float), 'wire scalar must be numeric, never bool')
    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise AssertionError('wire scalar must be finite binary64')
    need(math.isfinite(number), 'wire scalar must be finite binary64')
    if type(value) is int:
        need(int(number) == value, 'integer wire token must be exactly binary64')
    return number


def bits(value):
    return struct.pack('>d', numeric(value)).hex()


def signed_json(value):
    if type(value) in (int, float):
        numeric(value)
        if value == 0 and math.copysign(1, value) < 0:
            return '-0'
        return json.dumps(value, allow_nan=False, separators=(',', ':'))
    if type(value) is list:
        return '[' + ','.join(signed_json(x) for x in value) + ']'
    if type(value) is dict:
        return '{' + ','.join(json.dumps(k) + ':' + signed_json(v)
                              for k, v in value.items()) + '}'
    return json.dumps(value, allow_nan=False, separators=(',', ':'))


def fields(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), label + ': exact object fields')


def integer(value, maximum, label):
    need(type(value) is int and 0 <= value <= maximum, label + ': unsigned integer token')
    return value


def enum(value, choices):
    need(type(value) is str and value in choices, 'known frozen enum')
    return choices.index(value)


def flatten(value):
    return [x for pair in value for x in pair]


def optional(value, size):
    return [int(value is not None)] + (value if value is not None else [0] * size)


def work(value):
    fields(value, WORK, 'pure Work')
    need(type(value['workExact']) is bool, 'Work exact flag type')
    return [int(value[k]) if k == 'workExact' else value[k] for k in WORK]


def cell(value):
    fields(value, ['parameter', 'depth'], 'pure Cell')
    return value['parameter'] + [value['depth']]


def query_values(source):
    s = source['settings']
    p = s['mesh']['primitive']
    values = source['start'] + source['end'] + [source['radius'], s['mesh']['maxSurfaces']]
    values += [p[k] for k in PRIMITIVE_SETTINGS] + [s[k] for k in GUARD_SETTINGS] + [0] * 5
    need(len(values) == 24, 'query24 layout')
    return values


def source_values(source):
    return [[t['id']] + flatten(t['vertices']) for t in source['triangles']]


def mesh_header(result, source_count):
    n = result['nearest']
    return [result['status'], result['reason'], int(n is not None), source_count,
            len(result['rows'])] + optional(None if result['failedIndex'] is None else [result['failedIndex']], 1) \
        + optional(None if result['firstFailedRow'] is None else [result['firstFailedRow']], 1) \
        + [result[k] for k in ['queries', 'candidatesExamined', 'sqrtRefinements',
                               'sqrtLimitedRows', 'failedRows']] \
        + [len(n['possibleSurfaceIds']) if n is not None else 0] \
        + ([v for k in ['squaredDistance', 'distance', 'gap'] for v in n[k]]
           if n is not None else [0] * 6) + [0] * 3


def primitive_packet(result, surface_id):
    g = result['geometry']
    packet = [result['status'], result['reason'], int(g is not None),
              surface_id,
              g['survivingFeatures'] if g is not None else 0,
              g['relation'] if g is not None else 0,
              len(result['candidates']), result['candidatesExamined'],
              result['sqrtRefinements'], int(result['sqrtRefinementLimited'])]
    packet += optional(result['squaredCross'], 2) + optional(result['sineSquared'], 2)
    if g is None:
        packet += [0] * 42
    else:
        packet += [v for k in ['barycentric', 'closestLocal', 'closest', 'delta',
                              'normal', 'spherePoint'] for v in flatten(g[k])]
        packet += [v for k in ['squaredDistance', 'distance', 'gap'] for v in g[k]]
    need(len(packet) == 58, 'primitive58 layout')
    return packet


def candidate_packet(candidate):
    return [candidate['feature'], candidate['disposition'], candidate['kktCount']] \
        + flatten(candidate['barycentric']) + flatten(candidate['kkt'])


def audit_packet(audit, ordinal):
    packet = [ordinal] + cell(audit['cell']) + [audit['midpoint'], enum(audit['outcome'], OUTCOMES)]
    for key in ['pathBounds', 'pointBounds']:
        packet += optional(flatten(audit[key]) if audit[key] is not None else None, 6)
    packet += optional(audit['anchor'], 3) + [int(audit['meshQueried'])]
    for key in ['meshStatus', 'meshReason']:
        packet += optional([audit[key]] if audit[key] is not None else None, 1)
    for key in INTERVALS:
        packet += optional(audit[key], 2)
    packet += work(audit['work']) + [0] * 3
    need(len(packet) == 64, 'audit64 layout')
    return packet


def trajectory_header(result, source_count):
    return [enum(result['status'], STATUSES), enum(result['reason'], REASONS), source_count,
            int(result['snapshot'] is not None)] \
        + optional([result['failedIndex']] if result['failedIndex'] is not None else None, 1) \
        + [len(result['certifiedLeaves']), len(result['frontier']), len(result['audits'])] \
        + optional(result['safePrefix'], 2) \
        + [int(result[k] is not None) for k in ['witness', 'current', 'lastMesh']] \
        + optional([result['lastMeshAuditIndex']] if result['lastMeshAuditIndex'] is not None else None, 1) \
        + [result['partitionLeaves'], result['maximumDepth']] + work(result['work']) + [0] * 2


def leaf_packet(leaf):
    return cell(leaf['cell']) + leaf['lowerGapCertificate'] + [leaf['auditIndex']]


def witness_packet(witness):
    return [0] + cell(witness['cell']) + [witness['parameter']] \
        + flatten(witness['exactPathBounds']) + witness['anchor'] \
        + [witness['errorUpper']] + witness['upperGapCertificate'] + [witness['auditIndex']]


def source_packets(source, last_mesh):
    result = []
    for ordinal, values in enumerate(source_values(source)):
        has_row = last_mesh is not None and ordinal < len(last_mesh['rows'])
        has_query = has_row and last_mesh['rows'][ordinal]['query'] is not None
        nearest = last_mesh['nearest'] if last_mesh is not None else None
        possible = nearest is not None and values[0] in nearest['possibleSurfaceIds']
        result.append([ordinal] + values + [int(has_row), int(has_query), int(possible)])
    return result


def host_path(source):
    """Classify exchange shape only, without consulting fixture name/order/status."""
    triangles = source_values(source)
    if len(triangles) > 64:
        return 1, [], 1, 'begin'
    append_statuses = []
    for offset in range(0, len(triangles), 6):
        chunk = triangles[offset:offset + 6]
        valid = all(1 <= t[0] <= 2 ** 53 - 1 and int(t[0]) == t[0]
                    and all(math.isfinite(numeric(v)) for v in t) for t in chunk)
        append_statuses.append(0 if valid else 1)
        if not valid:
            return 0, append_statuses, 1, 'append'
    q = query_values(source)
    valid = all(math.isfinite(numeric(v)) for v in q) \
        and all(0 <= q[i] <= 2 ** 32 - 1 and int(q[i]) == q[i]
                for i in [7, 8, 9, 10, 14, 15, 16, 17, 18]) \
        and all(bits(q[i]) == '0000000000000000' for i in range(19, 24))
    return 0, append_statuses, 0 if valid else 1, None if valid else 'query'


class Compare:
    def __init__(self):
        self.numeric_count = 0
        self.negative_zeros = 0

    def equal(self, actual, expected, label):
        if type(expected) in (int, float):
            need(bits(actual) == bits(expected), label + ': exact binary64 bits')
            self.numeric_count += 1
            self.negative_zeros += bits(actual) == '8000000000000000'
        elif type(expected) is list:
            need(type(actual) is list and len(actual) == len(expected), label + ': exact array length')
            for i, (a, e) in enumerate(zip(actual, expected)):
                self.equal(a, e, f'{label}[{i}]')
        elif type(expected) is dict:
            fields(actual, expected, label)
            for key in expected:
                self.equal(actual[key], expected[key], label + '.' + key)
        else:
            need(type(actual) is type(expected) and actual == expected, label + ': exact value/type')

    def packet(self, actual, actual_bits, expected, label):
        if expected is None:
            need(actual is None and actual_bits is None, label + ': absent packet')
            return
        self.equal(actual, expected, label)
        need(type(actual_bits) is list and len(actual_bits) == len(expected), label + ': bit length')
        for n, token in zip(actual, actual_bits):
            need(type(token) is str and re.fullmatch('[0-9a-f]{16}', token)
                 and token == bits(n), label + ': raw JSON / bit token integrity')


RECORD_KEYS = {'name', 'input', 'inputBits', 'triangles', 'triangleBits',
               'beginStatus', 'appendStatuses', 'exchangeStatus', 'failedPhase',
               'summary', 'summaryBits', 'echo', 'echoBits', 'sources', 'sourceBits',
               'audits', 'auditBits', 'leaves', 'leafBits', 'frontier', 'frontierBits',
               'current', 'currentBits', 'witness', 'witnessBits',
               'lastMeshSummary', 'lastMeshSummaryBits', 'lastMeshRows',
               'outputBefore', 'outputBeforeBits', 'outputAfter', 'outputAfterBits',
               'hostFailurePreserved'}


def verify_packets(source, packets):
    fields(packets, {'schema', 'kind', 'fixtureCount', 'accepted', 'hostRejected', 'fixtures'},
           'packet envelope')
    need(type(packets['schema']) is int and packets['schema'] == 1
         and packets['kind'] == 'sphere-triangle-mesh-trajectory-sdk-packets', 'packet schema')
    count = len(source['fixtures'])
    need(integer(packets['fixtureCount'], 256, 'fixtureCount') == count, 'full fixture count')
    need(type(packets['fixtures']) is list and len(packets['fixtures']) == count, 'all wire cases')
    comparison = Compare()
    counts = {'modelFixtures': 0, 'hostRejected': 0, 'separated': 0,
              'penetrationWitnesses': 0, 'expectedModelFailures': 0,
              'audits': 0, 'certifiedLeaves': 0, 'lastMeshRows': 0,
              'lastMeshCandidates': 0, 'maximumSourceCount': 0,
              'maximumAuditCount': 0, 'maximumLeafCount': 0}
    prior_output = []
    for index, (fixture, record) in enumerate(zip(source['fixtures'], packets['fixtures'])):
        label = f'fixture[{index}]'
        fields(record, RECORD_KEYS, label)
        comparison.equal(record['name'], fixture['name'], label + '.identity')
        q, r = fixture['input'], fixture['result']
        original = source_values(q)
        comparison.packet(record['input'], record['inputBits'], query_values(q), label + '.input')
        need(type(record['triangles']) is list and type(record['triangleBits']) is list
             and len(record['triangles']) == len(record['triangleBits']) == len(original),
             label + ': complete triangle echo')
        for ordinal, (values, raw_bits, expected) in enumerate(zip(
                record['triangles'], record['triangleBits'], original)):
            comparison.packet(values, raw_bits, expected, label + f'.triangles[{ordinal}]')
        comparison.packet(record['outputBefore'], record['outputBeforeBits'], prior_output,
                          label + '.outputBefore')
        begin, append, exchange, phase = host_path(q)
        for key, expected in [('beginStatus', begin), ('exchangeStatus', exchange)]:
            need(type(record[key]) is int and record[key] == expected, label + '.' + key)
        comparison.equal(record['appendStatuses'], append, label + '.appendStatuses')
        comparison.equal(record['failedPhase'], phase, label + '.failedPhase')
        if exchange:
            counts['hostRejected'] += 1
            comparison.equal(record['hostFailurePreserved'], True, label + '.preserved')
            for key in ['summary', 'echo', 'current', 'witness', 'lastMeshSummary']:
                comparison.packet(record[key], record[key + 'Bits'], None, label + '.' + key)
            for key, bit_key in [('sources', 'sourceBits'), ('audits', 'auditBits'),
                                 ('leaves', 'leafBits'), ('frontier', 'frontierBits')]:
                comparison.equal(record[key], [], label + '.' + key)
                comparison.equal(record[bit_key], [], label + '.' + bit_key)
            comparison.equal(record['lastMeshRows'], [], label + '.lastMeshRows')
            comparison.packet(record['outputAfter'], record['outputAfterBits'], prior_output,
                              label + '.outputAfter')
            continue
        counts['modelFixtures'] += 1
        counts['separated'] += r['status'] == 'separated'
        counts['penetrationWitnesses'] += r['status'] == 'penetration_witness'
        counts['expectedModelFailures'] += r['status'] not in ('separated', 'penetration_witness')
        comparison.equal(record['hostFailurePreserved'], None, label + '.noHostFailure')
        # The rational stage also checks every snapshot setting/source bit;
        # the final PASS requires both that stage and this full wire mapping.
        expected_summary = trajectory_header(r, len(original))
        need(len(expected_summary) == 32, 'trajectory header32')
        comparison.packet(record['summary'], record['summaryBits'], expected_summary, label + '.summary')
        comparison.packet(record['echo'], record['echoBits'], query_values(q), label + '.echo')
        last_output = query_values(q)
        matrix = [
            ('sources', 'sourceBits', source_packets(q, r['lastMesh'])),
            ('audits', 'auditBits', [audit_packet(a, i) for i, a in enumerate(r['audits'])]),
            ('leaves', 'leafBits', [leaf_packet(v) for v in r['certifiedLeaves']]),
            ('frontier', 'frontierBits', [[i] + cell(v) for i, v in enumerate(r['frontier'])])]
        for key, bit_key, expected_rows in matrix:
            need(type(record[key]) is list and type(record[bit_key]) is list
                 and len(record[key]) == len(record[bit_key]) == len(expected_rows),
                 label + '.' + key + ': exact complete rows')
            for ordinal, (row, raw_bits, expected) in enumerate(zip(
                    record[key], record[bit_key], expected_rows)):
                comparison.packet(row, raw_bits, expected, label + f'.{key}[{ordinal}]')
                last_output = expected
        counts['audits'] += len(r['audits'])
        counts['certifiedLeaves'] += len(r['certifiedLeaves'])
        counts['maximumSourceCount'] = max(counts['maximumSourceCount'], len(original))
        counts['maximumAuditCount'] = max(counts['maximumAuditCount'], len(r['audits']))
        counts['maximumLeafCount'] = max(counts['maximumLeafCount'], len(r['certifiedLeaves']))
        current = [0] + cell(r['current']) if r['current'] is not None else None
        witness = witness_packet(r['witness']) if r['witness'] is not None else None
        for key, expected in [('current', current), ('witness', witness)]:
            comparison.packet(record[key], record[key + 'Bits'], expected, label + '.' + key)
            if expected is not None:
                last_output = expected
        mesh = r['lastMesh']
        header = mesh_header(mesh, len(original)) if mesh is not None else None
        comparison.packet(record['lastMeshSummary'], record['lastMeshSummaryBits'], header,
                          label + '.lastMeshSummary')
        if header is not None:
            last_output = header
        expected_rows = list(enumerate(mesh['rows'])) if mesh is not None else []
        need(type(record['lastMeshRows']) is list and len(record['lastMeshRows']) == len(expected_rows),
             label + ': full last mesh row prefix')
        for (ordinal, row), raw_row in zip(expected_rows, record['lastMeshRows']):
            fields(raw_row, ['rowOrdinal', 'packet', 'bits', 'candidates', 'candidateBits'],
                   label + '.lastMeshRow')
            need(type(raw_row['rowOrdinal']) is int and raw_row['rowOrdinal'] == ordinal,
                 label + ': original row ordinal')
            comparison.equal(row['triangle'], q['triangles'][ordinal], label + ': pure owned row source')
            query = row['query']
            expected = primitive_packet(query, row['triangle']['id']) if query is not None else None
            comparison.packet(raw_row['packet'], raw_row['bits'], expected, label + '.lastMeshRow.packet')
            if expected is not None:
                last_output = expected
            candidates = query['candidates'] if query is not None else []
            need(type(raw_row['candidates']) is list and type(raw_row['candidateBits']) is list
                 and len(raw_row['candidates']) == len(raw_row['candidateBits']) == len(candidates),
                 label + ': every candidate prefix including last row')
            for c, (raw_candidate, raw_bits, expected_candidate) in enumerate(zip(
                    raw_row['candidates'], raw_row['candidateBits'], candidates)):
                expected = candidate_packet(expected_candidate)
                comparison.packet(raw_candidate, raw_bits, expected, label + f'.candidate[{ordinal}][{c}]')
                last_output = expected
            counts['lastMeshRows'] += 1
            counts['lastMeshCandidates'] += len(candidates)
        comparison.packet(record['outputAfter'], record['outputAfterBits'], last_output,
                          label + '.outputAfter')
        prior_output = last_output
    need(integer(packets['accepted'], count, 'accepted') == counts['modelFixtures'], 'actual model classification total')
    need(integer(packets['hostRejected'], count, 'hostRejected') == counts['hostRejected'], 'actual host rejection total')
    need(counts['modelFixtures'] + counts['hostRejected'] == count, 'complete classified corpus')
    counts['wireNumericComparisons'] = comparison.numeric_count
    counts['negativeZeroComparisons'] = comparison.negative_zeros
    return counts


def negative_controls(source, packets):
    """Self-check important independent packet gates, after the real data pass.

    Bit companions are repaired for semantic edits so those controls cannot
    succeed solely because a stale integrity token was noticed first.
    """
    mutations = []

    def add(name, change):
        altered = copy.deepcopy(packets)
        change(altered)
        try:
            verify_packets(source, altered)
        except (AssertionError, KeyError, IndexError, TypeError, ValueError) as error:
            mutations.append({'name': name, 'rejected': True, 'diagnostic': str(error)[:240]})
        else:
            raise AssertionError('negative control accepted: ' + name)

    def first(test):
        return next(i for i, r in enumerate(packets['fixtures']) if test(r))

    def set_packet(p, index, key, bit_key, slot, value):
        r = p['fixtures'][index]
        r[key][slot] = value
        r[bit_key][slot] = bits(value)

    accepted = first(lambda r: r['exchangeStatus'] == 0)
    add('unknown-envelope-field', lambda p: p.update({'unexpected': 0}))
    add('fixture-tail-dropped', lambda p: p['fixtures'].pop())
    add('summary-count-fractional', lambda p: set_packet(p, accepted, 'summary', 'summaryBits', 8, .5))
    add('summary-flag-out-of-range', lambda p: set_packet(p, accepted, 'summary', 'summaryBits', 3, 2))
    add('summary-unused-negative-zero', lambda p: set_packet(p, accepted, 'summary', 'summaryBits', 31, -0.0))
    add('summary-work-exact-false', lambda p: set_packet(p, accepted, 'summary', 'summaryBits', 29, 0))
    add('summary-work-upper-changed', lambda p: set_packet(
        p, accepted, 'summary', 'summaryBits', 25,
        packets['fixtures'][accepted]['summary'][25] + 1))
    add('echo-setting-changed', lambda p: set_packet(p, accepted, 'echo', 'echoBits', 18, 123))
    add('numeric-bool-instead-of-f64', lambda p: p['fixtures'][accepted]['summary'].__setitem__(0, True))
    add('bit-integrity-token', lambda p: p['fixtures'][accepted]['summaryBits'].__setitem__(0, 'ffffffffffffffff'))
    with_audit = first(lambda r: bool(r['audits']))
    def alter_audit(p):
        r = p['fixtures'][with_audit]
        r['audits'][-1][61] = -0.0
        r['auditBits'][-1][61] = bits(-0.0)
    add('audit-tail-reserved-negative-zero', alter_audit)
    with_source = first(lambda r: bool(r['sources']))
    add('source-tail-removed', lambda p: (p['fixtures'][with_source]['sources'].pop(),
                                        p['fixtures'][with_source]['sourceBits'].pop()))
    with_signed_source = first(lambda r: any('8000000000000000' in v for v in r['sourceBits']))
    def alter_source_zero(p):
        r = p['fixtures'][with_signed_source]
        row = next(i for i, v in enumerate(r['sourceBits']) if '8000000000000000' in v)
        slot = r['sourceBits'][row].index('8000000000000000')
        r['sources'][row][slot] = 0
        r['sourceBits'][row][slot] = bits(0)
    add('original-source-negative-zero-erased', alter_source_zero)
    with_leaf = first(lambda r: bool(r['leaves']))
    def alter_leaf(p):
        r = p['fixtures'][with_leaf]
        r['leaves'][-1][1] = math.nextafter(float(r['leaves'][-1][1]), 0)
        r['leafBits'][-1][1] = bits(r['leaves'][-1][1])
    add('closed-leaf-boundary-one-ulp', alter_leaf)
    with_witness = first(lambda r: r['witness'] is not None and r['witness'][14] != 0)
    add('witness-error-removed', lambda p: set_packet(p, with_witness, 'witness', 'witnessBits', 14, 0))
    with_rows = first(lambda r: bool(r['lastMeshRows']))
    add('last-mesh-row-tail-dropped', lambda p: p['fixtures'][with_rows]['lastMeshRows'].pop())
    with_candidates = first(lambda r: any(v['candidates'] for v in r['lastMeshRows']))
    def alter_candidate(p):
        row = next(v for v in p['fixtures'][with_candidates]['lastMeshRows'] if v['candidates'])
        row['candidates'].pop()
        row['candidateBits'].pop()
    add('last-mesh-candidate-tail-dropped', alter_candidate)
    def alter_unused_kkt(p):
        row = next(v for v in p['fixtures'][with_candidates]['lastMeshRows'] if v['candidates'])
        candidate = next(i for i, v in enumerate(row['candidates']) if v[2] < 2)
        slot = 9 + 2 * int(row['candidates'][candidate][2])
        value = -0.0 if bits(row['candidates'][candidate][slot]) == bits(0) else 0
        row['candidates'][candidate][slot] = value
        row['candidateBits'][candidate][slot] = bits(value)
    add('unused-kkt-signed-zero-erased-or-flipped', alter_unused_kkt)
    host = first(lambda r: r['exchangeStatus'] != 0)
    add('host-preservation-false', lambda p: p['fixtures'][host].update({'hostFailurePreserved': False}))
    return {'count': len(mutations), 'allRejected': all(m['rejected'] for m in mutations),
            'controls': mutations,
            'scope': 'Duplicated captured packets only; no allocation fault injection or new model execution.'}


def rows_text(fixtures):
    lines = ['pikapika_sphere_triangle_mesh_trajectory_sdk 1', f'cases {len(fixtures)}']
    for fixture in fixtures:
        name, source = fixture['name'], fixture['input']
        need(type(name) is str and re.fullmatch('[A-Za-z0-9_-]{1,96}', name), 'ASCII fixture identity')
        triangles = source_values(source)
        lines.append(json.dumps(name) + ' ' + str(len(triangles)) + ' '
                     + ' '.join(signed_json(v) for v in query_values(source)))
        lines.extend(' '.join(signed_json(v) for v in t) for t in triangles)
    need(all(len(line.encode('ascii')) <= 4096 for line in lines), 'bounded ASCII rows')
    return ('\n'.join(lines) + '\n').encode('ascii')


def write_new(path, content):
    with path.open('xb') as stream:
        stream.write(content if type(content) is bytes else content.encode('utf-8'))


def file_info(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures')
    parser.add_argument('probe', help='Native probe executable; - with --packets')
    parser.add_argument('output', help='fresh output directory (must not exist)')
    parser.add_argument('--packets', help='read captured raw packets instead of running Native probe')
    parser.add_argument('--scope', choices=['native', 'wasm-wire'], default='native')
    args = parser.parse_args()
    need(__debug__, 'runner cannot execute under Python -O')
    directory = Path(args.output).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source_bytes = Path(args.fixtures).read_bytes()
    source = reference.loads(source_bytes)
    need(source['schema'] == 1 and source['kind'] == 'sphere-triangle-mesh-trajectory-fixtures'
         and len(source['fixtures']) == 62, 'frozen 62-input pure fixture envelope')
    write_new(directory / 'inputs.rows', rows_text(source['fixtures']))
    if args.packets:
        raw = Path(args.packets).read_bytes()
        invocation = {'mode': 'captured-packets', 'path': str(Path(args.packets).resolve())}
    else:
        need(args.scope == 'native', 'WASM scope requires --packets')
        command = [str(Path(args.probe).resolve()), '--rows', str(directory / 'inputs.rows')]
        with (directory / 'probe.stdout.json').open('xb') as stdout, \
                (directory / 'probe.stderr.txt').open('xb') as stderr:
            completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stdout,
                                       stderr=stderr, timeout=180, check=False)
        need(completed.returncode == 0, 'Native probe exit must be zero; preserve raw stderr')
        raw = (directory / 'probe.stdout.json').read_bytes()
        invocation = {'mode': 'native-probe', 'command': command, 'exitCode': completed.returncode}
    need(len(raw) <= 64 * 1024 * 1024, 'bounded raw packet bytes')
    write_new(directory / 'packets.json', raw)
    packets = reference.loads(raw)
    # The packet schema/layout verifier is intentionally independent of C ABI
    # packet-generation helpers; every retained pure DTO field is mapped below.
    stats = verify_packets(source, packets)
    controls = negative_controls(source, packets)
    # The original checker pins all 62 inputs. The three host-rejected entries
    # below are NOT described as exchange-derived or replayed model results.
    exact_reference = reference.verify(source)
    write_new(directory / 'reference.json', json.dumps(exact_reference, indent=2) + '\n')
    write_new(directory / 'negative-controls.json', json.dumps(controls, indent=2) + '\n')
    report = {'schema': 1, 'status': 'PASS', 'scope': args.scope,
              'fixtureCount': len(source['fixtures']), **stats,
              'reference': exact_reference,
              'referenceScope': 'Independent rational checker executed on the original pinned 62 pure Native fixtures. All exchange-accepted model DTO fields are independently encoded and bit-compared against raw packets. Host-rejected cases are source-only mathematical inputs, never claimed as replayed model calls.',
              'invocation': invocation, 'source': file_info(Path(args.fixtures)),
              'negativeControls': controls, 'files': {},
              'limitations': 'Read-only defined-segment C ABI only. No JavaScript owned-wrapper, UI, World, TOI, contact response, or injected allocation/unknown-work exception coverage.'}
    for name in ['inputs.rows', 'packets.json', 'reference.json', 'negative-controls.json']:
        report['files'][name] = file_info(directory / name)
    if not args.packets:
        report['probeExecutable'] = file_info(Path(args.probe))
        report['files']['probe.stderr.txt'] = file_info(directory / 'probe.stderr.txt')
    write_new(directory / 'report.json', json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
