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
# Actual final API metadata has all 26 rows, including terminal Complete job.
# This exercises metadata only, never successful-log collect() acceptance.
import re, subprocess
current_jobs_path = ROOT / 'reports/world-static-mesh-flight-guard-public-checks/run-20261105-gnu-acceptance-001/jobs.json'
current_jobs = m.load(current_jobs_path)
git_argv = ['git', 'show', commit + ':.github/workflows/verify.yml']
git = subprocess.run(git_argv, cwd=ROOT, capture_output=True, check=False)
(OUT / 'workflow-git.stdout.txt').write_bytes(git.stdout)
(OUT / 'workflow-git.stderr.txt').write_bytes(git.stderr)
m.write(OUT / 'workflow-git.command.json', {'argv': git_argv, 'exitCode': git.returncode,
        'stdout': stamp(OUT / 'workflow-git.stdout.txt'), 'stderr': stamp(OUT / 'workflow-git.stderr.txt')})
m.need(git.returncode == 0, 'Pinned workflow read')
expected = ['Set up job'] + re.findall(r'^      - name: (.+)$', git.stdout.decode('utf-8'), re.M)
m.need(len(expected) == 25, '25 required original workflow stages')
case('actual-final-api-26-rows-with-complete-job', lambda: m.select_job(current_jobs, 41883086801, 126760312295, expected), True)
without_cleanup = deepcopy(current_jobs)
job26 = next(x for x in without_cleanup['jobs'] if x['id'] == 126760312295)
m.need(len(job26['steps']) == 26 and job26['steps'][-1]['name'] == 'Complete job', 'Actual final metadata 26 rows')
job26['steps'].pop()
case('synthetic-api-shape-omits-only-terminal-complete', lambda: m.select_job(without_cleanup, 41883086801, 126760312295, expected), True)
missing = deepcopy(without_cleanup)
next(x for x in missing['jobs'] if x['id'] == 126760312295)['steps'].pop(8)
case('missing-required-middle-stage-rejected', lambda: m.select_job(missing, 41883086801, 126760312295, expected), False)
failed_cleanup = deepcopy(current_jobs)
next(x for x in failed_cleanup['jobs'] if x['id'] == 126760312295)['steps'][-1]['conclusion'] = 'failure'
case('failed-returned-complete-job-rejected', lambda: m.select_job(failed_cleanup, 41883086801, 126760312295, expected), False)
wrong_cleanup = deepcopy(current_jobs)
next(x for x in wrong_cleanup['jobs'] if x['id'] == 126760312295)['steps'][-1]['name'] = 'Unknown housekeeping'
case('unknown-returned-terminal-row-rejected', lambda: m.select_job(wrong_cleanup, 41883086801, 126760312295, expected), False)
wrong_number = deepcopy(current_jobs)
next(x for x in wrong_number['jobs'] if x['id'] == 126760312295)['steps'][-1]['number'] = 25
case('duplicate-terminal-number-rejected', lambda: m.select_job(wrong_number, 41883086801, 126760312295, expected), False)
after = {str(path): stamp(path) for path in watched}
result = {'schema': 1, 'status': 'PASS' if before == after and all(row['passed'] for row in results) else 'FAIL',
          'scope': 'Windows parser/metadata controls plus rejection of the actual saved failed/incomplete job. Actual final job metadata also checked (26 rows); no fabricated successful log and no full current successful GNU collector invocation.',
          'cases': results, 'groups': len(results), 'passed': sum(row['passed'] for row in results),
          'sourceBefore': before, 'sourceAfter': after, 'sourcesStable': before == after,
          'actualRestSelectionInput': {'path': str(runs_path), **stamp(runs_path)},
          'finalJobMetadataInput': {'path': str(current_jobs_path), **stamp(current_jobs_path)},
          'stepMetadataScope': '25 required stages plus actual final terminal Complete job makes 26. Optional-omission test is a labeled copied API shape, not a newly observed job.'}
m.write(OUT / 'result.json', result)
print(json.dumps({key: result[key] for key in ['status', 'groups', 'passed', 'sourcesStable', 'scope']}))
raise SystemExit(0 if result['status'] == 'PASS' else 1)
