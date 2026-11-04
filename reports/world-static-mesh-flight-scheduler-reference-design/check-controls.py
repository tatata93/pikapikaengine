"""Run selected-credit checker on actual prototype002 and compact patched controls.

Mutated inputs are retained in an ignored fresh build child. Exact ordered JSON
patches, source/input hashes and actual child stdout/stderr are retained here.
No nested AdvanceReport/physics acceptance is inferred.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-scheduler-credit.py'
INPUT = ROOT / 'reports/world-static-mesh-flight-scheduler-recipes/run-20261105-prototype-002/observations.json'
OUT = ROOT / 'reports/world-static-mesh-flight-scheduler-credit-checks/run-002'
TEMP = ROOT / 'build/wfs-credit-controls1'


def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def need(value, message):
    if not value:
        raise ValueError(message)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    TEMP.mkdir(parents=True, exist_ok=False)
    data = json.loads(INPUT.read_text(encoding='utf8'))
    before = [stamp(CHECKER), stamp(INPUT)]
    results = []

    def execute(name, path, success, optimized=False, patch=None):
        args = [sys.executable, '-B', '-X', 'utf8', *(['-O'] if optimized else []), str(CHECKER), str(path)]
        r = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=60)
        (OUT / (name + '.stdout.txt')).write_bytes(r.stdout)
        (OUT / (name + '.stderr.txt')).write_bytes(r.stderr)
        row = {'name': name, 'argv': args, 'exitCode': r.returncode, 'input': stamp(path),
               'expectedSuccess': success, 'patch': patch}
        results.append(row)
        need((r.returncode == 0) == success, 'Unexpected actual checker result ' + name)
        return json.loads(r.stdout)

    result = {'status': 'FAIL', 'UTC': datetime.now(timezone.utc).isoformat(), 'commands': results, 'inputs': before}
    try:
        baseline = execute('actual-baseline', INPUT, True)
        need(baseline['traces'] == len(data['traces']), 'All actual observations checked')
        good = next(i for i, t in enumerate(data['traces']) if t['report']['committed'] > 0)
        failed = next(i for i, t in enumerate(data['traces']) if t['report']['accepted'] and t['report']['attempts'] and t['report']['committed'] == 0)
        edits = [
            ('admitted-credit', good, ['report', 'admittedCreditBits'], '3ff0000000000000'),
            ('queue-proposal', good, ['report', 'queue', 0, 'proposedBits'], '3ff0000000000000'),
            ('queue-error', good, ['report', 'queue', 0, 'errorBits'], ['3ff0000000000000', '3ff0000000000000']),
            ('negative-zero-backlog', good, ['report', 'after', 'backlogBits'], '8000000000000000'),
            ('drop-negative-zero', good, ['report', 'dropBits'], '8000000000000000'),
            ('prefix-count', good, ['report', 'committed'], 8),
            ('progress-ticks', good, ['progressAfter', 'ticks'], 0),
            ('progress-time', good, ['progressAfter', 'timeBits'], '0000000000000000'),
            ('rejected-world-change', failed, ['worldAfterBits', 0], '0000000000000000'),
            ('source-change', good, ['sourceAfterBits', 0], '0000000000000000'),
            ('boolean-store-count', good, ['report', 'ticks', 0, 'bodyStores'], True),
            ('accepted-nan', good, ['report', 'elapsedBits'], '7ff8000000000000'),
            ('false-admission', good, ['report', 'accepted'], False),
            ('attempt-cap', good, ['report', 'before', 'maxAttempts'], 9),
        ]
        for name, index, path, value in edits:
            changed = deepcopy(data)
            parent = changed['traces'][index]
            for key in path[:-1]:
                parent = parent[key]
            need(parent[path[-1]] != value or type(parent[path[-1]]) is not type(value), 'Control actually changes value/type')
            parent[path[-1]] = value
            destination = TEMP / (name + '.json')
            destination.write_text(json.dumps(changed, separators=(',', ':')) + '\n', encoding='utf8')
            execute(name, destination, False, patch={'path': ['traces', index, *path], 'value': value})
        reordered = deepcopy(data)
        reordered['traces'].reverse()
        for row in reordered['traces']:
            row['name'] = 'independent-label'
        positive = TEMP / 'label-order.json'
        positive.write_text(json.dumps(reordered, separators=(',', ':')) + '\n', encoding='utf8')
        execute('label-order', positive, True, patch={'operation': 'reverse traces; replace every name with independent-label'})
        execute('optimized-refusal', INPUT, False, optimized=True)
        need(before == [stamp(CHECKER), stamp(INPUT)], 'Original source/input unchanged')
        result.update(status='SELECTED_CREDIT_FINITE_PASS', actual=baseline, rejectedControls=len(edits),
                      labelOrderIndependent=True, actualOptimizedRefusal=True, sourceInputStable=True,
                      scope='Actual Native prototype002 selected credit/queue/Progress transcript and14 altered controls. Full nested Report/child physics and complete successful World independent comparison are not present in selected serializer and remain separate gates. Not main integration, sanitizer, GNU scheduler or machine proof.')
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ['status', 'rejectedControls', 'error'] if k in result}))
    return 0 if result['status'] == 'SELECTED_CREDIT_FINITE_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
