"""Windows metadata/parser checks only; does not accept the new successful job."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = ROOT / 'reports/world-static-mesh-flight-guard-recipes/collect-gnu-public.py'
FAILURE = ROOT / 'reports/world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-failure-001'
watched = [SOURCE, Path(__file__).resolve(), FAILURE / 'decoded-job-log.json', FAILURE / 'jobs.json']


def stamp(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


before = {str(path): stamp(path) for path in watched}
(OUT / 'recipe.py.txt').write_bytes(SOURCE.read_bytes())
spec = importlib.util.spec_from_file_location('gnu_public_collector_driver', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
results = []


def case(name, action, accepted):
    row = {'name': name, 'expected': 'ACCEPT' if accepted else 'REJECT'}
    try:
        value = action()
    except (ValueError, TypeError, KeyError) as error:
        row.update(observed='REJECT', passed=not accepted, error=type(error).__name__ + ': ' + str(error))
    else:
        row.update(observed='ACCEPT', passed=accepted)
    results.append(row)
    m.write(OUT / 'cases' / (name + '.json'), row)


bad = m.load(FAILURE / 'decoded-job-log.json')
jobs = m.load(FAILURE / 'jobs.json')
old_sha = '462742caf805e94c557168d56c3f90851ca8bd73'
case('actual-old-failed-log-error-annotation-rejected', lambda: m.decoded_log(bad, bad['run'], bad['job'], old_sha), False)
case('actual-old-incomplete-failed-job-rejected', lambda: m.select_job(jobs, bad['run'], bad['job'], ['unavailable'] * 25), False)
for name, key, value in [('boolean-schema', 'schema', True), ('unknown-schema', 'schema', 2),
                         ('non-string-content', 'content', []), ('wrong-run', 'run', 1), ('wrong-job', 'job', 1)]:
    copy = deepcopy(bad); copy[key] = value
    case('wrapper-' + name, lambda copy=copy: m.decoded_log(copy, bad['run'], bad['job'], old_sha), False)
copy = deepcopy(bad); copy['unknown'] = 1
case('wrapper-unknown-field', lambda: m.decoded_log(copy, bad['run'], bad['job'], old_sha), False)
case('duplicate-json-key', lambda: m.loads('{"schema":1,"schema":1}'), False)
case('nonfinite-json', lambda: m.loads('{"x":NaN}'), False)
line = '2026-11-05T00:00:00Z /repo/core/src/example.cpp:7:9: warning: synthetic [-Wexample]'
case('synthetic-warning-format', lambda: m.need(m.warnings_from_lines([line]) ==
     [{'file': 'core/src/example.cpp', 'line': 7, 'column': 9, 'diagnostic': ' synthetic [-Wexample]'}], 'warning extraction'), True)
case('unknown-warning-format', lambda: m.warnings_from_lines(['unlocated warning: unknown']), False)
rows = m.warnings_from_lines([line, line])
case('multiset-keeps-duplicates', lambda: m.need(sum(m.warning_multiset(rows).values()) == 2, 'warning multiplicity'), True)
case('boolean-warning-line-rejected', lambda: m.warning_multiset([{'file': 'core/x', 'line': True, 'column': 1, 'diagnostic': 'x'}]), False)
case('prior-accepted-sphere-full-log-reextracts48', lambda: m.need(len(m.prior_warnings()) == 48, 'prior warning count'), True)
# Existing actual metadata is read, not invented. This checks selection alone;
# it never calls collect() on the newly successful current job/log.
runs_path = ROOT / 'reports/world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-final-status-001/runs.json'
runs = m.load(runs_path)
commit = 'd302f5b760307b8a3b023658d251bba3d023fc49'
case('actual-rest-list-exact-selection-only', lambda: m.select_run(runs, 41883086801, commit), True)
case('actual-rest-list-wrong-source-rejected', lambda: m.select_run(runs, 41883086801, '0' * 40), False)
run = next(x for x in runs['workflow_runs'] if x['id'] == 41883086801)
case('actual-single-run-selection-only', lambda: m.select_run(run, 41883086801, commit), True)
case('duplicated-run-selection-rejected', lambda: m.select_run({'total_count': 2, 'workflow_runs': [run, run]}, 41883086801, commit), False)
after = {str(path): stamp(path) for path in watched}
result = {'schema': 1, 'status': 'PASS' if before == after and all(row['passed'] for row in results) else 'FAIL',
          'scope': 'Windows parser/metadata controls plus rejection of the actual saved failed/incomplete job. No fabricated successful log and no full current successful GNU collector invocation.',
          'cases': results, 'groups': len(results), 'passed': sum(row['passed'] for row in results),
          'sourceBefore': before, 'sourceAfter': after, 'sourcesStable': before == after,
          'actualRestSelectionInput': {'path': str(runs_path), **stamp(runs_path)}}
m.write(OUT / 'result.json', result)
print(json.dumps({key: result[key] for key in ['status', 'groups', 'passed', 'sourcesStable', 'scope']}))
raise SystemExit(0 if result['status'] == 'PASS' else 1)
