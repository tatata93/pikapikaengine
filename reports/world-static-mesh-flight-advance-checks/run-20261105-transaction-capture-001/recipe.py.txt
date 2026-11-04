"""Build only a new fixture probe against frozen local Native development objects.

No existing build is reconfigured/rebuilt. This generates finite saved data, not
new binary machine attestation, independent mathematical or public acceptance.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'build/wfa2'
MAIN = ROOT / 'tests/world_static_mesh_flight_advance_fixtures.cpp'
SUPPORT = ROOT / 'tests/world_static_mesh_flight_advance_fixture_support.hpp'
OBJECT_NAMES = ('accelerated_pair_coverage_fixtures', 'accelerated_plane_box_coverage_fixtures',
                'accelerated_sphere_box_coverage_fixtures', 'sphere_triangle_mesh_free_flight_guard_fixtures',
                'sphere_triangle_mesh_held_load_fixtures', 'world_static_mesh_flight_guard_fixtures',
                'world_static_mesh_flight_preparation_fixtures')

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}

def snapshot(paths):
    return [stamp(p) for p in paths]

def write(path, value):
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    output, build = args.output.resolve(), args.build.resolve()
    need(output.is_relative_to(ROOT / 'reports/world-static-mesh-flight-advance-checks') and
         output != ROOT / 'reports/world-static-mesh-flight-advance-checks', 'Fresh report child')
    need(build.is_relative_to(ROOT / 'build') and build != ROOT / 'build' and
         build not in (ROOT / 'build/native', NATIVE), 'Separate fresh build child')
    project = build.with_name(build.name + '-src')
    need(not any(p.exists() for p in (output, build, project)), 'All output/build/project paths must be fresh')
    output.mkdir(parents=True)
    project.mkdir(parents=True)
    objects = [NATIVE / 'pikapika_world_static_mesh_flight_guard_tests.dir/Release' / (n + '.obj') for n in OBJECT_NAMES]
    library = NATIVE / 'Release/pikapika_core.lib'
    protected = {Path(__file__).resolve(), ROOT / 'CMakeLists.txt', ROOT / 'cmake/WorldFlightBinding.cmake',
                 ROOT / 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py', MAIN, SUPPORT, library, *objects}
    for folder in ('core', 'tests'):
        protected.update(p for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in ('.cpp', '.hpp', '.h'))
    for directory in (ROOT / 'build/native', NATIVE):
        for name in ('Release/pikapika_core.lib', 'pikapika_core.dir/Release/core.obj', 'world-flight-binding-Release.json'):
            protected.add(directory / name)
        protected.update(p for p in (directory / 'Release').glob('pikapika*probe.exe'))
        protected.update(p for p in (directory / 'Release').glob('pikapika*world_static_mesh_flight*tests.exe'))
        protected.update((directory / 'Release').glob('world-flight-*.map'))
    protected.update(ROOT / p for p in ('assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json'))
    protected = sorted(protected)
    before = snapshot(protected)
    write(output / 'before.json', before)
    shutil.copyfile(Path(__file__), output / 'recipe.py.txt')
    profile = json.loads((NATIVE / 'world-flight-binding-Release.json').read_text(encoding='utf8'))
    need(profile['sourceSet'] == 'world-static-mesh-flight-advance-v1' and profile['profile'] == 1 and
         len(profile['sources']) == 7, 'Existing seven-source Release profile')
    for row in profile['sources']:
        need(stamp(ROOT / row['path'])['sha256'] == row['sha256'], 'Existing profile source unchanged')
    shutil.copyfile(NATIVE / 'world-flight-binding-Release.json', output / 'reused-profile.json')
    quote = lambda p: '"' + p.as_posix().replace('"', '\\"') + '"'
    cmake = '\n'.join((
        'cmake_minimum_required(VERSION 3.24)', 'project(WorldAdvanceFixtureProbe LANGUAGES CXX)',
        'add_library(frozen_core STATIC IMPORTED)',
        'set_target_properties(frozen_core PROPERTIES IMPORTED_LOCATION ' + quote(library) + ')',
        'add_executable(pp_wfat ' + quote(MAIN) + ')',
        'target_compile_features(pp_wfat PRIVATE cxx_std_20)',
        'target_include_directories(pp_wfat PRIVATE ' + quote(ROOT / 'core/include') + ' ' + quote(ROOT / 'tests') + ')',
        'target_compile_options(pp_wfat PRIVATE /W4 /WX /permissive- /fp:strict /GL-)',
        'target_link_options(pp_wfat PRIVATE /LTCG:OFF /INCREMENTAL:NO /OPT:NOREF "/MAP:${CMAKE_BINARY_DIR}/fixture.map")',
        'target_link_libraries(pp_wfat PRIVATE frozen_core ' + ' '.join(quote(p) for p in objects) + ')',
        'file(WRITE "${CMAKE_BINARY_DIR}/compiler.txt" "${CMAKE_CXX_COMPILER_ID}\\n${CMAKE_CXX_COMPILER_VERSION}\\n${CMAKE_CXX_COMPILER}\\n${CMAKE_LINKER}\\n")', ''))
    (project / 'CMakeLists.txt').write_text(cmake, encoding='utf8', newline='\n')
    shutil.copyfile(project / 'CMakeLists.txt', output / 'probe-project.CMakeLists.txt')
    result = {'schema': 1, 'status': 'FAIL', 'started': datetime.now(timezone.utc).isoformat(),
              'scope': 'New standalone MSVC fixture-main strict-Werror compile linked to unchanged existing local core library and7 fixture objects. Finite saved transactions only; no new artifact machine gate, independent checker, sanitizer/GNU or public acceptance.',
              'reusedBuildId': profile['buildId'], 'commands': [], 'newArtifactMachineAccepted': False,
              'independentTransactionCheckerPassed': False, 'reusedObjects': [stamp(p) for p in objects]}
    def run(name, argv, timeout):
        start = time.monotonic()
        done = subprocess.run(list(map(str, argv)), cwd=ROOT, capture_output=True, timeout=timeout)
        row = {'name': name, 'argv': list(map(str, argv)), 'exitCode': done.returncode, 'elapsedSeconds': time.monotonic()-start}
        for stream in ('stdout', 'stderr'):
            path = output / (name + '.' + stream + '.txt')
            path.write_bytes(getattr(done, stream)); row[stream] = stamp(path)
        result['commands'].append(row); write(output / (name + '.command.json'), row)
        if done.returncode:
            print(json.dumps({'failed': name, 'stdout': done.stdout.decode('utf8', errors='replace'), 'stderr': done.stderr.decode('utf8', errors='replace')}), flush=True)
        need(done.returncode == 0, 'Actual command failed: ' + name)
        need(snapshot(protected) == before, 'Frozen source/artifact changed during ' + name)
        return done.stdout
    try:
        run('configure', ['cmake', '-S', project, '-B', build, '-G', 'Visual Studio 18 2026', '-A', 'x64'], 180)
        facts = (build / 'compiler.txt').read_text(encoding='utf8').splitlines()
        need(len(facts) == 4 and facts[0] == 'MSVC' and facts[1].startswith('19.51.'), 'Actual existing MSVC19.51 only')
        result['compiler'] = {'id': facts[0], 'version': facts[1], 'path': facts[2], 'linker': facts[3]}
        tool_paths = [Path(facts[2]), Path(facts[3])]
        tool_before = [{'path': str(p), 'sha256': sha256(p.read_bytes()).hexdigest()} for p in tool_paths]
        run('build-fixture-probe', ['cmake', '--build', build, '--config', 'Release', '--parallel', '2'], 300)
        raw = run('capture-transactions', [build / 'Release/pp_wfat.exe', '--fixtures'], 180)
        packet = json.loads(raw)
        need(packet['schema'] == 1 and packet['kind'] == 'world-static-mesh-flight-advance-transaction-fixtures' and
             len(packet['fixtures']) == 51, 'Actual complete transaction51 JSON envelope')
        fixture_path = output / 'transactions.json'; fixture_path.write_bytes(raw)
        result.update(status='FINITE_FIXTURE_CAPTURE_PASS', cases=51, fixture=stamp(fixture_path),
                      actualArtifacts=[stamp(p) for p in (build / 'Release/pp_wfat.exe', build / 'fixture.map')],
                      compilerAndLinker=tool_before)
        need(tool_before == [{'path': str(p), 'sha256': sha256(p.read_bytes()).hexdigest()} for p in tool_paths], 'Compiler/linker unchanged')
    except Exception as error:
        result.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
    finally:
        after = snapshot(protected); write(output / 'after.json', after)
        result['protectedUnchanged'] = before == after
        result['protectedFiles'] = len(protected)
        if before != after:
            result.update(status='FAIL', error='Protected source/artifact changed')
        result['finished'] = datetime.now(timezone.utc).isoformat()
        write(output / 'result.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'cases', 'protectedFiles', 'protectedUnchanged', 'error') if k in result}), flush=True)
    return 0 if result['status'] == 'FINITE_FIXTURE_CAPTURE_PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
