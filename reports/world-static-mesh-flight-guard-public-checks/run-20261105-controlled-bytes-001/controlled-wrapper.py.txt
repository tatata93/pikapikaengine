"""Read selected controlled-tick publication bytes through the unchanged HTTP checker.

Source distribution only; no controlled-tick GNU or browser numerical API claim.
"""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCHEDULER = ROOT / "reports/world-static-mesh-flight-scheduler-publication/public-bytes.py"
GUARD = ROOT / 'reports/world-static-mesh-flight-guard-recipes/public-bytes.py'
ADVANCE = ROOT / 'reports/world-static-mesh-flight-advance-recipes/public-bytes.py'
EXTRA = ('core/include/pikapika/world_static_mesh_flight_controlled_tick.hpp', 'core/src/world_static_mesh_flight_controlled_tick.cpp', 'tests/world_static_mesh_flight_controlled_tick_tests.cpp', 'tests/world_static_mesh_flight_controlled_tick_fixtures.cpp', 'tests/world_static_mesh_flight_controlled_tick_fixture_support.hpp', 'scripts/verify-world-static-mesh-flight-controlled-tick.py', 'tests/world_static_mesh_flight_controlled_tick_reference_tests.py', 'docs/WORLD_STATIC_MESH_FLIGHT_CONTROLLED_TICK.md', 'docs/learn/diagrams/world-static-mesh-flight-controlled-tick.svg', 'reports/world-static-mesh-flight-controlled-tick-local-verification.json', 'reports/world-static-mesh-flight-controlled-tick-recipes/README.md')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def archive_attribute_response(out):
    # A captured HTTP body must never become active Git attributes. In
    # particular, a 404 HTML response has no Git-attributes syntax at all.
    source = out / 'http/.gitattributes'
    target = out / 'http/.gitattributes.response.bin'
    if not source.exists():
        return
    if target.exists():
        raise ValueError('Refuse overwriting captured attribute response')
    raw = source.read_bytes()
    source.rename(target)
    original = (out / 'receipt.json').read_bytes()
    (out / 'receipt-before-path-relocation.json').write_bytes(original)
    receipt = json.loads(original)
    changed = 0
    for row in receipt['files']:
        if row.get('rawPath') == 'http/.gitattributes':
            if row.get('actual') != {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}:
                raise ValueError('Captured attribute response differs from actual transfer identity')
            row['originalRawPath'] = row['rawPath']
            row['rawPath'] = 'http/.gitattributes.response.bin'
            changed += 1
    if changed != 1:
        raise ValueError('Expected one captured attribute response in receipt')
    receipt['capturePathRelocation'] = {
        'from': 'http/.gitattributes', 'to': 'http/.gitattributes.response.bin',
        'bytes': len(raw), 'sha256': sha256(raw).hexdigest(),
        'scope': 'Response bytes and all transfer results unchanged; archive basename avoids active Git directives. Original receipt bytes retained separately.',
    }
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')


def main():
    sys.dont_write_bytecode = True
    before = [stamp(p) for p in [Path(__file__), GUARD, ADVANCE, SCHEDULER]]
    guard = module('scheduler_source_guard_transfers', GUARD)
    advance = module('scheduler_source_advance_paths', ADVANCE)
    scheduler = module("controlled_source_scheduler_paths", SCHEDULER)
    guard.ADDITIONS = (*guard.ADDITIONS, *advance.ADDITIONS, *scheduler.EXTRA, *EXTRA)
    status = guard.main()
    if before != [stamp(p) for p in [Path(__file__), GUARD, ADVANCE, SCHEDULER]]:
        raise ValueError('Source checker or helpers changed during observation')
    out = Path(sys.argv[2]).resolve()
    archive_attribute_response(out)
    (out / 'controlled-wrapper.py.txt').write_bytes(Path(__file__).read_bytes())
    guard.write_json(out / 'controlled-wrapper.json', {
        'status': 'PASS' if status == 0 else 'FAIL', 'wrapperAndHelpers': before,
        'extraPaths': EXTRA, 'controlledGNUAccepted': False,
        'scope': 'Unchanged bounded HTTP/Git-byte checker with explicit controlled tick and retained scheduler source/doc paths. Raw equality only, not new scheduler numerical, GNU, main integration or browser API acceptance.',
    })
    return status


if __name__ == '__main__':
    raise SystemExit(main())
