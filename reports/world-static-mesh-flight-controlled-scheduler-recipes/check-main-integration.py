"""Fresh main-CMake MSVC packet scheduler acceptance; no old build is mutated.

Finite same-ABI transcript/reference, actual compile commands and Debug-core
refusal only. GNU/sanitizer/SDK and complete machine proof remain separate.
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
HERE = RECIPE.parent
LIB = 'pikapika_world_static_mesh_flight_controlled_scheduler'
TICK = 'pikapika_world_static_mesh_flight_controlled_tick'
CLOCK = 'pikapika_world_static_mesh_flight_scheduler'
MODULE = ROOT / 'cmake/PikapikaWorldFlightControlledSchedulerBinding.cmake'
CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-controlled-scheduler.py'
CONTROLS = ROOT / 'tests/world_static_mesh_flight_controlled_scheduler_reference_tests.py'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='run-20261105-main-integration-001')
    parser.add_argument('--build', default='build/wfcqm1')
    args = parser.parse_args()
    need(sys.platform == 'win32', 'Actual MSVC Windows only')
    need(re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}', args.name), 'Fresh evidence component')
    build = (ROOT / args.build).resolve()
    out = HERE / args.name
    need(build.parent == ROOT / 'build' and re.fullmatch(r'wfcqm[1-9][0-9]*', build.name), 'Fresh short build/wfcqmN only')
    need(not build.exists() and not out.exists(), 'Never overwrite build or evidence')
    build.mkdir()
    out.mkdir()
    (out / 'recipe.py.txt').write_bytes(RECIPE.read_bytes())
    write(out / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd())})
    sys.dont_write_bytecode = True
    old = runpy.run_path(str(ROOT / 'reports/world-static-mesh-flight-scheduler-recipes/check-full-fixtures.py'), run_name='readonly_paths')
    prototype = HERE / 'run-20261105-full-003/controlled-scheduler-full.json'
    old88 = ROOT / 'reports/world-static-mesh-flight-controlled-tick-recipes/run-20261105-main-integration-001/controlled-full.json'
    old28 = ROOT / 'reports/world-static-mesh-flight-scheduler-recipes/run-20261105-main-integration-001/scheduler-full.json'
    watched = set(old['protected']()) | {RECIPE, MODULE, CHECKER, CONTROLS, prototype, old88, old28, ROOT / 'CMakeLists.txt'}
    for p in ['core/include/pikapika/world_static_mesh_flight_controlled_scheduler.hpp',
              'core/src/world_static_mesh_flight_controlled_scheduler.cpp',
              'tests/world_static_mesh_flight_controlled_scheduler_tests.cpp',
              'tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp',
              'cmake/PikapikaWorldFlightControlledTickBinding.cmake',
              'cmake/PikapikaWorldFlightSchedulerBinding.cmake']:
        watched.add(ROOT / p)
    # No configure/build command below targets any historical build directory.
    for name in ['wfcm1', 'wfcq3', 'wfcqt3']:
        watched.update(p for p in (ROOT / 'build' / name).rglob('*') if p.is_file() and (
            p.suffix in {'.exe', '.lib', '.map', '.vcxproj'} or p.name.endswith('command.1.tlog') or p.name.startswith('world-flight-')))
    watched = sorted(watched)
    identities = lambda: {p.relative_to(ROOT).as_posix(): stamp(p) for p in watched}
    before = identities()
    write(out / 'before.json', before)
    for path in [ROOT / 'CMakeLists.txt', MODULE]:
        (out / (path.name + '.txt')).write_bytes(path.read_bytes())
    commands = []

    def run(name, argv, timeout=600):
        started = time.monotonic()
        row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT)}
        try:
            done = subprocess.run(row['argv'], cwd=ROOT, capture_output=True, timeout=timeout)
            code, stdout, stderr = done.returncode, done.stdout, done.stderr
        except BaseException as error:
            code, stdout, stderr = None, getattr(error, 'stdout', None) or b'', (getattr(error, 'stderr', None) or b'') + str(error).encode()
        (out / (name + '.stdout.txt')).write_bytes(stdout)
        (out / (name + '.stderr.txt')).write_bytes(stderr)
        row.update(exitCode=code, seconds=time.monotonic()-started,
                   stdout=stamp(out / (name + '.stdout.txt')), stderr=stamp(out / (name + '.stderr.txt')))
        commands.append(row)
        write(out / (name + '.command.json'), row)
        print(json.dumps({k: row[k] for k in ['name', 'exitCode', 'seconds']}), flush=True)
        if code != 0:
            print(stdout.decode(errors='replace')[-12000:])
            print(stderr.decode(errors='replace')[-12000:])
        need(code == 0, 'Actual command failed: ' + name)
        return stdout

    result = {'schema': 1, 'status': 'FAIL', 'scope': __doc__}
    try:
        run('01-configure', ['cmake', '-S', ROOT, '-B', build, '-A', 'x64', '-DBUILD_TESTING=ON'])
        for stem in ['world-flight-binding', 'world-flight-scheduler-binding', 'world-flight-controlled-tick-binding']:
            for cfg in ['Release', 'Debug']:
                name = stem + '-' + cfg + '.json'
                need((build / name).read_bytes() == (ROOT / 'build/wfcm1' / name).read_bytes(), 'Old configured profile raw exact: ' + name)
        profiles = {}
        for cfg in ['Release', 'Debug']:
            p = build / ('world-flight-controlled-scheduler-binding-' + cfg + '.json')
            profile = json.loads(p.read_bytes())
            material = profile['identityMaterial']
            need(hashlib.sha256(json.dumps(material, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() == profile['buildId'], 'Independent configuration ID recomputation')
            need(material['helperSha256'] == stamp(MODULE)['sha256'] and len(material['sources']) == 2, 'Actual separate helper/two-source material')
            for source in material['sources']:
                need(source['sha256'] == stamp(ROOT / source['path'])['sha256'], 'Actual configured source hash')
            for key, stem in [('controlledTickBuildId', 'world-flight-controlled-tick-binding'), ('clockBuildId', 'world-flight-scheduler-binding')]:
                need(material[key] == json.loads((build / (stem + '-' + cfg + '.json')).read_bytes())['buildId'], 'Actual upstream configuration IDs')
            need(profile['profile'] == int(cfg == 'Release'), 'Actual supported Release / default Debug profile')
            need(profile['runtimeBuildId'] == (profile['buildId'] if cfg == 'Release' else ''), 'Runtime identity eligibility')
            profiles[cfg] = profile
            (out / p.name).write_bytes(p.read_bytes())
        listing = json.loads(run('02-inventory', ['ctest', '--test-dir', build, '-C', 'Release', '--show-only=json-v1']))
        old_names = set(re.findall(r'^\s*add_test\(\[=\[([^\]]+)\]=\]', (ROOT / 'build/wfcm1/CTestTestfile.cmake').read_text(), re.M))
        names = [x['name'] for x in listing['tests']]
        need(len(old_names) == 49 and len(names) == 50 and set(names) == old_names | {'world_static_mesh_flight_controlled_scheduler'}, 'Exactly old49 plus new scheduler')
        run('03-release-build', ['cmake', '--build', build, '--config', 'Release', '--parallel', '2'], 1200)
        run('04-directed', [build / 'Release' / (LIB + '_tests.exe'), '--run'])
        raw = run('05-full', [build / 'Release' / (LIB + '_fixtures.exe'), '--fixtures'])
        full = out / 'controlled-scheduler-full.json'
        full.write_bytes(raw)
        prior = prototype.read_bytes()
        previous_rows, rows = json.loads(prior)['fixtures'], json.loads(raw)['fixtures']
        previous_id = previous_rows[0]['report']['binding']['buildId']
        identity = profiles['Release']['buildId']
        need(len(rows) == len(previous_rows) == 84 and identity != previous_id, '84 actual same-ABI rows / distinct formal ID')
        for a, b in zip(previous_rows, rows, strict=True):
            need(a['report']['binding']['buildId'] == previous_id and b['report']['binding']['buildId'] == identity, 'Exact outer identity path')
        need(raw.count(identity.encode()) == prior.count(previous_id.encode()) == 84 and raw.replace(identity.encode(), previous_id.encode()) == prior, 'All raw bytes differ only at84 explicit outer IDs, preserving signed zero/order/types')
        write(out / 'prototype-comparison.json', {'status': 'PASS', 'identityFamilies': 1, 'path': 'fixtures[*].report.binding.buildId', 'leafCount': 84, 'previousId': previous_id, 'currentId': identity, 'allOtherRawBytesExact': True})
        reference = json.loads(run('06-reference', [sys.executable, '-B', '-X', 'utf8', CHECKER, full]))
        controls = json.loads(run('07-controls', [sys.executable, '-B', '-X', 'utf8', CONTROLS, full, '--output', out / 'controls'], 360))
        for name, executable, baseline in [('08-old88', TICK + '_tests', old88), ('09-old51', 'pikapika_world_static_mesh_flight_advance_fixtures', old['BASE']), ('10-old28', CLOCK + '_fixtures', old28)]:
            data = run(name, [build / 'Release' / (executable + '.exe'), '--fixtures'])
            (out / (name + '.json')).write_bytes(data)
            need(data == baseline.read_bytes(), 'Legacy full raw bytes exact: ' + name)
        run('11-all50-ctest', ['ctest', '--test-dir', build, '-C', 'Release', '--output-on-failure', '--timeout', '300'], 900)
        debug_tests = [LIB + '_tests', TICK + '_tests', CLOCK + '_tests', 'pikapika_world_static_mesh_flight_guard_tests', 'pikapika_world_static_mesh_flight_advance_tests']
        run('12-debug-build', ['cmake', '--build', build, '--config', 'Debug', '--target', *debug_tests, '--parallel', '2'], 1200)
        run('13-debug-five-refusals', ['ctest', '--test-dir', build, '-C', 'Debug', '-R', '^world_static_mesh_flight_(guard|advance|scheduler|controlled_tick|controlled_scheduler)$', '--output-on-failure', '--timeout', '300'], 360)
        provenance = []
        strict = {ROOT / 'core/src/world_static_mesh_flight_controlled_scheduler.cpp', ROOT / 'tests/world_static_mesh_flight_controlled_scheduler_tests.cpp', ROOT / 'tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp', ROOT / 'tests/world_static_mesh_flight_controlled_tick_fixtures.cpp', old['SHARED']}
        for path in sorted(build.rglob('CL.command.1.tlog')):
            if not any(x + '.dir' in path.parts for x in [LIB, LIB + '_tests', LIB + '_fixtures']):
                continue
            cfg = 'Debug' if 'Debug' in path.parts else 'Release'
            lines = path.read_bytes().decode('utf-16').splitlines()
            entries = []
            for i, line in enumerate(lines):
                if not line.startswith('^'):
                    continue
                source = Path(line[1:]).resolve()
                end = next((j for j in range(i+1, len(lines)) if lines[j].startswith('^')), len(lines))
                command = ' '.join(lines[i+1:end])
                if source in strict:
                    for token in ['/W4', '/WX', '/permissive-', '/fp:strict', '/GL-']:
                        need(re.search(r'(?:^|\s)' + re.escape(token) + r'(?=\s|$)', command, re.I), 'Actual strict compile option: ' + token)
                    need(not re.search(r'(?:^|\s)/(?:GL|WX-)(?=\s|$)', command, re.I), 'No strict override')
                if source.name == 'world_static_mesh_flight_controlled_scheduler.cpp':
                    need(profiles[cfg]['buildId'] in command and 'PIKAPIKA_CONTROLLED_SCHEDULER_PROFILE=' + str(profiles[cfg]['profile']) in command, 'Actual new binding macros')
                    for key in ['controlledTickBuildId', 'clockBuildId']:
                        need(profiles[cfg]['identityMaterial'][key] in command, 'Actual upstream macro')
                if cfg == 'Debug':
                    need('/MDd' in command and '_ITERATOR_DEBUG_LEVEL=0' not in command and 'NDEBUG' not in command, 'Actual Debug runtime / no Release-import workaround')
                entries.append({'source': source.relative_to(ROOT).as_posix(), 'command': command})
            copy = out / ('compile-' + str(len(provenance)) + '.tlog.txt')
            copy.write_bytes(path.read_bytes())
            provenance.append({'original': stamp(path), 'copy': stamp(copy), 'configuration': cfg, 'entries': entries})
        # Release: 1+10+10 TUs; Debug: 1+10, genuine Debug core/dependencies built by CMake.
        need(len(provenance) == 5 and sum(len(x['entries']) for x in provenance) == 32, 'Actual new compile provenance')
        for target in ['pikapika_core', TICK, CLOCK]:
            logs = list((build / (target + '.dir/Debug')).rglob('CL.command.1.tlog'))
            need(len(logs) == 1, 'Actual Debug dependency compilation log: ' + target)
            raw = logs[0].read_bytes()
            text = raw.decode('utf-16')
            need('/MDd' in text and '_ITERATOR_DEBUG_LEVEL=0' not in text and 'NDEBUG' not in text, 'Genuine Debug dependency ABI')
            (out / (target + '-debug.tlog.txt')).write_bytes(raw)
        result.update(status='FINITE_MAIN_CONTROLLED_SCHEDULER_INTEGRATION_PASS', profiles=profiles,
                      oldThreeProfilesRawIdentical=True, outerIdentityLeavesOnly=84, directedGroups=21,
                      fullReference=reference, fullControls=controls, legacyFullRawIdentical=[88, 51, 28],
                      ctestPassed=50, actualDebugCoreBuilt=True, debugRefusals=5,
                      actualCompileProvenance=provenance, actualGNUExecuted=False, actualSanitizerExecuted=False,
                      machineClockCommitProofComplete=False, SDKChanged=False)
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
    return 0 if result['status'] == 'FINITE_MAIN_CONTROLLED_SCHEDULER_INTEGRATION_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
