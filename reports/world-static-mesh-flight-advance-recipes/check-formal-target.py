"""Fresh main-CMake MSVC transaction target; preserve all earlier builds."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-formal-target-001'
BUILD = ROOT / 'build/wfa3'
TARGET = 'pikapika_world_static_mesh_flight_advance_fixtures'
GUARD = 'pikapika_world_static_mesh_flight_guard_tests'
ADVANCE = 'pikapika_world_static_mesh_flight_advance_tests'
HELPER = Path(__file__).with_name('check-native-integration.py')
BASELINE = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-transaction-capture-001/transactions.json'

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def main():
    need(not OUT.exists() and not BUILD.exists(), 'Fresh report and short main build required')
    OUT.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('formal_target_existing_commands', HELPER)
    h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
    h.OUTPUT = OUT  # Fresh destination only; original helper/source/receipt unchanged.
    protected = {Path(__file__).resolve(), HELPER, BASELINE, ROOT / 'CMakeLists.txt',
                 ROOT / 'cmake/WorldFlightBinding.cmake', ROOT / 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py',
                 ROOT / 'scripts/verify-world-static-mesh-flight-advance.py', ROOT / 'tests/world_static_mesh_flight_advance_reference_tests.py',
                 Path(__file__).with_name('clock-reference.py')}
    for folder in ('core', 'tests'):
        protected.update(p for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in ('.cpp', '.hpp', '.h'))
    for directory in (ROOT / 'build/native', ROOT / 'build/wfa2'):
        protected.update(directory / p for p in ('Release/pikapika_core.lib', 'pikapika_core.dir/Release/core.obj', 'world-flight-binding-Release.json'))
        protected.update((directory / 'Release').glob('pikapika*probe.exe'))
        protected.update((directory / 'Release').glob('pikapika*world_static_mesh_flight*tests.exe'))
        protected.update((directory / 'Release').glob('world-flight-*.map'))
    protected.update(ROOT / p for p in ('build/wfat1/Release/pp_wfat.exe', 'build/wfat1/fixture.map',
                     'assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json'))
    protected = sorted(protected)
    before = h.snapshot(protected); h.write_json(OUT / 'before.json', before)
    shutil.copyfile(Path(__file__), OUT / 'recipe.py.txt'); shutil.copyfile(HELPER, OUT / 'command-helper.py.txt')
    commands = h.Commands(protected)
    result = {'schema': 1, 'status': 'FAIL', 'started': datetime.now(timezone.utc).isoformat(),
              'scope': 'Fresh main CMake three-target MSVC integration, finite9/18/51 and independent14/85, actual existing three-leaf/caller/core-command gate on the new executable. Whole clock/commit machine proof, GNU/sanitizer and public acceptance remain separate.',
              'completeClockCommitMachineProof': False, 'GNUAccepted': False, 'publicAccepted': False}
    try:
        commands.run('configure', ['cmake', '-S', ROOT, '-B', BUILD, '-G', 'Visual Studio 18 2026', '-A', 'x64'], 180)
        old_five = json.loads((ROOT / 'build/native/world-flight-binding-Release.json').read_text())['buildId']
        profile = h.checked_profile(BUILD / 'world-flight-binding-Release.json', old_five)
        previous = json.loads((ROOT / 'build/wfa2/world-flight-binding-Release.json').read_text())
        need(profile == previous, 'New target must not change seven-source compiler/profile identity')
        shutil.copyfile(BUILD / 'world-flight-binding-Release.json', OUT / 'configured-profile.json')
        commands.run('build-three-targets', ['cmake', '--build', BUILD, '--config', 'Release', '--target',
                     TARGET, ADVANCE, GUARD, '--parallel', '2'], 1200)
        commands.run('advance-directed-nine', [BUILD / 'Release' / (ADVANCE + '.exe'), '--run'], 180)
        raw_clock = commands.run('clock-eighteen', [BUILD / 'Release' / (ADVANCE + '.exe'), '--clock-fixtures'], 180)
        (OUT / 'clock.json').write_bytes(raw_clock)
        commands.run('independent-clock', [sys.executable, '-B', Path(__file__).with_name('clock-reference.py'), OUT / 'clock.json'], 180)
        raw = commands.run('transaction-fifty-one', [BUILD / 'Release' / (TARGET + '.exe'), '--fixtures'], 180)
        (OUT / 'transactions.json').write_bytes(raw)
        need(raw == BASELINE.read_bytes(), 'Whole actual transaction packet changed from standalone development capture')
        commands.run('independent-transactions', [sys.executable, '-B', ROOT / 'scripts/verify-world-static-mesh-flight-advance.py', OUT / 'transactions.json'], 180)
        commands.run('independent-negative-controls', [sys.executable, '-B', ROOT / 'tests/world_static_mesh_flight_advance_reference_tests.py',
                     OUT / 'transactions.json', '--output', OUT / 'reference-controls'], 180)
        commands.run('new-executable-leaf-and-command-audit', [sys.executable, '-B', ROOT / 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py',
                     '--profile', BUILD / 'world-flight-binding-Release.json', '--object', BUILD / 'pikapika_core.dir/Release/core.obj',
                     '--binary', BUILD / 'Release' / (TARGET + '.exe'), '--map', BUILD / 'Release/world-flight-advance-fixtures.map',
                     '--build-directory', BUILD, '--output', OUT / 'artifact-audit'], 180)
        audit = json.loads((OUT / 'artifact-audit/audit.json').read_text())
        need(audit['status'] == 'PASS' and len(audit['compilationProvenance']['sourceCommands']) == 4, 'Actual new executable existing gate')
        tlogs = list((BUILD / (TARGET + '.dir/Release')).rglob('CL.command.1.tlog'))
        need(len(tlogs) == 1, 'Unique actual new target compile tlog')
        tlog = tlogs[0].read_bytes(); (OUT / 'new-target-compiler.tlog.raw').write_bytes(tlog)
        text = tlog.decode('utf-16')
        source = str((ROOT / 'tests/world_static_mesh_flight_advance_fixtures.cpp').resolve()).casefold()
        lines = text.splitlines(); selected = []
        for i, line in enumerate(lines):
            if line.startswith('^') and line[1:].casefold() == source:
                end = next((j for j in range(i+1, len(lines)) if lines[j].startswith('^')), len(lines))
                selected.append(' '.join(lines[i+1:end]))
        need(len(selected) == 1, 'Actual unique main source command')
        for flag in ('/W4', '/WX', '/permissive-', '/fp:strict', '/GL-'):
            need(re.search(r'(?:^|\s)' + re.escape(flag) + r'(?=\s|$)', selected[0], re.I), 'Actual new main command flag ' + flag)
        result.update(status='PASS', buildId=profile['buildId'], directedGroups=9, clockCases=18, transactionCases=51,
                      transactionPacketSameRaw=True, transactionPacket=h.stamp(OUT / 'transactions.json'),
                      independentSelfTests=14, rejectedControls=85, newMainActualCommand=selected[0],
                      actualExistingLeafGraphs=3, actualCoreSourceCommands=4,
                      artifactAudit=h.stamp(OUT / 'artifact-audit/audit.json'), advanceScope=audit['advanceScope'])
    except Exception as error:
        result.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
    finally:
        after = h.snapshot(protected); h.write_json(OUT / 'after.json', after)
        result.update(protectedFiles=len(protected), protectedUnchanged=before == after, commands=commands.rows,
                      finished=datetime.now(timezone.utc).isoformat())
        if before != after:
            result.update(status='FAIL', error='Protected source/accepted artifact changed')
        h.write_json(OUT / 'result.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'transactionCases', 'protectedFiles', 'protectedUnchanged', 'error') if k in result}), flush=True)
    return 0 if result['status'] == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
