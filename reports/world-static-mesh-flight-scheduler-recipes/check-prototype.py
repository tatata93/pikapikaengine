"""Fresh MSVC scheduler TU experiment using the immutable wfa3 imported library.

No main configure, old build, source integration, GNU execution, independent
checker or artifact/clock/commit formal proof is performed by this recipe.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'core/src/world_static_mesh_flight_scheduler.cpp'
HEADER = ROOT / 'core/include/pikapika/world_static_mesh_flight_scheduler.hpp'
TEST = ROOT / 'tests/world_static_mesh_flight_scheduler_tests.cpp'
HELPER = ROOT / 'reports/world-static-mesh-flight-advance-recipes/check-configured-prototype.py'
LIBRARY = ROOT / 'build/wfa3/Release/pikapika_core.lib'
OLD_PROFILE = ROOT / 'build/wfa3/world-flight-binding-Release.json'
OPTIONS = ['/W4', '/WX', '/permissive-', '/fp:strict', '/GL-']

def need(ok, message):
    if not ok:
        raise ValueError(message)

def stamp(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')

def protected():
    result = {SOURCE, HEADER, TEST, HELPER, Path(__file__).resolve(), ROOT / 'CMakeLists.txt', ROOT / 'cmake/WorldFlightBinding.cmake'}
    result.update(path for path in (ROOT / 'core').rglob('*') if path.is_file() and path.suffix in {'.cpp', '.hpp', '.h'})
    result.update(path for path in (ROOT / 'assets').glob('pikapika-simulation*') if path.is_file())
    for name in ['native', 'wfa2', 'wfat1', 'wfa3']:
        directory = ROOT / 'build' / name
        result.update(path for path in directory.rglob('*') if path.is_file() and (
            path.name == 'pikapika_core.lib' or path.name == 'core.obj' or path.suffix in {'.exe', '.map', '.vcxproj'} or
            path.name.startswith('world-flight-binding-') or path.name.endswith('command.1.tlog')))
    result.update(path for path in (ROOT / 'tests').glob('world_static_mesh_flight*') if path.is_file())
    return sorted(result)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='run-20261105-prototype-001')
    parser.add_argument('--build', default='build/wfs1')
    args = parser.parse_args()
    need(re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}', args.name), 'Safe fresh report component required')
    build = (ROOT / args.build).resolve()
    need(build.parent == ROOT / 'build' and re.fullmatch(r'wfs[1-9][0-9]*', build.name), 'Fresh short build/wfsN only')
    output = Path(__file__).parent / args.name
    need(not build.exists() and not output.exists(), 'Never overwrite scratch or report')
    need(sys.platform == 'win32', 'This isolated recipe is MSVC Windows only; no GNU success substitution')
    build.mkdir(); output.mkdir()
    (output / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    write(output / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd()), 'UTC': datetime.now(timezone.utc).isoformat()})
    paths = protected()
    identities = lambda: {path.relative_to(ROOT).as_posix(): stamp(path) for path in paths}
    before = identities(); write(output / 'before.json', before)
    commands = []
    def run(name, argv, timeout=600):
        record = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT), 'before': identities()}
        started = time.monotonic()
        try:
            done = subprocess.run(record['argv'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            code, stdout, stderr = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as error:
            code, stdout, stderr = None, error.stdout or b'', (error.stderr or b'') + str(error).encode()
        except BaseException as error:
            code, stdout, stderr = None, b'', str(error).encode()
        (output / (name + '.stdout.txt')).write_bytes(stdout)
        (output / (name + '.stderr.txt')).write_bytes(stderr)
        record.update(exitCode=code, seconds=time.monotonic()-started, after=identities())
        record['sourceStable'] = record['before'] == record['after']
        record['stdout'] = stamp(output / (name + '.stdout.txt')); record['stderr'] = stamp(output / (name + '.stderr.txt'))
        commands.append(record); write(output / (name + '.command.json'), record)
        print(json.dumps({'command': name, 'exitCode': code, 'seconds': record['seconds'], 'stable': record['sourceStable']}), flush=True)
        if code != 0:
            print(stdout.decode('utf-8', errors='replace'), flush=True); print(stderr.decode('utf-8', errors='replace'), file=sys.stderr, flush=True)
        need(code == 0 and record['sourceStable'], 'Command failed or protected files changed: ' + name)
        return stdout
    summary = {'schema': 1, 'status': 'FAIL', 'scope': 'Isolated MSVC19.51 x64 finite scheduler prototype. Imported seven-source library unchanged. No independent checker, GNU, sanitizer, full nested fixture serialization, main integration or machine clock/commit proof.'}
    try:
        sys.dont_write_bytecode = True
        helper = runpy.run_path(str(HELPER), run_name='scheduler_readonly_build_helpers')
        probe = build / 'probe'; probe.mkdir()
        (probe / 'CMakeLists.txt').write_text(helper['preamble']('SchedulerCompilerProbe'), encoding='utf-8', newline='\n')
        run('01-compiler-probe', ['cmake', '-S', probe, '-B', build / 'probe-build', '-A', 'x64'])
        facts = json.loads((build / 'probe-build/compiler-facts.json').read_text())
        need(facts['CMAKE_CXX_COMPILER_ID'] == 'MSVC' and facts['MSVC_VERSION'] == '1951' and facts['CMAKE_SIZEOF_VOID_P'] == '8', 'Known genuine MSVC19.51 x64 only')
        old = json.loads(OLD_PROFILE.read_text())
        need(old['sourceSet'] == 'world-static-mesh-flight-advance-v1' and len(old['sources']) == 7 and old['profile'] == 1, 'Actual imported seven-source Release profile required')
        material = {'schema': 1, 'kind': 'scheduler-isolated-config-v1', 'sources': [stamp(HEADER), stamp(SOURCE)], 'compiler': facts,
                    'compileOptions': OPTIONS, 'configuration': 'Release', 'standard': 'C++20', 'IPO': False, 'linkOptions': ['/LTCG:OFF'],
                    'importedLibrary': stamp(LIBRARY), 'importedSevenSourceBuildId': old['buildId']}
        canonical = json.dumps(material, sort_keys=True, separators=(',', ':')).encode()
        identity = hashlib.sha256(canonical).hexdigest()
        need(identity != old['buildId'], 'Scheduler identity cannot reuse seven-source ID')
        write(output / 'identity-material.json', material)
        (output / 'identity-material.canonical.txt').write_bytes(canonical)
        write(output / 'scheduler-profile.json', {'schema': 1, 'profile': 1, 'buildId': identity, 'sourceCount': 2, 'oldSevenBuildId': old['buildId'], 'artifactAuditComplete': False})
        project = build / 'project'; project.mkdir()
        quote = helper['cmake_path']; cquote = helper['cmake_quote']
        lines = [helper['preamble']('SchedulerIsolatedPrototype'), 'add_library(old_core STATIC IMPORTED)',
                 'set_target_properties(old_core PROPERTIES IMPORTED_LOCATION ' + quote(LIBRARY) + ')']
        for target, enabled in [('scheduler_prototype', True), ('scheduler_unconfigured', False)]:
            lines += ['add_executable(' + target + ' ' + quote(SOURCE) + ' ' + quote(TEST) + ')',
                      'target_include_directories(' + target + ' PRIVATE ' + quote(ROOT / 'core/include') + ')',
                      'target_link_libraries(' + target + ' PRIVATE old_core)',
                      'target_compile_options(' + target + ' PRIVATE ' + ' '.join(OPTIONS) + ')',
                      'set_property(TARGET ' + target + ' PROPERTY INTERPROCEDURAL_OPTIMIZATION FALSE)',
                      'target_link_options(' + target + ' PRIVATE /LTCG:OFF "/MAP:$<TARGET_FILE_DIR:' + target + '>/' + target + '.map")']
            if enabled:
                definition = 'PIKAPIKA_FLIGHT_SCHEDULER_PROFILE=1;PIKAPIKA_FLIGHT_SCHEDULER_BUILD_ID="' + identity + '"'
                lines.append('target_compile_definitions(' + target + ' PRIVATE ' + cquote(definition) + ')')
        driver = '\n'.join(lines) + '\n'
        (project / 'CMakeLists.txt').write_text(driver, encoding='utf-8', newline='\n')
        (output / 'CMakeLists.txt').write_text(driver, encoding='utf-8', newline='\n')
        run('02-configure', ['cmake', '-S', project, '-B', build / 'configured', '-A', 'x64'])
        run('03-build', ['cmake', '--build', build / 'configured', '--config', 'Release', '--parallel', '2'])
        exe = build / 'configured/Release/scheduler_prototype.exe'
        raw = run('04-run', [exe, '--run'])
        observation = run('05-observations', [exe, '--observations'])
        (output / 'observations.json').write_bytes(observation)
        data = json.loads(observation)
        need(data['kind'] == 'world-flight-scheduler-prototype-observations', 'Actual complete observation JSON required')
        run('06-default-refusal', [build / 'configured/Release/scheduler_unconfigured.exe', '--unsupported-profile'])
        command_provenance = []
        for path in sorted((build / 'configured').rglob('CL.command.1.tlog')):
            if not any(part in path.parts for part in ['scheduler_prototype.dir', 'scheduler_unconfigured.dir']):
                continue  # CMake's compiler-id probe is NOT either product TU.
            rawlog = path.read_bytes(); text = rawlog.decode('utf-16')
            target_configured = 'scheduler_prototype.dir' in path.parts
            entries, lines = [], text.splitlines()
            for i, line in enumerate(lines):
                if not line.startswith('^'):
                    continue
                end = next((j for j in range(i+1, len(lines)) if lines[j].startswith('^')), len(lines))
                command = ' '.join(lines[i+1:end])
                source = Path(line[1:]).resolve()
                need(source in {SOURCE, TEST}, 'Unexpected compilation in dedicated new target')
                fp = re.findall(r'(?:^|\s)/fp:([^\s]+)', command, re.I)
                need(fp and all(flag.casefold() == 'strict' for flag in fp), 'Actual new source must be strict')
                for token in ['/WX', '/W4', '/permissive-', '/GL-']:
                    need(re.search(r'(?:^|\s)' + re.escape(token) + r'(?=\s|$)', command, re.I), 'Actual new source flag missing: ' + token)
                need(not re.search(r'(?:^|\s)/(?:WX-|GL)(?=\s|$)', command, re.I), 'Actual command weakens warning or LTO gate')
                if target_configured:
                    need(identity in command and 'PIKAPIKA_FLIGHT_SCHEDULER_PROFILE=1' in command, 'Actual separate scheduler identity missing')
                entries.append({'source': source.relative_to(ROOT).as_posix(), 'command': command})
            need(len(entries) == 2 and {row['source'] for row in entries} == {SOURCE.relative_to(ROOT).as_posix(), TEST.relative_to(ROOT).as_posix()}, 'Both new sources must have actual command evidence')
            copy = output / ('compile-' + str(len(command_provenance)) + '.tlog.txt'); copy.write_bytes(rawlog)
            command_provenance.append({'original': stamp(path), 'copy': stamp(copy), 'entries': entries, 'scope': 'Actual compiler command capture, not machine instruction proof'})
        need(len(command_provenance) == 2, 'Two independent configured/default new-target actual compile logs')
        artifacts = [stamp(path) for path in sorted((build / 'configured').rglob('*')) if path.is_file() and path.suffix in {'.exe', '.obj', '.map', '.vcxproj'}]
        summary.update(status='FINITE_ISOLATED_PROTOTYPE_PASS', directedGroups=13, pumpObservations=len(data['traces']),
                       configuredStdout=raw.decode().strip(), separateBuildId=identity, oldSevenBuildId=old['buildId'],
                       compileProvenance=command_provenance, artifacts=artifacts, actualGNUExecuted=False, independentCheckerComplete=False)
    except BaseException as error:
        summary['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = identities(); write(output / 'after.json', after)
        summary.update(sourceStable=before == after, protectedPaths=len(paths), commands=commands)
        if not summary['sourceStable']:
            summary['status'] = 'FAIL'
        write(output / 'result.json', summary)
    print(json.dumps({'status': summary['status'], 'report': str(output / 'result.json'), 'error': summary.get('error')}), flush=True)
    return 0 if summary['status'] == 'FINITE_ISOLATED_PROTOTYPE_PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
