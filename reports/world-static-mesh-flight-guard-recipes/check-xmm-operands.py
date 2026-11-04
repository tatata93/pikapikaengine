"""Finite operand/dataflow regression against the real imported audit module.

Instruction records and their placeholder bytes are SYNTHETIC, not assembled or
decoded GNU/MSVC code. This does not establish actual artifact machine binding.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
AUDITOR = ROOT / 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def records(lines):
    # Dataflow does not decode machine bytes. Deliberately obvious one-byte
    # placeholders prevent these fixtures being mistaken for artifact evidence.
    return [(0x1000 + i, b'\x90', op, operands) for i, (op, operands) in enumerate(lines)]


def packed(family, kind):
    a = 'rsi' if family == 'GNU' and kind == 'subtract' else ('rdi' if family == 'GNU' else 'rcx')
    b = 'rsp+8' if family == 'GNU' else ('r8' if kind == 'subtract' else 'rdx')
    bz = 'rsp+24' if family == 'GNU' else b + '+16'
    if kind == 'subtract':
        output = 'rdi' if family == 'GNU' else 'rdx'
        return records([
            ('movupd', 'xmm0,XMMWORD PTR [' + a + ']'),
            ('subpd', 'xmm0,XMMWORD PTR [' + b + ']'),
            ('movups', 'XMMWORD PTR [' + output + '],xmm0'),
            ('movsd', 'xmm0,QWORD PTR [' + a + '+16]'),
            ('subsd', 'xmm0,QWORD PTR [' + bz + ']'),
            ('movsd', 'QWORD PTR [' + output + '+16],xmm0'), ('ret', '')])
    lines = [('movupd', 'xmm0,XMMWORD PTR [' + a + ']'),
             ('mulpd', 'xmm0,' + ('xmm0' if kind == 'length' else 'XMMWORD PTR [' + b + ']')),
             ('movapd', 'xmm1,xmm0'), ('unpckhpd', 'xmm1,xmm1'), ('addsd', 'xmm0,xmm1'),
             ('movsd', 'xmm1,QWORD PTR [' + a + '+16]'),
             ('mulsd', 'xmm1,' + ('xmm1' if kind == 'length' else 'QWORD PTR [' + bz + ']')),
             ('addsd', 'xmm0,xmm1')]
    if kind == 'length':
        lines.append(('sqrtsd', 'xmm0,xmm0'))
    return records([*lines, ('ret', '')])


def scalar(family, kind):
    a = 'rsi' if family == 'GNU' and kind == 'subtract' else ('rdi' if family == 'GNU' else 'rcx')
    b = 'rsp+8' if family == 'GNU' else ('r8' if kind == 'subtract' else 'rdx')

    def memory(pointer, offset):
        if pointer == 'rsp+8':
            pointer, offset = 'rsp', offset + 8
        return 'QWORD PTR [' + pointer + ('+' + str(offset) if offset else '') + ']'

    lines = []
    if kind == 'subtract':
        output = 'rdi' if family == 'GNU' else 'rdx'
        for offset in (0, 8, 16):
            lines.extend([('movsd', 'xmm0,' + memory(a, offset)),
                          ('subsd', 'xmm0,' + memory(b, offset)),
                          ('movsd', memory(output, offset) + ',xmm0')])
    else:
        for i, offset in enumerate((0, 8, 16)):
            reg = 'xmm' + str(i)
            lines.extend([('movsd', reg + ',' + memory(a, offset)),
                          ('mulsd', reg + ',' + (reg if kind == 'length' else memory(b, offset)))])
        lines.extend([('addsd', 'xmm0,xmm1'), ('addsd', 'xmm0,xmm2')])
        if kind == 'length':
            lines.append(('sqrtsd', 'xmm0,xmm0'))
    return records([*lines, ('ret', '')])


class Suite:
    def __init__(self, module, output):
        self.module, self.output, self.results = module, output, []

    def case(self, name, action, accept=True, contains=None, fixture=None):
        row = {'name': name, 'status': 'FAIL', 'expected': 'ACCEPT' if accept else 'REJECT',
               'scope': 'Synthetic operand/dataflow fixture only; no assembled/disassembled artifact proof'}
        if fixture is not None:
            row['fixture'] = fixture
        try:
            result = action()
        except Exception as error:
            row.update(observed='REJECT', error=type(error).__name__ + ': ' + str(error))
            if not accept and isinstance(error, ValueError) and (contains is None or contains in str(error)):
                row['status'] = 'PASS'
        else:
            row.update(observed='ACCEPT', returned=result)
            if accept:
                row['status'] = 'PASS'
        self.results.append(row)
        write_json(self.output / 'cases' / (name + '.json'), row)

    def graph(self, name, family, kind, items, accept=True, contains=None):
        fixture = {'family': family, 'kind': kind, 'instructionBytesArePlaceholders': True,
                   'instructions': [{'address': address, 'placeholderBytes': code.hex(), 'opcode': op, 'operands': operands}
                                    for address, code, op, operands in items]}
        self.case(name, lambda: self.module.Dataflow(family, kind, [self.module.GNU_NAMES['dot'],
                                                                  self.module.MSVC_NAMES['dot']]).execute(items),
                  accept, contains, fixture)


def changed(items, index, op=None, operands=None):
    result = deepcopy(items)
    address, code, old_op, old_operands = result[index]
    result[index] = address, code, old_op if op is None else op, old_operands if operands is None else operands
    return result


def exercise(suite):
    module = suite.module
    for i in range(16):
        for suffix, operand in (('lower', 'xmm' + str(i)), ('upper-space', ' XMM' + str(i) + ' ')):
            suite.case('register-' + str(i) + '-' + suffix,
                       lambda operand=operand: require(module.xmm_register(operand), 'Valid register not recognized'),
                       fixture={'operand': operand, 'expectedRegister': True})
    for index, operand in enumerate(('xmmword ptr [rsi]', 'XMMWORD PTR [rsp+8]', 'qword ptr [rdi]',
                                     'xmm', 'xmm16', 'xmm-1', 'xmm0junk', 'xmm00', 'xmmword')):
        suite.case('not-register-' + str(index),
                   lambda operand=operand: require(not module.xmm_register(operand), 'Non-register accepted as register'),
                   fixture={'operand': operand, 'expectedRegister': False})
    for family in ('GNU', 'MSVC'):
        for kind in ('subtract', 'dot', 'length'):
            for style, factory in (('packed', packed), ('scalar', scalar)):
                suite.graph(family.lower() + '-' + kind + '-' + style, family, kind, factory(family, kind))
    suite.graph('msvc-length-via-audited-dot', 'MSVC', 'length', records([
        ('mov', 'rdx,rcx'), ('call', '2000 <' + module.MSVC_NAMES['dot'] + '>'),
        ('sqrtsd', 'xmm0,xmm0'), ('ret', '')]))

    def vector_memory():
        flow = module.Dataflow('GNU', 'subtract', [])
        require(flow.vector('xmmword ptr [rsi]', packed=True) == [('a', 0), ('a', 1)], 'Packed memory lanes differ')
        require(flow.vector('XMMWORD PTR [rsi+8]', packed=True) == [('a', 1), ('a', 2)], 'Offset packed memory lanes differ')
        return {'memoryLanes': 'actual input expressions, not register lookup'}
    suite.case('memory-xmmword-is-not-a-register', vector_memory)

    def scalar_move_lanes():
        flow = module.Dataflow('GNU', 'subtract', [])
        # Retaining an existing destination high lane for legacy register movsd
        # and zeroing it for a scalar memory load are distinct SSE semantics.
        # Stop intentionally before full function validation and inspect state.
        try:
            flow.execute(records([('movupd', 'xmm0,XMMWORD PTR [rsi]'),
                                  ('movupd', 'xmm1,XMMWORD PTR [rsi+8]'), ('movsd', 'xmm0,xmm1')]))
        except ValueError as error:
            require('subtractions not proven' in str(error), 'Unexpected partial-graph failure')
        require(flow.xmm['xmm0'] == [('a', 1), ('a', 1)], 'Register movsd high-lane preservation differs')
        try:
            flow.execute(records([('movsd', 'xmm0,QWORD PTR [rsi]')]))
        except ValueError as error:
            require('subtractions not proven' in str(error), 'Unexpected scalar memory partial-graph failure')
        require(flow.xmm['xmm0'] == [('a', 0), module.ZERO], 'Scalar memory load must zero high lane')
        return {'registerHighLanePreserved': True, 'memoryHighLaneZero': True}
    suite.case('scalar-register-versus-memory-high-lane', scalar_move_lanes)

    base = packed('GNU', 'subtract')
    suite.graph('reject-unknown-pointer', 'GNU', 'subtract', changed(base, 0, operands='xmm0,XMMWORD PTR [r10]'),
                False, 'Unknown pointer')
    suite.graph('reject-wrong-input-pointer', 'GNU', 'subtract', changed(base, 0, operands='xmm0,XMMWORD PTR [rdi]'),
                False, 'Uninitialized/non-input memory')
    suite.graph('reject-uninitialized-register', 'GNU', 'subtract', changed(base, 0, operands='xmm0,xmm7'),
                False, 'Uninitialized XMM register: xmm7')
    suite.graph('reject-uninitialized-lane', 'GNU', 'subtract', changed(base, 0, operands='xmm0,XMMWORD PTR [rsi+16]'),
                False, 'Uninitialized/non-input memory')
    suite.graph('reject-unknown-opcode', 'GNU', 'subtract', changed(base, 0, op='pshufd'),
                False, 'Unsupported instruction')
    suite.graph('reject-reversed-subtraction', 'GNU', 'subtract', changed(base, 1, operands='xmm0,XMMWORD PTR [rsi]'),
                False, 'subtractions not proven')
    suite.graph('reject-wrong-output-pointer', 'GNU', 'subtract', changed(base, 2, operands='XMMWORD PTR [rsi],xmm0'),
                False, 'subtractions not proven')
    base = scalar('GNU', 'dot')
    wrong = changed(base, 6, operands='xmm1,xmm2')
    wrong = changed(wrong, 7, operands='xmm0,xmm1')
    suite.graph('reject-reassociated-dot', 'GNU', 'dot', wrong, False, 'Wrong product/add association')
    suite.graph('reject-dot-product-omission', 'GNU', 'dot', changed(base, 5, op='addsd'),
                False, 'Wrong product/add association')
    base = packed('GNU', 'length')
    suite.graph('reject-approximate-root', 'GNU', 'length', changed(base, 8, op='rsqrtsd'),
                False, 'Forbidden')
    suite.graph('reject-fused-op', 'GNU', 'length', changed(base, 1, op='vfmadd132pd'),
                False, 'Forbidden')
    suite.graph('reject-x87-root', 'GNU', 'length', changed(base, 8, op='fsqrt'),
                False, 'Forbidden')
    suite.graph('reject-missing-root', 'GNU', 'length', changed(base, 8, op='movsd'),
                False, 'Wrong product/add association')
    suite.graph('reject-libm-call', 'GNU', 'length', changed(base, 8, op='call', operands='2000 <sqrt@plt>'),
                False, 'unknown/non-dot target')

    for count in (1, 128, 131):
        def diagnostic(count=count):
            items = [(0x2000 + i, bytes([i % 256]), 'synthetic-op-' + str(i), 'synthetic-operand-' + str(i))
                     for i in range(count)]
            tables = {'object': {'localNameCollisions': 2}, 'linked': {'localNameCollisions': 5}}
            error = module.DataflowFailure(ValueError('synthetic original failure'), 'subtract', 'synthetic-symbol', items, tables)
            require(isinstance(error, ValueError) and str(error) == 'synthetic original failure', 'Failure base class/message differs')
            context = json.loads(json.dumps(error.context, allow_nan=False))
            require(context['instructionCount'] == count and context['instructionLimit'] == 128 and
                    context['truncated'] is (count > 128) and len(context['instructions']) == min(count, 128),
                    'Diagnostic count/cap/truncation differs')
            require(context['symbolTables'] == tables and context['family'] == 'GNU' and
                    context['kind'] == 'subtract' and context['symbol'] == 'synthetic-symbol', 'Diagnostic identity differs')
            for i, item in enumerate(context['instructions']):
                require(item == {'address': items[i][0], 'codeHex': items[i][1].hex(),
                                 'mnemonic': items[i][2], 'operands': items[i][3]}, 'Diagnostic instruction order/content differs')
            return {'count': count, 'retained': len(context['instructions']), 'JSONRoundTrip': True,
                    'note': 'Direct constructor unit test on synthetic records; does not satisfy the actual object/link byte-identity gate.'}
        suite.case('diagnostic-json-cap-' + str(count), diagnostic)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    allowed_roots = [(ROOT / 'reports/world-static-mesh-flight-guard-public-checks').resolve(),
                     (ROOT / 'build').resolve()]
    require(any(output != base and output.is_relative_to(base) for base in allowed_roots),
            'Output must be a fresh directory inside public checks or build')
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    before, recipe = AUDITOR.read_bytes(), Path(__file__).read_bytes()
    (output / 'auditor-before.py.txt').write_bytes(before)
    (output / 'recipe.py.txt').write_bytes(recipe)
    write_json(output / 'invocation.json', {'argv': sys.argv, 'cwd': str(Path.cwd()),
               'started': datetime.now(timezone.utc).isoformat(), 'auditorBefore': stamp(before), 'recipe': stamp(recipe)})
    result = {'schema': 1, 'kind': 'synthetic-xmm-operand-regression', 'status': 'FAIL',
              'scope': 'Synthetic operand strings and placeholder instruction bytes passed to actual imported auditor functions. '
                       'No actual GNU/MSVC assembly, binary/ELF machine graph, product math or formal clock acceptance.',
              'compilerInvocations': 0, 'actualArtifactAudits': 0}
    try:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('actual_auditor_xmm_regression', AUDITOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suite = Suite(module, output)
        exercise(suite)
        old_commit = '9306e4ca4cd4dc95975a86b5b3248ec7eccbfaac'
        # The original local before/after run retained the exact Git blob here.
        # Read and bind that committed fixture, so CI needs no old Git history.
        old_fixture = ROOT / 'reports/world-static-mesh-flight-guard-public-checks/run-20261105-xmm-operands-001/scratch/old-auditor.py'
        old_raw = old_fixture.read_bytes()
        require(stamp(old_raw) == {'bytes': 49724, 'sha256':
                'aa4787419dea4dd085a9d9fa1e2c3376e142111cca9d18c703c7f1068228b1c9'},
                'Historical auditor fixture identity mismatch')
        write_json(output / 'old-auditor-input.json', {'path': old_fixture.relative_to(ROOT).as_posix(),
                   'commit': old_commit, **stamp(old_raw),
                   'scope': 'Pinned committed copy from original Git-blob observation; no history lookup or network access.'})
        old_path = output / 'scratch/old-auditor.py'
        old_path.parent.mkdir()
        old_path.write_bytes(old_raw)
        old_spec = importlib.util.spec_from_file_location('historical_9306_auditor_xmm_regression', old_path)
        old_module = importlib.util.module_from_spec(old_spec)
        old_spec.loader.exec_module(old_module)
        before_after_fixture = packed('GNU', 'subtract')
        suite.case('historical-9306-rejects-packed-xmmword-memory',
                   lambda: old_module.Dataflow('GNU', 'subtract', []).execute(before_after_fixture),
                   False, 'Uninitialized XMM register: xmmword ptr [rsi]',
                   {'origin': 'Same synthetic GNU packed subtract spelling as current positive; no actual GNU graph proof',
                    'commit': old_commit, 'auditor': stamp(old_raw)})
        result['historicalAuditor'] = {'commit': old_commit, **stamp(old_raw),
                                      'sameSyntheticFixtureOldRejectCurrentAccept': all(
                                          row['status'] == 'PASS' for row in suite.results if row['name'] in
                                          ('gnu-subtract-packed', 'historical-9306-rejects-packed-xmmword-memory'))}
        result.update(groups=len(suite.results), passed=sum(row['status'] == 'PASS' for row in suite.results),
                      acceptedPositiveControls=sum(row['status'] == 'PASS' and row['expected'] == 'ACCEPT' for row in suite.results),
                      rejectedNegativeControls=sum(row['status'] == 'PASS' and row['expected'] == 'REJECT' for row in suite.results),
                      cases=suite.results)
        require(all(row['status'] == 'PASS' for row in suite.results), 'One or more operand regressions failed')
        result['status'] = 'PASS'
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        result.update(auditorAfter=stamp(AUDITOR.read_bytes()), recipeAfter=stamp(Path(__file__).read_bytes()),
                      sourceStable=AUDITOR.read_bytes() == before, recipeStable=Path(__file__).read_bytes() == recipe,
                      elapsedSeconds=time.perf_counter() - started)
        if not result['sourceStable'] or not result['recipeStable']:
            result['status'] = 'FAIL'
            result['stabilityError'] = 'Actual auditor or recipe changed during execution'
        write_json(output / 'result.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'groups', 'passed', 'acceptedPositiveControls',
                      'rejectedNegativeControls', 'sourceStable', 'recipeStable', 'error') if key in result}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
