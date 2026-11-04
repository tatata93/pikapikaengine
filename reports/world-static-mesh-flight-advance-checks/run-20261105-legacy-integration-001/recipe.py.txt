"""Compare old/new actual Native probes and independently audit new guard51.

The unchanged GNU helper's exact comparator is reused for configuration-ID-only
normalization; its normal/sanitized argument names mean old-five/new-seven here.
No sanitizer, GNU compiler, full CTest, Node suite or clock/commit proof runs.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-legacy-integration-001'
OLD = ROOT / 'build/native'
NEW = ROOT / 'build/wfa2'
HELPER = ROOT / 'reports/world-static-mesh-flight-guard-recipes/verify-gnu.py'
CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-guard.py'
CONTROLS = ROOT / 'tests/world_static_mesh_flight_guard_reference_tests.py'
GUARD = 'pikapika_world_static_mesh_flight_guard_tests.exe'
PROBES = (
    ('w1', 'pikapika-free-flight-legacy-probe.exe', []),
    ('simulation', 'pikapika-simulation-probe.exe', []),
    ('supported', 'pikapika-supported-probe.exe', ['--fixtures']),
    ('held-load', 'pikapika_sphere_triangle_mesh_held_load_tests.exe', ['--fixtures']),
    ('free-flight', 'pikapika_sphere_triangle_mesh_free_flight_guard_tests.exe', ['--fixtures']),
    ('free-flight-supplemental', 'pikapika_sphere_triangle_mesh_free_flight_guard_tests.exe', ['--supplemental-fixtures']),
)
DIRTY = ['CMakeLists.txt', 'cmake/WorldFlightBinding.cmake', 'docs/PLAN.md',
         'reports/world-static-mesh-flight-guard-recipes/audit-binding.py']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def snapshot(paths):
    return {path.relative_to(ROOT).as_posix(): stamp(path) for path in paths}


class Commands:
    def __init__(self, monitored):
        self.monitored, self.rows = monitored, []

    def run(self, name, argv, timeout=180):
        argv = [str(x) for x in argv]
        before = snapshot(self.monitored)
        write_json(OUTPUT / (name + '.before.json'), before)
        row = {'name': name, 'argv': argv, 'cwd': str(ROOT), 'timeoutSeconds': timeout,
               'started': datetime.now(timezone.utc).isoformat()}
        write_json(OUTPUT / (name + '.started.json'), row)
        print(json.dumps({'phase': name, 'state': 'running'}), flush=True)
        stdout, stderr = OUTPUT / (name + '.stdout.txt'), OUTPUT / (name + '.stderr.txt')
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        started = time.perf_counter()
        try:
            with stdout.open('xb') as out, stderr.open('xb') as err:
                completed = subprocess.run(argv, cwd=ROOT, env=environment, stdout=out, stderr=err, timeout=timeout)
            row['exitCode'] = completed.returncode
        except subprocess.TimeoutExpired:
            row.update(exitCode=None, timedOut=True)
        after = snapshot(self.monitored)
        write_json(OUTPUT / (name + '.after.json'), after)
        row.update(elapsedSeconds=time.perf_counter() - started, stdout=stamp(stdout), stderr=stamp(stderr),
                   sourceAndArtifactStable=before == after)
        self.rows.append(row)
        write_json(OUTPUT / (name + '.command.json'), row)
        print(json.dumps({'phase': name, 'exitCode': row['exitCode'], 'stable': row['sourceAndArtifactStable']}), flush=True)
        require(row['sourceAndArtifactStable'], 'Monitored original changed during ' + name)
        require(row['exitCode'] == 0, 'Command failed: ' + name)
        return stdout.read_bytes()


def main():
    require(sys.argv[1:] == [], 'Usage: check-integrated-legacy.py (fixed fresh evidence directory)')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    source_paths = {Path(__file__).resolve(), HELPER, CHECKER, CONTROLS}
    for folder, suffixes in (('core', {'.cpp', '.hpp', '.h'}), ('tests', {'.cpp', '.hpp', '.h', '.py'}),
                             ('scripts', {'.py'}), ('cmake', {'.cmake'})):
        source_paths.update(p for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in suffixes)
    source_paths.update(ROOT / path for path in DIRTY)
    binaries = sorted({name for _, name, _ in PROBES} | {GUARD})
    old_artifacts, new_artifacts = [], []
    for build, items, map_name in ((OLD, old_artifacts, 'world-flight-guard.map'),
                                   (NEW, new_artifacts, 'world-flight-advance.map')):
        items.extend(build / 'Release' / name for name in binaries)
        items.extend((build / 'Release/pikapika_core.lib', build / 'pikapika_core.dir/Release/core.obj',
                      build / 'Release' / map_name, build / 'world-flight-binding-Release.json'))
    protected = sorted(source_paths | set(old_artifacts) | set(new_artifacts) | {
        ROOT / 'assets/pikapika-simulation.wasm', ROOT / 'assets/pikapika-simulation.mjs',
        ROOT / 'assets/pikapika-simulation.build.json'})
    before = snapshot(protected)
    write_json(OUTPUT / 'before.json', before)
    (OUTPUT / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    (OUTPUT / 'comparison-helper.py.txt').write_bytes(HELPER.read_bytes())
    write_json(OUTPUT / 'invocation.json', {'argv': sys.argv, 'cwd': str(ROOT), 'python': sys.version,
               'started': datetime.now(timezone.utc).isoformat(), 'recipe': stamp(Path(__file__).resolve()),
               'monitoredSources': len(source_paths), 'oldArtifactPaths': [p.relative_to(ROOT).as_posix() for p in old_artifacts],
               'newArtifactPaths': [p.relative_to(ROOT).as_posix() for p in new_artifacts]})
    commands = Commands(protected)
    record = {'schema': 1, 'kind': 'integrated-advance-legacy-and-world-guard-reference', 'status': 'FAIL',
              'scope': 'Same-MSVC old accepted/new seven-source Native probe raw-byte regression and independent finite Worldguard51 mathematics. '
                       'Configuration buildId only is normalized for guard corpus comparison; no GNU/sanitizer, SDK query, '
                       'clock/commit formal machine proof, full CTest/Node rerun or public acceptance.',
              'oldArtifactCount': len(old_artifacts), 'newArtifactCount': len(new_artifacts)}
    started = time.perf_counter()
    try:
        commands.run('four-production-diff', ['git', 'diff', '--', *DIRTY], 30)
        old_profile = json.loads((OLD / 'world-flight-binding-Release.json').read_text('utf-8'))
        new_profile = json.loads((NEW / 'world-flight-binding-Release.json').read_text('utf-8'))
        require(old_profile['profile'] == new_profile['profile'] == 1 and len(old_profile['sources']) == 5 and
                len(new_profile['sources']) == 7 and new_profile['sourceSet'] == 'world-static-mesh-flight-advance-v1' and
                old_profile['buildId'] != new_profile['buildId'], 'Distinct old-five/new-seven configured identities required')
        comparisons = []
        for name, filename, arguments in PROBES:
            old_raw = commands.run('old-' + name, [OLD / 'Release' / filename, *arguments])
            new_raw = commands.run('new-' + name, [NEW / 'Release' / filename, *arguments])
            old_path, new_path = OUTPUT / ('old-' + name + '.json'), OUTPUT / ('new-' + name + '.json')
            old_path.write_bytes(old_raw)
            new_path.write_bytes(new_raw)
            row = {'name': name, 'arguments': arguments, 'old': stamp(old_path), 'new': stamp(new_path),
                   'rawByteEqual': old_raw == new_raw, 'normalization': 'NONE'}
            comparisons.append(row)
            write_json(OUTPUT / 'raw-comparisons.json', comparisons)
            require(row['rawByteEqual'], 'Legacy raw bytes differ: ' + name)
        old_guard = OUTPUT / 'old-world-guard.json'
        new_guard = OUTPUT / 'new-world-guard.json'
        old_guard.write_bytes(commands.run('old-world-guard', [OLD / 'Release' / GUARD, '--fixtures']))
        new_guard.write_bytes(commands.run('new-world-guard', [NEW / 'Release' / GUARD, '--fixtures']))
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('unchanged_gnu_exact_guard_comparator', HELPER)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        old_data, new_data = helper.load(old_guard), helper.load(new_guard)
        comparison = helper.compare_fixtures(deepcopy(old_data), deepcopy(new_data), old_profile['buildId'], new_profile['buildId'])
        write_json(OUTPUT / 'guard-exact-comparison.json', {'helperResult': comparison,
                   'roles': {'normalArgument': 'Old accepted five-source MSVC configuration',
                             'sanitizedArgument': 'New seven-source MSVC configuration; NOT a sanitizer build'},
                   'helper': stamp(HELPER), 'oldRaw': stamp(old_guard), 'newRaw': stamp(new_guard),
                   'onlyAllowedDifference': 'fixtures[*].result.binding.buildId',
                   'method': 'Unchanged verify-gnu.load and compare_fixtures; complete key order, scalar type, array order and binary64 signed-zero bits'})
        old_reference = json.loads(commands.run('old-world-independent-checker', [sys.executable, CHECKER, old_guard]))
        new_reference = json.loads(commands.run('new-world-independent-checker', [sys.executable, CHECKER, new_guard]))
        require(old_reference['status'] == new_reference['status'] == 'PASS' and
                old_reference['fixtures'] == new_reference['fixtures'] == 51, 'Actual independent guard51 references required')
        controls_output = OUTPUT / 'new-world-reference-controls'
        commands.run('new-world-independent-controls', [sys.executable, CONTROLS, new_guard, '--output', controls_output])
        controls = json.loads((controls_output / 'negative-controls.json').read_text('utf-8'))
        require(controls['status'] == 'PASS' and controls['fixtures'] == 51 and controls['labelAndOrderIndependent'] is True and
                all(row['rejected'] is True for row in controls['rejectedControls']), 'Independent negative controls did not pass')
        record.update(status='PASS', rawComparisons=comparisons, guardComparison=comparison,
                      comparatorArgumentRoles='normal=old-five; sanitized=new-seven; neither side is an instrumentation build here',
                      oldGuardReference=old_reference, newGuardReference=new_reference,
                      independentSelfTestGroups=controls['selfTestGroups'],
                      independentRejectedControls=len(controls['rejectedControls']),
                      independentLabelAndOrder=True, sourceSet=new_profile['sourceSet'],
                      oldBuildId=old_profile['buildId'], newBuildId=new_profile['buildId'])
    except BaseException as error:
        record['failure'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        after = snapshot(protected)
        write_json(OUTPUT / 'after.json', after)
        record.update(sourceAndArtifactStable=before == after, commands=commands.rows,
                      elapsedSeconds=time.perf_counter() - started, recipe=stamp(Path(__file__).resolve()),
                      finished=datetime.now(timezone.utc).isoformat())
        if before != after:
            record.update(status='FAIL', stabilityError='Protected old/new artifact, source or production dirty-file changed')
        write_json(OUTPUT / 'result.json', record)
        print(json.dumps({key: record[key] for key in ('status', 'independentSelfTestGroups', 'independentRejectedControls',
                          'sourceAndArtifactStable', 'failure') if key in record}), flush=True)
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
