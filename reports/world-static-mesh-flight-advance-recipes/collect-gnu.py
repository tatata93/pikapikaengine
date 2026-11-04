"""Bind saved dedicated GNU job logs to exact source and finite checks.

The raw fixture files remain runner-local; this collects actual driver records
and their reported hashes, not a fabricated local copy of runner artifacts.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FEATURE = 'bb58cf2aff81a00c55f7034dccf153c268824df4'
RUN, JOB = 41895203663, 126802750687
BASE = ROOT / 'reports/world-static-mesh-flight-advance-public-checks'
OUT = BASE / 'run-20261105-gnu-001'
COMMANDS = ['actual-compiler-version', 'actual-compiler-dumpversion', 'actual-compiler-target',
    'normal-seven-source-artifact-audit', 'new-warning-tu-0', 'new-warning-tu-1', 'new-warning-tu-2',
    'normal-nine-groups', 'normal-clock-fixtures', 'normal-clock-integer-reference', 'normal-guard51',
    'normal-guard-independent-math', 'normal-guard-independent-controls', 'normal-full-transactions',
    'normal-transaction-independent-reference', 'normal-transaction-independent-controls',
    'debug-configure', 'debug-build-both', 'debug-advance-profile0-refusal', 'debug-guard-profile0-refusal',
    'sanitizer-configure', 'sanitizer-build-all-core-and-three-harnesses', 'sanitized-nine-groups',
    'sanitized-clock-fixtures', 'sanitized-clock-integer-reference', 'sanitized-guard51',
    'sanitized-guard-independent-math', 'sanitized-guard-independent-controls', 'sanitized-full-transactions',
    'sanitized-transaction-independent-reference', 'sanitized-transaction-independent-controls']


def need(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def main():
    result = {'status': 'FAIL', 'feature': FEATURE, 'run': RUN, 'job': JOB,
              'observedUTC': datetime.now(timezone.utc).isoformat()}
    try:
        original = load(OUT / 'decoded-job-log.json')
        need(original['run'] == RUN and original['job'] == JOB, 'Decoded log wrapper linkage')
        log = original['content']
        need('SOURCE_SHA: ' + FEATURE in log and 'Complete job name: native-world-advance' in log,
             'Actual log source/job linkage')
        need('##[error]' not in log, 'Actions error annotation')
        jobs = load(BASE / 'run-20261105-jobs-001/engine-jobs.json')
        job = [x for x in jobs['jobs'] if x['id'] == JOB]
        need(len(job) == 1, 'Unique raw REST job')
        job = job[0]
        need(job['run_id'] == RUN and job['head_sha'] == FEATURE and job['name'] == 'native-world-advance'
             and job['status'] == 'completed' and job['conclusion'] == 'success', 'Completed exact source job')
        names = ['Set up job', 'Fetch exact public source commit', 'Build bounded Native advance targets on GNU 13',
                 'Audit Native World advance independently', 'Complete job']
        need([s['name'] for s in job['steps']] == names and
             all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps']), 'Actual ordered steps')
        duration = (datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00')) -
                    datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))).total_seconds()
        need(0 < duration < 1200, 'Actual dedicated job within initial20min budget')
        records = []
        for line in log.splitlines():
            body = re.sub(r'^\ufeff?\S+Z\s+', '', line)
            if body.startswith('{'):
                try:
                    records.append(json.loads(body))
                except ValueError:
                    pass
        matches = [x for x in records if x.get('kind') == 'gnu13-seven-source-advance-ci']
        need(len(matches) == 1, 'Unique actual driver result')
        r = matches[0]
        need(r['status'] == 'PASS' and r['actualGNUExecuted'] is True and r['clockCommitFormalMachineProof'] is False,
             'Finite real GNU success without full machine proof')
        need(r['normalBuildReconfiguredOrBuilt'] is False and
             all(r[k] is True for k in ['sourceStable', 'normalArtifactsStable', 'compilerStable']), 'Protected provenance')
        recipe = subprocess.check_output(['git', 'show', FEATURE + ':reports/world-static-mesh-flight-advance-recipes/verify-gnu.py'], cwd=ROOT)
        need(r['recipe']['bytes'] == len(recipe) and r['recipe']['sha256'] == sha256(recipe).hexdigest(), 'Exact published recipe bytes')
        need(r['actualCompilerVersion'] == '13.3.0' and r['actualCompilerTarget'] == 'x86_64-linux-gnu', 'Observed compiler')
        need([c['name'] for c in r['commands']] == COMMANDS and all(c['exitCode'] == 0 for c in r['commands']), 'All31 actual commands')
        for c in r['commands']:
            for field in ['stdout', 'stderr']:
                need(type(c[field]['bytes']) is int and c[field]['bytes'] >= 0 and
                     re.fullmatch('[0-9a-f]{64}', c[field]['sha256']), 'Actual child stream metadata')
        for profile, expected in [('normalProfile', 1), ('sanitizedProfile', 1), ('debugProfile', 0)]:
            p = r[profile]
            need(p['sourceSet'] == 'world-static-mesh-flight-advance-v1' and p['profile'] == expected and len(p['sources']) == 7,
                 'Seven-source explicit profile state')
            for s in p['sources']:
                blob = subprocess.check_output(['git', 'show', FEATURE + ':' + s['path']], cwd=ROOT)
                need(sha256(blob).hexdigest() == s['sha256'], 'Configured actual source hash')
        need(r['normalProfile']['buildId'] != r['sanitizedProfile']['buildId'], 'Distinct actual instrumented identity')
        need(r['advanceAssertionGroupsPerBuild'] == 9 and r['clockCasesPerBuild'] == 18 and
             r['transactionFixturesPerBuild'] == 51 and r['libraryTranslationUnits'] == 40 and
             r['harnessCompileCommandsPerBuild'] == 17 and r['warningTranslationUnits'] == 3, 'Actual finite counts')
        for name in ['normal', 'sanitized']:
            clock, reference, controls = r['clockReferences'][name], r['transactionReferences'][name], r['transactionControls'][name]
            need(clock['status'] == 'PASS' and (clock['cases'], clock['committed'], clock['rejected'], clock['selfTests']) == (18, 7, 11, 11), 'Clock reference')
            need(reference['status'] == 'PASS' and (reference['fixtures'], reference['committed'], reference['failed'], reference['actualOwnedGuardsVerified'], reference['committedBodiesCompared'], reference['guard']['childCalls']) == (51, 14, 37, 50, 32, 180), 'Transaction reference')
            need(controls['status'] == 'PASS' and controls['selfTestGroups'] == 14 and controls['negativeControls'] == 85
                 and controls['labelAndOrderIndependent'] is True, 'Actual reference controls')
        need(r['clockComparison']['status'] == 'PASS' and r['clockComparison']['normalization'] == 'NONE', 'Whole clock comparison')
        need(r['transactionComparison']['status'] == 'PASS' and r['transactionComparison']['normalizedPaths'] == [
            'fixtures[*].report.binding.buildId', 'fixtures[*].report.guard.binding.buildId iff guard is nonnull'], 'Precisely two identity paths')
        result.update(status='GNU_FINITE_ADVANCE_PASS', actualJobSeconds=duration, actualCommands=len(COMMANDS),
            driverResult=r, inputs=[stamp(OUT / 'decoded-job-log.json'), stamp(BASE / 'run-20261105-jobs-001/engine-jobs.json')],
            completeClockCommitMachineProof=False, publicPortableCoreComplete=False,
            scope='Actual dedicated GNU13 normal, Debug and all40core plus17harness compile commands O1 ASan/UBSan. Both9/18/51 and independent14self/85negative references/comparisons succeeded. Raw child fixtures/artifacts remain runner-local; their metadata and parsed reference outputs are bound to actual success log, not separately downloaded raw artifacts. Separate portable-core and final public aggregation still pending; no SDK/response/FPS or whole machine proof.')
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    path = ROOT / 'reports/world-static-mesh-flight-advance-gnu-verification.json'
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ['status', 'actualJobSeconds', 'actualCommands', 'error'] if k in result}))
    return 0 if result['status'] == 'GNU_FINITE_ADVANCE_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
