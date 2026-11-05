"""Copied real transcript comparison controls and actual Windows GNU refusal.

No GNU execution is fabricated. The second identity tuple is explicitly a copy
control, not an observation from an instrumented executable.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def load_module(name, path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='run-20261105-gnu-driver-controls-001')
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}', args.name):
        raise ValueError('Fresh report component')
    out = HERE / args.name
    if out.exists():
        raise ValueError('Never overwrite evidence')
    out.mkdir()
    (out / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    driver = load_module('packet_driver_controls', HERE / 'verify-gnu.py')
    helper = load_module('packet_driver_exact_tree', ROOT / 'reports/world-static-mesh-flight-guard-recipes/verify-gnu.py')
    fixture = HERE / 'run-20261105-full-003/controlled-scheduler-full.json'
    data = helper.load(fixture)
    binding = data['fixtures'][0]['report']['binding']
    ids = {family: binding[key] for family, key in [('packet', 'buildId'), ('controlled', 'controlledBuildId'), ('clock', 'schedulerBuildId'), ('advance', 'upstreamBuildId')]}
    copied_ids = {k: sha256(('explicit-copy-control-only-' + v).encode()).hexdigest() for k, v in ids.items()}
    # Replace only actual corresponding binding fields in a copy.
    copied = deepcopy(data)
    for row in copied['fixtures']:
        r = row['report']
        for family, key in [('packet', 'buildId'), ('controlled', 'controlledBuildId'), ('clock', 'schedulerBuildId'), ('advance', 'upstreamBuildId')]:
            r['binding'][key] = copied_ids[family]
        for tick in r['tickReports']:
            if tick is None:
                continue
            c = tick['report']
            c['binding']['buildId'] = copied_ids['controlled']
            c['binding']['upstreamBuildId'] = copied_ids['advance']
            if c['child'] is not None:
                c['child']['binding']['buildId'] = copied_ids['advance']
                if c['child']['guard'] is not None:
                    c['child']['guard']['binding']['buildId'] = copied_ids['advance']
    watched = {Path(__file__), HERE / 'verify-gnu.py', HERE / 'GNU_PLAN.md', fixture}
    stamps = lambda: {str(p): sha256(p.read_bytes()).hexdigest() for p in sorted(watched)}
    before = stamps()
    started = time.monotonic()
    result = {'status': 'FAIL', 'actualGNUExecuted': False, 'scope': __doc__}
    try:
        comparison = driver.compare_full(helper, data, copied, ids, copied_ids)
        negatives = []
        def reject(name, mutate):
            changed = deepcopy(copied)
            mutate(changed)
            try:
                driver.compare_full(helper, data, changed, ids, copied_ids)
            except (ValueError, KeyError, TypeError):
                negatives.append(name)
                return
            raise ValueError('Copied alteration accepted: ' + name)
        def setpath(path, value):
            def mutate(d):
                for key in path[:-1]:
                    d = d[key]
                d[path[-1]] = value
            return mutate
        p = ['fixtures', 0, 'report']
        for key in ['buildId', 'controlledBuildId', 'schedulerBuildId', 'upstreamBuildId']:
            reject('parent-' + key, setpath(p + ['binding', key], '0' * 64))
        reject('controlled-id', setpath(p + ['tickReports', 0, 'report', 'binding', 'buildId'], '0' * 64))
        reject('private-advance-id', setpath(p + ['tickReports', 0, 'report', 'child', 'binding', 'buildId'], '0' * 64))
        reject('owned-guard-id', setpath(p + ['tickReports', 0, 'report', 'child', 'guard', 'binding', 'buildId'], '0' * 64))
        reject('unused-optional', setpath(p + ['tickReports', 7], False))
        reject('metadata-integer-to-float', setpath(p + ['attempts'], float(copied['fixtures'][0]['report']['attempts'])))
        if type(copied['fixtures'][0]['input']['scene']['gravity'][0]) is not float or copied['fixtures'][0]['input']['scene']['gravity'][0].hex() != '-0x0.0p+0':
            raise ValueError('This actual comparison control requires observed negative zero')
        reject('source-signed-zero-bit', setpath(['fixtures', 0, 'input', 'scene', 'gravity', 0], 0.0))
        reject('whole-frame-order', lambda d: d['fixtures'].reverse())
        def reorder(d):
            b = d['fixtures'][0]['report']['binding']
            d['fixtures'][0]['report']['binding'] = dict(reversed(list(b.items())))
        reject('binding-key-order', reorder)
        reject('unrelated-extra-id-field', lambda d: d['fixtures'][0].update(extraIdentity=copied_ids['packet']))
        reject('missing-frame', lambda d: d['fixtures'].pop())
        for name, altered in [('aliased-family', dict(copied_ids, clock=copied_ids['packet'])), ('extra-family', dict(copied_ids, other='1' * 64)), ('stale-family', dict(copied_ids, packet=ids['packet']))]:
            try:
                driver.compare_full(helper, data, copied, ids, altered)
            except ValueError:
                negatives.append(name)
            else:
                raise ValueError('Bad identity tuple accepted: ' + name)
        refusal = None
        if sys.platform == 'win32':
            build_out = ROOT / 'build/public-checks' / ('packet-' + args.name)
            argv = [sys.executable, '-B', '-X', 'utf8', str(HERE / 'verify-gnu.py'), '--normal', str(ROOT / 'build/wfcqm2'),
                    '--output', str(build_out), '--sanbuild', str(ROOT / 'build' / ('packet-san-' + args.name)),
                    '--debugbuild', str(ROOT / 'build' / ('packet-debug-' + args.name))]
            done = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=120)
            (out / 'windows-refusal.stdout.txt').write_bytes(done.stdout)
            (out / 'windows-refusal.stderr.txt').write_bytes(done.stderr)
            refusal = json.loads((build_out / 'verification.json').read_bytes())
            if done.returncode == 0 or refusal['actualGNUExecuted'] is not False or refusal['status'] != 'FAIL' or 'Actual Linux GNU13 required' not in refusal.get('error', ''):
                raise ValueError('Actual Windows process must refuse GNU execution')
            (out / 'windows-refusal-verification.json').write_bytes((build_out / 'verification.json').read_bytes())
            result['actualWindowsRefusal'] = {'exitCode': done.returncode, 'argv': argv, 'error': refusal['error']}
        result.update(status='PASS', copyComparison=comparison, copiedNegativeControls=len(negatives), rejected=negatives,
                      actualFixture={'path': fixture.relative_to(ROOT).as_posix(), 'sha256': sha256(fixture.read_bytes()).hexdigest()})
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        result.update(seconds=time.monotonic()-started, sourceStable=before == stamps())
        if not result['sourceStable']:
            result['status'] = 'FAIL'
        (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8', newline='\n')
    print(json.dumps({k: result[k] for k in ['status', 'copiedNegativeControls', 'actualGNUExecuted', 'sourceStable', 'seconds', 'error'] if k in result}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
