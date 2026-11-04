"""Independent full Native advance transaction audit; never calls production.

The fixed sources are the previously accepted guard51 inputs. Actual returned
guard children are re-enveloped into the protected Fraction/metadata checker.
Clock expectations use integer ties-even/Fraction, not host floating addition.
Pointer booleans and sizeof remain Native observations, not machine proofs.
"""
from pathlib import Path
from fractions import Fraction
import copy
import importlib.util
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


guard = module('advance_guard_reference', ROOT / 'scripts/verify-world-static-mesh-flight-guard.py')
clock = module('advance_clock_reference', ROOT / 'reports/world-static-mesh-flight-advance-recipes/clock-reference.py')
need, fields, uint = guard.need, guard.fields, guard.uint
load, loads, bits = guard.load, guard.loads, guard.bits
fraction = guard.fraction
RESULT_KEYS = {'status','reason','committed','requestedDt','advancedDt','originalProgress',
               'proposedProgress','clock','binding','advanceProfileChecked','advanceProfileMatches',
               'failure','guard','guardMessage','work','storage','message'}
WORK_KEYS = {'guardQueriesAttempted','guardQueriesReturned','pairRecordsChecked','callRecordsChecked',
             'originBodiesChecked','originPlanesChecked','originMeshesChecked','originFacesChecked',
             'candidatesCopied','candidateValidationsAttempted','candidatesValidated',
             'destinationLookups','destinationsResolved','bodyAssignments','progressAssignments'}
STORAGE_KEYS = {'bodyBufferSlots','destinationSlots','bodyBufferSizeofBytes','destinationBufferSizeofBytes'}
STATUSES = {'committed','not_certified','invalid_input','unsupported_environment','numerical_failure'}
REASONS = {'none','environment','binding_unsupported','horizon','progress_time','progress_ticks','tick_limit',
           'time_overflow','time_limit','time_resolution','clock_enclosure','guard_failed','guard_incomplete',
           'origin_mismatch','candidate_mismatch','candidate_validation','destination_mismatch',
           'allocation_failure','unexpected_exception'}
STAGES = {'environment','binding','clock','guard','commit_preparation','candidate_validation'}
ROW_KEYS = {'name','input','inputAfter','worldBefore','worldAfter','progressBefore','progressAfter','report','observations'}
OBSERVATION_KEYS = {'captureComplete','advanceCalls','sourceUnchanged','settingsUnchanged','horizonUnchanged',
                    'planesUnchanged','gravityUnchanged','worldUnchanged','progressUnchanged',
                    'failureAtomicObserved','pointerStability'}
INITIAL_PROGRESS = {'time': .125, 'ticks': 17}


def equal(a, b, label):
    guard.equal(a, b, label)


def boolean(value, label):
    need(type(value) is bool, label+' strict boolean')


def text(value, label):
    need(type(value) is str, label+' string')
    value.encode('utf-8', errors='strict')


def finite_tree(value, depth=0):
    need(depth <= 100, 'bounded finite tree depth')
    if type(value) is dict:
        for key, child in value.items():
            text(key, 'object key')
            finite_tree(child, depth+1)
    elif type(value) is list:
        for child in value:
            finite_tree(child, depth+1)
    elif type(value) in (int, float):
        fraction(value)
    else:
        need(value is None or type(value) in (bool, str), 'JSON scalar type')
        if type(value) is str:
            text(value, 'text')


def progress_shape(value):
    fields(value, {'time','ticks'}, 'Progress')
    fraction(value['time'])
    uint(value['ticks'], 2**53-1, 'canonical Progress ticks')


def world_shape(value):
    fields(value, {'bodies','planes','gravity'}, 'complete World')
    need(type(value['bodies']) is list and type(value['planes']) is list, 'World source arrays')
    for body in value['bodies']:
        guard.prep.body_shape(body)
    for plane in value['planes']:
        guard.prep.plane_shape(plane)
    guard.prep.vector(value['gravity'])


def binding_shape(value):
    fields(value, {'mode','state','checked','profile','buildId'}, 'binding')
    need(value['mode'] == 'source_enforced' and value['state'] == 'ready',
         'actual configured corpus cannot substitute profile refusals')
    boolean(value['checked'], 'binding checked')
    need(value['checked'], 'binding actually checked')
    uint(value['profile'], 1, 'binding profile')
    need(value['profile'] == 1 and type(value['buildId']) is str and
         re.fullmatch('[0-9a-f]{64}', value['buildId']), 'owned profile identity, not artifact proof')


def failure_shape(value):
    if value is None:
        return
    fields(value, {'stage','object'}, 'failure')
    need(type(value['stage']) is str and value['stage'] in STAGES, 'known failure stage')
    if value['object'] is not None:
        v = value['object']
        fields(v, {'kind','index','faceIndex'}, 'failure location')
        need(type(v['kind']) is str and v['kind'] in {'settings','world','body','plane','mesh','face'}, 'known typed failure kind')
        for key in ('index','faceIndex'):
            if v[key] is not None:
                uint(v[key], 2**64-1, 'canonical failure ordinal')


def predicted_clock(original, horizon):
    """Use original input bits and exact rational addition, including RN ties."""
    progress_shape(original)
    t, h, ticks = fraction(original['time']), fraction(horizon), original['ticks']
    if not 0 < h <= fraction(.1):
        return 'invalid_input', 'horizon', None
    if not 0 <= t <= 10**9:
        return 'invalid_input', 'progress_time', None
    if ticks == 2**53-1:
        return 'invalid_input', 'tick_limit', None
    proposed_bits = clock.rn(t+h)
    proposed = clock.number(proposed_bits)
    if proposed > 10**9:
        return 'invalid_input', 'time_limit', None
    if proposed <= t:
        return 'not_certified', 'time_resolution', None
    return None, None, {'bits': proposed_bits, 'time': proposed, 'ticks': ticks+1}


def clock_audit(value, original, horizon, proposal):
    fields(value, {'timeSum','representedDifference','sumRoundingError','representedDt'}, 'complete clock audit')
    t, h, new = fraction(original['time']), fraction(horizon), proposal['time']
    for key, exact in [('timeSum', t+h), ('representedDifference', new-t), ('sumRoundingError', new-(t+h))]:
        interval = value[key]
        need(type(interval) is list and len(interval) == 2, 'clock interval pair')
        lo, hi = map(fraction, interval)
        need(lo <= exact <= hi, 'exact clock expression contained: '+key)
    need(bits(value['representedDt']).hex() == clock.rn(new-t), 'integer-RN represented clock difference')


def pointer_observations(value, source):
    fields(value, {'bodyCountUnchanged','bodyStorageStable','planeStorageStable','meshStorageStable',
                   'bodies','meshFaceStorageStable'}, 'pointer observation fields')
    for key in ('bodyCountUnchanged','bodyStorageStable','planeStorageStable','meshStorageStable'):
        boolean(value[key], key)
        need(value[key], 'Native storage observation: '+key)
    need(type(value['bodies']) is list and len(value['bodies']) == len(source['bodies']), 'complete original body observations')
    for i, row in enumerate(value['bodies']):
        fields(row, {'ordinal','originalId','sameOrdinalAddress','sameLookupResult',
                     'lookupBeforeMatchesOrdinal','lookupAfterMatchesOrdinal'}, 'body address observations')
        uint(row['ordinal'], 2**64-1, 'pointer ordinal')
        uint(row['originalId'], 2**64-1, 'pointer source ID')
        need(row['ordinal'] == i and row['originalId'] == source['bodies'][i]['id'], 'original pointer mapping')
        first = next(j for j, body in enumerate(source['bodies']) if body['id'] == row['originalId'])
        expected = {'sameOrdinalAddress': True, 'sameLookupResult': True,
                    'lookupBeforeMatchesOrdinal': first == i, 'lookupAfterMatchesOrdinal': first == i}
        for key, wanted in expected.items():
            boolean(row[key], key)
            need(row[key] == wanted, 'stable pointer/find_body observation '+key)
    need(type(value['meshFaceStorageStable']) is list and len(value['meshFaceStorageStable']) == len(source['meshes']),
         'complete mesh face-vector pointer observations')
    for flag in value['meshFaceStorageStable']:
        boolean(flag, 'mesh source pointer')
        need(flag, 'mesh source pointer stable')


def new_stats():
    return {'fixtures': 0, 'committed': 0, 'failed': 0, 'clockRefusals': 0,
            'actualOwnedGuardsVerified': 0, 'committedBodiesCompared': 0,
            'pointerBodyObservations': 0, 'guard': guard.new_stats()}


def verify_fixture(row, layout, advance_layout, stats):
    fields(row, ROW_KEYS, 'complete transaction fixture')
    text(row['name'], 'fixture label')
    s, after, r = row['input'], row['inputAfter'], row['report']
    guard.source_shape(s)
    guard.source_shape(after)
    world_shape(row['worldBefore'])
    world_shape(row['worldAfter'])
    for key in ('progressBefore','progressAfter'):
        progress_shape(row[key])
    expected_before = {key: s[key] for key in ('bodies','planes','gravity')}
    equal(expected_before, row['worldBefore'], 'entire World before/source identity')
    expected_after = {key: after[key] for key in ('bodies','planes','gravity')}
    equal(expected_after, row['worldAfter'], 'entire World after/inputAfter identity')
    for key in ('planes','gravity','meshes','horizon','settings'):
        equal(s[key], after[key], 'borrowed source/settings/H unchanged: '+key)
    fields(r, RESULT_KEYS, 'complete AdvanceReport')
    need(type(r['status']) is str and r['status'] in STATUSES, 'known advance status')
    need(type(r['reason']) is str and r['reason'] in REASONS, 'known advance reason')
    for key in ('committed','advanceProfileChecked','advanceProfileMatches'):
        boolean(r[key], key)
    need(r['advanceProfileChecked'] and r['advanceProfileMatches'], 'configured real transaction, not refusal fill')
    binding_shape(r['binding'])
    text(r['message'], 'actual AdvanceReport message')
    failure_shape(r['failure'])
    fields(r['work'], WORK_KEYS, 'all 15 CommitWork counters')
    for key, value in r['work'].items():
        uint(value, 2**64-1, 'CommitWork '+key)
    fields(r['storage'], STORAGE_KEYS, 'all CommitStorage fields')
    for key, value in r['storage'].items():
        uint(value, 2**64-1, 'CommitStorage '+key)
    progress_shape(r['originalProgress'])
    equal(row['progressBefore'], r['originalProgress'], 'original Progress bits')
    equal(s['horizon'], r['requestedDt'], 'original requested H bits')
    clock_status, clock_reason, proposal = predicted_clock(row['progressBefore'], s['horizon'])
    expected_work = {key: 0 for key in WORK_KEYS}
    expected_storage = {key: 0 for key in STORAGE_KEYS}
    if proposal is None:
        need(r['status'] == clock_status and r['reason'] == clock_reason and not r['committed'], 'clock preflight priority/status')
        need(r['proposedProgress'] is r['clock'] is r['guard'] is r['guardMessage'] is None, 'clock refusal has no proposal/guard/diagnostic fill')
        equal({'stage':'clock','object':None}, r['failure'], 'clock failure stage')
        stats['clockRefusals'] += 1
    else:
        progress_shape(r['proposedProgress'])
        need(bits(r['proposedProgress']['time']).hex() == proposal['bits'] and
             r['proposedProgress']['ticks'] == proposal['ticks'], 'exact integer-RN proposal')
        clock_audit(r['clock'], row['progressBefore'], s['horizon'], proposal)
        need(r['guard'] is not None, 'valid finite clock must retain its actual returned owned guard')
        text(r['guardMessage'], 'actual outer GuardResult message')
        # No old Result supplies a replacement. Audit this transaction's actual
        # nested result against its own complete original input and same-run sizes.
        guard.verify_fixture(s, r['guard'], layout, stats['guard'])
        stats['actualOwnedGuardsVerified'] += 1
        stats['guard']['fixtures'] += 1
        equal(r['binding'], r['guard']['binding'], 'guard/advance owned binding identity')
        expected_work.update(guardQueriesAttempted=1, guardQueriesReturned=1)
        if r['guard']['status'] != 'certified_separated':
            need(r['status'] == r['guard']['status'] and r['reason'] == 'guard_failed' and not r['committed'],
                 'actual failed guard mapping, not a candidate prefix commit')
            equal({'stage':'guard','object':None}, r['failure'], 'guard failure stage')
        else:
            need(r['status'] == 'committed' and r['reason'] == 'none' and r['committed'] and r['failure'] is None,
                 'normal finite certified source fully commits')
            candidates = r['guard']['candidateBodies']
            count = len(s['bodies'])
            need(type(candidates) is list and len(candidates) == count, 'all body candidates including static/empty')
            committed = copy.deepcopy(candidates)
            for body in committed:
                body['force'] = [0.,0.,0.]
                body['torque'] = [0.,0.,0.]
            equal(committed, after['bodies'], 'every committed body field equals owned candidate except consumed +0 loads')
            expected_work.update(pairRecordsChecked=len(r['guard']['pairs']),
                callRecordsChecked=r['guard']['work']['childCallsAttempted'],
                originBodiesChecked=2*count, originPlanesChecked=2*len(s['planes']),
                originMeshesChecked=2*len(s['meshes']),
                originFacesChecked=2*sum(len(m['triangles']) for m in s['meshes']),
                candidatesCopied=count, candidateValidationsAttempted=count, candidatesValidated=count,
                destinationLookups=count, destinationsResolved=count, bodyAssignments=count, progressAssignments=1)
            expected_storage.update(bodyBufferSlots=8, destinationSlots=8,
                bodyBufferSizeofBytes=8*layout['rigidBody'], destinationBufferSizeofBytes=8*8)
            stats['committedBodiesCompared'] += count
    if r['committed']:
        equal(r['proposedProgress'], row['progressAfter'], 'actual Progress equals complete proposal')
        equal(s['horizon'], r['advancedDt'], 'actual requested H advanced, not represented difference')
        stats['committed'] += 1
    else:
        equal(s['bodies'], after['bodies'], 'failure preserves ALL body/load bits and original order')
        equal(row['progressBefore'], row['progressAfter'], 'failure preserves ALL Progress bits/ticks')
        need(bits(r['advancedDt']).hex() == '0000000000000000', 'failure advancedDt canonical +0')
        stats['failed'] += 1
    equal(expected_work, r['work'], 'all actual commit/preflight work counters')
    equal(expected_storage, r['storage'], 'fixed named buffer sizeof observations')
    o = row['observations']
    fields(o, OBSERVATION_KEYS, 'complete Native observations')
    uint(o['advanceCalls'], 1, 'actual outer advance calls')
    need(o['advanceCalls'] == 1, 'fresh one-call transaction')
    for key in ('captureComplete','sourceUnchanged','settingsUnchanged','horizonUnchanged','planesUnchanged','gravityUnchanged'):
        boolean(o[key], key)
        need(o[key], 'Native original-source observation '+key)
    unchanged_world = True
    try:
        equal(row['worldBefore'], row['worldAfter'], 'observed World equality')
    except AssertionError:
        unchanged_world = False
    unchanged_progress = True
    try:
        equal(row['progressBefore'], row['progressAfter'], 'observed Progress equality')
    except AssertionError:
        unchanged_progress = False
    for key, expected in [('worldUnchanged', unchanged_world), ('progressUnchanged', unchanged_progress)]:
        boolean(o[key], key)
        need(o[key] == expected, 'actual observation derived from full captured fields '+key)
    if r['committed']:
        need(o['failureAtomicObserved'] is None, 'failure-only observation not applicable after success')
    else:
        boolean(o['failureAtomicObserved'], 'failure observation')
        need(o['failureAtomicObserved'] and unchanged_world and unchanged_progress, 'actual failure atomic observation')
    pointer_observations(o['pointerStability'], s)
    stats['pointerBodyObservations'] += len(s['bodies'])
    stats['fixtures'] += 1


def verify(data):
    need(__debug__, 'Protected reference stack requires normal Python; optimized execution is not accepted')
    finite_tree(data)
    fields(data, {'schema','kind','scope','initialProgress','layoutSizes','advanceLayoutSizes','fixtures'}, 'advance fixture envelope')
    need(type(data['schema']) is int and data['schema'] == 1 and
         data['kind'] == 'world-static-mesh-flight-advance-transaction-fixtures', 'known schema/kind')
    text(data['scope'], 'serializer scope')
    progress_shape(data['initialProgress'])
    equal(INITIAL_PROGRESS, data['initialProgress'], 'fixed original Progress input')
    guard.layout_shape(data['layoutSizes'])
    fields(data['advanceLayoutSizes'], {'AdvanceReport','Progress','ClockAudit','CommitWork','CommitStorage'}, 'same-run new sizeof observations')
    for key, value in data['advanceLayoutSizes'].items():
        uint(value, 1048576, 'sizeof '+key)
        need(value > 0, 'positive observed sizeof')
    fixtures = data['fixtures']
    need(type(fixtures) is list and len(fixtures) == guard.EXPECTED_FIXTURE_COUNT, 'complete previously fixed guard51 source corpus')
    for row in fixtures:
        fields(row, ROW_KEYS, 'full fixture fields before fingerprint')
    fingerprint = guard.input_fingerprint(fixtures)
    need(fingerprint == guard.EXPECTED_INPUT_FINGERPRINT, 'all original source scalar types/bits/order; label-independent multiset')
    stats, labels, identities = new_stats(), set(), set()
    for row in fixtures:
        text(row['name'], 'label')
        need(row['name'] and row['name'] not in labels, 'unique nonempty labels')
        labels.add(row['name'])
        equal(data['initialProgress'], row['progressBefore'], 'every fresh transaction begins at original Progress')
        verify_fixture(row, data['layoutSizes'], data['advanceLayoutSizes'], stats)
        identities.add(row['report']['binding']['buildId'])
    need(len(identities) == 1, 'one observed configuration per actual corpus; not a machine hash proof')
    return {'status':'PASS', **stats, 'inputFingerprint':fingerprint,
        'scope':'Actual complete original input/World/Progress and owned Report correspondence, integer/Fraction clock RN, all-or-none candidate commit with +0 load consumption, full failure bit preservation, Work and named-buffer storage metadata. Actual returned guard children use protected independent Fraction/metadata references; six box coordinates use exact quadratic extrema+B, downstream recorded-box RN/root proofs separately. Pointer booleans and sizeof are Native observations, not independently observable addresses or heap/stack bounds. Outer messages are retained strings; stripped child text is not reconstructed. No natural allocation/nonreturn fault injection, thread/CPU atomicity, complete clock/commit machine proof, contact response or SDK integration.'}


if __name__ == '__main__':
    need(len(sys.argv) == 2, 'Usage: verify-world-static-mesh-flight-advance.py FIXTURE.json')
    print(json.dumps(verify(load(sys.argv[1]))))
