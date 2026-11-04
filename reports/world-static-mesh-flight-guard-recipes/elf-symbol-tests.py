"""Synthetic ELF64 symbol-binding regression tests for the actual audit Elf class.

This tests parser selection/ambiguity policy, not machine binding or product math.
GLOBAL/WEAK conflicting extents are rejected by conservative audit policy; gABI
linker resolution itself gives GLOBAL precedence over WEAK.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
AUDITOR = ROOT / 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py'
GABI = 'https://gabi.xinuos.com/elf/05-symtab.html'
LOCAL, GLOBAL, WEAK = 0, 1, 2
TARGET = '_ZNK8pikapika4Vec33dotES0_'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(data):
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def symbol(name, binding, offset, size=8):
    return {'name': name, 'binding': binding, 'sectionIndex': 1, 'value': offset, 'size': size}


def synthetic_elf(symbols):
    """An ELF64/x86-64 ET_REL with conventional section and symbol tables.

    All locals precede nonlocals; sh_info identifies the first nonlocal entry.
    The initial symbol is all-zero STN_UNDEF. All test functions have owned code
    extents in one executable .text section. No actual instruction audit is run.
    """
    rows = sorted(enumerate(symbols), key=lambda item: item[1]['binding'] != LOCAL)
    ordered = [row for _, row in rows]
    text = bytes(range(256))
    names, offsets = bytearray(b'\0'), {}
    for row in ordered:
        require(0 <= row['binding'] <= 15, 'Unexpected synthetic binding')
        require(row['name'].isascii() and '\0' not in row['name'], 'Synthetic name encoding')
        require(0 <= row['value'] and 0 < row['size'] and row['value'] + row['size'] <= len(text),
                'Synthetic function extent')
        if row['name'] not in offsets:
            offsets[row['name']] = len(names)
            names.extend(row['name'].encode('ascii') + b'\0')
    table = bytearray(24)
    for row in ordered:
        table.extend(struct.pack('<IBBHQQ', offsets[row['name']], row['binding'] << 4 | 2,
                                 0, row['sectionIndex'], row['value'], row['size']))
    section_names = b'\0.text\0.strtab\0.symtab\0.shstrtab\0'
    raw = bytearray(64)

    def append(data, alignment):
        raw.extend(b'\0' * (-len(raw) % alignment))
        start = len(raw)
        raw.extend(data)
        return start

    text_offset = append(text, 16)
    string_offset = append(names, 1)
    symbol_offset = append(table, 8)
    section_name_offset = append(section_names, 1)
    raw.extend(b'\0' * (-len(raw) % 8))
    section_offset = len(raw)
    first_nonlocal = 1 + sum(row['binding'] == LOCAL for row in ordered)
    sections = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (1, 1, 6, 0, text_offset, len(text), 0, 0, 16, 0),
        (7, 3, 0, 0, string_offset, len(names), 0, 0, 1, 0),
        (15, 2, 0, 0, symbol_offset, len(table), 2, first_nonlocal, 8, 24),
        (23, 3, 0, 0, section_name_offset, len(section_names), 0, 0, 1, 0),
    ]
    for section in sections:
        raw.extend(struct.pack('<IIQQQQIIQQ', *section))
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    raw[:64] = struct.pack('<16sHHIQQQIHHHHHH', ident, 1, 62, 1, 0, 0, section_offset,
                           0, 64, 0, 0, 64, len(sections), 4)
    return bytes(raw), ordered


def cases(gnu_names):
    local_name = '_ZN12_GLOBAL__N_16helperEv'
    bridges = ['_ZN8pikapika6detail' + str(len(name)) + name + 'Ev' for name in
               ('world_predicate_binding_profile', 'world_predicate_binding_build_id')]
    caller = '_ZN8pikapika8dynamics6detail31solve_contacts_at_current_stateEv'
    names = [*gnu_names.values(), *bridges, caller]
    return [
        {'name': 'local-same-name-different-extents',
         'symbols': [symbol(local_name, LOCAL, 0), symbol(local_name, LOCAL, 16)], 'expected': {}},
        {'name': 'local-and-global-same-name',
         'symbols': [symbol(TARGET, LOCAL, 0), symbol(TARGET, GLOBAL, 16)],
         'expected': {TARGET: (1, 16, 8)}, 'required': TARGET},
        {'name': 'local-and-weak-same-name',
         'symbols': [symbol(TARGET, LOCAL, 0), symbol(TARGET, WEAK, 16)],
         'expected': {TARGET: (1, 16, 8)}, 'required': TARGET},
        {'name': 'global-conflicting-extents',
         'symbols': [symbol(TARGET, GLOBAL, 0), symbol(TARGET, GLOBAL, 16)], 'reject': True},
        {'name': 'global-weak-conflicting-extents',
         'symbols': [symbol(TARGET, GLOBAL, 0), symbol(TARGET, WEAK, 16)], 'reject': True},
        {'name': 'weak-global-conflicting-extents',
         'symbols': [symbol(TARGET, WEAK, 0), symbol(TARGET, GLOBAL, 16)], 'reject': True},
        {'name': 'global-weak-same-extent-different-binding',
         'symbols': [symbol(TARGET, GLOBAL, 16), symbol(TARGET, WEAK, 16)], 'reject': True},
        {'name': 'weak-global-same-extent-different-binding',
         'symbols': [symbol(TARGET, WEAK, 16), symbol(TARGET, GLOBAL, 16)], 'reject': True},
        {'name': 'weak-conflicting-extents',
         'symbols': [symbol(TARGET, WEAK, 0), symbol(TARGET, WEAK, 16)], 'reject': True},
        {'name': 'identical-global-repeat-preserves-old-policy',
         'symbols': [symbol(TARGET, GLOBAL, 16), symbol(TARGET, GLOBAL, 16)],
         'expected': {TARGET: (1, 16, 8)}, 'required': TARGET},
        {'name': 'identical-weak-repeat-preserves-old-policy',
         'symbols': [symbol(TARGET, WEAK, 16), symbol(TARGET, WEAK, 16)],
         'expected': {TARGET: (1, 16, 8)}, 'required': TARGET},
        {'name': 'missing-required-target', 'symbols': [], 'expected': {},
         'required': TARGET, 'missingRequired': True},
        {'name': 'local-only-cannot-satisfy-required-target', 'symbols': [symbol(TARGET, LOCAL, 16)],
         'expected': {}, 'required': TARGET, 'missingRequired': True},
        *[{'name': 'local-only-cannot-satisfy-' + label, 'symbols': [symbol(name, LOCAL, 16)],
           'expected': {}, 'required': name, 'missingRequired': True} for label, name in
          (('profile-bridge', bridges[0]), ('identity-bridge', bridges[1]), ('caller', caller))],
        {'name': 'other-binding-cannot-satisfy-required-target', 'symbols': [symbol(TARGET, 10, 16)],
         'expected': {}, 'required': TARGET, 'missingRequired': True},
        {'name': 'local-collision-diagnostics-bounded-to-eight',
         'symbols': [symbol(local_name, LOCAL, 16 * index) for index in range(12)], 'expected': {}},
        {'name': 'all-audited-names-have-global-definitions',
         'symbols': [symbol(name, GLOBAL, 16 * index) for index, name in enumerate(names)],
         'expected': {name: (1, 16 * index, 8) for index, name in enumerate(names)},
         'selection': {'leaves': list(gnu_names.values()), 'bridges': bridges, 'caller': caller}},
        {'name': 'local-lookalikes-do-not-enter-audit-selection',
         'symbols': [*[symbol(name, LOCAL, 128 + 16 * index) for index, name in enumerate(names)],
                     *[symbol(name, GLOBAL, 16 * index) for index, name in enumerate(names)],
                     symbol(caller + '.constprop.0', LOCAL, 240)],
         'expected': {name: (1, 16 * index, 8) for index, name in enumerate(names)},
         'selection': {'leaves': list(gnu_names.values()), 'bridges': bridges, 'caller': caller}},
    ]


def inspect_case(module, case, output):
    raw, symbols = synthetic_elf(case['symbols'])
    destination = output / (case['name'] + '.elf')
    destination.write_bytes(raw)
    record = {'name': case['name'], 'fixture': {'path': destination.name, **stamp(raw)},
              'symbolsInTableOrder': symbols, 'expectation': {key: value for key, value in case.items()
                                                            if key not in ('name', 'symbols')},
              'status': 'FAIL'}
    try:
        try:
            parsed = module.Elf(raw)
        except ValueError as error:
            record['parserError'] = str(error)
            require(case.get('reject') and 'duplicate function' in str(error),
                    'Unexpected parser rejection: ' + str(error))
            record['status'] = 'PASS'
            return record
        require(not case.get('reject'), 'Conflicting nonlocal definitions were accepted')
        record['selectedSymbols'] = parsed.symbols
        require(parsed.symbols == case['expected'], 'External symbol selection differs')
        expected_bindings = {row['name']: row['binding'] for row in symbols if row['binding'] in (GLOBAL, WEAK)}
        require(parsed.symbol_bindings == expected_bindings, 'Selected binding metadata differs')
        local_rows = [row for row in symbols if row['binding'] == LOCAL]
        collision_count = len(local_rows) - len({row['name'] for row in local_rows})
        diagnostics = parsed.symbol_diagnostics
        require(diagnostics['localFunctionEntries'] == len(local_rows) and
                diagnostics['localNameCollisions'] == collision_count and
                len(diagnostics['localCollisionExamples']) == min(collision_count, 8) and
                diagnostics['otherBindingFunctionEntries'] == sum(row['binding'] not in (LOCAL, GLOBAL, WEAK)
                                                                  for row in symbols),
                'Binding diagnostics counts or bounded examples differ')
        record['symbolBindings'] = parsed.symbol_bindings
        record['symbolDiagnostics'] = diagnostics
        if 'required' in case:
            if case.get('missingRequired'):
                try:
                    parsed.body(case['required'])
                except ValueError as error:
                    require('Missing ELF function' in str(error), 'Wrong missing-target rejection')
                    record['requiredTargetError'] = str(error)
                else:
                    raise ValueError('Missing/local-only required target was accepted')
            else:
                body, value, _ = parsed.body(case['required'])
                _, offset, size = case['expected'][case['required']]
                require(body == bytes(range(256))[offset:offset + size] and value == offset,
                        'Required target body extent differs')
                record['requiredBody'] = stamp(body)
        if 'selection' in case:
            expected = case['selection']
            require(all(name in parsed.symbols for name in expected['leaves']), 'Required GNU leaves missing')
            bridges = [name for name in parsed.symbols if 'world_predicate_binding_' in name]
            callers = [name for name in parsed.symbols if name.startswith('_ZN') and
                       'solve_contacts_at_current_state' in name and not name.endswith('.cold')]
            require(set(bridges) == set(expected['bridges']) and callers == [expected['caller']],
                    'Audit selector admitted a local-only lookalike or lost its global target')
            record['auditSelection'] = {'bridges': bridges, 'callers': callers, 'leaves': expected['leaves']}
        record['status'] = 'PASS'
    except Exception as error:
        record['error'] = type(error).__name__ + ': ' + str(error)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh repository evidence directory')
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT) and output != ROOT, 'Output must remain within the repository')
    output.mkdir(parents=True, exist_ok=False)
    before = AUDITOR.read_bytes()
    recipe = Path(__file__).read_bytes()
    (output / 'auditor-before.py.txt').write_bytes(before)
    (output / 'recipe.py.txt').write_bytes(recipe)
    write_json(output / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd()),
                                           'started': datetime.now(timezone.utc).isoformat()})
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('actual_binding_auditor_symbol_tests', AUDITOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = [inspect_case(module, case, output) for case in cases(module.GNU_NAMES)]
    source_stable = AUDITOR.read_bytes() == before and Path(__file__).read_bytes() == recipe
    result = {'schema': 1, 'kind': 'world-flight-elf-symbol-binding-synthetic-tests',
              'status': 'PASS' if source_stable and all(row['status'] == 'PASS' for row in records) else 'FAIL',
              'auditor': {'path': str(AUDITOR), **stamp(before)}, 'recipe': stamp(recipe),
              'sourceStable': source_stable, 'cases': records, 'groups': len(records),
              'passed': sum(row['status'] == 'PASS' for row in records),
              'reference': {'url': GABI, 'sections': ['5.1 Symbol Table Entry', '5.2 Symbol Binding'],
                            'read': '2026-11-05',
                            'policy': 'Ignore LOCAL for externally selected audit symbols; retain nonlocal ambiguity refusal. '
                                      'Identical nonlocal tuple deduplication is historical auditor policy, not linker validation.'},
              'scope': 'Synthetic ELF symbol selection only. No actual CI collision identification, instruction audit, numerical proof or linker execution.',
              'finished': datetime.now(timezone.utc).isoformat()}
    write_json(output / 'result.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'groups', 'passed', 'sourceStable')}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
