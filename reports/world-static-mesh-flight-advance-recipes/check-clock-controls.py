"""Run rejection controls against real Native clock fixture output (kept intact)."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if len(sys.argv) != 3:
    raise SystemExit('usage: check-clock-controls.py FIXTURES NEW_OUTPUT_DIRECTORY')
fixture = (ROOT / sys.argv[1]).resolve()
out = (ROOT / sys.argv[2]).resolve()
if not out.is_relative_to((ROOT / 'reports/world-static-mesh-flight-advance-checks').resolve()):
    raise SystemExit('output must be within advance checks')
out.mkdir(parents=True, exist_ok=False)
raw = fixture.read_bytes()
data = json.loads(raw)
success = next(i for i, x in enumerate(data['cases']) if x['output']['committed'])
failure = next(i for i, x in enumerate(data['cases']) if not x['output']['committed'])
checker = ROOT / 'reports/world-static-mesh-flight-advance-recipes/clock-reference.py'
records = []


def run(label, document, accepted, optimized=False):
    path = out / (label + '.json')
    path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf8')
    argv = [sys.executable, '-B', '-X', 'utf8']
    if optimized:
        argv.append('-O')
    argv.extend([str(checker), str(path)])
    completed = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    (out / (label + '.stdout.txt')).write_bytes(completed.stdout)
    (out / (label + '.stderr.txt')).write_bytes(completed.stderr)
    okay = (completed.returncode == 0) == accepted
    records.append({'name': label, 'expectedAccepted': accepted, 'exitCode': completed.returncode,
                    'passed': okay, 'argv': argv})
    if not okay:
        raise RuntimeError('control failed: ' + label)


def corrupt(label, index, key, value, optimized=False):
    mutated = deepcopy(data)
    mutated['cases'][index]['output'][key] = value
    run(label, mutated, False, optimized)


record = {'schema': 1, 'status': 'RUNNING', 'fixture': str(fixture),
          'fixtureBytes': len(raw), 'fixtureSha256': sha256(raw).hexdigest(),
          'checkerSha256': sha256(checker.read_bytes()).hexdigest(), 'commands': records,
          'scope': 'Checker rejection controls derived from real clock corpus; not additional Native physics executions.'}
try:
    run('original', data, True)
    reordered = deepcopy(data)
    reordered['cases'].reverse()
    for index, case in enumerate(reordered['cases']):
        case['name'] = 'independent-label-' + str(index)
    run('order-and-label-independent', reordered, True)
    corrupt('success-actual-time', success, 'actualTimeBits', 'bff0000000000000')
    corrupt('success-proposed-time', success, 'proposedTimeBits', 'bff0000000000000')
    corrupt('success-actual-ticks', success, 'actualTicks', data['cases'][success]['output']['actualTicks'] + 1)
    corrupt('success-advanced-horizon', success, 'advancedDtBits', '0000000000000000')
    corrupt('success-original-negative-zero', success, 'originalTimeBits', 'bff0000000000000')
    corrupt('success-requested-horizon', success, 'requestedDtBits', '0000000000000000')
    corrupt('success-profile-false', success, 'advanceProfileMatches', False)
    corrupt('success-counter-bool', success, 'guardQueriesAttempted', True)
    corrupt('success-counter-bool-optimized', success, 'guardQueriesAttempted', True, True)
    corrupt('failure-advanced-minus-zero', failure, 'advancedDtBits', '8000000000000000')
    corrupt('failure-time-mutated', failure, 'actualTimeBits', 'bff0000000000000')
    corrupt('failure-tick-mutated', failure, 'actualTicks', data['cases'][failure]['input']['ticks'] + 1)
    corrupt('failure-performed-query', failure, 'guardQueriesAttempted', 1)
    corrupt('failure-committed-clock', failure, 'progressAssignments', 1)
    for key in ['sum', 'difference', 'error']:
        altered = deepcopy(data)
        altered['cases'][success]['output']['clock'][key] = ['bff0000000000000', 'bff0000000000000']
        run('exact-expression-outside-' + key, altered, False)
    altered = deepcopy(data)
    altered['cases'][success]['output']['clock']['representedDtBits'] = 'bff0000000000000'
    run('represented-delta-corrupted', altered, False)
    altered = deepcopy(data)
    altered['schema'] = True
    run('schema-bool', altered, False)
    altered = deepcopy(data)
    altered['cases'][success]['input']['timeBits'] = '7ff0000000000000'
    run('nonfinite-input-bits', altered, False)
    record['status'] = 'PASS'
    record['positiveControls'] = sum(r['expectedAccepted'] for r in records)
    record['negativeControls'] = sum(not r['expectedAccepted'] for r in records)
    if fixture.read_bytes() != raw:
        raise RuntimeError('original Native fixture changed')
except Exception as error:
    record['status'] = 'FAIL'
    record['failure'] = {'type': type(error).__name__, 'message': str(error)}
    raise
finally:
    (out / 'controls.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
print(json.dumps({key: record[key] for key in ['status', 'positiveControls', 'negativeControls', 'scope']}))
