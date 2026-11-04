"""Collect already-decoded GitHub GNU job evidence, without fetching or running it.

Inputs are original REST run/job JSON and the explicit decoded connector wrapper.
Failure/unknown schema is fail-closed. This is not the original downloaded ZIP,
not public UI/distribution acceptance, and not a new actual machine audit.
"""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIOR_CI = ROOT / 'reports/accelerated-sphere-box-coverage-public-ci-evidence.json'
PRIOR_LOG = ROOT / 'reports/accelerated-sphere-box-coverage-job-126627509578-full.txt'
PRIOR_CI_HASH = 'ac5dcff15915fa06c4bb65e3d93ac9ea2d6e6ffb1ce8ba1b97c5fdcaf06f61c2'
PRIOR_LOG_HASH = 'c840a532951713d0baf692107a9e002ceb63d10e2f1a7319cfca01318581c030'
ANSI = re.compile(r'\x1b\[[0-9;]*m')
TIME = re.compile(r'^\ufeff?\d{4}-\d\d-\d\dT\S+Z\s+')
STRICT = {'-fno-fast-math', '-ffp-contract=off', '-frounding-math',
          '-fexcess-precision=standard', '-mfpmath=sse', '-msse2', '-fno-lto'}
FIVE = {'core/src/core.cpp', 'core/include/pikapika/core.hpp', 'core/src/dynamics.cpp',
        'core/include/pikapika/world_static_mesh_flight_guard.hpp', 'core/src/world_static_mesh_flight_guard.cpp'}
COMMANDS = ['normal-target-build', 'normal-artifact-audit', 'warning-0', 'warning-1', 'warning-2',
            'normal-tests', 'normal-fixtures', 'normal-storage', 'normal-independent-math',
            'normal-independent-controls', 'debug-configure', 'debug-build',
            'debug-unconfigured-actual-guard', 'sanitizer-configure', 'sanitizer-build-all-dependencies',
            'sanitizer-tests', 'sanitizer-fixtures', 'sanitizer-independent-math', 'sanitizer-independent-controls']


def need(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def unique(items):
    out = {}
    for key, value in items:
        need(key not in out, 'Duplicate JSON key: ' + key)
        out[key] = value
    return out


def loads(text):
    return json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON: ' + value)))


def load(path):
    raw = Path(path).read_bytes()
    need(len(raw) <= 64 * 1024 * 1024, 'Bounded JSON input')
    return loads(raw.decode('utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def metadata_stamp(value):
    need(type(value) is dict and {'path', 'bytes', 'sha256'} <= set(value), 'Remote path/hash metadata')
    need(type(value['path']) is str and value['path'] and type(value['bytes']) is int and value['bytes'] >= 0 and
         type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']), 'Remote bytes/hash types')
    return {key: value[key] for key in ('bytes', 'sha256')}


def select_run(data, run_id, commit):
    need(type(data) is dict, 'REST run object/list wrapper')
    if 'workflow_runs' in data:
        need(type(data.get('total_count')) is int and data['total_count'] >= 0 and type(data['workflow_runs']) is list,
             'REST workflow_runs schema')
        matches = [row for row in data['workflow_runs'] if type(row) is dict and row.get('id') == run_id and row.get('head_sha') == commit]
        need(len(matches) == 1, 'Unique exact run-id/head_sha in REST list')
        run = matches[0]
    else:
        run = data
    need(type(run.get('id')) is int and run['id'] == run_id and run.get('head_sha') == commit,
         'Exact workflow run/commit')
    need(run.get('status') == 'completed' and run.get('conclusion') == 'success', 'Run must be completed/success')
    return run


def select_job(data, run_id, job_id, step_names):
    need(type(data) is dict and type(data.get('jobs')) is list, 'Connector jobs schema')
    matches = [row for row in data['jobs'] if type(row) is dict and row.get('id') == job_id]
    need(len(matches) == 1, 'Unique exact job')
    job = matches[0]
    need(type(job.get('id')) is int and job['id'] == job_id and type(job.get('run_id')) is int and
         job['run_id'] == run_id and job.get('name') == 'portable-core', 'Job/run/name linkage')
    need(job.get('status') == 'completed' and job.get('conclusion') == 'success', 'Job must be completed/success')
    steps = job.get('steps')
    # Connector snapshots may omit the terminal housekeeping row. The required
    # Set up + 24 named workflow stages remain exact and must all succeed. Never
    # discard a returned Complete job row or represent 26 actual rows as 25.
    need(type(steps) is list and len(step_names) == 25 and len(steps) in (25, 26),
         'Exactly 25 required stages plus optional terminal Complete job')
    expected_names = step_names + (['Complete job'] if len(steps) == 26 else [])
    for index, (step, expected) in enumerate(zip(steps, expected_names), 1):
        need(type(step) is dict and step.get('name') == expected and type(step.get('number')) is int and
             step['number'] == index and step.get('status') == 'completed' and step.get('conclusion') == 'success',
             'Step order/status at ' + str(index))
    return job


def decoded_log(data, run_id, job_id, commit):
    need(type(data) is dict and set(data) == {'schema', 'scope', 'run', 'job', 'content'}, 'Known decoded log wrapper schema only')
    need(type(data['schema']) is int and data['schema'] == 1 and type(data['scope']) is str and data['scope'] and
         type(data['run']) is int and data['run'] == run_id and type(data['job']) is int and data['job'] == job_id,
         'Decoded wrapper run/job linkage')
    content = data['content']
    need(type(content) is str and 0 < len(content) <= 64 * 1024 * 1024, 'Nonempty bounded decoded content string')
    clean = ANSI.sub('', content)
    need('SOURCE_SHA: ' + commit in clean and 'Complete job name: portable-core' in clean, 'Log source/job textual linkage')
    need('##[error]' not in clean, 'Job log contains an Actions error annotation')
    return content, clean


def warnings_from_lines(lines):
    rows = []
    for line in lines:
        if 'warning:' not in line:
            continue
        match = re.search(r'((?:core|tests|tools|reports)/[^\s:]+):(\d+):(\d+): warning:(.*)$', line)
        need(match is not None, 'Unknown warning diagnostic format: ' + line[:180])
        rows.append({'file': match[1], 'line': int(match[2]), 'column': int(match[3]), 'diagnostic': match[4]})
    return rows


def warning_multiset(rows):
    result = []
    need(type(rows) is list, 'Warning rows list')
    for row in rows:
        need(type(row) is dict and set(row) == {'file', 'line', 'column', 'diagnostic'} and
             type(row['file']) is str and type(row['diagnostic']) is str and
             type(row['line']) is int and row['line'] > 0 and type(row['column']) is int and row['column'] > 0,
             'Warning row schema')
        result.append((row['file'], row['line'], row['column'], row['diagnostic']))
    return Counter(result)


def prior_warnings():
    ci_raw, full = PRIOR_CI.read_bytes(), PRIOR_LOG.read_bytes()
    need(sha256(ci_raw).hexdigest() == PRIOR_CI_HASH and sha256(full).hexdigest() == PRIOR_LOG_HASH,
         'Pinned accepted Sphere public baseline bytes')
    ci = loads(ci_raw.decode('utf-8'))
    need(ci['commit'] == '63f5d3d7b841633980eac2006717f30614ee9e1f' and ci['engine']['runId'] == 41845414301 and
         ci['engine']['jobId'] == 126627509578 and ci['engine']['log']['sha256'] == PRIOR_LOG_HASH,
         'Sphere baseline run/job/commit identity')
    rows = warnings_from_lines(ANSI.sub('', full.decode('utf-8')).splitlines())
    need(len(rows) == 48 and warning_multiset(rows) == warning_multiset(ci['warnings']['current']),
         'Prior full log re-extracted 48 warnings match accepted evidence')
    return rows


def json_records(clean):
    records = []
    for number, line in enumerate(clean.splitlines(), 1):
        text = TIME.sub('', line).strip()
        if text.startswith('{') and text.endswith('}'):
            try:
                value = loads(text)
            except ValueError:
                continue
            if type(value) is dict:
                records.append((number, value))
    return records


def profile(data, configuration, feature_blob):
    need(type(data) is dict and type(data.get('schema')) is int and data['schema'] == 1 and type(data.get('profile')) is int and
         data['profile'] == (1 if configuration == 'Release' else 0) and data.get('configuration') == configuration and
         data.get('architecture') == 'x64-sse2' and data.get('compiler', {}).get('id') == 'GNU' and
         re.match(r'^13(?:\.|$)', data['compiler'].get('version', '')), 'GNU13 configured profile')
    need(type(data.get('buildId')) is str and re.fullmatch('[0-9a-f]{64}', data['buildId']), 'Build identity')
    rows = data.get('sources')
    need(type(rows) is list and len(rows) == 5 and {row['path'] for row in rows} == FIVE, 'Exact five-source public guard profile')
    for row in rows:
        need(row['sha256'] == sha256(feature_blob(row['path'])).hexdigest(), 'Profile source matches feature blob')
        if row['path'].endswith('.cpp'):
            need(type(row['flags']) is list and STRICT <= set(row['flags']), 'Requested source strict flags')
    return data['buildId']


def collect(log, runs, jobs, commit, run_id, job_id, output, feature_blob):
    workflow = feature_blob('.github/workflows/verify.yml').decode('utf-8')
    step_names = ['Set up job'] + re.findall(r'^      - name: (.+)$', workflow, re.M)
    run = select_run(runs, run_id, commit)
    job = select_job(jobs, run_id, job_id, step_names)
    content, clean = decoded_log(log, run_id, job_id, commit)
    old, current = prior_warnings(), warnings_from_lines(clean.splitlines())
    need(len(current) == 48 and warning_multiset(current) == warning_multiset(old), 'Current visible 48 warning multiset equals accepted prior 48')
    records = json_records(clean)
    early = [(line, row) for line, row in records if 'proof' in row and 'profile' in row and 'compilationProvenance' in row]
    helpers = [(line, row) for line, row in records if 'normalBindingAudit' in row and 'sanitizedProfile' in row and 'comparison' in row]
    need(len(early) == len(helpers) == 1, 'Exactly one full early audit and one full final GNU helper JSON')
    early_line, audit = early[0]
    helper_line, helper = helpers[0]
    need(early_line < helper_line and audit['schema'] == 1 and audit['status'] == 'PASS' and audit['binaryExecuted'] is False and
         all(audit.get(key) is True for key in ['artifactsStable', 'sourcesStable', 'toolsStable', 'recipeStable', 'compilationFilesStable']),
         'Actual early normal audit status and provenance stability')
    normal_id = profile(audit['profile'], 'Release', feature_blob)
    need(metadata_stamp(audit['recipe']) == stamp(feature_blob('reports/world-static-mesh-flight-guard-recipes/audit-binding.py')),
         'Actual early auditor recipe equals exact feature blob')
    functions = audit['proof']['functions']
    need(type(functions) is list and len(functions) == 3 and {row['kind'] for row in functions} == {'subtract', 'dot', 'length'},
         'Actual three Vec3 leaf dataflow graphs')
    source_commands = audit['compilationProvenance']['sourceCommands']
    need(len(source_commands) == 3 and {row['source'] for row in source_commands} ==
         {'core/src/core.cpp', 'core/src/dynamics.cpp', 'core/src/world_static_mesh_flight_guard.cpp'}, 'Three normal actual compiler commands')
    for row in source_commands:
        need(row['strictFP'] is True and row['noLTO'] is True and STRICT <= set(row['argv']), 'Actual normal strict/no-LTO command')
    need(audit['compilationProvenance']['noLinkTimeCodeGeneration'] is True, 'Normal actual non-LTO link')
    need(type(helper['schema']) is int and helper['schema'] == 1 and helper['status'] == 'PASS' and helper['sourceStable'] is True and
         type(helper['finiteFixtures']) is int and helper['finiteFixtures'] == 51, 'Final actual GNU helper success/current corpus')
    need(profile(helper['normalProfile'], 'Release', feature_blob) == normal_id, 'Helper normal identity matches early actual audit')
    sanitized_id = profile(helper['sanitizedProfile'], 'Release', feature_blob)
    profile(helper['debugProfile'], 'Debug', feature_blob)
    need(normal_id != sanitized_id, 'Distinct instrumented configuration identity')
    need(metadata_stamp(helper['recipe']) == stamp(feature_blob('reports/world-static-mesh-flight-guard-recipes/verify-gnu.py')),
         'Actual helper recipe equals feature blob')
    commands = helper['commands']
    need(type(commands) is list and [row['name'] for row in commands] == COMMANDS, 'Exact 19 known helper command phases')
    by_name = {}
    for row in commands:
        need(type(row['exitCode']) is int and row['exitCode'] == 0 and 'exception' not in row and
             type(row['argv']) is list and all(type(arg) is str for arg in row['argv']), 'Actual helper child command success')
        metadata_stamp(row['stdout']); metadata_stamp(row['stderr'])
        by_name[row['name']] = row
    for index in range(3):
        need(STRICT | {'-Wall', '-Wextra', '-Wpedantic', '-Werror'} <= set(by_name['warning-' + str(index)]['argv']),
             'Separate actual new-source Werror commands')
    for key in ['normal-independent-math', 'sanitizer-independent-math']:
        need(any(arg.endswith('scripts/verify-world-static-mesh-flight-guard.py') for arg in by_name[key]['argv']), 'Pinned independent mathematical checker command')
    expected_controls = {'status': 'PASS', 'selfTestGroups': 12, 'fixtures': 51,
                         'labelAndOrderIndependent': True, 'rejectedControls': 138}
    expected_control_stdout = (json.dumps(expected_controls) + '\n').encode('utf-8')
    for key in ['normal-independent-controls', 'sanitizer-independent-controls']:
        need(any(arg.endswith('tests/world_static_mesh_flight_guard_reference_tests.py') for arg in by_name[key]['argv']) and
             metadata_stamp(by_name[key]['stdout']) == stamp(expected_control_stdout),
             'Remote control stdout commitment equals exact 12/51/138 one-line output')
    need(by_name['debug-unconfigured-actual-guard']['argv'][-1] == '--unsupported-profile', 'Actual Debug refusal command')
    need(type(helper['instrumentedLibraryTranslationUnits']) is int and helper['instrumentedLibraryTranslationUnits'] > 0,
         'Observed whole-library instrumented source count')
    comparison = helper['comparison']
    need(comparison['status'] == 'PASS' and type(comparison['fixtures']) is int and comparison['fixtures'] == 51 and
         comparison['normalizedPaths'] == 'fixtures[*].result.binding.buildId ONLY' and
         comparison['normalBuildId'] == normal_id and comparison['sanitizedBuildId'] == sanitized_id and
         re.fullmatch('[0-9a-f]{64}', comparison['normalizedTreeSha256']), 'Complete normal/sanitizer 51 comparison scope')
    for marker in ['100% tests passed, 0 tests failed out of 46', '# tests 684', '# pass 684', '# fail 0', '# skipped 0']:
        need(marker in clean, 'Measured existing regression marker: ' + marker)
    if output:
        write(output / 'actual-early-audit.json', audit)
        write(output / 'actual-final-gnu-helper.json', helper)
        write(output / 'warnings-current.json', current)
        write(output / 'warnings-prior.json', old)
        (output / 'expected-control-stdout.NOT-downloaded.txt').write_bytes(expected_control_stdout)
        (output / 'decoded-job-content.txt').write_text(content, encoding='utf-8', newline='')
    return {
        'schema': 1, 'status': 'PASS', 'commit': commit, 'runId': run_id, 'jobId': job_id,
        'steps': 25, 'requiredSteps': 25, 'returnedSteps': len(job['steps']),
        'completeJobReturned': len(job['steps']) == 26,
        'stepCountScope': '25 required stages = Set up job + 24 named workflow stages. A returned terminal Complete job is counted separately and must also succeed; the original job rows are retained intact.',
        'ctest': 46, 'node': 684, 'skipped': 0,
        'decodedLog': {'characters': len(content), 'lines': len(content.splitlines()), **stamp(content.encode('utf-8'))},
        'run': {'id': run['id'], 'head_sha': run['head_sha'], 'status': run['status'], 'conclusion': run['conclusion']},
        'job': job, 'warnings': {'current': 48, 'prior': 48, 'sameMultiset': True, 'newVisibleDiagnostics': 0,
            'priorRun': 41845414301, 'priorJob': 126627509578,
            'extraction': 'Same file/line/column/diagnostic Counter as accepted Sphere public-summary.py. No diagnostic or line-number normalization.',
            'scope': 'Warnings actually visible in complete decoded job text only. Successful helper child stderr is captured remotely and represented by hashes, not its complete downloaded content.'},
        'earlyNormalAudit': {'line': early_line, 'actualLeafGraphs': 3, 'actualStrictSourceCommands': 3,
                             'normalBuildId': normal_id, 'scope': audit['scope'], 'normalSourceProfile': audit['profile']},
        'finalHelper': {'line': helper_line, 'commands': 19, 'finiteFixtures': 51,
                        'instrumentedLibraryTranslationUnits': helper['instrumentedLibraryTranslationUnits'],
                        'normalAuditRemoteFile': helper['normalBindingAudit'], 'comparison': comparison,
                        'debugProfile': 0, 'debugRefusalActualCommand': by_name['debug-unconfigured-actual-guard'],
                        'independentControls': {'report': expected_controls, 'expectedStdout': stamp(expected_control_stdout),
                            'normalRemoteStdout': by_name['normal-independent-controls']['stdout'],
                            'sanitizedRemoteStdout': by_name['sanitizer-independent-controls']['stdout'],
                            'scope': 'Actual child exit0 and recorded stdout bytes/hash equal the exact expected report line. Child raw stdout/stderr files were not separately downloaded.'},
                        'scope': helper['scope']},
        'limitations': ['Connector-decoded text, not original download ZIP bytes.',
                       'Early normal three-leaf/caller/command audit differs from sanitizer behavior and whole-library instrumentation.',
                       'No source-field/whole caller/clock/commit symbolic machine proof, new World advance, UI, distribution or all-target acceptance.',
                       'Successful helper child raw files and captured stderr bodies are not locally present; remote hashes remain metadata commitments.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['log', 'run', 'jobs', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--job-id', type=int, required=True)
    args = parser.parse_args()
    need(re.fullmatch('[0-9a-f]{40}', args.commit) and args.run_id > 0 and args.job_id > 0, 'Full feature/run/job identity')
    output = args.output.resolve()
    need(output.is_relative_to(ROOT / 'reports/world-static-mesh-flight-guard-public-checks') and output.name.startswith('run-'), 'Fresh run directory under guard public checks')
    output.mkdir(parents=True, exist_ok=False)
    watched = [args.log.resolve(), args.run.resolve(), args.jobs.resolve(), PRIOR_CI, PRIOR_LOG, Path(__file__).resolve()]
    before = {str(path): stamp(path.read_bytes()) for path in watched}
    write(output / 'inputs-before.json', before)
    (output / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    write(output / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd()), 'startedUtc': datetime.now(timezone.utc).isoformat()})
    cache = {}
    def feature_blob(relative):
        need(type(relative) is str and not relative.startswith('/') and '..' not in Path(relative).parts, 'Git source relative path')
        if relative not in cache:
            argv = ['git', 'show', args.commit + ':' + relative]
            done = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
            index = len(cache)
            (output / f'git/{index}.stdout.txt').parent.mkdir(exist_ok=True)
            (output / f'git/{index}.stdout.txt').write_bytes(done.stdout)
            (output / f'git/{index}.stderr.txt').write_bytes(done.stderr)
            write(output / f'git/{index}.command.json', {'argv': argv, 'cwd': str(ROOT), 'exitCode': done.returncode,
                  'stdout': stamp(done.stdout), 'stderr': stamp(done.stderr)})
            need(done.returncode == 0, 'Exact feature Git blob missing: ' + relative)
            cache[relative] = done.stdout
        return cache[relative]
    result = {'schema': 1, 'status': 'FAIL', 'commit': args.commit, 'runId': args.run_id, 'jobId': args.job_id}
    try:
        result = collect(load(args.log), load(args.run), load(args.jobs), args.commit, args.run_id, args.job_id, output, feature_blob)
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = {str(path): stamp(path.read_bytes()) for path in watched}
        result.update(inputsStable=before == after, inputsBefore=before, inputsAfter=after,
                      featureBlobs={path: stamp(raw) for path, raw in cache.items()})
        if before != after:
            result.update(status='FAIL', stabilityError='Collector inputs changed during collection')
        write(output / 'inputs-after.json', after)
        write(output / 'result.json', result)
    print(json.dumps({key: result[key] for key in ['status', 'commit', 'runId', 'jobId', 'steps', 'warnings', 'inputsStable', 'error'] if key in result}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
