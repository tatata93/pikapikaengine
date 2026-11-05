"""GNU13 packet scheduler: actual normal/Debug/all-dependency ASan-UBSan.

Normal build is immutable. Configuration identities are not a machine proof.
Windows can run comparison controls and actual platform refusal, not GNU.
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
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LIB = 'pikapika_world_static_mesh_flight_controlled_scheduler'
TEST, FULL = LIB + '_tests', LIB + '_fixtures'
MODULE = ROOT / 'cmake/PikapikaWorldFlightControlledSchedulerBinding.cmake'
CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-controlled-scheduler.py'
CONTROLS = ROOT / 'tests/world_static_mesh_flight_controlled_scheduler_reference_tests.py'
PROFILE = 'world-flight-controlled-scheduler-binding-'
WARN = {'core/src/world_static_mesh_flight_controlled_scheduler.cpp',
        'tests/world_static_mesh_flight_controlled_scheduler_tests.cpp',
        'tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp',
        'tests/world_static_mesh_flight_controlled_tick_fixtures.cpp',
        'tests/world_static_mesh_flight_advance_fixtures.cpp'}
SERIALIZERS = {'tests/' + n + '.cpp' for n in [
    'world_static_mesh_flight_controlled_tick_fixtures', 'world_static_mesh_flight_advance_fixtures',
    'world_static_mesh_flight_guard_fixtures', 'world_static_mesh_flight_preparation_fixtures',
    'sphere_triangle_mesh_free_flight_guard_fixtures', 'sphere_triangle_mesh_held_load_fixtures',
    'accelerated_pair_coverage_fixtures', 'accelerated_plane_box_coverage_fixtures',
    'accelerated_sphere_box_coverage_fixtures']}


def need(value, message):
    if not value:
        raise ValueError(message)


def imported(name, path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stamp(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def compare_full(helper, normal, sanitized, normal_ids, sanitized_ids):
    """Four named identities at eight exact paths; all other values preserved."""
    keys = {'packet', 'controlled', 'clock', 'advance'}
    for ids in [normal_ids, sanitized_ids]:
        need(type(ids) is dict and set(ids) == keys and len(set(ids.values())) == 4 and
             all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in ids.values()), 'Four distinct exact identity families')
    need(all(normal_ids[k] != sanitized_ids[k] for k in keys), 'Distinct normal/sanitized configuration IDs')
    trees, counts = [], []
    for original, ids in [(normal, normal_ids), (sanitized, sanitized_ids)]:
        data = deepcopy(original)
        need(type(data.get('fixtures')) is list and len(data['fixtures']) == 84 and
             data.get('kind') == 'world-static-mesh-flight-controlled-scheduler-fixtures', 'Actual complete84 corpus')
        count = [0] * 8
        def leaf(binding, key, family, slot):
            need(binding[key] == ids[family], 'Exact observed identity leaf')
            binding[key] = '<' + family + '-configuration-only>'
            count[slot] += 1
        for row in data['fixtures']:
            r = row['report']
            for key, family, slot in [('buildId', 'packet', 0), ('controlledBuildId', 'controlled', 1),
                                      ('schedulerBuildId', 'clock', 2), ('upstreamBuildId', 'advance', 3)]:
                leaf(r['binding'], key, family, slot)
            for tick in r['tickReports']:
                if tick is None:
                    continue
                c = tick['report']
                leaf(c['binding'], 'buildId', 'controlled', 4)
                leaf(c['binding'], 'upstreamBuildId', 'advance', 5)
                if c['child'] is not None:
                    leaf(c['child']['binding'], 'buildId', 'advance', 6)
                    if c['child']['guard'] is not None:
                        leaf(c['child']['guard']['binding'], 'buildId', 'advance', 7)
        need(count == [84, 84, 84, 84, 83, 83, 79, 79], 'Exactly660 identity leaves at8 paths')
        trees.append(helper.exact_tree(data))
        counts.append(count)
    need(trees[0] == trees[1], 'Whole raw-typed/ordered/IEEE64 tree differs outside exact identity paths')
    return {'status': 'PASS', 'frames': 84, 'identityFamilies': 4, 'pathPatterns': 8,
            'normalizedLeavesPerSide': counts, 'normalIds': normal_ids, 'sanitizedIds': sanitized_ids,
            'comparison': 'Every other key/array order, scalar type, IEEE64/signed-zero bit, unused slot, layout and storage observation exact.',
            'treeSha256': sha256(json.dumps(trees[0], ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()}


def compile_rows(helper, build, target, wanted):
    rows = {}
    for entry in helper.load(build / 'compile_commands.json'):
        directory = Path(entry['directory'])
        source = Path(entry['file'])
        source = (source if source.is_absolute() else directory / source).resolve()
        argv = entry.get('arguments') or shlex.split(entry['command'])
        need('-o' in argv and argv.index('-o') + 1 < len(argv), 'Actual object argument')
        obj = Path(argv[argv.index('-o') + 1])
        obj = (obj if obj.is_absolute() else directory / obj).resolve()
        if not obj.is_relative_to(build / 'CMakeFiles' / (target + '.dir')):
            continue
        relative = source.relative_to(ROOT).as_posix()
        need(relative in wanted and relative not in rows and obj.is_file(), 'Actual unique built target-specific TU')
        rows[relative] = {'argv': argv, 'directory': str(directory), 'object': obj}
    need(set(rows) == wanted, 'Exact linked TU inventory: ' + target)
    return rows


def profile(helper, tick, clock, advance, auditor, build, configuration):
    upstream = advance.checked_profile(helper, auditor, build, configuration)
    core, controlled_rows, _ = tick.library_compilation(helper, build)
    _, clock_rows, _ = clock.library_compilation(helper, build)
    controlled = tick.checked_controlled_tick_profile(helper, build, configuration, upstream, controlled_rows)
    scheduler = clock.checked_scheduler_profile(helper, build, configuration, upstream, clock_rows)
    own = helper.compilation(build, LIB)
    need(len(own) == 1 and set(own) == {ROOT / 'core/src/world_static_mesh_flight_controlled_scheduler.cpp'}, 'One actual packet library TU')
    data = helper.load(build / (PROFILE + configuration + '.json'))
    material = data['identityMaterial']
    active = int(configuration == 'Release')
    need(data['schema'] == 1 and type(data['profile']) is int and data['profile'] == active and data['configuration'] == configuration and
         data['sourceSet'] == material['sourceSet'] == 'world-static-mesh-flight-controlled-scheduler-v1' and data['artifactAuditComplete'] is False, 'Separate configured packet identity, no artifact promotion')
    need(re.fullmatch('[0-9a-f]{64}', data['buildId']) and data['runtimeBuildId'] == (data['buildId'] if active else ''), 'Runtime eligibility')
    need(sha256(json.dumps(material, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() == data['buildId'], 'Exact configuration identity formula')
    need(material['helperSha256'] == stamp(MODULE)['sha256'] and material['compileOptions'] == tick.CONTROLLED_TICK_OPTIONS and
         material['profile'] == active and material['upstreamProfile'] == 1 and material['IPO'] is False, 'Actual helper/options/upstream eligibility')
    for key, expected in [('controlledTickBuildId', controlled['buildId']), ('clockBuildId', scheduler['buildId']), ('upstreamAdvanceBuildId', upstream['buildId']),
                          ('compilerId', 'GNU'), ('compilerVersion', upstream['compiler']['version']), ('system', 'Linux'), ('architecture', 'x86_64'), ('pointerBytes', '8'), ('generator', 'Unix Makefiles')]:
        need(material[key] == expected, 'Actual packet material: ' + key)
    need(Path(material['compilerPath']).resolve() == Path(upstream['compiler']['path']).resolve(), 'Same actual compiler')
    cache = helper.cache(build)
    need(material['globalFlags'] == cache.get('CMAKE_CXX_FLAGS', '') and material['configurationFlags'] == cache.get('CMAKE_CXX_FLAGS_' + configuration.upper(), ''), 'Actual cache flags bound')
    need(len(material['sources']) == 2 and {r['path'] for r in material['sources']} == {'core/include/pikapika/world_static_mesh_flight_controlled_scheduler.hpp', 'core/src/world_static_mesh_flight_controlled_scheduler.cpp'}, 'Exactly own source2')
    for row in material['sources']:
        need(row['sha256'] == stamp(ROOT / row['path'])['sha256'] and row['flags'] == (tick.CONTROLLED_TICK_OPTIONS if row['path'].endswith('.cpp') else []), 'Actual two-source hash/options')
    argv = next(iter(own.values()))['argv']
    tick.strict_command(argv, werror=True)
    for macro, expected in [('PROFILE', str(active)), ('BUILD_ID', data['buildId']), ('CONTROLLED_ID', controlled['buildId']), ('CLOCK_ID', scheduler['buildId'])]:
        need(tick.definitions(argv, 'PIKAPIKA_CONTROLLED_SCHEDULER_' + macro) == [expected], 'Actual packet macro: ' + macro)
    libraries = {**core, **controlled_rows, **clock_rows, **own}
    need(len(core) == 40 and len(libraries) == 43, 'All core40+three actual independent library TUs')
    ids = {'packet': data['buildId'], 'controlled': controlled['buildId'], 'clock': scheduler['buildId'], 'advance': upstream['buildId']}
    return data, libraries, core, ids, upstream


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag, default in [('normal', 'build/ci-world-packet'), ('output', 'build/public-checks/packet-gnu'), ('sanbuild', 'build/wfq-san'), ('debugbuild', 'build/wfq-debug')]:
        parser.add_argument('--' + flag, type=Path, default=ROOT / default)
    parser.add_argument('--parallel', type=int, default=2)
    parser.add_argument('--command-timeout', type=int, default=600)
    args = parser.parse_args(argv)
    paths = []
    for key in ['normal', 'output', 'sanbuild', 'debugbuild']:
        p = getattr(args, key).resolve()
        need(p.is_relative_to(ROOT / 'build') and p != ROOT / 'build', 'Repository build children only')
        setattr(args, key, p)
        paths.append(p)
    need(args.output.is_relative_to(ROOT / 'build/public-checks') and args.output != ROOT / 'build/public-checks', 'Fresh public-checks child')
    need(len(set(paths)) == 4 and 1 <= args.parallel <= 4 and 30 <= args.command_timeout <= 1200, 'Distinct bounded paths/command settings')
    for p in [args.output, args.sanbuild, args.debugbuild]:
        need(not p.exists(), 'Never overwrite output/Debug/sanitizer')
    for i, a in enumerate(paths):
        for b in paths[i+1:]:
            need(not a.is_relative_to(b) and not b.is_relative_to(a), 'No path overlap')
    return args


def main():
    args = arguments()
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    args.output.mkdir(parents=True)
    (args.output / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    write(args.output / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd()), 'python': sys.version})
    tick = imported('packet_gnu_tick', ROOT / 'reports/world-static-mesh-flight-controlled-tick-recipes/verify-gnu.py')
    clock = imported('packet_gnu_clock', ROOT / 'reports/world-static-mesh-flight-scheduler-recipes/verify-gnu.py')
    helper = imported('packet_gnu_guard', tick.GUARD_RECIPE)
    advance = imported('packet_gnu_advance', tick.ADVANCE_RECIPE)
    auditor = imported('packet_gnu_auditor', tick.AUDITOR)
    commands = helper.Commands(args.output, args.command_timeout)
    def sources():
        paths = {Path(__file__).resolve(), HERE / 'GNU_PLAN.md',
                 ROOT / 'reports/world-static-mesh-flight-scheduler-recipes/verify-gnu.py'}
        paths.update(Path(v['path']) for v in tick.sources())
        return [stamp(p) for p in sorted(paths)]
    before = sources()
    write(args.output / 'sources-before.json', before)
    result = {'schema': 1, 'status': 'FAIL', 'actualGNUExecuted': False, 'normalBuildReconfiguredOrBuilt': False,
              'machineClockCommitProofComplete': False, 'SDKChanged': False,
              'scope': 'Finite actual GNU13 normal/Debug/all43 library and20 harness TU O1 ASan-UBSan only. No allocation/post-child fault injection, new machine instruction proof or game integration.'}
    normal_before = compiler_before = None
    try:
        need(sys.platform.startswith('linux'), 'Actual Linux GNU13 required; other platforms refusal-only')
        advance.checked_normal_cache(helper, args.normal)
        normal_profile, libraries, core, normal_ids, upstream = profile(helper, tick, clock, advance, auditor, args.normal, 'Release')
        compiler = Path(upstream['compiler']['path'])
        compiler_before = stamp(compiler)
        need(b'Free Software Foundation' in commands.run('compiler-version', [compiler, '--version']), 'Actual GNU compiler')
        version = commands.run('compiler-full-version', [compiler, '-dumpfullversion', '-dumpversion']).decode().strip()
        machine = commands.run('compiler-target', [compiler, '-dumpmachine']).decode().strip()
        need(version == upstream['compiler']['version'] and re.fullmatch(r'13(?:\.[0-9]+)*', version) and machine.startswith('x86_64'), 'Actual GNU13/x64 agrees')
        result['actualGNUExecuted'] = True
        wanted = {TEST: SERIALIZERS | {'tests/world_static_mesh_flight_controlled_scheduler_tests.cpp'}, FULL: SERIALIZERS | {'tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp'}}
        def harnesses(build, sanitized=False):
            result = {}
            for target, paths in wanted.items():
                for source, item in compile_rows(helper, build, target, paths).items():
                    tick.strict_command(item['argv'], sanitized=sanitized, werror=source in WARN)
                    need(tick.definitions(item['argv'], 'PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY') == ['1'], 'Target-private shared writer main suppression')
                    result[target + ':' + source] = item
            need(len(result) == 20, 'Actual twenty target-specific harness TUs')
            return result
        normal_harness = harnesses(args.normal)
        def artifacts():
            paths = {args.normal / 'CMakeCache.txt', args.normal / 'compile_commands.json'}
            for stem in ['world-flight-binding-', 'world-flight-controlled-tick-binding-', 'world-flight-scheduler-binding-', PROFILE]:
                paths.add(args.normal / (stem + 'Release.json'))
            for target in [LIB, 'pikapika_core', tick.LIBRARY, clock.LIBRARY]:
                paths.update([args.normal / ('lib' + target + '.a'), args.normal / 'CMakeFiles' / (target + '.dir/link.txt')])
            for target in wanted:
                paths.update([args.normal / target, args.normal / (target + '.map'), args.normal / 'CMakeFiles' / (target + '.dir/link.txt')])
            paths.update(v['object'] for v in [*libraries.values(), *normal_harness.values()])
            return [stamp(p) for p in sorted(paths)]
        def observed(rows):
            return {str(k): {'argv': v['argv'], 'directory': v['directory'], 'object': stamp(v['object'])} for k, v in rows.items()}
        normal_before = artifacts()
        write(args.output / 'normal-artifacts-before.json', normal_before)
        write(args.output / 'normal-library-compilation.json', observed(libraries))
        write(args.output / 'normal-harness-compilation.json', observed(normal_harness))
        warning = args.output / 'warning-objects'
        warning.mkdir()
        for i, source in enumerate(sorted(WARN)):
            item = libraries[(ROOT / source).resolve()] if source.startswith('core/') else normal_harness[(TEST if source.endswith('_tests.cpp') else FULL) + ':' + source]
            argv = list(item['argv'])
            tick.strict_command(argv, werror=True)
            argv[argv.index('-o') + 1] = str(warning / (str(i) + '.o'))
            tick.compile_at(commands, 'werror-' + str(i), argv, item['directory'])
        def run(build, prefix, env=None):
            directed = commands.run(prefix + '-directed', [build / TEST, '--run'], env=env)
            need(b'21 directed groups PASS' in directed, 'Actual21 assertions including separate raw NaN packet case')
            raw = commands.run(prefix + '-full84', [build / FULL, '--fixtures'], env=env)
            path = args.output / (prefix + '-full.json')
            path.write_bytes(raw)
            reference = json.loads(commands.run(prefix + '-independent', [sys.executable, '-B', CHECKER, path], env=env))
            need(reference['status'] == 'PASS' and reference['frames'] == 84 and reference['attempts'] == 83 and reference['committedTicks'] == 44, 'Actual84 independent reference')
            controls = json.loads(commands.run(prefix + '-controls', [sys.executable, '-B', CONTROLS, path, '--output', args.output / (prefix + '-controls')], env=env))
            need(controls['status'] == 'PASS' and controls['copiedRejectionControls'] == 80 and controls['optimizedPythonRefused'] is True and controls['actualOld88PureCoreRegression'] is True, 'Actual80 rejects, old88 and -O process')
            return {'raw': raw, 'directed': directed, 'data': helper.load(path), 'reference': reference, 'controls': controls, 'capture': stamp(path)}
        normal = run(args.normal, 'normal')
        common = ['-G', 'Unix Makefiles', '-DCMAKE_CXX_COMPILER=' + str(compiler), '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DBUILD_TESTING=ON']
        commands.run('debug-configure', ['cmake', '-S', ROOT, '-B', args.debugbuild, *common, '-DCMAKE_BUILD_TYPE=Debug'])
        commands.run('debug-build', ['cmake', '--build', args.debugbuild, '--target', TEST, '--parallel', args.parallel, '--verbose'])
        debug_profile, debug_libs, _, _, _ = profile(helper, tick, clock, advance, auditor, args.debugbuild, 'Debug')
        for item in debug_libs.values():
            need('-g' in item['argv'] and '-DNDEBUG' not in item['argv'], 'Actual Debug dependencies / no NDEBUG')
        need(b'default profile refusal PASS' in commands.run('debug-refusal', [args.debugbuild / TEST, '--unsupported-profile']), 'Actual Debug refusal')
        flags = ' '.join(['-O1', '-g', *helper.SANITIZERS])
        commands.run('sanitizer-configure', ['cmake', '-S', ROOT, '-B', args.sanbuild, *common, '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CXX_FLAGS=' + flags, '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG', '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined'])
        commands.run('sanitizer-build-all-dependencies', ['cmake', '--build', args.sanbuild, '--target', TEST, FULL, '--parallel', args.parallel, '--verbose'])
        san_profile, san_libs, _, san_ids, _ = profile(helper, tick, clock, advance, auditor, args.sanbuild, 'Release')
        write(args.output / 'sanitized-core-compilation.json', helper.check_sanitized_compilation(args.sanbuild, core))
        for source, item in san_libs.items():
            if source not in core:
                tick.strict_command(item['argv'], sanitized=True, werror=True)
        write(args.output / 'sanitized-library-compilation.json', observed(san_libs))
        write(args.output / 'sanitized-harness-compilation.json', observed(harnesses(args.sanbuild, sanitized=True)))
        env = {'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1', 'PYTHONDONTWRITEBYTECODE': '1'}
        san = run(args.sanbuild, 'sanitized', env)
        need(normal['directed'] == san['directed'], 'Actual normal/sanitized assertion stdout exact')
        comparison = compare_full(helper, normal['data'], san['data'], normal_ids, san_ids)
        replaced = san['raw']
        for family in sorted(san_ids):
            replaced = replaced.replace(san_ids[family].encode(), normal_ids[family].encode())
        need(replaced == normal['raw'], 'Same GNU ABI raw bytes exact beyond8 already validated ID paths')
        comparison['allOtherRawBytesExact'] = True
        write(args.output / 'full-comparison.json', comparison)
        result.update(status='PASS', actualCompilerVersion=version, actualCompilerTarget=machine,
                      normalProfile=normal_profile, debugProfile=debug_profile, sanitizedProfile=san_profile,
                      fullComparison=comparison, references={k: v['reference'] for k, v in [('normal', normal), ('sanitized', san)]},
                      controls={k: v['controls'] for k, v in [('normal', normal), ('sanitized', san)]},
                      captures={k: v['capture'] for k, v in [('normal', normal), ('sanitized', san)]},
                      libraryTranslationUnits=43, harnessTranslationUnits=20, warningTranslationUnits=5,
                      directedGroupsPerBuild=21, fullFramesPerBuild=84, copiedRejectionsPerBuild=80)
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = sources()
        write(args.output / 'sources-after.json', after)
        result['sourceStable'] = before == after
        if before != after:
            result.update(status='FAIL', sourceStabilityError=True)
        if normal_before is not None:
            after_artifacts = artifacts()
            write(args.output / 'normal-artifacts-after.json', after_artifacts)
            result['normalArtifactsStable'] = normal_before == after_artifacts
            if normal_before != after_artifacts:
                result.update(status='FAIL', normalArtifactsChanged=True)
        if compiler_before is not None:
            result['compilerStable'] = compiler_before == stamp(compiler_before['path'])
            if not result['compilerStable']:
                result['status'] = 'FAIL'
        result.update(commands=commands.items, recipe=stamp(Path(__file__)))
        write(args.output / 'verification.json', result)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
