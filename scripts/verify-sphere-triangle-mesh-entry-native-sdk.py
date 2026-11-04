"""Frozen entry DTO / raw C ABI conformance, independent of production encoder.

Shared helper code below is the previous independent triangle wire encoder,
not a Native API implementation. New entry header, initial/window/partition,
audit, frontier, island, source and witness packets are assembled here from
the complete pure Native 65-input corpus. The original Fraction corpus and its
negative controls are executed separately; host-rejected pure results are never
called exchange-derived mathematical outputs or JavaScript owned DTOs.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


legacy = module('entry_previous_independent_wire', 'verify-sphere-triangle-mesh-trajectory-native-sdk.py')
reference = module('entry_exact_reference', 'verify-sphere-triangle-mesh-entry.py')
need, bits, fields = reference.need, legacy.bits, legacy.fields
numeric, integer, flatten = legacy.numeric, legacy.integer, legacy.flatten
optional, cell, work = legacy.optional, legacy.cell, legacy.work
source_values, source_packets = legacy.source_values, legacy.source_packets
mesh_header, primitive_packet = legacy.mesh_header, legacy.primitive_packet
candidate_packet, Compare = legacy.candidate_packet, legacy.Compare
signed_json, write_new, file_info = legacy.signed_json, legacy.write_new, legacy.file_info
STATUSES = ['entry_window', 'separated', 'initial_penetration', 'not_certified',
            'invalid_input', 'unsupported_environment', 'numerical_failure']
REASONS = ['none', 'settings', 'surface_count', 'surface_id', 'duplicate_id',
           'input_domain', 'surface_budget', 'mesh_query_failed', 'initial_boundary',
           'evaluation_budget', 'leaf_budget', 'depth_budget', 'sqrt_budget',
           'parameter_resolution', 'nonfinite_intermediate', 'allocation_failure',
           'environment', 'coverage_inconsistent']
KINDS = ['initial_point', 'cell']
OUTCOMES = ['pending', 'initial_separated', 'initial_penetration', 'initial_uncertain',
            'separated', 'split', 'unresolved']
LEAF_STATES = ['unqueried', 'certified', 'unresolved', 'current']


def ordinal(value, choices):
    need(type(value) is str and value in choices, 'known entry enum')
    return choices.index(value)


def query_values(source):
    settings = source['settings']
    primitive = settings['mesh']['primitive']
    result = source['start'] + source['end'] + [source['radius'], settings['mesh']['maxSurfaces']]
    result += [primitive[k] for k in legacy.PRIMITIVE_SETTINGS]
    result += [settings[k] for k in legacy.GUARD_SETTINGS] + [settings['parameterTolerance']] + [0] * 4
    need(len(result) == 24, 'entry query24')
    return result


def header(result, source_count):
    value = [ordinal(result['status'], STATUSES), ordinal(result['reason'], REASONS),
             source_count, int(result['snapshot'] is not None)]
    value += optional([result['failedIndex']] if result['failedIndex'] is not None else None, 1)
    value += [int(result['initial'] is not None), int(result['initialSeparationProven']),
              len(result['certifiedLeaves']), len(result['partition']), len(result['frontier']), len(result['audits'])]
    value += optional(result['safePrefix'], 2)
    value += [int(result['bestWitness'] is not None), int(result['window'] is not None),
              len(result['candidateSurfaceIds']), int(result['current'] is not None),
              int(result['lastMesh'] is not None)]
    value += optional([result['lastMeshAuditIndex']] if result['lastMeshAuditIndex'] is not None else None, 1)
    value += [result['partitionLeaves'], result['maximumDepth']] + work(result['work']) + [0] * 5
    need(len(value) == 40, 'entry header40')
    return value


def audit_packet(audit, index):
    value = [index, ordinal(audit['kind'], KINDS)] + cell(audit['cell'])
    value += [audit['parameter'], ordinal(audit['outcome'], OUTCOMES)]
    for key in ['pathBounds', 'pointBounds']:
        value += optional(flatten(audit[key]) if audit[key] is not None else None, 6)
    value += optional(audit['anchor'], 3) + [int(audit['meshQueried'])]
    for key in ['meshStatus', 'meshReason']:
        value += optional([audit[key]] if audit[key] is not None else None, 1)
    for key in legacy.INTERVALS:
        value += optional(audit[key], 2)
    value += work(audit['work']) + [0] * 2
    need(len(value) == 64, 'entry audit64')
    return value


def partition_packet(leaf, index):
    return [index] + cell(leaf['cell']) + [ordinal(leaf['state'], LEAF_STATES)] \
        + optional([leaf['auditIndex']] if leaf['auditIndex'] is not None else None, 1) \
        + [ordinal(leaf['blockedReason'], REASONS)]


def initial_packet(initial):
    return [0] + initial['lowerGapCertificate'] + initial['upperGapCertificate'] + [initial['auditIndex']]


def window_packet(window):
    return [0] + window['parameter'] + window['width'] + [window['witnessAuditIndex']]


def host_path(source):
    """Exchange-only classification, independent of fixture name/model status."""
    rows = source_values(source)
    if len(rows) > 64:
        return 1, [], 1, 'begin'
    append_statuses = []
    for offset in range(0, len(rows), 6):
        valid = all(1 <= row[0] <= 2 ** 53 - 1 and int(row[0]) == row[0]
                    for row in rows[offset:offset + 6])
        append_statuses.append(0 if valid else 1)
        if not valid:
            return 0, append_statuses, 1, 'append'
    query = query_values(source)
    for scalar in query:
        numeric(scalar)
    valid = all(0 <= query[i] <= 2 ** 32 - 1 and int(query[i]) == query[i]
                for i in [7, 8, 9, 10, 14, 15, 16, 17, 18])
    valid = valid and all(bits(query[i]) == bits(0) for i in range(20, 24))
    return 0, append_statuses, 0 if valid else 1, None if valid else 'query'


RECORD_KEYS = (legacy.RECORD_KEYS - {'witness', 'witnessBits'}) | {
    'bestWitness', 'bestWitnessBits', 'partition', 'partitionBits', 'initial', 'initialBits',
    'window', 'windowBits', 'candidateIds', 'candidateIdBits'}


def verify_packets(source, packets):
    fields(packets, {'schema', 'kind', 'fixtureCount', 'accepted', 'hostRejected', 'fixtures'}, 'entry raw envelope')
    need(type(packets['schema']) is int and packets['schema'] == 1
         and packets['kind'] == 'sphere-triangle-mesh-entry-sdk-packets', 'entry raw kind')
    count = len(source['fixtures'])
    need(integer(packets['fixtureCount'], 256, 'entry raw fixtureCount') == count
         and type(packets['fixtures']) is list and len(packets['fixtures']) == count, 'complete raw entry corpus')
    compare = Compare()
    counts = {'modelFixtures': 0, 'hostRejected': 0, 'entryWindows': 0, 'separated': 0,
              'initialPenetrations': 0, 'expectedModelFailures': 0, 'audits': 0,
              'certifiedLeaves': 0, 'partitionLeaves': 0, 'frontierLeaves': 0,
              'lastMeshRows': 0, 'lastMeshCandidates': 0, 'maximumSourceCount': 0,
              'maximumAuditCount': 0, 'maximumPartitionCount': 0,
              'maximumCertifiedLeafCount': 0, 'maximumFrontierCount': 0}
    prior = []
    for index, (fixture, record) in enumerate(zip(source['fixtures'], packets['fixtures'])):
        label = f'entry[{index}]'
        fields(record, RECORD_KEYS, label)
        compare.equal(record['name'], fixture['name'], label + '.name')
        source_input, result = fixture['input'], fixture['result']
        query, originals = query_values(source_input), source_values(source_input)
        compare.packet(record['input'], record['inputBits'], query, label + '.input')
        need(type(record['triangles']) is list and type(record['triangleBits']) is list
             and len(record['triangles']) == len(record['triangleBits']) == len(originals), 'complete source echo')
        for n, (actual, raw_bits, expected) in enumerate(zip(record['triangles'], record['triangleBits'], originals)):
            compare.packet(actual, raw_bits, expected, label + f'.triangle[{n}]')
        compare.packet(record['outputBefore'], record['outputBeforeBits'], prior, label + '.outputBefore')
        begin, append, exchange, phase = host_path(source_input)
        for key, expected in [('beginStatus', begin), ('exchangeStatus', exchange)]:
            need(type(record[key]) is int and record[key] == expected, label + '.' + key)
        compare.equal(record['appendStatuses'], append, label + '.appendStatuses')
        compare.equal(record['failedPhase'], phase, label + '.failedPhase')
        optional_fields = ['summary', 'echo', 'current', 'initial', 'bestWitness', 'window', 'lastMeshSummary']
        matrix_fields = [('sources', 'sourceBits'), ('audits', 'auditBits'), ('leaves', 'leafBits'),
                         ('partition', 'partitionBits'), ('frontier', 'frontierBits'), ('candidateIds', 'candidateIdBits')]
        if exchange:
            counts['hostRejected'] += 1
            compare.equal(record['hostFailurePreserved'], True, label + '.preserved')
            for key in optional_fields:
                compare.packet(record[key], record[key + 'Bits'], None, label + '.' + key)
            for key, raw_key in matrix_fields:
                compare.equal(record[key], [], label + '.' + key)
                compare.equal(record[raw_key], [], label + '.' + raw_key)
            compare.equal(record['lastMeshRows'], [], label + '.lastMeshRows')
            compare.packet(record['outputAfter'], record['outputAfterBits'], prior, label + '.outputAfter')
            continue
        counts['modelFixtures'] += 1
        counts['entryWindows'] += result['status'] == 'entry_window'
        counts['separated'] += result['status'] == 'separated'
        counts['initialPenetrations'] += result['status'] == 'initial_penetration'
        counts['expectedModelFailures'] += result['status'] not in {'entry_window', 'separated', 'initial_penetration'}
        compare.equal(record['hostFailurePreserved'], None, label + '.noHostFailure')
        compare.packet(record['summary'], record['summaryBits'], header(result, len(originals)), label + '.header')
        compare.packet(record['echo'], record['echoBits'], query, label + '.echo')
        last = query
        matrices = [('sources', 'sourceBits', source_packets(source_input, result['lastMesh'])),
                    ('audits', 'auditBits', [audit_packet(a, i) for i, a in enumerate(result['audits'])]),
                    ('leaves', 'leafBits', [legacy.leaf_packet(leaf) for leaf in result['certifiedLeaves']]),
                    ('partition', 'partitionBits', [partition_packet(p, i) for i, p in enumerate(result['partition'])]),
                    ('frontier', 'frontierBits', [[i] + cell(c) for i, c in enumerate(result['frontier'])])]
        for key, raw_key, expected_rows in matrices:
            need(type(record[key]) is list and type(record[raw_key]) is list
                 and len(record[key]) == len(record[raw_key]) == len(expected_rows), label + '.' + key + ': complete rows')
            for n, (actual, raw_bits, expected) in enumerate(zip(record[key], record[raw_key], expected_rows)):
                compare.packet(actual, raw_bits, expected, label + f'.{key}[{n}]')
                last = expected
        optional_values = [('current', [0] + cell(result['current']) if result['current'] is not None else None),
                           ('initial', initial_packet(result['initial']) if result['initial'] is not None else None),
                           ('bestWitness', legacy.witness_packet(result['bestWitness']) if result['bestWitness'] is not None else None),
                           ('window', window_packet(result['window']) if result['window'] is not None else None)]
        for key, expected in optional_values:
            compare.packet(record[key], record[key + 'Bits'], expected, label + '.' + key)
            if expected is not None:
                last = expected
        ids = [[i, identifier] for i, identifier in enumerate(result['candidateSurfaceIds'])]
        need(type(record['candidateIds']) is list and type(record['candidateIdBits']) is list
             and len(record['candidateIds']) == len(record['candidateIdBits']) == len(ids), 'all conservative source IDs')
        for n, (actual, raw_bits, expected) in enumerate(zip(record['candidateIds'], record['candidateIdBits'], ids)):
            compare.packet(actual, raw_bits, expected, label + f'.candidateIds[{n}]')
            last = expected
        mesh = result['lastMesh']
        mesh_summary = mesh_header(mesh, len(originals)) if mesh is not None else None
        compare.packet(record['lastMeshSummary'], record['lastMeshSummaryBits'], mesh_summary, label + '.lastMeshSummary')
        if mesh_summary is not None:
            last = mesh_summary
        rows = mesh['rows'] if mesh is not None else []
        need(type(record['lastMeshRows']) is list and len(record['lastMeshRows']) == len(rows), 'all last mesh actual rows')
        for n, (row, actual_row) in enumerate(zip(rows, record['lastMeshRows'])):
            fields(actual_row, ['rowOrdinal', 'packet', 'bits', 'candidates', 'candidateBits'], 'last mesh row packet')
            need(type(actual_row['rowOrdinal']) is int and actual_row['rowOrdinal'] == n, 'last row original ordinal')
            compare.equal(row['triangle'], source_input['triangles'][n], label + f'.lastMeshSource[{n}]')
            q = row['query']
            expected = primitive_packet(q, row['triangle']['id']) if q is not None else None
            compare.packet(actual_row['packet'], actual_row['bits'], expected, label + f'.lastMeshRow[{n}]')
            if expected is not None:
                last = expected
            candidates = q['candidates'] if q is not None else []
            need(type(actual_row['candidates']) is list and type(actual_row['candidateBits']) is list
                 and len(actual_row['candidates']) == len(actual_row['candidateBits']) == len(candidates), 'complete last-row candidate prefix')
            for c, (actual, raw_bits, candidate) in enumerate(zip(actual_row['candidates'], actual_row['candidateBits'], candidates)):
                expected = candidate_packet(candidate)
                compare.packet(actual, raw_bits, expected, label + f'.lastMeshCandidate[{n}][{c}]')
                last = expected
            counts['lastMeshRows'] += 1
            counts['lastMeshCandidates'] += len(candidates)
        compare.packet(record['outputAfter'], record['outputAfterBits'], last, label + '.outputAfter')
        prior = last
        for key, target in [('audits', 'audits'), ('certifiedLeaves', 'certifiedLeaves'),
                            ('partition', 'partitionLeaves'), ('frontier', 'frontierLeaves')]:
            counts[target] += len(result[key])
        for key, value in [('maximumSourceCount', len(originals)), ('maximumAuditCount', len(result['audits'])),
                           ('maximumPartitionCount', len(result['partition'])),
                           ('maximumCertifiedLeafCount', len(result['certifiedLeaves'])),
                           ('maximumFrontierCount', len(result['frontier']))]:
            counts[key] = max(counts[key], value)
    need(integer(packets['accepted'], count, 'accepted') == counts['modelFixtures']
         and integer(packets['hostRejected'], count, 'hostRejected') == counts['hostRejected'], 'actual exchange classification totals')
    need(counts['modelFixtures'] + counts['hostRejected'] == count, 'entire entry corpus classified')
    return {**counts, 'wireNumericComparisons': compare.numeric_count,
            'negativeZeroComparisons': compare.negative_zeros}


def negative_controls(source, packets):
    """Captured-packet mutations only; semantic edits also repair their bit echo."""
    records = []
    fixtures = packets['fixtures']

    def choose(predicate):
        return next(i for i, r in enumerate(fixtures) if predicate(r))

    def add(name, change):
        altered = copy.deepcopy(packets)
        change(altered)
        try:
            verify_packets(source, altered)
        except (AssertionError, TypeError, ValueError, KeyError, IndexError) as error:
            records.append({'name': name, 'rejected': True, 'diagnostic': str(error)[:240]})
        else:
            raise AssertionError('entry raw corruption accepted: ' + name)

    def set_packet(p, index, key, raw_key, slot, value):
        r = p['fixtures'][index]
        r[key][slot], r[raw_key][slot] = value, bits(value)

    def set_matrix(p, index, key, raw_key, row, slot, value):
        r = p['fixtures'][index]
        r[key][row][slot], r[raw_key][row][slot] = value, bits(value)

    accepted = choose(lambda r: r['exchangeStatus'] == 0)
    initial = choose(lambda r: r['initial'] is not None)
    window = choose(lambda r: r['window'] is not None)
    witness = choose(lambda r: r['bestWitness'] is not None and r['bestWitness'][14] != 0)
    capacity = choose(lambda r: len(r['audits']) == 256)
    frontier = choose(lambda r: len(r['frontier']) > 33)
    ids = choose(lambda r: len(r['candidateIds']) == 64)
    host = choose(lambda r: r['exchangeStatus'] != 0)
    rows = choose(lambda r: bool(r['lastMeshRows']))
    add('unknown envelope field', lambda p: p.update({'unexpected': 0}))
    add('fixed corpus tail omitted', lambda p: p['fixtures'].pop())
    add('header initial flag invalid', lambda p: set_packet(p, accepted, 'summary', 'summaryBits', 7, 2))
    add('header count fractional', lambda p: set_packet(p, accepted, 'summary', 'summaryBits', 11, .5))
    add('header reserved negative zero', lambda p: set_packet(p, accepted, 'summary', 'summaryBits', 39, -0.0))
    add('header work exact forged false', lambda p: set_packet(p, accepted, 'summary', 'summaryBits', 34, 0))
    add('echo tolerance changed', lambda p: set_packet(p, accepted, 'echo', 'echoBits', 19, .75))
    add('initial owner moved', lambda p: set_packet(p, initial, 'initial', 'initialBits', 5, 1))
    add('initial certificate erased', lambda p: set_packet(p, initial, 'initial', 'initialBits', 1, 0))
    add('window width erased', lambda p: set_packet(p, window, 'window', 'windowBits', 4, 0))
    add('window owner moved', lambda p: set_packet(p, window, 'window', 'windowBits', 5, 0))
    add('witness E omitted', lambda p: set_packet(p, witness, 'bestWitness', 'bestWitnessBits', 14, 0))
    add('witness parameter moved', lambda p: set_packet(p, witness, 'bestWitness', 'bestWitnessBits', 4, 0))
    add('audit256 tail omitted', lambda p: (p['fixtures'][capacity]['audits'].pop(), p['fixtures'][capacity]['auditBits'].pop()))
    add('audit reserved negative zero', lambda p: set_matrix(p, capacity, 'audits', 'auditBits', -1, 63, -0.0))
    add('initial audit kind replaced by cell', lambda p: set_matrix(p, capacity, 'audits', 'auditBits', 0, 1, 1))
    add('initial audit parameter moved', lambda p: set_matrix(p, capacity, 'audits', 'auditBits', 0, 5, .5))
    add('partition128 tail omitted', lambda p: (p['fixtures'][capacity]['partition'].pop(), p['fixtures'][capacity]['partitionBits'].pop()))
    add('partition owner changed', lambda p: set_matrix(p, capacity, 'partition', 'partitionBits', -1, 6, 0))
    add('frontier truncated to old DFS33', lambda p: (p['fixtures'][frontier]['frontier'].__delitem__(slice(33, None)), p['fixtures'][frontier]['frontierBits'].__delitem__(slice(33, None))))
    add('conservative64 candidate IDs tail omitted', lambda p: (p['fixtures'][ids]['candidateIds'].pop(), p['fixtures'][ids]['candidateIdBits'].pop()))
    add('conservative candidate ID changed', lambda p: set_matrix(p, ids, 'candidateIds', 'candidateIdBits', 0, 1, 0))
    add('last mesh row tail omitted', lambda p: p['fixtures'][rows]['lastMeshRows'].pop())
    def candidate_tail(p):
        row = next(v for v in p['fixtures'][rows]['lastMeshRows'] if v['candidates'])
        row['candidates'].pop();row['candidateBits'].pop()
    add('last mesh candidate tail omitted', candidate_tail)
    add('host preservation flag false', lambda p: p['fixtures'][host].update({'hostFailurePreserved': False}))
    add('boolean F64 alias', lambda p: p['fixtures'][accepted]['summary'].__setitem__(0, True))
    add('raw bit integrity mismatch', lambda p: p['fixtures'][accepted]['summaryBits'].__setitem__(0, 'ffffffffffffffff'))
    return {'count': len(records), 'allRejected': all(r['rejected'] for r in records), 'controls': records,
            'scope': 'Duplicated raw packets only. No fault injection, model edit, or unknown-work exception execution.'}


def rows_text(fixtures):
    lines = ['pikapika_sphere_triangle_mesh_entry_sdk 1', f'cases {len(fixtures)}']
    for fixture in fixtures:
        name, q = fixture['name'], fixture['input']
        need(type(name) is str and legacy.re.fullmatch('[A-Za-z0-9_-]{1,96}', name), 'bounded ASCII identity')
        sources = source_values(q)
        lines.append(json.dumps(name) + ' ' + str(len(sources)) + ' ' + ' '.join(signed_json(v) for v in query_values(q)))
        lines.extend(' '.join(signed_json(v) for v in source) for source in sources)
    need(all(len(line.encode('ascii')) <= 4096 for line in lines), 'bounded ASCII probe lines')
    return ('\n'.join(lines) + '\n').encode('ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures')
    parser.add_argument('probe', help='Native executable, or - when --packets is supplied')
    parser.add_argument('output', help='fresh output directory')
    parser.add_argument('--packets', help='captured raw packets; skips Native probe invocation')
    parser.add_argument('--scope', choices=['native', 'wasm-wire'], default='native')
    args = parser.parse_args()
    need(__debug__, 'run entry exchange checker without Python -O')
    directory = Path(args.output).resolve();directory.mkdir(parents=True, exist_ok=False)
    source = reference.load(args.fixtures)
    # This freezes all 65 inputs and verifies the original pure numerical data.
    # It does not silently turn three host rejects into exchange model results.
    exact_reference = reference.verify(source)
    write_new(directory / 'inputs.rows', rows_text(source['fixtures']))
    if args.packets:
        raw = Path(args.packets).read_bytes()
        invocation = {'mode': 'captured-packets', 'path': str(Path(args.packets).resolve())}
    else:
        need(args.scope == 'native', 'WASM scope requires --packets')
        command = [str(Path(args.probe).resolve()), '--rows', str(directory / 'inputs.rows')]
        with (directory / 'probe.stdout.json').open('xb') as stdout, (directory / 'probe.stderr.txt').open('xb') as stderr:
            completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=180, check=False)
        need(completed.returncode == 0, 'Native entry probe failed; raw stdout/stderr preserved')
        raw = (directory / 'probe.stdout.json').read_bytes()
        invocation = {'mode': 'native-probe', 'command': command, 'exitCode': completed.returncode}
    need(len(raw) <= 64 * 1024 * 1024, 'bounded complete raw entry stream')
    write_new(directory / 'packets.json', raw)
    packets = reference.loads(raw)
    stats = verify_packets(source, packets)
    controls = negative_controls(source, packets)
    write_new(directory / 'reference.json', json.dumps(exact_reference, indent=2) + '\n')
    write_new(directory / 'packet-negative-controls.json', json.dumps(controls, indent=2) + '\n')
    command = [sys.executable, '-X', 'utf8', str(HERE.parent / 'tests/sphere_triangle_mesh_entry_reference_tests.py'),
               str(Path(args.fixtures).resolve()), '--output', str(directory / 'mathematical-negative-controls')]
    with (directory / 'math-negative.stdout.txt').open('xb') as stdout, (directory / 'math-negative.stderr.txt').open('xb') as stderr:
        mathematical = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=240, check=False)
    need(mathematical.returncode == 0, 'original 65-input mathematical negative suite failed; raw output preserved')
    negative = reference.loads((directory / 'math-negative.stdout.txt').read_bytes())
    report = {'schema': 1, 'status': 'PASS', 'scope': args.scope, 'fixtureCount': len(source['fixtures']),
              **stats, 'reference': exact_reference, 'packetNegativeControls': controls,
              'mathematicalNegativeControls': negative, 'source': file_info(Path(args.fixtures)),
              'invocation': invocation, 'mathematicalInvocation': {'command': command, 'exitCode': mathematical.returncode},
              'referenceScope': 'Original pinned 65 pure Native results were independently checked. Every exchange-accepted complete model DTO field is independently encoded and bit-compared with captured packets. Host-rejected cases remain pure source mathematical inputs; no claim that all 65 are replayed model calls or decoded WASM DTOs.',
              'limitations': 'Raw C ABI only. Public JavaScript owned entry wrapper is unimplemented. No UI, World, TOI, response, or allocator/unknown-work fault injection.', 'files': {}}
    report['checkerSources'] = {name: file_info(HERE / name) for name in [
        Path(__file__).name, 'verify-sphere-triangle-mesh-trajectory-native-sdk.py',
        'verify-sphere-triangle-mesh-entry.py', 'verify-sphere-triangle-mesh-trajectory.py',
        'verify-sphere-triangle-mesh.py', 'verify-sphere-triangle.py']}
    report['mathematicalNegativeSource'] = file_info(HERE.parent / 'tests/sphere_triangle_mesh_entry_reference_tests.py')
    for name in ['inputs.rows', 'packets.json', 'reference.json', 'packet-negative-controls.json',
                 'math-negative.stdout.txt', 'math-negative.stderr.txt']:
        report['files'][name] = file_info(directory / name)
    if not args.packets:
        report['probeExecutable'] = file_info(Path(args.probe))
        report['files']['probe.stderr.txt'] = file_info(directory / 'probe.stderr.txt')
    write_new(directory / 'report.json', json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
