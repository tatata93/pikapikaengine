"""Fresh main-CMake scheduler integration, without touching accepted builds.

Finite MSVC transaction/reference/target evidence; not a GNU, sanitizer, CPU
artifact, whole clock/commit/scheduler proof or SDK acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
RECIPE = Path(__file__).resolve()
HERE = RECIPE.parent
LIB = 'pikapika_world_static_mesh_flight_scheduler'
TEST = LIB + '_tests'
FULL = LIB + '_fixtures'
ADVANCE = 'pikapika_world_static_mesh_flight_advance_tests'
GUARD = 'pikapika_world_static_mesh_flight_guard_tests'
OLD51 = 'pikapika_world_static_mesh_flight_advance_fixtures'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='run-20261105-main-integration-001')
    parser.add_argument('--build', default='build/wfsm1')
    args = parser.parse_args()
    need(sys.platform == 'win32', 'Actual MSVC experiment only; no simulated GNU')
    need(re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}', args.name), 'Fresh single output component')
    build = (ROOT / args.build).resolve()
    out = HERE / args.name
    need(build.parent == ROOT / 'build' and re.fullmatch(r'wfsm[1-9][0-9]*', build.name), 'Fresh short build/wfsmN only')
    need(not build.exists() and not out.exists(), 'Never overwrite builds or raw evidence')
    build.mkdir()
    out.mkdir()
    (out / 'recipe.py.txt').write_bytes(RECIPE.read_bytes())
    write(out / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd())})
    sys.dont_write_bytecode = True
    old = runpy.run_path(str(HERE / 'check-full-fixtures.py'), run_name='readonly_full_helpers')
    formal = runpy.run_path(str(HERE / 'check-formal-binding.py'), run_name='readonly_formal_helpers')
    watched = set(old['protected']())
    watched.update({RECIPE, HERE / 'check-formal-binding.py', ROOT / 'cmake/PikapikaWorldFlightSchedulerBinding.cmake',
                    formal['FULL_CHECKER'], formal['FULL_CONTROLS'], formal['CREDIT_CHECKER'],
                    formal['FULL_BASELINE'], formal['PROTOTYPE'] / 'scheduler-profile.json',
                    formal['PROTOTYPE'] / 'observations.json', HERE / 'main-integration-before.cmake.txt'})
    # Prior isolated experiments are evidence, never input build directories.
    for directory in ['wfsf1', 'wfsb1', 'wfsb2']:
        watched.update(p for p in (ROOT / 'build' / directory).rglob('*') if p.is_file() and (
            p.suffix in {'.lib', '.exe', '.map', '.vcxproj'} or p.name.endswith('command.1.tlog') or p.name.endswith('.json')))
    watched = sorted(watched)
    identities = lambda: {p.relative_to(ROOT).as_posix(): stamp(p) for p in watched}
    before = identities()
    write(out / 'before.json', before)
    (out / 'CMakeLists.txt').write_bytes((ROOT / 'CMakeLists.txt').read_bytes())
    commands = []

    def run(name, argv, timeout=600):
        row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT), 'before': identities()}
        start = time.monotonic()
        try:
            done = subprocess.run(row['argv'], cwd=ROOT, capture_output=True, timeout=timeout)
            code, stdout, stderr = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as error:
            code, stdout, stderr = None, error.stdout or b'', (error.stderr or b'') + str(error).encode()
        except BaseException as error:
            code, stdout, stderr = None, b'', str(error).encode()
        (out / (name + '.stdout.txt')).write_bytes(stdout)
        (out / (name + '.stderr.txt')).write_bytes(stderr)
        row.update(exitCode=code, seconds=time.monotonic()-start, after=identities())
        row.update(sourceStable=row['before'] == row['after'], stdout=stamp(out / (name + '.stdout.txt')),
                   stderr=stamp(out / (name + '.stderr.txt')))
        commands.append(row)
        write(out / (name + '.command.json'), row)
        print(json.dumps({key: row[key] for key in ['name', 'exitCode', 'seconds', 'sourceStable']}), flush=True)
        if code != 0:
            print(stdout.decode('utf-8', errors='replace'), flush=True)
            print(stderr.decode('utf-8', errors='replace'), file=sys.stderr, flush=True)
        need(code == 0 and row['sourceStable'], 'Command failed or protected byte changed: ' + name)
        return stdout

    result = {'schema': 1, 'status': 'FAIL', 'scope': __doc__}
    try:
        # Save the exact authored CMake delta against the pre-edit raw snapshot.
        import difflib
        original = (HERE / 'main-integration-before.cmake.txt').read_bytes()
        current = (ROOT / 'CMakeLists.txt').read_bytes()
        delta = ''.join(difflib.unified_diff(original.decode().splitlines(True), current.decode().splitlines(True),
                                            fromfile='before/CMakeLists.txt', tofile='after/CMakeLists.txt'))
        (out / 'integration.patch').write_text(delta, encoding='utf-8', newline='\n')
        run('01-configure', ['cmake', '-S', ROOT, '-B', build, '-A', 'x64', '-DBUILD_TESTING=ON'])
        old_profile = json.loads((ROOT / 'build/wfa3/world-flight-binding-Release.json').read_bytes())
        new_profile = json.loads((build / 'world-flight-binding-Release.json').read_bytes())
        need(new_profile == old_profile, 'Fresh main seven-source profile changed; refuse normalization')
        seven = new_profile['buildId']
        profiles = {}
        for configuration in ['Release', 'Debug']:
            path = build / ('world-flight-scheduler-binding-' + configuration + '.json')
            profile = json.loads(path.read_bytes())
            material = profile['identityMaterial']
            need(hashlib.sha256(json.dumps(material, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() == profile['buildId'], 'Independent actual source2 config identity')
            need(material['upstreamAdvanceBuildId'] == seven and len(material['sources']) == 2, 'Separate source2 set and unchanged upstream reference')
            for source in material['sources']:
                need(stamp(ROOT / source['path'])['sha256'] == source['sha256'], 'Configured actual source2 hash')
            active = configuration == 'Release'
            need(profile['profile'] == int(active) and profile['runtimeBuildId'] == (profile['buildId'] if active else ''), 'Actual Release configured / Debug refused')
            profiles[configuration] = profile
            (out / path.name).write_bytes(path.read_bytes())
        identity = profiles['Release']['buildId']
        previous = json.loads((formal['PROTOTYPE'] / 'scheduler-profile.json').read_bytes())['buildId']
        need(identity != seven and identity != previous, 'Scheduler ID remains separate and config-derived')
        # Listing does not pretend that the old 47 tests were executed here.
        old_names = list(dict.fromkeys(re.findall(r'^\s*add_test\(\[=\[([^\]]+)\]=\]',
                                                  (ROOT / 'build/wfa3/CTestTestfile.cmake').read_text(), re.M)))
        listing = json.loads(run('02-ctest-list', ['ctest', '--test-dir', build, '-C', 'Release', '--show-only=json-v1']))
        names = [row['name'] for row in listing['tests']]
        need(len(old_names) == 47 and len(names) == 48 and set(names) == set(old_names) | {'world_static_mesh_flight_scheduler'}, 'Exactly old47 plus scheduler; no serialization-only CTest')
        write(out / 'ctest-inventory.json', {'oldNames': old_names, 'actualNames': names, 'oldTestsExecutedInThisRun': False})
        run('03-release-build', ['cmake', '--build', build, '--config', 'Release', '--target', TEST, FULL, OLD51, '--parallel', '2'], 900)
        run('04-new-ctest', ['ctest', '--test-dir', build, '-C', 'Release', '-R', '^world_static_mesh_flight_scheduler$', '--output-on-failure', '--timeout', '300'], 360)
        raw = run('05-thirteen', [build / 'Release' / (TEST + '.exe'), '--run'])
        need(raw == (formal['PROTOTYPE'] / '04-run.stdout.txt').read_bytes(), 'Actual Native13 directed stdout unchanged')
        raw = run('06-observations', [build / 'Release' / (TEST + '.exe'), '--observations'])
        (out / 'observations.json').write_bytes(raw)
        need(raw == (formal['PROTOTYPE'] / 'observations.json').read_bytes(), '1382 selected pumps raw exact, no normalization')
        run('07-credit-reference', [sys.executable, '-B', formal['CREDIT_CHECKER'], out / 'observations.json'], 240)
        raw = run('08-full-fixtures', [build / 'Release' / (FULL + '.exe'), '--fixtures'])
        (out / 'scheduler-full.json').write_bytes(raw)
        comparison = formal['compare_full'](json.loads(formal['FULL_BASELINE'].read_bytes()), json.loads(raw), previous, identity, seven)
        write(out / 'full-comparison.json', comparison)
        full_reference = json.loads(run('09-full-reference', [sys.executable, '-B', formal['FULL_CHECKER'], out / 'scheduler-full.json'], 240))
        full_controls = json.loads(run('10-full-controls', [sys.executable, '-B', formal['FULL_CONTROLS'], out / 'scheduler-full.json', '--output', out / 'full-controls'], 240))
        raw = run('11-legacy51', [build / 'Release' / (OLD51 + '.exe'), '--fixtures'])
        (out / 'legacy51.json').write_bytes(raw)
        need(raw == old['BASE'].read_bytes() and len(raw) == 2979456, 'Target-private macro preserves old51 main and all exact bytes')
        run('12-legacy51-reference', [sys.executable, '-B', old['CHECKER'], out / 'legacy51.json'], 240)
        run('13-legacy51-controls', [sys.executable, '-B', old['CONTROLS'], out / 'legacy51.json', '--output', out / 'legacy-controls'], 240)
        run('14-debug-build', ['cmake', '--build', build, '--config', 'Debug', '--target', TEST, GUARD, ADVANCE, '--parallel', '2'], 900)
        run('15-debug-scheduler-refusal', [build / 'Debug' / (TEST + '.exe'), '--unsupported-profile'])
        run('16-debug-guard-refusal', [build / 'Debug' / (GUARD + '.exe'), '--unsupported-profile'])
        run('17-debug-advance-refusal', [build / 'Debug' / (ADVANCE + '.exe'), '--unsupported-profile'])
        # Real compiler commands: only new3 TUs and the already shared writer
        # have WX. Seven old writers retain their previous warning policy.
        provenance = []
        new_sources = {formal['SCHEDULER'], formal['TEST'], formal['MAIN'], formal['SHARED']}
        for path in sorted(build.rglob('CL.command.1.tlog')):
            if not any(part in path.parts for part in [LIB + '.dir', TEST + '.dir', FULL + '.dir', OLD51 + '.dir']):
                continue
            entries = []
            lines = path.read_bytes().decode('utf-16').splitlines()
            debug = 'Debug' in path.parts
            for index, line in enumerate(lines):
                if not line.startswith('^'):
                    continue
                source = Path(line[1:]).resolve()
                end = next((j for j in range(index+1, len(lines)) if lines[j].startswith('^')), len(lines))
                command = ' '.join(lines[index+1:end])
                if source in new_sources:
                    for token in ['/W4', '/WX', '/permissive-', '/fp:strict', '/GL-']:
                        need(re.search(r'(?:^|\s)' + re.escape(token) + r'(?=\s|$)', command, re.I), 'Actual new-TU strict command token missing ' + token)
                    need(not re.search(r'(?:^|\s)/(?:GL|WX-)(?=\s|$)', command, re.I), 'Actual new-TU LTO/WX override')
                if source == formal['SCHEDULER']:
                    p = profiles['Debug' if debug else 'Release']
                    need('PIKAPIKA_FLIGHT_SCHEDULER_PROFILE=' + str(p['profile']) in command and p['buildId'] in command, 'Real source2 TU profile/ID')
                if source == formal['SHARED']:
                    library_only = 'PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY=1' in command
                    need(library_only == (FULL + '.dir' in path.parts), 'Library-only macro must be full-target private')
                entries.append({'source': source.relative_to(ROOT).as_posix(), 'command': command, 'newStrictTU': source in new_sources})
            copy = out / ('compile-' + str(len(provenance)) + '.tlog.txt')
            copy.write_bytes(path.read_bytes())
            provenance.append({'original': stamp(path), 'copy': stamp(copy), 'configuration': 'Debug' if debug else 'Release', 'entries': entries})
        need(len(provenance) == 6, 'Four Release and two Debug scheduler/old51 actual target tlogs')
        artifacts = [p for p in build.rglob('*') if p.is_file() and ('CMakeFiles' not in p.parts) and
                     (p.suffix in {'.exe', '.lib', '.map'} or p.name in {'core.obj', 'world-flight-binding-Release.json', 'world-flight-binding-Debug.json'})]
        result.update(status='FINITE_MAIN_SCHEDULER_INTEGRATION_PASS',
                      sevenSourceProfileExactToWfa3=True, unchangedSevenBuildId=seven, profiles=profiles,
                      newSchedulerBuildId=identity, source2SemanticsUnchanged=True,
                      ctestListed=48, ctestExecuted=['world_static_mesh_flight_scheduler'], old47ListedNotRerun=old_names,
                      nativeGroups=13, selectedPumps=1382, fullComparison=comparison,
                      fullReference=full_reference, fullControls=full_controls, legacy51RawIdentical=True,
                      DebugScope='Actual main-CMake Debug core and scheduler builds; explicit scheduler/guard/advance profile0 refusal only. Not Debug numerical acceptance.',
                      actualCompileProvenance=provenance, artifacts=[stamp(p) for p in sorted(artifacts)],
                      actualGNUExecuted=False, sanitizerExecuted=False, machineClockCommitProofComplete=False)
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = identities()
        write(out / 'after.json', after)
        result.update(sourceStable=before == after, protectedPaths=len(watched), commands=commands)
        if not result['sourceStable']:
            result['status'] = 'FAIL'
        write(out / 'result.json', result)
    print(json.dumps({key: result[key] for key in ['status', 'newSchedulerBuildId', 'sourceStable', 'error'] if key in result}), flush=True)
    return 0 if result['status'] == 'FINITE_MAIN_SCHEDULER_INTEGRATION_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
