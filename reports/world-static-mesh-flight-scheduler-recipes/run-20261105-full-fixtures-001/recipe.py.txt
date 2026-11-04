"""Isolated full scheduler writer + fresh macro-free legacy51 writer regression.

Imports immutable wfa3 core/7 writer objects; never reconfigures existing builds.
The scheduler source configuration identity remains the original separate ID.
No independent new full scheduler checker result is synthesized by this recipe.
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
SHARED = ROOT / 'tests/world_static_mesh_flight_advance_fixtures.cpp'
SHARED_HEADER = ROOT / 'tests/world_static_mesh_flight_advance_fixture_support.hpp'
MAIN = ROOT / 'tests/world_static_mesh_flight_scheduler_fixtures.cpp'
HEADER = ROOT / 'tests/world_static_mesh_flight_scheduler_fixture_support.hpp'
SCHEDULER = ROOT / 'core/src/world_static_mesh_flight_scheduler.cpp'
SCHEDULER_HEADER = ROOT / 'core/include/pikapika/world_static_mesh_flight_scheduler.hpp'
LIB = ROOT / 'build/wfa3/Release/pikapika_core.lib'
OBJDIR = ROOT / 'build/wfa3/pikapika_world_static_mesh_flight_advance_fixtures.dir/Release'
OBJECTS = [OBJDIR / (name + '.obj') for name in [
    'world_static_mesh_flight_guard_fixtures', 'world_static_mesh_flight_preparation_fixtures',
    'sphere_triangle_mesh_free_flight_guard_fixtures', 'sphere_triangle_mesh_held_load_fixtures',
    'accelerated_pair_coverage_fixtures', 'accelerated_plane_box_coverage_fixtures', 'accelerated_sphere_box_coverage_fixtures']]
BASE = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-formal-target-001/transactions.json'
PROTOTYPE = ROOT / 'reports/world-static-mesh-flight-scheduler-recipes/run-20261105-prototype-002'
HELPER = ROOT / 'reports/world-static-mesh-flight-advance-recipes/check-configured-prototype.py'
CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-advance.py'
CONTROLS = ROOT / 'tests/world_static_mesh_flight_advance_reference_tests.py'
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
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')

def protected():
    result = {RECIPE, SHARED, SHARED_HEADER, MAIN, HEADER, SCHEDULER, SCHEDULER_HEADER,
              LIB, BASE, HELPER, CHECKER, CONTROLS, ROOT / 'CMakeLists.txt', ROOT / 'cmake/WorldFlightBinding.cmake', *OBJECTS}
    result.update(path for path in (ROOT / 'core').rglob('*') if path.is_file() and path.suffix in {'.h','.hpp','.cpp'})
    result.update(path for path in (ROOT / 'tests').glob('world_static_mesh_flight*') if path.is_file())
    result.update(path for path in (ROOT / 'assets').glob('pikapika-simulation*') if path.is_file())
    for name in ['native','wfa2','wfat1','wfa3','wfs1','wfs2']:
        directory = ROOT / 'build' / name
        result.update(path for path in directory.rglob('*') if path.is_file() and (
            path.name == 'pikapika_core.lib' or path.name == 'core.obj' or path.suffix in {'.exe','.map','.vcxproj'} or
            path.name.startswith('world-flight-binding-') or path.name.endswith('command.1.tlog')))
    return sorted(result)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='run-20261105-full-fixtures-001')
    parser.add_argument('--build', default='build/wfsf1')
    args = parser.parse_args()
    need(sys.platform == 'win32', 'MSVC Windows experiment only, no simulated GNU acceptance')
    need(re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}', args.name), 'Fresh report component')
    build = (ROOT / args.build).resolve(); output = RECIPE.parent / args.name
    need(build.parent == ROOT / 'build' and re.fullmatch(r'wfsf[1-9][0-9]*', build.name), 'Fresh short build/wfsfN only')
    need(not build.exists() and not output.exists(), 'Never overwrite old scratch or evidence')
    build.mkdir(); output.mkdir()
    (output / 'recipe.py.txt').write_bytes(RECIPE.read_bytes()); write(output / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd())})
    watched = protected()
    identities = lambda: {path.relative_to(ROOT).as_posix(): stamp(path) for path in watched}
    before = identities(); write(output / 'before.json', before)
    commands = []
    def run(name, argv, timeout=600):
        row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT), 'before': identities()}; start = time.monotonic()
        try:
            done = subprocess.run(row['argv'], cwd=ROOT, capture_output=True, timeout=timeout)
            code, stdout, stderr = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as error:
            code, stdout, stderr = None, error.stdout or b'', (error.stderr or b'') + str(error).encode()
        except BaseException as error:
            code, stdout, stderr = None, b'', str(error).encode()
        (output / (name + '.stdout.txt')).write_bytes(stdout); (output / (name + '.stderr.txt')).write_bytes(stderr)
        row.update(exitCode=code, seconds=time.monotonic()-start, after=identities())
        row.update(sourceStable=row['before'] == row['after'], stdout=stamp(output / (name + '.stdout.txt')), stderr=stamp(output / (name + '.stderr.txt')))
        commands.append(row); write(output / (name + '.command.json'), row)
        print(json.dumps({key: row[key] for key in ['name','exitCode','seconds','sourceStable']}), flush=True)
        if code != 0:
            print(stdout.decode('utf-8', errors='replace'), flush=True); print(stderr.decode('utf-8', errors='replace'), file=sys.stderr, flush=True)
        need(code == 0 and row['sourceStable'], 'Failed command or changed protected bytes: ' + name)
        return stdout
    result = {'schema': 1, 'status': 'FAIL', 'scope': 'Fresh MSVC full scheduler serialization and legacy51 exact-byte/independent regression. Actual external pump before/after only; intermediate candidate chain is not external observation. New independent full scheduler reference/GNU/sanitizer/main integration/machine proof not claimed.'}
    try:
        sys.dont_write_bytecode = True
        helper = runpy.run_path(str(HELPER), run_name='full_fixture_readonly_build_helpers')
        probe = build / 'probe'; probe.mkdir()
        (probe / 'CMakeLists.txt').write_text(helper['preamble']('SchedulerFullCompilerProbe'), encoding='utf-8', newline='\n')
        run('01-probe-configure', ['cmake','-S',probe,'-B',build / 'probe-build','-A','x64'])
        facts = json.loads((build / 'probe-build/compiler-facts.json').read_text())
        material = json.loads((PROTOTYPE / 'identity-material.json').read_text())
        profile = json.loads((PROTOTYPE / 'scheduler-profile.json').read_text())
        need(facts == material['compiler'] and material['compileOptions'] == OPTIONS, 'Actual compiler/full settings must match frozen scheduler identity')
        need(material['sources'] == [stamp(SCHEDULER_HEADER),stamp(SCHEDULER)] and material['importedLibrary'] == stamp(LIB), 'Scheduler source2/imported library identity unchanged')
        canonical = json.dumps(material, sort_keys=True, separators=(',', ':')).encode()
        identity = hashlib.sha256(canonical).hexdigest()
        need(identity == profile['buildId'] and identity != profile['oldSevenBuildId'], 'Separate original scheduler identity preserved')
        write(output / 'preserved-profile.json', {'sourceCount':2,'buildId':identity,'oldSevenBuildId':profile['oldSevenBuildId'],'material':material,'artifactAuditComplete':False})
        project = build / 'project'; project.mkdir(); quote = helper['cmake_path']; cquote = helper['cmake_quote']
        lines = [helper['preamble']('SchedulerFullFixtures'), 'add_library(old_core STATIC IMPORTED)',
                 'set_target_properties(old_core PROPERTIES IMPORTED_LOCATION ' + quote(LIB) + ')']
        for target, sources, library_only in [('scheduler_full',[MAIN,SCHEDULER,SHARED],True),('old51_fixtures',[SHARED],False)]:
            lines += ['add_executable(' + target + ' ' + ' '.join(quote(path) for path in sources) + ')',
                      'target_include_directories(' + target + ' PRIVATE ' + quote(ROOT / 'core/include') + ' ' + quote(ROOT / 'tests') + ')',
                      'target_link_libraries(' + target + ' PRIVATE old_core ' + ' '.join(quote(path) for path in OBJECTS) + ')',
                      'target_compile_options(' + target + ' PRIVATE ' + ' '.join(OPTIONS) + ')',
                      'target_link_options(' + target + ' PRIVATE /LTCG:OFF "/MAP:$<TARGET_FILE_DIR:' + target + '>/' + target + '.map")',
                      'set_property(TARGET ' + target + ' PROPERTY INTERPROCEDURAL_OPTIMIZATION FALSE)']
            if library_only:
                defs = 'PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY=1;PIKAPIKA_FLIGHT_SCHEDULER_PROFILE=1;PIKAPIKA_FLIGHT_SCHEDULER_BUILD_ID="' + identity + '"'
                lines.append('target_compile_definitions(' + target + ' PRIVATE ' + cquote(defs) + ')')
        driver = '\n'.join(lines) + '\n'
        (project / 'CMakeLists.txt').write_text(driver, encoding='utf-8', newline='\n'); (output / 'CMakeLists.txt').write_text(driver, encoding='utf-8', newline='\n')
        run('02-configure', ['cmake','-S',project,'-B',build / 'configured','-A','x64'])
        run('03-build', ['cmake','--build',build / 'configured','--config','Release','--parallel','2'])
        raw = run('04-old51', [build / 'configured/Release/old51_fixtures.exe','--fixtures'])
        (output / 'old51-transactions.json').write_bytes(raw)
        need(len(raw) == 2979456 and raw == BASE.read_bytes(), 'Macro-free legacy51 exact raw compatibility required')
        run('05-old51-independent', [sys.executable,'-B',CHECKER,output / 'old51-transactions.json'], 240)
        run('06-old51-controls', [sys.executable,'-B',CONTROLS,output / 'old51-transactions.json','--output',output / 'legacy-controls'], 240)
        raw = run('07-scheduler-full', [build / 'configured/Release/scheduler_full.exe','--fixtures'])
        (output / 'scheduler-full.json').write_bytes(raw)
        data = json.loads(raw.decode('utf-8'), parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON token: '+value)))
        need(data['schema'] == 1 and data['kind'] == 'world-static-mesh-flight-scheduler-fixtures' and len(raw)<=data['maximumDocumentBytes'], 'Actual complete bounded full scheduler document')
        frames=data['fixtures']; attempts=sum(row['report']['attempts'] for row in frames); committed=sum(row['report']['committedTicks'] for row in frames)
        compile_commands=[]
        for path in sorted((build / 'configured').rglob('CL.command.1.tlog')):
            if not any(part in path.parts for part in ['scheduler_full.dir','old51_fixtures.dir']):
                continue
            rawlog=path.read_bytes(); lines=rawlog.decode('utf-16').splitlines(); entries=[]
            for i,line in enumerate(lines):
                if not line.startswith('^'):
                    continue
                source=Path(line[1:]).resolve(); end=next((j for j in range(i+1,len(lines)) if lines[j].startswith('^')),len(lines)); command=' '.join(lines[i+1:end])
                need(source in {MAIN,SCHEDULER,SHARED}, 'No unexpected/recompiled dependency TU')
                for flag in OPTIONS:
                    need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',command,re.I), 'Actual strict/WX flag absent: '+flag)
                need(not re.search(r'(?:^|\s)/(?:GL|WX-)(?=\s|$)',command,re.I), 'Actual warning/LTO weakening')
                if 'scheduler_full.dir' in path.parts:
                    need('PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY=1' in command and identity in command,'Actual new target shared-main removal/identity')
                else:
                    need('PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY' not in command,'Legacy target must keep original main')
                entries.append({'source':source.relative_to(ROOT).as_posix(),'command':command})
            dest=output/('compile-'+str(len(compile_commands))+'.tlog.txt');dest.write_bytes(rawlog)
            compile_commands.append({'original':stamp(path),'copy':stamp(dest),'entries':entries})
        need(sorted(len(row['entries']) for row in compile_commands)==[1,3], 'Exactly four actual new TU compiles; imports not rebuilt')
        write(output / 'source-archive.json', [stamp(path) for path in [MAIN,HEADER,SHARED,SHARED_HEADER,SCHEDULER,SCHEDULER_HEADER,*OBJECTS,LIB]])
        for path in [MAIN,HEADER,SHARED,SHARED_HEADER]:
            (output / (path.name+'.txt')).write_bytes(path.read_bytes())
        result.update(status='FINITE_FULL_FIXTURE_NATIVE_PASS', schedulerBuildId=identity,oldSevenBuildId=profile['oldSevenBuildId'],scenarios=len({row['scenario'] for row in frames}),frames=len(frames),attempts=attempts,committedTicks=committed,
                      schedulerDocument=stamp(output/'scheduler-full.json'),legacy51=stamp(output/'old51-transactions.json'),legacy51ExactBytes=True,legacyIndependent=json.loads((output/'05-old51-independent.stdout.txt').read_text()),
                      legacyControls=json.loads((output/'06-old51-controls.stdout.txt').read_text()),actualCommands=compile_commands,newFullIndependentCheckerComplete=False)
    except BaseException as error:
        result['error']=type(error).__name__+': '+str(error)
    finally:
        after=identities();write(output/'after.json',after);result.update(sourceStable=before==after,protectedPaths=len(watched),commands=commands)
        if not result['sourceStable']:
            result['status']='FAIL'
        write(output/'result.json',result)
    print(json.dumps({key:result[key] for key in ['status','frames','attempts','committedTicks','sourceStable','error'] if key in result}),flush=True)
    return 0 if result['status']=='FINITE_FULL_FIXTURE_NATIVE_PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
