"""Extend the unchanged guard HTTP/blob checker with explicit advance files.

Usage: python public-bytes.py FULL_COMMIT FRESH_OUTPUT
The guard checker retains its exact raw-byte HTTP/Git checks and bounded reads.
This wrapper adds source/documentation paths; it does not imply numeric or UI acceptance.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'reports/world-static-mesh-flight-guard-recipes/public-bytes.py'
ADDITIONS = (
    'CMakeLists.txt',
    'core/include/pikapika/world_static_mesh_flight_advance.hpp',
    'core/src/world_static_mesh_flight_advance.cpp',
    'tests/world_static_mesh_flight_advance_tests.cpp',
    'tests/world_static_mesh_flight_advance_fixtures.cpp',
    'tests/world_static_mesh_flight_advance_fixture_support.hpp',
    'scripts/verify-world-static-mesh-flight-advance.py',
    'tests/world_static_mesh_flight_advance_reference_tests.py',
    'docs/WORLD_STATIC_MESH_FLIGHT_ADVANCE_NATIVE.md',
    'docs/WORLD_STATIC_MESH_FLIGHT_ADVANCE_PLAN.md',
    'docs/learn/diagrams/world-static-mesh-flight-advance-native.svg',
    'reports/2026-11-05-world-static-mesh-flight-advance-native.md',
    'reports/world-static-mesh-flight-advance-native-integration-verification.json',
    'reports/world-static-mesh-flight-advance-formal-target-verification.json',
    'reports/world-static-mesh-flight-advance-recipes/verify-gnu.py',
    'reports/world-static-mesh-flight-advance-recipes/GNU_PLAN.md',
    'reports/world-static-mesh-flight-advance-recipes/clock-reference.py',
)


def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    sys.dont_write_bytecode = True
    before = {str(p): stamp(p) for p in [Path(__file__), HELPER]}
    spec = importlib.util.spec_from_file_location('advance_public_bytes_guard', HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    original = helper.ADDITIONS
    helper.ADDITIONS = (*original, *ADDITIONS)
    status = helper.main()
    after = {str(p): stamp(p) for p in [Path(__file__), HELPER]}
    if before != after:
        raise ValueError('Public byte helper/wrapper changed during capture')
    out = Path(sys.argv[2]).resolve()
    (out / 'advance-wrapper.py.txt').write_bytes(Path(__file__).read_bytes())
    helper.write_json(out / 'advance-wrapper.json', {
        'status': 'PASS' if status == 0 else 'FAIL',
        'wrapperAndHelper': before, 'sourceStable': True,
        'additionalPaths': ADDITIONS,
        'scope': 'Unchanged helper main and transfer logic with explicit ADDITIONS extension. Raw byte equality only, no numeric, CI or browser acceptance.',
    })
    return status


if __name__ == '__main__':
    sys.exit(main())
