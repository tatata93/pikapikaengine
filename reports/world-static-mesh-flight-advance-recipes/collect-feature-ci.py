"""Collect the earlier source publication's CI; not full advance acceptance."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-feature-ci-001'


def need(value, message):
    if not value:
        raise ValueError(message)


jobs = json.loads((OUT / 'jobs.json').read_text(encoding='utf8'))['jobs']
need(len(jobs) == 1, 'Expected one earlier portable-core job')
job = jobs[0]
need(job['id'] == 126790399324 and job['conclusion'] == 'success', 'Actual source job failed')
need(len(job['steps']) == 26 and all(s['conclusion'] == 'success' for s in job['steps']), 'Actual steps incomplete')
log = json.loads((OUT / 'decoded-job-log.json').read_text(encoding='utf8'))['content']
markers = {}
for name, pattern in {
    'ctest': r'100% tests passed, 0 tests failed out of 47',
    'nodeTests': r'# tests 684',
    'nodePass': r'# pass 684',
    'nodeFail': r'# fail 0',
    'nodeSkipped': r'# skipped 0',
}.items():
    matches = [line for line in log.splitlines() if re.search(pattern, line)]
    need(matches, 'Missing actual log marker ' + name)
    markers[name] = matches
records = []
for line in log.splitlines():
    body = re.sub(r'^\S+Z ', '', line)
    if body.startswith('{'):
        try:
            records.append(json.loads(body))
        except ValueError:
            pass
guard = [r for r in records if r.get('status') == 'PASS' and 'normalProfile' in r and 'sanitizedProfile' in r]
need(len(guard) == 1, 'Expected the actual final guard driver result')
guard = guard[0]
need(guard['normalProfile']['sourceSet'] == 'world-static-mesh-flight-advance-v1', 'Seven-source profile absent')
result = {
    'status': 'EARLIER_SOURCE_CI_PASS_FULL_ADVANCE_PENDING',
    'feature': '30894e35f6e3099bc66d8e95330a96da673ef41e',
    'run': 41891672385, 'job': job['id'], 'successfulStepsIncludingComplete': 26,
    'markers': markers,
    'guardProfile': guard['normalProfile'],
    'guardDriverStatus': guard['status'],
    'inputs': {name: {'bytes': (OUT / name).stat().st_size,
                      'sha256': hashlib.sha256((OUT / name).read_bytes()).hexdigest()}
               for name in ['jobs.json', 'decoded-job-log.json']},
    'advanceClock18ExecutedByThisJob': False,
    'advanceTransactions51ExecutedByThisJob': False,
    'fullAdvanceGNUAccepted': False,
    'scope': 'Actual prior portable-core all steps, CTest47 and Node684 plus existing guard driver. Full new advance clock/transaction sanitizer validation belongs to the new separate job. No Pages, browser or whole clock/commit proof implied.',
}
(OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: result[k] for k in ['status', 'run', 'successfulStepsIncludingComplete', 'fullAdvanceGNUAccepted']}))
