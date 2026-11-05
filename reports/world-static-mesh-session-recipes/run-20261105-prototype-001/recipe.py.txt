"""Fresh isolated MSVC owned-session prototype over immutable accepted libraries.

Release ownership/lifetime/direct dyadic assertions and actual imported default
model refusal only. No full transcript/reference/GNU/main/SDK/fault acceptance.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
RECIPE = Path(__file__).resolve()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', default='build/wfo1')
    parser.add_argument('--name', default='run-20261105-prototype-001')
    args = parser.parse_args()
    need(sys.platform == 'win32', 'Actual MSVC Windows only')
    build = (ROOT / args.build).resolve()
    out = RECIPE.parent / args.name
    need(build.parent == ROOT / 'build' and re.fullmatch('wfo[1-9][0-9]*', build.name), 'Fresh short build/wfoN')
    need(re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}', args.name), 'Fresh report component')
    need(not build.exists() and not out.exists(), 'Never overwrite build/evidence')
    build.mkdir()
    out.mkdir()
    (out / 'recipe.py.txt').write_bytes(RECIPE.read_bytes())
    write(out / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd())})
    sys.dont_write_bytecode = True
    old = runpy.run_path(str(ROOT / 'reports/world-static-mesh-flight-scheduler-recipes/check-full-fixtures.py'), run_name='readonly_old_paths')
    helper = runpy.run_path(str(ROOT / 'reports/world-static-mesh-flight-advance-recipes/check-configured-prototype.py'), run_name='readonly_path_quote')
    quote = helper['cmake_path']
    base = ROOT / 'build/wfcqm2'
    variants = {'owner_configured': base / 'Release/pikapika_world_static_mesh_flight_controlled_scheduler.lib',
                'owner_default': ROOT / 'build/wfcq3/configured/Release/packet_default.lib'}
    libs = [base / ('Release/' + n + '.lib') for n in ['pikapika_world_static_mesh_flight_controlled_tick', 'pikapika_world_static_mesh_flight_scheduler', 'pikapika_core']]
    objects = sorted(p for p in (base / 'pikapika_world_static_mesh_flight_controlled_scheduler_tests.dir/Release').glob('*.obj') if p.name != 'world_static_mesh_flight_controlled_scheduler_tests.obj')
    need(len(objects) == 9 and all(p.is_file() for p in [*variants.values(), *libs]), 'Actual four immutable configured libraries/default parent and nine serializer objects')
    owned = [ROOT / p for p in ['core/include/pikapika/world_static_mesh_session.hpp', 'core/src/world_static_mesh_session.cpp', 'tests/world_static_mesh_session_tests.cpp']]
    watched = set(old['protected']()) | {RECIPE, *owned, *libs, *variants.values(), *objects}
    for name in ['wfcm1', 'wfcqm1', 'wfcqm2', 'wfcq3', 'wfcqt3']:
        watched.update(p for p in (ROOT / 'build' / name).rglob('*') if p.is_file() and (
            p.suffix in {'.exe', '.lib', '.map', '.vcxproj'} or p.name.endswith('command.1.tlog') or p.name.startswith('world-flight-')))
    watched = sorted(watched)
    identities = lambda: {p.relative_to(ROOT).as_posix(): stamp(p) for p in watched}
    before = identities()
    write(out / 'before.json', before)
    for p in owned:
        (out / (p.name + '.txt')).write_bytes(p.read_bytes())
    project = build / 'project'
    project.mkdir()
    lines = ['cmake_minimum_required(VERSION 3.24)', 'project(OwnedSessionPrototype LANGUAGES CXX)',
             'set(CMAKE_CXX_STANDARD 20)', 'set(CMAKE_CXX_STANDARD_REQUIRED ON)', 'set(CMAKE_CXX_EXTENSIONS OFF)',
             'set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL)', 'set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)',
             'if(NOT MSVC OR NOT MSVC_VERSION EQUAL 1951 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8 OR CMAKE_CROSSCOMPILING)',
             'message(FATAL_ERROR "Actual native matching MSVC19.51 x64 required")', 'endif()',
             'file(WRITE "${CMAKE_BINARY_DIR}/actual-compiler.txt" "${CMAKE_CXX_COMPILER}\n${CMAKE_CXX_COMPILER_VERSION}\n${CMAKE_SYSTEM_PROCESSOR}\n")',
             'add_library(owner_kernel STATIC ' + quote(owned[0]) + ' ' + quote(owned[1]) + ')',
             'target_include_directories(owner_kernel PUBLIC ' + quote(ROOT / 'core/include') + ')',
             'target_compile_options(owner_kernel PRIVATE /W4 /WX /permissive- /fp:strict /GL-)']
    for name, library in variants.items():
        lines += ['add_executable(' + name + ' ' + quote(owned[2]) + ' ' + ' '.join(quote(p) for p in objects) + ')',
                  'target_include_directories(' + name + ' PRIVATE ' + quote(ROOT / 'tests') + ')',
                  'target_compile_options(' + name + ' PRIVATE /W4 /WX /permissive- /fp:strict /GL-)',
                  'target_link_libraries(' + name + ' PRIVATE owner_kernel ' + ' '.join(quote(p) for p in [library, *libs]) + ')',
                  'target_link_options(' + name + ' PRIVATE /LTCG:OFF /OPT:NOREF /OPT:NOICF "/MAP:$<TARGET_FILE_DIR:' + name + '>/' + name + '.map")']
    (project / 'CMakeLists.txt').write_text('\n'.join(lines) + '\n', encoding='utf8', newline='\n')
    (out / 'project.cmake.txt').write_bytes((project / 'CMakeLists.txt').read_bytes())
    commands = []

    def run(name, argv):
        started = time.monotonic()
        done = subprocess.run(list(map(str, argv)), cwd=ROOT, capture_output=True, timeout=600)
        (out / (name + '.stdout.txt')).write_bytes(done.stdout)
        (out / (name + '.stderr.txt')).write_bytes(done.stderr)
        row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT), 'exitCode': done.returncode,
               'seconds': time.monotonic()-started, 'sourceStable': before == identities()}
        commands.append(row)
        write(out / (name + '.command.json'), row)
        print(json.dumps({k: row[k] for k in ['name', 'exitCode', 'seconds', 'sourceStable']}), flush=True)
        if done.returncode:
            print(done.stdout.decode(errors='replace')[-10000:])
            print(done.stderr.decode(errors='replace')[-10000:])
        need(done.returncode == 0 and row['sourceStable'], 'Actual command failed/protected input changed: ' + name)
        return done.stdout

    result = {'schema': 1, 'status': 'FAIL', 'scope': __doc__, 'actualNewGNUExecuted': False, 'mainCMakeChanged': False}
    try:
        run('01-configure', ['cmake', '-S', project, '-B', build / 'configured', '-A', 'x64'])
        compiler = (build / 'configured/actual-compiler.txt').read_text().splitlines()
        expected = json.loads((base / 'world-flight-binding-Release.json').read_bytes())['compiler']
        need(Path(compiler[0]).resolve() == Path(expected['path']).resolve() and compiler[1] == expected['version'] and compiler[2] == 'AMD64', 'Actual compiler matches accepted imported ABI')
        run('02-release-build', ['cmake', '--build', build / 'configured', '--config', 'Release', '--parallel', '2'])
        raw = run('03-directed', [build / 'configured/Release/owner_configured.exe', '--run'])
        need(b'13 lifecycle and 5 actual numerical groups PASS' in raw, 'Actual13 lifecycle /5 numerical assertion groups')
        need(b'actual default model refusal PASS' in run('04-default-model-refusal', [build / 'configured/Release/owner_default.exe', '--unsupported-profile']), 'Actual imported default model refusal')
        logs = []
        for p in sorted((build / 'configured').rglob('CL.command.1.tlog')):
            if not any(n + '.dir' in p.parts for n in ['owner_kernel', *variants]):
                continue
            command = p.read_bytes().decode('utf16')
            for token in ['/W4', '/WX', '/permissive-', '/fp:strict', '/GL-']:
                need(re.search(r'(?:^|\s)' + re.escape(token) + r'(?=\s|$)', command, re.I), 'Actual strict token: ' + token)
            copy = out / ('compile-' + str(len(logs)) + '.tlog.txt')
            copy.write_bytes(p.read_bytes())
            logs.append({'original': stamp(p), 'copy': stamp(copy)})
        need(len(logs) == 3, 'Three actual new owner/main compile logs')
        result.update(status='FINITE_OWNED_SESSION_PROTOTYPE_PASS', lifecycleGroups=13, actualNumericalGroups=5,
                      actualDefaultModelRefusal=True, actualCompiler=compiler, compileLogs=logs,
                      importedLibraries=[stamp(p) for p in [*libs, *variants.values()]],
                      limits='No full transcript/independent owner reference, GNU/default new-owner identity, actual Debug owner, busy/reentrant or allocation/post-child fault injection, thread atomicity, cross-registry authentication, SDK or game acceptance.')
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = identities()
        write(out / 'after.json', after)
        result.update(sourceStable=before == after, protectedPaths=len(watched), commands=commands)
        if before != after:
            result['status'] = 'FAIL'
        write(out / 'result.json', result)
    print(json.dumps({k: result[k] for k in ['status', 'sourceStable', 'error'] if k in result}), flush=True)
    return 0 if result['status'] == 'FINITE_OWNED_SESSION_PROTOTYPE_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
