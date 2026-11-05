"""Actual Windows orchestration + copied comparison controls, never GNU proof."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
import importlib.util


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def need(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    need(out.is_relative_to(HERE) and out != HERE and not out.exists(), 'Fresh local report child')
    out.mkdir(parents=True)
    driver = module('controlled_gnu_driver_under_test', HERE / 'verify-gnu.py')
    helper = module('controlled_gnu_readonly_helpers', driver.GUARD_RECIPE)
    before = driver.sources()
    commands = helper.Commands(out, 300)
    original = helper.load(args.fixture.resolve())
    groups = []
    result = {'status': 'FAIL', 'actualGNUExecuted': False, 'actualSanitizerExecuted': False, 'scope': __doc__}
    try:
        # Real MSVC binary/independent Python subprocesses exercise orchestration;
        # these are explicitly NOT calls to a GNU build or sanitizer executable.
        actual = driver.controlled_tick_run(helper, commands, 'msvc-orchestration', args.binary.resolve(), args.binary.resolve(), out)
        need(actual['reference']['fixtures'] == 88 and actual['controls']['negativeControls'] == 144, 'Actual finite MSVC reference/control forwarding')
        groups.append('actual-msvc-orchestration-reference-controls')
        source_ids = {'controlled_tick': original['fixtures'][0]['report']['binding']['buildId'],
                      'advance': original['fixtures'][0]['report']['binding']['upstreamBuildId']}
        copied_ids = {'controlled_tick': 'a' * 64, 'advance': 'b' * 64}
        copied = deepcopy(original)
        for row in copied['fixtures']:
            r = row['report']
            r['binding']['buildId'] = copied_ids['controlled_tick']
            r['binding']['upstreamBuildId'] = copied_ids['advance']
            if r['child'] is not None:
                r['child']['binding']['buildId'] = copied_ids['advance']
                if r['child']['guard'] is not None:
                    r['child']['guard']['binding']['buildId'] = copied_ids['advance']
        comparison = driver.compare_full(helper, original, copied, source_ids, copied_ids)
        need(comparison['normalizedLeavesPerSide'] == [[88, 88, 64, 59]] * 2, 'Four exact paths and299 leaves')
        groups.append('copied-positive-only299-exact-identity-paths')
        rejected = []

        def refuse(name, mutation):
            changed = deepcopy(copied)
            mutation(changed)
            try:
                driver.compare_full(helper, original, changed, source_ids, copied_ids)
            except (ValueError, KeyError, TypeError):
                rejected.append(name)
            else:
                raise ValueError('Copied control was accepted: ' + name)

        refuse('extra-row', lambda d: d['fixtures'].append(deepcopy(d['fixtures'][0])))
        refuse('missing-row', lambda d: d['fixtures'].pop())
        refuse('whole-row-order', lambda d: d['fixtures'].reverse())
        refuse('bool-to-int', lambda d: d['fixtures'][0]['report'].__setitem__('committed', 1))
        refuse('unexpected-diagnostic', lambda d: d['fixtures'][0]['report'].__setitem__('message', 'changed'))
        refuse('wrong-controlled-id', lambda d: d['fixtures'][0]['report']['binding'].__setitem__('buildId', 'c' * 64))
        refuse('wrong-upstream-id', lambda d: d['fixtures'][0]['report']['binding'].__setitem__('upstreamBuildId', 'c' * 64))
        child_index = next(i for i, row in enumerate(copied['fixtures']) if row['report']['child'] is not None)
        guard_index = next(i for i, row in enumerate(copied['fixtures']) if row['report']['child'] is not None and row['report']['child']['guard'] is not None)
        refuse('absent-child', lambda d: d['fixtures'][child_index]['report'].__setitem__('child', None))
        refuse('wrong-child-id', lambda d: d['fixtures'][child_index]['report']['child']['binding'].__setitem__('buildId', 'c' * 64))
        refuse('absent-guard', lambda d: d['fixtures'][guard_index]['report']['child'].__setitem__('guard', None))
        refuse('wrong-guard-id', lambda d: d['fixtures'][guard_index]['report']['child']['guard']['binding'].__setitem__('buildId', 'c' * 64))
        refuse('unrelated-build-id', lambda d: d['fixtures'][0]['input'].__setitem__('buildId', 'a' * 64))
        refuse('sizeof-change', lambda d: d['controlledLayoutSizes'].__setitem__(next(iter(d['controlledLayoutSizes'])), 1))
        refuse('body-force-change', lambda d: d['fixtures'][0]['worldBefore']['bodies'][0]['force'].__setitem__(0, 99))
        # Locate an actual signed-zero numeric field, not a generated input.
        zero_path = None

        def find_zero(value, path=()):
            nonlocal zero_path
            if zero_path is not None:
                return
            import math
            if type(value) is float and value == 0 and math.copysign(1, value) < 0:
                zero_path = path
            elif type(value) is dict:
                for key, item in value.items():
                    find_zero(item, (*path, key))
            elif type(value) is list:
                for key, item in enumerate(value):
                    find_zero(item, (*path, key))

        find_zero(copied)
        need(zero_path is not None, 'Actual raw negative zero parsed losslessly')

        def flip_zero(data):
            parent = data
            for key in zero_path[:-1]:
                parent = parent[key]
            parent[zero_path[-1]] = 0.0

        refuse('negative-zero-bit', flip_zero)
        groups.append('fifteen-copied-full-tree-refusals')
        # Quoted -D and paths containing spaces must survive direct argv replay.
        probe_dir = out / 'cwd with spaces'
        probe_dir.mkdir()
        expected = ['-DPIKAPIKA_CONTROLLED_TICK_BUILD_ID="' + source_ids['controlled_tick'] + '"', 'a b', '-DPIKAPIKA_CONTROLLED_TICK_UPSTREAM_ID="' + source_ids['advance'] + '"']
        argv = [sys.executable, '-c', 'import os,sys,json;print(json.dumps({"cwd":os.getcwd(),"argv":sys.argv[1:]}))', *expected]
        probe = json.loads(driver.compile_at(commands, 'actual-direct-argv-probe', argv, probe_dir))
        need(probe['argv'] == expected and Path(probe['cwd']) == probe_dir, 'Actual cwd and quoted macro argv exactly retained')
        groups.append('actual-direct-subprocess-argv-cwd-retains-quoted-macros')
        targets = driver.targets(module('controlled_old_advance_targets', driver.ADVANCE_RECIPE))
        need(len(targets) == 3 and sum(map(len, targets.values())) == 19 and len(targets[driver.TEST]) == 10, 'Three actual intended targets/19 harness commands')
        groups.append('three-target-nineteen-harness-inventory')
        result.update(status='PASS', groups=groups, rejectedControls=rejected, comparison=comparison,
                      actualMSVCFiniteFixtures=88, actualMSVCDirectedGroups=94, actualMSVCReferenceControls=144,
                      negativeZeroPath=list(zero_path), actualArgvProbe=probe)
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        result.update(sourceStable=before == driver.sources(), commands=commands.items)
        if not result['sourceStable']:
            result['status'] = 'FAIL'
        (out / 'verification.json').write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k not in {'commands', 'comparison'}}, ensure_ascii=False))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
