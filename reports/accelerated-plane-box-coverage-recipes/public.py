"""Read-only exact-commit Actions state and selected Pages byte comparison."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import subprocess
import sys
import urllib.request

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'accelerated-plane-box-coverage'
MAX_BYTES = 16 * 1024 * 1024
PATHS = (
    'core/include/pikapika/simulation_api.h',
    'core/src/simulation_api.cpp',
    'core/src/sphere_triangle_mesh_flight_api_internal.hpp',
    'tests/sphere_triangle_mesh_flight_sdk_tests.cpp',
    'tests/sphere_triangle_mesh_flight_sdk_support.hpp',
    'tools/sphere_triangle_mesh_flight_sdk_probe.cpp',
    'scripts/verify-sphere-triangle-mesh-flight-native-sdk.py',
    'scripts/verify-sphere-triangle-mesh-flight-wasm-wire.mjs',
    'scripts/build-simulation.mjs',
    'CMakeLists.txt',
    'core/include/pikapika/sphere_triangle_mesh_held_load.hpp',
    'core/src/sphere_triangle_mesh_held_load.cpp',
    'core/include/pikapika/sphere_triangle_mesh_free_flight_guard.hpp',
    'core/src/sphere_triangle_mesh_free_flight_guard.cpp',
    'core/src/free_flight_internal.hpp',
    'core/src/dynamics.cpp',
    'core/src/continuous_world.cpp',
    'tests/sphere_triangle_mesh_held_load_fixtures.cpp',
    'tests/sphere_triangle_mesh_held_load_test_support.hpp',
    'tests/sphere_triangle_mesh_free_flight_guard_fixtures.cpp',
    'tests/sphere_triangle_mesh_free_flight_guard_test_support.hpp',
    'docs/SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md',
    'docs/SPHERE_TRIANGLE_MESH_FLIGHT_SDK_PLAN.md',
    'docs/learn/diagrams/sphere-triangle-mesh-flight-sdk.svg',
    'docs/learn/index.html',
    'docs/PLAN.md',
    'docs/RESEARCH.md',
    'docs/legal/ASSETS.md',
    'docs/legal/DEPENDENCIES.md',
    'docs/legal/REFERENCES.md',
    'assets/pikapika-simulation.wasm',
    'assets/pikapika-simulation.mjs',
    'assets/pikapika-simulation.build.json',
    'engine/simulation.mjs',
    'engine/sphere-triangle-mesh-entry.mjs',
    'tools/sphere-triangle-mesh-entry-lab.html',
    'tools/sphere-triangle-mesh-entry-lab.mjs',
    'index.html',
    'style.css',
    'samples/app.mjs',
    'samples/robot.mjs',
    'samples/back-cover.mjs',
    'assets/robot-back-cover.skin.json',
    'assets/robot-back-cover.scene.json',
    'tools/free_flight_legacy_probe.cpp',
)
PATHS += (
    'engine/sphere-triangle-mesh-flight.mjs',
    'tests/sphere-triangle-mesh-flight.test.mjs',
    'scripts/verify-sphere-triangle-mesh-flight-sdk.mjs',
    'scripts/verify-sphere-triangle-mesh-flight-owned.py',
    'docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS.md',
    'docs/learn/diagrams/sphere-triangle-mesh-flight-owned.svg',
    'reports/sphere-triangle-mesh-flight-js-browser/index.html',
)
PATHS += (
    'tools/sphere-triangle-mesh-flight-lab.html',
    'tools/sphere-triangle-mesh-flight-lab.mjs',
    'tools/sphere-triangle-mesh-flight-presets.mjs',
    'tests/sphere-triangle-mesh-flight-lab.test.mjs',
    'scripts/verify-sphere-triangle-mesh-flight-lab.mjs',
    'scripts/build-web.mjs',
    'tests/web-build.test.mjs',
    'docs/SPHERE_TRIANGLE_MESH_FLIGHT_LAB.md',
    'docs/SPHERE_TRIANGLE_MESH_FLIGHT_LAB_PLAN.md',
    'docs/learn/diagrams/sphere-triangle-mesh-flight-lab.svg',
)
PATHS += (
    'core/include/pikapika/world_static_mesh_flight.hpp',
    'core/src/world_static_mesh_flight.cpp',
    'tests/world_static_mesh_flight_preparation_tests.cpp',
    'tests/world_static_mesh_flight_preparation_fixtures.cpp',
    'tests/world_static_mesh_flight_preparation_support.hpp',
    'scripts/verify-world-static-mesh-preparation.py',
    'tests/world_static_mesh_preparation_reference_tests.py',
    'docs/WORLD_STATIC_MESH_PREPARATION.md',
    'docs/WORLD_STATIC_MESH_FLIGHT_PLAN.md',
    'docs/learn/diagrams/world-static-mesh-preparation.svg',
    '.github/workflows/verify.yml',
    '.gitattributes',
)
PATHS += (
    'core/include/pikapika/accelerated_pair_coverage.hpp',
    'core/src/accelerated_pair_coverage.cpp',
    'tests/accelerated_pair_coverage_tests.cpp',
    'tests/accelerated_pair_coverage_fixtures.cpp',
    'tests/accelerated_pair_coverage_test_support.hpp',
    'scripts/verify-accelerated-pair-coverage.py',
    'tests/accelerated_pair_coverage_reference_tests.py',
    'docs/ACCELERATED_PAIR_COVERAGE.md',
    'docs/ACCELERATED_PAIR_COVERAGE_PLAN.md',
    'docs/learn/diagrams/accelerated-pair-coverage.svg',
)
PATHS += ('core/include/pikapika/accelerated_plane_box_coverage.hpp', 'core/src/accelerated_plane_box_coverage.cpp', 'tests/accelerated_plane_box_coverage_tests.cpp', 'tests/accelerated_plane_box_coverage_fixtures.cpp', 'tests/accelerated_plane_box_coverage_test_support.hpp', 'scripts/verify-accelerated-plane-box-coverage.py', 'tests/accelerated_plane_box_coverage_reference_tests.py', 'docs/ACCELERATED_PLANE_BOX_COVERAGE.md', 'docs/ACCELERATED_PLANE_BOX_COVERAGE_PLAN.md', 'docs/learn/diagrams/accelerated-plane-box-coverage.svg', 'docs/WORLD_PREDICATE_FLOATING_POINT_AUDIT.md', 'docs/WORLD_STATIC_MESH_FLIGHT_SEED_AUDIT.md', 'docs/WORLD_STATIC_MESH_PLANE_COVERAGE_PLAN.md', 'reports/accelerated-plane-box-coverage-local-verification.json', 'reports/2026-11-04-accelerated-plane-box-coverage.md', 'reports/accelerated-plane-box-coverage-primary-sources.json')
assert len(PATHS) == len(set(PATHS)) == 100


def request(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'pikapikaengine-public-verification', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = response.read(MAX_BYTES + 1)
        assert len(result) <= MAX_BYTES, url
        return result


def blob(commit, path):
    data = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
    assert len(data) <= MAX_BYTES
    return data


def main():
    assert len(sys.argv) == 3, 'Usage: public.py status|bytes FULL_FEATURE_COMMIT'
    mode, commit = sys.argv[1:]
    assert re.fullmatch('[0-9a-f]{40}', commit), 'A full exact feature commit is required'
    assert subprocess.check_output(['git', 'rev-parse', commit + '^{commit}'], cwd=ROOT, text=True).strip() == commit
    if mode == 'status':
        url = 'https://api.github.com/repos/tatata93/pikapikaengine/actions/runs?head_sha=' + commit + '&per_page=10'
        runs = json.loads(request(url))['workflow_runs']
        assert type(runs) is list and len(runs) <= 10
        assert all(run['head_sha'] == commit for run in runs)
        result = {'schema': 1, 'checked': datetime.now(timezone.utc).isoformat(), 'commit': commit, 'runs': runs}
        target = ROOT / f'reports/{PREFIX}-public-runs.json'
        target.write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
        print(json.dumps([{key: run[key] for key in ['id', 'name', 'status', 'conclusion', 'html_url']} for run in runs]))
    elif mode == 'bytes':
        html = blob(commit, 'index.html').decode('utf-8')
        match = re.search(r'\?build=([0-9a-f]{16})', html);assert match
        build = match.group(1)
        files = []
        for path in PATHS:
            query = '?build=' + build if path.startswith('assets/') or path.endswith('.mjs') else '?v=' + commit[:7]
            distribution = 'github-source' if path == '.github/workflows/verify.yml' else 'pages'
            url = ('https://raw.githubusercontent.com/tatata93/pikapikaengine/' + commit + '/' + path
                   if distribution == 'github-source' else 'https://tatata93.github.io/pikapikaengine/' + path + query)
            actual = request(url)
            assert actual == blob(commit, path), path + ' public bytes differ from feature blob'
            files.append({'path': path, 'url': url, 'distribution': distribution, 'bytes': len(actual), 'sha256': sha256(actual).hexdigest()})
        result = {'schema': 1, 'status': 'PASS', 'commit': commit, 'checked': datetime.now(timezone.utc).isoformat(),
                  'build': build, 'files': files, 'channels': {'pages': 99, 'githubSource': 1}}
        assert sum(row['distribution'] == 'pages' for row in files) == 99
        assert sum(row['distribution'] == 'github-source' for row in files) == 1
        assert sum(row['bytes'] for row in files) <= 64 * 1024 * 1024
        target = ROOT / f'reports/{PREFIX}-public-bytes.json'
        target.write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
        print(json.dumps({'status': 'PASS', 'files': len(files), 'bytes': sum(row['bytes'] for row in files), 'build': build, 'channels': result['channels']}))
    else:
        raise ValueError('status or bytes required')


if __name__ == '__main__':
    main()
