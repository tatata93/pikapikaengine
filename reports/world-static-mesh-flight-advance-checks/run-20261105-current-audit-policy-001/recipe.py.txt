"""Execute the UNAPPLIED auditor patch in an isolated synthetic policy sandbox.

No compiler, linker, instruction audit or clock query runs here. Source files
are actual byte copies; profile/command/project/link records are SYNTHETIC.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import ast
import importlib.util
import json
import re
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
RECIPE_DIR = Path(__file__).resolve().parent
AUDITOR_PATH = 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py'
SOURCE_SET = 'world-static-mesh-flight-advance-v1'
ADVANCE = 'core/src/world_static_mesh_flight_advance.cpp'
FIVE = ['core/src/core.cpp', 'core/include/pikapika/core.hpp', 'core/src/dynamics.cpp',
        'core/include/pikapika/world_static_mesh_flight_guard.hpp', 'core/src/world_static_mesh_flight_guard.cpp']
SEVEN = [*FIVE, 'core/include/pikapika/world_static_mesh_flight_advance.hpp', ADVANCE]
MSVC = ['/fp:strict']
MSVC_EXTRA = ['/GL-', '/W4', '/WX', '/permissive-']
GNU = ['-fno-fast-math', '-ffp-contract=off', '-frounding-math', '-fexcess-precision=standard',
       '-mfpmath=sse', '-msse2', '-fno-lto']
GNU_EXTRA = ['-Wall', '-Wextra', '-Wpedantic', '-Werror']
NAMESPACE = 'http://schemas.microsoft.com/developer/msbuild/2003'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def patched_source(original, patch):
    lines, before = patch.splitlines(keepends=True), original.splitlines(keepends=True)
    require(lines[:3] == ['diff --git a/' + AUDITOR_PATH + ' b/' + AUDITOR_PATH + '\n',
                         '--- a/' + AUDITOR_PATH + '\n', '+++ b/' + AUDITOR_PATH + '\n'],
            'Unexpected patch target')
    result, cursor, i = [], 0, 3
    while i < len(lines):
        match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', lines[i])
        require(match is not None, 'Patch hunk header')
        start, count, new_start, new_count = (int(match[1]), int(match[2] or 1),
                                             int(match[3]), int(match[4] or 1))
        require(start - 1 >= cursor, 'Overlapping patch hunks')
        result.extend(before[cursor:start - 1])
        require(len(result) == new_start - 1, 'Patch new line position')
        cursor, old_used, new_used = start - 1, 0, 0
        i += 1
        while i < len(lines) and not lines[i].startswith('@@ '):
            line = lines[i]
            require(line and line[0] in ' +-', 'Unexpected patch record')
            if line[0] in ' -':
                require(cursor < len(before) and before[cursor] == line[1:], 'Patch context differs')
                cursor += 1
                old_used += 1
            if line[0] in ' +':
                result.append(line[1:])
                new_used += 1
            i += 1
        require((old_used, new_used) == (count, new_count), 'Patch hunk counts differ')
    result.extend(before[cursor:])
    text = ''.join(result)
    ast.parse(text)
    return text


def profile(scratch, family, expanded):
    paths = SEVEN if expanded else FIVE
    rows = []
    for path in paths:
        flags = [] if path.endswith('.hpp') else list(MSVC if family == 'MSVC' else GNU)
        if path == ADVANCE:
            flags += MSVC_EXTRA if family == 'MSVC' else GNU_EXTRA
        rows.append({'path': path, 'sha256': stamp((scratch / path).read_bytes())['sha256'], 'flags': flags})
    result = {'schema': 1, 'profile': 1, 'configuration': 'Release', 'architecture': 'x64-sse2',
              'buildId': 'a' * 64, 'artifactAuditRequired': True,
              'scope': 'SYNTHETIC policy input. Not a compiler/configuration or machine-code attestation.',
              'compiler': {'id': family, 'version': '19.51.36247.0' if family == 'MSVC' else '13.3.0',
                           # This actual existing file satisfies the path-shape gate only;
                           # it is deliberately NOT claimed to be a C++ compiler.
                           'path': str(Path(sys.executable).resolve())},
              'sources': rows}
    if expanded:
        result['sourceSet'] = SOURCE_SET
    return result


def source_row(value, path):
    return next(row for row in value['sources'] if row['path'] == path)


class Suite:
    def __init__(self, module, output, scratch):
        self.module, self.output, self.scratch, self.rows = module, output, scratch, []

    def run(self, name, accept, action, error_contains=None):
        row = {'name': name, 'expected': 'ACCEPT' if accept else 'REJECT', 'status': 'FAIL',
               'evidenceOrigin': 'Synthetic parser/policy fixture; no actual compilation or artifact audit'}
        try:
            value = action()
        except Exception as error:
            row['observed'] = 'REJECT'
            row['error'] = type(error).__name__ + ': ' + str(error)
            if not accept and isinstance(error, ValueError) and (not error_contains or error_contains in str(error)):
                row['status'] = 'PASS'
        else:
            row['observed'] = 'ACCEPT'
            row['returned'] = value
            if accept:
                row['status'] = 'PASS'
        self.rows.append(row)
        write_json(self.output / 'cases' / (name + '.json'), row)

    def profile_case(self, name, value, accept, error=None):
        write_json(self.output / 'profiles' / (name + '.json'), value)

        def action():
            family, rows = self.module.check_profile(deepcopy(value))
            require(family == value['compiler']['id'] and len(rows) == len(value['sources']),
                    'Profile validation returned wrong source set')
            return {'family': family, 'sourceCount': len(rows), 'sources': rows}
        self.run(name, accept, action, error)

    def command_case(self, name, value, accept, mutation=None, error=None):
        directory = self.output / 'command-fixtures' / name
        build, evidence = directory / 'build', directory / 'captured-by-auditor'
        build.mkdir(parents=True)
        evidence.mkdir()
        obj = build / 'object-records/core.object.txt'
        obj.parent.mkdir()
        obj.write_text('Synthetic object PATH placeholder, not an object file.\n', encoding='ascii')
        binary = build / 'synthetic-target.exe.txt'
        binary.write_text('Synthetic binary PATH placeholder, not executable code.\n', encoding='ascii')
        expanded = value.get('sourceSet') == SOURCE_SET
        required = ['core/src/core.cpp', 'core/src/dynamics.cpp', 'core/src/world_static_mesh_flight_guard.cpp']
        if expanded:
            required.append(ADVANCE)
        records = {'family': value['compiler']['id'], 'commands': {}, 'projectStrict': {},
                   'linkFlags': ['/LTCG:OFF'] if expanded and value['compiler']['id'] == 'MSVC' else [],
                   'binaryName': binary.name}
        for path in required:
            flags = list(MSVC if records['family'] == 'MSVC' else GNU)
            if path == ADVANCE:
                flags += MSVC_EXTRA if records['family'] == 'MSVC' else GNU_EXTRA
            if path != 'core/src/dynamics.cpp':
                prefix = '/D' if records['family'] == 'MSVC' else '-D'
                flags.extend([prefix + 'PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1',
                              prefix + 'PIKAPIKA_WORLD_FLIGHT_BUILD_ID="' + value['buildId'] + '"'])
            records['commands'][path] = flags
            records['projectStrict'][path] = 'Strict'
        if mutation:
            mutation(records)
        write_json(directory / 'profile.synthetic.json', value)
        write_json(directory / 'records.synthetic.json', records)
        (directory / 'SYNTHETIC.txt').write_text(
            'All project/tlog/compile_commands/link/object/binary inputs here are SYNTHETIC.\n'
            'They test actual parser functions, not actual C++ command execution or machine binding.\n', encoding='ascii')
        if records['family'] == 'MSVC':
            document = ET.Element('{' + NAMESPACE + '}Project')
            group = ET.SubElement(document, '{' + NAMESPACE + '}ItemGroup')
            for path, model in records['projectStrict'].items():
                entry = ET.SubElement(group, '{' + NAMESPACE + '}ClCompile', Include=str((self.scratch / path).resolve()))
                ET.SubElement(entry, '{' + NAMESPACE + '}FloatingPointModel',
                              Condition="'$(Configuration)|$(Platform)'=='Release|x64'").text = model
            ET.ElementTree(document).write(build / 'pikapika_core.vcxproj', encoding='utf-8', xml_declaration=True)
            tlog = ''.join('^' + str((self.scratch / path).resolve()) + '\n' + ' '.join(flags) + '\n'
                           for path, flags in records['commands'].items())
            (obj.parent / 'CL.command.1.tlog').write_text(tlog, encoding='utf-16')
            link_dir = build / (binary.stem + '.dir') / 'Release'
            link_dir.mkdir(parents=True)
            (link_dir / 'link.command.1.tlog').write_text(' '.join(records['linkFlags']) +
                                                       ' /OUT:' + records['binaryName'] + '\n', encoding='utf-16')
        else:
            entries = []
            for path, flags in records['commands'].items():
                entries.append({'directory': str(build), 'file': str((self.scratch / path).resolve()),
                                'arguments': [value['compiler']['path'], *flags, '-c',
                                              str((self.scratch / path).resolve()), '-o', str(obj)]})
            if records.get('duplicateAdvance'):
                entries.append(deepcopy(next(row for row in entries if row['file'] == str((self.scratch / ADVANCE).resolve()))))
            if records.get('wrongCoreObject'):
                entries[0]['arguments'][-1] += '.wrong'
            if records.get('wrongCompiler'):
                entries[-1]['arguments'][0] = str(Path(__file__).resolve())
            write_json(build / 'compile_commands.json', entries)
            link_dir = build / 'CMakeFiles' / (binary.stem + '.dir')
            link_dir.mkdir(parents=True)
            (link_dir / 'link.txt').write_text('synthetic-linker ' + ' '.join(records['linkFlags']) +
                                             ' -o ' + records['binaryName'] + '\n', encoding='utf-8')

        def action():
            # Invoke the proposed actual parser, but on explicitly generated
            # metadata; intentionally do NOT invoke audit_msvc/audit_gnu/main.
            self.module.check_profile(deepcopy(value))
            result = self.module.command_provenance(value, obj, binary, build, None, evidence)
            require(len(result['sourceCommands']) == len(required), 'Wrong required actual-command count')
            return {'provenanceParserResultOnSyntheticRecords': result,
                    'actualCompilerInvoked': False, 'actualArtifactAudited': False}
        self.run(name, accept, action, error)


def mutate_copy(value, action):
    copied = deepcopy(value)
    action(copied)
    return copied


def exercise(suite):
    profiles = {(family, expanded): profile(suite.scratch, family, expanded)
                for family in ('MSVC', 'GNU') for expanded in (False, True)}
    for (family, expanded), value in profiles.items():
        suite.profile_case('profile-' + family.lower() + ('-7' if expanded else '-5'), value, True)
    seven, five = profiles['MSVC', True], profiles['MSVC', False]
    for label, change, message in (
        ('unknown-source-set', lambda p: p.update(sourceSet='world-flight-unknown'), 'Unknown sourceSet'),
        ('null-source-set', lambda p: p.update(sourceSet=None), 'Unknown sourceSet'),
        ('empty-source-set', lambda p: p.update(sourceSet=''), 'Unknown sourceSet'),
        ('untagged-seven', lambda p: p.pop('sourceSet'), 'source-set size'),
        ('missing-source', lambda p: p['sources'].pop(), 'source-set size'),
        ('duplicate-path', lambda p: p['sources'].__setitem__(-1, deepcopy(p['sources'][0])), 'Unexpected/duplicate source'),
        ('unknown-path', lambda p: p['sources'][-1].update(path='core/src/unrelated.cpp'), 'Unexpected/duplicate source'),
        ('path-traversal', lambda p: p['sources'][-1].update(path='core/src/../src/world_static_mesh_flight_advance.cpp'), 'Unexpected/duplicate source'),
        ('source-hash', lambda p: p['sources'][-1].update(sha256='0' * 64), 'source hash mismatch'),
        ('header-flags', lambda p: source_row(p, SEVEN[-2]).update(flags=['/fp:strict']), 'Header flags'),
    ):
        suite.profile_case('profile-' + label, mutate_copy(seven, change), False, message)
    suite.profile_case('profile-tagged-five', mutate_copy(five, lambda p: p.update(sourceSet=SOURCE_SET)),
                       False, 'source-set size')
    for family in ('MSVC', 'GNU'):
        value = profiles[family, True]
        strict = '/fp:strict' if family == 'MSVC' else '-ffp-contract=off'
        extras = MSVC_EXTRA if family == 'MSVC' else GNU_EXTRA
        suite.profile_case('profile-' + family.lower() + '-missing-strict',
                           mutate_copy(value, lambda p: source_row(p, ADVANCE)['flags'].remove(strict)),
                           False, 'strict' if family == 'GNU' else '/fp:strict')
        for flag in extras:
            label = re.sub('[^a-z0-9]', '', flag.lower())
            suite.profile_case('profile-' + family.lower() + '-missing-' + label,
                               mutate_copy(value, lambda p, f=flag: source_row(p, ADVANCE)['flags'].remove(f)),
                               False, 'warning/no-LTO flags')
        for expanded in (False, True):
            suite.command_case('command-' + family.lower() + ('-7' if expanded else '-5'),
                               profiles[family, expanded], True)
        mutations = [
            ('missing-advance', lambda r: r['commands'].pop(ADVANCE),
             'Missing actual compiler command' if family == 'MSVC' else 'Unique actual GNU source command'),
            ('wrong-profile', lambda r: r['commands'].__setitem__(ADVANCE,
                [f.replace('AUDITED_PROFILE=1', 'AUDITED_PROFILE=0') for f in r['commands'][ADVANCE]]),
             'profile/identity definitions' if family == 'MSVC' else 'profile definitions'),
            ('wrong-id', lambda r: r['commands'].__setitem__(ADVANCE,
                [f.replace('a' * 64, 'b' * 64) for f in r['commands'][ADVANCE]]),
             'profile/identity definitions' if family == 'MSVC' else 'profile definitions'),
            ('missing-strict', lambda r, f=strict: r['commands'][ADVANCE].remove(f),
             'exclusive strict FP' if family == 'MSVC' else 'strict flags'),
            ('enabling-lto', lambda r: r['commands'][ADVANCE].append('/GL' if family == 'MSVC' else '-flto'),
             'GL/LTO' if family == 'MSVC' else 'unsafe/LTO'),
            ('link-enabling-lto', lambda r: r['linkFlags'].append('/LTCG' if family == 'MSVC' else '-flto'),
             'link enables LTO' if family == 'MSVC' else 'link LTO'),
        ]
        for flag in extras:
            mutations.append(('missing-' + re.sub('[^a-z0-9]', '', flag.lower()),
                              lambda r, f=flag: r['commands'][ADVANCE].remove(f),
                              'missing flag' if family == 'MSVC' else 'warning flags'))
        for label, mutation, error in mutations:
            suite.command_case('command-' + family.lower() + '-' + label, value, False, mutation, error)
    suite.command_case('command-msvc-old-five-refuses-ltcg-off', five, False,
                       lambda r: r['linkFlags'].append('/LTCG:OFF'), 'link enables LTO')
    suite.command_case('command-msvc-project-not-strict', seven, False,
                       lambda r: r['projectStrict'].__setitem__(ADVANCE, 'Precise'), 'project FP mode')
    suite.command_case('command-msvc-project-missing-advance', seven, False,
                       lambda r: r['projectStrict'].pop(ADVANCE), 'Unique source project item')
    for label, key, error in (('duplicate-advance', 'duplicateAdvance', 'Unique actual GNU source command'),
                              ('wrong-core-output', 'wrongCoreObject', 'core object path'),
                              ('wrong-compiler', 'wrongCompiler', 'compiler mismatch')):
        suite.command_case('command-gnu-' + label, profiles['GNU', True], False,
                           lambda r, k=key: r.update({k: True}), error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    expected_parent = (ROOT / 'reports/world-static-mesh-flight-advance-checks').resolve()
    require(output.parent == expected_parent and output.name == 'run-20261105-current-audit-policy-001',
            'Use a fresh run-...audit-policy-001 directory within advance checks')
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    protected = sorted(set([AUDITOR_PATH, 'CMakeLists.txt', 'cmake/WorldFlightBinding.cmake',
                            *SEVEN, 'tests/world_static_mesh_flight_advance_tests.cpp',
                            'assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs',
                            *[p.relative_to(ROOT).as_posix() for p in RECIPE_DIR.glob('*.patch')],
                            (RECIPE_DIR / 'integration-notes.json').relative_to(ROOT).as_posix(),
                            *['reports/world-static-mesh-flight-advance-recipes/' + name for name in
                              ('integration.patch', 'audit-integration.patch', 'integration-notes.json', 'check-integration-audit-policy.py')]]))
    before = {path: stamp((ROOT / path).read_bytes()) for path in protected}
    recipe = Path(__file__).read_bytes()
    write_json(output / 'protected-before.json', before)
    write_json(output / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd()),
               'started': datetime.now(timezone.utc).isoformat(), 'recipe': stamp(recipe),
               'scope': 'Synthetic policy/parser tests only; no actual C++ compilation, machine binding or clock verification.'})
    (output / 'recipe.py.txt').write_bytes(recipe)
    scratch = output / 'scratch'
    result = {'schema': 1, 'kind': 'unapplied-advance-auditor-policy-tests', 'status': 'FAIL',
              'compilerCommandsExecuted': 0, 'artifactAuditsExecuted': 0, 'clockQueriesExecuted': 0,
              'scope': 'Actual proposed parser functions executed against explicitly synthetic profile/project/compiler/link metadata. '
                       'No production patch, CMake change, compiler execution or formal artifact/clock acceptance.'}
    try:
        notes = json.loads((RECIPE_DIR / 'integration-notes.json').read_text('utf-8'))
        raw = (ROOT / AUDITOR_PATH).read_bytes()
        require(stamp(raw) == {key: notes['auditProposal']['baseAuditor'][key] for key in ('bytes', 'sha256')},
                'Auditor base precondition differs from frozen proposal')
        patch = (RECIPE_DIR / 'audit-integration.patch').read_bytes()
        require(stamp(patch) == {key: notes['auditProposal'][key] for key in ('bytes', 'sha256')}, 'Patch hash changed')
        proposed = patched_source(raw.decode('utf-8').replace('\r\n', '\n'), patch.decode('utf-8'))
        require(stamp(proposed.encode('utf-8')) == notes['auditProposal']['proposedCanonicalAuditor'],
                'Patched source differs from proposed result')
        (output / 'base-auditor.py.txt').write_bytes(raw)
        base_text = raw.decode('utf-8').replace('\r\n', '\n')
        preserved = {}
        for name in ('xmm_register', 'DataflowFailure', 'Dataflow', 'audit_gnu'):
            def source_component(text):
                node = next(n for n in ast.parse(text).body
                            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
                return ast.get_source_segment(text, node)
            original_component, proposed_component = source_component(base_text), source_component(proposed)
            require(original_component == proposed_component, 'Current graph/diagnostic source changed: ' + name)
            preserved[name] = stamp(original_component.encode('utf-8'))
        result['unchangedCurrentSourceComponents'] = preserved
        auditor = scratch / 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py'
        auditor.parent.mkdir(parents=True)
        auditor.write_text(proposed, encoding='utf-8', newline='\n')
        for path in SEVEN:
            target = scratch / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / path).read_bytes())
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('isolated_proposed_advance_auditor', auditor)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        require(module.ROOT == scratch.resolve(), 'Isolated auditor ROOT must be scratch')
        suite = Suite(module, output, scratch)
        exercise(suite)
        result.update(cases=suite.rows, groups=len(suite.rows), passed=sum(r['status'] == 'PASS' for r in suite.rows),
                      acceptedPositiveControls=sum(r['status'] == 'PASS' and r['expected'] == 'ACCEPT' for r in suite.rows),
                      rejectedNegativeControls=sum(r['status'] == 'PASS' and r['expected'] == 'REJECT' for r in suite.rows),
                      patchedAuditor=stamp(proposed.encode()),
                      sourceOrigin='Actual seven source byte copies; all compiler/profile/link records are synthetic; Python executable is a deliberate placeholder file, not a claimed C++ compiler.')
        require(all(row['status'] == 'PASS' for row in suite.rows), 'One or more policy controls failed')
        result['status'] = 'PASS'
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = {path: stamp((ROOT / path).read_bytes()) for path in protected}
        write_json(output / 'protected-after.json', after)
        result['protectedStable'] = before == after
        result['recipeStable'] = Path(__file__).read_bytes() == recipe
        result['elapsedSeconds'] = time.perf_counter() - started
        if not result['protectedStable'] or not result['recipeStable']:
            result['status'] = 'FAIL'
            result['stabilityError'] = 'Protected production/proposal bytes or recipe changed'
        write_json(output / 'result.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'groups', 'passed', 'acceptedPositiveControls',
          'rejectedNegativeControls', 'protectedStable', 'recipeStable', 'error') if key in result}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
