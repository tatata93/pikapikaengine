"""GNU13 seven-source advance CI driver; existing normal artifacts stay unchanged.

Normal must already contain three binaries/maps/compile_commands. Debug and
O1 ASan/UBSan are fresh separate builds. This is not a complete clock/commit
machine proof. Windows can only exercise CLI/path/platform refusals.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import os
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
GUARD_RECIPES = ROOT / 'reports/world-static-mesh-flight-guard-recipes'
HELPER_PATH = GUARD_RECIPES / 'verify-gnu.py'
AUDITOR_PATH = GUARD_RECIPES / 'audit-binding.py'
CLOCK = Path(__file__).with_name('clock-reference.py')
TRANSACTION_CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-advance.py'
TRANSACTION_CONTROLS = ROOT / 'tests/world_static_mesh_flight_advance_reference_tests.py'
PLAN = Path(__file__).with_name('GNU_PLAN.md')
ADVANCE = 'pikapika_world_static_mesh_flight_advance_tests'
GUARD = 'pikapika_world_static_mesh_flight_guard_tests'
FIXTURES = 'pikapika_world_static_mesh_flight_advance_fixtures'
SOURCE_SET = 'world-static-mesh-flight-advance-v1'
SOURCES = {'core/src/core.cpp', 'core/include/pikapika/core.hpp', 'core/src/dynamics.cpp',
           'core/include/pikapika/world_static_mesh_flight_guard.hpp', 'core/src/world_static_mesh_flight_guard.cpp',
           'core/include/pikapika/world_static_mesh_flight_advance.hpp', 'core/src/world_static_mesh_flight_advance.cpp'}
WARN = ('core/src/world_static_mesh_flight_advance.cpp', 'tests/world_static_mesh_flight_advance_tests.cpp',
        'tests/world_static_mesh_flight_advance_fixtures.cpp')
TARGET_SOURCES = {ADVANCE: {'tests/world_static_mesh_flight_advance_tests.cpp'}, GUARD: {
    'tests/world_static_mesh_flight_guard_tests.cpp', 'tests/world_static_mesh_flight_guard_fixtures.cpp',
    'tests/world_static_mesh_flight_preparation_fixtures.cpp', 'tests/sphere_triangle_mesh_free_flight_guard_fixtures.cpp',
    'tests/sphere_triangle_mesh_held_load_fixtures.cpp', 'tests/accelerated_pair_coverage_fixtures.cpp',
    'tests/accelerated_plane_box_coverage_fixtures.cpp', 'tests/accelerated_sphere_box_coverage_fixtures.cpp'}}
TARGET_SOURCES[FIXTURES] = (TARGET_SOURCES[GUARD] - {'tests/world_static_mesh_flight_guard_tests.cpp'}) | {
    'tests/world_static_mesh_flight_advance_fixtures.cpp'}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def write(path, data):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')


def import_file(name, path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sources():
    paths = {ROOT / 'CMakeLists.txt', Path(__file__).resolve(), HELPER_PATH, AUDITOR_PATH, CLOCK, PLAN}
    for folder, suffixes in (('core', {'.cpp', '.hpp', '.h'}), ('tests', {'.cpp', '.hpp', '.h', '.py'}),
                             ('scripts', {'.py'}), ('cmake', {'.cmake'})):
        paths.update(p for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in suffixes)
    for relative in ('assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json',
                     'build/native/Release/pikapika_core.lib', 'build/native/pikapika_core.dir/Release/core.obj',
                     'build/native/Release/pikapika_world_static_mesh_flight_guard_tests.exe',
                     'build/native/Release/world-flight-guard.map', 'build/native/world-flight-binding-Release.json'):
        path = ROOT / relative
        if path.is_file():
            paths.add(path)
    return [stamp(p) for p in sorted(paths)]


def checked_profile(helper, auditor, build, configuration):
    data = helper.load(build / ('world-flight-binding-' + configuration + '.json'))
    need(type(data.get('schema')) is int and data['schema'] == 1 and data.get('sourceSet') == SOURCE_SET,
         'Explicit seven-source advance profile required; no old/unknown profile fallback')
    need(data.get('configuration') == configuration and data.get('architecture') == 'x64-sse2', 'Configuration/architecture')
    need(data.get('compiler', {}).get('id') == 'GNU' and
         re.fullmatch(r'13(?:\.[0-9]+)*', data['compiler'].get('version', '')), 'GNU13 only')
    need(type(data.get('profile')) is int and data['profile'] == (1 if configuration == 'Release' else 0), 'Expected profile state')
    need(re.fullmatch('[0-9a-f]{64}', data.get('buildId', '')), 'Full configuration identity')
    rows = data.get('sources')
    need(isinstance(rows, list) and len(rows) == 7 and {row['path'] for row in rows} == SOURCES, 'Exact seven-source inventory')
    for row in rows:
        need(stamp(ROOT / row['path'])['sha256'] == row['sha256'], 'Current configured source hash')
    if configuration == 'Release':
        # Uses the real current auditor's seven-set flags/hash validation. Its
        # object/link machine audit is a separate actual child command below.
        auditor.check_profile(data)
    return data


def checked_normal_cache(helper, build):
    cache = helper.cache(build)
    need(cache.get('CMAKE_BUILD_TYPE') == 'Release' and cache.get('CMAKE_GENERATOR') == 'Unix Makefiles',
         'Existing normal Release Unix Makefiles build required')
    need(cache.get('CMAKE_EXPORT_COMPILE_COMMANDS') in ('ON', 'TRUE', '1'), 'Normal compile database must already be enabled')
    need(Path(cache.get('CMAKE_HOME_DIRECTORY', '')).resolve() == ROOT, 'Existing source directory differs')
    return cache


def normal_artifacts(helper, build, compilation, harnesses):
    paths = {build / 'CMakeCache.txt', build / 'compile_commands.json', build / 'world-flight-binding-Release.json',
             build / ADVANCE, build / GUARD, build / FIXTURES,
             build / 'world-flight-advance.map', build / 'world-flight-guard.map',
             build / 'world-flight-advance-fixtures.map',
             build / 'libpikapika_core.a'}
    paths.update(row['object'] for row in compilation.values())
    paths.update(Path(row['object']['path']) for row in harnesses.values())
    paths.update(build / 'CMakeFiles' / (target + '.dir') / 'link.txt' for target in TARGET_SOURCES)
    return [stamp(p) for p in sorted(paths)]


def advance_run(helper, commands, name, binary, output, env=None):
    text = commands.run(name + '-nine-groups', [binary, '--run'], env=env)
    match = re.search(rb'(\d+) directed groups PASS', text)
    need(match is not None and int(match[1]) == 9, 'Actual nine directed advance assertion groups required')
    raw = commands.run(name + '-clock-fixtures', [binary, '--clock-fixtures'], env=env)
    path = output / (name + '-clock-fixtures.json')
    path.write_bytes(raw)
    data = helper.load(path)
    need(type(data.get('schema')) is int and data['schema'] == 1 and
         data.get('kind') == 'world-static-mesh-flight-advance-clock-fixtures' and len(data.get('cases', [])) == 18,
         'Actual complete eighteen clock fixtures required')
    reference = json.loads(commands.run(name + '-clock-integer-reference', [sys.executable, CLOCK, path]))
    need(reference.get('status') == 'PASS' and reference.get('cases') == 18, 'Independent integer clock reference')
    return {'stdout': text, 'path': path, 'data': data, 'reference': reference}


def guard_run(helper, commands, name, binary, output, env=None):
    # Dependency guard51 and full advance transactions are separate captures.
    path, data = helper.run_fixture(commands, name + '-guard51', binary, output, env)
    commands.run(name + '-guard-independent-math', [sys.executable, helper.CHECKER, path])
    commands.run(name + '-guard-independent-controls', [sys.executable, helper.CONTROLS, path,
                 '--output', output / (name + '-guard-reference')])
    return path, data


def transaction_run(helper, commands, name, binary, output, env=None):
    raw = commands.run(name + '-full-transactions', [binary, '--fixtures'], env=env)
    path = output / (name + '-transactions.json')
    path.write_bytes(raw)
    data = helper.load(path)
    need(type(data.get('schema')) is int and data['schema'] == 1 and
         data.get('kind') == 'world-static-mesh-flight-advance-transaction-fixtures' and
         type(data.get('fixtures')) is list and len(data['fixtures']) == 51,
         'Actual complete one-call transaction51 capture required')
    reference = json.loads(commands.run(name + '-transaction-independent-reference',
                           [sys.executable, TRANSACTION_CHECKER, path]))
    need(reference.get('status') == 'PASS' and reference.get('fixtures') == 51,
         'Actual full transaction independent reference required')
    control_dir = output / (name + '-transaction-reference')
    controls = json.loads(commands.run(name + '-transaction-independent-controls',
        [sys.executable, TRANSACTION_CONTROLS, path, '--output', control_dir]))
    need(controls.get('status') == 'PASS' and controls.get('fixtures') == 51 and
         controls.get('labelAndOrderIndependent') is True and
         type(controls.get('negativeControls')) is int and controls['negativeControls'] > 0,
         'Actual full transaction controls required')
    control_report = helper.load(control_dir / 'negative-controls.json')
    optimized = control_report.get('optimizedPythonRejected', {})
    need(optimized.get('status') == 'PASS' and type(optimized.get('exitCode')) is int and
         optimized['exitCode'] != 0, 'Actual optimized-Python refusal required')
    return {'path': path, 'data': data, 'reference': reference, 'controls': controls,
            'controlsReport': stamp(control_dir / 'negative-controls.json')}


def compare_transactions(helper, normal, sanitized, normal_id, sanitized_id):
    """Normalize precisely two identity locations, only where owned guard exists."""
    need(type(normal_id) is str and type(sanitized_id) is str and
         re.fullmatch('[0-9a-f]{64}', normal_id) and re.fullmatch('[0-9a-f]{64}', sanitized_id)
         and normal_id != sanitized_id, 'Distinct valid normal/instrumented identities')
    left_data, right_data = deepcopy(normal), deepcopy(sanitized)
    counts = []
    for data, identity in ((left_data, normal_id), (right_data, sanitized_id)):
        need(type(data.get('schema')) is int and data['schema'] == 1 and
             data.get('kind') == 'world-static-mesh-flight-advance-transaction-fixtures' and
             type(data.get('fixtures')) is list and len(data['fixtures']) == 51,
             'Whole actual transaction51 documents')
        owned = 0
        for fixture in data['fixtures']:
            report = fixture['report']
            need(report['binding']['buildId'] == identity, 'AdvanceReport actual configuration identity')
            report['binding']['buildId'] = '<only-approved-configuration-identity>'
            if report['guard'] is not None:
                need(report['guard']['binding']['buildId'] == identity, 'Actual owned guard configuration identity')
                report['guard']['binding']['buildId'] = '<only-approved-configuration-identity>'
                owned += 1
        counts.append(owned)
    left, right = helper.exact_tree(left_data), helper.exact_tree(right_data)
    need(left == right, 'Full transaction JSON differs beyond the two authorized buildId locations')
    raw = json.dumps(left, ensure_ascii=False, separators=(',', ':')).encode()
    return {'status':'PASS', 'fixtures':51, 'ownedGuardsPerBuild':counts,
            'normalizedPaths':['fixtures[*].report.binding.buildId',
                               'fixtures[*].report.guard.binding.buildId iff guard is nonnull'],
            'normalBuildId':normal_id, 'sanitizedBuildId':sanitized_id,
            'comparison':'Complete key order, array order, scalar types and binary64 signed-zero bits; no other strings replaced.',
            'normalizedTreeSha256':sha256(raw).hexdigest()}


def harness_compilation(helper, build, *, sanitized):
    entries = helper.load(build / 'compile_commands.json')
    selected = {}
    for entry in entries:
        source = Path(entry['file'])
        if not source.is_absolute():
            source = Path(entry['directory']) / source
        argv = entry.get('arguments') or shlex.split(entry['command'])
        if '-o' not in argv:
            continue
        obj = Path(argv[argv.index('-o') + 1])
        if not obj.is_absolute():
            obj = Path(entry['directory']) / obj
        for target, paths in TARGET_SOURCES.items():
            if source.resolve() not in {ROOT / p for p in paths} or not obj.resolve().is_relative_to(build / 'CMakeFiles' / (target + '.dir')):
                continue
            key = target + ':' + source.relative_to(ROOT).as_posix()
            need(key not in selected, 'Duplicate harness command')
            if sanitized:
                need(set(helper.SANITIZERS) <= set(argv), 'Every linked harness/fixture TU must be instrumented')
                optimizations = [x for x in argv if re.fullmatch(r'-O(?:[0-3sgz]|fast)', x)]
                need(optimizations and all(x == '-O1' for x in optimizations) and '-DNDEBUG' in argv, 'Harness O1/NDEBUG')
            need(not any(re.match(r'-flto(?:=|$)', x) for x in argv), 'Harness has LTO')
            selected[key] = {'argv': argv, 'object': stamp(obj)}
    need(len(selected) == sum(map(len, TARGET_SOURCES.values())), 'Complete three-target harness/fixture source set')
    return selected


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal', type=Path, default=ROOT / 'build/ci')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/ci/advance-gnu-verification')
    parser.add_argument('--sanbuild', type=Path, default=ROOT / 'build/wfa-san')
    parser.add_argument('--debugbuild', type=Path, default=ROOT / 'build/wfa-debug')
    parser.add_argument('--parallel', type=int, default=2)
    parser.add_argument('--command-timeout', type=int, default=600)
    args = parser.parse_args()
    for key in ('normal', 'output', 'sanbuild', 'debugbuild'):
        path = getattr(args, key).resolve()
        need(path != ROOT / 'build' and path.is_relative_to(ROOT / 'build'), 'All paths must remain inside repository build children')
        setattr(args, key, path)
    need(len({args.normal, args.output, args.sanbuild, args.debugbuild}) == 4, 'Four distinct directories required')
    need(not args.normal.is_relative_to(args.output), 'Output must not contain the normal build')
    for other in (args.sanbuild, args.debugbuild):
        need(not other.exists(), 'Fresh sanitizer/Debug directory required')
        for peer in (args.normal, args.output, args.debugbuild if other == args.sanbuild else args.sanbuild):
            need(not other.is_relative_to(peer) and not peer.is_relative_to(other), 'Build/output directories must not overlap')
    need(1 <= args.parallel <= 4 and 30 <= args.command_timeout <= 1200, 'Bounded command settings')
    need(not args.output.exists(), 'Fresh output directory required')
    return args


def main():
    args = arguments()
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    (args.output / 'guard-helper.py.txt').write_bytes(HELPER_PATH.read_bytes())
    write(args.output / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd()), 'python': sys.version})
    before = sources()
    write(args.output / 'sources-before.json', before)
    helper = import_file('unchanged_guard_gnu_utilities_for_advance', HELPER_PATH)
    commands = helper.Commands(args.output, args.command_timeout)
    result = {'schema': 1, 'status': 'FAIL', 'kind': 'gnu13-seven-source-advance-ci',
              'clockCommitFormalMachineProof': False, 'actualGNUExecuted': False,
              'normalBuildReconfiguredOrBuilt': False,
              'scope': 'Normal existing artifact/compiler provenance; finite nine assertion groups, full eighteen clock JSON/integer reference and actual full transaction51/independent references; '
                       'separate Debug refusal and all-core O1 ASan/UBSan numerical/memory evidence. Not complete clock/commit machine proof or public acceptance.'}
    normal_before, normal_rows, normal_harnesses, compiler_before = None, None, None, None
    try:
        need(sys.platform.startswith('linux'), 'Actual Linux GNU13 execution required; Windows is refusal-only')
        auditor = import_file('actual_current_seven_source_binding_auditor', AUDITOR_PATH)
        checked_normal_cache(helper, args.normal)
        normal = checked_profile(helper, auditor, args.normal, 'Release')
        compiler = Path(normal['compiler']['path'])
        compiler_before = stamp(compiler)
        version = commands.run('actual-compiler-version', [compiler, '--version'])
        need(b'Free Software Foundation' in version, 'Actual GNU compiler identity required')
        # Preserve this observation even if a later artifact or numerical gate
        # fails. Windows/refused profiles never reach this compiler invocation.
        result['actualGNUExecuted'] = True
        actual_version = commands.run('actual-compiler-dumpversion', [compiler, '-dumpfullversion', '-dumpversion']).decode().strip()
        need(re.fullmatch(r'13(?:\.[0-9]+)*', actual_version), 'Actual GNU13 required')
        machine = commands.run('actual-compiler-target', [compiler, '-dumpmachine']).decode().strip()
        need(machine.startswith('x86_64'), 'Actual x86-64 compiler target required')
        normal_rows = helper.compilation(args.normal)
        normal_harnesses = harness_compilation(helper, args.normal, sanitized=False)
        normal_before = normal_artifacts(helper, args.normal, normal_rows, normal_harnesses)
        write(args.output / 'normal-artifacts-before.json', normal_before)
        write(args.output / 'normal-harness-compilation.json', normal_harnesses)
        raw = commands.run('normal-seven-source-artifact-audit', [sys.executable, AUDITOR_PATH,
            '--profile', args.normal / 'world-flight-binding-Release.json',
            '--object', normal_rows[(ROOT / 'core/src/core.cpp').resolve()]['object'],
            '--binary', args.normal / ADVANCE, '--map', args.normal / 'world-flight-advance.map',
            '--build-directory', args.normal, '--output', args.output / 'normal-binding'])
        audit = json.loads(raw)
        need(audit.get('status') == 'PASS' and audit['profile']['sourceSet'] == SOURCE_SET, 'Normal actual artifact audit')
        need(audit['advanceScope']['clockInstructionsAudited'] is False and
             audit['advanceScope']['commitPathAudited'] is False and audit['advanceScope']['WorldAdvanceAccepted'] is False,
             'Compilation/old leaf proof must not be promoted to clock/commit machine proof')
        warning_dir = args.output / 'warning-objects'
        warning_dir.mkdir()
        for index, source in enumerate(WARN):
            commands.run('new-warning-tu-' + str(index), [compiler, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-Werror',
                *helper.STRICT, '-I' + str(ROOT / 'core/include'),
                '-DPIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1', '-DPIKAPIKA_WORLD_FLIGHT_BUILD_ID="' + normal['buildId'] + '"',
                '-c', ROOT / source, '-o', warning_dir / (str(index) + '.o')])
        normal_advance = advance_run(helper, commands, 'normal', args.normal / ADVANCE, args.output)
        normal_guard_path, normal_guard = guard_run(helper, commands, 'normal', args.normal / GUARD, args.output)
        normal_transactions = transaction_run(helper, commands, 'normal', args.normal / FIXTURES, args.output)
        common = ['-G', 'Unix Makefiles', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DCMAKE_CXX_COMPILER=' + str(compiler), '-DBUILD_TESTING=ON']
        commands.run('debug-configure', ['cmake', '-S', ROOT, '-B', args.debugbuild, *common, '-DCMAKE_BUILD_TYPE=Debug'])
        commands.run('debug-build-both', ['cmake', '--build', args.debugbuild, '--target', ADVANCE, GUARD,
                                        '--parallel', args.parallel, '--verbose'])
        debug = checked_profile(helper, auditor, args.debugbuild, 'Debug')
        debug_advance = commands.run('debug-advance-profile0-refusal', [args.debugbuild / ADVANCE, '--unsupported-profile'])
        debug_guard = commands.run('debug-guard-profile0-refusal', [args.debugbuild / GUARD, '--unsupported-profile'])
        need(b'default NEW TU refusal' in debug_advance and b'unsupported build profile refusal PASS' in debug_guard,
             'Actual separate Debug profile0 refusal messages required')
        flags = ' '.join(['-O1', '-g', *helper.SANITIZERS])
        commands.run('sanitizer-configure', ['cmake', '-S', ROOT, '-B', args.sanbuild, *common, '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_CXX_FLAGS=' + flags, '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG',
            '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined'])
        commands.run('sanitizer-build-all-core-and-three-harnesses', ['cmake', '--build', args.sanbuild,
                     '--target', ADVANCE, GUARD, FIXTURES, '--parallel', args.parallel, '--verbose'])
        sanitized = checked_profile(helper, auditor, args.sanbuild, 'Release')
        need(sanitized['buildId'] != normal['buildId'], 'Instrumented configuration requires distinct identity')
        write(args.output / 'sanitized-core-compilation.json', helper.check_sanitized_compilation(args.sanbuild, normal_rows))
        write(args.output / 'sanitized-harness-compilation.json', harness_compilation(helper, args.sanbuild, sanitized=True))
        env = {'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1',
               'PYTHONDONTWRITEBYTECODE': '1'}
        san_advance = advance_run(helper, commands, 'sanitized', args.sanbuild / ADVANCE, args.output, env)
        san_guard_path, san_guard = guard_run(helper, commands, 'sanitized', args.sanbuild / GUARD, args.output, env)
        san_transactions = transaction_run(helper, commands, 'sanitized', args.sanbuild / FIXTURES, args.output, env)
        need(normal_advance['stdout'] == san_advance['stdout'], 'Normal/sanitized nine-group assertion stdout differs')
        left, right = helper.exact_tree(normal_advance['data']), helper.exact_tree(san_advance['data'])
        need(left == right, 'Complete clock18 JSON differs (no normalization allowed)')
        clock_comparison = {'status': 'PASS', 'cases': 18, 'normalization': 'NONE',
                            'comparison': 'Complete key/scalar type/order/binary64 signed-zero bits via unchanged exact_tree',
                            'treeSha256': sha256(json.dumps(left, separators=(',', ':')).encode()).hexdigest()}
        guard_comparison = helper.compare_fixtures(deepcopy(normal_guard), deepcopy(san_guard), normal['buildId'], sanitized['buildId'])
        transaction_comparison = compare_transactions(helper, normal_transactions['data'], san_transactions['data'],
                                                       normal['buildId'], sanitized['buildId'])
        write(args.output / 'clock-comparison.json', clock_comparison)
        write(args.output / 'guard-comparison.json', guard_comparison)
        write(args.output / 'transaction-comparison.json', transaction_comparison)
        result.update(status='PASS', actualGNUExecuted=True, actualCompilerVersion=actual_version, actualCompilerTarget=machine,
                      normalProfile=normal, sanitizedProfile=sanitized, debugProfile=debug,
                      normalBindingAudit=stamp(args.output / 'normal-binding/audit.json'),
                      advanceAssertionGroupsPerBuild=9, clockCasesPerBuild=18,
                      clockReferences={'normal': normal_advance['reference'], 'sanitized': san_advance['reference']},
                      clockComparison=clock_comparison, guardComparison=guard_comparison,
                      transactionComparison=transaction_comparison, transactionFixturesPerBuild=51,
                      transactionReferences={name: run['reference'] for name, run in [('normal',normal_transactions),('sanitized',san_transactions)]},
                      transactionControls={name: run['controls'] for name, run in [('normal',normal_transactions),('sanitized',san_transactions)]},
                      transactionCaptures={'normal':stamp(normal_transactions['path']), 'sanitized':stamp(san_transactions['path'])},
                      warningTranslationUnits=len(WARN), harnessCompileCommandsPerBuild=len(normal_harnesses),
                      libraryTranslationUnits=len(normal_rows), normalGuard=stamp(normal_guard_path), sanitizedGuard=stamp(san_guard_path),
                      scopeDetails={'normal': 'Actual existing seven-source artifact leaf/caller plus four actual compiler commands; no normal rebuild/reconfigure.',
                                    'sanitizer': 'All core library dependencies and all three harness/linked fixture sets O1 ASan/UBSan; numerical/memory development only, NOT normal-machine binding.',
                                    'fixtures': 'Actual fresh transaction51 per build includes complete input/World/Progress/Report/owned guard/messages/observations. Both actual datasets pass the new independent reference and controls. Complete comparison permits only the two declared buildId paths; clock18 comparison permits no normalization.',
                                    'helpers': 'Unchanged guard Commands/load/compilation/exact_tree/compare_fixtures. Here normal/sanitized mean actual normal vs instrumented configurations.',
                                    'unproved': 'Complete clock operation/commit/EH/alias machine proof, natural allocation faults, World response/TOI/SDK and all-target/public acceptance.'})
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = sources()
        write(args.output / 'sources-after.json', after)
        result['sourceStable'] = before == after
        if not result['sourceStable']:
            result.update(status='FAIL', stabilityError='Source/SDK/available old accepted artifact changed')
        if normal_before is not None:
            normal_after = normal_artifacts(helper, args.normal, normal_rows, normal_harnesses)
            write(args.output / 'normal-artifacts-after.json', normal_after)
            result['normalArtifactsStable'] = normal_before == normal_after
            if not result['normalArtifactsStable']:
                result.update(status='FAIL', normalArtifactError='Existing normal artifact/configuration changed')
        if compiler_before is not None:
            result['compilerStable'] = compiler_before == stamp(compiler_before['path'])
            if not result['compilerStable']:
                result.update(status='FAIL', compilerError='Compiler binary changed')
        result.update(commands=commands.items, recipe=stamp(Path(__file__)))
        write(args.output / 'verification.json', result)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
