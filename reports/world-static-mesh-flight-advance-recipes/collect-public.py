"""Collect exact source's final public finite acceptance from saved evidence.

No fetching, target execution, raw artifact reconstruction or new machine proof.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FEATURE = 'bb58cf2aff81a00c55f7034dccf153c268824df4'
BASE = ROOT / 'reports/world-static-mesh-flight-advance-public-checks'


def need(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def blob(path):
    return subprocess.check_output(['git', 'show', FEATURE + ':' + path], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.jobs, args.log, args.output = [p.resolve() for p in [args.jobs, args.log, args.output]]
    need(all(p.is_relative_to(BASE) for p in [args.jobs, args.log, args.output]), 'Advance public paths only')
    args.output.mkdir(parents=True, exist_ok=False)
    result = {'status': 'FAIL', 'feature': FEATURE, 'observedUTC': datetime.now(timezone.utc).isoformat()}
    try:
        run = load(args.jobs / 'engine-run.json')
        need(run['id'] == 41895203663 and run['head_sha'] == FEATURE and run['status'] == 'completed'
             and run['conclusion'] == 'success', 'Exact complete Engine run')
        jobs = load(args.jobs / 'engine-jobs.json')['jobs']
        need(len(jobs) == 2 and {j['name'] for j in jobs} == {'portable-core', 'native-world-advance'} and
             all(j['head_sha'] == FEATURE and j['run_id'] == run['id'] and j['status'] == 'completed'
                 and j['conclusion'] == 'success' for j in jobs), 'Both actual engine jobs')
        portable = next(j for j in jobs if j['name'] == 'portable-core')
        need(portable['id'] == 126802751106, 'Exact portable job')
        workflow = blob('.github/workflows/verify.yml').decode()
        section = workflow.split('  portable-core:\n', 1)[1].split('  native-world-advance:\n', 1)[0]
        expected = ['Set up job', *re.findall(r'^      - name: (.+)$', section, re.M), 'Complete job']
        need(len(expected) == 26 and [s['name'] for s in portable['steps']] == expected and
             all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in portable['steps']), 'All actual portable steps')
        decoded = load(args.log)
        need(decoded['run'] == run['id'] and decoded['job'] == portable['id'], 'Decoded log linkage')
        log = decoded['content']
        need('SOURCE_SHA: ' + FEATURE in log and 'Complete job name: portable-core' in log
             and '##[error]' not in log, 'Actual portable source log')
        markers = {}
        for name, pattern in {'ctest': r'100% tests passed, 0 tests failed out of 47', 'nodeTests': r'# tests 684',
                              'nodePass': r'# pass 684', 'nodeFail': r'# fail 0', 'nodeSkipped': r'# skipped 0'}.items():
            markers[name] = [line for line in log.splitlines() if re.search(pattern, line)]
            need(markers[name], 'Actual marker ' + name)
        helper_path = ROOT / 'reports/world-static-mesh-flight-guard-recipes/collect-gnu-public.py'
        spec = importlib.util.spec_from_file_location('existing_guard_log_readers', helper_path)
        helper = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(helper)
        clean = helper.ANSI.sub('', log)
        old, current = helper.prior_warnings(), helper.warnings_from_lines(clean.splitlines())
        need(helper.warning_multiset(old) == helper.warning_multiset(current), 'Visible old diagnostic multiset unchanged')
        records = [r for _, r in helper.json_records(clean)]
        audits = [r for r in records if 'proof' in r and 'compilationProvenance' in r]
        guards = [r for r in records if 'normalBindingAudit' in r and 'comparison' in r]
        need(len(audits) == len(guards) == 1, 'Actual early audit/final guard driver')
        audit, guard = audits[0], guards[0]
        need(audit['status'] == guard['status'] == 'PASS' and all(audit[k] is True for k in [
            'artifactsStable', 'sourcesStable', 'toolsStable', 'recipeStable', 'compilationFilesStable']), 'Actual audit provenance')
        need(audit['advanceScope']['clockInstructionsAudited'] is False and audit['advanceScope']['commitPathAudited'] is False,
             'No false complete clock/commit proof')
        need(len(audit['compilationProvenance']['sourceCommands']) == 4, 'Four actual core command records')
        need(guard['comparison']['status'] == 'PASS' and guard['comparison']['fixtures'] == 51 and
             guard['comparison']['normalizedPaths'] == 'fixtures[*].result.binding.buildId ONLY' and
             guard['sourceStable'] is True and all(c['exitCode'] == 0 for c in guard['commands']), 'Existing guard finite driver')
        need(guard['normalProfile']['sourceSet'] == 'world-static-mesh-flight-advance-v1', 'Seven-source profile')
        for row in guard['normalProfile']['sources']:
            need(sha256(blob(row['path'])).hexdigest() == row['sha256'], 'Actual profile source bytes')
        gnu_path = ROOT / 'reports/world-static-mesh-flight-advance-gnu-verification.json'
        gnu = load(gnu_path)
        need(gnu['status'] == 'GNU_FINITE_ADVANCE_PASS' and gnu['feature'] == FEATURE and
             gnu['run'] == run['id'] and gnu['job'] == 126802750687, 'Dedicated finite GNU receipt')
        pages = load(args.jobs / 'pages-run.json')
        pjobs = load(args.jobs / 'pages-jobs.json')['jobs']
        need(pages['id'] == 41895200177 and pages['head_sha'] == FEATURE and pages['conclusion'] == 'success'
             and pages['status'] == 'completed' and len(pjobs) == 3 and all(j['head_sha'] == FEATURE
                 and j['conclusion'] == 'success' and j['status'] == 'completed' for j in pjobs), 'All actual Pages jobs')
        byte_path = BASE / 'run-20261105-bytes-001/receipt.json'
        distribution = load(byte_path)
        need(distribution['status'] == 'PASS' and distribution['commit'] == FEATURE and
             distribution['fileCount'] == 217 and distribution['bytes'] == 5087597 and
             distribution['channels'] == {'pages': 216, 'githubSource': 1} and not distribution['failedPaths'], 'Raw distribution cohort')
        for row in distribution['files']:
            raw = (byte_path.parent / row['rawPath']).read_bytes()
            need(row['status'] == 'PASS' and raw == blob(row['path']), 'Saved HTTP bytes match exact source')
        browser = ROOT / 'reports/world-static-mesh-flight-advance-public-browser-bb58cf2'
        ready, lesson = browser / 'ready-full-ax.txt', browser / 'lesson-full-ax.txt'
        need('C++ WASM / WEBGPU READY' in ready.read_text(encoding='utf8') and
             '候補が全部そろってから、Worldと時計を進める' in lesson.read_text(encoding='utf8'), 'Actual public READY/lesson text')
        result.update(status='PUBLIC_FINITE_ACCEPTED', engineRun=run['id'], engineJobs=[j['id'] for j in jobs],
            portableRequiredSteps=25, portableActualRows=26, actualVisibleWarnings=len(current), warningMultisetUnchanged=True,
            actualMarkers=markers, actualPortableGuardComparison=guard['comparison'],
            dedicatedGNU=stamp(gnu_path), distribution=stamp(byte_path),
            pageRun=pages['id'], pageJobs=[j['id'] for j in pjobs],
            inputs=[stamp(args.log), stamp(args.jobs / 'engine-run.json'), stamp(args.jobs / 'engine-jobs.json'),
                    stamp(args.jobs / 'pages-run.json'), stamp(args.jobs / 'pages-jobs.json'), stamp(ready), stamp(lesson)],
            browserImages=[stamp(browser / 'ready.jpg'), stamp(browser / 'lesson.jpg')],
            completeClockCommitMachineProof=False, browserAdvanceAPI=False, schedulerAccepted=False,
            scope='Finite native advance/source public acceptance, both Engine jobs and all Pages jobs, selected exact217 distribution files and actual READY/original lesson display. Dedicated driver fixture/artifact streams are actual runner hash/parsed-checker evidence, not separately downloaded raw child artifacts. No new sortie rerun, FPS/deadline/general-input proof, scheduler, SDK, collision response, CFD, damage or specialist model completion.')
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    if result['status'] == 'PUBLIC_FINITE_ACCEPTED':
        (ROOT / 'reports/world-static-mesh-flight-advance-public-verification.json').write_bytes((args.output / 'result.json').read_bytes())
    print(json.dumps({k: result[k] for k in ['status', 'actualVisibleWarnings', 'engineRun', 'error'] if k in result}))
    return 0 if result['status'] == 'PUBLIC_FINITE_ACCEPTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
