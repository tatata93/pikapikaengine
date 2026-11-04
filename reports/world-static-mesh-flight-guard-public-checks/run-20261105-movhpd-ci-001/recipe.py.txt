"""Exercise the planned five-source CI MOVHPD command without Git history.

Only a short, fresh export is changed. Recorded instruction replay and synthetic
controls do not establish whole-object, GNU-release or clock/commit acceptance.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
RECIPE = 'reports/world-static-mesh-flight-guard-recipes/check-movhpd.py'
PRODUCTION = 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py'
BASELINE = 'reports/world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-001/retry-002/git-base.stdout.py.txt'
COPIES = {
    PRODUCTION: 'build/world-flight-publication/audit-movhpd-candidate.py',
    RECIPE: RECIPE,
    'reports/world-static-mesh-flight-guard-recipes/movhpd-load.patch':
        'reports/world-static-mesh-flight-guard-recipes/movhpd-load.patch',
    'reports/world-static-mesh-flight-guard-recipes/check-xmm-operands.py':
        'reports/world-static-mesh-flight-guard-recipes/check-xmm-operands.py',
    'reports/world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-failure-001/audit.json':
        'reports/world-static-mesh-flight-guard-public-checks/run-20261105-movhpd-failure-001/audit.json',
    'reports/world-static-mesh-flight-guard-public-checks/run-20261105-xmm-operands-001/scratch/old-auditor.py':
        'reports/world-static-mesh-flight-guard-public-checks/run-20261105-xmm-operands-001/scratch/old-auditor.py',
    BASELINE: BASELINE,
}
CANDIDATE_SHA = 'b46e181bfe427bdc85e27c00042ce31a5ce3f4e2ec9c17fd9aeba45a69f658cf'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def stamp(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def identity(path):
    return {'path': path.relative_to(ROOT).as_posix(), **stamp(path.read_bytes())}


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write('\n')


def tree(path):
    return {p.relative_to(path).as_posix(): stamp(p.read_bytes())
            for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--export', type=Path, default=ROOT / 'build/mhp')
    args = parser.parse_args()
    out, export = args.output.resolve(), args.export.resolve()
    allowed = ROOT / 'reports/world-static-mesh-flight-guard-public-checks'
    need(out.is_relative_to(allowed) and out != allowed, 'Fresh owned public-checks child required')
    need(export.parent == ROOT / 'build' and len(export.name) <= 12, 'Short direct build child required')
    need(not out.exists() and not export.exists(), 'Output and physical export must both be fresh')
    candidate = (ROOT / COPIES[PRODUCTION]).read_bytes()
    need(len(candidate) == 51764 and stamp(candidate)['sha256'] == CANDIDATE_SHA,
         'Exact planned five-source candidate required')
    prototype = ROOT / 'reports/world-static-mesh-flight-advance-prototype-verification.json'
    frozen = json.loads(prototype.read_text(encoding='utf-8'))
    for item in frozen['files']:
        need(identity(ROOT / item['path']) == item, 'Frozen prototype input changed: '+item['path'])
    watched = {ROOT / src for src in COPIES.values()}
    watched.update((ROOT / PRODUCTION, Path(__file__).resolve(), prototype))
    watched.update(ROOT / item['path'] for item in frozen['files'])
    before = {p.relative_to(ROOT).as_posix(): identity(p) for p in sorted(watched)}
    out.mkdir(parents=True, exist_ok=False)
    export.mkdir(parents=True, exist_ok=False)
    write(out / 'source-before.json', before)
    (out / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    env = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(key, None)
    env.update(GIT_CEILING_DIRECTORIES=str(export.parent), GIT_DISCOVERY_ACROSS_FILESYSTEM='0',
               PYTHONDONTWRITEBYTECODE='1', GIT_TERMINAL_PROMPT='0')
    commands, result = [], {'schema': 1, 'status': 'FAIL',
        'scope': 'No-history short export of the actual planned CI five-source MOVHPD command; saved instruction replay and synthetic controls only. No binary execution or whole GNU artifact/clock/commit acceptance.',
        'requiredExportFiles': len(COPIES), 'configuredGitCeiling': str(export.parent),
        'compilerInvocations': 0, 'binaryExecutions': 0, 'wholeArtifactAudits': 0}

    def run(name, argv):
        start = time.perf_counter()
        completed = subprocess.run(argv, cwd=export, env=env, capture_output=True, timeout=120, check=False)
        stdout, stderr = out / (name+'.stdout.txt'), out / (name+'.stderr.txt')
        stdout.write_bytes(completed.stdout)
        stderr.write_bytes(completed.stderr)
        record = {'name': name, 'argv': argv, 'cwd': str(export), 'exit': completed.returncode,
                  'elapsedSeconds': time.perf_counter()-start, 'stdout': identity(stdout), 'stderr': identity(stderr),
                  'environment': {k: env[k] for k in ('GIT_CEILING_DIRECTORIES', 'GIT_DISCOVERY_ACROSS_FILESYSTEM', 'PYTHONDONTWRITEBYTECODE')}}
        write(out / (name+'.command.json'), record)
        commands.append(record)
        return completed

    started = time.perf_counter()
    try:
        mapping = []
        for relative, source in COPIES.items():
            destination = export / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            raw = (ROOT / source).read_bytes()
            with destination.open('xb') as stream:
                stream.write(raw)
            mapping.append({'source': source, 'exportPath': relative, **stamp(raw)})
        write(out / 'export-inputs.json', mapping)
        need(len(tree(export)) == 7 and not (export / '.git').exists(), 'Exactly seven inputs and no exported Git metadata')
        root_lookup = run('git-root-refused', ['git', 'rev-parse', '--show-toplevel'])
        old_lookup = run('git-old-commit-refused', ['git', 'show', '462742caf805e94c557168d56c3f90851ca8bd73:'+PRODUCTION])
        for attempt in (root_lookup, old_lookup):
            need(attempt.returncode != 0 and attempt.stdout == b'' and b'not a git repository' in attempt.stderr.lower(),
                 'Git discovery/history must actually be refused in the export')
        argv = [sys.executable, RECIPE, '--production', '--output', 'build/ci-movhpd']
        success = run('production-success', argv)
        need(success.returncode == 0, 'Exact production CI command failed')
        success_path = export / 'build/ci-movhpd'
        accepted = json.loads((success_path / 'result.json').read_text(encoding='utf-8'))
        need(accepted['status'] == 'PASS' and accepted['sourcesStable'] is True, 'Actual production result/stability')
        expected = {'actualRecordReplay': 1, 'auditorExistingRegressions': 73,
                    'historicalObservations': 2, 'newSyntheticMovhpdControls': 20}
        need(set(accepted['counts']) == set(expected), 'Exact control groups')
        for group, count in expected.items():
            need(accepted['counts'][group]['total'] == count and accepted['counts'][group]['passed'] == count,
                 'All actual 96 controls must pass')
        need(accepted['executedAuditor']['mode'] == 'production' and
             accepted['executedAuditor']['path'] == str(export / PRODUCTION) and
             accepted['executedAuditor']['sha256'] == CANDIDATE_SHA,
             'Execute the exported planned five-source candidate at PRODUCTION')
        successful_tree = tree(success_path)
        write(out / 'successful-output-tree.json', successful_tree)
        all_export_after_success = tree(export)
        reuse = run('production-reuse-refused', argv)
        need(reuse.returncode != 0 and b'FileExistsError' in reuse.stderr,
             'Fresh-output guard must reject reuse')
        need(tree(export) == all_export_after_success, 'Output reuse must not change any successful/export byte')
        baseline_path = export / BASELINE
        original_baseline = baseline_path.read_bytes()
        changed_baseline = original_baseline+b'\n# synthetic exported-baseline corruption\n'
        baseline_path.write_bytes(changed_baseline)
        write(out / 'baseline-copy-mutation.json', {'path': BASELINE, 'before': stamp(original_baseline),
              'mutated': stamp(changed_baseline),
              'scope': 'Artificial corruption of the export copy only; not a Native/CPU fault injection.'})
        try:
            bad = run('modified-baseline-refused', [sys.executable, RECIPE, '--production', '--output', 'build/ci-movhpd-corrupt'])
            need(bad.returncode != 0, 'Modified baseline must fail closed')
            rejected = json.loads((export / 'build/ci-movhpd-corrupt/result.json').read_text(encoding='utf-8'))
            need(rejected['status'] == 'FAIL' and rejected.get('error') == 'ValueError: Pinned five-source Git auditor identity',
                 'Exact baseline-identity rejection required')
            need(tree(success_path) == successful_tree, 'Baseline rejection must not alter prior successful output')
        finally:
            baseline_path.write_bytes(original_baseline)
        for relative, source in COPIES.items():
            need((export / relative).read_bytes() == (ROOT / source).read_bytes(), 'Export input not restored: '+relative)
        flat = out / 'copies'
        flat.mkdir()
        archived = []
        for ordinal, path in enumerate(sorted(p for p in export.rglob('*') if p.is_file()), 1):
            raw = path.read_bytes()
            copy = flat / ('f'+str(ordinal).zfill(5)+'.dat')
            with copy.open('xb') as stream:
                stream.write(raw)
            archived.append({'exportPath': path.relative_to(export).as_posix(),
                             'copy': copy.relative_to(ROOT).as_posix(), **stamp(raw)})
        write(out / 'flat-copy-map.json', archived)
        result.update(status='PASS', checks=96, counts=accepted['counts'],
                      gitRootDiscoveryRefused=True, oldCommitLookupRefused=True,
                      outputReuseRefused=True, successfulTreeUnchanged=True,
                      exportedBaselineMutationRefused=True, exportedInputsRestored=True,
                      outputFilesArchived=len(archived), exportPath=export.relative_to(ROOT).as_posix(),
                      actualExecutedAuditor=accepted['executedAuditor'])
    except Exception as error:
        result['error'] = type(error).__name__+': '+str(error)
    finally:
        after = {p.relative_to(ROOT).as_posix(): identity(p) for p in sorted(watched)}
        write(out / 'source-after.json', after)
        write(out / 'commands.json', commands)
        result.update(originalSourcesAndFrozenEvidenceUnchanged=before == after,
                      elapsedSeconds=time.perf_counter()-started)
        if before != after:
            result['status'] = 'FAIL'
            result['stabilityError'] = 'Original input or frozen prototype changed'
        write(out / 'result.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'requiredExportFiles', 'outputFilesArchived',
                     'originalSourcesAndFrozenEvidenceUnchanged', 'elapsedSeconds', 'error') if k in result}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
